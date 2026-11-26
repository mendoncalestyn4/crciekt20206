"""Then and now (stage 5, your answers of 26 November): a team's latest season in a competition beside the same team 1,
3 or 5 seasons earlier (only those the career has, and only seasons the team played), side by side: results, batting,
bowling, the leading players, and who has come in and gone out of the side."""

from __future__ import annotations

AGO = (1, 3, 5)


def team_seasons(career, section: str, team: str) -> list:
    """The seasons this team played in this competition, oldest first."""
    m = career.matches[(career.matches.section == section) & ((career.matches.home == team) | (career.matches.away == team))]
    return sorted(m.season.unique())


def choices(career, section: str, team: str) -> list[tuple[int, object, object]]:
    """(seasons ago, then, now) for each of 1, 3 and 5 seasons ago that the career has: counted in the competition's
    own seasons, and only when the team played that season."""
    every = sorted(career.matches[career.matches.section == section].season.unique())
    mine = team_seasons(career, section, team)
    if not mine:
        return []
    now = mine[-1]
    i = every.index(now)
    return [(k, every[i - k], now) for k in AGO if i - k >= 0 and every[i - k] in set(mine)]


def season(career, section: str, team: str, s) -> dict:
    """One season of a team: results, batting and bowling as a side, the leading players and the players used."""
    m = career.matches
    g = m[(m.section == section) & (m.season == s) & ((m.home == team) | (m.away == team))]
    ids = set(g.match_id)
    done = g[g.result_type != "no result"]
    won, lost = int((done.winner == team).sum()), int((done.loser == team).sum())
    inn = career.innings[career.innings.match_id.isin(ids)]
    bat_i, bowl_i = inn[inn.team == team], inn[inn.opposition == team]
    rate = lambda d: (d[d.counted_in_balls.astype(bool)].runs.sum() * 6 / d[d.counted_in_balls.astype(bool)].balls.sum()  # noqa: E731
                      if d[d.counted_in_balls.astype(bool)].balls.sum() else None)
    per_wkt = lambda d: d.runs.sum() / d.wickets.sum() if d.wickets.sum() else None   # noqa: E731
    bat = career.batting[career.batting.match_id.isin(ids) & (career.batting.team == team)]
    bowl = career.bowling[career.bowling.match_id.isin(ids) & (career.bowling.team == team)]
    did = bat[bat.did_bat.astype(bool)]
    runs = did.groupby("player").runs.sum().sort_values(ascending=False)
    wkts = bowl.groupby("player").wickets.sum().sort_values(ascending=False)
    games = bat.groupby("player").match_id.nunique()
    return dict(season=str(s), matches=len(g), won=won, lost=lost, other=len(done) - won - lost,
                win_pct=won / len(done) * 100 if len(done) else None,
                bat_avg=per_wkt(bat_i), bat_rate=rate(bat_i), bowl_avg=per_wkt(bowl_i), bowl_rate=rate(bowl_i),
                highest=int(bat_i.runs.max()) if len(bat_i) else None, lowest_against=int(bowl_i.runs.min()) if len(bowl_i) else None,
                hundreds=int((did.runs >= 100).sum()), fifties=int(((did.runs >= 50) & (did.runs < 100)).sum()),
                five_fors=int((bowl.wickets >= 5).sum()),
                top_runs=[(p, int(v)) for p, v in runs.head(3).items() if v > 0],
                top_wkts=[(p, int(v)) for p, v in wkts.head(3).items() if v > 0],
                players=dict(games))


def compare(career, section: str, team: str, ago: int) -> dict | None:
    """The team's latest season against `ago` seasons earlier: both seasons, and the players who came in (played now,
    not then), went out (then, not now) and stayed, each with their games."""
    pick = [c for c in choices(career, section, team) if c[0] == ago]
    if not pick:
        return None
    _, then_s, now_s = pick[0]
    then, now = season(career, section, team, then_s), season(career, section, team, now_s)
    a, b = set(then["players"]), set(now["players"])
    order = lambda names, d: sorted(names, key=lambda p: (-d[p], p))   # noqa: E731
    return dict(ago=ago, then=then, now=now,
                came_in=[(p, now["players"][p]) for p in order(b - a, now["players"])],
                went_out=[(p, then["players"][p]) for p in order(a - b, then["players"])],
                stayed=[(p, then["players"][p], now["players"][p]) for p in order(a & b, now["players"])])
