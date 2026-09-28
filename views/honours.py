import pandas as pd
import streamlit as st

from ccstats import extras as E
from ui import state
from ui.theme import page_header

career = state.current()
if career is None:
    st.info("Load a career on the Home page first.")
    st.stop()

page_header("Honours board", "Champions",
            "Every competition's winners, season by season, with the top run-scorer and wicket-taker, and each "
            "team's trophy cabinet.")
h = E.honours(career)
if h.empty:
    st.info("No competition has been decided yet. Champions appear once a final is played (or, for a league with "
            "no final like the County Championship, once the season is over).")
    st.stop()

t_board, t_cabinet = st.tabs(["Honours board", "Trophy cabinets"])
with t_board:
    for section in h.drop_duplicates("section").section:
        g = h[h.section == section]
        with st.container(border=True):
            st.markdown(f"**{section}**")
            st.dataframe(pd.DataFrame({
                "Season": g.season,
                "Champions": ["🏆 " + c if "so far" not in w else c for c, w in zip(g.champions, g.how)],
                "How": g.how, "Runners-up": g.runners_up, "Most runs": g.top_runs, "Most wickets": g.top_wickets,
                "Player of the final": g.final_potm}), hide_index=True, width="stretch")
    st.caption("Champions come from the final. A league with no final (like the County Championship) is won by the "
               "team top of the table once the season is over; until then it shows who is leading. Bilateral series "
               "are on the Competitions page.")

with t_cabinet:
    won = h[~h.how.str.contains("so far")]
    counts = won.champions.value_counts()
    if counts.empty:
        st.caption("No titles decided yet.")
    else:
        st.dataframe(pd.DataFrame({"Team": counts.index, "Titles": counts.values,
                                   "Won": [", ".join(f"{s} {y}" for s, y in zip(won[won.champions == t].section,
                                                                                 won[won.champions == t].season))
                                           for t in counts.index]}), hide_index=True, width="stretch")
