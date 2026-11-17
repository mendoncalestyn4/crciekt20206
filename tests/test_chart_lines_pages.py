"""The three lines under every chart on the other pages (design/CHART_LINES.md, the owner's choice of 14 November):
My team, Matches, Opponent preview, Teams, Team v team, Competitions, Season and Season review. Every chart part the
server sends has What it is, Who's best and What it's for; the numbers in "Who's best" are counted again another way.
(Rivalries, Honours and the Planner show tables only: tables keep their own notes.)"""

import pytest

from ccstats.loader import Career
from server import matchpage as MP
from server import myteam as MY
from server import styleguide as SG
from server import teampage as TPG
from server.app import create_app
from serverkit import FIXTURES, Live, make_pc


@pytest.fixture(scope="module")
def career():
    c = Career.build("Test career", [(f.name, f.read_bytes()) for f in FIXTURES])
    c.count_fielding = False   # as the new site opens it
    return c


@pytest.fixture(scope="module")
def every(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("lines")
    pc = make_pc(tmp, files=FIXTURES)
    web = tmp / "dist"
    (web / "assets").mkdir(parents=True)
    (web / "index.html").write_text("<!doctype html><title>Stats Pack</title><div id=root></div>")
    s = Live(create_app(pc[0], web=web, watch_every=0))
    yield s
    s.stop()


def _walk(x, where, found, bad):
    """Every part with chart lines (is_ and for_ beside each other), anywhere in a page's answer."""
    if isinstance(x, dict):
        if "is_" in x and "for_" in x and not x.get("empty"):
            found.append(where)
            for k in ("is_", "best", "for_"):
                if not (isinstance(x.get(k), str) and x[k].strip()):
                    bad.append((where, k))
            if "best_label" in x:
                assert isinstance(x["best_label"], str) and x["best_label"].strip(), where
        for k, v in x.items():
            if isinstance(v, str):
                assert not v.startswith("Couldn't be worked out"), (where, k, v)
            _walk(v, f"{where}/{k}", found, bad)
    elif isinstance(x, list):
        for i, v in enumerate(x):
            _walk(v, f"{where}[{i}]", found, bad)


def _q(**kw) -> str:
    """As test_pages asks: Live.json puts the address right for the web itself."""
    return "?" + "&".join(f"{k}={v}" for k, v in kw.items())


def test_every_chart_on_the_other_pages_has_its_three_lines(every):
    found: list[str] = []
    bad: list = []
    pages = ["/api/myteam", "/api/season", "/api/season" + _q(view="month")]
    fin = every.json("/api/matches")
    for sec in fin["sections"][:4]:
        pages.append("/api/matches" + _q(section=sec, team="England"))
    pages += [f"/api/match/{m['id']}" for m in fin["matches"][::max(1, len(fin["matches"]) // 12)]]
    comp = every.json("/api/competition")
    pages += ["/api/competition" + _q(event=c["event"]) for c in comp["choices"]]
    rv = every.json("/api/review")
    pages += ["/api/review" + _q(pick=c["key"]) for c in rv["choices"]]
    pv = every.json("/api/preview")
    pages += ["/api/preview" + _q(tab=t) for t in pv.get("tabs", [])]
    tm = every.json("/api/team" + _q(team="England"))["page"]
    for sec in [s["section"] for s in tm.get("sections", [])][:3] or [""]:
        for tab in ("Overview", "Season"):
            pages.append("/api/team" + _q(team="England", section=sec, tab=tab))
    tv = every.json("/api/teamvteam")["page"]
    pages.append("/api/teamvteam" + _q(section=tv.get("section", ""), a=tv.get("a", ""), b=tv.get("b", "")))
    for p in pages:
        _walk(every.json(p), p, found, bad)
    assert not bad, bad[:20]
    # every kind of chart turned up somewhere
    ends = {w.rsplit("/", 1)[-1] for w in found}
    for k in ("lines", "record_lines", "runs_lines", "lines_runs", "lines_wickets", "win", "wickets", "race", "mvp",
              "vs_average", "top_bat", "top_bowl", "depth", "stands", "streaks", "venues", "calendar", "tape",
              "bat_first", "bat_dots", "bowl_dots", "above", "saved", "batters", "bowlers", "weak_spot", "how_out",
              "where", "contribution", "how_they_play", "discipline", "strength"):
        assert k in ends, (k, sorted(ends))


def test_my_team_whos_best_counted_again(career):
    m = career.matches
    team = "England"
    d = MY.page(career, team, "", [team], {}, [])
    b = d["block"]
    sec, season = b["section"], b["season"]
    ids = set(m[(m.section == sec) & (m.season.astype(str) == str(season))].match_id)
    bat = career.batting[career.batting.match_id.isin(ids) & (career.batting.team == team)]
    runs = bat.groupby("player").runs.sum().sort_values(ascending=False)
    top = runs[runs == runs.iloc[0]]
    assert any(b["lines_runs"]["best"].startswith(p) for p in top.index[:3])
    assert f"{runs.iloc[0]:,} run" in b["lines_runs"]["best"]
    bowl = career.bowling[career.bowling.match_id.isin(ids) & (career.bowling.team == team)]
    if bowl.wickets.sum():
        w = bowl.groupby("player").wickets.sum().sort_values(ascending=False)
        assert f"{w.iloc[0]:,} wicket" in b["lines_wickets"]["best"]
    # the highest total this season, each competition on its own
    rs = d["season"]["results"]
    inn = career.innings[career.innings.match_id.isin([r["id"] for r in rs]) & (career.innings.team == team)]
    for sec_, x in inn.groupby(inn.match_id.map(m.set_index("match_id").section)):
        assert str(x.runs.max()) in d["scores"]["lines"]["best"], sec_
    # the season ring: the record adds up
    o = [r["outcome"] for r in rs]
    assert d["season"]["record_lines"]["best"].startswith(f"won {o.count('W')} of {len(o)}")


def test_match_biggest_stand_counted_again_from_the_fall_of_wickets(career):
    checked = 0
    for mid in career.matches.match_id[::7]:
        d = MP.page(career, mid, [], {})
        stands = []
        for c in SG.scorecard(career, mid)["cards"]:
            prev = 0
            for f in c["fow"]:
                stands.append(f["score"] - prev)
                prev = f["score"]
            if c["wickets"] < 10:   # the stand still going at the end
                stands.append(c["runs"] - prev)
        if not stands or not d["wickets"]["best"]:
            continue
        assert d["wickets"]["best"].split(" ")[0].rstrip("*") == str(max(stands)), (mid, d["wickets"]["best"], stands)
        checked += 1
    assert checked >= 5


def test_teams_top_scorers_counted_again(career):
    m = career.matches
    sec = m.section.value_counts().index[0]
    team = m[m.section == sec].home.value_counts().index[0]
    d = TPG.page(career, sec, "", team, "all", "Overview")["body"]
    ids = set(m[m.section == sec].match_id)
    bat = career.batting[career.batting.match_id.isin(ids) & (career.batting.team == team)]
    runs = bat.groupby("player").runs.sum().sort_values(ascending=False)
    assert f"{runs.iloc[0]:,} runs" in d["top_bat"]["best"]
    assert d["top_bat"]["best"].split(",")[0] in set(runs[runs == runs.iloc[0]].index)
    # discipline: your team against everyone, the fewest extras a match first
    if d.get("discipline"):
        assert "a match" in d["discipline"]["best"]
