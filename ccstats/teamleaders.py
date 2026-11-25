"""Team leaders (stage 3; agreed 13 November, your answer 13): each team's two biggest contributors to its runs and to
its wickets in one competition (formats never mixed) and one season or all time, just to see, not to compare.

- Runs: the top 2 by share of the team's runs off the bat (extras are nobody's, so the batters' shares add up to 100%),
  the same counting as "Who carries the team" (ccstats.aim.team_shares). Wickets, apart: the top 2 by share of the
  wickets the team's bowlers took. No threshold: the top two, whoever they are.
- Equal shares go to more matches, then A to Z. A player who played for two teams counts for each separately.
- No longer playing: crossed out when they played no game for that team in this competition in its last two seasons
  (the latest, which may still be going, and the one before), so a season that has only just started never crosses
  anyone out on its own, and a player who comes back is shown normally again."""

from __future__ import annotations

import pandas as pd

from .aim import team_shares


def gone(career, section: str, team: str) -> set[str]:
    """The team's players in this competition who played none of its last two seasons for it."""
    m = career.matches[(career.matches.section == section) & ((career.matches.home == team) | (career.matches.away == team))]
    seasons = sorted(m.season.unique())
    if len(seasons) < 2:
        return set()
    recent = set(m[m.season.isin(seasons[-2:])].match_id)
    b = career.batting[career.batting.match_id.isin(set(m.match_id)) & (career.batting.team == team)]
    everyone = set(b.player)
    lately = set(b[b.match_id.isin(recent)].player)
    return everyone - lately


def leaders(career, section: str, season, team: str, n: int = 2) -> dict:
    """runs and wickets: the top `n` rows each (player, share, value, matches, gone); team_runs, team_wickets."""
    m = career.matches[career.matches.section == section]
    if season is not None:
        m = m[m.season == season]
    sh = team_shares(career, list(m.match_id), team)
    out = gone(career, section, team)
    def top(share, value):
        if sh.empty:
            return []
        x = sh[sh[value] > 0].sort_values([share, "matches", "player"], ascending=[False, False, True]).head(n)
        return [dict(player=r.player, share=float(getattr(r, share)), value=int(getattr(r, value)), matches=int(r.matches),
                     gone=r.player in out) for r in x.itertuples()]
    return dict(runs=top("run_share", "runs"), wickets=top("wicket_share", "wickets"),
                team_runs=int(sh.attrs.get("team_runs", 0)), team_wickets=int(sh.attrs.get("team_wickets", 0)),
                matches=int(sh.attrs.get("team_matches", 0)))
