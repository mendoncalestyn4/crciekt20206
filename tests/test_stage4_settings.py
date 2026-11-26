"""Stage 4, Settings (your answers of 26 November): careers added four ways (a folder, an uploaded folder or files or a
zip, a career file) with the old site's warnings word for word, downloaded as a file, renamed and removed (a backup
first), the full reset asked twice (never touching the game's Scorecards folder); your teams and the first-start
question; backups of every career, each checked by reading it back, a warning instead of a backup on a nearly full
disk, a copy before an update; the logos folder. The current site reads the same files."""

from __future__ import annotations

import base64
import json
import shutil
from pathlib import Path

import pytest

from ccstats.loader import Career
from ccstats.local import CareerStore, Watcher
from server import settingspage as SP
from server.app import create_app
from serverkit import FIXTURES, Live, make_pc


@pytest.fixture
def pc(tmp_path):
    store, folder, game = make_pc(tmp_path, n=12, team="England")
    s = Live(create_app(store, web=tmp_path / "nothing", watch_every=0))
    yield s, store, folder, tmp_path
    s.stop()


def post(s, path="/api/settings", **b):
    status, _, body = s.post(path, b)
    return status, json.loads(body)


def test_the_page_and_its_tabs(pc):
    s, store, folder, _ = pc
    d = s.json("/api/settings")
    assert d["tabs"] == SP.TABS and not d["first"] and d["current"] == "My career"
    assert d["careers"][0]["name"] == "My career" and d["careers"][0]["folder"] == str(folder)
    assert d["career"]["matches"] == 12 and d["teams"]["picked"] == ["England"]
    ch = d["teams"]["choices"]
    assert len(ch) >= 235 and ch[0] in ("Afghanistan",) and "England" in ch[:31]   # national sides first
    assert d["backups"]["kept"] == 8 and d["logos"]["teams"] >= 1


def test_add_a_career_from_a_folder_with_the_old_warnings(pc, tmp_path):
    s, store, folder, _ = pc
    status, b = post(s, action="add_folder", name="Second", folder=str(folder))
    assert status == 400 and "already used by **My career**" in b["error"]
    status, b = post(s, action="add_folder", name="Second", folder=str(tmp_path / "nowhere"))
    assert status == 400 and b["error"] == "That folder doesn't exist on this PC. Check the path or use Browse…."
    other = tmp_path / "Other" / "Scorecards"
    other.mkdir(parents=True)
    for f in FIXTURES[12:20]:
        shutil.copy(f, other / f.name)
    status, b = post(s, action="add_folder", name="My career", folder=str(other))
    assert status == 400 and b["error"] == "A career with that name already exists. Pick another name."
    status, b = post(s, action="add_folder", name="Second", folder=str(other))
    assert status == 200 and b["line"].startswith("Finished: 8 loaded")
    assert set(store.names()) == {"My career", "Second"} and s.json("/api/settings")["current"] == "Second"
    assert Watcher(store).owner(str(other)) == "Second"


def test_uploads_new_add_and_a_career_file(pc):
    s, store, _, _ = pc
    files = [dict(name=f.name, data=base64.b64encode(f.read_bytes()).decode()) for f in FIXTURES[20:26]]
    status, b = post(s, "/api/upload", files=files[:3])
    tok = b["token"]
    status, b = post(s, "/api/upload", token=tok, files=files[3:], finish="new", name="Uploaded")
    assert status == 200 and b["name"] == "Uploaded" and "6 loaded" in b["line"]
    # added to the career on screen
    more = [dict(name=f.name, data=base64.b64encode(f.read_bytes()).decode()) for f in FIXTURES[26:28]]
    status, b = post(s, "/api/upload", files=more, finish="add")
    assert status == 200 and b["name"] == "Uploaded"
    c, _ = store.load("Uploaded")
    assert len(c.matches) == 8
    # its career file, downloaded and opened again as a new career: the same matches
    status, headers, data = s.get("/api/careers/Uploaded/file")
    assert status == 200 and Career.is_pack(data) and "attachment" in headers["Content-Disposition"]
    status, b = post(s, "/api/upload", files=[dict(name="x.zip", data=base64.b64encode(data).decode())], finish="new", name="From file")
    assert status == 200
    c2, _ = store.load("From file")
    assert sorted(c2.matches.match_id) == sorted(c.matches.match_id)
    status, b = post(s, "/api/upload", files=[dict(name="bad.txt", data="%%%")], finish="new", name="Bad")
    assert status == 400


def test_demo_league(pc):
    s, store, _, _ = pc
    status, b = post(s, action="demo")
    assert status == 200 and SP.DEMO_NAME in store.names()
    assert s.json("/api/career")["name"] == SP.DEMO_NAME


def test_rename_and_remove_with_a_backup_first(pc):
    s, store, folder, tmp_path = pc
    store.backup("My career")
    status, b = post(s, action="rename", name="My career", new="India save")
    assert status == 200 and store.names() == ["India save"]
    assert Watcher(store).owner(str(folder)) == "India save" and store.backups("India save")
    assert s.json("/api/career")["name"] == "India save"
    st = store.load_settings("India save")[1]
    assert st.my_teams == ["England"] and st.folder == str(folder)
    status, b = post(s, action="remove", name="India save")
    assert status == 400   # not ticked
    status, b = post(s, action="remove", name="India save", sure=True)
    assert status == 200 and store.names() == [] and "backup" in b["message"]
    assert any("before-remove" in p.name for p, _ in store.backups("India save"))
    assert folder.is_dir() and list(folder.glob("*.txt"))      # the game's folder untouched
    assert Watcher(store).owner(str(folder)) is None           # a new career can take it
    assert s.json("/api/settings")["first"]


def test_full_reset_asked_twice_and_never_the_scorecards(pc):
    s, store, folder, _ = pc
    store.backup("My career")
    n_cards = len(list(folder.glob("*.txt")))
    status, b = post(s, action="reset", sure="yes")
    assert status == 400 and store.names() == ["My career"]
    status, b = post(s, action="reset", sure="DELETE EVERYTHING")
    assert status == 200 and store.names() == [] and store.all_backups() == 0
    assert len(list(folder.glob("*.txt"))) == n_cards
    assert not (store.root / "folders.json").exists()


def test_teams_and_the_first_start_question(pc):
    s, store, _, _ = pc
    st = store.load_settings("My career")[1]
    st.my_teams, st.teams_asked = [], False
    store.save_settings(st)
    assert s.json("/api/settings")["teams"]["ask"]
    status, b = post(s, action="teams", teams=["England", "Not A Team"])
    assert status == 400
    status, _ = post(s, action="teams", teams=["England", "Mumbai Indians" if "Mumbai Indians" in s.json("/api/settings")["teams"]["choices"] else "India"])
    st = store.load_settings("My career")[1]
    assert st.my_teams[0] == "England" and st.teams_asked and store.preferences()["last_teams"] == st.my_teams
    st.my_teams, st.teams_asked = [], False
    store.save_settings(st)
    post(s, action="teams_never")
    st = store.load_settings("My career")[1]
    assert st.teams_asked and not s.json("/api/settings")["teams"]["ask"]


def test_backup_now_restore_and_undo(pc):
    s, store, _, _ = pc
    status, b = post(s, action="backup_now")
    assert status == 200 and len(store.backups("My career")) == 1
    first = s.json("/api/settings")["backups"]["items"][0]["file"]
    status, b = post(s, action="restore", file=first)
    assert status == 200 and "Restored" in b["message"]
    items = s.json("/api/settings")["backups"]["items"]
    assert any(x["before_restore"] for x in items)          # the restore can itself be undone
    status, b = post(s, action="restore", file="nope.zip")
    assert status == 400


def test_backups_check_themselves_and_a_full_disk_warns(tmp_path, monkeypatch):
    store, _, _ = make_pc(tmp_path, n=5)
    made, why = store.checked_backup("My career")
    assert made and not why and made.read_bytes() == (store._dir("My career") / "career.stats-pack.zip").read_bytes()
    # a backup that doesn't read back is made again; twice wrong: said so, nothing broken left behind
    real = Path.read_bytes
    calls = {"n": 0}

    def bad(self):
        if self.parent.parent.name == "backups":
            calls["n"] += 1
            return b"broken"
        return real(self)
    monkeypatch.setattr(Path, "read_bytes", bad)
    made, why = store.checked_backup("My career")
    monkeypatch.setattr(Path, "read_bytes", real)
    assert made is None and "didn't read back" in why and calls["n"] == 2
    assert len(store.backups("My career")) == 1
    # a nearly full disk: a warning instead of a backup
    import shutil as sh
    monkeypatch.setattr(sh, "disk_usage", lambda p: sh._ntuple_diskusage(10, 9, 1))
    made, why = store.checked_backup("My career")
    assert made is None and "Not enough room" in why


def test_every_career_gets_its_weekly_backup(tmp_path):
    store, folder, game = make_pc(tmp_path, n=5)
    other = tmp_path / "B" / "Scorecards"
    other.mkdir(parents=True)
    for f in FIXTURES[5:9]:
        shutil.copy(f, other / f.name)
    Watcher(store).create("Second", other)
    done, problems = store.checked_backup_all_due()
    assert sorted(done) == ["My career", "Second"] and not problems
    assert store.checked_backup_all_due()[0] == []           # not due again for a week


def test_a_copy_before_an_update(tmp_path):
    store, _, _ = make_pc(tmp_path, n=5)
    store.save_preference("last_version", "an-older-version")
    s = Live(create_app(store, web=tmp_path / "nothing", watch_every=60))
    try:
        import time
        for _ in range(100):
            if store.backups("My career"):
                break
            time.sleep(0.1)
        assert any("before-update" in p.name for p, _ in store.backups("My career"))
        assert store.preferences()["last_version"] != "an-older-version"
    finally:
        s.stop()


def test_logos_folder(pc):
    s, store, _, _ = pc
    status, _ = post(s, action="logos_folder", folder="C:/somewhere")
    assert status == 200 and store.preferences()["logos_folder"] == "C:/somewhere"
    assert s.json("/api/settings")["logos"]["chosen"] == "C:/somewhere"


def test_no_careers_first_start(tmp_path):
    store = CareerStore(tmp_path / "home")
    s = Live(create_app(store, web=tmp_path / "nothing", watch_every=0))
    try:
        d = s.json("/api/settings")
        assert d["first"] and d["careers"] == [] and "Autosave scorecards" in d["scorecards_help"]
        status, b = post(s, action="browse")
        assert status == 200 and (b["folder"] or b["unavailable"])
    finally:
        s.stop()


def test_a_folder_that_vanishes_and_comes_back(tmp_path):
    import time
    from serverkit import by_date
    files = sorted(FIXTURES, key=by_date)
    store, folder, game = make_pc(tmp_path, files=files[:10])
    s = Live(create_app(store, web=tmp_path / "nothing", watch_every=0.2))
    try:
        gone = folder.with_name("Scorecards-moved")
        folder.rename(gone)
        time.sleep(1.5)
        assert s.json("/api/health")["ok"] and s.json("/api/fixtures")["teams"] == ["England"]
        assert len(store.load("My career")[0].matches) == 10        # nothing lost while it was away
        gone.rename(folder)
        for f in files[10:13]:
            shutil.copy(f, folder / f.name)
        for _ in range(100):
            if len(store.load("My career")[0].matches) == 13:
                break
            time.sleep(0.1)
        assert len(store.load("My career")[0].matches) == 13
    finally:
        s.stop()
