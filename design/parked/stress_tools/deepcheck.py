"""python3 deepcheck.py <home>: every feature recomputed another way on a real career, and compared."""
import sys, random
from pathlib import Path
sys.path.insert(0, "/home/user/crciekt20206")
import numpy as np
import pandas as pd
from ccstats.local import CareerStore
from ccstats import marks as MK, scouting as SC, attributes as AT, depth as DP
from ccstats.records import by_played
from ccstats.stats import KIND

st = CareerStore(Path(sys.argv[1])); c = st.load(st.names()[0])[0]; print(len(c.matches), "matches")
_mine = list(st.load_settings(st.names()[0])[1].my_teams or [])
_present = set(c.matches.home) | set(c.matches.away)
_busiest = list(pd.concat([c.matches.home, c.matches.away]).value_counts().index)
TEAMS = [t for t in dict.fromkeys(_mine + ["India", "Mumbai Indians", "Australia", "England", "Mumbai", "Karnataka", "Sussex"]
                                  + _busiest[:6]) if t in _present]
SECTIONS = [s_ for s_ in c.matches.section.value_counts().index if c.matches.section.value_counts()[s_] >= 3]
bad = []
def check(ok, what):
    if not ok:
        bad.append(what)

# 1 match values by hand: batting share for 40 random batting rows
v = MK.match_values(c).set_index(["match_id", "team", "player"])
inn = c.innings
rng = random.Random(1)
rows = c.batting[c.batting.did_bat & (c.batting.runs > 0)]
for _, r in rows.sample(40, random_state=1).iterrows():
    m = c.matches.set_index("match_id").loc[r.match_id]
    if m.result_type == "no result":
        continue
    tot = inn[inn.match_id == r.match_id]
    own = tot[tot.team == r.team].runs.sum(); avg = tot.runs.sum() / 2
    # by team too: two players can share a name in one match (M Rizwan of Pakistan and of Bangladesh)
    runs = c.batting[(c.batting.match_id == r.match_id) & (c.batting.player == r.player) & (c.batting.team == r.team)
                     & c.batting.did_bat]
    R, B = runs.runs.sum(), runs.balls.sum()
    white = KIND.get(m.format) != "multi"
    rpb = tot.runs.sum() / tot.balls.sum() if tot.balls.sum() else 0
    speed = 0.5 * (R - B * rpb) if white else 0
    div = 0.5 * (1 / max(max(own, 0.5 * avg), 1) + 1 / max(avg, 1))
    weight = 1.0
    if m.rain and white:
        from ccstats.stats import BALL_QUOTA
        q = BALL_QUOTA.get(m.format)
        if q:
            weight = min(1.0, tot.balls.sum() / (2 * q))
    want = (R + speed) * div * weight
    got = v.loc[(r.match_id, r.team, r.player)].bat
    check(abs(want - got) < 1e-6, f"bat value {r.player} {r.match_id}: {got} v {want}")
print("1 match values: checked 40 innings")

# 2 inbox results v the matches (series and tournaments), and each one's scorecard link
import re
pos = {mid: i for i, mid in enumerate(by_played(c, c.matches).match_id)}
for team in TEAMS:
    msgs = [x for x in DP.inbox(c, team) if x["kind"] == "result"]
    rep = {r["label"]: r for r in MK.team_report(c, team)}
    mm = c.matches.assign(series=MK.series_key(c.matches))
    for x in msgs:
        s_ = rep[x["series"]]
        g = mm[mm.series == s_["series"]]
        g = g[(g.home == team) | (g.away == team)]
        w, l = int((g.winner == team).sum()), int((g.loser == team).sum())
        nums = re.search(r"(\d+)–(\d+) v |: (\d+) won, (\d+) lost", x["title"])
        got = (int(nums.group(1)), int(nums.group(2))) if nums.group(1) else (int(nums.group(3)), int(nums.group(4)))
        check(got == (w, l), f"inbox {team} '{x['title']}' but {w}-{l}")
        check(x["match"] in set(g.match_id), f"inbox link {team} {x['title']} not the team's game")
        check(x["match"] == max(g.match_id, key=pos.get), f"inbox link {team} {x['title']} not the last game")
print("2 inbox results checked")

# 3 struggling, worked out again
def again(team, section):
    s = MK.series_marks(c)
    m = c.matches[c.matches.section == section]
    s = s[(s.team == team) & s.series.isin(set(MK.series_key(m)))]
    if s.empty:
        return set()
    last = m.assign(series=MK.series_key(m)).merge(pd.DataFrame({"series": list(set(s.series))}))
    pos = {mid: i for i, mid in enumerate(by_played(c, c.matches).match_id)}
    last["at"] = last.match_id.map(pos)
    order = list(last.groupby("series").at.max().sort_values(ascending=False).index)
    now = order[0]
    own = SC.own_numbers(c, team, section)
    out = set()
    for p in s[s.series == now].player:
        role = own.role.get(p) if p in own.index else None
        if not isinstance(role, str) or role not in SC.FITS:
            continue
        mine = s[s.player == p].set_index("series").mark
        marks = [int(mine[x]) for x in order if x in mine.index][:3]
        if (len(marks) == 3 and np.mean(marks) <= 4 and max(marks) <= 5) or (len(marks) >= 2 and max(marks[:2]) <= 4):
            out.add(p)
    return out
n = 0
for team in TEAMS:
    secs = list(dict.fromkeys(c.matches[(c.matches.home == team) | (c.matches.away == team)].section))
    for sec in secs:
        got = {x["player"] for x in SC.struggling(c, team, sec)}
        check(got == again(team, sec), f"struggling {team} {sec}: {sorted(got)} v {sorted(again(team, sec))}")
        n += 1
        # 4 every pick: eligible, right role, enough cricket, not in the side, gain worked out again
        latest, side = SC._latest_side(c, team, sec)
        own = SC.own_numbers(c, team, sec)
        conv = SC.converted(c, team, sec)
        kind = SC.sections(c).kind[sec]
        reps = SC.replacements(c, team, sec)
        brought = [r["picks"][0]["player"] for r in reps if r["verdict"].startswith("Replace")]
        check(len(brought) == len(set(brought)), f"one man brought in twice {team} {sec}: {brought}")
        owner = {r["picks"][0]["player"]: r["player"] for r in reps if r["verdict"].startswith("Replace")}
        for r in reps:
            check(len(r["picks"]) <= 3 and all(owner.get(p["player"], r["player"]) == r["player"] for p in r["picks"]),
                  f"a pick shown who goes in for someone else {team} {sec} {r['player']}")
            for x in r["lost"]:
                check(x["player"] in brought and x["goes_to"] != r["player"], f"lost {team} {sec} {x}")
        for r in reps:
            me = own.loc[r["player"]]
            for p in r["picks"]:
                cand = conv.loc[p["player"]]
                check(p["player"] not in side, f"pick in the side {team} {sec} {p['player']}")
                check(cand.role in SC.FITS[r["role"]], f"pick role {team} {sec} {p['player']} {cand.role} for {r['role']}")
                if SC.sections(c).level[sec] == "International":
                    check(cand.country == team or cand.also == team, f"pick country {team} {p['player']} {cand.country}")
                if SC.sections(c).level[sec] == "Franchise":
                    check(p["player"] not in SC.taken(c, team, sec), f"pick under contract {team} {p['player']}")
                job = SC._job(r["role"])
                e = SC.ENOUGH[kind]
                if job in ("bat", "both"):
                    check(cand.bat_inns >= e["inns"], f"pick too few innings {p['player']}")
                if job in ("bowl", "both"):
                    check(cand.bowl_balls >= e["balls"], f"pick too few balls {p['player']}")
                if job == "bat":
                    g = cand.avg / me.avg
                    g = np.sqrt(g * cand.sr / me.sr) if kind != "multi" else g
                elif job == "bowl":
                    g = me.bowl_avg / cand.bowl_avg
                    g = np.sqrt(g * me.econ / cand.econ) if kind != "multi" else g
                else:
                    g = None
                if g is not None:
                    check(abs((g - 1) - p["gain"]) < 1e-9, f"gain {team} {p['player']}: {p['gain']} v {g - 1}")
            check(r["verdict"].startswith("Replace") == bool(r["picks"] and r["picks"][0]["gain"] >= SC.BAR),
                  f"verdict {team} {sec} {r['verdict']}")
print(f"3-4 struggling and picks: {n} team-competitions")

# 5 squad depth: everyone in the latest side appears once
for team in TEAMS:
    secs = list(dict.fromkeys(c.matches[(c.matches.home == team) | (c.matches.away == team)].section))
    for sec in secs:
        d = DP.squad_depth(c, team, sec)
        latest, side = SC._latest_side(c, team, sec)
        starters = [p["player"] for r in d["roles"] for p in r["starters"]]
        missing = side - set(starters)
        check(not missing, f"depth {team} {sec}: not shown {sorted(missing)}")
        check(len(starters) == len(set(starters)), f"depth twice {team} {sec}")
print("5 squad depth checked")

# 6 attributes: Run-scoring ranks again
for sec in SECTIONS:
    t = AT.table(c, sec)["bat"]
    if t.empty or "average" not in t.columns:   # too few players here for attributes: nothing to check
        continue
    r = t.average.rank(pct=True, method="average")
    check((np.clip(np.ceil(r * 20), 1, 20).astype(int) == t["Run-scoring"].astype(int)).all(), f"run-scoring {sec}")
    w = AT.table(c, sec)["bowl"]
    if w.empty or "economy" not in w.columns:
        continue
    r = w.economy.rank(pct=True, method="average", ascending=False)
    check((np.clip(np.ceil(r * 20), 1, 20).astype(int) == w["Control"].astype(int)).all(), f"control {sec}")
print(f"6 attributes checked in {len(SECTIONS)} competitions; teams checked: {TEAMS}")
print("PROBLEMS:", len(bad)); [print("  ", b) for b in bad[:40]]
