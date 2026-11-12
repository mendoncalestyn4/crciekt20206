"""Stage 2's new pieces (ccstats/aim.py): who carries the team, the usual score at each wicket and the score to aim
for, each checked against the scorecards counted by hand or against the engine's own figures."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from ccstats import aim as A
from ccstats import players as PL
from ccstats.loader import Career
from serverkit import FIXTURES


@pytest.fixture(scope="module")
def career():
    return Career.build("Test career", [(f.name, f.read_bytes()) for f in FIXTURES])


def ids_of(c, section, season=None):
    m = c.matches[c.matches.section == section]
    if season is not None:
        m = m[m.season == season]
    return set(m.match_id)


# --------------------------------------------------------------------------- who carries the team
def test_every_players_share_is_the_same_as_on_their_own_page(career):
    """For every player in every competition and season they played, the team table gives the same matches, runs,
    wickets and shares as the Player page's share of the team."""
    seen = 0
    for p in sorted(career.batting.player.unique()):
        for r in PL.team_share(career, p).itertuples():
            t = A.team_shares(career, ids_of(career, r.section, r.season), r.team)
            row = t[t.player == p].iloc[0]
            assert (row.matches, row.runs, row.wickets) == (r.matches, r.runs, r.wickets)
            assert (t.attrs["team_runs"], t.attrs["team_wickets"], t.attrs["team_matches"]) == (r.team_runs, r.team_wickets, r.team_matches)
            if r.team_runs:
                assert row.run_share == pytest.approx(r.run_share)
            if r.team_wickets:
                assert row.wicket_share == pytest.approx(r.wicket_share)
            seen += 1
    assert seen > 500


def test_the_shares_add_up_to_the_team(career):
    """Every wicket the team's bowlers took is someone's, and the runs fall short of the totals by the extras only."""
    for sec in career.matches.section.unique():
        ids = ids_of(career, sec)
        for team in sorted(set(career.matches[career.matches.match_id.isin(ids)].home)):
            t = A.team_shares(career, ids, team)
            mids = set(career.matches[career.matches.match_id.isin(ids) & ((career.matches.home == team) | (career.matches.away == team))].match_id)
            inn = career.innings[career.innings.match_id.isin(mids) & (career.innings.team == team)]
            assert t.runs.sum() == t.attrs["team_runs"] - inn.extras.sum()
            assert t.wickets.sum() == t.attrs["team_wickets"]
            assert list(t.runs) == sorted(t.runs, reverse=True)


def test_no_games_means_an_empty_table_not_an_error(career):
    t = A.team_shares(career, set(), "India")
    assert t.empty and t.attrs["team_runs"] == 0 and list(t.columns) == ["player", "matches", "runs", "run_share", "wickets", "wicket_share"]
    assert A.usual_by_wicket(career, set(), "India").empty


# --------------------------------------------------------------------------- the usual score at each wicket
def test_the_usual_score_at_each_wicket_counted_by_hand(career):
    """The middle score at each wicket's fall, from the fall-of-wicket lines, for the team and for their opponents in
    the same games; only wickets that fell in at least 30% of the team's innings."""
    checked = 0
    for sec in career.matches.section.unique():
        ids = ids_of(career, sec)
        for team in sorted(set(career.matches[career.matches.match_id.isin(ids)].home)):
            u = A.usual_by_wicket(career, ids, team)
            mids = set(career.matches[career.matches.match_id.isin(ids) & ((career.matches.home == team) | (career.matches.away == team))].match_id)
            n = len(career.innings[career.innings.match_id.isin(mids) & (career.innings.team == team)])
            f = career.fow[career.fow.match_id.isin(mids)]
            for w in range(1, 11):
                mine = sorted(f[(f.team == team) & (f.wicket == w)].score)
                theirs = sorted(f[(f.team != team) & (f.wicket == w)].score)
                row = u[u.wicket == w]
                if len(mine) < 0.3 * n or not mine:
                    assert row.empty
                    continue
                r = row.iloc[0]
                assert r.usual == math.floor(float(np.median(mine)) + 0.5)
                assert (r.innings, r.best, r.worst) == (len(mine), max(mine), min(mine))
                if theirs:
                    assert r.opp_usual == math.floor(float(np.median(theirs)) + 0.5)
                else:
                    assert pd.isna(r.opp_usual)
                checked += 1
    assert checked > 50


# --------------------------------------------------------------------------- the score to aim for
def test_the_fit_finds_a_known_answer():
    """Made-up games where the chance of winning batting first is known exactly: the fit gets close to it, and the
    total it gives for a chance gives that chance back."""
    rng = np.random.default_rng(7)
    n = 6000
    runs = rng.normal(160, 25, n)
    elo = rng.normal(0, 100, n)
    venue = rng.choice(["home", "away", "neutral"], n)
    z = -0.2 + 1.1 * (runs - 160) / 25 + 0.5 * elo / 100 + 0.3 * (venue == "home") - 0.3 * (venue == "away")
    won = (rng.random(n) < 1 / (1 + np.exp(-z))).astype(float)
    mu, sd = runs.mean(), runs.std(ddof=1)
    X = np.column_stack([np.ones(n), (runs - mu) / sd, elo / 100, venue == "home", venue == "away"]).astype(float)
    w = A._fit(X, won, ridge=0.0)
    fit = dict(w=w, mu=mu, sd=sd)
    assert w[1] * 25 / sd == pytest.approx(1.1, abs=0.12)
    assert w[2] == pytest.approx(0.5, abs=0.1)
    assert w[3] - w[4] == pytest.approx(0.6, abs=0.15)
    for venue_ in A.VENUES:
        for p in (0.5, 0.7):
            t = A.total_for(fit, p, 40.0, venue_)
            assert A.chance(fit, t, 40.0, venue_) == pytest.approx(p * 100)
    # the true total for an even game at home with a 40-point edge: 160 + 25 * (0.2 - 0.2 - 0.3) / 1.1
    assert A.total_for(fit, 0.5, 40.0, "home") == pytest.approx(160 + 25 * (0.2 - 0.2 - 0.3) / 1.1, abs=4)


def test_the_ridge_keeps_a_lonely_term_near_nought():
    """Three away games among hundreds: their term stays small instead of running off to whatever fits them."""
    rng = np.random.default_rng(3)
    n = 400
    runs = rng.normal(0, 1, n)
    away = np.zeros(n)
    away[:3] = 1
    won = (rng.random(n) < 1 / (1 + np.exp(-runs))).astype(float)
    won[:3] = 1.0
    X = np.column_stack([np.ones(n), runs, away])
    with np.errstate(over="ignore"):
        loose = A._fit(X, won, ridge=0.01)[2]
    assert abs(A._fit(X, won)[2]) < 1.5 < abs(loose)


def test_the_score_to_aim_says_why_when_it_cant_be_given(career):
    assert "multi-day" in A.score_to_aim(career, ids_of(career, "Tests"), "India", "England")["none"]
    both = ids_of(career, "ODIs") | ids_of(career, "T20Is")
    assert "Pick one format" in A.score_to_aim(career, both, "India", "England")["none"]
    few = A.score_to_aim(career, ids_of(career, "ODIs"), "India", "England")
    assert few["none"].startswith("Not enough finished games") and str(A.MIN_GAMES) in few["none"]


def test_the_score_to_aim_from_the_games_themselves(career, monkeypatch):
    """With the bar lowered so the few test games are enough: the even total is below the 70% one everywhere, the
    games used are the finished first innings, and the opponent's score and the meetings are the real ones."""
    monkeypatch.setattr(A, "MIN_GAMES", 5)
    done = 0
    for sec in ("T20 Blast", "Indian Premier League", "ODIs"):
        ids = ids_of(career, sec)
        fit = A.model(career, ids)
        if fit is None:
            continue
        d = A._games(career, ids)
        assert fit["games"] == len(d) and set(d.outcome) <= {"won", "lost"}
        m = career.matches[career.matches.match_id.isin(ids)]
        assert not set(d.match_id) & set(m[m.rain.astype(bool) | (m.result_type != "win")].match_id)
        teams = sorted(set(m.home) | set(m.away))
        for me in teams:
            for opp in teams:
                if me == opp:
                    continue
                a = A.score_to_aim(career, ids, me, opp)
                assert not a["none"]
                for venue, v in a["venues"].items():
                    assert v["even"] < v["seventy"]
                    met = m[((m.home == me) & (m.away == opp)) | ((m.home == opp) & (m.away == me))]
                    here = [x for x in met.itertuples() if (("neutral" if x.neutral else "home" if x.home == me else "away") == venue)]
                    assert sorted(x["id"] for x in v["meetings"]) == sorted(x.match_id for x in here)
                    first = career.innings[career.innings.match_id.isin([x.match_id for x in here]) & (career.innings.innings_no == 1)]
                    set_ = [r.runs for r in first.itertuples() if r.team == opp and r.match_id in set(d.match_id) | set(
                        A.first_innings(career, ids).match_id)]
                    assert v["they_set_n"] == len(set_)
                    if set_:
                        assert v["they_set"] == int(round(float(np.median(set_))))
                done += 1
    assert done > 20


# --------------------------------------------------------------------------- your season, wrapped
def test_season_wrapped_counted_by_hand(career):
    """Every team in every competition and season: each slide's figure from the scorecards counted directly."""
    from ccstats import analysis as AN
    from ccstats import mvp as MV
    from ccstats import partnerships as PS
    from ccstats import wrapped as WR
    m = career.matches
    seen = 0
    for (sec, season), g in m.groupby(["section", "season"]):
        for team in sorted(set(g.home) | set(g.away)):
            w = WR.season_wrapped(career, sec, season, team)
            mids = set(g[(g.home == team) | (g.away == team)].match_id)
            assert w["matches"] == len(mids)
            tm = AN.team_matches(career, mids, team)
            assert w["record"]["won"] == (tm.winner == team).sum() and w["record"]["played"] == len(tm)
            bat = career.batting[career.batting.match_id.isin(mids) & (career.batting.team == team) & career.batting.did_bat]
            runs = bat.groupby("player").runs.sum()
            if runs.max() > 0:
                assert w["runs"]["runs"] == runs.max() and runs[w["runs"]["player"]] == runs.max()
                assert w["score"]["runs"] == bat.runs.max()
            bowl = career.bowling[career.bowling.match_id.isin(mids) & (career.bowling.team == team)]
            if bowl.wickets.sum():
                wk = bowl.groupby("player").wickets.sum()
                assert w["wickets"]["wickets"] == wk.max() and wk[w["wickets"]["player"]] == wk.max()
                best = bowl[bowl.wickets == bowl.wickets.max()]
                assert (w["bowling"]["wickets"], w["bowling"]["runs"]) == (bowl.wickets.max(), best.runs.min())
            else:
                assert "wickets" not in w and "bowling" not in w
            st = PS.stands(career, mids)
            st = st[st.team == team]
            if len(st) and st.runs.max() > 0:
                assert w["stand"]["runs"] == st.runs.max()
            # the longest run of wins in date order
            best_run = run = 0
            for o in tm.outcome:
                run = run + 1 if o == "W" else 0
                best_run = max(best_run, run)
            assert w.get("streak", {}).get("wins", 0) == best_run
            won = tm[tm.outcome == "W"]
            assert ("win" in w) == bool(len(won))
            if "win" in w:
                assert w["win"]["id"] in set(won.match_id)
                inns = won[won.innings_win.fillna(False).astype(bool)]
                if len(inns):
                    assert w["win"]["id"] in set(inns.match_id)
                elif won.margin_runs.fillna(0).max() > 0:
                    assert won.set_index("match_id").margin_runs[w["win"]["id"]] == won.margin_runs.max()
            mv = MV.season_mvp(career, sec, season, "impact")
            mv = mv[mv.team == team]
            if len(mv):
                assert w["player"]["player"] == mv.iloc[0].player and w["player"]["points"] == pytest.approx(mv.points.max())
            seen += 1
    assert seen > 60


def test_season_wrapped_with_no_games_is_empty(career):
    from ccstats import wrapped as WR
    w = WR.season_wrapped(career, "ODIs", "1999", "India")
    assert w["matches"] == 0 and not any(k in w for k in WR.SLIDES)


def test_knocking_on_the_door_when_the_regulars_never_batted(career):
    """Every game of a team abandoned before its regulars batted (the odd save of only abandoned games): there's no
    regulars' figure to beat, so nobody is listed, and nothing is worked out from an empty list."""
    import warnings
    from types import SimpleNamespace
    m = career.matches
    ids = set(m[m.section == "ODIs"].match_id)
    team = "England"
    bat = career.batting.copy()
    bat.loc[bat.team == team, "did_bat"] = False
    c = SimpleNamespace(matches=career.matches, batting=bat, bowling=career.bowling.iloc[0:0], innings=career.innings)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        kn = PL.knocking(c, ids, team)
    assert kn.empty
