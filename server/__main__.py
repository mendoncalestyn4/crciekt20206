"""Start the new site:  python -m server  [--port 8601] [--no-browser]

It runs only on this computer (127.0.0.1). The browser opens on it by itself; keep the window open while you use it."""

from __future__ import annotations

import argparse
import socket
import sys
import threading
import time
import webbrowser

import uvicorn

from .app import create_app

PORT = 8601   # the current site is on 8501; the new one sits next to it


def free_port(start: int, tries: int = 50) -> int:
    """The first port from `start` that nothing else on this computer is using."""
    for port in range(start, start + tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise SystemExit(f"No free port between {start} and {start + tries - 1}: close another program and try again.")


def open_when_ready(url: str, port: int) -> None:
    for _ in range(100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                webbrowser.open(url)
                return
        time.sleep(0.1)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="python -m server", description="The Stats Pack's new site (preview).")
    ap.add_argument("--port", type=int, default=PORT, help="the port to use (the next free one if it's taken)")
    ap.add_argument("--no-browser", action="store_true", help="don't open the browser")
    args = ap.parse_args(argv)
    port = free_port(args.port)
    url = f"http://127.0.0.1:{port}/"
    print(f"\n  Stats Pack (new site, preview) is running at {url}\n"
          "  Keep this window open while you use it. Close it (or press Ctrl+C) to stop.\n", flush=True)
    if not args.no_browser:
        threading.Thread(target=open_when_ready, args=(url, port), daemon=True).start()
    uvicorn.run(create_app(), host="127.0.0.1", port=port, log_level="warning", timeout_graceful_shutdown=2)


if __name__ == "__main__":
    main(sys.argv[1:])
