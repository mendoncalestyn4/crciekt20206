"""The style guide's numbers: every piece of the chart kit drawn from your own career, for your team's latest section
and season (or, with no team picked, the team with the most matches).

Every number comes from the engine (the same functions the current site uses); this module only picks and arranges
them. Each piece is worked out on its own: one that can't be (too few matches, say) comes back as None with a short
reason in `missing`, and the rest of the page is still drawn."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from ccstats import seasonal as SN
from ccstats import tables as TB
from ccstats import matchstory as MS
from ccstats import myteam as MT
from ccstats import partnerships as PT
from ccstats import teamplay as TP
from ccstats.colours import nation_of
from ccstats.rankings import player_ratings, team_elo
from ccstats.records import by_played
from ccstats.stats import KIND, Scope, player_tables
from ccstats.winprob import match_report

FORMAT_WORD = {"T20Is": "T20I", "ODIs": "ODI", "Tests": "Test"}
# what every page says on a career with no matches yet (the current site's words, ui/state.py)
NO_MATCHES = ("No matches in this career yet. Play a match in Cricket Captain (with Autosave scorecards on in Options) "
              "and this page fills in within about 20 seconds.")


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


def _innings(g: list | None, team: str) -> list[dict]:
    """One side's innings of a match, in order: runs, wickets, all out, declared (`g`: the match's innings rows)."""
    return [dict(runs=int(i.runs), wkts=int(i.wickets), all_out=bool(i.all_out), declared=bool(i.declared))
            for i in g or [] if i.team == team]


def _score(g: list | None, team: str) -> str:
    """score_of from a match's innings rows already in hand."""
    return " & ".join(f"{int(i.runs)}" + ("" if i.all_out else f"/{int(i.wickets)}") + ("d" if i.declared else "")
                      for i in g or [] if i.team == team)


def results(career, team: str, ids=None) -> list[dict]:
    """The team's matches, newest first: score both sides, the result from the team's side, the headline; and for the
    charts, the margin, every innings of both sides, who batted first, where it was played (home, away or neutral,
    and the host) and the player of the match. Worked out once for each team of a career and kept with it (the
    headlines take a while over a few hundred matches); `ids` picks some of them."""
    stamp = (id(career.matches), len(career.matches))
    kept = getattr(career, "_sg_results", None)
    if kept is None or kept.get("_stamp") != stamp:   # one list per team, so going back and forth costs nothing
        kept = {"_stamp": stamp}
        try:
            career._sg_results = kept
        except AttributeError:
            pass
    if team not in kept:
        if ids is not None:   # only some matches wanted (a series): work out just those, and keep nothing partial
            return _results(career, team, set(ids))
        kept[team] = _results(career, team)
    rows = kept[team]
    if ids is None:
        return list(rows)
    wanted = set(ids)
    return [r for r in rows if r["id"] in wanted]


def _results(career, team: str, only: set | None = None) -> list[dict]:
    m = career.matches
    g = m[(m.home == team) | (m.away == team)]
    if only is not None:
        g = g[g.match_id.isin(only)]
    inns = {k: list(x.itertuples()) for k, x in career.innings[career.innings.match_id.isin(g.match_id)]
            .sort_values("innings_no").groupby("match_id")}
    out = []
    for r in g.sort_values(["date", "match_id"]).itertuples():
        opp = r.away if r.home == team else r.home
        outcome = ("W" if r.winner == team else "L" if r.winner == opp else
                   "NR" if r.result_type == "no result" else "T" if r.result_type == "tie" else "D")
        inn = inns.get(r.match_id)
        first = inn[0].team if inn else (r.batted_first or "")
        pom = r.player_of_match or ""
        out.append(dict(id=r.match_id, date=clean(r.date), section=r.section, event=r.event, opp=opp, outcome=outcome,
                        result=r.result, us=_score(inn, team), them=_score(inn, opp),
                        no=clean(r.series_match_no), of=clean(r.series_length), series=r.series_id,
                        headline=MS.pom_headline(career, r.match_id),
                        margin_runs=clean(r.margin_runs), margin_wickets=clean(r.margin_wickets),
                        innings_win=bool(r.innings_win), rain=bool(r.rain), batted_first=first == team,
                        venue="neutral" if r.neutral else ("home" if r.home == team else "away"),
                        host="" if r.neutral else r.home, ours=_innings(inn, team), theirs=_innings(inn, opp),
                        pom=pom, pom_team=MS.team_of(career, r.match_id, pom) if pom else ""))
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
    return series_of(career, g.series_id.iloc[-1], team)


def series_of(career, sid: str, team: str) -> dict:
    """One bilateral series from `team`'s side: its story, every match in played order with the series score after
    each (the ladder), whether the last match was a decider, and the most runs and wickets in it."""
    m = career.matches
    ids = list(m[m.series_id == sid].match_id)
    story = MS.series_story(career, ids, team)
    sb, sw = TB.series_leaders(career, ids)
    played = in_played_order(career, results(career, team, ids))
    won = lost = 0
    progress = []
    for r in played:   # the series score after each match
        won, lost = won + (r["outcome"] == "W"), lost + (r["outcome"] == "L")
        progress.append(dict(won=won, lost=lost))
    last = played[-1]
    before = progress[-2] if len(progress) > 1 else None
    decider = bool(before and before["won"] == before["lost"] and last["of"] and last["no"] == last["of"])
    return dict(id=sid, section=m[m.series_id == sid].section.iloc[0], team=team, opp=story["opponent"], story=story,
                matches=played, progress=progress, decider=decider,
                most_runs=rows(sb, ["player", "team", "runs", "balls", "inns", "outs", "hs"]),
                most_wickets=rows(sw, ["player", "team", "wickets", "runs", "balls", "economy"]))


def season_start(d) -> int:
    """The year a season starts in: April 2026 to March 2027 is the 2026 season (as on the current site's calendar)."""
    d = pd.Timestamp(d)
    return d.year if d.month >= 4 else d.year - 1


def in_played_order(career, rs: list[dict]) -> list[dict]:
    """Result rows in the order the matches were played (the game can save scorecards dated out of order)."""
    order = by_played(career, pd.DataFrame({"match_id": [r["id"] for r in rs]})).match_id
    by_id = {r["id"]: r for r in rs}
    return [by_id[i] for i in order]


def runs_of(outcomes: list[str]) -> list[dict]:
    """The same result in a row: [{o, start, end}], start and end the first and last match of each run."""
    out: list[dict] = []
    for i, o in enumerate(outcomes):
        if out and out[-1]["o"] == o:
            out[-1]["end"] = i
        else:
            out.append(dict(o=o, start=i, end=i))
    return out


def _record(rs: list[dict]) -> dict:
    o = [r["outcome"] for r in rs]
    return dict(played=len(o), won=o.count("W"), lost=o.count("L"), drawn=o.count("D"),
                other=len(o) - o.count("W") - o.count("L") - o.count("D"))


FORM_GAMES = 5   # the form line: the share of the last five matches won


def form(rs: list[dict], n: int = FORM_GAMES) -> dict:
    """The form line for matches in played order: after each match, the share of the last n won (wins and defeats
    only; None when none of them had a result), the first n-1 still building up; the best and worst full five, how
    it's going now against five matches before, and each series over its matches with its score."""
    pct: list[int | None] = []
    for i in range(len(rs)):
        last = [r["outcome"] for r in rs[max(0, i - n + 1): i + 1] if r["outcome"] in ("W", "L")]
        pct.append(round(last.count("W") / len(last) * 100) if last else None)
    full = [i for i in range(n - 1, len(rs)) if pct[i] is not None]
    best = max(full, key=lambda i: (pct[i], -i)) if full else None    # the first time it was this high
    worst = min(full, key=lambda i: (pct[i], i)) if full else None
    trend = None
    now = len(rs) - 1
    if now >= n - 1:   # now None: none of the last five had a result (five draws in Tests)
        prev = pct[now - n] if now - n >= n - 1 else None
        word = ("" if prev is None or pct[now] is None else
                "up" if pct[now] > prev else "down" if pct[now] < prev else "level")
        trend = dict(now=pct[now], prev=prev, word=word)
    groups: list[dict] = []
    for i, r in enumerate(rs):
        if not r["series"]:
            continue
        if groups and groups[-1]["series"] == r["series"] and groups[-1]["end"] == i - 1:
            groups[-1]["end"] = i
        else:
            groups.append(dict(series=r["series"], opp=r["opp"], start=i, end=i))
    for g in groups:
        o = [x["outcome"] for x in rs[g["start"]: g["end"] + 1]]
        g.update(won=o.count("W"), lost=o.count("L"))
    return dict(n=n, pct=pct, best=best, worst=worst, trend=trend, groups=groups)


def calendar(career, team: str) -> dict:
    """The team's season, April to March (the season of its latest match): every match in played order, each month's
    record (the best month marked), the formats (longest game first, for the colour under each match) and the runs
    of results through the season.

    A series or a tournament belongs whole to the season most of it is played in, so the IPL starting on 29 March
    stays with the rest of its season: its March games are counted in April's tile and listed at its top (and any
    played after the end of March, in March's)."""
    rs = results(career, team)
    if not rs:
        raise ValueError("The team hasn't played yet.")
    m = career.matches
    year_of = SN.april_seasons(m[m.match_id.isin([r["id"] for r in rs])])   # a tournament goes whole to its season
    latest = in_played_order(career, rs)[-1]
    y = int(year_of[latest["id"]])
    start, end = f"{y}-04-01", f"{y + 1}-03-31"
    rs = in_played_order(career, [r for r in rs if year_of[r["id"]] == y])
    months = []
    for k in range(12):
        yy, mm = (y, 4 + k) if k < 9 else (y + 1, k - 8)
        x = [r for r in rs if r["date"].startswith(f"{yy}-{mm:02d}")]
        extra = [r for r in rs if (k == 0 and r["date"] < start) or (k == 11 and r["date"] > end)]
        x = extra + x if k == 0 else x + extra
        names = list(dict.fromkeys(f"v {r['opp']}" if r["series"] else r["event"] for r in x))
        months.append(dict(year=yy, month=mm, **_record(x), names=names, extra=extra))
    busy = [i for i, mo in enumerate(months) if mo["played"]]
    best = max(busy, key=lambda i: (months[i]["won"] - months[i]["lost"] + months[i]["played"] / 100, -i)) if busy else None
    fm = career.matches.set_index("match_id").format
    count: dict[str, int] = {}
    kind: dict[str, str] = {}
    for r in rs:
        count[r["section"]] = count.get(r["section"], 0) + 1
        kind[r["section"]] = KIND.get(fm.get(r["id"], ""), "t20")
    order = {"multi": 0, "one": 1, "t20": 2}
    formats = [dict(section=s, kind=kind[s]) for s in sorted(count, key=lambda s: (order[kind[s]], -count[s], s))]
    return dict(year=y, start=start, end=end, results=rs, months=months, best=best, formats=formats,
                streaks=runs_of([r["outcome"] for r in rs]))


def venues(rs: list[dict], team: str) -> dict:
    """The record at home, away and on neutral grounds, then host by host (the scorecards don't name the ground, so
    it goes by the home side: for a national side, the country)."""
    out = {k: _record([r for r in rs if r["venue"] == k]) for k in ("home", "away", "neutral")}
    hosts: dict[str, list[dict]] = {}
    for r in rs:
        hosts.setdefault("" if r["venue"] == "neutral" else r["host"], []).append(r)
    out["hosts"] = sorted(([dict(host=h, venue="neutral" if not h else "home" if h == team else "away",
                                 outcomes=[r["outcome"] for r in x], **_record(x)) for h, x in hosts.items()]),
                          key=lambda h: (-h["played"], h["venue"] != "home", h["host"]))
    out["nation"] = nation_of([team]) == team
    return out


def strength(career, team: str, rs: list[dict]) -> list[dict]:
    """Every match with both sides' rating (Elo) just before it, in its section: gap = theirs minus ours."""
    out = []
    hist = {sec: team_elo(career, sec)[1].set_index(["match_id", "team"]).before for sec in {r["section"] for r in rs}}
    for r in rs:
        h = hist[r["section"]]
        me, them = h.get((r["id"], team)), h.get((r["id"], r["opp"]))
        if me is None or them is None:   # no result: not rated
            continue
        out.append(dict(id=r["id"], date=r["date"], section=r["section"], opp=r["opp"], outcome=r["outcome"],
                        me=round(me), them=round(them), gap=round(them - me)))
    return out


def bat_first(career, team: str, ids) -> dict:
    """Batting first or chasing in these matches: the record each way; in a one-innings game also the score usually
    set, the lowest total defended, the highest lost with, the highest chased down and the lowest not chased (games
    shortened by rain left out of the totals)."""
    g = TP.games(career, ids)
    t = g[g.team == team]
    if t.empty:
        raise ValueError("No matches for the team here yet.")
    res = career.matches.set_index("match_id").result
    first, chase = t[t.batted_first], t[~t.batted_first]
    rec = lambda x: dict(played=len(x), won=int((x.outcome == "W").sum()), lost=int((x.outcome == "L").sum()))  # noqa: E731
    out = dict(first=rec(first), chase=rec(chase), multi=TP.is_multi(t))
    if not out["multi"]:
        def pick(x, outcome, high):
            x = x[(x.outcome == outcome) & x.first_score.notna()]
            if x.empty:
                return None
            r = x.loc[x.first_score.idxmax() if high else x.first_score.idxmin()]
            return dict(score=int(r.first_score), opp=r.opponent, date=clean(r.date), result=res[r.match_id])
        set_ = first.first_score.dropna()
        out.update(avg_set=round(float(set_.mean())) if len(set_) else None,
                   lowest_defended=pick(first, "W", False), highest_lost=pick(first, "L", True),
                   highest_chased=pick(chase, "W", True), lowest_missed=pick(chase, "L", False))
    return out


def scores(rs: list[dict]) -> dict:
    """Our score and theirs: the average first innings each way (one-innings games, rain left out), won and lost."""
    one = [r for r in rs if r["ours"] and r["theirs"] and not r["rain"] and len(r["ours"]) == 1]
    avg = lambda k: round(sum(r[k][0]["runs"] for r in one) / len(one)) if one else None  # noqa: E731
    return dict(avg_made=avg("ours"), avg_conceded=avg("theirs"), **_record(rs))


def match_winners(rs: list[dict], team: str) -> dict:
    """Who won the team's matches: its players of the match in its wins, most first, with each match."""
    by: dict[str, list[dict]] = {}
    for r in rs:
        if r["outcome"] == "W" and r["pom"] and r["pom_team"] == team:
            by.setdefault(r["pom"], []).append(dict(id=r["id"], date=r["date"], section=r["section"], opp=r["opp"],
                                                    headline=r["headline"]))
    wins = sum(r["outcome"] == "W" for r in rs)
    return dict(players=[dict(player=p, matches=x) for p, x in sorted(by.items(), key=lambda kv: (-len(kv[1]), kv[0]))],
                wins=wins, others=wins - sum(len(x) for x in by.values()))


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
        out["missing"]["everything"] = NO_MATCHES
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
    piece("this_season", lambda: in_played_order(career, results(career, team, ids)))   # this season here, oldest first
    piece("form", lambda: form(out["this_season"] or []))
    piece("scores", lambda: scores(out["this_season"] or []))
    piece("bat_first", lambda: bat_first(career, team, ids))
    piece("calendar", lambda: calendar(career, team))   # the whole season, every format: April to March
    season_rs = (out["calendar"] or {}).get("results", [])
    piece("venues", lambda: venues(season_rs, team))
    piece("strength", lambda: strength(career, team, season_rs))
    piece("winners", lambda: match_winners(season_rs, team))
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
