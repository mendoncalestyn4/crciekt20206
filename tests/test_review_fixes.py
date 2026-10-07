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
    home = [dict(fx[0], venue="home")]  # one venue can't fit a whole tournament: its scorecards decide
    assert F.with_venues(career, F.track(career, home)) is career


def test_an_undated_tournament_takes_the_current_edition_only(career):
    import copy
    t = F.track(career, F.make_tournament("England", "Champions Trophy", "ODI"))
    assert not (t.status == "played").any()  # no Champions Trophy in these files: nothing claimed
    # in the middle of the World Cup (before its final): an undated "ODI World Cup" is this one
    during = copy.copy(career)
    during.matches = career.matches[career.matches.date < pd.Timestamp("2027-06-20")].copy()
    t = F.track(during, F.make_tournament("England", "ODI World Cup", "ODI"), auto=["England"])
    assert (t[~t.auto].status == "played").sum() == 2 and not t.auto.any()
    # once England have won it, an undated one means the next edition: it waits, the games show auto-added
    t = F.track(career, F.make_tournament("England", "ODI World Cup", "ODI"), auto=["England"])
    assert list(t[~t.auto].status) == ["next"] and (t[t.auto].status == "played").sum() == 3
    # with its month it's ticked off whatever happened
    t = F.track(career, F.make_tournament("England", "ODI World Cup", "ODI", "2027-06"))
    assert (t.status == "played").sum() == 3


def test_a_tournament_line_is_not_read_as_a_team(career):
    known = sorted(set(career.matches.home) | set(career.matches.away))
    rows, err = F.parse_line("Indian Premier League T20 Apr 2027", "Chennai Super Kings", known)
    assert not err and rows[0]["opponent"] == "" and rows[0]["series"].startswith("Indian Premier League")
    assert rows[0]["format"] == "T20"  # a franchise's tournament is T20, never T20I
    rows, err = F.parse_line("Trans-Tasman Trophy v Austral 3 Tests", "India", sorted(F.NATIONS))
    assert not err and rows[0]["opponent"] == "Australia" and len(rows) == 3  # "v" names the opponent
    assert F.parse_line("Trans-Tasman Trophy v Austral 3 Tests", "India", known + ["Australia"])[0][0]["opponent"] == "Australia"
    rows, err = F.parse_line("Trans-Tasman Trophy v Austral 3 Tests", "India", known + ["South Australia"])  # which one?
    assert not rows and "could mean Australia or South Australia" in err
    # a word of the tournament's name is never taken for the opponent named after "v"
    rows, err = F.parse_line("Indian Premier League final v Chennai T20 May 2027", "Kolkata Knight Riders",
                             known + ["Chennai Super Kings"])
    assert not err and rows[0]["opponent"] == "Chennai Super Kings"
    rows, err = F.parse_line("Champions Trophy final v TBC Feb 2027 ODI", "India", known)  # no team after v: a tournament
    assert not err and rows[0]["opponent"] == "" and rows[0]["format"] == "ODI" and rows[0]["series"].startswith("Champions Trophy ·")
    # the opponent before "v" (your own team after it)
    assert F.parse_line("Austral v India 3 Tests Dec 2027", "India", sorted(F.NATIONS))[0][0]["opponent"] == "Australia"
    assert F.parse_line("Kolkata v Chennai 2 T20s Apr 2027", "Chennai Super Kings",
                        known + ["Chennai Super Kings"])[0][0]["opponent"] == "Kolkata Knight Riders"
    # a misspelt opponent in a series line is an error, never a made-up tournament
    rows, err = F.parse_line("Trans-Tasman Trophy v Austrlia 3 Tests", "India", sorted(F.NATIONS))
    assert not rows and "check the spelling" in err
    # known competitions by their names, in their own formats
    for line, team_, name, fmt in (("Royal London One-Day Cup May 2027", "Kent", "One-Day Cup", "List A"),
                                   ("The Hundred Aug 2027", "Kent", "The Hundred", "The Hundred"),
                                   ("Vitality Blast May 2027", "Kent", "T20 Blast", "T20"),
                                   ("Indian Premier League Apr 2027", "Chennai Super Kings", "Indian Premier League", "T20"),
                                   ("T20 World Cup Qualifier Jun 2027", "Italy", "T20 World Cup Qualifier", "T20I")):
        rows, err = F.parse_line(line, team_, known)
        assert not err and rows[0]["series"].startswith(name) and rows[0]["format"] == fmt, (line, rows, err)
    rows, err = F.parse_line("T20 World Cup Qualifier T20I Jun 2027", "Italy", known)  # a side not on the list keeps T20I
    assert not err and rows[0]["format"] == "T20I"
    rows, err = F.parse_line("Kolkata 2 T20s home Apr 2027", "Chennai Super Kings", known)
    assert not err and rows[0]["opponent"] == "Kolkata Knight Riders"  # one word still finds a team when it's a series


def test_wtc_goal_ordinals():
    from ccstats.stats import ordinal
    assert [ordinal(n) for n in (1, 2, 3, 4, 11, 12, 13, 21, 22, 23, 101)] == \
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
    p = D.percentiles(pd.DataFrame({"x": [1.0, 2.0, np.nan, 4.0]}), "x", "high")
    assert np.isnan(p.iloc[2]) and D.top_text(p.iloc[2]) == "–"  # no figure: no place
    tied = [D.top_text(v) for v in D.percentiles(pd.DataFrame({"x": [1, 1, 1, 2, 3]}), "x", "high")]
    assert tied == ["bottom 20%", "bottom 20%", "bottom 20%", "top 40%", "top 20%"]  # tied last: bottom, never top
    many = [D.top_text(v) for v in D.percentiles(pd.DataFrame({"x": [1, 1, 1, 1, 2]}), "x", "high")]
    assert many == ["bottom 20%"] * 4 + ["top 20%"]  # however many share last place
    mid = [D.top_text(v) for v in D.percentiles(pd.DataFrame({"x": [1, 2, 2, 2, 2, 2, 3]}), "x", "high")]
    assert mid[1:6] == ["top 50%"] * 5  # a tie across the middle is the middle
    five = [D.top_text(v) for v in D.percentiles(pd.DataFrame({"x": range(5)}), "x", "high")]
    assert five == ["bottom 20%", "bottom 40%", "top 50%", "top 40%", "top 20%"]  # the middle one is in neither half


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


def test_the_schedule_reader_reads_every_team_every_way(career):
    """Every opponent, written in full, before or after 'v', with every format and venue, comes out exactly."""
    import random
    teams = sorted(set(career.matches.home) | set(career.matches.away) | F.NATIONS)
    rnd = random.Random(3)
    for opp in teams:
        me = rnd.choice([t for t in teams if t != opp])
        for fmt_word, n in (("Tests", 3), ("ODIs", 2), ("T20s", 5), ("Test", 1)):
            for shape in ("{o} {n} {f} away Jan 2027", "{n} {f} v {o} home Mar 2027", "{o} v {me} {n} {f} Feb 2027",
                          "v {o} {n} {f} neutral 2027-05"):
                line = shape.format(o=opp, n=n, f=fmt_word, me=me)
                rows, err = F.parse_line(line, me, teams)
                assert not err and len(rows) == n and {r["opponent"] for r in rows} == {opp}, (line, me, err)
                want = {"Tests": "Test", "Test": "Test", "ODIs": "ODI"}.get(fmt_word) or ("T20I" if opp in F.NATIONS else "T20")
                assert rows[0]["format"] == want, (line, rows[0]["format"])


def test_the_schedule_reader_never_breaks_on_anything(career):
    import random
    teams = sorted(set(career.matches.home) | set(career.matches.away) | F.NATIONS)
    words = (["v", "vs", "against", "home", "away", "@", "(h)", "Jan", "2027", "3", "Tests", "ODI", "T20", "T20I", "Cup",
              "Trophy", "League", "final", "World", "Qualifier", "Royal", "London", "One-Day", "The", "Hundred", "Blast",
              "TBC", "12", "Feb", "2026-03-04", "x", "∑", "Premier", "Indian", "Austral", "Mumbai", "WTC", "games", "7"]
             + [t.split()[0] for t in teams[:20]] + teams[:10])
    rnd = random.Random(17)
    for _ in range(4000):
        me = rnd.choice(teams)
        line = " ".join(rnd.choice(words) for _ in range(rnd.randint(0, 10)))
        rows, err = F.parse_line(line, me, teams)
        assert isinstance(rows, list) and isinstance(err, str) and (not rows or not err)
        for r in rows:
            assert r["opponent"] != me and r["format"] in F.FORMATS, (line, r)
            assert (r["opponent"] == "") == (r["no"] == 0)  # a tournament row, or a numbered match of a series
        assert len(rows) <= 10


@pytest.mark.parametrize("line,team,name,fmt", [
    ("WTC Final v TBC 1 Test Jun 2027", "India", "World Test Championship Final", "Test"),
    ("Asia Cup (T20I) Sep 2027", "India", "Asia Cup", "T20I"),
    ("Asia Cup T20I edition Sep 2027", "India", "Asia Cup", "T20I"),
    ("v TBC Champions Trophy final ODI Feb 2027", "India", "Champions Trophy", "ODI"),
    ("Super Smash T20 Jan 2027", "Auckland", "Super Smash", "T20"),
    ("Pakistan Super League T20 Feb 2027", "Lahore Qalandars", "Pakistan Super League", "T20"),
    ("Bangladesh Premier League Jan 2027", "Lahore Qalandars", "Bangladesh Premier League", "T20"),
    ("T20 World Cup Qualifier Jun 2027", "Italy", "T20 World Cup Qualifier", "T20I"),
    ("T20 World Cup Jun 2027", "India", "T20 World Cup", "T20I"),
    ("World Cup Oct 2027", "India", "ODI World Cup", "ODI"),
])
def test_tournament_lines_by_name(line, team, name, fmt):
    known = sorted(F.NATIONS) + ["Chennai Super Kings", "Auckland", "Lahore Qalandars", "Kent"]
    rows, err = F.parse_line(line, team, known)
    assert not err and rows[0]["opponent"] == "" and rows[0]["series"].split(" · ")[0] == name and rows[0]["format"] == fmt


def test_a_misspelt_opponent_with_a_number_of_matches_is_an_error():
    for line in ("Trans-Tasman Trophy v Austrlia 3 matches", "Trans-Tasman Trophy v Austrlia 3 Tests"):
        rows, err = F.parse_line(line, "India", sorted(F.NATIONS))
        assert not rows and "check the spelling" in err


@pytest.mark.parametrize("line,team,series,fmt,opp", [
    ("World Cup 2027", "India", "ODI World Cup", "ODI", ""),  # not "World Cup 20" (the T20 one)
    ("T20I World Cup Jun 2027", "India", "T20 World Cup · Jun 2027", "T20I", ""),
    ("WTC Final v ? 1 Test Jun 2027", "India", "World Test Championship Final · Jun 2027", "Test", ""),
    ("Indian Premier League Mumbai Indians 1 match Apr 2027", "Chennai Super Kings", "v Mumbai Indians · 1 T20 · Apr 2027", "T20",
     "Mumbai Indians"),
    ("IPL Qualifier 1 May 2027", "Chennai Super Kings", "Indian Premier League · May 2027", "T20", ""),
    ("Champions Trophy final v TBC Feb 2027 ODI", "India", "Champions Trophy · Feb 2027", "ODI", ""),
    ("T20 World Cup in India Feb 2026", "England", "T20 World Cup · Feb 2026", "T20I", ""),  # the host, not an opponent
    ("Champions Trophy Pakistan Feb 2027", "India", "Champions Trophy · Feb 2027", "ODI", ""),
    ("World Cup v Pakistan T20I", "India", "v Pakistan · 1 T20I", "T20I", "Pakistan"),  # the typed format wins
    ("U19 World Cup Qualifier Jan 2027", "India", "U19 ODI World Cup Qualifier · Jan 2027", "ODI", ""),
    ("U19 World Cup Jan 2027", "India", "U19 ODI World Cup · Jan 2027", "ODI", ""),
    ("Asia Cup Qualifier Aug 2027", "Italy", "Asia Cup Qualifier · Aug 2027", "ODI", ""),
    ("PSL Feb 2027", "Lahore Qalandars", "Pakistan Super League · Feb 2027", "T20", ""),
])
def test_more_lines_read_right(line, team, series, fmt, opp):
    known = sorted(F.NATIONS) + ["Chennai Super Kings", "Mumbai Indians", "Lahore Qalandars", "Kent"]
    rows, err = F.parse_line(line, team, known)
    assert not err, err
    assert rows[0]["series"] == series and rows[0]["format"] == fmt and rows[0]["opponent"] == opp


def test_a_final_line_is_the_tournament_and_its_knockouts_come_by_themselves(career):
    known = sorted(set(career.matches.home) | set(career.matches.away))
    rows, added = F.merge(*[F.parse_line("IPL May 2026 T20", "Gujarat Titans", known)[0]] * 1, [])
    final, err = F.parse_line("IPL final May 2026", "Gujarat Titans", known)
    assert not err and F.merge(rows, final)[1] == 0  # the same tournament: already there
    t = F.track(career, rows)
    m = career.matches.set_index("match_id")
    stages = {m.stage[x] for x in t[t.status == "played"].match_id}
    assert {"Qualifier 1", "Final"} <= stages  # its knockout games are ticked off on the tournament's own row


def test_an_undated_tournament_that_is_over_means_the_next_one(career):
    # India won this T20 World Cup's final: an undated "T20 World Cup" now means the next edition
    t = F.track(career, F.make_tournament("India", "T20 World Cup", "T20I"))
    assert list(t.status) == ["next"]
