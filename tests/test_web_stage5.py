"""Stage 5's new pieces in a real browser, on the made-up IPL (two full seasons): On this day on My team (shown only on
a day with something to show), the Eras and Then and now tabs, the Career arc tab, and the Selection review. No browser
errors, and everything fits."""

from __future__ import annotations

import pytest
from playwright import sync_api

from server.app import create_app
from serverkit import Live, chrome, make_pc
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


@pytest.fixture(scope="module")
def demo_files(tmp_path_factory):
    from ccstats.demo_league import generate
    d = tmp_path_factory.mktemp("demo")
    out = []
    for n, t in generate((2026, 2027)):
        f = d / n
        f.write_text(t, encoding="utf-8")
        out.append(f)
    return out


def site(tmp_path, files, team):
    store, _, _ = make_pc(tmp_path, team=team, files=files)
    store.save_preference("tour_done", True)
    return Live(create_app(store, web=WEB, watch_every=0))


def opened(browser, live, path):
    pg = browser.new_page(viewport={"width": 1440, "height": 900})
    said: list[str] = []
    pg.on("console", lambda m: said.append(m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda e: said.append(str(e)))
    pg.goto(live.url(path), wait_until="networkidle")
    pg.wait_for_selector("body[data-ready='1']", timeout=120000)
    return pg, said


@pytest.mark.parametrize("team,shown", [("Delhi Capitals", True), ("Chennai Super Kings", False)])
def test_on_this_day_only_on_a_day_with_something(browser, tmp_path, demo_files, team, shown):
    live = site(tmp_path, demo_files, team)
    try:
        pg, said = opened(browser, live, "/")
        try:
            tile = pg.locator(".t:has(.tl:has-text('On this day'))")
            assert tile.count() == (1 if shown else 0)
            if shown:
                assert "1 year ago" in tile.inner_text() and tile.locator("a:has-text('Scorecard')").count() >= 1
            assert pg.evaluate(f"(\n{FIT}\n)()") == []
            assert said == [], said
        finally:
            pg.close()
    finally:
        live.stop()


def test_the_new_tabs_on_the_made_up_league(browser, tmp_path, demo_files):
    live = site(tmp_path, demo_files, "Delhi Capitals")
    try:
        for path, needs in (("/teams/Delhi Capitals?tab=Eras&section=Indian Premier League", "Every season"),
                            ("/teams/Delhi Capitals?tab=Then and now&section=Indian Premier League", "Who changed"),
                            ("/insights?tab=Career arc&section=Indian Premier League", "the usual curve"),
                            ("/?view=selection", "Selection")):
            pg, said = opened(browser, live, path)
            try:
                pg.wait_for_selector(f"text={needs}", timeout=60000)
                assert pg.evaluate(f"(\n{FIT}\n)()") == [], path
                assert said == [], (path, said)
            finally:
                pg.close()
    finally:
        live.stop()
