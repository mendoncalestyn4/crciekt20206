"""Stage 3, Team leaders (agreed 13 November, your answer 13): each team's top two by share of its runs off the bat and
of its wickets, counted again from the scorecards; all teams with yours first then A to Z; opening on your team; the
crossed-out rule; formats never mixed."""

from __future__ import annotations

import json

import pytest

from ccstats import demo_league as DL
from ccstats import teamleaders as TL
from ccstats.loader import Career
from server import leaderteams as LT
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


def test_top_two_counted_again(career):
    m = career.matches[career.matches.section == "ODIs"]
    for team in sorted(set(m.home) | set(m.away)):
        ids = set(m[(m.home == team) | (m.away == team)].match_id)
        b = career.batting[career.batting.match_id.isin(ids) & (career.batting.team == team)]
        w = career.bowling[career.bowling.match_id.isin(ids) & (career.bowling.team == team)]
        runs = b[b.did_bat].groupby("player").runs.sum()
        wk = w.groupby("player").wickets.sum()
        played = b.groupby("player").match_id.nunique()
        x = TL.leaders(career, "ODIs", None, team)
        want = sorted(((r / runs.sum() * 100, int(played[p]), p) for p, r in runs.items() if r > 0), key=lambda t: (-t[0], -t[1], t[2]))[:2]
        assert [r["player"] for r in x["runs"]] == [p for _, _, p in want]
        assert all(r["value"] == int(runs[r["player"]]) and r["matches"] == int(played[r["player"]]) for r in x["runs"])
        if wk.sum():
            top = sorted(((v, int(played.get(p, 0)), p) for p, v in wk.items() if v > 0), key=lambda t: (-t[0], -t[1], t[2]))[:2]
            assert [r["player"] for r in x["wickets"]] == [p for _, _, p in top]


def test_all_teams_yours_first_and_opening_on_yours(career):
    d = LT.page(career, dict(section="ODIs"), ["India"])
    assert d["picked"] == ["India"] and [b["team"] for b in d["blocks"]] == ["India"]
    d = LT.page(career, dict(section="ODIs", teams="all"), ["India"])
    teams = [b["team"] for b in d["blocks"]]
    assert teams[0] == "India" and teams[1:] == sorted(teams[1:]) and d["all"]


def test_crossed_out_when_missing_the_last_two_seasons(league):
    sec = league.matches.section.iloc[0]
    m = league.matches[league.matches.section == sec]
    team = m.home.iloc[0]
    seasons = sorted(m.season.unique())
    mine = m[(m.home == team) | (m.away == team)]
    b = league.batting[league.batting.match_id.isin(set(mine.match_id)) & (league.batting.team == team)]
    recent = set(b[b.match_id.isin(set(mine[mine.season.isin(seasons[-2:])].match_id))].player)
    assert TL.gone(league, sec, team) == set(b.player) - recent


def test_every_competition_and_season(career, league):
    for c in (career, league):
        for sec in c.matches.section.unique():
            for season in [""] + sorted(map(str, c.matches[c.matches.section == sec].season.unique())):
                assert json.dumps(LT.page(c, dict(section=sec, season=season, teams="all"), ["India"]))
    assert LT.page(Career.build("E", []), {}, [])["none"]
