"""The second wave: streaks, journey, Player of the Match, duos, rivalries, on pace,
discipline, chasing, par, all-round matches, team style, opponent preview,
honours and headlines.  Every figure is checked against a count made another way."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from ccstats import analysis as A
from ccstats import extras as E
from ccstats.demo_league import generate
from ccstats.loader import Career
from ccstats.stats import Scope

ROOT = Path(__file__).parent.parent
FIXTURES = sorted((Path(__file__).parent / "fixtures").glob("*.txt"))
IPL = "Indian Premier League"


@pytest.fixture(scope="module")
def career():
    return Career.build("x", [(p.name, p.read_bytes()) for p in FIXTURES])


@pytest.fixture(scope="module")
def demo_files():
    return [(n, t.encode()) for n, t in generate()]


@pytest.fixture(scope="module")
def demo(demo_files):
    return Career.build("demo", demo_files)


@pytest.fixture(scope="module")
def half_season(demo, demo_files):
    """The demo league with the second season cut off after 25 matches (a season in progress)."""
    m = demo.matches.sort_values("date")
    s2 = sorted(m.season.unique())[-1]
    keep = set(m[m.season != s2].source) | set(m[m.season == s2].source.head(25))
    return Career.build("half", [(n, b) for n, b in demo_files if n in keep])


def ids(c, section=IPL, season=None):
    return Scope(sections=[section], seasons=[season] if season else []).match_ids(c.matches)


# ---------------------------------------------------------------- 5
def test_streaks_by_hand():
    inns = pd.DataFrame({"runs": [25, 30, 5, 0, 0, 60, 70, 21], "out": [True] * 8})
    s = {r["streak"]: (r["longest"], r["current"]) for r in E.batting_streaks(inns, "t20")}
    assert s["Innings in a row with 20+"] == (3, 3)
    assert s["Innings in a row with 50+"] == (2, 0)
    assert s["Ducks in a row"] == (2, 0)
    assert s["Innings in a row without a duck"] == (3, 3)
    b = {r["streak"]: (r["longest"], r["current"]) for r in E.bowling_streaks(pd.DataFrame({"wickets": [1, 2, 0, 3, 3, 1]}))}
    assert b["Innings in a row taking a wicket"] == (3, 3) and b["Wicketless innings in a row"] == (1, 0)
    assert b["Innings in a row with 3+ wickets"] == (2, 0)


def test_journey_adds_up(career):
    j = E.journey(career, "S Gill")
    b = career.batting[(career.batting.player == "S Gill") & career.batting.did_bat]
    assert j.runs.sum() == b.runs.sum() and j.matches.sum() == b.match_id.nunique()
    assert list(j["first"]) == sorted(j["first"])


# ---------------------------------------------------------------- 9
def test_player_of_match(demo):
    i = ids(demo)
    p = E.player_of_match(demo, i)
    m = demo.matches[demo.matches.match_id.isin(i)]
    assert p.awards.sum() == (m.player_of_match != "").sum()
    assert p.finals.sum() == ((m.stage == "Final") & (m.player_of_match != "")).sum()
    assert list(p.awards) == sorted(p.awards, reverse=True)


# ---------------------------------------------------------------- 11
def test_duos_account_for_every_credited_catch(demo):
    i = ids(demo)
    duo, cab = E.deadly_duos(demo, i)
    f = demo.fielding[demo.fielding.match_id.isin(i) & demo.fielding.resolved]
    assert duo.wickets.sum() + cab.wickets.sum() + ((f.player == f.bowler) & (f.kind != "caught")).sum() == len(f)
    assert (duo.player != duo.bowler).all()


# ---------------------------------------------------------------- 12
def test_rivalries(demo):
    i = ids(demo)
    rv = E.rivalries(demo, i)
    m = demo.matches[demo.matches.match_id.isin(i)]
    assert rv.played.sum() == len(m)
    assert (rv.wins_a + rv.wins_b + rv.other == rv.played).all()
    r = rv.iloc[0]
    games = m[((m.home == r.team_a) & (m.away == r.team_b)) | ((m.home == r.team_b) & (m.away == r.team_a))]
    runs, wkts = E.rivalry_players(demo, i, r.team_a, r.team_b)
    assert runs.runs.sum() == demo.batting[demo.batting.match_id.isin(games.match_id)].runs.sum()
    assert wkts.wickets.sum() == demo.bowling[demo.bowling.match_id.isin(games.match_id)].wickets.sum()


# ---------------------------------------------------------------- 13
def test_on_pace(demo, half_season):
    assert E.season_in_progress(demo, IPL) is None  # both seasons finished
    info = E.season_in_progress(half_season, IPL)
    assert info is not None and info[1] == 25
    p = E.on_pace(half_season, IPL)
    assert len(p) and set(p.what) == {"runs", "wickets"}
    s2 = info[0]
    m = half_season.matches
    prev = m[(m.section == IPL) & (m.season != s2)]
    r = p[p.what == "runs"].iloc[0]
    played = int(((m.season == s2) & ((m.home == r.team) | (m.away == r.team))).sum())
    full = int(((prev.home == r.team) | (prev.away == r.team)).sum())
    assert r.matches == played and r.projected == round(r.so_far / played * full)


# ---------------------------------------------------------------- 15
def test_discipline(demo, career):
    for c in (demo, career):
        i = c.matches.match_id
        d = E.discipline(c, i)
        assert d.extras.sum() == c.innings.extras.sum()
        assert (d.extras == d.wides + d.no_balls + d.byes + d.leg_byes).all()


# ---------------------------------------------------------------- 16
def test_chasing(demo):
    i = ids(demo)
    ch = E.chasing(demo, i, min_innings=1)
    r = ch.iloc[0]
    b = demo.batting[(demo.batting.player == r.player) & demo.batting.did_bat & demo.batting.match_id.isin(i)
                     & (demo.batting.innings_no == 2)]
    m = demo.matches.set_index("match_id")
    b = b[m.loc[b.match_id, "winner"].values != ""]  # ties and no results aren't won or lost chases
    assert r.innings == len(b) and r.runs == b.runs.sum()
    assert r.won_innings == int((m.loc[b.match_id, "winner"].values == b.team.values).sum())


# ---------------------------------------------------------------- 22
def test_par(demo):
    i = ids(demo)
    p = E.par_by_wicket(demo, i).set_index("wicket")
    f = demo.fow[demo.fow.match_id.isin(i)]
    assert p.loc[1, "par"] == f[f.wicket == 1].score.median() and p.loc[3, "innings"] == (f.wicket == 3).sum()


# ---------------------------------------------------------------- 25
def test_all_round(demo):
    i = ids(demo)
    ar = E.all_round_matches(demo, i)
    inn = demo.innings[demo.innings.match_id.isin(i)]
    rpw = inn.runs.sum() / inn.wickets.sum()
    assert np.allclose(ar.score, ar.runs + ar.wickets * rpw)
    assert (ar.runs > 0).all() and (ar.wickets > 0).all()
    r = ar.iloc[0]
    assert r.runs == demo.batting[(demo.batting.match_id == r.match_id) & (demo.batting.player == r.player)].runs.sum()


# ---------------------------------------------------------------- 27
def test_team_style(demo):
    i = ids(demo)
    s = E.team_style(demo, i).set_index("team")
    b = demo.batting[demo.batting.match_id.isin(i) & demo.batting.did_bat & (demo.batting.team == "Mumbai Indians")]
    assert abs(s.loc["Mumbai Indians", "boundary_pct"] - (4 * b.fours + 6 * b.sixes).sum() / b.runs.sum() * 100) < 1e-9
    assert (s.bowled_lbw_pct + s.caught_pct <= 100 + 1e-9).all()


# ---------------------------------------------------------------- 32
def test_opponent_preview(demo):
    i = ids(demo)
    pv = E.opponent_preview(demo, i, "Mumbai Indians")
    assert abs(pv["how_out"].sum() - 100) < 1e-9
    assert pv["innings"] == int(((demo.innings.team == "Mumbai Indians") & demo.innings.match_id.isin(i)).sum())
    assert len(pv["recent"]) == 5 and pv["batters"].runs.is_monotonic_decreasing


# ---------------------------------------------------------------- 37
def test_honours(demo, career, half_season):
    h = E.honours(demo).set_index("season")
    m = demo.matches
    for season, r in h.iterrows():
        f = m[(m.season == season) & (m.stage == "Final")].iloc[0]
        assert r.champions == f.winner and r.how == "won the final" and r.final_potm == f.player_of_match
    hc = E.honours(career)
    assert not hc.section.str.contains("bilateral").any()
    assert "Ranji Trophy" not in set(hc.section)  # it has knockouts but no final in these files
    cc = hc[hc.section.str.startswith("County")]
    assert cc.how.str.contains("so far").all()  # only one season: still in progress
    hh = E.honours(half_season)
    assert len(hh) == 1  # the unfinished season has no champion yet


# ---------------------------------------------------------------- 23
def test_headlines(career):
    news = E.headlines(career, limit=50)
    recent = career.matches.sort_values(["date", "match_id"]).tail(10)
    b = career.batting[career.batting.match_id.isin(recent.match_id) & (career.batting.runs >= 100)]
    for r in b.itertuples():
        assert any(f"{r.player} hits {r.runs}" in h for h in news), r.player
    assert all(isinstance(h, str) and h for h in news)


# ---------------------------------------------------------------- pages
PAGES = {"hall_of_fame.py": ["hf_section"], "rivalries.py": ["rv_section"], "opponent.py": ["op_section"],
         "records.py": ["rc_section"]}


@pytest.mark.parametrize("page", list(PAGES))
@pytest.mark.parametrize("which", ["career", "demo", "half"])
def test_new_pages_every_section(page, which, career, demo, half_season):
    c = {"career": career, "demo": demo, "half": half_season}[which]
    for section in c.matches.section.unique():
        at = AppTest.from_file(str(ROOT / "views" / page), default_timeout=90)
        at.session_state["career_obj"] = c
        for k in PAGES[page]:
            at.session_state[k] = section
        at.run()
        assert not at.exception, (page, which, section, at.exception)


@pytest.mark.parametrize("page", ["honours.py", "home.py"])
@pytest.mark.parametrize("which", ["career", "demo", "half"])
def test_pages_without_choices(page, which, career, demo, half_season):
    c = {"career": career, "demo": demo, "half": half_season}[which]
    at = AppTest.from_file(str(ROOT / "views" / page), default_timeout=90)
    at.session_state["career_obj"] = c
    at.run()
    assert not at.exception, (page, which, at.exception)


def test_opponent_with_my_team(demo):
    at = AppTest.from_file(str(ROOT / "views" / "opponent.py"), default_timeout=90)
    at.session_state["career_obj"] = demo
    at.session_state["op_section"] = IPL
    at.session_state["op_opp"] = "Mumbai Indians"
    at.session_state["op_mine"] = "Chennai Super Kings"
    at.run()
    assert not at.exception


@pytest.mark.parametrize("page,keys", [("teams.py", {"tm_section": IPL, "tm_team": "Mumbai Indians"}),
                                       ("player.py", {"pl_player": "R Gaikwad"}),
                                       ("player.py", {"pl_player": "K Rabada"}),
                                       ("match.py", {"mt_section": IPL})])
def test_updated_pages(page, keys, demo):
    at = AppTest.from_file(str(ROOT / "views" / page), default_timeout=90)
    at.session_state["career_obj"] = demo
    for k, v in keys.items():
        at.session_state[k] = v
    if page == "match.py":
        at.session_state["mt_match"] = demo.matches.match_id.iloc[-1]
    at.run()
    assert not at.exception, (page, at.exception)
