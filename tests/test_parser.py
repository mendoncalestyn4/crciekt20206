from pathlib import Path

import pytest

from ccstats.parser import parse_dismissal, parse_scorecard, resolve_candidates, resolve_name

FIXTURES = sorted((Path(__file__).parent / "fixtures").glob("*.txt"))


def load(name: str):
    path = Path(__file__).parent / "fixtures" / name
    return parse_scorecard(path.read_text(), path.name)


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.name)
def test_every_innings_reconciles(path):
    """Batting + extras, bowling figures, wickets and FOW must all agree
    with the TOTAL line for every innings of every real scorecard."""
    m = parse_scorecard(path.read_text(), path.name)
    assert m.team1 and m.team2 and m.date and m.title and m.result_type
    for inn in m.innings:
        assert len(inn.batting) == 11
        assert sum(b.runs for b in inn.batting) + inn.extras == inn.total
        assert sum(b.did_bat and not b.not_out for b in inn.batting) == inn.wickets
        assert sum(b.runs for b in inn.bowling) + inn.byes + inn.leg_byes == inn.total
        run_outs = sum(b.how_out == "run out" for b in inn.batting)
        assert sum(b.wickets for b in inn.bowling) + run_outs == inn.wickets
        assert sum(b.balls for b in inn.bowling) == inn.balls
        assert len(inn.fow) == inn.wickets
        # every dismissal is credited to a bowler on the card, unless the
        # surname is genuinely ambiguous (T Curran and S Curran both bowling)
        bowlers = [b.player for b in inn.bowling]
        for b in inn.batting:
            if b.bowler and b.bowler not in bowlers:
                assert len(resolve_candidates(b.bowler, bowlers)) > 1, b.bowler


def test_odi_header_and_result():
    m = load("1_oct_2026-ind_v_wi_1st_odi.txt")
    assert (m.team1, m.team2) == ("India", "West Indies")
    assert m.title == "1st One Day International (of 3)"
    assert (m.series_match_no, m.series_length) == (1, 3)
    assert str(m.date) == "2026-10-01"
    assert (m.winner, m.margin_wickets, m.player_of_match) == ("India", 7, "S Gill")
    wi, ind = m.innings
    assert (wi.team, wi.bowling_team, wi.total, wi.wickets, wi.balls) == (
        "West Indies", "India", 255, 10, 49 * 6 + 2)
    gill = ind.batting[0]
    assert (gill.player, gill.runs, gill.balls, gill.fours, gill.sixes, gill.not_out) == (
        "S Gill", 161, 121, 22, 4, True)
    assert [b.player for b in ind.batting if not b.did_bat] == [
        "R Gaikwad", "H Pandya", "N Kumar Reddy", "A Patel", "K Yadav", "A Singh"]
    # "b Joseph" with both S Joseph (0 wkts) and A Joseph (2 wkts) bowling
    assert ind.batting[1].bowler == "A Joseph"
    # abbreviated surname "K'r Reddy"
    assert wi.batting[3].bowler == "N Kumar Reddy"
    assert (wi.no_balls, wi.extras) == (2, 2)


def test_t20_bowling_has_dots_not_maidens():
    m = load("1_oct_2026-pak_v_sl_1st_20_over_int.txt")
    afridi = m.innings[1].bowling[0]
    assert (afridi.player, afridi.balls, afridi.dots, afridi.maidens, afridi.wickets) == (
        "A Afridi", 19, 13, None, 3)


def test_ipl_and_county_titles():
    assert load("6_may_2026-hdr_v_pnj_ipl.txt").title == "Indian Premier League"
    m = load("8_sep_2026-drh_v_mid_county_-_d2.txt")
    assert m.title == "County Championship - D2"
    assert m.result_type == "draw" and not m.winner
    assert [i.team_innings for i in m.innings] == [1, 1, 2, 2]


def test_retired_hurt_and_stumping():
    m = load("8_sep_2026-lcs_v_som_county_-_d1.txt")
    scriven = next(b for b in m.innings[3].batting if b.player == "T Scriven")
    assert scriven.how_out == "retired hurt" and scriven.not_out
    assert m.innings[1].batting and any(
        b.bowler == "L Goldsworthy" for b in m.innings[1].batting)
    m = load("24_sep_2026-som_v_sry_county_-_d1.txt")
    foakes = next(b for b in m.innings[2].batting if b.player == "B Foakes")
    assert (foakes.how_out, foakes.fielder, foakes.bowler) == ("stumped", "Rew", "J Leach")


@pytest.mark.parametrize("text,how,bowler,fielder", [
    ("c Kohli b Pandya", "caught", "Pandya", "Kohli"),
    ("c & b Motie", "caught", "Motie", "Motie"),
    ("lbw b Yadav", "lbw", "Yadav", ""),
    ("b Hosein", "bowled", "Hosein", ""),
    ("st Sharma b Pandya", "stumped", "Pandya", "Sharma"),
    ("run out", "run out", "", ""),
    ("not out", "not out", "", ""),
    ("rtrd ht", "retired hurt", "", ""),
    ("", "dnb", "", ""),
])
def test_dismissals(text, how, bowler, fielder):
    d = parse_dismissal(text)
    assert (d["how_out"], d["bowler"], d["fielder"]) == (how, bowler, fielder)


def test_resolve_name():
    xi = ["S Khan", "U Khan", "N Kumar Reddy", "T Kohler-Cadmore", "L Goldsworthy"]
    assert resolve_name("Khan", xi) == ""  # ambiguous
    assert resolve_name("K'r Reddy", xi) == "N Kumar Reddy"
    assert resolve_name("K'Cadmore", xi) == "T Kohler-Cadmore"
    assert resolve_name("G'sworthy", xi) == "L Goldsworthy"


def test_blast_titles_and_duplicate_names_in_one_xi():
    m = load("3_jul_2026-yrk_v_drh_blast_-_n.txt")
    assert m.title == "T20 Blast - North"
    m = load("3_jul_2026-wrc_v_knt_blast_-_group.txt")
    assert m.title == "T20 Blast - Group Match"
    # Kent field two different players both printed as "J Denly"
    kent = m.innings[0]
    assert [b.position for b in kent.batting if b.player == "J Denly"] == [5, 7]


def test_particle_and_abbreviated_surnames():
    m = load("10_jul_2026-wrk_v_glm_blast_-_s.txt")
    assert {b.bowler for b in m.innings[1].batting if b.bowler} >= {"T v' Gugten", "N McAndrew"}
    m = load("3_jul_2026-yrk_v_drh_blast_-_n.txt")
    assert m.innings[0].batting[2].bowler == "L van Beek"


def test_hundred_uses_balls_not_overs():
    m = load("1_aug_2026-brm_v_cdf_hundred.txt")
    assert m.title == "The Hundred"
    phoenix, fire = m.innings
    assert (phoenix.total, phoenix.wickets, phoenix.balls) == (150, 6, 100)
    assert (fire.total, fire.balls) == (153, 92)
    ahmed = fire.bowling[-1]
    assert (ahmed.player, ahmed.balls, ahmed.dots, ahmed.runs) == ("R Ahmed", 12, 3, 19)


@pytest.mark.parametrize("name,title", [
    ("15_jul_2026-drh_v_knt_blast_-_qf.txt", "T20 Blast - Qtr-Final"),
    ("17_jul_2026-nht_v_knt_blast_-_sf.txt", "T20 Blast - Semi-Final"),
    ("18_jul_2026-som_v_nht_blast_-_f.txt", "T20 Blast - Final"),
])
def test_knockout_titles(name, title):
    assert load(name).title == title
