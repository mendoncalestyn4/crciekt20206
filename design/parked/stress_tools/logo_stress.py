"""python3 logo_stress.py <dir> <port>: the logo stress test. A pretend game folder with a picture for every team and
competition the game knows, made as awkward as real ones get: tiny, huge, see-through, black and white, odd colour
modes, and some broken (cut short, empty, not a picture at all). A career watches the scorecards beside it; the site
then serves every logo at every size on dark and light pages. Every answer must be a picture or a plain 404, never a
crash; the broken ones must give a 404, and the site's list of logos must only name ones it can draw."""
import io
import json
import random
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path("/home/user/crciekt20206")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from serverkit import FIXTURES, played_in_order  # noqa: E402

from ccstats import catalogue as CAT  # noqa: E402
from ccstats.local import CareerStore, Watcher  # noqa: E402

base_dir, port = Path(sys.argv[1]), int(sys.argv[2])
random.seed(3)
home = base_dir / "logos"
if home.exists():
    shutil.rmtree(home)
game = home / "Cricket Captain 2026"
folder = game / "Scorecards"
folder.mkdir(parents=True)
for f in FIXTURES:
    shutil.copy(f, folder / f.name)
played_in_order(folder)
emb, comp = game / "editor" / "emblems", game / "editor" / "complogos"
emb.mkdir(parents=True)
comp.mkdir(parents=True)


def picture(kind: int) -> bytes:
    size = [(1, 1), (8, 8), (64, 64), (256, 256), (300, 120), (120, 300), (2000, 2000)][kind % 7]
    mode = ["RGBA", "RGB", "L", "P", "LA", "I;16", "1"][kind % 7]
    im = Image.new("RGBA", size, (random.randrange(256), random.randrange(256), random.randrange(256), random.randrange(256)))
    if mode != "RGBA":
        im = im.convert("RGB").convert(mode) if mode != "I;16" else im.convert("L").convert("I;16")
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


BROKEN = {"empty": b"", "text": b"not a picture", "cut": None, "jpeg": None}
teams = sorted(set(CAT.every_team()))
m_names = set()
import re  # noqa: E402
for f in FIXTURES:
    first = f.read_text().splitlines()[1]
    m_names |= set(re.split(r" v ", first.strip()))
teams = sorted(set(teams) | m_names)
broken_names = set()
for i, t in enumerate(teams):
    data = picture(i)
    if i % 23 == 0:
        kind = ["empty", "text", "cut", "jpeg"][(i // 23) % 4]
        if kind == "cut":
            data = data[: len(data) // 3]
        elif kind == "jpeg":
            buf = io.BytesIO()
            Image.new("RGB", (40, 40), (200, 10, 10)).save(buf, "JPEG")
            data = buf.getvalue()
        else:
            data = BROKEN[kind]
        if kind != "jpeg":   # a JPEG saved as .png is a real picture the site can draw
            broken_names.add(t)
    (emb / f"{t}.png").write_bytes(data)
comps = ["Tests", "ODIs", "T20Is", "Indian Premier League", "T20 Blast", "The Hundred", "County Championship · Division 1",
         "Ranji Trophy", "Vijay Hazare Trophy", "World Cup", "T20 World Cup"]
for i, c in enumerate(comps):
    (comp / f"{c.replace('·', '-').replace('/', '-')}.png").write_bytes(picture(i + 3))
store = CareerStore(home / "home")
Watcher(store).create("Logos", folder)
s = store.load_settings("Logos")[1]
s.my_teams = ["India"]
store.save_settings(s)
serve = Path("/tmp/claude-0/-home-user-crciekt20206/db8ebe3d-6d6c-58e2-9ecc-4739d2cc52d6/scratchpad/serve.sh")
subprocess.run(["bash", str(serve), str(port), str(home / "home")], capture_output=True, timeout=300)

base = f"http://127.0.0.1:{port}"
problems = []


def get(path):
    try:
        with urllib.request.urlopen(base + path, timeout=120) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:  # noqa: BLE001
        return -1, str(e).encode()


listed = json.loads(get("/api/logos")[1])
asked = 0
for kind, names in (("team", teams), ("comp", comps)):
    for name in names:
        for size in (12, 28, 48, 96, 240):
            for page in ("dark", "light"):
                asked += 1
                st, body = get(f"/api/logo/{kind}/{urllib.parse.quote(name)}?size={size}&page={page}")
                if st == 200:
                    try:
                        im = Image.open(io.BytesIO(body))
                        im.load()
                    except Exception as e:  # noqa: BLE001
                        problems.append(f"{kind} {name} {size} {page}: not a picture ({e})")
                elif st != 404:
                    problems.append(f"{kind} {name} {size} {page}: {st} {body[:100]!r}")
                elif kind == "team" and name not in broken_names and name in listed["teams"]:
                    problems.append(f"{kind} {name} {size} {page}: listed as having a logo, but 404")
for name in listed["teams"]:
    if name in broken_names:
        problems.append(f"broken picture listed as a logo: {name}")
print(f"{len(teams)} team pictures ({len(broken_names)} broken on purpose), {len(comps)} competition pictures; "
      f"listed: {len(listed['teams'])} teams, {len(listed['comps'])} competitions; {asked} logos asked for")
print(f"PROBLEMS: {len(problems)}")
for p in problems[:40]:
    print("   ", p)
