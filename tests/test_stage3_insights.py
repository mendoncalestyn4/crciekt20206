"""Stage 3, Insights (your answers 7 and 14 of 13 November): every number the page shows equals the current site's for
the same career (the same engine sums, views/insights.py), and each is counted again here a second way, straight from
the scorecards: the board and the bands from the first innings, home advantage from the results, season by season from
the innings, innings by innings, the first-innings lead, breakouts from each season's own tables, the chase calculator's
similar games, and the new score to aim for against every side (the same targets as Opponent preview; in multi-day
cricket the totals that won, drew and lost). Odd addresses never break it, and there's no fielding."""

from __future__ import annotations

import json
import math

import numpy as np
import pytest

from ccstats import aim as AIM
from ccstats import demo_league as DL
from ccstats import insights as I
from ccstats import teamplay as TP
from ccstats import winprob as WP
from ccstats.loader import Career
from ccstats.stats import Scope, kind_of, player_tables
from server import insightspage as IP
from server.teampage import choices
from serverkit import FIXTURES


@pytest.fixture(scope="module")
def career():
    c = Career.build("Test career", [(f.name, f.read_bytes()) for f in FIXTURES])
    c.count_fielding = False
    return c


@pytest.fixture(scope="module")
def league():
    files = DL.generate((2026, 2027, 2028))
    c = Career.build("Demo", [(n, t.encode() if isinstance(t, str) else t) for n, t in files])
    c.count_fielding = False
    return c


def page(c, **q):
    return IP.insights_page(c, {k: str(v) for k, v in q.items()}, ["India"])


def first_innings_by_hand(c, ids):
    """Each finished, rain-free match's first innings and whether that side won, from the innings and the results."""
    m = c.matches[c.matches.match_id.isin(set(ids)) & (c.matches.result_type != "no result")]
    if "rain" in m:
        m = m[~m.rain.astype(bool)]
    out = []
    for r in m.itertuples():
        inn = c.innings[(c.innings.match_id == r.match_id) & (c.innings.innings_no == 1)]
        if inn.empty:
            continue
        t = inn.iloc[0]
        out.append((int(t.runs), r.winner == t.team, r.winner not in ("", t.team), r.result_type == "draw"))
    return out


def test_tabs_competitions_in_order_and_one_at_a_time(career):
    d = page(career)
    order = [x["section"] for x in choices(career)]
    assert d["tabs"] == IP.TABS and d["options"] == order and d["section"] == order[0]
    # several competitions asked for (remembered from another page): the first of them, on its own
    d = page(career, section="ODIs|T20Is")
    assert d["section"] == "ODIs"
    d = page(career, tab="Innings by innings")
    multi = [s for s in order if kind_of(career.matches[career.matches.section == s]) == "multi"]
    assert d["options"] == multi and d["section"] == multi[0]


@pytest.mark.parametrize("sec", ["ODIs", "T20Is", "Indian Premier League", "Tests"])
def test_total_enough_counted_again(career, sec):
    ids = career.matches[career.matches.section == sec].match_id
    rows = first_innings_by_hand(career, ids)
    for score in (0, 150, 250, 316, 2000):
        d = page(career, section=sec, score=score)
        score = min(score, 1500)
        hi = [r for r in rows if r[0] >= score]
        lo = [r for r in rows if r[0] < score]
        won_hi, won_lo = sum(r[1] for r in hi), sum(r[1] for r in lo)
        assert d["score"] == score
        assert d["board"]["line"] == f"won with {score} or more ({won_hi} of {len(hi)})"
        want = f"{won_hi / len(hi) * 100:.0f}%" if hi else "–"
        assert d["board"]["pct"] == want
        assert d["board"]["res"].startswith(f"With less than {score}: won {won_lo} of {len(lo)}")
    # the bands: every first innings in one band, its wins counted again (and the old site's own sums, equal)
    d = page(career, section=sec)
    size = d["bands"]["size"]
    table, size_old = I.total_enough(career, ids)
    assert size == size_old == {"t20": 10, "one": 20, "multi": 50}[kind_of(career.matches[career.matches.section == sec])]
    assert len(d["bands"]["rows"]) == len(table)
    for bar in d["bands"]["rows"]:
        lo_ = int(bar["label"].split("–")[0])
        x = [r for r in rows if lo_ <= r[0] < lo_ + size]
        assert bar["text"] == f"{sum(r[1] for r in x) / len(x) * 100:.0f}% · won {sum(r[1] for r in x)} of {len(x)}"
    # highest band at the top
    lows = [int(b["label"].split("–")[0]) for b in d["bands"]["rows"]]
    assert lows == sorted(lows, reverse=True)
    # the default score is the middle first-innings score, as on the current site
    assert d["default"] == int(np.median([r[0] for r in rows]))


def test_score_chances_and_good_side_equal_the_current_site(career):
    ids = career.matches[career.matches.section == "ODIs"].match_id
    for team in ("Every team", "India", "England"):
        d = page(career, section="ODIs", score=280, team=team)
        sc = TP.score_chances(career, ids, 280, "" if team == "Every team" else team)
        for side, key in zip(d["sides"], ("batting_first", "bowling_first")):
            r = sc[key]
            if not r["played"]:
                assert side["none"]
            else:
                assert side["value"] == (f"{r['win_pct']:.0f}%" if r["decided"] else "–")
                assert f"Won {r['won']} of {r['decided']}" in side["note"]
    # the default team is yours when you play here
    assert page(career, section="ODIs")["team"] == "India"
    pbs = I.par_by_strength(career, ids)
    d = page(career, section="ODIs")
    assert [r[0] for r in d["strong"]["rows"]] == list(pbs.band)


def test_score_to_aim_equals_opponent_preview_and_its_own_fit(career, league):
    """Every opponent's targets equal Opponent preview's (the same sums), and putting the even total back into the fit
    gives a 50% chance and the 70% total 70% (counted the other way round)."""
    for c, sec, me in ((career, "T20Is", "India"), (career, "ODIs", "India"), (league, None, None)):
        if sec is None:
            sec = next(s for s in c.matches.section.unique() if kind_of(c.matches[c.matches.section == s]) != "multi")
            m = c.matches[c.matches.section == sec]
            me = sorted(set(m.home) | set(m.away))[0]
        d = page(c, tab="Score to aim for", section=sec, team=me)
        assert d["team"] == me and d["kind"] == "limited"
        ids = list(c.matches[c.matches.section == sec].match_id)
        a = AIM.aim_table(c, sec, me)
        length = AIM.LENGTH.get(c.matches[c.matches.section == sec].format.mode().iloc[0], "t20")
        fit = AIM.model(c, length)
        for r in a["rows"]:
            pv = AIM.score_to_aim(c, ids, me, r["opp"])
            for v in a["venues"]:
                assert (r[v]["even"], r[v]["seventy"]) == (pv["venues"][v]["even"], pv["venues"][v]["seventy"])
                t = AIM.targets(fit, sec, me, r["opp"], v)
                st = fit["st"][sec]
                bowl, bat = st["bowl"].get(me, (0.0, 0))[0], st["bat"].get(r["opp"], (0.0, 0))[0]
                side = 1 if v == "home" else -1 if v == "away" else 0
                for total, want in ((t["even"], 0.5), (t["seventy"], 0.7)):
                    z = (total - bowl - bat + side * st["home"] - st["usual"]) / fit["sd"]
                    p = 1 / (1 + math.exp(-(fit["w"][0] * z + fit["w"][1 + fit["secs"][sec]])))
                    assert p == pytest.approx(want, abs=1e-9)
        # the table on the page: one row per opponent, each venue's two totals
        assert len(d["aim"]["rows"]) == len(a["rows"])
        for row, r in zip(d["aim"]["rows"], a["rows"]):
            assert row[0] == r["opp"]
            got = [x.rstrip("†") for x in row[1:1 + 2 * len(a["venues"])]]
            assert got == [str(r[v][k]) for v in a["venues"] for k in ("even", "seventy")]


def test_score_to_aim_multi_day_counted_again(career):
    """In Tests: each opponent's typical first-innings totals in wins, draws and defeats, from the innings."""
    m = career.matches[career.matches.section == "Tests"]
    for me in sorted(set(m.home) | set(m.away)):
        d = page(career, tab="Score to aim for", section="Tests", team=me)
        assert d["kind"] == "multi"
        rows = d["aim"]["rows"] if d.get("aim") else []
        want = {}
        for r in m.itertuples():
            if me not in (r.home, r.away) or r.result_type == "no result":
                continue
            opp = r.away if r.home == me else r.home
            venue = "neutral" if r.neutral else "home" if r.home == me else "away"
            inn = career.innings[(career.innings.match_id == r.match_id) & (career.innings.team == me) & (career.innings.team_innings == 1)]
            if inn.empty:
                continue
            res = "won" if r.winner == me else "lost" if r.winner == opp else "drawn" if r.result_type == "draw" else "tied"
            want.setdefault((opp, venue), {}).setdefault(res, []).append(int(inn.iloc[0].runs))
        words = {"home": f"{me} at home", "away": f"{me} away", "neutral": "Neutral ground"}
        got = {(r[0], r[1]): r for r in rows}
        assert len(got) == len(want)
        for (opp, venue), res in want.items():
            row = got[(opp, words[venue])]
            for i, k in enumerate(("won", "drawn", "lost")):
                xs = res.get(k, [])
                assert row[2 + i] == (f"{int(round(float(np.median(xs))))} ({len(xs)})" if xs else "–")
            assert row[5] == sum(len(x) for x in res.values())


def test_bat_first_and_strength_for_the_team_picked(career):
    d = page(career, tab="Score to aim for", section="ODIs", team="India")
    bf = d["bat_first"]
    g = TP.games(career, career.matches[career.matches.section == "ODIs"].match_id)
    t = g[g.team == "India"]
    assert bf["first"]["played"] == int(t.batted_first.sum()) and bf["chase"]["played"] == int((~t.batted_first).sum())
    assert bf["first"]["won"] == int(((t.outcome == "W") & t.batted_first).sum())
    assert all(k in bf for k in ("is_", "best", "for_"))
    s = d["strength"]
    assert s and {r["opp"] for r in s["rows"]} <= set(career.matches.home) | set(career.matches.away)
    assert all(r["gap"] == r["them"] - r["me"] for r in s["rows"])


@pytest.mark.parametrize("sec", ["ODIs", "T20Is", "Tests"])
def test_chase_calculator_counted_again(career, sec):
    """The similar chases: every match whose chase passed through that many wickets down within the band of runs
    (counted from the win states), the band never wider than 1.6^4 times the usual (it used to grow to thousands of
    runs), the wickets used inside 0-9."""
    ids = list(career.matches[career.matches.section == sec].match_id)
    kind = kind_of(career.matches[career.matches.section == sec])
    st = WP.states(career, ids)
    for target, now, down in ((181, 60, 3), (300, 150, 5), (250, 80, 0), (120, 100, 9)):
        c = WP.chase_chance(st, kind, target, now, down)
        assert c["band"] <= WP.BAND[kind] * 1.6 ** 4 + 1e-9
        lo, hi = c["wickets_used"]
        assert 0 <= lo <= down <= hi <= 9
        if c["n"]:
            inns = 4 if kind == "multi" else 2
            lead = (target - 1) - now
            x = st[(st.innings_no == inns) & ~st.t1_batting.astype(bool) & (st.wickets >= lo) & (st.wickets <= hi) & ((st.lead - lead).abs() <= c["band"])]
            if "rain" in x:
                x = x[~x.rain.astype(bool)]
            assert x.match_id.nunique() == c["n"]
        d = page(career, tab="Chase calculator", section=sec, target=target, now=now, down=down)
        if now >= target:
            assert d["won"]
        elif c["n"]:
            assert d["kpis"][0]["v"] == f"{c['win']:.0f}%"
            assert "34588" not in d["line"] and f"from {c['n']} {sec} chases" in d["line"]
    # the starting figures for each kind of cricket, as on the current site
    d = page(career, tab="Chase calculator", section=sec)
    assert (d["target"], d["now"], d["down"]) == ({**IP.CHASE_DEFAULTS}[kind] + (3,))


def test_home_advantage_counted_again(career):
    d = page(career, tab="Home advantage")
    order = [x["section"] for x in choices(career)]
    secs = [r["section"] for r in d["home"]["rows"]]
    assert secs == [s for s in order if s in set(secs)]
    for r in d["home"]["rows"]:
        g = career.matches[(career.matches.section == r["section"]) & ~career.matches.neutral.astype(bool)
                           & (career.matches.result_type != "no result")]
        hw, aw = int((g.winner == g.home).sum()), int((g.winner == g.away).sum())
        assert r["label"] == f"{r['section']} ({len(g)})"
        assert r["home"] == pytest.approx(hw / len(g) * 100, abs=0.05) and r["away"] == pytest.approx(aw / len(g) * 100, abs=0.05)
        assert r["home"] + r["away"] + r["other"] == pytest.approx(100, abs=0.1)


@pytest.mark.parametrize("which", ["career", "league"])
def test_season_by_season_counted_again(career, league, which):
    c = career if which == "career" else league
    for sec in c.matches.section.unique():
        d = page(c, tab="Season by season", section=sec)
        charts = {x["id"]: x for x in d["charts"]}
        assert list(charts) == [m[1] for m in IP.SEASON_MEASURES]
        for p in charts["runs_per_wicket"]["points"]:
            ids = c.matches[(c.matches.section == sec) & (c.matches.season.astype(str) == p["season"])].match_id
            inn = c.innings[c.innings.match_id.isin(ids)]
            assert p["v"] == pytest.approx(inn.runs.sum() / inn.wickets.sum(), abs=0.0051)   # sent to 2 decimals (a half rounds up)
        for p in charts["sixes_per_match"]["points"]:
            ids = c.matches[(c.matches.section == sec) & (c.matches.season.astype(str) == p["season"])].match_id
            b = c.batting[c.batting.match_id.isin(ids) & c.batting.did_bat]
            assert p["v"] == pytest.approx(b.sixes.sum() / len(ids), abs=0.0051) and p["matches"] == len(ids)


def test_breakouts_counted_again(league):
    sec = league.matches.section.iloc[0]
    seasons = sorted(map(str, league.matches[league.matches.section == sec].season.unique()))
    d = page(league, tab="Breakout players", section=sec, season=seasons[-1], min=3)
    assert d["earlier"] and d["season"] == seasons[-1]
    bats = d["parts"][0]
    assert bats.get("rows"), "the made-up league has improved batters"
    real = {str(s): s for s in league.matches.season.unique()}
    for bar in bats["rows"][:3]:
        p = bar["label"]
        now = player_tables(league, Scope(sections=[sec], seasons=[real[seasons[-1]]]))[0].set_index("player").loc[p]
        before_r = before_i = 0.0
        for s in seasons[:-1]:
            b = player_tables(league, Scope(sections=[sec], seasons=[real[s]]))[0].set_index("player")
            if p in b.index:
                before_r += b.loc[p].runs_above_average
                before_i += b.loc[p].innings
        jump = now.runs_above_average / now.innings - before_r / before_i
        assert bar["value"] == pytest.approx(jump, abs=0.01)
    # the first season has nothing before it
    d = page(league, tab="Breakout players", section=sec, season=seasons[0])
    assert d["first"] and not d["earlier"]


def test_innings_by_innings_counted_again(career):
    d = page(career, tab="Innings by innings", section="Tests")
    ids = career.matches[career.matches.section == "Tests"].match_id
    for i, bar in enumerate(d["innings"]["rows"]):
        inn = career.innings[career.innings.match_id.isin(ids) & (career.innings.innings_no == i + 1)]
        assert bar["value"] == pytest.approx(inn.runs.sum() / max(inn.wickets.sum(), 1), abs=0.005)
    fl = WP.first_innings_lead(career, ids)
    assert [r[0] for r in d["lead"]["rows"]] == list(fl[fl.matches > 0].band)
    fo = TP.follow_on_and_declarations(career, ids)
    assert (d.get("follow") is None) == fo.empty


@pytest.mark.parametrize("q", [dict(tab="junk"), dict(section="No such cup"), dict(score="abc"), dict(score="-40"),
                               dict(score="1e9"), dict(tab="Chase calculator", target="-5", now="x", down="99"),
                               dict(tab="Breakout players", season="1999", min="7"), dict(tab="Score to aim for", team="Nobody"),
                               dict(tab="Innings by innings", section="T20Is"), dict(tab="Is this total enough?", team="Nobody", season="x")])
def test_odd_addresses_never_break_it(career, q):
    d = page(career, **q)
    assert d["tab"] in IP.TABS and json.dumps(d)
    if "score" in q:
        assert 0 <= d["score"] <= 1500
    if q.get("tab") == "Chase calculator":
        assert 1 <= d["target"] <= 1000 and 0 <= d["now"] <= 1000 and 0 <= d["down"] <= 9


def test_no_fielding_and_empty_career():
    empty = Career.build("Empty", [])
    d = IP.insights_page(empty, {}, [])
    assert d["none"] and d["choices"] == []


def test_no_fielding_words(career):
    for tab in IP.TABS:
        text = json.dumps(page(career, tab=tab)).lower()
        assert not any(w in text for w in ("catch", "caught", "stumping", "run-out credit"))


def test_batting_first_line_matches_its_chart(career):
    """Found in the stage 3 screenshots: the chart said "won 60%" (21 of 35 played, two drawn) and the line under it
    "64% won" (draws left out). Both now count out of the games played, as the Teams page does."""
    for sec in ("Tests", "ODIs"):
        for team in sorted(set(career.matches[career.matches.section == sec].home))[:4]:
            bf = page(career, tab="Score to aim for", section=sec, team=team).get("bat_first")
            if not bf:
                continue
            for key, word in (("first", "batting first"), ("chase", "batting second" if bf["multi"] else "chasing")):
                r = bf[key]
                if r["played"] and word in bf["best"]:
                    assert f"{r['won'] / r['played'] * 100:.0f}% won" in bf["best"], (team, bf["best"], r)
