"""Ties settled by a super over, and the unclear-catch suggestions."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from ccstats import checks
from ccstats.loader import Career, Fixes
from ccstats.parser import parse_scorecard, validate_match
from ccstats.stats import Scope, player_tables

ROOT = Path(__file__).parent.parent
SUPER = sorted((Path(__file__).parent / "fixtures_super").glob("*.txt"))
FIXTURES = sorted((Path(__file__).parent / "fixtures").glob("*.txt"))


def test_super_over_innings_are_kept_apart():
    m = parse_scorecard(SUPER[1].read_text(), SUPER[1].name)  # 2 May 2026, Bangladesh v New Zealand
    assert [(i.team, i.total, i.wickets, i.balls) for i in m.innings] == [
        ("Bangladesh", 177, 9, 120), ("New Zealand", 177, 8, 120)]
    assert [(i.team, i.total, i.wickets) for i in m.super_overs] == [("Bangladesh", 11, 2), ("New Zealand", 21, 0)]
    assert (m.result_type, m.winner) == ("tie", "New Zealand")
    assert validate_match(m) == []
    z = parse_scorecard(SUPER[0].read_text(), SUPER[0].name)  # Zimbabwe v Australia, rain-reduced tie
    assert [(i.team, i.total, i.wickets) for i in z.innings] == [("Zimbabwe", 237, 7), ("Australia", 211, 7)]
    assert (z.result_type, z.winner) == ("tie", "Australia") and validate_match(z) == []


def test_super_overs_do_not_count_in_any_figures():
    c = Career.build("so", [(p.name, p.read_bytes()) for p in SUPER])
    assert c.problems.empty
    m = c.matches.set_index("home")
    nz = m.loc["Bangladesh"]
    assert (nz.result_type, nz.winner, nz.tiebreak_winner) == ("tie", "", "New Zealand")
    assert nz.result == "Match tied · New Zealand won the super over"
    assert nz.super_over == "Bangladesh 11/2 · New Zealand 21/0"
    # F Allen made 16 in the main innings and 16* in the super over: only the 16 counts
    bat = player_tables(c, Scope())[0].set_index("player")
    assert bat.runs["F Allen"] == 16 and bat.innings["F Allen"] == 1
    # J Duffy took 2 super-over wickets that don't count: 1/47 in the match
    bowl = player_tables(c, Scope())[1].set_index("player")
    assert (bowl.wickets["J Duffy"], bowl.runs["J Duffy"]) == (1, 47)
    assert len(c.batting) == 44 and len(c.innings) == 4  # two matches x two real innings x 11


def test_every_unclear_catch_has_two_or_more_real_candidates():
    c = Career.build("c", [(p.name, p.read_bytes()) for p in FIXTURES + SUPER])
    u = checks.uncredited(c)
    from ccstats.parser import resolve_candidates
    for r in u.itertuples():
        # the surname really is shared: two or more of the side could have taken it
        assert len(resolve_candidates(r.printed, r.candidates)) >= 2, (r.printed, r.candidates)
        if r.kind == "caught":  # and the bowler isn't offered first: that would have been printed "c & b"
            assert r.candidates[0] != r.bowler


def test_suggestions_have_reasons_and_accept_all_is_undoable():
    c = Career.build("c", [(p.name, p.read_bytes()) for p in FIXTURES + SUPER])
    u = checks.uncredited(c)
    sug = u[u.suggestion != ""]
    assert len(sug) >= 1 and (sug.reason != "").all()
    assert all(s in cands for s, cands in zip(sug.suggestion, sug.candidates))
    khan = sug[sug.printed == "Khan"]
    assert (khan.suggestion == "U Khan").all()  # Pakistan's wicketkeeper
    fixed = c.with_fixes(Fixes(credits=dict(zip(sug.credit_key, sug.suggestion)), suggested=list(sug.credit_key)))
    assert len(checks.uncredited(fixed)) == len(u) - len(sug)
    assert Fixes.from_json(fixed.fixes.to_json()).suggested == list(sug.credit_key)  # saved with the career
    assert len(checks.uncredited(fixed.with_fixes(Fixes()))) == len(u)


def test_data_check_accept_all(tmp_path, monkeypatch):
    monkeypatch.setenv("STATS_PACK_HOME", str(tmp_path))
    c = Career.build("c", [(p.name, p.read_bytes()) for p in FIXTURES + SUPER])
    at = AppTest.from_file(str(ROOT / "views" / "data_check.py"), default_timeout=120)
    at.session_state["career_obj"] = c
    at.run()
    assert not at.exception
    n = int((checks.uncredited(c).suggestion != "").sum())
    at.button(key="dc_accept_all").click().run()
    assert not at.exception, at.exception
    after = at.session_state["career_obj"]
    assert len(after.fixes.suggested) == n and len(after.fixes.credits) == n


def test_a_wicket_listed_twice_never_breaks_the_player_page():
    """The crash from the old super-over reading: New Zealand's innings had two
    '1st wicket' entries (1-13 and the super over's 1-1)."""
    import pandas as pd
    from ccstats import analysis as A
    c = Career.build("so", [(p.name, p.read_bytes()) for p in SUPER])
    nz = c.innings[c.innings.team == "New Zealand"].iloc[0]
    dup = pd.DataFrame([dict(match_id=nz.match_id, innings_no=nz.innings_no, team="New Zealand", wicket=1, score=1),
                        dict(match_id=nz.match_id, innings_no=nz.innings_no, team="New Zealand", wicket=2, score=11)])
    c.fow = pd.concat([c.fow, dup], ignore_index=True)
    e = A.entry_scores(c)
    assert pd.api.types.is_numeric_dtype(e.came_in_score)
    for player in ("G Phillips", "L Ferguson", "M Henry"):  # a batter, a bowler, a tail-ender
        at = AppTest.from_file(str(ROOT / "views" / "player.py"), default_timeout=120)
        at.session_state["career_obj"] = c
        at.session_state["pl_player"] = player
        at.run()
        assert not at.exception, (player, at.exception)
        assert not [w for w in at.warning if "couldn't be shown" in w.value], player


def test_repeated_wickets_are_dropped_when_reading():
    text = SUPER[1].read_text().replace("6-148  7-163  8-177", "6-148  7-163  8-177  1-99")
    c = Career.build("d", [("dup.txt", text.encode())])
    f = c.fow
    assert not f.duplicated(["match_id", "innings_no", "wicket"]).any()
    nz = f[f.team == "New Zealand"].set_index("wicket").score
    assert nz[1] == 13  # the first one is kept


def test_every_key_names_exactly_one_row():
    """Pages look rows up by these keys; a repeat would make a lookup return
    several rows (the player-page crash)."""
    from ccstats.loader import UNIQUE_KEYS
    c = Career.build("all", [(p.name, p.read_bytes()) for p in FIXTURES + SUPER])
    for name, keys in UNIQUE_KEYS.items():
        df = getattr(c, name)
        assert not df.duplicated(keys).any(), name


def test_a_name_on_two_bowling_lines_is_two_bowlers():
    text = SUPER[1].read_text().replace("J Duffy         4      6     47     1     11.75",
                                        "J Duffy         4      6     47     1     11.75\n"
                                        "J Duffy         1      0     10     1     10.00", 1)
    c = Career.build("d", [("twice.txt", text.encode())])
    w = c.bowling[c.bowling.player.str.startswith("J Duffy")].set_index("player")
    assert w.balls["J Duffy (2)"] > w.balls["J Duffy"]                # the one who bowled more is "(2)"
    # (the extra line makes the card's bowling add up to more than the innings: put right by the fair guess, noted)
    assert len(c.guesses) and not c.problems.problem.str.contains("bowling runs|overs do not").any()
    assert not c.problems.problem.str.contains("appears twice").any()
    at = AppTest.from_file(str(ROOT / "views" / "player.py"), default_timeout=120)
    at.session_state["career_obj"] = c
    at.session_state["pl_player"] = "J Duffy"
    at.run()
    assert not at.exception and not [x for x in at.warning if "couldn't be shown" in x.value]


# ---------------------------------------------------------------- international matches pooled by format
def _wtc_final():
    """A Test fixture re-titled as the World Test Championship Final."""
    p = Path(__file__).parent / "fixtures" / "16_may_2026-ban_v_pak_2nd_tst.txt"
    text = p.read_text().replace("2nd Test Match (of 2) - 16 May 2026", "World Test Championship Final - 16 Jun 2027")
    return ("wtc_final.txt", text.encode())


def test_every_test_is_in_tests_and_every_odi_in_odis():
    from ccstats.competitions import shown_name
    c = Career.build("intl", [(p.name, p.read_bytes()) for p in FIXTURES] + [_wtc_final()])
    m = c.matches
    intl = m[m.level == "International"]
    assert set(intl.section) == {"Tests", "ODIs", "T20Is"}
    assert (intl.section == intl.format.map({"Test": "Tests", "ODI": "ODIs", "T20I": "T20Is"})).all()
    wtc = m[m.competition == "World Test Championship Final"].iloc[0]
    assert (wtc.section, wtc.event, wtc.season) == ("Tests", "World Test Championship Final", "2027")
    assert (wtc.stage, wtc.knockout) == ("Final", True)
    assert set(m[m.competition == "ODI World Cup"].section) == {"ODIs"}
    # domestic and franchise competitions are never pooled
    dom = m[m.level != "International"]
    assert (dom.section == dom.event).all()
    # seasons of international cricket are calendar years
    assert (intl.season == intl.date.dt.year.astype(str)).all()
    # on screen a World Cup match keeps its name; a series match shows the format
    assert shown_name(wtc.section, wtc.event) == "World Test Championship Final"
    series = m[m.event == "ODIs (bilateral series)"].iloc[0]
    assert shown_name(series.section, series.event) == "ODIs"
    # stats: a player's Test figures include the final
    bat = player_tables(c, Scope(sections=["Tests"]))[0].set_index("player")
    only_series = player_tables(c, Scope(sections=["Tests"], competitions=["Test"]))[0].set_index("player")
    fin = c.batting[c.batting.match_id == wtc.match_id]
    p = fin.groupby("player").runs.sum().idxmax()
    assert bat.runs[p] == only_series.runs.get(p, 0) + fin[fin.player == p].runs.sum()


def test_honours_and_competitions_keep_each_event_apart():
    from ccstats import extras as E
    c = Career.build("intl", [(p.name, p.read_bytes()) for p in FIXTURES] + [_wtc_final()])
    h = E.honours(c)
    wtc = h[h.section == "World Test Championship Final"]  # the re-titled Test was drawn: a shared title
    assert len(wtc) == 1 and wtc.how.iloc[0] == "final drawn: title shared"
    assert wtc.champion_teams.iloc[0] == ["Bangladesh", "Pakistan"]
    assert len(E.trophy_cabinet(c, "Bangladesh")) == 1 and len(E.trophy_cabinet(c, "Pakistan")) == 1
    assert not h.section.isin(["Tests", "ODIs", "T20Is"]).any()
    at = AppTest.from_file(str(ROOT / "views" / "competitions.py"), default_timeout=120)
    at.session_state["career_obj"] = c
    at.session_state["cp2_event"] = "World Test Championship Final"
    at.run()
    assert not at.exception
    assert any("share the World Test Championship Final 2027 title" in x.value for x in at.markdown)
    at = AppTest.from_file(str(ROOT / "views" / "honours.py"), default_timeout=120)
    at.session_state["career_obj"] = c
    at.run()
    assert not at.exception
    # and a won final: England's 299-run win, re-titled
    p = Path(__file__).parent / "fixtures" / "19_aug_2026-eng_v_pak_1st_tst.txt"
    won = p.read_text().replace("1st Test Match (of 3) - 19 Aug 2026", "World Test Championship - Final - 19 Jun 2027")
    c2 = Career.build("won", [("wtc_won.txt", won.encode())])
    h2 = E.honours(c2)
    assert list(h2.champions) == ["England"] and list(h2.how) == ["won the final"] and list(h2.runners_up) == ["Pakistan"]


def test_a_world_cup_final_does_not_end_the_international_year():
    from ccstats import extras as E
    c = Career.build("intl", [(p.name, p.read_bytes()) for p in FIXTURES])
    m = c.matches
    assert ((m.section == "ODIs") & (m.stage == "Final")).any()
    info = E.season_in_progress(c, "ODIs")
    assert info is None or info[0] == "2027"  # judged on match counts, never stopped by the World Cup final


def test_a_bowlers_page_opens_on_bowling():
    c = Career.build("tabs", [(p.name, p.read_bytes()) for p in FIXTURES])
    for player, first in (("J Archer", ["Bowling", "Fielding", "Batting"]), ("J Root", ["Batting"])):
        at = AppTest.from_file(str(ROOT / "views" / "player.py"), default_timeout=120)
        at.session_state["career_obj"] = c
        at.session_state["pl_player"] = player
        at.session_state["pl_section"] = "Tests"
        at.run()
        assert not at.exception
        assert [t.label for t in at.tabs][:len(first)] == first, player


def test_the_key_guard_handles_every_kind_of_repeat():
    import pandas as pd
    from ccstats.loader import _one_row_per_key, build_tables
    from ccstats.parser import parse_scorecard as ps
    frames = build_tables([ps(SUPER[1].read_text(), SUPER[1].name)], Fixes())
    for name in ("matches", "innings", "batting", "fow", "fielding"):
        frames[name] = pd.concat([frames[name], frames[name].head(1)], ignore_index=True)
    _one_row_per_key(frames)
    from ccstats.loader import UNIQUE_KEYS
    for name, keys in UNIQUE_KEYS.items():
        assert not frames[name].duplicated(keys).any(), name
    assert frames["problems"].source.map(lambda s: isinstance(s, str)).all()
    assert frames["problems"].problem.str.contains("appears twice").sum() == 5


def test_two_bowlers_with_the_same_printed_name_are_kept_apart():
    """WI v SL and RSA v BAN: two 'K Mendis' / 'M Hasan' in one XI, both bowling in
    the same innings.  That's not an error: like batting, the second is '(2)'."""
    p = Path(__file__).parent / "fixtures" / "19_aug_2026-eng_v_pak_1st_tst.txt"
    text = p.read_text().replace("N Shah", "N Ali").replace("b Shah", "b Ali")  # Pakistan now has two "N Ali"
    c = Career.build("same", [("same_name.txt", text.encode())])
    assert c.problems.empty
    w = c.bowling[c.bowling.innings_no == 1].set_index("player")
    # the one who bowled more (Naseem, 17 overs) is taken to be the one batting lower ("(2)", no. 10)
    assert (w.runs["N Ali (2)"], w.wickets["N Ali (2)"]) == (89, 1)
    assert (w.runs["N Ali"], w.wickets["N Ali"]) == (52, 4)
    bat = c.batting[c.batting.innings_no == 2].set_index("position").player
    assert (bat[9], bat[10]) == ("N Ali", "N Ali (2)")
    for player in ("N Ali", "N Ali (2)"):
        at = AppTest.from_file(str(ROOT / "views" / "player.py"), default_timeout=120)
        at.session_state["career_obj"] = c
        at.session_state["pl_player"] = player
        at.run()
        assert not at.exception and not [x for x in at.warning if "couldn't be shown" in x.value], player
    at = AppTest.from_file(str(ROOT / "views" / "home.py"), default_timeout=120)
    at.session_state["career_obj"] = c
    at.run()
    assert not at.exception and not [x for x in at.warning if "self-check" in x.value]
