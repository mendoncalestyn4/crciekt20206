"""Season MVP table: IPL MVP points counted by hand, impact points that are the match impact summed, two players
under one name kept apart, and the Season review page in both counts for every season."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from ccstats import mvp as MV
from ccstats.demo_league import generate
from ccstats.loader import Career
from ccstats.playerdeep import match_impact

HERE = Path(__file__).parent
IPL = "Indian Premier League"


@pytest.fixture(scope="module")
def demo():
    return Career.build("demo", [(n, t.encode()) for n, t in generate()])


@pytest.fixture(scope="module")
def fixtures():
    return Career.build("fx", [(p.name, p.read_bytes()) for p in sorted((HERE / "fixtures").glob("*.txt"))])


def test_ipl_points_by_hand(demo):
    d = MV.season_mvp(demo, IPL, "2027", "ipl")
    ids = demo.matches[(demo.matches.section == IPL) & (demo.matches.season == "2027")].match_id
    for r in d.head(25).itertuples():
        b = demo.batting[demo.batting.match_id.isin(ids) & (demo.batting.player == r.player) & (demo.batting.team == r.team)]
        w = demo.bowling[demo.bowling.match_id.isin(ids) & (demo.bowling.player == r.player) & (demo.bowling.team == r.team)]
        f = demo.fielding[demo.fielding.match_id.isin(ids) & (demo.fielding.player == r.player)
                          & (demo.fielding.team == r.team) & demo.fielding.resolved]
        hand = (2.5 * b.fours.sum() + 3.5 * b.sixes.sum() + 3.5 * w.wickets.sum() + w.dots.sum()
                + 2.5 * (f.kind == "caught").sum() + 2.5 * (f.kind == "stumped").sum())
        assert r.points == pytest.approx(hand), r.player
        assert r.matches == b.match_id.nunique()
        assert r.points == pytest.approx(r.batting + r.bowling + r.fielding)
    assert list(d.points) == sorted(d.points, reverse=True)


def test_impact_points_are_the_match_impact(demo):
    d = MV.season_mvp(demo, IPL, "2026", "impact")
    imp = match_impact(demo, demo.matches[demo.matches.section == IPL].match_id)  # the whole section's averages
    imp = imp[imp.match_id.isin(demo.matches[demo.matches.season == "2026"].match_id)]
    total = imp.groupby(["player", "team"]).impact.sum()
    for r in d.head(25).itertuples():
        assert r.points == pytest.approx(total[(r.player, r.team)]), r.player
    assert d.points.sum() == pytest.approx(total.sum())


def test_a_name_in_two_teams_is_two_players(fixtures):
    # "A Sharma" plays for Gujarat Titans and for Sunrisers Hyderabad in the sample IPL games: two players, split by
    # name (14 November), each counted on his own
    d = MV.season_mvp(fixtures, IPL, "2026", "impact")
    assert set(d[d.player == "A Sharma"].team) == {"Gujarat Titans"}
    assert set(d[d.player == "A Sharma (Sunrisers Hyderabad)"].team) == {"Sunrisers Hyderabad"}
    assert d.groupby(["player", "team"]).size().max() == 1


def test_dot_balls_only_where_the_scorecards_print_them(fixtures):
    assert MV.counts_dots(fixtures, IPL)
    assert not MV.counts_dots(fixtures, "Tests")


def test_the_season_review_shows_it(demo):
    for season in ("2026", "2027"):
        for how in ("Impact points", "IPL MVP points"):
            at = AppTest.from_file(str(HERE.parent / "views" / "review.py"), default_timeout=120)
            at.session_state["career_obj"] = demo
            at.session_state["rv2_pick"] = (IPL, season)
            at.session_state[f"rv_mvp_how_{IPL}"] = how
            at.run()
            assert not at.exception, at.exception
            text = " ".join(x.value for x in at.markdown)
            assert "Most valuable players" in text and "What it shows" in text, (season, how)
            top = MV.season_mvp(demo, IPL, season, "ipl" if how == "IPL MVP points" else "impact").iloc[0]
            assert top.player in text
