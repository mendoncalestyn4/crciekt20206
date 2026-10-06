"""The third wave: partnerships with names, headlines in the order you played,
multi-select filters, and the team, player, series, analytics and planning
features.  Built on a real season the user played (tests/fixtures_2026) and on
the hand-made fixtures."""

import time

import numpy as np
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


# ---------------------------------------------------------------- teams (1-7, 23, 29-36, 52)
from ccstats import teamplay as TP  # noqa: E402
from ccstats import tables as T  # noqa: E402


def test_games_are_two_rows_per_match_and_add_up(season):
    for sec in season.matches.section.unique():
        ids = Scope(sections=[sec]).match_ids(season.matches)
        g = TP.games(season, ids)
        assert len(g) == 2 * len(ids)
        assert (g.groupby("match_id").batted_first.sum() == 1).all()  # exactly one side batted first
        w = (g.outcome == "W").sum()
        assert w == (g.outcome == "L").sum() == (season.matches.match_id.isin(ids) & (season.matches.winner != "")).sum()
        t, avg = TP.bat_first_table(season, ids)
        assert t.bf_played.sum() + t.ch_played.sum() == len(g)
        assert t.bf_won.sum() + t.ch_won.sum() == w
        a, b = avg["first"], avg["second"]
        if a["decided"] and not avg["multi"]:
            assert abs(a["win_pct"] + b["win_pct"] - 100) < 1e-9  # one side's win is the other's loss


def test_score_chances_add_up_to_100(season):
    ids = Scope(sections=[IPL]).match_ids(season.matches)
    for score in (120, 160, 180, 200, 230):
        sc = TP.score_chances(season, ids, score)
        a, b = sc["batting_first"], sc["bowling_first"]
        assert a["decided"] == b["decided"]
        if a["decided"]:
            assert abs(a["win_pct"] + b["win_pct"] - 100) < 1e-9
        near = TP.games(season, ids)
        near = near[near.batted_first & ((near.first_score - score).abs() <= sc["band"])]
        assert a["played"] == len(near)
    one = TP.score_chances(season, ids, 170, "Mumbai Indians")
    assert one["batting_first"]["played"] <= TP.score_chances(season, ids, 170)["batting_first"]["played"]


def test_targets_close_games_stages_and_opponents_add_up(season):
    ids = Scope(sections=[IPL]).match_ids(season.matches)
    g = TP.games(season, ids)
    tb = TP.target_buckets(season, ids)
    assert tb.chase_played.sum() == (~g.batted_first).sum()
    assert tb.defend_played.sum() == g.batted_first.sum()
    for team in sorted(set(g.team)):
        mine = g[g.team == team]
        cg = TP.close_games(season, ids, team)
        assert cg["close"]["played"] + cg["other"]["played"] == len(mine)
        sr = TP.stage_record(season, ids, team).set_index("stage")
        assert sr.played["League games"] + sr.played["Knockouts (all)"] == len(mine)
        op = TP.opponents(season, ids, team)
        assert op.played.sum() == len(mine) and op.won.sum() == (mine.outcome == "W").sum()
        assert op.favourite.sum() <= 1 and op.bogey.sum() <= 1
        rv = TP.revenge(season, ids, team)
        assert rv["revenge"]["played"] + rv["other"]["played"] == len(mine)
        ar = TP.after_result(season, ids, team)
        assert ar.played.sum() == len(mine) - 1 - (mine.outcome.iloc[:-1].isin(["T", "NR"])).sum()
        sh = TP.season_halves(season, ids, team)
        tot = sh.iloc[-1]
        assert tot.early["played"] + tot.late["played"] == (~mine.knockout).sum()
        ss = TP.start_split(season, ids, team)
        assert ss["good"]["played"] + ss["middle"]["played"] + ss["bad"]["played"] == ss["all"]["played"] == len(mine)


def test_league_race_ends_where_the_table_does(season, career):
    for c in (season, career):
        for (ev, se), g in c.matches.groupby(["event", "season"]):
            race = TP.position_race(c, g.match_id)
            if race.empty:
                continue
            last = race[race["round"] == race.groupby("group")["round"].transform("max")]
            for label, t, _ in T.league_tables(c, g.match_id):
                mine = last[last.group == label].set_index("team").position
                assert [mine[x] for x in t.team] == list(t.index), (ev, se, label)


def test_series_situations():
    """A made-up 3-match series: A win the first two (so the third is a dead rubber), and a 2-2 five-match series
    whose last game is the decider."""
    from types import SimpleNamespace
    rows = []
    for i, w in enumerate(["A", "A", "B"], start=1):
        rows.append(dict(match_id=f"s{i}", date=pd.Timestamp(2026, 5, i), season="2026", section="ODIs", event="ODIs",
                         competition="ODI", format="ODI", knockout=False, stage="", series_id="X", series_match_no=i,
                         series_length=3, home="A", away="B", neutral=False, winner=w, loser="B" if w == "A" else "A",
                         result_type="win", result="", tiebreak_winner="", margin_runs=20.0, margin_wickets=np.nan,
                         innings_win=False, super_over="", batted_first="A", player_of_match=""))
    for i, w in enumerate(["C", "D", "C", "D", "C"], start=1):
        rows.append(dict(match_id=f"t{i}", date=pd.Timestamp(2026, 6, i), season="2026", section="ODIs", event="ODIs",
                         competition="ODI", format="ODI", knockout=False, stage="", series_id="Y", series_match_no=i,
                         series_length=5, home="C", away="D", neutral=False, winner=w, loser="D" if w == "C" else "C",
                         result_type="win", result="", tiebreak_winner="", margin_runs=20.0, margin_wickets=np.nan,
                         innings_win=False, super_over="", batted_first="C", player_of_match=""))
    matches = pd.DataFrame(rows)
    inn = pd.DataFrame([dict(match_id=r["match_id"], innings_no=1, team_innings=1, team=r["batted_first"], runs=200)
                        for r in rows], columns=["match_id", "innings_no", "team_innings", "team", "runs"])
    c = SimpleNamespace(matches=matches, innings=inn)
    s = TP.series_games(c, matches.match_id)
    x = s[s.series_id == "X"].set_index(["no", "team"])
    assert x.dead[(3, "A")] and x.dead[(3, "B")] and not x.dead[(2, "A")]
    assert not x.decider.any()
    y = s[s.series_id == "Y"].set_index(["no", "team"])
    assert y.decider[(5, "C")] and y.decider[(5, "D")] and not y.decider[(4, "C")]
    assert not y.dead.any()
    fb = TP.first_blood(c, matches.match_id).set_index("start")
    assert fb.loc["Won the first match", "series"] == 2 and fb.loc["Won the first match", "won"] == 2


def test_innings_by_number_and_follow_on(career):
    tests = Scope(sections=["Tests"]).match_ids(career.matches)
    ib = TP.innings_by_number(career, tests)
    inn = career.innings[career.innings.match_id.isin(tests)]
    assert ib.innings_played.sum() == len(inn)
    fo = TP.follow_on_and_declarations(career, tests)
    declared = inn.declared.sum()
    assert fo[fo.situation.str.startswith("Declared")].times.sum() == declared


def test_qualification(season):
    d = TP.qualification_defaults(season, IPL, "2026")
    assert d == dict(games=14, places=4, groups=1)  # the IPL's own shape: no earlier season to learn it from
    q = TP.qualification(season, IPL, "2026", 14, 4)
    assert len(q) == 10 and set(q.status) <= {"Through", "Out", "Alive"}
    for r in q.itertuples():
        assert r.max_points == r.points + r.left * 2
    done = TP.qualification(season, IPL, "2026", int(q.played.max()) - 1, 4)  # everybody has played their games
    assert list(done.status) == ["Through"] * 4 + ["Out"] * 6 or (done.played < int(q.played.max()) - 1).any()


# ---------------------------------------------------------------- players (8-20, 37-48, 59-65)
from ccstats import players as PL  # noqa: E402


def test_player_stories_add_up(season):
    ids = Scope(sections=[IPL]).match_ids(season.matches)
    bat = season.batting[season.batting.match_id.isin(ids) & season.batting.did_bat]
    wb, ww = PL.win_when(season, ids, min_times=1)
    fifties = bat[bat.runs >= 50].groupby("player").match_id.nunique()
    assert dict(zip(wb.player, wb.times)) == fifties.to_dict()
    q = PL.quirks(season, ids)
    nine = bat[bat.out & bat.runs.between(90, 99)].groupby("player").size()
    assert dict(zip(q["nineties"].player, q["nineties"].times)) == nine.to_dict()
    assert q["not_outs"].not_outs.sum() == (~bat.out).sum()
    ci, cp = PL.carried(season, ids, 1)
    assert (ci.share <= 100).all() and (cp.share <= 100).all()
    mw = PL.match_winners(season, ids)
    assert mw.match_winning.sum() == (season.matches.match_id.isin(ids) & (season.matches.winner != "")).sum()
    dp = PL.dependence(season, ids)
    assert dp.team.is_unique
    fb, fw = PL.form_guide(season, ids)
    for r in fb.head(5).itertuples():
        last = bat[bat.player == r.player].merge(season.matches[["match_id", "date"]], on="match_id") \
            .sort_values(["date", "match_id", "innings_no"]).tail(5)
        assert r.last == " ".join(f"{x}{'' if o else '*'}" for x, o in zip(last.runs, last.out))
    rae = PL.runs_above_expected(season, ids, min_innings=1)
    assert abs(rae.above.sum()) < 1e-6  # against the average batter in the same spot, it all evens out
    aa = PL.adjusted_averages(season, ids)
    base = aa.attrs["base"]
    for r in aa.itertuples():  # a settled average lies between the player's own and the section's
        if np.isfinite(r.average):
            assert min(r.average, base) - 1e-9 <= r.settled <= max(r.average, base) + 1e-9
    ww_ = PL.what_wins(season, ids)
    assert ((ww_.won_pct >= 0) & (ww_.won_pct <= 100)).all() and (ww_.games <= len(ids)).all()
    ew = PL.expected_wins(season, ids)
    assert abs(ew.luck.sum() - (ew.won.sum() - ew.expected.sum())) < 1e-9
    up = PL.upsets(season, IPL)
    assert (up.chance < 50).all()
    bb = PL.boom_or_bust(season, ids)
    assert set(bb.label) <= {"Boom or bust", "Reliable and big", "Steady, rarely big", "Struggling"}
    fr = PL.form_is_real(season, ids, last=4, min_innings=8)
    assert set(fr.verdict) <= {"Real: hot", "Real: cold", "Maybe", "Probably luck"}


def test_milestones_and_firsts(season):
    ids = Scope(sections=[IPL]).match_ids(season.matches)
    mw = PL.milestone_watch(season, ids)
    bat = season.batting[season.batting.match_id.isin(ids) & season.batting.did_bat]
    runs = bat.groupby("player").runs.sum()
    for r in mw[mw.what == "runs"].itertuples():
        assert r.now == runs[r.player] and r.next - r.now == r.needed > 0
    top = runs.idxmax()
    fi = PL.firsts(season, top)
    assert fi.date.is_monotonic_increasing
    assert fi.what.iloc[0] == "First match"
    first50 = bat[(bat.player == top) & (bat.runs >= 50)].merge(season.matches[["match_id", "date"]], on="match_id").date.min()
    assert fi[fi.what == "First fifty"].date.iloc[0] == first50


def test_pairs_order_plan_and_fringe(season):
    ids = Scope(sections=[IPL]).match_ids(season.matches)
    s = P.stands(season, ids)
    bp = PL.batting_pairs(season, ids, min_stands=1)
    assert bp.runs.sum() == s[s.known].runs.sum()
    team = "Mumbai Indians"
    order = PL.batting_order(season, ids, team)
    sug = PL.suggested_order(order)
    assert sug.player.is_unique and len(sug) <= 7
    plan = PL.bowling_plan(season, ids, team, min_balls=1)
    bowl = season.bowling[season.bowling.match_id.isin(ids) & (season.bowling.team == team)]
    for r in plan.itertuples():
        assert r.top + r.middle + r.tail == bowl[bowl.player == r.player].wickets.sum()
    kn = PL.knocking(season, ids, team)
    tm = season.matches[season.matches.match_id.isin(ids) & ((season.matches.home == team) | (season.matches.away == team))]
    assert (kn.games < len(tm) * 0.4).all()
    ps = PL.player_of_series(season, Scope(sections=["ODIs"]).match_ids(season.matches))
    assert len(ps) == 1  # one series, one Player of the Series


# ---------------------------------------------------------------- preview (54, 55, 70-80)
from ccstats import preview as PV  # noqa: E402


def test_preview(season):
    ids = Scope(sections=[IPL]).match_ids(season.matches)
    a, b = "Mumbai Indians", "Chennai Super Kings"
    mt = PV.meetings(season, ids, a, b)
    games = season.matches[((season.matches.home == a) & (season.matches.away == b))
                           | ((season.matches.home == b) & (season.matches.away == a))]
    assert mt["record"]["played"] == len(games) == len(mt["cards"])
    h = mt["how"]
    assert h["bat_first_wins"][a] + h["chasing_wins"][a] == mt["record"]["won"]
    mu = PV.matchups(season, ids, a, b)
    bat = season.batting[season.batting.match_id.isin(games.match_id) & season.batting.out
                         & (season.batting.how_out != "run out") & (season.batting.team == a)]
    theirs = set(season.batting[season.batting.match_id.isin(ids) & (season.batting.team == b)].player)
    assert mu["their_bowlers"].dismissals.sum() == bat.bowler.isin(theirs).sum()
    every = PV.matchups(season, ids, a, b, everywhere=True)
    assert every["their_bowlers"].dismissals.sum() >= mu["their_bowlers"].dismissals.sum()
    for f in (PV.key_wicket, PV.weak_spot, PV.attack_to_target, PV.batting_strip, PV.chase_extremes, PV.venue_record,
              PV.big_matches, PV.trend):
        f(season, ids, b)
    sb = PV.side_by_side(season, ids, a, b)
    assert set(sb.better) <= {"mine", "theirs", ""}
    assert all(isinstance(x, str) for x in PV.game_plan(season, ids, a, b))
    never = PV.meetings(season, Scope(sections=["ODIs"]).match_ids(season.matches), "Bangladesh", "Mumbai Indians")
    assert never["record"]["played"] == 0 and never["cards"] == []


# ---------------------------------------------------------------- my team (82, 67)
from ccstats import myteam as MT  # noqa: E402


def test_my_team(season):
    for team in ("Mumbai Indians", "Bangladesh"):
        secs = MT.sections_of(season, team)
        assert secs
        b = MT.banner(season, team)
        assert [x["section"] for x in b] == secs
        sec = secs[0]
        se = MT.latest_season(season, team, sec)
        sq = MT.squad(season, team, sec, se)
        bat = season.batting[(season.batting.team == team) & season.batting.match_id.isin(
            season.matches[(season.matches.section == sec) & (season.matches.season == se)].match_id)]
        assert sq.runs.sum() == bat[bat.did_bat].runs.sum()
        rc = MT.report_card(season, team, sec, se)
        assert {s for s, _, _ in rc} >= {"Results", "Batting", "Bowling", "Form"}
        assert all(g in "ABCDE" for _, g, _ in rc)
        hi = MT.history(season, team)
        assert hi.played.sum() == ((season.matches.home == team) | (season.matches.away == team)).sum()
    last = MT.last_game(season, "Mumbai Indians")
    order = RC.played_order(season)
    mi = order[(order.home == "Mumbai Indians") | (order.away == "Mumbai Indians")]
    assert last.match_id == mi.match_id.iloc[-1]


# ---------------------------------------------------------------- pages
from streamlit.testing.v1 import AppTest  # noqa: E402

NEW_PAGES = ["analytics.py", "stories.py", "planner.py", "season.py", "opponent.py", "teams.py", "insights.py",
             "competitions.py", "team_vs_team.py", "player.py", "home.py", "stat_by_stat.py"]


@pytest.mark.parametrize("page", NEW_PAGES)
def test_new_pages_open_with_my_team(page, season):
    at = AppTest.from_file(str(ROOT / "views" / page), default_timeout=120)
    at.session_state["career_obj"] = season
    at.session_state[f"my_teams::{season.name}"] = ["Mumbai Indians", "Bangladesh"]
    if page == "player.py":
        at.query_params["player"] = "Q DKock"
    at.run()
    assert not at.exception, at.exception
    assert not [w for w in at.warning if "couldn't be shown" in w.value]
    if page == "home.py":
        labels = [t.label for t in at.tabs]
        assert labels[:3] == ["🏏 Mumbai Indians", "🏏 Bangladesh", "Everything"]


def test_opponent_preview_with_internationals_switch(season):
    at = AppTest.from_file(str(ROOT / "views" / "opponent.py"), default_timeout=120)
    at.session_state["career_obj"] = season
    at.session_state["op_section"] = "Internationals"
    at.session_state["op_mine"] = "Bangladesh"
    at.run()
    assert not at.exception
    for f in ("ODIs", "T20Is", "All"):
        at.session_state["op_format"] = f
        at.run()
        assert not at.exception, f
        assert at.selectbox(key="op_opp").value == "New Zealand"


def test_low_score_alerts_are_only_for_batters(season):
    """A no. 8 bowler on a few low scores is no news: only top-7 batters get the alert."""
    for team in sorted(set(season.matches.home) | set(season.matches.away)):
        for sec in MT.sections_of(season, team):
            se = MT.latest_season(season, team, sec)
            sq = MT.squad(season, team, sec, se).set_index("player")
            for line in MT.alerts(season, team, sec, se):
                if line.startswith("📉"):
                    who = line.removeprefix("📉 ").split(" has been out")[0]
                    assert sq.usual_position[who] <= 7, (team, line)
    fb, _ = PL.form_guide(season, Scope(sections=[IPL]).match_ids(season.matches))
    bat = season.batting[season.batting.did_bat]
    pos = bat[bat.match_id.isin(Scope(sections=[IPL]).match_ids(season.matches))].groupby("player").position.median()
    assert (pos[fb.player] <= 7).all()


def test_every_chart_is_explained():
    """Every chart on every page has a 'What it shows / What it's for' note right after it."""
    missing = []
    for f in sorted((ROOT / "views").glob("*.py")):
        lines = f.read_text().split("\n")
        for i, ln in enumerate(lines):
            if "st.plotly_chart(" in ln and "chart_note(" not in "\n".join(lines[i:i + 30]):
                missing.append(f"{f.name}:{i + 1}")
    assert not missing, missing


def test_bars_follow_the_format(career):
    """A big score is 100 in Tests but 50 in white-ball cricket; a haul is 5 wickets in Tests, 4 one-day, 3 in T20."""
    from ccstats import extras as E_
    from ccstats.stats import bars_for
    assert (bars_for("multi")["big"], bars_for("one")["big"], bars_for("t20")["big"]) == (100, 50, 50)
    assert (bars_for("multi")["haul"], bars_for("one")["haul"], bars_for("t20")["haul"]) == (5, 4, 3)
    tests = Scope(sections=["Tests"]).match_ids(career.matches)
    wb, ww = PL.win_when(career, tests, min_times=1)
    assert wb.attrs["big"] == 100 and ww.attrs["haul"] == 5
    bat = career.batting[career.batting.match_id.isin(tests) & career.batting.did_bat]
    hundreds = bat[bat.runs >= 100].groupby("player").match_id.nunique()
    assert dict(zip(wb.player, wb.times)) == hundreds.to_dict()  # 100s, not 50s
    labels = [r["streak"] for r in E_.batting_streaks(pd.DataFrame({"runs": [60, 120], "out": [True, True]}), "multi")]
    assert "Innings in a row with 50+" in labels and "Innings in a row with 100+" in labels
    steps = [r["streak"] for r in E_.bowling_streaks(pd.DataFrame({"wickets": [5, 1]}), "multi")]
    assert "Innings in a row with 5+ wickets" in steps and "Innings in a row with 3+ wickets" in steps
    # a Test won by 40 runs is close; a T20 won by 40 isn't
    g = TP.games(career, tests)
    won_by_runs = g[g.margin_runs.notna() & (g.outcome == "W")]
    assert (won_by_runs.close == (won_by_runs.margin_runs < 50)).all()
    ipl = Scope(sections=[IPL]).match_ids(career.matches)
    gi = TP.games(career, ipl)
    wi = gi[gi.margin_runs.notna() & (gi.outcome == "W")]
    assert (wi.close == (wi.margin_runs < 10)).all()
    ss = TP.start_split(career, tests)
    assert (ss["good_bar"], ss["bad_bar"]) == (100, 25)


# ---------------------------------------------------------------- win chance (100-110, 125, 133, 137)
from ccstats import winprob as WP  # noqa: E402


def test_win_chance_engine(season, career):
    ids = Scope(sections=[IPL]).match_ids(season.matches)
    st_ = WP.states(season, ids)
    m = season.matches[season.matches.match_id.isin(ids) & (season.matches.result_type != "no result")]
    assert st_.match_id.nunique() == len(m)
    # every state starts each innings at 0 wickets, and leads add up: innings 2 starts at the first innings total
    s2 = st_[(st_.innings_no == 2) & (st_.wickets == 0)].set_index("match_id").lead
    first = season.innings[(season.innings.innings_no == 1)].set_index("match_id").runs
    assert (s2 == first.loc[s2.index]).all()
    mid = m.match_id.iloc[5]
    line = WP.match_line(season, mid, st_, "t20")
    assert len(line) == len(st_[st_.match_id == mid])
    ok = line.dropna(subset=["W"])
    assert ((ok.W + ok.D + ok.L + ok["T"] - 100).abs() < 1e-6).all()
    assert (ok.W > 0).all() and (ok.W < 100).all()  # small samples are pulled away from certainty
    ch = WP.chase_chance(st_, "t20", 181, 60, 3)
    assert abs(ch["win"] + ch["lose"] + ch["draw"] + ch["tie"] - 100) < 1e-6
    tests = Scope(sections=["Tests"]).match_ids(career.matches)
    fl = WP.first_innings_lead(career, tests)
    assert fl.matches.sum() <= len(tests)
    score, why = WP.match_rating(season, mid, line)
    assert 0 <= score <= 10 and isinstance(why, list)
    assert WP.match_report(season, mid, line).endswith(".")
    o = WP.series_odds(0.5, 0.0, 1, 0, 2)
    assert abs(sum(o.values()) - 100) < 1e-9 and abs(o["A"] - 75) < 1e-9  # 1-0 up with 2 to play at 50/50
    pr = WP.predict(season, ids, "Mumbai Indians", "Chennai Super Kings", "home")
    assert abs(pr["win"] + pr["lose"] + pr["draw"] - 100) < 1e-6
    cb = WP.comebacks(season, ids)
    assert (cb.low < 25).all()
