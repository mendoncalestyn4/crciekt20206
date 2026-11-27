"""Stage 5, the program (your answers of 26 November): updates looked for when it opens and offered with a button, safe
(a download that isn't complete and unchanged replaces nothing), every career backed up first; one copy only; it stops
a minute after its last window closes; "What's new" in Settings with a small mark in the menu; the tour of every
section on the first start; the version's fingerprint when the code is packed away. The program itself is built and
started on GitHub's Windows machine (.github/workflows/program.yml)."""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path

import pytest

from desktop import program as PG
from desktop import updates as UP
from server.app import create_app
from serverkit import Live, make_pc


def zip_of(files: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for n, d in files.items():
            z.writestr(n, d)
    return buf.getvalue()


def test_versions_sort_by_date_and_a_hand_built_copy_is_never_newer():
    assert UP.newer("2026.11.27.2", "2026.11.27.1") and UP.newer("2026.12.1.0", "2026.11.30.9")
    assert not UP.newer("2026.11.27.1", "2026.11.27.1") and not UP.newer("dev", "2026.11.27.1")
    assert UP.newer("2026.11.27.1", "dev")


def test_looking_for_an_update():
    latest = dict(version="2026.12.01.1", file="x.zip", size=10, sha256="ab", notes=["Faster"])
    assert UP.look("2026.11.27.1", fetch=lambda url, t: json.dumps(latest).encode())["version"] == "2026.12.01.1"
    assert UP.look("2026.12.01.1", fetch=lambda url, t: json.dumps(latest).encode()) is None   # nothing newer
    assert UP.look("2026.11.27.1", fetch=lambda url, t: b"not json") is None
    assert UP.look("2026.11.27.1", fetch=lambda url, t: (_ for _ in ()).throw(OSError("no internet"))) is None
    assert UP.look("2026.11.27.1", fetch=lambda url, t: json.dumps({"version": "2027.1.1.1"}).encode()) is None  # half a file


def test_a_download_is_checked_before_anything_is_replaced(tmp_path):
    good = zip_of({"Cricket Captain Stats Pack/Cricket Captain Stats Pack.exe": b"MZ program", "x/data.txt": b"1"})
    info = dict(version="2026.12.01.1", file="new.zip", size=len(good), sha256=hashlib.sha256(good).hexdigest())
    got = UP.download(info, tmp_path, fetch=lambda url, t: good)
    assert got.read_bytes() == good
    with pytest.raises(UP.NotSafe, match="whole"):
        UP.download(info, tmp_path, fetch=lambda url, t: good[:-5])                      # cut short
    with pytest.raises(UP.NotSafe, match="damaged"):
        UP.download(dict(info, sha256="0" * 64), tmp_path, fetch=lambda url, t: good)   # not the version published
    no_exe = zip_of({"readme.txt": b"hello"})
    with pytest.raises(UP.NotSafe, match="missing"):
        UP.download(dict(info, size=len(no_exe), sha256=hashlib.sha256(no_exe).hexdigest()), tmp_path, fetch=lambda url, t: no_exe)


def test_unpacked_beside_the_one_running_and_the_swap_script(tmp_path):
    install = tmp_path / "Cricket Captain Stats Pack"
    install.mkdir()
    z = tmp_path / "new.zip"
    z.write_bytes(zip_of({"Cricket Captain Stats Pack/Cricket Captain Stats Pack.exe": b"MZ", "Cricket Captain Stats Pack/_internal/a": b"1"}))
    new = UP.unpack(z, install)
    assert (new / UP.EXE).exists() and new.parent.name.endswith(".new")
    script = UP.swap_script(install, new, 1234, "/players/J Root")
    assert 'PID eq 1234' in script                                  # waits for this program to close
    assert script.index(f'move "{install}" "{install}.old"') < script.index(f'move "{new}" "{install}"')
    assert '--open "/players/J Root"' in script and "--update-failed" in script   # reopens; says so if it failed


def test_the_update_backs_up_every_career_first_and_never_half_installs(tmp_path, monkeypatch):
    store, _, _ = make_pc(tmp_path, n=4)
    stopped = []
    prog = PG.Program({"version": "2026.11.27.1"}, tmp_path, stop=lambda: stopped.append(1))
    install = tmp_path / "app" / "Cricket Captain Stats Pack"
    install.mkdir(parents=True)
    monkeypatch.setattr(UP, "install_folder", lambda: install)
    good = zip_of({"Cricket Captain Stats Pack/Cricket Captain Stats Pack.exe": b"MZ"})
    prog.offer = dict(version="2026.12.01.1", file="new.zip", size=len(good), sha256=hashlib.sha256(good).hexdigest())
    swapped = []
    monkeypatch.setattr(UP, "_fetch", lambda url, t: good)
    monkeypatch.setattr(UP, "run_swap", lambda inst, new, page: swapped.append((inst, new, page)))
    prog.apply_update(store, "/fixtures")
    assert swapped and swapped[0][2] == "/fixtures" and any("before-update" in p.name for p, _ in store.backups("My career"))
    # a damaged download: no backup needed, nothing swapped, the version you have stays, said in plain words
    swapped.clear()
    prog.offer = dict(prog.offer, sha256="0" * 64)
    prog.apply_update(store, "/")
    assert not swapped and "wasn't installed" in prog.state["error"] and not prog.state["busy"]


def test_stops_a_minute_after_the_last_window_closes(monkeypatch):
    clock = {"t": 0.0}
    monkeypatch.setattr(PG.time, "time", lambda: clock["t"])
    monkeypatch.setattr(PG.time, "sleep", lambda s: clock.__setitem__("t", clock["t"] + s))
    stopped = []
    windows = iter([0] * 10 + [1] * 30 + [0] * 1000)        # opens after 20 s, closed after 80 s
    prog = PG.Program({}, Path("."), stop=lambda: stopped.append(clock["t"]))
    prog.started = 0.0
    prog.watch(lambda: next(windows))
    assert stopped and 80 + PG.IDLE_STOP <= stopped[0] <= 80 + PG.IDLE_STOP + 4
    # never opened at all: waits FIRST_WAIT before giving up on it
    clock["t"], stopped[:] = 0.0, []
    prog = PG.Program({}, Path("."), stop=lambda: stopped.append(clock["t"]))
    prog.started = 0.0
    prog.watch(lambda: 0)
    assert stopped[0] >= PG.FIRST_WAIT + PG.IDLE_STOP - 2


@pytest.fixture
def live(tmp_path):
    store, _, _ = make_pc(tmp_path, n=4)
    info = {"version": "2026.11.27.1", "date": "27 Nov 2026",
            "history": [{"version": "2026.11.27.1", "date": "27 Nov 2026", "notes": ["The Stats Pack is its own program."]}]}
    prog = PG.Program(info, tmp_path)
    s = Live(create_app(store, web=tmp_path / "nothing", watch_every=0, program=prog))
    yield s, store, prog
    s.stop()


def post(s, **b):
    status, _, body = s.post("/api/program", b)
    return status, json.loads(body)


def test_whats_new_and_the_mark_in_the_menu(live):
    s, store, prog = live
    d = s.json("/api/program")
    assert d["program"] and d["version"] == "2026.11.27.1" and d["updated"] and d["whats_new"][0]["notes"]
    post(s, action="seen")
    assert not s.json("/api/program")["updated"] and store.preferences()["whats_new_seen"] == "2026.11.27.1"
    prog.offer = dict(version="2026.12.01.1", date="1 Dec 2026", notes=["Faster"], file="x.zip", size=1, sha256="0")
    assert s.json("/api/program")["update"] == dict(version="2026.12.01.1", date="1 Dec 2026", notes=["Faster"])


def test_the_tour_of_every_section_once_then_again_on_request(live):
    s, store, _ = live
    tour = s.json("/api/program")["tour"]
    assert [x["key"] for x in tour] == ["my-team", "inbox", "players", "matches", "teams", "seasons", "fixtures",
                                         "leaders", "insights", "settings", "search"]
    post(s, action="tour_done")
    assert s.json("/api/program")["tour"] is None
    post(s, action="tour_again")
    assert len(s.json("/api/program")["tour"]) == 11


def test_one_copy_only(live, tmp_path):
    s, store, _ = live
    PG.lock_file(tmp_path).write_text(json.dumps({"port": s.port, "pid": 1}))
    assert PG.running(tmp_path)["port"] == s.port                   # the copy already running answers
    status, b = post(s, action="focus")
    assert status == 200 and b["windows"] == 0                     # no window open: a new one would be opened
    PG.lock_file(tmp_path).write_text(json.dumps({"port": 1, "pid": 1}))
    assert PG.running(tmp_path) is None                            # an old file left by a copy that stopped


def test_no_update_to_install_and_running_from_the_code(live, tmp_path):
    s, _, _ = live
    status, b = post(s, action="update")
    assert status == 400 and "no update" in b["error"]
    plain = Live(create_app(make_pc(tmp_path / "b", n=2)[0], web=tmp_path / "nothing", watch_every=0))
    try:
        assert plain.json("/api/program") == {"program": False, "tour": None}   # no tour, no What's new from the code
    finally:
        plain.stop()


def test_the_fingerprint_when_the_code_is_packed_away(tmp_path, monkeypatch):
    from ccstats import keep
    root = Path(__file__).resolve().parent.parent
    assert keep.code_fingerprint(root) and keep.code_fingerprint(tmp_path) == ""
    monkeypatch.setattr(keep, "_version", None)
    monkeypatch.setattr(keep, "code_fingerprint", lambda r: "")
    monkeypatch.setattr(keep, "_built_fingerprint", lambda: "abc123def456")
    assert keep.version() == "abc123def456"


def test_the_program_reopens_where_you_left_off(live):
    """Your choice of 14 November: the page you were on is noted (a second after you arrive) and the program opens on
    it next time; never an API address or something that isn't a page; My team when there's none."""
    s, store, _ = live
    assert PG.last_page(store.root) == "/"
    assert post(s, action="page", page="/teams/England?tab=Eras")[0] == 200
    assert PG.last_page(store.root) == "/teams/England?tab=Eras"
    for bad in ("/api/career", "http://elsewhere", "/" + "x" * 500):
        assert post(s, action="page", page=bad)[0] == 400
    assert PG.last_page(store.root) == "/teams/England?tab=Eras"
