"""Cricket Captain 2026 Stats Pack.

Run with:  streamlit run app.py   (or double-click "Start Stats Pack.bat")
"""

import os
import time
from pathlib import Path

import streamlit as st

from ccstats.loader import Career
from ccstats.records import new_records
from ui import state
from ui.search import search_box
from ui.theme import inject_css

st.set_page_config(page_title="Cricket Captain Stats Pack", page_icon="🏏", layout="wide")
inject_css()

# Developer start-up options: a folder of scorecards (STATS_PACK_FOLDER) or the demo league (?demo=1).
if state.current() is None and "boot_done" not in st.session_state:
    st.session_state["boot_done"] = True
    folder = os.environ.get("STATS_PACK_FOLDER")
    if folder and Path(folder).is_dir():
        files = [(p.name, p.read_bytes()) for p in sorted(Path(folder).glob("*.txt"))]
        state.show(Career.build(os.environ.get("STATS_PACK_CAREER", "My career"), files))
    elif st.query_params.get("demo"):
        state.show(state.demo_career())


@st.fragment(run_every="20s")
def watch_status() -> None:
    """Check every watched Scorecards folder and add new matches to its career."""
    w = state.watcher()
    folders = {s.folder for n in state.career_names() if (s := state.settings_of(n)) and s.folder}
    shown = state.current()
    refresh = False
    for folder in sorted(folders):
        res = w.sync(folder)
        if res and res.added:
            n = len(res.added)
            st.toast(f"{n} new match{'es' if n > 1 else ''} added to **{res.career.name}**", icon="🏏")
            for msg in new_records(res.career, res.added)[:5]:
                st.toast(msg, icon="🏆")
            if shown is not None and res.career.name == shown.name:
                st.session_state["career_obj"] = res.career
                st.session_state.pop("stats_cache", None)
                refresh = True
        if res and res.failed:
            st.toast(f"{len(res.failed)} file(s) could not be read. See the Home page.", icon="⚠️")
    if folders:
        st.caption(f"Watching {len(folders)} folder{'s' if len(folders) > 1 else ''} · checked {time.strftime('%H:%M:%S')}")
    if refresh:
        st.rerun()


with st.sidebar:
    st.markdown('<div class="brand">🏏 Stats Pack<small>Cricket Captain 2026</small></div>', unsafe_allow_html=True)
    career = state.current()
    names = state.career_names()
    if career is not None:
        options = names + ([state.DEMO_NAME] if career.name == state.DEMO_NAME else [])
        if career.name not in options:
            options.append(career.name)
        # the switches always show what is saved; changing one saves it straight away
        st.session_state["sb_viewing"] = career.name
        st.selectbox("Viewing", options, key="sb_viewing",
                     on_change=lambda: state.open_career(st.session_state["sb_viewing"]))
        settings = state.settings_of(career.name)
        if settings and settings.folder:
            st.caption("New matches from your Scorecards folder are added automatically.")
        st.caption(f"{len(career.matches):,} matches")
        search_box(career)
    watch_status()

pages = [
    st.Page("views/home.py", title="Home", icon=":material/home:", default=True),
    st.Page("views/stat_by_stat.py", title="Stat by stat", icon=":material/leaderboard:"),
    st.Page("views/player.py", title="Players", icon=":material/person:"),
    st.Page("views/compare.py", title="Compare players", icon=":material/compare_arrows:"),
    st.Page("views/teams.py", title="Teams", icon=":material/groups:"),
    st.Page("views/team_vs_team.py", title="Team vs team", icon=":material/swords:"),
    st.Page("views/match.py", title="Matches", icon=":material/scoreboard:"),
    st.Page("views/competitions.py", title="Competitions", icon=":material/emoji_events:"),
    st.Page("views/insights.py", title="Insights", icon=":material/insights:"),
    st.Page("views/rankings.py", title="Rankings", icon=":material/trending_up:"),
    st.Page("views/records.py", title="Records", icon=":material/military_tech:"),
    st.Page("views/data_check.py", title="Data check", icon=":material/fact_check:"),
]
nav = st.navigation(pages)
goto = st.session_state.pop("search_goto", None)  # set by the search box
if goto:
    st.switch_page(goto)
nav.run()
