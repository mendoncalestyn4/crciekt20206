"""Stage 3, Rankings (your answers 21, 24, 25, 28, 29): ranked on the Player page's marks out of 10, recent series
counting more, three lists, who is ranked, peaks, time at No. 1, movement, several formats combined, and every team
by runs and wickets up to any date. Each figure is counted again another way."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ccstats import demo_league as DL
from ccstats import marks as MK
from ccstats import ranking as RK
from ccstats import rankings as R
from ccstats.loader import Career
from server import leaderspage as LP
from serverkit import FIXTURES


@pytest.fixture(scope="module")
def league():
    """Three IPL-style seasons, enough for players to be ranked."""
    files = DL.generate((2026, 2027, 2028))
    c = Career.build("Demo", [(n, t.encode() if isinstance(t, str) else t) for n, t in files])
    c.count_fielding = False
    return c


@pytest.fixture(scope="module")
def career():
    c = Career.build("Test career", [(f.name, f.read_bytes()) for f in FIXTURES])
    c.count_fielding = False
    return c


@pytest.mark.parametrize("which", ["league", "career"])
def test_the_marks_are_the_player_pages(which, request):
    """A finished series' batting (or bowling) mark is the Player page's mark wherever he only batted (or bowled)."""
    c = request.getfixturevalue(which)
    fin = RK.states(c).groupby(["series", "team", "player"]).tail(1).set_index(["series", "team", "player"])
    sm = MK.series_marks(c).set_index(["series", "team", "player"])
    bat = fin[fin.bowl_mark.isna() & fin.bat_mark.notna()].join(sm.mark, how="inner")
    bowl = fin[fin.bat_mark.isna() & fin.bowl_mark.notna()].join(sm.mark, how="inner")
    assert len(bat) > 20 and (bat.bat_mark == bat.mark).all()
    assert (bowl.bowl_mark == bowl.mark).all()


def test_each_rating_counted_again_from_its_series(league):
    sec = league.matches.section.iloc[0]
    for what in RK.KINDS:
        b = RK.board(league, sec, what)
        assert len(b["table"]) > 5, what
        for r in b["table"].head(15).itertuples():
            parts, val = RK.breakdown(league, sec, r.player, what)
            assert val == pytest.approx(r.rating), (what, r.player)
            if what != "all-round":   # a weighted average of marks out of 10
                k = "bat" if what == "batting" else "bowl"
                marks = [p[k] for p in parts if p[k] is not None]
                assert min(marks) <= r.rating <= max(marks)
            else:                     # ranked on batting × bowling, shown as its square root
                bat = RK.breakdown(league, sec, r.player, "batting")[1]
                bowl = RK.breakdown(league, sec, r.player, "bowling")[1]
                assert r.rating == pytest.approx((bat * bowl) ** 0.5)
        ratings = list(b["table"].rating)
        assert ratings == sorted(ratings, reverse=True)


def test_who_is_ranked(league):
    """At least 10 innings (T20) in the last two seasons, from both seasons in a league played once a season; those
    close to it are listed with what they still need."""
    sec = league.matches.section.iloc[0]
    st = RK.states(league)
    last_two = sorted(league.matches.season.unique())[-2:]
    for what, col in (("batting", "bat_inns"), ("bowling", "bowl_inns")):
        b = RK.board(league, sec, what)
        here = st[(st.section == sec) & st.season.isin(last_two)]
        inns = here.groupby(["series", "team", "player"]).tail(1).groupby("player")[col].sum()
        seasons = here.groupby("player").season.nunique()
        for r in b["table"].itertuples():
            assert inns[r.player] == r.inns >= 10 and seasons[r.player] == 2
        for r in b["near"].itertuples():
            assert r.needs and (r.inns < 10 or seasons[r.player] < 2)


def test_recent_series_count_more(league):
    """A series that ended a year before the latest match counts half (by games)."""
    sec = league.matches.section.iloc[0]
    r = RK.board(league, sec, "batting")["table"].iloc[0]
    parts, _ = RK.breakdown(league, sec, r.player, "batting")
    assert len(parts) == 2
    old, new = sorted(parts, key=lambda p: p["weight"] / p["games"])
    assert new["weight"] > 0.95 * new["games"]                     # the latest season: (almost) full weight
    assert 0.3 < old["weight"] / old["games"] < 0.7               # the season before: about half


def test_peaks_number_ones_and_movement_counted_again(league):
    sec = league.matches.section.iloc[0]
    b = RK.board(league, sec, "batting")
    h = RK.history(league, sec, "batting")
    days = sorted(h.date.unique())
    prev = h[h.date == days[-2]].set_index("player")["rank"]
    for r in b["table"].itertuples():
        mine = h[h.player == r.player]
        assert r.peak == pytest.approx(mine.rating.max())
        assert r.at_one == int(mine[mine["rank"] == 1].matches.sum())
        if r.player in prev.index:
            assert r.moved == prev[r.player] - r.rank
    assert sum(x["matches"] for x in b["reigns"]) == int(h[h["rank"] == 1].drop_duplicates("date").matches.sum())


def test_several_formats_combine_by_innings(league):
    sec = league.matches.section.iloc[0]
    c = RK.combined(league, [sec], "batting")
    one = RK.board(league, sec, "batting")["table"]
    assert list(c.player) == list(one.player) and np.allclose(c.rating, one.rating)


def test_every_team_by_runs_and_wickets_counted_again(career):
    m = career.matches
    secs = ["ODIs", "T20Is"]
    upto = m[m.section.isin(secs)].date.sort_values().iloc[len(m[m.section.isin(secs)]) // 2]
    d = LP.rankings_page(career, dict(tab="Teams by runs and wickets", section="|".join(secs), date=f"{upto:%Y-%m-%d}"), [])
    ids = set(m[m.section.isin(secs) & (m.date <= upto)].match_id)
    b = career.batting[career.batting.match_id.isin(ids) & career.batting.did_bat]
    cols = d["table"]["cols"]
    for row in d["table"]["rows"]:
        x = dict(zip(cols, row))
        assert int(x["Runs"].replace(",", "")) == b[b.team == x["Team"]].runs.sum()
        played = ((m.match_id.isin(ids)) & ((m.home == x["Team"]) | (m.away == x["Team"]))).sum()
        assert x["Mat"] == played
    assert d["date"] == f"{upto:%Y-%m-%d}" and d["ends"][0]["date"] == d["last"]
    assert R.team_totals(career, list(ids)).runs.sum() == b.runs.sum()


@pytest.mark.parametrize("q", [dict(tab="junk"), dict(what="fielding"), dict(tab="Teams by runs and wickets", date="zz"),
                               dict(tab="Rankings history", players="Nobody|<b>"), dict(tab="Team ratings", teams="x", team="y"),
                               dict(section="junk|ODIs")])
def test_junk_in_the_address_gives_the_normal_page(career, q):
    d = LP.rankings_page(career, q, [])
    assert d["tab"] in d["tabs"] and d["what"] in ("batting", "bowling", "all-round") and d["ticked"]
