"""Leaders and records (stage 3): the sums behind the Stat by stat page, worked out here so the server only passes
them on.

Stat by stat ranks every qualifying player on one stat in the competitions ticked, as the current site's page does
(views/stat_by_stat.py): the same tables (ccstats.stats.player_tables), the same minimum to qualify, the same order
for equal figures, the same "Rank %" and change since the season before. What's new (your answers of 13 and 19
November): every competition is its own tick box, any of them can be ticked together, and then each one is measured
against its own average: a figure that is itself "against the average" (runs above average, runs saved) is worked
out in each competition and added up, so a T20 innings is never measured against a Test batter's average. Fielding
is not shown (your decision of 14 November)."""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np
import pandas as pd

from . import deep as D
from .stats import POSITION_GROUPS, Baseline, Scope, Stat, player_tables, rank, stat_definitions

DISCS = ("Batting", "Bowling")
# the minimum to qualify, in balls faced or bowled, for each kind of cricket (the current site's lists)
MINS = {"Batting": {"t20": [0, 20, 30, 60, 100], "one": [0, 40, 60, 120, 200], "multi": [0, 60, 100, 200, 400]},
        "Bowling": {"t20": [0, 20, 36, 60, 120], "one": [0, 30, 60, 120, 240], "multi": [0, 60, 120, 240, 480]}}
UNIT = {"Batting": "balls faced", "Bowling": "balls bowled"}
VENUES = {"Home": "home", "Away": "away", "Neutral": "neutral"}
HOW = ["caught", "bowled", "lbw", "run out", "stumped", "not out", "retired hurt"]   # how the batter was out
GROUPS = list(POSITION_GROUPS)
AGAINST = {"Batting": "runs_above_average", "Bowling": "runs_saved"}   # figures that are already "against the average"
MEASURES = {"all": "Everyone ticked together", "section": "Each competition's own average",
            "season": "Each season's own average"}


@dataclass
class Board:
    table: pd.DataFrame    # every player in the selection, with the stat's column
    pool: pd.DataFrame     # those who qualify (and are in "Only these players")
    ranked: pd.DataFrame   # the pool, best (or worst) first
    stat: Stat             # the stat ranked (its fair form when measured against each part's own average)
    raw: Stat              # the stat as picked
    base: Baseline
    options: list[int]     # the minimum-to-qualify choices
    minimum: int
    default_min: int
    measures: list[str]
    measure: str


def tables(career, scope: Scope, disc: str) -> tuple[pd.DataFrame, Baseline]:
    """The batting or bowling table for the selection. Several competitions ticked: runs above average (or runs saved)
    is each competition's own, added up."""
    bat, bowl, _, base = player_tables(career, scope)
    table = bat if disc == "Batting" else bowl
    if len(scope.sections) > 1 and len(table):
        col = AGAINST[disc]
        fair, _ = D.fair_index(career, scope, disc, col, "section")
        table = table.assign(**{col: table.player.map(fair)})
    return table, base


def stats_for(base: Baseline, disc: str) -> list[Stat]:
    return stat_definitions(base)["bat" if disc == "Batting" else "bowl"]


def measures_for(scope: Scope, career) -> list[str]:
    """"Everyone ticked together", then each competition's own average (several ticked) and each season's own
    average (several seasons in play)."""
    out = ["all"]
    if len(scope.sections) > 1:
        out.append("section")
    m = career.matches
    seasons = scope.seasons or sorted(m[m.section.isin(scope.sections)].season.unique())
    if len(seasons) > 1:
        out.append("season")
    return out


def board(career, scope: Scope, disc: str, stat_id: str, best: bool = True, minimum: int | None = None,
          only: tuple = (), measure: str = "all") -> Board:
    table, base = tables(career, scope, disc)
    defs = stats_for(base, disc)
    raw = next((s for s in defs if s.id == stat_id), defs[0])
    options = MINS[disc][base.kind]
    # the current site's default: the stricter end of the list, as long as at least 12 players still qualify
    default_min = next((v for v in reversed(options[:3]) if (table["balls"] >= v).sum() >= 12), options[0])
    if minimum not in options:
        minimum = default_min
    measures = measures_for(scope, career)
    if measure not in measures:
        measure = "all"
    stat = raw
    if measure != "all" and len(table):
        fair, unit = D.fair_index(career, scope, disc, raw.id, measure)
        table = table.assign(fair=table.player.map(fair))
        stat = D.fair_stat(raw, unit, measure)
        stat = replace(stat, label=stat.label.replace("own section", "own competition"),
                       definition=stat.definition.replace("section", "competition"))
    pool = table[table[stat.column].notna() & (table["balls"] >= minimum)] if len(table) else table
    if only:
        pool = pool[pool.player.isin(set(only))]
    ranked = rank(pool, stat, best=best) if len(pool) else pool
    return Board(table, pool, ranked, stat, raw, base, options, int(minimum), int(default_min), measures, measure)


def better_side(board_: Board) -> tuple[float, pd.Series]:
    """(the share of qualifying players on the better side of the average line, each player's line value)."""
    d = board_.stat.dot
    pool = board_.pool
    xs, ys = pool[d.x].astype(float), pool[d.y].astype(float)
    line = xs * d.value if d.line == "slope" else pd.Series(d.value, index=pool.index)
    on = (ys < line) if d.better_below else (ys > line)
    return (float(on.mean() * 100) if len(pool) else np.nan), line


def positions_of(groups: list[str], single: list[int]) -> list[int]:
    """Batting positions from the groups picked (or the single positions, when picked one by one)."""
    if single:
        return sorted({int(x) for x in single if 1 <= int(x) <= 11})
    return sorted({x for g in groups for x in POSITION_GROUPS.get(g, [])})
