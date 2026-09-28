"""The stats engine must agree with an independent count taken straight from
the scorecard text by column position - no parser involved."""
import re
from pathlib import Path

import numpy as np
import pytest

from ccstats.loader import Career
from ccstats.stats import Scope, player_tables, rank, stat_definitions

FIXTURES = sorted((Path(__file__).parent / "fixtures").glob("*.txt"))
FORMAT_OF_TITLE = [("Test Match", "Test"), ("World Cup 20", "T20I"), ("20 Over International", "T20I"),
                   ("One Day International", "ODI"), ("World Cup", "ODI"), ("Indian Premier League", "T20"),
                   ("T20 Blast", "T20"), ("The Hundred", "The Hundred"), ("County Championship", "First-class")]


def count_from_text(fmt):
    out = {}
    num = lambda s: 0 if s.strip() in ("", "-") else int(s)
    for f in FIXTURES:
        lines = f.read_text().splitlines()
        if next((v for k, v in FORMAT_OF_TITLE if k in lines[2]), None) != fmt:
            continue
        for i, line in enumerate(lines):
            if re.search(r" - (1st|2nd) Innings\s+R\s+B\s+4s\s+6s", line):
                cR, cB, c4, c6 = line.index(" R ") + 1, line.index(" B ") + 1, line.index("4s"), line.index("6s")
                seen = {}
                for row in lines[i + 2:]:
                    if row.startswith("---"):
                        break
                    name = row[:16].strip()
                    seen[name] = seen.get(name, 0) + 1
                    name = name if seen[name] == 1 else f"{name} ({seen[name]})"
                    p = out.setdefault(name, dict(runs=0, balls=0, fours=0, sixes=0, wickets=0, bballs=0))
                    if len(row.rstrip()) > cR:
                        p["runs"] += num(row[cR:cR + 4]); p["balls"] += num(row[cB:cB + 4])
                        p["fours"] += num(row[c4:c4 + 3]); p["sixes"] += num(row[c6:c6 + 3])
            if re.match(r"^\s+(O|B)\s+(M|D)\s+R\s+W\s+Econ", line):
                for row in lines[i + 2:]:
                    if row.startswith("---"):
                        break
                    t = row[16:].split()
                    p = out.setdefault(row[:16].strip(), dict(runs=0, balls=0, fours=0, sixes=0, wickets=0, bballs=0))
                    ov = t[0].split(".")
                    p["bballs"] += int(t[0]) if line.split()[0] == "B" else int(ov[0]) * 6 + (int(ov[1]) if len(ov) > 1 else 0)
                    p["wickets"] += int(t[3])
    return out


@pytest.fixture(scope="module")
def career():
    return Career.build("t", [(p.name, p.read_bytes()) for p in FIXTURES])


@pytest.mark.parametrize("fmt", ["Test", "ODI", "T20I", "T20", "The Hundred", "First-class"])
def test_engine_matches_the_raw_text(career, fmt):
    # the county check is limited to the County Championship: the CC2025 Ranji
    # files are first-class too, and their "R Patel" is not Surrey's R Patel
    scope = Scope(competitions=["County Championship"]) if fmt == "First-class" else Scope(formats=[fmt])
    bat, bowl, _, _ = player_tables(career, scope)
    expected = count_from_text(fmt)
    b = bat.set_index("player")
    w = bowl.set_index("player")
    for name, e in expected.items():
        if e["balls"] or e["runs"]:
            assert (b.loc[name, "runs"], b.loc[name, "balls"], b.loc[name, "fours"], b.loc[name, "sixes"]) == \
                (e["runs"], e["balls"], e["fours"], e["sixes"]), (fmt, name)
        if e["bballs"]:
            assert (w.loc[name, "balls"], w.loc[name, "wickets"]) == (e["bballs"], e["wickets"]), (fmt, name)


def test_hand_checked_player(career):
    bat, _, _, _ = player_tables(career, Scope(formats=["ODI"]))
    gill = bat.set_index("player").loc["S Gill"]  # 161* and 100 v West Indies, 211* v England
    assert (gill.innings, gill.runs, gill.outs, gill.not_outs, gill.hundreds, gill.high_score_text) == (3, 472, 1, 2, 3, "211*")
    assert gill.average == 472.0


def test_scope_filters_and_team_view(career):
    ipl = Scope(competitions=["Indian Premier League"])
    bat, bowl, fld, base = player_tables(career, ipl)
    assert base.matches == 8 and base.kind == "t20" and base.has_dots
    pbks = Scope(competitions=["Indian Premier League"], team="Punjab Kings", venue="away")
    bat, _, _, base = player_tables(career, pbks)
    assert set(bat.teams) == {"Punjab Kings"} and base.matches == 3


def test_ranking_and_definitions(career):
    bat, bowl, fld, base = player_tables(career, Scope(formats=["Test"]))
    defs = stat_definitions(base)
    assert [s.id for s in defs["bowl"]][4] == "maidens"  # Tests list maidens, not dots
    avg = next(s for s in defs["bat"] if s.id == "average")
    top = rank(bat, avg, best=True, minimum=("balls", 100))
    assert top.average.is_monotonic_decreasing and (top.balls >= 100).all()
    econ = next(s for s in defs["bowl"] if s.id == "economy")
    top = rank(bowl, econ, best=True)
    assert top.economy.is_monotonic_increasing
    # runs above average sums to ~0 across everyone in the selection (by construction, multi-day: runs - outs * avg)
    assert abs(bat.runs_above_average.sum()) < 1e-6


@pytest.mark.parametrize("fmt", ["Test", "ODI", "T20I", "T20", "The Hundred", "First-class"])
def test_every_derived_figure_follows_its_formula(career, fmt):
    bat, bowl, fld, _ = player_tables(career, Scope(formats=[fmt]))
    out = bat[bat.outs > 0]
    assert np.allclose(out.average, out.runs / out.outs)
    assert bat[bat.outs == 0].average.isna().all()  # never dismissed: no average, not "infinite"
    faced = bat[bat.balls > 0]
    assert np.allclose(faced.strike_rate, faced.runs / faced.balls * 100)
    assert (bat.fifties + bat.hundreds == bat.fifty_plus).all()
    assert (bat.innings == bat.outs + bat.not_outs).all()
    assert (bat.boundary_runs == 4 * bat.fours + 6 * bat.sixes).all()
    assert (bat.boundary_runs <= bat.runs).all()
    assert np.allclose(bowl.economy, bowl.runs / bowl.balls * 6)
    took = bowl[bowl.wickets > 0]
    assert np.allclose(took.average, took.runs / took.wickets)
    assert np.allclose(took.strike_rate, took.balls / took.wickets)
    assert bowl[bowl.wickets == 0].average.isna().all()
    assert (fld.dismissals == fld.catches + fld.stumpings).all()
    # best bowling can never beat the bowler's own totals
    best_w = bowl.best.str.split("/").str[0].astype(int)
    assert (best_w <= bowl.wickets).all()


def test_ties_go_to_the_player_who_needed_fewer_balls():
    from pathlib import Path
    from ccstats.loader import Career
    files = sorted((Path(__file__).parent / "fixtures").glob("*.txt"))
    c = Career.build("ties", [(p.name, p.read_bytes()) for p in files])
    bat, bowl, _, base = player_tables(c, Scope(sections=["Indian Premier League"]))
    defs = {s.id: s for s in stat_definitions(base)["bowl"]}
    top = rank(bowl, defs["wickets"], best=True)
    for (_, a), (_, b) in zip(top.iterrows(), top.iloc[1:].iterrows()):
        if a.wickets == b.wickets:
            assert a.balls <= b.balls  # same wickets: fewer balls first
    assert list(top.player[:3]) != ["M Jansen", "K Rabada", "N Sindhu"]  # 7 wkts in 96 balls no longer tops 7 in 66
    worst = rank(bowl, defs["wickets"], best=False)
    for (_, a), (_, b) in zip(worst.iterrows(), worst.iloc[1:].iterrows()):
        if a.wickets == b.wickets:
            assert a.balls >= b.balls
