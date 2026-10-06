"""Accuracy checks for records over time, near misses, best XIs, ranking history,
picks against an opponent, the after-match summary, table extras, the World Test
Championship table and the reviews: each recounted straight from the scorecards."""

from pathlib import Path


import pandas as pd
import pytest

from ccstats import rankings as R
from ccstats import records as RC
from ccstats import seasonal as SN
from ccstats import tables as T
from ccstats.loader import Career
from ccstats.local import CareerSettings, CareerStore

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


# --------------------------------------------------------------------------- 104 · record timeline
@pytest.mark.parametrize("section", [IPL, "T20Is", "ODIs"])
def test_record_timeline_steps(season, career, section):
    c = season if section == IPL else career
    ids = ids_of(c, section)
    tl = SN.record_timeline(c, ids)
    recs = RC.records(c, ids, top=1)
    full = RC.records(c, ids, top=10 ** 9)
    for name in set(tl.record):
        s = tl[tl.record == name].reset_index(drop=True)
        low = name.startswith("Lowest")
        # the last step is today's record
        assert s["sort"].iloc[-1] == recs[name]["sort"].iloc[0]
        # each step strictly beats the one before, and dates never go backwards
        diffs = s["sort"].diff().dropna()
        assert ((diffs < 0) if low else (diffs > 0)).all()
        assert s.date.is_monotonic_increasing
        assert list(s.step) == list(range(len(s)))
        assert s.until.iloc[-1] is pd.NaT or pd.isna(s.until.iloc[-1])
        assert (s.until.iloc[:-1].to_numpy() == s.date.iloc[1:].to_numpy()).all()
        # brute force: at each step's date, nothing earlier was as good
        f = full[name]
        for r in s.itertuples():
            before = f[f.date < r.date]
            if len(before):
                assert (r.sort < before["sort"].min()) if low else (r.sort > before["sort"].max())
        # the first mark is from the first date with an entry
        assert s.date.iloc[0] == f.date.min()


def test_record_number(season):
    assert SN.record_number("Highest individual scores", 115 * 2 + 1) == 115
    assert SN.record_number("Best bowling in an innings", 6 * 1000 - 37) == 6
    assert SN.record_number("Most wickets in a season", 31 * 100000 - 400) == 31
    assert SN.record_number("Highest team totals", 256) == 256


# --------------------------------------------------------------------------- 105 · near misses
def test_near_misses_measure_the_gap(season):
    ids = ids_of(season, IPL)
    recs = RC.records(season, ids, top=5)
    b = season.batting[season.batting.match_id.isin(ids) & season.batting.did_bat]
    top2 = b.sort_values(["runs", "out"], ascending=[False, True]).head(2)
    txt = SN.near_miss("Highest individual scores", recs["Highest individual scores"])
    gap = int(top2.runs.iloc[0] - top2.runs.iloc[1])
    assert txt.startswith("closest:") and (f"({gap} run" in txt or "same score" in txt)
    assert top2.player.iloc[1] in txt
    t = recs["Highest team totals"]
    if (t["rank"] == 1).sum() == 1:
        assert f"({int(t['sort'].iloc[0] - t[t['rank'] > 1]['sort'].iloc[0])} run" in SN.near_miss("Highest team totals", t)
    # best bowling: same wickets -> more runs; fewer wickets -> wickets short
    w = season.bowling[season.bowling.match_id.isin(ids) & (season.bowling.balls > 0)]
    w = w.assign(k=w.wickets * 1000 - w.runs).sort_values("k", ascending=False)
    a, c = w.iloc[0], w[w.k < w.k.iloc[0]].iloc[0]
    txt = SN.near_miss("Best bowling in an innings", recs["Best bowling in an innings"])
    want = (f"{a.wickets - c.wickets} wicket" if a.wickets != c.wickets else f"{c.runs - a.runs} more run")
    assert want in txt
    assert SN.near_miss("Highest team totals", t.head(1)) == ""


# --------------------------------------------------------------------------- 106 · best XI
@pytest.mark.parametrize("section", [IPL, "Tests", "T20 Blast", "ODIs"])
def test_best_xi_follows_the_rules(season, career, section):
    c = season if section == IPL else career
    ids = ids_of(c, section)
    xi = SN.best_xi(c, ids)
    assert len(xi) == 11 and xi.player.is_unique
    d, base = SN.player_pool(c, ids)
    d = d.set_index("player")
    need = xi.attrs["need"]
    assert need == max(2, -(-int(d.games.max()) // 3))
    real = xi[~xi.slot.str.contains("best available")]
    for r in real.itertuples():
        p = d.loc[r.player]
        if r.slot.startswith("Opener"):
            assert p.inns >= need and p.top >= 0.5
        if r.slot == "Bowler":
            assert p.spells >= need and p.wkts > 0
        if "eeper" in r.slot:
            assert p.stumpings > 0
        if r.slot == "All-rounder":
            assert p.pos <= 8 and p.spells >= need and p.inns >= need
    # the bowlers are the best four qualified bowlers left once the batters were picked
    bowlers = real[real.slot == "Bowler"].player
    if len(bowlers):
        before = set(xi.player) - set(bowlers)
        q = d[(d.spells >= need) & (d.wkts > 0) & ~d.index.isin(before)].sort_values("bowl_score", ascending=False)
        assert set(bowlers) == set(q.index[:len(bowlers)])
    # batting measure by format
    p0 = d.loc[xi.player.iloc[0]]
    want = p0.avg if base["kind"] == "multi" else p0.avg * p0.sr / 100
    assert p0.bat_score == pytest.approx(want)
    assert p0.avg == pytest.approx(p0.runs / max(p0.outs, 1))


def test_team_xi_only_uses_that_team(season):
    ids = ids_of(season, IPL)
    team = season.matches[season.matches.match_id.isin(ids)].home.iloc[0]
    xi = SN.best_xi(season, ids, team)
    played = set(season.batting[season.batting.match_id.isin(ids) & (season.batting.team == team)].player)
    assert set(xi.player) <= played and len(xi) == 11


# --------------------------------------------------------------------------- 107 · rankings history
def test_ranking_history_ends_on_todays_ratings(season):
    for what in ("batting", "bowling"):
        h, reigns = SN.ranking_history(season, IPL, what)
        now = R.player_ratings(season, IPL)
        now = now[now[what].notna()].set_index("player")[what]
        cur = h.set_index("player").current.dropna()
        assert set(cur.index) == set(now.index)
        for p in now.index:
            assert round(cur[p]) == pytest.approx(now[p], abs=1)
        assert (h.peak >= h.current.fillna(-1) - 1e-9).all()
        # every rated match day has a No. 1, and the reigns add up to the days
        assert reigns.matches.sum() <= h.at_no1.sum()
        assert reigns["from"].is_monotonic_increasing
        top_now = cur.idxmax()
        assert reigns.player.iloc[-1] == top_now or cur[reigns.player.iloc[-1]] == cur.max()


def test_combined_international_is_weighted_by_innings(career):
    ci = SN.combined_international(career, "batting")
    secs = SN.international_sections(career)
    assert set(secs) <= {"Test", "ODI", "T20I"}
    parts = {f: R.player_ratings(career, s).set_index("player") for f, s in secs.items()}
    for r in ci.head(10).itertuples():
        num = den = 0
        for f, t in parts.items():
            if r.player in t.index and pd.notna(t.batting.get(r.player)):
                num += t.batting[r.player] * t.batting_innings[r.player]
                den += t.batting_innings[r.player]
        assert r.combined == round(num / den)
        assert r.innings == den


# --------------------------------------------------------------------------- 112 · picks against an opponent
def test_picks_against_recount(season):
    ids = ids_of(season, IPL)
    m = season.matches[season.matches.match_id.isin(ids)]
    team = m.home.value_counts().index[0]
    opp = m[(m.home == team)].away.value_counts().index[0]
    bat, bowl = SN.picks_against(season, ids, team, opp)
    b = season.batting[season.batting.match_id.isin(ids) & season.batting.did_bat & (season.batting.team == team)]
    for r in bat.itertuples():
        v = b[(b.player == r.player) & (b.opposition == opp)]
        assert r.inns_vs == len(v) and r.runs_vs == v.runs.sum()
        assert r.avg_vs == pytest.approx(v.runs.sum() / max(v.out.sum(), 1))
        g = b[b.player == r.player]
        mv = r.avg_vs * r.sr_vs / 100
        mo = (g.runs.sum() / max(g.out.sum(), 1)) * (g.runs.sum() / max(g.balls.sum(), 1) * 100) / 100
        if mo:
            assert r.change == pytest.approx((mv / mo - 1) * 100)
        else:  # no runs at all here: nothing to compare with
            assert pd.isna(r.change)
        if r.inns_vs >= 2:
            assert r.verdict.startswith("Pick") == (r.change >= 25)
            assert r.verdict.startswith("Think") == (r.change <= -25)
    w = season.bowling[season.bowling.match_id.isin(ids) & (season.bowling.balls > 0) & (season.bowling.team == team)]
    for r in bowl.itertuples():
        v = w[(w.player == r.player) & (w.opposition == opp)]
        assert r.spells_vs == len(v) and r.wkts_vs == v.wickets.sum()


# --------------------------------------------------------------------------- 115 · after the match
def test_after_match(season):
    team = "Mumbai Indians"
    am = SN.after_match(season, team)
    po = RC.played_order(season)
    last = po[(po.home == team) | (po.away == team)].iloc[-1]
    assert am["match_id"] == last.match_id
    _, hist = R.team_elo(season, last.section)
    h = hist[(hist.match_id == last.match_id) & (hist.team == team)].iloc[0]
    assert am["elo"] == (pytest.approx(h.before), pytest.approx(h.after))
    if am.get("position"):
        lg = season.matches[(season.matches.event == last.event) & (season.matches.season == last.season)
                            & ~season.matches.knockout].sort_values(["date", "match_id"])
        upto = list(lg.match_id)[:list(lg.match_id).index(last.match_id) + 1]
        t = T.league_tables(season, upto)[0][1]
        assert am["position"][1][0] == int(t.index[t.team == team][0])


def test_after_match_series_score(career):
    m = career.matches
    last = m[m.series_id == "Test-7"].sort_values("date").iloc[-1]
    am = SN.after_match(career, "England", last.match_id)
    assert am["series"]["won"] == 3 and am["series"]["lost"] == 0
    inn = career.innings[career.innings.match_id == last.match_id]
    f = inn[inn.team_innings == 1].set_index("team").runs
    assert am["lead"] == f["England"] - f["Pakistan"]


# --------------------------------------------------------------------------- 118 · table extras
def test_table_extras(season):
    ids = ids_of(season, IPL)
    label, t, _ = T.league_tables(season, ids)[0]
    ex = SN.table_extras(season, ids, t, label).set_index("team")
    m = season.matches[season.matches.match_id.isin(ids) & ~season.matches.knockout].sort_values(["date", "match_id"])
    inn = season.innings[season.innings.match_id.isin(m.match_id)]
    for team in t.team:
        g = m[(m.home == team) | (m.away == team)]
        win = [w or (tw if rt == "tie" else "") for w, tw, rt in zip(g.winner, g.tiebreak_winner, g.result_type)]
        res = ["W" if w == team else "L" if w else "N" if rt == "no result" else "T" for w, rt in zip(win, g.result_type)]
        assert ex.loc[team, "form"] == " ".join(res[-5:])
        wins = sum(r == "W" for r in res)
        hw, hl = map(int, ex.loc[team, "home"].split("–"))
        aw, al = map(int, ex.loc[team, "away"].split("–"))
        assert hw + aw == wins  # IPL games all have a home side
        assert hw == sum(1 for w, h in zip(win, g.home) if w == team and h == team)
        assert t.set_index("team").won[team] == wins
        b = inn[inn.team == team]
        assert ex.loc[team, "rr_for"] == pytest.approx(b.runs.sum() / b.balls.sum() * 6)
    # position change: the table before the last match day
    before = m[m.date < m.date.max()].match_id
    prev = T.league_tables(season, before)[0][1]
    for team in t.team:
        moved = int(prev.index[prev.team == team][0]) - int(t.index[t.team == team][0])
        assert ex.loc[team, "moved"] == moved


# --------------------------------------------------------------------------- 136 · WTC
def test_wtc_table(career):
    assert SN.wtc_cycle(pd.Timestamp("2026-10-18")) == 2025
    assert SN.wtc_cycle(pd.Timestamp("2027-05-31")) == 2025
    assert SN.wtc_cycle(pd.Timestamp("2027-06-01")) == 2027
    assert SN.wtc_cycle(pd.Timestamp("2028-01-01")) == 2027
    w = SN.wtc_matches(career)
    assert (w.format == "Test").all() and w.home.isin(SN.WTC_TEAMS).all() and w.away.isin(SN.WTC_TEAMS).all()
    for cyc in w.cycle.unique():
        t = SN.wtc_table(career, cyc).set_index("team")
        g = w[w.cycle == cyc]
        for team in t.index:
            mine = g[(g.home == team) | (g.away == team)]
            won = (mine.winner == team).sum()
            drawn = (mine.result_type == "draw").sum()
            tied = (mine.result_type == "tie").sum()
            assert t.loc[team, "points"] == 12 * won + 6 * tied + 4 * drawn
            assert t.loc[team, "pct"] == pytest.approx(t.loc[team, "points"] / (12 * len(mine)) * 100)
        assert t.pct.is_monotonic_decreasing
    # England beat Pakistan 3-0 (36 points of 36) and Pakistan drew with Bangladesh
    t = SN.wtc_table(career, 2025).set_index("team")
    assert t.loc["England", "points"] == 36 and t.loc["England", "pct"] == 100
    assert t.loc["Pakistan", "points"] == 4


# --------------------------------------------------------------------------- 117 · reviews
def test_season_review(season):
    rv = SN.season_review(season, IPL, "2026", ["Mumbai Indians"])
    ids = ids_of(season, IPL)
    b = season.batting[season.batting.match_id.isin(ids) & season.batting.did_bat].groupby("player").runs.sum()
    assert rv["top_bat"].player.iloc[0] == b.idxmax() and rv["top_bat"].runs.iloc[0] == b.max()
    w = season.bowling[season.bowling.match_id.isin(ids)].groupby("player").wickets.sum()
    assert rv["top_bowl"].wickets.iloc[0] == w.max()
    assert len(rv["xi"]) == 11
    assert "Mumbai Indians" in rv["report_cards"]
    assert rv["matches"] == len(ids)
    assert rv["first_season"] and rv["records"].empty  # the first season can't break an earlier season's record


def test_season_review_records_broken(career):
    # ODIs: 2026 bilateral series, then the 2027 World Cup
    rv = SN.season_review(career, "ODIs", "2027")
    tl = SN.record_timeline(career, ids_of(career, "ODIs"))
    start = career.matches[(career.matches.section == "ODIs") & (career.matches.season == "2027")].date.min()
    for r in rv["records"].itertuples():
        g = tl[tl.record == r.record]
        assert r.old_value == g[g.date < start].value.iloc[-1]
        assert r.value == g[g.date >= start].value.iloc[-1]
    broken = {n for n, g in tl.groupby("record") if (g.date < start).any() and (g.date >= start).any()}
    assert set(rv["records"].record) == broken


def test_year_review(career):
    yr = SN.year_review(career, "2026")
    from ccstats import playerdeep as PDp
    for fmt, d in yr["formats"].items():
        ids = career.matches[(career.matches.section == d["section"]) & (career.matches.season == "2026")].match_id
        imp = PDp.match_impact(career, ids).groupby("player").impact.sum()
        assert d["player"].player.iloc[0] == imp.idxmax()
        assert d["player"].impact.iloc[0] == pytest.approx(imp.max())
    tot = pd.concat([PDp.match_impact(career, career.matches[(career.matches.section == d["section"])
                                                             & (career.matches.season == "2026")].match_id)
                     for d in yr["formats"].values()]).groupby("player").impact.sum()
    assert yr["cricketer"].player.iloc[0] == tot.idxmax()


# --------------------------------------------------------------------------- 116 / 122 · saved with the career
def test_notes_and_remembered_filters_are_saved(tmp_path, season):
    store = CareerStore(tmp_path / "home")
    s = CareerSettings(name="2026", notes={"a.txt": "rested Bumrah"}, remembered={"section": IPL, "season": "2026"})
    store.save(season, s)
    _, back = store.load_settings("2026")
    assert back.notes == {"a.txt": "rested Bumrah"}
    assert back.remembered == {"section": IPL, "season": "2026"}
    # old settings files (before notes existed) still load
    (store._dir("2026") / "settings.json").write_text('{"name": "2026", "folder": "", "updated": 0, "my_teams": []}')
    _, old = store.load_settings("2026")
    assert old.notes == {} and old.remembered == {}



# --------------------------------------------------------------------------- pages
from streamlit.testing.v1 import AppTest  # noqa: E402

ROOT = Path(__file__).parent.parent


def test_remembered_filters_follow_you_across_pages(season):
    at = AppTest.from_file(str(ROOT / "views" / "teams.py"), default_timeout=120)
    at.session_state["career_obj"] = season
    at.run()
    at = at.selectbox(key="tm_section").select("T20Is").run()
    remembered = at.session_state["remembered_cache"][1]
    assert remembered["section"] == "T20Is"
    # another page opens on it
    rc = AppTest.from_file(str(ROOT / "views" / "records.py"), default_timeout=120)
    rc.session_state["career_obj"] = season
    rc.session_state["remembered_cache"] = (season.name, dict(remembered))
    rc.run()
    assert rc.selectbox(key="rc_section").value == "T20Is"
    assert not rc.exception
    # a remembered choice that isn't on a page is ignored there
    rc2 = AppTest.from_file(str(ROOT / "views" / "records.py"), default_timeout=120)
    rc2.session_state["career_obj"] = season
    rc2.session_state["remembered_cache"] = (season.name, {"section": "No such section", "season": "1999"})
    rc2.run()
    assert not rc2.exception and rc2.selectbox(key="rc_section").value in set(season.matches.section)


def test_match_note_saves(season):
    mid = season.matches.match_id.iloc[0]
    at = AppTest.from_file(str(ROOT / "views" / "match.py"), default_timeout=120)
    at.session_state["career_obj"] = season
    at.query_params["match"] = mid
    at.run()
    at.text_area(key=f"note_{mid}").input("rested Bumrah, regretted it")
    at = at.button[0].click().run() if at.button else at
    src = season.matches.set_index("match_id").source[mid]
    assert at.session_state[f"notes::{season.name}"][src] == "rested Bumrah, regretted it"
    assert not at.exception
