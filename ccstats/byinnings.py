"""A player's figures innings by innings (asked for 31 October). In Tests and first-class cricket the match's 1st, 2nd,
3rd and 4th innings apart, the 4th split into chasing to win and batting to save the match; in one-day and T20 cricket
batting (or bowling) first against second. Each slot is set against the player's own other innings and against the
usual there, and settled before a best or weakest slot is named, so a handful of innings can't decide it.

The scorecards don't say how much time was left when the 4th innings began, so it's worked out from the overs: the
target against the overs left in a match of the competition's usual length (the length of its longest games). Needing
3 an over or more counts as batting to save; in the owner's saves sides chasing at that rate won about 1 in 9, and under
2 an over about 3 in 4. A side that got there was chasing, whatever the rate.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .parser import balls_to_overs
from .players import SHRINK

SAVE_RATE = 3.0          # runs an over needed in the time left from which the 4th innings is batting to save
TEST_OVERS = 450         # five days of 90 overs
DAYS = (288, 384, 450)   # three, four and five days: the lengths a first-class match can have
LENGTH_FROM = 20         # four-innings games a competition needs before its own length is used
SMALL = 5                # fewer innings than this in a slot: "only a few", and never named the best or weakest
SAME = 10                # best and weakest within this many % of each other: about the same in every innings
ECON_SETTLE_BALLS = 60   # T20 economy: 10 overs at the usual rate added before comparing

MULTI = ["1", "2", "3", "4c", "4s"]
LIMITED = ["1", "2"]
BAT_LABEL = {"1": "1st innings", "2": "2nd innings", "3": "3rd innings", "4c": "4th innings, chasing",
             "4s": "4th innings, batting to save"}
BOWL_LABEL = {**BAT_LABEL, "4c": "4th innings, defending a total", "4s": "4th innings, bowling to win"}
BAT_LABEL_LIMITED = {"1": "Batting first", "2": "Chasing"}
BOWL_LABEL_LIMITED = {"1": "Bowling first", "2": "Bowling second"}


def order(kind: str) -> list[str]:
    return MULTI if kind == "multi" else LIMITED


def label(kind: str, slot: str, bowling: bool) -> str:
    if kind == "multi":
        return (BOWL_LABEL if bowling else BAT_LABEL)[slot]
    return (BOWL_LABEL_LIMITED if bowling else BAT_LABEL_LIMITED)[slot]


def others(kind: str, slot: str) -> list[str]:
    """The player's other innings for a slot: in a Test the other three innings of the match (both kinds of 4th innings
    count as the 4th), in one-day cricket the other side."""
    if kind != "multi":
        return [s for s in LIMITED if s != slot]
    if slot in ("4c", "4s"):
        return ["1", "2", "3"]
    return [s for s in MULTI if s != slot]


def match_length(career, section: str) -> float:
    """The overs in a full match of this competition: its longest games (99th percentile) once it has 20 four-innings
    games. Before that, five days for a Test, and otherwise the shortest of three, four or five days that its longest
    game fits in (tour matches are often three-day games, the county and Ranji games four)."""
    m = career.matches[career.matches.section == section]
    inn = career.innings[career.innings.match_id.isin(m.match_id)]
    if inn.empty:
        return float(DAYS[1])
    by = inn.groupby("match_id")
    overs = by.balls.sum() / 6
    if int((by.innings_no.max() == 4).sum()) >= LENGTH_FROM:
        return float(overs.quantile(0.99))
    if m.format.mode().iloc[0] == "Test":
        return float(TEST_OVERS)
    return float(next((d for d in DAYS if overs.max() <= d), DAYS[-1]))


def slots(career, ids, kind: str) -> pd.DataFrame:
    """Every innings in these matches with its slot: match_id, innings_no, slot, and for a 4th innings the target, the
    overs left and the rate needed."""
    inn = career.innings[career.innings.match_id.isin(set(ids))]
    cols = ["match_id", "innings_no", "slot", "target", "left", "rate"]
    if kind != "multi":
        inn = inn[inn.innings_no.isin([1, 2])]
        return inn.assign(slot=inn.innings_no.astype(str), target=np.nan, left=np.nan, rate=np.nan)[cols]
    inn = inn[inn.innings_no.between(1, 4)]
    out = inn.assign(slot=inn.innings_no.astype(str), target=np.nan, left=np.nan, rate=np.nan)
    fourth = inn[inn.innings_no == 4].set_index("match_id")
    if fourth.empty:
        return out[cols]
    before = inn[(inn.innings_no < 4) & inn.match_id.isin(fourth.index)]
    own = before.team.values == fourth.team.reindex(before.match_id).values
    target = (before.runs.where(~own, 0).groupby(before.match_id).sum()
              - before.runs.where(own, 0).groupby(before.match_id).sum() + 1).reindex(fourth.index)
    used = (before.balls.groupby(before.match_id).sum() / 6).reindex(fourth.index)
    m = career.matches.set_index("match_id").reindex(fourth.index)
    length = m.section.map({s: match_length(career, s) for s in m.section.unique()})
    # never shorter than this match itself went (a longer knockout, say)
    length = np.maximum(length, (inn[inn.match_id.isin(fourth.index)].groupby("match_id").balls.sum() / 6).reindex(fourth.index))
    left = length - used
    rate = (target / left.where(left > 0)).fillna(np.inf)
    chase = (m.winner == fourth.team) | (rate < SAVE_RATE)
    is4 = out.innings_no == 4
    mids = out.loc[is4, "match_id"]
    out.loc[is4, "slot"] = np.where(chase.reindex(mids).values, "4c", "4s")
    out.loc[is4, "target"] = target.reindex(mids).values
    out.loc[is4, "left"] = left.reindex(mids).values
    out.loc[is4, "rate"] = rate.reindex(mids).values
    return out[cols]


def _avg(runs, outs):
    return runs / outs if outs else np.nan


def batting(career, ids, name: str, kind: str, sl: pd.DataFrame | None = None) -> pd.DataFrame:
    """One row a slot the player batted in (in order): innings, not outs, runs, balls, high (text), average, strike
    rate, fifties, hundreds; their average and strike rate in their other innings; the usual average and strike rate
    for a batter at the positions they batted at in that slot; settled edge on the usual (for naming the best)."""
    sl = slots(career, ids, kind) if sl is None else sl
    b = career.batting[career.batting.match_id.isin(set(ids)) & career.batting.did_bat]
    b = b.merge(sl[["match_id", "innings_no", "slot"]], on=["match_id", "innings_no"])
    me = b[b.player == name]
    pool = b.groupby(["slot", "position"]).agg(runs=("runs", "sum"), outs=("out", "sum"), balls=("balls", "sum"))
    pool_avg = pool.runs / pool.outs.replace(0, np.nan)
    pool_sr = pool.runs / pool.balls.replace(0, np.nan) * 100
    k = SHRINK[kind]
    rows = []
    for slot in order(kind):
        g = me[me.slot == slot]
        if g.empty:
            continue
        o = me[me.slot.isin(others(kind, slot))]
        n = g.position.value_counts()
        ua = pool_avg.reindex(pd.MultiIndex.from_product([[slot], n.index])).values
        us = pool_sr.reindex(pd.MultiIndex.from_product([[slot], n.index])).values
        w = n.values.astype(float)
        usual = np.nansum(ua * w) / w[~np.isnan(ua)].sum() if (~np.isnan(ua)).any() else np.nan
        usual_sr = np.nansum(us * w) / w[~np.isnan(us)].sum() if (~np.isnan(us)).any() else np.nan
        runs, outs, balls = int(g.runs.sum()), int(g.out.sum()), int(g.balls.sum())
        top = g.loc[g.assign(_k=g.runs * 2 + ~g.out.astype(bool))._k.idxmax()]
        settled = (runs + k * usual) / (outs + k) if np.isfinite(usual) else np.nan
        rows.append(dict(slot=slot, label=label(kind, slot, False), innings=len(g), not_outs=len(g) - outs, runs=runs,
                         balls=balls, high=f"{int(top.runs)}{'' if top.out else '*'}", average=_avg(runs, outs),
                         strike_rate=runs / balls * 100 if balls else np.nan,
                         fifties=int(((g.runs >= 50) & (g.runs < 100)).sum()), hundreds=int((g.runs >= 100).sum()),
                         other_innings=len(o), other_average=_avg(o.runs.sum(), o.out.sum()),
                         other_sr=o.runs.sum() / o.balls.sum() * 100 if o.balls.sum() else np.nan,
                         usual_average=usual, usual_sr=usual_sr,
                         edge=(settled - usual) / usual * 100 if np.isfinite(settled) and usual else np.nan))
    return _mark(pd.DataFrame(rows))


def bowling(career, ids, name: str, kind: str, sl: pd.DataFrame | None = None) -> pd.DataFrame:
    """One row a slot the player bowled in (in order): innings, balls, overs (text), runs, wickets, bbi (best, text),
    average, economy, strike rate (balls a wicket), hauls (5 wickets in an innings in first-class cricket, 4 or more in
    one-day and T20); their average and economy in their other innings; the usual average and economy there; settled
    edge on the usual (economy in T20 cricket, average otherwise; + is better)."""
    sl = slots(career, ids, kind) if sl is None else sl
    w = career.bowling[career.bowling.match_id.isin(set(ids)) & (career.bowling.balls > 0)]
    w = w.merge(sl[["match_id", "innings_no", "slot"]], on=["match_id", "innings_no"])
    me = w[w.player == name]
    pool = w.groupby("slot").agg(runs=("runs", "sum"), wickets=("wickets", "sum"), balls=("balls", "sum"))
    k = SHRINK[kind]
    haul = 5 if kind == "multi" else 4
    rows = []
    for slot in order(kind):
        g = me[me.slot == slot]
        if g.empty:
            continue
        o = me[me.slot.isin(others(kind, slot))]
        p = pool.loc[slot]
        u_avg = p.runs / p.wickets if p.wickets else np.nan
        u_econ = p.runs / p.balls * 6 if p.balls else np.nan
        runs, wkts, balls = int(g.runs.sum()), int(g.wickets.sum()), int(g.balls.sum())
        bb = g.loc[g.assign(_k=g.wickets * 1000 - g.runs)._k.idxmax()]
        if kind == "t20":
            settled = (runs + ECON_SETTLE_BALLS * u_econ / 6) / (balls + ECON_SETTLE_BALLS) * 6
            edge = (u_econ - settled) / u_econ * 100 if u_econ else np.nan
        else:
            settled = (runs + k * u_avg) / (wkts + k) if np.isfinite(u_avg) else np.nan
            edge = (u_avg - settled) / u_avg * 100 if np.isfinite(settled) and u_avg else np.nan
        rows.append(dict(slot=slot, label=label(kind, slot, True), innings=len(g), balls=balls, overs=balls_to_overs(balls),
                         runs=runs, wickets=wkts, bbi=f"{int(bb.wickets)}/{int(bb.runs)}", average=_avg(runs, wkts),
                         economy=runs / balls * 6, strike_rate=balls / wkts if wkts else np.nan,
                         hauls=int((g.wickets >= haul).sum()), other_innings=len(o),
                         other_average=_avg(o.runs.sum(), o.wickets.sum()),
                         other_economy=o.runs.sum() / o.balls.sum() * 6 if o.balls.sum() else np.nan,
                         usual_average=u_avg, usual_economy=u_econ, edge=edge))
    return _mark(pd.DataFrame(rows))


def _mark(d: pd.DataFrame) -> pd.DataFrame:
    """`small` (under 5 innings), and `best` / `weakest`: the biggest and smallest settled edge among the slots with 5+
    innings, when there are two such slots and they're more than 10% apart (`same` when they aren't)."""
    if d.empty:
        return d
    d["small"] = d.innings < SMALL
    d["best"] = d["weakest"] = d["same"] = False
    ok = d[~d.small & d.edge.notna()]
    if len(ok) >= 2:
        hi, lo = ok.edge.idxmax(), ok.edge.idxmin()
        if ok.edge[hi] - ok.edge[lo] > SAME:
            d.loc[hi, "best"] = True
            d.loc[lo, "weakest"] = True
        else:
            d.loc[ok.index, "same"] = True
    return d
