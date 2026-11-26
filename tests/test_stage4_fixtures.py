"""Stage 4, Fixtures (your answers of 26 November): all 8 tabs; schedules only for your teams; a franchise or county
picks its competition; all four ways of adding; a list of recent changes, each with its own undo; the old four goals
plus ten new kinds, each counted again by hand; goals suggested each season; how good the predictions are, each
match's chance worked out from only the matches before it (checked against the site's own chance on a career cut
just before the match); the last time against each opponent; the tournament path. Everything saved in the same file
the current site reads, so the old site sees the same schedule and goals."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from ccstats import demo_league as DL
from ccstats import fixtures as FX
from ccstats import goals as GL
from ccstats import planning as PLN
from ccstats import winprob as WP
from ccstats.loader import Career
from server import fixturespage as FP
from server.app import create_app
from serverkit import FIXTURES, Live, make_pc


@pytest.fixture(scope="module")
def career():
    c = Career.build("Test career", [(f.name, f.read_bytes()) for f in FIXTURES])
    c.count_fielding = False
    return c


@pytest.fixture(scope="module")
def league():
    files = DL.generate((2026, 2027))
    c = Career.build("Demo", [(n, t.encode() if isinstance(t, str) else t) for n, t in files])
    c.count_fielding = False
    return c, files


@pytest.fixture
def pc(tmp_path):
    store, folder, game = make_pc(tmp_path, n=len(FIXTURES), team="England")
    s = Live(create_app(store, web=tmp_path / "nothing", watch_every=0))
    yield s, store
    s.stop()


def post(s, **b):
    status, _, body = s.post("/api/fixtures", b)
    return status, json.loads(body)


# --------------------------------------------------------------------------- the page and the tabs
def test_every_tab_for_your_team_only(pc):
    s, store = pc
    for tab in FP.TABS:
        d = s.json(f"/api/fixtures?tab={tab}")
        assert d["tabs"] == FP.TABS and d["tab"] == tab and d["teams"] == ["England"] and d["team"] == "England"
        assert "body" in d and "missing" not in d["body"], (tab, d["body"])
    # another team in the address: your own team instead (schedules are only for your teams)
    assert s.json("/api/fixtures?team=India")["team"] == "England"
    status, body = post(s, action="add_series", team="India", opponent="England", format="ODI", n=3, venue="home", month="2030-01")
    assert status == 400 and "your own teams" in body["error"]


def test_no_teams_picked_says_so(tmp_path):
    store, _, _ = make_pc(tmp_path, n=5, team="England")
    st = store.load_settings("My career")[1]
    st.my_teams = []
    store.save_settings(st)
    s = Live(create_app(store, web=tmp_path / "nothing", watch_every=0))
    try:
        d = s.json("/api/fixtures")
        assert d["teams"] == [] and "Settings" in d["none"]
    finally:
        s.stop()


# --------------------------------------------------------------------------- adding, changing, deleting, undo
def test_add_change_delete_and_every_change_undoable(pc):
    s, store = pc
    status, b = post(s, action="add_series", team="England", opponent="India", format="Test", n=3, venue="away",
                     month="2030-01")
    assert status == 200 and b["message"].startswith("Added")
    sched = store.load_settings("My career")[1].fixtures
    assert len(sched) == 3 and {r["opponent"] for r in sched} == {"India"} and all(r["venue"] == "away" for r in sched)
    series = sched[0]["series"]
    # the same again is refused, in the old words
    status, b = post(s, action="add_series", team="England", opponent="India", format="Test", n=3, venue="away", month="2030-01")
    assert status == 400 and b["error"] == "That series is already in the schedule."
    # a tournament
    status, _ = post(s, action="add_tournament", team="England", name="T20 World Cup", format="T20I", month="2030-06", games=7)
    assert status == 200
    # typed lines: read first (nothing saved), then added
    status, b = post(s, action="read_lines", team="England", text="Australia 5 ODIs home Mar 2030\nnonsense line")
    assert status == 200 and len(b["will"]) == 1 and b["skipped"]
    assert len(store.load_settings("My career")[1].fixtures) == 3 + 1
    post(s, action="add_lines", team="England", text="Australia 5 ODIs home Mar 2030")
    assert len(store.load_settings("My career")[1].fixtures) == 3 + 1 + 5
    # change the Test series to 2 matches at home
    status, b = post(s, action="change", team="England", series=series, opponent="India", format="Test", n=2,
                     venue="home", month="2030-02")
    assert status == 200
    now = store.load_settings("My career")[1].fixtures
    tests = [r for r in now if r["format"] == "Test"]
    assert len(tests) == 2 and all(r["venue"] == "home" for r in tests)
    # delete the ODIs, then undo each change from the list, newest first, back to nothing
    odi = next(r["series"] for r in now if r["format"] == "ODI")
    post(s, action="delete", team="England", series=odi)
    hist = s.json("/api/fixtures?tab=Change or delete")["history"]
    assert [h["what"].split(":")[0].split(" ")[0] for h in hist][:2] == ["Deleted", "Changed"]
    for h in hist:
        status, b = post(s, action="undo", team="England", id=h["id"])
        assert status == 200, b
    assert store.load_settings("My career")[1].fixtures == []
    # an undone change can't be undone twice
    status, b = post(s, action="undo", team="England", id=hist[0]["id"])
    assert status == 400


def test_undo_of_an_older_change_keeps_the_later_ones(pc):
    s, store = pc
    post(s, action="add_series", team="England", opponent="India", format="Test", n=3, venue="away", month="2030-01")
    post(s, action="add_series", team="England", opponent="Australia", format="ODI", n=3, venue="home", month="2030-03")
    hist = s.json("/api/fixtures?tab=Change or delete")["history"]
    older = hist[-1]
    assert "India" in older["what"]
    post(s, action="undo", team="England", id=older["id"])
    left = store.load_settings("My career")[1].fixtures
    assert {r["opponent"] for r in left} == {"Australia"}


def test_dates_out_of_order_and_bad_input_refused(pc):
    s, _ = pc
    status, b = post(s, action="add_series", team="England", opponent="India", format="ODI", n=2, venue="home",
                     month="2030-01", dates=["2030-01-20", "2030-01-10"])
    assert status == 400 and "match order" in b["error"]
    for bad in (dict(opponent="", format="ODI", n=3), dict(opponent="India", format="Golf", n=3), dict(opponent="India", format="ODI", n=40)):
        status, _ = post(s, action="add_series", team="England", venue="home", month="2030-01", **bad)
        assert status == 400
    status, b = post(s, action="save_table", team="England", rows=[dict(series="x", opponent="India", format="ODI", month="Smarch 2030")])
    assert status == 400 and "Not saved" in b["error"]


def test_the_table_and_the_old_site_read_the_same_file(pc):
    s, store = pc
    rows = [dict(series="v India · 2 ODIs · home · Jan 2030", opponent="India", format="ODI", no=1, venue="home", month="Jan 2030"),
            dict(series="v India · 2 ODIs · home · Jan 2030", opponent="India", format="ODI", no=2, venue="home", month="Jan 2030", date="2030-01-12")]
    status, _ = post(s, action="save_table", team="England", rows=rows)
    assert status == 200
    saved = store.load_settings("My career")[1].fixtures
    assert [r["month"] for r in saved] == ["2030-01", "2030-01"] and saved[1]["date"] == "2030-01-12"
    assert set(FX.COLUMNS) <= set(saved[0])   # every column the current site's table reads


def test_series_note_and_goals_saved(pc):
    s, store = pc
    post(s, action="add_series", team="England", opponent="India", format="Test", n=3, venue="away", month="2030-01")
    series = store.load_settings("My career")[1].fixtures[0]["series"]
    post(s, action="note", team="England", series=series, text="rest the strike bowler")
    assert store.load_settings("My career")[1].notes[f"series::England::{series}"] == "rest the strike bowler"
    status, b = post(s, action="goal_add", team="England", goal=dict(kind="series", series=series))
    assert status == 200
    status, b = post(s, action="goal_add", team="England", goal=dict(kind="series", series=series))
    assert status == 400 and "already" in b["error"]
    status, b = post(s, action="goal_add", team="England", goal=dict(kind="streak", format="Test", season="2027"))
    assert status == 400   # a box left empty
    status, _ = post(s, action="goal_add", team="England", goal=dict(kind="streak", format="Test", season="2027", target=3))
    assert status == 200
    d = s.json("/api/fixtures?tab=Goals")["body"]
    assert len(d["goals"]) == 2 and all(g["label"] for g in d["goals"])
    gid = d["goals"][0]["id"]
    post(s, action="goal_remove", team="England", id=gid)
    assert len(store.load_settings("My career")[1].goals) == 1


def test_forecasts_kept_once_before_ball_one(pc):
    s, store = pc
    post(s, action="add_series", team="England", opponent="India", format="ODI", n=3, venue="home", month="2031-01")
    s.json("/api/fixtures")
    fc = store.load_settings("My career")[1].forecasts
    assert len(fc) == 1 and next(iter(fc.values()))["opponent"] == "India"
    first = dict(fc)
    s.json("/api/fixtures")
    assert store.load_settings("My career")[1].forecasts == first


# --------------------------------------------------------------------------- a franchise or county (answer 3)
def test_a_franchise_picks_its_competition(league):
    c, _ = league
    team = sorted(set(c.matches.home))[0]
    ctx = FP._context(c, team)
    assert not ctx["national"] and ctx["competitions"]
    comp = ctx["competitions"][0]
    assert comp["format"] == "T20" and team not in comp["opponents"] and len(comp["opponents"]) >= 5


# --------------------------------------------------------------------------- the goals, counted again by hand
def test_new_goals_counted_again(career):
    m = career.matches
    team = "England"
    sea = GL.april_seasons_of(career)
    year = int(sea[m[(m.home == team) | (m.away == team)].match_id].iloc[0])
    games = m[(m.format == "Test") & ((m.home == team) | (m.away == team))]
    games = games[[int(sea[i]) == year for i in games.match_id]].sort_values("date")
    outs = [FX._outcome(r, team) for r in games.itertuples()]
    best = cur = 0
    for o in outs:
        if o == "NR":
            continue
        cur = cur + 1 if o == "W" else 0
        best = max(best, cur)
    g = GL.progress(career, dict(kind="streak", team=team, format="Test", season=str(year), target=best))
    assert g["status"] == "achieved" and g["done"] == 1.0
    g = GL.progress(career, dict(kind="streak", team=team, format="Test", season=str(year), target=best + 1))
    assert g["status"] != "achieved"
    home = games[(games.home == team) & ~games.neutral.astype(bool)]
    lost = sum(FX._outcome(r, team) == "L" for r in home.itertuples())
    g = GL.progress(career, dict(kind="home", team=team, format="Test", season=str(year)))
    assert (g["status"] == "missed") == (lost > 0)
    # hundreds and five-fors
    ids = set(games.match_id)
    b = career.batting[career.batting.match_id.isin(ids) & (career.batting.team == team)]
    p = b.groupby("player").runs.max().idxmax()
    n100 = int((b[b.player == p].runs >= 100).sum())
    g = GL.progress(career, dict(kind="hauls", player=p, format="Test", season=str(year), what="hundreds", target=max(n100, 1)))
    assert g["text"].startswith(f"{n100} hundred")
    # top scorer in a competition-season
    sec = "ODIs"
    season = str(m[m.section == sec].season.iloc[0])
    here = m[(m.section == sec) & (m.season.astype(str) == season)]
    tot = career.batting[career.batting.match_id.isin(here.match_id)].groupby("player").runs.sum()
    top = tot.idxmax()
    g = GL.progress(career, dict(kind="topscorer", player=top, section=sec, season=season, what="runs"))
    assert g["done"] == 1.0 and f"{int(tot.max()):,}" in g["text"]
    other = tot.sort_values().index[0]
    g = GL.progress(career, dict(kind="topscorer", player=other, section=sec, season=season, what="runs"))
    assert g["done"] < 1.0 and "behind" in g["text"]
    # a batting average
    bb = career.batting[career.batting.match_id.isin(ids) & (career.batting.player == p) & career.batting.did_bat]
    avg = bb.runs.sum() / bb.out.astype(bool).sum()
    g = GL.progress(career, dict(kind="average", player=p, format="Test", season=str(year), what="batting", target=10))
    assert f"{avg:.2f}" in g["text"]


def test_every_goal_kind_has_a_label_and_a_progress(career):
    for team in ("England", "India", "Karnataka"):
        ch = GL.choices(career, team)
        y = ch["years"][-1]["v"]
        f = ch["formats"][0]
        sec = ch["sections"][0]
        season = ch["seasons"][sec][0]
        p = ch["players"][0]
        opp = ch["opponents"][0]
        for g in [dict(kind="title", section=sec, season=season), dict(kind="top", section=sec, season=season, n=0),
                  dict(kind="top", section=sec, season=season, n=4), dict(kind="home", format=f, season=y),
                  dict(kind="no1", section=sec), dict(kind="rival", opponent=opp, format=f, season=y),
                  dict(kind="away", format=f, season=y), dict(kind="streak", format=f, season=y, target=3),
                  dict(kind="topscorer", player=p, section=sec, season=season, what="wickets"),
                  dict(kind="average", player=p, format=f, season=y, what="bowling", target=30),
                  dict(kind="hauls", player=p, format=f, season=y, what="fivefors", target=2)]:
            g = dict(g, team=team)
            assert FX.goal_label(g) != "Goal"
            pg = FX.goal_progress(career, None, g)
            assert 0 <= pg["done"] <= 1 and pg["status"] in FP.BADGE | {"unknown": ""} and pg["text"], (g, pg)


def test_the_old_site_shows_new_goals_too(career):
    """A goal made on the new site shows on the old site's Goals tab (the same engine function)."""
    g = dict(kind="hauls", team="England", player="J Root", format="Test", season="2026", what="hundreds", target=2)
    assert "J Root" in FX.goal_label(g) and FX.goal_progress(career, None, g)["text"]


# --------------------------------------------------------------------------- the prediction record
def test_chance_before_a_match_is_the_sites_chance_from_the_matches_before_it(league):
    """Counted another way: a career cut just before the match, asked for its chance the site's own way, gives the
    same chance as the record worked out on the whole career."""
    c, files = league
    team = sorted(set(c.matches.home))[0]
    rec = WP.chances_before(c, team)
    assert len(rec)
    m = c.matches.sort_values(["date", "match_id"]).reset_index(drop=True)
    checked = 0
    for k in (len(rec) // 3, len(rec) // 2, len(rec) - 1):
        r = rec.iloc[k]
        pos = int(m.index[m.match_id == r.match_id][0])
        before = set(m.source.iloc[:pos])    # the scorecard files of every match played before it
        part = Career.build("Part", [(n, t.encode() if isinstance(t, str) else t) for n, t in files if n in before])
        part.count_fielding = False
        ids = part.matches[part.matches.section == r.section].match_id
        p = WP.predict(part, ids, team, r.opponent, r.venue)
        assert abs(p["win"] - r.win) < 1e-6 and abs(p["lose"] - r.lose) < 1e-6, (k, p, r)
        checked += 1
    assert checked == 3


def test_prediction_record_counts(league):
    c, _ = league
    team = sorted(set(c.matches.home))[0]
    rec = WP.chances_before(c, team)
    decided = rec[rec.outcome.isin(["W", "L"])]
    right = int(((decided.win >= decided.lose) == (decided.outcome == "W")).sum())
    pr = WP.prediction_record(c, team)
    assert pr["total"]["games"] == len(decided) and pr["total"]["right"] == right


# --------------------------------------------------------------------------- last meeting and the tournament path
def test_last_meeting_counted_again(career):
    m = career.matches
    g = m[(m.format == "ODI") & (((m.home == "England") & (m.away == "India")) | ((m.home == "India") & (m.away == "England")))]
    lm = PLN.last_meeting(career, "England", "India", "ODI")
    if g.empty:
        assert lm is None
        return
    last = g.sort_values(["date", "match_id"]).iloc[-1]
    assert lm["match_id"] == last.match_id
    b = career.batting[career.batting.match_id == last.match_id]
    assert lm["top"]["runs"] == int(b.groupby("player").runs.sum().max())


def test_tournament_path_mid_league(league):
    _, files = league
    half = Career.build("Half", [(n, t.encode() if isinstance(t, str) else t) for n, t in files][: len(files) // 4])
    m = half.matches
    ev, se = m.event.iloc[0], m.season.iloc[0]
    for team in sorted(set(m.home))[:4]:
        p = PLN.tournament_path(half, team, ev, se)
        assert p is not None and 0 <= p["playoffs"] <= 100 and p["left"] >= 0
        assert all(0 <= x["chance"] <= 100 for x in p["by_wins"])
        # more wins never makes going through less likely (up to the noise of the runs)
        ch = [x["chance"] for x in p["by_wins"]]
        assert all(b >= a - 8 for a, b in zip(ch, ch[1:])), ch
        text = FP._path_text(team, p)
        assert text["lines"] and "go through" in text["lines"][0]


def test_every_tab_on_the_demo_league_and_odd_input(league, tmp_path):
    c, _ = league
    team = sorted(set(c.matches.home))[0]

    class S:   # settings as saved
        fixtures, goals, notes, forecasts, fixture_changes = [], [], {}, {}, []
    for tab in FP.TABS:
        d = FP.page(c, dict(tab=tab, team=team), [team], S())
        assert json.dumps(d) and "missing" not in d.get("body", {}), (tab, d.get("body"))
    for q in (dict(tab="x"), dict(team="Nobody"), dict(season="junk", tab="Calendar")):
        assert json.dumps(FP.page(c, q, [team], S()))
