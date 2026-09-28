import time
import shutil

import pytest
from pathlib import Path

from ccstats.local import CareerStore, Watcher, default_scorecards_folder

FIXTURES = sorted((Path(__file__).parent / "fixtures").glob("*.txt"))


def setup(tmp_path, n=5):
    folder = tmp_path / "Scorecards"
    folder.mkdir()
    for p in FIXTURES[:n]:
        shutil.copy(p, folder)
    return folder, Watcher(CareerStore(tmp_path / "home"))


def test_new_matches_are_added_to_the_folders_career(tmp_path):
    folder, w = setup(tmp_path)
    res = w.create("My career", folder)
    assert len(res.career.matches) == 5 and w.owner(str(folder)) == "My career"
    assert w.sync(str(folder)) is None  # nothing new yet
    for p in FIXTURES[5:8]:  # the game autosaves three more matches
        shutil.copy(p, folder)
    res = w.sync(str(folder))
    assert res.career.name == "My career" and len(res.added) == 3 and len(res.career.matches) == 8


def test_one_folder_is_one_career(tmp_path):
    folder, w = setup(tmp_path)
    w.create("My career", folder)
    with pytest.raises(ValueError):
        w.create("Second career", folder)


def test_deleting_files_never_loses_matches(tmp_path):
    folder, w = setup(tmp_path)
    w.create("My career", folder)
    (folder / FIXTURES[0].name).unlink()
    assert w.sync(str(folder)) is None
    assert len(w.store.load("My career")[0].matches) == 5


def test_default_folder_on_windows(tmp_path, monkeypatch):
    target = tmp_path / "Roaming" / "Childish Things" / "Cricket Captain 2026" / "Scorecards"
    target.mkdir(parents=True)
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
    assert default_scorecards_folder() == target


def test_weekly_backups_keep_the_newest_and_restore_is_undoable(tmp_path):
    folder, w = setup(tmp_path)
    store = w.store
    w.create("My career", folder)
    day = 24 * 3600
    t0 = time.time() - 100 * day  # real past dates: a restore happens "now"
    assert store.backup_all_due(t0) == ["My career"]
    assert store.backup_all_due(t0 + 3 * day) == []  # not a week yet
    assert store.backup_all_due(t0 + 7 * day) == ["My career"]
    for k in range(2, 12):  # many weeks later: only the newest 8 are kept
        store.backup_all_due(t0 + 7 * day * k)
    kept = store.backups("My career")
    assert len(kept) == store.BACKUPS_KEPT
    assert [t for _, t in kept] == sorted([t for _, t in kept], reverse=True)
    # restore the oldest (5 matches) after the career has grown to 8
    oldest = kept[-1][0]
    for p in FIXTURES[5:8]:
        shutil.copy(p, folder)
    assert len(w.sync(str(folder)).career.matches) == 8
    restored = store.restore("My career", oldest)
    assert len(restored.matches) == 5 and len(store.load("My career")[0].matches) == 5
    # the state just before the restore was backed up, so the restore can be undone
    before = [p for p, _ in store.backups("My career") if "before-restore" in p.name]
    assert before and len(store.restore("My career", before[0]).matches) == 8
    # after a restore, a rescan brings back matches still in the folder
    store.restore("My career", store.backups("My career")[-1][0])  # the oldest still kept (5 matches)
    assert len(store.load("My career")[0].matches) == 5
    w.rescan(str(folder))
    assert len(w.sync(str(folder)).career.matches) == 8


def test_restore_refuses_a_file_that_is_not_a_career(tmp_path):
    folder, w = setup(tmp_path)
    w.create("My career", folder)
    bad = tmp_path / "not a career.zip"
    bad.write_bytes(b"hello")
    with pytest.raises(ValueError):
        w.store.restore("My career", bad)
    assert len(w.store.load("My career")[0].matches) == 5  # untouched
