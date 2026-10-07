import pandas as pd
import streamlit as st

from ccstats import extras as E
from ccstats.stats import Scope
from ui import state
from ui.charts import _n, pct, CONFIG, bars, fmt
from ui.theme import chart_note, page_header

career = state.current()
if career is None:
    st.info("Load a career on the Home page first.")
    st.stop()

m = career.matches
page_header("Hall of fame", "The big performers",
            "Player of the Match awards, the catcher-and-bowler pairs that take wickets together, and the best "
            "all-round performances in a single match.")
c1, c2 = st.columns([2, 1])
sections = m.section.value_counts()
state.recall("hf_section", "section", list(sections.index))
section = c1.selectbox("Section", list(sections.index), key="hf_section", on_change=state.remember("hf_section", "section"), format_func=lambda s: f"{s} · {sections[s]} matches")
seasons = sorted(m[m.section == section].season.unique(), reverse=True)
state.recall("hf_season", "season", ["All seasons"] + seasons)
season = c2.selectbox("Season", ["All seasons"] + seasons, key="hf_season", on_change=state.remember("hf_season", "season"))
ids = Scope(sections=[section], seasons=[] if season == "All seasons" else [season]).match_ids(m)
t_potm, t_duo, t_ar = st.tabs(["Player of the Match", "Deadly duos", "All-round matches"])

with t_potm:
    p = E.player_of_match(career, ids)
    if p.empty:
        st.info("No Player of the Match awards in these matches.")
    else:
        left, right = st.columns([1.1, 1], gap="medium")
        with left:
            with st.container(border=True):
                top = p.head(12)
                st.markdown("**Most Player of the Match awards**")
                st.plotly_chart(bars(top.player, top.awards, "Awards", notes=[
                    f"{t} · {a} in {n} matches ({pct(r)} of their games) · {k} in knockouts, {f} in finals"
                    for t, a, n, r, k, f in zip(top.team, top.awards, top.matches, top.rate, top.knockouts, top.finals)]),
                    width="stretch", config=CONFIG, key="hf_potm")
                t0 = top.iloc[0]
                chart_note(f"{t0.player} has {_n(t0.awards, 'award')} in {_n(t0.matches, 'match', 'matches')}: {pct(t0.rate)} of their "
                           f"games, {t0.knockouts} of them in knockouts.",
                           "Who wins matches on their own most often. Rate = awards as a share of the matches they "
                           "played here.")
        with right:
            with st.container(border=True):
                st.markdown("**Big-game players** · awards in knockouts and finals")
                big = p[p.knockouts > 0].sort_values(["finals", "knockouts"], ascending=False)
                if big.empty:
                    st.caption("No knockout matches here yet.")
                else:
                    st.dataframe(pd.DataFrame({"Player": big.player, "Team": big.team, "Knockouts": big.knockouts,
                                               "Finals": big.finals}), hide_index=True, width="stretch")
        st.caption("Rate = awards as a share of the matches they played here. The game names one Player of the Match "
                   "per scorecard.")

with t_duo:
    duo, cab = E.deadly_duos(career, ids)
    left, right = st.columns([1.2, 1], gap="medium")
    with left:
        with st.container(border=True):
            st.markdown("**Fielder and bowler together** · e.g. 'c Dhoni b Overton'")
            if duo.empty:
                st.caption("No catches or stumpings yet.")
            else:
                top = duo.head(12)
                st.plotly_chart(bars([f"{f} & {b}" for f, b in zip(top.player, top.bowler)], top.wickets, "Wickets together",
                                     notes=[f"{t} · {'caught' if k == 'caught' else 'stumped'} {f}, bowled {b}"
                                            for t, k, f, b in zip(top.team, top.kind, top.player, top.bowler)]),
                                width="stretch", config=CONFIG, key="hf_duo")
                d0 = top.iloc[0]
                tot = int(duo.wickets.sum())
                chart_note(f"{d0.player} and {d0.bowler} have combined for {_n(d0.wickets, 'wicket')}, {d0.wickets / max(tot, 1) * 100:.0f}% "
                           f"of the {tot} catches and stumpings here.",
                           "The fielder-and-bowler pairs that work: keep the fielder where the catches go when that "
                           "bowler is on.")
    with right:
        with st.container(border=True):
            st.markdown("**Caught and bowled** · bowlers who took the catch themselves")
            if cab.empty:
                st.caption("None yet.")
            else:
                st.dataframe(pd.DataFrame({"Bowler": cab.bowler, "Team": cab.team, "Wickets": cab.wickets}).head(12),
                             hide_index=True, width="stretch")
    st.caption("Only catches the scorecard makes clear are counted; unclear ones can be credited on the Data check page.")

with t_ar:
    ar = E.all_round_matches(career, ids)
    if ar.empty:
        st.info("Nobody has both scored runs and taken wickets in the same match here yet.")
    else:
        wv = ar.attrs.get("wicket_value", 0)
        with st.container(border=True):
            st.markdown("**Best all-round matches** · runs and wickets in the same match")
            top = ar.head(12)
            st.plotly_chart(bars([f"{p} v {a} ({d:%d %b %Y})" for p, a, d in zip(top.player, top.against, top.date)],
                                 top.score, "Match score (runs + wickets × runs per wicket)", 0,
                                 texts=list(top.figures), x_range=[0, top.score.max() * 1.4],
                                 notes=[f"{t} · {'won' if w else 'did not win'} · match score {fmt(s, 0)}"
                                        for t, w, s in zip(top.team, top.won, top.score)]),
                            width="stretch", config=CONFIG, key="hf_ar")
            a0 = top.iloc[0]
            chart_note(f"The best: {a0.player} v {a0.against}, {a0.figures}, a match score of {fmt(a0.score, 0)}"
                       f" ({'won' if a0.won else 'did not win'}).",
                       f"Ranks the best all-round games. Each wicket counts as {fmt(wv, 1)} runs, the average runs per "
                       f"wicket in {section}, so runs and wickets can be added up. Only players who both scored and took "
                       "a wicket in the match are listed.")
