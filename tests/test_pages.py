"""Stage 1's pages from the stats server: the Player page (server/playerpage.py), the demo of attributes, the scout
report, squad depth and the inbox (ccstats/attributes.py, ccstats/depth.py, server/demo.py), and every endpoint
asked the way the website asks, on the test scorecards."""

import json

import numpy as np
import pandas as pd
import pytest

from ccstats import attributes as AT
from ccstats import depth as DP
from ccstats import playerdeep as PD
from ccstats.loader import Career
from server import playerpage as PP
from server.app import create_app
from serverkit import FIXTURES, Live, make_pc


@pytest.fixture(scope="module")
def career():
    return Career.build("Test career", [(f.name, f.read_bytes()) for f in FIXTURES])


def players_by_matches(c, n):
    b = c.batting.groupby("player").match_id.nunique().sort_values(ascending=False)
    return list(b.index[:n])


# ------------------------------------------------------------------ the Player page
def test_every_format_side_by_side_agrees_with_the_engine(career):
    """The page's copy (on the tables kept with the career) gives what ccstats.playerdeep.all_formats gives."""
    for p in players_by_matches(career, 12):
        mine, theirs = PP.all_formats(career, p), PD.all_formats(career, p)
        pd.testing.assert_frame_equal(mine.reset_index(drop=True), theirs.reset_index(drop=True), check_dtype=False)


def test_the_form_line_as_the_current_site_draws_it():
    """Nothing until a full window; 5 innings for a career under 20, 10 from 20; runs over dismissals."""
    f = PP._form([10, 20, 30, 40, 50, 60], [1, 1, 0, 1, 1, 1])
    assert f["window"] == 5 and f["rolling"][:4] == [None] * 4
    assert f["rolling"][4] == pytest.approx(150 / 4) and f["rolling"][5] == pytest.approx(200 / 4)
    assert f["overall"] == pytest.approx(210 / 5)
    assert PP._form(range(20), [1] * 20)["window"] == 10
    w = PP._form([1, 2, 0, 3, 4], None)   # wickets: the mean an innings
    assert w["rolling"][4] == pytest.approx(2.0) and w["overall"] == pytest.approx(2.0)


def test_every_player_has_a_whole_page(career):
    """No part missing for anyone, in their main competition and in every other; the same table columns everywhere."""
    names = sorted(set(career.batting.player) | set(career.bowling.player))
    cols = None
    for p in names[::3]:
        d = PP.page(career, p)
        json.dumps(d)
        assert d["missing"] == {}, (p, d["missing"])
        assert d["tabs"][-1] == "Story" and "Fielding" in d["tabs"]
        if d["bat_table"]:
            cols = cols or d["bat_table"]["cols"]
            assert d["bat_table"]["cols"] == cols
        for sec in d["sections"][1:2]:
            assert PP.page(career, p, sec)["missing"] == {}
    with pytest.raises(KeyError):
        PP.page(career, "Nobody At All")


def test_the_card_and_the_tables_agree(career):
    """The career card's runs and wickets are the sums of the table at the top."""
    for p in players_by_matches(career, 6):
        d = PP.page(career, p)
        runs = sum(int(r["Runs"]) for r in d["bat_table"]["rows"]) if d["bat_table"] else 0
        wkts = sum(int(r["Wkts"]) for r in d["bowl_table"]["rows"]) if d["bowl_table"] else 0
        assert (d["card"]["runs"], d["card"]["wickets"]) == (runs, wkts)


# ------------------------------------------------------------------ attributes and the scout report
def busiest(career) -> str:
    """The competition with the most batters who have enough innings to be rated."""
    return max(career.matches.section.unique(), key=lambda s: len(AT.table(career, s)["bat"]))


def test_attributes_rank_within_the_competition(career):
    """1-20 by rank among the qualified players there: the best average gets 20, the worst 1; a short record is
    settled, so it can't top the list on a handful of innings."""
    sec = busiest(career)
    t = AT.table(career, sec)
    bt = t["bat"]
    assert len(bt) >= 5
    assert bt["Run-scoring"].max() == 20 and bt["Run-scoring"].min() >= 1
    assert bt.loc[bt.average.idxmax(), "Run-scoring"] == 20
    assert (bt.innings >= AT.ENOUGH_INNS[t["kind"]]).all()
    assert bt["Big scores"].isna().equals(bt.decent < AT.MIN_STARTS)


def test_a_scout_report_reads_from_the_attributes(career):
    sec = busiest(career)
    t = AT.table(career, sec)
    p = t["bat"].overall.idxmax()
    r = AT.scout_report(career, sec, p)
    assert r["verdict"] and r["strengths"] and all("/20)" in x for x in r["strengths"])
    a = AT.player(career, sec, p)
    assert all(x["score"] is None or 1 <= x["score"] <= 20 for x in a["bat"] + a["bowl"])
    assert AT.scout_report(career, sec, "Nobody At All")["none"]
    # a competition where nobody has enough cricket yet: no attributes, a report that says so
    empty = min(career.matches.section.unique(), key=lambda s: len(AT.table(career, s)["bat"]))
    if AT.table(career, empty)["bat"].empty:
        anyone = career.batting[career.batting.match_id.isin(career.matches[career.matches.section == empty].match_id)].player.iloc[0]
        assert AT.player(career, empty, anyone)["bat"] == [] and AT.scout_report(career, empty, anyone)["none"]


# ------------------------------------------------------------------ squad depth and the inbox
def test_squad_depth_puts_everyone_once(career):
    from ccstats import scouting as SC
    for team in career.matches.home.value_counts().index[:6]:
        for sec in career.matches[(career.matches.home == team) | (career.matches.away == team)].section.unique():
            d = DP.squad_depth(career, team, sec)
            names = [p["player"] for r in d["roles"] for p in r["starters"] + r["backups"]]
            assert len(names) == len(set(names))
            starters = {p["player"] for r in d["roles"] for p in r["starters"]}
            assert starters == SC._latest_side(career, team, sec)[1], (team, sec)   # everyone in the side, tail too


def test_the_inbox_is_newest_first_with_a_result_for_every_series(career):
    team = career.matches.home.value_counts().index[0]
    msgs = DP.inbox(career, team)
    assert msgs
    assert [m["date"] for m in msgs] == sorted((m["date"] for m in msgs), reverse=True)
    from ccstats.marks import team_report
    assert sum(m["kind"] == "result" for m in msgs) == min(8, len(team_report(career, team)))


# ------------------------------------------------------------------ asked the way the website asks
@pytest.fixture(scope="module")
def live(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("pages")
    pc = make_pc(tmp)
    web = tmp / "dist"
    (web / "assets").mkdir(parents=True)
    (web / "index.html").write_text("<!doctype html><title>Stats Pack</title><div id=root></div>")
    s = Live(create_app(pc[0], web=web, watch_every=0))
    yield s
    s.stop()


def test_the_pages_answer(live):
    landing = live.json("/api/players")
    assert landing["players"] and {"player", "team", "teams", "matches", "sections"} <= set(landing["players"][0])
    p = landing["players"][0]["player"]
    page = live.json(f"/api/player?name={p}")
    assert page["player"] == p and page["missing"] == {}
    status, _, body = live.get("/api/player?name=Nobody At All")
    assert status == 404 and b"hasn't batted or bowled" in body
    team = live.json("/api/myteam")["team"]
    demo = live.json(f"/api/demo?team={team}&players={p}")
    assert demo["missing"] == {} and demo["inbox"] is not None and demo["players"][0]["player"] == p
    assert live.get("/api/demo?team=Nowhere FC")[0] == 404


def test_a_tournament_in_the_inbox_counts_only_the_team_s_games():
    """A tournament holds everyone's games: A won one and lost one; B v C is not A's."""
    from fakecareer import Book
    b = Book()
    games = [("g1", "2026-04-01", "A", "B", "A"), ("g2", "2026-04-03", "B", "C", "C"), ("g3", "2026-04-05", "A", "C", "C")]
    for mid, date, home, away, winner in games:
        b.match(mid, date, home, away, section="T20 Cup", fmt="T20", level="Domestic", country="X", event="T20 Cup",
                season="2026", winner=winner)
        b.inns(mid, 1, home, away, [(f"{home}1", 40, 30, True), (f"{home}2", 20, 20, True)])
        b.bowl(mid, 1, away, home, [(f"{away}9", 24, 30, 2)])
        b.inns(mid, 2, away, home, [(f"{away}1", 30, 25, True)])
        b.bowl(mid, 2, home, away, [(f"{home}9", 24, 30, 1)])
    msgs = [m for m in DP.inbox(b.career(), "A") if m["kind"] == "result"]
    assert len(msgs) == 1
    assert msgs[0]["title"].endswith(": 1 won, 1 lost") and not msgs[0]["title"].startswith("Series")
    assert msgs[0]["match"] == "g3"   # A's last game, not the tournament's


def test_the_inbox_reads_and_removes_and_remembers(live):
    """Messages have ids; marking one read and removing another is saved with the career (a fresh look still knows)."""
    box = live.json("/api/inbox")
    assert box["messages"] and box["unread"] == len(box["messages"])
    a, b = box["messages"][0]["id"], box["messages"][1]["id"]
    st, _, body = live.post("/api/inbox", {"read": [a], "remove": [b]})
    assert st == 200
    after = json.loads(body)
    ids = {m["id"]: m for m in after["messages"]}
    assert ids[a]["read"] and b not in ids and after["unread"] == box["unread"] - 2
    again = live.json("/api/inbox")                       # read again from the saved settings
    assert {m["id"] for m in again["messages"]} == set(ids) and again["unread"] == after["unread"]
    assert live.post("/api/inbox", {"read": "everything"})[0] == 400


def test_my_team_has_its_squad_depth(live):
    d = live.json("/api/myteam")
    assert d["missing"] == {} and d["depth"]["section"] == d["block"]["section"]
