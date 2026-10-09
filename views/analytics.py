import streamlit as st

from ccstats import players as PL
from ccstats import teamplay as TP
from ccstats.stats import Scope
from ui import state
from ui.charts import _n, pct, CONFIG, bars, fmt, quadrant_chart
from ui.theme import chart_note, html_table, page_header, player_link, safe_section

career = state.current()
if career is None:
    st.info("Load a career on the Home page first.")
    st.stop()
state.stop_if_no_matches(career)

m = career.matches
page_header("Analytics", "Under the bonnet",
            "Deeper numbers for one section: runs against what the situation called for, averages made fair, what "
            "really wins games, luck, match-winners, styles, consistency and whether a run of form is real.")
c1, c2 = st.columns([2, 1])
sections = m.section.value_counts()
state.recall("an_section", "section", list(sections.index))
section = c1.selectbox("Section", list(sections.index), key="an_section", on_change=state.remember("an_section", "section"), format_func=lambda s: f"{s} · {sections[s]} matches")
seasons = sorted(m[m.section == section].season.unique(), reverse=True)
state.recall("an_season", "season", ["All seasons"] + seasons)
season = c2.selectbox("Season", ["All seasons"] + seasons, key="an_season", on_change=state.remember("an_season", "season"))
scope = Scope(sections=[section], seasons=[] if season == "All seasons" else [season])
ids = scope.match_ids(m)
where = f"{section}{'' if season == 'All seasons' else ' ' + season}"
mine = state.my_teams(career)

tabs = st.tabs(["Runs above expected", "Fair averages", "What wins games", "Luck", "Match-winners", "Style maps",
                "Boom or bust", "Is the form real?", "Bat or bowl first?"])

# ---------------------------------------------------------------- 38
with tabs[0], safe_section("runs above expected"):
    rae = state.memo(PL.runs_above_expected, career, ids)
    with st.container(border=True):
        st.markdown("**Runs above expected** · each innings against what the average batter made coming in at the same "
                    "position with the same number of wickets down")
        if rae.empty:
            st.caption("Not enough innings yet (5 or more each).")
        else:
            top = rae.head(12)
            st.plotly_chart(bars(top.player, top.above, "Runs above expected", 0, signed=True,
                                 notes=[f"{r} runs in {i} innings, {e:.0f} expected · usually bats {p}"
                                        for r, i, e, p in zip(top.runs, top.innings, top.expected, top.usual_position)]),
                            width="stretch", config=CONFIG, key="an_rae")
            t0 = top.iloc[0]
            edge_pct = t0.above / t0.expected * 100 if t0.expected else 0
            chart_note(f"{t0.player} has made {t0.above:+.0f} runs more than an average batter would have in the same "
                       f"spots ({t0.runs} runs against {t0.expected:.0f} expected, {edge_pct:+.0f}%), the most in {where}. "
                       f"Blue bars are above what was expected, red below.",
                       "Fair credit for batting position: a no. 7 who makes 30 coming in at 5 down has done more than an "
                       "opener making 30 at 0 for 0. Situations are grouped by wickets down when they came in: 0, 1, 2, "
                       "3-4, 5+.")
            rows = [[player_link(r.player), r.team, r.innings, r.runs, f"{r.expected:.0f}", f"{r.above:+.0f}",
                     f"{r.per_innings:+.1f}"] for r in rae.head(30).itertuples()]
            html_table(rows, ["Player", "Team", "Inns", "Runs", "Expected", "Above", "Per innings"],
                       numeric={2, 3, 4, 5, 6}, raw={0})

# ---------------------------------------------------------------- 39, 40
with tabs[1], safe_section("fair averages"):
    left, right = st.columns(2, gap="medium")
    with left:
        aa = state.memo(PL.adjusted_averages, career, ids)
        with st.container(border=True):
            st.markdown("**Batting averages made fair**")
            if aa.empty:
                st.caption("Not enough innings yet.")
            else:
                rows = [[player_link(r.player), r.innings, fmt(r.average, 1), fmt(r.adjusted, 1), fmt(r.settled, 1),
                         "✅ reliable" if r.tag == "reliable" else "⏳ still settling"] for r in aa.head(25).itertuples()]
                html_table(rows, ["Player", "Inns", "Average", "v attacks faced", "Settled", ""],
                           numeric={1, 2, 3, 4}, raw={0})
    with right:
        ab = state.memo(PL.adjusted_bowling, career, ids)
        with st.container(border=True):
            st.markdown("**Bowling averages made fair** · lower is better")
            if ab.empty:
                st.caption("Not enough innings yet.")
            else:
                rows = [[player_link(r.player), r.innings, fmt(r.average, 1), fmt(r.adjusted, 1), fmt(r.settled, 1),
                         "✅ reliable" if r.tag == "reliable" else "⏳ still settling"] for r in ab.head(25).itertuples()]
                html_table(rows, ["Player", "Inns", "Average", "v batting faced", "Settled", ""],
                           numeric={1, 2, 3, 4}, raw={0})
    st.caption("**v attacks faced**: runs against an attack that gives away fewer runs per wicket than average count for "
               "more (and the other way round for bowlers). **Settled**: a few average innings are added to everyone, "
               "so a hot start over a handful of games is pulled towards the section average until there are enough "
               "dismissals to trust it. Sorted by the settled figure.")

# ---------------------------------------------------------------- 42
with tabs[2], safe_section("what wins games"):
    ww = state.memo(PL.what_wins, career, ids)
    with st.container(border=True):
        st.markdown(f"**What wins games in {where}** · % of games won by the side that did more of each")
        if ww.empty:
            st.caption("No finished games yet.")
        else:
            st.plotly_chart(bars(ww.measure, ww.won_pct, "% of games won by the side that did this", 0, reference=50,
                                 reference_label="coin toss", x_range=[0, 112],
                                 texts=[f"{p:.0f}%" for p in ww.won_pct], notes=[f"{n} games" for n in ww.games]),
                            width="stretch", config=CONFIG, key="an_ww")
            top = ww.iloc[0]
            low = ww.iloc[-1]
            chart_note(f"The side with the {top.measure[0].lower() + top.measure[1:]} won {top.won_pct:.0f}% of "
                       f"{_n(top.games, 'game')}, the strongest sign of a win here; '{low.measure.lower()}' won only "
                       f"{low.won_pct:.0f}%. The dashed line at 50% is a coin toss.",
                       "Shows what to aim for in this competition: the longer the bar, the more that thing decides "
                       "games. Games where both sides were level on a measure are left out of it.")

# ---------------------------------------------------------------- 43
with tabs[3], safe_section("expected wins"):
    ew = state.memo(PL.expected_wins, career, ids)
    with st.container(border=True):
        st.markdown("**Wins against expected wins** · from the runs each team scored and gave away")
        if ew.empty:
            st.caption("No games yet.")
        else:
            st.plotly_chart(bars(ew.team, ew.luck, "Wins above expected", 1, signed=True,
                                 notes=[f"won {w} of {d}, expected {e:.1f}" for w, d, e in zip(ew.won, ew.decided, ew.expected)]),
                            width="stretch", config=CONFIG, key="an_ew")
            hi_, lo_ = ew.iloc[0], ew.iloc[-1]
            chart_note(f"{hi_.team} won {hi_.won} of {hi_.decided} ({pct(hi_.win_pct)}) when their runs pointed to "
                       f"{hi_.expected:.1f} ({hi_.expected_pct:.0f}%): {hi_.luck:+.1f} wins. {lo_.team} won {lo_.won}, "
                       f"{lo_.luck:+.1f} on what their runs deserved ({lo_.expected_pct:.0f}% expected, "
                       f"{pct(lo_.win_pct)} actual).",
                       "Separates luck from quality. Expected wins come from the share of runs a team scores (per "
                       "wicket in multi-day cricket), fitted to these games. Above zero: they win the close ones; "
                       "below: unlucky, or they lose the tight ones, so their results should improve.")

# ---------------------------------------------------------------- 44, 45
with tabs[4], safe_section("match-winners"):
    left, right = st.columns(2, gap="medium")
    with left:
        mw = state.memo(PL.match_winners, career, ids)
        with st.container(border=True):
            st.markdown("**Match-winners** · the winning side's biggest contributor in each win")
            if mw.empty:
                st.caption("No wins yet.")
            else:
                rows = [[player_link(r.player), r.team, r.match_winning, f"{pct(r.share)}"] for r in mw.head(15).itertuples()]
                html_table(rows, ["Player", "Team", "Wins", "Share of team's wins"], numeric={2, 3}, raw={0},
                           row_class=["hi" if r.team in mine else "" for r in mw.head(15).itertuples()])
                st.caption("Contribution = runs, plus each wicket worth the section's runs per wicket.")
    with right:
        dp = state.memo(PL.dependence, career, ids)
        with st.container(border=True):
            st.markdown(f"**Who each team leans on** · win % when their key player fires ({dp.attrs.get('big', 50)}+ "
                        f"or {dp.attrs.get('haul', 3)}+ wickets) v when not")
            if dp.empty:
                st.caption("Not enough games yet.")
            else:
                rows = [[r.team, player_link(r.player), f"{pct(r.pct_fired)}", f"{pct(r.pct_not)}", f"{r.gap:+.0f}"]
                        for r in dp.itertuples()]
                html_table(rows, ["Team", "Player", "When fires", "When not", "Gap"], numeric={2, 3, 4}, raw={1},
                           row_class=["hi" if r.team in mine else "" for r in dp.itertuples()])

# ---------------------------------------------------------------- 46
with tabs[5], safe_section("style maps"):
    bat, bowl, _, base = state.tables(career, scope)
    mins = {"t20": 60, "one": 120, "multi": 200}[base.kind]
    left, right = st.columns(2, gap="medium")
    with left:
        b = PL.batting_styles(bat[bat.balls >= mins], base)
        with st.container(border=True):
            st.markdown(f"**Batting styles** · {mins}+ balls faced")
            if len(b) < 3:
                st.caption("Not enough batters yet.")
            else:
                st.plotly_chart(quadrant_chart(b, "average", "strike_rate", "Average", "Strike rate", base.average,
                                               base.strike_rate, ("Scores lots, scores fast", "Fast but out often",
                                                                  "Scores lots, steadily", "Slow and out often")),
                                width="stretch", config=CONFIG, key="an_bstyle")
                best_c = (b["style"] == "Scores lots, scores fast").mean() * 100
                chart_note(f"{best_c:.0f}% of the {len(b)} batters are in the top-right corner: above the average of "
                           f"{base.average:.1f} and the strike rate of {base.strike_rate:.1f} at the same time.",
                           "Tells you how each batter scores: fast or steady, reliable or not. Use it to pick a "
                           "finisher (high strike rate) or an anchor (high average).")
    with right:
        w = PL.bowling_styles(bowl[bowl.balls >= mins], base)
        with st.container(border=True):
            st.markdown(f"**Bowling styles** · {mins}+ balls bowled")
            if len(w) < 3:
                st.caption("Not enough bowlers yet.")
            else:
                st.plotly_chart(quadrant_chart(w, "economy", "strike_rate", "Economy (runs per over)",
                                               "Strike rate (balls per wicket)", base.economy, base.bowl_strike_rate,
                                               ("Costly and few wickets", "Tight but few wickets", "Wicket-taker but costly",
                                                "Wicket-taker and tight"), x_better_low=True, y_better_low=True),
                                width="stretch", config=CONFIG, key="an_wstyle")
                best_w = (w["style"] == "Wicket-taker and tight").mean() * 100
                chart_note(f"{best_w:.0f}% of the {len(w)} bowlers are in the bottom-left corner: cheaper than "
                           f"{base.economy:.2f} an over and quicker to a wicket than every {base.bowl_strike_rate:.0f} balls.",
                           "Tells you who takes wickets and who keeps it tight, so you know who to bowl when you need a "
                           "wicket and who when you need to stop the runs.")
    st.caption("The dashed lines are the section's average batter and bowler. Blue dots are in the best corner.")

# ---------------------------------------------------------------- 47
with tabs[6], safe_section("boom or bust"):
    bb = state.memo(PL.boom_or_bust, career, ids)
    with st.container(border=True):
        st.markdown("**Boom or bust** · how a batter's scores are spread (8+ innings)")
        if bb.empty:
            st.caption("Not enough innings yet.")
        else:
            big = bb.attrs.get("big", 50)
            d = bb.rename(columns={"low_pct": "low", "big_pct": "big"}).assign(style=bb.label)
            st.plotly_chart(quadrant_chart(d, "low", "big", "% of innings under 10", f"% of innings {big}+",
                                           bb.attrs["low_median"], bb.attrs["big_median"],
                                           ("Boom or bust", "Reliable and big", "Struggling", "Steady, rarely big"),
                                           x_better_low=True),
                            width="stretch", config=CONFIG, key="an_boom")
            share_b = (bb.label == "Boom or bust").mean() * 100
            share_r = (bb.label == "Reliable and big").mean() * 100
            chart_note(f"Of {len(bb)} batters, {share_r:.0f}% are reliable and make big scores (top left) and "
                       f"{share_b:.0f}% are boom or bust (top right). The middle batter is out for under 10 in "
                       f"{bb.attrs['low_median']:.0f}% of innings and makes {big}+ in {bb.attrs['big_median']:.0f}%.",
                       "Shows how dependable each batter is, not just how good: a boom-or-bust player can win you a "
                       "game but needs a steady one alongside.")
            rows = [[player_link(r.player), r.innings, f"{r.mean:.1f}", f"{r.low_pct:.0f}%", f"{r.big_pct:.0f}%",
                     f"{r.spread:.2f}", r.label] for r in bb.head(25).itertuples()]
            html_table(rows, ["Player", "Inns", "Runs per inns", "Under 10", f"{big}+", "Spread", "Type"],
                       numeric={1, 2, 3, 4, 5}, raw={0})
            st.caption("Spread: how much the scores bounce around compared with the player's own average (higher = "
                       "less predictable). The lines are the middle player on each.")

# ---------------------------------------------------------------- 48
with tabs[7], safe_section("form"):
    fr = state.memo(PL.form_is_real, career, ids)
    with st.container(border=True):
        st.markdown("**Is the form real?** · last 8 innings against their earlier innings")
        if fr.empty:
            st.caption("Players need 12+ innings here for this.")
        else:
            rows = [[player_link(r.player), r.team, r.innings, f"{r.recent:.1f}", f"{r.before:.1f}", f"{r.z:+.1f}", r.verdict]
                    for r in fr.head(25).itertuples()]
            html_table(rows, ["Player", "Team", "Inns", "Last 8 (runs per inns)", "Before", "Strength", "Verdict"],
                       numeric={2, 3, 4, 5}, raw={0},
                       row_class=["hi" if r.verdict.startswith("Real") else "" for r in fr.head(25).itertuples()])
            st.caption("Strength: how far the recent run is from normal, allowing for how much this player's scores "
                       "usually vary. 2 or more = real (it would happen by luck about 1 time in 20); 1 to 2 = maybe; "
                       "under 1 = probably just luck.")

# ---------------------------------------------------------------- 50
with tabs[8], safe_section("bat or bowl first"):
    bft, avg = state.memo(TP.bat_first_table, career, ids)
    multi = avg["multi"]
    second = "batting second" if multi else "chasing"
    with st.container(border=True):
        a, b = avg["first"], avg["second"]
        st.markdown(f"**Bat or bowl first in {where}?**")
        if not a["decided"]:
            st.caption("No finished games yet.")
        else:
            diff = (a["win_pct"] or 0) - 50 if not multi else (a["win_pct"] or 0) - (b["win_pct"] or 0)
            pick = "Bat first" if diff > 0 else f"Bowl first ({second})"
            sure = "a clear edge" if abs(diff) >= 10 and a["decided"] >= 20 else "a slight edge" if abs(diff) >= 4 \
                else "no real edge either way"
            st.markdown(f"### {pick if sure != 'no real edge either way' else 'Either: no real edge'}")
            st.caption(f"The side batting first won {pct(a['win_pct'])} of {a['decided']} decided games"
                       + (f" (W–D–L {a['won']}–{a['drawn']}–{a['lost']}); batting second {pct(b['win_pct'])}"
                          if multi else "") + f": {sure}.")
            rows = []
            for r in bft.sort_values("team").itertuples():
                if not (r.bf_decided and r.ch_decided):
                    continue
                d = (r.bf_win_pct or 0) - (r.ch_win_pct or 0)
                adv = "Bat first" if d >= 10 else "Bowl first" if d <= -10 else "Either"
                rows.append([r.team, f"{pct(r.bf_win_pct)} ({r.bf_decided})", f"{pct(r.ch_win_pct)} ({r.ch_decided})",
                             adv])
            if rows:
                st.markdown("**Team by team** · their own win % each way (decided games in brackets)")
                html_table(rows, ["Team", "Batting first", "Chasing" if not multi else "Batting second", "Advice"],
                           numeric={1, 2}, row_class=["hi" if r[0] in mine else "" for r in rows])
                st.caption("Advice needs a 10-point gap; with few games it is only a hint.")
