"""The update, tried for real on GitHub's Windows machine (stage 5): the previous published version is unzipped and
started with a career in it; it must find the new version on its own, install it when asked (backing every career up
first), close and open again as the new version, with the career as it was.

    python tools/update_check.py <previous version's zip> <the version expected after the update>

Exits 0 when all of that happened, 1 (saying what didn't) otherwise."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def get(port: int, path: str, data: dict | None = None, timeout: float = 30) -> dict:
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=None if data is None else json.dumps(data).encode(),
                                 headers={"Content-Type": "application/json"} if data is not None else {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def wait(what: str, check, seconds: float):
    end = time.time() + seconds
    last = None
    while time.time() < end:
        try:
            got = check()
            if got:
                return got
        except Exception as e:  # noqa: BLE001
            last = e
        time.sleep(1)
    raise SystemExit(f"FAILED: {what} (waited {seconds:.0f}s{'; last: ' + str(last) if last else ''})")


def main() -> int:
    old_zip, expect = Path(sys.argv[1]), sys.argv[2]
    tmp = Path(tempfile.mkdtemp(prefix="update-check-"))
    install = tmp / "program"
    with zipfile.ZipFile(old_zip) as z:
        z.extractall(install)
    exe = next(install.rglob("Cricket Captain Stats Pack.exe"))
    home = tmp / "home"
    os.environ["STATS_PACK_HOME"] = str(home)
    # a career to carry through the update: the test scorecards, read by the same code
    from ccstats.local import CareerStore, Watcher
    folder = tmp / "Scorecards"
    folder.mkdir()
    for f in sorted((ROOT / "tests" / "fixtures").glob("*.txt"))[:12]:
        (folder / f.name).write_bytes(f.read_bytes())
    store = CareerStore(home)
    Watcher(store).create("Update check", folder)
    before = sorted(store.names())
    env = dict(os.environ, STATS_PACK_HOME=str(home))
    subprocess.Popen([str(exe), "--no-window"], env=env, cwd=exe.parent)
    lock = home / "running.json"
    first = wait("the old version started", lambda: json.loads(lock.read_text()) if lock.is_file() else None, 120)
    port = int(first["port"])
    info = wait("the old version answered", lambda: get(port, "/api/program"), 120)
    old = info["version"]
    print(f"old version {old} running on port {port}")
    try:
        offer = wait("the update was offered", lambda: get(port, "/api/program").get("update"), 180)
    except SystemExit:
        print("why not:", (get(port, "/api/program").get("state") or {}).get("looked", "(not said)"))
        raise
    if offer["version"] != expect:
        raise SystemExit(f"FAILED: offered {offer['version']}, expected {expect}")
    print(f"offered {offer['version']}: installing")
    get(port, "/api/program", {"action": "update", "page": "/settings"})

    def reopened():
        if not lock.is_file():
            return None
        d = json.loads(lock.read_text())
        if int(d["pid"]) == int(first["pid"]):
            return None
        return get(int(d["port"]), "/api/program")
    try:
        now = wait("the new version opened again", reopened, 300)
    except SystemExit:
        from desktop import updates as UP
        print("the swap's own log:\n" + (UP.LOG.read_text(errors="replace") if UP.LOG.is_file() else "(none)"))
        plog = home / "program.log"
        print("program.log:\n" + (plog.read_text(errors="replace")[-3000:] if plog.is_file() else "(none)"))
        print("the old version's process:", subprocess.run(["tasklist", "/V", "/FI", f"PID eq {first['pid']}"],
                                                           capture_output=True, text=True).stdout)
        print("every copy of the program still running:", subprocess.run(
            ["tasklist", "/V", "/FI", "IMAGENAME eq Cricket Captain Stats Pack.exe"], capture_output=True, text=True).stdout)
        raise
    if now["version"] != expect:
        raise SystemExit(f"FAILED: reopened as {now['version']}, expected {expect}")
    print(f"reopened as {now['version']}")
    plog = home / "program.log"      # (how the old version closed: how long it took, and anything it said)
    print("program.log:\n" + (plog.read_text(errors="replace")[-4000:] if plog.is_file() else "(none)"))
    after = sorted(CareerStore(home).names())
    if after != before:
        raise SystemExit(f"FAILED: careers before {before}, after {after}")
    backups = list((home).rglob("*before-update*"))
    if not backups:
        raise SystemExit("FAILED: no backup was made before the update")
    print(f"OK: {old} → {now['version']}, careers {after} intact, {len(backups)} backup(s) made first")
    return 0          # (with no window open, the program closes by itself a few minutes later)


if __name__ == "__main__":
    sys.exit(main())
