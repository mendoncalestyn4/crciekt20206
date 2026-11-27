"""Updates (your answers of 26 November): looked for each time the program opens; offered with a button; one click
backs up every career, puts the new version in place and reopens on the same page. Safe: the download is checked
complete and unchanged (its size and fingerprint) before anything is replaced; if it isn't, the version you have stays
and it tries again next time. "What's new" lives in Settings.

The updates come from the project's own releases on GitHub (public since 26 November, so nothing else is needed: the
newest release holds the finished program; the build on GitHub's Windows machine publishes it when asked). Each
release holds:
    latest.json   {"version": "2026.11.27.1", "date": "27 Nov 2026", "file": "<zip name>", "size": <bytes>,
                   "sha256": "<hex>", "notes": ["plain words", ...]}
    <zip name>    the program's folder, zipped
Versions are dates with a number, so a later one always sorts after an earlier one."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

REPO = "mendoncalestyn4/crciekt20206"
# the newest release, asked of GitHub's own list (always current: the "latest" download shortcut can point at the
# release before for a few minutes after a new one goes out, found by the real update test of 27 November)
API = f"https://api.github.com/repos/{REPO}/releases/latest"
TIMEOUT = 8          # seconds for the quick look when the program opens


def parse(version: str) -> tuple:
    """'2026.11.27.1' -> (2026, 11, 27, 1); anything else sorts first (a copy built by hand is never 'newer')."""
    try:
        return tuple(int(x) for x in version.split("."))
    except ValueError:
        return ()


def newer(available: str, current: str) -> bool:
    return bool(parse(available)) and parse(available) > parse(current)


def look(current: str, fetch=None, why: list | None = None) -> dict | None:
    """The update on offer, or None (nothing newer, no internet, or a file that doesn't make sense; the reason is added
    to `why` when given, so a look that fails is never silent). The newest release is asked of GitHub's list, then its
    own latest.json read: the version, the zip's name, size and fingerprint, and the notes."""
    fetch = fetch or _fetch
    why = why if why is not None else []
    try:
        rel = json.loads(fetch(API, TIMEOUT))
        files = {a["name"]: a["browser_download_url"] for a in rel.get("assets", []) if "name" in a}
        if "latest.json" not in files:
            why.append(f"the newest release ({rel.get('tag_name', '?')}) has no latest.json")
            return None
        info = json.loads(fetch(files["latest.json"], TIMEOUT))
        if not isinstance(info, dict) or not all(k in info for k in ("version", "file", "size", "sha256")):
            why.append("latest.json is incomplete")
            return None
        if str(info["file"]) not in files:
            why.append(f"the release has no {info['file']}")
            return None
        info["url"] = files[str(info["file"])]
        if not newer(str(info["version"]), current):
            why.append(f"nothing newer than {current} (the newest is {info['version']})")
            return None
        return info
    except Exception as e:  # noqa: BLE001 - no internet or GitHub unreachable: simply no update this time
        why.append(f"couldn't look: {type(e).__name__}: {e}")
        return None


def _fetch(url: str, timeout: float) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Stats-Pack-updater", "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


class NotSafe(Exception):
    """The download isn't complete and unchanged: nothing is replaced."""


def download(info: dict, folder: Path, fetch=None) -> Path:
    """The new version's zip, checked: the right size and the right fingerprint, and a zip that opens."""
    fetch = fetch or _fetch
    data = fetch(str(info["url"]), 600)
    if len(data) != int(info["size"]):
        raise NotSafe(f"The download was {len(data):,} bytes, not {int(info['size']):,}: it didn't arrive whole.")
    if hashlib.sha256(data).hexdigest() != str(info["sha256"]).lower():
        raise NotSafe("The download isn't exactly the version published: it may have been damaged on the way.")
    out = Path(folder) / str(info["file"])
    out.write_bytes(data)
    try:
        with zipfile.ZipFile(out) as z:
            bad = z.testzip()
            names = z.namelist()
    except zipfile.BadZipFile as e:
        raise NotSafe("The download isn't a whole zip.") from e
    if bad or not any(n.endswith(".exe") for n in names):
        raise NotSafe("The download is missing parts of the program.")
    return out


def unpack(zip_path: Path, install: Path) -> Path:
    """The new version unpacked beside the one running ('<folder>.new'), ready to swap in once the program closes."""
    new = install.with_name(install.name + ".new")
    if new.exists():
        import shutil
        shutil.rmtree(new)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(new)
    inner = [p for p in new.iterdir()]
    if len(inner) == 1 and inner[0].is_dir() and not (new / EXE).exists():   # a zip holding one folder: its contents
        return inner[0]
    return new


EXE = "Cricket Captain Stats Pack.exe"


def swap_script(install: Path, new: Path, pid: int, reopen: str) -> str:
    """A small Windows script run once the program has closed: the old folder set aside, the new one put in its place,
    the program started again on the same page, the old folder removed. If the swap fails, the old folder goes back."""
    old = install.with_name(install.name + ".old")
    q = lambda p: f'"{p}"'   # noqa: E731
    log = q(LOG)
    return "\r\n".join([
        "@echo off",
        f"cd /d {q(install.parent)}",            # never inside the folder being moved (Windows won't move it then)
        f"echo %date% %time% waiting for the program to close >> {log}",
        # (no pipes and no "timeout": hidden, with no window, a piped search could wait for ever after the program had
        # gone, and "timeout" needs a keyboard; found by the real update test, 27 November. The task list goes to a
        # file that's searched, a second's pause is two pings, and after two minutes it goes on regardless: if the
        # program were somehow still there, the move below fails safely and the version you had opens again.)
        "set /a waited=0",
        ":wait",
        f'tasklist /FI "PID eq {pid}" /NH > {q(WAIT)} 2>nul',
        f'findstr /C:" {pid} " {q(WAIT)} >nul || goto closed',     # (the number with a space each side: its column)
        "set /a waited+=1",
        f"if %waited% GEQ {SWAP_WAIT} (echo %date% %time% still running after {SWAP_WAIT} seconds: going on >> {log} & goto closed)",
        "ping -n 2 127.0.0.1 >nul",
        "goto wait",
        ":closed",
        f"del {q(WAIT)} 2>nul",
        f"echo %date% %time% the program has closed >> {log}",
        "ping -n 2 127.0.0.1 >nul",              # (a moment for Windows to let go of its files)
        f"if exist {q(old)} rmdir /s /q {q(old)}",
        f"echo %date% %time% setting the old version aside >> {log}",
        f"move {q(install)} {q(old)} >> {log} 2>&1 || goto failed",
        f"echo %date% %time% putting the new version in place >> {log}",
        f"move {q(new)} {q(install)} >> {log} 2>&1 || (move {q(old)} {q(install)} >> {log} 2>&1 & goto failed)",
        f"echo %date% %time% starting the new version >> {log}",
        f'start "" /d {q(install)} {q(install / EXE)} --open "{reopen}"',
        f"rmdir /s /q {q(old)}",
        f"if exist {q(install.with_name(install.name + '.new'))} rmdir /s /q {q(install.with_name(install.name + '.new'))}",
        f"echo %date% %time% done >> {log}",
        'del "%~f0" & exit',
        ":failed",
        f"echo %date% %time% FAILED: the version you had is back >> {log}",
        f'start "" /d {q(install)} {q(install / EXE)} --open "{reopen}" --update-failed',
        'del "%~f0" & exit',
    ])


LOG = Path(tempfile.gettempdir()) / "stats-pack-update.log"     # what the swap did, step by step
WAIT = Path(tempfile.gettempdir()) / "stats-pack-update-wait.txt"   # the task list the swap searches
SWAP_WAIT = 120     # seconds the swap waits for the program to close before going on regardless


def run_swap(install: Path, new: Path, reopen: str) -> None:
    """Start the swap script, hidden, to run as soon as this program has closed."""
    script = Path(tempfile.gettempdir()) / f"stats-pack-update-{os.getpid()}.cmd"
    script.write_text(swap_script(install, new, os.getpid(), reopen), encoding="utf-8")
    # hidden, with a console of its own that has no window (so the commands it runs never open one), in its own group
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    subprocess.Popen(["cmd", "/c", str(script)], creationflags=flags, close_fds=True, cwd=str(install.parent))


def install_folder() -> Path | None:
    """The folder the program runs from, when it runs as the program (None when it runs from the code)."""
    return Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else None
