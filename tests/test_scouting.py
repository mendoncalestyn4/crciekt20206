"""Scouting (ccstats/scouting.py): who belongs to which country, how domestic numbers are converted, who is
struggling and who could replace him, each rule on made-up numbers worked out by hand, then on the test scorecards."""

import math

import numpy as np
import pandas as pd
import pytest

from ccstats import scouting as SC
from ccstats.loader import Career
from fakecareer import Book
from serverkit import FIXTURES


def one(b, mid, date, home, away, player, team, runs=10, out=True, **kw):
    b.match(mid, date, home, away, **kw)
    b.inns(mid, 1, team, away if team == home else home, [(player, runs, 20, out)])


def test_who_belongs_to_which_country():
    b = Book()
    one(b, "t1", "2026-01-01", "India", "England", "P", "India")
    one(b, "t2", "2026-02-01", "India", "England", "P", "India")
    one(b, "r1", "2026-03-01", "Mumbai", "Delhi", "P", "Mumbai", section="Ranji Trophy", fmt="First-class",
        level="Domestic", country="India")
    # two nations capped the name: the one he played for most, marked unsure
    one(b, "o1", "2026-01-05", "India", "UAE", "Q", "India", section="ODIs", fmt="ODI")
    for k in range(3):
        one(b, f"o{k + 2}", f"2026-02-0{k + 1}", "UAE", "Oman", "Q", "UAE", section="ODIs", fmt="ODI")
    # uncapped, county and Ranji: the Ranji wins (county cricket takes overseas players)
    for k in range(5):
        one(b, f"c{k}", f"2026-05-0{k + 1}", "Kent", "Essex", "R", "Kent", section="County Championship · Division 1",
            fmt="First-class", level="Domestic", country="England")
    for k in range(2):
        one(b, f"r{k + 2}", f"2026-11-0{k + 1}", "Mumbai", "Delhi", "R", "Mumbai", section="Ranji Trophy",
            fmt="First-class", level="Domestic", country="India")
    # only ever in a franchise league: that league's country, marked as a guess
    one(b, "i1", "2026-04-01", "Mumbai Indians", "Chennai Super Kings", "S", "Mumbai Indians",
        section="Indian Premier League", fmt="T20", level="Franchise", country="India")
    one(b, "c9", "2026-06-01", "Kent", "Essex", "T", "Essex", section="County Championship · Division 1",
        fmt="First-class", level="Domestic", country="England")
    # capped by Canada, but plays in the Ranji Trophy (no overseas players): two players with one name, so India's too
    one(b, "k1", "2026-01-09", "Canada", "USA", "U", "Canada", section="T20Is", fmt="T20")
    one(b, "r9", "2026-11-09", "Mumbai", "Delhi", "U", "Delhi", section="Ranji Trophy", fmt="First-class",
        level="Domestic", country="India")
    c = SC.countries(b.career()).set_index("player")
    assert c.loc["P"].tolist() == ["India", True, "played for India", False, ""]
    assert c.loc["Q"].tolist() == ["UAE", True, "played for UAE", True, ""]
    assert c.loc["R"].tolist() == ["India", False, "domestic cricket", True, ""]
    assert c.loc["S"].tolist() == ["India", False, "going by the league", True, ""]
    assert c.loc["T"].tolist() == ["England", False, "domestic cricket", False, ""]
    assert c.loc["U"].tolist() == ["Canada", True, "played for Canada; also plays domestic cricket in India, which "
                                   "takes no overseas players (likely two players with one name)", True, "India"]


def test_a_measured_gap_is_pulled_to_the_minimum_and_never_below_it():
    assert SC._settle_gap(0.36, 8, 0.25) == pytest.approx((8 * 0.36 + 10 * 0.25) / 18)
    assert SC._settle_gap(-0.10, 29, 0.25) == 0.25          # the save says easier: the minimum stands
    assert SC._settle_gap(float("nan"), 0, 0.15) == 0.15     # nobody to measure: the minimum
    assert SC._settle_gap(0.50, 40, 0.25) == pytest.approx(0.45)
    assert SC._settle_gap(0.02, 50, 0.0) == pytest.approx(50 * 0.02 / 60)   # same level: pulled towards no gap


def test_the_gap_measured_from_players_in_both():
    b = Book()
    k = 0
    # A: Tests 120 for 3 outs (40), Ranji 200 for 4 (50); B: Tests 150 for 5 (30), Ranji 120 for 3 (40)
    for player, sec, scores in (("A", "Tests", [40, 40, 40]), ("A", "Ranji", [50, 50, 50, 50]),
                                ("B", "Tests", [30] * 5), ("B", "Ranji", [40, 40, 40])):
        for r in scores:
            k += 1
            one(b, f"m{k}", "2026-01-01", "X", "Y", player, "X", runs=r, section=sec)
    c = b.career()
    m = c.matches
    gaps, n = SC.measure(c, m[m.section == "Tests"].match_id, m[m.section == "Ranji"].match_id)
    # weights: the fewer dismissals of the two, 3 each; the geometric mean of 40/50 and 30/40
    assert gaps["bat"] == pytest.approx(1 - math.sqrt(0.8 * 0.75)) and n["bat"] == 2


def test_how_much_better_a_candidate_is():
    cand = pd.Series(dict(avg=44.0, sr=150.0, bowl_avg=20.0, econ=7.0))
    mine = pd.Series(dict(avg=40.0, sr=120.0, bowl_avg=25.0, econ=8.75))
    assert SC.gain(cand, mine, "bat", "multi") == pytest.approx(0.1)
    assert SC.gain(cand, mine, "bat", "t20") == pytest.approx(math.sqrt(1.1 * 1.25) - 1)
    assert SC.gain(cand, mine, "bowl", "multi") == pytest.approx(0.25)
    assert SC.gain(cand, mine, "bowl", "t20") == pytest.approx(0.25)


def test_settled_numbers_pull_a_short_record_towards_the_usual():
    base = dict(avg=30.0, rpb=0.5, bowl_avg=30.0, bowl_rpb=0.5)
    d = pd.DataFrame(dict(bat_runs=[360.0, 1500.0], bat_outs=[5, 30], bat_balls=[600.0, 3000.0], bat_inns=[7, 32],
                          bowl_runs=[0.0, 0.0], bowl_wickets=[0, 0], bowl_balls=[0.0, 0.0]), index=["short", "long"])
    s = SC._settled(d, base, "multi", "bat_runs", "bat_balls", "bowl_runs", "bowl_balls")
    # 5 dismissals at 30 added: (360 + 150) / 10 = 51, against 72 as it is; thirty innings at 50 hardly move
    assert s.avg["short"] == pytest.approx(51.0) and s.raw_avg["short"] == pytest.approx(72.0)
    assert s.avg["long"] == pytest.approx((1500 + 150) / 35)
    assert s.avg["long"] < s.avg["short"] < s.raw_avg["short"]


def test_who_is_struggling(monkeypatch):
    rows = []
    plan = {  # player: marks in s1 (oldest) .. s3 (latest), games in s3
        "Poor3": ([4, 3, 5], 3), "Poor2": ([7, 4, 3], 3), "OneBad": ([7, 7, 1], 3), "Mixed": ([3, 6, 4], 3),
        "Tail": ([1, 1, 1], 3), "Fine": ([6, 7, 8], 3)}
    for p, (marks, games) in plan.items():
        for k, mk in enumerate(marks):
            rows.append(dict(series=f"s{k + 1}", team="India", player=p, mark=mk, games=games if k == 2 else 3,
                             line="", label=f"series {k + 1}"))
    b = Book()
    for k in range(3):
        b.match(f"m{k}", f"2026-0{k + 1}-01", "India", "England", series=f"s{k + 1}")
    c = b.career()
    monkeypatch.setattr(SC, "_marks", lambda career: pd.DataFrame(rows))
    roles = pd.DataFrame(dict(role=["Opener", "Bowler", "Middle order", "Opener", "Tail", "Opener"]),
                         index=["Poor3", "Poor2", "OneBad", "Mixed", "Tail", "Fine"])
    monkeypatch.setattr(SC, "own_numbers", lambda career, team, target: roles)
    flagged = {f["player"]: f for f in SC.struggling(c, "India", "Tests")}
    # one bad series (even 1/10) is not enough; a 5 between two poor ones breaks the run of two, not the three
    assert set(flagged) == {"Poor3", "Poor2"}
    assert flagged["Poor3"]["why"] == "poor for three series running: 5/10, 3/10, 4/10 (latest first)"
    assert flagged["Poor2"]["why"] == "poor for two series running: 3/10, 4/10 (latest first)"
    # as of the series before: Poor3 had two poor ones running (3, 4); Mixed had 6 then 3
    assert {f["player"] for f in SC.struggling(c, "India", "Tests", at=1)} == {"Poor3"}


def pk(player, gain):
    return dict(player=player, gain=gain, clears=gain >= SC.BAR)


def test_one_man_goes_in_for_one_player():
    """Two struggling players with the same best pick: the one he'd improve on by more gets him, the other moves on to
    his next best still free; a level gain goes to the one listed first; a pick below the bar is never taken."""
    wants = [[pk("X", 0.5), pk("Y", 0.3)],     # A
             [pk("X", 0.4), pk("Z", 0.2)],     # B: loses X to A (0.5 beats 0.4), gets Z
             [pk("X", 0.3)],                   # C: loses X too, no one else
             [pk("W", 0.05)],                  # D: no one 10% better
             [pk("X", 0.12), pk("W", 0.06)]]   # E: loses X, W is below the bar
    assert SC.share(wants) == {"X": 0, "Z": 1}
    # a chain: B gets X, so A moves on to Y, which C wants more; A is left with no one
    assert SC.share([[pk("X", 0.3), pk("Y", 0.2)], [pk("X", 0.4)], [pk("Y", 0.5)]]) == {"X": 1, "Y": 2}
    # A moves on to Y, which nobody else wants
    assert SC.share([[pk("X", 0.3), pk("Y", 0.25)], [pk("X", 0.4), pk("Y", 0.35)]]) == {"X": 1, "Y": 0}
    assert SC.share([[pk("X", 0.3)], [pk("X", 0.3)]]) == {"X": 0}
    assert SC.share([]) == {}


def test_the_verdicts_when_two_want_the_same_man(monkeypatch):
    b = Book()
    b.match("m1", "2026-01-01", "India", "England")
    c = b.career()
    flagged = [dict(player=p, role="Opener", why="poor", mark=3, marks=[3, 3], line="", series="s", label="s")
               for p in ("A", "B", "C", "D")]
    wants = {"A": [pk("X", 0.5), pk("Y", 0.3), pk("V", 0.2), pk("U", 0.15)],
             "B": [pk("X", 0.4), pk("Z", 0.2), pk("Y", 0.15), pk("T", 0.1), pk("S", 0.05)],
             "C": [pk("X", 0.3), pk("Y", 0.08)],
             "D": [pk("X", 0.2)]}
    tops = []
    monkeypatch.setattr(SC, "struggling", lambda *a, **k: flagged)
    monkeypatch.setattr(SC, "picks_for", lambda career, team, target, player, role, top=3:
                        tops.append(top) or wants[player][:top])
    monkeypatch.setattr(SC, "own_numbers", lambda *a: pd.DataFrame(dict(keeper=[False] * 4), index=list("ABCD")))
    monkeypatch.setattr(SC, "lines", lambda *a, **k: {})
    r = {x["player"]: x for x in SC.replacements(c, "India", "Tests", top=3)}
    assert tops == [6, 6, 6, 6]       # three each, plus one for every other struggling player who could take one
    assert r["A"]["verdict"] == "Replace A with X" and [p["player"] for p in r["A"]["picks"]] == ["X", "Y", "V"]
    # B is shown his own list without X (going in for A); Y stays on it: no one brings Y in
    assert r["A"]["elsewhere"] == "" and r["A"]["lost"] == []
    why = "Their best pick, X, goes in for A instead, a bigger step up there."
    assert r["B"]["verdict"] == "Replace B with Z" and r["B"]["elsewhere"] == why
    assert [p["player"] for p in r["B"]["picks"]] == ["Z", "Y", "T"]
    assert r["B"]["lost"] == [dict(player="X", goes_to="A")]
    assert r["C"]["verdict"] == "Keep C for now: no one else is 10% better (closest: Y)" and r["C"]["elsewhere"] == why
    assert r["D"]["verdict"] == "Keep D for now: no one else is 10% better" and r["D"]["elsewhere"] == why
    assert r["D"]["picks"] == []


def test_several_men_going_in_for_others_said_once():
    assert SC._going_elsewhere([]) == ""
    assert SC._going_elsewhere([("X", "A"), ("Y", "B")]) == (
        "Their best picks go in for others instead, bigger steps up there: X for A and Y for B.")
    assert SC._going_elsewhere([("X", "A"), ("Y", "B"), ("Z", "C")]) == (
        "Their best picks go in for others instead, bigger steps up there: X for A, Y for B and Z for C.")


@pytest.fixture(scope="module")
def fixtures_career():
    return Career.build("Test career", [(f.name, f.read_bytes()) for f in FIXTURES])


def test_which_competitions_feed_which(fixtures_career):
    c = fixtures_career
    assert SC.feeders(c, "India", "Tests") == ["Ranji Trophy"]
    assert SC.feeders(c, "India", "ODIs") == ["Vijay Hazare Trophy"]
    assert SC.feeders(c, "India", "T20Is") == ["Indian Premier League"]
    assert set(SC.feeders(c, "England", "T20Is")) == {"T20 Blast", "The Hundred"}
    assert set(SC.feeders(c, "England", "Tests")) == {"County Championship · Division 1", "County Championship · Division 2"}
    ipl = c.matches[c.matches.section == "Indian Premier League"].home.iloc[0]
    assert SC.feeders(c, ipl, "Indian Premier League") == ["Indian Premier League"]
    d1 = "County Championship · Division 1"
    assert SC.feeders(c, "x", d1) == [d1, "County Championship · Division 2"]
    assert SC.feeders(c, "x", "County Championship · Division 2") == ["County Championship · Division 2"]


def test_the_conversion_never_goes_below_its_minimum(fixtures_career):
    c = fixtures_career
    t = SC.conversion(c, "Tests", "Ranji Trophy")
    assert t["minimum"] == 0.25 and t["pace_minimum"] == 0.10
    assert all(t[k] >= 0.25 for k in ("bat", "bowl")) and all(t[k] >= 0.10 for k in ("sr", "econ"))
    o = SC.conversion(c, "ODIs", "Vijay Hazare Trophy")
    assert o["minimum"] == 0.15 and o["bat"] >= 0.15
    d = SC.conversion(c, "County Championship · Division 1", "County Championship · Division 2")
    assert d["minimum"] == 0.10 and d["bat"] >= 0.10
    same = SC.conversion(c, "Tests", "Tests")
    assert (same["bat"], same["bowl"], same["sr"], same["econ"]) == (0.0, 0.0, 0.0, 0.0)


def test_candidates_are_eligible_and_not_in_the_side(fixtures_career):
    c = fixtures_career
    for team in ("India", "England"):
        for target in ("Tests", "ODIs", "T20Is"):
            pool = SC.candidates(c, team, target)
            _, in_side = SC._latest_side(c, team, target)
            if len(pool):
                assert (pool.country == team).all() and not (set(pool.index) & in_side)
                # converted numbers are never better than the same numbers as they were (settled the same way)
                gap = {f: SC.conversion(c, target, f) for f in SC.feeders(c, team, target)}
                assert all(g["bat"] >= SC.MIN_GAP_INTERNATIONAL[SC.sections(c).kind[target]] for g in gap.values())


def test_a_candidate_says_where_they_play_now(fixtures_career):
    """Each pick carries the side they last played for and in which competition (read by name: a pandas row's
    .where is a method, which once turned every competition into a blank)."""
    c = fixtures_career
    for target in SC.sections(c).index:
        teams = set(c.matches[c.matches.section == target].home)
        for team in sorted(teams)[:2]:
            pool = SC.candidates(c, team, target)
            if len(pool):
                who = SC._who(pool.iloc[0])
                assert who["side"] and who["where"] in set(c.matches.section)
                return
    pytest.skip("no candidates in the test scorecards")
