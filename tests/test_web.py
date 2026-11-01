"""The new website in a real browser (Chromium, through Playwright), served by the real stats server from the built
site in web/dist: every page opens with nothing wrong in the browser's console, nothing spills out of its tile (the
approved fit rules, tests/fit_rules.js) at the usual screen widths and in light and dark colours, every logo draws,
the search box finds things, and new matches show up on an open page by themselves.

Needs Playwright and its Chromium (a developer's machine); they aren't part of the Stats Pack itself."""

import os
import shutil
from pathlib import Path

import pytest

from server.app import create_app
from serverkit import FIXTURES, LATEST, Live, make_pc

sync_api = pytest.importorskip("playwright.sync_api")

WEB = Path(__file__).parent.parent / "web" / "dist"
FIT = (Path(__file__).parent / "fit_rules.js").read_text()
# a Chromium already on this machine (the cloud machines keep one under /opt/pw-browsers, its folder named by version)
CHROME = next((str(p) for p in [Path("/opt/pw-browsers/chromium"), *sorted(Path("/opt/pw-browsers").glob("chromium-*/chrome-linux*/chrome"))]
               if p.exists()), None) if Path("/opt/pw-browsers").is_dir() else None
PAGES = ["/", "/inbox", "/style-guide", "/settings", "/players", "/players/J Bethell", "/matches", "/teams", "/seasons", "/fixtures",
         "/leaders", "/insights", "/no-such-page"]


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
