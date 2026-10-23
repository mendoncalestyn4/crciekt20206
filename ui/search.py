"""The search box in the sidebar: players, teams, sections and matches, all in one list."""

from __future__ import annotations

import streamlit as st

from ccstats import search as SR
from ccstats.loader import Career


ICONS = {"player": "👤", "team": "👥", "section": "🏆", "match": "🏏"}


def options(career: Career) -> dict[str, tuple[str, str]]:
    """label -> (kind, value), in the order they show in the list (see ccstats.search)."""
    return {f"{ICONS[i['kind']]} {i['label']}": (i["kind"], i["value"]) for i in SR.items(career)}


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
        ss["sbs_find"] = "—"
        for k in ("sbs_only", "sbs_seasons", "sbs_teams", "sbs_events", "sbs_venues", "sbs_how", "sbs_combine",
                  "sbs_more_sections"):
            ss.pop(k, None)
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
