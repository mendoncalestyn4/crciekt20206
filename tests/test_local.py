import os
import shutil
from pathlib import Path

from ccstats.local import CareerStore, default_scorecards_folder, start_watching, sync

FIXTURES = sorted((Path(__file__).parent / "fixtures").glob("*.txt"))


def test_watch_folder_picks_up_new_matches(tmp_path):
    folder = tmp_path / "Scorecards"
    folder.mkdir()
    for p in FIXTURES[:5]:
        shutil.copy(p, folder)
    res = start_watching("India save", folder)
    assert len(res.career.matches) == 5 and len(res.added) == 5
    assert sync(res.career, res.settings) is None  # nothing new
    for p in FIXTURES[5:8]:  # the game autosaves three more matches
        shutil.copy(p, folder)
    res2 = sync(res.career, res.settings)
    assert res2 is not None and len(res2.added) == 3 and len(res2.career.matches) == 8
    # deleting files from the game's folder never loses matches already loaded
    (folder / FIXTURES[0].name).unlink()
    assert sync(res2.career, res2.settings) is None
    assert len(res2.career.matches) == 8


def test_store_round_trip(tmp_path):
    folder = tmp_path / "Scorecards"
    folder.mkdir()
    for p in FIXTURES[:4]:
        shutil.copy(p, folder)
    res = start_watching("Surrey save", folder)
    store = CareerStore(tmp_path / "home")
    store.save(res.career, res.settings)
    assert store.names() == ["Surrey save"] and store.last_used() == "Surrey save"
    career, settings = store.load("Surrey save")
    assert len(career.matches) == 4 and settings.folder == str(folder)
    assert settings.snapshot == res.settings.snapshot
    store.delete("Surrey save")
    assert store.names() == []


def test_default_folder_on_windows(tmp_path, monkeypatch):
    target = tmp_path / "Roaming" / "Childish Things" / "Cricket Captain 2026" / "Scorecards"
    target.mkdir(parents=True)
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
    assert default_scorecards_folder() == target
