"""Career arc (stage 5, your answers of 26 November): how players usually develop season by season of their career in
one competition, and each player against that usual curve.

The measure is the breakouts' one: runs above average per innings batting, runs saved per innings bowling, each season
against that season's own average (so a high-scoring year doesn't flatter everyone). A season counts for a player when
they have `LEAST` innings in it.

The usual curve is worked out the fair way, from each player's change between one season and their next (not from the
level of the players still playing in their 5th season, which would only show the ones good enough to last): the
average change from the 1st season to the 2nd, the 2nd to the 3rd, and so on, added up from 0 at the 1st season. A
step needs `MIN_PLAYERS` players behind it, or the curve stops there.

A player already there in the competition's first season may have played for years before it, so their "1st season"
isn't known. They get a curve of their own: players there from the start, counted by seasons since then. A player
who first appears later is measured against the curve of new players."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .stats import KIND, Scope, player_tables

LEAST = 5            # innings in a season for it to count
MIN_PLAYERS = 3      # players behind a step of the curve
MARGIN = {"bat": {"t20": 2.5, "one": 4.0, "multi": 5.0}, "bowl": {"t20": 2.0, "one": 3.0, "multi": 4.0}}   # ahead/behind
JOBS = (("bat", "runs_above_average"), ("bowl", "runs_saved"))


def seasons(career, section: str) -> pd.DataFrame:
    """One row per player, job and season played here: n (their 1st, 2nd... season here), innings, value per innings,
    whether they were there from the start, and their teams that season."""
    m = career.matches[career.matches.section == section]
    cols = ["player", "job", "season", "n", "innings", "value", "from_start", "teams"]
    if m.empty:
        return pd.DataFrame(columns=cols)
    order = sorted(m.season.unique())
    rows = []
    for s in order:
        b, w, _, _ = player_tables(career, Scope(sections=[section], seasons=[s]))
        for job, col, t in (("bat", "runs_above_average", b), ("bowl", "runs_saved", w)):
            t = t[t.innings > 0]
            rows.append(pd.DataFrame({"player": t.player, "job": job, "season": s, "innings": t.innings.astype(int),
                                      "value": t[col] / t.innings, "teams": t.teams}))
    d = pd.concat(rows, ignore_index=True)
    # seasons a player appeared in at all (batting or bowling), counted 1, 2, 3...
    seen = d[["player", "season"]].drop_duplicates().sort_values(["player", "season"])
    seen["n"] = seen.groupby("player").cumcount() + 1
    first = seen.groupby("player").season.min()
    d = d.merge(seen, on=["player", "season"])
    d["from_start"] = d.player.map(first) == order[0]
    return d[cols].sort_values(["player", "job", "n"]).reset_index(drop=True)


def curve(per: pd.DataFrame, job: str, from_start: bool, least: int = LEAST) -> pd.DataFrame:
    """The usual change since the 1st season, season by season: n, change (0 at n=1), players (behind the step to n)."""
    q = per[(per.job == job) & (per.from_start == from_start) & (per.innings >= least)]
    steps = []
    for _, g in q.groupby("player"):
        g = g.set_index("n")
        for n in g.index:
            if n + 1 in g.index:
                a, b = g.loc[n], g.loc[n + 1]
                steps.append((n, b.value - a.value, 2 / (1 / a.innings + 1 / b.innings)))   # weighted by both seasons' innings
    out = [dict(n=1, change=0.0, players=int(q[q.n == 1].player.nunique()))]
    if steps:
        s = pd.DataFrame(steps, columns=["n", "change", "w"])
        level = 0.0
        for n in range(1, int(s.n.max()) + 1):
            g = s[s.n == n]
            if len(g) < MIN_PLAYERS:
                break
            level += float(np.average(g.change, weights=g.w))
            out.append(dict(n=n + 1, change=level, players=len(g)))
    return pd.DataFrame(out)


def verdicts(career, section: str, per: pd.DataFrame | None = None, least: int = LEAST) -> pd.DataFrame:
    """Each player with two or more counted seasons in a job, against the usual curve: from their first counted season
    to their latest, their own change and the usual change over the same seasons (ahead, on or behind it)."""
    per = seasons(career, section) if per is None else per
    cols = ["player", "job", "from_start", "first_n", "last_n", "seasons", "own", "usual", "diff", "verdict", "teams",
            "last_season", "last_value"]
    m = career.matches[career.matches.section == section]
    if per.empty or m.empty:
        return pd.DataFrame(columns=cols)
    kind = KIND.get(m.format.iloc[0], "one")
    curves = {(job, fs): curve(per, job, fs, least).set_index("n").change for job, _ in JOBS for fs in (True, False)}
    rows = []
    for (p, job), g in per[per.innings >= least].groupby(["player", "job"]):
        if len(g) < 2:
            continue
        g = g.sort_values("n")
        fs = bool(g.from_start.iloc[0])
        c = curves[(job, fs)]
        k, last = int(g.n.iloc[0]), int(g.n.iloc[-1])
        top = int(c.index.max())
        if k >= top:                        # the usual curve doesn't reach past their first counted season
            continue
        upto = min(last, top)               # beyond the curve's end, compared up to where it stops
        own = float(g[g.n <= upto].value.iloc[-1] - g.value.iloc[0])
        usual = float(c[upto] - c[k])
        diff = own - usual
        cut = MARGIN[job][kind]
        rows.append((p, job, fs, k, upto, len(g), own, usual, diff,
                     "ahead" if diff >= cut else "behind" if diff <= -cut else "on", g.teams.iloc[-1],
                     g.season.iloc[-1], float(g.value.iloc[-1])))
    return pd.DataFrame(rows, columns=cols).sort_values("diff", ascending=False).reset_index(drop=True)


def ordinal(n: int) -> str:
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def sentence(r, section: str) -> str:
    """One player's arc in words: "Batting in Tests: +6.2 runs an innings from their 1st season to their 4th; players
    usually go +2.1 over the same seasons, so ahead of the usual curve." """
    what = "Batting" if r.job == "bat" else "Bowling"
    unit = "runs above average an innings" if r.job == "bat" else "runs saved an innings"
    when = (f"from their {ordinal(r.first_n)} season here to their {ordinal(r.last_n)}" if not r.from_start else
            f"from the {ordinal(r.first_n)} season of this career here to the {ordinal(r.last_n)} (they were already "
            "playing when it began)")
    word = {"ahead": "ahead of the usual curve", "on": "on the usual curve", "behind": "behind the usual curve"}[r.verdict]
    return (f"{what} in {section}: {r.own:+.1f} {unit} {when}; players usually go {r.usual:+.1f} over the same seasons, "
            f"so {word}.")
