import time
from pathlib import Path

import pandas as pd
import streamlit as st

from ccstats.competitions import shown_name
from ccstats.loader import Career
from ccstats.extras import headlines
from ccstats.local import default_scorecards_folder
from ui import state
from ui.pick_folder import choose_folder
from ui.theme import kpis, page_header, scoreboard


def new_career_form(first: bool) -> None:
    """Set up a career that watches a Scorecards folder on this PC."""
    k = "first" if first else "add"  # separate keys, so the two forms never share old answers
    detected = default_scorecards_folder()
    if f"{k}_folder" not in st.session_state:
        current = state.current()
        s = state.settings_of(current.name) if current is not None else None
        st.session_state[f"{k}_folder"] = s.folder if s and s.folder else (str(detected) if detected else "")
    st.markdown("**1 · Your Scorecards folder**")
    st.caption("In Cricket Captain 2026, turn on **Autosave scorecards** in Options. The folder is normally "
               "`AppData\\Roaming\\Childish Things\\Cricket Captain 2026\\Scorecards`"
               + (" and it was found on this PC." if detected else "."))
    c1, c2 = st.columns([5, 1], vertical_alignment="bottom")
    c1.text_input("Folder", key=f"{k}_folder", label_visibility="collapsed", placeholder="Paste the folder path here")

    def browse():
        picked = choose_folder(st.session_state[f"{k}_folder"])
        if picked:
            st.session_state[f"{k}_folder"] = picked

    c2.button("Browse…", width="stretch", on_click=browse, key=f"{k}_browse")
    folder = Path(st.session_state[f"{k}_folder"]) if st.session_state[f"{k}_folder"] else None
    owner = state.watcher().owner(str(folder)) if folder else None
    st.markdown("**2 · Name this career**")
    name = st.text_input("Career name", value="My career" if first else "", placeholder="e.g. India save",
                         label_visibility="collapsed", key=f"{k}_name")
    if owner:
        st.error(f"This folder is already watched by **{owner}**. One Scorecards folder is one career, so both saves' "
                 "matches go there. Pick a different folder for a separate career.")
    ok = folder is not None and folder.is_dir() and not owner and name.strip() and name.strip() not in state.career_names()
    if folder is not None and st.session_state[f"{k}_folder"] and not folder.is_dir():
        st.error("That folder doesn't exist on this PC. Check the path or use Browse….")
    if name.strip() in state.career_names():
        st.error("A career with that name already exists.")
    if st.button("Start watching", type="primary", disabled=not ok, key=f"{k}_start"):
        with st.spinner("Reading scorecards…"):
            res = state.watcher().create(name.strip(), folder)
        state.show(res.career)
        st.session_state["last_report"] = res.career.report
        st.rerun()


def upload_panel(existing: Career | None) -> None:
    """For a copy of the site that isn't on your PC: upload instead of watching."""
    tab_folder, tab_files, tab_pack = st.tabs(["Upload a folder", "Upload files or a zip", "Open a career file"])
    with tab_folder:
        folder = st.file_uploader("Scorecards folder", accept_multiple_files="directory", type=["txt"], key="up_folder",
                                  label_visibility="collapsed")
    with tab_files:
        files = st.file_uploader("Scorecard .txt files or a .zip", accept_multiple_files=True, type=["txt", "zip"],
                                 key="up_files", label_visibility="collapsed")
    with tab_pack:
        pack = st.file_uploader("Career file (.zip saved from this site)", type=["zip"], key="up_pack",
                                label_visibility="collapsed")
    batch = [(f.name, f.getvalue()) for f in (folder or []) + (files or [])]
    if st.button("Load", disabled=not (batch or pack), key="up_go"):
        with st.spinner("Reading scorecards…"):
            if pack is not None and Career.is_pack(pack.getvalue()):
                career = Career.from_pack(pack.getvalue())
            elif existing is not None and existing.name != state.DEMO_NAME:
                career = existing.add_files(batch)
            else:
                career = Career.build("Uploaded career", batch)
        state.show(career)
        st.session_state["last_report"] = career.report
        st.rerun()


def backups_panel(name: str) -> None:
    """Weekly backups of this career, with restore (two clicks, and undoable)."""
    store = state.store()
    items = store.backups(name)
    with st.expander(f"Backups ({len(items)})"):
        st.caption(f"A copy of this career is saved automatically once a week; the newest {store.BACKUPS_KEPT} are kept, in "
                   f"`{store.root / 'backups'}`. Restoring puts that copy back; your current state is backed up first, "
                   "so you can always undo it.")
        if st.button("Back up now", key="bk_now"):
            store.backup(name)
            st.session_state["bk_msg"] = "Backed up."
            st.rerun()
        msg = st.session_state.pop("bk_msg", None)
        if msg:
            st.success(msg)
        for i, (path, made) in enumerate(items):
            c1, c2 = st.columns([4, 1], vertical_alignment="center")
            note = " · made just before a restore" if "before-restore" in path.name else ""
            c1.markdown(f"**{time.strftime('%a %d %b %Y, %H:%M', time.localtime(made))}**{note}")
            if st.session_state.get("bk_confirm") == str(path):
                if c2.button("Yes, restore", key=f"bk_yes_{i}", type="primary"):
                    restored = store.restore(name, path)
                    s = state.settings_of(name)
                    if s and s.folder:
                        state.watcher().rescan(s.folder)  # matches still in the folder come back on the next check
                    state.show(restored)
                    st.session_state.pop("bk_confirm", None)
                    st.session_state["bk_msg"] = (f"Restored the backup from {time.strftime('%d %b %Y, %H:%M', time.localtime(made))}. "
                                                  "Any newer matches still in your Scorecards folder are added back within 20 seconds.")
                    st.rerun()
            elif c2.button("Restore", key=f"bk_{i}"):
                st.session_state["bk_confirm"] = str(path)
                st.rerun()


career = state.current()

if career is None:
    page_header("Cricket Captain 2026", "Your stats pack",
                "Point the site at your Scorecards folder and every page fills in: leaderboards for every stat, player "
                "and team pages, team-vs-team comparisons and records. New matches appear by themselves while you play.")
    with st.container(border=True):
        new_career_form(first=True)
    with st.expander("Other ways to load: upload files, open a career file, or try the demo league"):
        upload_panel(None)
        if st.button("Try the demo league"):
            state.show(state.demo_career())
            st.rerun()
    st.stop()

page_header("Career", career.name,
            "International matches are grouped by format (all Tests, all ODIs, all T20Is, World Cups included); "
            "everything else, like IPL, T20 Blast and each County Championship division, is its own section.")

report = st.session_state.pop("last_report", None)
if report:
    counts = pd.Series([r.status for r in report]).value_counts().to_dict()
    words = {"loaded": "loaded", "duplicate": "duplicates skipped", "failed": "could not be read", "skipped": "not scorecards"}
    st.success("Finished: " + ", ".join(f"{v} {words.get(k, k)}" for k, v in counts.items()) + ".")
    bad = [r for r in report if r.status == "failed"]
    if bad:
        with st.expander(f"{len(bad)} file(s) could not be read"):
            st.dataframe(pd.DataFrame([(r.source, r.message) for r in bad], columns=["File", "Reason"]), hide_index=True)

m = career.matches
if m.empty:
    st.info("No matches yet. Play a match in Cricket Captain (with Autosave scorecards on) and it will appear here "
            "within about 20 seconds.")
else:
    last = m.sort_values(["date", "match_id"]).iloc[-1]
    inn = career.innings[career.innings.match_id == last.match_id]

    def score(team):
        parts = []
        for _, r in inn[inn.team == team].sort_values("innings_no").iterrows():
            parts.append(f"{r.runs}" if r.all_out else f"{r.runs}/{r.wickets}{'d' if r.declared else ''}")
        return " & ".join(parts) or "–"

    stage = f" · {last.stage}" if last.stage else ""
    scoreboard(f"Latest result · {shown_name(last.section, last.event)}{stage} · {last.date:%d %b %Y}",
               last.home, score(last.home), last.away, score(last.away),
               f"{last.result} · Player of the match: {last.player_of_match}" if last.player_of_match else last.result)
    st.write("")
    kpis([("Matches", f"{len(m):,}"), ("Sections", f"{m.section.nunique()}"), ("Seasons", f"{m.season.nunique()}"),
          ("Players", f"{career.batting.player.nunique():,}"),
          ("Runs", f"{int(career.innings.runs.sum()):,}"), ("Wickets", f"{int(career.innings.wickets.sum()):,}")])
    if not career.problems.empty:
        st.warning(f"{career.problems.match_id.nunique()} scorecard(s) failed the self-check (numbers that don't add up). "
                   "They'll be listed on the Data check page.")
    st.write("")
    news = headlines(career)
    with st.container(border=True):
        st.markdown("**📰 Headlines** · hundreds, five-fors, collapses, titles and new records from your 10 most recent matches")
        if news:
            st.markdown("\n".join(f"- {h}" for h in news))
        else:
            st.caption("Nothing big in your last 10 matches. Hundreds, five-wicket hauls, collapses, titles and new "
                       "records show up here, and records also pop up as a message while you play.")
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
    st.dataframe(latest, hide_index=True, width="stretch", height=35 * (len(latest) + 1) + 3, column_config={
        "date": st.column_config.DateColumn("Date", format="D MMM YYYY"), "section": "Section", "stage": "Stage",
        "home": "Home", "away": "Away", "result": "Result", "player_of_match": "Player of the match"})

with st.expander("Add another career (a different Scorecards folder)"):
    new_career_form(first=False)
with st.expander("Upload files instead, or open a career file"):
    upload_panel(career)
if career.name != state.DEMO_NAME and career.name in state.career_names():
    backups_panel(career.name)
st.download_button("Download career file", career.to_pack(), file_name=f"{career.name}.stats-pack.zip",
                   help="One small file with every match and your manual fixes, e.g. to back it up or open it on another PC.")
