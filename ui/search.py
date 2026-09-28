"""The search box in the sidebar: players, teams, sections and matches, all in one list."""

from __future__ import annotations

import streamlit as st

from ccstats.loader import Career


def options(career: Career) -> dict[str, tuple[str, str]]:
    """label -> (kind, value), in the order they show in the list."""
    out: dict[str, tuple[str, str]] = {}
    for p in sorted(set(career.batting.player) | set(career.bowling.player)):
        out[f"👤 {p}"] = ("player", p)
    m = career.matches
    for t in sorted(set(m.home) | set(m.away)):
        out[f"👥 {t}"] = ("team", t)
    for s in sorted(m.section.unique()):
        out[f"🏆 {s}"] = ("section", s)
    for r in m.sort_values(["date", "match_id"], ascending=False).itertuples():
        stage = f" · {r.stage}" if r.stage else ""
        out[f"🏏 {r.date:%d %b %Y} · {r.home} v {r.away}{stage}"] = ("match", r.match_id)
    return out


PAGES = {"player": "views/player.py", "team": "views/teams.py", "section": "views/stat_by_stat.py",
         "match": "views/match.py"}


def go_to(career: Career, kind: str, value: str) -> None:
    """Set the chosen page's boxes so it opens on what was picked."""
    ss = st.session_state
    if kind == "player":
        ss["pl_player"] = value
        ss.pop("pl_section", None)
        ss.pop("pl_season", None)
    elif kind == "team":
        m = career.matches
        mine = m[(m.home == value) | (m.away == value)]
        ss["tm_section"] = mine.section.value_counts().index[0]  # their most-played section
        ss["tm_season"] = "All seasons"
        ss["tm_team"] = value
    elif kind == "section":
        ss["sbs_section"] = value
        ss["sbs_season"] = "All seasons"
        ss["sbs_team"] = "All teams"
        ss["sbs_find"] = "—"
        ss.pop("sbs_only", None)
    elif kind == "match":
        ss["mt_section"] = "All sections"
        ss["mt_team"] = "All teams"
        ss["mt_match"] = value
    ss["search_goto"] = PAGES[kind]


def search_box(career: Career) -> None:
    opts = options(career)

    def picked() -> None:
        label = st.session_state.get("search")
        if label in opts:
            go_to(career, *opts[label])
        st.session_state["search"] = None

    st.selectbox("Search", list(opts), index=None, key="search", on_change=picked,
                 placeholder="🔎 Player, team, competition or match", label_visibility="collapsed")
