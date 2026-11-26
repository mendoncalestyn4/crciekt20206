"""Names that may be one player (your answers of 26 November): Data check looks wider (near-spellings, a missing or
extra initial, a move with the very same surname), never two names in the same match; pairs beyond doubt are joined by
themselves, each listed, undoable (kept apart for good) and alerted once; anything less sure waits for your click.

The test data: the real test scorecards with one England player printed a second way from a date on, as the game
might. Joined by itself, every number on the site is the same as with the one name all along."""

from __future__ import annotations

import re

import pandas as pd
import pytest

from ccstats import alerts as AL
from ccstats import checks
from ccstats import datacheck as DC
from ccstats import lookalike as LA
from ccstats.loader import Career, Fixes
from serverkit import FIXTURES, by_date

FROM = pd.Timestamp("2027-06-12")       # B Duckett is printed "BM Duckett" from here on


def _date(f) -> pd.Timestamp:
    return pd.Timestamp(by_date(f)[0]) if isinstance(by_date(f), tuple) else pd.Timestamp(by_date(f))


def renamed(files, old="B Duckett", new="BM Duckett", start=FROM, end=None):
    """The scorecards with `old` printed as `new` in the matches from `start` (to `end`), keeping each line's width."""
    base = Career.build("x", [(f.name, f.read_bytes()) for f in files])
    when = base.matches.set_index("source").date
    out = []
    for f in files:
        t = f.read_bytes().decode("utf-8", "ignore")
        d = when.get(f.name)
        if d is not None and d >= start and (end is None or d < end):
            t = re.sub(re.escape(old) + r"( {%d})?" % (len(new) - len(old)), new.replace("\\", ""), t)
        out.append((f.name, t.encode()))
    return out


@pytest.fixture(scope="module")
def plain():
    c = Career.build("t", [(f.name, f.read_bytes()) for f in FIXTURES])
    c.count_fielding = False
    return c


@pytest.fixture(scope="module")
def twice():
    c = Career.build("t", renamed(FIXTURES))
    c.count_fielding = False
    return c


def test_how_names_are_read():
    assert LA.parts("R Patel (Surrey)") is None and LA.parts("D Jansen (2)") is None
    assert LA.parts("Q de Kock")[2] == "dekock" and LA.parts("F O'Neill")[2] == "oneill"
    assert LA.why("M Mohammed", "M Muhammad").startswith("surnames that sound the same")
    assert LA.why("S Smith", "S Smyth").startswith("surnames spelt nearly the same")   # one letter: said that way
    assert LA.why("A Ahmadi", "A Ahmede").startswith("surnames that sound the same")
    assert LA.why("S Harmer", "S Harper").startswith("surnames spelt nearly the same")
    assert "extra initial" in LA.why("J Root", "JE Root") and "extra initial" in LA.why("J Root", "Joe Root")
    assert "without an initial" in LA.why("Root", "J Root")
    assert LA.why("F O'Neill", "F ONeill") == "the same name, printed a little differently"
    # "Jr." isn't a surname, a hyphenated surname is one, and father and son are two players
    assert LA.parts("A Rahane Jr.")[2] == "rahane" and LA.parts("J Smith-Nunez")[2] == "smithnunez"
    assert "extra initial" in LA.why("J Root Jr.", "JE Root Jr.")
    for a, b in [("A Rahane Jr.", "A Sharma Jr."), ("J Smith-Ñúñez", "J Bethell-Ñúñez"), ("A Rahane", "A Rahane Jr."),
                 ("J Bird", "J Broad"), ("A Best", "A Basith"), ("A Hosein", "A Husnain"), ("J Root", "M Root"),
                 ("J Root", "J Root"), ("S Kang", "S King")]:
        assert LA.why(a, b) == "", (a, b)


def test_a_player_printed_two_ways_is_joined_by_itself(twice):
    j = twice.auto_joins
    assert len(j) == 1 and set(j[["other", "keep"]].iloc[0]) == {"B Duckett", "BM Duckett"} and j.sure.iloc[0]
    assert j.team.iloc[0] == "England" and "extra initial" in j.why.iloc[0]
    names = set(twice.batting.player) | set(twice.bowling.player)
    assert len({"B Duckett", "BM Duckett"} & names) == 1          # one player everywhere


def test_every_number_the_same_as_one_name_all_along(plain, twice):
    keep = twice.auto_joins.keep.iloc[0]
    for tab in ("batting", "bowling"):
        # a match's id comes from its scorecard's text, so the matches are lined up by file
        a = getattr(plain, tab).replace({"player": {"B Duckett": keep}}).merge(plain.matches[["match_id", "source"]], on="match_id")
        b = getattr(twice, tab).merge(twice.matches[["match_id", "source"]], on="match_id")
        cols = [c for c in a.columns if c not in ("bowler", "fielder", "match_id")]
        key = ["source", "innings_no", "player"]
        pd.testing.assert_frame_equal(a[cols].sort_values(key).reset_index(drop=True),
                                      b[cols].sort_values(key).reset_index(drop=True), check_dtype=False)
    assert len(plain.matches) == len(twice.matches)


def test_kept_apart_and_joined_again(twice):
    j = twice.auto_joins.iloc[0]
    pv = DC.preview(twice, "keep_apart", dict(other=j.other, keep=j.keep))
    assert sum(x["matches"] for x in pv["after"]) == pv["before"][0]["matches"]
    assert sum(x["runs"] for x in pv["after"]) == pv["before"][0]["runs"]
    f, msg = DC.change(twice, "keep_apart", dict(other=j.other, keep=j.keep))
    assert "kept apart" in msg and f.keep_apart == [[j.other, j.keep]]
    apart = twice.with_fixes(f)
    assert apart.auto_joins.empty and {j.other, j.keep} <= set(apart.batting.player)
    assert not any({r.other, r.keep} == {j.other, j.keep} for r in checks.merge_suggestions(apart).itertuples())  # not asked again
    ch = DC.your_changes(apart)
    mine = [x for x in ch if x["kind"] == "keep_apart"]
    assert len(mine) == 1
    f2, msg2 = DC.change(apart, "undo", dict(kind="keep_apart", key=mine[0]["key"]))
    assert len(apart.with_fixes(f2).auto_joins) == 1 and "joined again" in msg2
    # undone from Your changes on the joined career too
    auto = [x for x in DC.your_changes(twice) if x["kind"] == "auto_join"]
    assert len(auto) == 1
    f3, _ = DC.change(twice, "undo", dict(kind="auto_join", key=auto[0]["key"]))
    assert f3.keep_apart == [[j.other, j.keep]]
    # the career file keeps the choice
    assert Fixes.from_json(f3.to_json()).keep_apart == [[j.other, j.keep]]


def test_never_joined_when_not_sure():
    # a third way of printing the same name (two candidates each): only listed, never joined
    files = renamed(FIXTURES)
    first = Career.build("x", files)
    his = first.batting[first.batting.player.str.contains("Duckett")].merge(first.matches[["match_id", "date", "source"]], on="match_id")
    last = his.date.max()
    assert his.player.nunique() == 1
    third = [(n, t.decode().replace("BM Duckett", "Ben Duckett").encode()) if n in set(his[his.date == last].source) else (n, t)
             for n, t in files]
    c = Career.build("t", third)
    assert {"B Duckett", "BM Duckett", "Ben Duckett"} <= set(c.batting.player)
    assert c.auto_joins.empty
    listed = checks.merge_suggestions(c)
    assert len(listed[listed.other.str.contains("Duckett") | listed.keep.str.contains("Duckett")]) >= 2
    # and a pair that played in the same match is never even listed
    assert not any(DC.played_together(c, r.other, r.keep) for r in listed.itertuples())


def test_not_straight_after_is_only_listed():
    # the old name in his first ODI only, the new one from the fourth: two England ODIs between is the most allowed;
    # here the gap is made longer by printing the old name only in the first of his games
    c0 = Career.build("x", [(f.name, f.read_bytes()) for f in FIXTURES])
    eng = c0.matches[((c0.matches.home == "England") | (c0.matches.away == "England"))].sort_values("date")
    duck = c0.batting[c0.batting.player == "B Duckett"].merge(c0.matches[["match_id", "date"]], on="match_id").date.sort_values()
    start = duck.iloc[1]
    files = renamed(FIXTURES, start=start)
    c = Career.build("t", files)
    between = c0.matches[(c0.matches.date > duck.iloc[0]) & (c0.matches.date < start) &
                         c0.matches.match_id.isin(eng.match_id) & (c0.matches.format == "ODI")]
    if len(between) > LA.GAP:
        assert c.auto_joins.empty and len(checks.merge_suggestions(c))
    else:
        assert len(c.auto_joins) == 1


def test_summary_counts_and_the_old_site_columns(twice):
    s = DC.summary(twice)
    assert any("joined by themselves" in x for x in s["fine"]) and s["counts"]["Player with two names"] >= 1
    assert s["counts"]["Your changes"] >= 1
    mg = checks.merge_suggestions(twice)
    for col in ("keep", "other", "keep_matches", "other_matches", "teams", "why"):
        assert col in mg.columns


def test_names_joined_alert_said_once(twice):
    _, seen = AL.check(twice, [], ["England"], [], {})
    assert not [a for a in AL.check(twice, [], ["England"], [], seen)[0] if a["kind"] == "names"]   # primed: old news
    out, seen2 = AL.check(twice, [], ["England"], [], dict(seen, said=[]))
    names = [a for a in out if a["kind"] == "names"]
    assert len(names) == 1 and "Duckett" in names[0]["text"] and "Data check" in names[0]["text"]
    assert not [a for a in AL.check(twice, [], ["England"], [], seen2)[0] if a["kind"] == "names"]


def test_lasting_alerts_are_never_forgotten(twice):
    """A goal reached or two names joined stays true, so it's remembered for good (it used to be cut alphabetically
    with everything else at 3,000, and could have been said again)."""
    seen = {"started": True, "said": ["join|B Duckett|BM Duckett", "join|BM Duckett|B Duckett"] +
            [f"mile|{i:05d}|x" for i in range(3500)]}
    out, after = AL.check(twice, [], ["England"], [], seen)
    assert not [a for a in out if a["kind"] == "names"]
    assert "join|B Duckett|BM Duckett" in after["said"] and len([k for k in after["said"] if k.startswith("mile|")]) == 3000
    assert after["said"][-1] == "mile|03499|x"                     # the oldest of the rest go first
