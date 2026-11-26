"""One match at a time (stage 5, kept for good): a career built up one scorecard at a time, as the game saves them,
ends exactly equal to the same scorecards read all at once: every table (matches, innings, batting, bowling, fall of
wickets, the checks and the cards put right, the names kept apart or joined) and every player's numbers in every
competition. Tried in the order played (every run) and in the reverse order (the weekly run)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from ccstats.loader import Career
from ccstats.stats import Scope, player_tables

HERE = Path(__file__).parent
FILES = sorted({f.name: f for d in ("fixtures", "fixtures_declare", "fixtures_rain", "fixtures_super", "fixtures_names")
                for f in (HERE / d).glob("*.txt")}.values())
TABLES = ["matches", "innings", "batting", "bowling", "fow", "problems", "corrections", "guesses", "auto_splits",
          "auto_joins", "leftovers"]


def same(a: pd.DataFrame, b: pd.DataFrame, name: str) -> None:
    cols = list(a.columns)
    assert cols == list(b.columns), name
    key = [c for c in cols if a[c].map(lambda v: isinstance(v, (str, int, float, bool)) or pd.isna(v)).all()]
    sa = a.sort_values(key).reset_index(drop=True) if key else a.reset_index(drop=True)
    sb = b.sort_values(key).reset_index(drop=True) if key else b.reset_index(drop=True)
    pd.testing.assert_frame_equal(sa, sb, check_dtype=False, obj=name)


@pytest.fixture(scope="module")
def whole():
    return Career.build("all", [(f.name, f.read_bytes()) for f in FILES])


@pytest.mark.parametrize("order", ["as played", pytest.param("reversed", marks=pytest.mark.weekly)])
def test_one_at_a_time_equals_all_at_once(whole, order):
    files = FILES if order == "as played" else FILES[::-1]
    c = Career.build("all", [])
    for f in files:
        c = c.add_files([(f.name, f.read_bytes())])
    for name in TABLES:
        same(getattr(c, name), getattr(whole, name), name)
    for sec in sorted(set(whole.matches.section)):
        for x, y, what in zip(player_tables(c, Scope(sections=[sec]))[:2], player_tables(whole, Scope(sections=[sec]))[:2],
                              ("batting", "bowling")):
            same(x, y, f"{sec} {what}")
