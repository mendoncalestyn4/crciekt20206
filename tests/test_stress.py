"""What the stress test found, kept as tests: half-saved scorecards, careers of
only abandoned games, odd names and junk files, and the faster versions of the
partnerships, badges and win-chance lines giving exactly the old answers."""

import random
import re
from pathlib import Path


import pytest
from streamlit.testing.v1 import AppTest

from ccstats import extras as E
from ccstats import partnerships as P
from ccstats import playerdeep as PD
from ccstats import seasonal as SN
from ccstats import teamdeep as TD
from ccstats import winprob as WP
from ccstats.loader import Career
from ccstats.local import CareerStore, Watcher

ROOT = Path(__file__).parent.parent
STRESS = Path(__file__).parent / "fixtures_stress"
FIXTURES = sorted((Path(__file__).parent / "fixtures").glob("*.txt"))
ABANDONED = sorted(p for p in STRESS.glob("*.txt") if "blast" not in p.name)
BLAST = next(STRESS.glob("*blast*.txt"))


@pytest.fixture(scope="module")
def career():
    return Career.build("Stress fixtures", [(p.name, p.read_bytes()) for p in FIXTURES])


@pytest.fixture(scope="module")
def abandoned():
    return Career.build("Stress abandoned", [(p.name, p.read_bytes()) for p in ABANDONED])


# --------------------------------------------------------------------------- half-saved scorecards
def test_a_cut_off_scorecard_is_not_counted():
    text = BLAST.read_text()
    c = Career.build("x", [("half.txt", text[: len(text) // 2].encode()), ("whole.txt", text.encode())])
    rep = {r.source: r for r in c.report}
    assert rep["half.txt"].status == "failed" and "incomplete" in rep["half.txt"].message
    assert rep["whole.txt"].status == "loaded" and len(c.matches) == 1


def test_the_watcher_reads_it_again_once_the_game_finishes_saving(tmp_path):
    folder = tmp_path / "Scorecards"
    folder.mkdir()
    text = BLAST.read_text()
    f = folder / BLAST.name
    f.write_text(text[: len(text) // 2])
    w = Watcher(CareerStore(tmp_path / "home"))
    res = w.create("Watched", folder)
    assert len(res.career.matches) == 0
    f.write_text(text)  # the game finishes writing it
    import os
    import time
    os.utime(f, (time.time() + 5, time.time() + 5))
    res = w.sync(str(folder))
    assert res is not None and len(res.career.matches) == 1
    assert res.career.matches.result.iloc[0]


def test_junk_files_are_reported_never_loaded():
    junk = [("empty.txt", b""), ("binary.txt", bytes(range(256)) * 20), ("html.txt", b"<html>no</html>"),
            ("latin1.txt", "Zoë café".encode("latin-1")), ("huge.txt", b"x" * 2_000_000), ("notes.csv", b"a,b")]
    c = Career.build("junk", junk)
    assert c.matches.empty
    assert {r.status for r in c.report} <= {"failed", "skipped"}


# --------------------------------------------------------------------------- a competition of only abandoned games
def test_only_abandoned_games(abandoned):
    m = abandoned.matches
    assert len(m) == 3 and (m.result_type == "no result").all()
    for sec in m.section.unique():
        ids = m[m.section == sec].match_id
        ur = TD.unit_ratings(abandoned, ids)
        assert ur.batting.notna().all() and ur.bowling.notna().all()  # nobody with nothing to rate is listed
        xi = SN.best_xi(abandoned, ids)
        assert xi.player.is_unique
        SN.season_review(abandoned, sec, m[m.section == sec].season.iloc[0], [])


@pytest.mark.parametrize("page", ["teams.py", "rankings.py", "review.py", "home.py", "stories.py", "records.py",
                                  "competitions.py", "fixtures.py", "insights.py", "analytics.py"])
def test_pages_open_on_only_abandoned_games(abandoned, page):
    at = AppTest.from_file(str(ROOT / "views" / page), default_timeout=180)
    at.session_state["career_obj"] = abandoned
    at.session_state[f"my_teams::{abandoned.name}"] = ["India", "England"]
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    assert not [w for w in at.warning if "couldn't be shown" in w.value], [w.value for w in at.warning]


# --------------------------------------------------------------------------- odd names
@pytest.mark.parametrize("page", ["player.py", "stat_by_stat.py", "teams.py", "records.py", "match.py", "stories.py"])
def test_odd_names_everywhere(page):
    files = []
    for p in FIXTURES[:12]:
        t = p.read_text()
        t = re.sub(r"\b([A-Z]) ([A-Z][a-z]+)\b", lambda mm: f"{mm.group(1)} {mm.group(2)}ë'<b>&", t, count=3)
        files.append((p.name, t.encode()))
    c = Career.build("Odd names", files)
    at = AppTest.from_file(str(ROOT / "views" / page), default_timeout=180)
    at.session_state["career_obj"] = c
    if page == "player.py":
        at.query_params["player"] = c.batting.player.iloc[0]
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    assert not [w for w in at.warning if "couldn't be shown" in w.value]


# --------------------------------------------------------------------------- faster, and exactly the same answers
def _slow_stands(career):
    """The partnerships the way they were first worked out (one innings at a time), to check the fast version."""
    rows = []
    bat = career.batting.sort_values(["match_id", "innings_no", "position"])
    fow = career.fow.sort_values(["match_id", "innings_no", "wicket"])
    for r in career.innings.itertuples():
        g = bat[(bat.match_id == r.match_id) & (bat.innings_no == r.innings_no)]
        fall = list(fow[(fow.match_id == r.match_id) & (fow.innings_no == r.innings_no)].score.astype(int))
        pairs = [None] * (len(fall) + 1)
        if len(g):
            did = g[g.did_bat]
            order = [(p, int(x), bool(o)) for p, x, o in zip(did.player, did.runs, did.out)]
            if not did.how_out.astype(str).str.contains("retired", case=False).any() and \
                    sum(o[2] for o in order) == len(fall) and fall == sorted(fall):
                pairs = P._solve(order, fall, int(r.runs))
        bounds = [0] + fall
        for k, score in enumerate(fall):
            p = pairs[k]
            rows.append((r.match_id, r.innings_no, k + 1, score - bounds[k], p[0] if p else "", p[1] if p else ""))
        if not r.all_out and len(fall) < 10:
            p = pairs[len(fall)] if len(pairs) > len(fall) else None
            rows.append((r.match_id, r.innings_no, len(fall) + 1, int(r.runs) - bounds[-1], p[0] if p else "",
                         p[1] if p else ""))
    return rows


def test_fast_partnerships_match_the_slow_way(career):
    fast = P._all_stands(career)
    slow = _slow_stands(career)
    assert len(fast) == len(slow)
    assert list(zip(fast.match_id, fast.innings_no, fast.wicket, fast.runs, fast.batter1, fast.batter2)) == slow


def test_badges_are_recounted_from_the_scorecards(career):
    a = PD.achievements(career)
    b = career.batting[career.batting.did_bat]
    w = career.bowling[career.bowling.balls > 0]
    kind = career.matches.set_index("match_id").format.map(lambda f: {"T20": "t20", "T20I": "t20", "The Hundred": "t20",
                                                                     "ODI": "one", "List A": "one"}.get(f, "multi"))
    assert (a.badge == "T20 hundred").sum() == ((b.match_id.map(kind) == "t20") & (b.runs >= 100)).sum()
    assert (a.badge == "Seven in an innings").sum() == ((w.match_id.map(kind) == "multi") & (w.wickets >= 7)).sum()
    mw = w[w.match_id.map(kind) == "multi"].groupby(["match_id", "player"]).wickets.sum()
    assert (a.badge == "Ten in a match").sum() == (mw >= 10).sum()
    assert a.date.is_monotonic_decreasing


def test_win_chance_lines_use_the_sections_states_correctly(career):
    for sec in career.matches.section.unique():
        ids = career.matches[career.matches.section == sec].match_id
        st_ = WP.states(career, ids)
        kind = WP.kind_of_ids(career, ids)
        for mid in list(ids)[:5]:
            own = WP.states(career, [mid])
            fast = WP.match_line(career, mid, st_, kind)
            if own.empty:
                assert fast.empty
                continue
            # the same states, worked out on their own, give the same line
            assert len(fast) == len(own)
            assert list(fast.innings_no) == list(own.innings_no) and list(fast.wickets) == list(own.wickets)


def test_honours_are_worked_out_once_and_cannot_be_changed_by_a_page(career):
    h1 = E.honours(career)
    h1.loc[:, "champions"] = "changed"
    h2 = E.honours(career)
    assert not (h2.champions == "changed").any()
    assert h2.equals(E.honours(career))


def test_random_typing_never_breaks_the_schedule_reader():
    from ccstats import fixtures as F
    rnd = random.Random(11)
    words = ["England", "3", "Tests", "away", "Jan", "2027", "ODI", "v", "@", "(h)", "T20", "World", "Cup", "12", "x", "∑"]
    for _ in range(2000):
        line = " ".join(rnd.choice(words) for _ in range(rnd.randint(0, 9)))
        rows, err = F.parse_line(line, "India", sorted(F.NATIONS))
        assert isinstance(rows, list) and isinstance(err, str)
        assert all(r["opponent"] != "India" for r in rows)

