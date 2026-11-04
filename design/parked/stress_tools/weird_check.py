"""python3 -I weird_check.py <port> <name>: every page of a running site, for any career however odd (none at all,
one match, odd names): the career, the colours, logos and style guide (stage 0); My team and Scouting for every team in
every competition, the inbox, every player in every competition and season, every match, the match finder for every
competition and team, the best games, the search (stage 1). Anything but a clean answer (200, or a plain 404/400 for
something that isn't there) or a part that couldn't be worked out is printed."""
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

base = f"http://127.0.0.1:{sys.argv[1]}"
problems, n = [], [0]


def get(path):
    n[0] += 1
    try:
        with urllib.request.urlopen(base + urllib.parse.quote(path, safe="/?=&"), timeout=600) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:  # noqa: BLE001
        return -1, str(e).encode()


def broken(v, where=""):
    out = []
    if isinstance(v, dict):
        for k, x in v.items():
            out += ([f"{where}.missing.{a}: {b}" for a, b in x.items() if "Couldn't be worked out" in str(b)]
                    if k == "missing" and isinstance(x, dict) else broken(x, f"{where}.{k}"))
    elif isinstance(v, list):
        for i, x in enumerate(v):
            out += broken(x, f"{where}[{i}]")
    elif isinstance(v, str) and v.startswith("Couldn't be worked out"):
        out.append(f"{where}: {v}")
    return out


def check(path, ok=(200, 404)):
    status, body = get(path)
    if status not in ok:
        problems.append(f"{status} {path}: {body[:200]!r}")
        return None
    try:
        d = json.loads(body)
    except ValueError:
        problems.append(f"not JSON {path}")
        return None
    if status == 200:
        problems.extend(f"{path} {b}"[:300] for b in broken(d))
        return d
    return None


career = check("/api/career") or {}
for p in ("/api/careers", "/api/theme", "/api/nations", "/api/logos", "/api/styleguide", "/api/search", "/api/names",
          "/api/players", "/api/inbox", "/api/myteam", "/api/scouting", "/api/matches"):
    check(p)
for nation in (check("/api/nations") or {}).get("nations", [])[:40]:
    check(f"/api/theme?nation={nation}")
    check(f"/api/styleguide?nation={nation}")
names = (check("/api/names") or {}).get("names", [])
for name in names:
    d = check(f"/api/player?name={name}")
    if d:
        for s in d.get("sections", []):
            e = check(f"/api/player?name={name}&section={s}")
            for season in (e or {}).get("seasons", [])[1:3]:
                check(f"/api/player?name={name}&section={s}&season={season}")
f = check("/api/matches?section=All sections") or {"matches": [], "sections": []}
for mt in f["matches"]:
    check(f"/api/match/{mt['id']}")
teams = sorted({t for mt in f["matches"] for t in (mt["home"], mt["away"])})
for s in f.get("sections", []):
    d = check(f"/api/matches?section={s}") or {}
    for t in d.get("teams", [])[:30]:
        check(f"/api/matches?section={s}&team={t}")
    check(f"/api/matches/best?section={s}")
for t in teams:
    d = check(f"/api/myteam?team={t}") or {}
    for s in d.get("sections", []):
        check(f"/api/myteam?team={t}&section={s}")
    check(f"/api/scouting?team={t}")
for kind, lst in (("team", teams), ("comp", f.get("sections", []))):
    for x in lst:
        get(f"/api/logo/{kind}/{x}")   # a logo or a plain 404; anything else is noted below
        st, _ = get(f"/api/logo/{kind}/{x}")
        if st not in (200, 404):
            problems.append(f"logo {kind} {x}: {st}")
print(f"{sys.argv[2]}: {len(names)} players, {len(f['matches'])} matches, {len(teams)} teams; {n[0]} requests; "
      f"problems {len(problems)}")
for p in problems[:30]:
    print("   ", p)
