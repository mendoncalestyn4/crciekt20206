"""Cricket Captain 2026 Stats Pack.

Run with:  streamlit run app.py
"""

import os
from pathlib import Path

import streamlit as st

from ccstats.loader import Career
from ui import state
from ui.theme import inject_css

st.set_page_config(page_title="Cricket Captain Stats Pack", page_icon="🏏", layout="wide")
inject_css()

# Start-up data: a Scorecards folder on this PC (STATS_PACK_FOLDER), or the demo league (?demo=1).
if state.current() is None:
    folder = os.environ.get("STATS_PACK_FOLDER")
    if folder and Path(folder).is_dir():
        files = [(p.name, p.read_bytes()) for p in sorted(Path(folder).glob("*.txt"))]
        state.set_current(Career.build(os.environ.get("STATS_PACK_CAREER", "My career"), files))
    elif st.query_params.get("demo"):
        state.set_current(state.demo_career())

with st.sidebar:
    st.markdown("### 🏏 Stats Pack")
    career = state.current()
    if career is not None:
        n = len(career.matches)
        demo = " · <span class='chip demo'>demo data</span>" if career.name == state.DEMO_NAME else ""
        st.markdown(f"<div class='side-status'>Career<br><b>{career.name}</b>{demo}<br>{n} matches</div>",
                    unsafe_allow_html=True)
        names = list(state.careers())
        if len(names) > 1:
            pick = st.selectbox("Switch career", names, index=names.index(career.name))
            if pick != career.name:
                state.set_current(state.careers()[pick])
                st.rerun()

pages = [
    st.Page("views/home.py", title="Home", icon=":material/home:", default=True),
    st.Page("views/stat_by_stat.py", title="Stat by stat", icon=":material/leaderboard:"),
]
st.navigation(pages).run()
