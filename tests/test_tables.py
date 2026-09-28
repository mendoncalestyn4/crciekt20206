"""League tables, knockout brackets and series."""

from pathlib import Path

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

from ccstats import analysis as A
from ccstats import tables as T
from ccstats.loader import Career
from ccstats.stats import Scope

ROOT = Path(__file__).parent.parent
FIXTURES = sorted((Path(__file__).parent / "fixtures").glob("*.txt"))


@pytest.fixture(scope="module")
def career():
    return Career.build("tables", [(p.name, p.read_bytes()) for p in FIXTURES])


def ids_of(career, section, season):
    return Scope(sections=[section], seasons=[season]).match_ids(career.matches)


def test_ipl_table(career):
    [(label, t, rule)] = T.league_tables(career, ids_of(career, "Indian Premier League", "2026"))
    t = t.set_index("team")
    assert (t.points == 2 * t.won + t.tied + t.no_result).all()
    assert t.won.sum() == t.lost.sum()
    assert t.loc["Gujarat Titans", "points"] == 4 and t.index[0] == "Gujarat Titans"
    league = career.matches[career.matches.match_id.isin(ids_of(career, "Indian Premier League", "2026"))
                            & ~career.matches.knockout]
    nrr = A.team_table(career, league.match_id).set_index("team").nrr
    assert np.allclose(t.nrr.sort_index(), nrr.sort_index())
    assert t.played.sum() == 2 * len(league)  # knockouts never count in the table


def test_county_and_ranji_points(career):
    [(_, cc, rule)] = T.league_tables(career, ids_of(career, "County Championship · Division 1", "2026"))
    assert (cc.points == 16 * cc.won + 8 * cc.drawn + 8 * cc.tied).all() and "bonus" in rule
    for season in career.matches[career.matches.section == "Ranji Trophy"].season.unique():
        for _, t, _ in T.league_tables(career, ids_of(career, "Ranji Trophy", season)):
            assert (t.points >= 6 * t.won + t.drawn).all() and (t.points <= 7 * t.won + 3 * t.drawn + 3 * t.tied + t.no_result).all()


def test_rows_are_in_points_order(career):
    for section in career.matches.section.unique():
        for season in career.matches[career.matches.section == section].season.unique():
            for _, t, _ in T.league_tables(career, ids_of(career, section, season)):
                if t.points.notna().all():
                    assert list(t.points) == sorted(t.points, reverse=True), (section, season)


def test_ipl_bracket_order(career):
    ko = T.knockouts(career, ids_of(career, "Indian Premier League", "2026"))
    assert list(ko.stage) == ["Qualifier 1", "Eliminator", "Qualifier 2", "Final"]
    assert ko.through.iloc[-1] == "Gujarat Titans"
    # the Qualifier 1 loser plays Qualifier 2 against the Eliminator winner
    q1, el, q2 = ko.iloc[0], ko.iloc[1], ko.iloc[2]
    q1_loser = q1.away if q1.through == q1.home else q1.home
    assert {q2.home, q2.away} == {q1_loser, el.through}


def test_tiebreak_winner_goes_through(career):
    ko = T.knockouts(career, career.matches.match_id)
    r = ko[ko.result.str.contains("more wickets left")].iloc[0]
    assert r.winner == "" and r.through == "Karnataka"


def test_series(career):
    s = T.series_table(career, career.matches.match_id).set_index("teams")
    eng = s.loc["England v Pakistan"]
    assert eng.score == "England 3–0 Pakistan" and eng.result == "England won the series"
    assert eng.top_runs == "J Bethell (254)"


def test_competitions_page_every_section_and_season(career):
    runs = 0
    for section in career.matches.section.unique():
        for season in career.matches[career.matches.section == section].season.unique():
            at = AppTest.from_file(str(ROOT / "views" / "competitions.py"), default_timeout=60)
            at.session_state["career_obj"] = career
            at.session_state["cp2_section"] = section
            at.session_state["cp2_season"] = season
            at.run()
            assert not at.exception, (section, season, at.exception)
            runs += 1
    assert runs == len(career.matches.groupby(["section", "season"]))
