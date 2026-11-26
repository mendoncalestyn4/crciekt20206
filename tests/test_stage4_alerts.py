"""Stage 4, the new alerts, the daily summary and the weekly recheck (your picks of 26 November). Each alert counted
again by hand from the scorecards, said once only, only for your teams; nothing old pops up the first time; the daily
summary shows once a day what happened since; the recheck finds a kept copy that differs from a fresh read and puts it
right."""

from __future__ import annotations

import json
import shutil
import time

import pytest

from ccstats import alerts as AL
from ccstats import fixtures as FX
from ccstats.loader import Career
from ccstats.local import recheck
from server.app import create_app
from serverkit import FIXTURES, Live, by_date, make_pc


def build(files):
    c = Career.build("t", [(f.name, f.read_bytes()) for f in files])
    c.count_fielding = False
    return c


def test_first_run_says_nothing_then_each_alert_once():
    files = sorted(FIXTURES, key=by_date)
    c = build(files)
    team = "England"
    out, seen = AL.check(c, list(c.matches.source), [team], [], {})
    assert out == [] and seen["started"]                       # nothing old pops up
    # a streak counted by hand: the run England are on in each format, alerted only at 3, 5 or 10
    out2, seen2 = AL.check(c, list(c.matches.source), [team], [], dict(seen, said=[]))
    m = c.matches
    for fmt in m[(m.home == team) | (m.away == team)].format.unique():
        tm = m[((m.home == team) | (m.away == team)) & (m.format == fmt)].sort_values(["date", "match_id"])
        outs = [FX._outcome(r, team) for r in tm.itertuples() if FX._outcome(r, team) != "NR"]
        run = 0
        for o in reversed(outs):
            if o != outs[-1]:
                break
            run += 1
        expect = (outs[-1] == "W" and run in AL.STREAK_WINS) or (outs[-1] == "L" and run in AL.STREAK_LOSSES)
        got = any(a["kind"] == "streak" and f"{fmt}s in a row" in a["text"] for a in out2)
        assert got == expect, (fmt, outs, run)
    again, _ = AL.check(c, list(c.matches.source), [team], [], seen2)
    assert again == []                                          # said once only


def test_only_your_teams():
    c = build(FIXTURES)
    _, seen = AL.check(c, [], ["Nobody FC"], [], {})
    out, _ = AL.check(c, list(c.matches.source), ["Nobody FC"], [], dict(seen, said=[]))
    assert out == []


def test_goal_reached_and_series_won_counted_again():
    c = build(FIXTURES)
    team = "England"
    m = c.matches
    tm = m[(m.home == team) | (m.away == team)]
    wins = sum(FX._outcome(r, team) == "W" for r in tm[tm.format == "Test"].itertuples())
    year = str(tm[tm.format == "Test"].date.dt.year.iloc[0])
    g = dict(id="g1", kind="wins", team=team, format="Test", target=1, year=year)
    _, seen = AL.check(c, [], [team], [], {})
    out, _ = AL.check(c, list(m.source), [team], [g], dict(seen, said=[]))
    reached = [a for a in out if a["kind"] == "goal"]
    assert bool(reached) == (wins >= 1)
    # series won: a bilateral series England won by more than half its games
    for sid, s in tm[tm.series_id.fillna("") != ""].groupby("series_id"):
        n = int(s.series_length.iloc[0] or 0)
        won = sum(FX._outcome(r, team) == "W" for r in s.itertuples())
        if n >= 2 and won > n // 2:
            assert any(a["kind"] == "series" and "series" in a["text"] for a in out)
            break


def test_alerts_arrive_with_new_matches_and_are_logged(tmp_path):
    files = sorted(FIXTURES, key=by_date)
    store, folder, game = make_pc(tmp_path, files=files[:-6], team="England")
    s = Live(create_app(store, web=tmp_path / "nothing", watch_every=0.2))
    try:
        for _ in range(100):
            if store.load_settings("My career")[1].alerts_seen.get("started"):
                break
            time.sleep(0.1)
        assert store.load_settings("My career")[1].alerts_seen.get("started")
        for f in files[-6:]:
            shutil.copy(f, folder / f.name)
        # the site reads scorecards as they appear, so the six can come in more than one batch (as from the game)
        def counted(log):
            return sum(int(x["text"].split(" ")[0]) for x in log if x["kind"] == "matches")
        for _ in range(300):
            log = store.load_settings("My career")[1].alert_log
            if counted(log) >= 6:
                break
            time.sleep(0.1)
        log = store.load_settings("My career")[1].alert_log
        assert counted(log) == 6, log
        assert all(x["text"].endswith(("new match", "new matches")) for x in log if x["kind"] == "matches")
    finally:
        s.stop()


def test_daily_summary_once_a_day(tmp_path):
    store, _, _ = make_pc(tmp_path, n=5)
    s = Live(create_app(store, web=tmp_path / "nothing", watch_every=0))
    try:
        assert s.json("/api/daily")["show"] is False            # the very first day: counting starts
        st = store.load_settings("My career")[1]
        st.daily = {"day": "2000-01-01", "at": time.time() - 100}
        st.alert_log = [dict(at=time.time() - 50, kind="matches", title="New matches", text="3 new matches"),
                        dict(at=time.time() - 40, kind="goal", title="Goal reached!", text="England: 1 Test win")]
        store.save_settings(st)
        d = s.json("/api/daily")
        assert d["show"] and d["matches"] == 3 and d["groups"][0]["title"] == "Goal reached!"
        s.post("/api/daily", {})
        assert s.json("/api/daily")["show"] is False            # seen for today
    finally:
        s.stop()


def test_weekly_recheck_finds_and_puts_right(tmp_path):
    import pickle
    store, _, _ = make_pc(tmp_path, n=6)
    c, _ = store.load("My career")              # makes the ready-to-read copy
    assert recheck(store, "My career") == []
    # a damaged kept copy (a figure changed behind the site's back): found, and the copy removed
    f = store._dir("My career") / "career.ready.pickle"
    got = pickle.loads(f.read_bytes())
    got["career"].batting.loc[got["career"].batting.index[0], "runs"] += 7
    f.write_bytes(pickle.dumps(got))
    diff = recheck(store, "My career")
    assert diff and "batting" in diff[0] and not f.exists()
    assert recheck(store, "My career") == []


def test_a_series_whose_length_isnt_printed_never_stops_the_alerts():
    """Found by the deep check on your career: a series with no length printed stopped every alert for that batch."""
    import numpy as np
    c = build(FIXTURES)
    team = "England"
    m = c.matches
    sid = m[((m.home == team) | (m.away == team)) & (m.series_id.fillna("") != "")].series_id.iloc[0]
    _, seen = AL.check(c, [], [team], [], {})
    full, _ = AL.check(c, list(m.source), [team], [], dict(seen, said=[]))
    c.matches = m.assign(series_length=np.where(m.series_id == sid, np.nan, m.series_length))
    out, _ = AL.check(c, list(c.matches.source), [team], [], dict(seen, said=[]))
    # every other alert still arrives; only that series' "won" can't be judged without its length
    assert [a for a in full if a["kind"] != "series"] == [a for a in out if a["kind"] != "series"]
    assert len([a for a in full if a["kind"] != "series"]) > 0
