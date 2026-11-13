"""How they play (Opponent preview · About them, ccstats/howtheyplay.py): every figure counted again from the
scorecards by hand, for every team in every competition of the test scorecards; and the season picked as agreed
(this season, last season offered when this one has fewer than 5 matches)."""

from __future__ import annotations

import numpy as np
import pytest

from ccstats import howtheyplay as HP
from ccstats.loader import Career
from server.app import create_app
from serverkit import FIXTURES, Live, make_pc


@pytest.fixture(scope="module")
def career():
    return Career.build("Test career", [(f.name, f.read_bytes()) for f in FIXTURES])


def _kind(fmt):
    return {"Test": "multi", "First-class": "multi", "ODI": "one", "List A": "one"}.get(fmt, "t20")


def test_every_figure_counted_by_hand(career):
    m = career.matches
    done = 0
    for sec in sorted(m.section.unique()):
        here = m[m.section == sec]
        ids = set(here.match_id)
        for team in sorted(set(here.home) | set(here.away)):
            h = HP.how_they_play(career, ids, team)
            mine = here[(here.home == team) | (here.away == team)]
            kind = _kind(mine.format.mode().iloc[0])
            assert h["kind"] == kind and h["matches"] == len(mine)
            bw, bt = h["bowling"], h["batting"]
            inns = career.innings[career.innings.match_id.isin(mine.match_id)]
            theirs, own = inns[inns.team != team], inns[inns.team == team]
            # when the wickets come: the middle score at their 1st, 2nd and 3rd wicket, half rounded up
            for w in (1, 2, 3):
                xs = []
                for r in theirs.itertuples():
                    f = career.fow[(career.fow.match_id == r.match_id) & (career.fow.innings_no == r.innings_no) & (career.fow.wicket == w)]
                    xs += list(f.score)
                assert bw["at"][w]["innings"] == len(xs)
                assert bw["at"][w]["usual"] == (int(np.floor(np.median(xs) + 0.5)) if xs else None)
            cheap = 0
            for r in theirs.itertuples():
                f = career.fow[(career.fow.match_id == r.match_id) & (career.fow.innings_no == r.innings_no) & (career.fow.wicket == 3)]
                cheap += bool(len(f) and f.score.iloc[0] <= HP.CHEAP[kind])
            assert (bw["innings"], bw["cheap"], bw["bowled_out"]) == (len(theirs), cheap, int(theirs.all_out.sum()))
            # the new-ball pair: the first two bowlers on each card
            new = tot = 0
            for (mid, no), g in career.bowling[career.bowling.match_id.isin(mine.match_id) & (career.bowling.team == team)].groupby(
                    ["match_id", "innings_no"], sort=False):
                new += int(g.wickets.iloc[:2].sum())
                tot += int(g.wickets.sum())
            assert (bw["new_ball"], bw["wickets"]) == (new, tot)
            outs = career.batting[career.batting.match_id.isin(mine.match_id) & (career.batting.team != team) & career.batting.out]
            assert (bw["outs"], bw["top_order"]) == (len(outs), int((outs.position <= 3).sum()))
            # each part of the order
            bat = career.batting[career.batting.match_id.isin(mine.match_id) & (career.batting.team == team) & career.batting.did_bat]
            for p, (label, lo, hi) in zip(bt["parts"], HP.PARTS):
                x = bat[(bat.position >= lo) & (bat.position <= hi)]
                assert (p["part"], p["runs"], p["balls"], p["fours"], p["sixes"]) == (label, x.runs.sum(), x.balls.sum(), x.fours.sum(), x.sixes.sum())
                if p["balls"]:
                    assert p["strike_rate"] == pytest.approx(x.runs.sum() / x.balls.sum() * 100)
            assert bt["from_fours"] + bt["from_sixes"] + bt["running"] == bt["runs"] == bat.runs.sum()
            # the usual score at each wicket: rising, and each one the middle score of the innings it fell in
            u = bt["usual"]
            assert list(u) == list(range(1, len(u) + 1)) and list(u.values()) == sorted(set(u.values()))
            for w, v in u.items():
                xs = [s for r in own.itertuples() for s in career.fow[(career.fow.match_id == r.match_id)
                      & (career.fow.innings_no == r.innings_no) & (career.fow.wicket == w)].score]
                assert v == int(np.floor(np.median(xs) + 0.5)) and len(xs) >= 0.5 * len(own)
            done += 1
    assert done > 60


def test_this_season_and_last(career):
    """This season is the competition's latest; last season is the one before it they played in; the matches each."""
    m = career.matches
    for sec in m.section.unique():
        here = m[m.section == sec]
        for team in set(here.home) | set(here.away):
            this, last, n = HP.seasons(career, set(here.match_id), team)
            assert this == here.sort_values("date").season.iloc[-1] or this == here.groupby("season").date.max().idxmax()
            mine = here[(here.home == team) | (here.away == team)]
            assert n == mine.season.value_counts().to_dict()
            earlier = [s for s in mine.season.unique() if here[here.season == s].date.max() < here[here.season == this].date.max()]
            if last:
                assert last in earlier and n[last] > 0
            else:
                assert not earlier


def test_the_page_shows_it_this_season_with_last_season_a_click_away(tmp_path):
    pc = make_pc(tmp_path, files=FIXTURES)
    web = tmp_path / "dist"
    (web / "assets").mkdir(parents=True)
    (web / "index.html").write_text("<!doctype html><title>Stats Pack</title><div id=root></div>")
    s = Live(create_app(pc[0], web=web, watch_every=0))
    try:
        c = s.app.state.site.career()
        m = c.matches
        checked = 0
        for sec in ("ODIs", "T20Is", "Tests"):
            here = m[m.section == sec]
            for opp in sorted(set(here.home) | set(here.away))[:5]:
                q = f"/api/preview?section=Internationals&format={sec}&opp={opp}&tab=About them"
                b = s.json(q)["body"]
                if b.get("none"):
                    continue
                h = b["how"]
                assert b["missing"] == {} and h["season"] == h["this"]
                n = HP.seasons(c, set(here.match_id), opp)[2].get(h["this"], 0)
                assert bool(h.get("note")) == (n < HP.MIN_MATCHES)
                if h.get("last"):
                    x = s.json(q + "&htp=last")
                    assert x["htp"] == "last" and x["body"]["how"]["season"] == h["last"] and x["body"]["how"]["showing_last"]
                checked += 1
        assert s.json("/api/preview?section=Internationals&format=All&tab=About them")["body"]["how"]["none"].startswith("Pick one format")
        assert checked >= 5
    finally:
        s.stop()
