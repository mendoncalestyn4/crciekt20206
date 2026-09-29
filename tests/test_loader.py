import io
import zipfile
from pathlib import Path

import pytest

from ccstats.loader import Career, Fixes

FIXTURES = sorted((Path(__file__).parent / "fixtures").glob("*.txt"))


def files(paths=FIXTURES):
    return [(p.name, p.read_bytes()) for p in paths]


@pytest.fixture(scope="module")
def career():
    return Career.build("Test career", files())


def test_loads_every_sample(career):
    assert len(career.matches) == len(FIXTURES)
    assert {r.status for r in career.report} == {"loaded"}
    assert career.problems.empty


def test_tables_add_up(career):
    bat = career.batting.groupby(["match_id", "innings_no"]).runs.sum()
    inn = career.innings.set_index(["match_id", "innings_no"])
    assert ((bat.reindex(inn.index) + inn.extras) == inn.runs).all()
    bowl = career.bowling.groupby(["match_id", "innings_no"]).wickets.sum()
    run_outs = career.batting[career.batting.how_out == "run out"].groupby(["match_id", "innings_no"]).size()
    assert (bowl.add(run_outs, fill_value=0).reindex(inn.index) == inn.wickets).all()


def test_duplicates_and_zips_and_bad_files():
    one = FIXTURES[0]
    text = one.read_text()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("Scorecards/a.txt", text)
        zf.writestr("Scorecards/autosave copy.txt", text.replace("\n", "\r\n"))  # same match, other line endings
        zf.writestr("Scorecards/notes.txt", "shopping list: milk, eggs")
        zf.writestr("Scorecards/picture.png", b"\x89PNG")
    c = Career.build("x", [("save.zip", buf.getvalue())])
    status = {r.source.split("/")[-1]: r.status for r in c.report}
    assert status == {"a.txt": "loaded", "autosave copy.txt": "duplicate", "notes.txt": "failed", "picture.png": "skipped"}
    assert len(c.matches) == 1


def test_adding_files_keeps_existing_matches(career):
    more = career.add_files(files(FIXTURES[:3]))  # already loaded -> all duplicates
    assert len(more.matches) == len(career.matches)
    assert {r.status for r in more.report} == {"duplicate"}


def test_career_pack_round_trip(career):
    fixes = Fixes(merges={"Q DKock": "Q de Kock"})
    c = career.with_fixes(fixes)
    back = Career.from_pack(c.to_pack())
    assert back.name == "Test career"
    assert len(back.matches) == len(career.matches)
    assert back.fixes.merges == {"Q DKock": "Q de Kock"}
    assert "Q de Kock" in set(back.batting.player) and "Q DKock" not in set(back.batting.player)


def test_manual_fixes_are_applied(career):
    # split: the A Sharma who plays for Northamptonshire is a different player
    fixes = Fixes(splits=[{"player": "A Sharma", "team": "Northamptonshire", "new_name": "A Sharma (Northants)"}])
    c = career.with_fixes(fixes)
    teams = c.batting[c.batting.player == "A Sharma (Northants)"].team.unique().tolist()
    assert teams == ["Northamptonshire"]
    assert "Northamptonshire" not in set(c.batting[c.batting.player == "A Sharma"].team)
    # credit: an ambiguous catch ("c Khan" with two Khans) credited by hand
    open_ = career.fielding[~career.fielding.resolved].iloc[0]
    c = career.with_fixes(Fixes(credits={open_.credit_key: "S Khan"}))
    row = c.fielding[c.fielding.credit_key == open_.credit_key].iloc[0]
    assert row.resolved and row.player == "S Khan"


def test_results_and_declarations(career):
    m = career.matches.set_index("source")
    sf = m.loc["17_feb_2026-guj_v_kar_fc_league_-_sf.txt"]
    assert (sf.result_type, sf.winner, sf.tiebreak_winner) == ("draw", "", "Karnataka")
    final = m.loc["31_may_2026-gjt_v_pnj_ipl_-_f.txt"]
    assert (final.winner, final.loser, final.stage) == ("Gujarat Titans", "Punjab Kings", "Final")
    elim = m.loc["27_may_2026-mmb_v_del_ipl_-_q1.txt"]
    assert elim.stage == "Eliminator"
    durham = career.innings.merge(career.matches[["match_id", "source"]])
    durham = durham[(durham.source == "8_sep_2026-drh_v_mid_county_-_d2.txt")].set_index("innings_no")
    assert durham.loc[3, "declared"] and not durham.loc[4, "declared"]


def test_every_competition_is_its_own_section(career):
    # international matches are pooled by format; everything else is its own section
    sections = career.matches.groupby("section").size().to_dict()
    assert sections == {
        "County Championship · Division 1": 3, "County Championship · Division 2": 2,
        "Indian Premier League": 8, "ODIs": 11, "Ranji Trophy": 5,
        "T20 Blast": 10, "T20Is": 4, "Tests": 6,
        "The Hundred": 4, "Vijay Hazare Trophy": 3}
    # ... while each competition keeps its own table, bracket and champion
    events = career.matches.groupby("event").size().to_dict()
    assert events == {
        "County Championship · Division 1": 3, "County Championship · Division 2": 2,
        "Indian Premier League": 8, "ODI World Cup": 4, "ODIs (bilateral series)": 7, "Ranji Trophy": 5,
        "T20 Blast": 10, "T20 World Cup": 1, "T20Is (bilateral series)": 3, "Tests (bilateral series)": 6,
        "The Hundred": 4, "Vijay Hazare Trophy": 3}
