"""Eleven matches worked out by hand from the printed scorecards (your pick of 14 November), one of every kind: a Test,
an ODI decided by the rain rule, a T20I, an IPL final, The Hundred, a County Championship match, a Blast final, a
domestic one-day final, a follow-on, a rain game settled by a super over, and a tied T20I settled by a super over.

Every expected number below was read off the card and added up by hand (the sums are in the comments), never taken from
the site, so if the reading of a scorecard ever changes, these say so."""

from pathlib import Path

import pytest

from ccstats.loader import Career

HERE = Path(__file__).parent

# source file -> what the card says, worked out by hand
CARDS = {
    "fixtures/19_aug_2026-eng_v_pak_1st_tst.txt": dict(
        # 275 + 322 = 597; 119 + 179 = 298; 597 - 298 = 299
        innings=[("England", 275, 10, 456), ("Pakistan", 119, 10, 207), ("England", 322, 10, 492), ("Pakistan", 179, 10, 333)],
        winner="England", margin_runs=299, margin_wickets=None, pom="G Atkinson", result_type="win",
        bat={"G Atkinson": (51, 96, 5), "J Bethell": (122, 215, 16)},        # 21 + 30 off 48 + 48; 3 + 119 off 11 + 204
        bowl={"G Atkinson": (7, 95, 156), "M Abbas": (7, 149, 300)}),       # 4/32 + 3/63 in 11 + 15 overs; 2/57 + 5/92 in 22 + 28
    "fixtures/16_jul_2026-eng_v_ind_2nd_odi.txt": dict(
        # 377 - 200 = 177, but the card says 127: England's chase was cut by rain (the rain rule)
        innings=[("India", 377, 5, 300), ("England", 200, 10, 211)],
        winner="India", margin_runs=127, margin_wickets=None, pom="S Gill", result_type="win", rain=True,
        bat={"S Gill": (211, 152, 29)}, bowl={}),
    "fixtures/7_jul_2026-eng_v_ind_3rd_20_over_int.txt": dict(
        innings=[("England", 161, 9, 120), ("India", 164, 4, 95)],          # 15.5 overs = 95 balls; 10 - 4 = 6 wickets
        winner="India", margin_runs=None, margin_wickets=6, pom="A Sharma", result_type="win",
        bat={"A Sharma": (66, 28, 9)}, bowl={}),
    "fixtures/31_may_2026-gjt_v_pnj_ipl_-_f.txt": dict(
        innings=[("Punjab Kings", 154, 9, 120), ("Gujarat Titans", 160, 7, 106)],   # 17.4 overs = 106 balls; 10 - 7 = 3
        winner="Gujarat Titans", margin_runs=None, margin_wickets=3, pom="N Sindhu", result_type="win",
        bat={"N Sindhu": (36, 30, 2)}, bowl={"N Sindhu": (3, 32, 24)}),     # 4 overs, 9 dot balls, 32 runs, 3 wickets
    "fixtures/1_aug_2026-brm_v_cdf_hundred.txt": dict(
        innings=[("Birmingham Phoenix", 150, 6, 100), ("Welsh Fire", 153, 7, 92)],    # The Hundred counts balls
        winner="Welsh Fire", margin_runs=None, margin_wickets=3, pom="J Cox", result_type="win",
        bat={"J Cox": (43, 18, 7)}, bowl={}),
    "fixtures/24_sep_2026-som_v_sry_county_-_d1.txt": dict(
        # Surrey 265 + 282 = 547; Somerset 411 + 137 = 548, passing it with 7 wickets left
        innings=[("Surrey", 265, 10, 418), ("Somerset", 411, 10, 590), ("Surrey", 282, 10, 441), ("Somerset", 137, 3, 204)],
        winner="Somerset", margin_runs=None, margin_wickets=7, pom="L Gregory", result_type="win",
        bat={"L Gregory": (94, 107, 13)},                                    # did not bat in the second innings
        bowl={"L Gregory": (6, 146, 222)}),                                  # 2/78 in 19 overs + 4/68 in 18 overs
    "fixtures/18_jul_2026-som_v_nht_blast_-_f.txt": dict(
        innings=[("Somerset", 163, 8, 120), ("Northamptonshire", 96, 10, 87)],   # 163 - 96 = 67
        winner="Somerset", margin_runs=67, margin_wickets=None, pom="T Lammonby", result_type="win",
        bat={"T Lammonby": (76, 47, 10)}, bowl={"T Lammonby": (2, 1, 6)}),   # 1 over, 5 dot balls, 1 run, 2 wickets
    "fixtures/18_jan_2028-kar_v_krc_1_day_cup_-_f.txt": dict(
        innings=[("Kerala CC", 228, 10, 279), ("Karnataka", 232, 3, 286)],  # 46.3 and 47.4 overs
        winner="Karnataka", margin_runs=None, margin_wickets=7, pom="P Krishna", result_type="win",
        bat={}, bowl={"P Krishna": (4, 34, 48)}),
    "fixtures_declare/15_sep_2026-ess_v_wrk_county_-_d1.txt": dict(
        # Essex 293; Warwickshire 134/9 and, following on, 247: 381 - 293 = 88, so 89 to win; Essex 91/0
        innings=[("Essex", 293, 10, 503), ("Warwickshire", 134, 9, 300), ("Warwickshire", 247, 10, 546), ("Essex", 91, 0, 127)],
        winner="Essex", margin_runs=None, margin_wickets=10, pom="P Walter", result_type="win",
        bat={"P Walter": (93, 144, 8)}, bowl={}),                           # 53 off 88 + 40 not out off 56
    "fixtures_rain/20_sep_2026-zim_v_aus_3rd_odi.txt": dict(
        # a rain-shortened game, level by the rain rule, Australia winning the super over 9 to 2
        innings=[("Zimbabwe", 237, 7, 246), ("Australia", 211, 7, 198)],
        winner="Australia", margin_runs=None, margin_wickets=None, pom="J Inglis", result_type="tie", rain=True,
        bat={"J Inglis": (68, 48, 8)}, bowl={}),
    "fixtures_super/2_may_2026-ban_v_nz_3rd_20_over_int.txt": dict(
        # 177 each; the super over: Bangladesh 11/2, New Zealand 21/0
        innings=[("Bangladesh", 177, 9, 120), ("New Zealand", 177, 8, 120)],
        winner="New Zealand", margin_runs=None, margin_wickets=None, pom="L Ferguson", result_type="tie",
        bat={}, bowl={"L Ferguson": (5, 17, 24)}),                          # 4 overs, 15 dot balls, 17 runs, 5 wickets
}


@pytest.fixture(scope="module")
def career():
    c = Career.build("Hand-worked", [(Path(f).name, (HERE / f).read_bytes()) for f in CARDS])
    c.count_fielding = False
    return c


@pytest.mark.parametrize("src", list(CARDS))
def test_hand_worked_match(career, src):
    want = CARDS[src]
    m = career.matches[career.matches.source == Path(src).name]
    assert len(m) == 1, src
    m = m.iloc[0]
    inns = career.innings[career.innings.match_id == m.match_id].sort_values("innings_no")
    got = [(r.team, int(r.runs), int(r.wickets), int(r.balls)) for r in inns.itertuples()]
    assert got == want["innings"], src
    winner = m.winner or m.tiebreak_winner
    assert (m.result_type, winner, m.player_of_match) == (want["result_type"], want["winner"], want["pom"]), src
    runs = None if m.margin_runs != m.margin_runs or m.margin_runs is None else int(m.margin_runs)
    wkts = None if m.margin_wickets != m.margin_wickets or m.margin_wickets is None else int(m.margin_wickets)
    assert (runs, wkts) == (want["margin_runs"], want["margin_wickets"]), src
    assert bool(m.rain) == want.get("rain", False), src
    bat = career.batting[career.batting.match_id == m.match_id]
    for p, (r, b, fours) in want["bat"].items():
        mine = bat[(bat.player == p) & bat.did_bat]
        assert (int(mine.runs.sum()), int(mine.balls.sum()), int(mine.fours.sum())) == (r, b, fours), (src, p)
    bowl = career.bowling[career.bowling.match_id == m.match_id]
    for p, (w, r, b) in want["bowl"].items():
        mine = bowl[bowl.player == p]
        assert (int(mine.wickets.sum()), int(mine.runs.sum()), int(mine.balls.sum())) == (w, r, b), (src, p)


def test_hand_worked_matches_pass_their_own_checks(career):
    """None of the eleven has a sum that doesn't add up, and each is marked checked."""
    assert career.problems.empty or not career.problems.match_id.isin(career.matches.match_id).any()
