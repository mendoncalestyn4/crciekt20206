"""What a player managing a country found: Team vs team's Home / Away, the Teams page's Home / Away for the whole
page, Opponent preview's team and opponent boxes, the next opponent from the schedule, the season calendar (April
to March, with the series still to come), every page opening on your team, and the question that asks which teams
you play as once and saves the answer."""
import json
from pathlib import Path

import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from ccstats import fixtures as F
from ccstats import teamplay as TP
from ccstats.loader import Career
from ccstats.local import CareerSettings, CareerStore
from ccstats.stats import Scope
from ui import calendar_view as CV

ROOT = Path(__file__).parent.parent
FIXTURES = sorted((Path(__file__).parent / "fixtures").glob("*.txt"))


@pytest.fixture(scope="module")
def career():
    return Career.build("User round", [(p.name, p.read_bytes()) for p in FIXTURES])


def page(name, c, mine=("India",), fx=None, **state):
    at = AppTest.from_file(str(ROOT / "views" / name), default_timeout=240)
    at.session_state["career_obj"] = c
    at.session_state[f"my_teams::{c.name}"] = list(mine)
    at.session_state[f"fixtures::{c.name}"] = fx or []
    for k, v in state.items():
        at.session_state[k] = v
    return at


def ok(at):
    assert not at.exception, [e.message for e in at.exception]
    assert not [w for w in at.warning if "couldn't be shown" in w.value], [w.value for w in at.warning]
    assert not at.error, [e.value for e in at.error]


def text(at) -> str:
    return " ".join([m.value for m in at.markdown] + [c.value for c in at.caption] + [i.value for i in at.info])


def seg(at, label):
    return next(s for s in at.main.segmented_control if s.label == label)


# --------------------------------------------------------------------------- Team vs team: where
def test_team_vs_team_where_is_one_side_at_home_and_the_other_away(career):
    m = career.matches
    at = page("team_vs_team.py", career, tv_section="ODIs", tv_a="India", tv_b="England").run()
    ok(at)
    where = seg(at, "Where")
    assert list(where.options)[:3] == ["All venues", "At India's home", "At England's home"]
    # all their matches, at England's home: India's away games against England's home games
    where.set_value("At England's home").run()
    ok(at)
    odis = m[m.section == "ODIs"]
    india_away = odis[(odis.away == "India") & ~odis.neutral]
    england_home = odis[(odis.home == "England") & ~odis.neutral]
    tiles = " ".join(m.value for m in at.markdown if "class='kpi'" in m.value)
    assert tiles.count("<span>Played</span><strong>") == 2
    assert f"<span>Played</span><strong>{len(india_away)}</strong>" in tiles.split("England")[0]
    assert f"<span>Played</span><strong>{len(england_home)}</strong>" in tiles.split("England", 1)[1]
    # only against each other, at England's home: their meetings there (both sides count the same games)
    seg(at, "Matches").set_value("Only against each other").run()
    ok(at)
    meet = odis[(odis.home == "England") & (odis.away == "India")]
    assert len(meet) >= 1
    assert f"{len(meet)} meeting" in text(at)
    # at India's home they haven't met in ODIs: a clear message naming both, never a dead "no matches"
    seg(at, "Where").set_value("At India's home").run()
    ok(at)
    assert "India and England haven't met at India's home yet" in text(at)


def test_team_vs_team_starts_on_your_team(career):
    at = page("team_vs_team.py", career, mine=("India",), tv_section="ODIs").run()
    ok(at)
    a = next(s for s in at.main.selectbox if s.label == "Team A")
    assert a.value == "India"


def test_scope_neutral_venue(career):
    m = career.matches
    ids = Scope(sections=["ODIs"], team="England", venue="neutral").match_ids(m)
    assert set(m[m.match_id.isin(ids)].neutral) <= {True}


# --------------------------------------------------------------------------- Teams page: Home / Away for the whole page
def test_teams_home_and_away_change_the_whole_page(career):
    at = page("teams.py", career, tm_section="ODIs", tm_team="India").run()
    ok(at)
    overall = {d.value.shape[0] for d in at.dataframe}
    seg(at, "Venue").set_value("Home").run()
    ok(at)
    assert any("Home games only" in i.value for i in at.info)
    res = [d.value for d in at.dataframe if "Venue" in d.value.columns][0]
    assert set(res.Venue) == {"Home"} and len(res) == 2  # India's two home ODIs v West Indies
    seg(at, "Venue").set_value("Away").run()
    ok(at)
    res = [d.value for d in at.dataframe if "Venue" in d.value.columns][0]
    assert set(res.Venue) == {"Away"} and len(res) == 1
    assert overall


def test_after_result_and_revenge_by_venue(career):
    ids = career.matches[career.matches.section == "ODIs"].match_id
    g = TP.games(career, ids)
    for venue in ("home", "away"):
        a = TP.after_result(career, ids, "India", venue=venue)
        assert a.played.sum() <= (g[(g.team == "India") & (g.venue == venue)]).shape[0]
        r = TP.revenge(career, ids, "India", venue=venue)
        assert r["revenge"]["played"] + r["other"]["played"] == ((g.team == "India") & (g.venue == venue)).sum()


# --------------------------------------------------------------------------- Opponent preview
def test_your_team_is_there_even_before_its_first_game_in_a_format(career):
    # India have played no Test here: they're still a choice, and the page says what fills in later
    at = page("opponent.py", career, op_section="Internationals", op_format="Tests", op_opp="Pakistan").run()
    ok(at)
    mine = next(s for s in at.main.selectbox if s.label == "Your team")
    assert mine.value == "India" and mine.options[1] == "India"
    assert "India haven't played a Test yet" in text(at)


def test_an_opponent_with_no_games_in_the_format_says_where_they_have_played(career):
    at = page("opponent.py", career, op_section="Internationals", op_format="Tests", op_opp="West Indies").run()
    ok(at)
    assert "West Indies haven't played a Test in this career yet" in text(at)
    show = [b for b in at.main.button if b.label.startswith("Show ")]
    assert show
    show[0].click().run()
    ok(at)
    assert at.session_state["op_format"] != "Tests"


def test_the_page_opens_on_your_next_match(career):
    # India are 2 games into a 3-match ODI series at home to West Indies: that's next, then the Tests in the schedule
    fx = F.make_series("India", "Pakistan", "Test", 2, "away", "2026-11")
    at = page("opponent.py", career, fx=fx).run()
    ok(at)
    assert at.session_state["op_section"] == "Internationals" and at.session_state["op_format"] == "ODIs"
    assert at.session_state["op_opp"] == "West Indies" and at.session_state["op_pred_where"] == "Home"
    opp = next(s for s in at.main.selectbox if s.label == "Opponent")
    assert "West Indies (next)" in opp.options
    # in Tests, the scheduled Pakistan series is tagged, and India (no Test yet) can still be picked
    seg(at, "Format").set_value("Tests").run()
    ok(at)
    opp = next(s for s in at.main.selectbox if s.label == "Opponent")
    assert "Pakistan (scheduled)" in opp.options


def test_upcoming(career):
    fx = F.make_series("India", "Pakistan", "ODI", 2, "away", "2026-11") + F.make_series("India", "England", "Test", 1,
                                                                                         "home", "2027-02")
    up = F.upcoming(career, fx, ["India"])
    # the last game of the West Indies series under way comes first, then the schedule in order
    assert list(up.opponent) == ["West Indies", "Pakistan", "Pakistan", "England"]
    assert list(up.no) == [3, 1, 2, 1]
    assert F.upcoming(career, fx, []).empty


# --------------------------------------------------------------------------- the season calendar
def test_season_runs_april_to_march():
    assert CV.season_of(pd.Timestamp("2027-03-31")) == 2026 and CV.season_of(pd.Timestamp("2027-04-01")) == 2027
    assert CV.months_of(2026)[0] == (2026, 4) and CV.months_of(2026)[-1] == (2027, 3)


def test_calendar_shows_results_and_the_series_to_come(career):
    fx = (F.make_series("India", "Sri Lanka", "ODI", 3, "away", "2026-12")  # no dates: in December's box
          + F.make_series("India", "England", "T20I", 1, "home", "", "2027-01-15"))  # a date: on its day
    t = F.track(career, fx, auto=("India",))
    days, notes = CV.team_chips(career, "India", t, 2026)
    m = career.matches
    ind = m[((m.home == "India") | (m.away == "India")) & (m.date.map(CV.season_of) == 2026)]
    played = sum(1 for v in days.values() for c in v if "class='UP'" not in c)
    assert played == len(ind)
    assert any("Sri Lanka" in x and "3 matches to come" in x for x in notes[(2026, 12)])
    assert any("class='UP'" in c for c in days[pd.Timestamp("2027-01-15").date()])
    html = CV.season_html(2026, days, notes)
    assert html.index("April 2026") < html.index("December 2026") < html.index("March 2027")


def test_season_page_and_fixtures_calendar(career):
    fx = F.make_series("India", "Sri Lanka", "ODI", 3, "away", "2026-12")
    at = page("season.py", career, fx=fx).run()
    ok(at)
    body = " ".join(m.value for m in at.markdown)
    assert "calgrid" in body and "v Sri Lanka" in body
    seg(at, "Show").set_value("One month").run()
    ok(at)
    at = page("fixtures.py", career, fx=fx)
    at.run()
    ok(at)
    body = " ".join(m.value for m in at.markdown)
    assert "calgrid" in body and "dates to come" in body


# --------------------------------------------------------------------------- every page opens on your team
def test_pages_open_on_your_teams_latest_section(career):
    at = page("stat_by_stat.py", career, mine=("India",)).run()
    ok(at)
    m = career.matches
    last = m[(m.home == "India") | (m.away == "India")].sort_values("date").iloc[-1]
    assert at.session_state["sbs_section"] == last.section
    at = page("competitions.py", career, mine=("India",)).run()
    ok(at)
    assert at.session_state["cp2_event"] == last.event


# --------------------------------------------------------------------------- which teams do you play as?
def test_teams_question_is_asked_once_and_saved(tmp_path, monkeypatch, career):
    home = tmp_path / "home"
    monkeypatch.setenv("STATS_PACK_HOME", str(home))
    st.cache_resource.clear()
    store = CareerStore(home)
    store.save(career, CareerSettings(name=career.name))
    try:
        at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=240)
        at.session_state["career_obj"] = career
        at.run()
        assert not at.exception, at.exception
        pick = next(s for s in at.multiselect if s.label == "Your teams")  # the question is open
        assert "India" in pick.options and "Afghanistan" in pick.options  # every country, played yet or not
        pick.set_value(["India"]).run()
        next(b for b in at.button if b.label == "Save").click().run()
        assert not at.exception, at.exception
        _, s = store.load_settings(career.name)
        assert s.my_teams == ["India"] and s.teams_asked
        assert json.loads((home / "preferences.json").read_text())["last_teams"] == ["India"]
        # the next visit: not asked again, and My team in the sidebar shows it
        at2 = AppTest.from_file(str(ROOT / "app.py"), default_timeout=240)
        at2.session_state["career_obj"] = career
        at2.run()
        assert not [s for s in at2.multiselect if s.label == "Your teams"]
        assert next(s for s in at2.sidebar.multiselect if s.label == "My team").value == ["India"]
        # a new career starts with them ticked
        other = Career.build("Second save", [(p.name, p.read_bytes()) for p in FIXTURES[:6]])
        store.save(other, CareerSettings(name=other.name))
        at3 = AppTest.from_file(str(ROOT / "app.py"), default_timeout=240)
        at3.session_state["career_obj"] = other
        at3.run()
        assert next(s for s in at3.multiselect if s.label == "Your teams").value == ["India"]
        # "I don't play as one team": never asked again for that career
        next(b for b in at3.button if b.label == "I don't play as one team").click().run()
        _, s3 = store.load_settings(other.name)
        assert s3.teams_asked and s3.my_teams == []
    finally:
        st.cache_resource.clear()


def test_settings_keep_the_answer_and_read_old_and_new_files(tmp_path, career):
    store = CareerStore(tmp_path / "home")
    store.save(career, CareerSettings(name=career.name, my_teams=["India"], teams_asked=True))
    _, s = store.load_settings(career.name)
    assert s.teams_asked
    # a save from the folder watcher with an older copy of the settings never loses it
    store.save(career, CareerSettings(name=career.name))
    _, s = store.load_settings(career.name)
    assert s.teams_asked and s.my_teams == ["India"]
    # an older settings file (no teams_asked) and a newer one (a key this version doesn't know) both load
    f = store._dir(career.name) / "settings.json"
    raw = json.loads(f.read_text())
    raw.pop("teams_asked")
    raw["from_the_future"] = 1
    f.write_text(json.dumps(raw))
    _, s = store.load_settings(career.name, fresh=True)
    assert s.teams_asked is False and s.my_teams == ["India"]


def test_a_country_picked_before_its_first_match_can_be_scheduled(career):
    # Zimbabwe haven't played in this career: still yours on the Fixtures page, and a series can be added
    at = page("fixtures.py", career, mine=("Zimbabwe",)).run()
    ok(at)
    team = next(s for s in at.main.selectbox if s.label == "Schedule for")
    assert team.value == "Zimbabwe"
    next(b for b in at.main.button if b.label == "Add series").click().run()
    ok(at)
    fx = at.session_state[f"fixtures::{career.name}"]
    assert fx and all(r["team"] == "Zimbabwe" for r in fx)
    # Home shows their tab, saying it fills in after their first game
    at = page("home.py", career, mine=("Zimbabwe",)).run()
    ok(at)
    assert any("No matches for Zimbabwe yet" in i.value for i in at.main.info)


@pytest.mark.parametrize("name", sorted(p.name for p in (ROOT / "views").glob("*.py")))
def test_every_page_with_a_brand_new_empty_career(name):
    """A new save with an empty Scorecards folder: every page says what to do, none breaks."""
    empty = Career.build("Brand new", [])
    at = page(name, empty, mine=("India",)).run()
    ok(at)
    if name not in ("home.py", "fixtures.py"):
        assert any("No matches in this career yet" in i.value for i in at.main.info), name


def test_the_whole_app_with_an_empty_career(tmp_path, monkeypatch):
    monkeypatch.setenv("STATS_PACK_HOME", str(tmp_path / "home"))
    st.cache_resource.clear()
    try:
        empty = Career.build("Brand new", [])
        CareerStore(tmp_path / "home").save(empty, CareerSettings(name=empty.name))
        for target in ("views/home.py", "views/stat_by_stat.py", "views/fixtures.py"):
            at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=240)
            at.session_state["career_obj"] = empty
            at.switch_page(target)
            at.run()
            assert not at.exception, (target, at.exception)
            # the teams question is open, with every country to pick from before the first match
            pick = next(s for s in at.multiselect if s.label == "Your teams")
            assert "India" in pick.options
    finally:
        st.cache_resource.clear()


def test_schedule_and_calendars_before_the_first_match():
    """A new career with no matches yet and a schedule added: the Fixtures calendar and the Season page show it."""
    empty = Career.build("Brand new", [])
    fx = F.make_series("India", "Afghanistan", "Test", 3, "home", "2026-07")
    at = page("fixtures.py", empty, mine=("India",), fx=fx).run()
    ok(at)
    body = " ".join(m.value for m in at.markdown)
    assert "calgrid" in body and "v Afghanistan" in body and "dates to come" in body
    days, notes = CV.team_chips(empty, "India", F.track(empty, fx, auto=("India",)), 2026)
    assert not days and len(notes[(2026, 7)]) == 1


# --------------------------------------------------------------------------- T20: the fifty is the big score
def test_t20_player_page_focuses_on_fifties():
    from ccstats import playerdeep as PD
    from ccstats.demo_league import generate
    demo = Career.build("demo", [(n, t.encode()) for n, t in generate()])
    ids = demo.matches[demo.matches.section == "Indian Premier League"].match_id
    bat = demo.batting[demo.batting.match_id.isin(ids) & demo.batting.did_bat]
    p = bat.groupby("player").runs.sum().idxmax()
    dz = PD.danger_zones(demo, ids, p)
    assert list(dz.zone) == ["0–9", "10–19", "20–49", "50+"] and PD.KEY_ZONE["t20"] == (20, 49)
    fn = PD.funnel(demo, ids, p)
    assert fn.mark.max() == 50 and fn.attrs["hundreds"] == int((bat[bat.player == p].runs >= 100).sum())
    at = AppTest.from_file(str(ROOT / "views" / "player.py"), default_timeout=240)
    at.session_state["career_obj"] = demo
    at.query_params["player"] = p
    at.run()
    ok(at)
    body = " ".join(m.value for m in at.markdown)
    assert "Got in, out before 50 (20–49)" in body and "Hundreds, on their own" in body
    season_table = [d.value for d in at.dataframe if "season" in d.value.columns and "Runs" in d.value.columns][0]
    cols = list(season_table.columns)
    assert cols.index("50") < cols.index("100")


def test_unclear_catches_count_for_the_team_with_nothing_to_do():
    from ccstats import myteam as MT
    c = Career.build("Fixtures", [(p.name, p.read_bytes()) for p in FIXTURES])
    unc = c.fielding[~c.fielding.resolved]
    at = page("home.py", c, mine=()).run()
    ok(at)
    assert not any("catch" in m.value and "pick who took" in m.value for m in at.markdown)
    at = page("data_check.py", c).run()
    ok(at)
    assert not any("Unclear catches" in m.value for m in at.markdown)
    assert any(t.label.startswith("Team catches") for t in at.tabs)
    if len(unc):  # a side's report card counts every catch it took, these too
        r = unc.iloc[0]
        m = c.matches.set_index("match_id").loc[r.match_id]
        card = MT.report_card(c, r.team, m.section, m.season)
        fc = c.fielding[c.fielding.match_id.isin(c.matches[(c.matches.section == m.section)
                                                              & (c.matches.season == m.season)].match_id)
                        & (c.fielding.team == r.team) & (c.fielding.kind == "caught")]
        assert any(x[0] == "Fielding" for x in card) and len(fc) >= 1


def test_season_one_month_shows_fixtures_to_come(career):
    fx = (F.make_series("India", "Sri Lanka", "ODI", 3, "away", "2026-12")
          + F.make_series("India", "England", "T20I", 1, "home", "", "2027-01-15"))
    at = page("season.py", career, fx=fx).run()
    ok(at)
    seg(at, "Show").set_value("One month").run()
    ok(at)
    month = next(s for s in at.main.selectbox if s.label == "Month")
    assert "December 2026" in month.options and "January 2027" in month.options  # months with only fixtures to come
    month.set_value((2026, 12)).run()
    ok(at)
    assert any("v Sri Lanka" in m.value and "dates to come" in m.value for m in at.markdown)
    next(s for s in at.main.selectbox if s.label == "Month").set_value((2027, 1)).run()
    ok(at)
    assert any("⏳ v England" in m.value for m in at.markdown)


def test_home_shows_your_team_before_the_first_match():
    empty = Career.build("Brand new", [])
    at = page("home.py", empty, mine=("India",)).run()
    ok(at)
    assert [t.label for t in at.tabs][:2] == ["🏏 India", "Everything"]
    assert any("No matches for India yet" in i.value for i in at.main.info)
