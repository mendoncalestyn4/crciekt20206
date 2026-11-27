"""Deep test step 4: the real site on the owner's save, every page asked with every choice it offers (two levels deep),
every team, every competition and season, every match and every player; each answer checked."""
import sys, os, json, time, math, re, urllib.request, urllib.parse as U, threading, collections, pickle
from pathlib import Path
sys.path[:0] = ["/home/user/crciekt20206", "/home/user/crciekt20206/tests"]
os.environ.setdefault("STATS_PACK_HELPERS", "0")
root = Path(sys.argv[1]); out = Path(sys.argv[2]); limit_players = int(sys.argv[3]) if len(sys.argv) > 3 else 10**9
from ccstats.local import CareerStore
from server.app import create_app
from serverkit import Live
store = CareerStore(root / "home")
store.save_preference("tour_done", True)
live = Live(create_app(store, web=Path("/home/user/crciekt20206/web/dist"), watch_every=0))
log = open(out, "w", buffering=1)
seen, bad, timing = set(), [], []
COUNT_KEYS = {"played", "won", "lost", "drawn", "tied", "runs", "wickets", "balls", "matches", "innings", "games",
              "fours", "sixes", "hundreds", "fifties", "maidens", "points_count", "count", "not_outs", "outs"}
BAD_STR = {"nan", "NaN", "None", "undefined", "inf", "-inf", "Infinity", "null"}

def scan(x, path, url, found):
    if isinstance(x, dict):
        for k, v in x.items():
            if k in ("missing",) and v:
                found.append(f"{path}.{k}: a piece failed: {str(v)[:200]}")
            if k == "error" and v:
                found.append(f"{path}.error: {str(v)[:200]}")
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                    found.append(f"{path}.{k} = {v}")
                elif k in COUNT_KEYS and v < 0:
                    found.append(f"{path}.{k} = {v} (a count below 0)")
                elif (k.endswith("pct") or k.endswith("_percent") or k in ("pct", "win_pct", "percent")) and v > 100.0001:
                    found.append(f"{path}.{k} = {v} (over 100%)")
            scan(v, f"{path}.{k}", url, found)
    elif isinstance(x, list):
        for i, v in enumerate(x[:4000]):
            scan(v, f"{path}[{i}]", url, found)
    elif isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
        found.append(f"{path} = {x}")
    elif isinstance(x, str):
        s = x.strip()
        if s in BAD_STR or re.search(r"\bnan\b|\bNaN\b|\bNone\b|undefined|\binf\b|Traceback", s):
            found.append(f"{path}: \"{s[:120]}\"")

def ask(url):
    if url in seen:
        return None
    seen.add(url)
    t = time.time()
    for _ in range(600):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{live.port}{url}", timeout=900) as r:
                body = r.read(); status = r.status; break
        except urllib.error.HTTPError as e:
            body = e.read(); status = e.code
            if status == 503: time.sleep(0.5); continue
            break
        except Exception as e:
            body = str(e).encode(); status = -1; break
    dt = time.time() - t
    timing.append((dt, url))
    found = []
    data = None
    if status != 200:
        found.append(f"status {status}: {body[:200]!r}")
    else:
        try:
            data = json.loads(body)
        except Exception as e:
            found.append(f"not JSON: {e}")
    if data is not None:
        scan(data, "", url, found)
    for f in found:
        bad.append((url, f)); log.write(f"BAD {url} | {f}\n")
    if len(seen) % 200 == 0:
        log.write(f"... {len(seen)} asked, {len(bad)} findings, slowest {max(timing)[0]:.1f}s\n")
    return data

PLURAL = {"tabs": "tab", "choices": "section", "sections": "section", "seasons": "season", "teams": "team", "events": "event",
          "formats": "format", "views": "view", "measures": "measure", "stats": "stat", "discs": "disc", "picks": "pick",
          "months": "month", "opps": "opp", "opp_opts": "opp", "mine_opts": "mine", "results": "result", "positions": "pos",
          "whats": "what", "grounds": "ground", "venues": "venue", "races": "race", "options": None}

def options(data, params):
    """{param: [values]} from the option lists an answer offers."""
    got = collections.defaultdict(list)
    def walk(x, depth=0):
        if depth > 3: return
        if isinstance(x, dict):
            for k, v in x.items():
                p = PLURAL.get(k, k[:-1] if k.endswith("s") else k)
                if p in params and isinstance(v, list) and v:
                    for e in v[:80]:
                        if isinstance(e, str): got[p].append(e)
                        elif isinstance(e, dict):
                            val = next((e[q] for q in ("key", "value", p, "section", "name", "label") if q in e and isinstance(e[q], (str, int))), None)
                            if val is not None: got[p].append(str(val))
                walk(v, depth + 1)
    walk(data)
    return {p: list(dict.fromkeys(v)) for p, v in got.items()}

PARAMS = {"/api/analytics": ["section", "tab"], "/api/compare": ["disc", "section"], "/api/competition": ["event", "season", "pick", "series"],
          "/api/datacheck": ["tab"], "/api/fixtures": ["season", "tab", "team"], "/api/hall": ["section", "tab", "team"], "/api/honours": ["tab"],
          "/api/insights": ["section", "tab"], "/api/matches": ["section", "team"], "/api/matches/best": ["section", "team"],
          "/api/myteam": ["section", "team"], "/api/planner": ["event", "season", "section", "tab", "team"],
          "/api/preview": ["format", "mine", "opp", "section", "tab"], "/api/rankings": ["section", "tab", "what"],
          "/api/records": ["season", "section"], "/api/review": ["pick"], "/api/rivalries": ["pick", "section"],
          "/api/season": ["month", "season", "tab", "team", "view"], "/api/selection": ["team"],
          "/api/statbystat": ["disc", "measure", "pos", "result", "section", "stat", "view"], "/api/stories": ["section", "tab"],
          "/api/team": ["season", "section", "tab", "team", "venue"], "/api/teamleaders": ["season", "section"],
          "/api/teamvteam": ["a", "b", "ground", "season", "section", "which"], "/api/inbox": [], "/api/players": [],
          "/api/names": [], "/api/nations": [], "/api/styleguide": [], "/api/daily": [], "/api/career": [], "/api/settings": [],
          "/api/scouting": ["team"]}

def url_of(ep, q):
    return ep + ("?" + U.urlencode(q) if q else "")

# warm: wait for the career to be read
ask("/api/career")
c = pickle.load(open(root / "career.pickle", "rb"))
m = c.matches
TEAMS = sorted(set(m.home) | set(m.away)); SECTIONS = sorted(set(m.section))
log.write(f"teams {len(TEAMS)}, sections {len(SECTIONS)}, matches {len(m)}\n")
# 1. every page, every choice it offers, two levels deep (one choice changed at a time from each answer)
for ep, ps in PARAMS.items():
    first = ask(url_of(ep, {}))
    if not ps or first is None: continue
    level1 = []
    for p, vals in options(first, ps).items():
        for v in vals:
            q = {p: v}; d = ask(url_of(ep, q)); level1.append((q, d))
    for q, d in level1:
        if d is None: continue
        for p, vals in options(d, ps).items():
            if p in q: continue
            for v in vals[:40]:
                ask(url_of(ep, {**q, p: v}))
log.write(f"== level two done: {len(seen)} asked\n")
# 2. every team on its team pages (every tab), My team, fixtures and selection
for t in TEAMS:
    d = ask(url_of("/api/team", {"team": t}))
    for tab in (d or {}).get("tabs", []) if isinstance(d, dict) else []:
        tv = tab if isinstance(tab, str) else tab.get("key") or tab.get("label")
        ask(url_of("/api/team", {"team": t, "tab": tv}))
    for ep in ("/api/myteam", "/api/fixtures", "/api/selection", "/api/hall", "/api/matches", "/api/scouting"):
        ask(url_of(ep, {"team": t}))
log.write(f"== every team done: {len(seen)} asked\n")
# 3. every competition in every season
for (ev, season), _ in m.groupby(["event", "season"]):
    ask(url_of("/api/competition", {"event": ev, "season": season}))
for sec in SECTIONS:
    for season in sorted(set(m[m.section == sec].season)):
        ask(url_of("/api/records", {"section": sec, "season": season}))
        ask(url_of("/api/teamleaders", {"section": sec, "season": season}))
log.write(f"== every competition and season done: {len(seen)} asked\n")
# 4. every match page
for mid in m.match_id:
    ask(f"/api/match/{mid}")
log.write(f"== every match done: {len(seen)} asked\n")
# 5. every player page
players = sorted(set(c.batting.player) | set(c.bowling.player))
for p in players[:limit_players]:
    ask(url_of("/api/player", {"name": p}))
log.write(f"== every player done ({min(len(players), limit_players)} of {len(players)}): {len(seen)} asked\n")
# the server's own error log
pr = ask("/api/problems")
log.write(f"server problems: {json.dumps(pr)[:3000]}\n")
timing.sort(reverse=True)
log.write("slowest:\n" + "\n".join(f"  {s:6.1f}s {u}" for s, u in timing[:25]) + "\n")
log.write(f"DONE: {len(seen)} asked, {len(bad)} findings\n")
live.stop()
