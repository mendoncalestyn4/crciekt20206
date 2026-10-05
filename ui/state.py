"""Which careers exist on this PC, which one is on screen, and cached stats."""

from __future__ import annotations

import streamlit as st

from ccstats.demo_league import generate
from ccstats.loader import Career
from ccstats.local import CareerSettings, CareerStore, Watcher
from ccstats.stats import Scope, player_tables

DEMO_NAME = "Demo IPL (made-up results)"


@st.cache_resource
def store() -> CareerStore:
    return CareerStore()


def watcher() -> Watcher:
    return Watcher(store())


@st.cache_resource(show_spinner="Playing two demo IPL seasons ball by ball…")
def demo_career() -> Career:
    files = [(name, text.encode()) for name, text in generate()]
    return Career.build(DEMO_NAME, files)


def career_names() -> list[str]:
    return store().names()


def current() -> Career | None:
    c = st.session_state.get("career_obj")
    if c is None and "career_boot" not in st.session_state:
        st.session_state["career_boot"] = True
        last = store().last_used()
        if last:
            c, _ = store().load(last)
            st.session_state["career_obj"] = c
    return c


def settings_of(name: str) -> CareerSettings | None:
    try:
        return store().load_settings(name)[1]
    except OSError:
        return None


def show(c: Career) -> None:
    """Put a career on screen (and remember it for next time)."""
    st.session_state["career_obj"] = c
    st.session_state.pop("stats_cache", None)
    if c.name != DEMO_NAME:
        s = settings_of(c.name) or CareerSettings(name=c.name)
        store().save(c, s)


def open_career(name: str) -> None:
    if name == DEMO_NAME:
        show(demo_career())
    else:
        c, _ = store().load(name)
        show(c)


def tables(c: Career, scope: Scope, by_team: bool = False):
    """player_tables, cached per career + selection for this browser session."""
    cache = st.session_state.setdefault("stats_cache", {})
    key = (c.name, id(c), repr(scope), by_team)
    if key not in cache:
        if len(cache) > 64:
            cache.clear()
        cache[key] = player_tables(c, scope, by_team)
    return cache[key]


# --------------------------------------------------------------------------- my team
def my_teams(c: Career | None) -> list[str]:
    """The teams you play as in this career (saved with the career on this PC)."""
    if c is None:
        return []
    teams = set(c.matches.home) | set(c.matches.away)
    s = settings_of(c.name) if c.name in career_names() else None
    picked = s.my_teams if s is not None else st.session_state.get(f"my_teams::{c.name}", [])
    return [t for t in picked if t in teams]


def set_my_teams(c: Career, teams: list[str]) -> None:
    if c.name in career_names():
        s = settings_of(c.name)
        if s is not None:
            s.my_teams = list(teams)
            store().save_settings(s)
            return
    st.session_state[f"my_teams::{c.name}"] = list(teams)


# --------------------------------------------------------------------------- cache
def _key(v):
    import pandas as pd
    if isinstance(v, (pd.Index, pd.Series, list, tuple, set)):
        return tuple(sorted(map(str, v)))
    return v


def memo(fn, c: Career, *args, **kw):
    """fn(c, *args, **kw), cached per career for this browser session."""
    cache = st.session_state.setdefault("memo_cache", {})
    if cache.get("__career") != (c.name, id(c)):
        cache.clear()
        cache["__career"] = (c.name, id(c))
    key = (fn.__module__, fn.__name__, tuple(_key(a) for a in args), tuple(sorted((k, _key(v)) for k, v in kw.items())))
    if key not in cache:
        if len(cache) > 400:
            cache.clear()
            cache["__career"] = (c.name, id(c))
        cache[key] = fn(c, *args, **kw)
    return cache[key]
