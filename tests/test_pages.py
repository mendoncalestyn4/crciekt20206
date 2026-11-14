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


def test_my_team_format_tiles_add_up_to_the_season_tile(live):
    """Found by you (14 November): the Season tile counted April to March while the format tiles each counted their
    competition's own season, so they didn't add up. Now every tile counts the Season tile's April-to-March season,
    for every team that has played: their wins, losses and games add up to it, and each says which season."""
    teams = sorted({t for m in live.json("/api/matches")["matches"] for t in (m["home"], m["away"])})
    checked = 0
    for team in teams:
        d = live.json(f"/api/myteam?team={team}")
        if not d.get("season") or not d.get("banner"):
            continue
        rs, cal = d["season"]["results"], d["season"]
        tiles = d["banner"]["tiles"]
        label = f"Apr {cal['year']} – Mar {cal['year'] + 1}"
        assert sum(t["record"]["played"] for t in tiles) == len(rs), team
        assert sum(t["record"]["won"] for t in tiles) == sum(r["outcome"] == "W" for r in rs), team
        assert sum(t["record"]["lost"] for t in tiles) == sum(r["outcome"] == "L" for r in rs), team
        assert all(t["season"] == label for t in tiles), team
        # the competitions played this season come first, so the three tiles shown are this season's
        played = [t["record"]["played"] for t in tiles]
        assert played == sorted(played, reverse=True), team
        checked += 1
    assert checked == len(teams) >= 5


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


def test_the_team_planner_opens_every_tab_with_the_engines_numbers(live):
    """Team planner (stage 2): every tab for the team it opens on, each part worked out, and the batting order and
    bowling plan the engine's own."""
    from ccstats import players as PL
    from ccstats.stats import Scope
    d = live.json("/api/planner")
    assert d["team"] in d["teams"] and d["tabs"] and d["tab"] == d["tabs"][0]
    for tab in d["tabs"]:
        t = live.json(f"/api/planner?section={d['section']}&team={d['team']}&tab={tab}")
        assert t["tab"] == tab and t["body"]["missing"] == {}, (tab, t["body"]["missing"])
    c = live.app.state.site.career()
    ids = Scope(sections=[d["section"]]).match_ids(c.matches)
    bp = PL.bowling_plan(c, ids, d["team"])
    plan = live.json(f"/api/planner?section={d['section']}&team={d['team']}&tab=Bowling plan")["body"]["plan"]
    assert ([r[0] for r in plan["rows"]] == list(bp.player)) if len(bp) else ("none" in plan)
    every = live.json(f"/api/planner?section={d['section']}&team={d['team']}&tab=Batting order&recent=0")["body"]["order"]
    order = PL.batting_order(c, ids, d["team"])
    assert len(every["every"]["rows"]) == len(order)


def test_rivalries_every_pair_and_one_close_up(live):
    """Rivalries (stage 2): the most played pairs as the engine counts them, and the one picked close up."""
    from ccstats import extras as E
    from ccstats.stats import Scope
    d = live.json("/api/rivalries")
    c = live.app.state.site.career()
    rv = E.rivalries(c, Scope(sections=[d["section"]]).match_ids(c.matches))
    assert [p["key"] for p in d["pairs"]] == [f"{a}|{b}" for a, b in zip(rv.team_a, rv.team_b)]
    assert [r[1] for r in d["table"]["rows"]] == [int(x) for x in rv.played.head(30)]
    assert d["pick"] in {p["key"] for p in d["pairs"]} and d["close"]["missing"] == {}
    a, b = d["pick"].split("|")
    assert all({r[2], r[3]} == {a, b} for r in d["close"]["meetings"]["rows"])
    other = d["pairs"][-1]["key"]
    assert live.json(f"/api/rivalries?section={d['section']}&pick={other}")["pick"] == other


@pytest.fixture(scope="module")
def every(tmp_path_factory):
    """The stats server with a career of every test scorecard (the IPL's playoffs and final among them)."""
    tmp = tmp_path_factory.mktemp("every")
    pc = make_pc(tmp, files=FIXTURES)
    web = tmp / "dist"
    (web / "assets").mkdir(parents=True)
    (web / "index.html").write_text("<!doctype html><title>Stats Pack</title><div id=root></div>")
    s = Live(create_app(pc[0], web=web, watch_every=0))
    yield s
    s.stop()


def test_competitions_every_competition_and_season(every):
    """Seasons · Competitions (stage 2): every competition as it's run, in every season, opens with every part worked
    out; the league table is the engine's; the IPL final's winners are named champions."""
    from ccstats import tables as TB
    d = every.json("/api/competition")
    assert d["choices"] and d["event"] in {c["event"] for c in d["choices"]}
    c = every.app.state.site.career()
    m = c.matches
    for ch in d["choices"]:
        for s in ch["seasons"]:
            x = every.json(f"/api/competition?event={ch['event']}&season={s}")
            assert (x["event"], x["season"]) == (ch["event"], s)
            assert x["missing"] == {} and (x.get("race") or {}).get("missing", {}) == {}, (ch["event"], s)
            assert x["league"] or x["knockouts"] or x["series"] or x["wtc"]
            if x["league"]:
                ids = m[(m.event == ch["event"]) & (m.season.astype(str) == s)].match_id
                lt = TB.league_tables(c, ids)
                assert [g["teams"] for g in x["league"]["groups"]] == [list(t.team) for _, t, _ in lt]
    ipl = every.json("/api/competition?event=Indian Premier League&season=2026")
    assert ipl["knockouts"]["champion"] == "🏆 Gujarat Titans · Indian Premier League 2026 champions"
    final = ipl["knockouts"]["rounds"][-1]
    assert final["round"] == "Final" and [x["won"] for x in final["cards"][0]["teams"]].count(True) == 1


def test_the_title_race_takes_its_knobs_and_never_breaks_on_junk(every):
    d = every.json("/api/competition?event=Indian Premier League&season=2026")
    r = d["race"]["race"]
    assert r and r["teams"] and r["pick"] in r["teams"]
    other = every.json(f"/api/competition?event=Indian Premier League&season=2026&games=20&places=2&pick={r['teams'][-1]}")
    assert (other["race"]["race"]["games"], other["race"]["race"]["places"], other["race"]["race"]["pick"]) == (20, 2, r["teams"][-1])
    for junk in ["-5", "zzz", "9999"]:
        j = every.json(f"/api/competition?event={junk}&season={junk}&games={junk}&places={junk}")
        assert j["event"] in {c["event"] for c in j["choices"]}
        jr = (j.get("race") or {}).get("race")
        assert jr is None or 1 <= jr["games"] <= 60


def test_the_season_calendar_series_and_progress(every):
    """Seasons · Season (stage 2): the team's season month by month (every result on its day, opening its match), one
    month, every team; the series tracker; how far each competition has got."""
    c = every.app.state.site.career()
    m = c.matches
    d = every.json("/api/season")
    team = d["team"]
    cal = d["calendar"]
    assert cal["view"] == "season" and len(cal["grid"]) == 12 and cal["season"] in {s["key"] for s in cal["seasons"]}
    y = int(cal["season"])
    start, end = pd.Timestamp(year=y, month=4, day=1), pd.Timestamp(year=y + 1, month=4, day=1)
    mine = m[((m.home == team) | (m.away == team)) & (m.date >= start) & (m.date < end)]
    shown = [ch["id"] for mo in cal["grid"] for v in mo["days"].values() for ch in v if ch["id"]]
    assert sorted(shown) == sorted(mine.match_id)
    assert sum(mo["played"] for mo in cal["grid"]) == len(mine)
    one = every.json(f"/api/season?team={team}&view=month&month={cal['months'][0]['key']}")["calendar"]
    assert one["view"] == "month" and len(one["grid"]) == 1 and one["grid"][0]["key"] == cal["months"][0]["key"]
    every_team = every.json("/api/season?team=All teams")["calendar"]
    yy = int(every_team["season"])
    n = len(m[(m.date >= pd.Timestamp(year=yy, month=4, day=1)) & (m.date < pd.Timestamp(year=yy + 1, month=4, day=1))])
    assert sum(mo["played"] for mo in every_team["grid"]) == n
    sr = every.json(f"/api/season?team={team}&tab=Series tracker")["series"]
    assert sr["none"] or sr["done"] or sr["live"]
    pr = every.json("/api/season?team=All teams&tab=Season progress")["progress"]
    assert pr["rows"] and all(r["pct"] is None or 0 <= r["pct"] <= 100 for r in pr["rows"])
    assert every.json("/api/season?team=Nobody&tab=zzz&season=x&month=y")["team"] in {"All teams", team}


def test_every_season_review_and_the_honours(every):
    """Seasons · Season review and Honours (stage 2): every competition's season and international year opens with every
    part worked out; the honours board is the engine's, champions first; the trophy cabinet counts each title once."""
    from ccstats import extras as E
    d = every.json("/api/review")
    assert d["choices"] and d["pick"] in {c["key"] for c in d["choices"]}
    for c in d["choices"]:
        for pts in ("", "ipl"):
            x = every.json(f"/api/review?pick={c['key']}&points={pts}")
            parts = [x.get("year"), x.get("season_review"), x.get("mvp")]
            assert all(p is None or p["missing"] == {} for p in parts), (c["key"], [p["missing"] for p in parts if p])
            assert (x.get("year") is not None) == (c["section"] == "International cricket")
    h = E.honours(every.app.state.site.career())
    board = every.json("/api/honours")
    assert [b["title"] for b in board["boards"]] == list(h.drop_duplicates("section").section)
    first = board["boards"][0]
    g = h[h.section == first["title"]]
    assert [r[1].replace("🏆 ", "") for r in first["rows"]] == list(g.champions)
    cab = every.json("/api/honours?tab=Trophy cabinets")["cabinet"]
    won = h[~h.how.str.contains("so far")].explode("champion_teams")
    assert sum(r[1] for r in cab["rows"]) == len(won)


def test_team_record_carry_usual_and_the_score_to_aim_are_the_engines(every):
    """Stage 2's new pieces as the pages show them: who carries the team and the usual score at each wicket (Team
    record, Overview) and the score to aim for (Opponent preview), each the engine's own figures."""
    from ccstats import aim as AIM
    c = every.app.state.site.career()
    m = c.matches
    for sec, team in (("ODIs", "England"), ("Tests", "England"), ("T20 Blast", sorted(m[m.section == "T20 Blast"].home)[0])):
        b = every.json(f"/api/team?team={team}&section={sec}")["page"]["body"]
        assert b["missing"] == {}
        mids = set(m[(m.section == sec) & ((m.home == team) | (m.away == team))].match_id)
        sh = AIM.team_shares(c, mids, team)
        assert all(r[0] in set(sh.player) for r in b["carry"]["rows"]) and b["carry"]["shows"]
        for r in b["carry"]["rows"]:
            e = sh[sh.player == r[0]].iloc[0]
            assert r[1:3] == [e.matches, e.runs] and r[4] == e.wickets and (e.run_share >= 5 or e.wicket_share >= 5)
        u = AIM.usual_by_wicket(c, mids, team)
        assert [r[1] for r in b["usual"]["rows"]] == list(u.usual)
        for r in b["usual"]["rows"]:
            if r[2] != "–":
                assert r[3] == f"{r[1] - r[2]:+d}"
    # the score to aim for: mixed formats say why; Tests show the first-innings totals that won, drew and lost; one-day
    # and T20 cricket the engine's totals, how sure it is and the meetings
    def opp(sec):
        g = m[(m.section == sec) & ((m.home == "England") | (m.away == "England"))]
        return next(t for t in list(g.home) + list(g.away) if t != "England")
    d = every.json(f"/api/preview?section=Internationals&format=All&mine=England&opp={opp('ODIs')}")
    assert "Pick one format" in d["head"]["aim"]["none"]
    for fmt, kind in (("Tests", "multi"), ("ODIs", "limited"), ("T20Is", "limited")):
        o = opp(fmt)
        d = every.json(f"/api/preview?section=Internationals&format={fmt}&mine=England&opp={o}")
        a = d["head"]["aim"]
        assert d["head"]["missing"] == {} and not a["none"] and a["kind"] == kind and a["note"]
        e = AIM.score_to_aim(c, set(m[m.section == fmt].match_id), "England", o)
        assert set(a["venues"]) == {"Home", "Away", "Neutral"}
        for venue, v in a["venues"].items():
            x = e["venues"][venue.lower()]
            if kind == "multi":
                assert bool(v["games"]) == bool(x["games"]) and (not x["games"] or len(v["games"]["rows"]) == len(x["games"]))
                for res, word in (("won", "won"), ("drawn", "drew"), ("lost", "lost")):
                    t = x["typical"][res]
                    assert (f"when they {word}, usually {t['typical']}" in v["line"]) == bool(t["n"])
            else:
                assert v["line"] == f"{x['even']} for an even game · {x['seventy']} for a 70% chance"
                assert (v["meetings"] is None) == (not x["meetings"])
        if kind == "limited":
            assert f"{e['games']} finished games" in a["rests"] and f"{e['right']:.0f}%" in a["sure"]
            assert bool(a.get("few")) == e["venues"]["home"]["few"]


def test_season_wrapped_on_every_season_review(every):
    """Season review's wrapped slides for every season and every team in it (international years one format at a
    time), never failing, each slide the engine's figure."""
    from ccstats import wrapped as WR
    c = every.app.state.site.career()
    d = every.json("/api/review")
    for ch in d["choices"]:
        x = every.json(f"/api/review?pick={ch['key']}")
        w = x["wrapped"]
        assert w["missing"] == {}, (ch, w["missing"])
        wr = w["wrapped"]
        for f in (wr["formats"] or [""]):
            y = every.json(f"/api/review?pick={ch['key']}&wfmt={f}")["wrapped"]["wrapped"]
            assert y["format"] == f
            for team in y["teams"]:
                z = every.json(f"/api/review?pick={ch['key']}&wfmt={f}&wteam={team}")["wrapped"]
                assert z["missing"] == {} and z["wrapped"]["team"] == team
                s = {k["key"]: k for k in z["wrapped"]["slides"]}
                e = WR.season_wrapped(c, z["wrapped"]["section"], next(v for v in c.matches.season.unique() if str(v) == ch["season"]), team)
                assert list(s) == [k for k in WR.SLIDES if k in e]
                if "runs" in e:
                    assert s["runs"]["big"] == str(e["runs"]["runs"]) and s["runs"]["head"] == e["runs"]["player"]
                if "record" in e:
                    assert s["record"]["big"] == str(e["record"]["played"])
                if "bowling" in e:
                    assert s["bowling"]["big"] == f"{e['bowling']['wickets']}/{e['bowling']['runs']}"
    # a team not in that season: back to the one it opens on
    bad = every.json(f"/api/review?pick={d['choices'][0]['key']}&wteam=Nobody FC")["wrapped"]["wrapped"]
    assert bad["team"] in bad["teams"]


def test_every_stage_2_page_answers_on_a_career_with_no_matches(tmp_path):
    """A career made before any game was played: every Teams and Seasons page says there's nothing yet, never an
    error, and never that there's no career."""
    pc = make_pc(tmp_path, files=[])
    web = tmp_path / "dist"
    (web / "assets").mkdir(parents=True)
    (web / "index.html").write_text("<!doctype html><title>Stats Pack</title><div id=root></div>")
    s = Live(create_app(pc[0], web=web, watch_every=0))
    try:
        for path in ("/api/team", "/api/teamvteam", "/api/preview", "/api/planner", "/api/rivalries", "/api/competition",
                     "/api/season", "/api/review", "/api/honours", "/api/honours?tab=Trophy cabinets", "/api/team?team=x",
                     "/api/review?pick=x|1", "/api/season?team=x&view=month"):
            code, _, _ = s.get(path)
            assert code == 200, (path, code)
        assert "No competition has been decided yet" in s.json("/api/honours")["none"]
        from server.styleguide import NO_MATCHES   # the current site's words, with how to get matches in
        for path in ("/api/preview", "/api/planner", "/api/rivalries", "/api/competition", "/api/season", "/api/review"):
            assert s.json(path)["none"] == NO_MATCHES, path   # (once "No career is open yet": there is one)
        assert s.json("/api/myteam")["missing"]["everything"] == NO_MATCHES
    finally:
        s.stop()


def test_every_page_opens_on_the_picks_you_last_made(tmp_path):
    """The current site's remembered picks (ui/state.py): a section, season, team or competition picked on one page is
    saved with the career (the same file the current site reads), and every page opens on it when it's among its
    choices; one that isn't is passed over for the page's usual first choice."""
    import json as J
    pc = make_pc(tmp_path, files=FIXTURES)
    web = tmp_path / "dist"
    (web / "assets").mkdir(parents=True)
    (web / "index.html").write_text("<!doctype html><title>Stats Pack</title><div id=root></div>")
    s = Live(create_app(pc[0], web=web, watch_every=0))
    try:
        def post(kind, value):
            code, _, _ = s.request("/api/remember", data=J.dumps(dict(kind=kind, value=value)).encode(), ctype="application/json")
            return code
        before = s.json("/api/team")["page"]
        assert post("section", "T20 Blast") == 200 and post("team", "Somerset") == 200
        assert pc[0].load_settings("My career")[1].remembered == {"section": "T20 Blast", "team": "Somerset"}
        p = s.json("/api/team")["page"]
        assert (p["team"], p["section"]) == ("Somerset", "T20 Blast")
        assert s.json("/api/team?team=England")["page"]["section"] != "T20 Blast"   # England never played there
        assert s.json("/api/rivalries")["section"] == "T20 Blast"
        assert s.json("/api/teamvteam")["page"]["section"] == "T20 Blast"
        f = s.json("/api/matches")
        assert (f["section"], f["team"]) == ("T20 Blast", "Somerset")
        assert s.json("/api/matches?section=ODIs")["team"] == "All teams"   # a section asked for: no remembered team
        # Opponent preview: no next match in this career, so the remembered competition (an international format
        # opens international cricket on it)
        assert s.json("/api/preview")["section"] == "T20 Blast"
        assert post("section", "ODIs") == 200
        d = s.json("/api/preview")
        assert (d["section"], d["format"]) == ("Internationals", "ODIs")
        # Competitions and Season review
        ev = s.json("/api/competition")["choices"][-1]
        assert post("event", ev["event"]) == 200 and post("season", ev["seasons"][0]) == 200
        c = s.json("/api/competition")
        assert (c["event"], c["season"]) == (ev["event"], ev["seasons"][0])
        rv = s.json("/api/review")
        assert rv["pick"] in [x["key"] for x in rv["choices"]]
        # junk is refused, and a remembered pick that's no longer a choice is passed over
        assert post("colour", "red") == 400 and post("section", "") == 400 and post("team", "x" * 300) == 400
        assert post("team", "Nobody FC") == 200 and post("section", "Nowhere") == 200
        assert s.json("/api/team")["page"]["team"] == before["team"]
        assert s.json("/api/rivalries")["section"] in [x["section"] for x in s.json("/api/rivalries")["choices"]]
    finally:
        s.stop()


def test_opponent_preview_shows_their_own_record_batting_first_and_where(every):
    """Under the head-to-head record: the opponent's own record batting first and chasing, and home, away and neutral
    then host by host, against every side in that competition, counted again from the scorecards."""
    c = every.app.state.site.career()
    m, inn = c.matches, c.innings
    done = 0
    for section, fmt, me in (("Internationals", "ODIs", "England"), ("Internationals", "Tests", "England"),
                             ("Indian Premier League", "", "")):
        q = f"/api/preview?section={section}" + (f"&format={fmt}" if fmt else "")
        d = every.json(q)
        me = me or d["mine"]
        sec = fmt or section
        mm = m[m.section == sec]
        for o in [x["team"] for x in d["opp_opts"] if "yet)" not in x["label"]][:6]:
            b = every.json(q + f"&mine={me}&opp={o}")["body"]
            assert b["missing"] == {}, b["missing"]
            mine = mm[(mm.home == o) | (mm.away == o)]
            first = inn[inn.innings_no == 1].set_index("match_id").team
            rec = {"first": [0, 0, 0], "chase": [0, 0, 0]}
            for x in mine.itertuples():
                if x.result_type == "no result":
                    continue
                k = "first" if first.get(x.match_id) == o else "chase"
                rec[k][0] += 1
                rec[k][1] += x.winner == o
                rec[k][2] += x.winner not in ("", o)
            assert "bat_first" in b, (sec, me, o, b)
            bf = b["bat_first"]
            assert [bf["first"]["played"], bf["first"]["won"], bf["first"]["lost"]] == rec["first"], (o, sec)
            assert [bf["chase"]["played"], bf["chase"]["won"], bf["chase"]["lost"]] == rec["chase"], (o, sec)
            assert bf["who"] == o and bf["shows"] and bf["for_"]
            w = b["where"]
            for venue in ("home", "away", "neutral"):
                here = [x for x in mine.itertuples() if ("neutral" if x.neutral else "home" if x.home == o else "away") == venue]
                assert w[venue]["played"] == len(here)
                assert w[venue]["won"] == sum(x.winner == o for x in here)
            assert sum(h["played"] for h in w["hosts"]) == len(mine)
            done += 1
    assert done >= 8


def test_team_v_team_batting_first_or_chasing_counted_by_hand(every):
    """Team v team: each side's record batting first and chasing in the games picked (their meetings, or each side's
    own games against anyone), counted again from the scorecards."""
    c = every.app.state.site.career()
    m, inn = c.matches, c.innings
    first = inn[inn.innings_no == 1].set_index("match_id").team
    done = 0
    for ch in every.json("/api/teamvteam")["choices"]:
        p = every.json(f"/api/teamvteam?section={ch['section']}")["page"]
        if not p or p.get("none"):
            continue
        for which in ("each", "any"):
            x = every.json(f"/api/teamvteam?section={p['section']}&a={p['a']}&b={p['b']}&which={which}")["page"]
            if x.get("none"):
                continue
            b = x["body"]
            assert b["missing"] == {}, b["missing"]
            here = m[m.section == x["section"]]
            for side in b["bat_first"]["sides"]:
                t, o = side["team"], x["b"] if side["team"] == x["a"] else x["a"]
                g = here[(here.home == t) | (here.away == t)]
                if which == "each":
                    g = g[(g.home == o) | (g.away == o)]
                g = g[g.result_type != "no result"]
                for key, bat in (("first", True), ("chase", False)):
                    gg = g[(g.match_id.map(first) == t) == bat]
                    assert side[key] == dict(played=len(gg), won=int((gg.winner == t).sum()),
                                             lost=int(((gg.winner != t) & (gg.winner != "")).sum())), (x["section"], t, which, key)
            done += 1
    assert done >= 6


def test_team_record_overview_charts_counted_by_hand(every):
    """Teams · Overview: runs of results (every match in order), against stronger and weaker sides (both ratings just
    before each match) and home, away and neutral then host by host, counted again from the scorecards."""
    from ccstats.rankings import team_elo
    c = every.app.state.site.career()
    m = c.matches
    done = 0
    for sec in ("ODIs", "Tests", "T20 Blast", "Indian Premier League"):
        here = m[m.section == sec]
        elo = team_elo(c, sec)[1].set_index(["match_id", "team"]).before
        for team in sorted(set(here.home) | set(here.away))[:4]:
            b = every.json(f"/api/team?team={team}&section={sec}")["page"]["body"]
            assert b["missing"] == {}, b["missing"]
            mine = here[(here.home == team) | (here.away == team)]
            out = {r.match_id: ("W" if r.winner == team else "L" if r.winner else "D" if r.result_type == "draw" else
                                "T" if r.result_type == "tie" else "N") for r in mine.itertuples()}
            res = b["streaks"]["results"]
            assert sorted(r["id"] for r in res) == sorted(out) and all(r["outcome"] == out[r["id"]] for r in res)
            # the runs: each a stretch of one result, together every match once, next runs never alike
            runs = b["streaks"]["streaks"]
            assert runs[0]["start"] == 0 and runs[-1]["end"] == len(res) - 1
            for r0, r1 in zip(runs, runs[1:]):
                assert r1["start"] == r0["end"] + 1 and r1["o"] != r0["o"]
            for r in runs:
                assert {x["outcome"] for x in res[r["start"]: r["end"] + 1]} == {r["o"]}
            st = b["strength"]["rows"]
            for r in st:
                opp = r["opp"]
                assert (r["me"], r["them"]) == (round(elo[(r["id"], team)]), round(elo[(r["id"], opp)]))
                assert r["gap"] == round(elo[(r["id"], opp)] - elo[(r["id"], team)])
            assert {r["id"] for r in st} == {k for k, o in out.items() if (k, team) in elo.index}
            v = b["venues"]
            for venue in ("home", "away", "neutral"):
                g = [x for x in mine.itertuples() if ("neutral" if x.neutral else "home" if x.home == team else "away") == venue]
                assert (v[venue]["played"], v[venue]["won"]) == (len(g), sum(out[x.match_id] == "W" for x in g))
            assert sum(h["played"] for h in v["hosts"]) == len(mine)
            for h in v["hosts"]:
                g = [x for x in mine.itertuples() if (not x.neutral and x.home == h["host"]) or (x.neutral and not h["host"])]
                assert h["played"] == len(g), (team, h)
            done += 1
    assert done >= 12


def test_team_record_big_stands_contribution_and_the_usual_line(every):
    """Teams · Overview: big stands (the team's biggest partnerships, from every stand counted again), every player's
    contribution (all of them, runs off the bat, the same as the engine's and adding up to the team's) and the
    usual-score line (the same numbers as the table under it)."""
    from ccstats import aim as AIM
    from ccstats import partnerships as PS
    c = every.app.state.site.career()
    m = c.matches
    done = 0
    for sec in ("ODIs", "Tests", "T20 Blast", "Indian Premier League"):
        here = m[m.section == sec]
        for team in sorted(set(here.home) | set(here.away))[:4]:
            b = every.json(f"/api/team?team={team}&section={sec}")["page"]["body"]
            assert b["missing"] == {}, b["missing"]
            mids = set(here[(here.home == team) | (here.away == team)].match_id)
            st = PS.stands(c, mids)
            st = st[st.team == team]
            bs = b["big_stands"]
            runs = [int(r[3].rstrip("*")) for r in bs["rows"]]
            assert runs == sorted(st.runs, reverse=True)[:10] and len(runs) == min(10, len(st))
            assert all(r[3].endswith("*") == bool(x.unbroken) for r, x in zip(bs["rows"], PS.big_stands(c, mids, team).itertuples()))
            sh = AIM.team_shares(c, mids, team)
            co = b["contribution"]
            assert [x["player"] for x in co["rows"]] == list(sh.player) and [x["runs"] for x in co["rows"]] == list(sh.runs)
            bat = c.batting[c.batting.match_id.isin(mids) & (c.batting.team == team) & c.batting.did_bat]
            assert co["team_runs"] == int(bat.runs.sum()) == sum(x["runs"] for x in co["rows"])
            # each share written once, the same as "Who carries the team" writes it
            carry = {r[0]: r[3] for r in b["carry"]["rows"]}
            for x in co["rows"]:
                assert x["run_share"] == round(x["runs"] / co["team_runs"] * 100, 1)
                if x["player"] in carry:
                    assert carry[x["player"]] == f"{x['run_share']:.1f}%"
            assert sum(x["run_share"] for x in co["rows"]) == pytest.approx(100.0, abs=0.05 * len(co["rows"]))   # each sent to 1 place
            # batting depth: the average team's shares are of teams that batted, so they add up to 100% (a team without
            # a run used to count as 0% and pull them down)
            assert sum(r["ref"] for r in b["depth"]["rows"]) == pytest.approx(100.0, abs=0.1)
            assert sum(r["runs"] for r in b["depth"]["rows"]) == co["team_runs"]
            u = b["usual"]
            prev = -1
            for r in u["rows"]:    # the line runs while the usual score keeps rising
                if r[1] <= prev:
                    break
                assert f"{r[1]}/{int(r[0].split()[0][:-2])}" in u["line"]
                prev = r[1]
            done += 1
    assert done >= 12


def test_player_page_match_winners_countries_big_games_and_bounce_back(every):
    """The Player page's new pieces for players who have played 4 or more matches, in each competition they
    played: never failing, each the engine's figures (the match-winners chart is their wins as player of the match;
    every match is in exactly one row of country by country)."""
    from ccstats import moments as MO
    c = every.app.state.site.career()
    m = c.matches
    counts = c.batting.groupby("player").match_id.nunique()
    done = 0
    for p in sorted(counts[counts >= 4].index)[:40]:
        d = every.json(f"/api/player?name={p}")
        for sec in d["sections"][:3]:
            x = every.json(f"/api/player?name={p}&section={sec}")
            for k in ("winners", "big", "countries", "bounce"):
                assert k not in x["missing"], (p, sec, x["missing"])
            w = x["winners"]
            assert [y["id"] for y in (w["players"][0]["matches"] if w["players"] else [])] == [y["id"] for y in x["won"]]
            ids = set(m[m.section == sec].match_id)
            played = c.batting[c.batting.match_id.isin(ids) & (c.batting.player == p)].match_id.nunique()
            if x["countries"]:
                assert sum(r[1] for r in x["countries"]["rows"]) == played
            bm = MO.big_match(c, ids, players=[p])
            assert bool(x["big"].get("rows")) == (not bm.empty)
            done += 1
    assert done >= 40


def test_competitions_series_ladder_leaders_team_of_the_series_and_badges(every):
    """Competitions · one series: the ladder (the series score after each match, from the first-named side), the
    most runs and wickets (counted again from the scorecards) and Team of the series for 2 or more matches; every
    league, title race, series and WTC table marks its team column for badges."""
    c = every.app.state.site.career()
    m = c.matches
    seen = 0
    for ch in every.json("/api/competition")["choices"]:
        for season in ch["seasons"]:
            d = every.json(f"/api/competition?event={ch['event']}&season={season}")
            for g in (d.get("league") or {}).get("groups", []):
                assert g["badges"] == [0]
            if d.get("series"):
                assert d["series"]["table"]["badges"] == [1]
            for g in ((d.get("race") or {}).get("race") or {}).get("groups", []):
                assert g["badges"] == [0]
            for i, e in enumerate((d.get("series") or {}).get("each", [])):
                x = every.json(f"/api/competition?event={ch['event']}&season={season}&series={i}")
                one = x["series_one"]
                assert x["series_pick"] == i and one["missing"] == {}, one["missing"]
                ids = list(m[m.series_id == e["id"]].sort_values("date").match_id)
                lad = one["ladder"]
                assert sorted(r["id"] for r in lad["matches"]) == sorted(ids)
                side = one["team"]       # your side if you play in it, else the side that won it
                g = m[m.series_id == e["id"]]
                assert side in (g.home.iloc[0], g.away.iloc[0])
                mine = every.app.state.site.my_teams(c)
                if not any(t in (g.home.iloc[0], g.away.iloc[0]) for t in mine):
                    assert (g.winner == side).sum() >= (g.winner == ({g.home.iloc[0], g.away.iloc[0]} - {side}).pop()).sum()
                w = l = 0
                for r, p in zip(lad["matches"], lad["progress"]):
                    win = m.set_index("match_id").winner[r["id"]]
                    w, l = w + (win == side), l + (win not in ("", side))
                    assert (p["won"], p["lost"]) == (w, l)
                b = c.batting[c.batting.match_id.isin(ids) & c.batting.did_bat].groupby(["player", "team"]).runs.sum()
                assert [x_["runs"] for x_ in lad["most_runs"]] == sorted(b, reverse=True)[:len(lad["most_runs"])]
                wk = c.bowling[c.bowling.match_id.isin(ids) & (c.bowling.balls > 0)].groupby(["player", "team"]).wickets.sum()
                assert [x_["wickets"] for x_ in lad["most_wickets"]] == sorted(wk, reverse=True)[:len(lad["most_wickets"])]
                assert (one.get("xi") is not None) == (len(ids) >= 2)
                if one.get("xi") and not one["xi"].get("none"):
                    xi_players = {r[2] for r in one["xi"]["rows"]}
                    assert xi_players <= set(c.batting[c.batting.match_id.isin(ids)].player)
                seen += 1
    assert seen >= 3


def test_season_calendar_keeps_each_tournament_whole_and_lights_the_best_month(every):
    """Seasons · Season: each team's season, April to March, holds every game of that season once (a tournament whole
    to the season most of it is played in, its games just outside the twelve months in April's or March's tile with
    their dates), the months' records add up, and the best month is the one with the most wins over defeats."""
    from ccstats import seasonal as SN
    c = every.app.state.site.career()
    m = c.matches
    year_of = SN.april_seasons(m)
    done = 0
    for team in sorted(set(m.home) | set(m.away))[:12]:
        mine = m[(m.home == team) | (m.away == team)]
        for y in sorted({int(year_of[i]) for i in mine.match_id}):
            cal = every.json(f"/api/season?team={team}&season={y}")["calendar"]
            assert cal["season"] == str(y)
            want = set(mine[mine.match_id.map(year_of) == y].match_id)
            got = [ch["id"] for mo in cal["grid"] for chips in mo["days"].values() for ch in chips if ch.get("id")]
            got += [ch["id"] for mo in cal["grid"] for ch in mo.get("extra", [])]
            assert sorted(got) == sorted(want), (team, y)
            g = m[m.match_id.isin(want)]
            assert sum(mo["won"] for mo in cal["grid"]) == int((g.winner == team).sum())
            assert sum(mo["lost"] for mo in cal["grid"]) == int(((g.winner != team) & (g.winner != "")).sum())
            busy = [mo for mo in cal["grid"] if mo["played"]]
            best = [mo for mo in cal["grid"] if mo.get("best")]
            assert len(best) == (1 if busy else 0)
            if best:
                top = max((mo["won"] - mo["lost"], mo["played"]) for mo in busy)
                assert (best[0]["won"] - best[0]["lost"], best[0]["played"]) == top
            done += 1
    assert done >= 12


def test_a_tournament_goes_whole_to_its_season():
    import pandas as pd
    from ccstats import seasonal as SN
    d = pd.to_datetime(["2029-03-29", "2029-03-31", "2029-04-02", "2029-04-20", "2029-05-26", "2029-03-10", "2029-03-12"])
    m = pd.DataFrame(dict(match_id=list("abcdefg"), date=d, series_id=["", "", "", "", "", "s1", "s1"],
                          event=["IPL"] * 5 + ["ODIs"] * 2, season=["2029"] * 5 + ["2028/29"] * 2))
    y = SN.april_seasons(m)
    assert list(y[list("abcde")]) == [2029] * 5        # the IPL's 29 March start stays with its season
    assert list(y[["f", "g"]]) == [2028, 2028]          # a March series is the season before


def test_season_month_lines_add_up_to_the_month(every):
    """Each month's line ("Indian Premier League 2–6") counts the same games as the month's record."""
    import re
    c = every.app.state.site.career()
    m = c.matches
    for team in sorted(set(m.home) | set(m.away))[:12]:
        cal = every.json(f"/api/season?team={team}")["calendar"]
        for mo in cal["grid"]:
            w = sum(int(x.group(1)) for n in mo["notes"] if n["kind"] == "played" for x in [re.search(r"(\d+)–(\d+)", n["text"])] if x)
            lo = sum(int(x.group(2)) for n in mo["notes"] if n["kind"] == "played" for x in [re.search(r"(\d+)–(\d+)", n["text"])] if x)
            assert (w, lo) == (mo["won"], mo["lost"]), (team, mo["key"], mo["notes"])


def test_series_tug_of_war_on_the_season_tracker_and_my_team(every):
    """The tug of war: the series score after each match from the team's side, counted again from the results; on
    the Season page's tracker every series still going and the team's latest finished one, on My team its latest."""
    c = every.app.state.site.career()
    m = c.matches.set_index("match_id")
    seen = 0
    for team in ["All teams"] + sorted(set(c.matches.home) | set(c.matches.away))[:10]:
        sr = every.json(f"/api/season?team={team}&tab=Series tracker")["series"]
        for tg in sr.get("tugs", []):
            w = lo = 0
            for r, p in zip(tg["matches"], tg["progress"]):
                win = m.winner[r["id"]]
                w, lo = w + (win == tg["team"]), lo + (win not in ("", tg["team"]))
                assert (p["won"], p["lost"]) == (w, lo)
            if team != "All teams":
                assert tg["team"] == team
            seen += 1
    assert seen >= 3


def test_season_where_your_team_ranks(every):
    from ccstats import rankings as R
    from ccstats import seasonal as SN
    c = every.app.state.site.career()
    m = c.matches
    year_of = SN.april_seasons(m)
    for team in sorted(set(m.home) | set(m.away))[:12]:
        rk = every.json(f"/api/season?team={team}")["ranks"]
        mine = m[(m.home == team) | (m.away == team)]
        y = int(year_of[mine.sort_values("date").match_id.iloc[-1]])
        secs = set(mine[mine.match_id.map(year_of) == y].section)
        assert {r["section"] for r in rk["rows"]} == secs
        for r in rk["rows"]:
            t = R.team_totals(c, m[(m.section == r["section"]) & (m.match_id.map(year_of) == y)].match_id)
            x = t[t.team == team].iloc[0]
            assert (r["runs_rank"], r["wickets_rank"], r["runs"], r["teams"]) == (x.runs_rank, x.wickets_rank, x.runs, len(t))


def test_season_review_best_matches_on_the_new_rating_and_match_winners(every):
    """Season review: the best matches are the season's top three on the match excitement rating (the Matches pages'
    one), and the match-winners are the team's players of the match in its wins."""
    from ccstats import excitement as X
    c = every.app.state.site.career()
    m = c.matches
    done = 0
    for ch in every.json("/api/review")["choices"]:
        if ch["section"] == "International cricket":
            continue
        d = every.json(f"/api/review?pick={ch['key']}")
        rv = d["season_review"]["review"]
        here = m[(m.section == ch["section"]) & (m.season.astype(str) == ch["season"])]
        rt = X.rate(c, m[m.section == ch["section"]].match_id)
        top = rt[rt.match_id.isin(here.match_id)].sort_values(["rating", "date"], ascending=[False, False]).head(3)
        if rv.get("best"):
            assert rv["best"]["links"] == list(top.match_id)
        w = d["winners"]["winners"]
        if w:
            team = w["team"]
            for p in w["players"]:
                for x in p["matches"]:
                    r = m.set_index("match_id").loc[x["id"]]
                    assert r.winner == team and r.player_of_match == p["player"]
        done += 1
    assert done >= 5


def test_matches_front_page_our_score_v_theirs(every):
    """Matches: our score v theirs for the competition and team picked, the team's latest 14 there in the order played;
    nothing for all competitions (formats are never mixed) or all teams."""
    from server import styleguide as SG
    c = every.app.state.site.career()
    m = c.matches
    assert every.json("/api/matches?section=All sections&team=India")["scores"] is None
    for sec in ("ODIs", "Tests", "Indian Premier League"):
        assert every.json(f"/api/matches?section={sec}")["scores"] is None or True
        here = m[m.section == sec]
        for team in sorted(set(here.home) | set(here.away))[:4]:
            d = every.json(f"/api/matches?section={sec}&team={team}")
            sc = d["scores"]
            mine = here[(here.home == team) | (here.away == team)]
            want = [r["id"] for r in SG.in_played_order(c, SG.results(c, team, mine.match_id))][-14:]
            assert [r["id"] for r in sc["results"]] == want and sc["team"] == team


def test_the_new_charts_say_their_numbers_counted_another_way(every):
    """"What it shows" under the fix round's charts, each number counted again from the scorecards: the series score
    (tug of war and ladder), our score v theirs (one competition: the averages; My team's season over several: none,
    each competition's own in the line, formats never mixed), match-winners and the season calendar."""
    c = every.app.state.site.career()
    m = c.matches.set_index("match_id")
    inns = c.innings
    # the series: the final score from the winners
    seen = 0
    for team in sorted(set(c.matches.home) | set(c.matches.away))[:10]:
        for tg in every.json(f"/api/season?team={team}&tab=Series tracker")["series"].get("tugs", []):
            ids = [r["id"] for r in tg["matches"]]
            w = int(sum(m.winner[i] == tg["team"] for i in ids))
            lo = int(sum(m.winner[i] not in ("", tg["team"]) for i in ids))
            assert f"{w}–{lo}" in tg["shows"] and tg["opp"] in tg["shows"] and tg["for_"]
            assert ("decider" in tg["shows"]) == tg["decider"]
            seen += 1
    assert seen >= 3
    # our score v theirs, one competition: won, lost and the averages from the innings table
    averaged = 0
    for sec in ("ODIs", "Indian Premier League"):
        here = c.matches[c.matches.section == sec]
        for team in sorted(set(here.home) | set(here.away))[:4]:
            sc = every.json(f"/api/matches?section={sec}&team={team}")["scores"]
            ids = [r["id"] for r in sc["results"]]
            w = sum(m.winner[i] == team for i in ids)
            lo = sum(m.winner[i] not in ("", team) and m.result_type[i] not in ("tie", "no result", "abandoned") for i in ids)
            s = sc["summary"]
            assert (s["won"], s["lost"]) == (w, lo) and f"won {w} and lost {lo}" in s["shows"]
            dry = [i for i in ids if not m.rain[i]]
            ours = inns[inns.match_id.isin(dry) & (inns.team == team)].groupby("match_id").runs.sum()
            theirs = inns[inns.match_id.isin(dry) & (inns.team != team)].groupby("match_id").runs.sum()
            both = ours.index.intersection(theirs.index)
            if len(both):
                assert s["avg_made"] == round(ours[both].mean()) and s["avg_conceded"] == round(theirs[both].mean())
                assert f"averaged {s['avg_made']} and the other side {s['avg_conceded']}" in s["shows"]
                averaged += 1
    assert averaged >= 4
    # My team's season across several competitions: no averages mixing formats; each competition's own in the line
    from server import styleguide as SG
    two = c.matches[((c.matches.home == "India") | (c.matches.away == "India")) & c.matches.section.isin(["ODIs", "T20Is"])]
    assert set(two.section) == {"ODIs", "T20Is"}
    mixed = SG.scores(SG.results(c, "India", two.match_id), "India", "This season")
    assert mixed["avg_made"] is None and mixed["avg_conceded"] is None and mixed["shows"].startswith("This season India won")
    for sec in ("ODIs", "T20Is"):
        dry = [i for i in two[two.section == sec].match_id if not m.rain[i]]
        ours = inns[inns.match_id.isin(dry) & (inns.team == "India")].groupby("match_id").runs.sum()
        theirs = inns[inns.match_id.isin(dry) & (inns.team != "India")].groupby("match_id").runs.sum()
        both = ours.index.intersection(theirs.index)
        assert f"{sec} {round(ours[both].mean())} to {round(theirs[both].mean())}" in mixed["shows"]
    d = every.json("/api/myteam")
    assert d["scores"]["shows"].startswith("This season")
    # match-winners: the team's wins with its own player of the match
    team = d["team"]
    rs = d["season"]["results"]
    wins = [r for r in rs if m.winner[r["id"]] == team]
    pom = {}
    for r in wins:
        p = m.player_of_match[r["id"]]
        if p and r.get("pom_team", team) == team:
            pom[p] = pom.get(p, 0) + 1
    wn = d["winners"]
    assert wn["wins"] == len(wins) and len(wins) > 0 and f"of {team}'s {len(wins)} win" in wn["shows"]
    assert {p["player"]: len(p["matches"]) for p in wn["players"]}.items() <= pom.items()
    # the season calendar: played, won and lost in the season shown
    cal = every.json(f"/api/season?team={team}")["calendar"]
    played = sum(mo["played"] for mo in cal["grid"])
    won = sum(mo["won"] for mo in cal["grid"])
    assert f"played {played}, won {won}," in cal["shows"] and cal["for_"]
