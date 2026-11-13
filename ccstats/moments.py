"""Players at the moments that matter (the stage 2 fix round's picked ideas, 13 November):

- big-match players: each player in finals, semi-finals, qualifiers, eliminators and every other knockout, and in
  series deciders (level with one to play), against their ordinary games; shown once a player has 3 such games;
- record by country: each player's runs and wickets in each host (the home side's country for a national side, the
  home side's ground otherwise), neutral grounds a row of their own;
- bounce-back: how a player does in the game after a poor one (batting: a duck or under 10; bowling: no wicket for 30
  runs or more), against their usual; shown once they have had 3 poor games;
- danger men: a team's three players with the most impact points (the Season review's MVP points) in a season, each
  with their last five innings or spells.

Everything from the scorecards; each format and competition apart (the caller passes the matches of one)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import teamplay as TP

BIG_MIN = 3       # big games a player needs before their big-match record shows
BOUNCE_MIN = 3    # poor games a player needs before their bounce-back shows
LOW = 10          # under this (or a duck) is a poor innings
DEAR = 30         # no wicket for this many runs or more is a poor spell


def big_match_ids(career, ids) -> set:
    """The big games among these matches: every knockout (finals, semi-finals, qualifiers, eliminators, quarter-finals)
    and every series decider."""
    m = career.matches[career.matches.match_id.isin(ids)]
    big = set(m[m.knockout].match_id)
    s = TP.series_games(career, ids)
    if len(s):
        big |= set(s[s.decider].match_id)
    return big


def _bat(b: pd.DataFrame) -> dict:
    inns, runs, outs, balls = len(b), int(b.runs.sum()), int(b.out.sum()), int(b.balls.sum())
    return dict(innings=inns, runs=runs, outs=outs, average=runs / outs if outs else None,
                strike_rate=runs / balls * 100 if balls else None)


def _bowl(w: pd.DataFrame) -> dict:
    wk, runs, balls = int(w.wickets.sum()), int(w.runs.sum()), int(w.balls.sum())
    return dict(spells=len(w), wickets=wk, runs=runs, average=runs / wk if wk else None,
                economy=runs / balls * 6 if balls else None)


def big_match(career, ids, players=None, team: str = "", big: set | None = None) -> pd.DataFrame:
    """One row per player with BIG_MIN or more big games here: big games and ordinary games, batting and bowling in
    each (runs, average, strike rate; wickets, average, economy). `players` / `team` narrow it down; `big`, the big
    games if already worked out."""
    cols = ["player", "team", "big", "ordinary", "big_bat", "ord_bat", "big_bowl", "ord_bowl"]
    big = big_match_ids(career, ids) if big is None else big
    xi = career.batting[career.batting.match_id.isin(ids)]
    if team:
        xi = xi[xi.team == team]
    if players is not None:
        xi = xi[xi.player.isin(set(players))]
    rows = []
    for (p, t), g in xi.groupby(["player", "team"]):
        mids = set(g.match_id)
        b_ids = mids & big
        if len(b_ids) < BIG_MIN:
            continue
        o_ids = mids - big
        bat = g[g.did_bat]
        w = career.bowling[career.bowling.match_id.isin(mids) & (career.bowling.player == p) & (career.bowling.team == t)]
        rows.append(dict(player=p, team=t, big=len(b_ids), ordinary=len(o_ids),
                         big_bat=_bat(bat[bat.match_id.isin(b_ids)]), ord_bat=_bat(bat[bat.match_id.isin(o_ids)]),
                         big_bowl=_bowl(w[w.match_id.isin(b_ids)]), ord_bowl=_bowl(w[w.match_id.isin(o_ids)])))
    d = pd.DataFrame(rows, columns=cols)
    return d.sort_values(["big", "player"], ascending=[False, True]).reset_index(drop=True)


def host_of(career) -> pd.Series:
    """Match id -> where it was played: the home side (a national side is its country), or "" for a neutral ground."""
    m = career.matches
    return pd.Series(np.where(m.neutral.astype(bool), "", m.home), index=m.match_id)


def by_host(career, ids, players=None, team: str = "") -> pd.DataFrame:
    """One row per player and host: matches, batting and bowling there (host "" is neutral grounds), most matches
    first."""
    cols = ["player", "team", "host", "matches", "bat", "bowl"]
    xi = career.batting[career.batting.match_id.isin(ids)]
    if team:
        xi = xi[xi.team == team]
    if players is not None:
        xi = xi[xi.player.isin(set(players))]
    if xi.empty:
        return pd.DataFrame(columns=cols)
    host = host_of(career)
    xi = xi.assign(host=xi.match_id.map(host))
    w = career.bowling[career.bowling.match_id.isin(set(xi.match_id))]
    w = w.assign(host=w.match_id.map(host))
    rows = []
    for (p, t, h), g in xi.groupby(["player", "team", "host"]):
        ww = w[(w.player == p) & (w.team == t) & (w.host == h)]
        rows.append(dict(player=p, team=t, host=h, matches=g.match_id.nunique(), bat=_bat(g[g.did_bat]), bowl=_bowl(ww)))
    d = pd.DataFrame(rows, columns=cols)
    return d.sort_values(["player", "matches", "host"], ascending=[True, False, True]).reset_index(drop=True)


def bounce_back(career, ids, player: str) -> dict:
    """After a poor game (a duck or under 10 with the bat; no wicket for 30+ with the ball), the next game's figures
    against the player's usual. Each part shows from BOUNCE_MIN poor games, the next game being their next one here
    that they batted (or bowled) in."""
    m = career.matches.set_index("match_id")
    out = {}
    b = career.batting[career.batting.match_id.isin(ids) & (career.batting.player == player) & career.batting.did_bat]
    b = b.assign(date=b.match_id.map(m.date)).sort_values(["date", "match_id", "innings_no"]).reset_index(drop=True)
    poor = (b.runs < LOW) & b.out          # out for a duck or under 10 (a not-out 4* is no failure)
    after = b.loc[_next_game(b, poor)]
    out["bat"] = dict(poor=int(poor.sum()), followed=len(after), after=_bat(after), usual=_bat(b),
                      shown=len(after) >= BOUNCE_MIN,
                      games=[dict(id=r.match_id, runs=int(r.runs), out=bool(r.out)) for r in after.itertuples()])
    w = career.bowling[career.bowling.match_id.isin(ids) & (career.bowling.player == player) & (career.bowling.balls > 0)]
    w = w.assign(date=w.match_id.map(m.date)).sort_values(["date", "match_id", "innings_no"]).reset_index(drop=True)
    dear = (w.wickets == 0) & (w.runs >= DEAR)
    after = w.loc[_next_game(w, dear)]
    out["bowl"] = dict(poor=int(dear.sum()), followed=len(after), after=_bowl(after), usual=_bowl(w),
                       shown=len(after) >= BOUNCE_MIN,
                       games=[dict(id=r.match_id, wickets=int(r.wickets), runs=int(r.runs)) for r in after.itertuples()])
    return out


def _next_game(rows: pd.DataFrame, poor: pd.Series) -> list:
    """For each poor row (in played order), the first row of the next match after it (a Test's second innings is the
    same game, not the one after)."""
    mids = list(rows.match_id)
    out = []
    for i in rows.index[poor]:
        j = next((k for k in range(i + 1, len(rows)) if mids[k] != mids[i]), None)
        if j is not None and (not out or out[-1] != j):
            out.append(j)
    return out


def danger_men(career, section: str, season: str, team: str, n: int = 3) -> list[dict]:
    """The team's `n` players with the most impact points in this section and season (the MVP points of Season
    review), each with their points, matches, the side of the game the points came from, and their last five innings
    and spells in the section (to the end of that season)."""
    from .mvp import season_mvp
    mv = season_mvp(career, section, season)
    mv = mv[mv.team == team].head(n)
    if mv.empty:
        return []
    m = career.matches
    sec = m[m.section == section]
    end = sec[sec.season == season].date.max()
    ids = set(sec[sec.date <= end].match_id)
    date = m.set_index("match_id").date
    opp_of = {r.match_id: (r.away if r.home == team else r.home) for r in sec.itertuples()}
    out = []
    for r in mv.itertuples():
        b = career.batting[career.batting.match_id.isin(ids) & (career.batting.player == r.player)
                           & (career.batting.team == team) & career.batting.did_bat]
        b = b.assign(date=b.match_id.map(date)).sort_values(["date", "match_id", "innings_no"]).tail(5)
        w = career.bowling[career.bowling.match_id.isin(ids) & (career.bowling.player == r.player)
                           & (career.bowling.team == team) & (career.bowling.balls > 0)]
        w = w.assign(date=w.match_id.map(date)).sort_values(["date", "match_id", "innings_no"]).tail(5)
        role = "bat" if r.batting >= 2 * max(r.bowling, 0) else "bowl" if r.bowling >= 2 * max(r.batting, 0) else "both"
        out.append(dict(player=r.player, points=float(r.points), matches=int(r.matches), batting=float(r.batting),
                        bowling=float(r.bowling), fielding=float(r.fielding), role=role,
                        innings=[dict(id=x.match_id, date=x.date, opp=opp_of.get(x.match_id, ""), runs=int(x.runs),
                                      balls=int(x.balls), out=bool(x.out)) for x in b.itertuples()],
                        spells=[dict(id=x.match_id, date=x.date, opp=opp_of.get(x.match_id, ""), wickets=int(x.wickets),
                                     runs=int(x.runs), balls=int(x.balls)) for x in w.itertuples()]))
    return out
