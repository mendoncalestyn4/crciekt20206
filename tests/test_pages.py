"""Stage 1's pages from the stats server: the Player page (server/playerpage.py), the demo of attributes, the scout
report, squad depth and the inbox (ccstats/attributes.py, ccstats/depth.py, server/demo.py), and every endpoint
asked the way the website asks, on the test scorecards."""

import json

import numpy as np
import pandas as pd
import pytest

from ccstats import analysis as A
from ccstats import attributes as AT
from ccstats import catalogue as CAT
from ccstats import depth as DP
from ccstats import playerdeep as PD
from ccstats.loader import Career
from ccstats.stats import Scope, player_tables
from server import playerpage as PP
from server import teampage as TPG
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


def test_the_best_format_goes_by_what_they_are_picked_for():
    """A batter's few part-time wickets never make their best format (Gill's 6 ODI wickets at +164% once beat his IPL
    batting at +112%); a bowler is judged on bowling, an all-rounder (or anyone with no role yet) on the better."""
    assert [PD.judged_on(r) for r in ("Opener", "Middle order", "Tail", "Bowler", "All-rounder", None, "")] == \
        ["bat", "bat", "bat", "bowl", "both", "both", "both"]
    assert PD.format_score("bat", 65.0, 53, 164.0, 6) == (65.0, "bat")
    assert PD.format_score("bowl", 65.0, 53, 164.0, 6) == (164.0, "bowl")
    assert PD.format_score("both", 65.0, 53, 164.0, 6) == (164.0, "bowl")
    assert PD.format_score("both", 30.0, 10, 30.0, 9) == (30.0, "bat")        # level: batting
    # too little behind a side: batting needs 3 matches, bowling 5 wickets
    assert PD.format_score("both", 80.0, 2, 20.0, 5) == (20.0, "bowl")
    s, side = PD.format_score("bowl", 50.0, 20, 90.0, 4)
    assert np.isnan(s) and side == ""
    s, side = PD.format_score("bat", float("nan"), 12, 10.0, 8)               # never out: no batting average
    assert np.isnan(s) and side == ""


def test_the_best_format_line_in_words():
    row = lambda s, judged: pd.Series(dict(section="IPL", score=s, judged=judged))   # noqa: E731
    assert PP._best_format_line(row(112.4, "bat")) == ("Best format: IPL, where they are 112% better than the average "
                                                       "batter (judged on what they're picked for).")
    assert "46% worse than the average bowler" in PP._best_format_line(row(-46.2, "bowl"))   # never "-46% better"
    assert "level with the average batter" in PP._best_format_line(row(0.3, "bat"))


def test_the_best_format_is_judged_on_each_players_role_there(career):
    """On the test scorecards: every row's job comes from the player's role in that competition, and the star sits on
    the highest score of the side they're judged on."""
    seen = set()
    for p in players_by_matches(career, 20):
        d = PD.all_formats(career, p)
        for r in d.itertuples():
            assert r.job == PD.judged_on(PD.roles_in(career, r.section).get(p))
            assert r.judged in ({"bat", "bowl"} if r.job == "both" else {r.job}) or (r.judged == "" and np.isnan(r.score))
            seen.add(r.job)
        if d.score.notna().any():
            assert list(d.best).count(True) >= 1 and d[d.best].score.iloc[0] == d.score.max()
    assert {"bat", "bowl"} <= seen


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


def test_the_innings_tiles_add_up_to_the_competition_record(career):
    """Innings by innings (ccstats/byinnings.py): every slot together is the player's whole record in that competition,
    for batting and bowling, in every format."""
    kinds = set()
    for p in players_by_matches(career, 12):
        for sec in PP.page(career, p)["sections"][:3]:
            d = PP.page(career, p, sec)
            bt, wt, _, base = PP.tables(career, sec, "")
            if d["bat_innings"]:
                kinds.add(d["bat_innings"]["kind"])
                me = bt[bt.player == p].iloc[0]
                n = d["bat_innings"]["views"][0]
                assert (n["total"]["runs"], n["total"]["innings"]) == (int(me.runs), int(me.innings))
                assert sum(r["innings"] for r in n["rows"]) == int(me.innings)
            if d["bowl_innings"]:
                me = wt[wt.player == p].iloc[0]
                t = d["bowl_innings"]["views"][0]["total"]
                assert (t["wickets"], t["runs"]) == (int(me.wickets), int(me.runs))
                # the same pitches: every innings together is their whole record here too
                pt = next((v for v in d["bowl_innings"]["views"] if v["key"] == "pitches"), None)
                assert pt and pt["rows"][-1]["slot"] == "all" and pt["rows"][-1]["innings"] == t["innings"]
    assert kinds == {"multi", "one", "t20"}


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
    names = live.json("/api/names")["names"]                    # for the player menu on names in sentences and charts
    assert names == sorted(names) and p in names and len(names) == len(landing["players"])
    page = live.json(f"/api/player?name={p}")
    assert page["player"] == p and page["missing"] == {}
    status, _, body = live.get("/api/player?name=Nobody At All")
    assert status == 404 and b"hasn't batted or bowled" in body
    # the attributes and scout report come with the page (for the competition picked)
    assert "profile" in page and (page["profile"] is None or {"attributes", "report", "show", "other"} <= set(page["profile"]))
    st, _, body = live.get("/api/demo")                  # the demo is gone (approved 31 October)
    assert st == 404 or b"<div id=root>" in body


def test_inbox_milestones_are_only_your_players(career):
    """The inbox's milestone messages name only your own players, who played for you in that competition (the other
    side's milestones show under "What changed" on My team, never in the inbox)."""
    seen = 0
    for team in career.matches.home.value_counts().index[:6]:
        for msg in DP.inbox(career, team):
            if msg["kind"] != "milestone":
                continue
            ids = career.matches[career.matches.section == msg["section"]].match_id
            mine = career.batting[career.batting.match_id.isin(ids) & (career.batting.team == team)]
            assert msg["player"] in set(mine.player), (team, msg["title"])
            seen += 1
    assert seen


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
    # the whole career at the foot of the page (the current site's "Everything" tab)
    w = d["career"]
    assert w["matches"] > 0 and w["sections"] >= 1 and w["runs"] > w["wickets"] > 0 and isinstance(w["headlines"], list)


def test_my_team_for_a_team_not_in_this_career_shows_yours_and_says_so(live):
    """Found by the stress test: an old link naming a team that hasn't played in this career (another career's team, or
    one since changed) gave a "not found" and a dead end on the home page. Now it's your own team's page, saying so."""
    mine = live.json("/api/myteam")
    d = live.json("/api/myteam?team=Nobody FC")
    assert (d["team"], d["mine"], d["asked"]) == (mine["team"], True, "Nobody FC") and d["missing"] == {}
    assert live.json(f"/api/myteam?team={mine['team']}")["asked"] == ""
    # a team that has played but isn't yours still gets its own page
    other = next(t for m in live.json("/api/matches")["matches"] for t in (m["home"], m["away"]) if t != mine["team"])
    o = live.json(f"/api/myteam?team={other}")
    assert (o["team"], o["mine"], o["asked"]) == (other, False, "")


def test_the_best_batting_position_is_settled():
    """Each position on its own, settled with the format's few dismissals at that position's usual level: 2 innings of
    228 and 12 at no. 4 beat 12 ordinary innings at no. 5; the best over a longer run is named too."""
    from fakecareer import Book
    b = Book()
    # the usual no. 4 averages 40 and no. 5 averages 40 (an "X" batter each game); our player P moves about
    plan = [(4, 228), (4, 12)] + [(5, 30)] * 12
    for i, (pos, runs) in enumerate(plan):
        mid = f"t{i}"
        b.match(mid, f"2026-{1 + i // 28:02d}-{1 + i % 28:02d}", "India", "England")
        bats = [(f"O{j}", 40, 60, True) for j in range(1, pos)] + [("P", runs, 100, True)]
        bats += [(f"Q{pos}", 40, 60, True)] if pos == 4 else []
        b.inns(mid, 1, "India", "England", bats)
        b.inns(mid, 2, "England", "India", [(f"E{j}", 40, 60, True) for j in range(1, 6)])
    c = b.career()
    t = AT.position_table(c, c.matches.match_id, "P").set_index("position")
    k = 5   # first-class: five dismissals at the usual level
    assert t.average[4] == pytest.approx(120) and t.average[5] == pytest.approx(30)
    assert t.settled[4] == pytest.approx((240 + k * t.all_average[4]) / (2 + k))
    assert t.settled[5] == pytest.approx((360 + k * t.all_average[5]) / (12 + k))
    best = AT.best_position(c, c.matches.match_id, "P")
    assert best["position"] == 4 and best["small"] and best["proven"]["position"] == 5


def test_my_team_scouting_tab(live):
    """Every competition the team plays, each with its struggling players (and who could come in) or a plain reason why
    there's nobody; the latest series agrees with the report card's "Who to bring in"."""
    d = live.json("/api/scouting")
    my = live.json("/api/myteam")
    assert d["team"] == my["team"] and [s["section"] for s in d["sections"]] == my["sections"]
    for s in d["sections"]:
        assert bool(s["advice"]) != bool(s["none"])
        for a in s["advice"]:
            assert a["verdict"] and a["why"] and isinstance(a["picks"], list) and isinstance(a["elsewhere"], str)
        # one man is never brought in for two players
        brought = [a["picks"][0]["player"] for a in s["advice"] if a["verdict"].startswith("Replace")]
        assert len(brought) == len(set(brought))
    if my.get("report") and my["report"]["section"] in my["sections"]:
        same = next(s for s in d["sections"] if s["section"] == my["report"]["section"])
        assert [a["player"] for a in same["advice"]] == [a["player"] for a in my["report"]["advice"]]
    assert live.get("/api/scouting?team=Nobody FC")[0] == 404


# ------------------------------------------------------------------ the Teams page (stage 2)
def test_teams_page_opens_on_your_team_and_every_tab_works(live):
    """With nothing picked: your team in its most played competition. Every tab, overall, home and away, comes back
    whole (no part that couldn't be worked out); an unknown team is a 404."""
    d = live.json("/api/team")
    p = d["page"]
    assert p["team"] == "England" and p["tab"] == "Overview" and not p["head"]["none"]
    counts = [c["matches"] for c in d["choices"]]
    assert counts == sorted(counts, reverse=True)
    m = live.json("/api/career")
    for tab in p["tabs"]:
        for venue in ("", "home", "away"):
            x = live.json(f"/api/team?team=England&section={p['section']}&tab={tab}&venue={venue}")["page"]
            assert x["tab"] == tab
            if x["head"]["none"]:
                assert venue, "overall always has a record"
                continue
            assert x["body"]["missing"] == {}, (tab, venue, x["body"]["missing"])
    assert live.get("/api/team?team=Nobody FC")[0] == 404
    assert m


def test_teams_page_numbers_are_the_engines(career):
    """The record, the table of every team, the top run-scorers, the results and the best XI are what the engine
    says, in every competition, overall and at home."""
    from ccstats import seasonal as SN
    for sec in sorted(career.matches.section.unique()):
        ids = Scope(sections=[sec]).match_ids(career.matches)
        tbl = A.team_table(career, ids, "all")
        for team in list(tbl.team)[:3]:
            h = TPG.head(career, sec, "All seasons", team, "all")
            r = tbl.set_index("team").loc[team]
            kp = {k["k"]: k["v"] for k in h["kpis"]}
            assert kp["Played"] == str(int(r.played)) and kp["Won–Lost"] == f"{int(r.won)}–{int(r.lost)}"
            assert kp["Win %"] == f"{r.win_pct:.0f}%"
            ov = TPG.overview(career, sec, "All seasons", team, "all")
            assert ov["missing"] == {}, (sec, team, ov["missing"])
            assert sorted(row[0] for row in ov["every_team"]["rows"]) == sorted(tbl.team)
            bat = player_tables(career, Scope(sections=[sec]), by_team=True)[0]
            top = bat[bat.team == team].sort_values("runs", ascending=False).head(6)
            assert [x["runs"] for x in ov["top_bat"]["rows"]] == [int(v) for v in top.runs if v > 0]
            res = TPG.results_tab(career, sec, "All seasons", team, "all")["results"]
            assert len(res["rows"]) == int(r.played) and sum(row[-1] == "W" for row in res["rows"]) == int(r.won)
            assert len(res["links"]) == len(res["rows"])
            xi = SN.best_xi(career, ids, team)
            got = TPG.squad_tab(career, sec, "All seasons", team, "all")["best_xi"]
            assert [row[2] for row in got.get("rows", [])] == list(xi.player)
            # home only: the games at home that weren't on neutral ground
            here = career.matches[career.matches.match_id.isin(ids)]
            home = here[(here.home == team) & ~here.neutral]
            hh = TPG.head(career, sec, "All seasons", team, "home")
            if len(home):
                assert {k["k"]: k["v"] for k in hh["kpis"]}["Played"] == str(len(home))
            else:
                assert hh["none"]


def test_teams_page_says_why_when_theres_nothing(career):
    """Neutral ground has no home games; a team that belongs in a competition but hasn't played there yet is told
    where it has played."""
    m = career.matches
    for sec in m.section.unique():
        here = m[m.section == sec]
        every, todo = CAT.section_teams(here, sec, here)
        if here.neutral.all():
            h = TPG.head(career, sec, "All seasons", here.home.iloc[0], "home")
            assert h["none"].startswith(f"{sec} matches are played at neutral venues")
        for t in sorted(todo)[:1]:
            h = TPG.head(career, sec, "All seasons", t, "all")
            assert h["none"].startswith(f"{t} haven't played in {sec} yet")


def test_teams_page_league_race_positions(career):
    """Each league race line holds a position for every match day it played, from 1 to the number of teams."""
    m = career.matches
    for sec in m.section.unique():
        here = m[m.section == sec]
        for team in sorted(set(here.home))[:2]:
            r = TPG.season_tab(career, sec, "All seasons", team, "all")["race"]
            if not r or not r["lines"]:
                continue
            n = len(r["lines"])
            assert team in {line["team"] for line in r["lines"]}
            for line in r["lines"]:
                rounds = [x["round"] for x in line["points"]]
                assert rounds == sorted(rounds) and all(1 <= x["position"] <= n for x in line["points"])


# ------------------------------------------------------------------ Team v team (stage 2)
def test_team_v_team_defaults_and_every_choice(live):
    """With nothing picked: your team against the side it has met most, their meetings at every ground; every choice
    of matches and ground comes back whole or with a plain reason."""
    d = live.json("/api/teamvteam")
    p = d["page"]
    assert p["a"] == "England" and p["b"] != "England" and p["which"] in ("each", "any")
    for which in ("each", "any"):
        for g in p["grounds"]:
            x = live.json(f"/api/teamvteam?section={p['section']}&a={p['a']}&b={p['b']}&which={which}&ground={g['key']}")["page"]
            assert x["which"] == which and x["ground"] == g["key"]
            assert bool(x["none"]) != bool(x.get("body")), (which, g)
            if x.get("body"):
                assert x["body"]["missing"] == {}, (which, g, x["body"]["missing"])


def test_team_v_team_numbers_are_the_engines(career):
    """Against each other: each side's record is the engine's for their meetings, the head to head adds up, and the
    tale of the tape's ticks go to the better side."""
    from server import tvtpage as TV
    m = career.matches
    done = 0
    for sec in sorted(m.section.unique()):
        here = m[m.section == sec]
        pairs = (here.home + "|" + here.away).value_counts()
        for pair in pairs.index[:2]:
            a, b = pair.split("|")
            d = TV.page(career, sec, "All seasons", a, b, "each", "all", [])
            if d["none"]:
                continue
            body = d["body"]
            assert body["missing"] == {}, (sec, a, b, body["missing"])
            meet = here[((here.home == a) & (here.away == b)) | ((here.home == b) & (here.away == a))]
            rec = A.team_table(career, Scope(sections=[sec], team=a, opponent=b).match_ids(m)).set_index("team").loc[a]
            figs = {f["k"]: f["v"] for f in body["tiles"][0]["figures"]}
            assert figs["Played"] == str(int(rec.played)) == str(len(meet))
            assert len(body["meetings"]["rows"]) == len(meet)
            aw, bw = int((meet.winner == a).sum()), int((meet.winner == b).sum())
            assert body["meetings"]["line"].startswith(f"{len(meet)} meeting") and f"{a} {aw} – {bw} {b}" in body["meetings"]["line"]
            for r in body["tape"]["rows"]:
                assert not (r["a_better"] and r["b_better"])
            done += 1
    assert done >= 3


def test_team_v_team_says_why_when_theres_nothing(career):
    from server import tvtpage as TV
    m = career.matches
    for sec in m.section.unique():
        here = m[m.section == sec]
        if here.neutral.all():
            d = TV.page(career, sec, "All seasons", here.home.iloc[0], here.away.iloc[0], "each", "a_home", [])
            assert d["ground"] == "all" or d["none"].endswith("Choose All venues.")


# ------------------------------------------------------------------ Opponent preview (stage 2)
def test_opponent_preview_opens_on_your_latest_game_and_every_tab_works(live):
    """No schedule: it opens on your team's latest game; every tab, and both ways of counting who gets whom out, comes
    back whole."""
    d = live.json("/api/preview")
    assert d["mine"] == "England" and d["opp"] and not d["none"]
    for tab in d["tabs"]:
        for mu, cur in (("", ""), ("every", "1")):
            x = live.json(f"/api/preview?section={d['section']}&format={d['format']}&mine={d['mine']}&opp={d['opp']}&tab={tab}&mu={mu}&cur={cur}")
            assert x["tab"] == tab and x["mu"] == (mu == "every") and x["cur"] == (cur == "1")
            assert x["head"]["missing"] == {} and x["body"]["missing"] == {}, (tab, x["head"]["missing"], x["body"]["missing"])
    # no team of yours picked: their side only, and the tabs that need your team say so
    x = live.json(f"/api/preview?section={d['section']}&format={d['format']}&mine=—&opp={d['opp']}&tab=Side by side")
    assert x["body"]["none"] == "Pick your team above to compare the two sides." and "predicted" not in x["head"]


def test_opponent_preview_numbers_are_the_engines(career):
    """Their record is the engine's preview record; the meetings add up; the predicted result's three chances add to
    100 at every ground."""
    from ccstats import extras as E
    from ccstats import preview as PV
    from server import previewpage as PG
    m = career.matches
    done = 0
    for sec in ["Tests", "ODIs", "T20Is"]:
        here = m[m.section == sec]
        if here.empty:
            continue
        pairs = (here.home + "|" + here.away).value_counts()
        for pair in pairs.index[:2]:
            me, opp = pair.split("|")
            d = PG.page(career, {"section": PG.INTL, "format": sec, "mine": me, "opp": opp}, [me], [me], [])
            assert not d["none"], d["none"]
            ids = here.match_id
            rec = A.team_record(E.opponent_preview(career, ids, opp)["matches"])
            k = {x["k"]: x["v"] for x in d["head"]["kpis"]}
            assert k["Played"] == str(rec["played"]) and k["Won–Lost"] == f"{rec['won']}–{rec['lost']}"
            mt = PV.meetings(career, ids, me, opp)
            h = d["body"]["h2h"]
            assert {x["k"]: x["v"] for x in h["kpis"]}["Meetings"] == str(mt["record"]["played"])
            assert len(h["cards"]) == len(mt["cards"])
            for where, p in d["head"]["predicted"].items():
                nums = [float(x.split()[-1].rstrip("%")) for x in p["line"].split(" · ")]
                assert abs(sum(nums) - 100) <= 2, (where, p["line"])
            done += 1
    assert done >= 2
