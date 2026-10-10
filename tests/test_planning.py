"""Planning the season (ccstats/planning.py): each number checked against the scorecards worked out another way."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ccstats import fixtures as F
from ccstats import planning as P
from ccstats import teamplay as TP
from ccstats.loader import Career

FIXTURES = sorted((Path(__file__).parent / "fixtures").glob("*.txt"))


@pytest.fixture(scope="module")
def career():
    return Career.build("Planning", [(p.name, p.read_bytes()) for p in FIXTURES])


@pytest.fixture(scope="module")
def tour():
    """2026 only, England's Tests v Pakistan stopped after the 1st: two Tests still to come."""
    keep = [p for p in FIXTURES if "2026" in p.name and "eng_v_pak_2nd_tst" not in p.name
            and "eng_v_pak_3rd_tst" not in p.name]
    return Career.build("Tour", [(p.name, p.read_bytes()) for p in keep])


def schedule():
    return (F.make_series("England", "Pakistan", "Test", 3, "home", date="2026-08-19")
            + F.make_series("England", "Pakistan", "ODI", 3, "home", month="2026-09")
            + F.make_series("England", "India", "T20I", 2, "away", month="2026-11"))


def test_chances_and_how_hard(tour):
    tr = F.track(tour, schedule(), auto=("England",))
    ch = P.chances(tour, tr, "England")
    todo = tr[(tr.team == "England") & tr.status.isin(["next", "to come"]) & (tr.opponent != "")]
    assert len(ch) == len(todo) == 2 + 3 + 2
    assert list(ch.anchor) == sorted(ch.anchor)  # in the order they'll be played
    assert np.allclose(ch.win + ch.draw + ch.lose, 100)
    for r in ch.itertuples():
        share = r.win / (r.win + r.lose) * 100
        assert r.level == ("easy" if share >= 60 else "hard" if share <= 40 else "even")
    assert (ch[ch.format == "Test"].draw > 0).all() and (ch[ch.format != "Test"].draw == 0).all()


def test_toughest_run_is_the_lowest_three_in_a_row():
    ch = pd.DataFrame(dict(win=[70, 30, 20, 40, 80], lose=[30, 70, 80, 60, 20], level=["easy", "hard", "hard", "even",
                                                                                         "easy"],
                           anchor=pd.date_range("2026-01-01", periods=5)))
    run = P.toughest_run(ch)
    assert round(run["share"], 6) == round(np.mean([30, 20, 40]), 6) and run["hard"] == 2
    assert run["start"] == pd.Timestamp("2026-01-02")
    assert P.toughest_run(ch.head(2)) is None


def test_wins_spread_is_a_proper_distribution():
    d = P._wins_spread([0.5, 0.5, 0.5])
    assert np.allclose(d, [1 / 8, 3 / 8, 3 / 8, 1 / 8])
    d = P._wins_spread([0.9, 0.2])
    assert np.allclose(d, [0.1 * 0.8, 0.9 * 0.8 + 0.1 * 0.2, 0.9 * 0.2]) and np.isclose(d.sum(), 1)


def test_projection_adds_up(tour):
    tr = F.track(tour, schedule(), auto=("England",))
    start, end = pd.Timestamp("2026-04-01"), pd.Timestamp("2027-04-01")
    pr = P.projection(tour, tr, "England", start, end)
    m = tour.matches
    mine = m[((m.home == "England") | (m.away == "England")) & (m.date >= start) & (m.date < end)]
    assert pr["played"] == len(mine)
    assert pr["now"]["W"] == int((mine.winner == "England").sum())
    assert pr["now"]["L"] == int(((mine.winner != "England") & (mine.winner != "")).sum())
    ch = pr["chances"]
    assert np.isclose(pr["exp_won"], pr["now"]["W"] + ch.win.sum() / 100)
    assert pr["now"]["W"] <= pr["low"] <= pr["exp_won"] + 1 and pr["exp_won"] - 1 <= pr["high"] <= pr["now"]["W"] + len(ch)
    assert sum(f["left"] for f in pr["by_format"].values()) == pr["left"] == len(ch)


def test_conditions_are_the_hosts_home_games(career):
    c = P.conditions(career, "England", "Test")
    m = career.matches
    there = m[(m.format == "Test") & (m.home == "England") & ~m.neutral]
    assert c is not None and c["there"]["games"] == len(there)
    inn = career.innings
    first = inn[inn.match_id.isin(there.match_id) & (inn.innings_no == 1)]
    rained = set(there[there.rain].match_id)
    assert np.isclose(c["there"]["first"], first[~first.match_id.isin(rained)].runs.mean())
    all_inn = inn[inn.match_id.isin(there.match_id)]
    assert np.isclose(c["there"]["runs_per_wicket"], all_inn.runs.sum() / all_inn.wickets.sum())
    assert c["everywhere"]["games"] == int((m.format == "Test").sum())
    assert P.conditions(career, "Nepal", "Test") is None  # no games there


def test_travellers_split_home_and_away(career):
    tv = P.travellers(career, "England", "Test", min_inns=1, min_balls=1)
    m = career.matches
    eng = m[(m.format == "Test") & ((m.home == "England") | (m.away == "England"))]
    assert tv["home_games"] == int(((eng.home == "England") & ~eng.neutral).sum())
    assert tv["away_games"] == int(((eng.away == "England") & ~eng.neutral).sum())
    b = career.batting
    for r in tv["bat"].head(3).itertuples():
        away = b[b.match_id.isin(eng[eng.away == "England"].match_id) & (b.player == r.player) & b.did_bat
                 & (b.team == "England")]
        assert r.runs_away == away.runs.sum() and r.inns_away == len(away)
    assert list(tv["bat"]["diff"]) == sorted(tv["bat"]["diff"], reverse=True)


def test_series_history_and_one_still_being_played(career, tour):
    h = P.series_history(career, "England", "Pakistan", "Test")
    assert len(h["rows"]) == 1
    r = h["rows"][0]
    m = career.matches
    x = m[(m.format == "Test") & (((m.home == "England") & (m.away == "Pakistan")) | ((m.home == "Pakistan") & (m.away == "England")))]
    assert (r["won"], r["lost"], r["games"]) == (int((x.winner == "England").sum()), int((x.winner == "Pakistan").sum()), len(x))
    assert r["venue"] == "home" and r["result"] in ("won", "lost", "drawn")
    # with only the 1st Test in, the series isn't a result yet
    h2 = P.series_history(tour, "England", "Pakistan", "Test")
    assert h2["rows"][0]["result"] == "under way" and h2["won"] + h2["lost"] + h2["drawn"] == 0


def test_rivalry_thresholds(career):
    g = P.team_games(career, "England")
    for opp in set(g.opponent):
        rec = TP.record(g[g.opponent == opp])
        rv = P.rivalry(career, "England", opp)
        if rec["decided"] < 3:
            assert rv is None
        elif rec["win_pct"] >= 70:
            assert rv["kind"] == "favourite"
        elif rec["win_pct"] <= 30:
            assert rv["kind"] == "bogey"
        else:
            assert rv is None


def test_runs_and_streak_words():
    assert P._run(list("LWWW"), lambda o: o == "W") == 3
    assert P._run(["W", "L", "W", "NR", "W"], lambda o: o == "W") == 2  # a no result doesn't break a run
    assert P._run(list("WWL"), lambda o: o == "W") == 0
    assert P.a_or_an("ODI") == "an ODI" and P.a_or_an("Test") == "a Test" and P.a_or_an("T20I") == "a T20I"


def test_series_records_are_the_biggest(career):
    lines = P.series_records(career, "England", "Pakistan", "Test", 3)
    m = career.matches
    x = m[(m.format == "Test") & (m.series_id != "")]
    b = career.batting.merge(x[["match_id", "series_id"]], on="match_id")
    top = b.groupby(["series_id", "player"]).runs.sum().max()
    assert any(f"Most runs in a Test series: {top} by" in s for s in lines)
    w = career.bowling.merge(x[["match_id", "series_id"]], on="match_id")
    assert any(f"Most wickets in a Test series: {w.groupby(['series_id', 'player']).wickets.sum().max()} by" in s
               for s in lines)


def test_check_finds_the_mistakes_and_fixes_them(tour):
    E = "England"
    fx = (F.make_series(E, "Pakistan", "Test", 3, "home", month="2026-06")  # played from 19 Aug: wrong month
          + F.make_series(E, "Sri Lanka", "ODI", 3, "home", dates=["2026-09-10", "2026-09-12", "2026-09-14"])
          + F.make_series(E, "Sri Lanka", "ODI", 3, "home", month="2026-10")  # the same series again
          + F.make_series(E, "Ireland", "T20I", 2, "away", dates=["2026-09-13", "2026-09-15"])  # same days
          + F.make_series(E, "India", "T20I", 5, "away", month="2026-07"))  # played at home (the scorecards)
    tr = F.track(tour, fx, auto=(E,))
    found = {x["kind"]: x for x in P.check(tour, fx, tr, E)}
    assert set(found) >= {"month", "twice", "overlap", "venue"}, found
    assert found["month"]["fix"] == {"month": "2026-08"}
    assert found["venue"]["fix"] == {"venue": "home"}
    fixed = P.apply_fix(fx, E, found["month"]["series"], found["month"]["fix"])
    it = next(i for i in F.schedule_items(fixed, E) if i["opponent"] == "Pakistan")
    assert it["month"] == "2026-08" and it["n"] == 3
    gone = P.apply_fix(fx, E, found["twice"]["series"], found["twice"]["fix"])
    assert len([i for i in F.schedule_items(gone, E) if i["opponent"] == "Sri Lanka"]) == 1
    home = P.apply_fix(fx, E, found["venue"]["series"], found["venue"]["fix"])
    assert next(i for i in F.schedule_items(home, E) if i["opponent"] == "India")["venue"] == "home"
    # a date given before a match already played: flagged, and clearing it works
    fx2 = F.make_series(E, "Pakistan", "Test", 3, "home", dates=["2026-08-19", "2026-08-10", ""])
    tr2 = F.track(tour, fx2, auto=(E,))
    early = [x for x in P.check(tour, fx2, tr2, E) if x["kind"] == "early"]
    assert early and early[0]["fix"] == {"clear_dates": True}
    cleared = P.apply_fix(fx2, E, early[0]["series"], early[0]["fix"])
    assert all(not r["date"] for r in cleared)


def test_goals_and_forecasts(tour):
    tr = F.track(tour, schedule(), auto=("England",))
    goals = P.suggested_goals(tour, tr, "England", [])
    names = {g.get("series") for g in goals if g["kind"] == "series"}
    assert {s["series"] for s in F.series_groups(tr, "England") if s["state"] in ("to come", "under way")} == names
    assert any(g["kind"] == "wtc" for g in goals)
    assert P.suggested_goals(tour, tr, "England", goals) == []  # nothing twice
    fc = P.take_forecasts(tour, tr, "England", {})
    keys = {P.forecast_key("England", s["series"]) for s in F.series_groups(tr, "England") if s["state"] == "to come"}
    assert set(fc) == keys and all(np.isclose(f["win"] + f["draw"] + f["lose"], 100, atol=0.2) for f in fc.values())
    assert P.take_forecasts(tour, tr, "England", fc) == {}  # made once, then kept
    # a finished series with a forecast: right when the favourite won
    done = next(s for s in F.series_groups(F.track(tour, F.make_series("England", "India", "T20I", 5, "home", month="2026-07"),
                                                          auto=("England",)), "England") if s["state"] in ("done", "missed"))
    saved = {P.forecast_key("England", done["series"]): dict(win=70.0, draw=0.0, lose=30.0, likely="3–2", games=5)}
    tr3 = F.track(tour, F.make_series("England", "India", "T20I", 5, "home", month="2026-07"), auto=("England",))
    chk = P.forecast_check(tr3, "England", saved)
    assert done["state"] == "done"
    assert len(chk) == 1 and chk[0]["right"] == (done["won"] > done["lost"]) and chk[0]["result"] == f"{done['won']}–{done['lost']}"


# --------------------------------------------------------------------------- the Fixtures page itself
from streamlit.testing.v1 import AppTest  # noqa: E402

ROOT = Path(__file__).parent.parent


def page(c, fx, team="England", **state):
    at = AppTest.from_file(str(ROOT / "views" / "fixtures.py"), default_timeout=240)
    at.session_state["career_obj"] = c
    at.session_state[f"my_teams::{c.name}"] = [team]
    at.session_state[f"fixtures::{c.name}"] = fx
    for k, v in state.items():
        at.session_state[k] = v
    return at


def ok(at):
    assert not at.exception, [e.message for e in at.exception]
    assert not [w for w in at.warning if "couldn't be shown" in w.value], [w.value for w in at.warning]
    assert not at.error, [e.value for e in at.error]


def everything(at) -> str:
    return " ".join([m.value for m in at.markdown] + [c.value for c in at.caption] + [i.value for i in at.info])


def test_schedule_tab_check_fix_and_undo(tour):
    fx = (F.make_series("England", "Pakistan", "Test", 3, "home", month="2026-06")  # played from 19 Aug
          + F.make_series("England", "Pakistan", "ODI", 3, "home", month="2026-09"))
    at = page(tour, fx).run()
    ok(at)
    text = everything(at)
    assert "Schedule check" in text and "change its month to Aug 2026?" in text
    fix = next(b for b in at.main.button if b.label == "✅ Fix it")
    fix.click().run()
    ok(at)
    now = at.session_state[f"fixtures::{tour.name}"]
    assert next(r for r in now if r["format"] == "Test")["month"] == "2026-08"
    assert "Schedule check: nothing looks wrong" in everything(at)
    next(b for b in at.main.button if b.label == "↩️ Undo").click().run()
    ok(at)
    assert at.session_state[f"fixtures::{tour.name}"] == fx  # back exactly as it was


def test_schedule_tab_chances_form_outlook_and_next_match(tour):
    at = page(tour, schedule()).run()
    ok(at)
    tables = " ".join(m.value for m in at.markdown if "<table" in m.value)
    assert "Your chance" in tables and "Their form" in tables
    assert tables.count("% · easy") + tables.count("% · even") + tables.count("% · hard") == 2 + 3 + 2
    text = everything(at)
    assert "The season ahead" in text and "Heading for" in " ".join(m.value for m in at.markdown)
    assert "Their last" in text  # the next match's opponent form
    assert any(c.key == "fx_outlook" for c in at.get("plotly_chart")) or "fx_outlook" in str(at.session_state)
    # forecasts are kept for the series that haven't started
    saved = at.session_state[f"forecasts::{tour.name}"]
    assert set(saved) == {P.forecast_key("England", s["series"]) for s in
                          F.series_groups(F.track(tour, schedule(), auto=("England",)), "England") if s["state"] == "to come"}


def test_series_tab_extras_note_goal_and_suggestions(tour):
    at = page(tour, schedule()).run()
    ok(at)
    text = everything(at)
    assert "Under way: v Pakistan · 3 Tests" in text
    assert "Records in reach" in text and "in ODI series" not in text
    # a note on a series: saved, then shown on the next-match box when it's that series
    box = next(t for t in at.main.text_input if str(t.key).startswith("fx_note_l0_"))
    box.set_value("Rest Anderson for the 3rd Test").run()
    next(b for b in at.main.button if b.key == f"{box.key}_save").click().run()
    ok(at)
    assert "Rest Anderson for the 3rd Test" in everything(at)
    # make it a goal, then the suggestions no longer offer it
    next(b for b in at.main.button if b.label == "🎯 Make winning this series a goal").click().run()
    ok(at)
    goals = at.session_state[f"goals::{tour.name}"]
    assert any(g["kind"] == "series" and "Pakistan · 3 Tests" in g["series"] for g in goals)
    sugg = [b for b in at.main.button if str(b.key).startswith("fx_sugg_") and b.key != "fx_sugg_all"]
    n = len(sugg)
    next(b for b in at.main.button if b.key == "fx_sugg_all").click().run()
    ok(at)
    assert len(at.session_state[f"goals::{tour.name}"]) == len(goals) + n
    assert not [b for b in at.main.button if str(b.key).startswith("fx_sugg_")]


def test_fixtures_page_for_every_team_with_and_without_a_schedule(career):
    m = career.matches
    for team in sorted(set(m.home) | set(m.away))[:40]:
        fmt_ = "Test" if team in F.NATIONS else "T20"
        fx = F.make_series(team, "England" if team != "England" else "India", fmt_, 2, "away", month="2027-01")
        for sched in ([], fx):
            at = page(career, sched, team=team, fx_team=team).run()
            ok(at)


# --------------------------------------------------------------------------- best and worst, series review
from ccstats import teamreport as TR  # noqa: E402
from ccstats.playerdeep import match_impact  # noqa: E402


def test_match_card_best_and_worst(career):
    m = career.matches
    for r in m[m.format.isin(["ODI", "Test", "T20I", "T20"])].itertuples():
        for side in (r.home, r.away):
            card = TR.match_card(career, r.match_id, side)
            assert card is not None
            imp = match_impact(career, F.format_ids(career, side, r.format))
            mine = imp[(imp.match_id == r.match_id) & (imp.team == side)].sort_values("impact", ascending=False)
            assert [p for p, _, _ in card["best"]] == list(mine.player.head(3))
            assert np.allclose([v for _, _, v in card["best"]], mine.impact.head(3))
            best = {p for p, _, _ in card["best"]}
            assert not best & {p for p, _, _ in card["worst"]}
            assert [v for _, _, v in card["worst"]] == sorted(v for _, _, v in card["worst"])
    one = m.iloc[0]
    assert TR.match_card(career, one.match_id, "Nobody FC") is None


def test_match_card_figures_are_the_scorecards(career):
    r = career.matches[career.matches.format == "ODI"].iloc[0]
    card = TR.match_card(career, r.match_id, r.home)
    b = career.batting[(career.batting.match_id == r.match_id) & (career.batting.team == r.home) & career.batting.did_bat]
    w = career.bowling[(career.bowling.match_id == r.match_id) & (career.bowling.team == r.home)]
    for p, fig, _ in card["best"] + card["worst"]:
        bp = b[b.player == p]
        if len(bp) and bp.balls.sum():
            assert fig.startswith(f"{int(bp.runs.sum())}{'' if bp.out.any() else '*'} ({int(bp.balls.sum())})")
        wp = w[w.player == p]
        if len(wp) and wp.balls.sum():
            assert f"{int(wp.wickets.sum())}/{int(wp.runs.sum())}" in fig


def test_series_review_advice_follows_its_rules(career):
    m = career.matches
    x = m[(m.series_id != "") & m.format.isin(["Test", "ODI", "T20I"])]
    checked = 0
    for sid, g in x.groupby("series_id"):
        for side in (g.home.iloc[0], g.away.iloc[0]):
            rv = TR.series_review(career, g.match_id, side)
            if rv is None:
                continue
            pl = rv["players"]
            hi, lo = pl.per_game.quantile(0.67), pl.per_game.quantile(0.33)
            for r in pl.itertuples():
                if r.verdict == "use more":
                    assert r.per_game >= hi and r.per_game > 0
                    assert not (pd.notna(r.u_per_game) and r.u_games >= 3) or r.per_game > r.u_per_game
                if r.verdict == "think about dropping":
                    assert r.games >= 2 and r.per_game <= lo
            now = rv["now"]
            assert now["games"] == len(g) and now["won"] == int((g.winner == side).sum())
            checked += 1
    assert checked >= 4


def test_pages_show_the_reports(tour):
    m = tour.matches
    eng = m[(m.home == "England") | (m.away == "England")].iloc[0]
    at = AppTest.from_file(str(ROOT / "views" / "match.py"), default_timeout=240)
    at.session_state["career_obj"] = tour
    at.session_state[f"my_teams::{tour.name}"] = ["England"]
    at.query_params["match"] = eng.match_id
    at.run()
    ok(at)
    assert any("England: best and worst in this match" in x.value for x in at.markdown)
    # a finished series: its report has the review
    fx = F.make_series("England", "India", "T20I", 5, "home", month="2026-07")
    at = page(tour, fx).run()
    ok(at)
    assert "Series review: England" in everything(at)
