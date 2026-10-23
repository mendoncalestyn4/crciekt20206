"""Logos on the pages: the team emblems and competition logos from your Cricket Captain editor files (see
ccstats/logos.py), found next to your Scorecards folder, in the Steam folder, or in a folder you choose."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from ccstats import local as L
from ccstats import logos as LG


# a see-through 1 x 1 picture: the gap in a table's picture column for a team without a logo
BLANK = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNgYGBgAAAABQABpfZFQAAAAABJRU5ErkJggg=="


def chosen_folder() -> str:
    """The folder you picked for logos (saved on this PC), or ''."""
    from ui import state
    try:
        return str(state.store().preferences().get("logos_folder") or "")
    except Exception:  # noqa: BLE001
        return ""


def places() -> list[Path]:
    """Where to look, in order (see ccstats.logos.places): the folder you chose, the game's folder above each
    Scorecards folder you watch, the Steam install folder, a 'logos' folder in the Stats Pack's own folder."""
    from ui import state
    folders = []
    try:
        folders = [s.folder for name in state.career_names() if (s := state.settings_of(name)) and s.folder]
    except Exception:  # noqa: BLE001
        pass
    return LG.places(chosen_folder(), folders, L.home_dir())


def book() -> LG.LogoBook:
    """The pictures for this session's teams and competitions (looked for again when a file or folder changes)."""
    found = LG.find(places())
    stamp = LG.stamp(found)
    cached = st.session_state.get("_logo_book")
    if cached is None or cached[0] != stamp:
        cached = (stamp, LG.LogoBook(found))
        st.session_state["_logo_book"] = cached
    return cached[1]


def look(path) -> str:
    """How this logo is drawn on the page: its look picked for the dark page, or on a light page (your national
    side's colours) as it is, apart from the white the game shows inside some (the looks that make dark parts show
    up on a dark page would only fade them on a light one)."""
    from ui.theme import is_night
    return LG.look_on(book().style(path), is_night())


def _img(path, size: int, title: str) -> str:
    """The logo size pixels across, in its look (every picture of a size has the same frame, so logos side by side
    or down a table line up)."""
    uri, px = LG.picture(path, size, look(path)) if path else ("", 0)
    if not uri:
        return ""
    from ui.theme import esc
    return (f"<img class='logo' src='{uri}' width='{px}' height='{px}' alt='' title='{esc(title)}' "
            f"style='width:{px}px;height:{px}px'>")


def team(name: str, size: int = 24) -> str:
    """An <img> of the team's emblem, or '' when there's no picture for it."""
    try:
        return _img(book().team(name), size, name)
    except Exception:  # noqa: BLE001 - a logo must never stop a page
        return ""


def comp(name: str, size: int = 40) -> str:
    """An <img> of a competition's logo, or ''."""
    try:
        return _img(book().comp(name), size, name)
    except Exception:  # noqa: BLE001
        return ""


def uri(name: str, size: int = 24) -> str | None:
    """The team's emblem as a data URI (for a table's picture column), or None."""
    try:
        p = book().team(name)
        return LG.badge(p, size, look(p)) or None if p else None
    except Exception:  # noqa: BLE001
        return None


def heading(title: str, sub: str = "", teams: tuple = (), comp_name: str = "") -> None:
    """A line with the teams' emblems (or a competition's logo) and a title, when there is a picture to show."""
    from ui.theme import esc
    pics = [team(t, 84) for t in teams] + ([comp(comp_name, 100)] if comp_name else [])
    if not any(pics):
        return
    if len(teams) == 2:
        inner = f"{pics[0]}<b>{esc(teams[0])}</b><span class='vs'>v</span>{pics[1]}<b>{esc(teams[1])}</b>"
    else:
        inner = "".join(pics) + f"<b>{esc(title)}</b>"
    st.markdown(f"<div class='logohead'>{inner}" + (f"<span class='sub'>{esc(sub)}</span>" if sub else "") + "</div>",
                unsafe_allow_html=True)


def my_teams_row(teams: list) -> None:
    """Your team(s) with their emblems, under the Home page's title (nothing when none has a picture)."""
    from ui.theme import esc
    pics = [(t, team(t, 84)) for t in teams]
    if not any(p for _, p in pics):
        return
    st.markdown("<div class='logohead'>" + "".join(f"<span class='mine'>{p}<b>{esc(t)}</b></span>" for t, p in pics)
                + "<span class='sub'>your team" + ("s" if len(teams) > 1 else "") + "</span></div>",
                unsafe_allow_html=True)


def named(name: str, size: int = 22) -> str:
    """The team's emblem then its (escaped) name: '<img …> Sydney Thunder'."""
    from ui.theme import esc
    lg = team(name, size)
    return f"{lg} {esc(name)}" if lg else esc(name)


def settings_box() -> None:
    """In the sidebar: where the logos come from, and choosing another folder."""
    from ui import state
    b = book()
    n_teams, n_comps = b.counts()
    with st.expander("🎨 Logos" + (f" · {n_teams} teams" if n_teams else ""), expanded=False):
        if n_teams or n_comps:
            where = b.found.get("emblems") or b.found.get("complogos")
            st.caption(f"{n_teams} team emblems and {n_comps} competition logos, from your Cricket Captain editor "
                       f"files in {where.parent if where else ''}.")
        else:
            st.caption("No logos found yet. They come from your Cricket Captain editor files: the emblems and "
                       "complogos folders (with editemblems.txt and editcomplogos.txt). Put the folder that has "
                       "them below.")
        cur = chosen_folder()
        txt = st.text_input("Folder with your editor files", value=cur, key="logos_folder_box",
                            placeholder=r"e.g. C:\...\Cricket Captain 2026\editor",
                            help="The folder holding 'emblems' and 'complogos' (or the game's folder above it). "
                                 "Leave empty to look next to your Scorecards folder and in the Steam folder.")
        if txt.strip() != cur and st.button("Use this folder", key="logos_folder_use"):
            state.store().save_preference("logos_folder", txt.strip())
            st.session_state.pop("_logo_book", None)
            st.rerun()
