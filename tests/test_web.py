"""The new website in a real browser (Chromium, through Playwright), served by the real stats server from the built
site in web/dist: every page opens with nothing wrong in the browser's console, nothing spills out of its tile (the
approved fit rules, tests/fit_rules.js) at the usual screen widths and in light and dark colours, every logo draws,
the search box finds things, and new matches show up on an open page by themselves.

Needs Playwright and its Chromium (a developer's machine); they aren't part of the Stats Pack itself."""

import os
import re
import shutil
from pathlib import Path

import pytest

from server.app import create_app
from serverkit import FIXTURES, LATEST, Live, chrome, make_pc

sync_api = pytest.importorskip("playwright.sync_api")

WEB = Path(__file__).parent.parent / "web" / "dist"
FIT = (Path(__file__).parent / "fit_rules.js").read_text()
CHROME = chrome()
PAGES = ["/", "/inbox", "/style-guide", "/settings", "/players", "/players/J Bethell", "/players/J Bethell?view=overview",
         "/players/J Bethell?view=bowling", "/players/J Bethell?view=story", "/players/K Rabada", "/matches", "/teams", "/teams?tab=How they win", "/teams?tab=Season",
         "/teams?tab=Squad&venue=home", "/teams/England", "/teams/vs",
         "/teams/vs?which=any", "/teams/preview", "/teams/preview?tab=About them", "/teams/preview?tab=Your best XI v them", "/teams/planner", "/teams/planner?tab=Batting order", "/teams/planner?tab=Partnerships", "/teams/rivalries", "/seasons", "/seasons?event=Indian Premier League&season=2026", "/seasons?event=T20 Blast&season=2026", "/seasons/season", "/seasons/season?view=month", "/seasons/season?team=All teams", "/seasons/season?tab=Series tracker", "/seasons/season?tab=Season progress", "/seasons/review", "/seasons/review?points=ipl", "/seasons/honours", "/seasons/honours?tab=Trophy cabinets", "/fixtures", "/leaders", "/insights", "/no-such-page"]


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as p:
        try:
            b = p.chromium.launch(**({"executable_path": CHROME} if CHROME else {}))
        except Exception as e:  # noqa: BLE001 - no browser on this machine
            pytest.skip(f"no Chromium for Playwright: {e}")
        yield b
        b.close()


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    """The stats server with a career of every test scorecard but the two played last, played as India; the folder is
    checked every half second."""
    assert (WEB / "index.html").is_file(), "web/dist is missing: run npm run build in web/"
    store, folder, game = make_pc(tmp_path_factory.mktemp("pc"), team="India", files=[f for f in FIXTURES if f not in LATEST])
    s = Live(create_app(store, web=WEB, watch_every=0.5))
    yield s, folder
    s.stop()


def open_page(browser, site, path, width=1440):
    """Open a page and wait until it says it's ready; returns the page and what the console said."""
    live, _ = site
    pg = browser.new_page(viewport={"width": width, "height": 900})
    said: list[str] = []
    pg.on("console", lambda m: said.append(f"{m.type}: {m.text}") if m.type in ("error", "warning") else None)
    pg.on("pageerror", lambda e: said.append(f"error: {e}"))
    pg.goto(live.url(path), wait_until="networkidle")
    pg.wait_for_selector("body[data-ready='1']", timeout=30000)
    return pg, said


def fit_problems(pg) -> list[dict]:
    return pg.evaluate(f"(\n{FIT}\n)()")


@pytest.mark.parametrize("path", PAGES)
def test_every_page_opens_cleanly_and_fits(browser, site, path):
    pg, said = open_page(browser, site, path)
    try:
        assert said == [], said
        assert fit_problems(pg) == []
        assert pg.locator("nav.rail a.nav").count() == 10   # with the Inbox
        broken = pg.evaluate("[...document.images].filter(i => i.complete && i.naturalWidth === 0 && i.style.display !== 'none').length")
        assert broken == 0
    finally:
        pg.close()


@pytest.mark.parametrize("which", ["empty", "one match"])
def test_a_brand_new_career_opens_cleanly(browser, tmp_path_factory, which):
    """Found by the stress test on made-up saves: with no matches, the Scouting tab asked about a team that didn't exist
    (a failed request and a browser error); with one match, a long match name was cut short and ran into the next
    column, and a one-season rank label sat on the season's name. Every page must open cleanly and fit."""
    files = [] if which == "empty" else FIXTURES[:1]
    store, folder, _ = make_pc(tmp_path_factory.mktemp("new"), team="England" if which == "empty" else "Worcestershire",
                               files=files)
    live = Live(create_app(store, web=WEB, watch_every=0))
    try:
        paths = ["/", "/?view=scouting", "/inbox", "/players", "/matches", "/settings"]
        if files:
            mid = live.json("/api/matches")["matches"][0]["id"]
            first = live.json("/api/names")["names"]
            paths += [f"/matches/{mid}", f"/matches/{mid}?view=scorecard", f"/players/{first[0]}?view=story",
                      f"/players/{first[-1]}?view=story"]
        for path in paths:
            for width in (1280, 1920):
                pg, said = open_page(browser, (live, folder), path, width=width)
                try:
                    assert said == [], (path, width, said)
                    assert fit_problems(pg) == [], (path, width, fit_problems(pg))
                finally:
                    pg.close()
    finally:
        live.stop()


@pytest.mark.parametrize("width", [1280, 1366])
def test_long_team_names_in_the_match_list_are_never_cut_short(browser, site, width):
    """Found by the stress test on an IPL-only save: at 1280 wide, "Lucknow Super Giants won by 7 wickets" was cut
    short in Find a match. A long match name or result wraps instead, at every width."""
    pg, said = open_page(browser, site, "/matches?section=Indian Premier League", width)
    try:
        assert said == []
        res = pg.locator(".mli .res", has_text="Lucknow Super Giants won by")
        assert res.count() >= 1
        assert fit_problems(pg) == []
        assert pg.evaluate("[...document.querySelectorAll('.mli .res, .mli .how')].every(e => e.scrollWidth <= e.clientWidth + 1)")
        # and in the search box
        pg.keyboard.press("Control+k")
        pg.keyboard.type("Lucknow Super Giants v Royal")
        pg.wait_for_selector(".finder li .what")
        assert pg.locator(".finder li .what", has_text="Royal Challengers Bengaluru").count() >= 1
        assert fit_problems(pg) == []
        assert pg.evaluate("[...document.querySelectorAll('.finder li .what, .finder li .where')]"
                           ".every(e => e.scrollWidth <= e.clientWidth + 1)")
    finally:
        pg.close()


@pytest.mark.parametrize("path", ["/?team=Nobody FC", "/?view=scouting&team=Nobody FC"])
def test_an_old_link_to_a_team_not_in_this_career_opens_your_team(browser, site, path):
    """Found by the stress test (a link to Mumbai Indians in a career without them): your team's page instead of a
    "not found", with a note saying why, and nothing wrong in the console."""
    pg, said = open_page(browser, site, path)
    try:
        assert said == []
        assert pg.locator(".tt .tl", has_text="Not in this career").count() == 1
        assert "Nobody FC" in pg.locator(".t", has_text="Not in this career").text_content()
        assert fit_problems(pg) == []
    finally:
        pg.close()


def test_a_page_that_breaks_is_noted_and_shown_in_settings(browser, tmp_path_factory):
    """Settings → Problems (asked for on 4 November): an error on a page and a promise nobody caught are each noted
    once, with the page; the menu shows a red count on Settings; the list there gives a report to copy and send; and
    clearing empties it."""
    store, folder, _ = make_pc(tmp_path_factory.mktemp("problems"), n=5)
    live = Live(create_app(store, web=WEB, watch_every=0))
    try:
        pg, _ = open_page(browser, (live, folder), "/players")
        assert pg.locator(".rail .badge.bad").count() == 0
        pg.evaluate("""() => { setTimeout(() => { throw new TypeError("made-up: x is undefined"); }, 0);
                              Promise.reject(new RangeError("made-up rejection")); }""")
        pg.wait_for_function("() => document.querySelector('.rail .badge.bad')?.textContent === '2'", timeout=10000)
        got = live.json("/api/problems")["problems"]
        assert sorted(p["what"] for p in got) == ["RangeError: made-up rejection", "TypeError: made-up: x is undefined"]
        assert {(p["kind"], p["where"], p["career"]) for p in got} == {("page", "/players", "My career")}
        pg.close()

        pg, said = open_page(browser, (live, folder), "/settings")
        try:
            assert said == []
            assert pg.locator(".grid > .t").first.locator(".tt .tl").text_content() == "Problems"   # at the top
            assert pg.locator("table.probs tbody tr").count() == 2
            pg.context.grant_permissions(["clipboard-read", "clipboard-write"], origin=live.url("/").rstrip("/"))
            pg.locator("button:has-text('Copy for Claude')").click()
            pg.wait_for_selector(".probbar .note")
            copied = pg.evaluate("navigator.clipboard.readText()")
            assert "made-up rejection" in copied and "page: /players" in copied and "career: My career" in copied
            pg.locator("button:has-text('Show the report')").click()
            assert pg.locator("pre.probtext").first.text_content() == live.json("/api/problems")["report"]
            assert fit_problems(pg) == []
            pg.locator("button:has-text('Clear all')").click()
            pg.wait_for_function("() => !document.querySelector('table.probs') && !document.querySelector('.rail .badge.bad')",
                                 timeout=10000)
            assert live.json("/api/problems")["count"] == 0
        finally:
            pg.close()
    finally:
        live.stop()


@pytest.mark.parametrize("width", [1280, 1366, 1920])
@pytest.mark.parametrize("nation", ["", "England", "Australia", "none"])
def test_the_style_guide_fits_every_screen_in_every_colour(browser, site, width, nation):
    pg, said = open_page(browser, site, "/style-guide" + (f"?nation={nation}" if nation else ""), width)
    try:
        assert said == [] and fit_problems(pg) == []
        dark = pg.evaluate("!document.body.classList.contains('light')")
        assert dark == (nation in ("", "none"))   # India and the night look are dark; England and Australia light
    finally:
        pg.close()


def test_the_style_guide_draws_every_piece_from_the_career(browser, site):
    pg, _ = open_page(browser, site, "/style-guide")
    try:
        text = pg.inner_text("main")
        for piece in ("MOST RUNS", "MOST WICKETS", "EVERY INNINGS", "HOW THEY COMPARE", "WHERE THE RUNS COME FROM",
                      "MATCH SUMMARY", "SCORECARD", "PARTNERSHIPS", "THE SERIES", "MOST RUNS IN THE SERIES", "TEAM TABLE",
                      "EVERY PLAYER", "THE SEASON · MONTH BY MONTH", "RUNS OF RESULTS", "SERIES SCORE · TUG OF WAR",
                      "SERIES SCORE · THE LADDER", "OUR SCORE V THEIRS", "BATTING FIRST OR CHASING",
                      "AGAINST STRONGER AND WEAKER SIDES", "HOME, AWAY AND NEUTRAL", "MATCH-WINNERS", "WHERE IT GOES"):
            assert piece in text.upper(), piece
        for gone in ("EVERY MATCH BY MARGIN", "SERIES SCORE AFTER EACH MATCH"):   # dropped and replaced (plan, section 14)
            assert gone not in text.upper(), gone
        # the calendar: twelve months, April to March; the rings have their lists beside them
        assert pg.locator(".mt").count() == 12 and pg.locator(".mt-h .pn").first.inner_text().upper() == "APR"
        assert pg.locator(".dl-row").count() >= 4
        assert pg.locator("svg").count() >= 15            # the charts are drawn
        assert pg.locator("img.lg").count() > 10          # with the teams' logos
        # the innings switch shows the other innings' scorecard
        buttons = pg.locator(".itabs button")
        second = buttons.nth(1).inner_text()
        buttons.nth(1).click()
        assert "on" in (buttons.nth(1).get_attribute("class") or "")
        assert second.split(" · ")[-1].split(" ")[0] in pg.locator(".itabs + .grid .tl").nth(1).inner_text().title()
    finally:
        pg.close()


@pytest.fixture(scope="module")
def domestic_site(tmp_path_factory):
    """The stats server with every test scorecard, played as Karnataka (the Ranji Trophy and the Vijay Hazare Trophy)."""
    store, folder, _ = make_pc(tmp_path_factory.mktemp("pc_domestic"), team="Karnataka", files=FIXTURES)
    s = Live(create_app(store, web=WEB, watch_every=0))
    yield s, folder
    s.stop()


@pytest.mark.parametrize("width", [1280, 1920])
def test_a_domestic_side_gets_short_competition_names_and_fits(browser, domestic_site, width):
    """Found with a three-season save: a county or state side's long competition names ran into each other in the
    runs-of-results strip and squeezed its charts. Where there's little room a competition has its short name."""
    pg, said = open_page(browser, domestic_site, "/style-guide", width)
    try:
        assert said == [] and fit_problems(pg) == []
        strip = pg.inner_text(".strip")
        assert "Ranji" in strip and "Ranji Trophy" not in strip
        assert pg.locator(".mt").count() == 12
    finally:
        pg.close()


def test_a_name_in_a_sentence_or_on_a_chart_opens_the_player_menu(browser, site):
    """Any player's name opens the menu: inside a sentence (a "What it shows" line) and on a chart's axis, as in a list."""
    live, _ = site
    # a batter whose Nemesis chart names a bowler (the chart and its "What it shows" line both name them)
    for p in live.json("/api/players")["players"][:40]:
        page = live.json(f"/api/player?name={p['player']}")
        nemesis = (page.get("batting") or {}).get("nemesis")
        if nemesis and nemesis["rows"]:
            batter, bowler = p["player"], nemesis["rows"][0]["label"]
            break
    pg, said = open_page(browser, site, f"/players/{batter}?view=batting")
    try:
        tile = pg.locator(".t", has=pg.locator(".tt .tl", has_text=re.compile("^Nemesis$"))).first
        tile.scroll_into_view_if_needed()
        in_sentence = tile.locator(".explain [data-player]").first
        assert in_sentence.get_attribute("data-player") == bowler and in_sentence.inner_text() == bowler
        in_sentence.click()
        pg.wait_for_selector(".pm-pop")
        assert pg.inner_text(".pm-pop .pm-t") == bowler
        pg.keyboard.press("Escape")
        assert pg.locator(".pm-pop").count() == 0
        first, last = bowler.split(" ", 1)
        on_chart = tile.locator("svg text").filter(has_text=re.compile(rf"^{re.escape(first)}\s+{re.escape(last)}$")).first
        on_chart.click()
        pg.wait_for_selector(".pm-pop")
        assert pg.inner_text(".pm-pop .pm-t") == bowler
        pg.click(".pm-pop a:has-text('Player page')")
        pg.wait_for_url(f"**/players/{bowler.replace(' ', '%20')}")
        assert not [x for x in said if x.startswith("error")], said
    finally:
        pg.close()


def test_search_finds_a_player_and_opens_their_page(browser, site):
    pg, _ = open_page(browser, site, "/")
    try:
        pg.keyboard.press("Control+k")
        pg.fill(".finder input", "bethell")
        pg.wait_for_selector(".finder li")
        assert "J Bethell" in pg.inner_text(".finder li.on")
        pg.keyboard.press("Enter")
        pg.wait_for_url("**/players/J%20Bethell")
        # the address changes before the new page replaces the old one, whose "ready" mark is still up: wait for the player
        pg.wait_for_function("document.querySelector('main .hero') && document.querySelector('main').innerText.includes('J Bethell')")
        pg.wait_for_selector("body[data-ready='1']")
        assert "J Bethell" in pg.inner_text("main")
        pg.keyboard.press("Control+k")
        pg.fill(".finder input", "nothing like this")
        assert "Nothing matches" in pg.inner_text(".finder")
        pg.keyboard.press("Escape")
        assert pg.locator(".finder").count() == 0
    finally:
        pg.close()


def test_new_matches_show_up_on_an_open_page(browser, site):
    live, folder = site
    pg, said = open_page(browser, site, "/")
    try:
        before = live.json("/api/career")["matches"]
        asked: list[str] = []   # the page's questions to the server from now on
        pg.on("request", lambda r: asked.append(r.url) if "/api/myteam" in r.url else None)
        for f in LATEST:   # the next two matches the game saves
            shutil.copy(f, folder / f.name)
        pg.wait_for_selector(".toast", timeout=20000)
        # the folder is checked every half second here, so the two files can land in one check ("2 new matches") or
        # in two ("1 new match" twice): either way the news adds up to the two matches
        pg.wait_for_function("""() => [...(document.querySelector('.toasts')?.innerText || '')
            .matchAll(/(\\d+) new match(?:es)? added to My career/g)].reduce((a, m) => a + Number(m[1]), 0) === 2""",
                             timeout=20000)
        assert live.json("/api/career")["matches"] == before + 2
        # the open page asks again for its numbers (My team: the two new games aren't India's, so they're the same)
        for _ in range(100):
            if asked:
                break
            pg.wait_for_timeout(100)
        assert asked, "the open page didn't ask for its numbers again after the news"
        pg.wait_for_selector("body[data-ready]", timeout=20000)
        assert pg.locator(".rail .watch").count() == 1   # 'Watching' with the time of the last check
        assert said == []
    finally:
        pg.close()


def test_a_page_opened_by_its_address_and_the_colours_preview(browser, site):
    pg, said = open_page(browser, site, "/settings?nation=England")
    try:
        assert pg.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--page').trim()") == "#eff3f9"
        pg.select_option("#nation", "New Zealand")
        pg.wait_for_url("**/settings?nation=New%20Zealand")
        pg.wait_for_function("getComputedStyle(document.documentElement).getPropertyValue('--page').trim() === '#f1f1f2'")
        pg.click("nav.rail a.nav >> text=Players")   # the preview follows you round the site
        pg.wait_for_url("**/players?nation=New%20Zealand")
        assert said == []
    finally:
        pg.close()


def test_a_chart_tile_saves_itself_as_a_picture(browser, site, tmp_path):
    """Pointing at a tile with a chart shows "Save picture" (a tab on its top edge, clear of the title); a tile without
    a chart never shows it; the saved file is a PNG of the tile at twice its size."""
    import struct
    live, _ = site
    pg = browser.new_page(viewport={"width": 1440, "height": 900}, accept_downloads=True)
    said: list[str] = []
    pg.on("pageerror", lambda e: said.append(f"error: {e}"))
    pg.on("console", lambda m: said.append(f"{m.type}: {m.text}") if m.type == "error" else None)
    pg.goto(live.url("/teams"), wait_until="networkidle")
    pg.wait_for_selector("body[data-ready='1']", timeout=30000)
    charts = pg.locator(".t:has([data-chart])")
    plain = pg.locator(".t:not(:has([data-chart]))")
    assert charts.count() >= 3 and plain.count() >= 1
    p = plain.first
    p.evaluate("t => t.scrollIntoView({ block: 'center' })")
    p.hover(position={"x": 30, "y": 10})
    assert not p.locator("> .savepic").is_visible()
    tile = charts.first
    tile.evaluate("t => t.scrollIntoView({ block: 'center' })")
    tile.hover(position={"x": 30, "y": 10})
    btn = tile.locator("> .savepic")
    assert btn.is_visible()
    clear = tile.evaluate("""t => { const b = t.querySelector(':scope > .savepic').getBoundingClientRect(),
        h = t.querySelector(':scope > .tt'); return !h || b.bottom <= h.getBoundingClientRect().top + 0.5; }""")
    assert clear, "the button covers the tile's title row"
    w, h = tile.evaluate("t => { const r = t.getBoundingClientRect(); return [Math.ceil(r.width), Math.ceil(r.height)]; }")
    with pg.expect_download() as dl:
        btn.click()
    d = dl.value
    assert d.suggested_filename.endswith(".png") and re.fullmatch(r"[a-z0-9-]+\.png", d.suggested_filename)
    out = tmp_path / d.suggested_filename
    d.save_as(out)
    head = out.read_bytes()[:24]
    assert head[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II", head[16:24]) == (w * 2, h * 2)
    assert not said, said
    pg.close()


# --------------------------------------------------------------------------- the fix round's looks (14 November)
def _match_id(site, home, date):
    live, _ = site
    m = live.app.state.site.career().matches
    return m[(m.home == home) & (m.date == date)].match_id.iloc[0]


def test_double_click_never_selects_but_dragging_still_does(browser, site):
    """Your request of 14 November: double- or triple-clicking anywhere never turns text blue; dragging across text
    still selects it, so a name or a number can be copied; typing boxes work as usual."""
    pg, said = open_page(browser, site, "/players/J Bethell")
    try:
        title = pg.locator(".hero h1, .hero .title, h1").first
        title.dblclick()
        assert pg.evaluate("String(window.getSelection())") == ""
        title.click(click_count=3)
        assert pg.evaluate("String(window.getSelection())") == ""
        # a single press (the start of a drag) is never blocked, so dragging still selects; a press that is the second
        # or third click of a double or triple click is; typing boxes are left alone
        blocked = pg.evaluate("""() => { const el = document.querySelector('.part .note');
            const press = (detail) => { const e = new MouseEvent('mousedown', { detail, bubbles: true, cancelable: true });
                el.dispatchEvent(e); return e.defaultPrevented; };
            const box = document.createElement('input'); document.body.appendChild(box);
            const e = new MouseEvent('mousedown', { detail: 2, bubbles: true, cancelable: true }); box.dispatchEvent(e);
            const typed = e.defaultPrevented; box.remove();
            return [press(1), press(2), press(3), typed]; }""")
        assert blocked == [False, True, True, False], blocked
        assert said == [], said
    finally:
        pg.close()


def test_the_scorecard_has_batting_on_the_left_and_marks_the_best(browser, site):
    """Your requests of 14 November: batting on the left, bowling on the right; a ★ by each innings' best batter and
    best bowler; the player of the match's 🏆 by his name, his rows shaded only where he earned it."""
    mid = _match_id(site, "Kolkata Knight Riders", "2026-05-16")
    pg, said = open_page(browser, site, f"/matches/{mid}?view=scorecard")
    try:
        bat = pg.locator(".t:has(.tl:text-matches('^Batting'))").first.bounding_box()
        bowl = pg.locator(".t:has(.tl:text-matches('^Bowling'))").first.bounding_box()
        assert bat["x"] < bowl["x"], (bat, bowl)
        assert pg.locator(".star").count() >= 2
        shaded = pg.evaluate("""[...document.querySelectorAll('tr.me')].map(r => r.textContent)""")
        assert all("🏆" in s for s in shaded), shaded
        assert said == [], said
    finally:
        pg.close()


def test_the_player_page_tabs_each_show_their_own_kind(browser, site):
    """Your answer of 14 November: Overview, Batting, Bowling and Story; Batting shows only batting (country by country
    included), Bowling only bowling; a bowler's page opens on Bowling; the tile's format tick boxes count formats
    together."""
    live, _ = site
    bowler = "K Rabada"
    d = live.json(f"/api/player?name={bowler}")
    assert d["tabs"][0] == "Overview" and d["tabs"][-1] == "Story" and d["open"] == "Bowling"
    pg, said = open_page(browser, site, f"/players/{bowler}")
    try:
        titles = pg.evaluate("[...document.querySelectorAll('.t .tl')].map(e => e.textContent)")
        assert any(t.startswith("Bowling · every competition") for t in titles) and not any(t.startswith("Batting ·") for t in titles)
        pg.locator(".itabs button", has_text="Batting").first.click()
        pg.wait_for_selector("body[data-ready='1']")
        titles = pg.evaluate("[...document.querySelectorAll('.t .tl')].map(e => e.textContent)")
        assert any(t.startswith("Batting · every competition") for t in titles)
        assert not any("Bowling" in t and "every competition" in t for t in titles)
        assert said == [], said
    finally:
        pg.close()
    # a player with more than one competition: ticking a second one counts both on the tile
    many = next(p for p in live.json("/api/players")["players"] if len(p["sections"]) >= 2)
    secs = many["sections"][:2]
    part = live.json(f"/api/player_part?name={many['player']}&part=countries&sections={secs[0]}|{secs[1]}")
    assert part["sections"] == secs and part["label"] == " + ".join(secs)


def test_find_a_player_keeps_each_name_in_its_own_column(browser, site):
    """Found by you (14 November): searching "smith" squeezed the names into a column a letter or two wide (a team
    with no logo let the name slide into the logo's place). Every name keeps its column and never breaks inside a
    word, at every width."""
    for width in (1280, 1920):
        pg, said = open_page(browser, site, "/players", width)
        try:
            pg.locator("input.typed").fill("a")
            pg.wait_for_selector(".pli")
            # no name squeezed: each is at least as wide as its longest word (a name the width of a letter or two was the bug)
            narrow = pg.evaluate("[...document.querySelectorAll('.pli .pn')].filter(e => e.getBoundingClientRect().width < 60).map(e => e.textContent)")
            assert narrow == [], narrow
            assert said == [], said
        finally:
            pg.close()
