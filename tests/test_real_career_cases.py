"""Cases found in a real 477-match career: games left over from a replayed season,
re-saved files, one-off internationals, the Blast's cross-group games and The
Hundred's eliminator."""

import io
import json
import os
import shutil
import time
import zipfile
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

from ccstats import checks
from ccstats import tables as T
from ccstats.loader import PACK_SOURCES, PACK_TIMES, Career, Fixes, _leaf
from ccstats.local import CareerStore, Watcher

ROOT = Path(__file__).parent.parent
FIX = Path(__file__).parent / "fixtures"
IPL = sorted(p for p in FIX.glob("*.txt") if "_ipl" in p.name)
FINAL = FIX / "31_may_2026-gjt_v_pnj_ipl_-_f.txt"


def old_final() -> tuple[str, bytes]:
    """The final of an earlier playthrough: other teams qualified, so the game
    saved it under another name and never overwrote it."""
    text = FINAL.read_text().replace("Punjab Kings", "Mumbai Indians")
    return "31_may_2026-gjt_v_mmb_ipl_-_f.txt", text.encode()


def ipl_files(t_old: float, t_new: float):
    """(name, bytes, saved time): this playthrough's games saved at t_new, the old final at t_old."""
    return [(p.name, p.read_bytes(), t_new) for p in IPL] + [(*old_final(), t_old)]


def test_a_final_from_an_earlier_playthrough_is_left_out():
    now = time.time()
    c = Career.build("replay", ipl_files(now - 86400, now))
    assert len(c.leftovers) == 1 and c.leftovers.auto.all()
    assert c.leftovers.away.iloc[0] == "Mumbai Indians" and "earlier playthrough" in c.leftovers.reason.iloc[0]
    finals = c.matches[c.matches.stage == "Final"]
    assert list(finals.away) == ["Punjab Kings"]  # only this playthrough's final counts
    assert len(c.matches) == len(IPL)
    ko = T.knockouts(c, c.matches.match_id)
    assert list(ko.stage) == ["Qualifier 1", "Eliminator", "Qualifier 2", "Final"]
    # the leftover's players aren't counted anywhere
    assert not c.batting.match_id.isin(c.leftovers.match_id).any()


def test_without_file_times_nothing_is_guessed_but_the_clash_is_shown():
    c = Career.build("no times", [(p.name, p.read_bytes()) for p in IPL] + [old_final()])
    assert c.leftovers.empty and (c.matches.stage == "Final").sum() == 2
    clash = checks.replay_conflicts(c)
    assert set(clash[clash.stage == "Final"].away) == {"Punjab Kings", "Mumbai Indians"}
    # leaving one out by hand
    old = c.matches[(c.matches.stage == "Final") & (c.matches.away == "Mumbai Indians")].match_id.iloc[0]
    c2 = c.with_fixes(Fixes(exclude=[old]))
    assert len(c2.leftovers) == 1 and not c2.leftovers.auto.any()
    assert (c2.matches.stage == "Final").sum() == 1 and checks.replay_conflicts(c2).empty


def test_counting_a_leftover_again():
    now = time.time()
    c = Career.build("replay", ipl_files(now - 86400, now))
    mid = c.leftovers.match_id.iloc[0]
    c2 = c.with_fixes(Fixes(include=[mid]))
    assert c2.leftovers.empty and mid in set(c2.matches.match_id)
    assert Career.from_pack(c2.to_pack()).leftovers.empty  # the choice is saved with the career


def test_games_in_order_are_never_left_out():
    """One playthrough, files saved in match order (a few seconds apart, or all in the
    same second when the game simulates a batch): nothing is left out."""
    for step in (0, 3, 60):
        files = []
        for i, p in enumerate(sorted(IPL, key=lambda p: pd.Timestamp(p.name.split("-")[0].replace("_", " ")))):
            files.append((p.name, p.read_bytes(), 1_780_000_000 + i * step))
        c = Career.build("in order", files)
        assert c.leftovers.empty, step


def test_the_career_file_keeps_names_and_times():
    now = time.time()
    c = Career.build("replay", ipl_files(now - 86400, now))
    pack = c.to_pack()
    with zipfile.ZipFile(io.BytesIO(pack)) as zf:
        sources = json.loads(zf.read(PACK_SOURCES))
        times = json.loads(zf.read(PACK_TIMES))
    assert set(sources.values()) == set(c.texts) and len(times) == len(c.texts)
    back = Career.from_pack(pack)
    assert set(back.texts) == set(c.texts) and len(back.leftovers) == 1
    assert back.times == c.times


def _flipped(p: Path) -> tuple[str, str]:
    """The same fixture played again with the other side winning."""
    c = Career.build("c", [(p.name, p.read_bytes())])
    winner, loser = c.matches.winner.iloc[0], c.matches.loser.iloc[0]
    return p.read_text(), p.read_text().replace(f"{winner} won", f"{loser} won", 1)


def test_a_replayed_match_with_a_new_result_replaces_the_old_one():
    p = FIX / "6_may_2026-hdr_v_pnj_ipl.txt"
    first, replayed = _flipped(p)
    c = Career.build("c", [(p.name, first.encode())])
    c2 = c.add_files([(p.name, replayed.encode())])
    assert len(c2.matches) == 1 and c2.matches.result.iloc[0] != c.matches.result.iloc[0]
    # an unchanged save of the same match is reported as a duplicate and changes nothing
    again = c2.add_files([(p.name, replayed.encode())])
    assert len(again.matches) == 1 and [r.status for r in again.report] == ["duplicate"]


def test_a_resaved_file_replaces_the_old_one_even_from_an_old_career_file():
    """Careers saved before names were kept stored "6 may 2026-hdr v pnj (ipl).txt" as
    "6_may_2026-hdr_v_pnj_ipl_.txt".  When the game saves that match again (replayed),
    the new version must replace the old one, not be counted as a second match."""
    p = FIX / "6_may_2026-hdr_v_pnj_ipl.txt"
    first, replayed = _flipped(p)
    name = "6 may 2026-hdr v pnj (ipl).txt"
    old = Career.build("old", [(_leaf(name), first.encode())])
    assert list(old.texts) == [_leaf(name)]
    newer = old.add_files([(name, replayed.encode())])
    assert len(newer.matches) == 1 and list(newer.texts) == [name]
    assert newer.matches.result.iloc[0] != old.matches.result.iloc[0]


def test_one_off_and_unnumbered_internationals_join_their_series():
    p = FIX / "16_may_2026-ban_v_pak_2nd_tst.txt"
    base = p.read_text()
    only = base.replace("2nd Test Match (of 2) - 16 May 2026", "Only Test Match - 8 May 2026")
    second = base.replace("2nd Test Match (of 2) - 16 May 2026", "2nd Test Match - 16 May 2026")
    lone = base.replace("2nd Test Match (of 2) - 16 May 2026", "Only Test Match - 16 Aug 2026")
    c = Career.build("tour", [("a.txt", only.encode()), ("b.txt", second.encode()), ("c.txt", lone.encode())])
    m = c.matches.sort_values("date")
    assert set(m.competition) == {"Test"} and set(m.section) == {"Tests"} and set(m.event) == {"Tests (bilateral series)"}
    assert m.series_id.iloc[0] == m.series_id.iloc[1] != m.series_id.iloc[2]
    s = T.series_table(c, m.match_id).set_index("start")
    assert list(s.played.sort_index()) == [2, 1]
    # pages show a match number without a series length
    for mid in m.match_id:
        at = AppTest.from_file(str(ROOT / "views" / "match.py"), default_timeout=60)
        at.session_state["career_obj"] = c
        at.session_state["mt_match"] = mid
        at.run()
        assert not at.exception
    at = AppTest.from_file(str(ROOT / "views" / "competitions.py"), default_timeout=60)
    at.session_state["career_obj"] = c
    at.run()
    assert not at.exception


def test_blast_groups_with_cross_group_games():
    """Three named groups of six plus cross-group games titled just "Group Match":
    three tables of six, each row counting all of the team's league games."""
    import itertools
    groups = {"North Group": list("ABCDEF"), "South Group": list("GHIJKL"), "Mid & West": list("MNOPQR")}
    rows, day = [], pd.Timestamp("2026-05-01")
    for g, teams in groups.items():
        for a, b in itertools.combinations(teams, 2):
            rows.append(dict(home=a, away=b, stage=g, date=day))
            day += pd.Timedelta(days=1)
    for a, b in zip(groups["North Group"], groups["South Group"]):
        rows.append(dict(home=a, away=b, stage="Group", date=day))
    got = T._groups(pd.DataFrame(rows))
    assert {label: members for label, _, members in got} == {g: set(t) for g, t in groups.items()}
    north = next(gm for label, gm, _ in got if label == "North Group")
    assert len(north) == 15 + 6  # its own games and its teams' cross-group games


def test_the_hundreds_preliminary_final_is_a_knockout():
    from ccstats.competitions import classify
    from ccstats.parser import parse_scorecard
    p = FIX / "1_aug_2026-brm_v_cdf_hundred.txt"
    text = p.read_text()
    title = text.splitlines()[2]
    m = parse_scorecard(text.replace(title, "The Hundred - Preliminary-Final - 15 Aug 2026"), "pf.txt")
    c = classify(m)
    assert (c.stage, c.knockout) == ("Eliminator", True)


def test_the_folder_watcher_attaches_times_to_an_older_career(tmp_path):
    folder = tmp_path / "Scorecards"
    folder.mkdir()
    now = time.time()
    for p in IPL:
        shutil.copy(p, folder)
        os.utime(folder / p.name, (now, now))
    name, data = old_final()
    (folder / name).write_bytes(data)
    os.utime(folder / name, (now - 86400, now - 86400))
    w = Watcher(CareerStore(tmp_path / "home"))
    res = w.create("My career", folder)
    assert len(res.career.leftovers) == 1  # a new career gets the times straight away
    # a career made by an older version: no times stored, folder record without the flag
    career, settings = w.store.load("My career")
    plain = Career.build(career.name, [(s, t.encode()) for s, t in career.texts.items()])
    assert plain.leftovers.empty
    w.store.save(plain, settings)
    data = json.loads(w.path.read_text())
    data[str(folder)].pop("times")
    w.path.write_text(json.dumps(data))
    res = w.sync(str(folder))
    assert res is not None and res.refreshed and not res.added and len(res.career.leftovers) == 1
    assert w.sync(str(folder)) is None  # once only
    assert len(w.store.load("My career")[0].leftovers) == 1


def test_data_check_buttons_on_shared_names_and_leftovers():
    now = time.time()
    c = Career.build("replay", ipl_files(now - 86400, now))
    at = AppTest.from_file(str(ROOT / "views" / "data_check.py"), default_timeout=120)
    at.session_state["career_obj"] = c
    at.run()
    assert not at.exception
    # catches the scorecard can't give to one player just count for the team: their tab is last, nothing to do
    assert [t.label.split(" · ")[0] for t in at.tabs] == ["Name shared by 2 players", "Player with 2 names",
                                                         "Games left out", "Scorecards", "Your changes", "Team catches"]
    at.button(key="dc_inc_0").click().run()  # count the old final again
    assert not at.exception and at.session_state["career_obj"].leftovers.empty
    at.button(key="dc_ui_0").click().run()  # undo from Your changes
    assert not at.exception and len(at.session_state["career_obj"].leftovers) == 1


def test_keep_apart_separates_a_shared_name():
    """Two different IPL players printed the same way: one click keeps them apart."""
    gt = FIX / "17_apr_2026-gjt_v_klk_ipl.txt"
    srh = FIX / "6_may_2026-hdr_v_pnj_ipl.txt"
    base = Career.build("b", [(gt.name, gt.read_bytes()), (srh.name, srh.read_bytes())])
    b = base.batting
    g_name = b[b.team == "Gujarat Titans"].player.iloc[0]
    s_name = b[b.team == "Sunrisers Hyderabad"].player.iloc[0]
    c = Career.build("names", [(gt.name, gt.read_bytes()), (srh.name, srh.read_text().replace(s_name, g_name).encode())])
    shared = checks.shared_names(c)
    assert list(shared.player) == [g_name]
    at = AppTest.from_file(str(ROOT / "views" / "data_check.py"), default_timeout=120)
    at.session_state["career_obj"] = c
    at.run()
    at.button(key="dc_split_all").click().run()
    after = at.session_state["career_obj"]
    assert not at.exception and checks.shared_names(after).empty
    names = set(after.batting.player)
    assert g_name in names and any(n.startswith(g_name + " (") for n in names)


def test_a_substitute_fielders_catch_is_not_an_unclear_catch():
    """'c Sub b Cook': taken by a substitute, who isn't in the XI, so it counts for no
    player and there is nothing to decide."""
    p = FIX / "19_aug_2026-eng_v_pak_1st_tst.txt"
    text = p.read_text().replace("c Rizwan b Shah", "c Sub b Shah", 1)
    c = Career.build("sub", [(p.name, text.encode())])
    assert c.problems.empty
    out = c.batting[c.batting.dismissal == "c Sub b Shah"]
    assert len(out) == 1 and out.how_out.iloc[0] == "caught"
    assert not (c.fielding.printed == "Sub").any() and not (c.fielding.player == "Sub").any()
    assert not (checks.uncredited(c).printed == "Sub").any()
