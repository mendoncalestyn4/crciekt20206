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
    if c is not None:
        c = _with_schedule_venues(c)
    return c


def _with_schedule_venues(c: Career) -> Career:
    """The career with home / away taken from your schedule for the matches in it
    (cached until the career or the schedule changes)."""
    fx = fixtures(c)
    if not fx:
        return c
    import json
    from ccstats import fixtures as FX
    key = (c.name, id(c), json.dumps(fx, sort_keys=True, default=str))
    cached = st.session_state.get("venue_cache")
    if cached and cached[0] == key:
        return cached[1]
    try:
        adj = FX.with_venues(c, FX.track(c, fx))
    except Exception:  # noqa: BLE001 - a schedule that can't be read must never stop the site
        adj = c
    st.session_state["venue_cache"] = (key, adj)
    return adj


def settings_of(name: str) -> CareerSettings | None:
    try:
        return store().load_settings(name)[1]
    except OSError:
        return None


def show(c: Career) -> None:
    """Put a career on screen (and remember it for next time)."""
    c = getattr(c, "_venue_base", c)  # never save the schedule's home / away into the career itself
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


# --------------------------------------------------------------------------- match journal
def notes(c: Career | None) -> dict[str, str]:
    """Your notes on matches, by scorecard file name (saved with the career on this PC)."""
    if c is None:
        return {}
    s = settings_of(c.name) if c.name in career_names() else None
    return dict(s.notes) if s is not None else dict(st.session_state.get(f"notes::{c.name}", {}))


def set_note(c: Career, source: str, text: str) -> None:
    text = text.strip()
    if c.name in career_names():
        s = settings_of(c.name)
        if s is not None:
            if text:
                s.notes[source] = text
            else:
                s.notes.pop(source, None)
            store().save_settings(s)
            return
    d = st.session_state.setdefault(f"notes::{c.name}", {})
    if text:
        d[source] = text
    else:
        d.pop(source, None)


# --------------------------------------------------------------------------- remembered filters
def _remembered(c: Career | None) -> dict:
    if c is None:
        return {}
    if "remembered_cache" in st.session_state and st.session_state["remembered_cache"][0] == c.name:
        return st.session_state["remembered_cache"][1]
    s = settings_of(c.name) if c.name in career_names() else None
    r = dict(s.remembered) if s is not None else {}
    st.session_state["remembered_cache"] = (c.name, r)
    return r


def recall(key: str, kind: str, options: list) -> None:
    """Before a section / season / team box: open it on what you last picked
    anywhere on the site (if it's one of the choices here).  The box's own choice
    wins while you stay on the page."""
    if key in st.session_state:
        return
    v = _remembered(current()).get(kind)
    if v is not None and v in list(options):
        st.session_state[key] = v


def remember(key: str, kind: str):
    """on_change for a section / season / team box: keep the choice for every page."""
    def _save() -> None:
        c = current()
        v = st.session_state.get(key)
        if c is None or v is None:
            return
        r = _remembered(c)
        r[kind] = v
        st.session_state["remembered_cache"] = (c.name, r)
        if c.name in career_names():
            s = settings_of(c.name)
            if s is not None:
                s.remembered = dict(r)
                store().save_settings(s)
    return _save


# --------------------------------------------------------------------------- schedule and goals
def _settings_list(c: Career | None, field_: str) -> list:
    if c is None:
        return []
    s = settings_of(c.name) if c.name in career_names() else None
    return list(getattr(s, field_)) if s is not None else list(st.session_state.get(f"{field_}::{c.name}", []))


def _save_list(c: Career, field_: str, value: list) -> None:
    if c.name in career_names():
        s = settings_of(c.name)
        if s is not None:
            setattr(s, field_, list(value))
            store().save_settings(s)
            return
    st.session_state[f"{field_}::{c.name}"] = list(value)


def fixtures(c: Career | None) -> list:
    """Your schedule (saved with the career on this PC)."""
    return _settings_list(c, "fixtures")


def set_fixtures(c: Career, rows: list) -> None:
    _save_list(c, "fixtures", rows)


def goals(c: Career | None) -> list:
    return _settings_list(c, "goals")


def set_goals(c: Career, rows: list) -> None:
    _save_list(c, "goals", rows)
