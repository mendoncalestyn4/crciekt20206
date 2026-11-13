"""Players at the moments that matter (ccstats/moments.py): big-match players, record by country, bounce-back and
danger men, each counted again from the scorecards by hand for every player of every competition in the test
scorecards."""

from __future__ import annotations

import pytest

from ccstats import moments as MO
from ccstats import teamplay as TP
from ccstats.loader import Career
from ccstats.mvp import season_mvp
from serverkit import FIXTURES


@pytest.fixture(scope="module")
def career():
    return Career.build("Test career", [(f.name, f.read_bytes()) for f in FIXTURES])


def _runs_outs(b):
    return int(b.runs.sum()), int(b.out.sum())


def test_big_games_are_the_knockouts_and_the_deciders(career):
    m = career.matches
    for sec in m.section.unique():
        ids = set(m[m.section == sec].match_id)
        s = TP.series_games(career, ids)
        want = set(m[m.match_id.isin(ids) & m.knockout].match_id) | (set(s[s.decider].match_id) if len(s) else set())
        assert MO.big_match_ids(career, ids) == want


def test_big_match_players_counted_by_hand(career):
    m = career.matches
    seen = 0
    for sec in m.section.unique():
        ids = set(m[m.section == sec].match_id)
        big = MO.big_match_ids(career, ids)
        bm = MO.big_match(career, ids)
        xi = career.batting[career.batting.match_id.isin(ids)]
        for (p, t), g in xi.groupby(["player", "team"]):
            n_big = len(set(g.match_id) & big)
            row = bm[(bm.player == p) & (bm.team == t)]
            assert len(row) == (n_big >= MO.BIG_MIN), (p, t, n_big)
            if not len(row):
                continue
            r = row.iloc[0]
            bat = g[g.did_bat]
            assert (r.big_bat["runs"], r.big_bat["outs"]) == _runs_outs(bat[bat.match_id.isin(big)])
            assert (r.ord_bat["runs"], r.ord_bat["outs"]) == _runs_outs(bat[~bat.match_id.isin(big)])
            w = career.bowling[career.bowling.match_id.isin(set(g.match_id)) & (career.bowling.player == p) & (career.bowling.team == t)]
            assert r.big_bowl["wickets"] == int(w[w.match_id.isin(big)].wickets.sum())
            assert r.ord_bowl["wickets"] == int(w[~w.match_id.isin(big)].wickets.sum())
            assert r.big + r.ordinary == g.match_id.nunique()
            seen += 1
    assert seen > 0


def test_record_by_country_counted_by_hand(career):
    m = career.matches.set_index("match_id")
    for sec in career.matches.section.unique():
        ids = set(career.matches[career.matches.section == sec].match_id)
        bh = MO.by_host(career, ids)
        xi = career.batting[career.batting.match_id.isin(ids)]
        for (p, t), g in xi.groupby(["player", "team"]):
            mine = bh[(bh.player == p) & (bh.team == t)]
            assert mine.matches.sum() == g.match_id.nunique()
            for r in mine.itertuples():
                here = [x for x in set(g.match_id) if (("" if m.neutral[x] else m.home[x]) == r.host)]
                assert r.matches == len(here)
                b = g[g.match_id.isin(here) & g.did_bat]
                assert (r.bat["runs"], r.bat["outs"]) == _runs_outs(b)
                w = career.bowling[career.bowling.match_id.isin(here) & (career.bowling.player == p) & (career.bowling.team == t)]
                assert r.bowl["wickets"] == int(w.wickets.sum())


def test_bounce_back_counted_by_hand(career):
    m = career.matches.set_index("match_id")
    shown = 0
    for p in sorted(set(career.batting.player))[:400]:
        for sec in career.matches.section.unique():
            ids = set(career.matches[career.matches.section == sec].match_id)
            bb = MO.bounce_back(career, ids, p)
            b = career.batting[career.batting.match_id.isin(ids) & (career.batting.player == p) & career.batting.did_bat]
            rows = sorted(b.itertuples(), key=lambda r: (m.date[r.match_id], r.match_id, r.innings_no))
            after = []
            for i, r in enumerate(rows):
                if r.runs < MO.LOW and r.out:
                    nxt = next((x for x in rows[i + 1:] if x.match_id != r.match_id), None)
                    if nxt is not None and (not after or after[-1] is not nxt):
                        after.append(nxt)
            assert bb["bat"]["poor"] == sum(r.runs < MO.LOW and r.out for r in rows)
            assert [g["id"] for g in bb["bat"]["games"]] == [x.match_id for x in after]
            assert bb["bat"]["after"]["runs"] == sum(x.runs for x in after)
            assert bb["bat"]["shown"] == (len(after) >= MO.BOUNCE_MIN)
            shown += bb["bat"]["shown"]
            w = career.bowling[career.bowling.match_id.isin(ids) & (career.bowling.player == p) & (career.bowling.balls > 0)]
            ws = sorted(w.itertuples(), key=lambda r: (m.date[r.match_id], r.match_id, r.innings_no))
            assert bb["bowl"]["poor"] == sum(x.wickets == 0 and x.runs >= MO.DEAR for x in ws)
    assert shown > 0


def test_danger_men_are_the_top_three_by_impact_points(career):
    m = career.matches
    done = 0
    for sec in m.section.unique():
        for season in m[m.section == sec].season.unique():
            mv = season_mvp(career, sec, season)
            for team in set(mv.team):
                d = MO.danger_men(career, sec, season, team)
                top = mv[mv.team == team].head(3)
                assert [x["player"] for x in d] == list(top.player)
                for x, r in zip(d, top.itertuples()):
                    assert x["points"] == pytest.approx(r.points) and x["matches"] == r.matches
                    assert len(x["innings"]) <= 5 and len(x["spells"]) <= 5
                    # the last five in the section, to the end of that season, newest last
                    end = m[(m.section == sec) & (m.season == season)].date.max()
                    ids = set(m[(m.section == sec) & (m.date <= end)].match_id)
                    b = career.batting[career.batting.match_id.isin(ids) & (career.batting.player == x["player"])
                                       & (career.batting.team == team) & career.batting.did_bat]
                    b = b.assign(d=b.match_id.map(m.set_index("match_id").date)).sort_values(["d", "match_id", "innings_no"]).tail(5)
                    assert [i["runs"] for i in x["innings"]] == list(b.runs)
                done += 1
    assert done > 20


def test_rivalry_runs_by_the_agreed_rules():
    """Wins in a row: a draw or a tie ends a run, a no-result is skipped; the longest is the first on a tie."""
    import pandas as pd
    from ccstats import extras as E

    def g(seq):
        rows = []
        for i, x in enumerate(seq):
            w = {"A": "A", "B": "B", "D": "", "T": "", "N": ""}[x]
            rt = {"D": "draw", "T": "tie", "N": "no result"}.get(x, "win")
            rows.append(dict(winner=w, result_type=rt, date=pd.Timestamp("2026-01-01") + pd.Timedelta(days=i)))
        return pd.DataFrame(rows)
    r = E.rivalry_runs(g("AABBBNBDA"))
    assert (r["current_team"], r["current_n"]) == ("A", 1)
    assert (r["longest_team"], r["longest_n"]) == ("B", 4)        # the no-result in the middle doesn't break it
    assert r["longest_from"] == pd.Timestamp("2026-01-03") and r["longest_to"] == pd.Timestamp("2026-01-07")
    r = E.rivalry_runs(g("AAT"))
    assert (r["current_team"], r["current_n"], r["longest_team"], r["longest_n"]) == ("", 0, "A", 2)
    r = E.rivalry_runs(g("ABBAAN"))
    assert (r["current_team"], r["current_n"], r["longest_team"], r["longest_n"]) == ("A", 2, "B", 2)   # the first of two 2s
    r = E.rivalry_runs(g("NN"))
    assert (r["current_n"], r["longest_n"]) == (0, 0)


def test_every_rivalry_run_counted_by_hand(career):
    from ccstats import extras as E
    from ccstats.records import by_played
    m = career.matches
    for sec in m.section.unique():
        ids = set(m[m.section == sec].match_id)
        rv = E.rivalries(career, ids)
        for r in rv.itertuples():
            g = by_played(career, m[m.match_id.isin(ids) & (((m.home == r.team_a) & (m.away == r.team_b)) | ((m.home == r.team_b) & (m.away == r.team_a)))])
            seq = [x.winner for x in g.itertuples() if x.result_type != "no result"]
            cur = 0
            for w in reversed(seq):
                if w and w == seq[-1]:
                    cur += 1
                else:
                    break
            assert r.current_n == cur and (r.current_team == (seq[-1] if cur else ""))
            best = run = 0
            prev = None
            for w in seq:
                run = run + 1 if (w and w == prev) else (1 if w else 0)
                prev = w
                best = max(best, run)
            assert r.longest_n == best
