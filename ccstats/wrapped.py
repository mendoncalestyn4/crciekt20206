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
    tm = A.team_matches(career, ids, team)
    out: dict = dict(team=team, section=section, season=str(season), matches=len(tm))
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

    sec_ids = m[m.section == section].match_id
    rt = X.rate(career, sec_ids) if ratings is None else ratings
    bm = rt[rt.match_id.isin(mids)].sort_values(["rating", "date"], ascending=[False, False])
    if len(bm):
        b = bm.iloc[0]
        out["game"] = dict(teams=f"{b.home} v {b.away}", result=b.result, rating=float(b.rating), why=b.why,
                           date=_date(b.date), id=b.match_id, rank=int(b["rank"]), of=int(b["of"]))

    mvp = MV.season_mvp(career, section, season, "impact")
    mvp = mvp[mvp.team == team]
    if len(mvp):
        p = mvp.iloc[0]
        out["player"] = dict(player=p.player, points=float(p.points), matches=int(p.matches), batting=float(p.batting),
                             bowling=float(p.bowling), fielding=float(p.fielding))
    return out
