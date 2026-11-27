"""Deep test step 3: every match of the save counted again by the second reader; every difference listed."""
import sys, pickle
from collections import defaultdict
from pathlib import Path
sys.path[:0] = ["/home/user/crciekt20206", "/home/user/crciekt20206/tests"]
import test_second_counter as SC
root = Path(sys.argv[1])
c = pickle.load(open(root / "career.pickle", "rb"))
guessed = set(c.guesses.match_id)
B, W, I = c.batting, c.bowling, c.innings
bi = {k: g for k, g in B[B.did_bat].groupby(["match_id", "innings_no"])}
wi = {k: g for k, g in W.groupby(["match_id", "innings_no"])}
src = c.matches.set_index("source").match_id
diffs, checked, inn_checked = [], 0, 0
for f in sorted((root / "Scorecards").glob("*.txt")):
    if f.name not in src.index:
        continue
    mid = src[f.name]
    mine = SC.count(f.read_text(errors="replace"))
    inns = I[I.match_id == mid]
    turn = defaultdict(int)
    if len(mine["innings"]) != len(inns):
        diffs.append((f.name, f"{len(mine['innings'])} innings counted, site has {len(inns)}")); continue
    for x in mine["innings"]:
        turn[x["team"]] += 1
        row = inns[(inns.team == x["team"]) & (inns.team_innings == turn[x["team"]])]
        if len(row) != 1:
            diffs.append((f.name, f"{x['team']} innings {turn[x['team']]} not found on the site")); continue
        no = int(row.innings_no.iloc[0])
        bat = bi.get((mid, no))
        rows = list(bat.sort_values("position").itertuples()) if bat is not None else []
        site_bat = [(int(r.runs), int(r.balls), int(r.fours), int(r.sixes), bool(r.out)) for r in rows]
        mine_bat = [(a, b_, c4, c6, (r.out if SC.corrected(c, mid, r.player) else out)) for (a, b_, c4, c6, out), r in zip(x["bat"], rows)]
        if len(rows) != len(x["bat"]) or site_bat != mine_bat:
            diffs.append((f.name, f"{x['team']} batting differs: site {site_bat[:3]}... counted {x['bat'][:3]}..."))
        bowl = wi.get((mid, no))
        site_bowl = sorted((int(r.balls), int(r.runs), int(r.wickets)) for r in bowl.itertuples()) if bowl is not None else []
        if site_bowl != sorted(x["bowl"]):
            tag = "GUESSED" if mid in guessed else "DIFF"
            diffs.append((f.name, f"{tag} {x['team']} bowling: site {site_bowl} counted {sorted(x['bowl'])}"))
        inn_checked += 1
    checked += 1
print(f"matches recounted: {checked}, innings: {inn_checked}, differences: {len(diffs)}")
for d in diffs[:40]:
    print("  ", d[0], "|", d[1][:300])
