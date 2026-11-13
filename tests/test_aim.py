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
    """Every wicket the team's bowlers took is someone's, and every run off the bat too (the totals less the extras)."""
    for sec in career.matches.section.unique():
        ids = ids_of(career, sec)
        for team in sorted(set(career.matches[career.matches.match_id.isin(ids)].home)):
            t = A.team_shares(career, ids, team)
            mids = set(career.matches[career.matches.match_id.isin(ids) & ((career.matches.home == team) | (career.matches.away == team))].match_id)
            inn = career.innings[career.innings.match_id.isin(mids) & (career.innings.team == team)]
            assert t.runs.sum() == t.attrs["team_runs"] == inn.runs.sum() - inn.extras.sum()
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
    """Made-up games where the chance of winning is known exactly (one slope, a level for each of three competitions):
    the fit gets close to all four."""
    rng = np.random.default_rng(7)
    n = 9000
    z = rng.normal(0, 1, n)
    sec = rng.integers(0, 3, n)
    level = np.array([-0.4, 0.0, 0.5])
    y = (rng.random(n) < 1 / (1 + np.exp(-(1.3 * z + level[sec])))).astype(float)
    w = A._fit(z, sec, 3, y, ridge=0.0)
    assert w[0] == pytest.approx(1.3, abs=0.08)
    assert w[1:] == pytest.approx(level, abs=0.1)
    # started from the answer, it stays there (what the leave-one-out refits rely on)
    assert A._fit(z, sec, 3, y, start=w, ridge=0.0) == pytest.approx(w, abs=1e-6)


def test_the_ridge_keeps_a_lonely_competition_near_nought():
    """Three games of one competition, all won, among hundreds: its level stays small instead of running off."""
    rng = np.random.default_rng(3)
    n = 400
    z = rng.normal(0, 1, n)
    sec = np.zeros(n, int)
    sec[:3] = 1
    y = (rng.random(n) < 1 / (1 + np.exp(-z))).astype(float)
    y[:3] = 1.0
    with np.errstate(over="ignore"):
        loose = A._fit(z, sec, 2, y, ridge=1e-4)[2]
    assert abs(A._fit(z, sec, 2, y)[2]) < 1.5 < abs(loose)


def test_the_strengths_counted_by_hand(career):
    """The usual total, each team's batting and bowling (pulled to the usual: n / (n + 5)) and what home is worth
    (n / (n + 30)), from the finished first innings counted again by hand."""
    d = A._first_innings_all(career)
    st = A._strengths(d)
    m = career.matches.set_index("match_id")
    checked = 0
    for sec in d.section.unique():
        rows = []
        for r in career.innings[(career.innings.innings_no == 1)].itertuples():
            x = m.loc[r.match_id]
            if (x.section != sec or x.result_type != "win" or bool(x.rain)
                    or A.LENGTH.get(x.format) == "multi"):
                continue
            opp = x.away if r.team == x.home else x.home
            venue = "neutral" if x.neutral else "home" if r.team == x.home else "away"
            rows.append((r.team, opp, venue, float(r.runs)))
        usual = sum(t[3] for t in rows) / len(rows)
        s = st[sec]
        assert s["usual"] == pytest.approx(usual)
        for team in {t[0] for t in rows}:
            mine = [t[3] - usual for t in rows if t[0] == team]
            assert s["bat"][team] == (pytest.approx(sum(mine) / (len(mine) + 5)), len(mine))
        for team in {t[1] for t in rows}:
            theirs = [t[3] - usual for t in rows if t[1] == team]
            assert s["bowl"][team] == (pytest.approx(sum(theirs) / (len(theirs) + 5)), len(theirs))
        h = [t[3] - usual for t in rows if t[2] == "home"]
        aw = [t[3] - usual for t in rows if t[2] == "away"]
        raw = (sum(h) / len(h) - sum(aw) / len(aw)) / 2 if h and aw else 0.0
        assert s["home"] == pytest.approx(raw * (len(h) + len(aw)) / (len(h) + len(aw) + 30) if h and aw else 0.0)
        checked += 1
    assert checked >= 5


def test_the_targets_give_the_chances_back(career):
    """Put the even total and the 70% total back through the fitted curve, adjusted the same way as every game: they
    come out at 50% and 70%."""
    done = 0
    for length in ("t20", "one"):
        fit = A.model(career, length)
        if fit is None:
            continue
        for sec, i in fit["secs"].items():
            s = fit["st"][sec]
            teams = sorted(set(s["bat"]) | set(s["bowl"]))
            for me in teams:
                for opp in teams:
                    if me == opp:
                        continue
                    for venue in A.VENUES:
                        t = A.targets(fit, sec, me, opp, venue)
                        v = 1 if venue == "home" else -1 if venue == "away" else 0
                        for total, p in ((t["even"], 0.5), (t["seventy"], 0.7)):
                            adj = total - s["bowl"].get(me, (0.0, 0))[0] - s["bat"].get(opp, (0.0, 0))[0] + v * s["home"]
                            zz = (adj - s["usual"]) / fit["sd"]
                            assert 1 / (1 + math.exp(-(fit["w"][0] * zz + fit["w"][1 + i]))) == pytest.approx(p)
                        assert t["even"] < t["seventy"]
                        done += 1
    assert done > 50


def test_how_often_it_calls_games_right_is_each_game_judged_from_the_others(career):
    """'It would have called X% right': each game refitted without it, counted again by hand for one length."""
    fit = A.model(career, "t20")
    d = A._first_innings_all(career)
    d = d[d.length == "t20"].reset_index(drop=True)
    st = A._strengths(d)
    secs = sorted(d.section.unique())
    sec = d.section.map({s: i for i, s in enumerate(secs)}).to_numpy()
    mean_s = d.groupby("section").runs.transform("mean").to_numpy()
    z = (A._adjusted(d, st) - mean_s) / fit["sd"]
    y = d.won.to_numpy()
    right = []
    for i in range(len(d)):
        keep = np.arange(len(d)) != i
        w = A._fit(z[keep], sec[keep], len(secs), y[keep])
        right.append(((w[0] * z[i] + w[1 + sec[i]]) > 0) == (y[i] == 1))
    d["right"] = right
    for s, g in d.groupby("section"):
        assert fit["right"][s] == pytest.approx(g.right.mean(), abs=1e-9)
        assert fit["games"][s] == len(g)


def test_the_score_to_aim_says_why_when_it_cant_be_given(career):
    both = ids_of(career, "ODIs") | ids_of(career, "T20Is")
    assert "Pick one format" in A.score_to_aim(career, both, "India", "England")["none"]
    assert A.score_to_aim(career, set(), "India", "England")["none"]


def test_the_score_to_aim_from_the_games_themselves(career):
    """Every pair of teams in each one-day and T20 competition: the even total below the 70% one, the games it rests on
    the finished first innings, and the opponent's score and the meetings the real ones."""
    done, kept = 0, {}
    fits = lambda n: kept.setdefault(n, A.model(career, n))  # noqa: E731 - the slow fit once per length, as the site keeps it
    for sec in ("T20 Blast", "Indian Premier League", "ODIs", "T20Is", "The Hundred", "Vijay Hazare Trophy"):
        ids = ids_of(career, sec)
        m = career.matches[career.matches.match_id.isin(ids)]
        d = A.first_innings(career, ids)
        fin = d[d.outcome.isin(["won", "lost"])]
        teams = sorted(set(m.home) | set(m.away))
        for me in teams:
            for opp in teams:
                if me == opp:
                    continue
                a = A.score_to_aim(career, ids, me, opp, fits)
                assert a == A.score_to_aim(career, ids, me, opp) if done == 0 else True
                assert not a["none"] and a["kind"] == "limited" and a["section"] == sec
                assert a["games"] == len(fin)
                for venue, v in a["venues"].items():
                    assert v["even"] < v["seventy"]
                    assert v["few"] == (min(v["my_bowling_n"], v["their_batting_n"], a["games"]) < A.FEW)
                    assert v["their_batting_n"] == int((fin.team == opp).sum())
                    met = m[((m.home == me) & (m.away == opp)) | ((m.home == opp) & (m.away == me))]
                    here = [x for x in met.itertuples() if (("neutral" if x.neutral else "home" if x.home == me else "away") == venue)]
                    assert sorted(x["id"] for x in v["meetings"]) == sorted(x.match_id for x in here)
                    set_ = [r.runs for r in d.itertuples() if r.team == opp and r.match_id in {x.match_id for x in here}]
                    assert v["they_set_n"] == len(set_)
                    if set_:
                        assert v["they_set"] == int(round(float(np.median(set_))))
                done += 1
    assert done > 20


def test_the_score_to_aim_in_multi_day_cricket_counted_by_hand(career):
    """Tests and first-class: India's first-innings totals against each side, home, away and neutral, split by won,
    drawn and lost, with the typical (middle) one of each."""
    done = 0
    for sec in ("Tests", "Ranji Trophy", "County Championship · Division 1"):
        ids = ids_of(career, sec)
        m = career.matches[career.matches.match_id.isin(ids)]
        teams = sorted(set(m.home) | set(m.away))
        for me in teams:
            for opp in teams:
                if me == opp:
                    continue
                a = A.score_to_aim(career, ids, me, opp)
                assert a["kind"] == "multi" and not a["none"]
                for venue, v in a["venues"].items():
                    by = {"won": [], "drawn": [], "lost": []}
                    for x in m.itertuples():
                        if {x.home, x.away} != {me, opp} or x.result_type == "no result":
                            continue
                        if ("neutral" if x.neutral else "home" if x.home == me else "away") != venue:
                            continue
                        first = career.innings[(career.innings.match_id == x.match_id) & (career.innings.team == me)
                                               & (career.innings.team_innings == 1)]
                        if first.empty:
                            continue
                        res = "won" if x.winner == me else "lost" if x.winner == opp else "drawn" if x.result_type == "draw" else ""
                        if res:
                            by[res].append(int(first.runs.iloc[0]))
                    for res, xs in by.items():
                        assert v["typical"][res]["n"] == len(xs)
                        assert v["typical"][res]["typical"] == (int(round(float(np.median(xs)))) if xs else None)
                    done += 1
    assert done > 5


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


def test_my_teams_next_up_shows_the_same_score_to_aim(career):
    """My team's "next up" line: the same totals as Opponent preview for that opponent, format and ground; in Tests
    the first-innings total that usually beat them there."""
    from ccstats import fixtures as F
    from server import myteam as MY
    x = MY.next_up(career, "India", F.make_series("India", "West Indies", "ODI", 3, "home"))["next"]
    assert (x["opponent"], x["venue"]) == ("West Indies", "home")
    v = A.score_to_aim(career, set(F.format_ids(career, "India", "ODI")), "India", "West Indies")["venues"]["home"]
    assert x["aim"] == f"v West Indies, home, ODI: {v['even']} for an even game, {v['seventy']} for 70%" + (
        " (few games, treat with care)" if v["few"] else "")
    done = 0
    m = career.matches[career.matches.format == "Test"]
    for r in m.itertuples():
        for team, opp in ((r.home, r.away), (r.away, r.home)):
            for venue in A.VENUES:
                line = MY._aim_line(career, team, dict(format="Test", venue=venue if venue != "neutral" else "", opponent=opp))
                won = A.score_to_aim(career, set(F.format_ids(career, team, "Test")), team, opp)["venues"][venue]["typical"]["won"]
                where = "on a neutral ground" if venue == "neutral" else venue
                assert line == (f"v {opp}, {where}, Test: first-innings totals that beat them there were usually "
                                f"{won['typical']} ({won['n']} game{'s' if won['n'] != 1 else ''})" if won["n"] else "")
                done += bool(line)
    assert done
