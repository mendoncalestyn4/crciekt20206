import re
from pathlib import Path

import pytest

from ccstats.loader import Career
from ccstats.parser import parse_dismissal, parse_scorecard, resolve_candidates, resolve_name, validate_match

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
    assert (foakes.how_out, foakes.fielder, foakes.bowler) == ("stumped", "J Rew", "J Leach")


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


def test_test_match_title_and_series():
    m = load("9_sep_2026-eng_v_pak_3rd_tst.txt")
    assert m.title == "3rd Test Match (of 3)"
    assert (m.series_match_no, m.series_length) == (3, 3)
    assert len(m.innings) == 4 and [i.team_innings for i in m.innings] == [1, 1, 2, 2]
    # "b Islam" with T Islam (3 wkts) and S Islam (0 wkts) both bowling
    m = load("22_aug_2026-aus_v_ban_2nd_tst.txt")
    assert {b.bowler for b in m.innings[1].batting if b.bowler.endswith("Islam")} == {"T Islam"}


def test_ipl_playoff_titles():
    # The game labels the Eliminator "Qualifier 1" as well, so playoff
    # stages must later be worked out from the bracket, not the label alone.
    q1 = load("26_may_2026-gjt_v_pnj_ipl_-_q1.txt")
    elim = load("27_may_2026-mmb_v_del_ipl_-_q1.txt")
    assert q1.title == elim.title == "Indian Premier League - Qualifier 1"
    assert load("29_may_2026-pnj_v_mmb_ipl_-_q2.txt").title == "Indian Premier League - Qualifier 2"
    final = load("31_may_2026-gjt_v_pnj_ipl_-_f.txt")
    assert (final.title, final.winner) == ("Indian Premier League - Final", "Gujarat Titans")


def test_cc2025_fc_league_byes_and_tiebreak_result():
    m = load("6_nov_2027-kar_v_goa_fc_league.txt")
    assert m.title == "FC League"
    kar2 = m.innings[2]
    assert (kar2.byes, kar2.leg_byes, kar2.no_balls, kar2.extras) == (8, 7, 3, 18)
    # drawn knockout decided by the game's tiebreak - no margin given
    m = load("17_feb_2026-guj_v_kar_fc_league_-_sf.txt")
    assert m.title == "FC League - Semi-Final"
    assert (m.result, m.winner) == ("Karnataka won on more wickets left", "Karnataka")
    assert m.margin_runs is None and m.margin_wickets is None


@pytest.mark.parametrize("name,title", [
    ("18_jan_2028-kar_v_krc_1_day_cup_-_f.txt", "One Day Cup - Final"),
    ("5_jan_2029-mbc_v_sik_1_day_cup.txt", "One Day Cup"),
    ("13_jun_2027-rsa_v_eng_wc_-_group.txt", "World Cup - Group Match"),
    ("23_jun_2027-sl_v_eng_wc_-_f.txt", "World Cup - Final"),
    ("11_mar_2026-aus_v_ind_wc20_-_f.txt", "World Cup 20 - Final"),
])
def test_one_day_cup_and_world_cup_titles(name, title):
    assert load(name).title == title


def _long_name(text: str, old: str, new: str) -> str:
    """The card as the game would print it for a side called `new`: the innings heading padded to 42 characters
    before the batting columns, with no gap at all once the name is too long for that."""
    out = []
    for line in text.split("\n"):
        h = re.match(r"^(.*?)\s*(R\s+B\s+4s\s+6s)\s*$", line)
        out.append(h.group(1).replace(old, new).ljust(42) + h.group(2) if h and old in h.group(1)
                   else line.replace(old, new))
    return "\n".join(out)


@pytest.mark.parametrize("card,old", [("fixtures_super/20_sep_2026-zim_v_aus_3rd_odi.txt", "Zimbabwe"),
                                      ("fixtures/19_aug_2026-eng_v_pak_1st_tst.txt", "England")])
def test_a_side_with_a_long_name_is_read_in_full(card, old):
    """In a real save, every innings of Trinidad and Tobago Red Force was lost: "Trinidad and Tobago Red Force - 1st
    InningsR    B    4s  6s" has no gap before the columns. The same card with a long name must read exactly the same:
    every innings and super over, every batter and bowler, every total."""
    new = "Trinidad and Tobago Red Force"
    text = (Path(__file__).parent / card).read_text()
    long = _long_name(text, old, new)
    assert "InningsR" in long
    a, b = parse_scorecard(text, "a.txt"), parse_scorecard(long, "b.txt")

    def figures(m, name):
        rename = lambda t: new if t == name else t   # noqa: E731
        inns = lambda xs: [(rename(i.team), rename(i.bowling_team), i.total, i.wickets, i.balls, i.extras, i.fow,   # noqa: E731
                            [(x.player, x.runs, x.balls, x.how_out, x.bowler) for x in i.batting],
                            [(x.player, x.balls, x.runs, x.wickets) for x in i.bowling]) for i in xs]
        return (rename(m.team1), rename(m.team2), rename(m.winner), m.result_type, inns(m.innings), inns(m.super_overs))

    assert len(b.innings) == len(a.innings) >= 2
    assert figures(a, old) == figures(b, new)


# --------------------------------------------------------------------------- scorecards that don't add up (14 Nov)
IPL_CARD = Path(__file__).parent / "fixtures" / "16_may_2026-klk_v_gjt_ipl.txt"


def _card(*swaps: tuple[str, str]) -> str:
    text = IPL_CARD.read_text()
    for old, new in swaps:
        assert text.count(old) == 1, old
        text = text.replace(old, new)
    return text


def test_a_batter_reprinted_retired_hurt_is_counted_out_to_the_bowler_the_card_proves():
    """Four of your scorecards (14 November): a batter printed "retired hurt" though the total, the fall of wickets
    and the bowlers' figures all count him out, and exactly one bowler (here R Ravindra, 3 wickets) has one wicket
    more than the batting card credits him with. He counts out to that bowler, how not printed; the card adds up."""
    text = _card(("K Kushagra      lbw b Ravindra            6", "K Kushagra      retired hurt              6"))
    m = parse_scorecard(text, "x.txt")
    k = next(b for b in m.innings[0].batting if b.player == "K Kushagra")
    assert (k.not_out, k.how_out, k.bowler, k.dismissal) == (False, "out, how not printed", "R Ravindra", "retired hurt")
    assert validate_match(m) == [] and len(m.corrections) == 1
    assert "K Kushagra is printed retired hurt" in m.corrections[0] and "counted out to R Ravindra" in m.corrections[0]
    # in the career: out, the wicket the bowler's own figures already had, listed as corrected, not as a problem
    c = Career.build("c", [("x.txt", text.encode())])
    b = c.batting.set_index("player").loc["K Kushagra"]
    assert bool(b.out) and b.bowler == "R Ravindra" and c.problems.empty
    assert list(c.corrections.correction) == m.corrections
    assert c.bowling.set_index("player").wickets["R Ravindra"] == 3


def test_a_real_retired_hurt_is_left_alone():
    """A genuine retired hurt (the total and the bowlers count him not out) stays not out, and two batters printed
    retired hurt in an innings that's a wicket short can't say which one was out: nothing is changed, the card stays
    on the problems list."""
    m = parse_scorecard(_card(("J Holder        not out ", "J Holder        retired hurt")), "x.txt")
    j = next(b for b in m.innings[0].batting if b.player == "J Holder")
    assert j.not_out and j.how_out == "retired hurt" and m.corrections == [] and validate_match(m) == []
    two = parse_scorecard(_card(("K Kushagra      lbw b Ravindra            6", "K Kushagra      retired hurt              6"),
                                ("J Holder        not out ", "J Holder        retired hurt")), "x.txt")
    assert two.corrections == [] and any("dismissals do not match" in p for p in validate_match(two))


def test_no_balls_left_off_every_bowler_are_recorded_as_not_charged():
    """Your SA20 scorecard (14 November): the bowlers' runs fell short of the total by exactly the innings' no-balls.
    They're recorded as no-balls not charged to any bowler, so the card adds up; every bowler stays as printed."""
    text = _card(("Extras: (nb1,w1)                          2\nTOTAL: (all out, 17.3 overs)              73",
                  "Extras: (nb2,w1)                          3\nTOTAL: (all out, 17.3 overs)              74"),
                 ("K Rabada        4      14    16", "K Rabada        4      14    15"),
                 ("10-73", "10-74"), ("won by 132 runs", "won by 131 runs"))
    m = parse_scorecard(text, "x.txt")
    inn = m.innings[1]
    assert (inn.uncharged, inn.uncharged_kind) == (2, "no-ball") and validate_match(m) == []
    assert "Recorded as 2 no-ball runs not charged to any bowler" in m.corrections[0]
    c = Career.build("c", [("x.txt", text.encode())])
    assert c.innings.set_index("innings_no").uncharged.tolist() == [0, 2] and c.problems.empty
    assert c.bowling.set_index("player").runs["K Rabada"] == 15
    # short by an amount that is neither the no-balls nor the wides: not put right, still a problem
    off = parse_scorecard(_card(("K Rabada        4      14    16", "K Rabada        4      14    13")), "x.txt")
    assert off.innings[1].uncharged == 0 and any("bowling runs" in p for p in validate_match(off))
