"""Guard against boundary / sixes figures being read from the wrong column."""
import re
from pathlib import Path

import pytest

from ccstats.parser import parse_scorecard, validate_match

FIXTURES = sorted((Path(__file__).parent / "fixtures").glob("*.txt"))


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.name)
def test_every_sample_passes_the_self_check(path):
    assert validate_match(parse_scorecard(path.read_text(), path.name)) == []


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.name)
def test_fours_and_sixes_match_their_fixed_columns(path):
    """Read R/B/4s/6s by their column positions under the header and check
    the parser saw exactly the same numbers for every batter."""
    lines = path.read_text().splitlines()
    m = parse_scorecard(path.read_text(), path.name)
    innings = iter(m.innings)
    for i, line in enumerate(lines):
        if not re.search(r" - (1st|2nd) Innings\s+R\s+B\s+4s\s+6s", line):
            continue
        inn = next(innings)
        cols = [line.index(" R ") + 1, line.index(" B ") + 1, line.index("4s"), line.index("6s")]
        rows = []
        for row in lines[i + 2:]:
            if row.startswith("---"):
                break
            if len(row.rstrip()) > cols[0]:
                cells = [row[c:c + 4].strip() or "-" for c in cols]
                rows.append([0 if v == "-" else int(v) for v in cells])
        parsed = [[b.runs, b.balls, b.fours, b.sixes] for b in inn.batting if b.did_bat]
        assert parsed == rows


def test_self_check_catches_a_misread_sixes_column():
    path = FIXTURES[0]
    m = parse_scorecard(path.read_text(), path.name)
    batter = next(b for b in m.innings[0].batting if b.did_bat)
    batter.sixes += 50
    assert any("boundary" in p for p in validate_match(m))
