"""Every scorecard read back (your pick of 14 November): written out again from what the site understood and compared
line by line with the card as printed; any difference is flagged. Clean on every test card, and each kind of misreading
shown being caught (even one whose sums still add up)."""

import copy
from pathlib import Path

import pytest

from ccstats.parser import parse_scorecard
from ccstats.readback import read_back

HERE = Path(__file__).parent
FILES = sorted(f for d in HERE.glob("fixtures*") if d.is_dir() for f in d.glob("*.txt"))
TEST = HERE / "fixtures" / "19_aug_2026-eng_v_pak_1st_tst.txt"
T20 = HERE / "fixtures" / "31_may_2026-gjt_v_pnj_ipl_-_f.txt"


def _card(f):
    t = f.read_text(errors="replace")
    return t, parse_scorecard(t, f.name)


def test_every_test_card_reads_back_the_same():
    bad = {}
    for f in FILES:
        try:
            t, m = _card(f)
        except Exception:  # noqa: BLE001 - the junk files on purpose
            continue
        if read_back(t, m):
            bad[f.name] = read_back(t, m)
    assert bad == {}


@pytest.mark.parametrize("change,says", [
    (lambda m: setattr(m.innings[0].batting[0], "fours", m.innings[0].batting[0].fours + 1), "read back as"),
    (lambda m: setattr(m.innings[0].batting[2], "runs", m.innings[0].batting[2].runs + 4), "read back as"),
    (lambda m: m.innings[0].batting.pop(), "batting lines printed"),
    (lambda m: setattr(m.innings[0], "extras", m.innings[0].extras + 1), "extras printed"),
    (lambda m: setattr(m.innings[1], "total", m.innings[1].total + 1), "total printed"),
    (lambda m: setattr(m.innings[0].bowling[0], "maidens", (m.innings[0].bowling[0].maidens or 0) + 1), "read back as"),
    (lambda m: setattr(m.innings[0].bowling[1], "balls", m.innings[0].bowling[1].balls + 6), "read back as"),
    (lambda m: m.innings[0].fow.__setitem__(2, (3, m.innings[0].fow[2][1] + 1)), "fall of wickets printed"),
    (lambda m: setattr(m, "player_of_match", "J Root"), "player of the match"),
    (lambda m: setattr(m, "result", "England won by 300 runs"), "the result"),
])
def test_each_kind_of_misreading_is_caught(change, says):
    t, m = _card(TEST)
    m = copy.deepcopy(m)
    change(m)
    assert any(says in d for d in read_back(t, m)), read_back(t, m)


def test_a_swap_whose_sums_still_add_up_is_caught():
    """4s and 6s swapped for a batter with as many of each: no sum breaks, but the read-back sees it."""
    t, m = _card(T20)
    b = next(b for i in m.innings for b in i.batting if b.fours != b.sixes and b.did_bat)
    b.fours, b.sixes = b.sixes, b.fours
    assert any("read back as" in d for d in read_back(t, m))


def test_t20_dot_balls_are_compared():
    t, m = _card(T20)
    w = next(w for i in m.innings for w in i.bowling if w.dots is not None)
    w.dots += 1
    assert any("read back as" in d for d in read_back(t, m))


def test_a_read_back_difference_is_a_problem_on_the_match():
    """Read into a career, every card is read back as it arrives (new ones too); a difference is one of the match's
    problems, so it loses its checked mark until it's put right."""
    from ccstats.loader import Career
    from ccstats.parser import validate_match
    c = Career.build("Read back", [(TEST.name, TEST.read_bytes())])
    assert c.problems.empty
    t, m = _card(TEST)
    m.read_back = ['England innings 1: "B Duckett lbw b Khan 85 161 8 -" read back as "B Duckett lbw b Khan 85 161 9 0"']
    assert any(p.startswith("read back: England innings 1") for p in validate_match(m))


ODI = HERE / "fixtures" / "16_jul_2026-eng_v_ind_2nd_odi.txt"


def test_a_long_team_name_with_no_gap_before_the_columns_reads_back_the_same():
    """A team name long enough leaves no gap: "Nugegoda Sports Welfare Club - 1st InningsR    B    4s  6s" (your
    save's Sri Lankan, Trinidad and Major League sides, 50 cards wrongly flagged on 27 November). The reader always
    read it; the read-back now finds the innings too."""
    t = ODI.read_text().replace("India", "Nugegoda Sports Welfare Club")
    t = "\n".join("Nugegoda Sports Welfare Club - 1st InningsR    B    4s  6s" if l.startswith("Nugegoda Sports Welfare Club - 1st")
                  else l for l in t.split("\n"))
    assert "1st InningsR" in t
    m = parse_scorecard(t, ODI.name)
    assert len(m.innings) == 2
    assert read_back(t, m) == []


def test_figures_put_right_by_the_fair_guess_are_not_reported_again_as_a_misreading():
    """A card whose bowlers were charged a run fewer than the innings conceded: the fair guess shares it out and is
    listed on its own; the read-back compares the card with what was read before the guess, so it isn't reported a
    second time as a misreading (two of your save's cards, 27 November)."""
    from ccstats.loader import Career
    t = ODI.read_text().replace("J Archer        10     0     44     1     4.40",
                                "J Archer        10     0     43     1     4.30")
    c = Career.build("guessed", [(ODI.name, t.encode())])
    assert len(c.guesses) == 1 and "1 run no bowler was charged with" in c.guesses.guess.iloc[0]
    assert c.problems.empty, c.problems.problem.tolist()
