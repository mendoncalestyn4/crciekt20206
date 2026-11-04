"""Settings → Problems (server/problems.py): every problem the site hits while you use it (a part of a page that
couldn't be worked out, a question the server couldn't answer, a page that broke in the browser) is noted once, with
how often and when, kept on this PC, and given as a plain report to copy and send to be fixed."""

import json
import time

import pytest

from server import myteam
from server import problems as PR
from server.app import create_app
from serverkit import FIXTURES, Live, make_pc


@pytest.fixture()
def pc(tmp_path):
    return make_pc(tmp_path)


@pytest.fixture()
def web(tmp_path):
    d = tmp_path / "dist"
    (d / "assets").mkdir(parents=True)
    (d / "index.html").write_text("<!doctype html><title>Stats Pack</title><div id=root></div>")
    return d


@pytest.fixture()
def site(pc, web):
    s = Live(create_app(pc[0], web=web, watch_every=0))
    yield s
    s.stop()


def boom(*_):
    raise ZeroDivisionError("division by zero")


def test_nothing_noticed_on_a_good_career(site):
    got = site.json("/api/problems")
    assert (got["problems"], got["count"]) == ([], 0)
    assert got["report"].startswith("Stats Pack: problems the site noticed (0)")


def test_a_part_that_cant_be_worked_out_is_noted_once_and_counted(site, monkeypatch):
    monkeypatch.setattr(myteam, "latest", boom)
    for _ in range(3):
        page = site.json("/api/myteam")
        assert page["missing"]["latest"].startswith("Couldn't be worked out (ZeroDivisionError")
        assert page["banner"]   # the rest of the page is still there
    got = site.json("/api/problems")
    (p,) = got["problems"]
    assert (p["kind"], p["count"], p["career"]) == ("part", 3, "My career")
    assert p["what"] == "latest: Couldn't be worked out (ZeroDivisionError: division by zero)"
    assert p["where"].startswith("/api/myteam")
    assert got["count"] == 1
    assert "[part] latest: Couldn't be worked out" in got["report"] and "seen 3 times" in got["report"]


def test_a_question_the_server_cant_answer_gets_a_plain_answer_and_is_noted(site, monkeypatch):
    monkeypatch.setattr(myteam, "page", boom)
    status, _, body = site.get("/api/myteam?section=Tests")
    assert status == 500
    assert json.loads(body)["error"] == "Something went wrong working this out. It's noted in Settings → Problems."
    (p,) = site.json("/api/problems")["problems"]
    assert (p["kind"], p["what"], p["where"]) == ("server", "ZeroDivisionError: division by zero", "/api/myteam?section=Tests")
    assert "Traceback" in p["detail"] and "boom" in p["detail"]


def test_a_page_that_broke_in_the_browser_and_clearing(site):
    st, _, _ = site.post("/api/problems", {"report": {"where": "/players/J Bumrah", "what": "TypeError: x is undefined",
                                                      "detail": "at Chart (app.js:1:2)"}})
    assert st == 200
    site.post("/api/problems", {"report": {"where": "/matches", "what": "RangeError: bad"}})
    got = site.json("/api/problems")
    assert [p["what"] for p in got["problems"]] == ["RangeError: bad", "TypeError: x is undefined"]   # newest first
    assert got["problems"][1]["kind"] == "page" and got["problems"][1]["detail"] == "at Chart (app.js:1:2)"
    # clear one (once it's fixed), then the rest
    site.post("/api/problems", {"clear": [got["problems"][0]["id"]]})
    assert [p["what"] for p in site.json("/api/problems")["problems"]] == ["TypeError: x is undefined"]
    site.post("/api/problems", {"clear": True})
    assert site.json("/api/problems")["count"] == 0


@pytest.mark.parametrize("payload,status", [({}, 400), ({"clear": "all"}, 400), ({"clear": [1, 2]}, 400),
                                            ({"report": {"what": "  "}}, 400), ({"report": "boom"}, 400)])
def test_odd_requests_are_turned_away(site, payload, status):
    assert site.post("/api/problems", payload)[0] == status
    assert site.json("/api/problems")["count"] == 0


def test_kept_on_this_pc_across_restarts(pc, web):
    s = Live(create_app(pc[0], web=web, watch_every=0))
    try:
        s.post("/api/problems", {"report": {"where": "/inbox", "what": "Error: kept"}})
    finally:
        s.stop()
    assert json.loads((pc[0].root / "problems.json").read_text())[0]["what"] == "Error: kept"
    s = Live(create_app(pc[0], web=web, watch_every=0))
    try:
        assert [p["what"] for p in s.json("/api/problems")["problems"]] == ["Error: kept"]
    finally:
        s.stop()


def test_a_damaged_list_starts_again_empty(pc, web):
    (pc[0].root / "problems.json").write_text("{not json")
    s = Live(create_app(pc[0], web=web, watch_every=0))
    try:
        assert s.json("/api/problems")["count"] == 0
        s.post("/api/problems", {"report": {"what": "Error: after"}})
        assert s.json("/api/problems")["count"] == 1
    finally:
        s.stop()


def test_scorecards_that_couldnt_be_read_are_listed_but_a_match_still_being_saved_isnt(tmp_path, web):
    """Noted by the folder check as it finds them: the career keeps only the matches it could read, so they'd be lost
    otherwise. A scorecard the game is still saving (no result yet) is read again when it's finished: not a problem."""
    store, folder, _ = make_pc(tmp_path, n=3)
    s = Live(create_app(store, web=web, watch_every=0.2))
    try:
        (folder / "zz_broken.txt").write_text("this is not a scorecard")
        half = FIXTURES[5].read_text()
        (folder / FIXTURES[5].name).write_text(half[: half.index("Man of the match")].rsplit("\n", 3)[0])
        for _ in range(100):
            got = s.json("/api/problems")
            if got["count"]:
                break
            time.sleep(0.1)
        time.sleep(0.5)   # a second check finds nothing more
        got = s.json("/api/problems")
        (p,) = got["problems"]
        assert (p["kind"], p["where"], p["career"], p["count"]) == ("scorecard", "zz_broken.txt", "My career", 1)
        assert "[scorecard]" in got["report"] and "file: zz_broken.txt" in got["report"]
    finally:
        s.stop()


def test_the_list_keeps_the_newest_and_clips_long_text(tmp_path):
    p = PR.Problems(tmp_path / "p.json")
    for i in range(PR.LIMIT + 5):
        p.add("page", "/x", f"Error {i}")
    items = p.items()
    assert len(items) == PR.LIMIT and items[0]["what"] == f"Error {PR.LIMIT + 4}" and items[-1]["what"] == "Error 5"
    p.add("page", "/x", "E" * 10_000)
    assert len(p.items()[0]["what"]) == PR.TEXT


def test_failed_parts_are_found_anywhere_in_an_answer():
    data = {"missing": {"a": "Couldn't be worked out (KeyError: 'x')", "b": "Not enough matches yet"},
            "rows": [{"none": "Couldn't be worked out (ValueError: y)"}, {"ok": 1}]}
    assert PR.failed_parts(data) == [("a", "Couldn't be worked out (KeyError: 'x')"),
                                     ("rows[0].none", "Couldn't be worked out (ValueError: y)")]
