"""The program itself: "Cricket Captain Stats Pack.exe" (your answers of 26 November).

- Opens the site in its own window (Edge or Chrome as an app window: no address bar, no tabs), or the normal browser
  when neither is there.
- One copy only: opening it again while it runs brings you back to the copy already running instead of starting a
  second one.
- Stops by itself a minute after its last window closes.
- A clear message window, saying what happened and what to do, if it can't start.
- Looks for an update each time it opens (updates.py); "What's new" and the update button are in Settings.

    Cricket Captain Stats Pack.exe [--open /page] [--no-window] [--check]

`--check` starts it, asks it one question and stops (the test on GitHub's Windows machine that the program runs)."""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

from . import updates as UP

NAME = "Cricket Captain Stats Pack"
IDLE_STOP = 60        # seconds after the last window closes
FIRST_WAIT = 180      # seconds to wait for the first window before giving up on it


def build_info() -> dict:
    """The version and its notes, written when the program is built (build.json beside this file); "dev" when it
    runs from the code."""
    f = Path(__file__).resolve().parent / "build.json"
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) and d.get("version") else {"version": "dev", "history": []}
    except (OSError, ValueError):
        return {"version": "dev", "history": []}


# --------------------------------------------------------------------------- messages and the window
def message(title: str, text: str) -> None:
    """A Windows message box (or the console elsewhere). For the checks only, STATS_PACK_MESSAGE_TO names a file the
    message is written to instead (a box would wait for a click no one makes)."""
    to = os.environ.get("STATS_PACK_MESSAGE_TO")
    if to:
        with open(to, "a", encoding="utf-8") as f:
            f.write(f"{title}: {text}\n")
        return
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, text, title, 0x40 | 0x10000)   # information, kept on top
            return
        except Exception:  # noqa: BLE001
            pass
    print(f"{title}: {text}", file=sys.stderr)


def browsers() -> list[Path]:
    """Where Edge and Chrome live on Windows (Edge comes with every Windows 10 and 11)."""
    out = []
    for env in ("PROGRAMFILES(X86)", "PROGRAMFILES", "LOCALAPPDATA"):
        base = os.environ.get(env)
        if base:
            out += [Path(base) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
                    Path(base) / "Google" / "Chrome" / "Application" / "chrome.exe"]
    return [p for p in out if p.exists()]


def open_window(url: str, home: Path) -> None:
    """The site in its own app window; the normal browser if there's no Edge or Chrome."""
    import subprocess
    for exe in browsers():
        try:
            subprocess.Popen([str(exe), f"--app={url}", f"--user-data-dir={home / 'window'}", "--window-size=1500,950",
                              "--no-first-run", "--no-default-browser-check"], close_fds=True)
            return
        except OSError:
            continue
    webbrowser.open(url)


# --------------------------------------------------------------------------- one copy only
def lock_file(home: Path) -> Path:
    return home / "running.json"


def running(home: Path) -> dict | None:
    """The copy already running ({port, pid}), if it answers."""
    try:
        d = json.loads(lock_file(home).read_text(encoding="utf-8"))
        with urllib.request.urlopen(f"http://127.0.0.1:{int(d['port'])}/api/health", timeout=3) as r:
            if json.loads(r.read()).get("site") == "Stats Pack":
                return d
    except Exception:  # noqa: BLE001 - no copy running (or an old file left by one that stopped)
        return None
    return None


def bring_back(d: dict, home: Path, page: str) -> None:
    """Opening the program again while it runs: the window it has is asked to come forward; if it has none open, a
    window opens on it."""
    base = f"http://127.0.0.1:{int(d['port'])}"
    try:
        req = urllib.request.Request(base + "/api/program", data=json.dumps({"action": "focus"}).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=3) as r:
            if json.loads(r.read()).get("windows", 0) > 0:
                return
    except Exception:  # noqa: BLE001
        pass
    open_window(base + page, home)


# --------------------------------------------------------------------------- the program while it runs
class Program:
    """What the site knows about the program it runs in: its version and notes, the update on offer, the page to
    reopen, and how to stop it."""

    def __init__(self, info: dict, home: Path, stop=None):
        self.info, self.home, self.stop = info, home, stop or (lambda: None)
        self.version = str(info.get("version", "dev"))
        self.offer: dict | None = None
        self.state = {"busy": False, "error": "", "said": ""}
        self.started = time.time()
        self.ever_connected = False

    def look_for_update(self, tries: int = 3, wait: float = 20.0) -> None:
        """Looked for each time the program opens (your answer of 26 November); a look that couldn't reach GitHub
        is tried again twice, and why there's no update is kept (in program.log and the program's state)."""
        if UP.install_folder() is None:       # running from the code: nothing to update
            return
        for k in range(tries):
            why: list[str] = []
            self.offer = UP.look(self.version, why=why)
            self.state["looked"] = "; ".join(why) or "an update is ready"
            print(f"update look: {self.state['looked']}", file=sys.stderr)
            if self.offer or not any(w.startswith("couldn't look") for w in why):
                return
            if k + 1 < tries:
                time.sleep(wait)

    def apply_update(self, store, reopen: str) -> None:
        """The update, safely: downloaded and checked first; every career backed up; the new version unpacked beside
        this one; then the program closes and a small script swaps the folders and reopens on the same page."""
        import tempfile
        install = UP.install_folder()
        self.state.update(busy=True, error="")
        try:
            if install is None or not self.offer:
                raise UP.NotSafe("There's no update to install.")
            with tempfile.TemporaryDirectory() as tmp:
                z = UP.download(self.offer, Path(tmp))
                for name in store.names():
                    made, why = store.checked_backup(name, note="before-update")
                    if why:
                        raise UP.NotSafe(f"Your careers couldn't all be backed up first ({why}), so nothing was changed.")
                new = UP.unpack(z, install)
            UP.run_swap(install, new, reopen)
            self.state.update(said="Updating: the Stats Pack closes and opens again in a moment.")
            threading.Timer(1.5, self.stop).start()
        except Exception as e:  # noqa: BLE001 - the version you have stays; it tries again next time
            self.state.update(busy=False, error=f"The update wasn't installed: {e} The version you have stays as it is.")

    def watch(self, windows) -> None:
        """Stop a minute after the last window closes (`windows()` says how many are open)."""
        quiet_since = None
        while True:
            time.sleep(2)
            n = windows()
            if n:
                self.ever_connected, quiet_since = True, None
                continue
            now = time.time()
            if not self.ever_connected and now - self.started < FIRST_WAIT:
                continue
            quiet_since = quiet_since or now
            if now - quiet_since >= IDLE_STOP:
                self.stop()
                return


def last_page(home: Path) -> str:
    """The page you were on when the program last closed (your choice of 14 November: it reopens where you left off);
    My team when there's none."""
    try:
        from ccstats.local import CareerStore
        p = str(CareerStore(home).preferences().get("last_page", "") or "")
        return p if p.startswith("/") and not p.startswith("/api") else "/"
    except Exception:  # noqa: BLE001 - a preferences file that can't be read: start on My team
        return "/"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog=NAME)
    ap.add_argument("--open", default="", help="the page to open (else the one you were on last time)")
    ap.add_argument("--no-window", action="store_true")
    ap.add_argument("--check", action="store_true", help="start, answer one question, stop (for the build's test)")
    ap.add_argument("--update-failed", action="store_true")
    args = ap.parse_args(argv)
    page = args.open if args.open.startswith("/") else ""
    if sys.stderr is None or sys.stdout is None:   # the program has no black window: what it would print goes to a file
        try:
            from ccstats.local import home_dir
            home_dir().mkdir(parents=True, exist_ok=True)
            log = open(home_dir() / "program.log", "a", encoding="utf-8", buffering=1)   # noqa: SIM115
            sys.stdout = sys.stdout or log
            sys.stderr = sys.stderr or log
        except OSError:
            import io
            sys.stdout = sys.stdout or io.StringIO()
            sys.stderr = sys.stderr or io.StringIO()
    try:
        from ccstats.local import home_dir as default_root
        home = default_root()
        home.mkdir(parents=True, exist_ok=True)
        page = page or last_page(home)
        other = None if args.check else running(home)
        if other:
            bring_back(other, home, page)
            return 0
        import uvicorn
        from server.__main__ import free_port
        from server.app import create_app

        port = free_port(8601)
        server: list = []
        prog = Program(build_info(), home, stop=lambda: setattr(server[0], "should_exit", True) if server else None)
        app = create_app(program=prog)
        config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", timeout_graceful_shutdown=2)
        srv = uvicorn.Server(config)
        server.append(srv)
        lock_file(home).write_text(json.dumps({"port": port, "pid": os.getpid()}), encoding="utf-8")
        url = f"http://127.0.0.1:{port}{page}"

        def when_ready():
            for _ in range(300):
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    if s.connect_ex(("127.0.0.1", port)) == 0:
                        break
                time.sleep(0.1)
            if args.check:
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=60) as r:
                        checked["ok"] = bool(json.loads(r.read()).get("ok"))
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=60) as r:
                        checked["ok"] = checked["ok"] and b"<div id=\"root\">" in r.read()
                finally:
                    srv.should_exit = True
                return
            threading.Thread(target=prog.look_for_update, daemon=True).start()
            if not args.no_window:
                open_window(url, home)
            if args.update_failed:
                message(NAME, "The update couldn't be put in place, so the version you had is still here. "
                              "It will be offered again next time.")
            prog.watch(lambda: app.state.windows())

        checked = {"ok": False}
        threading.Thread(target=when_ready, daemon=True).start()
        srv.run()
        return (0 if checked["ok"] else 2) if args.check else 0
    except SystemExit as e:   # e.g. no free port: said in plain words
        message(NAME, f"The Stats Pack couldn't start: {e}")
        return 1
    except Exception as e:  # noqa: BLE001 - never a silent failure
        message(NAME, "The Stats Pack couldn't start.\n\n"
                      f"What happened: {type(e).__name__}: {e}\n\n"
                      "What to do: close it and open it again. If it keeps happening, restart the computer; your "
                      "careers are safe in Documents\\Cricket Captain Stats Pack.")
        return 1
    finally:
        try:
            from ccstats.local import home_dir as default_root
            f = lock_file(default_root())
            if f.exists() and json.loads(f.read_text(encoding="utf-8")).get("pid") == os.getpid():
                f.unlink()
        except Exception:  # noqa: BLE001
            pass
