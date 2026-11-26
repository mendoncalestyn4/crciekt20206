"""Stage 4 in a real browser, clicked as you would: adding a series and a tournament, typed lines, changing and
deleting, undo from the list of recent changes, goals (suggested and from the form), a series note; Settings
(renaming a career, the teams question, a backup and a restore, the full reset asked twice); Data check (the fix
preview, a change made in the background, then undone); the first start with the demo league. No browser errors at
any step, and every page still fits."""

from __future__ import annotations

import re

import pytest
from playwright import sync_api

from server.app import create_app
from serverkit import FIXTURES, Live, chrome, make_pc
from test_web import FIT, WEB

CHROME = chrome()


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as p:
        try:
            b = p.chromium.launch(**({"executable_path": CHROME} if CHROME else {}))
        except Exception as e:  # noqa: BLE001
            pytest.skip(f"no Chromium for Playwright: {e}")
        yield b
        b.close()


@pytest.fixture
def pc(tmp_path):
    store, folder, game = make_pc(tmp_path, team="England", files=FIXTURES)
    s = Live(create_app(store, web=WEB, watch_every=0))
    yield s, store
    s.stop()


def open_page(browser, live, path):
    pg = browser.new_page(viewport={"width": 1440, "height": 900})
    said: list[str] = []
    pg.on("console", lambda m: said.append(f"{m.type}: {m.text}") if m.type == "error" else None)
    pg.on("pageerror", lambda e: said.append(f"error: {e}"))
    pg.goto(live.url(path), wait_until="networkidle")
    pg.wait_for_selector("body[data-ready='1']", timeout=60000)
    return pg, said


def pick(pg, label, option):
    """Choose from one of the site's dropdowns by its label."""
    pg.locator(".drop", has=pg.locator(".droplab", has_text=re.compile(f"^{re.escape(label)}$"))).first.locator(".dropbtn").click()
    pg.locator(".dropmenu .droprow button", has_text=re.compile(f"^{re.escape(option)}")).first.click()


def said_ok(pg, text):
    pg.wait_for_selector(f".saidok:has-text('{text}')", timeout=60000)


def test_fixtures_forms_end_to_end(browser, pc):
    live, store = pc
    pg, said = open_page(browser, live, "/fixtures?tab=Add matches")
    try:
        pick(pg, "Opponent", "India")
        pick(pg, "Format", "Test")
        pick(pg, "How many matches", "3")
        pick(pg, "Where", "Away")
        pg.wait_for_selector(".note:has-text('Adds: v India · 3 Tests · away')", timeout=10000)   # named by the server as you pick
        pg.click("button:has-text('Add series')")
        said_ok(pg, "Added v India")
        assert len(store.load_settings("My career")[1].fixtures) == 3
        # a tournament
        pick(pg, "What are you adding?", "Tournament")
        pg.click("button:has-text('Add tournament')")
        said_ok(pg, "Added T20 World Cup")
        # typed lines: read, then add
        pg.fill("textarea.typed", "Australia 2 ODIs home Mar 2031")
        pg.click("button:has-text('Read these lines')")
        pg.wait_for_selector("button:has-text('Add these 1')")
        pg.click("button:has-text('Add these 1')")
        said_ok(pg, "Added 2 matches")
        assert len(store.load_settings("My career")[1].fixtures) == 3 + 1 + 2
        # change the Tests to 2 at home, delete the ODIs, then undo both from the list
        pg.click(".itabs button:has-text('Change or delete')")
        pg.wait_for_selector(".fxitem")
        item = pg.locator(".fxitem", has_text="v India")
        item.locator("button:has-text('Change')").click()
        pick(pg, "How many matches", "2")
        pick(pg, "Where", "Home")
        pg.click(".editbox button:has-text('Save')")
        said_ok(pg, "Changed to")
        assert len([r for r in store.load_settings("My career")[1].fixtures if r["format"] == "Test"]) == 2
        pg.locator(".fxitem", has_text="v Australia").locator("button:has-text('Delete')").click()
        pg.click("button:has-text('Yes, delete it')")
        said_ok(pg, "Deleted")
        assert not [r for r in store.load_settings("My career")[1].fixtures if r["format"] == "ODI"]
        idle = "![...document.querySelectorAll('.hist button')].some(b => b.disabled)"
        for k in range(2):
            pg.wait_for_function(idle, timeout=30000)        # the page as it now stands (buttons wait for it)
            before = pg.locator(".hist button:has-text('Undo')").count()
            pg.locator(".hist button:has-text('Undo')").first.click()
            pg.wait_for_function(f"(() => {{ const u = [...document.querySelectorAll('.hist button')].filter(b => b.textContent.includes('Undo'));"
                                 f" return u.length === {before - 1} && !u.some(b => b.disabled); }})()", timeout=30000)
            assert "can't be undone" not in pg.content()
        fx = store.load_settings("My career")[1].fixtures
        assert len([r for r in fx if r["format"] == "ODI"]) == 2 and len([r for r in fx if r["format"] == "Test"]) == 3
        # goals: one suggested, one from the form, then removed
        pg.click(".itabs button:has-text('Goals')")
        pg.wait_for_selector("text=Add a goal")
        if pg.locator("button:has-text('Add all')").count():
            pg.click("button:has-text('Add all')")
            said_ok(pg, "goal")
        pick(pg, "Goal", "Win matches in a row")
        pg.click("button:has-text('Add goal')")
        said_ok(pg, "Goal added")
        n = len(store.load_settings("My career")[1].goals)
        assert n >= 1
        pg.locator(".goal button:has-text('Remove')").first.click()
        said_ok(pg, "Goal removed")
        assert len(store.load_settings("My career")[1].goals) == n - 1
        # every tab still opens cleanly and fits
        for tab in ("Schedule", "Series", "Calendar", "WTC race", "Milestones"):
            pg.click(f".itabs button:has-text('{tab}')")
            pg.wait_for_selector("body[data-ready='1']", timeout=60000)
            assert pg.evaluate(f"(\n{FIT}\n)()") == [], tab
        assert said == [], said
    finally:
        pg.close()


def test_settings_end_to_end(browser, pc):
    live, store = pc
    pg, said = open_page(browser, live, "/settings")
    try:
        pg.locator("tr", has_text="My career").locator("button:has-text('Rename')").click()
        pg.fill("input[aria-label='New name']", "England save")
        pg.locator("tr", has=pg.locator("input[aria-label='New name']")).locator("button:has-text('Save')").click()
        said_ok(pg, "Renamed")
        assert store.names() == ["England save"]
        pg.click(".itabs button:has-text('Backups')")
        pg.click("button:has-text('Back up now')")
        said_ok(pg, "Backed up")
        pg.locator(".hist button:has-text('Restore')").first.click()
        pg.click("button:has-text('Yes, restore')")
        said_ok(pg, "Restored")
        assert any("before-restore" in p.name for p, _ in store.backups("England save"))
        # the teams question when none are picked: shown, then saved
        st = store.load_settings("England save")[1]
        st.my_teams, st.teams_asked = [], False
        store.save_settings(st)
        pg.goto(live.url("/"), wait_until="networkidle")
        pg.wait_for_selector(".modal:has-text('Which teams do you play as?')", timeout=60000)
        pg.fill(".modal input[aria-label='Your teams']", "Engl")
        pg.locator(".modal .found button", has_text=re.compile("^England$")).click()
        pg.click(".modal button:has-text('Save')")
        pg.wait_for_selector(".modal", state="detached", timeout=30000)
        assert store.load_settings("England save")[1].my_teams == ["England"]
        assert said == [], said
    finally:
        pg.close()


def test_full_reset_and_the_first_start_with_the_demo(browser, pc):
    live, store = pc
    pg, said = open_page(browser, live, "/settings")
    try:
        pg.click("button:has-text('Delete all careers and backups')")
        pg.fill("input[aria-label='Type DELETE EVERYTHING']", "DELETE EVERYTHING")
        pg.click("button:has-text('Delete everything')")
        pg.wait_for_selector("text=Start a career", timeout=60000)
        assert store.names() == []
        pg.goto(live.url("/"), wait_until="networkidle")
        pg.wait_for_selector("text=Try the demo league", timeout=60000)
        pg.click("button:has-text('Try the demo league')")
        for _ in range(300):
            if store.names():
                break
            pg.wait_for_timeout(100)
        assert store.names() == ["Demo IPL (made-up results)"]
        assert said == [] or all("404" in x for x in said), said     # no career yet: the career question answers 404
    finally:
        pg.close()


def test_data_check_end_to_end(browser, pc):
    live, store = pc
    pg, said = open_page(browser, live, "/settings/data-check?tab=Games left out")
    try:
        c, _ = store.load("My career")
        n = len(c.matches)
        pg.fill(".editbox input.typed", c.matches.sort_values("date").home.iloc[-1])
        pg.locator(".editbox .found button").first.click()
        pg.click("button:has-text('Leave it out')")
        pg.wait_for_selector(".saidok:has-text('A backup of the career was made first')", timeout=120000)
        assert len(store.load("My career")[0].matches) == n - 1
        pg.click(".itabs button:has-text('Your changes')")
        pg.wait_for_selector(".hist button:has-text('Undo')")
        pg.click(".hist button:has-text('Undo')")
        pg.wait_for_selector(".saidok:has-text('Undone: that match counts again')", timeout=120000)
        c2, _ = store.load("My career")
        assert len(c2.matches) == n
        # the fix preview before a join: numbers before and after, nothing changed until the click
        pg.click(".itabs button:has-text('Player with two names')")
        pg.wait_for_selector("body[data-ready='1']")
        names = sorted(set(c.batting.player))
        a, b = names[0], names[1]
        pg.locator(".editbox .drop", has_text="This name").locator("input").fill(a)
        pg.locator(".editbox .found button", has_text=re.compile(f"^{re.escape(a)}$")).first.click()
        pg.locator(".editbox .drop", has_text="same player as").locator("input").fill(b)
        pg.locator(".editbox .found button", has_text=re.compile(f"^{re.escape(b)}$")).first.click()
        pg.wait_for_selector("text=What this does to the numbers")
        pg.wait_for_selector(".editbox table")
        assert store.load("My career")[0].fixes.merges == {}
        assert pg.evaluate(f"(\n{FIT}\n)()") == []
        assert said == [], said
    finally:
        pg.close()
