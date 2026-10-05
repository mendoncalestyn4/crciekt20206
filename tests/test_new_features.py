"""The third wave: partnerships with names, headlines in the order you played,
multi-select filters, and the team, player, series, analytics and planning
features.  Built on a real season the user played (tests/fixtures_2026) and on
the hand-made fixtures."""

import time
from pathlib import Path

import pandas as pd
import pytest

from ccstats import extras as E
from ccstats import partnerships as P
from ccstats import records as RC
from ccstats.loader import Career
from ccstats.stats import Scope, player_tables

ROOT = Path(__file__).parent.parent
FIXTURES = sorted((Path(__file__).parent / "fixtures").glob("*.txt"))
NEW = Path(__file__).parent / "fixtures_2026" / "new_playthrough.zip"
IPL = "Indian Premier League"


@pytest.fixture(scope="module")
def season():
    """44 IPL games and a Bangladesh v New Zealand tour, with the times the game saved them."""
    return Career.build("2026", [(NEW.name, NEW.read_bytes())])


@pytest.fixture(scope="module")
def career():
    return Career.build("x", [(p.name, p.read_bytes()) for p in FIXTURES])


def src(c, name):
    return next(s for s in c.matches.source if s.endswith(name))


# ---------------------------------------------------------------- partnerships
def test_stands_add_up_and_name_the_right_batters(season):
    s = P.stands(season, season.matches.match_id)
    per = s.groupby(["match_id", "innings_no"]).runs.sum()
    inn = season.innings.set_index(["match_id", "innings_no"]).runs
    assert (per == inn.loc[per.index]).all()  # every innings' stands add up to its total
    assert len(per) == len(inn)
    # MI v CSK, 23 Apr: 1-20 2-148 with De Kock 78, Jacks 17: Jacks fell first, De Kock and Varma put on 128
    mid = season.matches.set_index("source").match_id[src(season, "23 apr 2026-mmb v chn (ipl).txt")]
    mi = s[(s.match_id == mid) & (s.team == "Mumbai Indians")].set_index("wicket")
    assert (mi.loc[1, "batter1"], mi.loc[1, "batter2"]) == ("Q DKock", "W Jacks")
    assert (mi.loc[2, "runs"], mi.loc[2, "batter1"], mi.loc[2, "batter2"]) == (128, "Q DKock", "T Varma")
    assert mi.loc[3, "unbroken"] and {mi.loc[3, "batter1"], mi.loc[3, "batter2"]} == {"T Varma", "S Yadav"}
    # every named batter batted for that side in that innings
    bat = season.batting[season.batting.did_bat]
    who = set(zip(bat.match_id, bat.innings_no, bat.player))
    k = s[s.known]
    assert all((m, i, b) in who for m, i, b in zip(k.match_id, k.innings_no, k.batter1))
    assert all((m, i, b) in who for m, i, b in zip(k.match_id, k.innings_no, k.batter2))
    assert (s[s.wicket == 1].known).all()  # the openers are always known


def test_every_named_stand_fits_the_batters_runs(season):
    """No batter in a named stand made more runs than the stands they were in."""
    s = P.stands(season, season.matches.match_id)
    bat = season.batting[season.batting.did_bat].set_index(["match_id", "innings_no", "player"]).runs
    for (mid, no), g in s.groupby(["match_id", "innings_no"]):
        if not g.known.all():
            continue
        for p in set(g.batter1) | set(g.batter2):
            mine = g[(g.batter1 == p) | (g.batter2 == p)]
            assert bat[(mid, no, p)] <= mine.runs.sum(), (mid, no, p)


# ---------------------------------------------------------------- 53 headlines
def test_latest_is_the_last_one_played_not_the_last_date(season):
    """The game saves some scorecards dated months ahead; the latest result is the last one saved."""
    files = [(NEW.name, NEW.read_bytes())]
    now = time.time()
    future = Path(__file__).parent / "fixtures" / "1_oct_2026-ind_v_wi_1st_odi.txt"
    c = Career.build("t", files)
    c = Career.build("t", [(future.name, future.read_bytes(), now - 10 * 86400)], existing=c.texts,
                     times={**c.times})
    order = RC.played_order(c)
    assert order.date.max() == pd.Timestamp("2026-10-01")  # the October ODI is the latest date...
    assert order.iloc[-1].source != future.name  # ...but it was saved before this season's games
    assert order.iloc[0].source == future.name
    news = E.headlines(c, limit=40)
    assert not any("1 Oct" in h for h in news[:3])


def test_every_big_stand_in_recent_games_is_a_headline(season):
    news = E.headlines(season, limit=200)
    recent = RC.played_order(season).tail(10)
    s = P.stands(season, recent.match_id)
    for r in s[s.runs >= 100].itertuples():
        said = f"{r.batter1} and {r.batter2} put on {r.runs}" if r.known else f"{r.team} put on {r.runs}"
        pair = f"{r.batter1} & {r.batter2}" if r.known else r.team
        assert any(said in h or (pair in h and f" {r.runs} " in h) for h in news), r
    assert all(h.endswith(")") for h in news)  # every line names its match
    assert sum("🏅" in h for h in news) <= 3


# ---------------------------------------------------------------- 84 multi-select
def test_combined_choices_add_up_to_the_single_ones(season):
    one = lambda **kw: player_tables(season, Scope(sections=[IPL], **kw))[0].set_index("player")  # noqa: E731
    teams = ["Mumbai Indians", "Delhi Capitals"]
    both = one(teams=teams)
    parts = [one(teams=[t]) for t in teams]
    for col in ("runs", "balls", "innings", "fours", "sixes", "outs"):
        summed = sum(p[col] for p in parts) if False else pd.concat([p[col] for p in parts]).groupby(level=0).sum()
        assert (both[col].sort_index() == summed.loc[both.index].sort_index()).all(), col
    pos = one(positions=[1, 2, 3])
    pieces = pd.concat([one(positions=[i]).runs for i in (1, 2, 3)]).groupby(level=0).sum()
    assert (pos.runs.sort_index() == pieces.loc[pos.index].sort_index()).all()
    ven = one(venues=["home", "away"])
    vp = pd.concat([one(venues=[v]).runs for v in ("home", "away")]).groupby(level=0).sum()
    assert (ven.runs.sort_index() == vp.loc[ven.index].sort_index()).all()
    how = one(how_out=["caught", "bowled"])
    hp = pd.concat([one(how_out=[h]).runs for h in ("caught", "bowled")]).groupby(level=0).sum()
    assert (how.runs.sort_index() == hp.loc[how.index].sort_index()).all()
    # the whole section is the sum of every venue
    allv = one()
    assert allv.runs.sum() == sum(one(venues=[v]).runs.sum() for v in ("home", "away", "neutral"))
    # teams leave the average player alone; positions and venues change it
    base = lambda **kw: player_tables(season, Scope(sections=[IPL], **kw))[3]  # noqa: E731
    assert base(teams=teams).average == base().average
    assert base(positions=[1, 2]).average != base().average
    # two sections combined: every row is the sum of the two
    b2 = player_tables(season, Scope(sections=["ODIs", "T20Is"]))[0].set_index("player").runs
    b_ = pd.concat([player_tables(season, Scope(sections=[x]))[0].set_index("player").runs
                    for x in ("ODIs", "T20Is")]).groupby(level=0).sum()
    assert (b2.sort_index() == b_.loc[b2.index].sort_index()).all()
