"""The speed work (your picks of 14 November) keeps every number exactly the same:

- answers kept on disk are read back identical, and only ever for the exact same scorecards, choices and site version
  (a changed scorecard or Data check choice changes the stamp, so nothing old is used);
- "redo only what changed" (matches added one batch at a time) gives what a full redo from scratch gives;
- the speed guard: once the site has got its pages ready, every page answers in under a second.
"""

import time

import pandas as pd
import pytest

from ccstats import keep as KEEP
from ccstats import partnerships as P
from ccstats.loader import Career
from server import cache as C
from server import playerpage as PP
from serverkit import FIXTURES, Live, make_pc


@pytest.fixture
def kept_dir(tmp_path):
    old = KEEP.DIR
    KEEP.DIR = tmp_path / "kept"
    KEEP.reset()
    yield KEEP.DIR
    KEEP.DIR = old
    KEEP.reset()


def build(files):
    c = Career.build("Speed", [(f.name, f.read_bytes()) for f in files])
    c.count_fielding = False
    return c


def test_stands_kept_on_disk_are_read_back_the_same(kept_dir):
    first = P.stands(build(FIXTURES), build(FIXTURES).matches.match_id)
    KEEP.save()
    assert list(kept_dir.glob("memo-stands-*.pickle"))
    KEEP.reset()                                   # a new start: nothing in memory
    again = build(FIXTURES)
    pd.testing.assert_frame_equal(P.stands(again, again.matches.match_id), first)


def test_matches_added_one_batch_at_a_time_give_what_a_full_redo_gives(kept_dir):
    """The answers kept from the earlier matches are reused when new ones arrive; the result is identical to working
    everything out from scratch with nothing kept."""
    half = len(FIXTURES) // 2
    step = build(FIXTURES[:half])
    P.stands(step, step.matches.match_id)          # the first half, kept
    step = step.add_files([(f.name, f.read_bytes()) for f in FIXTURES[half:]])
    step.count_fielding = False
    got = P.stands(step, step.matches.match_id)
    KEEP.DIR = None
    KEEP.reset()
    whole = build(FIXTURES)
    pd.testing.assert_frame_equal(got, P.stands(whole, whole.matches.match_id))
    for p in ["J Bethell", "K Rabada"]:
        assert PP.page(step, p, *PP.picks(step, p, "", "")) == PP.page(whole, p, *PP.picks(whole, p, "", ""))


def test_a_page_kept_on_disk_comes_back_the_same_without_working_it_out(kept_dir):
    c = build(FIXTURES)
    key = ("player", "J Bethell") + PP.picks(c, "J Bethell", "", "")
    page = C.kept(c, key, lambda: PP.page(c, "J Bethell", *key[2:]))
    assert C.save(c)
    KEEP.save()                                    # (tidying the kept sums never touches the kept answers)
    fresh = build(FIXTURES)                        # the next start: the same scorecards

    def never():
        raise AssertionError("worked out again although it was kept")
    assert C.kept(fresh, key, never) == page


def test_a_changed_scorecard_or_choice_is_never_given_old_answers(kept_dir):
    c = build(FIXTURES)
    C.kept(c, ("x",), lambda: "old")
    C.save(c)
    f = FIXTURES[0]
    text = f.read_text(errors="replace").replace("Man of the match:", "Man of the match:  ", 1)
    changed = Career.build("Speed", [(f.name, text.encode())] + [(g.name, g.read_bytes()) for g in FIXTURES[1:]])
    assert C.kept(changed, ("x",), lambda: "new") == "new"
    fixed = build(FIXTURES)
    fixed = fixed.with_fixes(type(fixed.fixes)(merges={"J Bethell": "J Bethel"}))
    assert C.kept(fixed, ("x",), lambda: "new") == "new"
    assert C.kept(build(FIXTURES), ("x",), lambda: "new") == "old"     # the very same: read back


def test_every_page_answers_in_under_a_second_once_ready(tmp_path, monkeypatch):
    """The speed guard: the site gets its pages ready by itself (the progress bar), with two helpers on other cores,
    then no page takes a second; and what the helpers worked out is what the server works out itself."""
    monkeypatch.setenv("STATS_PACK_HELPERS", "2")
    store, folder, _ = make_pc(tmp_path, n=len(FIXTURES), team="India")
    from server.app import create_app
    live = Live(create_app(store, watch_every=0.5))
    try:
        end = time.time() + 600
        while time.time() < end:
            w = live.json("/api/warmup")
            if w["total"] and not w["busy"]:
                break
            time.sleep(0.5)
        assert w["total"] > 0 and w["done"] == w["total"], w
        slow = []
        for path in ["/api/myteam", "/api/players", "/api/matches", "/api/team", "/api/teamvteam", "/api/preview",
                     "/api/planner", "/api/competition", "/api/season", "/api/review", "/api/honours",
                     "/api/rivalries", "/api/inbox", "/api/player?name=J Bethell", "/api/player?name=K Rabada"]:
            t = time.time()
            live.json(path)
            if time.time() - t > 1.0:
                slow.append((path, round(time.time() - t, 2)))
        assert slow == []
        # the helpers' answers equal the server's own: a player at the end of the list, worked out afresh here
        c = live.app.state.site.career()
        last = c.batting.groupby("player").match_id.nunique().sort_values(ascending=False, kind="stable").index[-1]
        key = ("player", last) + PP.picks(c, last, "", "")
        assert C.ready(c, key)
        assert C.kept(c, key, lambda: None) == PP.page(c, last, *key[2:])
    finally:
        live.stop()


def test_the_ready_to_read_copy_of_a_career_is_the_career_itself(tmp_path):
    """The second start reads the career from its ready-to-read copy: identical to reading it afresh; and a career
    whose file changed (a new match) is read afresh, never from the old copy."""
    store, folder, _ = make_pc(tmp_path, n=10, team="India")
    name = store.names()[0]
    first, _ = store.load(name)
    assert (store._dir(name) / "career.ready.pickle").is_file()
    second, _ = store.load(name)
    for t in ("matches", "innings", "batting", "bowling", "fow"):
        pd.testing.assert_frame_equal(getattr(second, t), getattr(first, t))
    assert second.texts == first.texts
    more = first.add_files([(f.name, f.read_bytes()) for f in FIXTURES[10:12]])
    store.save(more, store.load_settings(name)[1])
    third, _ = store.load(name)
    assert len(third.matches) == len(more.matches) > len(first.matches)


def test_a_logo_is_kept_by_the_browser_until_it_changes(tmp_path):
    """Logos made once and kept: the browser asks with the picture's fingerprint and gets a tiny "not changed" back."""
    import urllib.error
    import urllib.request
    from server.app import create_app
    store, folder, game = make_pc(tmp_path, n=4, team="England")
    live = Live(create_app(store, watch_every=0))
    try:
        url = live.url("/api/logo/team/England.png?size=48")
        with urllib.request.urlopen(url) as r:
            tag, body = r.headers["ETag"], r.read()
        assert tag and body[:4] == b"\x89PNG"
        with pytest.raises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(urllib.request.Request(url, headers={"If-None-Match": tag}))
        assert e.value.code == 304
    finally:
        live.stop()


def test_a_junk_competition_name_on_my_team_is_the_normal_page_at_once(tmp_path):
    """My team with a competition the team hasn't played in the address (a junk or old name) is the normal page, kept
    as one page: a second, different junk name is answered at once, not worked out again."""
    from server.app import create_app
    store, folder, _ = make_pc(tmp_path, n=len(FIXTURES), team="India")
    live = Live(create_app(store, watch_every=0))
    try:
        normal = live.json("/api/myteam")
        assert live.json("/api/myteam?section=null") == normal
        t = time.time()
        assert live.json("/api/myteam?section=%3Cscript%3E") == normal
        assert time.time() - t < 1.0
    finally:
        live.stop()
