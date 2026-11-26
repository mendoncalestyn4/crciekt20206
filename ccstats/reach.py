"""Records within reach (stage 5, your answers of 26 November): career and all-time team records a player could break
with one good match: 100 runs in a multi-day game, 75 in a one-day game, 50 in a T20; 5 wickets (3 in a T20); one
hundred or one five-wicket haul. Each record is either the team's own ("England's most Test runs") or the competition's
("the most Test runs by anyone"). Only players still playing for the team (in its latest season of that competition)
are listed, never the holder himself. On My team (your players) and the opponent preview (both sides)."""

from __future__ import annotations

import pandas as pd

from .stats import KIND, poss

RUNS = {"multi": 100, "one": 75, "t20": 50}
WICKETS = {"multi": 5, "one": 5, "t20": 3}
COLUMNS = ["player", "team", "section", "record", "holder", "record_value", "now", "needed", "unit", "whose"]


def _tallies(career, ids) -> dict[str, pd.DataFrame]:
    """Each player's career runs, wickets, hundreds and five-fors in these matches, by team: (player, team, value)."""
    bat = career.batting[career.batting.match_id.isin(ids) & career.batting.did_bat.astype(bool)]
    bowl = career.bowling[career.bowling.match_id.isin(ids)]
    five = bowl[bowl.wickets >= 5]
    return {"runs": bat.groupby(["player", "team"]).runs.sum(),
            "wickets": bowl.groupby(["player", "team"]).wickets.sum(),
            "hundreds": bat[bat.runs >= 100].groupby(["player", "team"]).size(),
            "five-wicket hauls": five.groupby(["player", "team"]).size()}


def within(career, section: str, teams: list[str]) -> pd.DataFrame:
    """Every record within one good match of a current player of `teams` in this competition, the closest first."""
    m = career.matches[career.matches.section == section]
    if m.empty or not teams:
        return pd.DataFrame(columns=COLUMNS)
    kind = KIND.get(m.format.iloc[0], "one")
    gap = {"runs": RUNS[kind], "wickets": WICKETS[kind], "hundreds": 1, "five-wicket hauls": 1}
    latest = m.season.max()
    rows = []
    t = _tallies(career, m.match_id)
    for team in teams:
        tm = m[(m.home == team) | (m.away == team)]
        if tm.empty:
            continue
        last = tm[tm.season == tm.season.max()].match_id
        now_players = set(career.batting[career.batting.match_id.isin(last) & (career.batting.team == team)].player) | \
            set(career.bowling[career.bowling.match_id.isin(last) & (career.bowling.team == team)].player)
        for unit, s in t.items():
            if s.empty:
                continue
            by_player = s.groupby(level=0).sum()                       # all-time: every team a player played for here
            for whose, pool in ((team, s.xs(team, level=1) if team in s.index.get_level_values(1) else pd.Series(dtype=float)),
                                ("", by_player)):
                if pool.empty:
                    continue
                pool = pool.sort_values(ascending=False)
                holder, best = pool.index[0], int(pool.iloc[0])
                for p in now_players:
                    if p == holder or p not in pool.index:
                        continue
                    v = int(pool[p])
                    need = best - v + 1                                   # to pass the record, not just equal it
                    if 0 < need <= gap[unit]:
                        what = (f"{poss(team)} most {unit} in {section}" if whose else f"the most {unit} in {section}")
                        rows.append((p, team, section, what, holder, best, v, need, unit, whose))
    out = pd.DataFrame(rows, columns=COLUMNS).drop_duplicates(["player", "record"])
    # a team record that is also the competition's (same holder, same figure) is said once, as the bigger one
    allt = set(zip(out[out.whose == ""].player, out[out.whose == ""].unit, out[out.whose == ""].holder,
                   out[out.whose == ""].record_value))
    out = out[(out.whose == "") | ~pd.Series([(a, b, c, d) in allt for a, b, c, d in
                                              zip(out.player, out.unit, out.holder, out.record_value)], index=out.index)]
    out = out.assign(_share=out.needed / out.unit.map(gap)).sort_values(["_share", "player"]).drop(columns="_share")
    return out.reset_index(drop=True) if latest is not None else out


ONE = {"runs": "run", "wickets": "wicket", "hundreds": "hundred", "five-wicket hauls": "five-wicket haul"}


def sentence(r) -> str:
    unit = r.unit if r.needed != 1 else ONE[r.unit]
    return (f"{r.player} needs {r.needed:,} more {unit} to pass {r.record} ({r.holder}, {r.record_value:,}; "
            f"now {r.now:,})")
