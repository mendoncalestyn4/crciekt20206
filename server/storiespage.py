"""Player stories (stage 3): the current site's 15 tabs, in the same order (your answer 3 of 13 November): form guide,
milestones and records, win when they fire, heroes in defeat, carried the team, quirks, after a hundred, pairs,
Player of the Series, upsets, fastest to, match impact, badges, batter v bowler and clutch.

One competition and season at a time, as the current page (milestones, records, upsets and fastest-to count every
season of it); Batter v bowler follows the competition dropdown with tick boxes instead (your answer 32: ticking Tests
and ODIs adds their meetings up; the "Every competition" switch is gone, answer 17). No fielding anywhere (14
November): match impact is runs and wickets only. The sums are in the engine (ccstats/players.py, playerdeep.py,
teamdeep.py); this only turns them into what the page shows."""

from __future__ import annotations

from ccstats.partnerships import suffix

import pandas as pd

from ccstats import playerdeep as PD
from ccstats import players as PL
from ccstats import teamdeep as TD
from ccstats.stats import poss

from . import styleguide as SG
from .cache import kept
from .teampage import _n, choices, fmt, pct, secs_of, signed, table

TABS = ["Form guide", "Milestones and records", "Win when they fire", "Heroes in defeat", "Carried the team", "Quirks",
        "After a hundred", "Pairs", "Player of the Series", "Upsets", "Fastest to", "Match impact", "Badges",
        "Batter v bowler", "Clutch", "Partnership breakers"]


def _pct_s(v) -> str:
    t = signed(v)
    return t if t == "–" else t + "%"


def stories_page(career, q: dict, mine: list[str]) -> dict:
    ch = choices(career)
    if not ch:   # a career made before any game was played
        return SG.clean(dict(choices=[], none=SG.NO_MATCHES, tabs=TABS, tab=TABS[0]))
    tab = q.get("tab") if q.get("tab") in TABS else TABS[0]
    every = [c["section"] for c in ch]
    asked = [s for s in secs_of(q.get("section", "")) if s in set(every)] or [every[0]]
    ticked = asked if tab == "Batter v bowler" else asked[:1]   # only Batter v bowler adds competitions up (answer 32)
    seasons = sorted({s for c in ch if c["section"] in set(ticked) for s in c["seasons"]}, reverse=True)
    season = str(q.get("season", ""))
    season = season if season in seasons else ""
    head = dict(choices=[dict(section=c["section"], matches=c["matches"]) for c in ch], tabs=TABS, tab=tab,
                ticked=ticked, section="|".join(ticked), seasons=seasons, season=season)
    extra = (str(q.get("batter", "")), str(q.get("bowler", ""))) if tab == "Batter v bowler" else ()
    key = ("stories", tab, tuple(ticked), season, tuple(mine)) + extra
    body = kept(career, key, lambda: _tab(career, tab, ticked, season, mine, *extra))
    return SG.clean({**head, **body})


def _tab(career, tab, ticked, season, mine, *extra) -> dict:
    m = career.matches
    here = m[m.section.isin(ticked)]
    all_ids = list(here.match_id)                      # milestones, records, upsets and fastest-to: every season
    ids = list((here[here.season.astype(str) == season] if season else here).match_id)
    sec = ticked[0]
    mine_s = set(mine)
    hi = lambda teams: [any(t in mine_s for t in str(x).split(" / ")) for x in teams]   # noqa: E731
    fn = {TABS[0]: lambda: _form(career, ids, hi), TABS[1]: lambda: _milestones(career, all_ids, sec, hi),
          TABS[2]: lambda: _fire(career, ids, hi), TABS[3]: lambda: _heroes(career, ids),
          TABS[4]: lambda: _carried(career, ids, sec, season), TABS[5]: lambda: _quirks(career, ids),
          TABS[6]: lambda: _after(career, ids, hi), TABS[7]: lambda: _pairs(career, ids, hi),
          TABS[8]: lambda: _series(career, ids), TABS[9]: lambda: _upsets(career, sec),
          TABS[10]: lambda: _fastest(career, all_ids, sec, hi), TABS[11]: lambda: _impact(career, ids, sec, season, hi),
          TABS[12]: lambda: _badges(career, ids, sec, mine, hi), TABS[13]: lambda: _bvb(career, ids, ticked, *extra),
          TABS[14]: lambda: _clutch(career, ids, hi), TABS[15]: lambda: _breakers(career, ids, hi)}
    return fn[tab]()


# --------------------------------------------------------------------------- form guide (the current 18)
def _form(career, ids, hi) -> dict:
    fb, fw = PL.form_guide(career, ids)
    out: dict = {}
    arrow = lambda t, base: "▲" if t > 0.25 * base else "▼" if t < -0.25 * base else "▬"   # noqa: E731
    if fb.empty:
        out["bat_none"] = "Batters need 6+ innings."
    else:
        x = fb.head(30)
        out["bat"] = table(["Player", "Team", "Last 5", "Avg last 5", "Avg here", ""],
                           [[r.player, r.team, r.last, fmt(r.recent_avg, 1), fmt(r.career_avg, 1), arrow(r.trend, r.career_avg)]
                            for r in x.itertuples()], num=[3, 4], hi=hi(x.team))
    if fw.empty:
        out["bowl_none"] = "Bowlers need 6+ innings."
    else:
        x = fw.head(30)
        out["bowl"] = table(["Player", "Team", "Last 5", "Wkts/inns last 5", "Wkts/inns", "Econ last 5", ""],
                            [[r.player, r.team, r.last, fmt(r.recent_wpi, 1), fmt(r.career_wpi, 1), fmt(r.recent_econ, 2),
                              arrow(r.trend, r.career_wpi)] for r in x.itertuples()], num=[3, 4, 5], hi=hi(x.team))
    out["note"] = ("▲ hotter than usual (25%+ above their own average) · ▼ colder · ▬ about normal. Your team's players are "
                   "lit up. Analytics → Is the form real? says whether a hot run is more than luck.")
    return out


# --------------------------------------------------------------------------- milestones and records (the current 9, 64)
def _milestones(career, all_ids, sec, hi) -> dict:
    out: dict = dict(sec=sec)
    mw = PL.milestone_watch(career, all_ids)
    if mw.empty:
        out["miles_none"] = "Nobody is close to a milestone right now."
    else:
        x = mw.head(25)
        out["miles"] = table(["Player", "Team", "Milestone", "Now", "Needs"],
                             [[r.player, r.team, f"{r.next:,} {r.what}", f"{r.now:,}", f"{r.needed:,}"] for r in x.itertuples()],
                             num=[3, 4], hi=hi(x.team))
    rw = PL.record_watch(career, sec)
    if rw.empty:
        out["records_none"] = "No record is under threat right now."
    else:
        out["records"] = table(["Record", "Holder", "Chaser", "Now", "Needs"],
                               [[r.record, f"{r.holder} {r.record_value:,}", r.chaser, f"{r.now:,}", f"{r.needed:,}"]
                                for r in rw.itertuples()], num=[3, 4])
        out["records"]["note"] = ("Career records: players within 15% of the leader. Season records: players within 25% "
                                  "while the season is still going.")
    return out


# --------------------------------------------------------------------------- win when they fire (the current 8)
def _fire(career, ids, hi) -> dict:
    wb, ww = PL.win_when(career, ids)
    big, haul = wb.attrs.get("big", 50), wb.attrs.get("haul", 3)
    out: dict = dict(parts=[])
    for d, title, what in ((wb, f"When they make {big}+", f"{big}+ scores"), (ww, f"When they take {haul}+ wickets", f"{haul}-wicket hauls")):
        part = dict(title=title)
        if d.empty:
            part["none"] = f"Nobody has 3+ {what} yet."
        else:
            x = d.head(20)
            part["table"] = table(["Player", "Team", "Times", "Win % then", "Win % otherwise", "Lift"],
                                  [[r.player, r.team, int(r.times), pct(r.pct_when), pct(r.pct_other), signed(r.lift)]
                                   for r in x.itertuples()], num=[2, 3, 4, 5], hi=hi(x.team))
        out["parts"].append(part)
    return out


# --------------------------------------------------------------------------- heroes in defeat (the current 12)
def _heroes(career, ids) -> dict:
    hb, hw = PL.heroes_in_defeat(career, ids)
    out: dict = {}
    if len(hb):
        out["bat"] = table(["Match", "Player", "Score", "For", "Against"],
                           [[f"{r.date:%d %b %Y}", r.player, f"{r.runs}{'' if r.out else '*'} ({r.balls})", r.team, r.opposition]
                            for r in hb.itertuples()], links=list(hb.match_id))
    if len(hw):
        out["bowl"] = table(["Match", "Player", "Figures", "For", "Against"],
                            [[f"{r.date:%d %b %Y}", r.player, f"{r.wickets}/{r.runs}", r.team, r.opposition] for r in hw.itertuples()],
                            links=list(hw.match_id))
    return out


# --------------------------------------------------------------------------- carried the team (the current 13)
def _carried(career, ids, sec, season) -> dict:
    ci, cp = PL.carried(career, ids)
    out: dict = {}
    if len(ci):
        out["one"] = table(["Match", "Player", "Runs", "Team total", "Share"],
                           [[f"{r.team} v {r.opposition}", r.player, f"{r.runs}{'' if r.out else '*'}", f"{int(r.team_total)}",
                             f"{r.share:.0f}%"] for r in ci.itertuples()], num=[2, 3, 4], links=list(ci.match_id))
    top = cp.head(12)
    if top.empty:
        out["share_none"] = "Not enough innings yet."
    else:
        t0 = top.iloc[0]
        where = sec + (f" {season}" if season else "")
        out["share"] = dict(rows=[dict(label=r.player, value=round(float(r.share), 2), text=f"{r.share:.1f}%",
                                       note=f"{r.runs} of {r.team_runs} runs in {r.innings} innings · {r.team}") for r in top.itertuples()],
                            **SG.lines(f"Each batter's share of their team's runs in the innings they batted in {where} (5+ innings).",
                                       f"{t0.player}, {t0.share:.1f}% of {poss(t0.team)} runs ({t0.runs} of {t0.team_runs}); an "
                                       "even share across 11 batters would be about 9%",
                                       "Shows which teams lean on one batter: if they fail, the team usually does too.",
                                       best_label="Carries most"))
    return out


# --------------------------------------------------------------------------- quirks (the current 11)
def _quirks(career, ids) -> dict:
    q = PL.quirks(career, ids)
    out: dict = {}
    if len(q["nineties"]):
        out["nineties"] = table(["Player", "Times", "Scores"], [[r.player, int(r.times), r.scores] for r in q["nineties"].head(15).itertuples()], num=[1])
    if len(q["pairs"]):
        out["pairs"] = table(["Player", "Pairs", "Team"], [[r.player, int(r.pairs), r.team] for r in q["pairs"].head(15).itertuples()], num=[1])
    if len(q["not_outs"]):
        out["not_outs"] = table(["Player", "Not out", "Inns", "%"],
                                [[r.player, int(r.not_outs), int(r.innings), f"{r.pct:.0f}%"] for r in q["not_outs"].head(15).itertuples()],
                                num=[1, 2, 3])
    return out


# --------------------------------------------------------------------------- after a hundred (the current 37)
def _after(career, ids, hi) -> dict:
    ah = PL.after_hundred(career, ids)
    if ah.empty:
        return dict(after_none="No hundreds followed by another innings yet.")
    return dict(after=table(["Player", "Hundreds", "Next innings", "Avg next innings", "Avg overall"],
                            [[r.player, int(r.hundreds), r.next_scores, fmt(r.next_avg, 1), fmt(r.average, 1)] for r in ah.itertuples()],
                            num=[1, 3, 4], hi=hi(ah.team)))


# --------------------------------------------------------------------------- pairs (the current 65, 128, 131)
def _pairs(career, ids, hi) -> dict:
    out: dict = {}
    bp = PL.batting_pairs(career, ids)
    if len(bp):
        x = bp.head(20)
        out["bat"] = table(["Pair", "Team", "Stands", "Runs", "Avg", "Best", f"{bp.attrs.get('stand', 50)}+"],
                           [[r.pair, r.team, int(r.stands), int(r.runs), fmt(r.average, 1), r.best, int(r.big_stands)] for r in x.itertuples()],
                           num=[2, 3, 4, 5, 6], hi=hi(x.team),
                           parts=[dict(runs=int(r.runs), outs=int(r.broken), what="stands") for r in x.itertuples()])
        out["bat"]["note"] = "Only stands where the scorecard shows who batted together (see Records, best stand for each wicket)."
    wp = PL.bowling_pairs(career, ids)
    if len(wp):
        x = wp.head(20)
        out["bowl"] = table(["Pair", "Team", "Inns", "Wkts", "Wkts/inns", "Econ"],
                            [[r.pair, r.team, int(r.innings), int(r.wickets), f"{r.per_innings:.1f}", fmt(r.economy, 2)] for r in x.itertuples()],
                            num=[2, 3, 4, 5], hi=hi(x.team), parts=[dict(bruns=int(r.runs), bballs=int(r.balls)) for r in x.itertuples()])
    chem = TD.chemistry(career, ids)
    if chem.empty:
        out["chem_none"] = "No pair has 3 named stands yet."
    else:
        x = chem.head(15)
        out["chem"] = table(["Pair", "Team", "Stands", "Avg stand", "Expected", "Chemistry"],
                            [[r.pair, r.team, int(r.stands), f"{r.average:.1f}", f"{r.expected:.1f}", _pct_s(r.chemistry)] for r in x.itertuples()],
                            num=[2, 3, 4, 5], hi=hi(x.team))
        out["chem"]["note"] = ("Expected: what the average pair makes for the same wickets here, so an opening pair is compared "
                               "with opening stands. +50% = half as much again.")
    sp = TD.sr_pressure(career, ids)
    if sp.empty:
        out["pressure_none"] = "White-ball cricket only, and batters need 3+ named stands."
    else:
        x = pd.concat([sp.head(6), sp.tail(6)]).drop_duplicates("player")
        out["pressure"] = table(["Batter", "Team", "Inns", "Partners' SR with them", "Partners' SR otherwise", "Effect"],
                                [[r.player, r.team, int(r.innings), fmt(r.partner_sr_with, 1), fmt(r.partner_sr_without, 1),
                                  _pct_s(r.effect)] for r in x.itertuples()], num=[2, 3, 4, 5], hi=hi(x.team))
        out["pressure"]["note"] = ("The slowest-scoring partnerships first, then the fastest. The scorecards don't split a "
                                   "stand's runs, so this uses the partners' whole innings: a hint, not proof.")
    return out


# --------------------------------------------------------------------------- Player of the Series (the current 16)
def _series(career, ids) -> dict:
    ps = PL.player_of_series(career, ids)
    if ps.empty:
        return dict(series_none="No bilateral series here.")
    m = career.matches
    first = m[m.series_id != ""].groupby("series_id").agg(start=("date", "min"), home=("home", "first"), away=("away", "first"))
    ps = ps.join(first, on="series_id").sort_values("start", ascending=False)
    t = table(["Started", "Series", "Player", "For", "Runs", "Wkts", "Impact"],
              [[f"{r.start:%b %Y}", f"{r.home} v {r.away}", r.player, r.team, int(r.runs), int(r.wickets), f"{r.points:.0f}"]
               for r in ps.itertuples()], num=[4, 5, 6])
    t["note"] = "Impact = runs, plus each wicket worth the competition's runs per wicket."
    return dict(series=t)


# --------------------------------------------------------------------------- upsets (the current 15)
def _upsets(career, sec) -> dict:
    up = PL.upsets(career, sec)
    if up.empty:
        return dict(upsets_none="No upsets yet.", sec=sec)
    t = table(["Match", "Winner", "Beat", "Their chance", "Elo going in"],
              [[f"{r.date:%d %b %Y}", r.winner, r.loser, f"{r.chance:.0f}%", f"{r.winner_elo:.0f} v {r.loser_elo:.0f}"]
               for r in up.itertuples()], num=[3], links=list(up.match_id))
    t["note"] = "Chance from the two teams' ratings (Elo) before the game (see Rankings)."
    return dict(upsets=t, sec=sec)


# --------------------------------------------------------------------------- fastest to (the current 91)
def _fastest(career, all_ids, sec, hi) -> dict:
    fa = PD.fastest(career, all_ids)
    unit = fa.attrs.get("unit", "innings")
    out: dict = dict(fast_note=f"Counted in {unit}" + (" (as Test records are)" if unit == "matches" else "")
                     + f", across every season of {sec}.")
    if fa.empty:
        out["fast_none"] = "Nobody has reached a milestone here yet."
        return out
    groups = []
    for (what, ms), g in fa.groupby(["what", "milestone"], sort=False):
        x = g.head(8)
        groups.append(dict(title=f"Fastest to {ms:,} {what}", right=f"{len(g)} player{'s' if len(g) != 1 else ''} got there",
                           table=table(["#", "Player", "Team", "Took", "Reached"],
                                       [[int(r.rank), r.player, r.team, f"{r.taken} {unit}", f"{r.date:%d %b %Y}"] for r in x.itertuples()],
                                       num=[0], hi=hi(x.team))))
    out["fast"] = groups
    return out


# --------------------------------------------------------------------------- match impact (the current 94)
def _impact(career, ids, sec, season, hi) -> dict:
    mi = PD.match_impact(career, ids)
    if mi.empty:
        return dict(impact_none="No matches yet.")
    top = mi.sort_values("impact", ascending=False).head(15)
    out: dict = dict(top=table(["Match", "Player", "Team", "Impact", "Did"],
                               [[f"v {r.opponent}, {r.date:%d %b %Y}", r.player, r.team, f"{r.impact:.0f}",
                                 f"{int(r.runs)} & " + _n(int(r.wickets), "wkt")] for r in top.itertuples()], num=[3], hi=hi(top.team),
                               links=list(top.match_id)))
    g = mi.groupby("player").agg(matches=("impact", "size"), avg=("impact", "mean"), team=("team", "last")).reset_index()
    g = g[g.matches >= max(3, int(g.matches.quantile(0.5)))].sort_values("avg", ascending=False).head(12)
    if len(g):
        where = sec + (f" {season}" if season else "")
        mean = float(mi.impact.mean())
        white = mi.attrs.get("kind") != "multi"
        out["per"] = dict(rows=[dict(label=r.player, value=round(float(r.avg), 1), text=f"{r.avg:.0f}", note=f"{r.matches} matches · {r.team}")
                                for r in g.itertuples()],
                          **SG.lines(f"Impact per match of the regulars in {where}: runs, plus each wicket worth the competition's "
                                     f"runs per wicket ({mi.attrs['rpw']:.0f})"
                                     + (", with scoring speed and economy counted in white-ball cricket." if white else "."),
                                     f"{g.player.iloc[0]}, {g.avg.iloc[0]:.0f} a match ({(g.avg.iloc[0] / mean - 1) * 100:+.0f}% on "
                                     f"the average player's {mean:.0f})" if mean else f"{g.player.iloc[0]}, {g.avg.iloc[0]:.0f} a match",
                                     "One number for everything a player does in a match with bat and ball, so a batter and "
                                     "a bowler can be compared.", best_label="Most impact per match"))
    return out


# --------------------------------------------------------------------------- badges (the current 119)
def _badges(career, ids, sec, mine, hi) -> dict:
    ach = PD.achievements(career, ids)
    out: dict = dict(sec=sec)
    if ach.empty:
        out["badges_none"] = "No badges yet."
    else:
        x = ach.head(40)
        out["badges"] = table(["Match", "Badge", "Player", "Team", ""],
                              [[f"{r.date:%d %b %Y}", f"🏅 {r.badge}", r.player, r.team, r.detail] for r in x.itertuples()],
                              hi=hi(x.team), links=list(x.match_id))
        vc = ach.badge.value_counts()
        out["common"] = table(["Badge", "Times"], [[b, int(n)] for b, n in vc.items()], num=[1])
    out["badge_note"] = ("T20: 5-for, hundred, 100 at a strike rate of 200+, fifty off 20 balls. One-day: 150, double hundred, "
                         "five-for. Tests: double and triple hundreds, seven in an innings, ten in a match, a hundred or five-for "
                         "in both innings, carried the bat, a pair. Any format: hundred on debut, hundred and five-for in a match, "
                         "three big scores in a row, a hundred or Player of the Match in a final.")
    team_lines = []
    for t in sorted(mine):
        tb = PD.team_achievements(career, t)
        if len(tb):
            team_lines.append(f"{t}: " + ", ".join(f"🏆 {r.badge} ({r.detail})" for r in tb.itertuples()))
    out["team_badges"] = team_lines
    return out


# --------------------------------------------------------------------------- batter v bowler (the current 120)
def _bvb(career, ids, ticked, batter="", bowler="") -> dict:
    b, w = career.batting, career.bowling
    bat_names = sorted(b[b.did_bat & b.match_id.isin(ids)].player.unique())
    bowl_names = sorted(w[(w.balls > 0) & w.match_id.isin(ids)].player.unique())
    batter = batter if batter in set(bat_names) else ""
    bowler = bowler if bowler in set(bowl_names) else ""
    where = " + ".join(ticked)
    vs_bat = PD.faced(career, ids, batter=batter) if batter else None
    vs_bowl = PD.faced(career, ids, bowler=bowler) if bowler else None
    out: dict = dict(batter=batter, bowler=bowler, where=where)
    # once one is picked, the other list shows who they've met first (most dismissals first)
    met_bat = dict(zip(vs_bat.name, vs_bat.dismissals)) if vs_bat is not None else {}
    met_bowl = dict(zip(vs_bowl.name, vs_bowl.dismissals)) if vs_bowl is not None else {}
    if vs_bat is not None:
        bowl_names = list(vs_bat.name) + [x for x in bowl_names if x not in met_bat]
    if vs_bowl is not None:
        bat_names = list(vs_bowl.name) + [x for x in bat_names if x not in met_bowl]
    out["batters"] = [dict(v=x, label=x, note=(f"out to them {met_bowl[x]}×" if met_bowl.get(x) else "met" if x in met_bowl else ""))
                      for x in bat_names]
    out["bowlers"] = [dict(v=x, label=x, note=(f"got them out {met_bat[x]}×" if met_bat.get(x) else "met" if x in met_bat else ""))
                      for x in bowl_names]
    if bool(batter) != bool(bowler):
        one, t_ = (batter, vs_bat) if batter else (bowler, vs_bowl)
        other = "bowler" if batter else "batter"
        if t_ is None or t_.empty:
            out["one_none"] = f"No {other}s met {one} yet in {where}."
        else:
            out["one"] = table([other.capitalize(), "Innings met", "Got out" if batter else "Got them out", "Batter's runs in those innings"],
                               [[r.name, int(r.innings), int(r.dismissals), int(r.runs)] for r in t_.head(12).itertuples()], num=[1, 2, 3])
            out["one_title"] = f"{one} against every {other} met"
    elif not batter:
        out["pick"] = "Pick a batter, a bowler, or both."
    if batter and bowler:
        bv = PD.batter_v_bowler(career, batter, bowler, ids)
        inns = bv["innings"]
        if inns.empty:
            out["both_none"] = f"{bowler} has never bowled at {poss(batter)} side while {batter} batted in {where}."
        else:
            out["kpis"] = [dict(k="Innings met", v=str(bv["meetings"])), dict(k=f"{bowler.split()[-1]} got them out", v=str(bv["dismissals"])),
                           dict(k="Batter's runs in those innings", v=str(bv["runs"])),
                           dict(k="Average v this bowler", v=fmt(bv["runs_when_out"] / bv["dismissals"], 1) if bv["dismissals"] else "–",
                                how=(f"{bv['runs_when_out']} runs ÷ {bv['dismissals']} times out" if bv["dismissals"] else ""))]
            verdict = ("bowler on top" if bv["dismissals"] / bv["meetings"] >= 0.4 else
                       "batter on top" if bv["dismissals"] == 0 and bv["meetings"] >= 3 else "even")
            out["verdict"] = f"Verdict: {verdict} ({_n(bv['dismissals'], 'dismissal')} in {bv['meetings']} innings)."
            out["meetings"] = table(["Match", "Competition", "Batter's score", "How out", "Bowler's figures"],
                                    [[f"{r.date:%d %b %Y}", r.section, f"{r.runs}{'' if r.out else '*'} ({r.balls})",
                                      ("✔ " + r.dismissal) if r.bowler == bowler and r.out else r.dismissal or "not out",
                                      f"{r.bowl_wkts}/{r.bowl_runs}"] for r in inns.itertuples()], links=list(inns.match_id))
            out["meetings"]["note"] = ("The scorecards don't say which bowler each run came off, so these are the batter's whole "
                                       "innings when the two met. ✔ = this bowler got them out.")
    return out


# --------------------------------------------------------------------------- clutch (the current 127)
def _clutch(career, ids, hi) -> dict:
    cb, cw = TD.clutch(career, ids)
    multi = cb.attrs.get("kind") == "multi"
    out: dict = dict(clutch_note="Big games: knockouts, close games (by this format's margins) and series deciders"
                     + (", plus the 4th innings of a multi-day game." if multi else ".") + " Players need 3+ innings each way.")
    if cb.empty:
        out["bat_none"] = "Not enough big games yet."
    else:
        x = cb.head(15)
        out["bat"] = table(["Batter", "Team", "Big-game inns", "Avg then", "Avg otherwise", "Lift"],
                           [[r.player, r.team, int(r.clutch_innings), fmt(r.clutch_avg, 1), fmt(r.other_avg, 1), _pct_s(r.lift)]
                            for r in x.itertuples()], num=[2, 3, 4, 5], hi=hi(x.team))
    if cw.empty:
        out["bowl_none"] = "Not enough big games yet."
    else:
        x = cw.head(15)
        out["bowl"] = table(["Bowler", "Team", "Big-game inns", "Wkts/inns then", "Otherwise", "Avg then" if multi else "Econ then", "Lift"],
                            [[r.player, r.team, int(r.clutch_innings), f"{r.clutch_wpi:.2f}", f"{r.other_wpi:.2f}",
                              fmt(r.clutch_avg, 1) if multi else fmt(r.clutch_econ, 2), _pct_s(r.lift)] for r in x.itertuples()],
                            num=[2, 3, 4, 5, 6], hi=hi(x.team))
    return out


# --------------------------------------------------------------------------- partnership breakers (stage 5)
def _breakers(career, ids, hi) -> dict:
    """Bowlers ranked by the stands of 50 and more they ended (ccstats/breakers.py), and the biggest stands broken."""
    from ccstats import breakers as BR
    t = BR.table(career, ids)
    out: dict = dict(breakers_note=f"A stand of {BR.MIN_STAND}+ is broken by the bowler who took the wicket that ended it "
                     "(a run out counts for no one). Only innings where the scorecard shows who batted together.")
    if t.empty:
        out["breakers_none"] = f"No stand of {BR.MIN_STAND} or more has been broken by a bowler here yet."
        return out
    x = t.head(20)
    out["breakers"] = table(["Bowler", "Team", "Stands broken", "Biggest", "Avg stand", "Mat"],
                            [[r.bowler, r.team, int(r.broken), int(r.biggest), f"{r.average:.1f}", int(r.matches)]
                             for r in x.itertuples()], num=[2, 3, 4, 5], hi=hi(x.team))
    b = BR.broken(career, ids)
    m = career.matches.set_index("match_id")
    big = b.sort_values(["runs", "wicket"], ascending=[False, True]).head(10)
    out["biggest"] = table(["Stand", "Wicket", "Broken by", "Batter out", "Against", "Date"],
                           [[int(r.runs), f"{int(r.wicket)}{suffix(int(r.wicket))}", r.bowler, r.batter,
                             m.home[r.match_id] if m.away[r.match_id] == r.team else m.away[r.match_id],
                             SG.clean(m.date[r.match_id])] for r in big.itertuples()],
                           num=[0], hi=hi(big.team))
    top = x.iloc[0]
    out.update(SG.lines("Bowlers ranked by the stands of 50 and more they ended.",
                        f"{top.bowler} ({top.team}), {int(top.broken)} stand{'s' if top.broken != 1 else ''} broken",
                        "Shows who to bring on when a pair gets set: the bowlers who end big partnerships, not just "
                        "the ones who take the tail.", best_label="Most broken"))
    return out
