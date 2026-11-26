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


# --------------------------------------------------------------------------- form alerts
def test_form_alerts_counted_again_by_hand(c):
    """Every hot streak and lean spell said for a team's players matches its innings (or matches) counted by hand,
    and nothing is said twice."""
    from ccstats import alerts as AL
    from ccstats.stats import KIND
    m = c.matches
    teams = sorted(set(m.home) | set(m.away))
    said = 0
    for team in teams:
        out = AL.form_alerts(c, m, [team])
        for key, kind, title, text in out:
            what, p, sec, first = key.split("|")
            k = KIND.get(m[m.section == sec].format.iloc[0], "one")
            order = list(m[m.section == sec].sort_values(["date", "match_id"]).match_id)
            if what in ("formbat", "slumpbat"):
                b = c.batting[c.batting.match_id.isin(order) & (c.batting.player == p) & c.batting.did_bat.astype(bool)]
                b = b.assign(o=b.match_id.map({x: i for i, x in enumerate(order)})).sort_values(["o", "innings_no"])
                mid, no = first.split(":")
                start = (order.index(mid), int(no))
                tail = [r.runs for r in b.itertuples() if (r.o, r.innings_no) >= start]
                n = AL.HOT_RUN if what == "formbat" else AL.SLUMP_RUN
                assert len(tail) >= n
                assert all(r >= AL.HOT_BAT[k] for r in tail) if what == "formbat" else all(r < AL.SLUMP_BAT[k] for r in tail)
            said += 1
        _, seen = AL.check(c, [], [team], [], {})
        first_run, seen2 = AL.check(c, list(m.source), [team], [], dict(seen, said=[]))
        again, _ = AL.check(c, list(m.source), [team], [], seen2)
        assert not [a for a in again if a["title"] in ("Hot streak", "A lean spell")]


def test_form_alerts_on_made_streaks(c):
    """A player given 3 fifties in a row (and another 5 low scores in a row) at the end of a competition: exactly that
    streak is said, with its scores; one short of the run, nothing is."""
    import copy
    from ccstats import alerts as AL
    from ccstats.stats import KIND
    m = c.matches
    bat = c.batting[c.batting.did_bat.astype(bool)].merge(m[["match_id", "section", "date"]], on="match_id")
    counts = bat.groupby(["section", "player", "team"]).size()
    (sec, p, team), n = next((k, v) for k, v in counts.items() if v >= 5)
    k = KIND.get(m[m.section == sec].format.iloc[0], "one")
    rows = bat[(bat.section == sec) & (bat.player == p)].sort_values(["date", "match_id", "innings_no"])
    cc = copy.copy(c)
    cc.batting = c.batting.copy()
    idx = c.batting.index[c.batting.match_id.isin(rows.match_id) & (c.batting.player == p) & c.batting.did_bat.astype(bool)]
    order = rows.set_index(["match_id", "innings_no"]).index
    pos = {key: i for i, key in enumerate(order)}
    ranked = sorted(idx, key=lambda i: pos[(c.batting.match_id[i], c.batting.innings_no[i])])
    for i in ranked[-3:]:
        cc.batting.loc[i, "runs"] = AL.HOT_BAT[k] + 5
    cc.batting.loc[ranked[-4], "runs"] = 0
    out = AL.form_alerts(cc, m[m.section == sec], [team])
    hot = [a for a in out if a[0].startswith("formbat|" + p)]
    assert len(hot) == 1 and f"3 scores of {AL.HOT_BAT[k]}+" in hot[0][3]
    cc.batting.loc[ranked[-3], "runs"] = 0          # now only 2 in a row: nothing
    assert not [a for a in AL.form_alerts(cc, m[m.section == sec], [team]) if a[0].startswith("formbat|" + p)]
    for i in ranked[-5:]:
        cc.batting.loc[i, "runs"] = 1
    low = [a for a in AL.form_alerts(cc, m[m.section == sec], [team]) if a[0].startswith("slumpbat|" + p)]
    assert len(low) == 1 and "5 innings in a row" in low[0][3]


def test_form_alerts_only_for_your_players(c):
    from ccstats import alerts as AL
    assert AL.form_alerts(c, c.matches, ["Nobody FC"]) == []
