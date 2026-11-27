"""The competition rules checked by hand (deep check, 27 November): each points rule as the real competition has it,
and the one place a match's points are worked out (tables.side_points), used by the table, the title race and the
points through the season alike."""

from types import SimpleNamespace as Row

import pandas as pd
import pytest

from ccstats import tables as T


def inn(*rows):
    """One match's innings: (innings_no, team, team_innings, runs, all_out, declared)."""
    return pd.DataFrame([dict(innings_no=n, team=t, team_innings=ti, runs=r, all_out=ao, declared=d)
                         for n, t, ti, r, ao, d in rows])


@pytest.mark.parametrize("innings, who", [
    # both first innings complete: the bigger total has the lead
    (inn((1, "A", 1, 500, True, False), (2, "B", 1, 300, True, False)), "A"),
    (inn((1, "A", 1, 500, False, True), (2, "B", 1, 300, False, True)), "A"),          # declared counts as complete
    # the side batting second passes the total: its lead, finished or not
    (inn((1, "A", 1, 300, True, False), (2, "B", 1, 301, False, False)), "B"),
    # the side batting second is behind but not finished (rain): not decided
    (inn((1, "A", 1, 500, True, False), (2, "B", 1, 100, False, False)), ""),
    # only one side batted: not decided
    (inn((1, "A", 1, 500, False, False)), ""),
    # level on first innings: no one
    (inn((1, "A", 1, 300, True, False), (2, "B", 1, 300, True, False)), ""),
    # second innings don't count
    (inn((1, "A", 1, 200, True, False), (2, "B", 1, 250, True, False), (3, "A", 2, 400, False, True),
         (4, "B", 2, 10, False, False)), "B"),
])
def test_first_innings_lead_in_a_drawn_match(innings, who):
    assert T.first_innings_lead(innings) == who


def _r(**kw):
    base = dict(match_id="m", winner="", result_type="", tiebreak_winner="", innings_win=False, margin_wickets=None)
    return Row(**{**base, **kw})


def test_limited_overs_points():
    _, pts = T.points_rule("Indian Premier League", "T20")
    assert T.side_points(_r(winner="A", result_type="win"), "A", pts, True, {}) == 2
    assert T.side_points(_r(winner="A", result_type="win"), "B", pts, True, {}) == 0
    assert T.side_points(_r(result_type="tie"), "A", pts, True, {}) == 1                 # a tie with no super over
    assert T.side_points(_r(result_type="tie", tiebreak_winner="B"), "B", pts, True, {}) == 2   # super over won
    assert T.side_points(_r(result_type="tie", tiebreak_winner="B"), "A", pts, True, {}) == 0
    assert T.side_points(_r(result_type="no result"), "A", pts, True, {}) == 1


def test_ranji_points():
    _, pts = T.points_rule("Ranji Trophy", "First Class")
    win = _r(winner="A", result_type="win")
    assert T.side_points(win, "A", pts, False, {}) == 6
    assert T.side_points(_r(winner="A", result_type="win", innings_win=True), "A", pts, False, {}) == 7
    assert T.side_points(_r(winner="A", result_type="win", margin_wickets=10), "A", pts, False, {}) == 7
    assert T.side_points(win, "B", pts, False, {}) == 0
    draw = _r(result_type="draw")
    assert T.side_points(draw, "A", pts, False, {"m": "A"}) == 3 and T.side_points(draw, "B", pts, False, {"m": "A"}) == 1
    assert T.side_points(draw, "A", pts, False, {"m": ""}) == 1 == T.side_points(draw, "B", pts, False, {})
    assert T.side_points(_r(result_type="tie"), "A", pts, False, {}) == 3
    assert T.side_points(_r(result_type="no result"), "A", pts, False, {}) == 1


def test_county_championship_points():
    _, pts = T.points_rule("County Championship", "First Class")
    assert T.side_points(_r(winner="A", result_type="win"), "A", pts, False, {}) == 16
    assert T.side_points(_r(result_type="draw"), "A", pts, False, {"m": "A"}) == 8     # (no lead points here)
    assert T.side_points(_r(result_type="tie"), "A", pts, False, {}) == 8


def test_what_the_page_says_is_how_level_teams_are_split():
    text, _ = T.points_rule("Indian Premier League", "T20")
    assert "more wins, then net run rate" in text
