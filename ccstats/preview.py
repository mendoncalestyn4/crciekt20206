"""Opponent preview: everything about one opponent, and about your meetings
with them.  Works on a set of match ids (a section, or all international
formats together)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import teamplay as TP
from .players import kind_of_ids
from .stats import ordinal


def _score_text(career, mid: str, team: str) -> str:
    inn = career.innings[(career.innings.match_id == mid) & (career.innings.team == team)].sort_values("innings_no")
    parts = [f"{r.runs}" if r.all_out else f"{r.runs}/{r.wickets}{'d' if r.declared else ''}" for r in inn.itertuples()]
    return " & ".join(parts) or "–"


def recent_xi(career, ids, team: str, games: int = 3) -> set[str]:
    """Everyone who played for `team` in their last `games` matches here."""
    tm = career.matches[career.matches.match_id.isin(ids) & ((career.matches.home == team) | (career.matches.away == team))]
    from .records import by_played
    last = by_played(career, tm.sort_values(["date", "match_id"])).match_id.tail(games)
    b = career.batting[career.batting.match_id.isin(last) & (career.batting.team == team)]
    return set(b.player)


# --------------------------------------------------------------------------- #
# 54 · meetings
# --------------------------------------------------------------------------- #


def meetings(career, ids, mine: str, opp: str) -> dict:
    """Your record against them: W/D/L, last 5, how the games were won, typical
    scores, key players on both sides and one card per game."""
    m = career.matches[career.matches.match_id.isin(ids)]
    games = m[((m.home == mine) & (m.away == opp)) | ((m.home == opp) & (m.away == mine))].sort_values(["date", "match_id"])
    g = TP.games(career, games.match_id)
    me = g[g.team == mine]
    rec = TP.record(me)
    how = dict(bat_first_wins={mine: int(((me.outcome == "W") & me.batted_first).sum()),
                               opp: int(((me.outcome == "L") & ~me.batted_first).sum())},
               chasing_wins={mine: int(((me.outcome == "W") & ~me.batted_first).sum()),
                             opp: int(((me.outcome == "L") & me.batted_first).sum())})
    inn = career.innings[career.innings.match_id.isin(games.match_id)]
    first_inns = inn[inn.team_innings == 1].groupby("team").runs.mean()
    typical = {mine: first_inns.get(mine, np.nan), opp: first_inns.get(opp, np.nan)}
    # key players in these games
    bat = career.batting[career.batting.match_id.isin(games.match_id) & career.batting.did_bat]
    bowl = career.bowling[career.bowling.match_id.isin(games.match_id)]
    key = {}
    for team in (mine, opp):
        b = bat[bat.team == team].groupby("player").agg(runs=("runs", "sum"), innings=("runs", "size"),
                                                         outs=("out", "sum"), best=("runs", "max")).reset_index()
        b["average"] = b.runs / b.outs.replace(0, np.nan)
        w = bowl[bowl.team == team].groupby("player").agg(wickets=("wickets", "sum"), runs=("runs", "sum"),
                                                           balls=("balls", "sum")).reset_index()
        w["economy"] = w.runs / w.balls.replace(0, np.nan) * 6
        players = set(bat[bat.team == team].player)
        potm = games[games.player_of_match.isin(players)].player_of_match.value_counts()
        key[team] = dict(runs=b.sort_values("runs", ascending=False).head(3),
                         wickets=w[w.wickets > 0].sort_values(["wickets", "economy"], ascending=[False, True]).head(3),
                         potm=potm.head(3), current=recent_xi(career, ids, team))
    cards = []
    for r in games[::-1].itertuples():
        side = {}
        for team in (r.home, r.away):
            b = bat[(bat.match_id == r.match_id) & (bat.team == team)].sort_values("runs", ascending=False)
            w = bowl[(bowl.match_id == r.match_id) & (bowl.team == team)]
            w = w.groupby("player")[["wickets", "runs"]].sum().assign(k=lambda x: x.wickets * 1000 - x.runs) \
                .sort_values("k", ascending=False)
            side[team] = dict(score=_score_text(career, r.match_id, team),
                              top_bat=(f"{b.player.iloc[0]} {b.runs.iloc[0]}{'' if b.out.iloc[0] else '*'}" if len(b) else "–"),
                              top_bowl=(f"{w.index[0]} {int(w.wickets.iloc[0])}/{int(w.runs.iloc[0])}" if len(w) else "–"))
        cards.append(dict(match_id=r.match_id, date=r.date, section=r.section, event=r.event, stage=r.stage,
                          home=r.home, away=r.away, result=r.result, potm=r.player_of_match, sides=side,
                          story=story(career, r)))
    from .records import by_played
    last5 = list(by_played(career, me).outcome.tail(5))
    return dict(games=games, record=rec, last5=last5, how=how, typical=typical, key=key, cards=cards)


def story(career, r) -> str:
    """One line on how a game went: the decisive performance and the margin."""
    if not r.winner:
        word = {"draw": "Drawn", "tie": "Tied", "no result": "No result"}.get(r.result_type, r.result)
        if r.tiebreak_winner:
            return f"Tied, {r.tiebreak_winner} won the super over."
        return f"{word}."
    bat = career.batting[(career.batting.match_id == r.match_id) & career.batting.did_bat & (career.batting.team == r.winner)]
    bowl = career.bowling[(career.bowling.match_id == r.match_id) & (career.bowling.team == r.winner)]
    inn = career.innings[career.innings.match_id == r.match_id]
    rpw = inn.runs.sum() / max(inn.wickets.sum(), 1)
    best_b = bat.sort_values("runs", ascending=False).head(1)
    w = bowl.groupby("player")[["wickets", "runs"]].sum().sort_values(["wickets", "runs"], ascending=[False, True]).head(1)
    bat_pts = float(best_b.runs.iloc[0]) if len(best_b) else 0
    bowl_pts = float(w.wickets.iloc[0]) * rpw if len(w) else 0
    if pd.notna(r.margin_wickets):
        how = f"chased it down with {int(r.margin_wickets)} wicket{'s' if r.margin_wickets != 1 else ''} left"
    elif pd.notna(r.margin_runs):
        how = f"defended it by {int(r.margin_runs)} run{'s' if r.margin_runs != 1 else ''}"
        if r.innings_win:
            how = f"won by an innings and {int(r.margin_runs)} runs"
    else:
        how = "won"
    if bowl_pts > bat_pts and len(w):
        star = f"{w.index[0]} took {int(w.wickets.iloc[0])}/{int(w.runs.iloc[0])}"
    elif len(best_b):
        x = best_b.iloc[0]
        star = f"{x.player} made {x.runs}{'' if x.out else '*'}"
    else:
        star = ""
    return f"{r.winner} {how}" + (f"; {star}." if star else ".")


# --------------------------------------------------------------------------- #
# 55 · match-ups
# --------------------------------------------------------------------------- #


def matchups(career, ids, mine: str, opp: str, everywhere: bool = False, current_only: bool = False) -> dict:
    """(their bowlers v your batters, your bowlers v their batters): how many times
    each bowler got each batter out (run-outs aren't the bowler's, so they're left
    out).  `everywhere`: count every match in the career where these players
    faced each other, whatever teams they were playing for; otherwise only your
    meetings.  Runs are only those the batter made in the innings the bowler got
    them out in (the scorecards don't say which bowler they scored off)."""
    m = career.matches
    squad_m, squad_o = _squad(career, ids, mine), _squad(career, ids, opp)
    if current_only:
        squad_m &= recent_xi(career, ids, mine, games=5)
        squad_o &= recent_xi(career, ids, opp, games=5)
    if everywhere:
        pool = m.match_id
    else:
        mm = m[m.match_id.isin(ids)]
        pool = mm[((mm.home == mine) & (mm.away == opp)) | ((mm.home == opp) & (mm.away == mine))].match_id
    b = career.batting[career.batting.match_id.isin(pool) & career.batting.did_bat]
    out = {}
    for bowlers, batters, label in ((squad_o, squad_m, "their_bowlers"), (squad_m, squad_o, "our_bowlers")):
        if not everywhere:
            side_bat = mine if label == "their_bowlers" else opp
            x = b[(b.team == side_bat) & b.player.isin(batters)]
        else:
            x = b[b.player.isin(batters)]
        got = x[x.out & x.bowler.isin(bowlers) & (x.how_out != "run out")]
        g = got.groupby(["bowler", "player"]).agg(dismissals=("runs", "size"), runs_when_out=("runs", "sum"),
                                                  balls_when_out=("balls", "sum")).reset_index()
        # innings in which both played (the batter batted, the bowler bowled at that side)
        bw = career.bowling[career.bowling.match_id.isin(pool) & career.bowling.player.isin(bowlers) & (career.bowling.balls > 0)]
        met = x.merge(bw[["match_id", "innings_no", "player"]].rename(columns={"player": "bowler_"}),
                      on=["match_id", "innings_no"])
        met = met.groupby(["bowler_", "player"]).size().rename("innings_met")
        g["innings_met"] = [int(met.get((bo, ba), 0)) for bo, ba in zip(g.bowler, g.player)]
        out[label] = g.sort_values(["dismissals", "runs_when_out"], ascending=[False, True]).reset_index(drop=True)
    return out


def _squad(career, ids, team: str) -> set[str]:
    b = career.batting[career.batting.match_id.isin(ids) & (career.batting.team == team)]
    return set(b.player)


# --------------------------------------------------------------------------- #
# 70-80 · their side
# --------------------------------------------------------------------------- #


def key_wicket(career, ids, team: str, min_innings: int = 5) -> pd.DataFrame:
    """The batters whose score decides their results: team win % when they make a
    decent score (20 in T20, 30 in one-day, 50 in a Test match) against when they don't."""
    from .stats import bars_for
    kind = kind_of_ids(career, ids)
    bar = bars_for(kind)["decent"]
    g = TP.games(career, ids)
    res = g[g.team == team].set_index("match_id").outcome
    multi = kind == "multi"
    b = career.batting[career.batting.match_id.isin(res.index) & (career.batting.team == team) & career.batting.did_bat]
    per = b.groupby(["match_id", "player"]).runs.sum().reset_index()
    rows = []
    for p, x in per.groupby("player"):
        if len(x) < min_innings:
            continue
        good = x[x.runs >= bar].match_id
        bad = x[x.runs < bar].match_id
        if len(good) < 2 or len(bad) < 2:
            continue
        pg = TP.record(pd.DataFrame({"outcome": res.loc[good].values, "kind": kind}))
        pb = TP.record(pd.DataFrame({"outcome": res.loc[bad].values, "kind": kind}))
        rows.append(dict(player=p, innings=len(x), good=len(good), win_good=pg["win_pct"], win_bad=pb["win_pct"]))
    d = pd.DataFrame(rows, columns=["player", "innings", "good", "win_good", "win_bad"])
    d["gap"] = d.win_good - d.win_bad
    d.attrs.update(bar=bar, multi=multi)
    return d.dropna(subset=["gap"]).sort_values("gap", ascending=False).reset_index(drop=True)


def weak_spot(career, ids, team: str) -> pd.DataFrame:
    """Their average stand for each wicket against the competition's average for that wicket."""
    from . import partnerships as P
    s = P.stands(career, ids)
    mine = s[s.team == team].groupby("wicket").runs.agg(["mean", "size"])
    allw = s.groupby("wicket").runs.mean()
    d = mine.join(allw.rename("all")).reset_index().rename(columns={"mean": "average", "size": "stands"})
    d["vs"] = (d.average - d["all"]) / d["all"].replace(0, np.nan) * 100
    return d


def attack_to_target(career, ids, team: str, min_balls: int = 60) -> pd.DataFrame:
    """Their regular bowlers, most expensive first (economy in limited overs, average in multi-day)."""
    kind = kind_of_ids(career, ids)
    w = career.bowling[career.bowling.match_id.isin(ids)]
    econ0 = w.runs.sum() / max(w.balls.sum(), 1) * 6
    avg0 = w.runs.sum() / max(w.wickets.sum(), 1)
    t = w[w.team == team].groupby("player").agg(balls=("balls", "sum"), runs=("runs", "sum"), wickets=("wickets", "sum"),
                                                innings=("balls", lambda s: int((s > 0).sum())))
    t = t[t.balls >= min_balls]
    t["economy"] = t.runs / t.balls * 6
    t["average"] = t.runs / t.wickets.replace(0, np.nan)
    key = "average" if kind == "multi" else "economy"
    t = t.sort_values(key, ascending=False, na_position="first").reset_index()
    t.attrs.update(economy=econ0, average=avg0, key=key)
    return t


def batting_strip(career, ids, team: str, top: int = 7) -> pd.DataFrame:
    """Their main batters (most runs here) with their style against the section's average batter."""
    from .players import batting_styles
    from .stats import Scope, player_tables
    m = career.matches[career.matches.match_id.isin(ids)]
    secs = list(m.section.unique())
    bat, _, _, base = player_tables(career, Scope(sections=secs), by_team=True)
    mine = bat[bat.team == team].sort_values("runs", ascending=False).head(top)
    return batting_styles(mine, base).sort_values("runs", ascending=False).reset_index(drop=True) if len(mine) else mine


def chase_extremes(career, ids, team: str) -> dict:
    """Their record batting first and chasing, highest successful chase and lowest total defended."""
    g = TP.games(career, ids)
    t = g[g.team == team]
    multi = TP.is_multi(g)
    inn = career.innings[career.innings.match_id.isin(t.match_id)]
    whole = t.first_score.notna()  # games shortened by rain don't set chasing or defending marks
    chase = t[~t.batted_first & (t.outcome == "W") & whole]
    defend = t[t.batted_first & (t.outcome == "W") & whole]
    best_chase = low_defend = None
    if not multi:
        if len(chase):
            c = inn[inn.match_id.isin(chase.match_id) & (inn.team == team) & (inn.innings_no == 2)]
            if len(c):
                r = c.sort_values("runs", ascending=False).iloc[0]
                best_chase = (int(r.runs), int(r.wickets), r.match_id, r.opposition)
        if len(defend):
            d = inn[inn.match_id.isin(defend.match_id) & (inn.team == team) & (inn.innings_no == 1)]
            if len(d):
                r = d.sort_values("runs").iloc[0]
                low_defend = (int(r.runs), int(r.wickets), r.match_id, r.opposition, bool(r.all_out))
    return dict(first=TP.record(t[t.batted_first]), second=TP.record(t[~t.batted_first]), multi=multi,
                best_chase=best_chase, low_defend=low_defend)


def venue_record(career, ids, team: str) -> dict:
    g = TP.games(career, ids)
    t = g[g.team == team]
    return {v: TP.record(t[t.venue == v]) for v in ("home", "away", "neutral")}


def big_matches(career, ids, team: str) -> dict:
    """Knockouts and finals, and series deciders."""
    g = TP.games(career, ids)
    t = g[g.team == team]
    s = TP.series_games(career, ids)
    s = s[s.team == team]
    return dict(knockouts=TP.record(t[t.knockout]), finals=TP.record(t[t.knockout & (t.stage == "Final")]),
                deciders=TP.record(s[s.decider]))


def trend(career, ids, team: str, last: int = 5) -> dict:
    """Recent results and their Elo rating now and `last` games ago (each section rated separately)."""
    from .rankings import team_elo
    from .records import by_played
    g = by_played(career, TP.games(career, ids))
    t = g[g.team == team]
    m = career.matches[career.matches.match_id.isin(ids)]
    out = dict(last=list(t.outcome.tail(last)), recent=TP.record(t.tail(last)), before=TP.record(t.iloc[:-last]),
               elo_now=np.nan, elo_then=np.nan, elo_rank=None, teams=0)
    if m.section.nunique() == 1 and len(t):
        table, hist = team_elo(career, m.section.iloc[0])
        h = hist[hist.team == team].sort_values("date")
        if len(h):
            out["elo_now"] = float(h.after.iloc[-1])
            out["elo_then"] = float(h.after.iloc[-last - 1]) if len(h) > last else float(h.before.iloc[0])
            out["elo_rank"] = int(table.index[table.team == team][0]) if (table.team == team).any() else None
            out["teams"] = len(table)
    return out


def side_by_side(career, ids, mine: str, opp: str) -> pd.DataFrame:
    """Your team and theirs on the measures that matter, with a tick for the better one."""
    from .analysis import team_table
    tt = team_table(career, ids).set_index("team")
    bf, _ = TP.bat_first_table(career, ids)
    bf = bf.set_index("team")
    rows = []
    limited = tt.nrr.notna().any()
    measures = [("Win %", "win_pct", True, 0), ("Runs per wicket (batting)", "rpw_for", True, 1),
                ("Runs per wicket conceded", "rpw_against", False, 1)]
    if limited:
        measures += [("Run rate", "rr_for", True, 2), ("Economy", "rr_against", False, 2), ("Net run rate", "nrr", True, 2)]
    for label, col, higher, dec in measures:
        a, b = tt[col].get(mine, np.nan), tt[col].get(opp, np.nan)
        rows.append((label, a, b, higher, dec))
    for label, col in (("Win % batting first", "bf_win_pct"), ("Win % chasing" if limited else "Win % batting second", "ch_win_pct")):
        rows.append((label, bf[col].get(mine, np.nan), bf[col].get(opp, np.nan), True, 0))
    t1, t2 = trend(career, ids, mine), trend(career, ids, opp)
    rows.append(("Wins in the last 5", t1["recent"]["won"], t2["recent"]["won"], True, 0))
    if np.isfinite(t1["elo_now"]) and np.isfinite(t2["elo_now"]):
        rows.append(("Elo rating", t1["elo_now"], t2["elo_now"], True, 0))
    d = pd.DataFrame(rows, columns=["measure", "mine", "theirs", "higher", "dec"])
    d["better"] = [("mine" if (a > b) == h else "theirs") if np.isfinite(a) and np.isfinite(b) and a != b else ""
                   for a, b, h in zip(d.mine.astype(float), d.theirs.astype(float), d.higher)]
    return d


def game_plan(career, ids, mine: str, opp: str) -> list[str]:
    """A short plain-language plan from everything above."""
    lines = []
    ce = chase_extremes(career, ids, opp)
    a, b = ce["first"], ce["second"]
    if a["decided"] >= 3 and b["decided"] >= 3 and np.isfinite(a["win_pct"]) and np.isfinite(b["win_pct"]):
        if a["win_pct"] - b["win_pct"] >= 15:
            lines.append(f"**Make them chase.** {opp} win {a['win_pct']:.0f}% batting first but only {b['win_pct']:.0f}% "
                         f"{'chasing' if not ce['multi'] else 'batting second'}.")
        elif b["win_pct"] - a["win_pct"] >= 15:
            lines.append(f"**Make them set a total.** {opp} win {b['win_pct']:.0f}% "
                         f"{'chasing' if not ce['multi'] else 'batting second'} but only {a['win_pct']:.0f}% batting first.")
    kw = key_wicket(career, ids, opp)
    if len(kw) and kw.gap.iloc[0] >= 15:
        r = kw.iloc[0]
        lines.append(f"**Key wicket: {r.player}.** {opp} win {r.win_good:.0f}% when they make {kw.attrs['bar']}+ and "
                     f"{r.win_bad:.0f}% when they don't.")
    ws = weak_spot(career, ids, opp)
    ws = ws[ws.stands >= 3]
    if len(ws):
        r = ws.sort_values("vs").iloc[0]
        if r.vs <= -20:
            n = int(r.wicket)
            lines.append(f"**Their weak spot: the {ordinal(n)} wicket.** "
                         f"That stand averages {r.average:.0f}, against {r['all']:.0f} for every team here: one more "
                         "wicket there and they wobble.")
    at = attack_to_target(career, ids, opp)
    if len(at):
        r = at.iloc[0]
        key = at.attrs["key"]
        v, v0 = r[key], at.attrs[key]
        if np.isfinite(v) and v > v0 * 1.05:
            what = f"economy {v:.2f} against {v0:.2f}" if key == "economy" else f"average {v:.1f} against {v0:.1f}"
            lines.append(f"**Go after {r.player}:** {what} for the average bowler here.")
    mu = matchups(career, ids, mine, opp, everywhere=True, current_only=True)
    if len(mu["their_bowlers"]) and mu["their_bowlers"].dismissals.iloc[0] >= 2:
        r = mu["their_bowlers"].iloc[0]
        lines.append(f"**Watch out for {r.bowler}:** has got {r.player} out {r.dismissals} time{'' if r.dismissals == 1 else 's'}.")
    if len(mu["our_bowlers"]) and mu["our_bowlers"].dismissals.iloc[0] >= 2:
        r = mu["our_bowlers"].iloc[0]
        lines.append(f"**Your weapon: {r.bowler}** has got {r.player} out {r.dismissals} time{'' if r.dismissals == 1 else 's'}.")
    return lines
