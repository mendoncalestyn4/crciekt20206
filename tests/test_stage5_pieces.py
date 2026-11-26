"""Stage 5, the new pieces (your answers of 26 November, NEW_SITE_PLAN.md section 22), each counted again by hand."""

from __future__ import annotations

import pytest

from ccstats import breakers as BR
from ccstats import leaders as L
from ccstats.loader import Career
from ccstats.stats import Scope
from serverkit import FIXTURES


@pytest.fixture(scope="module")
def c():
    c = Career.build("t", [(f.name, f.read_bytes()) for f in FIXTURES])
    c.count_fielding = False
    return c


# --------------------------------------------------------------------------- partnership breakers
def test_each_broken_stand_counted_again_by_hand(c):
    """For every stand of 50+ said to be broken: the batter named was out at exactly that wicket (the next stand
    doesn't have him, or it was the last wicket), to the bowler named, and it wasn't a run out."""
    b = BR.broken(c, c.matches.match_id)
    assert len(b) > 10
    bat = c.batting
    fow = c.fow.set_index(["match_id", "innings_no", "wicket"]).score
    from ccstats import partnerships as P
    s = P.stands(c, c.matches.match_id).set_index(["match_id", "innings_no", "wicket"])
    for r in b.itertuples():
        st = s.loc[(r.match_id, r.innings_no, r.wicket)]
        assert r.runs == st.runs >= BR.MIN_STAND and not st.unbroken and r.batter in (st.batter1, st.batter2)
        assert fow[(r.match_id, r.innings_no, r.wicket)] == st.end
        row = bat[(bat.match_id == r.match_id) & (bat.innings_no == r.innings_no) & (bat.player == r.batter)].iloc[0]
        assert row.out and row.bowler == r.bowler and "run out" not in str(row.how_out)
        nxt = (r.match_id, r.innings_no, r.wicket + 1)
        if nxt in s.index and s.loc[nxt].known:
            assert r.batter not in (s.loc[nxt].batter1, s.loc[nxt].batter2)


def test_breakers_table_and_player_line_add_up(c):
    b = BR.broken(c, c.matches.match_id)
    t = BR.table(c, c.matches.match_id)
    assert t.broken.sum() == len(b)
    top = t.iloc[0]
    one = BR.of_player(c, c.matches.match_id, top.bowler)
    assert one["broken"] == len(b[b.bowler == top.bowler])     # (a bowler for two teams adds up across both)
    assert BR.of_player(c, c.matches.match_id, "Nobody At All") == {"broken": 0}


def test_stands_broken_on_stat_by_stat(c):
    sec = c.matches.section.value_counts().index[0]
    board = L.board(c, Scope(sections=[sec]), "Bowling", "stands_broken")
    assert board.stat.id == "stands_broken" and board.measures == ["all"]
    ids = c.matches[c.matches.section == sec].match_id
    counts = BR.broken(c, ids).bowler.value_counts()
    for r in board.table.itertuples():
        assert r.stands_broken == counts.get(r.player, 0)


# --------------------------------------------------------------------------- form alerts
def test_form_alerts_counted_again_by_hand(c):
    """Every hot streak and lean spell said for a team's players matches its innings (or matches) counted by hand,
    and nothing is said twice."""
    from ccstats import alerts as AL
    from ccstats.stats import KIND
    m = c.matches
    teams = sorted(set(m.home) | set(m.away))
    said = 0
    for team in teams:
        out = AL.form_alerts(c, m, [team])
        for key, kind, title, text in out:
            what, p, sec, first = key.split("|")
            k = KIND.get(m[m.section == sec].format.iloc[0], "one")
            order = list(m[m.section == sec].sort_values(["date", "match_id"]).match_id)
            if what in ("formbat", "slumpbat"):
                b = c.batting[c.batting.match_id.isin(order) & (c.batting.player == p) & c.batting.did_bat.astype(bool)]
                b = b.assign(o=b.match_id.map({x: i for i, x in enumerate(order)})).sort_values(["o", "innings_no"])
                mid, no = first.split(":")
                start = (order.index(mid), int(no))
                tail = [r.runs for r in b.itertuples() if (r.o, r.innings_no) >= start]
                n = AL.HOT_RUN if what == "formbat" else AL.SLUMP_RUN
                assert len(tail) >= n
                assert all(r >= AL.HOT_BAT[k] for r in tail) if what == "formbat" else all(r < AL.SLUMP_BAT[k] for r in tail)
            said += 1
        _, seen = AL.check(c, [], [team], [], {})
        first_run, seen2 = AL.check(c, list(m.source), [team], [], dict(seen, said=[]))
        again, _ = AL.check(c, list(m.source), [team], [], seen2)
        assert not [a for a in again if a["title"] in ("Hot streak", "A lean spell")]


def test_form_alerts_on_made_streaks(c):
    """A player given 3 fifties in a row (and another 5 low scores in a row) at the end of a competition: exactly that
    streak is said, with its scores; one short of the run, nothing is."""
    import copy
    from ccstats import alerts as AL
    from ccstats.stats import KIND
    m = c.matches
    bat = c.batting[c.batting.did_bat.astype(bool)].merge(m[["match_id", "section", "date"]], on="match_id")
    counts = bat.groupby(["section", "player", "team"]).size()
    (sec, p, team), n = next((k, v) for k, v in counts.items() if v >= 5)
    k = KIND.get(m[m.section == sec].format.iloc[0], "one")
    rows = bat[(bat.section == sec) & (bat.player == p)].sort_values(["date", "match_id", "innings_no"])
    cc = copy.copy(c)
    cc.batting = c.batting.copy()
    idx = c.batting.index[c.batting.match_id.isin(rows.match_id) & (c.batting.player == p) & c.batting.did_bat.astype(bool)]
    order = rows.set_index(["match_id", "innings_no"]).index
    pos = {key: i for i, key in enumerate(order)}
    ranked = sorted(idx, key=lambda i: pos[(c.batting.match_id[i], c.batting.innings_no[i])])
    for i in ranked[-3:]:
        cc.batting.loc[i, "runs"] = AL.HOT_BAT[k] + 5
    cc.batting.loc[ranked[-4], "runs"] = 0
    out = AL.form_alerts(cc, m[m.section == sec], [team])
    hot = [a for a in out if a[0].startswith("formbat|" + p)]
    assert len(hot) == 1 and f"3 scores of {AL.HOT_BAT[k]}+" in hot[0][3]
    cc.batting.loc[ranked[-3], "runs"] = 0          # now only 2 in a row: nothing
    assert not [a for a in AL.form_alerts(cc, m[m.section == sec], [team]) if a[0].startswith("formbat|" + p)]
    for i in ranked[-5:]:
        cc.batting.loc[i, "runs"] = 1
    low = [a for a in AL.form_alerts(cc, m[m.section == sec], [team]) if a[0].startswith("slumpbat|" + p)]
    assert len(low) == 1 and "5 innings in a row" in low[0][3]


def test_form_alerts_only_for_your_players(c):
    from ccstats import alerts as AL
    assert AL.form_alerts(c, c.matches, ["Nobody FC"]) == []


# --------------------------------------------------------------------------- records within reach
def test_records_within_reach_counted_again_by_hand(c):
    """Every record named is the real record (the team's own or the competition's), held by someone else, the player
    still plays for the team, and he needs no more than one good match to pass it."""
    from ccstats import reach as R
    from ccstats.stats import KIND
    m = c.matches
    seen = 0
    for sec in m.section.unique():
        here = m[m.section == sec]
        teams = sorted(set(here.home) | set(here.away))
        w = R.within(c, sec, teams)
        kind = KIND.get(here.format.iloc[0], "one")
        bat = c.batting[c.batting.match_id.isin(here.match_id) & c.batting.did_bat.astype(bool)]
        bowl = c.bowling[c.bowling.match_id.isin(here.match_id)]
        for r in w.itertuples():
            src = {"runs": bat.groupby(["player", "team"]).runs.sum(), "wickets": bowl.groupby(["player", "team"]).wickets.sum(),
                   "hundreds": bat[bat.runs >= 100].groupby(["player", "team"]).size(),
                   "five-wicket hauls": bowl[bowl.wickets >= 5].groupby(["player", "team"]).size()}[r.unit]
            pool = src.xs(r.whose, level=1) if r.whose else src.groupby(level=0).sum()
            assert pool.max() == r.record_value and pool[r.holder] == r.record_value and r.holder != r.player
            assert pool[r.player] == r.now and r.needed == r.record_value - r.now + 1
            limit = {"runs": R.RUNS[kind], "wickets": R.WICKETS[kind]}.get(r.unit, 1)
            assert 0 < r.needed <= limit
            tm = here[(here.home == r.team) | (here.away == r.team)]
            last = tm[tm.season == tm.season.max()].match_id
            assert r.player in set(c.batting[c.batting.match_id.isin(last) & (c.batting.team == r.team)].player) | \
                set(c.bowling[c.bowling.match_id.isin(last) & (c.bowling.team == r.team)].player)
            seen += 1
    assert seen > 10


def test_preview_in_form_players(tmp_path):
    """The opponent preview's in-form players: at most 3 a side, each playing above their own usual over their last 5,
    the biggest lift first, only current players."""
    import json
    from server.app import create_app
    from serverkit import Live, make_pc
    store, _, _ = make_pc(tmp_path, team="England", files=FIXTURES)
    s = Live(create_app(store, web=tmp_path / "nothing", watch_every=0))
    try:
        d = s.json("/api/preview?section=Internationals&format=ODI")
        form = (d.get("head") or {}).get("form") or []
        assert form and form[-1]["team"] == d["opp"]
        for side in form:
            lifts = [float(r["lift"].rstrip("%")) for r in side["rows"]]
            assert len(lifts) <= 3 and all(x > 0 for x in lifts) and lifts == sorted(lifts, reverse=True)
    finally:
        s.stop()


# --------------------------------------------------------------------------- who's fading
def test_whos_fading_picks_only_clear_drops_of_your_players(c):
    """Only your teams' players, only a clear drop (by format), the biggest drop first; the measure is the breakouts'
    own, so the numbers shown are the ones Breakout players works out."""
    import pandas as pd
    from server import insightspage as IP
    from ccstats.stats import KIND
    sec = "Tests" if "Tests" in set(c.matches.section) else c.matches.section.iloc[0]
    kind = KIND.get(c.matches[c.matches.section == sec].format.iloc[0], "one")
    cut = IP.FADE["bat"][kind]
    bat = pd.DataFrame([dict(player="A Mine", teams="England", now=10.0, before=10.0 + cut + 2, now_innings=6, before_innings=8, jump=-(cut + 2)),
                        dict(player="B Mine", teams="England", now=10.0, before=10.0 + cut - 1, now_innings=6, before_innings=8, jump=-(cut - 1)),
                        dict(player="C Theirs", teams="India", now=1.0, before=30.0, now_innings=6, before_innings=8, jump=-29.0),
                        dict(player="D Mine", teams="Lions / England", now=0.0, before=40.0, now_innings=6, before_innings=8, jump=-40.0)])
    out = IP._fading(c, sec, "2027", bat, pd.DataFrame(), ["England"], 5)
    assert [r["player"] for r in out["rows"]] == ["D Mine", "A Mine"]            # biggest drop first; B not clear; C not yours
    assert out["rows"][0]["team"] == "England" and out["rows"][1]["drop"] == f"{-(cut + 2):+.1f}"
    none = IP._fading(c, sec, "2027", bat, pd.DataFrame(), ["Nobody FC"], 5)
    assert "none" in none and "rows" not in none


# --------------------------------------------------------------------------- selection review
@pytest.fixture(scope="module")
def demo():
    """The made-up IPL (two full seasons): enough matches per team for runs of five."""
    from ccstats.demo_league import generate
    c = Career.build("demo", [(n, t.encode()) for n, t in generate((2026, 2027))])
    c.count_fielding = False
    return c


def _sel_case(c):
    """A team and competition with 7+ matches, and its XIs in order."""
    from ccstats import selection as SEL
    m = c.matches
    for sec in m.section.unique():
        here = m[m.section == sec]
        for team in sorted(set(here.home) | set(here.away)):
            xis = SEL._xis(c, here.match_id, team)
            if len(xis) >= 7:
                return sec, team, xis
    raise AssertionError("no team with 7 matches in a competition")


def test_selection_review_dropped_and_kept_on_made_cases(demo):
    c = demo
    import copy
    from ccstats import selection as SEL
    from ccstats.stats import KIND
    sec, team, xis = _sel_case(c)
    kind = KIND.get(c.matches[c.matches.section == sec].format.iloc[0], "one")
    cc = copy.copy(c)
    cc.batting = c.batting.copy()
    # dropped: a player given a good score in one match and left out of the next (the made-up league keeps one XI,
    # so his line in the next match is taken off the card here)
    i, gone = 2, sorted(xis[2][2] & xis[3][2])[0]
    cc.batting = cc.batting.drop(cc.batting.index[(cc.batting.match_id == xis[3][0]) & (cc.batting.player == gone)])
    rows = cc.batting.index[(cc.batting.match_id == xis[i][0]) & (cc.batting.player == gone) & (cc.batting.team == team)]
    cc.batting.loc[rows[0], ["runs", "did_bat"]] = [SEL.GOOD_RUNS[kind] + 1, True]
    r = SEL.review(cc, team, sec)
    hit = [x for x in r["dropped"] if x["player"] == gone and x["match_id"] == xis[i][0]]
    assert hit and hit[0]["next_id"] == xis[i + 1][0] and f"{SEL.GOOD_RUNS[kind] + 1} runs" in hit[0]["did"]
    cc.batting = c.batting.copy()                                            # back to the real cards for the next case
    # kept: someone in 6 XIs in a row, given 5 low scores, still in the 6th
    for j in range(len(xis) - 5):
        common = set.intersection(*[x[2] for x in xis[j:j + 6]])
        if common:
            p = sorted(common)[0]
            break
    for k in range(j, j + 5):
        idx = cc.batting.index[(cc.batting.match_id == xis[k][0]) & (cc.batting.player == p) & (cc.batting.team == team)]
        cc.batting.loc[idx, ["runs", "did_bat"]] = [1, True]
    r = SEL.review(cc, team, sec)
    kept = [x for x in r["kept"] if x["player"] == p and "innings" in x["did"]]
    assert any("(1, 1, 1, 1, 1)" in x["did"] and x["next_id"] == xis[j + 5][0] for x in kept)


def test_selection_changes_counted_by_hand(demo):
    c = demo
    from ccstats import selection as SEL
    sec, team, xis = _sel_case(c)
    ids = c.matches[c.matches.section == sec].match_id
    by_hand = sum(len(b[2] - a[2]) for a, b in zip(xis, xis[1:])) / (len(xis) - 1)
    assert abs(SEL.changes(c, ids, team) - by_hand) < 1e-9


# --------------------------------------------------------------------------- Stat by stat: against, and by result
def test_stat_by_stat_against_opponents_and_by_result_counted_by_hand(c):
    from ccstats.stats import player_tables
    m = c.matches
    sec = "ODIs" if "ODIs" in set(m.section) else m.section.iloc[0]
    ids = m[m.section == sec].match_id
    here = m[m.match_id.isin(ids)].set_index("match_id")
    bat = c.batting[c.batting.match_id.isin(ids) & c.batting.did_bat.astype(bool)]
    bowl = c.bowling[c.bowling.match_id.isin(ids)]
    opps = sorted(set(bat.opposition))[:2]
    b, w, _, base_all = player_tables(c, Scope(sections=[sec], opponents=opps))
    _, _, _, base = player_tables(c, Scope(sections=[sec]))
    assert base_all.runs_per_innings == base.runs_per_innings          # the average player stays the competition's
    by_hand = bat[bat.opposition.isin(opps)].groupby("player").runs.sum()
    assert dict(zip(b[b.innings > 0].player, b[b.innings > 0].runs)) == {k: int(v) for k, v in by_hand.items()}
    by_hand_w = bowl[bowl.opposition.isin(opps)].groupby("player").wickets.sum()
    got_w = dict(zip(w.player, w.wickets))
    assert all(got_w[k] == int(v) for k, v in by_hand_w.items())
    for result, keep in (("won", lambda r: here.winner[r.match_id] == r.team),
                         ("lost", lambda r: here.loser[r.match_id] == r.team),
                         ("chasing", lambda r: bool(here.batted_first[r.match_id]) and here.batted_first[r.match_id] != r.team)):
        b, _, _, _ = player_tables(c, Scope(sections=[sec], result=result))
        want = bat[[keep(r) for r in bat.itertuples()]].groupby("player").runs.sum()
        assert dict(zip(b[b.innings > 0].player, b[b.innings > 0].runs)) == {k: int(v) for k, v in want.items()}, result


# --------------------------------------------------------------------------- career arc
def test_career_arc_curve_worked_by_hand():
    """Three new players' changes from season 1 to 2 (+2, +4, +6 with equal innings) average +4; only two make it to a
    3rd season, too few for a step, so the curve stops at the 2nd. Players there from the start are kept apart."""
    import pandas as pd
    from ccstats import arc as ARC
    rows = []
    for p, v1, v2 in (("A", 0, 2), ("B", 1, 5), ("C", -3, 3)):
        rows += [(p, "bat", "2027", 1, 10, v1, False, "X"), (p, "bat", "2028", 2, 10, v2, False, "X")]
    rows += [("A", "bat", "2029", 3, 10, 9, False, "X"), ("B", "bat", "2029", 3, 10, 9, False, "X")]
    rows += [("D", "bat", "2026", 1, 10, 50, True, "X"), ("D", "bat", "2027", 2, 10, -50, True, "X")]
    rows += [("E", "bat", "2027", 1, 2, 0, False, "X"), ("E", "bat", "2028", 2, 2, 100, False, "X")]   # too few innings
    per = pd.DataFrame(rows, columns=["player", "job", "season", "n", "innings", "value", "from_start", "teams"])
    c = ARC.curve(per, "bat", False)
    assert list(c.n) == [1, 2] and c.change.tolist() == [0.0, 4.0] and c.players.tolist()[1] == 3
    # unequal innings weigh the change by both seasons' innings
    per2 = per.copy()
    per2.loc[(per2.player == "C"), "innings"] = 30
    w = 2 / (1 / 30 + 1 / 30)
    want = (2 * 10 + 4 * 10 + 6 * w) / (10 + 10 + w)
    assert abs(ARC.curve(per2, "bat", False).change.iloc[1] - want) < 1e-9
    assert ARC.curve(per, "bat", True).players.iloc[0] == 1 and len(ARC.curve(per, "bat", True)) == 1   # one player: no step


def test_career_arc_each_player_recounted_from_season_tables(demo):
    """Every verdict's own change equals the player's measure in their latest and first counted seasons, worked again
    from each season's own table; the usual change is the curve's over the same seasons; the verdict follows the
    margin."""
    from ccstats import arc as ARC
    from ccstats.stats import KIND, player_tables
    c = demo
    sec = c.matches.section.iloc[0]
    kind = KIND.get(c.matches[c.matches.section == sec].format.iloc[0], "one")
    per = ARC.seasons(c, sec)
    v = ARC.verdicts(c, sec, per)
    assert len(v)
    seasons = sorted(c.matches[c.matches.section == sec].season.unique())
    tabs = {s: player_tables(c, Scope(sections=[sec], seasons=[s])) for s in seasons}
    for r in v.sample(min(25, len(v)), random_state=1).itertuples():
        t_i, col = (0, "runs_above_average") if r.job == "bat" else (1, "runs_saved")
        vals = []
        for s in seasons:
            t = tabs[s][t_i]
            t = t[(t.player == r.player) & (t.innings >= ARC.LEAST)]
            if len(t):
                vals.append(float(t[col].iloc[0] / t.innings.iloc[0]))
        assert len(vals) == r.seasons >= 2
        assert abs(r.own - (vals[-1] - vals[0])) < 1e-9 or r.last_n < len(seasons)
        cv = ARC.curve(per, r.job, r.from_start).set_index("n").change
        assert abs(r.usual - (cv[r.last_n] - cv[r.first_n])) < 1e-9
        cut = ARC.MARGIN[r.job][kind]
        assert r.verdict == ("ahead" if r.diff >= cut else "behind" if r.diff <= -cut else "on")


def test_career_arc_on_the_pages(demo):
    """The Insights tab draws both curves and lists the players; each listed player's Player page says the same."""
    from server import insightspage as IP
    from server import playerpage as PP
    c = demo
    sec = c.matches.section.iloc[0]
    team = sorted(set(c.matches.home))[0]
    out = IP.insights_page(c, dict(tab="Career arc", section=sec), [team])
    assert [ch["id"] for ch in out["arc_charts"]] == ["bat", "bowl"]
    assert all(ch.get("lines") and ch.get("is_") and ch.get("for_") for ch in out["arc_charts"])
    rows = out["arc_mine"]["rows"]
    assert rows and all(r["team"] == team for r in rows)
    for r in rows[:4]:
        pg = PP.page(c, r["player"], sec)
        assert r["line"] in [x["text"] for x in pg["arc"]["lines"]]
    one = IP.insights_page(c, dict(tab="Career arc", section=sec), [])
    assert one["arc_mine"].get("none") and one["arc_top"]["rows"]


# --------------------------------------------------------------------------- eras
def test_era_rules_on_made_seasons():
    """Runs of 2+ seasons near the top are eras, a single good season isn't, and the names read as years."""
    import pandas as pd
    from ccstats import eras as ER
    assert ER.top_of(10) == 3 and ER.top_of(12) == 3 and ER.top_of(20) == 4 and ER.top_of(38) == 7
    assert ER.name("2029", "2031") == "the 2029–31 era" and ER.name("1999", "2001") == "the 1999–2001 era"
    assert ER.name("2026/27", "2027/28") == "the 2026/27–2027/28 era"

    class Fake:      # a career with no matches: the eras come from the ranks alone, results all zero
        matches = pd.DataFrame(columns=["section", "season", "home", "away", "result_type", "winner", "loser", "match_id"])
        batting = pd.DataFrame(columns=["match_id", "team", "player", "runs"])
        bowling = pd.DataFrame(columns=["match_id", "team", "player", "wickets"])
    tops = [True, True, False, True, False, True, True, True]
    ranks = pd.DataFrame(dict(season=[str(2020 + i) for i in range(8)], team="X", rating=1500.0,
                              rank=[1 if t else 6 for t in tops], teams=10, top=tops))
    found = ER.eras(Fake, "S", "X", ranks)
    assert [(e["first"], e["last"]) for e in found] == [("2020", "2021"), ("2025", "2027")]


def test_eras_ranked_from_the_ratings_and_recounted(demo):
    """Each season's rank is the team's rating after its last match of that season, ranked among the teams that played;
    each era's results and key players are recounted from the scorecards."""
    from ccstats import eras as ER
    from ccstats.rankings import team_elo
    c = demo
    sec = c.matches.section.iloc[0]
    ranks = ER.season_ranks(c, sec)
    _, hist = team_elo(c, sec)
    m = c.matches.set_index("match_id")
    for s, g in ranks.groupby("season"):
        h = hist[hist.match_id.map(m.season) == s]
        last = {t: x.sort_values(["date", "match_id"]).after.iloc[-1] for t, x in h.groupby("team")}
        assert dict(zip(g.team, g.rating.round(6))) == {t: round(v, 6) for t, v in last.items()}
        order = sorted(last, key=lambda t: -last[t])
        assert g.set_index("team").loc[order[0], "rank"] == 1
    any_era = False
    for team in sorted(set(ranks.team)):
        for e in ER.eras(c, sec, team, ranks):
            any_era = True
            g = c.matches[(c.matches.section == sec) & c.matches.season.astype(str).isin(e["seasons"])
                          & ((c.matches.home == team) | (c.matches.away == team))]
            assert e["matches"] == len(g) and e["won"] == int((g.winner == team).sum()) and e["lost"] == int((g.loser == team).sum())
            bat = c.batting[c.batting.match_id.isin(g.match_id) & (c.batting.team == team)]
            assert e["runs"][0]["value"] == int(bat.groupby("player").runs.sum().max())
    assert any_era


def test_then_and_now_recounted(demo):
    from ccstats import thenandnow as TN
    c = demo
    sec = c.matches.section.iloc[0]
    team = sorted(set(c.matches.home))[0]
    assert [k for k, _, _ in TN.choices(c, sec, team)] == [1]          # two seasons: only 1 season ago
    x = TN.compare(c, sec, team, 1)
    for part, s in (("then", "2026"), ("now", "2027")):
        g = c.matches[(c.matches.section == sec) & (c.matches.season.astype(str) == s) & ((c.matches.home == team) | (c.matches.away == team))]
        assert x[part]["matches"] == len(g) and x[part]["won"] == int((g.winner == team).sum())
        inn = c.innings[c.innings.match_id.isin(g.match_id) & (c.innings.team == team)]
        assert abs(x[part]["bat_avg"] - inn.runs.sum() / inn.wickets.sum()) < 1e-9
    who = lambda s: set(c.batting[c.batting.match_id.isin(c.matches[(c.matches.section == sec) & (c.matches.season.astype(str) == s)].match_id)  # noqa: E731
                                  & (c.batting.team == team)].player)
    assert {p for p, _ in x["came_in"]} == who("2027") - who("2026")
    assert {p for p, _ in x["went_out"]} == who("2026") - who("2027")
    assert TN.compare(c, sec, team, 3) is None


def test_eras_and_then_and_now_on_the_pages(demo):
    from ccstats import eras as ER
    from server import myteam as MYT
    from server import teampage as TPG
    c = demo
    sec = c.matches.section.iloc[0]
    ranks = ER.season_ranks(c, sec)
    with_era = [t for t in sorted(set(ranks.team)) if ER.eras(c, sec, t, ranks)]
    without = [t for t in sorted(set(ranks.team)) if t not in with_era]
    for team in with_era[:1] + without[:1]:
        for tab, key in (("Eras", "eras"), ("Then and now", "then_now")):
            b = TPG.page(c, sec, "", team, "all", tab)["body"]
            assert b["missing"] == {} and b[key]["blocks"]
        e = TPG.page(c, sec, "", team, "all", "Eras")["body"]["eras"]["blocks"][0]
        assert bool(e["eras"]) == (team in with_era) and bool(e["none"]) == (team not in with_era)
    # the My team line: only while the era lasts
    for team in with_era + without[:2]:
        found = ER.eras(c, sec, team, ranks)
        lasts = bool(found) and found[-1]["last"] == str(ranks[ranks.team == team].season.max())
        out = MYT.section_block(c, team, sec, {}, [])
        assert bool(out.get("era")) == lasts, team


# --------------------------------------------------------------------------- on this day
def test_on_this_day_exact_dates_only(c):
    """A year after any match, that match is listed for both its teams with its hundreds and hauls; the day before and
    the day after list nothing from it; and today's date is the career's latest match."""
    import pandas as pd
    from ccstats import onthisday as OD
    assert OD.today(c) == c.matches.date.max()
    m = c.matches.dropna(subset=["date"])
    for r in m.sample(8, random_state=3).itertuples():
        later = r.date + pd.DateOffset(years=2)
        for team in (r.home, r.away):
            got = OD.on_this_day(c, team, later)
            ids = [x["id"] for x in got]
            assert r.match_id in ids
            want = m[((m.home == team) | (m.away == team)) & (m.date.dt.month == later.month) & (m.date.dt.day == later.day)
                     & (m.date.dt.year < later.year)]
            assert set(ids) == set(want.match_id)
            x = got[ids.index(r.match_id)]
            bat = c.batting[(c.batting.match_id == r.match_id) & (c.batting.team == team)]
            assert sum(1 for t in x["moments"] if "/" not in t) == int((bat.runs >= 100).sum())
            assert x["years"] == 2 and x["outcome"] in ("won", "lost", "drew", "tied", "no result")
            for shift in (-1, 1):
                other = OD.on_this_day(c, team, later + pd.Timedelta(days=shift))
                assert r.match_id not in [y["id"] for y in other]
    # a match on that very date this year isn't "an earlier year"
    r = m.iloc[0]
    assert r.match_id not in [x["id"] for x in OD.on_this_day(c, r.home, r.date)]
