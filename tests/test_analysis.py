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
    ids = Scope(sections=["Tests"]).match_ids(career.matches)
    tm = A.team_matches(career, ids, "England")
    rec = A.team_record(tm)
    assert (rec["played"], rec["won"], rec["lost"], rec["win_pct"]) == (3, 3, 0, 100.0)
    s = A.streaks(["W", "L", "W", "W", "W", "D", "L", "L"])
    assert s["current"] == ("L", 2) and s["longest_win"] == 3 and s["longest_loss"] == 2


def test_nemesis_and_bunnies_match_the_dismissals(career):
    ids = Scope(sections=["Tests"]).match_ids(career.matches)
    n = A.nemesis(career, ids, "B Azam")
    inns = A.batting_innings(career, ids, "B Azam")
    assert n.dismissals.sum() <= inns.out.sum() and n.dismissals.sum() >= inns.out.sum() - (inns.how_out == "run out").sum()
    bunn = A.bunnies(career, ids, "J Archer")
    _, bowl = None, career.bowling[career.bowling.match_id.isin(ids) & (career.bowling.player == "J Archer")]
    assert bunn.dismissals.sum() == bowl.wickets.sum()  # every Archer wicket is credited to him
    q = A.wicket_quality(career, ids, "J Archer")
    assert q["top_order"] + q["middle_order"] + q["tail"] == q["total"] == 15


def test_splits_add_up(career):
    ids = Scope(sections=["Tests"]).match_ids(career.matches)
    inns = A.batting_innings(career, ids, "J Bethell")
    for by in ("venue", "outcome", "batting_first", "opposition"):
        s = A.split_batting(inns, by)
        assert s.runs.sum() == 254 and s.innings.sum() == 5
    c = A.consistency(inns, "multi")
    assert c["bar"] == 50 and round(c["past_bar_pct"]) == 40  # a decent Test score is 50: 119 and 96 of 3,119,28,96,8


def test_player_record_tables(career):
    ids = career.matches.match_id
    b = A.batting_record(career, ids, "J Bethell").set_index("section").loc["Tests"]
    assert (b.Inns, b.Runs, b["100"], b["50"]) == (5, 254, 1, 1)  # 3, 119, 28, 96, 8
    w = A.bowling_record(career, ids, "J Archer").set_index("section").loc["Tests"]
    assert w.Wkts == 15 and np.isnan(w.Dots) and w.Mdns >= 0


@pytest.mark.parametrize("section", ["Tests", "Indian Premier League", "The Hundred", "T20 Blast"])
def test_player_record_tables_agree_with_the_stat_tables(career, section):
    """The per-section table on the player page must give the same numbers as Stat by stat."""
    from ccstats.stats import player_tables
    scope = Scope(sections=[section])
    ids = scope.match_ids(career.matches)
    bat, bowl, fld, _ = player_tables(career, scope)
    for p in bat[bat.innings > 0].player.head(25):
        r = A.batting_record(career, ids, p).iloc[0]
        t = bat.set_index("player").loc[p]
        f = fld.set_index("player").loc[p]
        assert (r.Mat, r.Inns, r.Runs, r.BF, r["100"], r["50"], r["0"], r["4s"], r["6s"], r.HS) == \
               (t.matches, t.innings, t.runs, t.balls, t.hundreds, t.fifties, t.ducks, t.fours, t.sixes, t.high_score_text), p
        assert (r.Ct, r.St) == (f.catches, f.stumpings), p
        assert (np.isnan(r.Avg) and np.isnan(t.average)) or abs(r.Avg - t.average) < 1e-9, p
    for p in bowl.player.head(25):
        r = A.bowling_record(career, ids, p).iloc[0]
        t = bowl.set_index("player").loc[p]
        assert (r.Inns, r.Balls, r.Runs, r.Wkts, r.BBI, r.BBM) == (t.innings, t.balls, t.runs, t.wickets, t.best, t.best_match), p
        assert r["4w"] + r["5w"] == t.hauls and r["5w"] == t.five_fors, p
        assert abs(r.Econ - t.economy) < 1e-9, p


def test_role_labels(career):
    ids = Scope(sections=["T20 Blast"]).match_ids(career.matches)
    r = A.role_labels(career, ids, "t20", min_matches=2).set_index("player")
    assert r.role["W Smeed"] == "Opener" and r.role["T Banton"] == "Opener"
    everyone = A.role_labels(career, ids, "t20", min_matches=1).set_index("player")
    assert "Wicketkeeper" in everyone.tags["J Tattersall"]  # st Tattersall in the Blast
    assert "Wicketkeeper" not in everyone.tags.get("J Rew", [])  # his stumping was in the County Championship, not here
    assert sum("Wicketkeeper" in t for t in everyone.tags) == 1
    assert r.role["Y Chahal"] == "Bowler"
    assert (r.matches >= 2).all()
    # nobody with fewer matches than the minimum gets a label
    few = A.role_labels(career, ids, "t20", min_matches=3)
    counts = career.batting[career.batting.match_id.isin(ids)].groupby("player").match_id.nunique()
    assert set(few.player) == set(counts[counts >= 3].index)


def test_position_scope_counts_only_those_innings(career):
    from ccstats.stats import POSITION_GROUPS, player_tables
    sec = Scope(sections=["Indian Premier League"])
    total = player_tables(career, sec)[0].runs.sum()
    parts = sum(player_tables(career, Scope(sections=sec.sections, positions=p))[0].runs.sum() for p in POSITION_GROUPS.values())
    assert parts == total  # every innings is at exactly one position
    openers, _, _, base = player_tables(career, Scope(sections=sec.sections, positions=[1, 2]))
    b = career.batting[career.batting.match_id.isin(sec.match_ids(career.matches)) & career.batting.did_bat
                       & career.batting.position.isin([1, 2])]
    assert abs(base.average - b.runs.sum() / b.out.sum()) < 1e-9
    gill = A.position_record(career, sec.match_ids(career.matches), "S Gill").set_index("group")
    assert gill.runs.sum() == player_tables(career, sec)[0].set_index("player").runs["S Gill"]


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
