"""Every scorecard checks itself (your pick of 14 November): besides the sums (runs and extras to the total, bowlers'
overs and wickets, dismissals), the fall of wickets (numbered in order, never going down, never above the total) and the
result against the scores (a win by wickets, an innings win, a tie). Each check is shown catching a broken card."""

import copy

import pytest

from pathlib import Path

from ccstats.parser import Innings, Match, parse_scorecard, validate_match

# every test scorecard (the odd ones too: declarations, rain, super overs, odd names), not the two junk files
HERE = Path(__file__).parent
FILES = sorted(f for d in HERE.glob("fixtures*") if d.is_dir() for f in d.glob("*.txt"))


@pytest.fixture(scope="module")
def cards():
    out = []
    for f in FILES:
        try:
            m = parse_scorecard(f.read_text(errors="replace"), f.name)
        except Exception:  # noqa: BLE001 - the junk files on purpose
            continue
        if m.innings:
            out.append(m)
    return out


def _find(cards, test):
    m = next((m for m in cards if test(m)), None)
    if m is None:
        pytest.skip("no scorecard of that kind in the test set")
    return copy.deepcopy(m)


def test_every_test_scorecard_is_clean(cards):
    assert {m.source: validate_match(m) for m in cards if validate_match(m)} == {}


def test_fall_of_wickets_out_of_order_is_caught(cards):
    m = _find(cards, lambda m: any(len(i.fow) >= 3 for i in m.innings))
    inn = next(i for i in m.innings if len(i.fow) >= 3)
    inn.fow[0], inn.fow[1] = (inn.fow[1][0], inn.fow[0][1]), (inn.fow[0][0], inn.fow[1][1])   # numbered 2, 1, 3...
    assert any("not numbered 1, 2, 3" in p for p in validate_match(m))


def test_fall_of_wickets_going_down_is_caught(cards):
    m = _find(cards, lambda m: any(len(i.fow) >= 2 and i.fow[1][1] > i.fow[0][1] for i in m.innings))
    inn = next(i for i in m.innings if len(i.fow) >= 2 and i.fow[1][1] > i.fow[0][1])
    inn.fow[1] = (inn.fow[1][0], inn.fow[0][1] - 1)
    assert any("goes down" in p for p in validate_match(m))


def test_a_wicket_above_the_total_is_caught(cards):
    m = _find(cards, lambda m: any(i.fow for i in m.innings))
    inn = next(i for i in m.innings if i.fow)
    inn.fow[-1] = (inn.fow[-1][0], inn.total + 1)
    assert any("above the innings total" in p for p in validate_match(m))


def test_a_wicket_margin_the_chase_doesnt_give_is_caught(cards):
    m = _find(cards, lambda m: m.result_type == "win" and m.margin_wickets is not None and m.innings
              and m.innings[-1].team == m.winner and "dls" not in m.result.lower())
    m.margin_wickets = (m.margin_wickets % 9) + 1 if m.margin_wickets != 10 - m.innings[-1].wickets else (10 - m.innings[-1].wickets) % 10 + 1
    if m.margin_wickets == 10 - m.innings[-1].wickets:
        m.margin_wickets = 10 - m.innings[-1].wickets - 1
    assert any("lost" in p and "in the chase" in p for p in validate_match(m))


def test_wickets_win_by_the_side_batting_first_is_caught(cards):
    m = _find(cards, lambda m: m.result_type == "win" and m.margin_wickets is not None and len(m.innings) >= 2
              and m.innings[-1].team == m.winner)
    m.winner = m.innings[0].team if m.innings[0].team != m.winner else m.innings[-2].team
    assert any("batted last" in p for p in validate_match(m))


def test_innings_win_margin_is_checked():
    """No innings win among the test scorecards, so one made by hand: 300 against 100 and 120 is an innings and 80."""
    def card(margin):
        m = Match("hand-made", "hand-made", team1="Kent", team2="Essex", result=f"Kent won by an innings and {margin} runs")
        m.innings = [Innings("Kent", 1, 1, total=300), Innings("Essex", 2, 1, total=100), Innings("Essex", 3, 2, total=120)]
        m.result_type, m.winner, m.margin_runs, m.innings_win = "win", "Kent", margin, True
        return [p for p in validate_match(m) if "won by an innings" in p]
    assert card(80) == []
    assert card(87) == ["Kent won by an innings and 87 runs but the totals differ by 80"]


def test_a_tie_with_different_scores_is_caught(cards):
    m = _find(cards, lambda m: m.result_type == "win" and len(m.innings) == 2 and "super" not in m.result.lower()
              and "dls" not in m.result.lower())
    m.result_type, m.result, m.winner = "tie", "Match tied", ""
    assert any("is a tie but the scores" in p for p in validate_match(m))


def test_a_rain_revised_chase_is_not_a_problem(cards):
    """One innings each, won by wickets below the other side's total: a target the rain revised, never flagged."""
    m = _find(cards, lambda m: m.result_type == "win" and m.margin_wickets is not None and len(m.innings) == 2
              and m.innings[-1].team == m.winner)
    m.innings[-1].total = m.innings[0].total - 5
    assert not any("don't pass" in p for p in validate_match(m))


# ------------------------------------------------------------------ impossible values (your pick of 14 November)
def _bat_card(cards):
    return _find(cards, lambda m: any(b.did_bat and b.balls > 0 for i in m.innings for b in i.batting))


def test_more_than_six_a_ball_is_caught(cards):
    m = _bat_card(cards)
    b = next(b for i in m.innings for b in i.batting if b.did_bat and b.balls > 0)
    b.runs = 6 * b.balls + 1
    assert any("more than 6 a ball" in p for p in validate_match(m))


def test_a_figure_below_zero_and_eleven_wickets_are_caught(cards):
    m = _bat_card(cards)
    m.innings[0].byes = -1
    assert any("below 0" in p for p in validate_match(m))
    m = _bat_card(cards)
    m.innings[0].wickets = 11
    assert any("11 wickets in one innings" in p for p in validate_match(m))


def test_maidens_and_dot_balls_past_the_balls_are_caught(cards):
    m = _find(cards, lambda m: any(w.maidens is not None for i in m.innings for w in i.bowling))
    w = next(w for i in m.innings for w in i.bowling if w.maidens is not None)
    w.maidens = w.balls // 6 + 1
    assert any("more maidens than overs" in p for p in validate_match(m))
    m = _find(cards, lambda m: any(w.dots is not None for i in m.innings for w in i.bowling))
    w = next(w for i in m.innings for w in i.bowling if w.dots is not None)
    w.dots = w.balls + 1
    assert any("more dot balls than balls" in p for p in validate_match(m))


@pytest.mark.parametrize("fmt,limit", [("T20", 24), ("ODI", 60), ("The Hundred", 20)])
def test_a_bowler_past_the_formats_limit_is_caught(cards, fmt, limit):
    from ccstats.loader import QUOTA
    m = _find(cards, lambda m: any(i.bowling for i in m.innings))
    for i in m.innings:   # every bowler within the limit first (a T20 card's 24 balls are past The Hundred's 20)
        for x in i.bowling:
            x.balls = min(x.balls, limit)
    w = next(w for i in m.innings for w in i.bowling)
    w.balls = limit
    assert not any("past the limit" in p for p in validate_match(m, QUOTA[fmt]))
    w.balls = limit + 1
    assert any(f"past the limit of {limit}" in p for p in validate_match(m, QUOTA[fmt]))


def test_the_checked_mark_on_each_match():
    """A clean scorecard shows "checked ✓" on its page and in the match finder; one whose sums don't add up shows
    which ones instead (and the finder marks it)."""
    import pandas as pd

    from ccstats.loader import Career
    from serverkit import FIXTURES
    from server import matchpage as MP
    c = Career.build("Test career", [(f.name, f.read_bytes()) for f in FIXTURES[:6]])
    mid = c.matches.match_id.iloc[0]
    d = MP.page(c, mid, [], {})
    assert d["checked"]["ok"] is True and d["checked"]["problems"] == [] and len(d["checked"]["checks"]) >= 6
    assert all(x["checked"] for x in MP.finder(c, "All sections")["matches"])
    c.problems = pd.DataFrame([dict(match_id=mid, source="x", problem="England innings 1: batting runs + extras do not add up to the total")])
    d = MP.page(c, mid, [], {})
    assert d["checked"]["ok"] is False and "do not add up" in d["checked"]["problems"][0]
    marks = {x["id"]: x["checked"] for x in MP.finder(c, "All sections")["matches"]}
    assert marks[mid] is False and sum(not v for v in marks.values()) == 1
