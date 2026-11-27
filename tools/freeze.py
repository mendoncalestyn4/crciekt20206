"""The frozen copy of every number (stage 5, kept for good): every page's answer from the server, for a test career, kept
in tests/frozen/. tests/test_frozen.py asks the server the same questions on every test run and any number that moves
fails, unless the change is meant: then this is run again and the reason written in tests/frozen/CHANGES.md.

    python tools/freeze.py urls      # (rarely) open every page of the browser tests and note which answers they ask for
    python tools/freeze.py save "why the numbers changed"    # keep a new frozen copy, with the reason
    python tools/freeze.py save-long "why"                   # the same for the 20-season career (the weekly check)

The careers: "fixtures" (the test scorecards, played as India, as the browser tests have it; every test run) and
"long" (the 20-season made-up career, tests/longcareer.py; the weekly run)."""

from __future__ import annotations

import gzip
import json
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
FROZEN = ROOT / "tests" / "frozen"
URLS = FROZEN / "urls.json"
# answers that are about the moment, not the numbers: never frozen
VOLATILE = {"version", "built", "took", "seconds", "updated", "mtime", "saved", "when_saved", "checked_at", "now", "today_is",
            "elapsed", "ms", "age", "token", "folder", "path", "home", "file_time", "started", "last_check", "next_check",
            "backups", "size", "bytes"}
SKIP = ("/api/events", "/api/health", "/api/problems", "/api/warmup", "/api/program", "/api/settings", "/api/careers",
        "/api/backups", "/api/logo")


def site():
    """The fixture career as the browser tests have it: every test scorecard but the two played last, as India."""
    from server.app import create_app
    from serverkit import FIXTURES, LATEST, Live, make_pc
    tmp = Path(tempfile.mkdtemp(prefix="freeze-"))
    store, _, _ = make_pc(tmp, team="India", files=[f for f in FIXTURES if f not in LATEST])
    store.save_preference("tour_done", True)
    return Live(create_app(store, web=ROOT / "web" / "dist", watch_every=0))


def long_site(folder_files: list[Path]):
    """The 20-season made-up career (tests/longcareer.py) served the same way."""
    from server.app import create_app
    from serverkit import Live, make_pc
    tmp = Path(tempfile.mkdtemp(prefix="freeze-long-"))
    store, _, _ = make_pc(tmp, team="India", files=folder_files)
    store.save_preference("tour_done", True)
    return Live(create_app(store, web=ROOT / "web" / "dist", watch_every=0))


def long_urls() -> list[str]:
    """The answers that mean something on the made-up career (no test-career player, team or match named)."""
    return [u for u in json.loads(URLS.read_text()) if "name=" not in u and "team=" not in u and "/api/match/" not in u]


def long_files() -> list[Path]:
    import longcareer as LC
    d = Path(tempfile.mkdtemp(prefix="long-files-"))
    out = []
    for name, text in LC.generate(seasons=20):
        (d / name).write_text(text, encoding="utf-8")
        out.append(d / name)
    return out


def clean(x):
    """An answer with the moment-only fields taken out, numbers rounded to 6 places (no float noise)."""
    if isinstance(x, dict):
        return {k: clean(v) for k, v in sorted(x.items()) if k not in VOLATILE}
    if isinstance(x, list):
        return [clean(v) for v in x]
    if isinstance(x, float):
        return round(x, 6)
    return x


def ask(live, urls: list[str]) -> dict:
    import urllib.request
    out = {}
    for u in urls:
        for _ in range(240):            # the career is still being read: wait for it
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{live.port}{u}", timeout=600) as r:   # (as the page sent it)
                    out[u] = clean(json.loads(r.read()))
                break
            except Exception as e:  # noqa: BLE001
                if "503" in str(e) or "Connection" in str(e):
                    import time
                    time.sleep(0.5)
                    continue
                out[u] = {"error": str(e)}
                break
    return out


def find_urls() -> list[str]:
    from playwright import sync_api
    from serverkit import chrome
    from test_web import PAGES
    live = site()
    seen: set[str] = set()
    try:
        with sync_api.sync_playwright() as p:
            c = chrome()
            b = p.chromium.launch(**({"executable_path": c} if c else {}))
            for path in PAGES:
                pg = b.new_page(viewport={"width": 1440, "height": 900})
                pg.on("request", lambda r: seen.add(r.url.split(str(live.port), 1)[1])
                      if r.method == "GET" and "/api/" in r.url else None)
                pg.goto(live.url(path), wait_until="networkidle")
                try:
                    pg.wait_for_selector("body[data-ready='1']", timeout=60000)
                except Exception:  # noqa: BLE001
                    pass
                pg.close()
            b.close()
    finally:
        live.stop()
    return sorted(u for u in seen if not u.startswith(SKIP))


def main() -> None:
    what = sys.argv[1] if len(sys.argv) > 1 else ""
    FROZEN.mkdir(parents=True, exist_ok=True)
    if what == "urls":
        urls = find_urls()
        URLS.write_text(json.dumps(urls, indent=0) + "\n")
        print(f"{len(urls)} answers noted")
    elif what == "save":
        why = " ".join(sys.argv[2:]).strip()
        if not why:
            sys.exit("say why the numbers changed: python tools/freeze.py save \"...\"")
        live = site()
        try:
            got = ask(live, json.loads(URLS.read_text()))
        finally:
            live.stop()
        bad = [u for u, v in got.items() if isinstance(v, dict) and "error" in v]
        if bad:
            sys.exit(f"{len(bad)} answers failed, nothing frozen: {bad[:5]}")
        with gzip.open(FROZEN / "fixtures.json.gz", "wt", encoding="utf-8") as f:
            json.dump(got, f, sort_keys=True, separators=(",", ":"))
        with (FROZEN / "CHANGES.md").open("a", encoding="utf-8") as f:
            f.write(f"- {date.today():%d %B %Y}: {why}\n")
        print(f"{len(got)} answers frozen")
    elif what == "save-long":
        why = " ".join(sys.argv[2:]).strip()
        if not why:
            sys.exit("say why the numbers changed: python tools/freeze.py save-long \"...\"")
        live = long_site(long_files())
        try:
            got = ask(live, long_urls())
        finally:
            live.stop()
        bad = [u for u, v in got.items() if isinstance(v, dict) and "error" in v]
        if bad:
            sys.exit(f"{len(bad)} answers failed, nothing frozen: {bad[:5]}")
        with gzip.open(FROZEN / "long.json.gz", "wt", encoding="utf-8") as f:
            json.dump(got, f, sort_keys=True, separators=(",", ":"))
        with (FROZEN / "CHANGES.md").open("a", encoding="utf-8") as f:
            f.write(f"- {date.today():%d %B %Y} (the 20-season career): {why}\n")
        print(f"{len(got)} answers frozen for the 20-season career")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
