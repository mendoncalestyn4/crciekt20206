"""Insights (stage 3): questions about a whole competition, as the current site's page asks them (views/insights.py):
what total wins games, the chase calculator, how much home matters, how scoring changes from season to season, who has
suddenly got better and how each innings of a long match plays. New (your answers 7 and 14 of 13 November): the score
to aim for of your team (or any team) against every opponent, at home, away and on neutral grounds (in multi-day
cricket the first-innings totals that won, drew and lost), with that team's record batting first and chasing and
against stronger and weaker sides.

Every competition is one at a time here: a total, a chase, a season's scoring or a pitch wearing in a T20 means nothing
next to a Test's (your rule of 14 November: combining stays out where it has no meaning). The sums are in the engine
(ccstats/insights.py, teamplay.py, winprob.py, aim.py); this only turns them into what the page shows."""

from __future__ import annotations

import numpy as np

from ccstats import aim as AIM
from ccstats import insights as I
from ccstats import teamplay as TP
from ccstats import winprob as WP
from ccstats.stats import kind_of, ordinal, poss

from . import styleguide as SG
from .cache import aim_fits, kept
from .leaderspage import _strength_of
from .teampage import _n, choices, fmt, pct, secs_of, table

TABS = ["Is this total enough?", "Score to aim for", "Chase calculator", "Home advantage", "Season by season",
        "Breakout players", "Innings by innings"]
EVERY = "Every team"
CHASE_DEFAULTS = {"t20": (181, 60), "one": (281, 120), "multi": (250, 80)}   # the current site's starting target and score
MINS = [3, 5, 8, 10]                                                          # breakouts: innings needed in both


def _int(q: dict, key: str, lo: int, hi: int) -> int | None:
    """A typed number from the address, kept inside what the page allows (None when nothing sensible was typed)."""
    try:
        v = int(float(str(q.get(key, "")).strip()))
    except (TypeError, ValueError, OverflowError):
        return None
    return min(max(v, lo), hi)


def insights_page(career, q: dict, mine: list[str]) -> dict:
    ch = choices(career)
    if not ch:   # a career made before any game was played
        return SG.clean(dict(choices=[], none=SG.NO_MATCHES, tabs=TABS, tab=TABS[0]))
    tab = q.get("tab") if q.get("tab") in TABS else TABS[0]
    m = career.matches
    every = [c["section"] for c in ch]
    kinds = kept(career, ("insights_kinds",), lambda: {s: kind_of(m[m.section == s]) for s in every})
    options = [s for s in every if kinds.get(s) == "multi"] if tab == "Innings by innings" else every
    head = dict(choices=[dict(section=c["section"], matches=c["matches"]) for c in ch], tabs=TABS, tab=tab, options=options)
    if tab == "Home advantage":
        return SG.clean({**head, **kept(career, ("insights_home",), lambda: _home(career, every))})
    if not options:
        return SG.clean({**head, "none": "No multi-day cricket (Tests or first-class) yet."})
    asked = [s for s in secs_of(q.get("section", "")) if s in set(options)]
    sec = asked[0] if asked else options[0]
    head["section"] = sec
    mine_t = tuple(mine)
    if tab == TABS[0]:
        season, team, score = str(q.get("season", "")), str(q.get("team", "")), _int(q, "score", 0, 1500)
        body = kept(career, ("insights_total", sec, season, team, score, mine_t),
                    lambda: _total(career, sec, season, team, score, mine))
    elif tab == TABS[1]:
        team = str(q.get("team", ""))
        body = kept(career, ("insights_aim", sec, team, mine_t), lambda: _aim(career, sec, team, mine))
    elif tab == TABS[2]:
        args = (_int(q, "target", 1, 1000), _int(q, "now", 0, 1000), _int(q, "down", 0, 9))
        body = kept(career, ("insights_chase", sec) + args, lambda: _chase(career, sec, *args))
    elif tab == TABS[4]:
        body = kept(career, ("insights_seasons", sec), lambda: _seasons(career, sec))
    elif tab == TABS[5]:
        season, least = str(q.get("season", "")), _int(q, "min", 0, 99)
        body = kept(career, ("insights_breakouts", sec, season, least), lambda: _breakouts(career, sec, season, least))
    else:
        body = kept(career, ("insights_innings", sec), lambda: _innings(career, sec))
    return SG.clean({**head, **body})


# --------------------------------------------------------------------------- is this total enough?
def _total(career, sec, season, team, score, mine) -> dict:
    m = career.matches
    here = m[m.section == sec]
    seasons = sorted(map(str, here.season.unique()), reverse=True)
    season = season if season in seasons else ""
    ids = list((here[here.season.astype(str) == season] if season else here).match_id)
    where = sec + (f" in {season}" if season else "")
    out: dict = dict(seasons=seasons, season=season)
    bands, size = I.total_enough(career, ids)
    if bands.empty:
        out["none"] = "No finished matches here yet."
        return out
    kind = kind_of(m[m.match_id.isin(ids)])
    multi = kind == "multi"
    what = "first-innings score" if multi else "score batting first"
    default = int(np.median(I.first_innings(career, ids).runs))
    score = default if score is None else score
    out.update(what=what, score=score, default=default, multi=multi)
    c = I.chance_with(career, ids, score)
    a, b = c["at_least"], c["below"]
    out["board"] = dict(label=where, pct=pct(a["pct"]), line=f"won with {score} or more ({a['won']} of {a['matches']})",
                        res=f"With less than {score}: won {b['won']} of {b['matches']} ({pct(b['pct'])})")
    # both sides of a score (the current site's 52): batting first and making it, or keeping them to it and chasing
    in_ids = m[m.match_id.isin(ids)]
    teams = sorted(set(in_ids.home) | set(in_ids.away))
    if team not in teams and team != EVERY:
        team = next((t for t in mine if t in set(teams)), EVERY)
    out.update(teams=[EVERY] + teams, team=team)
    sc = TP.score_chances(career, ids, score, "" if team == EVERY else team)
    who = "" if team == EVERY else f"{team} "
    band = f"first-innings scores from {sc['low']} to {sc['high']}" if sc.get("band") else ""
    sides = []
    for key, title in (("batting_first", f"If {who}batted first and made {score}"),
                       ("bowling_first", f"If {who}kept them to {score} and {'batted second' if multi else 'chased'}")):
        r = sc.get(key)
        if not r or not r["played"]:
            sides.append(dict(title=title, none="No games with a score like this yet."))
            continue
        few = " · few matches, treat with care" if r["decided"] < 8 else ""
        left = f" {r['tied']} tied and {r['no_result']} with no result left out." if r["tied"] or r["no_result"] else ""
        sides.append(dict(title=title, label="Chance of winning", value=pct(r["win_pct"]),
                          note=(f"Won–drawn–lost {r['won']}–{r['drawn']}–{r['lost']}. " if multi else "")
                          + f"Won {r['won']} of {r['decided']} ({band}){few}.{left}"))
    out["sides"] = sides
    out["sides_note"] = ("Built from matches whose first-innings score was close to the one you typed "
                         f"(within {sc.get('band', 0)} runs either way)."
                         + (" Multi-day games can be drawn, so each side shows won-drawn-lost." if multi else
                            " Ties and no-results are left out, so the two sides add up to 100%."))
    # win % batting first, band by band (highest at the top)
    rows = []
    for r in bands[::-1].itertuples():
        rest = (f"{r.won} won, {r.lost} lost" + (f", {r.drawn} drawn" if r.drawn else "") + (f", {r.tied} tied" if r.tied else "")
                + f" · {_n(int(r.matches), 'match', 'matches')}")
        rows.append(dict(label=r.band, value=round(float(r.win_pct), 1), text=f"{r.win_pct:.0f}% · won {r.won} of {r.matches}",
                         note=rest))
    solid = bands[bands.matches >= 3]
    par = None
    for i in range(len(solid) - 1, -1, -1):   # from the top down, while every band wins half or more
        if solid.win_pct.iloc[i] < 50:
            break
        par = solid.iloc[i]
    if par is not None:
        best = (f"from {par.band} upwards the side batting first wins more often than not: {par.win_pct:.0f}% ({par.won} "
                f"of {par.matches}) in that band")
    else:
        best = "no band with 3 or more matches has the side batting first winning half its games yet"
    top = bands.iloc[-1]
    best = best[0].upper() + best[1:] + f". The highest band, {top.band}, won {top.win_pct:.0f}% ({top.won} of {top.matches})."
    out["bands"] = dict(rows=rows, size=size, **SG.lines(
        f"Win % for the side batting first in {where}, for each band of {size} runs of its {what}, highest at the top.",
        best, "Tells you what a winning score looks like here, so you know when you have enough and when to keep pushing. "
              "Hover a bar for how many matches it rests on (one or two matches is a small sample)."
              + (" In multi-day cricket many matches are drawn, so the win % stays lower." if multi else ""),
        best_label="Winning score"))
    # is it enough against a good side? (the current site's 109, kept: your answer 7)
    pbs = I.par_by_strength(career, ids)
    if len(pbs):
        out["strong"] = table([what[0].upper() + what[1:], "v stronger half", "v weaker half"],
                              [[r.band, f"{pct(r.stronger_pct)} ({r.stronger_n})" if r.stronger_n else "–",
                                f"{pct(r.weaker_pct)} ({r.weaker_n})" if r.weaker_n else "–"] for r in pbs.itertuples()],
                              num=[1, 2])
        sp = pbs[(pbs.stronger_n >= 3) & (pbs.stronger_pct >= 50)]
        wp = pbs[(pbs.weaker_n >= 3) & (pbs.weaker_pct >= 50)]
        out["strong"]["note"] = ((f"Against the stronger half you need about {int(sp.low.min())}+ to win more often than not"
                                  if len(sp) else "Against the stronger half no band (3+ games) wins half its games yet")
                                 + (f"; against the weaker half about {int(wp.low.min())}+." if len(wp) else ".")
                                 + " Matches in brackets.")
    return out


# --------------------------------------------------------------------------- the score to aim for (answer 7)
def _aim(career, sec, team, mine) -> dict:
    m = career.matches
    here = m[m.section == sec]
    teams = sorted(set(here.home) | set(here.away))
    if team not in teams:
        team = next((t for t in mine if t in set(teams)), teams[0])
    out: dict = dict(teams=teams, team=team)
    a = AIM.aim_table(career, sec, team, aim_fits(career))
    out["kind"] = a["kind"]
    words = {"home": f"{team} at home", "away": f"{team} away", "neutral": "Neutral ground"}
    if a["none"]:
        out["aim_none"] = a["none"]
    elif a["kind"] == "multi":
        def cell(r, k):
            return f"{r[k]} ({r[k + '_n']})" if r[k + "_n"] else "–"
        out["aim"] = table(["Opponent", "Where", "Won", "Drawn", "Lost", "Mat"],
                           [[r["opp"], words[r["venue"]], cell(r, "won"), cell(r, "drawn"), cell(r, "lost"), r["games"]]
                            for r in a["rows"]], num=[2, 3, 4, 5])
        out["aim"]["note"] = (f"{poss(team)} first-innings total against each side, at home, away and on neutral grounds: the "
                              "typical (middle) one in the games won, drawn and lost, with how many games in brackets. In "
                              "multi-day cricket the first-innings total doesn't decide the match on its own (declarations, "
                              "the follow-on and draws do), so this shows the totals that did instead of one target.")
    else:
        vs = a["venues"]
        cols = ["Opponent"] + [f"{x} {w}" for v in vs for x, w in [({"home": "Home", "away": "Away", "neutral": "Neutral"}[v], "even"),
                                                                    ({"home": "Home", "away": "Away", "neutral": "Neutral"}[v], "70%")]]
        cols += ["Mat", "Note"]
        def val(t, key):
            guess = (key == "seventy" and t["beyond"]) or (key == "even" and t["below"])
            return f"{t[key]}{'†' if guess else ''}"
        rows = [[r["opp"]] + [val(r[v], k) for v in vs for k in ("even", "seventy")] + [r["met"], "few games" if r["few"] else ""]
                for r in a["rows"]]
        out["aim"] = table(cols, rows, num=list(range(1, 2 * len(vs) + 2)))
        home = a["home"]
        out["aim"]["note"] = (
            f"Batting first against each side: the total for an even game (wins half the time) and for a 70% chance (wins "
            f"seven times in ten), the same sums as Opponent preview. Mat: {poss(team)} games against them here. Rests on "
            f"{a['games']} finished games in {sec}; sides batting first against {team} make {_runs(a['my_bowling'])} the "
            f"usual ({_n(a['my_bowling_n'], 'game')}). Judged from all the others, it would have called {a['right']:.0f}% of "
            f"them right (going by the total alone: {a['right_alone']:.0f}%). Playing at home is worth "
            + (f"about {_n(round(home), 'run')} here" if round(home) >= 1 else
               f"about {_n(round(-home), 'run')} less than playing away here" if round(home) <= -1 else "almost nothing here")
            + ". Few games: fewer than 10 games behind part of it, treat with care. † a guess beyond the totals made here "
            "(the 70% total higher than any made batting first, or the even total lower than any).")
    out["aim_lines"] = dict(is_=(f"{poss(team)} score to aim for against every side in {sec}"
                                 + (", the first-innings totals that won, drew and lost." if a["kind"] == "multi" else
                                    ", at home, away and on neutral grounds.")),
                            for_="What to make batting first against whoever is next, wherever it is: the stronger and "
                                 "weaker half view is on “Is this total enough?”.")
    ids = list(here.match_id)
    # batting first v chasing, and against stronger and weaker sides (answer 14), for the team picked
    try:
        x = SG.bat_first(career, team, ids)
    except ValueError:
        x = None
    if x is not None:
        second = "batting second" if x["multi"] else "chasing"
        def share(r):
            return r["won"] / (r["won"] + r["lost"]) * 100 if r["won"] + r["lost"] else None
        f_, c_ = share(x["first"]), share(x["chase"])
        each = [f"batting first, {f_:.0f}% won" if f_ is not None else "", f"{second}, {c_:.0f}% won" if c_ is not None else ""]
        x.update(who=team, **SG.lines(
            f"{poss(team)} wins and defeats batting first and {second} in {sec}, with the totals that decided them.",
            (each[0] if c_ is None or (f_ is not None and f_ > c_) else each[1] if f_ is None or c_ > f_ else
             f"level, {f_:.0f}% won each way") if f_ is not None or c_ is not None else "No wins or defeats yet.",
            "Whether to set a total or chase one at the toss, and the totals that have been enough.", best_label="Better at"))
        out["bat_first"] = x
    out["strength"] = _strength_of(career, team, ids, sec)
    return out


def _runs(x: float) -> str:
    r = int(round(x))
    return "level with" if r == 0 else f"{abs(r)} run{'s' if abs(r) != 1 else ''} {'above' if r > 0 else 'below'}"


# --------------------------------------------------------------------------- chase calculator (the current site's 108)
def _chase(career, sec, target, now, down) -> dict:
    m = career.matches
    ids = list(m[m.section == sec].match_id)
    kind = kind_of(m[m.section == sec])
    t0, s0 = CHASE_DEFAULTS[kind]
    target = t0 if target is None else target
    now = s0 if now is None else now
    down = 3 if down is None else down
    multi = kind == "multi"
    out: dict = dict(target=target, now=now, down=down, multi=multi)
    if now >= target:
        out["won"] = "That's the target reached: the chase is won."
        return out
    st = kept(career, ("win_states", sec), lambda: WP.states(career, ids))
    c = WP.chase_chance(st, kind, target, now, down)
    need = target - now
    if not c["n"]:
        out["chase_none"] = "No games like this yet."
        return out
    out["kpis"] = [dict(k="Chasers win", v=pct(c["win"]))] + ([dict(k="Draw", v=pct(c["draw"]))] if multi else []) + \
        [dict(k="Defenders win", v=pct(c["lose"]))]
    lo, hi = c["wickets_used"]
    wtxt = f"{lo} down" if lo == hi else f"{lo}-{hi} down"
    near = (f"needing within {c['band']:.0f} runs of {need}" if c["band"] < need else
            "needing any number of runs: there aren't enough chases this close yet to narrow it down")
    out["line"] = (f"Needing {need} with {10 - down} wickets left: from {c['n']} {sec} chases in the same spot ({wtxt}, "
                   f"{near}).")
    rows = []
    for w in sorted({max(0, down - 1), down, min(9, down + 1)}):
        x = WP.chase_chance(st, kind, target, now, w)
        rows.append([f"{w} down", pct(x["win"])] + ([pct(x["draw"])] if multi else []) + [x["n"]])
    out["table"] = table(["Wickets down", "Chasers win"] + (["Draw"] if multi else []) + ["Mat"], rows,
                         num=list(range(1, 4 if multi else 3)), hi=[r[0] == f"{down} down" for r in rows])
    out["table"]["note"] = ("How much one wicket either way is worth. The scorecards have no overs, so this is runs and "
                            "wickets only: early in a chase it can't tell a quick start from a slow one."
                            + (" In a Test the draw depends on time left, which the scorecards don't show either."
                               if multi else ""))
    return out


# --------------------------------------------------------------------------- home advantage
def _home(career, order: list[str]) -> dict:
    h = I.home_advantage(career)
    if h.empty:
        return dict(none="No home-and-away matches yet (ICC events are played at neutral venues).")
    rank = {s: i for i, s in enumerate(order)}
    h = h.assign(k=h.section.map(lambda s: rank.get(s, 999))).sort_values("k")   # the agreed order of competitions
    rows = [dict(label=f"{r.section} ({r.matches})", section=r.section, home=round(float(r.home_pct), 1),
                 away=round(float(r.away_pct), 1), other=round(100 - float(r.home_pct) - float(r.away_pct), 1),
                 home_text=f"{r.home_wins} of {r.matches}", away_text=f"{r.away_wins} of {r.matches}",
                 other_text=f"{r.other} of {r.matches}") for r in h.itertuples()]
    hi = h.sort_values(["home_pct", "matches"], ascending=[False, False]).iloc[0]
    lo = h.sort_values(["home_pct", "matches"], ascending=[True, False]).iloc[0]
    return dict(home=dict(rows=rows, **SG.lines(
        "Home wins against away wins in every competition played at home grounds (finished matches, how many in brackets).",
        f"{hi.section}: home sides won {hi.home_pct:.0f}%, away sides {hi.away_pct:.0f}% (least: {lo.section}, "
        f"{lo.home_pct:.0f}% against {lo.away_pct:.0f}%)",
        "Shows how much playing at home is worth in each competition, so you know how much to read into a home or away "
        "result. The first-named team on a scorecard is the home side; World Cups and other ICC events are left out "
        "because they're at neutral grounds.", best_label="Home sides win most")))


# --------------------------------------------------------------------------- season by season
SEASON_MEASURES = [("Runs per wicket", "runs_per_wicket", 1,
                    "Is batting getting easier or harder? More runs per wicket = a batter's game."),
                   ("Run rate (runs per over)", "run_rate", 2,
                    "How fast teams score, so you know what scoring rate keeps you in a game."),
                   ("Sixes per match", "sixes_per_match", 1,
                    "How much big hitting there is: more sixes usually means higher totals."),
                   ("Share of runs in boundaries (%)", "boundary_pct", 1,
                    "How much of the scoring comes in fours and sixes rather than running."),
                   ("Average first-innings score", "first_innings_avg", 0, "The typical score batting first: a quick guide to par."),
                   ("Win % batting first", "bat_first_win_pct", 0,
                    "Whether batting first or chasing pays off more, season by season.")]


def _seasons(career, sec) -> dict:
    bs = I.by_season(career, sec)
    out: dict = dict(charts=[])
    if len(bs) < 2:
        out["one"] = f"Only one season of {sec} so far. Come back after the next one to see how the game changes."
    for label, col, dec, purpose in SEASON_MEASURES:
        vals = bs[["season", col, "matches"]].dropna()
        pts = [dict(season=str(r.season), v=round(float(getattr(r, col)), 4), text=fmt(float(getattr(r, col)), dec),
                    matches=int(r.matches)) for r in vals.itertuples()]
        if len(vals) >= 2:
            a0, a1 = vals.iloc[0], vals.iloc[-1]
            change = (a1[col] - a0[col]) / a0[col] * 100 if a0[col] else 0
            best = f"{fmt(a0[col], dec)} in {a0.season}, {fmt(a1[col], dec)} in {a1.season} ({change:+.0f}%)."
        elif len(vals):
            best = f"{fmt(vals.iloc[0][col], dec)} in {vals.iloc[0].season}, the only season so far."
        else:
            best = ""
        out["charts"].append(dict(label=label, id=col, dec=dec, points=pts, **SG.lines(
            f"{label} in each season of {sec}.", best, purpose, best_label="First to latest")))
    return out


# --------------------------------------------------------------------------- breakout players
def _breakouts(career, sec, season, least) -> dict:
    m = career.matches
    seasons = sorted(map(str, m[m.section == sec].season.unique()), reverse=True)
    season = season if season in seasons else seasons[0]
    least = least if least in MINS else 5
    earlier = any(s < season for s in seasons)
    out: dict = dict(seasons=seasons, season=season, mins=MINS, min=least, earlier=earlier)
    if not earlier:
        out["first"] = f"{season} is the first season of {sec} here, so there's nothing earlier to compare with."
        return out
    real = next(s for s in m[m.section == sec].season.unique() if str(s) == season)
    bat, bowl = I.breakouts(career, sec, real, least)
    parts = []
    for d, title, unit in ((bat, "Batters", "runs above average per innings"), (bowl, "Bowlers", "runs saved per innings")):
        top = d[d.jump > 0].head(10) if len(d) else d
        part = dict(title=f"{title} who improved most", sub=f"{unit}, {season} against their earlier seasons")
        if top.empty:
            part["none"] = f"Nobody with {least}+ innings in both periods improved."
        else:
            part["rows"] = [dict(label=r.player, value=round(float(r.jump), 2), text=f"{r.jump:+.1f}",
                                 note=f"{season}: {fmt(r.now, 1)} ({int(r.now_innings)} inns) · before: {fmt(r.before, 1)} "
                                      f"({int(r.before_innings)} inns)") for r in top.itertuples()]
            r0 = top.iloc[0]
            part.update(**SG.lines(
                f"The {title.lower()} with {least}+ innings in {season} and before whose {unit} rose most.",
                f"{r0.player}: {fmt(r0.now, 1)} in {season} against {fmt(r0.before, 1)} before ({r0.jump:+.1f})",
                f"Spots the {title.lower()} who have stepped up this season, so you can give them a bigger role (or sign "
                "them).", best_label="Improved most"))
        parts.append(part)
    out["parts"] = parts
    out["note"] = ("Each season is measured against that season's own average, so a year when everyone scored more doesn't "
                   "make everyone look improved. Hover a bar for the before-and-after figures.")
    return out


# --------------------------------------------------------------------------- innings by innings (the current 35, 36)
def _innings(career, sec) -> dict:
    m = career.matches
    ids = list(m[m.section == sec].match_id)
    out: dict = {}
    ib = TP.innings_by_number(career, ids)
    if ib.empty:
        out["innings_none"] = "No innings yet."
    else:
        first = float(ib.runs_per_wicket.iloc[0])
        rows = []
        for i, r in enumerate(ib.itertuples()):
            v = float(r.runs_per_wicket)
            rows.append(dict(label=f"{ordinal(int(r.innings))} innings", value=round(v, 2),
                             text=f"{v:.1f} ({(v - first) / first * 100:+.0f}% v the 1st)" if i and first else f"{v:.1f}",
                             note=f"{r.innings_played} innings · average total {r.average_total:.0f} · run rate "
                                  f"{r.run_rate:.2f} · all out {r.all_out_pct:.0f}%"))
        last = ib.iloc[-1]
        lv = float(last.runs_per_wicket)
        out["innings"] = dict(rows=rows, **SG.lines(
            f"Runs per wicket in each innings of the match in {sec}.",
            (f"The {ordinal(int(last.innings))} innings averages {lv:.1f} runs per wicket against {first:.1f} in the 1st"
             + (f" ({(lv - first) / first * 100:+.0f}%)." if first else ".")),
            "Shows how much harder batting gets as the pitch wears, which tells you how big a fourth-innings target "
            "really is and whether to bat first.", best_label="Latest innings v the 1st"))
    fl = WP.first_innings_lead(career, ids)
    if fl.matches.sum() == 0:
        out["lead_none"] = "No finished games yet."
    else:
        played = fl[fl.matches > 0]
        out["lead"] = table(["Lead", "Mat", "Won", "Drawn", "Lost"],
                            [[r.band, int(r.matches), pct(r.won), pct(r.drawn), pct(r.lost)] for r in played.itertuples()],
                            num=[1, 2, 3, 4])
        big = fl[fl.matches >= 3].sort_values("won", ascending=False).head(1)
        if len(big):
            out["lead"]["note"] = (f"A lead of {big.band.iloc[0]} won {big.won.iloc[0]:.0f}% of {int(big.matches.iloc[0])} "
                                   "games. Bigger leads also mean fewer draws, because the side behind has to bat twice to "
                                   "catch up.")
    fo = TP.follow_on_and_declarations(career, ids)
    if fo.empty:
        out["follow_none"] = "No follow-ons or declarations yet."
    else:
        out["follow"] = table(["Situation", "Times", "Won–drawn–lost", "Win %"],
                              [[r.situation, int(r.times), f"{r.won}–{r.drawn}–{r.lost}", pct(r.win_pct)] for r in fo.itertuples()],
                              num=[1, 3])
        out["follow"]["note"] = ("A follow-on is spotted when the side batting second batted again straight away. "
                                 "Won-drawn-lost is from the point of view of the side in that row.")
    return out
