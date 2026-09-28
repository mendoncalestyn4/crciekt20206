import plotly.graph_objects as go
import streamlit as st

from ccstats import rankings as R
from ui import state
from ui.charts import CONFIG, _axis, _layout, bars, fmt
from ui.theme import colours, page_header

career = state.current()
if career is None:
    st.info("Load a career on the Home page first.")
    st.stop()

m = career.matches
page_header("Rankings", "Who's on top right now",
            "Player ratings and team Elo for one section. Recent form counts most, so these move as you play.")
sections = m.section.value_counts()
section = st.selectbox("Section", list(sections.index), key="rk_section", format_func=lambda s: f"{s} · {sections[s]} matches")
c = colours()
tab_p, tab_t = st.tabs(["Player ratings", "Team Elo"])

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
                st.markdown("**Current Elo**")
                st.plotly_chart(bars(elo.team, elo.elo, "Elo rating", 0, reference=1500, reference_label="start",
                                     notes=[f"{n} matches · best {p:.0f}" for n, p in zip(elo.played, elo.peak)]),
                                width="stretch", config=CONFIG, key="rk_elo")
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
        st.caption(f"Every team starts at 1500. The winner takes points from the loser: up to {R.ELO_K:g} in a league "
                   f"match and {R.ELO_K_KNOCKOUT:g} in a knockout, more for beating a stronger side. A draw or tie moves "
                   "the two sides towards each other. Points are only swapped, so the average stays at 1500.")
