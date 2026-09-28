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
    snapshot: dict = field(default_factory=dict)
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

    def load(self, name: str) -> tuple[Career, CareerSettings]:
        d = self._dir(name)
        settings = CareerSettings(**json.loads((d / "settings.json").read_text()))
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
# Watching
# --------------------------------------------------------------------------- #


@dataclass
class SyncResult:
    career: Career
    settings: CareerSettings
    added: list[str]  # sources of newly loaded matches
    failed: list[tuple[str, str]]  # (source, reason)


def start_watching(name: str, folder: Path, fixes: Fixes | None = None) -> SyncResult:
    """Create a career from everything currently in the folder."""
    snap = snapshot(folder)
    career = Career.build(name, read_files(folder, list(snap)), fixes)
    settings = CareerSettings(name=name, folder=str(folder), snapshot=snap)
    return SyncResult(career, settings, [r.source for r in career.report if r.status == "loaded"],
                      [(r.source, r.message) for r in career.report if r.status == "failed"])


def sync(career: Career, settings: CareerSettings) -> SyncResult | None:
    """Look at the watched folder; if anything is new or changed, add it.

    Matches already in the career stay even if their file is later deleted
    from the folder, so clearing out the game's folder never loses history.
    Returns None when nothing changed."""
    folder = Path(settings.folder)
    if not settings.folder or not folder.is_dir():
        return None
    snap = snapshot(folder)
    changed = [n for n, sig in snap.items() if settings.snapshot.get(n) != sig]
    if not changed:
        if snap != settings.snapshot:  # only deletions: remember, nothing to load
            settings.snapshot = snap
        return None
    updated = career.add_files(read_files(folder, changed))
    settings.snapshot = snap
    return SyncResult(updated, settings, [r.source for r in updated.report if r.status == "loaded"],
                      [(r.source, r.message) for r in updated.report if r.status == "failed"])
