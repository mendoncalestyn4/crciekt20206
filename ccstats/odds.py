"""Title and playoff odds: the rest of a league season played out thousands of times.

Each remaining league game is decided by the two sides' current team ratings (the Elo on the Rankings page), with
the competition's own share of draws (first-class) or no results (rain, limited overs).  The scorecards don't hold
the fixture list, so the games still to play are worked out from how many league games each side plays in a season
(an earlier season of the same competition, or the usual shape) and who has met whom least so far.  Points follow
the competition's points table, ties on points go to more wins and then net run rate (which moves with each result),
and the knockouts are played the way the competition plays them (the IPL's Qualifier 1 / Eliminator / Qualifier 2,
The Hundred's eliminator, the Blast's quarter-finals across the two groups).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

ODDS_COLUMNS = ["group", "team", "played", "points", "left", "rating", "top", "playoffs", "title"]


def _rating_at(career, section: str, before: pd.Timestamp | None, elo: tuple | None = None) -> dict[str, float]:
    """Each side's team rating (Elo) after its last match before `before` (all matches when None).  `elo`: the
    section's (table, history) from rankings.team_elo, when already worked out."""
    from .rankings import ELO_START, team_elo
    table, hist = elo if elo is not None else team_elo(career, section)
    if before is None:
        return dict(zip(table.team, table.elo))
    h = hist[hist.date < before].sort_values("date")
    out = h.groupby("team").after.last().to_dict()
    for t in table.team:
        out.setdefault(t, ELO_START)
    return out


def _fixtures_left(teams: list[str], played: dict[str, int], games: int, met: dict[tuple, int]) -> list[tuple[str, str]]:
    """The league games still to play: each side plays `games` in all, against the sides it has met least so far."""
    left = {t: max(games - played.get(t, 0), 0) for t in teams}
    met = dict(met)
    out = []
    while True:
        open_ = [t for t in teams if left[t] > 0]
        if len(open_) < 2:
            break
        a = max(open_, key=lambda t: (left[t], t))
        rest = [t for t in open_ if t != a]
        b = min(rest, key=lambda t: (met.get(tuple(sorted((a, t))), 0), -left[t], t))
        out.append((a, b))
        left[a] -= 1
        left[b] -= 1
        k = tuple(sorted((a, b)))
        met[k] = met.get(k, 0) + 1
    return out


def _beats(rng, elo: np.ndarray, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Winners of knockout games between side indices a and b (one per simulation)."""
    p = 1 / (1 + 10 ** ((elo[b] - elo[a]) / 400))
    return np.where(rng.random(len(a)) < p, a, b)


def _seeded(order: list[tuple[np.ndarray, np.ndarray]], places: int, extra: int) -> list[np.ndarray]:
    """The knockout field in seed order, one array of side indices per seed: every group's winners (best record
    first), then the runners-up …, then the best `extra` of the next-placed sides.  order[g] = (sides in finishing
    order, their table keys) for group g, one row per simulation."""
    field = []
    for pos in range(places + (1 if extra else 0)):
        cols = [(o[:, pos], k[:, pos]) for o, k in order if o.shape[1] > pos]
        if not cols:
            break
        sides, keys = np.stack([c[0] for c in cols], axis=1), np.stack([c[1] for c in cols], axis=1)
        by = np.argsort(-keys, axis=1)
        sides = np.take_along_axis(sides, by, axis=1)
        take = sides.shape[1] if pos < places else min(extra, sides.shape[1])
        field += [sides[:, j] for j in range(take)]
    return field


def _title(rng, elo: np.ndarray, order: list[tuple[np.ndarray, np.ndarray]], places: int, extra: int = 0) -> np.ndarray:
    """The champion in each simulation (see _seeded for `order`)."""
    q = [o[:, :places] for o, _ in order]  # qualifiers, best first
    if len(order) == 1:
        s = q[0]
        if places == 1:
            return s[:, 0]
        if places == 2:
            return _beats(rng, elo, s[:, 0], s[:, 1])
        if places == 3:  # The Hundred: 2nd v 3rd, the winner meets the 1st in the final
            return _beats(rng, elo, s[:, 0], _beats(rng, elo, s[:, 1], s[:, 2]))
        if places == 4:  # page playoffs (IPL): Q1 1v2, Eliminator 3v4, Q2 loser of Q1 v Eliminator winner, final
            q1 = _beats(rng, elo, s[:, 0], s[:, 1])
            q1_loser = np.where(q1 == s[:, 0], s[:, 1], s[:, 0])
            q2 = _beats(rng, elo, q1_loser, _beats(rng, elo, s[:, 2], s[:, 3]))
            return _beats(rng, elo, q1, q2)
    if len(order) == 2 and places in (1, 2, 4) and not extra:
        a, b = q
        if places == 1:
            return _beats(rng, elo, a[:, 0], b[:, 0])
        if places == 2:  # semi-finals across the groups
            return _beats(rng, elo, _beats(rng, elo, a[:, 0], b[:, 1]), _beats(rng, elo, b[:, 0], a[:, 1]))
        qf = [_beats(rng, elo, a[:, 0], b[:, 3]), _beats(rng, elo, b[:, 1], a[:, 2]),  # quarter-finals across groups
              _beats(rng, elo, b[:, 0], a[:, 3]), _beats(rng, elo, a[:, 1], b[:, 2])]
        return _beats(rng, elo, _beats(rng, elo, qf[0], qf[1]), _beats(rng, elo, qf[2], qf[3]))
    # anything else (the Blast's three groups and two best thirds): seeded single elimination, best v worst, the top
    # seeds getting byes when the field isn't a power of two
    field = _seeded(order, places, extra)
    while len(field) > 1:
        size = 1 << (len(field) - 1).bit_length()
        byes = size - len(field)
        nxt = field[:byes]
        rest = field[byes:]
        nxt += [_beats(rng, elo, rest[i], rest[-1 - i]) for i in range(len(rest) // 2)]
        field = nxt
    return field[0]


class _Season:
    """What the odds need about one competition-season's league stage, worked out once: each side's points, wins,
    defeats and net run rate figures from each match (cumulated up to any date), the groups, and the ratings."""

    def __init__(self, career, event: str, season: str, games: int | None, places: int | None,
                 extra: int | None = None):
        from .analysis import nrr_innings
        from .rankings import team_elo
        from .tables import LIMITED, _groups, points_rule
        from .teamplay import has_knockouts, qualification_defaults
        self.m = career.matches[(career.matches.event == event) & (career.matches.season == season)]
        self.league = self.m[~self.m.knockout].sort_values(["date", "match_id"])
        self.ok = not self.league.empty
        if not self.ok:
            return
        r0 = self.league.iloc[0]
        self.comp, self.fmt, self.section = r0.competition, r0.format, r0.section
        self.limited = self.fmt in LIMITED
        _, pts = points_rule(self.comp, self.fmt)
        self.by_points = bool(pts)
        self.win_pts = pts.get("win", 1) if pts else 1
        self.other_pts = (pts.get("nr", 0) if self.limited else pts.get("draw", 0)) if pts else 0
        d = qualification_defaults(career, event, season)
        self.games = int(games or d["games"])
        self.knockouts = has_knockouts(career, event)
        self.groups = [(label, sorted(members)) for label, _, members in _groups(self.league)]
        self.places = int(places or d["places"]) if self.knockouts else 1
        self.extra = (int(d.get("extra", 0) if extra is None else extra)
                      if self.knockouts and len(self.groups) > 1 else 0)
        sec = career.matches[career.matches.section == self.section]
        self.other = float((sec.result_type == ("no result" if self.limited else "draw")).mean()) if len(sec) else 0.0
        self.elo = team_elo(career, self.section)
        # each side's share of each league match, as the league table counts it (tables.league_tables)
        inn = career.innings[career.innings.match_id.isin(self.league.match_id)]
        first = inn[inn.team_innings == 1].groupby(["match_id", "team"]).runs.sum()
        nrr = nrr_innings(career, self.league.match_id) if self.limited else pd.DataFrame(columns=["match_id", "team"])
        nf = nrr.groupby(["match_id", "team"])[["runs", "balls"]].sum() if len(nrr) else None
        rows = []
        for r in self.league.itertuples():
            so = self.limited and r.result_type == "tie" and r.tiebreak_winner != ""
            for team, opp in ((r.home, r.away), (r.away, r.home)):
                win = r.winner == team or (so and r.tiebreak_winner == team)
                loss = r.winner == opp or (so and r.tiebreak_winner == opp)
                p = 0.0
                if pts:
                    if win:
                        big = "bonus_win" in pts and (bool(r.innings_win) or r.margin_wickets == 10)
                        p = pts["bonus_win"] if big else pts["win"]
                    elif r.result_type == "tie" and not so:
                        p = pts["tie"]
                    elif r.result_type == "no result":
                        p = pts["nr"]
                    elif r.result_type == "draw":
                        lead = first.get((r.match_id, team), np.nan) > first.get((r.match_id, opp), np.nan)
                        p = pts.get("draw_lead", pts["draw"]) if lead else pts["draw"]
                f = nf.loc[(r.match_id, team)] if nf is not None and (r.match_id, team) in nf.index else None
                a = nf.loc[(r.match_id, opp)] if nf is not None and (r.match_id, opp) in nf.index else None
                rows.append((r.match_id, r.date, team, opp, 1, int(win), int(loss), p,
                             float(f.runs) if f is not None else 0.0, float(f.balls) if f is not None else 0.0,
                             float(a.runs) if a is not None else 0.0, float(a.balls) if a is not None else 0.0))
        self.parts = pd.DataFrame(rows, columns=["match_id", "date", "team", "opponent", "played", "won", "lost",
                                                 "points", "rf", "bf", "ra", "ba"])

    def table(self, before: pd.Timestamp | None = None) -> pd.DataFrame:
        """The league table (every side in its group, best first) from the league games before `before`."""
        p = self.parts if before is None else self.parts[self.parts.date < before]
        s = p.groupby("team")[["played", "won", "lost", "points", "rf", "bf", "ra", "ba"]].sum()
        rows = []
        for label, members in self.groups:
            for t in members:
                x = s.loc[t] if t in s.index else None
                nrr = ((x.rf / x.bf - x.ra / x.ba) * 6 if x is not None and x.bf and x.ba else 0.0) if self.limited else 0.0
                rows.append(dict(group=label, team=t, played=int(x.played) if x is not None else 0,
                                 won=int(x.won) if x is not None else 0, lost=int(x.lost) if x is not None else 0,
                                 points=float(x.points) if x is not None else 0.0, nrr=nrr))
        return pd.DataFrame(rows, columns=["group", "team", "played", "won", "lost", "points", "nrr"])


def season_odds(career, event: str, season: str, games: int | None = None, places: int | None = None,
                sims: int = 4000, seed: int = 2026, before: pd.Timestamp | None = None, _s: _Season | None = None,
                extra: int | None = None) -> dict:
    """{table: one row per side (ODDS_COLUMNS, chances in %), knockouts, games, places, groups, state} for the
    league stage of one competition-season.  `before`: the odds as they stood before that date's games.
    state is "open" (odds worked out), "league over" (every league game played), or "none" (no league)."""
    S = _s or _Season(career, event, season, games, places, extra)
    empty = dict(table=pd.DataFrame(columns=ODDS_COLUMNS), knockouts=False, games=0, places=0, extra=0, groups=0,
                 state="none")
    if not S.ok:
        return empty
    league = S.league if before is None else S.league[S.league.date < before]
    if league.empty or not S.groups:
        return empty
    base = dict(empty, knockouts=S.knockouts, games=S.games, places=S.places, extra=S.extra, groups=len(S.groups))
    if before is None and S.m.knockout.any():
        return dict(base, state="league over")
    rating = _rating_at(career, S.section, before, S.elo)
    met: dict[tuple, int] = {}
    for h, a in zip(league.home, league.away):
        k = tuple(sorted((h, a)))
        met[k] = met.get(k, 0) + 1
    standing = S.table(before)
    rng = np.random.default_rng(seed)
    all_teams = list(standing.team)
    idx = {t: i for i, t in enumerate(all_teams)}
    elo = np.array([rating.get(t, 1500.0) for t in all_teams])
    orders, rows, any_left = [], [], False
    through = np.zeros((sims, len(all_teams)), dtype=bool)
    for label, tb in standing.groupby("group", sort=False):
        teams = list(tb.team)
        n = len(teams)
        base_pts = (tb.points if S.by_points else tb.won).to_numpy(dtype=float)
        played = dict(zip(tb.team, tb.played))
        fx = _fixtures_left(teams, played, S.games, met)
        any_left |= bool(fx)
        pnt = np.tile(base_pts, (sims, 1))
        wins = np.tile(tb.won.to_numpy(dtype=float), (sims, 1))
        lost = np.tile(tb.lost.to_numpy(dtype=float), (sims, 1))
        nrr = np.tile(tb.nrr.to_numpy(dtype=float), (sims, 1)) + rng.normal(0, 0.05, (sims, n))
        loc = {t: i for i, t in enumerate(teams)}
        for a, b in fx:
            ia, ib = loc[a], loc[b]
            pa = (1 - S.other) / (1 + 10 ** ((rating.get(b, 1500.0) - rating.get(a, 1500.0)) / 400))
            u = rng.random(sims)
            a_won, b_won = u < pa, (u >= pa) & (u < 1 - S.other)
            neither = ~(a_won | b_won)
            win_pts = S.win_pts if S.by_points else 1
            other_pts = S.other_pts if S.by_points else 0
            pnt[:, ia] += np.where(a_won, win_pts, np.where(neither, other_pts, 0))
            pnt[:, ib] += np.where(b_won, win_pts, np.where(neither, other_pts, 0))
            wins[:, ia] += a_won
            wins[:, ib] += b_won
            lost[:, ia] += b_won
            lost[:, ib] += a_won
            if S.limited:  # a win lifts net run rate a little, a defeat drops it
                swing = rng.normal(0.25, 0.1, sims) / max(S.games, 1) * 4
                nrr[:, ia] += np.where(a_won, swing, np.where(b_won, -swing, 0))
                nrr[:, ib] += np.where(b_won, swing, np.where(a_won, -swing, 0))
        # the table's order: points (or wins), then wins, then net run rate (limited overs), then fewest defeats
        key = pnt * 1e9 + wins * 1e6 + (np.clip(nrr, -400, 400) * 1e3 if S.limited else 0) - lost \
            + rng.random((sims, n)) * 1e-3
        order_local = np.argsort(-key, axis=1)
        orders.append((np.array([idx[t] for t in teams])[order_local] if n else order_local,
                       np.take_along_axis(key, order_local, axis=1)))
        rank = np.empty_like(order_local)
        rank[np.arange(sims)[:, None], order_local] = np.arange(n)[None, :]
        for i, t in enumerate(teams):
            through[:, idx[t]] = rank[:, i] < S.places
            rows.append(dict(group=label, team=t, played=int(played[t]), points=float(base_pts[i]),
                             left=sum(1 for p in fx if t in p), rating=float(elo[idx[t]]),
                             top=float((rank[:, i] == 0).mean() * 100), playoffs=np.nan, title=np.nan))
    if S.extra:  # the best of the next-placed sides across the groups go through too
        for side in _seeded(orders, S.places, S.extra)[S.places * len(orders):]:
            through[np.arange(sims), side] = True
    table = pd.DataFrame(rows, columns=ODDS_COLUMNS)
    if S.knockouts:
        table["playoffs"] = [float(through[:, idx[t]].mean() * 100) for t in table.team]
    if S.knockouts and all(o.shape[1] >= S.places for o, _ in orders):
        champ = _title(rng, elo, orders, S.places, S.extra)
        counts = np.bincount(champ, minlength=len(all_teams)) / sims * 100
        table["title"] = [counts[idx[t]] for t in table.team]
    elif not S.knockouts:
        table["title"] = table.top  # no knockouts: the top of the table are the champions
    return dict(base, table=table, state="open" if any_left else "league over")


def odds_with_change(career, event: str, season: str, games: int | None = None, places: int | None = None,
                     sims: int = 4000, extra: int | None = None) -> dict:
    """season_odds now, plus each side's change since before the latest day's league games (in points of %)."""
    S = _Season(career, event, season, games, places, extra)
    now = season_odds(career, event, season, games, places, sims, _s=S)
    if now["state"] != "open":
        return dict(now, change=None)
    days = sorted(S.league.date.unique())
    if len(days) < 2:
        return dict(now, change=None)
    then = season_odds(career, event, season, games, places, sims, before=pd.Timestamp(days[-1]), _s=S)
    if then["table"].empty:
        return dict(now, change=None)
    t0 = then["table"].set_index("team")
    col = "title" if now["table"].title.notna().any() else "top"
    change = {t: v - t0[col].get(t, np.nan) for t, v in zip(now["table"].team, now["table"][col])}
    return dict(now, change=change, change_of=col, since=pd.Timestamp(days[-1]))


def odds_history(career, event: str, season: str, games: int | None = None, places: int | None = None,
                 sims: int = 1500, extra: int | None = None) -> pd.DataFrame:
    """Each side's chances after every day of league games (date, team, top, playoffs, title), from the first day
    to now, with the champion (or league winner) at 100% once the season is decided."""
    cols = ["date", "team", "top", "playoffs", "title"]
    S = _Season(career, event, season, games, places, extra)
    if not S.ok:
        return pd.DataFrame(columns=cols)
    days = sorted(S.league.date.unique())
    out = []
    for i, day in enumerate(days):
        nxt = pd.Timestamp(days[i + 1]) if i + 1 < len(days) else pd.Timestamp(day) + pd.Timedelta(days=1)
        r = season_odds(career, event, season, games, places, sims, before=nxt, _s=S)
        if r["state"] == "none":
            continue
        for row in r["table"].itertuples():
            out.append((pd.Timestamp(day), row.team, row.top, row.playoffs, row.title))
    # the season decided: the champion (or the league winner) at 100%
    from .extras import honours
    h = honours(career)
    h = h[(h.section == event) & (h.season == season) & ~h.how.str.contains("so far")]
    if len(h) and out:
        champs = set(h.champion_teams.iloc[0])
        end = S.m.date.max() + pd.Timedelta(days=1)
        last_day = max(o[0] for o in out)
        for o in [o for o in out if o[0] == last_day]:
            won = o[1] in champs
            out.append((end, o[1], 100.0 if won else 0.0, o[3], 100.0 if won else 0.0))
    return pd.DataFrame(out, columns=cols)
