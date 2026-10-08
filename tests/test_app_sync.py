"""The site takes in new scorecards before it draws a page, so a page opened just as the game saves new matches
has them in it from the first draw.  (That the page opened is the one asked for is checked in a real browser, in
test_browser_sync.py: the test harness here keeps the page either way.)"""
import sys
from pathlib import Path

import streamlit as st
from streamlit.testing.v1 import AppTest

sys.path.insert(0, str(Path(__file__).parent))
from test_real_names import card  # noqa: E402

from ccstats import local as L  # noqa: E402

ROOT = Path(__file__).parent.parent


def test_a_page_opened_as_new_matches_arrive_opens_as_asked(tmp_path, monkeypatch):
    home, folder = tmp_path / "home", tmp_path / "Scorecards"
    folder.mkdir()
    monkeypatch.setenv("STATS_PACK_HOME", str(home))
    st.cache_resource.clear()  # the site's store of careers is made again, in this home
    (folder / "a.txt").write_text(card("T20", "Somerset", "Surrey", "T20 Blast", "4 Jul 2027"), encoding="utf-8")
    L.Watcher(L.CareerStore(home)).create("Mine", folder)
    (folder / "b.txt").write_text(card("T20", "Surrey", "Somerset", "T20 Blast", "9 Jul 2027"), encoding="utf-8")
    try:
        for n, (page, words) in enumerate((("views/fixtures.py", "Your schedule"), ("views/records.py", "The record books")),
                                          start=2):
            at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=120)
            at.switch_page(page)
            at.run()
            assert not at.exception, at.exception
            assert [t.value for t in at.title] == [words], page
            assert len(at.session_state["career_obj"].matches) == n  # the match saved just before is in
            (folder / f"c{len(page)}.txt").write_text(
                card("T20", "Somerset", "Surrey", "T20 Blast", f"1{len(page) % 9} Jul 2027"), encoding="utf-8")
    finally:
        st.cache_resource.clear()
