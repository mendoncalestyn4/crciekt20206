"""The new site's stats server (server/): a real server on a free port of this computer, asked the way the website
asks. A career watching a Scorecards folder, with the game's logo files beside it, as on a real PC."""

import io
import json
import shutil
import socket
import time
import urllib.request

import numpy as np
import pytest
from PIL import Image

from ccstats.loader import Career
from ccstats.local import CareerSettings, CareerStore
from server import theme as TH
from server.__main__ import free_port
from server.app import Hub, create_app
from serverkit import FIXTURES, Live, make_pc

@pytest.fixture()
def pc(tmp_path):
    """A PC with Cricket Captain's Scorecards folder (20 matches so far), the game's logo files beside it, and a
    career watching the folder, played as England."""
    return make_pc(tmp_path)


@pytest.fixture()
def web(tmp_path):
    """A built website: index.html and one file in assets/."""
    d = tmp_path / "dist"
    (d / "assets").mkdir(parents=True)
    (d / "index.html").write_text("<!doctype html><title>Stats Pack</title><div id=root></div>")
    (d / "assets" / "app-1234.js").write_text("console.log('hi')")
    (d / "favicon.svg").write_text("<svg/>")
    return d


@pytest.fixture()
def live(pc, web):
    s = Live(create_app(pc[0], web=web, watch_every=0))
    yield s
    s.stop()


def test_careers_and_the_one_on_screen(live, pc):
    store = pc[0]
    assert live.json("/api/health") == {"ok": True, "site": "Stats Pack", "careers": 1}
    got = live.json("/api/careers")
    assert got["careers"] == ["My career"] and got["current"] == "My career"
    assert got["folders"] == [str(pc[1])]
    c = live.json("/api/career")
    assert c["name"] == "My career" and c["matches"] == 20
    assert c["my_teams"] == ["England"] and c["folder"] == str(pc[1])
    assert c["sections"][0] == "Vijay Hazare Trophy" and set(c["sections"]) == {
        "Vijay Hazare Trophy", "Ranji Trophy", "ODIs", "Tests", "T20 Blast", "Indian Premier League", "T20Is"}
    # a second career; choosing it is remembered for next time (the current site opens on it too)
    store.save(Career.build("Second", [(FIXTURES[30].name, FIXTURES[30].read_bytes())]), CareerSettings(name="Second"))
    assert live.post("/api/careers/current", {"name": "Second"})[0] == 200
    assert live.json("/api/career")["matches"] == 1 and store.last_used() == "Second"
    assert live.post("/api/careers/current", {"name": "Nobody's"})[0] == 404
    # changes only as JSON: a form posted by another web page is refused
    assert live.request("/api/careers/current", data=b"name=My+career", ctype="application/x-www-form-urlencoded")[0] == 415
    assert live.request("/api/careers/current", data=b'["My career"]', ctype="application/json")[0] == 415


def test_only_this_computer_by_its_own_name(live):
    """A page on the internet that renamed itself to this computer's address (DNS rebinding) is refused."""
    assert live.get("/api/health", host="localhost")[0] == 200
    assert live.get("/api/health", host="evil.example")[0] == 400


def test_your_colours(live, pc):
    t = live.json("/api/theme")
    assert t["nation"] == "England" and t["dark"] is False and t["page"] == "#eff3f9"
    assert live.json("/api/theme?nation=India") == TH.tokens("India")
    assert live.json("/api/theme?nation=none")["nation"] is None
    assert live.get("/api/theme?nation=Kent")[0] == 404
    assert live.json("/api/nations")["nations"][:3] == ["Afghanistan", "Australia", "Bangladesh"]


def test_logos_as_pictures_in_the_look_for_the_page(live):
    status, headers, body = live.get("/api/logo/team/England.png?size=48&page=dark")
    assert status == 200 and headers["Content-Type"] == "image/png"
    dark = Image.open(io.BytesIO(body)).convert("RGBA")
    status, _, body = live.get("/api/logo/team/England.png?size=48&page=light")
    light = Image.open(io.BytesIO(body)).convert("RGBA")

    def brightest(im):
        a = np.asarray(im, float)
        return a[..., :3].mean(axis=2)[a[..., 3] > 128].max()
    # England's navy badge is lifted on the dark page (look B) and shown as it is on a light one
    assert brightest(light) < 70 < 150 < brightest(dark)
    assert dark.size[0] > 96   # drawn at twice the size, for sharp edges
    # your colours (England's are light) decide when the page isn't given
    assert live.get("/api/logo/team/England.png?size=48")[2] == live.get("/api/logo/team/England.png?size=48&page=light")[2]
    assert live.get("/api/logo/comp/T20 World Cup.png?size=60")[0] == 200
    assert live.get("/api/logo/team/Kent.png?size=48")[0] == 404           # no picture: no logo, never another's
    # the website is told which names have a picture, so it never asks for one that isn't there
    assert live.json("/api/logos") == {"teams": ["England", "India"], "comps": ["T20 World Cup"]}
    assert live.get("/api/logo/team/England.png?size=5000")[0] == 400
    assert live.get("/api/logo/flag/England.png?size=48")[0] == 400


def test_the_style_guide_numbers(live):
    d = live.json("/api/styleguide")
    """England's latest: the 2027 World Cup (ODIs), the first Test against Pakistan as their latest series."""
    assert d["team"] == "England" and d["mine"] and d["missing"] == {}
    assert (d["section"], d["season"], d["format"]) == ("ODIs", "2027", "ODI")
    assert [(r["opp"], r["outcome"]) for r in d["this_season"]] == [("New Zealand", "W"), ("South Africa", "W")]
    assert d["series"]["story"]["headline"] == "England lead Pakistan 1–0" and not d["series"]["story"]["complete"]
    assert d["match"]["pom"]["headline"] == "B Fortuin does it all: 32 and 4 for 52 but England win"
    assert [c["innings_no"] for c in d["match_test"]["cards"]] == [1, 2, 3, 4]
    st = d["star"]
    assert st["player"] == "H Brook" and st["runs"] == 128 == sum(i["runs"] for i in st["innings"])
    assert st["running"] + st["from4"] + st["from6"] == 128 and st["how_out"] == {"bowled": 1} and st["outs"] == 1
    assert st["among"] == "ODIs batters, every season" and set(st["percentiles"]) >= {"Runs", "Average"}
    assert [r["runs"] for r in d["leaders"]["runs"][:3]] == [128, 127, 106]
    assert d["banner"][0]["record"]["won"] == 2 and d["banner"][0]["rank"] == 1


def test_the_website_and_its_pages(live):
    status, headers, body = live.get("/")
    assert status == 200 and b"<div id=root>" in body and headers["Cache-Control"] == "no-cache"
    assert live.get("/players/J Bethell")[2] == body          # every page of the site is the same index.html
    assert live.get("/assets/app-1234.js")[2] == b"console.log('hi')"
    assert live.get("/favicon.svg")[0] == 200
    assert live.get("/api/no-such-question")[0] == 404
    assert live.get("/../../etc/passwd")[2] == body           # never a file outside the website
    assert live.get("/assets/../../index.html")[0] in (200, 404)


def test_no_website_built_says_so(pc, tmp_path):
    s = Live(create_app(pc[0], web=tmp_path / "nothing", watch_every=0))
    try:
        status, _, body = s.get("/")
        assert status == 503 and b"isn't built yet" in body
        assert s.json("/api/health")["ok"]
    finally:
        s.stop()


def test_no_career_yet(tmp_path, web):
    store = CareerStore(tmp_path / "empty")
    s = Live(create_app(store, web=web, watch_every=0))
    try:
        assert s.json("/api/careers") == {"careers": [], "current": None, "folders": []}
        assert s.get("/api/career")[0] == 404 and s.get("/api/styleguide")[0] == 404
        assert s.json("/api/theme")["nation"] is None and s.json("/api/theme")["dark"] is True   # the night look
        # a career added meanwhile on the current site opens here too, without starting again
        store.save(Career.build("Added later", [(FIXTURES[0].name, FIXTURES[0].read_bytes())]), CareerSettings(name="Added later"))
        assert s.json("/api/careers")["current"] == "Added later"
        assert s.json("/api/career")["name"] == "Added later"
    finally:
        s.stop()


def test_new_matches_reach_the_open_page(pc, web):
    """The folder is checked every few seconds; a new scorecard reaches an open page at once, with any record it
    broke, and a file that can't be read is named."""
    store, folder, _ = pc
    s = Live(create_app(store, web=web, watch_every=0.2))
    try:
        req = urllib.request.Request(s.url("/api/events"))
        with urllib.request.urlopen(req, timeout=30) as stream:
            assert stream.headers["Content-Type"].startswith("text/event-stream")
            for f in FIXTURES[20:23]:
                shutil.copy(f, folder / f.name)
            (folder / "1 jan 2027-xxx v yyy (odi).txt").write_text("not a scorecard")
            seen, deadline = [], time.time() + 30
            while time.time() < deadline and not {"matches", "failed", "checked"} <= {e["type"] for e in seen}:
                line = stream.readline().decode()
                if line.startswith("data: "):
                    seen.append(json.loads(line[6:]))
        news = next(e for e in seen if e["type"] == "matches")
        assert news["career"] == "My career" and news["added"] == 3
        failed = [e for e in seen if e["type"] == "failed"]
        assert failed and failed[0]["files"][0]["file"].endswith("(odi).txt")
        assert any(e["type"] == "checked" and e["folders"] == 1 for e in seen)
        assert s.json("/api/career")["matches"] == 23        # the page asks again and has them
    finally:
        s.stop()


def test_a_page_that_lost_its_connection_catches_up():
    hub = Hub(keep=3)
    for i in range(5):
        hub.publish({"n": i})
    q = hub.subscribe(after=3)
    assert q.get_nowait() == (4, {"n": 3}) and q.get_nowait() == (5, {"n": 4}) and q.empty()
    old = hub.subscribe(after=0)   # only the last few are kept
    assert [old.get_nowait()[0] for _ in range(3)] == [3, 4, 5]
    hub.unsubscribe(q)
    hub.publish({"n": 5})
    assert q.empty() and old.get_nowait() == (6, {"n": 5})


def test_a_busy_port_is_skipped():
    with socket.socket() as busy:
        busy.bind(("127.0.0.1", 0))
        busy.listen()
        port = busy.getsockname()[1]
        assert free_port(port) != port


def test_search_lists_what_the_current_site_lists(live, pc):
    """Players, teams, competitions and matches (newest first): the very list the current site's search box shows."""
    from ui.search import ICONS, options
    items = live.json("/api/search")["items"]
    c = pc[0].load("My career")[0]
    # (the current site's box adds "· no matches yet" to a team that hasn't played; the new site shows it as `sub`)
    assert [f"{ICONS[i['kind']]} {i['label']}" + (" · no matches yet" if i["sub"].endswith("no matches yet") else "")
            for i in items] == list(options(c))
    assert {"kind": "team", "value": "Perth Scorchers", "label": "Perth Scorchers", "sub": "team · no matches yet"} in items
    assert [(i["kind"], i["value"]) for i in items] == list(options(c).values())
    matches = [i for i in items if i["kind"] == "match"]
    assert len(matches) == 20 and matches[0]["label"] == "18 Jan 2028 · Karnataka v Kerala CC · Final"
    assert {"kind": "player", "value": "J Bethell", "label": "J Bethell", "sub": "player"} in items
