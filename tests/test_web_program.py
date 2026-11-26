"""Stage 5, the program's pieces in a real browser: the tour of every section on the first start (Next through all of
it, or Skip), "What's new" in Settings with the "new" mark in the menu until it's seen, "Show me around again", and the
"Update ready" bar with its button. No browser errors, and everything fits."""

from __future__ import annotations

import pytest
from playwright import sync_api

from desktop import program as PG
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


@pytest.fixture
def pc(tmp_path):
    store, _, _ = make_pc(tmp_path, n=12, team="England")
    info = {"version": "2026.11.27.1", "date": "27 Nov 2026",
            "history": [{"version": "2026.11.27.1", "date": "27 Nov 2026", "notes": ["The Stats Pack is its own program."]}]}
    prog = PG.Program(info, tmp_path)
    s = Live(create_app(store, web=WEB, watch_every=0, program=prog))
    yield s, store, prog
    s.stop()


def opened(browser, live, path):
    pg = browser.new_page(viewport={"width": 1440, "height": 900})
    said: list[str] = []
    pg.on("console", lambda m: said.append(m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda e: said.append(str(e)))
    pg.goto(live.url(path), wait_until="networkidle")
    return pg, said


def test_the_tour_then_whats_new(browser, pc):
    live, store, prog = pc
    pg, said = opened(browser, live, "/")
    try:
        pg.wait_for_selector(".tourtip", timeout=60000)
        for k in range(11):
            assert f"{k + 1} of 11" in pg.text_content(".tourstep")   # (shown in capitals by the style)
            box = pg.locator(".tourtip").bounding_box()
            assert box["x"] >= 0 and box["x"] + box["width"] <= 1440 and box["y"] >= 0 and box["y"] + box["height"] <= 900
            pg.click(".tourtip button:has-text('Next')" if k < 10 else ".tourtip button:has-text('Done')")
        pg.wait_for_selector(".tour", state="detached")
        assert store.preferences().get("tour_done") is True
        # the "new" mark in the menu, until What's new is seen
        assert pg.locator(".rail .badge.new").count() == 1
        pg.goto(live.url("/settings?tab=What's new"), wait_until="networkidle")
        pg.wait_for_selector("text=Version 2026.11.27.1")
        pg.wait_for_function("!document.querySelector('.rail .badge.new')", timeout=30000)
        assert pg.evaluate(f"(\n{FIT}\n)()") == []
        pg.click("button:has-text('Show me around again')")
        pg.wait_for_selector(".tourtip", timeout=30000)
        pg.click(".tourtip button:has-text('Skip the tour')")
        pg.wait_for_selector(".tour", state="detached")
        assert said == [], said
    finally:
        pg.close()


def test_the_update_bar(browser, pc):
    live, store, prog = pc
    store.save_preference("tour_done", True)
    prog.offer = dict(version="2026.12.01.1", date="1 Dec 2026", notes=["Faster first open", "Smaller pages"],
                      file="x.zip", size=1, sha256="0")
    pg, said = opened(browser, live, "/fixtures")
    try:
        pg.wait_for_selector(".updatebar:has-text('Update ready')", timeout=60000)
        assert "version 2026.12.01.1" in pg.inner_text(".updatebar") and "1 more" in pg.inner_text(".updatebar")
        pg.wait_for_selector("body[data-ready='1']", timeout=60000)
        assert pg.evaluate(f"(\n{FIT}\n)()") == []
        # running from the code, the update can't be installed: said in plain words, nothing changed
        pg.click(".updatebar button:has-text('Update')")
        pg.wait_for_selector(".updatebar.bad:has-text(\"wasn't installed\")", timeout=30000)
        assert said == [], said
    finally:
        pg.close()
