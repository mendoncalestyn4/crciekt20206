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


def sync_folders() -> tuple[bool, int]:
    """Check every watched Scorecards folder and add new matches to its career.  (Whether the career on screen
    changed, how many folders are watched.)"""
    st.session_state["synced_at"] = time.monotonic()
    w = state.watcher()
    try:
        state.store().backup_all_due()  # weekly copy of every career, see the Backups panel on Home
    except OSError:
        pass  # a full or read-only disk must never stop the site; the next check tries again
    folders = {s.folder for n in state.career_names() if (s := state.settings_of(n)) and s.folder}
    shown = state.current()
    refresh = False
    for folder in sorted(folders):
        try:
            res = w.sync(folder)
        except Exception:  # noqa: BLE001 - a half-written file or a busy disk: the next check tries again
            continue
        if res and (res.added or res.refreshed):
            n = len(res.added)
            if n:
                st.toast(f"{n} new match{'es' if n > 1 else ''} added to **{res.career.name}**", icon="🏏")
                for msg in new_records(res.career, res.added)[:5]:
                    st.toast(msg, icon="🏆")
            if shown is not None and res.career.name == shown.name:
                st.session_state["career_obj"] = res.career
                st.session_state.pop("stats_cache", None)
                refresh = True
        if res and res.failed:
            st.toast(f"{len(res.failed)} file(s) could not be read. See the Home page.", icon="⚠️")
    return refresh, len(folders)


# New matches are taken in before anything is drawn, so the page you opened (a bookmark, a new tab) shows them
# straight away; restarting the run here would lose which page you asked for.
try:
    sync_folders()
except Exception:  # noqa: BLE001 - a folder or settings file that can't be read must never stop the site
    pass  # (the 20-second check tries again)


@st.fragment(run_every="20s")
def watch_status() -> None:
    """Every 20 seconds while a page is open: new matches in a watched folder are added, and the page redrawn
    with them.  (When the whole page is drawn, the check above has just run.)"""
    if time.monotonic() - st.session_state.get("synced_at", 0.0) < 5:
        n = len({s.folder for name in state.career_names() if (s := state.settings_of(name)) and s.folder})
        refresh = False
    else:
        try:
            refresh, n = sync_folders()
        except Exception:  # noqa: BLE001 - the next check tries again
            refresh, n = False, 0
    if n:
        st.caption(f"Watching {n} folder{'s' if n > 1 else ''} · checked {time.strftime('%H:%M:%S')}")
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
        all_teams = sorted(set(career.matches.home) | set(career.matches.away))
        if all_teams:
            st.session_state["sb_my_teams"] = state.my_teams(career)

            def _save_my_teams():
                c = state.current()
                if c is not None:
                    state.set_my_teams(c, st.session_state.get("sb_my_teams", []))

            st.multiselect("My team", all_teams, key="sb_my_teams", on_change=_save_my_teams,
                           placeholder="The team(s) you play as",
                           help="Home opens on your team, and the planner, previews and lists start from it. "
                                "Saved with this career.")
        search_box(career)
    watch_status()

pages = {
    "": [st.Page("views/home.py", title="Home", icon=":material/home:", default=True)],
    "Players and teams": [
        st.Page("views/stat_by_stat.py", title="Stat by stat", icon=":material/leaderboard:"),
        st.Page("views/player.py", title="Players", icon=":material/person:"),
        st.Page("views/compare.py", title="Compare players", icon=":material/compare_arrows:"),
        st.Page("views/teams.py", title="Teams", icon=":material/groups:"),
        st.Page("views/team_vs_team.py", title="Team vs team", icon=":material/swords:"),
        st.Page("views/opponent.py", title="Opponent preview", icon=":material/visibility:"),
        st.Page("views/planner.py", title="Team planner", icon=":material/strategy:"),
        st.Page("views/stories.py", title="Player stories", icon=":material/auto_stories:"),
    ],
    "Matches and competitions": [
        st.Page("views/match.py", title="Matches", icon=":material/scoreboard:"),
        st.Page("views/fixtures.py", title="Fixtures", icon=":material/event:"),
        st.Page("views/season.py", title="Season", icon=":material/calendar_month:"),
        st.Page("views/competitions.py", title="Competitions", icon=":material/emoji_events:"),
        st.Page("views/review.py", title="Season review", icon=":material/summarize:"),
        st.Page("views/honours.py", title="Honours board", icon=":material/workspace_premium:"),
        st.Page("views/rivalries.py", title="Rivalries", icon=":material/sports_cricket:"),
    ],
    "Records and insights": [
        st.Page("views/records.py", title="Records", icon=":material/military_tech:"),
        st.Page("views/hall_of_fame.py", title="Hall of fame", icon=":material/star:"),
        st.Page("views/rankings.py", title="Rankings", icon=":material/trending_up:"),
        st.Page("views/insights.py", title="Insights", icon=":material/insights:"),
        st.Page("views/analytics.py", title="Analytics", icon=":material/analytics:"),
    ],
    "Tools": [st.Page("views/data_check.py", title="Data check", icon=":material/fact_check:")],
}
nav = st.navigation(pages, expanded=True)  # every page always listed
goto = st.session_state.pop("search_goto", None)  # set by the search box
if goto:
    st.switch_page(goto)
try:
    nav.run()
except Exception as e:  # noqa: BLE001 - shown, never hidden
    st.error("Something went wrong on this page. Every other page still works; pick one from the menu.")
    with st.expander("Details (send this to fix it)"):
        st.exception(e)
