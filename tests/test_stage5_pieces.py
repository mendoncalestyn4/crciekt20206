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


# --------------------------------------------------------------------------- records within reach
def test_records_within_reach_counted_again_by_hand(c):
    """Every record named is the real record (the team's own or the competition's), held by someone else, the player
    still plays for the team, and he needs no more than one good match to pass it."""
    from ccstats import reach as R
    from ccstats.stats import KIND
    m = c.matches
    seen = 0
    for sec in m.section.unique():
        here = m[m.section == sec]
        teams = sorted(set(here.home) | set(here.away))
        w = R.within(c, sec, teams)
        kind = KIND.get(here.format.iloc[0], "one")
        bat = c.batting[c.batting.match_id.isin(here.match_id) & c.batting.did_bat.astype(bool)]
        bowl = c.bowling[c.bowling.match_id.isin(here.match_id)]
        for r in w.itertuples():
            src = {"runs": bat.groupby(["player", "team"]).runs.sum(), "wickets": bowl.groupby(["player", "team"]).wickets.sum(),
                   "hundreds": bat[bat.runs >= 100].groupby(["player", "team"]).size(),
                   "five-wicket hauls": bowl[bowl.wickets >= 5].groupby(["player", "team"]).size()}[r.unit]
            pool = src.xs(r.whose, level=1) if r.whose else src.groupby(level=0).sum()
            assert pool.max() == r.record_value and pool[r.holder] == r.record_value and r.holder != r.player
            assert pool[r.player] == r.now and r.needed == r.record_value - r.now + 1
            limit = {"runs": R.RUNS[kind], "wickets": R.WICKETS[kind]}.get(r.unit, 1)
            assert 0 < r.needed <= limit
            tm = here[(here.home == r.team) | (here.away == r.team)]
            last = tm[tm.season == tm.season.max()].match_id
            assert r.player in set(c.batting[c.batting.match_id.isin(last) & (c.batting.team == r.team)].player) | \
                set(c.bowling[c.bowling.match_id.isin(last) & (c.bowling.team == r.team)].player)
            seen += 1
    assert seen > 10


def test_preview_in_form_players(tmp_path):
    """The opponent preview's in-form players: at most 3 a side, each playing above their own usual over their last 5,
    the biggest lift first, only current players."""
    import json
    from server.app import create_app
    from serverkit import Live, make_pc
    store, _, _ = make_pc(tmp_path, team="England", files=FIXTURES)
    s = Live(create_app(store, web=tmp_path / "nothing", watch_every=0))
    try:
        d = s.json("/api/preview?section=Internationals&format=ODI")
        form = (d.get("head") or {}).get("form") or []
        assert form and form[-1]["team"] == d["opp"]
        for side in form:
            lifts = [float(r["lift"].rstrip("%")) for r in side["rows"]]
            assert len(lifts) <= 3 and all(x > 0 for x in lifts) and lifts == sorted(lifts, reverse=True)
    finally:
        s.stop()


# --------------------------------------------------------------------------- who's fading
def test_whos_fading_picks_only_clear_drops_of_your_players(c):
    """Only your teams' players, only a clear drop (by format), the biggest drop first; the measure is the breakouts'
    own, so the numbers shown are the ones Breakout players works out."""
    import pandas as pd
    from server import insightspage as IP
    from ccstats.stats import KIND
    sec = "Tests" if "Tests" in set(c.matches.section) else c.matches.section.iloc[0]
    kind = KIND.get(c.matches[c.matches.section == sec].format.iloc[0], "one")
    cut = IP.FADE["bat"][kind]
    bat = pd.DataFrame([dict(player="A Mine", teams="England", now=10.0, before=10.0 + cut + 2, now_innings=6, before_innings=8, jump=-(cut + 2)),
                        dict(player="B Mine", teams="England", now=10.0, before=10.0 + cut - 1, now_innings=6, before_innings=8, jump=-(cut - 1)),
                        dict(player="C Theirs", teams="India", now=1.0, before=30.0, now_innings=6, before_innings=8, jump=-29.0),
                        dict(player="D Mine", teams="Lions / England", now=0.0, before=40.0, now_innings=6, before_innings=8, jump=-40.0)])
    out = IP._fading(c, sec, "2027", bat, pd.DataFrame(), ["England"], 5)
    assert [r["player"] for r in out["rows"]] == ["D Mine", "A Mine"]            # biggest drop first; B not clear; C not yours
    assert out["rows"][0]["team"] == "England" and out["rows"][1]["drop"] == f"{-(cut + 2):+.1f}"
    none = IP._fading(c, sec, "2027", bat, pd.DataFrame(), ["Nobody FC"], 5)
    assert "none" in none and "rows" not in none


# --------------------------------------------------------------------------- selection review
@pytest.fixture(scope="module")
def demo():
    """The made-up IPL (two full seasons): enough matches per team for runs of five."""
    from ccstats.demo_league import generate
    c = Career.build("demo", [(n, t.encode()) for n, t in generate((2026, 2027))])
    c.count_fielding = False
    return c


def _sel_case(c):
    """A team and competition with 7+ matches, and its XIs in order."""
    from ccstats import selection as SEL
    m = c.matches
    for sec in m.section.unique():
        here = m[m.section == sec]
        for team in sorted(set(here.home) | set(here.away)):
            xis = SEL._xis(c, here.match_id, team)
            if len(xis) >= 7:
                return sec, team, xis
    raise AssertionError("no team with 7 matches in a competition")


def test_selection_review_dropped_and_kept_on_made_cases(demo):
    c = demo
    import copy
    from ccstats import selection as SEL
    from ccstats.stats import KIND
    sec, team, xis = _sel_case(c)
    kind = KIND.get(c.matches[c.matches.section == sec].format.iloc[0], "one")
    cc = copy.copy(c)
    cc.batting = c.batting.copy()
    # dropped: a player given a good score in one match and left out of the next (the made-up league keeps one XI,
    # so his line in the next match is taken off the card here)
    i, gone = 2, sorted(xis[2][2] & xis[3][2])[0]
    cc.batting = cc.batting.drop(cc.batting.index[(cc.batting.match_id == xis[3][0]) & (cc.batting.player == gone)])
    rows = cc.batting.index[(cc.batting.match_id == xis[i][0]) & (cc.batting.player == gone) & (cc.batting.team == team)]
    cc.batting.loc[rows[0], ["runs", "did_bat"]] = [SEL.GOOD_RUNS[kind] + 1, True]
    r = SEL.review(cc, team, sec)
    hit = [x for x in r["dropped"] if x["player"] == gone and x["match_id"] == xis[i][0]]
    assert hit and hit[0]["next_id"] == xis[i + 1][0] and f"{SEL.GOOD_RUNS[kind] + 1} runs" in hit[0]["did"]
    cc.batting = c.batting.copy()                                            # back to the real cards for the next case
    # kept: someone in 6 XIs in a row, given 5 low scores, still in the 6th
    for j in range(len(xis) - 5):
        common = set.intersection(*[x[2] for x in xis[j:j + 6]])
        if common:
            p = sorted(common)[0]
            break
    for k in range(j, j + 5):
        idx = cc.batting.index[(cc.batting.match_id == xis[k][0]) & (cc.batting.player == p) & (cc.batting.team == team)]
        cc.batting.loc[idx, ["runs", "did_bat"]] = [1, True]
    r = SEL.review(cc, team, sec)
    kept = [x for x in r["kept"] if x["player"] == p and "innings" in x["did"]]
    assert any("(1, 1, 1, 1, 1)" in x["did"] and x["next_id"] == xis[j + 5][0] for x in kept)


def test_selection_changes_counted_by_hand(demo):
    c = demo
    from ccstats import selection as SEL
    sec, team, xis = _sel_case(c)
    ids = c.matches[c.matches.section == sec].match_id
    by_hand = sum(len(b[2] - a[2]) for a, b in zip(xis, xis[1:])) / (len(xis) - 1)
    assert abs(SEL.changes(c, ids, team) - by_hand) < 1e-9


# --------------------------------------------------------------------------- Stat by stat: against, and by result
def test_stat_by_stat_against_opponents_and_by_result_counted_by_hand(c):
    from ccstats.stats import player_tables
    m = c.matches
    sec = "ODIs" if "ODIs" in set(m.section) else m.section.iloc[0]
    ids = m[m.section == sec].match_id
    here = m[m.match_id.isin(ids)].set_index("match_id")
    bat = c.batting[c.batting.match_id.isin(ids) & c.batting.did_bat.astype(bool)]
    bowl = c.bowling[c.bowling.match_id.isin(ids)]
    opps = sorted(set(bat.opposition))[:2]
    b, w, _, base_all = player_tables(c, Scope(sections=[sec], opponents=opps))
    _, _, _, base = player_tables(c, Scope(sections=[sec]))
    assert base_all.runs_per_innings == base.runs_per_innings          # the average player stays the competition's
    by_hand = bat[bat.opposition.isin(opps)].groupby("player").runs.sum()
    assert dict(zip(b[b.innings > 0].player, b[b.innings > 0].runs)) == {k: int(v) for k, v in by_hand.items()}
    by_hand_w = bowl[bowl.opposition.isin(opps)].groupby("player").wickets.sum()
    got_w = dict(zip(w.player, w.wickets))
    assert all(got_w[k] == int(v) for k, v in by_hand_w.items())
    for result, keep in (("won", lambda r: here.winner[r.match_id] == r.team),
                         ("lost", lambda r: here.loser[r.match_id] == r.team),
                         ("chasing", lambda r: bool(here.batted_first[r.match_id]) and here.batted_first[r.match_id] != r.team)):
        b, _, _, _ = player_tables(c, Scope(sections=[sec], result=result))
        want = bat[[keep(r) for r in bat.itertuples()]].groupby("player").runs.sum()
        assert dict(zip(b[b.innings > 0].player, b[b.innings > 0].runs)) == {k: int(v) for k, v in want.items()}, result
