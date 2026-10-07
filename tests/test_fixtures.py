"""Your schedule (the Fixtures page): reading what you type, ticking fixtures off
as scorecards arrive, home / away from the schedule, series chances, the WTC
race, milestone countdowns, goals, series reports, the calendar, and the page
itself.  Every figure is checked against a recount from the scorecards."""

import random
import string
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from ccstats import fixtures as F
from ccstats import seasonal as SN
from ccstats.loader import Career
from ccstats.local import CareerSettings, CareerStore

ROOT = Path(__file__).parent.parent
FIXTURES = sorted((Path(__file__).parent / "fixtures").glob("*.txt"))
NEW = Path(__file__).parent / "fixtures_2026" / "new_playthrough.zip"


@pytest.fixture(scope="module")
def career():
    c = Career.build("Fixtures test", [(p.name, p.read_bytes()) for p in FIXTURES])
    return c


@pytest.fixture(scope="module")
def season():
    return Career.build("Fixtures season", [(NEW.name, NEW.read_bytes())])


def known(c):
    return sorted(set(c.matches.home) | set(c.matches.away) | F.NATIONS)


# --------------------------------------------------------------------------- reading what you type
@pytest.mark.parametrize("line,want", [
    ("England 3 Tests away Jan 2027", ("England", "Test", 3, "away", "2027-01", "")),
    ("v Australia, 5 ODIs, home, March 2027", ("Australia", "ODI", 5, "home", "2027-03", "")),
    ("12 Jan 2027 Test England away", ("England", "Test", 1, "away", "2027-01", "2027-01-12")),
    ("NZ 3 T20s @ Feb 2027", ("New Zealand", "T20I", 3, "away", "2027-02", "")),
    ("three tests v sa (h) 2027-11", ("South Africa", "Test", 3, "home", "2027-11", "")),
    ("2027-03-14 ODI v SL neutral", ("Sri Lanka", "ODI", 1, "neutral", "2027-03", "2027-03-14")),
    ("West Indies 2 Tests", ("West Indies", "Test", 2, "", "", "")),
    ("wi 5 t20is home sept 2027", ("West Indies", "T20I", 5, "home", "2027-09", "")),
])
def test_series_lines(career, line, want):
    rows, err = F.parse_line(line, "India", known(career))
    assert not err, err
    opp, fmt, n, venue, month, date = want
    assert len(rows) == n
    assert all(r["opponent"] == opp and r["format"] == fmt and r["venue"] == venue and r["month"] == month for r in rows)
    assert [r["no"] for r in rows] == list(range(1, n + 1))
    assert rows[0]["date"] == date and all(r["date"] == "" for r in rows[1:])
    assert len({r["series"] for r in rows}) == 1 and len({r["id"] for r in rows}) == n


@pytest.mark.parametrize("line,name,fmt,games", [
    ("T20 World Cup Jun 2027", "T20 World Cup", "T20I", 0),
    ("T20 World Cup 7 matches Jun 2027", "T20 World Cup", "T20I", 7),
    ("Champions Trophy feb 2027", "Champions Trophy", "ODI", 0),
    ("WTC final Jun 2027 Test", "World Test Championship Final", "Test", 0),
    ("ODI World Cup Oct 2027", "ODI World Cup", "ODI", 0),
])
def test_tournament_lines(career, line, name, fmt, games):
    rows, err = F.parse_line(line, "India", known(career))
    assert not err and len(rows) == 1
    r = rows[0]
    assert r["series"].startswith(name) and r["format"] == fmt and r["games"] == games and r["opponent"] == ""


@pytest.mark.parametrize("line,why", [
    ("England Jan 2027", "format"),
    ("blah blah", "couldn't find"),
    ("India 3 Tests home Jan 2027", "couldn't find"),  # your own team isn't an opponent
    ("England 40 Tests away", "40 matches"),
    ("31 Feb 2027 Test England", "date"),
])
def test_lines_that_cant_be_read_say_why(career, line, why):
    rows, err = F.parse_line(line, "India", known(career))
    assert not rows and why in err


def test_franchise_t20_stays_t20(season):
    rows, err = F.parse_line("Chennai 2 T20s home Apr 2027", "Mumbai Indians", known(season))
    assert not err and rows[0]["opponent"] == "Chennai Super Kings" and rows[0]["format"] == "T20"


def test_reading_never_crashes_on_anything():
    rnd = random.Random(7)
    alphabet = string.ascii_letters + string.digits + " ,.-/@()·–#\t"
    for _ in range(3000):
        line = "".join(rnd.choice(alphabet) for _ in range(rnd.randint(0, 60)))
        rows, err = F.parse_line(line, "India", sorted(F.NATIONS))
        assert isinstance(rows, list) and isinstance(err, str)
    rows, errs = F.parse_lines("\n\n# a note\nEngland 3 Tests away Jan 2027\nnonsense\n", "India", sorted(F.NATIONS))
    assert len(rows) == 3 and len(errs) == 1


def test_merge_skips_what_is_already_there():
    a = F.make_series("India", "England", "Test", 3, "away", "2027-01")
    rows, added = F.merge([], a)
    assert added == 3
    rows, added = F.merge(rows, F.make_series("India", "England", "Test", 3, "away", "2027-01"))
    assert added == 0 and len(rows) == 3


# --------------------------------------------------------------------------- ticking fixtures off
def test_series_is_ticked_off_in_order(career):
    fx = F.make_series("England", "Pakistan", "Test", 3, "home", "2026-08")
    t = F.track(career, fx)
    m = career.matches.set_index("match_id")
    real = career.matches[career.matches.series_id == "Test-7"].sort_values("series_match_no")
    assert list(t.match_id) == list(real.match_id)
    assert (t.status == "played").all() and (t.outcome == "W").all()
    for r in t.itertuples():
        assert r.result == m.result[r.match_id] and pd.Timestamp(r.played_date) == m.date[r.match_id]


def test_more_fixtures_than_played_leaves_the_rest_to_come(career):
    t = F.track(career, F.make_series("England", "Pakistan", "Test", 5, "home", "2026-08"))
    # England play on into 2027 in these files, so Tests 4 and 5 of an August 2026 series are overdue, not "next"
    assert list(t.status) == ["played"] * 3 + ["no scorecard"] * 2
    assert t.anchor.is_monotonic_increasing
    # India's last match here is in October 2026: a series still in the future is next / to come
    t = F.track(career, F.make_series("India", "England", "Test", 3, "away", "2027-01"))
    assert list(t.status) == ["next", "to come", "to come"]


def test_undated_series_takes_the_first_one_not_yet_used(career):
    fx = F.make_series("England", "Pakistan", "Test", 3) + F.make_series("India", "West Indies", "ODI", 3)
    t = F.track(career, fx)
    assert (t[t.team == "England"].status == "played").all()
    ind = t[t.team == "India"]
    assert list(ind.status) == ["played", "played", "next"]  # 2 of the 3 ODIs are in the files


def test_wrong_month_is_flagged_not_called_next(career):
    t = F.track(career, F.make_series("England", "Pakistan", "Test", 3, "home", "2026-01"))
    assert (t.status == "no scorecard").all()
    assert F.summary(t, "England")["next"] is None and F.summary(t, "England")["missing"] == 3


def test_a_match_is_never_used_twice(career):
    fx = F.make_series("England", "Pakistan", "Test", 3, "home", "2026-08") + \
        F.make_series("England", "Pakistan", "Test", 2, "home", "2026-08")[:0] + \
        [dict(r, series="second copy", id=F.new_id()) for r in F.make_series("England", "Pakistan", "Test", 3, "home", "2026-08")]
    t = F.track(career, fx)
    used = t[t.match_id != ""].match_id
    assert used.is_unique and len(used) == 3


def test_tournament_collects_every_match(career):
    t = F.track(career, F.make_tournament("India", "T20 World Cup", "T20I", "2026-03"))
    assert len(t) == 1 and t.status.iloc[0] == "played" and t.outcome.iloc[0] == "W"  # won the final, so nothing to come
    t = F.track(career, F.make_tournament("England", "ODI World Cup", "ODI", "2027-06", games=9))
    played = t[t.status == "played"]
    assert len(played) == 3 and (played.outcome == "W").all()
    assert len(t) == 3  # England won the final: no more games to come whatever was planned


def test_no_matches_at_all_is_fine(career):
    t = F.track(career, F.make_series("Scotland", "Nepal", "ODI", 3, "home", "2030-01"))
    assert list(t.status) == ["next", "to come", "to come"]
    assert F.track(career, []).empty


# --------------------------------------------------------------------------- 154 · home and away from your schedule
def test_venues_follow_the_schedule(career):
    fx = F.make_series("England", "Pakistan", "Test", 3, "away", "2026-08")  # say England were away
    t = F.track(career, fx)
    c2 = F.with_venues(career, t)
    assert c2 is not career and getattr(c2, "_venue_base") is career
    for mid in t.match_id:
        r = c2.matches.set_index("match_id").loc[mid]
        assert r.away == "England" and r.home == "Pakistan"
        inn = c2.innings[c2.innings.match_id == mid]
        assert (inn.home == (inn.team == "Pakistan")).all()
    # nothing else moved, and the original is untouched
    other = ~c2.matches.match_id.isin(t.match_id)
    assert (c2.matches[other].home.values == career.matches[other].home.values).all()
    assert (career.matches.set_index("match_id").loc[t.match_id].home == "England").all()
    assert len(c2.matches) == len(career.matches) and (c2.matches.winner.values == career.matches.winner.values).all()
    # the schedule agreeing with the scorecards changes nothing
    same = F.track(career, F.make_series("England", "Pakistan", "Test", 3, "home", "2026-08"))
    assert F.with_venues(career, same) is career
    # neutral
    c3 = F.with_venues(career, F.track(career, F.make_series("England", "Pakistan", "Test", 3, "neutral", "2026-08")))
    assert c3.matches.set_index("match_id").loc[t.match_id].neutral.all()
    assert not c3.innings[c3.innings.match_id.isin(t.match_id)].home.any()


# --------------------------------------------------------------------------- 145 / 148 · series chances
def test_scorelines_and_odds_add_up():
    for pw, pd_, n in ((0.6, 0.0, 3), (0.4, 0.25, 5), (0.5, 0.1, 1), (0.9, 0.0, 0)):
        lines = F.scorelines(pw, pd_, n)
        assert sum(lines.values()) == pytest.approx(100)
        assert all(a + b <= n for a, b in lines)
    lines = F.scorelines(1.0, 0.0, 3, (1, 0))
    assert lines == {(4, 0): pytest.approx(100)}


@pytest.mark.parametrize("won,lost,total,need", [
    (1, 1, 3, "win the last match to take the series"),
    (0, 0, 3, "win 2 of the last 3 to take the series"),
    (2, 0, 3, "the series is already won"),
    (0, 2, 3, "the series can't be won now"),
    (0, 0, 2, "win all 2 left to take the series"),
])
def test_what_is_needed(career, won, lost, total, need):
    rows = pd.DataFrame({"outcome": ["W"] * won + ["L"] * lost, "status": "played"})
    s = dict(series="x", opponent="Pakistan", format="Test", rows=rows, won=won, lost=lost, drawn=0, played=won + lost,
             total=total, state="under way", start=pd.Timestamp("2026-01-01"), venue="home")
    o = F.series_outlook(career, "England", s)
    assert o["need"].startswith(need)
    assert sum(o["odds"].values()) == pytest.approx(100)
    assert o["left"] == total - won - lost


# --------------------------------------------------------------------------- 149 · WTC race
def test_wtc_race_arithmetic(career):
    # India's Tests in December 2026 are still to come (their last match in these files is October 2026)
    t = F.track(career, F.make_series("India", "England", "Test", 2, "home", "2026-12"))
    r = F.wtc_race(career, t, "India")
    table = SN.wtc_table(career, r["cycle"]).set_index("team")
    pts = int(table.points.get("India", 0))
    n = int(table.played.get("India", 0))
    assert (r["points"], r["played"], r["remaining"]) == (pts, n, 2)
    assert r["best"] == pytest.approx((pts + 24) / (12 * (n + 2)) * 100)
    others = table.drop(index="India", errors="ignore").pct.sort_values(ascending=False)
    assert r["bar"] == pytest.approx(others.iloc[1])
    k = r["need"]
    assert k is None or ((pts + 12 * k) / (12 * (n + 2)) * 100 > r["bar"] and
                         (k == 0 or (pts + 12 * (k - 1)) / (12 * (n + 2)) * 100 <= r["bar"]))
    assert 0 <= r["chance"] <= 100
    assert F.wtc_race(career, t, "Ireland") is None


# --------------------------------------------------------------------------- 150 · milestones
def test_milestone_countdown_recount(season):
    m = season.matches
    t = F.track(season, F.make_series("Mumbai Indians", "Chennai Super Kings", "T20", 6, "home", "2030-04"))
    d = F.milestone_countdown(season, t, "Mumbai Indians")
    assert len(d)
    ids = m[(m.format == "T20") & ((m.home == "Mumbai Indians") | (m.away == "Mumbai Indians"))].match_id
    b = season.batting[season.batting.match_id.isin(ids) & (season.batting.team == "Mumbai Indians")]
    for r in d[d.what == "runs"].head(5).itertuples():
        mine = b[b.player == r.player]
        assert r.now == mine[mine.did_bat].runs.sum()
        assert r.per_match == pytest.approx(r.now / mine.match_id.nunique())
        assert r.needed == r.next - r.now and r.games_needed == int(np.ceil(r.needed / r.per_match))
        assert r.within == (r.games_needed <= 6)


# --------------------------------------------------------------------------- 151 · goals
def test_goals(career):
    t = F.track(career, F.make_series("England", "Pakistan", "Test", 3, "home", "2026-08"))
    s = F.series_groups(t, "England")[0]["series"]
    g = F.goal_progress(career, t, dict(kind="series", team="England", series=s))
    assert g["status"] == "achieved" and g["done"] == 1.0 and "3–0" in g["text"]
    m = career.matches
    eng = m[(m.format == "ODI") & ((m.home == "England") | (m.away == "England")) & (m.date.dt.year == 2027)]
    wins = int((eng.winner == "England").sum())
    g = F.goal_progress(career, t, dict(kind="wins", team="England", format="ODI", target=10, year="2027"))
    assert g["text"].startswith(f"{wins} of 10") and g["done"] == pytest.approx(wins / 10)
    b = career.batting[career.batting.match_id.isin(m[m.format == "Test"].match_id) & (career.batting.player == "J Root")]
    g = F.goal_progress(career, t, dict(kind="player", player="J Root", format="Test", what="runs", target=100000))
    assert g["text"].startswith(f"{int(b.runs.sum()):,} of 100,000")
    g = F.goal_progress(career, t, dict(kind="series", team="England", series="gone"))
    assert g["status"] == "unknown"
    assert F.goal_progress(career, t, dict(kind="wtc", team="England"))["status"] in ("achieved", "on course", "at risk", "unknown")


# --------------------------------------------------------------------------- 152 · series report
def test_series_report(career):
    t = F.track(career, F.make_series("England", "Pakistan", "Test", 3, "home", "2026-08"))
    s = F.series_groups(t, "England")[0]
    rep = F.series_report(career, s, "England")
    assert rep["result"] == "England won the series 3–0"
    mids = list(t.match_id)
    b = career.batting[career.batting.match_id.isin(mids) & career.batting.did_bat]
    assert rep["top_bat"].iloc[0] == b.groupby(["player", "team"]).runs.sum().max()
    assert rep["best_bat"].runs == b.runs.max()
    assert set(rep["matches"].match_id) == set(mids)
    assert rep["elo"]["England"][1] > rep["elo"]["England"][0]  # three wins: up


# --------------------------------------------------------------------------- 143 · calendar
def test_calendar(career):
    t = F.track(career, F.make_series("India", "England", "Test", 3, "away", "2027-01") +
                F.make_series("India", "England", "ODI", 1, "away", "", "2026-12-20"))
    days, months = F.calendar_entries(career, t, "India", 2026)
    m = career.matches
    ind = m[((m.home == "India") | (m.away == "India")) & (m.date.dt.year == 2026)]
    played = [e for v in days.values() for e in v if e["kind"] == "played"]
    assert len(played) == len(ind)
    assert any(e["kind"] == "to come" for e in days.get(pd.Timestamp("2026-12-20"), []))
    days27, months27 = F.calendar_entries(career, t, "India", 2027)
    assert len(months27.get(1, [])) == 3


# --------------------------------------------------------------------------- saved with the career
def test_schedule_and_goals_are_saved(tmp_path, career):
    store = CareerStore(tmp_path / "home")
    fx = F.make_series("India", "England", "Test", 3, "away", "2027-01")
    store.save(career, CareerSettings(name=career.name, fixtures=fx, goals=[dict(id="g", kind="wtc", team="India")]))
    _, back = store.load_settings(career.name)
    assert back.fixtures == fx and back.goals[0]["kind"] == "wtc"


# --------------------------------------------------------------------------- the page
def page(c, fx=None, goals=None, mine=("India",)):
    at = AppTest.from_file(str(ROOT / "views" / "fixtures.py"), default_timeout=180)
    at.session_state["career_obj"] = c
    at.session_state[f"my_teams::{c.name}"] = list(mine)
    at.session_state[f"fixtures::{c.name}"] = fx or []
    at.session_state[f"goals::{c.name}"] = goals or []
    return at


def ok(at):
    assert not at.exception, [e.message for e in at.exception]
    assert not [w for w in at.warning if "couldn't be shown" in w.value], [w.value for w in at.warning]


def test_page_empty_shows_how_to(career):
    at = page(career).run()
    ok(at)
    assert any("How to add your schedule" in x.value for x in at.markdown)


def test_page_add_series_with_the_pickers(career):
    at = page(career).run()
    at.selectbox(key="fx_opp").select("England").run()
    at.button(key="fx_add_series").click().run()
    ok(at)
    saved = at.session_state[f"fixtures::{career.name}"]
    assert len(saved) == 3 and {r["opponent"] for r in saved} == {"England"} and saved[0]["team"] == "India"
    at.button(key="fx_add_series").click().run()  # the same again: not added twice
    assert len(at.session_state[f"fixtures::{career.name}"]) == 3


def test_page_add_tournament(career):
    at = page(career).run()
    at.segmented_control(key="fx_kind").set_value("Tournament").run()
    at.button(key="fx_add_tour").click().run()
    ok(at)
    saved = at.session_state[f"fixtures::{career.name}"]
    assert len(saved) == 1 and saved[0]["opponent"] == "" and saved[0]["series"].startswith("T20 World Cup")


def test_page_type_lines(career):
    at = page(career).run()
    at.text_area(key="fx_text").input("England 3 Tests away Jan 2027\nnonsense line\nT20 World Cup Jun 2027").run()
    at.button(key="fx_read").click().run()
    ok(at)
    assert any("Skipped" in w.value for w in at.warning)
    at.button(key="fx_add_text").click().run()
    ok(at)
    assert len(at.session_state[f"fixtures::{career.name}"]) == 4


def test_page_with_a_full_schedule_and_goals(career):
    fx = (F.make_series("India", "West Indies", "ODI", 3, "home", "2026-10") +
          F.make_series("India", "England", "Test", 3, "away", "2027-01") +
          F.make_tournament("India", "T20 World Cup", "T20I", "2026-03") +
          F.make_series("India", "England", "T20I", 3, "away", "2026-07"))
    goals = [dict(id="a", kind="wtc", team="India"), dict(id="b", kind="series", team="India",
                                                          series=fx[3]["series"]),
             dict(id="c", kind="wins", team="India", format="ODI", target=5, year="2026")]
    at = page(career, fx, goals).run()
    ok(at)
    text = " ".join(x.value for x in at.markdown)
    for bit in ("Next match", "Before ball one", "World Test Championship"):
        assert bit in text, bit
    # remove a goal
    at.button(key="fx_goal_del_a").click().run()
    ok(at)
    assert [g["id"] for g in at.session_state[f"goals::{career.name}"]] == ["b", "c"]


def test_page_edit_table_saves(career):
    fx = F.make_series("India", "England", "Test", 3, "away", "2027-01")
    at = page(career, fx).run()
    ok(at)
    at.button(key="fx_save_edit").click().run()  # saving unchanged keeps everything (ids too)
    ok(at)
    saved = at.session_state[f"fixtures::{career.name}"]
    assert [r["id"] for r in saved] == [r["id"] for r in fx] and [r["month"] for r in saved] == ["2027-01"] * 3


def test_every_page_still_works_with_a_schedule(career):
    fx = F.make_series("England", "Pakistan", "Test", 3, "away", "2026-08")
    for p in ("teams.py", "insights.py", "home.py", "match.py", "competitions.py", "opponent.py"):
        at = AppTest.from_file(str(ROOT / "views" / p), default_timeout=180)
        at.session_state["career_obj"] = career
        at.session_state[f"my_teams::{career.name}"] = ["England"]
        at.session_state[f"fixtures::{career.name}"] = fx
        at.run()
        ok(at)
