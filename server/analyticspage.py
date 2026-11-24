"""Analytics (stage 3): the current site's deeper numbers for one competition (views/analytics.py), kept as its own page
(your answer 2 of 13 November): runs against what the situation called for, averages made fair, what really wins
games, luck, match-winners, styles, consistency, whether a run of form is real, and whether to bat or bowl first.
New: the match-winners chart (your answer 14): a team's players of the match in its wins, and what they did each time.

One competition at a time (and one season, or all of them): every figure here is measured against the competition's
own average batter, bowler or side, so a T20 and a Test can't share one (your rule of 14 November: combining stays
out where it has no meaning). No fielding: contributions are runs and wickets only. The sums are in the engine
(ccstats/players.py, teamplay.py); this only turns them into what the page shows."""

from __future__ import annotations

from ccstats import players as PL
from ccstats import teamplay as TP
from ccstats.stats import Scope, player_tables

from . import styleguide as SG
from .cache import kept
from .teampage import _n, choices, fmt, pct, secs_of, table

TABS = ["Runs above expected", "Fair averages", "What wins games", "Luck", "Match-winners", "Style maps", "Boom or bust",
        "Is the form real?", "Bat or bowl first?"]
STYLE_MINS = {"t20": 60, "one": 120, "multi": 200}   # balls faced or bowled to be on a style map


def analytics_page(career, q: dict, mine: list[str]) -> dict:
    ch = choices(career)
    if not ch:   # a career made before any game was played
        return SG.clean(dict(choices=[], none=SG.NO_MATCHES, tabs=TABS, tab=TABS[0]))
    tab = q.get("tab") if q.get("tab") in TABS else TABS[0]
    every = [c["section"] for c in ch]
    asked = [s for s in secs_of(q.get("section", "")) if s in set(every)]
    sec = asked[0] if asked else every[0]
    seasons = next(c["seasons"] for c in ch if c["section"] == sec)
    season = str(q.get("season", ""))
    season = season if season in seasons else ""
    head = dict(choices=[dict(section=c["section"], matches=c["matches"]) for c in ch], tabs=TABS, tab=tab, section=sec,
                seasons=seasons, season=season)
    team = str(q.get("team", ""))
    key = ("analytics", tab, sec, season) + ((team, tuple(mine)) if tab in (TABS[4], TABS[8]) else ())
    body = kept(career, key, lambda: _tab(career, tab, sec, season, team, mine))
    return SG.clean({**head, **body})


def _tab(career, tab, sec, season, team, mine) -> dict:
    m = career.matches
    here = m[m.section == sec]
    if season:
        here = here[here.season.astype(str) == season]
    ids = list(here.match_id)
    where = sec + (f" {season}" if season else "")
    if tab == TABS[0]:
        return _rae(career, ids, where)
    if tab == TABS[1]:
        return _fair(career, ids)
    if tab == TABS[2]:
        return _what_wins(career, ids, where)
    if tab == TABS[3]:
        return _luck(career, ids, where)
    if tab == TABS[4]:
        return _winners(career, ids, where, here, team, mine)
    if tab == TABS[5]:
        real = next((s for s in m[m.section == sec].season.unique() if str(s) == season), None)
        return _styles(career, Scope(sections=[sec], seasons=[real] if season else []), where)
    if tab == TABS[6]:
        return _boom(career, ids, where)
    if tab == TABS[7]:
        return _form(career, ids, mine)
    return _bat_or_bowl(career, ids, where, mine)


# --------------------------------------------------------------------------- runs above expected (the current 38)
def _rae(career, ids, where) -> dict:
    rae = PL.runs_above_expected(career, ids)
    if rae.empty:
        return dict(rae_none="Not enough innings yet (5 or more each).")
    top = rae.head(12)
    t0 = top.iloc[0]
    edge = t0.above / t0.expected * 100 if t0.expected else 0
    bars = dict(rows=[dict(label=r.player, value=round(float(r.above), 1), text=f"{r.above:+.0f}",
                           note=f"{r.runs} runs in {r.innings} innings, {r.expected:.0f} expected · usually bats {r.usual_position}")
                      for r in top.itertuples()],
                **SG.lines(f"Each batter's runs in {where} against what the average batter made coming in at the same position "
                           "with the same number of wickets down (blue above, red below).",
                           f"{t0.player}, {t0.above:+.0f} ({t0.runs} runs against {t0.expected:.0f} expected, {edge:+.0f}%)",
                           "Fair credit for batting position: a no. 7 who makes 30 coming in at 5 down has done more than an "
                           "opener making 30 at 0 for 0. Situations are grouped by wickets down when they came in: 0, 1, 2, "
                           "3-4, 5+.", best_label="Most above expected"))
    rows = [[r.player, r.team, int(r.innings), int(r.runs), f"{r.expected:.0f}", f"{r.above:+.0f}", f"{r.per_innings:+.1f}"]
            for r in rae.head(30).itertuples()]
    return dict(rae=bars, rae_table=table(["Player", "Team", "Inns", "Runs", "Expected", "Above", "Per inns"], rows,
                                          num=[2, 3, 4, 5, 6]))


# --------------------------------------------------------------------------- fair averages (the current 39, 40)
def _fair(career, ids) -> dict:
    out: dict = {}
    aa = PL.adjusted_averages(career, ids)
    if aa.empty:
        out["bat_none"] = "Not enough innings yet."
    else:
        x = aa.head(25)
        out["bat"] = table(["Player", "Inns", "Avg", "v attacks faced", "Settled", ""],
                           [[r.player, int(r.innings), fmt(r.average, 2), fmt(r.adjusted, 1), fmt(r.settled, 1),
                             "✅ reliable" if r.tag == "reliable" else "⏳ still settling"] for r in x.itertuples()],
                           num=[1, 2, 3, 4], parts=[dict(runs=int(r.runs), outs=int(r.outs), inns=int(r.innings)) for r in x.itertuples()])
    ab = PL.adjusted_bowling(career, ids)
    if ab.empty:
        out["bowl_none"] = "Not enough innings yet."
    else:
        x = ab.head(25)
        out["bowl"] = table(["Player", "Inns", "Avg", "v batting faced", "Settled", ""],
                            [[r.player, int(r.innings), fmt(r.average, 2), fmt(r.adjusted, 1), fmt(r.settled, 1),
                              "✅ reliable" if r.tag == "reliable" else "⏳ still settling"] for r in x.itertuples()],
                            num=[1, 2, 3, 4], parts=[dict(bruns=int(r.runs), wkts=int(r.wickets), binns=int(r.innings)) for r in x.itertuples()])
    out["note"] = ("v attacks faced: runs against an attack that gives away fewer runs per wicket than average count for more "
                   "(and the other way round for bowlers). Settled: a few average innings are added to everyone, so a hot "
                   "start over a handful of games is pulled towards the competition's average until there are enough "
                   "dismissals to trust it. Sorted by the settled figure.")
    return out


# --------------------------------------------------------------------------- what wins games (the current 42)
def _what_wins(career, ids, where) -> dict:
    ww = PL.what_wins(career, ids)
    if ww.empty:
        return dict(wins_none="No finished games yet.")
    top, low = ww.iloc[0], ww.iloc[-1]
    return dict(wins=dict(rows=[dict(label=r.measure, value=round(float(r.won_pct), 1), text=f"{r.won_pct:.0f}%",
                                     note=_n(int(r.games), "game")) for r in ww.itertuples()],
                          reference=50, **SG.lines(
                              f"The share of games in {where} won by the side that did more of each thing (games level on "
                              "it left out); the dashed line at 50% is a coin toss.",
                              f"{top.measure}: the side with more won {top.won_pct:.0f}% of {_n(int(top.games), 'game')} "
                              f"('{low.measure.lower()}' won only {low.won_pct:.0f}%)",
                              "Shows what to aim for in this competition: the longer the bar, the more that thing decides "
                              "games.", best_label="Decides most")))


# --------------------------------------------------------------------------- luck: wins against expected (the current 43)
def _luck(career, ids, where) -> dict:
    ew = PL.expected_wins(career, ids)
    if ew.empty:
        return dict(luck_none="No games yet.")
    hi, lo = ew.iloc[0], ew.iloc[-1]
    return dict(luck=dict(rows=[dict(label=r.team, value=round(float(r.luck), 2), text=f"{r.luck:+.1f}",
                                     note=f"won {r.won} of {r.decided}, expected {r.expected:.1f}") for r in ew.itertuples()],
                          **SG.lines(f"Each team's wins in {where} against the wins its runs scored and given away point to "
                                     "(blue more than expected, red fewer).",
                                     f"{hi.team} won {hi.won} of {hi.decided} ({pct(hi.win_pct)}) when their runs pointed to "
                                     f"{hi.expected:.1f} ({hi.expected_pct:.0f}%): {hi.luck:+.1f} wins. {lo.team}: {lo.luck:+.1f} "
                                     f"({lo.expected_pct:.0f}% expected, {pct(lo.win_pct)} actual)",
                                     "Separates luck from quality. Expected wins come from the share of runs a team scores (per "
                                     "wicket in multi-day cricket), fitted to these games. Above zero: they win the close ones; "
                                     "below: unlucky, or they lose the tight ones, so their results should improve.",
                                     best_label="Most wins above expected")))


# --------------------------------------------------------------------------- match-winners (the current 44, 45 + chart)
def _winners(career, ids, where, here, team, mine) -> dict:
    out: dict = {}
    mw = PL.match_winners(career, ids)
    if mw.empty:
        out["table_none"] = "No wins yet."
    else:
        x = mw.head(15)
        out["table"] = table(["Player", "Team", "Wins", "Share of team's wins"],
                             [[r.player, r.team, int(r.match_winning), pct(r.share)] for r in x.itertuples()],
                             num=[2, 3], hi=[r.team in set(mine) for r in x.itertuples()])
        out["table"]["note"] = "Contribution = runs, plus each wicket worth the competition's runs per wicket."
    dp = PL.dependence(career, ids)
    if dp.empty:
        out["leans_none"] = "Not enough games yet."
    else:
        out["leans"] = table(["Team", "Player", "When fires", "When not", "Gap"],
                             [[r.team, r.player, pct(r.pct_fired), pct(r.pct_not), f"{r.gap:+.0f}"] for r in dp.itertuples()],
                             num=[2, 3, 4], hi=[r.team in set(mine) for r in dp.itertuples()])
        out["leans_head"] = (f"Win % when their key player fires ({dp.attrs.get('big', 50)}+ or {dp.attrs.get('haul', 3)}+ "
                             "wickets) v when not")
    # the match-winners chart (answer 14): the team picked, yours when you play here, else the side with the most wins
    teams = sorted(set(here.home) | set(here.away))
    if teams:
        wins = here.winner.value_counts()
        if team not in teams:
            team = next((t for t in mine if t in set(teams)), None) or sorted(teams, key=lambda t: (-int(wins.get(t, 0)), t))[0]
        w = SG.match_winners(SG.results(career, team, here.match_id), team)
        out.update(teams=teams, team=team, winners=dict(w, team=team, yours=team in set(mine)))
    return out


# --------------------------------------------------------------------------- style maps (the current 46)
def _styles(career, scope, where) -> dict:
    bat, bowl, _, base = player_tables(career, scope)
    least = STYLE_MINS[base.kind]
    out: dict = dict(least=least)
    b = PL.batting_styles(bat[bat.balls >= least], base)
    if len(b) < 3:
        out["bat_none"] = "Not enough batters yet."
    else:
        share = (b["style"] == "Scores lots, scores fast").mean() * 100
        best = b[b["style"] == "Scores lots, scores fast"].sort_values("runs_above_average", ascending=False)
        out["bat"] = dict(points=[dict(player=r.player, team=r.teams, x=round(float(r.average), 2), y=round(float(r.strike_rate), 2),
                                       style=r.style) for r in b.itertuples()],
                          x_label="Average", y_label="Strike rate", x_ref=round(float(base.average), 2),
                          y_ref=round(float(base.strike_rate), 2), x_low=False, y_low=False,
                          corners=["Scores lots, scores fast", "Fast but out often", "Scores lots, steadily", "Slow and out often"],
                          **SG.lines(f"Every batter in {where} with {least}+ balls faced, by average and strike rate; the dashed "
                                     "lines are the average batter here.",
                                     (f"{share:.0f}% of the {len(b)} batters score lots and fast (top right): "
                                      f"above {base.average:.1f} and {base.strike_rate:.1f} at once"
                                      + (f", {best.iloc[0].player} the most runs above average of them" if len(best) else "")),
                                     "Tells you how each batter scores: fast or steady, reliable or not. Use it to pick a "
                                     "finisher (high strike rate) or an anchor (high average).", best_label="Best corner"))
    w = PL.bowling_styles(bowl[bowl.balls >= least], base)
    if len(w) < 3:
        out["bowl_none"] = "Not enough bowlers yet."
    else:
        share = (w["style"] == "Wicket-taker and tight").mean() * 100
        best = w[w["style"] == "Wicket-taker and tight"].sort_values("runs_saved", ascending=False)
        out["bowl"] = dict(points=[dict(player=r.player, team=r.teams, x=round(float(r.economy), 2), y=round(float(r.strike_rate), 2),
                                        style=r.style) for r in w.itertuples()],
                           x_label="Economy (runs per over)", y_label="Strike rate (balls per wicket)",
                           x_ref=round(float(base.economy), 2), y_ref=round(float(base.bowl_strike_rate), 2), x_low=True, y_low=True,
                           corners=["Costly and few wickets", "Tight but few wickets", "Wicket-taker but costly", "Wicket-taker and tight"],
                           **SG.lines(f"Every bowler in {where} with {least}+ balls bowled, by economy and strike rate; the "
                                      "dashed lines are the average bowler here.",
                                      (f"{share:.0f}% of the {len(w)} bowlers take wickets and keep it tight (bottom left): "
                                       f"cheaper than {base.economy:.2f} an over and a wicket quicker than every "
                                       f"{base.bowl_strike_rate:.0f} balls"
                                       + (f", {best.iloc[0].player} the most runs saved of them" if len(best) else "")),
                                      "Tells you who takes wickets and who keeps it tight, so you know who to bowl when you "
                                      "need a wicket and who when you need to stop the runs.", best_label="Best corner"))
    out["note"] = "The dashed lines are the competition's average batter and bowler. Blue dots are in the best corner."
    return out


# --------------------------------------------------------------------------- boom or bust (the current 47)
def _boom(career, ids, where) -> dict:
    bb = PL.boom_or_bust(career, ids)
    if bb.empty:
        return dict(boom_none="Not enough innings yet.")
    big = int(bb.attrs.get("big", 50))
    lo, bg = float(bb.attrs["low_median"]), float(bb.attrs["big_median"])
    share_b = (bb.label == "Boom or bust").mean() * 100
    share_r = (bb.label == "Reliable and big").mean() * 100
    chart = dict(points=[dict(player=r.player, team=r.team, x=round(float(r.low_pct), 2), y=round(float(r.big_pct), 2), style=r.label)
                         for r in bb.itertuples()],
                 x_label="% of innings under 10", y_label=f"% of innings {big}+", x_ref=round(lo, 2), y_ref=round(bg, 2),
                 x_low=True, y_low=False, corners=["Boom or bust", "Reliable and big", "Struggling", "Steady, rarely big"],
                 **SG.lines(f"Every batter in {where} with 8+ innings, by how often they fail (under 10) and how often they go "
                            f"big ({big}+); the dashed lines are the middle batter on each.",
                            f"{share_r:.0f}% of {len(bb)} batters are reliable and make big scores (top left), {share_b:.0f}% "
                            f"boom or bust (top right); the middle batter is out for under 10 in {lo:.0f}% of innings and "
                            f"makes {big}+ in {bg:.0f}%",
                            "Shows how dependable each batter is, not just how good: a boom-or-bust player can win you a game "
                            "but needs a steady one alongside.", best_label="Who's where"))
    rows = [[r.player, int(r.innings), f"{r.mean:.1f}", f"{r.low_pct:.0f}%", f"{r.big_pct:.0f}%", f"{r.spread:.2f}", r.label]
            for r in bb.head(25).itertuples()]
    t = table(["Player", "Inns", "Runs per inns", "Under 10", f"{big}+", "Spread", "Type"], rows, num=[1, 2, 3, 4, 5])
    t["note"] = ("Spread: how much the scores bounce around compared with the player's own average (higher = less "
                 "predictable). The lines are the middle player on each.")
    return dict(boom=chart, boom_table=t)


# --------------------------------------------------------------------------- is the form real? (the current 48)
def _form(career, ids, mine) -> dict:
    fr = PL.form_is_real(career, ids)
    if fr.empty:
        return dict(form_none="Players need 12+ innings here for this.")
    x = fr.head(25)
    t = table(["Player", "Team", "Inns", "Last 8 (runs per inns)", "Before", "Strength", "Verdict"],
              [[r.player, r.team, int(r.innings), f"{r.recent:.1f}", f"{r.before:.1f}", f"{r.z:+.1f}", r.verdict]
               for r in x.itertuples()], num=[2, 3, 4, 5], hi=[r.verdict.startswith("Real") for r in x.itertuples()])
    t["note"] = ("Strength: how far the recent run is from normal, allowing for how much this player's scores usually vary. "
                 "2 or more = real (it would happen by luck about 1 time in 20); 1 to 2 = maybe; under 1 = probably just luck.")
    return dict(form=t)


# --------------------------------------------------------------------------- bat or bowl first? (the current 50)
def _bat_or_bowl(career, ids, where, mine) -> dict:
    bft, avg = TP.bat_first_table(career, ids)
    multi = avg["multi"]
    second = "batting second" if multi else "chasing"
    a, b = avg["first"], avg["second"]
    if not a["decided"]:
        return dict(toss_none="No finished games yet.")
    diff = (a["win_pct"] or 0) - 50 if not multi else (a["win_pct"] or 0) - (b["win_pct"] or 0)
    pick = "Bat first" if diff > 0 else f"Bowl first ({second})"
    sure = ("a clear edge" if abs(diff) >= 10 and a["decided"] >= 20 else "a slight edge" if abs(diff) >= 4
            else "no real edge either way")
    out = dict(toss=dict(verdict=pick if sure != "no real edge either way" else "Either: no real edge",
                         line=(f"The side batting first won {pct(a['win_pct'])} of {a['decided']} decided games in {where}"
                               + (f" (W–D–L {a['won']}–{a['drawn']}–{a['lost']}); batting second {pct(b['win_pct'])}" if multi else "")
                               + f": {sure}.")))
    rows = []
    for r in bft.sort_values("team").itertuples():
        if not (r.bf_decided and r.ch_decided):
            continue
        d = (r.bf_win_pct or 0) - (r.ch_win_pct or 0)
        rows.append([r.team, f"{pct(r.bf_win_pct)} ({r.bf_decided})", f"{pct(r.ch_win_pct)} ({r.ch_decided})",
                     "Bat first" if d >= 10 else "Bowl first" if d <= -10 else "Either"])
    if rows:
        t = table(["Team", "Batting first", "Batting second" if multi else "Chasing", "Advice"], rows, num=[1, 2],
                  hi=[r[0] in set(mine) for r in rows])
        t["note"] = "Their own win % each way (decided games in brackets). Advice needs a 10-point gap; with few games it is only a hint."
        out["teams_table"] = t
    return out
