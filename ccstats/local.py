"""Running on the user's own PC: careers saved to disk and a watched
Scorecards folder.

Careers live in Documents\\Cricket Captain Stats Pack\\careers (override with
the STATS_PACK_HOME environment variable), outside the program folder, so
installing a new version of the site never touches them.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .loader import Career


def home_dir() -> Path:
    env = os.environ.get("STATS_PACK_HOME")
    return Path(env) if env else Path.home() / "Documents" / "Cricket Captain Stats Pack"


def default_scorecards_folder() -> Path | None:
    """Where Cricket Captain 2026 autosaves scorecards on Windows."""
    appdata = os.environ.get("APPDATA")
    candidates = []
    if appdata:
        candidates.append(Path(appdata) / "Childish Things" / "Cricket Captain 2026" / "Scorecards")
    candidates.append(Path.home() / "AppData" / "Roaming" / "Childish Things" / "Cricket Captain 2026" / "Scorecards")
    for c in candidates:
        if c.is_dir():
            return c
    return None


# --------------------------------------------------------------------------- #
# Folder snapshots
# --------------------------------------------------------------------------- #


def snapshot(folder: Path) -> dict[str, list]:
    """{relative path: [modified time, size]} for every .txt under the folder."""
    snap = {}
    for p in sorted(Path(folder).rglob("*.txt")):
        try:
            st = p.stat()
        except OSError:
            continue
        snap[p.relative_to(folder).as_posix()] = [round(st.st_mtime, 3), st.st_size]
    return snap


def read_files(folder: Path, names: list[str]) -> list[tuple[str, bytes]]:
    out = []
    for n in names:
        try:
            out.append((n, (Path(folder) / n).read_bytes()))
        except OSError:
            pass  # the game may still be writing it; it will be picked up next time
    return out


# --------------------------------------------------------------------------- #
# Career store
# --------------------------------------------------------------------------- #


@dataclass
class CareerSettings:
    name: str
    folder: str = ""  # watched Scorecards folder, "" if none
    updated: float = 0.0
    my_teams: list = field(default_factory=list)  # the teams you play as (the "My team" page)
    notes: dict = field(default_factory=dict)  # match journal: scorecard file name -> your note
    remembered: dict = field(default_factory=dict)  # last section / season / team picked, so every page opens on it


def _slug(name: str) -> str:
    return re.sub(r"[^\w\- ]+", "_", name).strip() or "career"


class CareerStore:
    def __init__(self, root: Path | None = None):
        self.root = Path(root) if root else home_dir()
        self.careers_dir = self.root / "careers"

    def _dir(self, name: str) -> Path:
        return self.careers_dir / _slug(name)

    def names(self) -> list[str]:
        if not self.careers_dir.is_dir():
            return []
        out = []
        for d in sorted(self.careers_dir.iterdir()):
            f = d / "settings.json"
            if f.is_file():
                try:
                    out.append(json.loads(f.read_text())["name"])
                except (ValueError, KeyError):
                    pass
        return out

    def save(self, career: Career, settings: CareerSettings) -> None:
        d = self._dir(career.name)
        d.mkdir(parents=True, exist_ok=True)
        settings.updated = time.time()
        (d / "career.stats-pack.zip").write_bytes(career.to_pack())
        (d / "settings.json").write_text(json.dumps(asdict(settings), indent=1))
        (self.root / "last.json").write_text(json.dumps({"career": career.name}))

    def load_settings(self, name: str) -> tuple[Path, CareerSettings]:
        d = self._dir(name)
        raw = json.loads((d / "settings.json").read_text())
        return d, CareerSettings(**{k: v for k, v in raw.items() if k in ("name", "folder", "updated", "my_teams", "notes", "remembered")})

    def save_settings(self, settings: CareerSettings) -> None:
        """Only the settings (e.g. My team), without rewriting the career file."""
        d = self._dir(settings.name)
        if d.is_dir():
            (d / "settings.json").write_text(json.dumps(asdict(settings), indent=1))

    def load(self, name: str) -> tuple[Career, CareerSettings]:
        d, settings = self.load_settings(name)
        career = Career.from_pack((d / "career.stats-pack.zip").read_bytes())
        career.name = name
        return career, settings

    def delete(self, name: str) -> None:
        d = self._dir(name)
        for p in d.glob("*"):
            p.unlink()
        d.rmdir()

    # ------------------------------------------------------------ backups
    # Documents\Cricket Captain Stats Pack\backups\<career>\2026-09-28_141500.stats-pack.zip
    BACKUP_EVERY = 7 * 24 * 3600  # seconds
    BACKUPS_KEPT = 8

    def _backup_dir(self, name: str) -> Path:
        return self.root / "backups" / _slug(name)

    def backups(self, name: str) -> list[tuple[Path, float]]:
        """(file, time made) for every backup of a career, newest first."""
        d = self._backup_dir(name)
        out = []
        for p in d.glob("*.stats-pack.zip") if d.is_dir() else []:
            try:
                made = time.mktime(time.strptime(p.name.split(".")[0][:17], "%Y-%m-%d_%H%M%S"))
            except ValueError:
                made = p.stat().st_mtime
            out.append((p, made))
        return sorted(out, key=lambda x: x[1], reverse=True)

    def backup(self, name: str, now: float | None = None, note: str = "") -> Path:
        """Copy a career's saved file into its backups folder and keep only the newest few."""
        now = time.time() if now is None else now
        src = self._dir(name) / "career.stats-pack.zip"
        d = self._backup_dir(name)
        d.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y-%m-%d_%H%M%S", time.localtime(now))
        dest = d / f"{stamp}{'_' + _slug(note) if note else ''}.stats-pack.zip"
        dest.write_bytes(src.read_bytes())
        for old, _ in self.backups(name)[self.BACKUPS_KEPT:]:
            old.unlink()
        return dest

    def backup_due(self, name: str, now: float | None = None) -> bool:
        now = time.time() if now is None else now
        b = self.backups(name)
        return not b or now - b[0][1] >= self.BACKUP_EVERY

    def backup_all_due(self, now: float | None = None) -> list[str]:
        """Back up every career whose last backup is a week old (or that has none)."""
        done = []
        for name in self.names():
            if (self._dir(name) / "career.stats-pack.zip").is_file() and self.backup_due(name, now):
                self.backup(name, now)
                done.append(name)
        return done

    def restore(self, name: str, backup: Path) -> Career:
        """Put a backup back as the career.  The current state is backed up first,
        so a restore can itself be undone."""
        data = Path(backup).read_bytes()  # read first: the backup below may prune the oldest file
        if not Career.is_pack(data):
            raise ValueError(f"{backup} is not a career file")
        self.backup(name, note="before-restore")
        d, settings = self.load_settings(name)
        (d / "career.stats-pack.zip").write_bytes(data)
        career, _ = self.load(name)
        self.save(career, settings)
        return career

    def last_used(self) -> str | None:
        f = self.root / "last.json"
        try:
            name = json.loads(f.read_text())["career"]
        except (OSError, ValueError, KeyError):
            return None
        return name if name in self.names() else None


# --------------------------------------------------------------------------- #
# Watching (one record per folder, shared by every career that uses it)
# --------------------------------------------------------------------------- #


@dataclass
class SyncResult:
    career: Career
    settings: CareerSettings
    added: list[str]  # sources of newly loaded matches
    failed: list[tuple[str, str]]  # (source, reason)
    refreshed: bool = False  # the career was rebuilt without new matches (e.g. file times attached)


def _result(career: Career, settings: CareerSettings) -> SyncResult:
    return SyncResult(career, settings, [r.source for r in career.report if r.status == "loaded"],
                      [(r.source, r.message) for r in career.report if r.status == "failed"])


def _times(snap: dict[str, list]) -> dict[str, float]:
    return {n: sig[0] for n, sig in snap.items()}


class Watcher:
    """Knows, for each watched folder, which files it has already seen and
    which career it belongs to.  One folder = one career: if several saves
    write into the same folder, their matches go into that one career."""

    def __init__(self, store: CareerStore):
        self.store = store
        self.path = store.root / "folders.json"

    def _all(self) -> dict:
        try:
            return json.loads(self.path.read_text())
        except (OSError, ValueError):
            return {}

    def _write(self, data: dict) -> None:
        self.store.root.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=1))

    def owner(self, folder: str) -> str | None:
        """The career that watches this folder, if any."""
        name = self._all().get(folder, {}).get("career")
        return name if name in self.store.names() else None

    def rescan(self, folder: str) -> None:
        """Forget which files in a folder were already read, so the next sync
        reads them all again (used after restoring a backup: matches still in
        the folder come back, and ones already in the career are skipped)."""
        data = self._all()
        if folder in data:
            data[folder]["snapshot"] = {}
            self._write(data)

    def create(self, name: str, folder: Path) -> SyncResult:
        """Start a career on a folder, taking everything already in it."""
        folder_key = str(folder)
        if self.owner(folder_key):
            raise ValueError(f"{folder} is already watched by {self.owner(folder_key)}")
        data = self._all()
        snap = snapshot(folder)
        career = Career.build(name, read_files(folder, list(snap)), times=_times(snap))
        settings = CareerSettings(name=name, folder=folder_key)
        self.store.save(career, settings)
        data[folder_key] = {"snapshot": snap, "career": name, "times": True}
        self._write(data)
        return _result(career, settings)

    def sync(self, folder: str) -> SyncResult | None:
        """Add new or changed scorecards to the folder's career.
        Returns None when nothing changed."""
        path = Path(folder)
        if not path.is_dir():
            return None
        data = self._all()
        entry = data.setdefault(folder, {"snapshot": {}})
        name = entry.get("career")
        if not name or name not in self.store.names():
            return None
        snap = snapshot(path)
        changed = [n for n, sig in snap.items() if entry["snapshot"].get(n) != sig]
        if not changed and not entry.get("times"):
            # a career made before file times were kept: attach them once, so games left
            # over from an earlier playthrough of a season can be told apart
            career, settings = self.store.load(name)
            career = career.add_files([], times=_times(snap))
            self.store.save(career, settings)
            entry["snapshot"], entry["times"] = snap, True
            self._write(data)
            return SyncResult(career, settings, [], [], refreshed=True)
        if not changed:
            if snap != entry["snapshot"]:  # only deletions: remember them, nothing to load
                entry["snapshot"] = snap
                self._write(data)
            return None
        career, settings = self.store.load(name)
        career = career.add_files(read_files(path, changed), times=_times(snap))
        self.store.save(career, settings)
        entry["snapshot"], entry["times"] = snap, True
        self._write(data)
        return _result(career, settings)
