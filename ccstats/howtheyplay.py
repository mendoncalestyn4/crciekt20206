"""How they play (Opponent preview, About them): a team's own way with bat and ball, read from what the scorecards
hold. There are no overs on a scorecard (no over a wicket fell in, no runs per over), so it goes by the score at each
wicket, the batting order, each batter's runs, balls, fours and sixes, and the order the bowlers came on.

Their own figures only, never against the usual (the owner's choice, 13 November). The few fixed lines it reads them
by are cricket's own rules of thumb, the same for every team, and are written out on the page:
- three down cheaply: the 3rd wicket by 30 runs in T20 cricket, 50 in one-day and 75 in multi-day cricket;
- attacking: a wicket every 18 balls or fewer (T20), 32 (one-day), 55 (multi-day);
- squeezing: under 7.5 runs an over (T20), 5.0 (one-day), 3.0 (multi-day);
- the order in four parts: openers (1-2), top order (3-4), middle order (5-7) and lower order (8-11);
- the usual score at each wicket: the middle score when it fell, for wickets that fell in at least half their innings,
  stopping where it would dip (each wicket's middle score is of different innings);
- "blast from the start" when the openers score 10% faster than the middle order, "build, then blast" when the middle
  order scores 10% faster than the openers; a fast start that fades or a slow start with a strong finish when the
  first three wickets' stands run 15% above or below the next three."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .stats import kind_of

CHEAP = {"t20": 30, "one": 50, "multi": 75}
ATTACK = {"t20": 18, "one": 32, "multi": 55}          # balls a wicket, or fewer
SQUEEZE = {"t20": 7.5, "one": 5.0, "multi": 3.0}      # runs an over, under
PARTS = [("Openers (1-2)", 1, 2), ("Top order (3-4)", 3, 4), ("Middle order (5-7)", 5, 7), ("Lower order (8-11)", 8, 11)]
FASTER = 1.10
SHIFT = 1.15
MIN_MATCHES = 5   # fewer matches than this in the season: a note and last season offered


def seasons(career, ids, team: str) -> tuple[str, str, dict]:
    """(this season, the last season before it that the team played, the team's matches in each season), this season
    being the competition's latest (so a side that hasn't played yet this season shows none)."""
    m = career.matches[career.matches.match_id.isin(ids)]
    if m.empty:
        return "", "", {}
    order = m.groupby("season").date.max().sort_values()
    this = order.index[-1]
    mine = m[(m.home == team) | (m.away == team)]
    n = mine.season.value_counts().to_dict()
    before = [s for s in order.index[:-1] if n.get(s, 0)]
    return str(this), (str(before[-1]) if before else ""), {str(k): int(v) for k, v in n.items()}


def how_they_play(career, ids, team: str) -> dict:
    """The team's bowling and batting in these matches, as figures (the page writes them in words)."""
    m = career.matches[career.matches.match_id.isin(ids)]
    mine = m[(m.home == team) | (m.away == team)]
    mids = set(mine.match_id)
    kind = kind_of(mine) if len(mine) else "t20"
    inn = career.innings[career.innings.match_id.isin(mids)]
    theirs_inn = inn[inn.team != team]          # the innings they bowled at
    own_inn = inn[inn.team == team]
    fow = career.fow[career.fow.match_id.isin(mids)]
    out: dict = dict(kind=kind, matches=len(mids), bowling={}, batting={})

    # ---- bowling: when the wickets come, from whom, and against whom
    key_t = set(zip(theirs_inn.match_id, theirs_inn.innings_no))
    f_t = fow[[k in key_t for k in zip(fow.match_id, fow.innings_no)]]
    at = {}
    for w in (1, 2, 3):
        x = f_t[f_t.wicket == w].score
        at[w] = dict(usual=int(np.floor(x.median() + 0.5)) if len(x) else None, innings=int(len(x)))
    third = f_t[f_t.wicket == 3].set_index(["match_id", "innings_no"]).score
    n_t = len(theirs_inn)
    cheap = int(sum(1 for k in key_t if k in third.index and third[k] <= CHEAP[kind]))
    bowled_out = int(theirs_inn.all_out.sum())
    bowl = career.bowling[career.bowling.match_id.isin(mids) & (career.bowling.team == team)].copy()
    bowl["order"] = bowl.groupby(["match_id", "innings_no"]).cumcount()     # the card lists them as they came on
    w_all = int(bowl.wickets.sum())
    w_new = int(bowl[bowl.order < 2].wickets.sum())
    bat_t = career.batting[career.batting.match_id.isin(mids) & (career.batting.team != team) & career.batting.out]
    outs = len(bat_t)
    top = int((bat_t.position <= 3).sum())
    balls, runs = int(bowl.balls.sum()), int(bowl.runs.sum())
    dots = bowl.dots.dropna() if "dots" in bowl else pd.Series(dtype=float)
    dot_pct = float(dots.sum() / bowl.loc[dots.index, "balls"].sum() * 100) if len(dots) and kind == "t20" \
        and bowl.loc[dots.index, "balls"].sum() else None
    sr = balls / w_all if w_all else None
    econ = runs / balls * 6 if balls else None
    out["bowling"] = dict(
        at=at, innings=n_t, cheap=cheap, cheap_line=CHEAP[kind], bowled_out=bowled_out, wickets=w_all, new_ball=w_new,
        new_ball_share=w_new / w_all * 100 if w_all else None, outs=outs, top_order=top,
        top_order_share=top / outs * 100 if outs else None, balls_per_wicket=sr, economy=econ, dot_pct=dot_pct,
        attack=bool(sr is not None and sr <= ATTACK[kind]), squeeze=bool(econ is not None and econ < SQUEEZE[kind]),
        attack_line=ATTACK[kind], squeeze_line=SQUEEZE[kind])

    # ---- batting: how fast each part of the order goes, the boundaries, and the usual score at each wicket
    b = career.batting[career.batting.match_id.isin(mids) & (career.batting.team == team) & career.batting.did_bat]
    parts = []
    for label, lo, hi in PARTS:
        x = b[(b.position >= lo) & (b.position <= hi)]
        r_, bl = int(x.runs.sum()), int(x.balls.sum())
        bound = int((x.fours * 4 + x.sixes * 6).sum())
        parts.append(dict(part=label, runs=r_, balls=bl, strike_rate=r_ / bl * 100 if bl else None,
                          boundary_share=bound / r_ * 100 if r_ else None, fours=int(x.fours.sum()), sixes=int(x.sixes.sum())))
    total = int(b.runs.sum())
    f4, f6 = int((b.fours * 4).sum()), int((b.sixes * 6).sum())
    op, mid = parts[0]["strike_rate"], parts[2]["strike_rate"]
    shape = ""
    if op and mid:
        shape = "blast" if op >= mid * FASTER else "build" if mid >= op * FASTER else "steady"
    key_o = set(zip(own_inn.match_id, own_inn.innings_no))
    f_o = fow[[k in key_o for k in zip(fow.match_id, fow.innings_no)]]
    usual = {}
    for w in range(1, 11):   # wickets that fell in at least half their innings, and only while the score keeps rising
        x = f_o[f_o.wicket == w].score    # (each wicket's middle score is of different innings, so it can dip)
        if not len(x) or len(x) < 0.5 * max(len(own_inn), 1):
            break
        v = int(np.floor(x.median() + 0.5))
        if usual and v <= usual[w - 1]:
            break
        usual[w] = v
    pace = ""
    if all(w in usual for w in (3, 6)):
        early, later = usual[3] / 3, (usual[6] - usual[3]) / 3
        pace = "fade" if early >= later * SHIFT else "finish" if later >= early * SHIFT else "even"
    most6 = max(parts, key=lambda p: p["sixes"]) if any(p["sixes"] for p in parts) else None
    out["batting"] = dict(parts=parts, runs=total, from_fours=f4, from_sixes=f6, running=total - f4 - f6,
                          four_share=f4 / total * 100 if total else None, six_share=f6 / total * 100 if total else None,
                          shape=shape, usual=usual, pace=pace, innings=len(own_inn),
                          most_sixes=most6["part"] if most6 else "", most_sixes_n=most6["sixes"] if most6 else 0)
    return out
