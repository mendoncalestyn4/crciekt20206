"""Marks out of 10 after every series (ccstats/marks.py): each rule on made-up matches worked out by hand, then the
whole thing on the test scorecards."""

import numpy as np
import pandas as pd
import pytest

from ccstats import marks as MK
from ccstats.loader import Career
from fakecareer import Book, side
from serverkit import FIXTURES


def values(book):
    return MK.match_values(book.career()).set_index(["match_id", "player"])


def lone_and_many():
    b = Book()
    # 1: India 180 all out, X1 a lone hundred; England 400 all out
    b.match("m1", "2026-01-01", "India", "England", series="s1", no=1, length=2)
    b.inns("m1", 1, "India", "England", side("X", [100, 20, 15, 10, 10, 5, 5, 3, 2]), extras=10)
    b.inns("m1", 2, "England", "India", side("E", [100, 80, 60, 50, 40, 30, 20, 10, 5, 5]))
    b.bowl("m1", 2, "India", "England", [("X10", 300, 100, 5), ("X11", 300, 150, 3), ("X9", 200, 150, 2)])
    b.catch("m1", 2, "India", "X2")
    # 2: India 600 for 4 with four hundreds (Y1 one of them); England 350 and 150 all out
    b.match("m2", "2026-01-10", "India", "England", series="s1", no=2, length=2)
    b.inns("m2", 1, "India", "England", side("Y", [100, 100, 100, 100, 150, 50], outs=4))
    b.inns("m2", 2, "England", "India", side("F", [100, 80, 60, 50, 30, 20, 10]))
    b.inns("m2", 3, "England", "India", side("G", [50, 40, 30, 20, 10]))
    b.bowl("m2", 2, "India", "England", [("Y10", 300, 100, 5), ("Y11", 300, 250, 5)])
    b.bowl("m2", 3, "India", "England", [("Y10", 200, 50, 5), ("Y9", 200, 100, 5)])
    return b


def test_a_lone_hundred_is_worth_more_than_one_of_four():
    v = values(lone_and_many())
    # half his side's share, half the average side's: (180 + 400) / 2 = 290; (600 + 350 + 150) / 2 = 550
    assert v.bat["m1", "X1"] == pytest.approx(100 * 0.5 * (1 / 180 + 1 / 290))
    assert v.bat["m2", "Y1"] == pytest.approx(100 * 0.5 * (1 / 600 + 1 / 550))
    assert v.bat["m1", "X1"] > 2.5 * v.bat["m2", "Y1"]


def test_forty_on_a_hard_pitch_counts_for_more():
    b = Book()
    for mid, theirs in (("hard", 110), ("flat", 500)):
        b.match(mid, "2026-02-01", "India", "England")
        b.inns(mid, 1, "India", "England", side("P", [40, 30, 20, 10, 10, 5, 5]))
        b.inns(mid, 2, "England", "India", side("Q", [theirs]))
    v = values(b)
    assert v.bat["hard", "P1"] == pytest.approx(40 * 0.5 * (1 / 120 + 1 / 115))
    # India's 120 against 500 is less than half the average side's 310, so it counts as 155 (one tiny total can't
    # blow a share up)
    assert v.bat["flat", "P1"] == pytest.approx(40 * 0.5 * (1 / 155 + 1 / 310))
    assert v.bat["hard", "P1"] > 1.4 * v.bat["flat", "P1"]


def test_a_five_for_is_a_share_of_the_wickets_the_side_took():
    v = values(lone_and_many())
    # m1: India took 10 (and lost 10): 5 x half of (1/10 + 1/10); m2: India took 20 of the 24 that fell
    assert v.bowl["m1", "X10"] == pytest.approx(5 * 0.5 * (1 / 10 + 1 / 10))
    assert v.bowl["m2", "Y11"] == pytest.approx(5 * 0.5 * (1 / 20 + 1 / 12))
    # a catch is a quarter of a wicket
    assert v.field["m1", "X2"] == pytest.approx(0.25 * 0.5 * (1 / 10 + 1 / 10))
    # in a Test the runs a bowler gives away don't count (no economy): Y10 and Y11 both took 5 in that innings
    assert v.bowl["m2", "Y10"] > v.bowl["m2", "Y11"]   # Y10 took 5 more in the second innings


def t20(rain=False, balls=120, result="win"):
    b = Book()
    b.match("t", "2026-03-01", "India", "England", section="T20Is", fmt="T20I", rain=rain, result=result)
    b.inns("t", 1, "India", "England", [("I1", 30, balls // 10, True), ("I2", 30, balls // 3, True),
                                        ("I3", 100, balls - balls // 10 - balls // 3, False)])
    b.inns("t", 2, "England", "India", [("E1", 150, balls, False)])
    b.bowl("t", 2, "India", "England", [("I4", balls // 2, 60, 0), ("I5", balls // 2, 90, 0)])
    return b


def test_white_ball_speed_counts():
    v = values(t20())
    rpb = 310 / 240
    div = 0.5 * (1 / 160 + 1 / 155)
    assert v.bat["t", "I1"] == pytest.approx((30 + 0.5 * (30 - 12 * rpb)) * div)
    assert v.bat["t", "I2"] == pytest.approx((30 + 0.5 * (30 - 40 * rpb)) * div)
    # economy: I4 gave 60 off 60 balls when the match went at 1.29 a ball, in runs per wicket of the match; India took
    # no wickets, and a share is never of fewer than one
    rpw = 310 / 2
    took_div = 0.5 * (1 / 1 + 1 / 1)
    assert v.bowl["t", "I4"] == pytest.approx((60 * rpb - 60) / rpw * took_div)


def test_two_players_with_one_name_in_a_match_are_kept_apart():
    """In a real save, Pakistan's M Rizwan made 13 off 7 and Bangladesh's M Rizwan 0 off 1 in the same T20I: each is
    valued on their own innings, by team, never the two added together."""
    b = Book()
    b.match("r", "2027-08-28", "Pakistan", "Bangladesh", section="T20Is", fmt="T20I")
    b.inns("r", 1, "Bangladesh", "Pakistan", [("M Rizwan", 0, 1, True), ("B2", 148, 108, True)])
    b.inns("r", 2, "Pakistan", "Bangladesh", [("M Rizwan", 13, 7, True), ("P2", 136, 98, False)])
    v = MK.match_values(b.career()).set_index(["team", "player"])
    rpb = (148 + 149) / (109 + 105)
    assert v.bat["Pakistan", "M Rizwan"] == pytest.approx((13 + 0.5 * (13 - 7 * rpb)) * 0.5 * (1 / 149 + 1 / 148.5))
    assert v.bat["Bangladesh", "M Rizwan"] == pytest.approx((0 + 0.5 * (0 - 1 * rpb)) * 0.5 * (1 / 148 + 1 / 148.5))


def test_a_rain_game_counts_for_its_overs_and_no_result_not_at_all():
    full, short = values(t20()), values(t20(rain=True, balls=60))
    assert short.weight.iloc[0] == pytest.approx(0.5)
    assert len(values(t20(result="no result"))) == 0
    assert full.weight.iloc[0] == 1.0


def test_the_mark_scale():
    assert list(MK._mark(np.array([-3, -2.25, -1, -0.3, 0, 0.74, 1, 1.5, 2, 2.25, 4]))) == [1, 1, 4, 5, 6, 7, 8, 9, 10, 10, 10]


def test_a_series_report():
    s = MK.series_marks(lone_and_many().career())
    india = s[(s.team == "India")].set_index("player")
    assert (india.series == "s1").all() and india.label.iloc[0] == "v England at home · 2 Tests · Jan 2026"
    # X1 batted once (100), Y1 once (100 of 600): the lone hundred ranks higher among batters
    assert india.mark["X1"] >= india.mark["Y1"] and india["rank"]["X1"] < india["rank"]["Y1"]
    assert india.line["X1"] == "100 runs at 100.0, 1 hundred"
    assert india.best["X1"] == "100 of India's 180 in the 1st Test v England"
    assert india.best["Y10"] == "10/150, 10 of the 20 wickets India took in the 2nd Test v England"
    # ranked 1..n within India's series, every mark 1 to 10
    assert sorted(india["rank"]) == list(range(1, len(india) + 1)) and india.mark.between(1, 10).all()


def test_a_player_who_did_nothing_in_a_match_isnt_marked_on_it():
    b = lone_and_many()
    b.match("m3", "2026-01-20", "India", "England", series="s1", no=3, length=3)
    b.inns("m3", 1, "England", "India", side("H", [50, 40]))
    b.inns("m3", 2, "India", "England", [("X1", 0, 0, False)])   # in the side, never faced a ball
    b.b[-1]["did_bat"] = False
    s = MK.series_marks(b.career()).set_index(["team", "player"])
    assert s.games["India", "X1"] == 1


@pytest.fixture(scope="module")
def fixtures_marks():
    c = Career.build("Test career", [(f.name, f.read_bytes()) for f in FIXTURES])
    return c, MK.series_marks(c)


def test_every_player_in_every_series_of_the_test_scorecards(fixtures_marks):
    c, s = fixtures_marks
    assert s.mark.between(1, 10).all() and s.games.ge(1).all()
    for (series, team), g in s.groupby(["series", "team"]):
        assert sorted(g["rank"]) == list(range(1, len(g) + 1))
        assert (g.sort_values("rank").settled.diff().dropna() <= 1e-12).all()   # best first
    assert set(s.player) <= set(c.batting.player) | set(c.bowling.player) | set(c.fielding.player)
    # the match a player did most in is one of his series' matches
    key = MK.series_key(c.matches.set_index("match_id"))
    assert all(key[r.best_match] == r.series for r in s.itertuples())


def test_a_players_share_of_the_team():
    """Runs out of the team's totals (extras included), wickets out of the team's bowlers', worked by hand."""
    from ccstats import players as PL
    b = Book()
    b.match("m1", "2026-01-01", "India", "England")
    b.inns("m1", 1, "India", "England", [("A", 60, 80, True), ("B", 30, 40, True)], extras=10)
    b.bowl("m1", 1, "England", "India", [("X", 60, 50, 2)])
    b.inns("m1", 2, "England", "India", [("X", 40, 50, True)], extras=0)
    b.bowl("m1", 2, "India", "England", [("B", 60, 20, 3), ("C", 60, 20, 1)])
    s = PL.team_share(b.career(), "B").iloc[0]
    assert (s.matches, s.team_matches, s.runs, s.team_runs, s.wickets, s.team_wickets) == (1, 1, 30, 100, 3, 4)
    assert s.run_share == pytest.approx(30.0) and s.wicket_share == pytest.approx(75.0)


def test_hundreds_and_fifties_are_counted_innings_by_innings():
    """A hundred in each innings of a Test is two hundreds; a hundred and a fifty is one of each."""
    b = Book()
    b.match("t1", "2026-01-01", "India", "England", series="S1")
    b.inns("t1", 1, "India", "England", [("A", 120, 200, True), ("B", 60, 100, True), ("C", 10, 20, True)])
    b.inns("t1", 2, "England", "India", [("X", 30, 60, True)])
    b.inns("t1", 3, "India", "England", [("A", 101, 150, True), ("B", 110, 150, False), ("C", 55, 80, True)])
    s = MK.series_marks(b.career()).set_index("player")
    assert (s.hundreds["A"], s.fifties["A"]) == (2, 0)
    assert (s.hundreds["B"], s.fifties["B"]) == (1, 1)
    assert (s.hundreds["C"], s.fifties["C"]) == (0, 1)
    assert "2 hundreds" in s.line["A"]
