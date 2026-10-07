"""Deeper versions of existing figures: percentiles, change since last season,
and 'fair' comparisons that measure each player against the average of their
own section (or their own season) before adding anything up."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd

from .stats import Scope, player_tables, stat_definitions

DISC_KEY = {"Batting": "bat", "Bowling": "bowl", "Fielding": "field"}


# --------------------------------------------------------------------------- #
# 85 · percentile
# --------------------------------------------------------------------------- #


def percentiles(pool: pd.DataFrame, column: str, better: str) -> pd.Series:
    """'Top X%' for each player in the pool on one figure: 1 = the very best."""
    v = pool[column].astype(float)
    asc = better == "low"
    best = v.rank(ascending=asc, method="min")  # a tie shares its best place…
    worst = v.rank(ascending=asc, method="max")  # …and its worst
    n = v.notna().sum()
    if n < 2:  # top or bottom of a pool of one says nothing
        return pd.Series(np.nan, index=pool.index)
    # which half: by the middle of the player's place (a tie sits in the middle of the places it shares), so the
    # best of 10 is top 10%, the last of 10 bottom 10%, four tied last of 5 are bottom 80%, and the middle of a
    # small pool (3rd of 5) reads top 50%; top_text reads p <= 50 as "top p%" and p > 50 as "bottom (101 - p)%"
    mid = (best + worst) / 2
    top = best / n * 100
    bottom = (n - worst + 1) / n * 100
    p = top.where(mid < (n + 1) / 2, (101 - bottom).where(mid > (n + 1) / 2, 50)).clip(lower=1)
    return p.where(v.notna())  # no figure: no place


def top_text(p: float) -> str:
    if p is None or not np.isfinite(p):
        return "–"
    p = max(1, int(np.ceil(p)))
    return f"top {p}%" if p <= 50 else f"bottom {101 - p}%"


# --------------------------------------------------------------------------- #
# 86 · change since last season
# --------------------------------------------------------------------------- #


def previous_season(matches: pd.DataFrame, sections: list[str], season: str) -> str | None:
    earlier = sorted(s for s in matches[matches.section.isin(sections)].season.unique() if s < season)
    return earlier[-1] if earlier else None


def change_since(career, scope: Scope, disc: str, column: str) -> tuple[pd.Series, str | None]:
    """(this figure minus the same figure the season before, per player; the previous season).
    Only when exactly one season is picked."""
    if len(scope.seasons) != 1:
        return pd.Series(dtype=float), None
    prev = previous_season(career.matches, scope.sections, scope.seasons[0])
    if prev is None:
        return pd.Series(dtype=float), None
    now = _table(career, scope, disc).set_index("player")[column]
    before = _table(career, replace(scope, seasons=[prev]), disc).set_index("player")[column]
    return (now - before.reindex(now.index)).dropna(), prev


def _table(career, scope: Scope, disc: str) -> pd.DataFrame:
    bat, bowl, fld, _ = player_tables(career, scope)
    return {"Batting": bat, "Bowling": bowl, "Fielding": fld}[disc]


# --------------------------------------------------------------------------- #
# 87 / 88 · fair: each player against their own section's (or season's) average
# --------------------------------------------------------------------------- #


def parts_of(career, scope: Scope, split: str) -> list[Scope]:
    """The scope cut into one piece per section ('section') or per section and season ('season')."""
    m = career.matches[career.matches.match_id.isin(scope.match_ids(career.matches))]
    out = []
    for sec in sorted(m.section.unique()):
        if split == "section":
            out.append(replace(scope, sections=[sec]))
        else:
            for se in sorted(m[m.section == sec].season.unique()):
                out.append(replace(scope, sections=[sec], seasons=[se]))
    return out


def fair_index(career, scope: Scope, disc: str, stat_id: str, split: str) -> tuple[pd.Series, str]:
    """(each player's figure against the average of each part they played in, combined over the parts; the unit).

    For a rate (runs per innings, average, strike rate, economy, ...) a part's
    value is the player's rate divided by that part's average rate, so +20% means
    20% better than the average player where they played (lower-is-better figures
    are turned round, so higher is always better).  The parts are weighted by how
    much the player did in each (innings, balls, ...).  Figures already measured
    against the average ('runs above average', 'runs saved') are simply added up."""
    num: dict[str, float] = {}
    den: dict[str, float] = {}
    flat = False
    for part in parts_of(career, scope, split):
        bat, bowl, fld, base = player_tables(career, part)
        table = {"Batting": bat, "Bowling": bowl, "Fielding": fld}[disc]
        stat = next((s for s in stat_definitions(base)[DISC_KEY[disc]] if s.id == stat_id), None)
        if stat is None or table.empty:
            continue
        d = stat.dot
        if d.line == "flat":
            flat = True
            for p, y in zip(table.player, table[d.y]):
                if pd.notna(y):
                    num[p] = num.get(p, 0.0) + float(y)
                    den[p] = 1.0
            continue
        ref = d.value
        if not ref or not np.isfinite(ref):
            continue
        for p, x, y in zip(table.player, table[d.x], table[d.y]):
            if not x or pd.isna(x) or pd.isna(y):
                continue
            rate = y / x
            ratio = (ref / rate if rate else np.nan) if d.better_below else rate / ref
            if not np.isfinite(ratio):
                continue
            num[p] = num.get(p, 0.0) + ratio * x
            den[p] = den.get(p, 0.0) + x
    if flat:
        return pd.Series(num, dtype=float), "runs"
    s = pd.Series({p: (num[p] / den[p] - 1) * 100 for p in num if den.get(p)}, dtype=float)
    return s, "%"


def fair_stat(stat, unit: str, split: str):
    """A Stat for ranking by the fair index (higher is always better)."""
    what = "own section" if split == "section" else "own season"
    label = f"{stat.label}: % v {what} average" if unit == "%" else f"{stat.label} v {what} average"
    if unit == "%":
        definition = (f"{stat.label} measured against the average player in each {what.split()[1]} they played in, "
                      f"then combined: +20% = 20% better than average where they played.")
    else:
        definition = f"{stat.label}, each {what.split()[1]} against its own average, added up."
    return replace(stat, id=f"{stat.id}_fair_{split}", label=label, column="fair", better="high",
                   decimals=0, definition=definition, reference=0.0)
