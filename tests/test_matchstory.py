"""A match and a series told in a line (ccstats/matchstory.py): the player of the match headline on the new site's
match summary, and the story of a series. Every line here was read against the scorecard it comes from."""

import dataclasses
from pathlib import Path

import pytest

from ccstats import matchstory as MS
from ccstats.loader import Career

FIXTURES = sorted((Path(__file__).parent / "fixtures").glob("*.txt"))
NEW = Path(__file__).parent / "fixtures_2026" / "new_playthrough.zip"


@pytest.fixture(scope="module")
def career():
    return Career.build("x", [(p.name, p.read_bytes()) for p in FIXTURES])


@pytest.fixture(scope="module")
def season():
    """44 IPL games and a Bangladesh v New Zealand tour."""
    return Career.build("2026", [(NEW.name, NEW.read_bytes())])


def mid(c, name):
    return c.matches.set_index("source").match_id[next(s for s in c.matches.source if s.endswith(name))]


def series(c, sid):
    return list(c.matches[c.matches.series_id == sid].match_id)


@pytest.mark.parametrize("name, line", [
    # won batting first: the runs or the wickets that did it, 'an' before an 8, 11 or 18
    ("11_mar_2026-aus_v_ind_wc20_-_f.txt", "J Bumrah's 3 for 6 bowls India to a 34-run win"),
    ("1_oct_2026-rsa_v_aus_1st_odi.txt", "W Mulder's 4 for 47 bowls South Africa to an 80-run win"),
    ("16_jul_2026-eng_v_ind_2nd_odi.txt", "S Gill's unbeaten 211 sets up India's 127-run win"),
    # won chasing: what was left, exactly (13 balls is never '2 overs'); the Hundred counts balls
    ("15_jul_2026-drh_v_knt_blast_-_qf.txt", "Z Crawley's unbeaten 91 takes Kent home with 2 balls to spare"),
    ("7_may_2026-lkn_v_bgl_ipl.txt", "M Breetzke's 56 takes Lucknow Super Giants home with 13 balls to spare"),
    ("1_oct_2026-ind_v_wi_1st_odi.txt", "S Gill's unbeaten 161 takes India home with more than 12 overs to spare"),
    ("11_jun_2027-eng_v_nz_wc_-_group.txt", "H Brook's unbeaten 103 takes England home with 1 over to spare"),
    ("1_aug_2026-brm_v_cdf_hundred.txt", "J Cox's 43 takes Welsh Fire home with 8 balls to spare"),
    ("17_jul_2026-nht_v_knt_blast_-_sf.txt", "C Harrison's 4 for 25 sets up Northamptonshire's 5-wicket win"),
    # two innings: both scores, never added up, and the verb agrees
    ("27_aug_2026-eng_v_pak_2nd_tst.txt", "O Pope's 91 and 60* take England home by 8 wickets"),
    ("11_oct_2027-kar_v_chd_fc_league.txt", "L Rahul's 107 and 86 take Karnataka home by 6 wickets"),
    ("8_sep_2026-dby_v_knt_county_-_d2.txt", "Z Crawley's 65 and 139 set up Kent's 19-run win"),
    ("22_aug_2026-aus_v_ban_2nd_tst.txt", "M Starc's 7 for 140 sets up Australia's 6-wicket win"),
    # all-rounders
    ("19_aug_2026-eng_v_pak_1st_tst.txt",
     "G Atkinson does it all: 21 and 30 with the bat, 7 for 95 with the ball, as England win by 299 runs"),
    ("9_oct_2026-rsa_v_aus_1st_tst.txt", "W Mulder does it all: 114 and 5 for 53 as South Africa get home by 7 wickets"),
    ("18_jul_2026-som_v_nht_blast_-_f.txt", "T Lammonby does it all: 76* and 2 for 1 as Somerset win by 67 runs"),
    ("13_jun_2027-rsa_v_eng_wc_-_group.txt", "B Fortuin does it all: 32 and 4 for 52 but England win"),
    # no winner
    ("8_sep_2026-drh_v_mid_county_-_d2.txt", "G Clark's 57 and 113 in a drawn match"),
    ("16_may_2026-ban_v_pak_2nd_tst.txt", "A Salman's 150* and 73 in a drawn match"),
])
def test_player_of_the_match_headlines(career, name, line):
    assert MS.pom_headline(career, mid(career, name)) == line


def test_a_rain_cut_chase_and_a_last_ball_win_say_the_margin(season):
    """When rain cut the chase, or it was won off the last ball, there's nothing to spare: the wickets say it."""
    assert MS.pom_headline(season, mid(season, "18 apr 2026-bgl v del (ipl).txt")) == \
        "V Iyer's 76 takes Royal Challengers Bengaluru home by 5 wickets"
    assert MS.pom_headline(season, mid(season, "26 apr 2026-gjt v chn (ipl).txt")) == \
        "S Sudharsan's 43 takes Gujarat Titans home by 1 wicket"


def test_every_match_gets_a_headline_that_names_the_player(career, season):
    for c in (career, season):
        for r in c.matches.itertuples():
            line = MS.pom_headline(c, r.match_id)
            assert line.startswith(r.player_of_match) and "  " not in line and not line.endswith(" "), line
            assert " a 8" not in line and " a 11-" not in line and " a 18-" not in line, line


def test_a_player_of_the_match_the_scorecards_cant_place(career):
    """No player of the match: no headline. One the scorecards don't have: just who it was and who won."""
    m = career.matches
    one = mid(career, "11_mar_2026-aus_v_ind_wc20_-_f.txt")
    nobody = dataclasses.replace(career, matches=m.assign(player_of_match=m.player_of_match.where(m.match_id != one, "")))
    assert MS.pom_headline(nobody, one) == ""
    stranger = dataclasses.replace(career, matches=m.assign(
        player_of_match=m.player_of_match.where(m.match_id != one, "Z Nobody")))
    assert MS.pom_headline(stranger, one) == "Z Nobody is player of the match as India win"


def test_figures_keep_two_innings_apart(career):
    f = MS.figures(career, mid(career, "27_aug_2026-eng_v_pak_2nd_tst.txt"), "O Pope")
    assert f["bat"]["text"] == "91 & 60*" and f["bat"]["runs"] == 151 and f["bat"]["innings"] == 2
    assert not f["bat"]["notout"]   # unbeaten only when there was one innings
    f = MS.figures(career, mid(career, "11_mar_2026-aus_v_ind_wc20_-_f.txt"), "J Bumrah")
    assert f["bowl"] == dict(wickets=3, runs=6, balls=f["bowl"]["balls"], text="3/6")
    assert MS.team_of(career, mid(career, "11_mar_2026-aus_v_ind_wc20_-_f.txt"), "J Bumrah") == "India"
    assert MS.overs_text(51) == "8.3" and MS.overs_text(120) == "20"


def test_a_series_story_from_each_side(career, season):
    s = MS.series_story(career, series(career, "Test-7"), "England")
    assert s["headline"] == "England sweep Pakistan 3–0" and s["complete"] and s["results"] == ["W", "W", "W"]
    assert s["deck"] == ("England won all three. J Bethell made the most runs (254), "
                         "G Atkinson took the most wickets (18).")
    assert s["player_of_series"]["player"] == "G Atkinson"
    assert MS.series_story(career, series(career, "Test-7"), "Pakistan")["headline"] == "England take the series 3–0"

    s = MS.series_story(season, series(season, "ODI-1"), "New Zealand")
    assert s["headline"] == "New Zealand win the decider to take the series 2–1"
    assert s["deck"] == ("New Zealand lost the first and won the last two. H Nicholls' 77 won the decider. "
                         "H Nicholls made the most runs (234), M Rahman and N Smith took the most wickets (8).")
    assert MS.series_story(season, series(season, "ODI-1"), "Bangladesh")["headline"] == "New Zealand take the series 2–1"

    s = MS.series_story(season, series(season, "T20I-2"), "New Zealand")
    assert s["flow"] == "won the first, lost the next and won the decider"
    assert s["player_of_series"]["player"] == "L Ferguson" and s["player_of_series"]["wickets"] == 10


def test_a_series_still_going_says_who_leads(career):
    s = MS.series_story(career, series(career, "ODI-9"), "India")   # the third match isn't in the career
    assert s["headline"] == "India lead West Indies 2–0" and not s["complete"]
    assert s["flow"] == "won the first two"
    assert MS.series_story(career, series(career, "T20I-10"), "Sri Lanka")["headline"] == "Pakistan lead Sri Lanka 2–0"
    assert MS.series_story(career, series(career, "Test-2"), "Bangladesh")["headline"] == \
        "Bangladesh and Pakistan level at 0–0"


def test_a_series_story_needs_one_series_your_team_played(career):
    with pytest.raises(ValueError):
        MS.series_story(career, series(career, "Test-7"), "India")
    with pytest.raises(ValueError):
        MS.series_story(career, series(career, "ODI-9") + series(career, "ODI-5"), "India")
    with pytest.raises(ValueError):
        MS.series_story(career, [], "India")
