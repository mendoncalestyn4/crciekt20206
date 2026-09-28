"""End-to-end audit.

1. Round trip: every scorecard is rebuilt, line by line, from what the parser
   understood and compared with the original file.  Every name, dismissal,
   run, ball, four, six, extra, total, over, maiden/dot, economy, fall of
   wicket, result and man of the match has to come back exactly.
2. Results: every margin ("won by 7 wickets", "by 80 runs") must follow from
   the innings totals.
3. Hand-checked players: figures worked out by hand from the files.
"""

import re
from pathlib import Path

import pytest

from ccstats.loader import Career
from ccstats.parser import Match, parse_scorecard
from ccstats.stats import Scope, player_tables

FIXTURES = sorted((Path(__file__).parent / "fixtures").glob("*.txt"))
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def overs(balls):
    return f"{balls // 6}" if balls % 6 == 0 else f"{balls // 6}.{balls % 6}"


def cell(v):
    return str(v) if v else "-"


def rebuild(m: Match) -> list[str]:
    """Write the scorecard back out from the parsed data."""
    d = m.date
    title = m.title
    lines = [f"{m.team1} v {m.team2}", f"{title} - {d.day} {MONTHS[d.month - 1]} {d.year}"]
    for inn in sorted(m.innings, key=lambda i: i.listed):  # file order, not batting order
        lines.append(f"{inn.team} - {'1st' if inn.team_innings == 1 else '2nd'} Innings R B 4s 6s")
        for b in inn.batting:
            if b.did_bat or b.how_out not in ("dnb",):
                lines.append(f"{b.player} {b.dismissal} {b.runs} {b.balls} {cell(b.fours)} {cell(b.sixes)}")
            else:
                lines.append(b.player)
        parts = [f"{k}{v}" for k, v in (("nb", inn.no_balls), ("w", inn.wides), ("b", inn.byes), ("lb", inn.leg_byes)) if v]
        lines.append(f"Extras: ({','.join(parts)}) {inn.extras}" if parts else f"Extras: {inn.extras}")
        wk = "all out" if inn.all_out else f"{inn.wickets} wkts"
        unit = f"{inn.balls} balls" if inn.counted_in_balls else f"{overs(inn.balls)} overs"
        lines.append(f"TOTAL: ({wk}, {unit}) {inn.total}")
        first = "B" if inn.counted_in_balls else "O"
        second = "D" if any(w.dots is not None for w in inn.bowling) else "M"
        lines.append(f"{first} {second} R W Econ")
        for w in inn.bowling:
            # economy is compared separately (see _econ_ok): the game's own printed figure
            # is sometimes cut and sometimes rounded; The Hundred shows runs per 5 balls
            econ = f"ECON:{w.runs / w.balls * (5 if inn.counted_in_balls else 6):.6f}"
            amount = w.balls if inn.counted_in_balls else overs(w.balls)
            lines.append(f"{w.player} {amount} {w.dots if second == 'D' else w.maidens} {w.runs} {w.wickets} {econ}")
        lines.append("Fall of Wickets:")
        fow = [f"{wk}-{sc}" for wk, sc in inn.fow]
        for i in range(0, len(fow), 5):
            lines.append(" ".join(fow[i:i + 5]))
    lines.append(m.result)
    lines.append(f"Man of the match: {m.player_of_match}")
    return lines


def original(path: Path) -> list[str]:
    out = []
    for line in path.read_text().splitlines():
        s = re.sub(r"\s+", " ", line).strip()
        if not s or set(s) <= set("*- "):
            continue
        out.append(s)
    return out


def _econ_ok(mine: str, theirs: str) -> bool:
    """Same line apart from the printed economy, which may differ from the exact value by up to 0.01."""
    if " ECON:" not in mine:
        return mine == theirs
    a, b = mine.rsplit(" ", 1), theirs.rsplit(" ", 1)
    try:
        return a[0] == b[0] and abs(float(a[1][5:]) - float(b[1])) <= 0.0101
    except ValueError:
        return False


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.name)
def test_every_line_of_every_scorecard_is_understood(path):
    m = parse_scorecard(path.read_text(), path.name)
    mine, theirs = rebuild(m), original(path)
    assert len(mine) == len(theirs)
    bad = [(x, y) for x, y in zip(mine, theirs) if not _econ_ok(x, y)]
    assert bad == []


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.name)
def test_result_margins_follow_from_the_scores(path):
    m = parse_scorecard(path.read_text(), path.name)
    if m.result_type != "win" or (m.margin_runs is None and m.margin_wickets is None):
        return
    agg = {}
    for inn in m.innings:
        agg[inn.team] = agg.get(inn.team, 0) + inn.total
    loser = m.team2 if m.winner == m.team1 else m.team1
    last = m.innings[-1]
    if m.margin_wickets is not None:
        assert last.team == m.winner  # won by wickets = won batting last
        assert m.margin_wickets == 10 - last.wickets
        assert agg[m.winner] > agg[loser]
    else:
        assert agg[m.winner] - agg[loser] == m.margin_runs


@pytest.fixture(scope="module")
def career():
    return Career.build("audit", [(p.name, p.read_bytes()) for p in FIXTURES])


def test_hand_checked_test_batter(career):
    # J Bethell in the three England v Pakistan Tests: 3 & 119, 28 & dnb, 96 & 8*
    bat, _, _, _ = player_tables(career, Scope(sections=["Tests (bilateral series)"]))
    b = bat.set_index("player").loc["J Bethell"]
    assert (b.matches, b.innings, b.not_outs, b.runs, b.balls, b.hundreds, b.fifties, b.fours, b.sixes) == \
        (3, 5, 1, 254, 401, 1, 1, 29, 1)
    assert b.high_score_text == "119" and b.average == 63.5 and round(b.strike_rate, 2) == 63.34


def test_hand_checked_test_bowler(career):
    # J Archer: 8-1-19-3, 11.3-1-22-1, 24-6-73-6, 12-0-41-1, 9-1-47-2, 18.5-4-48-2
    _, bowl, _, _ = player_tables(career, Scope(sections=["Tests (bilateral series)"]))
    w = bowl.set_index("player").loc["J Archer"]
    assert (w.innings, w.balls, w.runs, w.wickets, w.maidens, w.best, w.best_match, w.hauls, w.five_fors) == \
        (6, 500, 250, 15, 13, "6/73", "7/114", 1, 1)
    assert round(w.average, 2) == 16.67 and round(w.economy, 2) == 3.0 and round(w.strike_rate, 2) == 33.33


def test_hand_checked_hundred_bowler(career):
    # The Hundred counts balls: R Ahmed bowled 12 balls for 19 in Birmingham Phoenix v Welsh Fire
    _, bowl, _, _ = player_tables(career, Scope(sections=["The Hundred"]))
    w = bowl.set_index("player").loc["R Ahmed"]
    assert (w.balls, w.runs, w.wickets, w.dots) == (12, 19, 0, 3)


def test_hand_checked_team_record(career):
    m = career.matches
    eng = m[(m.section == "Tests (bilateral series)") & ((m.home == "England") | (m.away == "England"))]
    assert len(eng) == 3 and (eng.winner == "England").all()
    assert eng.series_id.nunique() == 1  # one 3-match series, England won 3-0


def test_follow_on_is_put_in_batting_order():
    """3rd Test: England 347, Pakistan 123 and (following on) 282, England 59/6 won by 4 wickets.
    The file lists England's second innings before Pakistan's."""
    path = Path(__file__).parent / "fixtures" / "9_sep_2026-eng_v_pak_3rd_tst.txt"
    m = parse_scorecard(path.read_text(), path.name)
    assert [(i.team, i.total) for i in m.innings] == [("England", 347), ("Pakistan", 123), ("Pakistan", 282), ("England", 59)]
    assert m.innings[2].follow_on and [i.number for i in m.innings] == [1, 2, 3, 4]


def test_follow_on_chase_is_not_a_declaration(career):
    inn = career.innings.merge(career.matches[["match_id", "source"]])
    chase = inn[(inn.source == "9_sep_2026-eng_v_pak_3rd_tst.txt") & (inn.team == "England") & (inn.team_innings == 2)].iloc[0]
    assert chase.innings_no == 4 and not chase.declared


def test_misprinted_margin_is_corrected_from_the_scores():
    path = Path(__file__).parent / "fixtures" / "16_jul_2026-eng_v_ind_2nd_odi.txt"
    m = parse_scorecard(path.read_text(), path.name)
    assert m.result == "India won by 127 runs"  # what the game printed
    assert m.margin_runs == 177  # 377 - 200
    assert "127" in m.margin_note
