"""The odd-cases library (your picks of 14 November): every rare way of getting out read right and counted right (hit
wicket, obstructing the field, handled the ball, hit the ball twice, timed out, retired out, retired hurt, absent hurt),
and an alarm for anything the site doesn't know (a dismissal it can't read, a line it doesn't understand). Each case is
a real scorecard with one line changed, so the rest of the card still adds up."""

from pathlib import Path

import pytest

from ccstats.loader import Career
from ccstats.parser import RUN_OUTS, parse_scorecard, validate_match

CARD = Path(__file__).parent / "fixtures" / "11_mar_2026-aus_v_ind_wc20_-_f.txt"
TEXT = CARD.read_text(errors="replace")
RUN_OUT = "T Head          run out                   3    6    -   -"
LBW = "K Yadav         lbw b Bell                20   9    3   1"


def card(old: str, new: str):
    assert old in TEXT
    return parse_scorecard(TEXT.replace(old, new), CARD.name)


def entry(m, player):
    return next(b for i in m.innings for b in i.batting if b.player == player)


def test_the_card_itself_is_clean():
    assert validate_match(parse_scorecard(TEXT, CARD.name)) == []


def test_hit_wicket_is_the_bowlers_wicket():
    m = card(LBW, "K Yadav         hit wicket b Bell         20   9    3   1")
    e = entry(m, "K Yadav")
    assert (e.how_out, e.bowler, e.not_out, e.did_bat) == ("hit wicket", "G Bell", False, True)   # the full name
    assert validate_match(m) == []          # still Bell's wicket, so the bowling still adds up


@pytest.mark.parametrize("text,kind", [("obstructing the field", "obstructing"), ("handled the ball", "obstructing"),
                                       ("hit the ball twice", "obstructing"), ("timed out", "timed out"),
                                       ("retired out", "retired out")])
def test_outs_that_are_not_the_bowlers(text, kind):
    """Like a run-out: a wicket for the side, none for any bowler (so it swaps cleanly for the card's run-out)."""
    m = card(RUN_OUT, f"T Head          {text:<26}3    6    -   -")
    e = entry(m, "T Head")
    assert (e.how_out, e.bowler, e.not_out) == (kind, "", False)
    assert kind in RUN_OUTS and validate_match(m) == []


def test_retired_hurt_is_not_out_and_not_a_wicket():
    """Swapped for a run-out, the innings has one wicket fewer than the card says, and the check says so: a retired
    hurt batter is not out."""
    m = card(RUN_OUT, "T Head          retired hurt              3    6    -   -")
    e = entry(m, "T Head")
    assert (e.how_out, e.not_out, e.did_bat) == ("retired hurt", True, True)
    assert any("dismissals do not match the wickets" in p for p in validate_match(m))


def test_absent_hurt_did_not_bat():
    """A batter who didn't bat, printed instead as absent hurt: no innings, and the card still adds up."""
    for f in sorted(CARD.parent.glob("*.txt")):
        text = f.read_text(errors="replace")
        m = parse_scorecard(text, f.name)
        dnb = next((b for i in m.innings for b in i.batting if not b.did_bat), None)
        line = next((l for l in text.splitlines() if dnb and l.strip() == dnb.player), None)
        if line:
            break
    else:
        pytest.skip("no batter who didn't bat in the test set")
    m = parse_scorecard(text.replace(line, f"{dnb.player:<16}absent hurt", 1), f.name)
    e = entry(m, dnb.player)
    assert (e.how_out, e.did_bat) == ("absent", False) and validate_match(m) == []


def test_a_dismissal_the_site_doesnt_know_raises_the_alarm():
    m = card(LBW, "K Yadav         stood on the stumps       20   9    3   1")
    problems = validate_match(m)
    assert any("is not one the site knows" in p for p in problems), problems


def test_a_line_the_site_doesnt_understand_raises_the_alarm():
    m = card(RUN_OUT, RUN_OUT + "\nA line from a newer version of the game")
    problems = validate_match(m)
    assert any("a line not understood" in p and "newer version" in p for p in problems), problems


def test_every_rare_dismissal_reaches_the_numbers():
    """Read into a career: hit wicket counts as the bowler's wicket, obstructing as the side's wicket only, and
    absent hurt is no innings at all."""
    t = TEXT.replace(LBW, "K Yadav         hit wicket b Bell         20   9    3   1").replace(
        RUN_OUT, "T Head          obstructing the field     3    6    -   -")
    c = Career.build("Odd cases", [(CARD.name, t.encode())])
    bat = c.batting.set_index("player")
    assert bat.loc["K Yadav"].how_out == "hit wicket" and bool(bat.loc["K Yadav"].out)
    assert bat.loc["T Head"].how_out == "obstructing" and bool(bat.loc["T Head"].out)
    assert c.problems.empty
