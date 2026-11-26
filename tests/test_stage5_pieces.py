"""Stage 5, the new pieces (your answers of 26 November, NEW_SITE_PLAN.md section 22), each counted again by hand."""

from __future__ import annotations

import pytest

from ccstats import breakers as BR
from ccstats import leaders as L
from ccstats.loader import Career
from ccstats.stats import Scope
from serverkit import FIXTURES


@pytest.fixture(scope="module")
def c():
    c = Career.build("t", [(f.name, f.read_bytes()) for f in FIXTURES])
    c.count_fielding = False
    return c


# --------------------------------------------------------------------------- partnership breakers
def test_each_broken_stand_counted_again_by_hand(c):
    """For every stand of 50+ said to be broken: the batter named was out at exactly that wicket (the next stand
    doesn't have him, or it was the last wicket), to the bowler named, and it wasn't a run out."""
    b = BR.broken(c, c.matches.match_id)
    assert len(b) > 10
    bat = c.batting
    fow = c.fow.set_index(["match_id", "innings_no", "wicket"]).score
    from ccstats import partnerships as P
    s = P.stands(c, c.matches.match_id).set_index(["match_id", "innings_no", "wicket"])
    for r in b.itertuples():
        st = s.loc[(r.match_id, r.innings_no, r.wicket)]
        assert r.runs == st.runs >= BR.MIN_STAND and not st.unbroken and r.batter in (st.batter1, st.batter2)
        assert fow[(r.match_id, r.innings_no, r.wicket)] == st.end
        row = bat[(bat.match_id == r.match_id) & (bat.innings_no == r.innings_no) & (bat.player == r.batter)].iloc[0]
        assert row.out and row.bowler == r.bowler and "run out" not in str(row.how_out)
        nxt = (r.match_id, r.innings_no, r.wicket + 1)
        if nxt in s.index and s.loc[nxt].known:
            assert r.batter not in (s.loc[nxt].batter1, s.loc[nxt].batter2)


def test_breakers_table_and_player_line_add_up(c):
    b = BR.broken(c, c.matches.match_id)
    t = BR.table(c, c.matches.match_id)
    assert t.broken.sum() == len(b)
    top = t.iloc[0]
    one = BR.of_player(c, c.matches.match_id, top.bowler)
    assert one["broken"] == len(b[b.bowler == top.bowler])     # (a bowler for two teams adds up across both)
    assert BR.of_player(c, c.matches.match_id, "Nobody At All") == {"broken": 0}


def test_stands_broken_on_stat_by_stat(c):
    sec = c.matches.section.value_counts().index[0]
    board = L.board(c, Scope(sections=[sec]), "Bowling", "stands_broken")
    assert board.stat.id == "stands_broken" and board.measures == ["all"]
    ids = c.matches[c.matches.section == sec].match_id
    counts = BR.broken(c, ids).bowler.value_counts()
    for r in board.table.itertuples():
        assert r.stands_broken == counts.get(r.player, 0)
