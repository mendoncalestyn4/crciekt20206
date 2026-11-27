"""Pressure on the owner's save: ~2,000 different questions asked calmly once (the true answers), then by 16 visitors at
once, three rounds; every answer must be identical, no errors. Then a new match arrives while it's busy: every answer
afterwards must be the new career's, never a mix."""
import sys, os, json, time, random, shutil, urllib.request, urllib.parse as U, threading, pickle
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path[:0] = ["/home/user/crciekt20206", "/home/user/crciekt20206/tests"]
os.environ.setdefault("STATS_PACK_HELPERS", "0")
root = Path(sys.argv[1]); log = open(sys.argv[2], "w", buffering=1)
from ccstats.local import CareerStore
from server.app import create_app
from serverkit import Live
import freeze
# its own copy of the save and the career (with three teams set as yours), so a match can be added under pressure
press_cards, press_home = root / "Scorecards_press", root / "home_press"
for d in (press_cards, press_home):
    shutil.rmtree(d, ignore_errors=True)
shutil.copytree(root / "Scorecards", press_cards)       # (copytree keeps the files' times)
shutil.copytree(root / "home_mine", press_home)
fj = press_home / "folders.json"
fj.write_text(fj.read_text().replace(str(root / "Scorecards"), str(press_cards)))
store = CareerStore(press_home)
live = Live(create_app(store, web=Path("/home/user/crciekt20206/web/dist"), watch_every=0.5))
c = pickle.load(open(root / "career.pickle", "rb")); m = c.matches
rnd = random.Random(7)
teams = sorted(set(m.home) | set(m.away)); secs = sorted(set(m.section))
players = sorted(set(c.batting.player)); mids = list(m.match_id)
urls = set()
for t in rnd.sample(teams, 60):
    for ep in ("/api/team", "/api/myteam", "/api/fixtures", "/api/hall", "/api/selection"):
        urls.add(f"{ep}?{U.urlencode({'team': t})}")
for s in secs:
    for ep, tabs in (("/api/insights", ["", "Career arc", "Breakout players"]), ("/api/analytics", [""]), ("/api/stories", [""]),
                     ("/api/rankings", [""]), ("/api/records", [""]), ("/api/statbystat", [""])):
        for tab in tabs:
            urls.add(f"{ep}?{U.urlencode({'section': s, **({'tab': tab} if tab else {})})}")
for p in rnd.sample(players, 700):
    urls.add(f"/api/player?{U.urlencode({'name': p})}")
for mid in rnd.sample(mids, 900):
    urls.add(f"/api/match/{mid}")
urls = sorted(urls)
log.write(f"{len(urls)} questions\n")

def get(u):
    for _ in range(1200):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{live.port}{u}", timeout=900) as r:
                return r.status, freeze.clean(json.loads(r.read()))
        except urllib.error.HTTPError as e:
            if e.code == 503: time.sleep(0.5); continue
            return e.code, e.read()[:200]
        except Exception as e:
            return -1, str(e)[:200]
calm = {}
t = time.time()
for u in urls:
    calm[u] = get(u)
log.write(f"calm answers in {time.time() - t:.0f}s; errors: {[u for u, (s, _) in calm.items() if s != 200][:10]}\n")
bad = 0
for rnd_no in range(3):
    order = urls[:]; rnd.shuffle(order)
    t = time.time(); slow = []
    def one(u):
        t0 = time.time(); got = get(u); slow.append((time.time() - t0, u)); return u, got
    with ThreadPoolExecutor(16) as pool:
        for u, got in pool.map(one, order):
            if got != calm[u]:
                bad += 1; log.write(f"BAD round {rnd_no + 1}: {u} differs under pressure: {str(got)[:200]}\n")
    slow.sort(reverse=True)
    log.write(f"round {rnd_no + 1}: {len(order)} at once by 16 in {time.time() - t:.0f}s, slowest {slow[0][0]:.1f}s ({slow[0][1]})\n")
# a new match arrives while it's busy: one more scorecard (an existing card on a later date) into the watched folder
src = max(press_cards.glob("*.txt"), key=os.path.getmtime)
lines = src.read_text().split("\n")
head, _, _ = lines[2].rpartition(" - ")
lines[2] = f"{head} - 30 Dec 2040"
before = get("/api/career")[1]
stop = threading.Event(); errors = []
def hammer():
    while not stop.is_set():
        u = rnd.choice(urls); s_, got = get(u)
        if s_ != 200: errors.append((u, s_, got))
pool = [threading.Thread(target=hammer) for _ in range(16)]
for th in pool: th.start()
time.sleep(5)
new = press_cards / "30 dec 2040-pressure (new match).txt"
new.write_text("\n".join(lines)); t_new = time.time()
def count_of(x): return json.dumps(x).count("match_id")
seen_new = False
for _ in range(600):
    time.sleep(1)
    s_, cur = get("/api/career")
    if s_ == 200 and cur != before:
        seen_new = True; break
stop.set()
for th in pool: th.join()
log.write(f"new match taken in under pressure: {seen_new} after {time.time() - t_new:.0f}s; errors meanwhile: {len(errors)} {errors[:3]}\n")
twice = [u for u in rnd.sample(urls, 200) if get(u) != get(u)]
log.write(f"answers asked twice after the new match that differ: {len(twice)} {twice[:5]}\n")
bad += len(errors) + len(twice) + (0 if seen_new else 1)
log.write(f"DONE: {bad} answers differed under pressure\n")
live.stop()
