"""The program itself, tried for real on GitHub's Windows machine after every build (stage 5):

1. It opens in its own app window (Edge or Chrome started with --app, a window with no address bar or tabs) and the
   window's page connects.
2. Only one copy runs: starting it again doesn't start a second one; it hands over to the one running and stops.
3. Closing the window closes the program: a minute after the last window goes, the program stops by itself.
4. When it can't start, a message says what happened and what to do.

    python tools/program_check.py "dist/Cricket Captain Stats Pack/Cricket Captain Stats Pack.exe"

Exits 0 when all of that happened, 1 (saying what didn't) otherwise."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path


def wait(what: str, check, seconds: float):
    end, last = time.time() + seconds, None
    while time.time() < end:
        try:
            got = check()
            if got:
                return got
        except Exception as e:  # noqa: BLE001
            last = e
        time.sleep(1)
    raise SystemExit(f"FAILED: {what} (waited {seconds:.0f}s{'; last: ' + str(last) if last else ''})")


def windows_of(pid_marker: str) -> list[dict]:
    """The browser processes started as the program's app window (their command line has --app= and our folder)."""
    out = subprocess.run(["powershell", "-NoProfile", "-Command",
                          "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*--app=*' } | "
                          "Select-Object ProcessId,CommandLine | ConvertTo-Json"], capture_output=True, text=True).stdout
    rows = json.loads(out) if out.strip() else []
    rows = rows if isinstance(rows, list) else [rows]
    return [r for r in rows if pid_marker in (r.get("CommandLine") or "")]


def alive(pid: int) -> bool:
    out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True).stdout
    return str(pid) in out


def main() -> int:
    exe = Path(sys.argv[1]).resolve()
    home = Path(tempfile.mkdtemp(prefix="program-check-"))
    env = dict(os.environ, STATS_PACK_HOME=str(home))
    # with a real career in it, so it's also preparing pages in the background (with its helper processes) while
    # the checks run: closing must still be quick then (found by the update test, 27 November)
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    os.environ["STATS_PACK_HOME"] = str(home)
    from ccstats.local import CareerStore, Watcher
    folder = home.parent / f"{home.name}-Scorecards"
    folder.mkdir()
    for f in sorted((Path(__file__).resolve().parent.parent / "tests" / "fixtures").glob("*.txt")):
        (folder / f.name).write_bytes(f.read_bytes())
    Watcher(CareerStore(home)).create("Program check", folder)
    lock = home / "running.json"
    first = subprocess.Popen([str(exe)], env=env, cwd=exe.parent)
    info = wait("the program started", lambda: json.loads(lock.read_text()) if lock.is_file() else None, 120)
    port, pid = int(info["port"]), int(info["pid"])
    print(f"1. started (pid {pid}, port {port})")
    # 1. its own app window, whose page connects
    wins = wait("its own app window opened", lambda: windows_of(str(home)), 60)
    print(f"   app window: {wins[0]['CommandLine'][:160]}")

    def connected():          # (asking the window to come forward answers how many windows are connected)
        req = urllib.request.Request(f"http://127.0.0.1:{port}/api/program", data=json.dumps({"action": "focus"}).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read()).get("windows", 0) >= 1
    wait("the window's page connected", connected, 90)
    print("   its page is connected")
    # 2. only one copy: a second start hands over and stops
    t = time.time()
    second = subprocess.run([str(exe), "--no-window"], env=env, cwd=exe.parent, timeout=120)
    if second.returncode != 0:
        raise SystemExit(f"FAILED: the second start ended with code {second.returncode}")
    now = json.loads(lock.read_text())
    if int(now["pid"]) != pid or not alive(pid):
        raise SystemExit("FAILED: a second copy took over (or the first one stopped)")
    print(f"2. only one copy: the second start handed over and stopped in {time.time() - t:.1f}s")
    # 3. closing the window closes the program (a minute later)
    for w in windows_of(str(home)):
        subprocess.run(["taskkill", "/PID", str(w["ProcessId"]), "/T", "/F"], capture_output=True)
    t = time.time()
    # (a minute after the window goes, and quickly after that: closing never waits for the helpers' work; it took
    # three minutes on this machine before that was put right, 27 November)
    wait("the program stopped within two minutes of its window closing", lambda: first.poll() is not None or not alive(pid), 120)
    print(f"3. the window closed: the program stopped by itself {time.time() - t:.0f}s later")
    # 4. a clear message when it can't start (its folder for your careers is a file, so nothing can be kept there)
    bad = Path(tempfile.mkdtemp(prefix="program-check-bad-")) / "not-a-folder"
    bad.write_text("x")
    said = bad.parent / "message.txt"
    r = subprocess.run([str(exe), "--no-window"], env=dict(os.environ, STATS_PACK_HOME=str(bad), STATS_PACK_MESSAGE_TO=str(said)),
                       cwd=exe.parent, timeout=120)
    text = said.read_text(encoding="utf-8") if said.is_file() else ""
    if r.returncode != 1 or "couldn't start" not in text or "What to do" not in text:
        raise SystemExit(f"FAILED: no clear message when it can't start (code {r.returncode}, said {text!r})")
    print(f"4. can't start: the message says what happened and what to do ({text.strip()[:120]}…)")
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
