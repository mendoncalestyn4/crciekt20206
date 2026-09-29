"""Is this total enough, home advantage, season by season, breakout players."""

from pathlib import Path

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

from ccstats import insights as I
from ccstats.demo_league import generate
from ccstats.loader import Career
from ccstats.stats import Scope, player_tables

ROOT = Path(__file__).parent.parent
FIXTURES = sorted((Path(__file__).parent / "fixtures").glob("*.txt"))


@pytest.fixture(scope="module")
def career():
    return Career.build("ins", [(p.name, p.read_bytes()) for p in FIXTURES])


@pytest.fixture(scope="module")
def demo():
    return Career.build("demo", [(n, t.encode()) for n, t in generate()])


def test_total_bands_add_up(career):
    for section in career.matches.section.unique():
        ids = Scope(sections=[section]).match_ids(career.matches)
        t, size = I.total_enough(career, ids)
        finished = career.matches[career.matches.match_id.isin(ids) & (career.matches.result_type != "no result")]
        assert t.matches.sum() == len(finished), section
        assert (t.won + t.lost + t.drawn + t.tied == t.matches).all()
        fi = I.first_innings(career, ids)
        for r in t.itertuples():  # every first-innings score sits in its own band
            assert ((fi.runs >= r.low) & (fi.runs < r.low + size)).sum() == r.matches


def test_chance_with_splits_every_match(career):
    ids = Scope(sections=["Indian Premier League"]).match_ids(career.matches)
    fi = I.first_innings(career, ids)
    for score in (0, 150, 180, 200, 400):
        ch = I.chance_with(career, ids, score)
        assert ch["at_least"]["matches"] + ch["below"]["matches"] == len(fi)
        assert ch["at_least"]["won"] + ch["below"]["won"] == (fi.outcome == "won").sum()


def test_home_advantage(career):
    h = I.home_advantage(career).set_index("section")
    assert "ODI World Cup" not in h.index  # a competition, not a section
    odis = career.matches[(career.matches.section == "ODIs") & ~career.matches.neutral]
    assert h.matches["ODIs"] == len(odis) and not (odis.competition == "ODI World Cup").any()  # World Cup: neutral
    m = career.matches[~career.matches.neutral & (career.matches.result_type != "no result")]
    assert h.matches.sum() == len(m)
    assert h.home_wins.sum() + h.away_wins.sum() == (m.winner != "").sum()
    assert np.allclose(h.home_pct + h.away_pct + h.other / h.matches * 100, 100)


def test_by_season(demo):
    s = I.by_season(demo, "Indian Premier League")
    assert list(s.season) == sorted(demo.matches.season.unique())
    for r in s.itertuples():
        ids = demo.matches[(demo.matches.section == "Indian Premier League") & (demo.matches.season == r.season)].match_id
        inn = demo.innings[demo.innings.match_id.isin(ids)]
        assert abs(r.runs_per_wicket - inn.runs.sum() / inn.wickets.sum()) < 1e-9
        assert r.matches == len(ids)


def test_breakouts_use_each_seasons_own_average(demo):
    seasons = sorted(demo.matches.season.unique())
    bat, bowl = I.breakouts(demo, "Indian Premier League", seasons[-1], 3)
    assert len(bat) and len(bowl)
    assert list(bat.jump) == sorted(bat.jump, reverse=True)
    p = bat.iloc[0]
    now = player_tables(demo, Scope(sections=["Indian Premier League"], seasons=[seasons[-1]]))[0].set_index("player").loc[p.player]
    before = player_tables(demo, Scope(sections=["Indian Premier League"], seasons=[seasons[0]]))[0].set_index("player").loc[p.player]
    assert abs(p.now - now.runs_above_average / now.innings) < 1e-9
    assert abs(p.before - before.runs_above_average / before.innings) < 1e-9
    assert I.breakouts(demo, "Indian Premier League", seasons[0])[0].empty  # nothing earlier to compare with


@pytest.mark.parametrize("which", ["career", "demo"])
def test_insights_page(which, career, demo):
    c = career if which == "career" else demo
    for section in c.matches.section.unique():
        for season in c.matches[c.matches.section == section].season.unique():
            at = AppTest.from_file(str(ROOT / "views" / "insights.py"), default_timeout=60)
            at.session_state["career_obj"] = c
            for k in ("in_t_section", "in_s_section", "in_b_section"):
                at.session_state[k] = section
            at.session_state["in_b_season"] = season
            at.run()
            assert not at.exception, (section, season, at.exception)
