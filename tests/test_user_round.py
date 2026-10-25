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
    odis = m[m.section == "ODIs"]
    at = page("team_vs_team.py", career, tv_section="ODIs", tv_a="India", tv_b="England").run()
    ok(at)
    # they've met: the page opens on their meetings, and Where says how many there were at each ground
    assert seg(at, "Matches").value == "Against each other"
    meet = odis[((odis.home == "England") & (odis.away == "India")) | ((odis.home == "India") & (odis.away == "England"))]
    at_eng = int(((meet.home == "England") & ~meet.neutral).sum())
    at_ind = int(((meet.home == "India") & ~meet.neutral).sum())
    assert list(seg(at, "Where").options)[:3] == [f"All venues ({len(meet)})", f"At India's home ({at_ind})",
                                                  f"At England's home ({at_eng})"]
    seg(at, "Where").set_value(f"At England's home ({at_eng})").run()
    ok(at)
    assert at_eng >= 1 and f"{at_eng} meeting" in text(at)
    # at India's home they haven't met in ODIs: a clear message naming both, never a dead "no matches"
    seg(at, "Where").set_value(f"At India's home ({at_ind})").run()
    ok(at)
    assert at_ind == 0 and "India and England haven't played each other in ODIs at India's home yet" in text(at)
    # against anyone, England home and India away: each side's own games, said plainly on the page and the tiles
    seg(at, "Matches").set_value("Against anyone").run()
    seg(at, "Where").set_value("India away · England home").run()
    ok(at)
    india_away = odis[(odis.away == "India") & ~odis.neutral]
    england_home = odis[(odis.home == "England") & ~odis.neutral]
    tiles = " ".join(x.value for x in at.markdown if "class='kpi'" in x.value)
    assert tiles.count("<span>Played</span><strong>") == 2
    assert f"<span>Played</span><strong>{len(india_away)}</strong>" in tiles.split("England")[0]
    assert f"<span>Played</span><strong>{len(england_home)}</strong>" in tiles.split("England", 1)[1]
    assert "away games v anyone" in tiles and "home games v anyone" in tiles
    assert any("Each team's own record against anyone" in i.value and "India's away games" in i.value
               and "England's home games" in i.value for i in at.info)


def test_team_vs_team_two_sides_that_never_met(career):
    """The screenshot: Australia v Bangladesh in ODIs, never played each other. The page must not look like a
    head to head: it opens on each side's own games and says they haven't met."""
    m = career.matches
    odis = m[m.section == "ODIs"]
    met = odis[((odis.home == "Australia") & (odis.away == "Bangladesh")) | ((odis.home == "Bangladesh") & (odis.away == "Australia"))]
    assert met.empty
    at = page("team_vs_team.py", career, mine=("Australia",), tv_section="ODIs", tv_a="Australia", tv_b="Bangladesh").run()
    ok(at)
    assert seg(at, "Matches").value == "Against anyone"
    assert any("Australia and Bangladesh haven't played each other here yet" in i.value for i in at.info)
    seg(at, "Where").set_value("Australia away · Bangladesh home").run()
    ok(at)
    tiles = " ".join(x.value for x in at.markdown if "class='kpi'" in x.value)
    assert "away games v anyone" in tiles and "home games v anyone" in tiles
    assert "Australia and Bangladesh haven't played each other in ODIs at Bangladesh's home yet" in text(at)
    # asking for their meetings says so plainly and points to Against anyone
    seg(at, "Matches").set_value("Against each other").run()
    ok(at)
    assert any("haven't played each other in ODIs" in i.value and "Against anyone" in i.value for i in at.info)
    # picking another opponent starts again on the right kind of match
    next(s for s in at.main.selectbox if s.label == "Team B").set_value("South Africa").run()
    ok(at)
    assert seg(at, "Matches").value == "Against each other"


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


# --------------------------------------------------------------------------- change or delete your schedule
def test_schedule_items_change_and_delete():
    fx = (F.make_series("India", "England", "Test", 3, "away", "2027-01")
          + F.make_tournament("India", "T20 World Cup", "T20I", "2027-06", 7)
          + F.make_series("Mumbai Indians", "Chennai Super Kings", "T20", 1, "home", "2027-04"))
    items = F.schedule_items(fx, "India")
    assert [(i["kind"], i["n"], i["opponent"], i["venue"], i["month"]) for i in items] == [
        ("series", 3, "England", "away", "2027-01"), ("tournament", 1, "", "", "2027-06")]
    new = F.make_series("India", "England", "Test", 5, "home", "2027-02")
    fx2 = F.replace_item(fx, "India", items[0]["series"], new)
    assert len(fx2) == len(fx) + 2 and fx2[:5] == new  # in its place, the rest untouched
    assert [i["n"] for i in F.schedule_items(fx2, "India")] == [5, 1]
    kept, gone = F.delete_item(fx2, "India", new[0]["series"])
    assert len(gone) == 5 and all(r["series"] != new[0]["series"] for r in kept)
    kept_all, gone_all = F.delete_item(fx2, "India")
    assert [r["team"] for r in kept_all] == ["Mumbai Indians"] and len(gone_all) == 6


def test_change_or_delete_tab(career):
    fx = F.make_series("India", "Sri Lanka", "ODI", 3, "away", "2026-12")
    at = page("fixtures.py", career, fx=fx).run()
    ok(at)
    assert any(t.label == "Change or delete" for t in at.tabs)
    # change: 3 ODIs away in December -> 5 ODIs at home
    next(b for b in at.main.button if b.label == "✏️ Change").click().run()
    ok(at)
    next(n for n in at.main.number_input if str(n.key).startswith("fx_e_n_")).set_value(5).run()
    next(s for s in at.main.segmented_control if str(s.key).startswith("fx_e_ven_")).set_value("Home").run()
    next(b for b in at.main.button if b.label == "Save").click().run()
    ok(at)
    now = at.session_state[f"fixtures::{career.name}"]
    assert len(now) == 5 and {r["venue"] for r in now} == {"home"} and now[0]["series"].startswith("v Sri Lanka · 5 ODIs")
    # delete, then undo
    next(b for b in at.main.button if b.label == "🗑️ Delete").click().run()
    next(b for b in at.main.button if b.label == "Yes, delete it").click().run()
    ok(at)
    assert at.session_state[f"fixtures::{career.name}"] == []
    next(b for b in at.main.button if b.label == "↩️ Undo").click().run()
    ok(at)
    assert len(at.session_state[f"fixtures::{career.name}"]) == 5


# --------------------------------------------------------------------------- the next match, and a date for every match
@pytest.fixture(scope="module")
def tour():
    """2026 only, with England's Tests v Pakistan stopped after the 1st (19 Aug): the 2nd and 3rd are still to come."""
    keep = [p for p in FIXTURES if "2026" in p.name and "eng_v_pak_2nd_tst" not in p.name
            and "eng_v_pak_3rd_tst" not in p.name]
    return Career.build("Tour", [(p.name, p.read_bytes()) for p in keep])


def _next(c, fx, team="England"):
    t = F.track(c, fx, auto=(team,))
    nx = t[(t.team == team) & (t.status == "next")]
    up = F.upcoming(c, fx, [team])
    assert len(nx) == 1 and len(up)
    assert (up.format.iloc[0], int(up.no.iloc[0])) == (nx.format.iloc[0], int(nx.no.iloc[0]))
    return t, nx.iloc[0]


def test_next_is_the_rest_of_the_series_under_way_however_it_was_typed(tour):
    tests = lambda **k: F.make_series("England", "Pakistan", "Test", 3, "home", **k)  # noqa: E731
    odis = lambda **k: F.make_series("England", "Pakistan", "ODI", 3, "home", **k)  # noqa: E731
    gap = pd.Timedelta(days=F.series_gaps(tour).get("Test", 8))
    cases = {"first dates": tests(date="2026-08-19") + odis(date="2026-09-20"),
             "months only": tests(month="2026-08") + odis(month="2026-08"),
             "ODIs listed first": odis(month="2026-08") + tests(month="2026-08"),
             "ODIs dated, Tests by month": tests(month="2026-08") + odis(date="2026-09-20"),
             "only the ODIs": odis(month="2026-08")}  # the Tests come from the scorecards (auto-added)
    for name, fx in cases.items():
        t, nx = _next(tour, fx)
        assert (nx.format, int(nx.no)) == ("Test", 2), name
        assert nx.anchor == pd.Timestamp("2026-08-19") + gap and nx.estimated, name  # from the 1st Test's date
        mine = t[(t.team == "England") & t.status.isin(["next", "to come"])]
        assert list(mine.format) == ["Test", "Test", "ODI", "ODI", "ODI"], name  # the Tests finish first
        assert mine.anchor.is_monotonic_increasing, name


def test_dates_you_type_are_used_and_a_series_under_way_fits_before_the_next(tour):
    fx = (F.make_series("England", "Pakistan", "Test", 3, "home", dates=["2026-08-19", "2026-08-27", "2026-09-09"])
          + F.make_series("England", "Pakistan", "ODI", 3, "home", dates=["2026-09-20", "", "2026-09-26"]))
    t, nx = _next(tour, fx)
    assert (nx.format, int(nx.no), nx.anchor, bool(nx.estimated)) == ("Test", 2, pd.Timestamp("2026-08-27"), False)
    odi = t[(t.format == "ODI") & (t.team == "England") & t.series.str.contains("Pakistan")].set_index("no")
    assert odi.anchor[1] == pd.Timestamp("2026-09-20") and odi.anchor[3] == pd.Timestamp("2026-09-26")
    assert odi.anchor[2] == pd.Timestamp("2026-09-23") and odi.estimated[2]  # halfway between the two it sits between
    # the ODIs typed for 1 Sep: the 2nd and 3rd Tests (no dates) are squeezed in before them, in order
    fx = F.make_series("England", "Pakistan", "Test", 3, "home", date="2026-08-19") + \
        F.make_series("England", "Pakistan", "ODI", 3, "home", date="2026-09-01")
    t, nx = _next(tour, fx)
    mine = t[(t.team == "England") & t.status.isin(["next", "to come"])]
    assert list(zip(mine.format, mine.no)) == [("Test", 2), ("Test", 3), ("ODI", 1), ("ODI", 2), ("ODI", 3)]
    assert pd.Timestamp("2026-08-19") < mine.anchor.iloc[0] < mine.anchor.iloc[1] < pd.Timestamp("2026-09-01")


def test_make_series_with_every_date_and_the_order_check():
    rows = F.make_series("India", "Sri Lanka", "ODI", 3, "away", "2026-11", dates=["2026-12-02", "", "2026-12-08"])
    assert [r["date"] for r in rows] == ["2026-12-02", "", "2026-12-08"]
    assert {r["month"] for r in rows} == {"2026-12"}  # the month follows the first date given
    assert rows[0]["series"] == "v Sri Lanka · 3 ODIs · away · Dec 2026"
    assert F.dates_in_order(["2026-12-02", "", "2026-12-08"]) == ""
    assert "Match 3" in F.dates_in_order(["2026-12-02", "2026-12-05", "2026-12-04"])
    assert "same day" in F.dates_in_order(["2026-12-02", "2026-12-02"])
    assert F.schedule_items(rows, "India")[0]["dates"] == ["2026-12-02", "", "2026-12-08"]


def test_add_and_change_a_series_with_a_date_for_every_match(career):
    import datetime as dt
    at = page("fixtures.py", career).run()
    ok(at)
    next(s for s in at.main.selectbox if s.key.startswith("fx_opp::")).set_value("Sri Lanka").run()
    next(s for s in at.main.segmented_control if s.key == "fx_fmt").set_value("ODI").run()
    next(t for t in at.main.toggle if t.key == "fx_know").set_value(True).run()
    ok(at)
    boxes = [d for d in at.main.date_input if str(d.key).startswith("fx_d_")]
    assert [d.label for d in boxes] == ["1st ODI", "2nd ODI", "3rd ODI"] and all(d.value is None for d in boxes)
    # out of order: a clear message and no Add
    boxes[0].set_value(dt.date(2026, 12, 8))
    boxes[1].set_value(dt.date(2026, 12, 5)).run()
    assert any("Match 2's date" in e.value for e in at.error)
    assert next(b for b in at.main.button if b.key == "fx_add_series").disabled
    next(d for d in at.main.date_input if d.key == "fx_d_1").set_value(dt.date(2026, 12, 2)).run()
    assert not at.error
    next(b for b in at.main.button if b.key == "fx_add_series").click().run()
    ok(at)
    now = at.session_state[f"fixtures::{career.name}"]
    assert [r["date"] for r in now] == ["2026-12-02", "2026-12-05", ""] and now[0]["month"] == "2026-12"
    # change it: the boxes come back filled in; give the 3rd its date
    next(b for b in at.main.button if b.label == "✏️ Change").click().run()
    ok(at)
    filled = [d for d in at.main.date_input if str(d.key).startswith("fx_e_d_")]
    assert [d.value for d in filled] == [dt.date(2026, 12, 2), dt.date(2026, 12, 5), None]
    filled[2].set_value(dt.date(2026, 12, 8)).run()
    next(b for b in at.main.button if b.label == "Save").click().run()
    ok(at)
    assert [r["date"] for r in at.session_state[f"fixtures::{career.name}"]] == ["2026-12-02", "2026-12-05", "2026-12-08"]
