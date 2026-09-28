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
