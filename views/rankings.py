import plotly.graph_objects as go
import streamlit as st

from ccstats import rankings as R
from ccstats import seasonal as SN
from ccstats import teamdeep as TD
from ui import state
from ui.charts import CONFIG, _axis, _layout, bars, fmt
from ui.theme import html_table, safe_section, chart_note, colours, page_header

career = state.current()
if career is None:
    st.info("Load a career on the Home page first.")
    st.stop()

m = career.matches
page_header("Rankings", "Who's on top right now",
            "Player ratings and team Elo for one section. Recent form counts most, so these move as you play.")
sections = m.section.value_counts()
state.recall("rk_section", "section", list(sections.index))
section = st.selectbox("Section", list(sections.index), key="rk_section", on_change=state.remember("rk_section", "section"), format_func=lambda s: f"{s} · {sections[s]} matches")
c = colours()
intl_secs = SN.international_sections(career)
tab_names = ["Player ratings", "Rankings history", "Team Elo"] + (["International rating"] if intl_secs else [])
tabs_ = st.tabs(tab_names)
tab_p, tab_h, tab_t = tabs_[:3]

with tab_p:
    table = R.player_ratings(career, section)
    if table.empty:
        st.info(f"Nobody has {R.MIN_INNINGS} innings in {section} yet, so there are no ratings.")
    else:
        kind = st.segmented_control("Rating", ["Batting", "Bowling", "All-round"], default="Batting", key="rk_kind") or "Batting"
        col = {"Batting": "batting", "Bowling": "bowling", "All-round": "all_round"}[kind]
        t = table[table[col].notna()].sort_values(col, ascending=False).head(20)
        left, right = st.columns([1.1, 1], gap="medium")
        with left:
            with st.container(border=True):
                st.markdown(f"**Top {len(t)} · {kind.lower()} rating**")
                st.plotly_chart(bars(t.player, t[col], f"{kind} rating", 0,
                                     notes=[f"{tm} · batting {fmt(b, 0)}, bowling {fmt(w, 0)} · {bi} innings batted, {wi} bowled"
                                            for tm, b, w, bi, wi in zip(t.team, t.batting, t.bowling, t.batting_innings, t.bowling_innings)],
                                     reference=500, reference_label="the average specialist"),
                                width="stretch", config=CONFIG, key="rk_bars")
                if len(t):
                    r0 = t.iloc[0]
                    chart_note(f"{r0.player} is top on {fmt(r0[col], 0)}, {(r0[col] - 500) / 5:+.0f}% on the average "
                               f"specialist's 500. {int((t[col] >= 500).sum())} of these {len(t)} are above 500.",
                               "Who is playing best right now: recent innings count most, so it moves with form.")
        with right:
            with st.container(border=True):
                st.markdown("**How the ratings work**")
                st.markdown(
                    "- **Batting**: runs in each innings, and in limited-overs cricket adjusted for "
                    "scoring speed (faster than the section's strike rate counts for more).\n"
                    "- **Bowling**: each wicket is worth the section's runs per wicket, plus the runs kept below the "
                    "section's economy rate.\n"
                    f"- **Recent form counts most**: each innings counts {R.DECAY:g}× the one after it.\n"
                    "- **500** is the average of the better half of the section's regulars; **1000** is twice that.\n"
                    "- **All-round** = batting × bowling ÷ 1000, so it needs both.\n"
                    f"- You need **{R.MIN_INNINGS} innings** (batting or bowling) in this section to get a rating.")
            if kind != "All-round":
                with st.container(border=True):
                    picks = st.multiselect("Rating over time", list(t.player), default=list(t.player[:3]), max_selections=5,
                                           key=f"rk_hist_{col}_{section}")
                    if picks:
                        h = R.rating_history(career, section, picks, col)
                        fig = go.Figure()
                        palette = [c["s1"], c["s2"], "#1baf7a", "#eda100", "#e87ba4"]
                        for i, p in enumerate(picks):
                            d = h[h.player == p]
                            fig.add_trace(go.Scatter(x=d.innings, y=d.rating, mode="lines", name=p,
                                                     line=dict(color=palette[i % 5], width=2.5),
                                                     customdata=d.date.dt.strftime("%d %b %Y"),
                                                     hovertemplate=f"<b>{p}</b><br>after innings %{{x}} (%{{customdata}}): %{{y:.0f}}<extra></extra>"))
                        fig.update_layout(**_layout(c, height=320, showlegend=True, legend=dict(orientation="h", y=1.12, x=0),
                                                    xaxis=_axis(c, "Innings in this section"), yaxis=_axis(c, f"{kind} rating"),
                                                    margin=dict(l=10, r=16, t=40, b=10)))
                        st.plotly_chart(fig, width="stretch", config=CONFIG, key="rk_hist")
                        ends = h.sort_values("innings").groupby("player").rating.agg(["first", "last"])
                        bits = [f"{p} {ends.loc[p, 'first']:.0f} → {ends.loc[p, 'last']:.0f}" for p in picks if p in ends.index]
                        chart_note("From their first innings here to now: " + ", ".join(bits) + ".",
                                   "Shows who is rising and who is falling, innings by innings.")
        with st.expander("Every rated player"):
            st.dataframe(table.sort_values(col, ascending=False), hide_index=True, width="stretch", column_config={
                "player": "Player", "team": "Latest team", "batting": st.column_config.NumberColumn("Batting", format="%d"),
                "bowling": st.column_config.NumberColumn("Bowling", format="%d"),
                "all_round": st.column_config.NumberColumn("All-round", format="%d"),
                "batting_innings": "Innings batted", "bowling_innings": "Innings bowled"})

with tab_t:
    elo, hist = R.team_elo(career, section)
    if elo.empty:
        st.info("No finished matches yet.")
    else:
        left, right = st.columns([1, 1.4], gap="medium")
        with left:
            with st.container(border=True):
                st.markdown("**Current Elo** · above (blue) or below (red) the 1500 every team starts on")
                st.plotly_chart(bars([f"{t} ({e:.0f})" for t, e in zip(elo.team, elo.elo)], elo.elo - 1500,
                                     "Points above or below 1500", 0, signed=True,
                                     notes=[f"{n} matches · best {p:.0f}" for n, p in zip(elo.played, elo.peak)]),
                                width="stretch", config=CONFIG, key="rk_elo")
                e0, e1 = elo.iloc[0], elo.iloc[-1]
                chart_note(f"{e0.team} lead on {e0.elo:.0f} ({e0.elo - 1500:+.0f}); {e1.team} are lowest on {e1.elo:.0f} "
                           f"({e1.elo - 1500:+.0f}).",
                           "The strongest teams right now, allowing for who they beat: beating a top side counts for more.")
        with right:
            with st.container(border=True):
                st.markdown("**Elo over time** · every match moves both teams")
                teams = st.multiselect("Teams", list(elo.team), default=list(elo.team[:4]), key=f"rk_teams_{section}")
                fig = go.Figure()
                palette = [c["s1"], c["s2"], "#1baf7a", "#eda100", "#e87ba4", "#8a6fdf", "#56b4e9", "#999999"]
                for i, team in enumerate(teams):
                    d = hist[hist.team == team]
                    fig.add_trace(go.Scatter(x=d.date, y=d.after, mode="lines+markers", name=team,
                                             line=dict(color=palette[i % len(palette)], width=2, shape="hv"),
                                             marker=dict(size=5),
                                             customdata=[f"v {o}: {r}" for o, r in zip(d.opponent, d.result)],
                                             hovertemplate=f"<b>{team}</b> %{{y:.0f}}<br>%{{customdata}}<extra></extra>"))
                fig.add_hline(y=1500, line=dict(color=c["muted"], dash="dash", width=1))
                fig.update_layout(**_layout(c, height=360, showlegend=True, legend=dict(orientation="h", y=1.12, x=0),
                                            xaxis=_axis(c, "Date"), yaxis=_axis(c, "Elo rating"),
                                            margin=dict(l=10, r=16, t=40, b=10)))
                st.plotly_chart(fig, width="stretch", config=CONFIG, key="rk_elo_hist")
                rise = elo.assign(gain=elo.elo - 1500).sort_values("peak", ascending=False).iloc[0]
                chart_note(f"The highest anyone has been: {rise.team} at {rise.peak:.0f}; now {rise.elo:.0f}.",
                           "Shows each team's strength over the season: rising lines are teams on a run.")
        st.caption(f"Every team starts at 1500. The winner takes points from the loser: up to {R.ELO_K:g} in a league "
                   f"match and {R.ELO_K_KNOCKOUT:g} in a knockout, more for beating a stronger side. A draw or tie moves "
                   "the two sides towards each other. Points are only swapped, so the average stays at 1500.")
    # ---------------------------------------------------------------- 99 · batting and bowling ratings
    with safe_section("batting and bowling ratings"), st.container(border=True):
        ur = TD.unit_ratings(career, career.matches[career.matches.section == section].match_id)
        st.markdown("**Batting and bowling ratings** · each half of every team, 1000 = average")
        mine_ = set(state.my_teams(career))
        html_table([[r.team, f"{r.batting:.0f}", r.batting_rank, f"{r.bowling:.0f}", r.bowling_rank, r.matches]
                    for r in ur.itertuples()], ["Team", "Batting", "#", "Bowling", "#", "Matches"],
                   numeric={1, 2, 3, 4, 5}, row_class=["hi" if r.team in mine_ else "" for r in ur.itertuples()])
        st.caption("Batting: runs per wicket against what each opponent's bowlers usually allow"
                   " (and, in white-ball cricket, the run rate against their usual economy). Bowling: the same the other "
                   "way round. 1100 = 10% better than an average side against the same opponents. Recent games count most.")

# ---------------------------------------------------------------- 107 · rankings history
with tab_h, safe_section("rankings history"):
    what_h = st.segmented_control("Rating", ["Batting", "Bowling"], default="Batting", key="rk_h_kind") or "Batting"
    hist_t, reigns = state.memo(SN.ranking_history, career, section, what_h.lower())
    if hist_t.empty:
        st.info(f"Nobody has {R.MIN_INNINGS} innings in {section} yet, so there's no rankings history.")
    else:
        top_h = hist_t.head(15)
        with st.container(border=True):
            st.markdown(f"**Highest {what_h.lower()} ratings ever** · the peak each player reached, and when")
            st.plotly_chart(bars([f"{p} ({d:%b %Y})" for p, d in zip(top_h.player, top_h.peak_date)], top_h.peak,
                                 f"Peak {what_h.lower()} rating", 0, reference=500, reference_label="the average specialist",
                                 notes=[f"{t} · now {fmt(c_, 0)} · {n} match{'es' if n != 1 else ''} at No. 1"
                                        for t, c_, n in zip(top_h.team, top_h.current, top_h.at_no1)]),
                            width="stretch", config=CONFIG, key="rk_h_bars")
            h0 = top_h.iloc[0]
            most1 = hist_t.sort_values(["at_no1", "peak"], ascending=False).iloc[0]
            chart_note(f"The highest {what_h.lower()} rating in {section} was {h0.player}'s {h0.peak:.0f} on "
                       f"{h0.peak_date:%d %b %Y} (now {fmt(h0.current, 0)}). {most1.player} has spent the most matches at "
                       f"No. 1: {int(most1.at_no1)}.",
                       "Who reached the greatest heights, not just who is on top today. Each rating is the one they had "
                       "at the time, worked out exactly as the Player ratings tab works it out now.")
        with st.container(border=True):
            st.markdown("**No. 1 reigns** · who held the top spot, from when to when")
            rv_ = reigns.iloc[::-1]
            html_table([[p, f"{a:%d %b %Y}", f"{b:%d %b %Y}", n] for p, a, b, n in zip(rv_.player, rv_["from"], rv_.to, rv_.matches)],
                       ["No. 1", "From", "To", "Matches at No. 1"], numeric={3})
            st.caption(f"Ratings start once a player has {R.MIN_INNINGS} innings here. A reign is counted in matches "
                       "played in this section while they were top (level at the top: both count).")

# ---------------------------------------------------------------- 107 · combined international rating
if intl_secs:
    with tabs_[3], safe_section("international rating"):
        what_i = st.segmented_control("Rating", ["Batting", "Bowling"], default="Batting", key="rk_i_kind") or "Batting"
        ci = state.memo(SN.combined_international, career, what_i.lower())
        if ci.empty:
            st.info(f"Nobody has {R.MIN_INNINGS} innings in an international format yet.")
        else:
            top_i = ci.head(20)
            with st.container(border=True):
                st.markdown(f"**Combined international {what_i.lower()} rating** · "
                            + ", ".join(f"{f} ({s_})" for f, s_ in intl_secs.items()))
                st.plotly_chart(bars(top_i.player, top_i.combined, f"Combined {what_i.lower()} rating", 0,
                                     reference=500, reference_label="the average specialist",
                                     notes=[f"{t} · " + " · ".join(f"{f} {fmt(v, 0)}" for f, v in
                                                                   (("Test", a), ("ODI", b), ("T20I", c3)) if v == v)
                                            + f" · {n} innings" for t, a, b, c3, n in
                                            zip(top_i.team, top_i.Test, top_i.ODI, top_i.T20I, top_i.innings)]),
                                width="stretch", config=CONFIG, key="rk_i_bars")
                i0 = top_i.iloc[0]
                parts_i = [f"{f} {fmt(v, 0)}" for f, v in (("Test", i0.Test), ("ODI", i0.ODI), ("T20I", i0.T20I)) if v == v]
                chart_note(f"{i0.player} is top on {i0.combined:.0f} ({', '.join(parts_i)}, over {i0.innings} innings). "
                           f"{int((ci.formats >= 2).sum())} players are rated in two or more formats.",
                           "One world ranking across all three formats, so an all-format star can be compared with a "
                           "specialist.")
            st.dataframe(ci, hide_index=True, width="stretch", column_config={
                "player": "Player", "team": "Team", "Test": st.column_config.NumberColumn("Test", format="%d"),
                "ODI": st.column_config.NumberColumn("ODI", format="%d"), "T20I": st.column_config.NumberColumn("T20I", format="%d"),
                "combined": st.column_config.NumberColumn("Combined", format="%d"), "formats": "Formats rated",
                "innings": "Innings"})
            st.caption("Each format's rating is the one on the Player ratings tab for that section. The combined "
                       "rating weights each format by how many innings the player has had in it, so the format they "
                       "play most counts most. Formats they aren't rated in (fewer than "
                       f"{R.MIN_INNINGS} innings) are left out.")
