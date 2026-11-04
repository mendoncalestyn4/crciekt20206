"""python3 make_weird.py <dir>: weird careers made from the project's own test scorecards (never the owner's), each a PC
with a watched Scorecards folder and a career home, for putting the whole website through odd cases:
  empty      no scorecards at all
  one        a single match
  abandoned  only abandoned games (and one rain-hit Blast game)
  oddnames   every scorecard, with names full of apostrophes, accents, other alphabets, HTML-like text and ampersands
  county     County Championship only, played as a county
  ipl        IPL only, played as a franchise
  noteam     every scorecard, with no team picked as yours
  messy      every scorecard, plus the same one twice under another name, a cut-off one, and junk files"""
import random
import re
import shutil
import sys
from pathlib import Path

ROOT = Path("/home/user/crciekt20206")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from serverkit import FIXTURES, played_in_order, png  # noqa: E402

from ccstats.local import CareerStore, Watcher  # noqa: E402

STRESS = ROOT / "tests" / "fixtures_stress"
base = Path(sys.argv[1])
random.seed(11)


def pc(name, files, team, extra=None):
    home = base / name
    if home.exists():
        shutil.rmtree(home)
    game = home / "Cricket Captain 2026"
    folder = game / "Scorecards"
    folder.mkdir(parents=True)
    for f in files:
        if isinstance(f, tuple):
            (folder / f[0]).write_bytes(f[1])
        else:
            shutil.copy(f, folder / f.name)
    played_in_order(folder)
    if extra:
        extra(folder)
    png(game / "editor" / "emblems" / "englandem.png", (18, 36, 96, 255))
    png(game / "editor" / "emblems" / "indiaem.png", (40, 90, 220, 255))
    store = CareerStore(home / "home")
    Watcher(store).create("Weird " + name, folder)
    s = store.load_settings("Weird " + name)[1]
    s.my_teams = [team] if team else []
    store.save_settings(s)
    print(name, len(list(folder.iterdir())), "files, playing as", team or "nobody")


ODD = [lambda s: "O'" + s, lambda s: s + "ë", lambda s: s + "-Ñúñez", lambda s: "Đ" + s[1:], lambda s: s + "&Co",
       lambda s: "<b>" + s + "</b>", lambda s: s + " Jr.", lambda s: "李" + s, lambda s: s + "'s"]


def odd(text: str) -> str:
    """Several surnames in a scorecard changed everywhere they appear (batting, bowling, how out)."""
    names = re.findall(r"^[A-Z][a-z']* ([A-Z][A-Za-z'-]{2,})\s{2,}", text, flags=re.M)
    for i, sur in enumerate(dict.fromkeys(names)):
        if i % 3 == 0:
            text = re.sub(rf"\b{re.escape(sur)}\b", ODD[(i // 3) % len(ODD)](sur), text)
    return text


county = [f for f in FIXTURES if "_county_" in f.name]
ipl = [f for f in FIXTURES if "_ipl" in f.name]
pc("empty", [], "England")
pc("one", FIXTURES[:1], "Worcestershire")
pc("abandoned", sorted(STRESS.glob("*.txt")), "England")
pc("oddnames", [(f.name, odd(f.read_text()).encode()) for f in FIXTURES], "England")
pc("county", county, "Somerset")
pc("ipl", ipl, "Mumbai Indians")
pc("noteam", FIXTURES, "")


def messy(folder):
    first = sorted(folder.iterdir())[0]
    (folder / ("copy of " + first.name)).write_bytes(first.read_bytes())
    t = sorted(folder.iterdir())[3].read_text()
    (folder / "cut_off_mid_save.txt").write_text(t[: len(t) // 2])
    (folder / "notes.txt").write_text("my own notes, not a scorecard\n")
    (folder / "empty.txt").write_text("")
    (folder / "picture.txt").write_bytes(bytes(random.randrange(256) for _ in range(4000)))
    (folder / "desktop.ini").write_text("[.ShellClassInfo]\n")
pc("messy", FIXTURES, "India", extra=messy)
