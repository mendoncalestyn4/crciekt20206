import streamlit as st

from ccstats import players as PL
from ccstats.stats import Scope
from ui import state
from ui.charts import signed, pct, CONFIG, bars, fmt
from ui.theme import chart_note, html_table, match_link, page_header, player_link, safe_section

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
section = c1.selectbox("Section", list(sections.index), key="st_section", format_func=lambda s: f"{s} · {sections[s]} matches")
seasons = sorted(m[m.section == section].season.unique(), reverse=True)
season = c2.selectbox("Season", ["All seasons"] + seasons, key="st_season")
ids = Scope(sections=[section], seasons=[] if season == "All seasons" else [season]).match_ids(m)
all_ids = Scope(sections=[section]).match_ids(m)  # milestones and records count the whole section
mine = set(state.my_teams(career))


def mark(teams) -> list[str]:
    return ["hi" if any(t in mine for t in str(x).split(" / ")) else "" for x in teams]


tabs = st.tabs(["Form guide", "Milestones and records", "Win when they fire", "Heroes in defeat", "Carried the team",
                "Quirks", "After a hundred", "Pairs", "Player of the Series", "Upsets"])

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
                     "▲" if r.trend > 5 else "▼" if r.trend < -5 else "▬"] for r in fb.head(30).itertuples()]
            html_table(rows, ["Player", "Team", "Last 5", "Avg last 5", "Avg", ""], numeric={3, 4}, raw={0},
                       row_class=mark(fb.head(30).team))
    with right, st.container(border=True):
        st.markdown("**Bowlers** · last 5 innings, wickets per innings against their own")
        if fw.empty:
            st.caption("Bowlers need 6+ innings.")
        else:
            rows = [[player_link(r.player), r.team, r.last, fmt(r.recent_wpi, 1), fmt(r.career_wpi, 1),
                     fmt(r.recent_econ, 2), "▲" if r.trend > 0.4 else "▼" if r.trend < -0.4 else "▬"]
                    for r in fw.head(30).itertuples()]
            html_table(rows, ["Player", "Team", "Last 5", "Wkts/inns last 5", "Wkts/inns", "Econ last 5", ""],
                       numeric={3, 4, 5}, raw={0}, row_class=mark(fw.head(30).team))
    st.caption("▲ hotter than usual · ▼ colder · ▬ about normal. Your team's players are highlighted. "
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
    for box, d, title, what in ((left, wb, "When they make 50+", "50+ scores"), (right, ww, "When they take 3+ wickets",
                                                                                  "3-fors")):
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
            st.caption("None yet.")
    with right, st.container(border=True):
        st.markdown("**Best bowling in a losing side**")
        rows = [[player_link(r.player), f"{r.wickets}/{r.runs}", r.team, r.opposition,
                 match_link(r.match_id, f"{r.date:%d %b %Y}")] for r in hw.itertuples()]
        if rows:
            html_table(rows, ["Player", "Figures", "For", "Against", "Match"], raw={0, 4})
        else:
            st.caption("None yet.")

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
            st.caption("None yet.")
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
        rows = [[r.pair, r.team, r.stands, r.runs, f"{r.average:.1f}", r.best, r.fifty_plus] for r in bp.head(20).itertuples()]
        if rows:
            html_table(rows, ["Pair", "Team", "Stands", "Runs", "Avg", "Best", "50+"], numeric={2, 3, 4, 5, 6},
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
