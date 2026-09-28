import numpy as np
from pathlib import Path

import pytest

from ccstats import analysis as A
from ccstats.loader import Career
from ccstats.stats import Scope

FIXTURES = sorted((Path(__file__).parent / "fixtures").glob("*.txt"))


@pytest.fixture(scope="module")
def career():
    return Career.build("t", [(p.name, p.read_bytes()) for p in FIXTURES])


def final_id(career):
    return career.matches.set_index("source").loc["18_jul_2026-som_v_nht_blast_-_f.txt"].match_id


def test_came_in_at(career):
    fid = final_id(career)
    inns = A.batting_innings(career, [fid], "T Lammonby")
    r = inns.iloc[0]  # Somerset 6/1, 16/2, 16/3, 17/4 ... Lammonby bats 6
    assert (r.position, r.came_in_wickets, r.came_in_score, r.runs) == (6, 4, 17, 76)
    opener = A.batting_innings(career, [fid], "W Smeed").iloc[0]
    assert (opener.came_in_wickets, opener.came_in_score) == (0, 0)


def test_collapse_and_opening_stand(career):
    fid = final_id(career)
    c = A.collapses(career, [fid], "Somerset")
    assert c[["from_score", "to_score", "wickets", "runs"]].values.tolist() == [["0/0", "25/5", 5, 25]]
    o = A.opening_partnerships(career, [fid], "Somerset")
    assert o[["pair", "runs", "unbroken"]].values.tolist() == [["T Banton & W Smeed", 6, False]]


def test_partnerships_add_up_to_the_score(career):
    fid = final_id(career)
    p = A.partnership_by_wicket(career, [fid], "Northamptonshire")  # all out 96
    assert p.average.sum() == 96 and p.stands.sum() == 10


def test_team_record_and_streaks(career):
    ids = Scope(sections=["Tests (bilateral series)"]).match_ids(career.matches)
    tm = A.team_matches(career, ids, "England")
    rec = A.team_record(tm)
    assert (rec["played"], rec["won"], rec["lost"], rec["win_pct"]) == (3, 3, 0, 100.0)
    s = A.streaks(["W", "L", "W", "W", "W", "D", "L", "L"])
    assert s["current"] == ("L", 2) and s["longest_win"] == 3 and s["longest_loss"] == 2


def test_nemesis_and_bunnies_match_the_dismissals(career):
    ids = Scope(sections=["Tests (bilateral series)"]).match_ids(career.matches)
    n = A.nemesis(career, ids, "B Azam")
    inns = A.batting_innings(career, ids, "B Azam")
    assert n.dismissals.sum() <= inns.out.sum() and n.dismissals.sum() >= inns.out.sum() - (inns.how_out == "run out").sum()
    bunn = A.bunnies(career, ids, "J Archer")
    _, bowl = None, career.bowling[career.bowling.match_id.isin(ids) & (career.bowling.player == "J Archer")]
    assert bunn.dismissals.sum() == bowl.wickets.sum()  # every Archer wicket is credited to him
    q = A.wicket_quality(career, ids, "J Archer")
    assert q["top_order"] + q["middle_order"] + q["tail"] == q["total"] == 15


def test_splits_add_up(career):
    ids = Scope(sections=["Tests (bilateral series)"]).match_ids(career.matches)
    inns = A.batting_innings(career, ids, "J Bethell")
    for by in ("venue", "outcome", "batting_first", "opposition"):
        s = A.split_batting(inns, by)
        assert s.runs.sum() == 254 and s.innings.sum() == 5
    c = A.consistency(inns, "multi")
    assert c["bar"] == 30 and round(c["past_bar_pct"]) == 40  # 119 and 96 of 3,119,28,96,8


def test_keepers_are_the_players_who_stumped(career):
    ids = career.matches.match_id
    k = A.keepers(career, ids)
    assert {"J Rew", "C Esterhuizen"} <= set(k.player)  # st Rew b Leach, st E'rhuizen b Sindhu
    assert A.keepers(career, ids, "Somerset").player.tolist() == ["J Rew"]


def test_team_table(career):
    ids = Scope(sections=["Indian Premier League"]).match_ids(career.matches)
    t = A.team_table(career, ids).set_index("team")
    gt = t.loc["Gujarat Titans"]
    assert (gt.played, gt.won, gt.lost) == (4, 4, 0) and gt.win_pct == 100
    assert t.played.sum() == 2 * len(ids)  # every match counted once for each side
    assert (t.won.sum() == (career.matches[career.matches.match_id.isin(ids)].winner != "").sum())
    # net run rate: all out counts as the full 20 overs; over a whole league the NRRs, weighted, net to ~0
    assert np.isfinite(t.nrr).all()
