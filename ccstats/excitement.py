"""How exciting a match was, 0 to 10, with the reasons: the new site's rating (NEW_SITE_PLAN.md, section 14).

The current site's score (winprob.match_rating) gave the tightest normal finish only 3 or 4 points and missed what
the scorecard shows plainly, so a 1-wicket Test win after trailing by 115 on first innings scored 4.1. This one:

  the finish     up to 7   a tie 7, a tie and a super over 8; a 1-run, 1-wicket or last-ball win 7; otherwise
                           smoothly less (a chase counts its wickets in hand and its balls left, whichever was
                           tighter); a draw with the last pair holding on, or the chasers just short, up to 7
  a comeback     up to 2   how far behind the winners were at their worst. Read from the scorecard: in the last
                           innings, the runs still needed against what the wickets left usually add (from the
                           section's own partnerships); in a Test, a first-innings deficit turned round; or, where
                           the win-chance model sees one (from 8 matches or more), the winner's chance under 25%
  the stakes     up to 1   a final or a series decider 1; a semi-final, qualifier or eliminator 0.7; levelling a
                           series, or another knockout, 0.5
  big moments    up to 1/2 a hundred, a big haul, both sides scoring big, a big chase (1/4 each)

A game shortened by rain is judged on its margin only (its target and overs weren't the full ones)."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from . import partnerships as P
from . import winprob as W
from .stats import bars_for

FINISH, COMEBACK, STAKES, SHOW = 7.0, 2.0, 1.0, 0.5
BALLS = {"T20": 120, "T20I": 120, "The Hundred": 100, "ODI": 300, "List A": 300}
RUN_SCALE = {"t20": 8, "one": 15, "multi": 40}      # the margin (above 1 run) that leaves about a third of the finish
WICKETS_LEFT = {1: 1.0, 2: 0.75, 3: 0.5, 4: 0.3, 5: 0.15}
BIG_CHASE = {"t20": 200, "one": 320, "multi": 300}
BIG_BOTH = {"t20": 180, "one": 320}
DRAW_DOWN = {9: 1.0, 8: 0.7, 7: 0.4}


def expected_left(career, ids) -> dict[int, float]:
    """After k wickets (0-9): what the wickets left usually add in these matches (the mean stand for each wicket)."""
    st = P.stands(career, ids)
    if st.empty:
        return {}
    mean = st.groupby("wicket").runs.mean().reindex(range(1, 11)).fillna(0.0)
    return {k: float(mean.loc[k + 1:].sum()) for k in range(10)}


def chance_chasing(needed: float, down: int, expected: dict[int, float]) -> float:
    """A plain chance for the side chasing: the runs needed against what its wickets left usually add (needing
    exactly that is even; twice that, about 1 in 9)."""
    if needed <= 0:
        return 1.0
    e = expected.get(int(down), 0.0)
    if e <= 0:
        return 0.0
    return 1 / (1 + (needed / e) ** 3)


def _chase(inn: pd.DataFrame, fow: pd.DataFrame) -> tuple[str, int, list[tuple[int, int]]]:
    """The last innings as a chase: (the side chasing, the target, (wickets down, score) at its start and after
    every wicket)."""
    last, before = inn.iloc[-1], inn.iloc[:-1]
    target = int(before[before.team != last.team].runs.sum() - before[before.team == last.team].runs.sum() + 1)
    falls = fow[fow.innings_no == last.innings_no].sort_values("wicket")
    return last.team, target, [(0, 0)] + [(int(w), int(s)) for w, s in zip(falls.wicket, falls.score)]


def _real_chase(r, inn: pd.DataFrame, kind: str) -> bool:
    """The last innings was a chase to the end: a one-innings game's second, or a Test's fourth (not after an innings
    win), never a game shortened by rain."""
    if bool(getattr(r, "rain", False)):
        return False
    return len(inn) == 2 if kind != "multi" else (len(inn) == 4 and not r.innings_win)


def finish(r, inn: pd.DataFrame, kind: str) -> tuple[float, str]:
    """0 to 1 (8/7 for a super over): how tight the result was, and the words for it."""
    if r.super_over:
        return 8 / 7, "tied, and a super over"
    if r.result_type == "tie":
        return 1.0, "tied"
    if r.innings_win:
        return 0.0, ""
    if pd.notna(r.margin_runs) and r.winner:
        f = math.exp(-(max(r.margin_runs, 1) - 1) / RUN_SCALE[kind])
        return f, (f"won by {int(r.margin_runs)} run{'s' if r.margin_runs != 1 else ''}" if f >= 0.15 else "")
    if pd.notna(r.margin_wickets) and r.winner:
        wk, bl, left = WICKETS_LEFT.get(int(r.margin_wickets), 0.0), 0.0, None
        if kind != "multi" and r.format in BALLS and not bool(getattr(r, "rain", False)) and len(inn) == 2:
            left = max(BALLS[r.format] - int(inn.balls.iloc[-1]), 0)
            bl = math.exp(-left / (BALLS[r.format] * 0.05))      # T20: 3 balls left keep 0.61, 6 balls 0.37
        f = 1 - (1 - wk) * (1 - bl)                               # tight on wickets or on balls; both, tighter still
        words = f"won by {int(r.margin_wickets)} wicket{'s' if r.margin_wickets > 1 else ''}"
        if left is not None and left <= BALLS[r.format] * 0.05:
            words += " off the last ball" if left == 0 else f" with {left} ball{'s' if left > 1 else ''} left"
        return f, (words if f >= 0.15 else "")
    if r.result_type == "draw" and len(inn) == 4:
        down = int(inn.wickets.iloc[-1])
        f, words = DRAW_DOWN.get(down, 0.0), f"drawn with {down} down"
        last, before = inn.iloc[-1], inn.iloc[:-1]
        short = int(before[before.team != last.team].runs.sum() - before[before.team == last.team].runs.sum() + 1
                    - last.runs)
        if 0 < short <= 60 and math.exp(-(short - 1) / RUN_SCALE[kind]) > f:   # chasing, and nearly there
            f = math.exp(-(short - 1) / RUN_SCALE[kind])
            words = f"drawn {short} run{'s' if short != 1 else ''} short of the target"
        return f, (words if f >= 0.15 else "")
    return 0.0, ""


def comeback(r, inn: pd.DataFrame, fow: pd.DataFrame, kind: str, expected: dict[int, float],
             line: pd.DataFrame | None = None) -> tuple[float, str]:
    """0 to 1: how far behind the winners were at their worst, and the words for it."""
    best, words = 0.0, ""
    if r.winner and expected and _real_chase(r, inn, kind):
        chaser, target, states = _chase(inn, fow)
        if chaser == r.winner:   # they chased it down: their worst moment in the chase
            low, at = 1.0, None
            for down, score in states:
                if down < 10:
                    ch = chance_chasing(target - score, down, expected)
                    if ch < low:
                        low, at = ch, (down, score)
            fb = min(1.0, max(0.0, (0.35 - low) / 0.30))
            if at and fb > best:
                best, words = fb, f"{at[1]}/{at[0]} needing {target - at[1]}"
        elif kind == "multi":   # they defended it: the chasers' best moment with two wickets or more still in hand
            high, at = 0.0, None
            for down, score in states:
                if down < 9:     # the last pair is the finish itself, counted there
                    ch = chance_chasing(target - score, down, expected)
                    if ch > high:
                        high, at = ch, (down, score)
            fb = min(1.0, max(0.0, (high - 0.65) / 0.30))
            if at and fb > best:
                best, words = fb, (f"{chaser} needed only {target} with all ten wickets left" if at == (0, 0) else
                                   f"{chaser} were {at[1]}/{at[0]} needing {target - at[1]}")
    if kind == "multi" and r.winner and len(inn) >= 3:
        first = inn[inn.innings_no <= 2]
        if len(first) == 2 and first.team.nunique() == 2:
            mine = int(first[first.team == r.winner].runs.sum())
            theirs = int(first[first.team != r.winner].runs.sum())
            if theirs > mine and min(1.0, (theirs - mine) / 150) > best:
                best, words = min(1.0, (theirs - mine) / 150), f"{theirs - mine} behind on first innings"
    low = model_low(line)
    if low and low[0] < 25 and 1 - low[0] / 25 > best:
        best, words = 1 - low[0] / 25, f"from {low[0]:.0f}%"
    return best, (f"a comeback ({words})" if best >= 0.2 else "")


def model_low(line: pd.DataFrame | None) -> tuple[float, str] | None:
    """The winner's lowest chance on the win-chance line, counting only the points the model judged from enough
    matches (in a section of two matches it says 0% from one other game, which means nothing)."""
    if line is None or line.empty or line.attrs.get("outcome") not in ("W", "L"):
        return None
    ok = line[line.n >= W.MIN_GAMES]
    ch = (ok.W if line.attrs["outcome"] == "W" else ok.L).astype(float).dropna()
    if ch.empty:
        return None
    i = ch.idxmin()
    return float(ch[i]), str(ok.label[i])


def stakes(r, series: pd.DataFrame | None) -> tuple[float, str]:
    """0 to 1: what was riding on it. `series`: the other matches of its series, if it's part of one."""
    if r.knockout:
        stage = str(r.stage)
        if stage == "Final":
            return 1.0, "a final"
        if stage in ("Semi-final", "Qualifier 1", "Qualifier 2", "Eliminator"):
            return 0.7, f"a {stage.lower()}"
        return 0.5, "a knockout"
    if series is not None and len(series) and pd.notna(r.series_length) and r.series_length > 1:
        before = series[series.series_match_no < r.series_match_no]
        a, b = int((before.winner == r.home).sum()), int((before.winner == r.away).sum())
        if r.series_match_no == r.series_length and a == b:
            return 1.0, "a series decider"
        if r.winner and ((r.winner == r.home and a + 1 == b) or (r.winner == r.away and b + 1 == a)):
            return 0.5, "levelled the series"
    return 0.0, ""


def big_moments(r, inn: pd.DataFrame, top_score: int, top_haul: int, kind: str) -> tuple[float, str]:
    """0 to 1: a hundred, a big haul, both sides scoring big, a big chase (half each)."""
    bits = []
    if top_score >= 100:
        bits.append("a hundred")
    if top_haul >= bars_for(kind)["headline_haul"]:
        bits.append(f"a {top_haul}-wicket haul")
    if kind in BIG_BOTH and len(inn) == 2 and inn.runs.min() >= BIG_BOTH[kind]:
        bits.append("both sides scored big")
    if r.winner and _real_chase(r, inn, kind) and inn.iloc[-1].team == r.winner:
        last, before = inn.iloc[-1], inn.iloc[:-1]
        target = int(before[before.team != last.team].runs.sum() - before[before.team == last.team].runs.sum() + 1)
        if target - 1 >= BIG_CHASE[kind]:
            bits.append(f"chased {target}")
    return min(1.0, len(bits) / 2), ", ".join(bits)


RATING_COLUMNS = ["match_id", "date", "section", "home", "away", "result", "stage", "rating", "finish", "comeback",
                  "stakes", "show", "why", "rank", "of"]


def rate(career, ids) -> pd.DataFrame:
    """Every match in these ids (one section, so each is judged against its own kind of cricket) rated, best first,
    with each part, the reasons and its place in the section."""
    m = career.matches[career.matches.match_id.isin(ids)]
    if m.empty:
        return pd.DataFrame(columns=RATING_COLUMNS)
    kind = W.kind_of_ids(career, ids)
    states = W.states(career, ids)
    expected = expected_left(career, ids)
    inns = {k: g for k, g in career.innings[career.innings.match_id.isin(m.match_id)].sort_values("innings_no")
            .groupby("match_id")}
    fows = {k: g for k, g in career.fow[career.fow.match_id.isin(m.match_id)].groupby("match_id")}
    top_score = career.batting[career.batting.match_id.isin(m.match_id)].groupby("match_id").runs.max()
    top_haul = career.bowling[career.bowling.match_id.isin(m.match_id)].groupby("match_id").wickets.max()
    series = {k: g for k, g in career.matches[career.matches.series_id != ""].groupby("series_id")}
    rows = []
    for r in m.itertuples():
        inn = inns.get(r.match_id)
        if inn is None or inn.empty:
            continue
        fow = fows.get(r.match_id, career.fow.iloc[0:0])
        line = W.match_line(career, r.match_id, states, kind)
        f, fw = finish(r, inn, kind)
        c, cw = comeback(r, inn, fow, kind, expected, line)
        s, sw = stakes(r, series.get(r.series_id) if r.series_id else None)
        b, bw = big_moments(r, inn, int(top_score.get(r.match_id, 0)), int(top_haul.get(r.match_id, 0)), kind)
        parts = dict(finish=round(FINISH * f, 2), comeback=round(COMEBACK * c, 2), stakes=round(STAKES * s, 2),
                     show=round(SHOW * b, 2))
        rows.append(dict(match_id=r.match_id, date=r.date, section=r.section, home=r.home, away=r.away,
                         result=r.result, stage=r.stage, rating=round(min(10.0, sum(parts.values())), 1), **parts,
                         why=", ".join(x for x in (fw, cw, sw, bw) if x)))
    d = pd.DataFrame(rows, columns=RATING_COLUMNS[:-2])
    d["rank"] = d.rating.rank(ascending=False, method="min").astype(int)
    d["of"] = len(d)
    return d.sort_values(["rating", "date"], ascending=[False, False]).reset_index(drop=True)
