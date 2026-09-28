"""Players whose names have more than one part (de Kock, van der Dussen,
de Lange) or that the game shortens (DKock, H' Shanto, v' Gugten) must end up
under one name for batting, bowling and fielding alike."""
from pathlib import Path

import pytest

from ccstats.parser import parse_scorecard

FIXTURES = Path(__file__).parent / "fixtures"

SYNTHETIC = """\
************************************************************
South Africa v India
1st Test Match (of 2) - 3 Jan 2027
************************************************************

India - 1st Innings                       R    B    4s  6s
------------------------------------------------------------
Y Jaiswal       st de Kock b Maharaj      41   60   5   -
S Gill          c de Kock b Rabada        12   20   2   -
V Kohli         c van der Dussen b de Lange 70  101  8   1
S Iyer          lbw b de Lange            3    9    -   -
R Pant          c & b de Lange            0    2    -   -
R Jadeja        c du Plessis b Maharaj    22   40   3   -
W Sundar        st de Kock b Maharaj      9    15   1   -
K Yadav         run out                   4    6    1   -
J Bumrah        c de Lange b Rabada       1    3    -   -
M Siraj         not out                   0    1    -   -
A Singh         b Rabada                  0    1    -   -
------------------------------------------------------------
Extras: (nb2)                             2
TOTAL: (all out, 43 overs)                164

************************************************************

                O      M     R      W     Econ
------------------------------------------------------------
K Rabada        14     2     50     3     3.57
M de Lange      12     1     57     3     4.75
K Maharaj       17     3     57     3     3.35
------------------------------------------------------------
Fall of Wickets:
1-30  2-60  3-70  4-72  5-120  
6-140  7-150  8-158  9-164  10-164

************************************************************
************************************************************

South Africa - 1st Innings                R    B    4s  6s
------------------------------------------------------------
A Markram       c Pant b Bumrah           10   20   1   -
Q de Kock       c Jadeja b Bumrah         55   70   7   1
R van der Dussen not out                  60   90   6   -
F du Plessis    not out                   40   52   5   -
T Bavuma        
M de Lange      
K Maharaj       
K Rabada        
L Ngidi         
T Stubbs        
D Brevis        
------------------------------------------------------------
Extras:                                   0
TOTAL: (2 wkts, 38.4 overs)               165

************************************************************

                O      M     R      W     Econ
------------------------------------------------------------
J Bumrah        14     3     50     2     3.57
M Siraj         12     1     60     0     5.00
R Jadeja        12.4   0     55     0     4.34
------------------------------------------------------------
Fall of Wickets:
1-20  2-90  

************************************************************
South Africa won by 8 wickets
Man of the match: M de Lange
************************************************************
"""


def load(name):
    return parse_scorecard((FIXTURES / name).read_text(), name)


def test_particle_names_are_one_player_everywhere():
    m = parse_scorecard(SYNTHETIC, "synthetic")
    india, sa = m.innings
    sa_names = {b.player for b in sa.batting}
    assert {"Q de Kock", "R van der Dussen", "F du Plessis", "M de Lange"} <= sa_names
    by = {b.player: b for b in india.batting}
    # stumpings and catches go to the keeper's own batting name
    assert (by["Y Jaiswal"].how_out, by["Y Jaiswal"].fielder) == ("stumped", "Q de Kock")
    assert by["W Sundar"].fielder == "Q de Kock"
    assert by["S Gill"].fielder == "Q de Kock"
    assert by["V Kohli"].fielder == "R van der Dussen"
    assert by["R Jadeja"].fielder == "F du Plessis"
    assert by["J Bumrah"].fielder == "M de Lange"
    # wickets go to the bowler's own bowling name
    assert {by[p].bowler for p in ("V Kohli", "S Iyer", "R Pant")} == {"M de Lange"}
    assert by["R Pant"].fielder == "M de Lange"  # c & b
    # every credited fielder is a real member of the fielding XI
    for b in india.batting:
        if b.fielder:
            assert b.fielder_resolved and b.fielder in sa_names


@pytest.mark.parametrize("name,batter,fielder", [
    ("1_oct_2026-rsa_v_aus_1st_odi.txt", "M Renshaw", "Q DKock"),          # c DKock
    ("22_aug_2026-aus_v_ban_2nd_tst.txt", "M Labuschagne", "N H' Shanto"),  # c H' Shanto
    ("3_jul_2026-yrk_v_drh_blast_-_n.txt", "G Clark", "L van Beek"),        # c van Beek
    ("24_sep_2026-som_v_sry_county_-_d1.txt", "B Foakes", "J Rew"),         # st Rew
    ("4_jul_2026-glc_v_sry_blast_-_group.txt", "J Roy", "J Taylor"),        # c Taylor b Taylor
    ("11_mar_2026-aus_v_ind_wc20_-_f.txt", "C Connolly", "R Singh"),        # c Singh b Singh
])
def test_real_fielders_resolve_to_their_own_names(name, batter, fielder):
    m = load(name)
    hit = [b for i in m.innings for b in i.batting if b.player == batter and b.fielder == fielder]
    assert hit and hit[0].fielder_resolved


def test_resolved_fielders_always_belong_to_the_fielding_xi():
    unresolved = []
    for path in FIXTURES.glob("*.txt"):
        m = load(path.name)
        squads = {}
        for inn in m.innings:
            squads.setdefault(inn.team, set()).update(b.player for b in inn.batting)
        for inn in m.innings:
            for b in inn.batting:
                if b.fielder and b.fielder_resolved:
                    assert b.fielder in squads[inn.bowling_team], (path.name, b.dismissal)
                elif b.fielder:
                    unresolved.append((path.name, b.dismissal))
    # only genuinely ambiguous surnames are left (two Khans, two Singhs, ...)
    assert len(unresolved) < 40, unresolved
