"""Updates (your answers of 26 November): looked for each time the program opens; offered with a button; one click
backs up every career, puts the new version in place and reopens on the same page. Safe: the download is checked
complete and unchanged (its size and fingerprint) before anything is replaced; if it isn't, the version you have stays
and it tries again next time. "What's new" lives in Settings.

The updates come from the public repository holding only the finished program:
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

REPO = "mendoncalestyn4/cricket-captain-stats-pack"
BASE = f"https://raw.githubusercontent.com/{REPO}/main"
TIMEOUT = 8          # seconds for the quick look when the program opens


def parse(version: str) -> tuple:
    """'2026.11.27.1' -> (2026, 11, 27, 1); anything else sorts first (a copy built by hand is never 'newer')."""
    try:
        return tuple(int(x) for x in version.split("."))
    except ValueError:
        return ()


def newer(available: str, current: str) -> bool:
    return bool(parse(available)) and parse(available) > parse(current)


def look(current: str, fetch=None) -> dict | None:
    """The update on offer, or None (nothing newer, no internet, or a file that doesn't make sense)."""
    fetch = fetch or _fetch
    try:
        info = json.loads(fetch(f"{BASE}/latest.json", TIMEOUT))
        if not isinstance(info, dict) or not all(k in info for k in ("version", "file", "size", "sha256")):
            return None
        return info if newer(str(info["version"]), current) else None
    except Exception:  # noqa: BLE001 - no internet or GitHub unreachable: simply no update this time
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
    data = fetch(f"{BASE}/{info['file']}", 600)
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
    return "\r\n".join([
        "@echo off",
        ":wait",
        f'tasklist /FI "PID eq {pid}" | find "{pid}" >nul && (timeout /t 1 /nobreak >nul & goto wait)',
        f"if exist {q(old)} rmdir /s /q {q(old)}",
        f"move {q(install)} {q(old)} >nul || goto failed",
        f"move {q(new)} {q(install)} >nul || (move {q(old)} {q(install)} >nul & goto failed)",
        f'start "" {q(install / EXE)} --open "{reopen}"',
        f"rmdir /s /q {q(old)}",
        f"if exist {q(install.with_name(install.name + '.new'))} rmdir /s /q {q(install.with_name(install.name + '.new'))}",
        'del "%~f0" & exit',
        ":failed",
        f'start "" {q(install / EXE)} --open "{reopen}" --update-failed',
        'del "%~f0" & exit',
    ])


def run_swap(install: Path, new: Path, reopen: str) -> None:
    """Start the swap script, hidden, to run as soon as this program has closed."""
    script = Path(tempfile.gettempdir()) / f"stats-pack-update-{os.getpid()}.cmd"
    script.write_text(swap_script(install, new, os.getpid(), reopen), encoding="utf-8")
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
    subprocess.Popen(["cmd", "/c", str(script)], creationflags=flags, close_fds=True)


def install_folder() -> Path | None:
    """The folder the program runs from, when it runs as the program (None when it runs from the code)."""
    return Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else None
