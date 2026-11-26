"""The selection review (stage 5, your answers of 26 November), a tab on My team: every XI the team picked, straight
from the scorecards, competition by competition.

- Dropped after a good score: 50+ in Tests and one-day games, 40+ in T20s, or 4+ wickets in a match (5+ in a
  multi-day game), then not in the side for the team's next match in that competition.
- Kept through a poor run: 5 innings in a row under 15 (under 10 in T20s), or 5 bowling matches in a row without a
  wicket, and still picked for the next match.
- How often the side changes: players in who weren't in the previous match's XI, per match, against the other teams in
  the same competition."""

from __future__ import annotations

import pandas as pd

from .stats import KIND

GOOD_RUNS = {"multi": 50, "one": 50, "t20": 40}
GOOD_WKTS = {"multi": 5, "one": 4, "t20": 4}
POOR_RUNS = {"multi": 15, "one": 15, "t20": 10}
RUN = 5


def _xis(career, ids, team: str) -> list[tuple[str, pd.Timestamp, set]]:
    """The team's XI in each of these matches, in the order played: (match_id, date, players)."""
    m = career.matches[career.matches.match_id.isin(ids) & ((career.matches.home == team) | (career.matches.away == team))]
    m = m.sort_values(["date", "match_id"])
    bat = career.batting[career.batting.match_id.isin(m.match_id) & (career.batting.team == team)]
    by = bat.groupby("match_id").player.apply(set)
    return [(mid, d, by.get(mid, set())) for mid, d in zip(m.match_id, m.date) if mid in by.index]


def changes(career, ids, team: str) -> float | None:
    """Average players brought in per match (against the previous match's XI)."""
    xis = _xis(career, ids, team)
    if len(xis) < 2:
        return None
    return sum(len(b[2] - a[2]) for a, b in zip(xis, xis[1:])) / (len(xis) - 1)


def review(career, team: str, section: str) -> dict:
    m = career.matches[career.matches.section == section]
    kind = KIND.get(m.format.iloc[0], "one") if len(m) else "one"
    xis = _xis(career, m.match_id, team)
    out: dict = dict(section=section, dropped=[], kept=[], changes=None, others=None, matches=len(xis))
    if len(xis) < 2:
        return out
    order = {mid: i for i, (mid, _, _) in enumerate(xis)}
    bat = career.batting[career.batting.match_id.isin(order) & (career.batting.team == team)]
    bowl = career.bowling[career.bowling.match_id.isin(order) & (career.bowling.team == team)]
    runs = bat.groupby(["match_id", "player"]).runs.max()          # their best innings in the match
    wkts = bowl.groupby(["match_id", "player"]).wickets.sum()
    # dropped straight after a good score
    for i, (mid, d, xi) in enumerate(xis[:-1]):
        nxt_mid, nxt_d, nxt = xis[i + 1]
        for p in sorted(xi - nxt):
            r, w = int(runs.get((mid, p), 0)), int(wkts.get((mid, p), 0))
            if r >= GOOD_RUNS[kind] or w >= GOOD_WKTS[kind]:
                what = f"{r} runs" if r >= GOOD_RUNS[kind] else f"{w} wickets"
                if r >= GOOD_RUNS[kind] and w >= GOOD_WKTS[kind]:
                    what = f"{r} runs and {w} wickets"
                out["dropped"].append(dict(player=p, did=what, date=d, match_id=mid, left_out=nxt_d, next_id=nxt_mid))
    # kept through a poor run: the run's last innings (or match), and he played the next match
    did = bat[bat.did_bat.astype(bool)].assign(o=lambda x: x.match_id.map(order)).sort_values(["o", "innings_no"])
    for p, g in did.groupby("player"):
        low = 0
        runs_so_far: list[int] = []
        for r in g.itertuples():
            runs_so_far.append(int(r.runs))
            low = low + 1 if r.runs < POOR_RUNS[kind] else 0
            if low == RUN and r.o + 1 < len(xis) and p in xis[r.o + 1][2]:
                scores = runs_so_far[-RUN:]                           # the run itself, innings by innings
                out["kept"].append(dict(player=p, did=f"{RUN} innings under {POOR_RUNS[kind]} ({', '.join(map(str, scores))})",
                                        date=xis[r.o][1], match_id=r.match_id, kept_for=xis[r.o + 1][1], next_id=xis[r.o + 1][0]))
    bw = bowl.assign(o=lambda x: x.match_id.map(order)).groupby(["player", "o"]).wickets.sum().reset_index().sort_values("o")
    for p, g in bw.groupby("player"):
        dry = 0
        for r in g.itertuples():
            dry = dry + 1 if r.wickets == 0 else 0
            if dry == RUN and r.o + 1 < len(xis) and p in xis[r.o + 1][2]:
                out["kept"].append(dict(player=p, did=f"{RUN} bowling matches in a row without a wicket", date=xis[r.o][1],
                                        match_id=xis[r.o][0], kept_for=xis[r.o + 1][1], next_id=xis[r.o + 1][0]))
    out["dropped"].sort(key=lambda x: x["date"], reverse=True)
    out["kept"].sort(key=lambda x: x["date"], reverse=True)
    out["changes"] = changes(career, m.match_id, team)
    teams = sorted((set(m.home) | set(m.away)) - {team})
    others = [c for c in (changes(career, m.match_id, t) for t in teams) if c is not None]
    out["others"] = sum(others) / len(others) if others else None
    return out
