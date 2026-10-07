"""The bugs found in the full code review, each pinned down so it can't come back."""

import copy
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ccstats import deep as D
from ccstats import fixtures as F
from ccstats import playerdeep as PD
from ccstats import records as RC
from ccstats import seasonal as SN
from ccstats import teamdeep as TD
from ccstats import winprob as WP
from ccstats.loader import Career
from ccstats.local import CareerSettings, CareerStore, read_json, write_atomic
from ui.charts import record_steps_chart, unique_labels, win_line_points

FIXTURES = sorted((Path(__file__).parent / "fixtures").glob("*.txt"))
BLAST = next((Path(__file__).parent / "fixtures_stress").glob("*blast*.txt"))


@pytest.fixture(scope="module")
def career():
    return Career.build("Review fixes", [(p.name, p.read_bytes()) for p in FIXTURES])


# --------------------------------------------------------------------------- a finished scorecard is never dropped
def test_a_result_line_the_parser_cant_read_keeps_the_match(tmp_path):
    text = BLAST.read_text()
    lines = text.splitlines()
    i = next(k for k, ln in enumerate(lines) if " won by " in ln)
    lines[i] = "Durham Women won by 30 runs"  # a result naming no team in the match
    odd = "\n".join(lines)
    c = Career.build("odd", [("odd.txt", odd.encode())])
    assert len(c.matches) == 1 and c.report[0].status == "loaded"
    # and it survives being saved and loaded again (it used to vanish from the career file)
    store = CareerStore(tmp_path)
    store.save(c, CareerSettings(name="odd"))
    back, _ = store.load("odd")
    assert len(back.matches) == 1
    # a file cut short (no result line at all) is still left out until the game finishes it
    cut = Career.build("cut", [("cut.txt", text[: len(text) // 2].encode())])
    assert cut.matches.empty


# --------------------------------------------------------------------------- the schedule
def test_a_tournament_in_the_schedule_never_changes_home_and_away(career):
    fx = F.make_tournament("Gujarat Titans", "Indian Premier League", "T20", "2026-04")
    assert fx[0]["venue"] == ""
    t = F.track(career, fx)
    assert (t.status == "played").any()
    assert F.with_venues(career, t) is career
    old = [dict(fx[0], venue="neutral")]  # schedules saved by the earlier version
    assert F.with_venues(career, F.track(career, old)) is career


def test_an_undated_tournament_takes_one_edition_and_an_unknown_name_takes_nothing(career):
    t = F.track(career, F.make_tournament("England", "Champions Trophy", "ODI"))
    assert not (t.status == "played").any()  # no Champions Trophy in these files: nothing claimed
    t = F.track(career, F.make_tournament("England", "ODI World Cup", "ODI"))
    played = t[t.status == "played"]
    m = career.matches.set_index("match_id")
    assert len(played) and len({(m.event[x], m.season[x]) for x in played.match_id}) == 1


def test_a_tournament_line_is_not_read_as_a_team(career):
    known = sorted(set(career.matches.home) | set(career.matches.away))
    rows, err = F.parse_line("Indian Premier League T20 Apr 2027", "Chennai Super Kings", known)
    assert not err and rows[0]["opponent"] == "" and rows[0]["series"].startswith("Indian Premier League")
    rows, err = F.parse_line("Kolkata 2 T20s home Apr 2027", "Chennai Super Kings", known)
    assert not err and rows[0]["opponent"] == "Kolkata Knight Riders"  # one word still finds a team when it's a series


def test_wtc_goal_ordinals():
    assert [F._ordinal(n) for n in (1, 2, 3, 4, 11, 12, 13, 21, 22, 23, 101)] == \
        ["1st", "2nd", "3rd", "4th", "11th", "12th", "13th", "21st", "22nd", "23rd", "101st"]


# --------------------------------------------------------------------------- saving
def test_a_career_save_never_overwrites_settings_changed_meanwhile(tmp_path, career):
    store = CareerStore(tmp_path)
    store.save(career, CareerSettings(name=career.name, folder="X"))
    _, stale = store.load_settings(career.name)  # the folder watcher loads the settings…
    _, s = store.load_settings(career.name)
    s.fixtures = F.make_series("India", "England", "Test", 3, "away", "2027-01")  # …you edit your schedule…
    s.notes = {"a.txt": "my note"}
    store.save_settings(s)
    store.save(career, stale)  # …and the watcher saves the career it rebuilt
    _, now = store.load_settings(career.name)
    assert len(now.fixtures) == 3 and now.notes == {"a.txt": "my note"} and now.folder == "X"


def test_settings_reads_are_fresh_copies_and_see_every_change(tmp_path):
    f = tmp_path / "s.json"
    write_atomic(f, '{"a": [1]}')
    x = read_json(f)
    x["a"].append(2)  # a caller changing what it got doesn't change the next read
    assert read_json(f) == {"a": [1]}
    write_atomic(f, '{"a": [1, 2, 3]}')
    assert read_json(f) == {"a": [1, 2, 3]}
    assert not list(tmp_path.glob(".*.tmp"))  # no temp files left behind


# --------------------------------------------------------------------------- figures
def test_drawn_knockouts_are_draws_in_dominance(career):
    m = career.matches
    r = m[(m.result_type == "draw") & (m.tiebreak_winner != "")]
    assert len(r)
    d = TD.dominance(career, m[m.section == r.section.iloc[0]].match_id).set_index("team")
    for team in (r.home.iloc[0], r.away.iloc[0]):
        assert d.loc[team, "drawn"] >= 1


def test_hundred_on_debut_is_only_in_the_debut_game(career):
    a = PD.achievements(career)
    deb = a[a.badge == "Hundred on debut"]
    m = career.matches.set_index("match_id")
    for x in deb.itertuples():
        sec = m.section[x.match_id]
        ids = m.index[m.section == sec]
        rows = pd.concat([career.batting[["match_id", "player", "team"]], career.bowling[["match_id", "player", "team"]]])
        mine = rows[(rows.player == x.player) & rows.match_id.isin(ids)]
        mine = mine[mine.team == mine[mine.match_id == x.match_id].team.iloc[0]]
        first = min(mine.match_id, key=lambda k: (m.date[k], k))
        assert first == x.match_id, x.player


def test_record_steps_only_when_the_number_is_beaten(career, monkeypatch):
    real = RC.records

    def fake(c, ids, top=10):
        out = real(c, ids, top=top)
        hs = out["Highest individual scores"].head(2).copy()
        if len(hs) < 2:
            return out
        d0 = pd.Timestamp("2020-01-01")
        hs["sort"] = [300, 301]  # 150 out, then 150 not out
        hs["date"] = [d0, d0 + pd.Timedelta(days=5)]
        out = dict(out)
        out["Highest individual scores"] = hs
        return out

    monkeypatch.setattr(RC, "records", fake)
    tl = SN.record_timeline(career, career.matches.match_id)
    hs = tl[tl.record == "Highest individual scores"]
    assert len(hs) == 1 and pd.isna(hs.until.iloc[0])  # equalled, not beaten


def test_percentiles_for_small_pools():
    for n in (2, 3, 10, 100):
        p = D.percentiles(pd.DataFrame({"x": range(n)}), "x", "high")
        texts = [D.top_text(v) for v in p]
        assert texts[-1] == f"top {int(np.ceil(100 / n))}%"  # the best
        assert texts[0].startswith("bottom") and texts[0] != "bottom 1%" or n >= 100  # the worst
    assert D.top_text(D.percentiles(pd.DataFrame({"x": [5]}), "x", "high").iloc[0]) == "–"
    two = [D.top_text(v) for v in D.percentiles(pd.DataFrame({"x": [1, 2]}), "x", "high")]
    assert two == ["bottom 50%", "top 50%"]


def test_last_five_follow_the_order_played():
    """Two files: the one played last was saved with an earlier date; form ends on it."""
    c = Career.build("Order", [(p.name, p.read_bytes()) for p in FIXTURES[:20]])
    m = c.matches.sort_values("date")
    first, last = m.iloc[0], m.iloc[-1]
    c.times = {s: float(i) for i, s in enumerate(m.source)}
    c.times[first.source] = 10_000.0  # the earliest-dated game was the one played last
    rows = pd.DataFrame({"match_id": [last.match_id, first.match_id]})
    assert list(RC.by_played(c, rows).match_id) == [last.match_id, first.match_id]


# --------------------------------------------------------------------------- charts
def test_bar_names_are_never_repeated():
    for labels in (["A (2)", "A", "A"], ["a", "b", "a", "a"], ["x", "x (2)", "x"], list("aaaa")):
        out = unique_labels(labels)
        assert len(set(out)) == len(out) and out[0] == labels[0]


def test_a_tie_ends_at_50_percent_on_the_one_line_chart():
    line = pd.DataFrame(dict(label=["Start", "A 50/1"], W=[50.0, 60.0], D=[0.0, 0.0], L=[50.0, 40.0], T=[0.0, 0.0],
                             n=[10, 10]))
    line.attrs["outcome"] = "T"
    assert win_line_points(line, "Match tied", multi=False).W.iloc[-1] == 50
    assert win_line_points(line, "Match tied", multi=True)["T"].iloc[-1] == 100
    line.attrs["outcome"] = "L"
    pts = win_line_points(line, "B won", multi=False)
    assert pts.W.iloc[-1] == 0 and pts.label.iloc[-1] == "Result: B won"


def test_a_record_still_standing_runs_on_to_today():
    steps = pd.DataFrame(dict(date=pd.to_datetime(["2024-01-01", "2025-01-01"]), until=[pd.Timestamp("2025-01-01"), pd.NaT],
                              holder=["A", "B"], value=["100", "120"], against=["X", "Y"]))
    fig = record_steps_chart(steps, [100, 120], "runs", pd.Timestamp("2027-06-01"))
    assert pd.Timestamp(fig.data[0].x[-1]) == pd.Timestamp("2027-06-01")


def test_win_chance_lookups_belong_to_their_own_table(career):
    ids = career.matches[career.matches.section == "Indian Premier League"].match_id
    st_ = WP.states(career, ids)
    other = st_.copy()
    other["outcome"] = "L"  # same length, different table
    mid = ids.iloc[0]
    kind = WP.kind_of_ids(career, ids)
    a = WP.match_line(career, mid, st_, kind)
    b = WP.match_line(career, mid, other, kind)
    assert not a.empty and not b.empty
    assert not a.attrs.get("_index") and "_by_match" not in st_.attrs  # nothing heavy rides along in attrs
    assert copy.copy(st_).attrs == {} or "_index" not in st_.attrs
