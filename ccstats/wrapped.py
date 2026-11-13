"""Your season, wrapped: one team's season in one competition (one format: Tests, ODIs and T20Is apart) as ten
slides: the record, the top run-scorer and wicket-taker, the highest score, the best bowling, the biggest stand, the
longest winning run, the biggest win, the best game and the player of the season. Every figure is the team's own in
these matches, from the scorecards as printed."""

from __future__ import annotations

import pandas as pd

from . import analysis as A
from . import excitement as X
from . import mvp as MV
from . import partnerships as PS

SLIDES = ["record", "runs", "wickets", "score", "bowling", "stand", "streak", "win", "game", "player"]


def _date(d) -> str:
    return f"{d:%d %b %Y}"


def season_wrapped(career, section: str, season, team: str, ratings: pd.DataFrame | None = None) -> dict:
    """{slide name: dict or None (nothing to show)} for `team` in `section` and `season`, plus matches. The best game
    goes by the match excitement rating (ccstats/excitement.py, the one the Matches pages use); `ratings`, the section's
    ratings if already worked out."""
    m = career.matches
    ids = set(m[(m.section == section) & (m.season == season)].match_id)
    rt = X.rate(career, m[m.section == section].match_id) if ratings is None else ratings
    mvp = MV.season_mvp(career, section, season, "impact")
    return _wrap(career, ids, team, rt, mvp[mvp.team == team], dict(section=section, season=str(season)))


def whole_season_wrapped(career, year: int, team: str, ratings_for=None) -> dict:
    """The whole April-to-March season for `team`, every format together (the owner's exception to "formats never
    mixed", for this view only): runs, wickets and records added up across Tests, ODIs, T20Is and any domestic or
    franchise competition it played; the best game on each competition's own excitement rating; the player of the
    season by impact points added up over every competition. `ratings_for(section)`: a section's ratings if kept."""
    from .seasonal import april_seasons
    m = career.matches
    mine = m[(m.home == team) | (m.away == team)]
    year_of = april_seasons(m)
    mine = mine[mine.match_id.map(year_of) == year]
    ids = set(mine.match_id)
    rate = ratings_for or (lambda sec: X.rate(career, m[m.section == sec].match_id))
    rt = pd.concat([rate(sec) for sec in sorted(mine.section.unique())]) if len(mine) else pd.DataFrame(columns=X.RATING_COLUMNS)
    # impact points game by game (each competition's own averages), only this season's games: a season label isn't
    # always April to March (Tests "2032" runs January to December)
    from .playerdeep import match_impact
    parts = []
    for sec in sorted(mine.section.unique()):
        imp = match_impact(career, m[m.section == sec].match_id)
        parts.append(imp[imp.match_id.isin(ids) & (imp.team == team)])
    imp = pd.concat(parts) if parts else pd.DataFrame(columns=["player", "team", "match_id", "bat", "bowl", "field"])
    mvp = pd.DataFrame(columns=["player", "team", "matches", "batting", "bowling", "fielding", "points"])
    if len(imp):
        xi = career.batting[career.batting.match_id.isin(ids) & (career.batting.team == team)]
        played = xi.groupby("player").match_id.nunique()
        g = imp.groupby("player")[["bat", "bowl", "field"]].sum()
        mvp = pd.DataFrame({"player": played.index, "team": team, "matches": played.values})
        mvp = mvp.assign(batting=mvp.player.map(g.bat).fillna(0.0), bowling=mvp.player.map(g.bowl).fillna(0.0),
                         fielding=mvp.player.map(g.field).fillna(0.0))
        mvp["points"] = mvp.batting + mvp.bowling + mvp.fielding
        mvp = mvp.sort_values(["points", "player"], ascending=[False, True]).reset_index(drop=True)
    return _wrap(career, ids, team, rt, mvp, dict(section="", season=f"{year}–{str(year + 1)[-2:]}",
                                                  sections=sorted(mine.section.unique())))


def _wrap(career, ids: set, team: str, rt: pd.DataFrame, mvp: pd.DataFrame, base: dict) -> dict:
    """The slides for these matches (one competition's season, or a whole season of every format)."""
    m = career.matches
    tm = A.team_matches(career, ids, team)
    out: dict = dict(team=team, matches=len(tm), **base)
    if tm.empty:
        return out
    mids = set(tm.match_id)
    by_id = tm.set_index("match_id")
    rec = A.team_record(tm)
    out["record"] = dict(played=rec["played"], won=rec["won"], lost=rec["lost"], drawn=rec["drawn"], tied=rec["tied"],
                         no_result=rec["no_result"], win_pct=rec["win_pct"])

    bat = career.batting[career.batting.match_id.isin(mids) & (career.batting.team == team) & career.batting.did_bat]
    if len(bat):
        g = bat.groupby("player").agg(runs=("runs", "sum"), innings=("runs", "size"), outs=("out", "sum"),
                                      best=("runs", "max")).reset_index()
        g = g.sort_values(["runs", "innings", "player"], ascending=[False, True, True])
        r = g.iloc[0]
        if r.runs > 0:
            out["runs"] = dict(player=r.player, runs=int(r.runs), innings=int(r.innings),
                               average=float(r.runs / r.outs) if r.outs else None, best=int(r.best))
        hs = bat.assign(notout=~bat.out.astype(bool), date=bat.match_id.map(by_id.date))
        hs = hs.sort_values(["runs", "notout", "balls", "date"], ascending=[False, False, True, True]).iloc[0]
        if hs.runs > 0:
            out["score"] = dict(player=hs.player, runs=int(hs.runs), notout=bool(hs.notout), balls=int(hs.balls),
                                against=hs.opposition, date=_date(hs.date), id=hs.match_id)

    bowl = career.bowling[career.bowling.match_id.isin(mids) & (career.bowling.team == team)]
    if len(bowl) and bowl.wickets.sum() > 0:
        g = bowl.groupby("player").agg(wickets=("wickets", "sum"), runs=("runs", "sum"), balls=("balls", "sum")).reset_index()
        g = g.sort_values(["wickets", "runs", "player"], ascending=[False, True, True])
        r = g.iloc[0]
        out["wickets"] = dict(player=r.player, wickets=int(r.wickets), average=float(r.runs / r.wickets),
                              economy=float(r.runs / r.balls * 6) if r.balls else None)
        bb = bowl.assign(date=bowl.match_id.map(by_id.date))
        bb = bb.sort_values(["wickets", "runs", "balls", "date"], ascending=[False, True, True, True]).iloc[0]
        out["bowling"] = dict(player=bb.player, wickets=int(bb.wickets), runs=int(bb.runs), against=bb.opposition,
                              date=_date(bb.date), id=bb.match_id)

    st = PS.stands(career, mids)
    st = st[st.team == team]
    if len(st) and st.runs.max() > 0:
        s = st.assign(date=st.match_id.map(by_id.date)).sort_values(["runs", "date"], ascending=[False, True]).iloc[0]
        out["stand"] = dict(runs=int(s.runs), wicket=int(s.wicket), unbroken=bool(s.unbroken),
                            pair=PS.pair_name(s), against=s.opposition, date=_date(s.date), id=s.match_id)

    # the longest unbroken run of wins, in date order (any other result ends it), with when it began and ended
    best, run, start = (0, None, None), 0, None
    for r in tm.itertuples():
        if r.outcome == "W":
            run, start = run + 1, start if run else r.date
            if run > best[0]:
                best = (run, start, r.date)
        else:
            run = 0
    if best[0]:
        out["streak"] = dict(wins=best[0], start=_date(best[1]), end=_date(best[2]))

    won = tm[tm.outcome == "W"]
    if len(won):
        inns = won[won.innings_win.fillna(False).astype(bool)]
        runs_ = won[won.margin_runs.notna() & (won.margin_runs > 0)]
        wkts_ = won[won.margin_wickets.notna() & (won.margin_wickets > 0)]
        pick = None
        if len(inns):
            pick = inns.sort_values(["margin_runs", "date"], ascending=[False, True]).iloc[0]
        elif len(runs_):
            pick = runs_.sort_values(["margin_runs", "date"], ascending=[False, True]).iloc[0]
        elif len(wkts_):
            pick = wkts_.sort_values(["margin_wickets", "date"], ascending=[False, True]).iloc[0]
        if pick is not None:
            out["win"] = dict(result=pick.result, against=pick.opponent, date=_date(pick.date), id=pick.match_id)
            if pick.match_id not in set(wkts_.match_id) and len(wkts_):
                w = wkts_.sort_values(["margin_wickets", "date"], ascending=[False, True]).iloc[0]
                out["win"]["also"] = dict(result=w.result, against=w.opponent, date=_date(w.date), id=w.match_id)

    bm = rt[rt.match_id.isin(mids)].sort_values(["rating", "date"], ascending=[False, False])
    if len(bm):
        b = bm.iloc[0]
        out["game"] = dict(teams=f"{b.home} v {b.away}", result=b.result, rating=float(b.rating), why=b.why,
                           date=_date(b.date), id=b.match_id, rank=int(b["rank"]), of=int(b["of"]))

    if len(mvp):
        p = mvp.iloc[0]
        out["player"] = dict(player=p.player, points=float(p.points), matches=int(p.matches), batting=float(p.batting),
                             bowling=float(p.bowling), fielding=float(p.fielding))
    return out
