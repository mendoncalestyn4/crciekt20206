"""In a real browser: a page opened (a bookmark, a new tab) just as the game saves new scorecards opens as asked,
with the new matches in it; a page left open takes them in by itself and stays where it is.  Skipped where
Playwright and Chromium aren't installed."""
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from serverkit import chrome  # noqa: E402
from test_real_names import card  # noqa: E402

from ccstats import local as L  # noqa: E402

ROOT = Path(__file__).parent.parent
CHROME = chrome()
playwright = pytest.importorskip("playwright.sync_api")


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def settle(pg, t=2.0):
    for _ in range(600):
        if not pg.query_selector("[data-testid='stStatusWidget']"):
            break
        time.sleep(0.25)
    time.sleep(t)


def sidebar_matches(pg) -> str:
    for c in pg.query_selector_all("[data-testid='stSidebar'] [data-testid='stCaptionContainer']"):
        if c.inner_text().strip().endswith("matches"):
            return c.inner_text().strip()
    return ""


@pytest.fixture
def site(tmp_path):
    home, folder = tmp_path / "home", tmp_path / "Scorecards"
    folder.mkdir()
    (folder / "a.txt").write_text(card("T20", "Somerset", "Surrey", "T20 Blast", "4 Jul 2027"), encoding="utf-8")
    L.Watcher(L.CareerStore(home)).create("Mine", folder)
    port = free_port()
    srv = subprocess.Popen([sys.executable, "-m", "streamlit", "run", "app.py", "--server.port", str(port),
                            "--server.headless", "true"], cwd=ROOT, env=dict(os.environ, STATS_PACK_HOME=str(home)),
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.time() + 60
    while time.time() < deadline:
        try:
            socket.create_connection(("127.0.0.1", port), timeout=1).close()
            break
        except OSError:
            time.sleep(0.5)
    yield f"http://localhost:{port}", folder
    os.killpg(srv.pid, signal.SIGTERM)
    srv.wait(timeout=30)


def test_pages_open_as_asked_while_new_matches_arrive(site):
    base, folder = site
    with playwright.sync_playwright() as pw:
        try:
            br = pw.chromium.launch(**({"executable_path": CHROME} if CHROME else {}), args=["--no-sandbox"])
        except Exception as e:  # noqa: BLE001 - no browser on this machine
            pytest.skip(f"no Chromium for Playwright: {e}")
        try:
            for n, page in enumerate(("fixtures", "records"), start=2):
                (folder / f"{page}.txt").write_text(card("T20", "Surrey", "Somerset", "T20 Blast", f"1{n} Jul 2027"),
                                                    encoding="utf-8")
                pg = br.new_page()
                pg.goto(f"{base}/{page}", wait_until="networkidle", timeout=120000)
                settle(pg, 3)
                assert pg.url.rstrip("/").endswith(page), pg.url  # not sent to Home
                assert sidebar_matches(pg) == f"{n} matches"
                assert not pg.query_selector_all("[data-testid='stException']")
                pg.close()
            pg = br.new_page()
            pg.goto(f"{base}/honours", wait_until="networkidle", timeout=120000)
            settle(pg, 3)
            (folder / "open.txt").write_text(card("T20", "Somerset", "Surrey", "T20 Blast", "25 Jul 2027"),
                                             encoding="utf-8")
            t0 = time.time()
            while time.time() - t0 < 60 and sidebar_matches(pg) != "4 matches":
                time.sleep(1)
            assert sidebar_matches(pg) == "4 matches"
            assert pg.url.rstrip("/").endswith("honours"), pg.url
        finally:
            br.close()
