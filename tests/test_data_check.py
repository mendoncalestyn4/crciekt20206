"""Data check suggestions, manual fixes (and undoing them), and the search box."""

import copy
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from ccstats import checks
from ccstats.loader import Career, Fixes
from ccstats.stats import Scope, player_tables

ROOT = Path(__file__).parent.parent
FIXTURES = sorted((Path(__file__).parent / "fixtures").glob("*.txt"))


@pytest.fixture(scope="module")
def career():
    return Career.build("dc", [(p.name, p.read_bytes()) for p in FIXTURES])


def test_unclear_catches_list_the_right_candidates(career):
    u = checks.uncredited(career)
    assert len(u) == (~career.fielding.resolved).sum() > 0
    for r in u.itertuples():
        assert len(r.candidates) == len(set(r.candidates))  # each player once, even in a two-innings match
        sur = r.printed.lower()
        assert all(sur in c.lower() for c in r.candidates[:2])  # players with that surname come first


def test_crediting_a_catch_moves_it_and_undo_restores_it(career):
    u = checks.uncredited(career).iloc[0]
    who = u.candidates[0]
    section = career.matches.set_index("match_id").loc[u.match_id, "section"]
    before = player_tables(career, Scope(sections=[section]))[2].set_index("player").catches.get(who, 0)
    fixed = career.with_fixes(Fixes(credits={u.credit_key: who}))
    after = player_tables(fixed, Scope(sections=[section]))[2].set_index("player").catches.get(who, 0)
    assert after == before + (1 if u.kind == "caught" else 0)
    assert len(checks.uncredited(fixed)) == len(checks.uncredited(career)) - 1
    undone = fixed.with_fixes(Fixes())
    assert len(checks.uncredited(undone)) == len(checks.uncredited(career))


def test_split_suggestions_and_splitting(career):
    s = checks.split_suggestions(career)
    ipl = s[s.section == "Indian Premier League"]
    assert "A Sharma" in set(ipl.player)
    fixed = career.with_fixes(Fixes(splits=[{"player": "A Sharma", "team": "Gujarat Titans",
                                             "new_name": "A Sharma (Gujarat Titans)"}]))
    b = fixed.batting
    assert set(b[b.player == "A Sharma (Gujarat Titans)"].team) == {"Gujarat Titans"}
    assert "Gujarat Titans" not in set(b[b.player == "A Sharma"].team)
    assert len(b) == len(career.batting)  # nothing lost
    assert "A Sharma" not in set(checks.split_suggestions(fixed).query("section == 'Indian Premier League'").player)


def test_merge_moves_every_row_and_undo_restores_it(career):
    bat, _, _, _ = player_tables(career, Scope(sections=["Tests"]))
    a, b = "J Bethell", "J Root"
    runs = bat.set_index("player").runs
    fixed = career.with_fixes(Fixes(merges={a: b}))
    bat2 = player_tables(fixed, Scope(sections=["Tests"]))[0].set_index("player")
    assert a not in bat2.index and bat2.runs[b] == runs[a] + runs[b]
    assert player_tables(fixed.with_fixes(Fixes()), Scope(sections=["Tests"]))[0].set_index("player").runs[a] == runs[a]


def test_merge_suggestions_never_pair_players_from_the_same_match(career):
    fake = copy.copy(career)
    b = career.batting.copy()
    # make a second spelling of a real player in other matches only
    target = b[b.player == "S Gill"].match_id.unique()
    b.loc[b.match_id.isin(target[:2]) & (b.player == "S Gill"), "player"] = "S  Gill"
    fake.batting = b
    s = checks.merge_suggestions(fake)
    assert {("S Gill", "S  Gill")} <= set(zip(s.keep, s.other))
    for r in s.itertuples():
        ma = set(b[b.player == r.keep].match_id)
        mb = set(b[b.player == r.other].match_id)
        assert not ma & mb


def run_page(career, **state):
    at = AppTest.from_file(str(ROOT / "views" / "data_check.py"), default_timeout=60)
    at.session_state["career_obj"] = career
    for k, v in state.items():
        at.session_state[k] = v
    at.run()
    return at


def test_data_check_page_renders(career):
    at = run_page(career)
    assert not at.exception, at.exception
    assert len(at.tabs) == 5


def test_search_lists_everything(career):
    from ui.search import options
    opts = options(career)
    kinds = {k for k, _ in opts.values()}
    assert kinds == {"player", "team", "section", "match"}
    assert sum(k == "match" for k, _ in opts.values()) == len(career.matches)
    assert ("player", "S Gill") in opts.values()


@pytest.mark.parametrize("page,kind,value,key", [
    ("player.py", "player", "S Gill", "pl_player"), ("teams.py", "team", "Somerset", "tm_team"),
    ("stat_by_stat.py", "section", "The Hundred", "sbs_section"), ("match.py", "match", None, "mt_match")])
def test_search_opens_the_page_on_the_pick(career, page, kind, value, key):
    """What go_to sets must be a valid choice on the page it opens."""
    import streamlit as st
    from ui import search
    value = value or career.matches.match_id.iloc[-1]
    fake = {}
    orig = st.session_state
    try:
        search.st.session_state = fake  # go_to only writes plain keys
        search.go_to(career, kind, value)
    finally:
        search.st.session_state = orig
    at = AppTest.from_file(str(ROOT / "views" / page), default_timeout=60)
    at.session_state["career_obj"] = career
    for k, v in fake.items():
        if k != "search_goto":
            at.session_state[k] = v
    at.run()
    assert not at.exception, at.exception
    assert at.session_state[key] == value
    assert fake["search_goto"] == f"views/{page}"
