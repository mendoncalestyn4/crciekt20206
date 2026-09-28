from datetime import date
from pathlib import Path

import pytest

from ccstats.competitions import (
    assign_seasons, assign_series, classify, fix_playoff_stages,
)
from ccstats.parser import parse_scorecard

FIXTURES = Path(__file__).parent / "fixtures"


def load(name):
    return parse_scorecard((FIXTURES / name).read_text(), name)


# every sample file -> (competition, format, level, stage, knockout)
EXPECTED = {
    "19_aug_2026-eng_v_pak_1st_tst.txt": ("Test", "Test", "International", "", False),
    "1_oct_2026-ind_v_wi_1st_odi.txt": ("ODI", "ODI", "International", "", False),
    "1_oct_2026-pak_v_sl_1st_20_over_int.txt": ("T20I", "T20I", "International", "", False),
    "13_jun_2027-rsa_v_eng_wc_-_group.txt": ("ODI World Cup", "ODI", "International", "Group", False),
    "23_jun_2027-sl_v_eng_wc_-_f.txt": ("ODI World Cup", "ODI", "International", "Final", True),
    "11_mar_2026-aus_v_ind_wc20_-_f.txt": ("T20 World Cup", "T20I", "International", "Final", True),
    "6_may_2026-hdr_v_pnj_ipl.txt": ("Indian Premier League", "T20", "Franchise", "", False),
    "29_may_2026-pnj_v_mmb_ipl_-_q2.txt": ("Indian Premier League", "T20", "Franchise", "Qualifier 2", True),
    "1_aug_2026-brm_v_cdf_hundred.txt": ("The Hundred", "The Hundred", "Franchise", "", False),
    "3_jul_2026-yrk_v_drh_blast_-_n.txt": ("T20 Blast", "T20", "Domestic", "North Group", False),
    "3_jul_2026-wrc_v_knt_blast_-_group.txt": ("T20 Blast", "T20", "Domestic", "Group", False),
    "15_jul_2026-drh_v_knt_blast_-_qf.txt": ("T20 Blast", "T20", "Domestic", "Quarter-final", True),
    "18_jul_2026-som_v_nht_blast_-_f.txt": ("T20 Blast", "T20", "Domestic", "Final", True),
    "24_sep_2026-som_v_sry_county_-_d1.txt": ("County Championship", "First-class", "Domestic", "Division 1", False),
    "8_sep_2026-dby_v_knt_county_-_d2.txt": ("County Championship", "First-class", "Domestic", "Division 2", False),
    # Cricket Captain 2025 generic names, resolved by the teams' country
    "6_nov_2027-kar_v_goa_fc_league.txt": ("Ranji Trophy", "First-class", "Domestic", "", False),
    "30_jan_2026-krc_v_kar_fc_league.txt": ("Ranji Trophy", "First-class", "Domestic", "", False),
    "17_feb_2026-guj_v_kar_fc_league_-_sf.txt": ("Ranji Trophy", "First-class", "Domestic", "Semi-final", True),
    "18_jan_2028-kar_v_krc_1_day_cup_-_f.txt": ("Vijay Hazare Trophy", "List A", "Domestic", "Final", True),
    "5_jan_2029-mbc_v_sik_1_day_cup.txt": ("Vijay Hazare Trophy", "List A", "Domestic", "", False),
}


@pytest.mark.parametrize("name,expected", EXPECTED.items(), ids=list(EXPECTED))
def test_classify(name, expected):
    c = classify(load(name))
    assert (c.competition, c.format, c.level, c.stage, c.knockout) == expected
    assert c.recognised


def test_every_sample_is_recognised():
    for path in FIXTURES.glob("*.txt"):
        assert classify(load(path.name)).recognised, path.name


def test_unknown_title_falls_back_to_scorecard_shape():
    m = load("1_aug_2026-brm_v_cdf_hundred.txt")
    m.title = "Some New League"
    c = classify(m)
    assert (c.format, c.recognised) == ("The Hundred", False)
    m = load("24_sep_2026-som_v_sry_county_-_d1.txt")
    m.title = "Tour Match"
    c = classify(m)
    assert (c.format, c.level, c.country) == ("First-class", "Domestic", "England")
    m = load("1_oct_2026-ind_v_wi_1st_odi.txt")
    m.title = "Tri-Series"
    assert (classify(m).format, classify(m).level) == ("ODI", "International")


def test_seasons_follow_the_fixture_calendar():
    items = [
        ("Ranji Trophy", date(2026, 1, 30)), ("Ranji Trophy", date(2026, 2, 17)),
        ("Ranji Trophy", date(2026, 10, 11)), ("Ranji Trophy", date(2026, 11, 6)),
        ("Ranji Trophy", date(2027, 2, 8)),
        ("Indian Premier League", date(2026, 3, 28)), ("Indian Premier League", date(2026, 5, 31)),
        ("Indian Premier League", date(2027, 3, 27)),
    ]
    assert assign_seasons(items) == [
        "2026", "2026", "2026/27", "2026/27", "2026/27", "2026", "2026", "2027"]


def test_series_grouping():
    games = [
        ("Test", "England", "Pakistan", 1, 3, date(2026, 8, 19)),
        ("Test", "England", "Pakistan", 2, 3, date(2026, 8, 27)),
        ("Test", "England", "Pakistan", 3, 3, date(2026, 9, 9)),
        ("Test", "Pakistan", "England", 1, 3, date(2027, 10, 1)),  # the return tour
        ("ODI", "England", "Pakistan", 1, 3, date(2026, 9, 20)),
    ]
    ids = assign_series(games)
    assert ids[0] == ids[1] == ids[2]
    assert len({ids[0], ids[3], ids[4]}) == 3


def test_ipl_eliminator_is_recovered_from_the_bracket():
    games = [
        {"stage": "Qualifier 1", "teams": {"Gujarat Titans", "Punjab Kings"},
         "loser": "Punjab Kings", "date": date(2026, 5, 26)},
        {"stage": "Qualifier 1", "teams": {"Mumbai Indians", "Delhi Capitals"},
         "loser": "Delhi Capitals", "date": date(2026, 5, 27)},
        {"stage": "Qualifier 2", "teams": {"Punjab Kings", "Mumbai Indians"},
         "loser": "Mumbai Indians", "date": date(2026, 5, 29)},
    ]
    fix_playoff_stages(games)
    assert [g["stage"] for g in games] == ["Qualifier 1", "Eliminator", "Qualifier 2"]


def test_home_team_is_first_named_except_at_icc_events():
    assert not classify(load("19_aug_2026-eng_v_pak_1st_tst.txt")).neutral
    assert not classify(load("6_may_2026-hdr_v_pnj_ipl.txt")).neutral
    assert classify(load("23_jun_2027-sl_v_eng_wc_-_f.txt")).neutral
