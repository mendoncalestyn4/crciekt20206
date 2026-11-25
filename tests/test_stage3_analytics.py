"""Stage 3, Analytics (your answers 2 and 14 of 13 November): every number equals the current site's for the same
career (the same engine sums, views/analytics.py), with key figures counted again a second way from the scorecards:
runs above expected, the fair averages' plain average, wins against expected, the match-winners chart (players of the
match in the team's wins), the style maps' corners and bat or bowl first. Odd addresses never break it; no fielding."""

from __future__ import annotations

import json

import pytest

from ccstats import demo_league as DL
from ccstats import players as PL
from ccstats.loader import Career
from ccstats.stats import Scope, player_tables
from server import analyticspage as AP
from server.teampage import choices
from serverkit import FIXTURES


@pytest.fixture(scope="module")
def career():
    c = Career.build("Test career", [(f.name, f.read_bytes()) for f in FIXTURES])
    c.count_fielding = False
    return c


@pytest.fixture(scope="module")
def league():
    files = DL.generate((2026, 2027, 2028))
    c = Career.build("Demo", [(n, t.encode() if isinstance(t, str) else t) for n, t in files])
    c.count_fielding = False
    return c


def page(c, **q):
    return AP.analytics_page(c, {k: str(v) for k, v in q.items()}, ["India"])


def ids_of(c, sec, season=""):
    m = c.matches[c.matches.section == sec]
    return list((m[m.season.astype(str) == season] if season else m).match_id)


def test_tabs_order_and_pickers(career):
    d = page(career)
    order = [x["section"] for x in choices(career)]
    assert d["tabs"] == AP.TABS and d["section"] == order[0] and d["season"] == ""
    d = page(career, section="ODIs|T20Is", season="1999")
    assert d["section"] == "ODIs" and d["season"] == ""


def test_runs_above_expected_counted_again(league):
    sec = league.matches.section.iloc[0]
    d = page(league, section=sec)
    rae = PL.runs_above_expected(league, ids_of(league, sec))
    assert [b["label"] for b in d["rae"]["rows"]] == list(rae.head(12).player)
    # the runs: every innings of the player in these matches, added up from the scorecards
    for r in d["rae_table"]["rows"][:5]:
        b = league.batting[league.batting.match_id.isin(ids_of(league, sec)) & league.batting.did_bat & (league.batting.player == r[0])]
        assert r[3] == int(b.runs.sum()) and r[2] == len(b)
    # runs above expected add up to nothing over everyone (each situation's expected is its own average)
    allr = PL.runs_above_expected(league, ids_of(league, sec), min_innings=1)
    assert allr.above.sum() == pytest.approx(0, abs=1e-6)


def test_fair_averages_plain_average_counted_again(league):
    sec = league.matches.section.iloc[0]
    d = page(league, tab="Fair averages", section=sec)
    ids = ids_of(league, sec)
    for row, parts in zip(d["bat"]["rows"][:5], d["bat"]["parts"][:5]):
        b = league.batting[league.batting.match_id.isin(ids) & league.batting.did_bat & (league.batting.player == row[0])]
        outs = int(b.out.sum()) if "out" in b else int((b.how_out != "not out").sum())
        assert parts["runs"] == int(b.runs.sum()) and parts["outs"] == outs
        assert row[2] == f"{b.runs.sum() / outs:.2f}"
    for row, parts in zip(d["bowl"]["rows"][:5], d["bowl"]["parts"][:5]):
        w = league.bowling[league.bowling.match_id.isin(ids) & (league.bowling.player == row[0])]
        assert parts["bruns"] == int(w.runs.sum()) and parts["wkts"] == int(w.wickets.sum())


def test_what_wins_and_luck_equal_the_current_site(league):
    sec = league.matches.section.iloc[0]
    ids = ids_of(league, sec)
    d = page(league, tab="What wins games", section=sec)
    ww = PL.what_wins(league, ids)
    assert [r["label"] for r in d["wins"]["rows"]] == list(ww.measure)
    d = page(league, tab="Luck", section=sec)
    ew = PL.expected_wins(league, ids)
    for bar, r in zip(d["luck"]["rows"], ew.itertuples()):
        m = league.matches[league.matches.match_id.isin(ids)]
        won = int((m.winner == r.team).sum())
        assert bar["label"] == r.team and f"won {won} of" in bar["note"]
        assert bar["value"] == pytest.approx(r.won - r.expected, abs=0.01)


def test_match_winners_chart_counted_again(career):
    d = page(career, tab="Match-winners", section="ODIs")
    assert d["team"] == "India"
    w = d["winners"]
    m = career.matches[(career.matches.section == "ODIs") & (career.matches.winner == "India")]
    assert w["wins"] == len(m)
    got = {p["player"]: len(p["matches"]) for p in w["players"]}
    for p, n in got.items():
        x = m[m.player_of_match == p] if "player_of_match" in m else None
        if x is not None:
            assert len(x) == n
    assert sum(got.values()) + w["others"] == w["wins"]
    # any team picked; an unknown one falls back
    assert page(career, tab="Match-winners", section="ODIs", team="England")["team"] == "England"
    assert page(career, tab="Match-winners", section="ODIs", team="Nobody")["team"] == "India"


def test_style_map_corners(league):
    sec = league.matches.section.iloc[0]
    d = page(league, tab="Style maps", section=sec)
    _, _, _, base = player_tables(league, Scope(sections=[sec]))
    near = lambda p, q: abs(p["x"] - q["x_ref"]) < 0.02 or abs(p["y"] - q["y_ref"]) < 0.02   # noqa: E731 - on a line (sent rounded)
    for p in d["bat"]["points"]:
        if near(p, d["bat"]):
            continue
        top_right = p["x"] >= d["bat"]["x_ref"] and p["y"] >= d["bat"]["y_ref"]
        assert (p["style"] == "Scores lots, scores fast") == top_right
    for p in d["bowl"]["points"]:
        if near(p, d["bowl"]):
            continue
        best = p["x"] <= d["bowl"]["x_ref"] and p["y"] <= d["bowl"]["y_ref"]
        assert (p["style"] == "Wicket-taker and tight") == best
    assert d["bat"]["x_ref"] == pytest.approx(base.average, abs=0.01)


def test_bat_or_bowl_first_counted_again(league):
    sec = league.matches.section.iloc[0]
    d = page(league, tab="Bat or bowl first?", section=sec)
    m = league.matches[league.matches.match_id.isin(ids_of(league, sec)) & (league.matches.winner != "")]
    first = league.innings[league.innings.match_id.isin(m.match_id) & (league.innings.innings_no == 1)].set_index("match_id").team
    won = int((m.set_index("match_id").winner == first.reindex(m.match_id)).sum())
    assert f"won {round(won / len(m) * 100)}% of {len(m)} decided games" in d["toss"]["line"]


@pytest.mark.parametrize("which", ["career", "league"])
def test_every_tab_every_competition_and_season(career, league, which):
    c = career if which == "career" else league
    for tab in AP.TABS:
        for sec in c.matches.section.unique():
            for season in [""] + sorted(map(str, c.matches[c.matches.section == sec].season.unique())):
                d = page(c, tab=tab, section=sec, season=season)
                text = json.dumps(d).lower()
                assert d["tab"] == tab and "nan" not in text.replace("nanc", "")
                assert not any(w in text for w in ("catch", "caught", "stumping"))


@pytest.mark.parametrize("q", [dict(tab="junk"), dict(section="No such cup"), dict(season="abc"), dict(team="Nobody", tab="Match-winners")])
def test_odd_addresses(career, q):
    assert json.dumps(page(career, **q))


def test_empty_career():
    d = AP.analytics_page(Career.build("Empty", []), {}, [])
    assert d["none"] and d["choices"] == []
