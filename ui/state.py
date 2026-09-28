"""Which careers are loaded, and cached stats for them."""

from __future__ import annotations

import streamlit as st

from ccstats.demo_league import generate
from ccstats.loader import Career
from ccstats.stats import Scope, player_tables

DEMO_NAME = "Demo IPL (made-up results)"


@st.cache_resource(show_spinner="Playing two demo IPL seasons ball by ball…")
def demo_career() -> Career:
    files = [(name, text.encode()) for name, text in generate()]
    return Career.build(DEMO_NAME, files)


def careers() -> dict[str, Career]:
    return st.session_state.setdefault("careers", {})


def current() -> Career | None:
    name = st.session_state.get("career")
    return careers().get(name)


def set_current(c: Career) -> None:
    careers()[c.name] = c
    st.session_state["career"] = c.name
    st.session_state.pop("stats_cache", None)


def tables(c: Career, scope: Scope, by_team: bool = False):
    """player_tables, cached per career + selection for this browser session."""
    cache = st.session_state.setdefault("stats_cache", {})
    key = (c.name, id(c), repr(scope), by_team)
    if key not in cache:
        if len(cache) > 64:
            cache.clear()
        cache[key] = player_tables(c, scope, by_team)
    return cache[key]
