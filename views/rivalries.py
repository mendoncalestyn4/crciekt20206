import pandas as pd
import streamlit as st

from ccstats import extras as E
from ccstats.stats import Scope
from ui import state
from ui.theme import counted
from ui.charts import CONFIG, bars, fmt
from ui.theme import chart_note, page_header

career = state.current()
if career is None:
    st.info("Load a career on the Home page first.")
    st.stop()
state.stop_if_no_matches(career)

m = career.matches
page_header("Rivalries", "Every head to head",
            "Every pair of teams that have met, the record between them, and who has done best in those games.")
sections = m.section.value_counts()
state.recall("rv_section", "section", list(sections.index))
section = st.selectbox("Section", list(sections.index), key="rv_section", on_change=state.remember("rv_section", "section"), format_func=lambda s: counted(s, sections[s]))
ids = Scope(sections=[section]).match_ids(m)
rv = E.rivalries(career, ids)
if rv.empty:
    st.info("No matches here yet.")
    st.stop()

with st.container(border=True):
    st.markdown("**Most-played rivalries**")
    show = rv.head(30)
    st.dataframe(pd.DataFrame({
        "Rivalry": [f"{a} v {b}" for a, b in zip(show.team_a, show.team_b)], "Played": show.played,
        "Won": [f"{wa} – {wb}" + (f" ({o} other)" if o else "") for wa, wb, o in zip(show.wins_a, show.wins_b, show.other)],
        "Last 5 (oldest first)": [" ".join({"A": "◀", "B": "▶", "–": "·"}[x] for x in last) for last in show.last5],
        "Last met": show["last"].dt.strftime("%d %b %Y")}), hide_index=True, width="stretch")
    st.caption("Won: wins for the first-named team – wins for the second. Last 5: ◀ = the first-named team won, ▶ = the second-named team won, · = draw, tie or no result.")

labels = [f"{a} v {b} ({p})" for a, b, p in zip(rv.team_a, rv.team_b, rv.played)]
pick = st.selectbox("Look closer at one rivalry", range(len(rv)), format_func=lambda i: labels[i], key=f"rv_pick_{section}")
r = rv.iloc[pick]
a, b = r.team_a, r.team_b
runs, wkts = E.rivalry_players(career, ids, a, b)
left, right = st.columns(2, gap="medium")
with left:
    with st.container(border=True):
        st.markdown(f"**Most runs in {a} v {b}**")
        top = runs.head(10)
        if top.empty:
            st.caption("No innings yet.")
        else:
            st.plotly_chart(bars([f"{p} ({t})" for p, t in zip(top.player, top.team)], top.runs, "Runs", notes=[
                f"{i} innings · average {fmt(av, 1)}" for i, av in zip(top.innings, top.average)]),
                width="stretch", config=CONFIG, key="rv_runs")
            tr = int(runs.runs.sum())
            chart_note(f"{top.player.iloc[0]} has {top.runs.iloc[0]} runs in these games, {top.runs.iloc[0] / max(tr, 1) * 100:.0f}% "
                       f"of the {tr} scored by everyone in them.",
                       "The batters who love this fixture.")
with right:
    with st.container(border=True):
        st.markdown(f"**Most wickets in {a} v {b}**")
        top = wkts.head(10)
        if top.empty:
            st.caption("No wickets yet.")
        else:
            st.plotly_chart(bars([f"{p} ({t})" for p, t in zip(top.player, top.team)], top.wickets, "Wickets", notes=[
                f"average {fmt(av, 1)} · {bl} balls" for av, bl in zip(top.average, top.balls)]),
                width="stretch", config=CONFIG, key="rv_wkts")
            tw = int(wkts.wickets.sum())
            chart_note(f"{top.player.iloc[0]} has {int(top.wickets.iloc[0])} wickets in these games, "
                       f"{top.wickets.iloc[0] / max(tw, 1) * 100:.0f}% of the {tw} taken.",
                       "The bowlers who do the damage in this fixture.")
g = m[m.match_id.isin(ids) & (((m.home == a) & (m.away == b)) | ((m.home == b) & (m.away == a)))].sort_values("date", ascending=False)
with st.container(border=True):
    st.markdown("**Every meeting**")
    st.dataframe(pd.DataFrame({"Date": g.date.dt.strftime("%d %b %Y"), "Stage": g.stage, "Home": g.home, "Away": g.away,
                               "Result": g.result}), hide_index=True, width="stretch")
