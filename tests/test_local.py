import shutil
from pathlib import Path

from ccstats.local import CareerStore, Watcher, default_scorecards_folder

FIXTURES = sorted((Path(__file__).parent / "fixtures").glob("*.txt"))


def setup(tmp_path, n=5):
    folder = tmp_path / "Scorecards"
    folder.mkdir()
    for p in FIXTURES[:n]:
        shutil.copy(p, folder)
    return folder, Watcher(CareerStore(tmp_path / "home"))


def test_new_matches_go_to_the_career_playing_now(tmp_path):
    folder, w = setup(tmp_path)
    res = w.create("India save", folder)
    assert len(res.career.matches) == 5 and w.playing(str(folder)) == "India save"
    assert w.sync(str(folder)) is None  # nothing new yet
    for p in FIXTURES[5:8]:  # the game autosaves three more matches
        shutil.copy(p, folder)
    res = w.sync(str(folder))
    assert res.career.name == "India save" and len(res.added) == 3 and len(res.career.matches) == 8


def test_two_saves_share_one_folder(tmp_path):
    folder, w = setup(tmp_path)
    w.create("India save", folder)
    # a second save on the same folder starts empty and becomes Playing now
    res = w.create("Surrey save", folder, include_existing=False)
    assert len(res.career.matches) == 0 and w.playing(str(folder)) == "Surrey save"
    for p in FIXTURES[5:7]:
        shutil.copy(p, folder)
    assert len(w.sync(str(folder)).career.matches) == 2  # went to Surrey save
    w.set_playing(str(folder), "India save")
    for p in FIXTURES[7:10]:
        shutil.copy(p, folder)
    res = w.sync(str(folder))
    assert res.career.name == "India save" and len(res.career.matches) == 8
    assert len(w.store.load("Surrey save")[0].matches) == 2
    assert sorted(w.careers_on(str(folder))) == ["India save", "Surrey save"]


def test_deleting_files_never_loses_matches(tmp_path):
    folder, w = setup(tmp_path)
    w.create("India save", folder)
    (folder / FIXTURES[0].name).unlink()
    assert w.sync(str(folder)) is None
    assert len(w.store.load("India save")[0].matches) == 5


def test_default_folder_on_windows(tmp_path, monkeypatch):
    target = tmp_path / "Roaming" / "Childish Things" / "Cricket Captain 2026" / "Scorecards"
    target.mkdir(parents=True)
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
    assert default_scorecards_folder() == target
