"""The "My team" home page: everything about one team you play as, gathered
from the rest of the site, plus report cards for the season so far."""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import teamplay as TP
from .analysis import team_table
from .records import played_order
from .stats import Scope, player_tables


def sections_of(career, team: str) -> list[str]:
    """The sections the team plays in, the one they played most recently first."""
    o = played_order(career)
    o = o[(o.home == team) | (o.away == team)]
    return list(dict.fromkeys(o.section[::-1]))


def latest_season(career, team: str, section: str) -> str:
    m = career.matches
    g = m[(m.section == section) & ((m.home == team) | (m.away == team))]
    return g.season.max() if len(g) else ""


def last_game(career, team: str):
    o = played_order(career)
    o = o[(o.home == team) | (o.away == team)]
    return o.iloc[-1] if len(o) else None


def banner(career, team: str) -> list[dict]:
    """One entry per section: this season's record, Elo rating and rank (and how
    it moved over the last 5 games) and league position where there is a table."""
    from .rankings import team_elo
    from .tables import BILATERAL, league_tables
    m = career.matches
    out = []
    for section in sections_of(career, team):
        season = latest_season(career, team, section)
        ids = m[(m.section == section) & (m.season == season)].match_id
        g = TP.games(career, ids)
        rec = TP.record(g[g.team == team])
        table, hist = team_elo(career, section)
        h = hist[hist.team == team].sort_values("date")
        elo = float(h.after.iloc[-1]) if len(h) else np.nan
        moved = elo - (float(h.after.iloc[-6]) if len(h) > 5 else float(h.before.iloc[0])) if len(h) else np.nan
        rank = int(table.index[table.team == team][0]) if (table.team == team).any() else None
        position = None
        mine = m[m.match_id.isin(ids) & ((m.home == team) | (m.away == team))]
        for event in mine.event.unique():
            e = m[(m.event == event) & (m.season == season)]
            if e.competition.iloc[0] in BILATERAL:
                continue
            for label, t, _ in league_tables(career, e.match_id):
                if team in set(t.team):
                    pos = int(t.index[t.team == team][0])
                    position = (event, label, pos, len(t))
        chances = None
        if position is not None:  # a league still being played: the chance of the playoffs and the title
            from .odds import season_odds
            od = season_odds(career, position[0], season, sims=2000)
            if od["state"] == "open":
                r = od["table"].set_index("team").loc[team] if team in set(od["table"].team) else None
                if r is not None:
                    chances = dict(playoffs=r.playoffs, title=r.title, top=r.top, knockouts=od["knockouts"])
        out.append(dict(section=section, season=season, record=rec, elo=elo, moved=moved, rank=rank, teams=len(table),
                        position=position, chances=chances))
    return out


def same_point(career, team: str, section: str) -> dict:
    """This season after N games against last season after the same N games."""
    m = career.matches
    seasons = sorted(m[(m.section == section) & ((m.home == team) | (m.away == team))].season.unique())
    if not seasons:
        return {}
    now_s = seasons[-1]
    g = TP.games(career, m[(m.section == section) & m.season.isin(seasons[-2:])].match_id)
    g = g[g.team == team]
    now = g[g.season == now_s]
    n = len(now)
    out = dict(season=now_s, n=n, now=TP.record(now), last_season=None, then=None)
    if len(seasons) > 1:
        before = g[g.season == seasons[-2]].head(n)
        out.update(last_season=seasons[-2], then=TP.record(before))
    return out


def form_arrow(scores: list[float], season_avg: float) -> str:
    if len(scores) < 2 or not np.isfinite(season_avg):
        return "▬"
    recent = float(np.mean(scores[-3:]))
    if recent > season_avg * 1.25:
        return "▲"
    if recent < season_avg * 0.75:
        return "▼"
    return "▬"


def squad(career, team: str, section: str, season: str) -> pd.DataFrame:
    """Everyone who has played for the team this season here: games, batting and
    bowling, their last 5 scores and a form arrow."""
    m = career.matches
    ids = m[(m.section == section) & (m.season == season) & ((m.home == team) | (m.away == team))].sort_values("date").match_id
    order = {mid: i for i, mid in enumerate(ids)}
    b = career.batting[career.batting.match_id.isin(ids) & (career.batting.team == team)]
    w = career.bowling[career.bowling.match_id.isin(ids) & (career.bowling.team == team) & (career.bowling.balls > 0)]
    last3 = set(ids[-3:])
    rows = []
    for p, g in b.groupby("player"):
        bb = g[g.did_bat].assign(o=lambda x: x.match_id.map(order)).sort_values(["o", "innings_no"])
        ww = w[w.player == p]
        outs = int(bb.out.sum())
        avg = bb.runs.sum() / outs if outs else np.nan
        rows.append(dict(player=p, games=g.match_id.nunique(), runs=int(bb.runs.sum()), average=avg,
                         strike_rate=bb.runs.sum() / bb.balls.sum() * 100 if bb.balls.sum() else np.nan,
                         wickets=int(ww.wickets.sum()),
                         economy=ww.runs.sum() / ww.balls.sum() * 6 if ww.balls.sum() else np.nan,
                         last5=" ".join(f"{r}{'' if o else '*'}" for r, o in zip(bb.runs.tail(5), bb.out.tail(5))),
                         form=form_arrow(list(bb.runs), bb.runs.mean() if len(bb) else np.nan),
                         recent=bool(set(g.match_id) & last3),
                         low_run=_low_run(list(bb.runs), list(bb.out)),
                         usual_position=float(bb.position.median()) if len(bb) else np.nan))
    d = pd.DataFrame(rows, columns=["player", "games", "runs", "average", "strike_rate", "wickets", "economy", "last5",
                                    "form", "recent", "low_run", "usual_position"])
    return d.sort_values(["games", "runs"], ascending=False).reset_index(drop=True)


def _low_run(runs: list[int], outs: list[bool]) -> int:
    """Innings in a row under 10 (out) at the end."""
    n = 0
    for r, o in zip(reversed(runs), reversed(outs)):
        if r < 10 and o:
            n += 1
        else:
            break
    return n


def alerts(career, team: str, section: str, season: str) -> list[str]:
    sq = squad(career, team, section, season)
    out = []
    # only the batters (usually in the top 7): a no. 8 bowler making a few low scores is no news
    for r in sq[(sq.low_run >= 3) & (sq.usual_position <= 7)].itertuples():
        out.append(f"📉 {r.player} has been out for under 10 in {r.low_run} innings in a row.")
    if len(sq):
        avg_runs = sq.runs.sum() / max(sq.games.sum(), 1)
        for r in sq[~sq.recent & (sq.games >= 2)].itertuples():
            per = r.runs / r.games
            if per > avg_runs * 1.3 or (r.wickets / r.games >= 1.5):
                out.append(f"🪑 {r.player} isn't in your last 3 XIs but has "
                           + (f"{r.runs} runs in {r.games} games" if per > avg_runs * 1.3 else
                              f"{r.wickets} wickets in {r.games} games") + ".")
    return out


GRADES = ["A", "B", "C", "D", "E"]


def _grade(diff_pct: float) -> str:
    if not np.isfinite(diff_pct):
        return "–"
    for cut, g in ((15, "A"), (5, "B"), (-5, "C"), (-15, "D")):
        if diff_pct >= cut:
            return g
    return "E"


def report_card(career, team: str, section: str, season: str) -> list[tuple[str, str, str]]:
    """(subject, grade, why) for the season so far, each against the average team here."""
    m = career.matches
    ids = m[(m.section == section) & (m.season == season)].match_id
    tt = team_table(career, ids)
    if team not in set(tt.team):
        return []
    me = tt.set_index("team").loc[team]
    avg = tt.mean(numeric_only=True)
    out = []
    tg = TP.games(career, ids)
    rec = TP.record(tg[tg.team == team])
    wp = rec["win_pct"] if np.isfinite(rec["win_pct"]) else 0.0
    g = "A" if wp >= 70 else "B" if wp >= 55 else "C" if wp >= 45 else "D" if wp >= 30 else "E"
    out.append(("Results", g, f"{TP.wdl(rec)} ({wp:.0f}% of games with a result)"))
    d = (me.rpw_for - avg.rpw_for) / avg.rpw_for * 100 if avg.rpw_for else np.nan
    out.append(("Batting", _grade(d), f"{me.rpw_for:.1f} runs per wicket, average team {avg.rpw_for:.1f}"))
    d = (avg.rpw_against - me.rpw_against) / avg.rpw_against * 100 if avg.rpw_against else np.nan
    out.append(("Bowling", _grade(d), f"{me.rpw_against:.1f} runs per wicket conceded, average team {avg.rpw_against:.1f}"))
    _, _, fld, _ = player_tables(career, Scope(sections=[section], seasons=[season]), by_team=True)
    cpm = fld.groupby("team").catches.sum() / tt.set_index("team").played
    if team in cpm.index and cpm.mean():
        d = (cpm[team] - cpm.mean()) / cpm.mean() * 100
        out.append(("Fielding", _grade(d), f"{cpm[team]:.1f} catches a game, average team {cpm.mean():.1f}"))
    last5 = in_played_order(career, tg[tg.team == team]).tail(5)
    w5 = int((last5.outcome == "W").sum())
    out.append(("Form", {5: "A", 4: "A", 3: "B", 2: "C", 1: "D"}.get(w5, "E"), f"won {w5} of the last {len(last5)}"))
    return out


def history(career, team: str) -> pd.DataFrame:
    """Every season in every section: record and where they finished."""
    from .extras import honours
    from .tables import BILATERAL, league_tables
    m = career.matches
    mine = m[(m.home == team) | (m.away == team)]
    h = honours(career)
    rows = []
    for (section, season), g in mine.groupby(["section", "season"]):
        tg = TP.games(career, g.match_id)
        rec = TP.record(tg[tg.team == team])
        finish = []
        for event in g.event.unique():
            won = h[(h.section == event) & (h.season == season)]
            if len(won) and team in won.champion_teams.iloc[0] and "so far" not in won.how.iloc[0]:
                finish.append(f"🏆 {event}")
                continue
            e = m[(m.event == event) & (m.season == season)]
            if e.competition.iloc[0] in BILATERAL:
                continue
            ko = e[e.knockout & ((e.home == team) | (e.away == team))]
            if len(ko):
                lastko = ko.sort_values("date").iloc[-1]
                finish.append(f"{event}: {lastko.stage or 'knockouts'}")
                continue
            for label, t, _ in league_tables(career, e.match_id):
                if team in set(t.team):
                    finish.append(f"{event}: {int(t.index[t.team == team][0])} of {len(t)}"
                                  + (f" ({label})" if label not in ("League", "Every team") else ""))
        rows.append(dict(section=section, season=season, **rec, finish=" · ".join(finish)))
    return pd.DataFrame(rows, columns=["section", "season", "played", "won", "lost", "drawn", "tied", "no_result",
                                       "win_pct", "decided", "finish"]).sort_values(["season", "section"], ascending=[False, True])


def team_records(career, team: str, section: str) -> list[tuple[str, str]]:
    """The team's own bests in a section: highest and lowest totals, biggest wins, best individual efforts."""
    from .records import records
    ids = career.matches[career.matches.section == section].match_id
    rec = records(career, ids, top=10_000)
    out = []
    for name, col in (("Highest team totals", "team"), ("Lowest completed totals", "team"),
                      ("Biggest wins by runs", "team"), ("Highest individual scores", "team"),
                      ("Best bowling in an innings", "team"), ("Highest partnerships", "team")):
        t = rec.get(name)
        if t is None or t.empty:
            continue
        mine = t[t[col] == team]
        if len(mine):
            r = mine.iloc[0]
            who = "" if name in ("Highest team totals", "Lowest completed totals", "Biggest wins by runs") else f"{r.holder} "
            out.append((name.replace("Highest team totals", "Highest total").replace("Lowest completed totals", "Lowest total")
                        .replace("Biggest wins by runs", "Biggest win").replace("Highest individual scores", "Highest score")
                        .replace("Best bowling in an innings", "Best bowling").replace("Highest partnerships", "Best stand"),
                        f"{who}{r.value}" + (f" v {r.against}" if r.against else "") + f" ({r.date:%b %Y})"))
    return out


def in_played_order(career, g: pd.DataFrame) -> pd.DataFrame:
    """Rows with a match_id, in the order the matches were played (the game can save
    scorecards dated out of order), so "last 5" ends on the latest result."""
    from .records import by_played
    return by_played(career, g)
