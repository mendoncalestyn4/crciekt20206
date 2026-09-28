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
from dataclasses import asdict, dataclass
from pathlib import Path

from .loader import Career, Fixes


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
        return d, CareerSettings(**{k: v for k, v in raw.items() if k in ("name", "folder", "updated")})

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


def _result(career: Career, settings: CareerSettings) -> SyncResult:
    return SyncResult(career, settings, [r.source for r in career.report if r.status == "loaded"],
                      [(r.source, r.message) for r in career.report if r.status == "failed"])


class Watcher:
    """Knows, for each watched folder, which files it has already seen and
    which career is **Playing now**.  New scorecards go to that career."""

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

    def playing(self, folder: str) -> str | None:
        return self._all().get(folder, {}).get("playing")

    def set_playing(self, folder: str, name: str) -> None:
        data = self._all()
        data.setdefault(folder, {"snapshot": {}})["playing"] = name
        self._write(data)

    def careers_on(self, folder: str) -> list[str]:
        out = []
        for name in self.store.names():
            try:
                _, settings = self.store.load_settings(name)
            except OSError:
                continue
            if settings.folder == folder:
                out.append(name)
        return out

    def create(self, name: str, folder: Path, include_existing: bool = True) -> SyncResult:
        """Start a career on a folder and make it Playing now.  The first
        career on a folder takes everything already there; a second save on
        the same folder starts empty unless `include_existing`."""
        folder_key = str(folder)
        data = self._all()
        snap = snapshot(folder)
        files = read_files(folder, list(snap)) if include_existing else []
        career = Career.build(name, files)
        settings = CareerSettings(name=name, folder=folder_key)
        self.store.save(career, settings)
        data[folder_key] = {"snapshot": snap, "playing": name}
        self._write(data)
        return _result(career, settings)

    def sync(self, folder: str) -> SyncResult | None:
        """Add new or changed scorecards to the Playing now career.
        Returns None when nothing changed (or no career is Playing now)."""
        path = Path(folder)
        if not path.is_dir():
            return None
        data = self._all()
        entry = data.setdefault(folder, {"snapshot": {}})
        name = entry.get("playing")
        if not name or name not in self.store.names():
            return None
        snap = snapshot(path)
        changed = [n for n, sig in snap.items() if entry["snapshot"].get(n) != sig]
        if not changed:
            if snap != entry["snapshot"]:  # only deletions: remember them, nothing to load
                entry["snapshot"] = snap
                self._write(data)
            return None
        career, settings = self.store.load(name)
        career = career.add_files(read_files(path, changed))
        self.store.save(career, settings)
        entry["snapshot"] = snap
        self._write(data)
        return _result(career, settings)
