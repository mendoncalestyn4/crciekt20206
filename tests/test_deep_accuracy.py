"""Accuracy checks for the deeper figures (Stat by stat, Players, Teams): each
figure is counted a second time, straight from the scorecard tables, in a
different way from the code that shows it, and the two must agree exactly."""

from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ccstats import deep as D
from ccstats import partnerships as P
from ccstats import playerdeep as PD
from ccstats import teamdeep as TD
from ccstats import teamplay as TP
from ccstats.loader import Career
from ccstats.stats import KIND, Scope, player_tables

FIXTURES = sorted((Path(__file__).parent / "fixtures").glob("*.txt"))
NEW = Path(__file__).parent / "fixtures_2026" / "new_playthrough.zip"
IPL = "Indian Premier League"


@pytest.fixture(scope="module")
def season():
    return Career.build("2026", [(NEW.name, NEW.read_bytes())])


@pytest.fixture(scope="module")
def career():
    return Career.build("x", [(p.name, p.read_bytes()) for p in FIXTURES])


def ids_of(c, section):
    return c.matches[c.matches.section == section].match_id


def batted(c, ids):
    b = c.batting[c.batting.match_id.isin(ids) & c.batting.did_bat]
    return b.assign(date=b.match_id.map(c.matches.set_index("match_id").date))


def bowled(c, ids):
    w = c.bowling[c.bowling.match_id.isin(ids) & (c.bowling.balls > 0)]
    return w.assign(date=w.match_id.map(c.matches.set_index("match_id").date))


# =========================================================================== #
# Stat by stat: percentiles, change since last season, fair figures
# =========================================================================== #


def test_percentiles_rank_the_best_first(season):
    bat, *_ = player_tables(season, Scope(sections=[IPL]))
    p = D.percentiles(bat, "runs", "high")
    best = bat.runs.idxmax()
    assert p[best] == pytest.approx(max(1, 1 / len(bat) * 100))
    # more runs never gives a worse percentile
    order = bat.runs.sort_values(ascending=False).index
    assert p[order].is_monotonic_increasing
    assert D.top_text(1) == "top 1%" and D.top_text(50) == "top 50%" and D.top_text(80) == "bottom 21%"
    # lower-is-better: the lowest economy is the top
    _, bowl, *_ = player_tables(season, Scope(sections=[IPL]))
    q = D.percentiles(bowl, "economy", "low")
    assert q[bowl.economy.idxmin()] == q.min()


def test_fair_index_in_one_section_is_rate_over_section_rate(season):
    scope = Scope(sections=[IPL])
    s, unit = D.fair_index(season, scope, "Batting", "runs", "section")
    assert unit == "%"
    b = batted(season, ids_of(season, IPL))
    section_rate = b.runs.sum() / len(b)  # runs per innings across everyone
    per = b.groupby("player").agg(runs=("runs", "sum"), inns=("runs", "size"))
    for p in per.sort_values("inns").index[-10:]:
        mine = per.loc[p, "runs"] / per.loc[p, "inns"]
        assert s[p] == pytest.approx((mine / section_rate - 1) * 100)
    # economy is lower-is-better: turned round, so a bowler with a low economy scores above 0
    e, _ = D.fair_index(season, scope, "Bowling", "economy", "section")
    w = bowled(season, ids_of(season, IPL))
    sec = w.runs.sum() / w.balls.sum()
    g = w.groupby("player")[["runs", "balls"]].sum()
    for p in g.sort_values("balls").index[-10:]:
        assert e[p] == pytest.approx((sec / (g.loc[p, "runs"] / g.loc[p, "balls"]) - 1) * 100)


def test_fair_index_over_two_sections_weights_by_innings(season):
    secs = ["T20Is", IPL]
    s, _ = D.fair_index(season, Scope(sections=secs), "Batting", "runs", "section")
    num, den = {}, {}
    for sec in secs:
        b = batted(season, ids_of(season, sec))
        rate = b.runs.sum() / len(b)
        for p, g in b.groupby("player"):
            num[p] = num.get(p, 0) + (g.runs.sum() / len(g) / rate) * len(g)
            den[p] = den.get(p, 0) + len(g)
    for p in num:
        assert s[p] == pytest.approx((num[p] / den[p] - 1) * 100)


def test_change_since_last_season_is_this_minus_last(career):
    sec = "ODIs"
    scope = Scope(sections=[sec], seasons=["2027"])
    ch, prev = D.change_since(career, scope, "Batting", "runs")
    assert prev == "2026"
    b = career.batting[career.batting.match_id.isin(ids_of(career, sec))]  # the whole XI: played, batted or not
    b = b.assign(season=b.match_id.map(career.matches.set_index("match_id").season))
    now = b[b.season == "2027"].groupby("player").runs.sum()
    before = b[b.season == "2026"].groupby("player").runs.sum()
    both = now.index.intersection(before.index)
    assert set(ch.index) == set(both)
    for p in both:
        assert ch[p] == now[p] - before[p]
    # not shown unless exactly one season is picked
    assert D.change_since(career, replace(scope, seasons=[]), "Batting", "runs")[1] is None


# =========================================================================== #
# Players: danger zones, funnel, fastest, impact, with/without, badges
# =========================================================================== #


def test_danger_zones_add_up_to_every_dismissal(season):
    ids = ids_of(season, IPL)
    b = batted(season, ids)
    outs = b[b.out]
    for p in b.player.value_counts().index[:15]:
        d = PD.danger_zones(season, ids, p)
        mine = outs[outs.player == p]
        assert d.outs.sum() == len(mine) == d.attrs["dismissals"]
        if len(mine):
            assert d.pct.sum() == pytest.approx(100)
        # T20 bands: 0-9, 10-19, 20-29, 30-49, 50+
        expect = [((mine.runs >= lo) & (mine.runs <= hi)).sum() for lo, hi in [(0, 9), (10, 19), (20, 29), (30, 49)]]
        expect.append((mine.runs >= 50).sum())
        assert d.outs.tolist() == expect
    assert d.all_pct.sum() == pytest.approx(100)


@pytest.mark.parametrize("section,keys", [(IPL, [20, 50]), ("ODIs", [30, 50, 80, 100]), ("Tests", [50, 80, 100])])
def test_funnel_counts_every_mark(season, career, section, keys):
    c = season if section == IPL else career
    ids = ids_of(c, section)
    b = batted(c, ids)
    assert PD.funnel(c, ids, b.player.iloc[0]).query("highlight").mark.tolist() == keys
    for p in b.player.value_counts().index[:12]:
        f = PD.funnel(c, ids, p).set_index("mark")
        mine = b[b.player == p]
        assert f.attrs["innings"] == len(mine)
        for mk in f.index:
            assert f.loc[mk, "innings"] == (mine.runs >= mk).sum()
            assert f.loc[mk, "pct"] == pytest.approx((mine.runs >= mk).mean() * 100)
            assert f.loc[mk, "all_pct"] == pytest.approx((b.runs >= mk).mean() * 100)
        # conversion between key marks: of the innings that reached the last key mark, how many reached this one
        for lo, hi in zip(keys, keys[1:]):
            reached = (mine.runs >= lo).sum()
            want = (mine.runs >= hi).sum() / reached * 100 if reached else np.nan
            got = f.loc[hi, "from_key"]
            assert (np.isnan(want) and np.isnan(got)) or got == pytest.approx(want)
            assert f.loc[hi, "key_from"] == str(lo)


def test_fastest_to_counts_innings_in_t20(season):
    ids = ids_of(season, IPL)
    f = PD.fastest(season, ids)
    assert f.attrs["unit"] == "innings"
    b = batted(season, ids).sort_values(["date", "match_id", "innings_no"])
    for p, g in b.groupby("player"):
        run = g.runs.cumsum().to_numpy()
        got = f[(f.what == "runs") & (f.milestone == 500) & (f.player == p)]
        if (run >= 500).any():
            assert got.taken.iloc[0] == int(np.argmax(run >= 500)) + 1
        else:
            assert got.empty
    # ranks: 1 = fewest innings
    r = f[(f.what == "runs") & (f.milestone == 500)]
    if len(r):
        assert (r[r["rank"] == 1].taken == r.taken.min()).all()


def test_fastest_to_counts_every_match_played_in_tests(career):
    ids = career.matches[KIND.get("Test") == "multi"].match_id if False else ids_of(career, "Tests")
    f = PD.fastest(career, ids)
    assert f.attrs["unit"] == "matches"
    # build each player's match-by-match runs from the full XI (did they bat or not)
    m = career.matches.set_index("match_id")
    xi = career.batting[career.batting.match_id.isin(ids)]
    for p, g in xi.groupby("player"):
        per = g.groupby("match_id").runs.sum()
        per = per.loc[sorted(per.index, key=lambda x: (m.date[x], x))]
        run = per.cumsum().to_numpy()
        for target in PD.MILESTONES["multi"]["runs"]:
            got = f[(f.what == "runs") & (f.milestone == target) & (f.player == p)]
            assert got.empty == (not (run >= target).any())


def test_match_impact_matches_the_formula(season):
    ids = ids_of(season, IPL)
    d = PD.match_impact(season, ids)
    b, w = batted(season, ids), bowled(season, ids)
    inn = season.innings[season.innings.match_id.isin(ids)]
    rpw = inn.runs.sum() / inn.wickets.sum()
    sr = b.runs.sum() / b.balls.sum()
    econ = w.runs.sum() / w.balls.sum()
    assert d.runs.sum() == b.runs.sum() and d.wickets.sum() == w.wickets.sum()
    f = season.fielding[season.fielding.match_id.isin(ids) & season.fielding.resolved]
    for r in d.sample(25, random_state=1).itertuples():
        mb = b[(b.match_id == r.match_id) & (b.player == r.player)]
        mw = w[(w.match_id == r.match_id) & (w.player == r.player)]
        mf = f[(f.match_id == r.match_id) & (f.player == r.player)]
        want = (mb.runs.sum() + 0.5 * (mb.runs.sum() - mb.balls.sum() * sr)
                + mw.wickets.sum() * rpw + (mw.balls.sum() * econ - mw.runs.sum()) + len(mf) * rpw * 0.25)
        assert r.impact == pytest.approx(want)


def test_with_and_without_wickets_add_up(season):
    ids = ids_of(season, IPL)
    w = bowled(season, ids)
    for p in w.player.value_counts().index[:10]:
        x = PD.with_without(season, ids, p)
        mine = w[w.player == p]
        assert x["with"]["spells"] + x["without"]["spells"] == len(mine)
        assert x["with"]["wickets"] == mine.wickets.sum() and x["without"]["wickets"] == 0
        assert x["with"]["runs"] + x["without"]["runs"] == mine.runs.sum()
        if x["without"]["balls"]:
            z = mine[mine.wickets == 0]
            assert x["without"]["economy"] == pytest.approx(z.runs.sum() / z.balls.sum() * 6)


def test_badges_are_all_real(season, career):
    for c in (season, career):
        a = PD.achievements(c)
        info = c.matches.set_index("match_id")
        kind = c.matches.set_index("match_id").format.map(lambda f: KIND.get(f, "t20"))
        b = batted(c, c.matches.match_id)
        w = bowled(c, c.matches.match_id)
        # T20 hundreds: exactly the T20 innings of 100+
        want = b[(b.match_id.map(kind) == "t20") & (b.runs >= 100)]
        assert (a.badge == "T20 hundred").sum() == len(want)
        # five-fors and sevens by format
        assert (a.badge == "5-for in a T20").sum() == ((w.match_id.map(kind) == "t20") & (w.wickets >= 5)).sum()
        assert (a.badge == "One-day five-for").sum() == ((w.match_id.map(kind) == "one") & (w.wickets >= 5)).sum()
        assert (a.badge == "Seven in an innings").sum() == ((w.match_id.map(kind) == "multi") & (w.wickets >= 7)).sum()
        assert (a.badge == "Double hundred").sum() == ((b.match_id.map(kind) == "multi") & (b.runs >= 200)).sum()
        # a pair is out for 0 twice in the same multi-day match
        mb = b[b.match_id.map(kind) == "multi"]
        pairs = mb[(mb.runs == 0) & mb.out].groupby(["match_id", "player"]).size()
        assert (a.badge == "Pair").sum() == (pairs >= 2).sum()
        # carried the bat: opener, not out, side all out, never in a T20
        for r in a[a.badge == "Carried the bat"].itertuples():
            row = b[(b.match_id == r.match_id) & (b.player == r.player) & ~b.out & (b.position <= 2)]
            assert len(row) and kind[r.match_id] != "t20"
            k = c.innings.set_index(["match_id", "innings_no"]).loc[(r.match_id, row.innings_no.iloc[0])]
            assert bool(k.all_out)
        # every badge is in a match that exists
        assert a.match_id.isin(info.index).all()


# =========================================================================== #
# Teams: dominance, ratings, clutch, chemistry, pressure, fortress, squads, Tests
# =========================================================================== #

THRASH = {"t20": (40, 7), "one": (75, 7), "multi": (150, 8)}
CLOSE = {"t20": 10, "one": 20, "multi": 50}


def classify(r, kind):
    runs, wkts = THRASH[kind]
    if r.innings_win:
        return "thrashing"
    if pd.notna(r.margin_runs):
        return "thrashing" if r.margin_runs >= runs else "scrape" if r.margin_runs < CLOSE[kind] else "comfortable"
    if pd.notna(r.margin_wickets):
        return "thrashing" if r.margin_wickets >= wkts else "scrape" if r.margin_wickets <= 2 else "comfortable"
    return "scrape"


@pytest.mark.parametrize("section", [IPL, "ODIs", "Tests", "T20 Blast"])
def test_dominance_recount(season, career, section):
    c = season if section == IPL else career
    ids = ids_of(c, section)
    d = TD.dominance(c, ids).set_index("team")
    m = c.matches[c.matches.match_id.isin(ids)]
    count = {}
    for r in m.itertuples():
        win = r.winner if r.winner else r.tiebreak_winner
        for t in (r.home, r.away):
            if win:
                key = ("won_" if win == t else "lost_") + classify(r, KIND.get(r.format, "t20"))
            else:
                key = {"draw": "drawn", "tie": "tied"}.get(r.result_type)
            if key:
                count[(t, key)] = count.get((t, key), 0) + 1
    for team in d.index:
        for col in ("won_thrashing", "won_comfortable", "won_scrape", "lost_thrashing", "lost_comfortable",
                    "lost_scrape", "drawn", "tied"):
            assert d.loc[team, col] == count.get((team, col), 0), (team, col)
        played = d.loc[team, ["won", "lost", "drawn", "tied"]].sum()
        assert d.loc[team, "index"] == pytest.approx((d.loc[team, "won_thrashing"] - d.loc[team, "lost_thrashing"])
                                                      / played * 100)
    # every win is someone's defeat, class for class
    for cls in ("thrashing", "comfortable", "scrape"):
        assert d[f"won_{cls}"].sum() == d[f"lost_{cls}"].sum()


def test_dominance_known_results(career):
    d = TD.dominance(career, ids_of(career, "Tests")).set_index("team")
    # England beat Pakistan by 299 runs and by 8 wickets (thrashings) and by 4 wickets (comfortable)
    assert d.loc["England", ["won_thrashing", "won_comfortable", "won_scrape"]].tolist() == [2, 1, 0]
    assert d.loc["Pakistan", "lost_thrashing"] == 2 and d.loc["Pakistan", "drawn"] == 1


@pytest.mark.parametrize("section", [IPL, "Tests"])
def test_unit_ratings_recount(season, career, section):
    c = season if section == IPL else career
    ids = ids_of(c, section)
    got = TD.unit_ratings(c, ids).set_index("team")
    white = KIND.get(c.matches[c.matches.section == section].format.mode().iloc[0], "t20") != "multi"
    m = c.matches[c.matches.match_id.isin(ids)].sort_values(["date", "match_id"])
    inn = c.innings[c.innings.match_id.isin(ids)]
    # totals per (match, batting side)
    per = {}
    for r in inn.itertuples():
        if r.runs == 0 and r.balls == 0:
            continue  # abandoned before it started
        k = (r.match_id, r.team, r.opposition)
        a = per.setdefault(k, [0, 0, 0])
        a[0] += r.runs
        a[1] += r.wickets
        a[2] += r.balls
    scored, allowed = {}, {}
    for (mid, t, o), (r, w, b) in per.items():
        for dct, key in ((scored, t), (allowed, o)):
            x = dct.setdefault(key, [0, 0, 0])
            x[0] += r
            x[1] += w
            x[2] += b
    order = {mid: i for i, mid in enumerate(m.match_id)}
    for team in got.index:
        bats, bowls = [], []
        for (mid, t, o), (r, w, b) in sorted(per.items(), key=lambda kv: order[kv[0][0]]):
            rpw = r / max(w, 1)
            if t == team:
                v = rpw / (allowed[o][0] / max(allowed[o][1], 1))
                if white and b:
                    v = 0.5 * v + 0.5 * (r / b * 6) / (allowed[o][0] / max(allowed[o][2], 1) * 6)
                bats.append(v)
            if o == team:
                v = (scored[t][0] / max(scored[t][1], 1)) / rpw
                if white and b:
                    v = 0.5 * v + 0.5 * (scored[t][0] / max(scored[t][2], 1) * 6) / (r / b * 6)
                bowls.append(v)
        for vals, col in ((bats, "batting"), (bowls, "bowling")):
            wts = [TD.DECAY ** (len(vals) - 1 - i) for i in range(len(vals))]
            assert got.loc[team, col] == pytest.approx(sum(v * x for v, x in zip(vals, wts)) / sum(wts) * 1000)


def test_clutch_recount(season):
    ids = ids_of(season, IPL)
    m = season.matches[season.matches.match_id.isin(ids)]
    big = set(m[m.knockout].match_id)
    for r in m.itertuples():  # close: tie, under 10 runs, or 1-2 wickets
        if r.result_type == "tie" or (pd.notna(r.margin_runs) and r.margin_runs < 10) or \
                (pd.notna(r.margin_wickets) and r.margin_wickets <= 2):
            big.add(r.match_id)
    got_big, _ = TD.pressure_games(season, ids)
    assert big <= got_big  # knockouts and close games are all in (series deciders too, in series)
    bat, bowl = TD.clutch(season, ids, min_innings=3)
    b = batted(season, ids)
    for r in bat.itertuples():
        mine = b[b.player == r.player]
        assert mine.position.median() <= 7
        a, o = mine[mine.match_id.isin(got_big)], mine[~mine.match_id.isin(got_big)]
        assert r.clutch_innings == len(a)
        assert r.clutch_avg == pytest.approx(a.runs.sum() / max(a.out.sum(), 1))
        assert r.other_avg == pytest.approx(o.runs.sum() / max(o.out.sum(), 1))
    w = bowled(season, ids)
    for r in bowl.itertuples():
        mine = w[w.player == r.player]
        a = mine[mine.match_id.isin(got_big)]
        assert r.clutch_innings == len(a) and r.clutch_wpi == pytest.approx(a.wickets.mean())
        assert r.clutch_econ == pytest.approx(a.runs.sum() / a.balls.sum() * 6)


def test_clutch_fourth_innings_counts_in_tests(career):
    ids = ids_of(career, "Tests")
    _, fourth = TD.pressure_games(career, ids)
    inn = career.innings[career.innings.match_id.isin(ids)]
    assert fourth == set(zip(inn[inn.innings_no == 4].match_id, inn[inn.innings_no == 4].innings_no))


def test_chemistry_recount(season):
    ids = ids_of(season, IPL)
    s = P.stands(season, ids)
    by_wkt = s.groupby("wicket").runs.mean()
    ch = TD.chemistry(season, ids, min_stands=3)
    assert len(ch)
    for r in ch.itertuples():
        a, b = r.pair.split(" & ")
        mine = s[s.known & (s.team == r.team) & (((s.batter1 == a) & (s.batter2 == b)) | ((s.batter1 == b) & (s.batter2 == a)))]
        assert r.stands == len(mine) >= 3
        assert r.average == pytest.approx(mine.runs.mean())
        assert r.best == mine.runs.max()
        want_exp = np.mean([by_wkt[x] for x in mine.wicket])
        assert r.expected == pytest.approx(want_exp)
        assert r.chemistry == pytest.approx((mine.runs.mean() / want_exp - 1) * 100)


def test_sr_pressure_recount(season):
    ids = ids_of(season, IPL)
    d = TD.sr_pressure(season, ids)
    s = P.stands(season, ids)
    s = s[s.known]
    b = batted(season, ids)
    for r in d.head(8).itertuples():
        assert b[b.player == r.player].position.median() <= 7
        shared = {(x.match_id, x.innings_no, x.batter2 if x.batter1 == r.player else x.batter1)
                  for x in s.itertuples() if r.player in (x.batter1, x.batter2)}
        partners = {k[2] for k in shared}
        pin = b[b.player.isin(partners)]
        w = pin[[(m_, i, p) in shared for m_, i, p in zip(pin.match_id, pin.innings_no, pin.player)]]
        wo = pin.drop(w.index)
        assert r.innings == len(w)
        assert r.partner_sr_with == pytest.approx(w.runs.sum() / w.balls.sum() * 100)
        assert r.partner_sr_without == pytest.approx(wo.runs.sum() / wo.balls.sum() * 100)
    assert TD.sr_pressure(season, ids_of(season, IPL)).columns.tolist()[:2] == ["player", "team"]


@pytest.mark.parametrize("section", [IPL, "Tests", "T20 Blast"])
def test_fortress_recount(season, career, section):
    c = season if section == IPL else career
    ids = ids_of(c, section)
    f = TD.fortress(c, ids).set_index("team")
    m = c.matches[c.matches.match_id.isin(ids) & ~c.matches.neutral]
    for team in f.index:
        h = m[m.home == team]
        assert f.loc[team, "played"] == len(h)
        assert f.loc[team, "won"] == (h.winner == team).sum()
        assert f.loc[team, "lost"] == (h.loser == team).sum()
    assert set(f.index) == set(m.home)
    assert f.played.sum() == len(m)


def test_squad_changes_are_set_differences(career):
    ids = ids_of(career, "ODIs")
    d = TD.squad_changes(career, ids, "England")
    assert d.attrs["international"] and len(d)
    m = career.matches[career.matches.match_id.isin(ids) & ((career.matches.home == "England") | (career.matches.away == "England"))]
    period = m.set_index("match_id").apply(lambda r: r.series_id or f"{r.event} {r.season}", axis=1)
    first = m.groupby(m.match_id.map(period)).date.min().sort_values()
    b = career.batting[career.batting.match_id.isin(m.match_id) & (career.batting.team == "England")]
    squads = [set(b[b.match_id.map(period) == p].player) for p in first.index]
    want = sum(len(a - c) + len(c - a) for a, c in zip(squads, squads[1:]))
    assert len(d) == want
    a, c = squads[0], squads[1]
    first_step = d[d["from"] == d["from"].iloc[0]]
    assert set(first_step[first_step.change == "out"].player) == a - c
    assert set(first_step[first_step.change == "in"].player) == c - a
    assert "England" not in " ".join(d["from"]).split(" v ")[1]  # the label names the opponents, not England


def test_second_innings_recount(career):
    ids = ids_of(career, "Tests")
    d = TD.second_innings(career, ids).set_index("team")
    inn = career.innings[career.innings.match_id.isin(ids)]
    m = career.matches.set_index("match_id")
    for team in d.index:
        sec = inn[(inn.team == team) & (inn.team_innings == 2)]
        assert d.loc[team, "second_innings"] == len(sec)
        assert d.loc[team, "cheap"] == (sec.all_out & (sec.runs < 200)).sum()
        four = inn[(inn.team == team) & (inn.innings_no == 4)]
        res = [("W" if m.winner[x] == team else "L" if m.winner[x] else "D" if m.result_type[x] == "draw" else "?")
               for x in four.match_id]
        assert (d.loc[team, "chases"], d.loc[team, "chase_won"], d.loc[team, "chase_drawn"], d.loc[team, "chase_lost"]) \
            == (len(four), res.count("W"), res.count("D"), res.count("L"))


def test_bowler_match_pattern_recount(career):
    ids = ids_of(career, "Tests")
    d = TD.bowler_match_pattern(career, ids, min_matches=1)
    assert len(d)
    w = bowled(career, ids)
    for r in d.itertuples():
        mine = w[w.player == r.player].sort_values(["match_id", "innings_no"])
        two = [g for _, g in mine.groupby("match_id") if len(g) >= 2]
        assert r.matches == len(two)
        f = pd.concat([g.iloc[[0]] for g in two])
        s = pd.concat([g.iloc[[1]] for g in two])
        if f.wickets.sum():
            assert r.first_avg == pytest.approx(f.runs.sum() / f.wickets.sum())
        if s.wickets.sum():
            assert r.second_avg == pytest.approx(s.runs.sum() / s.wickets.sum())
        assert r.both_pct == pytest.approx(np.mean([(g.wickets > 0).all() for g in two]) * 100)
        bm = mine.groupby("match_id")[["wickets", "runs"]].sum()
        top = bm.sort_values(["wickets", "runs"], ascending=[False, True]).iloc[0]
        assert r.best_match == f"{top.wickets}/{top.runs}"


def test_games_close_uses_the_format_bar(career):
    g = TP.games(career, ids_of(career, "Tests"))
    # a Test won by 4 wickets is not close; the Pakistan draw is not close either
    assert not g[g.margin_wickets == 4].close.any()


def test_sr_pressure_never_divides_by_zero(season):
    for sec in season.matches.section.unique():
        d = TD.sr_pressure(season, ids_of(season, sec), min_innings=1)
        assert np.isfinite(d.effect).all() and (d.partner_sr_without > 0).all()
