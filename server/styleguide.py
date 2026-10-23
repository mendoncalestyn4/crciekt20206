"""The style guide's numbers: every piece of the chart kit drawn from your own career, for your team's latest section
and season (or, with no team picked, the team with the most matches).

Every number comes from the engine (the same functions the current site uses); this module only picks and arranges
them. Each piece is worked out on its own: one that can't be (too few matches, say) comes back as None with a short
reason in `missing`, and the rest of the page is still drawn."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from ccstats import matchstory as MS
from ccstats import myteam as MT
from ccstats import partnerships as PT
from ccstats.rankings import player_ratings, team_elo
from ccstats.stats import Scope, player_tables
from ccstats.winprob import match_report

FORMAT_WORD = {"T20Is": "T20I", "ODIs": "ODI", "Tests": "Test"}


def clean(v):
    """A value the browser can read: plain numbers (no NaN), dates as YYYY-MM-DD, lists and dicts all the way down."""
    if isinstance(v, dict):
        return {str(k): clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [clean(x) for x in v]
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (float, np.floating)):
        f = float(v)
        if not math.isfinite(f):
            return None
        return int(f) if f.is_integer() else round(f, 2)
    if isinstance(v, pd.Timestamp):
        return v.strftime("%Y-%m-%d")
    if v is None or v is pd.NA or v is pd.NaT:
        return None
    return v


def rows(df: pd.DataFrame, cols) -> list[dict]:
    cols = [c for c in cols if c in df.columns]
    return [clean(dict(zip(cols, r))) for r in df[cols].itertuples(index=False)]


def overs(balls) -> str:
    return MS.overs_text(int(balls))


def pick_team(career, mine: list[str]) -> str | None:
    """Your first team with a match in the career, else the team with the most matches."""
    m = career.matches
    played = set(m.home) | set(m.away)
    for t in mine:
        if t in played:
            return t
    if m.empty:
        return None
    return pd.concat([m.home, m.away]).value_counts().index[0]


def score_of(career, match_id: str, team: str) -> str:
    """'245/6' or '180' (all out) or '310/4d & 120', for one side of a match."""
    inn = career.innings[(career.innings.match_id == match_id) & (career.innings.team == team)].sort_values("innings_no")
    return " & ".join(f"{int(i.runs)}" + ("" if i.all_out else f"/{int(i.wickets)}") + ("d" if i.declared else "")
                      for i in inn.itertuples())


def results(career, team: str, ids=None) -> list[dict]:
    """The team's matches, newest first: score both sides, the result from the team's side, the headline."""
    m = career.matches
    g = m[(m.home == team) | (m.away == team)]
    if ids is not None:
        g = g[g.match_id.isin(ids)]
    out = []
    for r in g.sort_values(["date", "match_id"]).itertuples():
        opp = r.away if r.home == team else r.home
        outcome = ("W" if r.winner == team else "L" if r.winner == opp else
                   "NR" if r.result_type == "no result" else "T" if r.result_type == "tie" else "D")
        out.append(dict(id=r.match_id, date=clean(r.date), section=r.section, opp=opp, outcome=outcome, result=r.result,
                        us=score_of(career, r.match_id, team), them=score_of(career, r.match_id, opp),
                        no=clean(r.series_match_no), of=clean(r.series_length), series=r.series_id,
                        headline=MS.pom_headline(career, r.match_id)))
    return out[::-1]


def scorecard(career, match_id: str) -> dict:
    """The whole scorecard, one card per innings, with the player of the match's figures, story and partnerships."""
    r = career.matches.set_index("match_id").loc[match_id]
    inn = career.innings[career.innings.match_id == match_id].sort_values("innings_no")
    cards = []
    for i in inn.itertuples():
        bt = career.batting[(career.batting.match_id == match_id) & (career.batting.innings_no == i.innings_no)]
        bw = career.bowling[(career.bowling.match_id == match_id) & (career.bowling.innings_no == i.innings_no)]
        fw = career.fow[(career.fow.match_id == match_id) & (career.fow.innings_no == i.innings_no)]
        cards.append(dict(innings_no=int(i.innings_no), team=i.team, runs=int(i.runs), wickets=int(i.wickets),
                          balls=int(i.balls), overs=overs(i.balls), all_out=bool(i.all_out), declared=bool(i.declared),
                          extras=int(i.extras),
                          bat=rows(bt.sort_values("position"), ["player", "position", "did_bat", "how_out", "dismissal",
                                                                "runs", "balls", "fours", "sixes", "out"]),
                          bowl=rows(bw, ["player", "balls", "maidens", "runs", "wickets", "dots"]),
                          fow=rows(fw.sort_values("wicket"), ["wicket", "score"])))
    st = PT.stands(career, [match_id])
    pom = None
    if r.player_of_match:
        f = MS.figures(career, match_id, r.player_of_match)
        pom = dict(player=r.player_of_match, team=MS.team_of(career, match_id, r.player_of_match), bat=f["bat"],
                   bowl=f["bowl"], headline=MS.pom_headline(career, match_id), report=match_report(career, match_id))
    return clean(dict(id=match_id, date=r.date, section=r.section, event=r.event, home=r.home, away=r.away,
                      result=r.result, no=r.series_match_no, of=r.series_length, cards=cards, pom=pom,
                      stands=rows(st, ["innings_no", "team", "wicket", "runs", "unbroken", "batter1", "batter2"])))


def leaders(career, ids) -> dict:
    """Leaderboards for these matches: most runs and wickets, and the qualified bests."""
    bat, bowl, _, _ = player_tables(career, Scope(), by_team=True) if ids is None else \
        player_tables(career, _scope_of(career, ids), by_team=True)
    b_cols = ["player", "team", "innings", "runs", "balls", "average", "strike_rate", "sixes", "fours", "high_score_text"]
    w_cols = ["player", "team", "innings", "balls", "wickets", "runs", "economy", "average", "best"]
    return dict(
        runs=rows(bat.sort_values(["runs", "balls"], ascending=[False, True]).head(10), b_cols),
        wickets=rows(bowl.sort_values(["wickets", "runs"], ascending=[False, True]).head(10), w_cols),
        sixes=rows(bat[bat.sixes > 0].sort_values(["sixes", "runs"], ascending=False).head(6), b_cols),
        average=rows(bat[bat.innings >= 4].sort_values("average", ascending=False).head(6), b_cols),
        strike_rate=rows(bat[bat.balls >= 60].sort_values("strike_rate", ascending=False).head(6), b_cols),
        economy=rows(bowl[bowl.balls >= 60].sort_values("economy").head(6), w_cols))


def _scope_of(career, ids) -> Scope:
    m = career.matches[career.matches.match_id.isin(ids)]
    return Scope(sections=sorted(m.section.unique()), seasons=sorted(m.season.unique()))


def star(career, team: str, section: str, season: str) -> dict:
    """The team's top run-scorer in the section this season: every innings, how they compare with the section's
    batters (percentiles), where the runs come from, how they get out, every format, their rating."""
    ids = career.matches[(career.matches.section == section) & (career.matches.season == season)].match_id
    b = career.batting[career.batting.match_id.isin(ids) & career.batting.did_bat & (career.batting.team == team)]
    if b.empty:
        raise ValueError("Nobody has batted for the team this season yet.")
    p = b.groupby("player").runs.sum().sort_values(ascending=False).index[0]
    m = career.matches.set_index("match_id")
    mine = b[b.player == p].assign(date=lambda x: x.match_id.map(m.date)).sort_values(["date", "innings_no"])
    opp = [m.away[x] if m.home[x] == team else m.home[x] for x in mine.match_id]
    innings = [dict(date=clean(d), opp=o, runs=int(r), balls=int(bl), out=bool(ou))
               for d, o, r, bl, ou in zip(mine.date, opp, mine.runs, mine.balls, mine.out)]
    bat, _, _, _ = player_tables(career, Scope(sections=[section], seasons=[season]))
    pool, among = bat[bat.innings >= 3], f"{section} batters in {season}"
    if len(pool) < 8 or not (pool.player == p).any():   # too few this season to compare with: every season here
        bat, _, _, _ = player_tables(career, Scope(sections=[section]))
        pool, among = bat[bat.innings >= 3], f"{section} batters, every season"
    stats = {"Runs": "runs", "Average": "average", "Strike rate": "strike_rate", "Boundary %": "boundary_pct",
             "Runs above average": "runs_above_average"}
    me = pool[pool.player == p]
    pct = {k: round(float((pool[v] <= me[v].iloc[0]).mean() * 100)) for k, v in stats.items()
           if v in pool and len(me) and pd.notna(me[v].iloc[0])}
    fours, sixes, runs = int(mine.fours.sum()), int(mine.sixes.sum()), int(mine.runs.sum())
    formats = []
    for sec in MT.sections_of(career, team):
        t, _, _, _ = player_tables(career, Scope(sections=[sec]))
        r = t[t.player == p]
        if len(r):
            formats.append(dict(section=sec, **rows(r, ["innings", "runs", "average", "strike_rate", "high_score_text",
                                                        "fours", "sixes", "hundreds", "fifties"])[0]))
    rating = None
    rt = player_ratings(career, section)
    rt = rt[rt.team == team].dropna(subset=["batting"]).sort_values("batting", ascending=False).reset_index(drop=True)
    if (rt.player == p).any():
        i = int(rt.index[rt.player == p][0])
        rating = dict(value=clean(rt.batting[i]), rank=i + 1)
    return dict(player=p, team=team, section=section, season=season, innings=innings, percentiles=pct,
                pool=int(len(pool)), among=among, runs=runs, fours=fours, sixes=sixes, from4=fours * 4, from6=sixes * 6,
                running=runs - fours * 4 - sixes * 6, outs=int(mine.out.sum()),
                how_out={str(k): int(v) for k, v in mine[mine.out].how_out.value_counts().items()},
                formats=formats, rating=rating)


def elo(career, section: str) -> dict:
    """Every team's rating (Elo) now, and after each match day: for the rating lines and the rank race."""
    table, hist = team_elo(career, section)
    if table.empty:
        raise ValueError("No matches with a result in this section yet.")
    teams = list(table.team)
    rating = {t: 1500.0 for t in teams}
    snaps = []
    hist = hist.sort_values(["date", "match_id"])
    for d, g in hist.groupby("date", sort=True):
        for r in g.itertuples():
            rating[r.team] = r.after
        order = sorted(teams, key=lambda t: -rating[t])
        snaps.append(dict(date=clean(d), elo={t: round(rating[t], 1) for t in teams},
                          rank={t: order.index(t) + 1 for t in teams}))
    return dict(table=rows(table.reset_index(names="rank"), ["rank", "team", "elo", "played", "peak"]), teams=teams,
                snaps=snaps)


def series(career, team: str) -> dict:
    """The team's latest bilateral series: its story, every match, the most runs and wickets."""
    m = career.matches
    g = m[((m.home == team) | (m.away == team)) & (m.series_id != "")].sort_values(["date", "match_id"])
    if g.empty:
        raise ValueError("The team hasn't played a series yet.")
    sid = g.series_id.iloc[-1]
    ids = list(m[m.series_id == sid].match_id)
    story = MS.series_story(career, ids, team)
    b = career.batting[career.batting.match_id.isin(ids) & career.batting.did_bat]
    sb = b.groupby(["player", "team"]).agg(runs=("runs", "sum"), balls=("balls", "sum"), inns=("runs", "size"),
                                           outs=("out", "sum"), hs=("runs", "max")).reset_index()
    sb = sb.sort_values(["runs", "balls"], ascending=[False, True])
    w = career.bowling[career.bowling.match_id.isin(ids) & (career.bowling.balls > 0)]
    sw = w.groupby(["player", "team"]).agg(wickets=("wickets", "sum"), runs=("runs", "sum"),
                                           balls=("balls", "sum")).reset_index()
    sw = sw.assign(economy=sw.runs / sw.balls * 6).sort_values(["wickets", "runs"], ascending=[False, True])
    return dict(id=sid, section=g.section.iloc[-1], opp=story["opponent"], story=story,
                matches=results(career, team, ids)[::-1],
                most_runs=rows(sb.head(6), ["player", "team", "runs", "balls", "inns", "outs", "hs"]),
                most_wickets=rows(sw.head(6), ["player", "team", "wickets", "runs", "balls", "economy"]))


def ratings(career, section: str) -> dict:
    pr = player_ratings(career, section)
    return dict(bat=rows(pr.dropna(subset=["batting"]).sort_values("batting", ascending=False).head(8),
                         ["player", "team", "batting", "batting_innings"]),
                bowl=rows(pr.dropna(subset=["bowling"]).sort_values("bowling", ascending=False).head(8),
                          ["player", "team", "bowling", "bowling_innings"]))


def build(career, mine: list[str]) -> dict:
    """Everything the style guide draws. Each piece on its own: one that can't be worked out is None, with why."""
    team = pick_team(career, mine)
    out: dict = dict(career=career.name, matches=int(len(career.matches)), team=team, mine=team in mine, missing={})
    if team is None:
        out["missing"]["everything"] = "This career has no matches yet."
        return out
    sections = MT.sections_of(career, team)
    section = sections[0]
    season = MT.latest_season(career, team, section)
    m = career.matches
    ids = m[(m.section == section) & (m.season == season)].match_id
    out.update(section=section, season=clean(season), format=FORMAT_WORD.get(section, section))

    def piece(name, fn):
        try:
            out[name] = clean(fn())
        except ValueError as e:   # not enough in the career for it yet: said in plain words
            out[name] = None
            out["missing"][name] = str(e)
        except Exception as e:  # noqa: BLE001 - one piece that can't be worked out never stops the others
            out[name] = None
            out["missing"][name] = f"Couldn't be worked out ({type(e).__name__}: {e})"

    piece("banner", lambda: [dict(section=b["section"], season=b["season"], elo=b["elo"], moved=b["moved"],
                                  rank=b["rank"], teams=b["teams"], record=dict(b["record"]))
                             for b in MT.banner(career, team)])
    piece("results", lambda: results(career, team)[:12])
    piece("this_season", lambda: results(career, team, ids)[::-1])   # this season in this section, oldest first
    piece("leaders", lambda: leaders(career, ids))
    piece("star", lambda: star(career, team, section, season))
    piece("match", lambda: scorecard(career, results(career, team)[0]["id"]))
    test = [r for r in results(career, team) if r["section"] in ("Tests", "First-class") or
            m.set_index("match_id").format.get(r["id"]) in ("Test", "First-class")]
    piece("match_test", lambda: scorecard(career, test[0]["id"]) if test else None)
    piece("series", lambda: series(career, team))
    piece("elo", lambda: elo(career, section))
    piece("ratings", lambda: ratings(career, section))
    piece("squad", lambda: rows(MT.squad(career, team, section, season).head(14),
                                ["player", "games", "runs", "average", "strike_rate", "wickets", "economy", "last5",
                                 "form"]))
    return out
