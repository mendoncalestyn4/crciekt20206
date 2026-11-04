"""python3 stage0_stress.py <dir> <port>: the stage 0 stress test (the server, careers, folder watching, live news,
logos, colours, style guide, the website's addresses). Builds a home with three careers from the project's own test
scorecards, starts the site on <port>, then: switches careers fast while pages load; drops 30 scorecards into the
watched folder in a burst (some half-saved first, as the game writes them) with 30 live-news connections open; asks
for every logo, every nation's colours and style guide; and throws junk at every address. Prints every problem."""
import http.client
import json
import random
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path("/home/user/crciekt20206")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from serverkit import FIXTURES, by_date, played_in_order  # noqa: E402

from ccstats.local import CareerStore, Watcher  # noqa: E402

base_dir, port = Path(sys.argv[1]), int(sys.argv[2])
base = f"http://127.0.0.1:{port}"
problems = []
random.seed(5)


def get(path, data=None, method=None, raw=False, ctype="application/json"):
    url = base + (path if raw else urllib.parse.quote(path, safe="/?=&"))
    body = data if isinstance(data, bytes) else (json.dumps(data).encode() if data is not None else None)
    req = urllib.request.Request(url, data=body, method=method, headers={"Content-Type": ctype} if body is not None else {})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:  # noqa: BLE001 - a hang or a dropped connection is a problem
        return -1, str(e).encode()


# ---------------------------------------------------------------- a home with three careers, one watching a folder
home = base_dir / "stage0"
if home.exists():
    shutil.rmtree(home)
ordered = sorted(FIXTURES, key=by_date)
store = CareerStore(home / "home")
folders = {}
for name, files in (("Alpha", ordered[:20]), ("Bravo", [f for f in FIXTURES if "_county_" in f.name]),
                    ("Charlie", [f for f in FIXTURES if "_ipl" in f.name])):
    folder = home / name / "Scorecards"
    folder.mkdir(parents=True)
    for f in files:
        shutil.copy(f, folder / f.name)
    played_in_order(folder)
    Watcher(store).create(name, folder)
    folders[name] = folder
for name, team in (("Alpha", "England"), ("Bravo", "Somerset"), ("Charlie", "Mumbai Indians")):
    s = store.load_settings(name)[1]
    s.my_teams = [team]
    store.save_settings(s)
serve = Path("/tmp/claude-0/-home-user-crciekt20206/db8ebe3d-6d6c-58e2-9ecc-4739d2cc52d6/scratchpad/serve.sh")
subprocess.run(["bash", str(serve), str(port), str(home / "home")], capture_output=True, timeout=300)
print("site up:", get("/api/health"))

# ---------------------------------------------------------------- 1. careers switched fast while pages load
names = json.loads(get("/api/careers")[1])["careers"]
stop = threading.Event()
seen = []


def reader():
    while not stop.is_set():
        for p in ("/api/career", "/api/myteam", "/api/players", "/api/matches", "/api/inbox", "/api/names", "/api/search"):
            st, body = get(p)
            seen.append(st)
            if st not in (200, 404):
                problems.append(f"while switching: {st} {p} {body[:120]!r}")


threads = [threading.Thread(target=reader) for _ in range(8)]
for t in threads:
    t.start()
for k in range(60):
    st, body = get("/api/careers/current", {"name": names[k % len(names)]})
    if st != 200:
        problems.append(f"switch to {names[k % len(names)]}: {st} {body[:100]!r}")
    time.sleep(0.05)
stop.set()
for t in threads:
    t.join()
get("/api/careers/current", {"name": "Alpha"})
info = json.loads(get("/api/career")[1])
if info["name"] != "Alpha" or info["matches"] != 20:
    problems.append(f"after switching: career {info['name']} with {info['matches']} matches, not Alpha with 20")
print(f"1. 60 switches with 8 readers ({len(seen)} pages read): problems so far {len(problems)}")

# ---------------------------------------------------------------- 2+3. a burst of scorecards, 30 live-news connections
heard = [0] * 30


def listen(i):
    try:
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=150)
        c.request("GET", "/api/events")
        r = c.getresponse()
        end = time.time() + 140
        while time.time() < end:
            line = r.fp.readline()
            if not line:
                break
            if line.startswith(b"data:"):
                heard[i] += 1
                if heard[i] >= 1:
                    break
        c.close()
    except Exception as e:  # noqa: BLE001
        problems.append(f"live news connection {i}: {e}")


listeners = [threading.Thread(target=listen, args=(i,)) for i in range(30)]
for t in listeners:
    t.start()
time.sleep(1)
folder = folders["Alpha"]
for f in ordered[20:50]:
    text = f.read_bytes()
    if random.random() < 0.3:   # half-saved first, finished a moment later
        (folder / f.name).write_bytes(text[: len(text) // 2])
        time.sleep(0.2)
    (folder / f.name).write_bytes(text)
played_in_order(folder)
deadline, count = time.time() + 150, 20
while time.time() < deadline:
    count = json.loads(get("/api/career")[1])["matches"]
    if count >= 50:
        break
    time.sleep(3)
for t in listeners:
    t.join(timeout=160)
if count != 50:
    problems.append(f"after the burst the career has {count} matches, not 50")
if sum(1 for h in heard if h) < 30:
    problems.append(f"live news: {sum(1 for h in heard if h)} of 30 connections heard about the new matches")
for p in ("/api/myteam", "/api/players", "/api/matches", "/api/inbox"):
    st, body = get(p)
    if st != 200:
        problems.append(f"after the burst: {st} {p}")
print(f"2-3. 30 scorecards dropped (some half-saved first): career now {count} matches; "
      f"{sum(1 for h in heard if h)} of 30 live connections told; problems so far {len(problems)}")

# ---------------------------------------------------------------- 4. every logo, colour and style guide
logos = json.loads(get("/api/logos")[1])
for kind, key in (("team", "teams"), ("comp", "comps")):
    for name in logos[key]:
        for size in (24, 48, 96):
            st, _ = get(f"/api/logo/{kind}/{name}?size={size}")
            if st != 200:
                problems.append(f"logo {kind} {name} {size}: {st}")
for path, want in (("/api/logo/team/No Such Team", 404), ("/api/logo/planet/India", 400), ("/api/logo/team/India?size=7", 400),
                   ("/api/logo/team/India?size=abc", 400), ("/api/logo/team/..%2F..%2Fetc%2Fpasswd", 404)):
    st, _ = get(path, raw="%2F" in path)
    if st != want:
        problems.append(f"{path}: {st}, not {want}")
nations = json.loads(get("/api/nations")[1])["nations"]
for nation in nations + ["none"]:
    for p in (f"/api/theme?nation={nation}", f"/api/styleguide?nation={nation}"):
        st, body = get(p)
        if st != 200:
            problems.append(f"{p}: {st} {body[:100]!r}")
if get("/api/theme?nation=Atlantis")[0] != 404:
    problems.append("an unknown nation's colours aren't a 404")
print(f"4. {len(logos['teams'])} team and {len(logos['comps'])} competition logos at 3 sizes, {len(nations)} nations' "
      f"colours and style guide: problems so far {len(problems)}")

# ---------------------------------------------------------------- 5. junk at every address
junk = [("GET", "/api/no-such-thing", None, (404,)), ("POST", "/api/career", {}, (405,)), ("DELETE", "/api/inbox", None, (405,)),
        ("POST", "/api/careers/current", b"not json", (415, 400)), ("POST", "/api/careers/current", {"name": "Nobody"}, (404,)),
        ("POST", "/api/careers/current", {"name": ["a", "list"]}, (404, 400)), ("POST", "/api/inbox", {"read": "x"}, (400,)),
        ("POST", "/api/inbox", {"read": list(range(5000))}, (400,)), ("POST", "/api/inbox", b"x" * 2_000_000, (400, 413, 415)),
        ("POST", "/api/notes", {"match": "nope", "text": "hi"}, (400, 404)), ("POST", "/api/notes", {"match": 5, "text": ["x"]}, (400, 404)), ("POST", "/api/notes", {"match": "x", "text": "y" * 6000}, (400,)),
        ("GET", "/api/match/" + "9" * 400, None, (404,)), ("GET", "/api/player?name=" + "x" * 20000, None, (404, 414, 431))]
for method, path, data, want in junk:
    st, body = get(path, data, method=method)
    if st not in want:
        problems.append(f"{method} {path[:60]}: {st}, not {want} ({body[:100]!r})")
for path in ("/", "/players/Anyone", "/matches/zzz", "/a/b/c/d", "/teams?x=" + "y" * 3000, "/%E2%98%83"):
    st, body = get(path, raw=True)
    if st != 200 or b"<div id" not in body:
        problems.append(f"page {path[:40]}: {st}")
print(f"5. {len(junk)} junk requests and 6 odd page addresses: problems so far {len(problems)}")

print(f"PROBLEMS: {len(problems)}")
for p in problems[:50]:
    print("   ", p)
