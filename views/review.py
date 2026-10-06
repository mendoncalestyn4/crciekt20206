import streamlit as st

from ccstats import seasonal as SN
from ui import state
from ui.charts import fmt
from ui.theme import esc, html_table, kpis, match_link, page_header, player_link, safe_section
from ui.xi import team_sheet

career = state.current()
if career is None:
    st.info("Load a career on the Home page first.")
    st.stop()

m = career.matches
page_header("Season review", "The end-of-season review",
            "Each competition's season in one place: the champions, Team of the Season, the leading players, the best "
            "match, the biggest upset and the records broken. International cricket gets a calendar-year review, "
            "awards style.")

INTL = "International cricket"
intl = SN.international_sections(career)
intl_secs = set(intl.values())
opts = []
for (sec, se), g in m[~m.section.isin(intl_secs)].groupby(["section", "season"]):
    opts.append((g.date.max(), sec, se))
if intl:
    for se, g in m[m.section.isin(intl_secs)].groupby("season"):
        opts.append((g.date.max(), INTL, se))
opts = [(sec, se) for _, sec, se in sorted(opts, reverse=True)]
if not opts:
    st.info("No matches yet.")
    st.stop()
labels = {o: f"{o[0]} {o[1]}" for o in opts}
remembered = state._remembered(career)
if "rv2_pick" not in st.session_state:
    want = (remembered.get("section"), remembered.get("season"))
    if want in labels:
        st.session_state["rv2_pick"] = want
pick = st.selectbox("Season", opts, format_func=labels.get, key="rv2_pick")
section, season = pick

# ---------------------------------------------------------------- international year
if section == INTL:
    with safe_section("year review"):
        yr = state.memo(SN.year_review, career, season)
        st.subheader(f"International cricket {season}", anchor=False)
        n_ = {f: d["matches"] for f, d in yr["formats"].items()}
        kpis([(f"{f}s" if f != "T20I" else "T20Is", f"{n}") for f, n in n_.items()]
             + ([("Cricketer of the Year", esc(yr["cricketer"].player.iloc[0]))] if len(yr["cricketer"]) else []))
        if len(yr["cricketer"]):
            with st.container(border=True):
                st.markdown("**🏅 Cricketer of the Year** · the most match impact across Tests, ODIs and T20Is")
                html_table([[i + 1, player_link(r.player), r.team, f"{r.impact:.0f}", r.runs, r.wickets, r.matches, r.formats]
                            for i, r in enumerate(yr["cricketer"].itertuples())],
                           ["", "Player", "Team", "Impact", "Runs", "Wkts", "Matches", "Formats"],
                           numeric={0, 3, 4, 5, 6}, raw={1})
        for fmt_, d in yr["formats"].items():
            st.markdown(f"### {fmt_} cricket · {d['matches']} match{'es' if d['matches'] != 1 else ''}")
            left, right = st.columns([1, 1.5], gap="medium")
            with left:
                with st.container(border=True):
                    p0 = d["player"]
                    st.markdown(f"**{fmt_} Player of the Year**")
                    if len(p0):
                        html_table([[i + 1, player_link(r.player), r.team, f"{r.impact:.0f}", r.runs, r.wickets]
                                    for i, r in enumerate(p0.itertuples())], ["", "Player", "Team", "Impact", "Runs", "Wkts"],
                                   numeric={0, 3, 4, 5}, raw={1})
                    tb, tw = d["top_bat"], d["top_bowl"]
                    bits = []
                    if len(tb):
                        bits.append(f"Most runs: **{tb.player.iloc[0]}** {int(tb.runs.iloc[0])}")
                    if len(tw):
                        bits.append(f"Most wickets: **{tw.player.iloc[0]}** {int(tw.wickets.iloc[0])}")
                    st.markdown(" · ".join(bits))
            with right:
                team_sheet(d["xi"], f"{fmt_} Team of the Year {season}")
        st.caption("Impact: runs, plus half the runs above what the format's strike rate would have made off the same "
                   "balls in white-ball cricket; each wicket worth the format's runs per wicket (plus runs kept below "
                   "its economy in white-ball cricket); a catch or stumping a quarter of a wicket. International "
                   "seasons are calendar years.")
    st.stop()

# ---------------------------------------------------------------- one competition's season
with safe_section("season review"):
    rv = state.memo(SN.season_review, career, section, season, state.my_teams(career))
    st.subheader(f"{section} {season}" + (" · so far" if rv["status"] != "complete" else ""), anchor=False)
    if rv["status"] != "complete":
        st.caption("This season isn't finished yet, so this is the review so far. It completes itself once the final "
                   "(or the last game) is in.")
    ch = rv["champions"]
    champ = ", ".join(ch.champions) if len(ch) else "–"
    tb, tw = rv["top_bat"], rv["top_bowl"]
    kpis([("Matches", f"{rv['matches']}"), ("Champions", esc(champ)),
          ("Top scorer", esc(f"{tb.player.iloc[0]} {int(tb.runs.iloc[0])}") if len(tb) else "–"),
          ("Top wicket-taker", esc(f"{tw.player.iloc[0]} {int(tw.wickets.iloc[0])}") if len(tw) else "–")])
    left, right = st.columns([1, 1.5], gap="medium")
    with left:
        with st.container(border=True):
            st.markdown("**🏆 Champions**")
            if len(ch):
                for r in ch.itertuples():
                    st.markdown(f"**{r.champions}** · {r.how}" + (f" · runners-up {r.runners_up}" if r.runners_up else "")
                                + (f" · {r.section}" if r.section != section else ""))
            else:
                st.caption("Not decided yet.")
            f = rv["final"]
            if f is not None:
                st.markdown("The final: " + match_link(f.match_id, f"{f.home} v {f.away}") + f" · {esc(f.result)}"
                            + (f" · Player of the Match {esc(f.player_of_match)}" if f.player_of_match else ""),
                            unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("**Leading players**")
            rows = [["Runs", player_link(r.player), f"{int(r.runs)} at {fmt(r.average, 1)}"] for r in tb.itertuples()]
            rows += [["Wickets", player_link(r.player), f"{int(r.wickets)} at {fmt(r.average, 1)}"] for r in tw.itertuples()]
            bb, bw = rv["breakout_bat"], rv["breakout_bowl"]
            if len(bb):
                r = bb.iloc[0]
                rows.append(["Breakout batter", player_link(r.player), f"{r.now:+.1f} runs an innings above average "
                                                                        f"(was {r.before:+.1f})"])
            if len(bw):
                r = bw.iloc[0]
                rows.append(["Breakout bowler", player_link(r.player), f"{r.now:+.1f} runs saved an innings "
                                                                         f"(was {r.before:+.1f})"])
            html_table(rows, ["", "Player", ""], raw={1})
    with right:
        team_sheet(rv["xi"], f"Team of the Season · {section} {season}")
    left, right = st.columns(2, gap="medium")
    with left:
        with st.container(border=True):
            st.markdown("**⭐ Best matches** · rated 0-10 for excitement")
            bm = rv["best_match"]
            if len(bm):
                html_table([[f"{r.rating:.1f}", match_link(r.match_id, f"{r.home} v {r.away}"), f"{r.date:%d %b}", r.why]
                            for r in bm.itertuples()], ["Rating", "Match", "Date", "Why"], numeric={0}, raw={1})
            else:
                st.caption("No matches rated yet.")
            up = rv["upset"]
            if len(up):
                u = up.iloc[0]
                st.markdown(f"**😱 Biggest upset:** {match_link(u.match_id, f'{u.winner} beat {u.loser}')}, "
                            f"{u.date:%d %b} ({u.chance:.0f}% chance going in by Elo, {u.winner_elo:.0f} v "
                            f"{u.loser_elo:.0f})", unsafe_allow_html=True)
    with right:
        with st.container(border=True):
            st.markdown("**📜 Records broken this season**")
            rec = rv["records"]
            if len(rec):
                html_table([[r.record, r.holder, r.value, f"{r.date:%d %b}", f"{r.old_value} ({r.old_holder})"]
                            for r in rec.itertuples()], ["Record", "Holder", "New record", "Date", "Old record"])
                st.caption("Records that stood at the start of the season and were beaten during it (the latest "
                           "new mark if it fell more than once).")
            else:
                st.caption("The first season here sets every record, so nothing could be broken yet." if rv["first_season"]
                           else "No records broken: every record from earlier seasons survived.")
    for team_, rc in rv["report_cards"].items():
        with st.container(border=True):
            st.markdown(f"**📋 {team_} report card**")
            if rc:
                html_table([[s_, f"<span class='grade {g}'>{g}</span>", esc(why)] for s_, g, why in rc],
                           ["", "Grade", "Why"], raw={1, 2})
            st.caption("Grades against the average team this season: A well above, C about average, E well below.")
    st.caption("Team of the Season, best matches and upsets use the same rules as the Teams, Matches and Player stories "
               "pages.")
