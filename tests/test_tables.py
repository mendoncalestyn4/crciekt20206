"""League tables, knockout brackets and series."""

from pathlib import Path

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

from ccstats import analysis as A
from ccstats import tables as T
from ccstats.loader import Career

ROOT = Path(__file__).parent.parent
FIXTURES = sorted((Path(__file__).parent / "fixtures").glob("*.txt"))


@pytest.fixture(scope="module")
def career():
    return Career.build("tables", [(p.name, p.read_bytes()) for p in FIXTURES])


def ids_of(career, event, season):
    """A competition as it's run (the Competitions page works on these), e.g. the ODI World Cup."""
    m = career.matches
    return m[(m.event == event) & (m.season == season)].match_id


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
    for event in career.matches.event.unique():
        for season in career.matches[career.matches.event == event].season.unique():
            for _, t, _ in T.league_tables(career, ids_of(career, event, season)):
                if t.points.notna().all():
                    assert list(t.points) == sorted(t.points, reverse=True), (event, season)


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


def test_bilateral_sections_have_no_points_or_groups(career):
    for event in ("Tests (bilateral series)", "ODIs (bilateral series)", "T20Is (bilateral series)"):
        [(label, t, rule)] = T.league_tables(career, ids_of(career, event, "2026"))
        assert label == "Every team" and t.points.isna().all() and "no league table" in rule
        assert t.won.sum() == (career.matches[career.matches.event == event].winner != "").sum()


def test_series(career):
    s = T.series_table(career, career.matches.match_id).set_index("teams")
    eng = s.loc["England v Pakistan"]
    assert eng.score == "England 3–0 Pakistan" and eng.result == "England won the series"
    assert eng.top_runs == "J Bethell (254)"


def test_competitions_page_every_section_and_season(career):
    runs = 0
    for event in career.matches.event.unique():
        for season in career.matches[career.matches.event == event].season.unique():
            at = AppTest.from_file(str(ROOT / "views" / "competitions.py"), default_timeout=60)
            at.session_state["career_obj"] = career
            at.session_state["cp2_event"] = event
            at.session_state["cp2_season"] = season
            at.run()
            assert not at.exception, (event, season, at.exception)
            runs += 1
    assert runs == len(career.matches.groupby(["event", "season"]))


def test_a_team_is_only_ever_in_one_table(career):
    for event in career.matches.event.unique():
        for season in career.matches[career.matches.event == event].season.unique():
            seen = []
            for _, t, _ in T.league_tables(career, ids_of(career, event, season)):
                seen += list(t.team)
            assert len(seen) == len(set(seen)), (event, season)


def _round_robin(teams, stage, start):
    import itertools
    import pandas as pd
    rows = [dict(home=a, away=b, stage=stage, date=pd.Timestamp(start) + pd.Timedelta(days=i))
            for i, (a, b) in enumerate(itertools.combinations(teams, 2))]
    return rows


def test_groups_from_who_played_whom():
    import pandas as pd
    north, south = ["A", "B", "C", "D"], ["E", "F", "G", "H"]
    named = pd.DataFrame(_round_robin(north, "North Group", "2026-06-01") + _round_robin(south, "South Group", "2026-06-02"))
    got = {label: set(g.home) | set(g.away) for label, g, _ in T._groups(named)}
    assert got == {"North Group": set(north), "South Group": set(south)}
    # the game only said "Group Match": the groups get letters, in order of their first game
    plain = pd.DataFrame(_round_robin(north, "Group", "2026-06-01") + _round_robin(south, "Group", "2026-06-02"))
    got = {label: set(g.home) | set(g.away) for label, g, _ in T._groups(plain)}
    assert got == {"Group A": set(north), "Group B": set(south)}
    # mixed labels for the same group still give one table per group
    mixed = named.copy()
    mixed.loc[mixed.index[:2], "stage"] = "Group"
    got = {label: set(g.home) | set(g.away) for label, g, _ in T._groups(mixed)}
    assert got == {"North Group": set(north), "South Group": set(south)}
    # one league (IPL-style): one table
    assert [l for l, _, _ in T._groups(pd.DataFrame(_round_robin(north + south, "", "2026-04-01")))] == ["League"]
