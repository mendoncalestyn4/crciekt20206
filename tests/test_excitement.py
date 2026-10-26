"""The match excitement rating (ccstats/excitement.py): each rule on made-up matches worked out by hand, then on the
test scorecards."""

import math
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from ccstats import excitement as X
from ccstats.loader import Career
from serverkit import FIXTURES

NAN = float("nan")


def match(**kw):
    base = dict(super_over="", result_type="win", innings_win=False, margin_runs=NAN, margin_wickets=NAN, winner="B",
                format="T20", rain=False, knockout=False, stage="", series_length=NAN, series_match_no=NAN,
                home="A", away="B")
    return SimpleNamespace(**{**base, **kw})


def innings(*rows):
    """(team, runs, wickets, balls) for each innings, in order."""
    return pd.DataFrame([dict(innings_no=i + 1, team=t, runs=r, wickets=w, balls=b) for i, (t, r, w, b) in enumerate(rows)])


TWO = innings(("A", 160, 7, 120), ("B", 161, 7, 120))


@pytest.mark.parametrize("kw, inn, kind, want, words", [
    (dict(margin_runs=1, winner="A"), TWO, "t20", 1.0, "won by 1 run"),                       # as tight as it gets
    (dict(margin_runs=5, winner="A"), TWO, "t20", math.exp(-4 / 8), "won by 5 runs"),
    (dict(margin_runs=10, winner="A", format="ODI"), TWO, "one", math.exp(-9 / 15), "won by 10 runs"),
    (dict(margin_wickets=3), TWO, "t20", 1.0, "won by 3 wickets off the last ball"),        # balls left count too
    (dict(margin_wickets=6), innings(("A", 160, 7, 120), ("B", 161, 4, 90)), "t20", math.exp(-30 / 6), ""),  # 30 balls left: easy
    (dict(margin_wickets=1), innings(("A", 160, 7, 120), ("B", 161, 9, 102)), "t20", 1.0, "won by 1 wicket"),
    (dict(result_type="tie", winner=""), TWO, "t20", 1.0, "tied"),
    (dict(result_type="tie", winner="", super_over="B"), TWO, "t20", 8 / 7, "tied, and a super over"),
    (dict(innings_win=True, margin_runs=50), TWO, "multi", 0.0, ""),
])
def test_the_finish(kw, inn, kind, want, words):
    f, w = X.finish(match(**kw), inn, kind)
    assert f == pytest.approx(want) and w == words


def test_a_draw_counts_the_last_pair_holding_on_or_the_chasers_just_short():
    held = innings(("A", 300, 10, 0), ("B", 250, 10, 0), ("A", 200, 4, 0), ("B", 120, 9, 0))
    assert X.finish(match(result_type="draw", winner=""), held, "multi") == (1.0, "drawn with 9 down")
    # B needed 300 + 200 - 250 + 1 = 251 and finished 241/5: ten short
    short = innings(("A", 300, 10, 0), ("B", 250, 10, 0), ("A", 200, 4, 0), ("B", 241, 5, 0))
    f, w = X.finish(match(result_type="draw", winner=""), short, "multi")
    assert f == pytest.approx(math.exp(-9 / 40)) and w == "drawn 10 runs short of the target"


def test_the_chance_of_a_chase():
    exp = {k: 25.0 * (10 - k) for k in range(10)}       # each wicket left usually adds 25
    assert X.chance_chasing(50, 8, exp) == pytest.approx(0.5)             # needing what the last two usually add
    assert X.chance_chasing(100, 8, exp) == pytest.approx(1 / 9)          # twice that
    assert X.chance_chasing(0, 9, exp) == 1.0 and X.chance_chasing(10, 9, {}) == 0.0


def test_a_comeback_from_the_scorecard():
    exp = {k: 25.0 * (10 - k) for k in range(10)}
    inn = innings(("A", 250, 10, 300), ("B", 251, 8, 296))
    fow = pd.DataFrame(dict(innings_no=2, wicket=range(1, 9), score=[10, 20, 30, 40, 50, 60, 70, 200]))
    # B's worst moment: 70/7 needing 181 when the last three usually add 75 (a chance of 1 in 15)
    c, w = X.comeback(match(margin_wickets=2, format="ODI"), inn, fow, "one", exp)
    low = 1 / (1 + (181 / 75) ** 3)
    assert c == pytest.approx((0.35 - low) / 0.30) and w == "a comeback (70/7 needing 181)"
    # the side defending in a Test: the chasers' best moment counts, never their last pair (that's the finish)
    test = innings(("A", 300, 10, 0), ("B", 280, 10, 0), ("A", 200, 10, 0), ("B", 219, 10, 0))   # B needed 221
    falls = pd.DataFrame(dict(innings_no=4, wicket=range(1, 11), score=[150, 170, 180, 190, 200, 205, 210, 212, 218, 219]))
    c, w = X.comeback(match(margin_runs=1, winner="A"), test, falls, "multi", exp)
    # 210/7 needing 11 with three wickets that usually add 75 is their best moment (better than 150/1 needing 71 with
    # nine that add 225); 218/9 needing 3 is the last pair, the finish itself
    assert 1 / (1 + (11 / 75) ** 3) > 1 / (1 + (71 / 225) ** 3) > 0.95
    assert c == 1.0 and w == "a comeback (B were 210/7 needing 11)"
    # a game shortened by rain: no chase to read
    assert X.comeback(match(margin_wickets=2, format="ODI", rain=True), inn, fow, "one", exp) == (0.0, "")


def test_a_first_innings_deficit_turned_round():
    test = innings(("A", 400, 10, 0), ("B", 280, 10, 0), ("A", 150, 10, 0), ("B", 271, 5, 0))   # B won by 5 wickets
    falls = pd.DataFrame(dict(innings_no=4, wicket=range(1, 6), score=[100, 150, 200, 230, 250]))
    c, w = X.comeback(match(margin_wickets=5), test, falls, "multi", {k: 40.0 * (10 - k) for k in range(10)})
    assert c == pytest.approx(120 / 150) and w == "a comeback (120 behind on first innings)"


def test_the_stakes():
    series = pd.DataFrame(dict(series_match_no=[1, 2, 3], winner=["A", "B", ""]))
    assert X.stakes(match(series_length=3, series_match_no=3, winner="A"), series) == (1.0, "a series decider")
    assert X.stakes(match(series_length=3, series_match_no=2, winner="B"), series) == (0.5, "levelled the series")
    assert X.stakes(match(series_length=3, series_match_no=2, winner="A"), series) == (0.0, "")
    assert X.stakes(match(knockout=True, stage="Final"), None) == (1.0, "a final")
    assert X.stakes(match(knockout=True, stage="Semi-final"), None) == (0.7, "a semi-final")


@pytest.fixture(scope="module")
def rated():
    c = Career.build("Test career", [(f.name, f.read_bytes()) for f in FIXTURES])
    return pd.concat([X.rate(c, g.match_id) for _, g in c.matches.groupby("section")]).set_index("match_id"), c


def test_the_test_scorecards(rated):
    d, c = rated
    assert len(d) == len(c.matches) and d.rating.between(0, 10).all()
    parts = d.finish + d.comeback + d.stakes + d.show
    assert all(r == round(min(10.0, p), 1) for r, p in zip(d.rating, parts))
    for sec, g in d.groupby("section"):   # ranked within each section, 1 the best
        assert g.loc[g.rating.idxmax(), "rank"] == 1 and (g["of"] == len(g)).all()
    # England's World Cup chase of 297 against South Africa: 301/9 with a ball to spare, the 9th wicket down at 287
    eng = d[(d.result == "England won by 1 wicket")].iloc[0]
    assert eng.finish == 7.0 and "won by 1 wicket with 1 ball left" in eng.why and "287/9 needing 10" in eng.why
    # the World Cup final: 2 wickets and 6 balls left, so 1 - (1 - 0.75)(1 - e^-6/15) of the finish
    final = d[(d.result == "Australia won by 2 wickets") & (d.stage == "Final")].iloc[0]
    assert final.finish == pytest.approx(7 * (1 - 0.25 * (1 - math.exp(-6 / 15))), abs=0.01) and final.stakes == 1.0
    # a drawn Ranji semi-final (Karnataka through on more wickets left): Gujarat held on with 8 down
    semi = d[d.result == "Karnataka won on more wickets left"].iloc[0]
    assert (semi.finish, semi.stakes) == (4.9, 0.7) and "drawn with 8 down" in semi.why
    # a section of two matches: the win-chance model's "0%" comes from one other game, so it isn't a comeback
    assert not d.why.str.contains("from 0%").any()
    assert np.isfinite(d.rating).all()
