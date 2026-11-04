"""python3 -I stress1.py <port> <out.txt>: the stage 1 stress test on a running site. Every player's page, every match's
page, My team and Scouting for every team in every competition, then 40 requests at once compared with the same pages
asked one by one, then the Inbox's read and remove pressed fast and put back. Anything other than a clean answer is
written down: a failed request, a part that couldn't be worked out, or an answer that differs under load."""
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

base = f"http://127.0.0.1:{sys.argv[1]}"
log = open(sys.argv[2], "w")
problems, times = [], []


def say(*a):
    print(*a, file=log, flush=True)


def get(path, data=None):
    url = base + urllib.parse.quote(path, safe="/?=&")
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None,
                                 headers={"Content-Type": "application/json"} if data is not None else {})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=900) as r:
            body = r.read()
            status = r.status
    except urllib.error.HTTPError as e:
        body, status = e.read(), e.code
    times.append((time.time() - t0, path))
    return status, body


def broken(v, where=""):
    """Every part that says it couldn't be worked out, anywhere in the answer."""
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


def check(path, ok=(200,)):
    status, body = get(path)
    if status not in ok:
        problems.append(f"{status} {path}: {body[:160]!r}")
        return None
    if status != 200:
        return None
    try:
        d = json.loads(body)
    except ValueError:
        problems.append(f"not JSON {path}")
        return None
    for b in broken(d):
        problems.append(f"{path} {b}"[:300])
    return d


t_all = time.time()
career = check("/api/career")
names = check("/api/names")["names"]
say(f"players: {len(names)}")
with ThreadPoolExecutor(4) as ex:
    list(ex.map(lambda n: check(f"/api/player?name={n}"), names))
say(f"  done, problems so far {len(problems)}")

matches = check("/api/matches?section=All sections")["matches"]
say(f"matches: {len(matches)}")
with ThreadPoolExecutor(4) as ex:
    list(ex.map(lambda mt: check(f"/api/match/{mt['id']}"), matches))
say(f"  done, problems so far {len(problems)}")

finder = check("/api/matches?section=All sections")
teams = sorted({t for mt in matches for t in (mt["home"], mt["away"])})
say(f"teams: {len(teams)}")
pages = []
for t in teams:
    d = check(f"/api/myteam?team={t}")
    if d:
        pages += [f"/api/myteam?team={t}&section={s}" for s in d.get("sections", [])]
        pages.append(f"/api/scouting?team={t}")
with ThreadPoolExecutor(4) as ex:
    list(ex.map(check, pages))
say(f"  My team and Scouting pages: {len(pages) + len(teams)}, problems so far {len(problems)}")

# 40 at once: the same answers as one by one (the inbox is left out: it changes as you read it)
burst = ([f"/api/player?name={n}" for n in names[:: max(1, len(names) // 12)][:12]]
         + [f"/api/match/{mt['id']}" for mt in matches[:: max(1, len(matches) // 12)][:12]]
         + [f"/api/myteam?team={t}" for t in teams[:8]] + [f"/api/scouting?team={t}" for t in teams[:4]]
         + ["/api/players", "/api/names", "/api/matches", "/api/career"])
alone = {p: get(p)[1] for p in burst}
for round_ in range(3):
    with ThreadPoolExecutor(40) as ex:
        together = dict(zip(burst, ex.map(lambda p: get(p)[1], burst)))
    for p in burst:
        if together[p] != alone[p]:
            problems.append(f"different under load (round {round_ + 1}): {p}")
say(f"burst: {len(burst)} pages x 3 rounds of 40 at once, problems so far {len(problems)}")

# the inbox: read pressed 50 times at once, then 3 removed (the career's inbox state is backed up and put back by the
# caller, as the site has no undo for these)
box = check("/api/inbox")
if box and box["messages"]:
    ids = [m["id"] for m in box["messages"][:10]]
    for _ in range(5):
        with ThreadPoolExecutor(10) as ex:
            list(ex.map(lambda i: get("/api/inbox", {"read": [i]}), ids))
    after = check("/api/inbox")
    if not all(m["read"] for m in after["messages"] if m["id"] in ids):
        problems.append("inbox: a message pressed read isn't read")
    if after["unread"] != sum(not m["read"] for m in after["messages"]):
        problems.append("inbox: the unread count doesn't match the messages")
    get("/api/inbox", {"remove": ids[:3]})
    after = check("/api/inbox")
    if {m["id"] for m in after["messages"]} & set(ids[:3]):
        problems.append("inbox: a removed message is still there")
    if len(after["messages"]) != len(box["messages"]) - 3:
        problems.append(f"inbox: {len(box['messages'])} messages, 3 removed, {len(after['messages'])} left")
    status, _ = get("/api/inbox", {"read": "not a list"})
    if status != 400:
        problems.append(f"inbox: a bad request answered {status}, not 400")
    say(f"inbox: read pressed 50 times at once, 3 removed, a bad request refused; problems so far {len(problems)}")

times.sort(reverse=True)
say(f"requests: {len(times)}, in {time.time() - t_all:.0f}s; slowest: " + "; ".join(f"{t:.1f}s {p}" for t, p in times[:5]))
say(f"PROBLEMS: {len(problems)}")
for p in problems[:60]:
    say("  ", p)
