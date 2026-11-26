"""Stage 4, Data check (your answers 15-18 of 26 November): six tabs; names shared by different players split by
themselves and each split undoable; names joined only by your click, never in the same match; games left out and
counted back; the scorecards' checks and corrections; copies; your changes each undoable; the fix preview counted
again by hand; a backup before every change; the change made in the background with the site usable; the line on My
team only when something needs you. No name is ever joined without your saved choice."""

from __future__ import annotations

import json
import time

import pytest

from ccstats import datacheck as DC
from ccstats.loader import Career
from server import datacheckpage as DP
from server.app import create_app
from serverkit import FIXTURES, Live, make_pc


@pytest.fixture(scope="module")
def career():
    c = Career.build("Test career", [(f.name, f.read_bytes()) for f in FIXTURES])
    c.count_fielding = False
    return c


@pytest.fixture
def pc(tmp_path):
    store, folder, game = make_pc(tmp_path, n=len(FIXTURES), team="England")
    s = Live(create_app(store, web=tmp_path / "nothing", watch_every=0))
    yield s, store
    s.stop()


def wait_done(s, timeout=120):
    for _ in range(timeout * 10):
        st = s.json("/api/datacheck")["state"]
        if not st["busy"]:
            return st
        time.sleep(0.1)
    raise AssertionError("the change never finished")


def test_every_tab(pc, career):
    s, _ = pc
    for tab in DP.TABS:
        d = s.json(f"/api/datacheck?tab={tab}")
        assert d["tabs"] == DP.TABS and d["tab"] == tab and json.dumps(d["body"])
    sm = DC.summary(career)
    assert set(sm["counts"]) == set(DP.TABS) and "Team catches" not in json.dumps(sm)


def test_preview_counted_again(career):
    bat, bowl = career.batting, career.bowling
    p = bat.groupby("player").match_id.nunique().idxmax()
    teams = DC.teams_of(career, p)
    t = teams[0]
    pv = DC.preview(career, "split", dict(player=p, team=t, new_name=f"{p} ({t})"))
    whole = pv["before"][0]
    assert whole["runs"] == int(bat[bat.player == p].runs.sum()) and whole["wickets"] == int(bowl[bowl.player == p].wickets.sum())
    assert sum(x["runs"] for x in pv["after"]) == whole["runs"] and sum(x["wickets"] for x in pv["after"]) == whole["wickets"]
    there = pv["after"][1]
    assert there["runs"] == int(bat[(bat.player == p) & (bat.team == t)].runs.sum())
    # a join: the two names' numbers added up
    names = DC.players(career)
    a, b = names[0], names[1]
    pj = DC.preview(career, "join", dict(name=a, keep=b))
    assert pj["after"][0]["runs"] == pj["before"][0]["runs"] + pj["before"][1]["runs"]


def test_never_joined_in_the_same_match(career):
    m = career.batting[career.batting.match_id == career.batting.match_id.iloc[0]]
    a, b = m.player.iloc[0], m.player.iloc[1]
    with pytest.raises(DC.Refused, match="same match"):
        DC.change(career, "join", dict(name=a, keep=b))


def test_a_change_needs_your_click_makes_a_backup_and_can_be_undone(pc):
    s, store = pc
    c, _ = store.load("My career")
    assert c.fixes.merges == {}   # nothing joined by itself
    p = c.batting.groupby("player").match_id.nunique().idxmax()
    t = DC.teams_of(c, p)[0]
    status, _, body = s.post("/api/datacheck", dict(action="split", player=p, team=t, new_name=f"{p} (test)", preview=True))
    assert status == 200 and json.loads(body)["preview"]["after"]
    assert store.load("My career")[0].fixes.splits == []          # a preview changes nothing
    status, _, body = s.post("/api/datacheck", dict(action="split", player=p, team=t, new_name=f"{p} (test)"))
    assert status == 200 and json.loads(body)["started"]
    st = wait_done(s)
    assert not st["error"] and st["done"].startswith("Done")
    c2, _ = store.load("My career")
    assert {"player": p, "team": t, "new_name": f"{p} (test)"} in c2.fixes.splits
    assert f"{p} (test)" in set(c2.batting.player)
    assert any("before-data-check" in f.name for f, _ in store.backups("My career"))
    # undone from Your changes
    ch = s.json("/api/datacheck?tab=Your changes")["body"]["changes"]
    sp = next(x for x in ch if x["kind"] == "split")
    s.post("/api/datacheck", dict(action="undo", kind="split", key=sp["key"]))
    wait_done(s)
    assert store.load("My career")[0].fixes.splits == []


def test_leave_out_and_count_back(pc):
    s, store = pc
    c, _ = store.load("My career")
    mid = c.matches.match_id.iloc[0]
    n = len(c.matches)
    s.post("/api/datacheck", dict(action="leave_out", match_id=mid))
    wait_done(s)
    c2, _ = store.load("My career")
    assert len(c2.matches) == n - 1 and mid in c2.fixes.exclude
    assert any(x["match_id"] == mid for x in s.json("/api/datacheck?tab=Games left out")["body"]["left"])
    s.post("/api/datacheck", dict(action="count_it", match_id=mid))
    wait_done(s)
    assert len(store.load("My career")[0].matches) == n


def test_shared_name_split_by_itself_undone_and_split_again(tmp_path):
    """Two different players printed the same way, for two teams in one competition and season: kept apart by
    themselves; undoing it keeps them as one (your choice, saved); splitting again puts it back."""
    from ccstats import demo_league as DL
    files = DL.generate((2026,))
    c = Career.build("Demo", [(n, t.encode() if isinstance(t, str) else t) for n, t in files])
    if c.auto_splits.empty:
        pytest.skip("the demo league has no shared name")
    p = c.auto_splits.player.iloc[0]
    f, msg = DC.change(c, "undo_auto_split", dict(player=p))
    assert p in f.keep_together
    c2 = c.with_fixes(f)
    assert p not in set(c2.auto_splits.player)
    f2, _ = DC.change(c2, "resplit", dict(player=p))
    assert p not in f2.keep_together


def test_my_team_line_only_when_something_needs_you(pc):
    s, store = pc
    d = s.json("/api/myteam")
    c, _ = store.load("My career")
    sm = DC.summary(c)
    assert (len(d["datacheck"]) > 0) == (sm["needs_you"] > 0)


def test_odd_input_refused(pc):
    s, _ = pc
    for b in (dict(action="join", name="Nobody", keep="Else"), dict(action="leave_out", match_id="nope"),
              dict(action="split", player="Nobody", team="X", new_name="Y"), dict(action="what")):
        status, _, _ = s.post("/api/datacheck", b)
        assert status == 400
