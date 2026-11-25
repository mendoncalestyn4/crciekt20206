"""Stage 3, Compare players (your answers 12, 15, 16, 22): up to four players, the competition dropdown with tick boxes
(runs above average and runs saved each against its own competition when several are ticked), every figure equal to
the Stat by stat tables, the career curves counted again from the scorecards, and "plays like" counted again by hand
(inside one competition only, the nearest on the figures it says, the player never matched with himself)."""

from __future__ import annotations

import json
import math

import numpy as np
import pytest

from ccstats import compare as CP
from ccstats import demo_league as DL
from ccstats import leaders as L
from ccstats.loader import Career
from ccstats.stats import Scope
from server import comparepage as CPg
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
    return CPg.compare_page(c, {k: str(v) for k, v in q.items()}, ["India"])


def test_defaults_and_at_most_four(career):
    d = page(career, section="ODIs")
    assert len(d["players"]) == 2 and d["ticked"] == ["ODIs"]
    names = d["names"][:6]
    d = page(career, section="ODIs", players="|".join(names))
    assert d["players"] == names[:4]
    assert page(career, section="ODIs", players="Nobody|Else")["players"] == d["players"][:0] + page(career, section="ODIs")["players"]


def test_figures_equal_stat_by_stat(career):
    for disc in ("Batting", "Bowling"):
        d = page(career, section="ODIs|T20Is", disc=disc)
        table, _ = L.tables(career, Scope(sections=["ODIs", "T20Is"]), disc)
        t = table.set_index("player")
        col = "runs_above_average" if disc == "Batting" else "runs_saved"
        label = "Runs above avg" if disc == "Batting" else "Runs saved"
        row = next(r for r in d["summary"]["rows"] if r[0] == label)
        for p, v in zip(d["players"], row[1:]):
            assert v.replace(",", "") == f"{t.loc[p, col]:.1f}"
        assert d["combined"] and all(c["reference"] is None for c in d["charts"])
    d = page(career, section="ODIs")
    assert any(c["reference"] is not None for c in d["charts"])


def test_career_curves_counted_again(career):
    d = page(career, section="ODIs")
    ids = set(career.matches[career.matches.section == "ODIs"].match_id)
    for s in d["curves"]["series"]:
        b = career.batting[career.batting.match_id.isin(ids) & career.batting.did_bat & (career.batting.player == s["player"])]
        assert s["points"][-1] == int(b.runs.sum()) and len(s["points"]) == len(b)


def test_plays_like_counted_again(league):
    sec = league.matches.section.iloc[0]
    for disc in ("Batting", "Bowling"):
        pool = CP._pool(league, sec, [], disc)
        cols = [c for c, _ in CP.FEATURES[disc]]
        x = pool[cols].astype(float)
        z = ((x - x.median()) / x.std(ddof=0)).fillna(0)
        me = pool.player.iloc[0]
        got = CP.plays_like(league, sec, [], me, disc)
        assert len(got) == 3 and me not in set(got.player)
        mz = z[pool.player == me].iloc[0]
        by_hand = {p: 100 * math.exp(-float(np.mean([(z.loc[i, c] - mz[c]) ** 2 for c in cols])) / 2)
                   for i, p in pool.player.items() if p != me}
        best = sorted(by_hand.items(), key=lambda kv: (-kv[1], kv[0]))[:3]
        assert list(got.player) == [p for p, _ in best]
        assert list(got.alike.round(6)) == [round(v, 6) for _, v in best]
        # only players of this one competition
        ids = set(league.matches[league.matches.section == sec].match_id)
        b = league.batting if disc == "Batting" else league.bowling
        assert set(got.player) <= set(b[b.match_id.isin(ids)].player)


def test_plays_like_on_the_page(league):
    sec = league.matches.section.iloc[0]
    pool = CP._pool(league, sec, [], "Batting")
    four = list(pool.player[:4])
    d = page(league, section=sec, players="|".join(four), like=four[1])
    assert d["like"]["player"] == four[1] and d["like"]["full"] and len(d["like"]["rows"]) == 3
    d = page(league, section=sec, players=four[0])
    assert not d["like"]["full"]


@pytest.mark.parametrize("which", ["career", "league"])
def test_every_competition_season_and_discipline(career, league, which):
    c = career if which == "career" else league
    for disc in ("Batting", "Bowling"):
        for sec in c.matches.section.unique():
            for season in [""] + sorted(map(str, c.matches[c.matches.section == sec].season.unique())):
                assert json.dumps(page(c, section=sec, season=season, disc=disc))


def test_empty_career_and_odd_addresses(career):
    assert CPg.compare_page(Career.build("Empty", []), {}, [])["none"]
    for q in (dict(section="x"), dict(disc="x"), dict(season="x"), dict(like="Nobody")):
        assert json.dumps(page(career, **q))
