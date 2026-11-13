"""Opponent preview (stage 2): your team and the team you're about to play, as the current site's Opponent preview
shows them: their record and form, the predicted result, a game plan, then four tabs (head to head with who gets whom
out, about them, side by side, your best XI against them). Every number comes from the same engine functions with the
same words; it opens on your next match (from your schedule, or the rest of a series under way), else your latest."""

from __future__ import annotations

import functools

import numpy as np
import pandas as pd

from ccstats import aim as AIM
from ccstats import howtheyplay as HP
from ccstats import moments as MO
from ccstats import analysis as A
from ccstats import catalogue as CAT
from ccstats import extras as E
from ccstats import fixtures as FX
from ccstats import preview as PV
from ccstats import seasonal as SN
from ccstats import teamplay as TP
from ccstats import winprob as WP
from ccstats.competitions import with_stage
from ccstats.stats import ordinal, poss

from . import styleguide as SG
from .cache import aim_fits, kept
from .teampage import _n, fmt, pct, say, signed, table

INTL = "Internationals"
FMT_SECTION = {"Test": "Tests", "ODI": "ODIs", "T20I": "T20Is"}
ONE = {"Tests": "a Test", "ODIs": "an ODI", "T20Is": "a T20I"}
TABS = ["Head to head", "About them", "Side by side", "Your best XI v them"]


def _sig(career, ids):
    return tuple(ids)


def page(career, q: dict, mine_all: list[str], mine_order: list[str], sched: list, remembered: dict | None = None) -> dict:
    """The pickers (with the defaults), the top of the page and one tab, or a plain reason there's nothing."""
    m = career.matches
    if m.empty:   # a career made before any game was played
        return SG.clean(dict(choices=[], section="", formats=[], format="", mine_opts=[], mine="", opp="", opp_opts=[],
                             none=SG.NO_MATCHES, elsewhere=[], tabs=TABS, tab=TABS[0]))
    intl = [s for s in ("Tests", "ODIs", "T20Is") if s in set(m.section)]
    counts = m.section.value_counts()
    choices = ([INTL] if intl else []) + [s for s in counts.index if s not in intl]
    up = kept(career, ("upcoming", repr(sched), tuple(mine_order)), lambda: FX.upcoming(career, sched, tuple(mine_order))) \
        if mine_order else None
    nxt = up.iloc[0] if up is not None and len(up) else None

    def place_of(team, fmt_):
        if fmt_ in FMT_SECTION and FMT_SECTION[fmt_] in intl:
            return INTL, FMT_SECTION[fmt_]
        x = m[(m.format == fmt_) & ((m.home == team) | (m.away == team))].sort_values("date")
        return (x.section.iloc[-1] if len(x) else None), None

    pick, fmt_pick, mine, opp = q.get("section", ""), q.get("format", ""), q.get("mine", ""), q.get("opp", "")
    where_default = "Neutral"
    if pick not in choices:   # first look: your next match, else your latest game
        start = None
        last_pick = (remembered or {}).get("section", "")
        if nxt is not None:
            start = (nxt["team"], nxt["format"], nxt["opponent"])
        elif last_pick in intl or last_pick in choices:   # no next match: the competition you last picked anywhere
            pick, fmt_pick = (INTL, last_pick) if last_pick in intl else (last_pick, "")
        elif mine_order:
            last_ = m[m.home.isin(mine_order) | m.away.isin(mine_order)].sort_values("date")
            if len(last_):
                r_ = last_.iloc[-1]
                me_ = r_.home if r_.home in mine_order else r_.away
                start = (me_, r_.format, r_.away if r_.home == me_ else r_.home)
        if pick not in choices:
            pick = choices[0]
        if start is not None:
            sec_, fmt_ = place_of(start[0], start[1])
            if sec_ in choices:
                pick, fmt_pick, mine, opp = sec_, fmt_ or fmt_pick, mine or start[0], opp or start[2]
                if nxt is not None and nxt["venue"] in ("home", "away", "neutral"):
                    where_default = nxt["venue"].title()
    group = m[m.section.isin(intl)] if pick == INTL else m[m.section == pick]
    formats = []
    if pick == INTL:
        formats = intl + ["All"]
        if fmt_pick not in formats:
            mg = group[group.home.isin(mine_order) | group.away.isin(mine_order)].sort_values("date")
            fmt_pick = mg.section.iloc[-1] if len(mg) else intl[0]
        sections = intl if fmt_pick == "All" else [fmt_pick]
    else:
        fmt_pick = ""
        sections = [pick]
    ids = m[m.section.isin(sections)].match_id
    here = m[m.match_id.isin(ids)]
    fmt_teams = set(here.home) | set(here.away)
    where_note = " + ".join(sections)
    fmt_words = "games here" if len(sections) > 1 or pick != INTL else sections[0]
    group_teams = set(group.home) | set(group.away)
    for s_ in sections:
        group_teams |= CAT.section_teams(m[m.section == s_], s_)[1]
    group_teams = sorted(group_teams)
    yours = [t for t in mine_all if t in group_teams or (pick == INTL and t in FX.NATIONS)]
    mine_opts = ["—"] + yours + [t for t in group_teams if t not in yours]
    if mine not in mine_opts:
        mine = yours[0] if yours else "—"
    group_fmts = set(group.format)
    sched_t = up[(up.team == mine) & up.format.isin(group_fmts)] if up is not None and len(up) and mine != "—" else None
    sched_opps = list(dict.fromkeys(sched_t.opponent)) if sched_t is not None else []
    opp_opts = sorted((set(group_teams) | set(sched_opps)) - {mine})
    out = dict(choices=[dict(section=c, matches=int(counts[intl].sum()) if c == INTL else int(counts[c])) for c in choices],
               section=pick, formats=formats, format=fmt_pick, mine_opts=mine_opts, mine=mine, opp="", opp_opts=[],
               none="", elsewhere=[], tabs=TABS, tab=q.get("tab", "") if q.get("tab", "") in TABS else TABS[0])
    if len(opp_opts) < 1:
        out["none"] = "Not enough teams here yet."
        return SG.clean(out)
    if opp not in opp_opts:
        if sched_opps and sched_opps[0] in opp_opts:
            opp = sched_opps[0]
        else:
            met_ = here[(here.home == mine) | (here.away == mine)].sort_values("date")
            last_opp = (met_.away.iloc[-1] if met_.home.iloc[-1] == mine else met_.home.iloc[-1]) if len(met_) else None
            opp = last_opp if last_opp in opp_opts else opp_opts[0]

    def opp_label(t):
        tags = []
        if sched_opps and t == sched_opps[0]:
            tags.append("next")
        elif t in sched_opps:
            tags.append("scheduled")
        if t not in fmt_teams:
            tags.append(f"no {fmt_words if fmt_words != 'games here' else 'games'} yet")
        return t + (f" ({', '.join(tags)})" if tags else "")
    out.update(opp=opp, opp_opts=[dict(team=t, label=opp_label(t)) for t in opp_opts])
    if opp not in fmt_teams:
        by_sec = group[(group.home == opp) | (group.away == opp)].section.value_counts()
        if pick == INTL and len(by_sec) and fmt_pick != "All":
            out["none"] = (f"{opp} haven't played {ONE.get(fmt_pick, fmt_pick)} in this career yet. They have played "
                           + ", ".join(f"{n} {s}" for s, n in by_sec.items()) + ": switch the format to see them.")
            out["elsewhere"] = list(by_sec.index)
        else:
            out["none"] = (f"{opp} haven't played a game here in this career yet. Their preview fills in as soon as they have"
                           + (f" (they're in your schedule: {sched_t[sched_t.opponent == opp].series.iloc[0].replace(FX.AUTO, '')})."
                              if opp in sched_opps else "."))
        return SG.clean(out)
    me = None if mine == "—" else mine
    out["mine_note"] = (f"{me} haven't played {ONE.get(fmt_words, 'here')} yet in this career: your history against {opp}, "
                        "side by side and your best XI fill in after your first. Their side of the preview is below."
                        if me and me not in fmt_teams else "")
    out["where_note"] = where_note
    key = (tuple(sections), me, opp)
    out["head"] = kept(career, ("preview_head",) + key, lambda: _head(career, ids, me, opp, where_note, where_default))
    tab = out["tab"]
    mu = q.get("mu", "") == "every"
    cur = q.get("cur", "") == "1"
    last = tab == "About them" and q.get("htp", "") == "last"
    out["body"] = kept(career, ("preview_tab", tab, mu, cur, last) + key,
                       lambda: (functools.partial(about_them, last=last) if tab == "About them" else TAB_FN[tab])(
                           career, ids, me, opp, where_note, mu, cur))
    out["mu"], out["cur"], out["htp"] = mu, cur, "last" if last else ""
    return SG.clean(out)


def _parts():
    out = {"missing": {}}

    def part(name, fn):
        try:
            out[name] = SG.clean(fn())
        except Exception as e:  # noqa: BLE001 - one part that can't be worked out never stops the others
            out[name] = None
            out["missing"][name] = f"Couldn't be worked out ({type(e).__name__}: {e})"
    return out, part


def _pv(career, ids, opp):
    return kept(career, ("opponent_preview", tuple(ids), opp), lambda: E.opponent_preview(career, ids, opp))


def _head(career, ids, me, opp, where_note, where_default) -> dict:
    out, part = _parts()
    pv = _pv(career, ids, opp)
    rec = A.team_record(pv["matches"])
    out.update(kpis=[dict(k="Played", v=f"{rec['played']}"), dict(k="Won–Lost", v=f"{rec['won']}–{rec['lost']}"),
                     dict(k="Win %", v=fmt(rec["win_pct"], 0) + "%" if rec["played"] else "–"),
                     dict(k="Collapses", v=f"{pv['collapses']}")],
               last5=list(pv["recent"].outcome),
               caption=f"{opp} in {where_note}. Last 5: W won, L lost, D drawn, T tied, oldest first. Collapses: innings "
                       f"where they lost 4 or more wickets for 30 runs or fewer, out of {pv['innings']} innings.",
               where_default=where_default)
    if me:
        def predicted():
            res = {}
            for where in ("Home", "Away", "Neutral"):
                pr = WP.predict(career, ids, me, opp, where.lower())
                parts = [f"{me} {pr['win']:.0f}%"] + ([f"draw {pr['draw']:.0f}%"] if pr["multi"] else []) + [f"{opp} {pr['lose']:.0f}%"]
                rows = [[name, why, (f"{val:.0f}%" if i == 0 else f"{val + 0.0:+.1f}".replace("-0.0", "0.0").replace("+0.0", "0.0"))]
                        for i, (name, why, val) in enumerate(pr["steps"])]
                res[where] = dict(line=" · ".join(parts), steps=table(["Step", "Why", f"{me} chance (start, then change)"], rows, num={2}),
                                  note="Built in steps: the Elo chance first, then small nudges for recent form, head to head "
                                       "and home ground, each capped so no single one can swing it far."
                                       + (" In multi-day cricket the draw share comes from how often games here are drawn."
                                          if pr["multi"] else ""))
            return res
        part("predicted", predicted)
        part("plan", lambda: list(PV.game_plan(career, ids, me, opp)))
        part("aim", lambda: _aim(career, ids, me, opp))
    return out


def _aim(career, ids, me, opp) -> dict:
    """The score to aim for batting first, at home, away and on a neutral ground (ccstats.aim); in multi-day cricket the
    first-innings totals that won, drew and lost against them instead."""
    a = kept(career, ("score_to_aim", tuple(ids), me, opp), lambda: AIM.score_to_aim(career, ids, me, opp, aim_fits(career)))
    out = dict(none=a["none"], kind=a.get("kind", ""), venues={})
    if a["none"]:
        return out
    if a["kind"] == "multi":
        said = {"won": "won", "drawn": "drew", "lost": "lost"}
        for where, v in a["venues"].items():
            t, g = v["typical"], v["games"]
            got = [f"when they {said[r]}, usually {t[r]['typical']} ({_n(t[r]['n'], 'game')})"
                   for r in ("won", "drawn", "lost") if t[r]["n"]]
            out["venues"][where.capitalize()] = dict(
                line=(f"{poss(me)} first-innings total against {opp}: " + "; ".join(got) + ".") if got else "",
                none="" if g else f"{me} haven't played {opp} {_ground(where, me)} yet.",
                games=table(["Date", f"{poss(me)} first innings", "Result"],
                            [[x["date"], f"{x['total']}" + ("" if x["all_out"] else f"/{x['wickets']}"
                                                            + (" dec" if x["declared"] else "")), x["text"]] for x in g],
                            links=[x["id"] for x in g]) if g else None)
        out["note"] = ("In multi-day cricket the first-innings total doesn't decide the match on its own (declarations, the "
                       "follow-on and draws do), so instead of one target this shows the first-innings totals that won, "
                       "drew and lost against them, at home, away and on neutral grounds: the typical (middle) one of each, "
                       "and every game under it.")
        return out
    for where, v in a["venues"].items():
        line = f"{v['even']} for an even game · {v['seventy']} for a 70% chance"
        warn = []
        if v["beyond"]:
            warn.append("the 70% total is more than any side has made batting first here, so it's a guess beyond what "
                        "has been seen")
        if v["below"]:
            warn.append("even a total lower than any made here would make it an even game, so it's a guess below what "
                        "has been seen")
        if v["they_set"] is not None:
            they = (f"{opp} set {v['they_set']} batting first against {me} {_ground(where, me)}, in their one game."
                    if v["they_set_n"] == 1 else
                    f"{opp} usually set {v['they_set']} batting first against {me} {_ground(where, me)} ({v['they_set_n']} games).")
        elif v.get("they_usual") is not None:
            they = (f"{opp} have never batted first against {me} {_ground(where, me)}. Against everyone, {_ground(where, opp, True)}, "
                    + (f"they set {v['they_usual']} in their one game." if v["they_usual_n"] == 1 else
                       f"they usually set {v['they_usual']} ({v['they_usual_n']} games)."))
        else:
            they = f"{opp} haven't batted first {_ground(where, opp, True)} in these games yet."
        meet = v["meetings"]
        out["venues"][where.capitalize()] = dict(
            line=line, warn=("Careful: " + "; ".join(warn) + ".") if warn else "", they=they,
            meetings=table(["Date", "Innings", "Result"], [[x["date"], x["first"], x["result"]] for x in meet],
                           links=[x["id"] for x in meet]) if meet else None)
    home = a["home"]
    v = next(iter(a["venues"].values()))      # their batting and your bowling are the same wherever it is
    out["rests"] = (f"Rests on {a['games']} finished games in {a['section']}. {opp} batting first make "
                    f"{_runs(v['their_batting'])} the usual ({_n(v['their_batting_n'], 'game')}); sides batting first "
                    f"against {me} make {_runs(v['my_bowling'])} the usual ({_n(v['my_bowling_n'], 'game')}).")
    out["few"] = "Few games, treat with care: fewer than 10 games behind part of this." if v["few"] else ""
    out["sure"] = (f"Judged from all the others, it would have called {a['right']:.0f}% of the {a['games']} finished games "
                   f"in {a['section']} right (going by the total alone: {a['right_alone']:.0f}%).")
    out["note"] = ("Worked out from every finished game where a side batted first (rain games, ties and no-results left "
                   "out), every team, not just these two: how the chance of winning rises with the total is learned from all "
                   "cricket of this length, and this competition keeps its own level of totals; playing at home is worth "
                   + (f"about {_n(round(home), 'run')} here" if round(home) >= 1 else
                      f"about {_n(round(-home), 'run')} less than playing away here" if round(home) <= -1 else
                      "almost nothing here")
                   + " (it starts near nothing and grows only as the games show it); and how well they bat and you bowl, in "
                   "runs against the usual, counts more the more games there are (5 games count half). Even game: the total "
                   "that wins half the time; 70%: the one that wins seven times in ten.")
    return out


def _runs(x: float) -> str:
    """'+12 runs on' / '8 runs under' / 'level with' the usual."""
    r = int(round(x))
    return "level with" if r == 0 else f"{abs(r)} run{'s' if abs(r) != 1 else ''} {'above' if r > 0 else 'below'}"


def _ground(where: str, team: str, own: bool = False) -> str:
    """Where a game was, said plainly: from `team`'s side ('when India are at home'), or with `own` for the opponent
    on their own ('at home', since our away is their home)."""
    if where == "neutral":
        return "on neutral grounds"
    if own:
        return "at home" if where == "away" else "away from home"
    return f"when {team} are {'at home' if where == 'home' else 'away'}"


def _their_record(career, ids, opp, where_note, part) -> None:
    """Under the head-to-head record: the opponent's own record batting first and chasing, and at home, away and on
    neutral grounds then country by country, in this competition against every side (the style guide's charts)."""
    m = career.matches
    one = m[m.match_id.isin(ids)].section.nunique() == 1
    mixed = "Pick one format to see this: formats are never mixed."

    def bat_first():
        """Their own record batting first and chasing in this competition, against everyone (the style guide's chart)."""
        if not one:
            return dict(none=mixed)
        rs = SG.results(career, opp, ids)
        if not rs:
            return dict(none=f"{opp} haven't played here yet.")
        x = SG.bat_first(career, opp, ids)
        second = "batting second" if x["multi"] else "chasing"
        x.update(who=opp, shows=f"{poss(opp)} own record batting first and {second} in {where_note}, against every side "
                                f"(not only you), with the totals they defended, lost with, chased down and failed to chase.",
                 for_=f"Whether they would rather set a total or chase one, and the totals that have been enough against "
                      f"them: think about it at the toss.")
        return x
    part("bat_first", bat_first)

    def where():
        """Their own record at home, away and on neutral grounds, then country by country (or ground by ground)."""
        if not one:
            return dict(none=mixed)
        rs = SG.results(career, opp, ids)
        if not rs:
            return dict(none=f"{opp} haven't played here yet.")
        v = SG.venues(rs, opp)
        v.update(who=opp, shows=f"{poss(opp)} own record in {where_note}, against every side: at home, away and on neutral "
                                f"grounds, then {'country' if v['nation'] else 'ground'} by {'country' if v['nation'] else 'ground'} "
                                f"(each bar every match there in order, green won, red lost).",
                 for_="How much they rely on home, and how they travel: where your match is decides which record counts.")
        return v
    part("where", where)


def head_to_head(career, ids, me, opp, where_note, mu, cur) -> dict:
    out, part = _parts()
    m = career.matches
    _their_record(career, ids, opp, where_note, part)   # theirs alone, so it shows with no team of yours picked
    if not me:
        out["h2h"] = dict(never="Pick your team above to see your history against them.", other="")
        return out

    def h2h():
        mt = PV.meetings(career, ids, me, opp)
        r = mt["record"]
        if not r["played"]:
            other = m[((m.home == me) & (m.away == opp)) | ((m.home == opp) & (m.away == me))]
            return dict(never=f"{me} and {opp} have never met in {where_note}. Here is what to expect from them instead: see "
                              "the other tabs for their form, key players and weak spots.",
                        other=(f"They have met {len(other)} time(s) in other competitions: " + ", ".join(sorted(set(other.section)))
                               + ".") if len(other) else "")
        h, ty = mt["how"], mt["typical"]
        multi = TP.is_multi(TP.games(career, mt["games"].match_id))
        second = "batting second" if multi else "chasing"
        keys = []
        for team in (me, opp):
            k = mt["key"][team]
            rows, dim = [], []
            for x in k["runs"].itertuples():
                rows.append([x.player, f"{x.runs} runs", f"{x.innings} inns, best {x.best}"])
                dim.append(x.player not in k["current"])
            for x in k["wickets"].itertuples():
                rows.append([x.player, _n(x.wickets, "wkt"), f"economy {fmt(x.economy, 2)}"])
                dim.append(x.player not in k["current"])
            for p, n in k["potm"].items():
                rows.append([p, f"{n} × Player of the Match", ""])
                dim.append(p not in k["current"])
            keys.append(dict(title=f"{poss(team)} key players in these games", rows=rows, dim=dim))
        cards = [dict(id=cd["match_id"], date=cd["date"], event=with_stage(cd["event"], cd["stage"]),
                      sides=[dict(team=t, score=s["score"], top_bat=s["top_bat"], top_bowl=s["top_bowl"]) for t, s in cd["sides"].items()],
                      potm=cd["potm"] or "", story=cd["story"]) for cd in mt["cards"]]
        return dict(never="", kpis=[dict(k="Meetings", v=f"{r['played']}"), dict(k=f"{me} record", v=TP.wdl(r)),
                                    dict(k="Win %", v=fmt(r["win_pct"], 0) + "%")], last5=list(mt["last5"]),
                    how=(f"How the games were won: {me} {h['bat_first_wins'][me]} batting first and {h['chasing_wins'][me]} "
                         f"{second}; {opp} {h['bat_first_wins'][opp]} batting first and {h['chasing_wins'][opp]} {second}."),
                    typical=f"Typical first-innings score: {me} {fmt(ty[me], 0)}, {opp} {fmt(ty[opp], 0)}.",
                    keys=keys, cards=cards)
    part("h2h", h2h)
    def matchups():
        mm = PV.matchups(career, ids, me, opp, everywhere=mu, current_only=cur)
        sides = []
        for key_, title, tag in (("their_bowlers", f"{poss(opp)} bowlers v your batters", "⚠️ Danger man"),
                                 ("our_bowlers", f"Your bowlers v {poss(opp)} batters", "🎯 Best weapon")):
            d = mm[key_].head(10)
            if d.empty:
                sides.append(dict(title=title, none="No dismissals between these players yet."))
                continue
            t = table(["Bowler", "Batter", "Out", "Innings met", "Runs (balls) in those innings"],
                      [[x.bowler, x.player, int(x.dismissals), int(x.innings_met), f"{x.runs_when_out} ({x.balls_when_out})"]
                       for x in d.itertuples()], num={2, 3}, hi=[True] + [False] * (len(d) - 1))
            t.update(title=title, note=f"{tag}: {d.bowler.iloc[0]}, {_n(d.dismissals.iloc[0], 'time')} v {d.player.iloc[0]}.")
            sides.append(t)
        return sides
    part("matchups", matchups)
    return out


def _how_they_play(career, ids, opp, where_note, last: bool) -> dict:
    """How they play, at the top of About them: their bowling and batting this season, read in plain words (their own
    figures only); last season instead when asked, offered when this season has fewer than 5 matches."""
    m = career.matches[career.matches.match_id.isin(ids)]
    if m.section.nunique() != 1:
        return dict(none="Pick one format to see how they play: formats are never mixed.")
    this, before, n = HP.seasons(career, ids, opp)
    season = before if last and before else this
    few = n.get(this, 0) < HP.MIN_MATCHES
    sids = m[m.season == season].match_id
    out = dict(season=season, this=this, last=before if (few or last) and before else "", showing_last=season != this,
               matches=n.get(season, 0), none="")
    if few and season == this:
        other = (f"See last season ({before}, {_n(n[before], 'match', 'matches')}) instead." if before else
                 "There's no earlier season of theirs here.")
        out["note"] = (other if not n.get(this, 0) else
                       f"{opp} have played {_n(n[this], 'match', 'matches')} in {where_note} this season ({this}): too few to "
                       f"read much from. " + other)
    if not n.get(season, 0):
        out["none"] = f"{opp} haven't played in {where_note} in {season} yet."
        return out
    h = HP.how_they_play(career, sids, opp)
    bw, bt, kind = h["bowling"], h["batting"], h["kind"]
    one = lambda x: f"{x:.0f}"  # noqa: E731
    # ---- bowling, in words
    at = bw["at"]
    falls = [f"{'their ' if w == 1 else 'the '}{ordinal(w)}{' wicket' if w == 1 else ''} at {a['usual']}"
             for w, a in at.items() if a["usual"] is not None]
    bowl = []
    if falls:
        bowl.append("Opponents usually lose " + (", ".join(falls[:-1]) + " and " + falls[-1] if len(falls) > 1 else falls[0]) + ".")
    if bw["innings"]:
        bowl.append(f"They had sides 3 down for {bw['cheap_line']} or fewer in {bw['cheap']} of {bw['innings']} innings, and "
                    f"bowled them out in {bw['bowled_out']}.")
    if bw["wickets"]:
        bowl.append(f"The new-ball pair (the first two bowlers on) took {one(bw['new_ball_share'])}% of the wickets "
                    f"({bw['new_ball']} of {bw['wickets']}); {one(bw['top_order_share'])}% of the batters they got out "
                    f"were top-order (1-3).")
    style = ("attack and squeeze" if bw["attack"] and bw["squeeze"] else "attack" if bw["attack"] else
             "squeeze" if bw["squeeze"] else "neither attack nor squeeze")
    if bw["balls_per_wicket"]:
        bowl.append(f"They {style}: a wicket every {bw['balls_per_wicket']:.0f} balls, {bw['economy']:.2f} runs an over"
                    + (f", {bw['dot_pct']:.0f}% dot balls" if bw["dot_pct"] is not None else "") + ".")
    # ---- batting, in words
    shape = {"blast": "blast from the start: the openers score fastest", "build": "build, then blast: the middle order "
             "scores faster than the openers", "steady": "keep much the same pace through the order"}.get(bt["shape"], "")
    bat = []
    if shape:
        bat.append(f"They {shape}.")
    if bt["runs"]:
        bat.append(f"{one(bt['four_share'])}% of their runs come in fours and {one(bt['six_share'])}% in sixes"
                   + (f"; the {bt['most_sixes'].split(' (')[0].lower()} hit the most sixes ({bt['most_sixes_n']})."
                      if bt["most_sixes"] else "."))
    if bt["usual"]:
        u = bt["usual"]
        first, next_ = (u[3], u[6] - u[3]) if 3 in u and 6 in u else (None, None)
        pace = {"fade": f" The big stands come early: the first three wickets usually put on {first}, the next three {next_}.",
                "finish": f" The big stands come later: the first three wickets usually put on {first}, the next three {next_}.",
                "even": f" The stands are much the same: the first three wickets usually put on {first}, the next three "
                        f"{next_}."}.get(bt["pace"], "")
        bat.append("Their usual score at each wicket: " + ", ".join(f"{v}/{w}" for w, v in bt["usual"].items()) + "." + pace)
    parts = table(["Part of the order", "Runs", "Balls", "Strike rate", "In fours and sixes", "4s", "6s"],
                  [[p["part"], p["runs"], p["balls"], fmt(p["strike_rate"], 1), pct(p["boundary_share"], 0), p["fours"], p["sixes"]]
                   for p in bt["parts"] if p["balls"]], num={1, 2, 3, 4, 5, 6})
    lead = []
    if style and bw["balls_per_wicket"]:
        times = {0: "", 1: "once", 2: "twice"}.get(bw["cheap"], f"{bw['cheap']} times")
        lead.append(f"With the ball they {style}" + ((f", and have had sides 3 down cheaply {times} in {bw['innings']} innings"
                                                       if bw["cheap"] else f", and haven't had a side 3 down cheaply in "
                                                       f"{bw['innings']} innings") if bw["innings"] else "") + ".")
    if shape:
        lead.append(f"With the bat they {shape.split(':')[0]}.")
    out.update(summary=" ".join(lead), bowling=bowl, batting=bat, parts=parts, matches=h["matches"],
               rules=(f"Read by fixed rules, the same for every team (no overs on a scorecard): 3 down cheaply is the 3rd "
                      f"wicket by {bw['cheap_line']}; attacking is a wicket every {bw['attack_line']} balls or fewer; "
                      f"squeezing is under {bw['squeeze_line']} an over; the new-ball pair is the first two bowlers on the "
                      f"card; blasting from the start is openers scoring 10% faster than the middle order (5-7), and the "
                      f"other way round is building, then blasting."))
    return out


def _current(career, ids, team: str, last: int = 10) -> list[str]:
    """The team's players in its last `last` matches here, most matches first: the side as it is now."""
    m = career.matches[career.matches.match_id.isin(ids) & ((career.matches.home == team) | (career.matches.away == team))]
    recent = set(m.sort_values("date").match_id.tail(last))
    xi = career.batting[career.batting.match_id.isin(recent) & (career.batting.team == team)]
    return list(xi.player.value_counts().index)


def _one_section(career, ids) -> bool:
    return career.matches[career.matches.match_id.isin(ids)].section.nunique() == 1


def _danger_men(career, ids, opp, where_note) -> dict:
    """Their three most dangerous players right now: the most impact points this season (last season when this one
    has fewer than 5 matches), each with their last five innings or spells."""
    if not _one_section(career, ids):
        return dict(none="Pick one format to see their danger men: formats are never mixed.", men=[])
    section = career.matches[career.matches.match_id.isin(ids)].section.iloc[0]
    this, before, n = HP.seasons(career, ids, opp)
    season, note = this, ""
    if n.get(this, 0) < HP.MIN_MATCHES and before:
        season = before
        note = (f"{opp} have played {_n(n.get(this, 0), 'match', 'matches')} here this season ({this}), so these are last "
                f"season's ({before}, {_n(n[before], 'match', 'matches')}).")
    men = MO.danger_men(career, section, season, opp)
    if not men:
        return dict(none=f"{opp} haven't played in {where_note} in {season} yet.", men=[])
    for x in men:
        x["innings"] = [dict(i, date=f"{i['date']:%d %b %y}", text=f"{i['runs']}{'' if i['out'] else '*'} ({i['balls']})")
                        for i in x["innings"]]
        x["spells"] = [dict(w, date=f"{w['date']:%d %b %y}", text=f"{w['wickets']}-{w['runs']}") for w in x["spells"]]
        x["line"] = (f"{x['points']:.0f} impact points in {_n(x['matches'], 'match', 'matches')} "
                     f"({x['batting']:.0f} batting, {x['bowling']:.0f} bowling"
                     + (f", {x['fielding']:.0f} fielding" if round(x["fielding"]) else "") + ")")
    return dict(none="", season=season, note=note, men=men,
                shows=f"{poss(opp)} three players with the most impact points in {where_note} in {season} (the points "
                      f"of Season review's MVPs: runs and wickets, and how fast or cheaply they came), each with their "
                      f"last five innings and spells here.",
                for_="The players to plan for: who is hurting sides right now, and how they've gone lately.")


def _big_players(career, ids, opp, where_note) -> dict | None:
    """Their players in big games (every knockout and series decider) against their ordinary games, from 3 big
    games."""
    if not _one_section(career, ids):
        return dict(none="Pick one format to see this: formats are never mixed.")
    now = _current(career, ids, opp)
    big = kept(career, ("big_games", tuple(sorted(ids))), lambda: MO.big_match_ids(career, ids))
    bm = MO.big_match(career, ids, players=now, team=opp, big=big)
    if bm.empty:
        return dict(none=f"None of {poss(opp)} current players has played {MO.BIG_MIN} or more big games (knockouts and "
                         f"series deciders) in {where_note} yet.")
    rows = []
    for r in bm.itertuples():
        bb, ob, bw, ow = r.big_bat, r.ord_bat, r.big_bowl, r.ord_bowl
        rows.append([r.player, r.big, f"{bb['runs']} at {fmt(bb['average'], 1)}" if bb["innings"] else "–",
                     f"{ob['runs']} at {fmt(ob['average'], 1)}" if ob["innings"] else "–",
                     f"{bw['wickets']} at {fmt(bw['average'], 1)}" if bw["spells"] else "–",
                     f"{ow['wickets']} at {fmt(ow['average'], 1)}" if ow["spells"] else "–"])
    t = table(["Player", "Big games", "Runs in big games", "Runs otherwise", "Wickets in big games", "Wickets otherwise"],
              rows, num={1})
    t.update(none="", shows=f"{poss(opp)} current players with {MO.BIG_MIN} or more big games in {where_note}: runs and "
                            f"wickets (with their average) in knockouts and series deciders, next to every other game.",
             for_="Who rises to the big occasion and who shrinks: the ones to fear in a final or a decider.")
    return t


def _by_country(career, ids, me, opp, where_note) -> dict:
    """Their current players' record where the match is: with you at home (in your country), away (in theirs) or on
    neutral grounds."""
    if not _one_section(career, ids):
        return dict(none="Pick one format to see this: formats are never mixed.", venues={})
    now = _current(career, ids, opp)
    bh = MO.by_host(career, ids, players=now, team=opp)
    nation = opp in FX.NATIONS
    hosts = {"Home": me, "Away": opp, "Neutral": ""} if me else {"Away": opp, "Neutral": ""}
    out = dict(none="", venues={})
    for where, host in hosts.items():
        x = bh[bh.host == host] if host is not None else bh.iloc[0:0]
        place = ("on neutral grounds" if not host else (f"in {host}" if nation else f"at {poss(host)} ground"))
        if x.empty:
            out["venues"][where] = dict(none=f"None of {poss(opp)} current players has played {place} in {where_note} yet.",
                                        place=place)
            continue
        x = x.assign(order=x.player.map({p: i for i, p in enumerate(now)})).sort_values(["matches", "order"],
                                                                                         ascending=[False, True])
        t = table(["Player", "Matches", "Runs", "Average", "Strike rate", "Wickets", "Average", "Economy"],
                  [[r.player, int(r.matches), r.bat["runs"], fmt(r.bat["average"], 1), fmt(r.bat["strike_rate"], 1),
                    r.bowl["wickets"], fmt(r.bowl["average"], 1), fmt(r.bowl["economy"], 2)] for r in x.itertuples()],
                  num={1, 2, 3, 4, 5, 6, 7})
        t.update(none="", place=place)
        out["venues"][where] = t
    out.update(shows=f"{poss(opp)} current players (those in their last 10 games here) {'in each country' if nation else 'at each ground'} "
                     f"in {where_note}: with you at home it's your {'country' if nation else 'ground'}, away theirs.",
               for_="Who is at home in the conditions of your match, and who has never played there.")
    return out



def about_them(career, ids, me, opp, where_note, mu, cur, last=False) -> dict:
    out, part = _parts()
    pv = _pv(career, ids, opp)
    part("how", lambda: _how_they_play(career, ids, opp, where_note, last))
    part("danger", lambda: _danger_men(career, ids, opp, where_note))
    part("big_players", lambda: _big_players(career, ids, opp, where_note))
    part("by_country", lambda: _by_country(career, ids, me, opp, where_note))

    def in_form(which):
        top = pv[which].head(6)
        if top.empty:
            return None
        if which == "batters":
            tot = pv["batters"].runs.sum()
            share = top.runs.iloc[0] / tot * 100 if tot else 0
            return dict(rows=[dict(player=r.player, team=opp, runs=int(r.runs)) for r in top.itertuples()],
                        notes=[f"{i} innings · average {fmt(a, 1)} · strike rate {fmt(s, 1)} · best {b}"
                               for i, a, s, b in zip(top.innings, top.average, top.strike_rate, top.best)],
                        shows=f"{top.player.iloc[0]} has {top.runs.iloc[0]} runs in their last 10 games, {share:.0f}% of the "
                              f"{tot} runs {poss(opp)} batters made in that time.",
                        for_="Who is scoring for them right now: the batters to plan for and get out early.")
        totw = pv["bowlers"].wickets.sum()
        share = top.wickets.iloc[0] / totw * 100 if totw else 0
        return dict(rows=[dict(player=r.player, team=opp, wickets=int(r.wickets)) for r in top.itertuples()],
                    notes=[f"{i} innings · economy {fmt(e, 2)} · average {fmt(a, 1)}"
                           for i, e, a in zip(top.innings, top.economy, top.average)],
                    shows=f"{top.player.iloc[0]} has {int(top.wickets.iloc[0])} wickets in their last 10 games, {share:.0f}% of "
                          f"the {int(totw)} {opp} took.",
                    for_="Who is taking their wickets right now: the bowlers to see off or play carefully.")
    part("batters", lambda: in_form("batters"))
    part("bowlers", lambda: in_form("bowlers"))

    def key_wicket():
        kw = PV.key_wicket(career, ids, opp)
        if kw.empty:
            return None
        h = kw.head(5)
        return table(["Batter", "Inns", f"Win % when {kw.attrs['bar']}+", "Win % when not", "Gap"],
                     [[x.player, int(x.innings), pct(x.win_good), pct(x.win_bad), f"{x.gap:+.0f}"] for x in h.itertuples()],
                     num={1, 2, 3, 4}, hi=[True] + [False] * (len(h) - 1))
    part("key_wicket", key_wicket)

    def weak_spot():
        ws = PV.weak_spot(career, ids, opp)
        ws = ws[ws.stands >= 2]
        if ws.empty:
            return None
        best_, worst_ = ws.sort_values("vs").iloc[-1], ws.sort_values("vs").iloc[0]
        return dict(rows=[dict(label=f"{ordinal(int(w))} wicket", value=v, text=f"{v:+.0f}% · {a:.0f} v {b:.0f}", note=f"{int(n)} stands")
                          for w, v, a, b, n in zip(ws.wicket, ws.vs, ws.average, ws["all"], ws.stands)],
                    shows=f"Their {ordinal(int(best_.wicket))} wicket stand is {best_.vs:+.0f}% against every team's "
                          f"({best_.average:.0f} v {best_['all']:.0f} runs); the {ordinal(int(worst_.wicket))} is {worst_.vs:+.0f}% "
                          f"({worst_.average:.0f} v {worst_['all']:.0f}). Blue: better than average; red: worse.",
                    for_="Finds where their batting order is soft, so you know which wicket to push hardest for.")
    part("weak_spot", weak_spot)

    def attack():
        at = PV.attack_to_target(career, ids, opp)
        if at.empty:
            return None
        key = at.attrs.get("key", "economy")
        base = at.attrs[key]
        h = at.head(6)
        t = table(["Bowler", "Inns", "Wkts", "Econ", "Avg"],
                  [[x.player, int(x.innings), int(x.wickets), fmt(x.economy, 2), fmt(x.average, 1)] for x in h.itertuples()],
                  num={1, 2, 3, 4}, hi=[(getattr(x, key) or 0) > base for x in h.itertuples()])
        t["note"] = (f"Highlighted: worse than the average bowler here ({'economy' if key == 'economy' else 'average'} "
                     f"{fmt(base, 2 if key == 'economy' else 1)}).")
        return t
    part("attack", attack)

    def styles():
        bs = PV.batting_strip(career, ids, opp)
        if not len(bs):
            return None
        return table(["Batter", "Runs", "Avg", "SR", "Style"],
                     [[x.player, int(x.runs), fmt(x.average, 1), fmt(x.strike_rate, 1), x.style] for x in bs.itertuples()],
                     num={1, 2, 3})
    part("styles", styles)

    def chase():
        ce = PV.chase_extremes(career, ids, opp)
        second = "Batting second" if ce["multi"] else "Chasing"
        t = table(["", "W–L", "Win %"], [["Batting first", TP.wdl(ce["first"]), pct(ce["first"]["win_pct"])],
                                        [second, TP.wdl(ce["second"]), pct(ce["second"]["win_pct"])]], num={2})
        links = []
        if ce["best_chase"]:
            r_, w_, mid, o_ = ce["best_chase"]
            links.append(dict(label="Highest winning chase (their score)", text=f"{r_}/{w_} v {o_}", id=mid))
        if ce["low_defend"]:
            r_, w_, mid, o_, allout = ce["low_defend"]
            links.append(dict(label="Lowest total defended", text=(f"{r_}" if allout else f"{r_}/{w_}") + f" v {o_}", id=mid))
        t.update(title=f"Batting first or {second.lower()}", extremes=links)
        return t
    part("chase", chase)

    def venues():
        vr = PV.venue_record(career, ids, opp)
        res = {}
        for where in ("Home", "Away", "Neutral"):
            theirs = {"Home": "away", "Away": "home", "Neutral": "neutral"}[where]
            r_ = vr[theirs]
            shown = [v for v in ("home", "away", "neutral") if vr[v]["played"]]
            t = table(["", "W–L", "Win %"], [[f"{v.title()} games", TP.wdl(vr[v]), pct(vr[v]["win_pct"])] for v in shown],
                      num={2}, hi=[v == theirs for v in shown])
            t["note"] = (f"With you at {where.lower()}, they are {'at a neutral ground' if theirs == 'neutral' else theirs}: "
                         + (f"{TP.wdl(r_)} there ({pct(r_['win_pct'])})." if r_["played"] else "no games like that yet."))
            res[where] = t
        return res
    part("venues", venues)

    def big():
        bm = PV.big_matches(career, ids, opp)
        rows = [[label, TP.wdl(r_), pct(r_["win_pct"])] for label, r_ in
                (("Knockouts", bm["knockouts"]), ("Finals", bm["finals"]), ("Series deciders", bm["deciders"])) if r_["played"]]
        return table(["", "W–L", "Win %"], rows, num={2}) if rows else None
    part("big", big)

    def trend():
        tr = PV.trend(career, ids, opp)
        line = f"Win % last 5: {pct(tr['recent']['win_pct'])} (before that {pct(tr['before']['win_pct'])})."
        if np.isfinite(tr["elo_now"]):
            d = tr["elo_now"] - tr["elo_then"]
            line += f" Elo rating {tr['elo_now']:.0f} ({d:+.0f} over the last 5), {tr['elo_rank']} of {tr['teams']} here."
        return dict(last=list(tr["last"]), line=line)
    part("trend", trend)

    def how_out():
        how = pv["how_out"]
        if how.empty:
            return None
        n = pv["how_out_n"]
        return dict(rows=[dict(label=say(h), value=float(v), n=int(n[h])) for h, v in how.items()], outs=int(n.sum()),
                    shows=f"{how.iloc[0]:.0f}% of their dismissals are {say(how.index[0]).lower()}"
                          + (f" and {how.iloc[1]:.0f}% {say(how.index[1]).lower()}" if len(how) > 1 else "") + ".",
                    for_="How to get them out: a high bowled or lbw share means attacking the stumps works; a high caught "
                         "share means set fields and wait for the mistake.")
    part("how_out", how_out)

    def depth():
        dep = pv["depth"]
        if not dep.runs.sum():
            return None
        out_ = dict(rows=[dict(label=g, value=s, note=f"{r} runs", runs=int(r)) for g, s, r in zip(dep.group, dep.share, dep.runs)],
                    shows="", for_="")
        if len(dep):
            d0 = dep.sort_values("share", ascending=False).iloc[0]
            out_["shows"] = f"{d0.share:.0f}% of their runs come from the {d0.group.lower()} ({d0.runs} runs)."
            out_["for_"] = ("If most runs come from the top order, early wickets hurt them most; if the middle or tail score "
                            "a lot, keep attacking after the top order is gone.")
        return out_
    part("depth", depth)
    return out


def side_by_side(career, ids, me, opp, where_note, mu, cur) -> dict:
    out, part = _parts()
    if not me:
        out["none"] = "Pick your team above to compare the two sides."
        return out

    def sbs():
        sb = PV.side_by_side(career, ids, me, opp)
        rows = []
        for x in sb.itertuples():
            a = fmt(x.mine, x.dec) if pd.notna(x.mine) else "–"
            b = fmt(x.theirs, x.dec) if pd.notna(x.theirs) else "–"
            if "%" in x.measure and pd.notna(x.mine):
                a += "%"
            if "%" in x.measure and pd.notna(x.theirs):
                b += "%"
            rows.append([x.measure, ("✓ " if x.better == "mine" else "") + a, ("✓ " if x.better == "theirs" else "") + b])
        t = table(["", me, opp], rows, num={1, 2})
        n1, n2 = int((sb.better == "mine").sum()), int((sb.better == "theirs").sum())
        t.update(title=f"{me} v {opp}", right=f"in {where_note} · ✓ marks the better side on each",
                 note=f"{me} ahead on {n1}, {opp} on {n2}. Lower is better for runs per wicket conceded and economy.")
        return t
    part("sbs", sbs)
    return out


def best_xi(career, ids, me, opp, where_note, mu, cur) -> dict:
    out, part = _parts()
    if not me:
        out["none"] = "Pick your team above to see how your players do against them."
        return out

    def xi():
        pb, pw = SN.picks_against(career, ids, me, opp)
        multi_x = pb.attrs.get("kind") == "multi"
        res = dict(title=f"Your {pb.attrs.get('season', '')} squad against {opp}",
                   right="each player's record v them against their own record here", none="", bat=None, bowl=None, lines=[])
        if pb.empty and pw.empty:
            res["none"] = f"None of your current squad has played {opp} here yet."
            return res

        def mark(v):
            return "pick" if v.startswith("Pick") else "think" if v.startswith("Think") else ""

        def signed_pct(v):
            t = signed(v)
            return t if t == "–" else t + "%"
        if multi_x:
            res["bat"] = table(["Player", "Inns v them", "Runs", "Avg v them", "Avg overall", "Change", "Verdict"],
                               [[r.player, int(r.inns_vs), int(r.runs_vs), fmt(r.avg_vs, 1), fmt(r.avg, 1), signed_pct(r.change), r.verdict]
                                for r in pb.itertuples()], num={1, 2, 3, 4, 5}, hi=[mark(r.verdict) == "pick" for r in pb.itertuples()])
        else:
            res["bat"] = table(["Player", "Inns v them", "Runs", "Avg v them", "SR v them", "Avg overall", "SR overall", "Change",
                                "Verdict"],
                               [[r.player, int(r.inns_vs), int(r.runs_vs), fmt(r.avg_vs, 1), fmt(r.sr_vs, 0), fmt(r.avg, 1),
                                 fmt(r.sr, 0), signed_pct(r.change), r.verdict] for r in pb.itertuples()],
                               num={1, 2, 3, 4, 5, 6, 7}, hi=[mark(r.verdict) == "pick" for r in pb.itertuples()])
        res["bat"]["dim"] = [mark(r.verdict) == "think" for r in pb.itertuples()]
        cols_ = (["Player", "Innings v them", "Wkts", "Avg v them"] + ([] if multi_x else ["Econ v them"]) + ["Avg overall"]
                 + ([] if multi_x else ["Econ overall"]) + ["Change", "Verdict"])
        res["bowl"] = table(cols_, [[r.player, int(r.spells_vs), int(r.wkts_vs), fmt(r.avg_vs, 1)] + ([] if multi_x else [fmt(r.econ_vs, 2)])
                                    + [fmt(r.avg, 1)] + ([] if multi_x else [fmt(r.econ, 2)]) + [signed_pct(r.change), r.verdict]
                                    for r in pw.itertuples()],
                            num=set(range(1, len(cols_) - 1)), hi=[mark(r.verdict) == "pick" for r in pw.itertuples()])
        res["bowl"]["dim"] = [mark(r.verdict) == "think" for r in pw.itertuples()]
        for what_, d_ in (("batting", pb), ("bowling", pw)):
            good_ = list(d_[d_.verdict.str.startswith("Pick")].player)
            bad_ = list(d_[d_.verdict.str.startswith("Think")].player)
            if good_ or bad_:
                res["lines"].append(f"{what_.capitalize()}: " + (f"pick {', '.join(good_)}" if good_ else "")
                                    + ("; " if good_ and bad_ else "") + (f"think again about {', '.join(bad_)}" if bad_ else "") + ".")
        res["note"] = (("Measured on average, as in multi-day cricket." if multi_x else
                        "Batting measured on average × strike rate; bowling on average × economy (lower is better).")
                       + " Change: their figure v this opponent against their own figure here; Pick = 25% or more better v "
                       "them, Think again = 25% or more worse. Needs 2 innings v them. Squad = everyone who played for you in "
                       "your latest season here; batting lists those who usually bat in the top 7.")
        return res
    part("xi", xi)
    return out


TAB_FN = {"Head to head": head_to_head, "About them": about_them, "Side by side": side_by_side, "Your best XI v them": best_xi}
