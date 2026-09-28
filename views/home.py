import pandas as pd
import streamlit as st

from ccstats.loader import Career
from ui import state
from ui.theme import kpis, page_header


def read_uploads(files) -> list[tuple[str, bytes]]:
    return [(getattr(f, "name", "file"), f.getvalue()) for f in files or []]


def load_panel(existing: Career | None) -> None:
    """Upload scorecards, a whole folder, or a saved career file."""
    tab_folder, tab_files, tab_pack = st.tabs(["Choose your Scorecards folder", "Pick files or a zip", "Open a career file"])
    with tab_folder:
        st.caption("In Cricket Captain, turn on **Autosave scorecards** (Options). The folder is usually "
                   "`AppData\\Roaming\\Childish Things\\Cricket Captain 2026\\Scorecards`. Matches already loaded are skipped.")
        folder = st.file_uploader("Scorecards folder", accept_multiple_files="directory", type=["txt"], key="up_folder",
                                  label_visibility="collapsed")
    with tab_files:
        files = st.file_uploader("Scorecard .txt files or a .zip", accept_multiple_files=True, type=["txt", "zip"],
                                 key="up_files", label_visibility="collapsed")
    with tab_pack:
        pack = st.file_uploader("Career file (.zip saved from this site)", type=["zip"], key="up_pack",
                                label_visibility="collapsed")
    batch = read_uploads(folder) + read_uploads(files)
    name = st.text_input("Career name", value=existing.name if existing and existing.name != state.DEMO_NAME else "My career",
                         key="career_name")
    c1, c2 = st.columns([1, 3])
    if c1.button("Load", type="primary", disabled=not (batch or pack)):
        with st.spinner("Reading scorecards…"):
            if pack is not None and Career.is_pack(pack.getvalue()):
                career = Career.from_pack(pack.getvalue())
            elif existing is not None and existing.name == name:
                career = existing.add_files(batch)
            else:
                career = Career.build(name, batch)
        state.set_current(career)
        st.session_state["last_report"] = career.report
        st.rerun()
    if c2.button("Try the demo league instead"):
        state.set_current(state.demo_career())
        st.rerun()


career = state.current()

if career is None:
    page_header("Cricket Captain 2026", "Your stats pack",
                "Load the scorecards from your save and every page fills in: leaderboards for every stat, "
                "player and team pages, team-vs-team comparisons and records. Nothing leaves your computer "
                "unless you put the site online.")
    load_panel(None)
    st.stop()

page_header("Career", career.name,
            "Every competition is kept in its own section, so IPL, Tests, bilateral ODIs, the ODI World Cup and each "
            "County Championship division never mix.")

m = career.matches
kpis([("Matches", f"{len(m):,}"), ("Sections", f"{m.section.nunique()}"), ("Seasons", f"{m.season.nunique()}"),
      ("Players", f"{career.batting.player.nunique():,}"),
      ("Runs", f"{int(career.innings.runs.sum()):,}"), ("Wickets", f"{int(career.innings.wickets.sum()):,}")])

report = st.session_state.pop("last_report", None)
if report:
    counts = pd.Series([r.status for r in report]).value_counts().to_dict()
    msg = ", ".join(f"{v} {k}" for k, v in counts.items())
    st.success(f"Upload finished: {msg}.")

st.subheader("Sections", anchor=False)
sec = (m.groupby("section")
       .agg(matches=("match_id", "size"), seasons=("season", lambda s: ", ".join(sorted(set(s)))),
            first=("date", "min"), last=("date", "max"), format=("format", "first"), level=("level", "first"))
       .sort_values("matches", ascending=False).reset_index())
st.dataframe(sec, hide_index=True, width="stretch", column_config={
    "section": st.column_config.TextColumn("Section"), "matches": st.column_config.NumberColumn("Matches"),
    "seasons": "Seasons", "first": st.column_config.DateColumn("First match", format="D MMM YYYY"),
    "last": st.column_config.DateColumn("Latest match", format="D MMM YYYY"), "format": "Format", "level": "Level"})

st.subheader("Latest results", anchor=False)
latest = m.sort_values("date", ascending=False).head(12)[["date", "section", "stage", "home", "away", "result", "player_of_match"]]
st.dataframe(latest, hide_index=True, width="stretch", column_config={
    "date": st.column_config.DateColumn("Date", format="D MMM YYYY"), "section": "Section", "stage": "Stage",
    "home": "Home", "away": "Away", "result": "Result", "player_of_match": "Player of the match"})

with st.expander("Add more scorecards or open another career"):
    load_panel(career)
st.download_button("Download career file", career.to_pack(), file_name=f"{career.name}.stats-pack.zip",
                   help="One small file with every match and your manual fixes. Open it here next time instead of re-uploading.")
