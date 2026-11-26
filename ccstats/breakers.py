"""Partnership breakers (stage 5, your pick of 26 November): which bowlers end big stands, from the fall of wickets.

A stand of `MIN_STAND` runs or more is "broken" by the bowler credited with the wicket that ended it: the batter out is
the one of the pair who isn't in the next stand (or, for the last wicket, the one out), and his dismissal's bowler took
it. A run out ends a stand with no bowler, so it's counted for no one. Innings the scorecard leaves unclear (who batted
with whom unknown, or a batter retired) are left out rather than guessed."""

from __future__ import annotations

import pandas as pd

from . import partnerships as P

MIN_STAND = 50
COLUMNS = ["match_id", "innings_no", "team", "bowler", "batter", "wicket", "runs"]


def broken(career, ids, min_stand: int = MIN_STAND) -> pd.DataFrame:
    """One row per stand of `min_stand`+ ended by a bowler: the bowling side (`team`), the bowler, the batter he got
    out, the wicket and the stand's runs."""
    s = P.stands(career, ids)
    if s.empty:
        return pd.DataFrame(columns=COLUMNS)
    bat = career.batting
    out = bat[bat.out.astype(bool)].set_index(["match_id", "innings_no", "player"])
    rows = []
    for (mid, no), g in s.groupby(["match_id", "innings_no"], sort=False):
        g = g.sort_values("wicket")
        pairs = list(zip(g.wicket, g.runs, g.unbroken, g.batter1, g.batter2, g.known, g.opposition))
        for i, (w, runs, unbroken, b1, b2, known, opp) in enumerate(pairs):
            if unbroken or runs < min_stand or not known:
                continue
            nxt = pairs[i + 1] if i + 1 < len(pairs) else None
            if nxt is not None and nxt[5]:
                gone = [b for b in (b1, b2) if b not in (nxt[3], nxt[4])]
            else:
                gone = [b for b in (b1, b2) if (mid, no, b) in out.index]
            if len(gone) != 1 or (mid, no, gone[0]) not in out.index:
                continue
            r = out.loc[(mid, no, gone[0])]
            r = r.iloc[0] if isinstance(r, pd.DataFrame) else r
            bowler = str(r.get("bowler", "") or "")
            if not bowler or "run out" in str(r.get("how_out", "")).lower() or " or " in bowler:
                continue
            rows.append((mid, no, opp, bowler, gone[0], int(w), int(runs)))
    return pd.DataFrame(rows, columns=COLUMNS)


def table(career, ids, team: str = "", min_stand: int = MIN_STAND) -> pd.DataFrame:
    """Bowlers ranked by the big stands they broke: how many, the biggest, the average size, and the batters they got."""
    b = broken(career, ids, min_stand)
    if team:
        b = b[b.team == team]
    cols = ["bowler", "team", "broken", "biggest", "average", "matches"]
    if b.empty:
        return pd.DataFrame(columns=cols)
    g = b.groupby(["bowler", "team"])
    t = pd.DataFrame({"broken": g.size(), "biggest": g.runs.max(), "average": g.runs.mean(),
                      "matches": g.match_id.nunique()}).reset_index()
    return t.sort_values(["broken", "biggest", "bowler"], ascending=[False, False, True]).reset_index(drop=True)[cols]


def of_player(career, ids, player: str, min_stand: int = MIN_STAND) -> dict:
    """One bowler's line for the Player page: big stands broken, the biggest, and the most often broken partner."""
    b = broken(career, ids, min_stand)
    b = b[b.bowler == player]
    if b.empty:
        return {"broken": 0}
    top = b.sort_values("runs", ascending=False).iloc[0]
    return {"broken": int(len(b)), "biggest": int(top.runs), "biggest_batter": str(top.batter),
            "average": round(float(b.runs.mean()), 1)}
