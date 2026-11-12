"""A PC for the new site's tests: a Cricket Captain Scorecards folder with the game's logo files beside it, a career
watching it, and the stats server running for real on a free port (used by test_server.py and test_web.py)."""

import json
import os
import shutil
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import uvicorn
from PIL import Image

from ccstats.local import CareerStore, Watcher
from server.__main__ import free_port

FIXTURES = sorted((Path(__file__).parent / "fixtures").glob("*.txt"))


def chrome() -> str | None:
    """The Chromium for the browser tests: STATS_PACK_CHROME if set, else one already on this machine (the cloud
    machines keep one under /opt/pw-browsers, its folder named by version), else None for Playwright's own."""
    if os.environ.get("STATS_PACK_CHROME"):
        return os.environ["STATS_PACK_CHROME"]
    base = Path("/opt/pw-browsers")
    if not base.is_dir():
        return None
    return next((str(p) for p in [base / "chromium", *sorted(base.glob("chromium-*/chrome-linux*/chrome"))] if p.exists()), None)


def png(path, colour):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGBA", (40, 30), colour).save(path)


def played_in_order(folder):
    """File times in the order the matches were played (the game saves each scorecard as the match ends; the engine
    tells which match came last from them)."""
    for i, p in enumerate(sorted(folder.glob("*.txt"), key=by_date)):
        os.utime(p, (1_790_000_000 + i * 60, 1_790_000_000 + i * 60))


class Live:
    """A running server: get / post like the browser, from its own address."""

    def __init__(self, app):
        self.app = app
        self.port = free_port(18600)
        self.server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=self.port, log_level="error",
                                                    timeout_graceful_shutdown=1))
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.thread.start()
        for _ in range(200):
            if self.server.started:
                break
            time.sleep(0.02)
        assert self.server.started

    def url(self, path, host="127.0.0.1"):
        return f"http://{host}:{self.port}{urllib.parse.quote(path, safe='/?=&')}"

    def request(self, path, data=None, ctype=None, host="127.0.0.1", headers=None):
        req = urllib.request.Request(self.url(path), data=data, headers=dict(headers or {}))
        if host != "127.0.0.1":
            req.add_header("Host", f"{host}:{self.port}")
        if ctype:
            req.add_header("Content-Type", ctype)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, r.headers, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.headers, e.read()

    def get(self, path, **kw):
        return self.request(path, **kw)

    def json(self, path):
        status, _, body = self.get(path)
        assert status == 200, (path, status, body[:200])
        return json.loads(body)

    def post(self, path, payload):
        return self.request(path, data=json.dumps(payload).encode(), ctype="application/json")

    def stop(self):
        self.server.should_exit = True
        self.thread.join(10)


def by_date(f: Path) -> time.struct_time:
    return time.strptime(f.name.split("-")[0], "%d_%b_%Y")


# the two matches played last of all (the game saves a scorecard as each match ends): what a PC gets next
LATEST = sorted(FIXTURES, key=by_date)[-2:]


def make_pc(tmp_path, n=20, team="England", files=None):
    """A PC with Cricket Captain's Scorecards folder (the first n scorecards, or these files), the game's logo files
    beside it, and a career watching the folder, played as `team`. Returns (store, folder, game folder)."""
    game = tmp_path / "Cricket Captain 2026"
    folder = game / "Scorecards"
    folder.mkdir(parents=True)
    for f in (FIXTURES[:n] if files is None else files):
        shutil.copy(f, folder / f.name)
    played_in_order(folder)
    png(game / "editor" / "emblems" / "englandem.png", (18, 36, 96, 255))       # navy, like the dark page
    png(game / "editor" / "emblems" / "indiaem.png", (40, 90, 220, 255))
    png(game / "editor" / "complogos" / "internationalworldcup20overcl.png", (90, 0, 160, 255))
    store = CareerStore(tmp_path / "home")
    Watcher(store).create("My career", folder)
    s = store.load_settings("My career")[1]
    s.my_teams = [team]
    store.save_settings(s)
    return store, folder, game
