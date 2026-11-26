"""Your eras (stage 5, your answers of 26 November): the stretches when a team was strongest, by its ratings.

A team's rating is the site's team rating (rankings.team_elo, the one on Competitions · Team ratings), one competition
at a time (ratings never mix formats). At the end of each season the teams that played in it are ranked by their
rating then; a season "near the top" is one finished in the top `TOP` (or the top sixth, when more than 12 teams
played that season: a Ranji Trophy season of 38 teams counts its top 7). An era is `MIN_SEASONS` or more of the team's own seasons in a row near the top (a season the team
didn't play in this competition doesn't break it), named by its years ("the 2029–31 era"), with its results, its peak
rating and its key players (most runs, most wickets)."""

from __future__ import annotations

import math

import pandas as pd

from .rankings import team_elo

TOP = 3
MIN_SEASONS = 2


def top_of(n_teams: int) -> int:
    """How high a team must finish to be "near the top": the top 3, or the top sixth of a big competition."""
    return max(TOP, math.ceil(n_teams / 6)) if n_teams > 12 else TOP


def season_ranks(career, section: str) -> pd.DataFrame:
    """Each team's rating at the end of each season it played, and its rank among that season's teams."""
    m = career.matches[career.matches.section == section]
    cols = ["season", "team", "rating", "rank", "teams", "top"]
    if m.empty:
        return pd.DataFrame(columns=cols)
    _, hist = team_elo(career, section)
    if hist.empty:
        return pd.DataFrame(columns=cols)
    hist = hist.assign(season=hist.match_id.map(m.set_index("match_id").season))
    end = hist.groupby(["season", "team"]).after.last().reset_index().rename(columns={"after": "rating"})
    # a rating carried into a season the team sat out isn't ranked: only the teams that played it
    end["rank"] = end.groupby("season").rating.rank(ascending=False, method="min").astype(int)
    end["teams"] = end.season.map(end.groupby("season").size())
    end["top"] = end["rank"] <= end.teams.map(top_of)
    return end[cols].sort_values(["team", "season"]).reset_index(drop=True)


def name(first: str, last: str) -> str:
    """"the 2029–31 era" (or "the 2026/27–2027/28 era" when the season names aren't plain years)."""
    a, b = str(first), str(last)
    if a == b:
        return f"the {a} era"
    if a.isdigit() and b.isdigit() and len(a) == len(b) == 4:
        return f"the {a}–{b[2:] if a[:2] == b[:2] else b} era"
    return f"the {a}–{b} era"


def eras(career, section: str, team: str, ranks: pd.DataFrame | None = None) -> list[dict]:
    """The team's eras in this competition, oldest first."""
    r = season_ranks(career, section) if ranks is None else ranks
    r = r[r.team == team].sort_values("season")
    out, run = [], []
    for row in list(r.itertuples()) + [None]:
        if row is not None and row.top:
            run.append(row)
            continue
        if len(run) >= MIN_SEASONS:
            out.append(_era(career, section, team, run))
        run = []
    return out


def _era(career, section, team, run) -> dict:
    seasons = [x.season for x in run]
    m = career.matches
    ids = m[(m.section == section) & m.season.isin(seasons) & ((m.home == team) | (m.away == team))]
    res = ids[ids.result_type != "no result"]
    won = int((res.winner == team).sum())
    lost = int((res.loser == team).sum())
    others = len(res) - won - lost
    bat = career.batting[career.batting.match_id.isin(ids.match_id) & (career.batting.team == team)]
    bowl = career.bowling[career.bowling.match_id.isin(ids.match_id) & (career.bowling.team == team)]
    runs = bat.groupby("player").runs.sum().sort_values(ascending=False)
    wkts = bowl.groupby("player").wickets.sum().sort_values(ascending=False)
    best = max(run, key=lambda x: x.rating)
    return dict(name=name(seasons[0], seasons[-1]), first=str(seasons[0]), last=str(seasons[-1]), seasons=[str(s) for s in seasons],
                ranks=[dict(season=str(x.season), rank=int(x.rank), teams=int(x.teams), rating=round(float(x.rating)))
                       for x in run],
                matches=int(len(ids)), won=won, lost=lost, other=others,
                win_pct=round(won / len(res) * 100, 1) if len(res) else None,
                peak=round(float(best.rating)), peak_season=str(best.season),
                runs=[dict(player=p, value=int(v)) for p, v in runs.head(3).items() if v > 0],
                wickets=[dict(player=p, value=int(v)) for p, v in wkts.head(3).items() if v > 0])
