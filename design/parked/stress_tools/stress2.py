"""python3 -I stress2.py <port> <out.txt>: the stage 1 stress test, round two, on a running site. Every player in every
competition they've played (and every season of it for the regulars), the match finder and the best games for every
competition and every team in it, search with hundreds of typed searches, and junk in every box and address: empty,
very long, odd characters, hacking-style text. The site must answer every one cleanly: no failed request (a 500), no
part that couldn't be worked out, no hang, and a plain 404 or 400 for anything that isn't there."""
import json
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

base = f"http://127.0.0.1:{sys.argv[1]}"
log = open(sys.argv[2], "w")
problems, times = [], []
random.seed(7)


def say(*a):
    print(*a, file=log, flush=True)


def get(path, raw=False):
    url = base + (path if raw else urllib.parse.quote(path, safe="/?=&"))
    t0 = time.time()
    try:
        with urllib.request.urlopen(url, timeout=600) as r:
            body, status = r.read(), r.status
    except urllib.error.HTTPError as e:
        body, status = e.read(), e.code
    except Exception as e:  # noqa: BLE001 - a hang or a dropped connection is a problem too
        body, status = str(e).encode(), -1
    times.append((time.time() - t0, path[:120]))
    return status, body


def broken(v, where=""):
    out = []
    if isinstance(v, dict):
        for k, x in v.items():
            if k == "missing" and isinstance(x, dict) and x:
                out += [f"{where}.missing.{a}: {b}" for a, b in x.items() if "Couldn't be worked out" in str(b)]
            else:
                out += broken(x, f"{where}.{k}")
    elif isinstance(v, list):
        for i, x in enumerate(v):
            out += broken(x, f"{where}[{i}]")
    elif isinstance(v, str) and v.startswith("Couldn't be worked out"):
        out.append(f"{where}: {v}")
    return out


def check(path, ok=(200,), raw=False):
    status, body = get(path, raw)
    if status not in ok:
        problems.append(f"{status} {path[:150]}: {body[:160]!r}")
        return None
    if status != 200:
        return None
    try:
        d = json.loads(body)
    except ValueError:
        problems.append(f"not JSON {path[:150]}")
        return None
    for b in broken(d):
        problems.append(f"{path[:120]} {b}"[:300])
    return d


t_all = time.time()
names = check("/api/names")["names"]

# 1. every player in every competition they've played; every season of it for the regulars
pages = []


def player_pages(n):
    d = check(f"/api/player?name={n}")
    if not d:
        return []
    out = [f"/api/player?name={n}&section={s}" for s in d.get("sections", []) if s != d.get("section")]
    if (d.get("card") or {}).get("matches", 0) >= 30:   # the regulars: every season of their main competition
        out += [f"/api/player?name={n}&section={d.get('section')}&season={s}" for s in d.get("seasons", []) if s != "All seasons"]
    return out


with ThreadPoolExecutor(4) as ex:
    for more in ex.map(player_pages, names):
        pages += more
say(f"players: {len(names)}; their other competitions and seasons: {len(pages)}")
with ThreadPoolExecutor(4) as ex:
    list(ex.map(check, pages))
say(f"  done, problems so far {len(problems)}")

# 2. the match finder and the best games for every competition, and every team in it
f = check("/api/matches")
secs = f["sections"]
finder = []
for s in secs:
    d = check(f"/api/matches?section={s}")
    if d:
        finder += [f"/api/matches?section={s}&team={t}" for t in d["teams"] if t != "All teams"]
    finder.append(f"/api/matches/best?section={s}")
with ThreadPoolExecutor(4) as ex:
    list(ex.map(check, finder))
say(f"finder: {len(secs)} competitions, {len(finder)} lists, problems so far {len(problems)}")

# 3. search (Ctrl K): everyone who batted or bowled, every team and every competition can be found
sr = check("/api/search") or {"items": []}
found = {(i["kind"], i["value"]) for i in sr["items"]}
lost = [n for n in names if ("player", n) not in found]
teams = {t for m_ in check("/api/matches?section=All sections")["matches"] for t in (m_["home"], m_["away"])}
lost += [t for t in teams if ("team", t) not in found]
lost += [x for x in secs if x != "All sections" and ("section", x) not in found]
if lost:
    problems.append(f"search can't find {len(lost)}: {lost[:10]}")
say(f"search: {len(sr['items'])} things to find; every player ({len(names)}), team ({len(teams)}) and competition checked")

# 4. junk in every box and address: a plain answer (404/400) or the page, never a 500 or a hang
junk = ["", " ", "%20", "..", "../../etc/passwd", "<script>alert(1)</script>", "' OR 1=1 --", "\" ; DROP TABLE x;",
        "名前", "Ⅻ", "😀", "a" * 5000, "%00", "null", "undefined", "NaN", "-1", "999999999999", "{}", "[]", "\\", "/", "?",
        "&", "#", "S%20Gill", "s gill", "S  Gill", "S Gill ", " S Gill", "Tests' ", "India\nEngland"]
tries = []
for j in junk:
    q = urllib.parse.quote(j, safe="")
    tries += [f"/api/player?name={q}", f"/api/player?name=S%20Gill&section={q}", f"/api/player?name=S%20Gill&season={q}",
              f"/api/myteam?team={q}", f"/api/myteam?team=India&section={q}", f"/api/scouting?team={q}", f"/api/match/{q}",
              f"/api/matches?section={q}", f"/api/matches?section=Tests&team={q}", f"/api/matches/best?section={q}",
              f"/api/logo/team/{q}", f"/api/logo/comp/{q}"]
with ThreadPoolExecutor(8) as ex:
    list(ex.map(lambda p: check(p, ok=(200, 400, 404), raw=True), tries))
say(f"junk: {len(junk)} kinds of junk in 12 places each ({len(tries)} requests), problems so far {len(problems)}")

times.sort(reverse=True)
slow = [x for x in times if x[0] > 30]
say(f"requests: {len(times)} in {time.time() - t_all:.0f}s; over 30 seconds: {len(slow)}; slowest: "
    + "; ".join(f"{t:.1f}s {p}" for t, p in times[:5]))
say(f"PROBLEMS: {len(problems)}")
for p in problems[:80]:
    say("  ", p)
