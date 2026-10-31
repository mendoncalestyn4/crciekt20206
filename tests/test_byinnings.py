"""Figures innings by innings (ccstats/byinnings.py and the Player page's two tiles): made-up matches with every number
worked out by hand, the 4th innings of a Test as chasing or saving, and the line naming the best and the weakest."""

import pytest

from ccstats import byinnings as BI
from fakecareer import Book
from server import playerpage as PP


def five_tests():
    """Five Tests, India v England, too few for the competition's own length, so a match is 450 overs.
    t1: England chase 251 with 220 overs left (1.14 an over): chasing; they win.
    t2: England need 501 with 130 overs left (3.85 an over): batting to save; they lose.
    t3: the same, but England get there: chasing, whatever the rate.
    t4: England need 401 with 170 overs left (2.36 an over): chasing, drawn.
    t5: England follow on and set India 51: India chase in the 4th innings."""
    b = Book()

    def test(mid, day, winner, result, innings):
        b.match(mid, f"2026-0{day}-01", "India", "England", winner=winner, result=result)
        for no, team, opp, e1, e2, balls in innings:
            first = "E" if team == "England" else "I"
            b.inns(mid, no, team, opp, [(f"{first}1", *e1), (f"{first}2", *e2)], balls=balls)

    test("t1", 1, "England", "win", [(1, "India", "England", (100, 200, True), (200, 300, True), 540),
                                      (2, "England", "India", (50, 100, True), (200, 300, True), 480),
                                      (3, "India", "England", (100, 150, True), (100, 150, True), 360),
                                      (4, "England", "India", (80, 150, False), (171, 200, False), 400)])
    test("t2", 2, "India", "win", [(1, "India", "England", (200, 400, True), (200, 400, True), 900),
                                    (2, "England", "India", (20, 100, True), (180, 300, True), 420),
                                    (3, "India", "England", (150, 300, True), (150, 300, True), 600),
                                    (4, "England", "India", (10, 50, True), (90, 200, True), 300)])
    test("t3", 3, "England", "win", [(1, "India", "England", (200, 400, True), (200, 400, True), 900),
                                      (2, "England", "India", (0, 10, True), (200, 400, True), 420),
                                      (3, "India", "England", (150, 300, True), (150, 300, True), 600),
                                      (4, "England", "India", (150, 300, True), (351, 300, False), 600)])
    test("t4", 4, "", "draw", [(1, "India", "England", (150, 300, True), (200, 300, True), 600),
                                (2, "England", "India", (100, 300, True), (200, 300, True), 600),
                                (3, "India", "England", (150, 240, True), (200, 240, True), 480),
                                (4, "England", "India", (40, 100, False), (100, 200, False), 300)])
    test("t5", 5, "India", "win", [(1, "India", "England", (250, 450, True), (250, 450, True), 900),
                                    (2, "England", "India", (5, 50, True), (145, 250, True), 300),
                                    (3, "England", "India", (60, 400, True), (340, 400, True), 800),
                                    (4, "India", "England", (30, 50, True), (21, 30, False), 80)])
    return b.career()


def test_the_4th_innings_is_chasing_or_saving():
    c = five_tests()
    assert BI.match_length(c, "Tests") == 450
    sl = BI.slots(c, c.matches.match_id, "multi").set_index(["match_id", "innings_no"])
    assert [sl.slot[(m, 4)] for m in ("t1", "t2", "t3", "t4", "t5")] == ["4c", "4s", "4c", "4c", "4c"]
    assert [sl.target[(m, 4)] for m in ("t1", "t2", "t3", "t4", "t5")] == [251, 501, 501, 401, 51]
    assert sl.rate[("t1", 4)] == pytest.approx(251 / 220)
    assert sl.rate[("t2", 4)] == pytest.approx(501 / 130)
    assert sl.rate[("t4", 4)] == pytest.approx(401 / 170)
    assert sl.left[("t5", 4)] == pytest.approx(450 - 2000 / 6)          # follow-on: England batted 2nd and 3rd
    assert list(sl.slot.loc[[(m, n) for m in c.matches.match_id for n in (1, 2, 3)]]) == ["1", "2", "3"] * 5


def test_a_batter_innings_by_innings_by_hand():
    """E1 opens for England: 2nd innings 50, 20, 0, 100, 5 (175 in 5, all out); 3rd innings 60 (the follow-on);
    4th chasing 80*, 150, 40* (270 for once out); 4th saving 10."""
    c = five_tests()
    t = BI.batting(c, c.matches.match_id, "E1", "multi").set_index("slot")
    assert list(t.index) == ["2", "3", "4c", "4s"]
    assert list(t.label) == ["2nd innings", "3rd innings", "4th innings, chasing", "4th innings, batting to save"]
    assert (t.innings["2"], t.runs["2"], t.not_outs["2"], t.average["2"]) == (5, 175, 0, 35.0)
    assert (t.innings["4c"], t.not_outs["4c"], t.runs["4c"], t.average["4c"], t.high["4c"]) == (3, 2, 270, 270.0, "150")
    assert t.hundreds["4c"] == 1 and t.fifties["4c"] == 1 and t.fifties["2"] == 1 and t.hundreds["2"] == 1
    assert t.other_average["4c"] == pytest.approx((175 + 60) / 6)        # the other three innings
    assert t.other_average["2"] == pytest.approx((60 + 270 + 10) / 3)
    assert t.usual_average["2"] == pytest.approx(35.0)                   # he was the only opener batting 2nd
    assert t.small["3"] and not t.small["2"] and not t["best"].any()     # only one slot with 5 innings: no verdict


def one_day_career(z_first: int, z_chasing: int):
    """Twelve ODIs, A v B. A bat first in the first six, B in the rest. Z opens for A, B1 for B (40 every time);
    AX bowls for A and BX for B, 10 overs each."""
    b = Book()
    for i in range(12):
        mid = f"o{i}"
        a_first = i < 6
        b.match(mid, f"2026-{1 + i:02d}-01", "A", "B", section="ODIs", fmt="ODI", winner="A" if a_first else "B")
        first, second = (("A", "B"), ("B", "A")) if a_first else (("B", "A"), ("A", "B"))
        for no, (team, opp) in enumerate((first, second), start=1):
            bats = [("Z", z_first if a_first else z_chasing, 60, True)] if team == "A" else [("B1", 40, 60, True)]
            b.inns(mid, no, team, opp, bats + [(f"{team}2", 30, 30, True)], balls=300)
            bowler = "BX" if team == "A" else "AX"
            # AX: 50 for 1 bowling first, 30 for 3 bowling second; BX: 40 for 2 every time
            spell = (bowler, 60, 40, 2) if bowler == "BX" else (bowler, 60, 50, 1) if no == 1 else (bowler, 60, 30, 3)
            b.bowl(mid, no, opp, team, [spell])
    return b.career()


def test_batting_first_or_chasing_with_the_best_named():
    """Z: 80 every time batting first, 20 chasing. The usual for an opener: batting first (6 x 80 + 6 x 40) / 12 = 60,
    chasing (6 x 20 + 6 x 40) / 12 = 30. Settled with 6 dismissals at the usual: 70 (+17%) and 25 (-17%)."""
    c = one_day_career(80, 20)
    ids = c.matches.match_id
    t = BI.batting(c, ids, "Z", "one").set_index("slot")
    assert list(t.label) == ["Batting first", "Chasing"]
    assert (t.average["1"], t.other_average["1"], t.usual_average["1"]) == (80.0, 20.0, 60.0)
    assert (t.average["2"], t.other_average["2"], t.usual_average["2"]) == (20.0, 80.0, 30.0)
    assert t.edge["1"] == pytest.approx((70 - 60) / 60 * 100) and t.edge["2"] == pytest.approx((25 - 30) / 30 * 100)
    assert t["best"]["1"] and t.weakest["2"]
    d = PP._by_innings(c, "Z", "ODIs", "", ids, "one", bowling=False)
    assert (d["title"], d["right"]) == ("Innings by innings", "batting first or chasing")
    assert d["shows"] == ("Better batting first: averages 80.0 (6 innings, 0 not out) against 20.0 chasing and the usual 60.0 "
                          "for their batting positions. Chasing: 20.0 (6 innings) against 80.0 batting first and "
                          "the usual 30.0 for their batting positions.")
    assert d["total"]["runs"] == 600 and d["total"]["innings"] == 12 and d["total"]["average"] == 50
    r = {x["slot"]: x for x in d["rows"]}
    assert r["1"]["vs_other"] == 60 and r["2"]["vs_usual"] == -10            # + is better


def test_about_the_same_and_not_enough():
    c = one_day_career(40, 40)
    d = PP._by_innings(c, "Z", "ODIs", "", c.matches.match_id, "one", bowling=False)
    assert d["shows"] == "About the same batting first and chasing: once settled, within 10% of each other."
    c = five_tests()
    d = PP._by_innings(c, "E1", "Tests", "", c.matches.match_id, "multi", bowling=False)
    assert d["shows"].startswith("Not enough innings yet") and d["rule"].startswith("4th innings: chasing to win")


def test_a_bowler_first_or_second_by_hand():
    """AX: bowling first 6 x 50 for 1 (average 50, economy 5.00); second 6 x 30 for 3 (10.0, 3.00). The usual: bowling
    first AX's 300 for 6 and BX's 240 for 12 (30.0, 4.50 an over); second BX 240 for 12 and AX 180 for 18 (14.0, 3.50)."""
    c = one_day_career(40, 40)
    ids = c.matches.match_id
    t = BI.bowling(c, ids, "AX", "one").set_index("slot")
    assert list(t.label) == ["Bowling first", "Bowling second"]
    assert (t.innings["1"], t.runs["1"], t.wickets["1"], t.average["1"], t.economy["1"]) == (6, 300, 6, 50.0, 5.0)
    assert (t.average["2"], t.economy["2"], t.bbi["2"], t.hauls["2"], t.overs["2"]) == (10.0, 3.0, "3/30", 0, "60")
    assert (t.usual_average["1"], t.usual_economy["1"]) == (30.0, 4.5)
    assert (t.usual_average["2"], t.usual_economy["2"]) == (14.0, 3.5)
    assert (t.other_average["1"], t.other_economy["1"]) == (10.0, 3.0)
    d = PP._by_innings(c, "AX", "ODIs", "", ids, "one", bowling=True)
    r = {x["slot"]: x for x in d["rows"]}
    assert r["1"]["avg_vs_usual"] == -20 and r["2"]["econ_vs_usual"] == 0.5   # + is better: a lower figure
    assert d["shows"].startswith("Better bowling second: 18 wickets at 10.0 (6 innings), economy 3.00, against 50.0 bowling "
                                 "first and the usual 14.0 here.")
    assert d["total"] == {"innings": 12, "overs": "120", "runs": 480, "wickets": 24, "best": "3/30", "average": 20,
                          "economy": 4, "strike_rate": 30, "hauls": 0}


def test_a_short_competition_s_match_length():
    """Too few games to measure: a Test is five days (450 overs); a first-class game is the shortest of three, four or
    five days (288, 384, 450 overs) that its longest game fits in, so three-day tour games aren't given four days."""
    b = Book()
    for mid, section, overs in (("a", "Tour matches", 250), ("b", "Tour matches", 270), ("c", "Ranji Trophy", 350)):
        b.match(mid, "2026-01-01", "India", "England", section=section, fmt="First-class", level="Domestic")
        for no in (1, 2, 3, 4):
            b.inns(mid, no, "India" if no % 2 else "England", "England" if no % 2 else "India", [("X", 10, 10, True)],
                   balls=overs * 6 // 4)
    c = b.career()
    assert BI.match_length(c, "Tour matches") == 288 and BI.match_length(c, "Ranji Trophy") == 384
    assert BI.match_length(five_tests(), "Tests") == 450
