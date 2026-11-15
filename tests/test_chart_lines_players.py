"""The three lines under every chart on the Player page (design/CHART_LINES.md, the owner's choice of 14 November):
What it is, Who's best (labelled for the player's top thing on a one-player chart) and What it's for, all written by
the server; the numbers in "Who's best" counted again from the scorecards."""

import re

import pytest

from ccstats.loader import Career
from server import playerpage as PP
from serverkit import FIXTURES

BAT = ["form", "compare", "runs_from", "seasons", "how_out", "danger", "funnel", "positions", "came_in", "nemesis", "against"]
BOWL = ["form", "seasons", "how_wickets", "quality", "bunnies"]


@pytest.fixture(scope="module")
def career():
    c = Career.build("Test career", [(f.name, f.read_bytes()) for f in FIXTURES])
    c.count_fielding = False   # as the new site opens it
    return c


def _check(part, where):
    if part.get("empty"):   # an empty chart shows its "not enough yet" message instead
        return
    assert isinstance(part.get("is_"), str) and part["is_"].strip(), (where, "is_")
    assert isinstance(part.get("for_"), str) and part["for_"].strip(), (where, "for_")
    assert isinstance(part.get("best"), str) and part["best"].strip(), (where, "best")
    assert part.get("best_label"), (where, "best_label: every Player page chart is one player's, so it names his top thing")


def test_every_player_page_chart_has_its_three_lines(career):
    names = sorted(set(career.batting.player) | set(career.bowling.player))
    seen = 0
    for p in names[::4]:
        d = PP.page(career, p)
        if d["card"] and len(d["card"]["last10"]) > 1:
            assert d["card"]["last10_is"] and d["card"]["last10_best"] and d["card"]["last10_for"]
        if d["winners"] and d["winners"]["wins"]:
            _check(d["winners"], (p, "winners"))
        if d.get("profile") and d["profile"].get("best"):
            _check(d["profile"], (p, "profile"))
        b, w, st = d["batting"], d["bowling"], d["story"]
        for k in BAT if b else []:
            if b.get(k):
                _check(b[k], (p, "batting", k))
                seen += 1
        for s in (b["splits"]["rows"] if b else []):
            _check(s, (p, "batting split", s["title"]))
        for k in BOWL if w else []:
            if w.get(k):
                _check(w[k], (p, "bowling", k))
                seen += 1
        for s in (w["splits"]["rows"] if w else []):
            _check(s, (p, "bowling split", s["title"]))
        for k in ("impact", "rank"):
            if st and st.get(k):
                _check(st[k], (p, "story", k))
    assert seen >= 50


def test_whos_best_on_the_player_page_counted_again_from_the_scorecards(career):
    """Best season (runs and wickets), most common way out, their nemesis and their best innings, each counted again
    straight from the scorecards for players with enough cricket."""
    m = career.matches.set_index("match_id")
    checked = 0
    for p in career.batting[career.batting.did_bat].player.value_counts().index[:15]:
        d = PP.page(career, p)
        sec = d["section"]
        mine = career.batting[(career.batting.player == p) & career.batting.did_bat
                              & career.batting.match_id.map(m.section).eq(sec)]
        b = d["batting"]
        # best season: the most runs in one season here
        per = mine.groupby(mine.match_id.map(m.season)).runs.sum()
        top = per.sort_values(ascending=False)
        assert b["seasons"]["best"].startswith(f"{top.index[0]}: {top.iloc[0]:,} runs") or top.iloc[0] == top.iloc[1]
        # best innings: the highest score (not out first when level)
        hi = mine.assign(k=mine.runs * 2 + ~mine.out).sort_values("k").iloc[-1]
        assert b["form"]["best"].startswith(f"{hi.runs}{'' if hi.out else '*'} off {hi.balls} v ")
        # most often out: the commonest way out
        if b["how_out"]:
            ways = mine[mine.out].how_out.value_counts()
            n = int(re.search(r": (\d+) of (\d+)", b["how_out"]["best"]).group(1))
            assert n == ways.iloc[0] and int(re.search(r" of (\d+)", b["how_out"]["best"]).group(1)) == ways.sum()
        # their nemesis: the bowler who got them out most
        if b["nemesis"]:
            got = mine[mine.out & (mine.bowler != "")].bowler.value_counts()
            assert b["nemesis"]["best"].endswith(f"{got.iloc[0]} time{'s' if got.iloc[0] != 1 else ''}")
            assert b["nemesis"]["best"].startswith(got.index[0]) or got.iloc[0] == got.iloc[1]
        checked += 1
    for p in career.bowling[career.bowling.balls > 0].player.value_counts().index[:10]:
        d = PP.page(career, p)
        if not d["bowling"]:
            continue
        sec = d["section"]
        spells = career.bowling[(career.bowling.player == p) & (career.bowling.balls > 0)
                                & career.bowling.match_id.map(m.section).eq(sec)]
        per = spells.groupby(spells.match_id.map(m.season)).wickets.sum().sort_values(ascending=False)
        assert d["bowling"]["seasons"]["best"].startswith(f"{per.index[0]}: {int(per.iloc[0])} wickets") or per.iloc[0] == per.iloc[1]
        best = spells.assign(k=spells.wickets * 1000 - spells.runs).sort_values("k").iloc[-1]
        assert d["bowling"]["form"]["best"].startswith(f"{int(best.wickets)}/{int(best.runs)} v ")
        checked += 1
    assert checked >= 15
