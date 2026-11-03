"""Reports on your own side: after every match, who was best and who did least; after a series, a review of every
player with selection advice ("use him more", "think about dropping him") set against their own record before it,
and the series set against your previous series in the format.

The measure is the match impact used on the Player page and for the season MVP: runs (with a strike-rate part in
white-ball cricket), wickets worth the section's runs per wicket (with an economy part in white-ball cricket) and a
little for catches and stumpings."""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import fixtures as FX
from .playerdeep import match_impact


def _line(r) -> str:
    """'87 (64) · 2/31' for one player in one match."""
    bits = []
    if r.balls_faced > 0 or r.runs > 0:
        bits.append(f"{int(r.runs)}{'' if r.out else '*'} ({int(r.balls_faced)})")
    if r.balls_bowled > 0:
        bits.append(f"{int(r.wickets)}/{int(r.conceded)} ({r.balls_bowled // 6}.{r.balls_bowled % 6} ov)")
    if r.dismissals:
        bits.append(f"{int(r.dismissals)} ct/st")
    return " · ".join(bits) or "did not bat or bowl"


def _figures(career, ids, team: str) -> pd.DataFrame:
    """Each of the team's players in these matches: match impact, with runs, balls, outs, wickets, balls bowled."""
    m = career.matches[career.matches.match_id.isin(ids)]
    if m.empty:
        return pd.DataFrame()
    fmt = m.format.iloc[0]
    base = FX.format_ids(career, team, fmt)  # the section's averages are the yardstick
    imp = match_impact(career, base)
    d = imp[imp.match_id.isin(ids) & (imp.team == team)].copy()
    b = career.batting[career.batting.match_id.isin(ids) & (career.batting.team == team) & career.batting.did_bat]
    bat = b.groupby(["match_id", "player"]).agg(balls_faced=("balls", "sum"), out=("out", "max")).reset_index()
    w = career.bowling[career.bowling.match_id.isin(ids) & (career.bowling.team == team)]
    bowl = w.groupby(["match_id", "player"]).agg(balls_bowled=("balls", "sum")).reset_index()
    d = d.merge(bat, on=["match_id", "player"], how="left").merge(bowl, on=["match_id", "player"], how="left")
    d = d.fillna({"balls_faced": 0, "balls_bowled": 0})
    d["balls_faced"] = d.balls_faced.astype(int)
    d["balls_bowled"] = d.balls_bowled.astype(int)
    d["out"] = d.out.eq(True)   # didn't bat: not out (eq, not fillna: pandas warns about filling a mixed column)
    return d


def match_card(career, match_id: str, team: str, top: int = 3) -> dict | None:
    """After one of the team's matches: its best players (most impact) and the ones who did least (of those who
    batted in the top seven or bowled), each with their figures. None if the team didn't play in it."""
    d = _figures(career, [match_id], team)
    if d.empty:
        return None
    d = d.sort_values("impact", ascending=False)
    best = d.head(top)
    # who did least: batted (top seven) or bowled, and not already among the best
    order = career.batting[(career.batting.match_id == match_id) & (career.batting.team == team)]
    top7 = set(order[order.position <= 7].player)
    used = d[(d.player.isin(top7) | (d.balls_bowled > 0)) & ~d.player.isin(best.player)]
    worst = used.sort_values("impact").head(min(top - 1, max(len(used), 0)))
    return dict(best=[(r.player, _line(r), float(r.impact)) for r in best.itertuples()],
                worst=[(r.player, _line(r), float(r.impact)) for r in worst.itertuples()],
                kind=d.attrs.get("kind", ""))


def series_review(career, match_ids, team: str, earlier: int = 3) -> dict | None:
    """After a series (or any run of the team's matches in one format): every player who played in it with their
    series figures, their usual figures before it (the same format, all earlier matches), and advice:
    - "Use more": among the side's best by impact a match in the series and above their own usual level
    - "Think about dropping": played twice or more, among the side's lowest by impact a match and below their usual
      level (a batter averaging under 20 in it, or a bowler conceding more per wicket than usual)
    and the series against the side's previous `earlier` series in the format (win %, runs per wicket made and
    conceded)."""
    m = career.matches
    ids = list(m[m.match_id.isin(match_ids)].sort_values("date").match_id)
    if not ids:
        return None
    fmt = m.set_index("match_id").format[ids[0]]
    start = m.set_index("match_id").date[ids[0]]
    d = _figures(career, ids, team)
    if d.empty:
        return None
    per = d.groupby("player").agg(games=("match_id", "nunique"), impact=("impact", "sum"), runs=("runs", "sum"),
                                  outs=("out", "sum"), balls_faced=("balls_faced", "sum"), wickets=("wickets", "sum"),
                                  conceded=("conceded", "sum"), balls_bowled=("balls_bowled", "sum")).reset_index()
    per["per_game"] = per.impact / per.games
    per["avg"] = per.runs / per.outs.replace(0, np.nan)
    per["bowl_avg"] = per.conceded / per.wickets.replace(0, np.nan)
    # their usual level: the same format before this series
    before_ids = m[(m.format == fmt) & (m.date < start) & ((m.home == team) | (m.away == team))].match_id
    usual = _figures(career, before_ids, team)
    if len(usual):
        u = usual.groupby("player").agg(u_games=("match_id", "nunique"), u_impact=("impact", "sum"),
                                        u_runs=("runs", "sum"), u_outs=("out", "sum"), u_wkts=("wickets", "sum"),
                                        u_conceded=("conceded", "sum")).reset_index()
        u["u_per_game"] = u.u_impact / u.u_games
        u["u_avg"] = u.u_runs / u.u_outs.replace(0, np.nan)
        u["u_bowl_avg"] = u.u_conceded / u.u_wkts.replace(0, np.nan)
        per = per.merge(u, on="player", how="left")
    for c in ("u_games", "u_per_game", "u_avg", "u_bowl_avg"):
        if c not in per:
            per[c] = np.nan
    hi, lo = per.per_game.quantile(0.67), per.per_game.quantile(0.33)

    def verdict(r) -> str:
        usual_ok = pd.notna(r.u_per_game) and r.u_games >= 3
        if r.per_game >= hi and r.per_game > 0 and (not usual_ok or r.per_game > r.u_per_game):
            return "use more"
        if r.games >= 2 and r.per_game <= lo and (not usual_ok or r.per_game < r.u_per_game):
            batter_poor = r.balls_faced >= 20 and pd.notna(r.avg) and r.avg < 20
            bowler_poor = r.balls_bowled >= 60 and (r.wickets == 0 or (pd.notna(r.u_bowl_avg) and pd.notna(r.bowl_avg)
                                                                       and r.bowl_avg > r.u_bowl_avg * 1.25))
            if batter_poor or bowler_poor:
                return "think about dropping"
        return "keep"
    per["verdict"] = [verdict(r) for r in per.itertuples()]
    per = per.sort_values("per_game", ascending=False).reset_index(drop=True)

    def why(r) -> str:
        bits = []
        if r.balls_faced >= 10 or r.runs >= 10 or r.balls_bowled < 12:  # a bowler's few balls at the end aren't news
            bits.append(f"{int(r.runs)} run{'s' if r.runs != 1 else ''}"
                        + (f" at {r.avg:.1f}" if pd.notna(r.avg) else " (never out)")
                        + (f" (usually {r.u_avg:.1f})" if pd.notna(r.u_avg) else ""))
        if r.balls_bowled >= 12:
            bits.append(f"{int(r.wickets)} wkt{'s' if r.wickets != 1 else ''}"
                        + (f" at {r.bowl_avg:.1f}" if pd.notna(r.bowl_avg) and r.conceded > 0 else f" for {int(r.conceded)}")
                        + (f" (usually {r.u_bowl_avg:.1f})" if pd.notna(r.u_bowl_avg) else ""))
        return ", ".join(bits)
    per["why"] = [why(r) for r in per.itertuples()]

    # the side's series before this one in the format
    def team_line(mids) -> dict:
        g = m[m.match_id.isin(mids)]
        inn = career.innings[career.innings.match_id.isin(mids)]
        mine, theirs = inn[inn.team == team], inn[inn.team != team]
        decided = int(((g.winner != "") & g.winner.notna()).sum())
        return dict(games=len(g), won=int((g.winner == team).sum()), lost=int(((g.winner != team) & (g.winner != "")).sum()),
                    win_pct=float((g.winner == team).sum() / decided * 100) if decided else np.nan,
                    rpw_for=float(mine.runs.sum() / max(mine.wickets.sum(), 1)) if len(mine) else np.nan,
                    rpw_against=float(theirs.runs.sum() / max(theirs.wickets.sum(), 1)) if len(theirs) else np.nan)
    prev = m[(m.format == fmt) & (m.date < start) & (m.series_id != "") & ((m.home == team) | (m.away == team))]
    prev_series = []
    for sid, g in sorted(prev.groupby("series_id"), key=lambda kv: kv[1].date.min())[-earlier:]:
        first = g.sort_values("date").iloc[0]
        opp = first.away if first.home == team else first.home
        prev_series.append(dict(label=f"v {opp} ({first.date:%b %Y})", **team_line(g.match_id)))
    return dict(format=fmt, players=per, now=team_line(ids), earlier=prev_series)
