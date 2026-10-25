"""Every team before its first match: the game's teams and the competitions each plays in (ccstats/catalogue.py), and
every page that lists teams offering them from the start of a new save, then saying plainly they haven't played."""

import re
import zipfile
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from ccstats import catalogue as CAT
from ccstats import fixtures as FX
from ccstats import names as NM
from ccstats import search as SR
from ccstats.loader import Career

ROOT = Path(__file__).parent.parent
NEW = Path(__file__).parent / "fixtures_2026" / "new_playthrough.zip"
IPL = "Indian Premier League"
IPL_SIDES = {"Chennai Super Kings", "Delhi Capitals", "Gujarat Titans", "Kolkata Knight Riders", "Lucknow Super Giants",
             "Mumbai Indians", "Punjab Kings", "Rajasthan Royals", "Royal Challengers Bengaluru", "Sunrisers Hyderabad"}


@pytest.fixture
def fresh_catalogue():
    saved, before = dict(CAT._names), {k: set(v) for k, v in CAT._before.items()}
    yield
    CAT._names.clear()
    CAT._names.update(saved)
    CAT._before.clear()
    CAT._before.update(before)


@pytest.fixture(scope="module")
def new_save():
    """A new save: two IPL games (Lucknow v Delhi, Chennai v Delhi) and one ODI of Bangladesh's tour, so seven IPL
    sides and every other nation haven't played yet."""
    keep = {"1 apr 2026-lkn v del (ipl).txt", "11 apr 2026-chn v del (ipl).txt", "17 apr 2026-ban v nz (1st odi).txt"}
    with zipfile.ZipFile(NEW) as z:
        files = [(n, z.read(n)) for n in z.namelist() if n in keep]
    c = Career.build("new save", files)
    assert len(c.matches) == 3
    return c


# ---------------------------------------------------------------- the catalogue
def test_every_league_and_format_has_its_sides():
    assert CAT.expected(IPL) == IPL_SIDES
    assert len(CAT.expected("The Hundred")) == 8 and "Welsh Fire" in CAT.expected("The Hundred")
    assert len(CAT.expected("Big Bash League")) == 8 and "Perth Scorchers" in CAT.expected("Big Bash League")
    assert len(CAT.expected("T20 Blast")) == len(CAT.expected("One-Day Cup")) == 18
    assert "Birmingham Phoenix" not in CAT.expected("T20 Blast")  # a Hundred side is no county
    assert len(CAT.expected("Ranji Trophy")) == 38 and not CAT.expected("Ranji Trophy") & IPL_SIDES
    assert CAT.expected("Sheffield Shield") == {"New South Wales", "Queensland", "South Australia", "Tasmania",
                                                "Victoria", "Western Australia"}  # no BBL side, no tour XI
    assert len(CAT.expected("Super Smash")) == 6
    assert CAT.expected("Tests") == CAT.TEST_NATIONS and len(CAT.expected("T20Is")) == 31
    assert CAT.nations() == FX.NATIONS
    every = CAT.every_team()
    assert len(every) == len(set(every)) and not [t for t in every if t.startswith("World XI")]
    assert set(every) == {real for c, _, real in NM.TEAMS if not real.startswith("World XI")}


def test_only_certain_sides_are_filled_in_ahead():
    # a County Championship division: which counties are in it shows once they've played
    assert CAT.expected("County Championship · Division 1", "County Championship") == set()
    # competitions only some of the country's sides play, and Afghanistan's (not certain which are which)
    for comp in ("CSA T20 Challenge", "West Indies Championship", "Shpageeza Cricket League", "Asia Cup"):
        assert CAT.expected(comp) == set(), comp
    assert CAT.rivals("Kabul Zwanan") == [] and CAT.rivals("Prime Minister's XI") == []


def test_rivals_and_names_shared_by_two_sides():
    assert set(CAT.rivals("Mumbai Indians")) == IPL_SIDES - {"Mumbai Indians"}
    # "Delhi" is the Ranji side (the IPL side's own name is Delhi too, but its scorecards say Delhi Capitals)
    assert "Mumbai" in CAT.rivals("Delhi") and "Mumbai Indians" not in CAT.rivals("Delhi")
    assert set(CAT.rivals("Delhi Capitals")) == IPL_SIDES - {"Delhi Capitals"}
    assert len(CAT.rivals("India")) == 30 and "Mumbai Indians" not in CAT.rivals("India")
    assert len(CAT.rivals("Kent")) == 17
    assert CAT.home_sections("Kent") == ["County Championship", "T20 Blast", "One-Day Cup"]
    assert CAT.home_sections("India") == ["Tests", "ODIs", "T20Is"]
    assert CAT.home_sections("Bermuda") == ["ODIs", "T20Is"]  # not a Test side


def test_a_side_played_under_the_games_own_name_is_not_listed_twice():
    # scorecards from a game without the real names say "Mumbai" and "Chennai" for the IPL sides
    todo = CAT.unplayed(IPL, {"Mumbai", "Chennai"})
    assert "Mumbai Indians" not in todo and "Chennai Super Kings" not in todo and len(todo) == 8


def test_a_team_renamed_in_the_game_is_listed_by_its_new_name(fresh_catalogue):
    CAT.learn([("India", "Mumbai", "Bombay Blasters"), ("International", "Netherlands", "Holland")])
    assert "Bombay Blasters" in CAT.expected(IPL) and "Mumbai Indians" not in CAT.expected(IPL)
    assert "Holland" in CAT.expected("ODIs") and "Netherlands" not in CAT.expected("ODIs")
    assert "Bombay Blasters" in CAT.every_team()
    assert CAT.unplayed(IPL, {"Mumbai Indians"}) == CAT.unplayed(IPL, {"Bombay Blasters"})  # a card from before


# ---------------------------------------------------------------- search and the My team box
def test_search_lists_every_team_and_says_which_havent_played(new_save):
    teams = {i["value"]: i["sub"] for i in SR.items(new_save) if i["kind"] == "team"}
    assert teams["Delhi Capitals"] == "team" and teams["Gujarat Titans"] == "team · no matches yet"
    assert teams["Australia"] == "team · no matches yet" and teams["Bangladesh"] == "team"
    assert set(teams) == set(CAT.every_team())


def test_the_search_box_says_which_teams_havent_played(new_save):
    from ui import search as US
    opts = US.options(new_save)
    assert opts["👥 Gujarat Titans · no matches yet"] == ("team", "Gujarat Titans")
    assert opts["👥 Delhi Capitals"] == ("team", "Delhi Capitals")


def test_search_opens_a_team_that_hasnt_played_on_its_competition(new_save):
    from ui import search as US
    fake = {}
    import streamlit as st
    real = st.session_state
    try:
        st.session_state = fake  # go_to only writes keys
        US.go_to(new_save, "team", "Gujarat Titans")
        assert fake["tm_section"] == IPL and fake["tm_team"] == "Gujarat Titans"
        assert fake["search_goto"] == "views/teams.py"
        fake.clear()
        US.go_to(new_save, "team", "Kent")  # no County Championship, Blast or One-Day Cup game in this career yet
        assert "search_goto" not in fake and "Kent haven't played in this career yet" in fake["search_note"]
    finally:
        st.session_state = real


def test_the_my_team_box_offers_a_franchise_before_its_first_match(new_save):
    from ui import state
    choices = state.team_choices(new_save)
    assert {"Mumbai Indians", "Kent", "Perth Scorchers", "India"} <= set(choices)


# ---------------------------------------------------------------- the pages
def plain(box) -> set[str]:
    """A team box's teams without what the page adds to a name ("  (no games yet)", "  ·  next match")."""
    return {re.split(r"\s+[(·]", o)[0] for o in box.options}


def page(name, career, mine=("Mumbai Indians",), **boxes):
    at = AppTest.from_file(str(ROOT / "views" / name), default_timeout=120)
    at.session_state["career_obj"] = career
    at.session_state[f"my_teams::{career.name}"] = list(mine)
    for k, v in boxes.items():
        at.session_state[k] = v
    return at


def test_team_vs_team_offers_every_ipl_side_and_says_who_hasnt_played(new_save):
    at = page("team_vs_team.py", new_save, tv_section=IPL).run()
    assert not at.exception, at.exception
    assert set(at.selectbox(key="tv_a").options) >= {f"{t} (0 games)" for t in IPL_SIDES - {
        "Lucknow Super Giants", "Delhi Capitals", "Chennai Super Kings"}} | {"Delhi Capitals"}
    at.session_state["tv_a"] = "Delhi Capitals"
    at.session_state["tv_b"] = "Mumbai Indians"
    at.run()
    assert not at.exception, at.exception
    said = " ".join(i.value for i in at.info)
    assert "Mumbai Indians haven't played in Indian Premier League yet" in said and "Choose another" not in said


def test_teams_page_says_a_side_hasnt_played_here(new_save):
    at = page("teams.py", new_save, tm_section=IPL, tm_team="Kolkata Knight Riders").run()
    assert not at.exception, at.exception
    assert "Kolkata Knight Riders haven't played in Indian Premier League yet" in " ".join(i.value for i in at.info)
    at = page("teams.py", new_save, tm_section=IPL, tm_team="Delhi Capitals").run()  # a side that has played
    assert not at.exception and not [i for i in at.info if "haven't played" in i.value]


def test_teams_page_offers_a_nation_and_sends_you_to_where_it_has_played(new_save):
    at = page("teams.py", new_save, mine=("Bangladesh",), tm_section="ODIs", tm_team="Australia").run()
    assert not at.exception, at.exception
    assert "Australia haven't played in ODIs yet" in " ".join(i.value for i in at.info)


def test_opponent_preview_offers_the_sides_still_to_play(new_save):
    at = page("opponent.py", new_save, op_section=IPL, op_mine="Mumbai Indians").run()
    assert not at.exception, at.exception
    assert IPL_SIDES - {"Mumbai Indians"} <= plain(at.selectbox(key="op_opp"))
    assert "Mumbai Indians" in plain(at.selectbox(key="op_mine"))  # your team, before its first game
    at.session_state["op_opp"] = "Punjab Kings"
    at.run()
    assert not at.exception
    assert "Punjab Kings haven't played a game here in this career yet" in " ".join(i.value for i in at.info)


def test_fixtures_offers_a_franchise_its_whole_league(new_save):
    at = page("fixtures.py", new_save, fx_team="Mumbai Indians").run()
    assert not at.exception, at.exception
    opps = at.selectbox(key="fx_opp::Mumbai Indians").options
    assert IPL_SIDES - {"Mumbai Indians"} <= set(opps)
    assert set(opps[:9]) == IPL_SIDES - {"Mumbai Indians"}  # its own league first, played or not, then the rest
    at = page("fixtures.py", new_save, mine=("Bangladesh",), fx_team="Bangladesh").run()
    assert not at.exception
    assert set(at.selectbox(key="fx_opp::Bangladesh").options) == FX.NATIONS - {"Bangladesh"}  # a nation plays nations


def test_home_page_next_opponent_includes_sides_still_to_play(new_save):
    at = page("home.py", new_save, mine=("Delhi Capitals",)).run()
    assert not at.exception, at.exception
    boxes = [s for s in at.selectbox if s.label == "Next opponent"]
    assert boxes and IPL_SIDES - {"Delhi Capitals"} <= plain(boxes[0])
    assert "Gujarat Titans  ·  no games yet" in boxes[0].options
