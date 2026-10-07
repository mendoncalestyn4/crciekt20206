import pandas as pd
import streamlit as st

from ccstats import players as PL
from ccstats import playerdeep as PD
from ccstats import teamdeep as TD
from ccstats.stats import Scope
from ui import state
from ui.charts import _n, signed, pct, CONFIG, bars, fmt
from ui.theme import chart_note, html_table, kpis, match_link, page_header, player_link, safe_section

career = state.current()
if career is None:
    st.info("Load a career on the Home page first.")
    st.stop()

m = career.matches
page_header("Player stories", "The stories behind the numbers",
            "Who's in form, who's closing in on a milestone or a record, who wins games, who stands up when the team "
            "loses, and the odd ones: nervous nineties, pairs and not-outs.")
c1, c2 = st.columns([2, 1])
sections = m.section.value_counts()
state.recall("st_section", "section", list(sections.index))
section = c1.selectbox("Section", list(sections.index), key="st_section", on_change=state.remember("st_section", "section"), format_func=lambda s: f"{s} · {sections[s]} matches")
seasons = sorted(m[m.section == section].season.unique(), reverse=True)
state.recall("st_season", "season", ["All seasons"] + seasons)
season = c2.selectbox("Season", ["All seasons"] + seasons, key="st_season", on_change=state.remember("st_season", "season"))
ids = Scope(sections=[section], seasons=[] if season == "All seasons" else [season]).match_ids(m)
all_ids = Scope(sections=[section]).match_ids(m)  # milestones and records count the whole section
mine = set(state.my_teams(career))


def mark(teams) -> list[str]:
    return ["hi" if any(t in mine for t in str(x).split(" / ")) else "" for x in teams]


def pct_s(v) -> str:
    t = signed(v)
    return t if t == "–" else t + "%"


tabs = st.tabs(["Form guide", "Milestones and records", "Win when they fire", "Heroes in defeat", "Carried the team",
                "Quirks", "After a hundred", "Pairs", "Player of the Series", "Upsets", "Fastest to", "Match impact",
                "Badges", "Batter v bowler", "Clutch"])

# ---------------------------------------------------------------- 18
with tabs[0], safe_section("form guide"):
    fb, fw = state.memo(PL.form_guide, career, ids)
    left, right = st.columns(2, gap="medium")
    with left, st.container(border=True):
        st.markdown("**Batters** · last 5 innings (oldest first), against their own average")
        if fb.empty:
            st.caption("Batters need 6+ innings.")
        else:
            rows = [[player_link(r.player), r.team, r.last, fmt(r.recent_avg, 1), fmt(r.career_avg, 1),
                     "▲" if r.trend > 0.25 * r.career_avg else "▼" if r.trend < -0.25 * r.career_avg else "▬"] for r in fb.head(30).itertuples()]
            html_table(rows, ["Player", "Team", "Last 5", "Avg last 5", "Avg", ""], numeric={3, 4}, raw={0},
                       row_class=mark(fb.head(30).team))
    with right, st.container(border=True):
        st.markdown("**Bowlers** · last 5 innings, wickets per innings against their own")
        if fw.empty:
            st.caption("Bowlers need 6+ innings.")
        else:
            rows = [[player_link(r.player), r.team, r.last, fmt(r.recent_wpi, 1), fmt(r.career_wpi, 1),
                     fmt(r.recent_econ, 2), "▲" if r.trend > 0.25 * r.career_wpi else "▼" if r.trend < -0.25 * r.career_wpi else "▬"]
                    for r in fw.head(30).itertuples()]
            html_table(rows, ["Player", "Team", "Last 5", "Wkts/inns last 5", "Wkts/inns", "Econ last 5", ""],
                       numeric={3, 4, 5}, raw={0}, row_class=mark(fw.head(30).team))
    st.caption("▲ hotter than usual (25%+ above their own average) · ▼ colder · ▬ about normal. Your team's players are highlighted. "
               "Analytics → Is the form real? says whether a hot run is more than luck.")

# ---------------------------------------------------------------- 9, 64
with tabs[1], safe_section("milestones"):
    left, right = st.columns(2, gap="medium")
    with left, st.container(border=True):
        mw = state.memo(PL.milestone_watch, career, all_ids)
        st.markdown(f"**Milestone watch** · close to a round number in {section} (all seasons)")
        if mw.empty:
            st.caption("Nobody is close to a milestone right now.")
        else:
            rows = [[player_link(r.player), r.team, f"{r.next:,} {r.what}", f"{r.now:,}", f"{r.needed:,}"]
                    for r in mw.head(25).itertuples()]
            html_table(rows, ["Player", "Team", "Milestone", "Now", "Needs"], numeric={3, 4}, raw={0},
                       row_class=mark(mw.head(25).team))
    with right, st.container(border=True):
        rw = state.memo(PL.record_watch, career, section)
        st.markdown(f"**Record watch** · records in {section} that could fall")
        if rw.empty:
            st.caption("No record is under threat right now.")
        else:
            rows = [[r.record, f"{r.holder} {r.record_value:,}", player_link(r.chaser), f"{r.now:,}", f"{r.needed:,}"]
                    for r in rw.itertuples()]
            html_table(rows, ["Record", "Holder", "Chaser", "Now", "Needs"], numeric={3, 4}, raw={2})
            st.caption("Career records: players within 15% of the leader. Season records: players within 25% while "
                       "the season is still going.")

# ---------------------------------------------------------------- 8
with tabs[2], safe_section("win when they fire"):
    wb, ww = state.memo(PL.win_when, career, ids)
    left, right = st.columns(2, gap="medium")
    big_, haul_ = wb.attrs.get("big", 50), wb.attrs.get("haul", 3)
    for box, d, title, what in ((left, wb, f"When they make {big_}+", f"{big_}+ scores"),
                                (right, ww, f"When they take {haul_}+ wickets", f"{haul_}-wicket hauls")):
        with box, st.container(border=True):
            st.markdown(f"**{title}** · their team's win % in those games and in the rest")
            if d.empty:
                st.caption(f"Nobody has 3+ {what} yet.")
            else:
                rows = [[player_link(r.player), r.team, r.times, f"{pct(r.pct_when)}", f"{pct(r.pct_other)}",
                         signed(r.lift)] for r in d.head(20).itertuples()]
                html_table(rows, ["Player", "Team", "Times", "Win % then", "Win % otherwise", "Lift"],
                           numeric={2, 3, 4, 5}, raw={0}, row_class=mark(d.head(20).team))

# ---------------------------------------------------------------- 12
with tabs[3], safe_section("heroes in defeat"):
    hb, hw = state.memo(PL.heroes_in_defeat, career, ids)
    left, right = st.columns(2, gap="medium")
    with left, st.container(border=True):
        st.markdown("**Best innings in a losing side**")
        rows = [[player_link(r.player), f"{r.runs}{'' if r.out else '*'} ({r.balls})", r.team, r.opposition,
                 match_link(r.match_id, f"{r.date:%d %b %Y}")] for r in hb.itertuples()]
        if rows:
            html_table(rows, ["Player", "Score", "For", "Against", "Match"], raw={0, 4})
        else:
            st.caption("Nothing yet.")
    with right, st.container(border=True):
        st.markdown("**Best bowling in a losing side**")
        rows = [[player_link(r.player), f"{r.wickets}/{r.runs}", r.team, r.opposition,
                 match_link(r.match_id, f"{r.date:%d %b %Y}")] for r in hw.itertuples()]
        if rows:
            html_table(rows, ["Player", "Figures", "For", "Against", "Match"], raw={0, 4})
        else:
            st.caption("Nothing yet.")

# ---------------------------------------------------------------- 13
with tabs[4], safe_section("carried the team"):
    ci, cp = state.memo(PL.carried, career, ids)
    left, right = st.columns(2, gap="medium")
    with left, st.container(border=True):
        st.markdown("**One-man shows** · biggest share of the team's total in one innings")
        rows = [[player_link(r.player), f"{r.runs}{'' if r.out else '*'}", f"{int(r.team_total)}", f"{r.share:.0f}%",
                 match_link(r.match_id, f"{r.team} v {r.opposition}")] for r in ci.itertuples()]
        if rows:
            html_table(rows, ["Player", "Runs", "Team total", "Share", "Match"], numeric={1, 2, 3}, raw={0, 4})
        else:
            st.caption("Nothing yet.")
    with right, st.container(border=True):
        st.markdown("**Who carries their team** · share of the team's runs over all their innings (5+)")
        top = cp.head(12)
        if top.empty:
            st.caption("Not enough innings yet.")
        else:
            st.plotly_chart(bars(top.player, top.share, "% of the team's runs", 1,
                                 notes=[f"{r} of {t} runs in {i} innings · {tm}" for r, t, i, tm in
                                        zip(top.runs, top.team_runs, top.innings, top.team)]),
                            width="stretch", config=CONFIG, key="st_carried")
            t0 = top.iloc[0]
            chart_note(f"{t0.player} makes {t0.share:.1f}% of {t0.team}'s runs in the innings they bat ({t0.runs} of "
                       f"{t0.team_runs}). An even share across 11 batters would be about 9%.",
                       "Shows which teams lean on one batter: if they fail, the team usually does too.")

# ---------------------------------------------------------------- 11
with tabs[5], safe_section("quirks"):
    q = state.memo(PL.quirks, career, ids)
    a, b, c = st.columns(3, gap="medium")
    with a, st.container(border=True):
        st.markdown("**Nervous nineties** · out between 90 and 99")
        rows = [[player_link(r.player), r.times, r.scores] for r in q["nineties"].head(15).itertuples()]
        if rows:
            html_table(rows, ["Player", "Times", "Scores"], numeric={1}, raw={0})
        else:
            st.caption("Nobody yet.")
    with b, st.container(border=True):
        st.markdown("**Pairs** · out for 0 in both innings of a match")
        rows = [[player_link(r.player), r.pairs, r.team] for r in q["pairs"].head(15).itertuples()]
        if rows:
            html_table(rows, ["Player", "Pairs", "Team"], numeric={1}, raw={0})
        else:
            st.caption("Nobody yet (only possible in two-innings matches).")
    with c, st.container(border=True):
        st.markdown("**Not out** · most unbeaten innings")
        rows = [[player_link(r.player), r.not_outs, r.innings, f"{r.pct:.0f}%"] for r in q["not_outs"].head(15).itertuples()]
        if rows:
            html_table(rows, ["Player", "Not out", "Inns", "%"], numeric={1, 2, 3}, raw={0})
        else:
            st.caption("Nobody yet.")

# ---------------------------------------------------------------- 37
with tabs[6], safe_section("after a hundred"):
    ah = state.memo(PL.after_hundred, career, ids)
    with st.container(border=True):
        st.markdown("**The innings after a hundred** · do they kick on or come back down?")
        if ah.empty:
            st.caption("No hundreds followed by another innings yet.")
        else:
            rows = [[player_link(r.player), r.hundreds, r.next_scores, fmt(r.next_avg, 1), fmt(r.average, 1)]
                    for r in ah.itertuples()]
            html_table(rows, ["Player", "Hundreds", "Next innings", "Avg next innings", "Avg overall"], numeric={1, 3, 4},
                       raw={0}, row_class=mark(ah.team))

# ---------------------------------------------------------------- 65
with tabs[7], safe_section("pairs"):
    left, right = st.columns(2, gap="medium")
    with left, st.container(border=True):
        bp = state.memo(PL.batting_pairs, career, ids)
        st.markdown("**Batting partners** · stands together (2+)")
        rows = [[r.pair, r.team, r.stands, r.runs, f"{r.average:.1f}", r.best, r.big_stands] for r in bp.head(20).itertuples()]
        if rows:
            html_table(rows, ["Pair", "Team", "Stands", "Runs", "Avg", "Best", f"{bp.attrs.get('stand', 50)}+"],
                       numeric={2, 3, 4, 5, 6},
                       row_class=mark(bp.head(20).team))
        else:
            st.caption("No pairs yet.")
        st.caption("Only stands where the scorecard shows who batted together (see Records → partnerships).")
    with right, st.container(border=True):
        wp = state.memo(PL.bowling_pairs, career, ids)
        st.markdown("**Bowling partners** · both bowled in the same innings (3+)")
        rows = [[r.pair, r.team, r.innings, r.wickets, f"{r.per_innings:.1f}", fmt(r.economy, 2)] for r in wp.head(20).itertuples()]
        if rows:
            html_table(rows, ["Pair", "Team", "Inns", "Wkts", "Wkts/inns", "Econ"], numeric={2, 3, 4, 5},
                       row_class=mark(wp.head(20).team))
        else:
            st.caption("No pairs yet.")

    # ---------------------------------------------------------------- 128 · chemistry · 131 · strike-rate pressure
    left, right = st.container(), st.container()  # stacked: each table needs the full width
    with left, safe_section("chemistry"), st.container(border=True):
        ch = state.memo(TD.chemistry, career, ids)
        st.markdown("**Partnership chemistry** · named pairs (3+ stands) against the average stand for the same wickets")
        if ch.empty:
            st.caption("No pair has 3 named stands yet.")
        else:
            html_table([[r.pair, r.team, r.stands, f"{r.average:.1f}", f"{r.expected:.1f}", pct_s(r.chemistry)]
                        for r in ch.head(15).itertuples()], ["Pair", "Team", "Stands", "Avg", "Expected", "Chemistry"],
                       numeric={2, 3, 4, 5}, row_class=mark(ch.head(15).team))
            st.caption("Expected: what the average pair makes for the same wickets here, so an opening pair is compared "
                       "with opening stands. +50% = half as much again.")
    with right, safe_section("strike-rate pressure"), st.container(border=True):
        sp_ = state.memo(TD.sr_pressure, career, ids)
        st.markdown("**Strike-rate pressure** · how fast their partners score when batting with them (top-7 batters)")
        if sp_.empty:
            st.caption("White-ball cricket only, and batters need 3+ named stands.")
        else:
            show_ = pd.concat([sp_.head(6), sp_.tail(6)]).drop_duplicates("player")
            html_table([[player_link(r.player), r.team, r.innings, fmt(r.partner_sr_with, 1), fmt(r.partner_sr_without, 1),
                         signed(r.effect) + ("%" if r.effect == r.effect else "")] for r in show_.itertuples()],
                       ["Batter", "Team", "Inns", "Partners' SR with them", "Partners' SR otherwise", "Effect"],
                       numeric={2, 3, 4, 5}, raw={0}, row_class=mark(show_.team))
            st.caption("The slowest-scoring partnerships first, then the fastest. The scorecards don't split a stand's "
                       "runs, so this uses the partners' whole innings: a hint, not proof.")

# ---------------------------------------------------------------- 16
with tabs[8], safe_section("player of the series"):
    ps = state.memo(PL.player_of_series, career, ids)
    with st.container(border=True):
        st.markdown("**Player of the Series** · most impact over each bilateral series")
        if ps.empty:
            st.caption("No bilateral series here.")
        else:
            first = m[m.series_id != ""].groupby("series_id").agg(start=("date", "min"), home=("home", "first"),
                                                                  away=("away", "first"))
            ps = ps.join(first, on="series_id").sort_values("start", ascending=False)
            rows = [[f"{r.start:%b %Y}", f"{r.home} v {r.away}", player_link(r.player), r.team, r.runs, r.wickets,
                     f"{r.points:.0f}"] for r in ps.itertuples()]
            html_table(rows, ["Started", "Series", "Player", "For", "Runs", "Wkts", "Impact"], numeric={4, 5, 6}, raw={2})
            st.caption("Impact = runs, plus each wicket worth the section's runs per wicket.")

# ---------------------------------------------------------------- 15
with tabs[9], safe_section("upsets"):
    up = state.memo(PL.upsets, career, section)
    with st.container(border=True):
        st.markdown(f"**Biggest upsets in {section}** · wins the ratings gave the least chance (all seasons)")
        if up.empty:
            st.caption("No upsets yet.")
        else:
            rows = [[match_link(r.match_id, f"{r.date:%d %b %Y}"), r.winner, r.loser, f"{r.chance:.0f}%",
                     f"{r.winner_elo:.0f} v {r.loser_elo:.0f}"] for r in up.itertuples()]
            html_table(rows, ["Match", "Winner", "Beat", "Their chance", "Elo going in"], numeric={3}, raw={0})
            st.caption("Chance from the two teams' Elo ratings before the game (see Rankings).")

# ---------------------------------------------------------------- 91
with tabs[10], safe_section("fastest"):
    fa = state.memo(PD.fastest, career, all_ids)
    unit_ = fa.attrs.get("unit", "innings")
    st.caption(f"Counted in {unit_}" + (" (as Test records are)" if unit_ == "matches" else "") + f", across every season of {section}.")
    if fa.empty:
        st.info("Nobody has reached a milestone here yet.")
    else:
        groups = list(fa.groupby(["what", "milestone"], sort=False))
        cols_ = st.columns(2, gap="medium")
        for i, ((what, ms), g) in enumerate(groups):
            with cols_[i % 2], st.container(border=True):
                st.markdown(f"**Fastest to {ms:,} {what}** · {len(g)} player{'s' if len(g) != 1 else ''} got there")
                html_table([[r.rank, player_link(r.player), r.team, f"{r.taken} {unit_}", f"{r.date:%d %b %Y}"]
                            for r in g.head(8).itertuples()], ["#", "Player", "Team", "Took", "Reached"],
                           numeric={0}, raw={1}, row_class=mark(g.head(8).team))

# ---------------------------------------------------------------- 94
with tabs[11], safe_section("match impact"):
    mi = state.memo(PD.match_impact, career, ids)
    if mi.empty:
        st.info("No matches yet.")
    else:
        left, right = st.columns(2, gap="medium")
        with left, st.container(border=True):
            st.markdown("**Biggest single-match impact**")
            top_ = mi.sort_values("impact", ascending=False).head(15)
            html_table([[player_link(r.player), r.team, f"{r.impact:.0f}", f"{int(r.runs)} & " + _n(r.wickets, "wkt"),
                         match_link(r.match_id, f"v {r.opponent}, {r.date:%d %b %Y}")] for r in top_.itertuples()],
                       ["Player", "Team", "Impact", "Did", "Match"], numeric={2}, raw={0, 4}, row_class=mark(top_.team))
        with right, st.container(border=True):
            g = mi.groupby(["player"]).agg(matches=("impact", "size"), avg=("impact", "mean"), team=("team", "last")) \
                .reset_index()
            g = g[g.matches >= max(3, int(g.matches.quantile(0.5)))].sort_values("avg", ascending=False).head(12)
            st.markdown("**Most impact per match** · regulars only")
            st.plotly_chart(bars(g.player, g.avg, "Impact per match", 0, notes=[f"{n} matches · {t}" for n, t in zip(g.matches, g.team)]),
                            width="stretch", config=CONFIG, key="st_impact")
            if len(g):
                chart_note(f"{g.player.iloc[0]} averages {g.avg.iloc[0]:.0f} a match, "
                           f"{(g.avg.iloc[0] / mi.impact.mean() - 1) * 100:+.0f}% on the average player's {mi.impact.mean():.0f}.",
                           "One number for everything a player does in a match: runs, plus each wicket worth the "
                           f"section's runs per wicket ({mi.attrs['rpw']:.0f})"
                           + (", with scoring speed and economy counted in white-ball cricket" if mi.attrs['kind'] != 'multi' else "")
                           + ", plus catches and stumpings.")

# ---------------------------------------------------------------- 119
with tabs[12], safe_section("badges"):
    ach = state.memo(PD.achievements, career, ids)
    left, right = st.columns([1.5, 1], gap="medium")
    with left, st.container(border=True):
        st.markdown(f"**Badges earned in {section}** · newest first")
        if ach.empty:
            st.caption("No badges yet.")
        else:
            html_table([[f"🏅 {r.badge}", player_link(r.player), r.team, r.detail, match_link(r.match_id, f"{r.date:%d %b %Y}")]
                        for r in ach.head(40).itertuples()], ["Badge", "Player", "Team", "", "Match"], raw={1, 4},
                       row_class=mark(ach.head(40).team))
    with right, st.container(border=True):
        st.markdown("**How common each badge is here**")
        if len(ach):
            vc = ach.badge.value_counts()
            html_table([[b, n] for b, n in vc.items()], ["Badge", "Times"], numeric={1})
        st.caption("T20: 5-for, hundred, 100 at a strike rate of 200+, fifty off 20 balls. One-day: 150, double hundred, "
                   "five-for. Tests: double and triple hundreds, seven in an innings, ten in a match, a hundred or five-for "
                   "in both innings, carried the bat, a pair. Any format: hundred on debut, hundred and five-for in a match, "
                   "three big scores in a row, a hundred or Player of the Match in a final.")
        for t in sorted(mine):
            tb = state.memo(PD.team_achievements, career, t)
            if len(tb):
                st.markdown(f"**{t}**: " + ", ".join(f"🏆 {r.badge} ({r.detail})" for r in tb.itertuples()))

# ---------------------------------------------------------------- 120
with tabs[13], safe_section("batter v bowler"):
    bat_names = sorted(career.batting[career.batting.match_id.isin(ids) & career.batting.did_bat].player.unique())
    bowl_names = sorted(career.bowling[career.bowling.match_id.isin(ids) & (career.bowling.balls > 0)].player.unique())
    c1_, c2_, c3_ = st.columns([1.3, 1.3, 1])
    batter = c1_.selectbox("Batter", bat_names, key="st_bvb_bat", index=None, placeholder="Pick a batter")
    bowler = c2_.selectbox("Bowler", bowl_names, key="st_bvb_bowl", index=None, placeholder="Pick a bowler")
    everywhere = c3_.toggle("Every competition", key="st_bvb_all", help="Count every match in the career, not only this section.")
    if batter and bowler:
        bv = PD.batter_v_bowler(career, batter, bowler, None if everywhere else ids)
        inns_ = bv["innings"]
        if inns_.empty:
            st.info(f"{bowler} has never bowled at {batter}'s side while {batter} batted" +
                    ("" if everywhere else f" in {section}") + ".")
        else:
            kpis([("Innings met", f"{bv['meetings']}"), (f"{bowler.split()[-1]} got them out", f"{bv['dismissals']}"),
                  ("Batter's runs in those innings", f"{bv['runs']}"),
                  ("Average v this bowler", fmt(bv["runs_when_out"] / bv["dismissals"], 1) if bv["dismissals"] else "–")])
            verdict = ("bowler on top" if bv["dismissals"] / bv["meetings"] >= 0.4 else
                       "batter on top" if bv["dismissals"] == 0 and bv["meetings"] >= 3 else "even")
            st.markdown(f"**Verdict: {verdict}** ({bv['dismissals']} dismissals in {bv['meetings']} innings).")
            html_table([[match_link(r.match_id, f"{r.date:%d %b %Y}"), r.section, f"{r.runs}{'' if r.out else '*'} ({r.balls})",
                         ("✔ " + r.dismissal) if r.bowler == bowler and r.out else r.dismissal or "not out",
                         f"{r.bowl_wkts}/{r.bowl_runs}"] for r in inns_.itertuples()],
                       ["Match", "", "Batter's score", "How out", "Bowler's figures"], raw={0})
            st.caption("The scorecards don't say which bowler each run came off, so these are the batter's whole innings "
                       "when the two met. ✔ = this bowler got them out.")

# ---------------------------------------------------------------- 127
with tabs[14], safe_section("clutch"):
    cb_, cw_ = state.memo(TD.clutch, career, ids)
    multi_ = cb_.attrs.get("kind") == "multi"
    st.caption("Big games: knockouts, close games (by this format's margins) and series deciders"
               + (", plus the 4th innings of a multi-day game." if multi_ else ".") + " Players need 3+ innings each way.")
    left, right = st.container(), st.container()  # stacked: each table needs the full width
    with left, st.container(border=True):
        st.markdown("**Batters in big games** · average then against average otherwise (top-7 batters)")
        if cb_.empty:
            st.caption("Not enough big games yet.")
        else:
            html_table([[player_link(r.player), r.team, r.clutch_innings, fmt(r.clutch_avg, 1), fmt(r.other_avg, 1),
                         pct_s(r.lift)] for r in cb_.head(15).itertuples()],
                       ["Batter", "Team", "Big-game inns", "Avg then", "Avg otherwise", "Lift"], numeric={2, 3, 4, 5},
                       raw={0}, row_class=mark(cb_.head(15).team))
    with right, st.container(border=True):
        st.markdown("**Bowlers in big games** · wickets per innings then against otherwise")
        if cw_.empty:
            st.caption("Not enough big games yet.")
        else:
            html_table([[player_link(r.player), r.team, r.clutch_innings, f"{r.clutch_wpi:.2f}", f"{r.other_wpi:.2f}",
                         fmt(r.clutch_avg, 1) if multi_ else fmt(r.clutch_econ, 2), pct_s(r.lift)]
                        for r in cw_.head(15).itertuples()],
                       ["Bowler", "Team", "Big-game inns", "Wkts/inns then", "Otherwise", "Avg then" if multi_ else "Econ then",
                        "Lift"], numeric={2, 3, 4, 5, 6}, raw={0}, row_class=mark(cw_.head(15).team))
