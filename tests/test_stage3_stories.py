"""Stage 3, Player stories (your answers 3, 17, 20, 32): all 15 tabs in the same order, every number equal to the
current site's for the same career (views/stories.py), key figures counted again from the scorecards (heroes in
defeat, one-man shows, quirks, batter v bowler meetings added up over the competitions ticked), no fielding (match
impact is runs and wickets only), and odd addresses never break it."""

from __future__ import annotations

import json

import pytest

from ccstats import demo_league as DL
from ccstats import playerdeep as PD
from ccstats import players as PL
from ccstats.loader import Career
from server import storiespage as SP
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
    return SP.stories_page(c, {k: str(v) for k, v in q.items()}, ["India"])


def ids_of(c, secs, season=""):
    m = c.matches[c.matches.section.isin(secs)]
    return list((m[m.season.astype(str) == season] if season else m).match_id)


def test_fifteen_tabs_in_order(career):
    d = page(career)
    assert d["tabs"] == ["Form guide", "Milestones and records", "Win when they fire", "Heroes in defeat", "Carried the team",
                         "Quirks", "After a hundred", "Pairs", "Player of the Series", "Upsets", "Fastest to", "Match impact",
                         "Badges", "Batter v bowler", "Clutch", "Partnership breakers"]
    order = [x["section"] for x in choices(career)]
    assert d["ticked"] == [order[0]]
    # only Batter v bowler adds competitions up
    assert page(career, section="ODIs|T20Is")["ticked"] == ["ODIs"]
    assert page(career, tab="Batter v bowler", section="ODIs|T20Is")["ticked"] == ["ODIs", "T20Is"]


def test_heroes_in_defeat_counted_again(career):
    d = page(career, tab="Heroes in defeat", section="ODIs")
    ids = set(ids_of(career, ["ODIs"]))
    m = career.matches.set_index("match_id")
    for row, mid in zip(d["bat"]["rows"], d["bat"]["links"]):
        assert mid in ids and m.winner[mid] not in ("", row[3])        # the player's side lost
        b = career.batting[(career.batting.match_id == mid) & (career.batting.player == row[1])]
        assert row[2].split(" ")[0].rstrip("*") == str(int(b.runs.iloc[0]))


def test_one_man_shows_counted_again(league):
    sec = league.matches.section.iloc[0]
    d = page(league, tab="Carried the team", section=sec)
    for row, mid in zip(d["one"]["rows"][:8], d["one"]["links"][:8]):
        b = league.batting[(league.batting.match_id == mid) & (league.batting.player == row[1])].iloc[0]
        inn = league.innings[(league.innings.match_id == mid) & (league.innings.team == b.team) & (league.innings.innings_no == b.innings_no)].iloc[0]
        assert row[3] == str(int(inn.runs)) and row[4] == f"{b.runs / inn.runs * 100:.0f}%"


def test_quirks_counted_again(league):
    sec = league.matches.section.iloc[0]
    d = page(league, tab="Quirks", section=sec)
    b = league.batting[league.batting.match_id.isin(ids_of(league, [sec])) & league.batting.did_bat]
    nineties = b[(b.runs >= 90) & (b.runs <= 99) & b.out].groupby("player").size()
    for row in (d.get("nineties") or {}).get("rows", []):
        assert row[1] == int(nineties[row[0]])
    for row in d["not_outs"]["rows"]:
        x = b[b.player == row[0]]
        assert row[1] == int((~x.out).sum()) and row[2] == len(x)


def test_batter_v_bowler_adds_competitions_up(career):
    secs = ["ODIs", "T20Is"]
    ids = ids_of(career, secs)
    batter = career.batting[career.batting.match_id.isin(ids) & career.batting.did_bat].player.value_counts().index[0]
    d = page(career, tab="Batter v bowler", section="|".join(secs), batter=batter)
    assert d["batter"] == batter and d["one"]
    each = {s: PD.faced(career, ids_of(career, [s]), batter=batter).set_index("name") for s in secs}
    for row in d["one"]["rows"]:
        want = sum(int(f.innings.get(row[0], 0)) for f in each.values())
        assert row[1] == want, row
    bowler = d["one"]["rows"][0][0]
    d = page(career, tab="Batter v bowler", section="|".join(secs), batter=batter, bowler=bowler)
    bv = PD.batter_v_bowler(career, batter, bowler, ids)
    assert d["kpis"][0]["v"] == str(bv["meetings"]) and len(d["meetings"]["rows"]) == len(bv["innings"])
    # a name that isn't in these competitions is let go
    assert page(career, tab="Batter v bowler", section="ODIs", batter="Nobody")["batter"] == ""


def test_match_impact_has_no_fielding(league):
    sec = league.matches.section.iloc[0]
    mi = PD.match_impact(league, ids_of(league, [sec]))
    assert (mi.field == 0).all()
    assert (mi.impact.round(6) == (mi.bat + mi.bowl).round(6)).all()


def test_form_guide_and_milestones_equal_the_current_site(league):
    sec = league.matches.section.iloc[0]
    d = page(league, section=sec)
    fb, fw = PL.form_guide(league, ids_of(league, [sec]))
    assert [r[0] for r in d["bat"]["rows"]] == list(fb.head(30).player)
    d = page(league, tab="Milestones and records", section=sec)
    mw = PL.milestone_watch(league, ids_of(league, [sec]))
    assert len((d.get("miles") or {}).get("rows", [])) == min(25, len(mw))


@pytest.mark.parametrize("which", ["career", "league"])
def test_every_tab_every_competition_and_season(career, league, which):
    c = career if which == "career" else league
    for tab in SP.TABS:
        for sec in c.matches.section.unique():
            for season in [""] + sorted(map(str, c.matches[c.matches.section == sec].season.unique())):
                d = page(c, tab=tab, section=sec, season=season)
                text = json.dumps(d).lower()
                assert d["tab"] == tab
                assert not any(w in text for w in ("catches", "stumping", "caught and bowled"))


@pytest.mark.parametrize("q", [dict(tab="junk"), dict(section="No such cup"), dict(season="abc"),
                               dict(tab="Batter v bowler", batter="x", bowler="y")])
def test_odd_addresses(career, q):
    assert json.dumps(page(career, **q))


def test_empty_career():
    d = SP.stories_page(Career.build("Empty", []), {}, [])
    assert d["none"] and d["choices"] == []
