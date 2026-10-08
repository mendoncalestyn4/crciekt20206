"""Games shortened by rain (real scorecards): which games count as rain-affected, net run rate by the ICC's rules,
first-innings totals that aren't compared with full games, win chances that don't learn from them, and the note on
the match page."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from ccstats import analysis as A
from ccstats import insights as I
from ccstats import teamplay as TP
from ccstats import winprob as W
from ccstats.loader import Career

HERE = Path(__file__).parent
RAIN = sorted((HERE / "fixtures_rain").glob("*.txt"))
DLS_ODI = HERE / "fixtures" / "16_jul_2026-eng_v_ind_2nd_odi.txt"


@pytest.fixture(scope="module")
def career():
    return Career.build("rain", [(p.name, p.read_bytes()) for p in RAIN + [DLS_ODI]])


def row(career, source):
    return career.matches.set_index("source").loc[source]


def test_which_games_the_weather_shortened(career):
    rain = dict(zip(career.matches.source, career.matches.rain))
    assert rain == {
        "1_apr_2026-lkn_v_del_ipl.txt": False,  # 187/6 in 20 overs, 135 all out: a full game
        "14_apr_2026-chn_v_klk_ipl.txt": True,  # 164/8 in 17 overs, 48/6 in 6: decided by the rain rule
        "23_apr_2026-mmb_v_chn_ipl.txt": True,  # 175/6 in 19 overs; Chennai won with 119/7: a revised target
        "3_aug_2026-cdf_v_stn_hundred.txt": True,  # 70 balls a side
        "4_aug_2026-lds_v_lnb_hundred.txt": True,  # abandoned after 60 balls
        "10_aug_2026-ntm_v_stn_hundred.txt": True,  # abandoned without a ball
        "20_sep_2026-zim_v_aus_3rd_odi.txt": True,  # 41 overs v 33 overs, tied on the rain rule
        "16_jul_2026-eng_v_ind_2nd_odi.txt": True,  # England's chase cut to 40 overs, "won by 127 runs"
    }


def test_net_run_rate_by_the_icc_rules(career):
    n = A.nrr_innings(career, career.matches.match_id).merge(career.matches[["match_id", "source"]])
    got = {(r.source, r.team): (r.runs, r.balls) for r in n.itertuples()}
    # a side bowled out is charged its full overs
    assert got[("1_apr_2026-lkn_v_del_ipl.txt", "Lucknow Super Giants")] == (135, 120)
    assert got[("1_apr_2026-lkn_v_del_ipl.txt", "Delhi Capitals")] == (187, 120)
    # decided by the rain rule with the chase stopped: the side batting first is credited with the par score
    # (Kolkata's 48 and the 20-run margin) off the same 6 overs Kolkata faced
    assert got[("14_apr_2026-chn_v_klk_ipl.txt", "Chennai Super Kings")] == (68, 36)
    assert got[("14_apr_2026-chn_v_klk_ipl.txt", "Kolkata Knight Riders")] == (48, 36)
    # bowled out in a chase cut to 40 overs (no bowler had more than 8): charged the 40 overs; India credited with
    # the revised target less one (200 + 127) off them
    assert got[("16_jul_2026-eng_v_ind_2nd_odi.txt", "England")] == (200, 240)
    assert got[("16_jul_2026-eng_v_ind_2nd_odi.txt", "India")] == (327, 240)
    # a revised target the scorecard doesn't give: each side's own runs and overs
    assert got[("23_apr_2026-mmb_v_chn_ipl.txt", "Mumbai Indians")] == (175, 114)
    assert got[("23_apr_2026-mmb_v_chn_ipl.txt", "Chennai Super Kings")] == (119, 84)
    # abandoned games don't count at all
    assert not any(s.startswith(("4_aug", "10_aug")) for s, _ in got)


def test_the_league_table_uses_them(career):
    ids = career.matches[career.matches.source.str.contains("ipl")].match_id
    t = A.team_table(career, ids).set_index("team")
    assert t.nrr["Kolkata Knight Riders"] == pytest.approx((48 / 36 - 68 / 36) * 6)
    # Chennai: 68 off 36 and 119 off 84 for, 48 off 36 and 175 off 114 against
    assert t.nrr["Chennai Super Kings"] == pytest.approx(((68 + 119) / (36 + 84) - (48 + 175) / (36 + 114)) * 6)
    hundred = career.matches[career.matches.source.str.contains("hundred")].match_id
    h = A.team_table(career, hundred).set_index("team")
    # Leeds and London only played the abandoned game: nothing for or against
    assert h.nrr["SunRisers Leeds"] == 0 and h.nrr["London Spirit"] == 0


def test_shortened_totals_are_not_compared_with_full_ones(career):
    g = TP.games(career, career.matches.match_id).merge(career.matches[["match_id", "rain"]])
    assert g[g.rain].first_score.isna().all()
    assert g[~g.rain].first_score.notna().all()
    fi = I.first_innings(career, career.matches.match_id)
    assert set(fi.match_id) == set(career.matches[~career.matches.rain].match_id)
    # a team's first-innings average leaves them out too
    t = A.team_table(career, career.matches[career.matches.source.str.contains("ipl")].match_id).set_index("team")
    assert t.first_innings_avg["Delhi Capitals"] == 187
    assert t.first_innings_avg.get("Mumbai Indians") != t.first_innings_avg.get("Mumbai Indians")  # NaN: only rain


def test_win_chances_do_not_learn_from_rain_games(career):
    s = W.states(career, career.matches.match_id)
    assert s.groupby("match_id").rain.first().to_dict() == {
        mid: bool(r) for mid, r in zip(career.matches.match_id, career.matches.rain)
        if mid in set(s.match_id)}
    ch = W.chance(s, 2, False, 0, -150, "t20")
    full = career.matches[~career.matches.rain & (career.matches.result_type != "no result")]
    assert ch["n"] <= len(full)
    # a rain game still has its own line
    mid = row(career, "14_apr_2026-chn_v_klk_ipl.txt").match_id
    assert len(W.match_line(career, mid, s, "t20")) > 0


def test_the_match_page_says_so(career):
    for source, words in (("14_apr_2026-chn_v_klk_ipl.txt", "decided by the rain rule (DLS)"),
                          ("4_aug_2026-lds_v_lnb_hundred.txt", "Abandoned because of rain"),
                          ("3_aug_2026-cdf_v_stn_hundred.txt", "Shortened by rain")):
        at = AppTest.from_file(str(HERE.parent / "views" / "match.py"), default_timeout=60)
        at.session_state["career_obj"] = career
        at.query_params["match"] = row(career, source).match_id
        at.run()
        assert not at.exception, at.exception
        text = " ".join(c.value for c in at.caption)
        assert words in text, source
    at = AppTest.from_file(str(HERE.parent / "views" / "match.py"), default_timeout=60)
    at.session_state["career_obj"] = career
    at.query_params["match"] = row(career, "1_apr_2026-lkn_v_del_ipl.txt").match_id
    at.run()
    assert not any("🌧️" in c.value for c in at.caption)


# --------------------------------------------------------------------------- declarations (not rain, same check)
def test_nobody_left_to_bat_is_all_out_not_a_declaration():
    files = sorted((HERE / "fixtures_declare").glob("*.txt"))
    c = Career.build("dec", [(p.name, p.read_bytes()) for p in files])
    inn = c.innings.merge(c.matches[["match_id", "source"]])
    # Warwickshire 134/9: Yates retired hurt, everyone else batted, then they followed on
    w = inn[(inn.team == "Warwickshire") & (inn.team_innings == 1)].iloc[0]
    assert (w.runs, w.wickets, w.all_out, w.declared) == (134, 9, True, False)
    # Leicestershire 512/9 with two batters not out: a real declaration
    lc = inn[(inn.team == "Leicestershire") & (inn.team_innings == 1)].iloc[0]
    assert (lc.runs, lc.wickets, lc.all_out, lc.declared) == (512, 9, False, True)
    # every declaration left at least two batters able to bat
    for r in inn[inn.declared].itertuples():
        b = c.batting[(c.batting.match_id == r.match_id) & (c.batting.innings_no == r.innings_no)]
        assert b.how_out.isin(["not out", "dnb"]).sum() >= 2
