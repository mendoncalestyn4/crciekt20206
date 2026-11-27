import sys, pickle, math
from collections import defaultdict
from pathlib import Path
sys.path[:0] = ["/home/user/crciekt20206", "/home/user/crciekt20206/tests"]
import test_second_counter as SC
from ccstats.stats import Scope
from ccstats.stats import player_tables
root = Path(sys.argv[1])
c = pickle.load(open(root / "career.pickle", "rb")); c.count_fielding = False
guessed = set(c.guesses.match_id)
B, W, I = c.batting, c.bowling, c.innings
sec = c.matches.set_index("source").section
mids = c.matches.set_index("source").match_id
bat_tot = defaultdict(lambda: [0, 0, 0]); bowl_tot = defaultdict(lambda: [0, 0, 0])
bi = {k: g for k, g in B[B.did_bat].groupby(["match_id", "innings_no"])}
for f in sorted((root / "Scorecards").glob("*.txt")):
    if f.name not in sec.index: continue
    mid = mids[f.name]; s = sec[f.name]
    mine = SC.count(f.read_text(errors="replace"))
    inns = I[I.match_id == mid]; turn = defaultdict(int)
    for x in mine["innings"]:
        turn[x["team"]] += 1
        no = int(inns[(inns.team == x["team"]) & (inns.team_innings == turn[x["team"]])].innings_no.iloc[0])
        b = bi.get((mid, no))
        if b is None:
            assert not x["bat"], (f.name, x["team"]); continue
        b = b.sort_values("position")
        for (r, bl, _, _, out), p, so in zip(x["bat"], b.player, b.out):
            t = bat_tot[(s, p)]; t[0] += r; t[1] += bl; t[2] += bool(so) if SC.corrected(c, mid, p) else out
    w = W[W.match_id == mid]       # (names from the site; the guessed cards' figures as the site put them right)
    for p, balls, runs, wk in zip(w.player, w.balls, w.runs, w.wickets):
        t = bowl_tot[(s, p)]; t[0] += int(balls); t[1] += int(runs); t[2] += int(wk)
bad, n = [], 0
for s in c.matches.section.unique():
    bt, wt, _, _ = player_tables(c, Scope(sections=[s]))
    for r in bt.itertuples():
        runs, balls, outs = bat_tot[(s, r.player)]
        ok = (int(r.runs), int(r.balls), int(r.outs)) == (runs, balls, outs)
        ok &= (not outs) or math.isclose(r.average, runs / outs, rel_tol=1e-9)
        ok &= (not balls) or math.isclose(r.strike_rate, runs / balls * 100, rel_tol=1e-9)
        if not ok: bad.append((s, r.player, "bat", (r.runs, r.balls, r.outs), (runs, balls, outs)))
        n += 1
    for r in wt.itertuples():
        balls, runs, wk = bowl_tot[(s, r.player)]
        ok = (int(r.balls), int(r.runs), int(r.wickets)) == (balls, runs, wk) and math.isclose(r.economy, runs / balls * 6, rel_tol=1e-9)
        ok &= (not wk) or (math.isclose(r.average, runs / wk, rel_tol=1e-9) and math.isclose(r.strike_rate, balls / wk, rel_tol=1e-9))
        if not ok: bad.append((s, r.player, "bowl", (r.balls, r.runs, r.wickets), (balls, runs, wk)))
        n += 1
print(f"player rows checked: {n}, sections: {c.matches.section.nunique()}, differences: {len(bad)}")
for x in bad[:30]: print("  ", x)
