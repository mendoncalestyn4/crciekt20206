"""Sums kept on disk between starts (the speed work, your picks of 14 November).

Two kinds:

- `memo(kind)`: answers that depend only on what they're worked out from (one innings' batting order and fall of
  wickets, say). Each is stored under its own inputs, so it can never be out of date: a new match only adds its own
  answers, and the rest are read back. Kept in one file per kind, shared by every career.
- `stamp(...)`: the fingerprint of a career's exact scorecards and choices, for things kept per career (the server's
  page answers): when any scorecard or choice changes, the stamp changes and the old answers are never used.

Every file is named with the site's own version (a fingerprint of its code), so an update never reads answers worked
out by older code. Nothing here is needed for the numbers to be right: with no folder set (tests, a fresh PC) or a
file that can't be read, everything is simply worked out again.
"""

from __future__ import annotations

import hashlib
import os
import pickle
import threading
from pathlib import Path

DIR: Path | None = None          # set by the server: <home>/kept
_lock = threading.Lock()
_memos: dict[str, dict] = {}
_dirty: set[str] = set()
_version: str | None = None


def version() -> str:
    """A fingerprint of the site's own code (the engine and the server): any change to either is a new version."""
    global _version
    if _version is None:
        root = Path(__file__).resolve().parent.parent
        h = hashlib.sha1()
        for part in ("ccstats", "server"):
            for f in sorted((root / part).glob("*.py")):
                h.update(f.name.encode())
                h.update(f.read_bytes())
        _version = h.hexdigest()[:12]
    return _version


def _file(kind: str) -> Path | None:
    return DIR / f"memo-{kind}-{version()}.pickle" if DIR else None


def memo(kind: str) -> dict:
    """The kept answers of one kind ({inputs: answer}), read from disk the first time."""
    with _lock:
        if kind not in _memos:
            got: dict = {}
            f = _file(kind)
            if f and f.is_file():
                try:
                    with open(f, "rb") as fh:
                        got = pickle.load(fh)
                except Exception:   # noqa: BLE001 - a damaged or half-written file: worked out again
                    got = {}
            _memos[kind] = got
        return _memos[kind]


def changed(kind: str) -> None:
    """New answers of this kind were added: written to disk at the next `save()`."""
    with _lock:
        _dirty.add(kind)


def save() -> None:
    """Write every kind with new answers (to a temporary file first, so a crash never leaves half a file)."""
    if not DIR:
        return
    with _lock:
        todo = [(k, dict(_memos[k])) for k in _dirty if k in _memos]
        _dirty.clear()
    DIR.mkdir(parents=True, exist_ok=True)
    for kind, values in todo:
        f = _file(kind)
        tmp = f.with_suffix(f".{os.getpid()}.tmp")
        with open(tmp, "wb") as fh:
            pickle.dump(values, fh, protocol=pickle.HIGHEST_PROTOCOL)
        os.replace(tmp, f)
    # older versions' files are never read again
    for old in DIR.glob("memo-*.pickle"):
        if not old.stem.endswith(version()):
            try:
                old.unlink()
            except OSError:
                pass


def stamp(career, *extra) -> str:
    """A career's fingerprint: its exact scorecards (every file's text), its Data check choices, and anything else
    its answers depend on, with the site's version."""
    h = hashlib.sha1(version().encode())
    for source in sorted(career.texts):
        h.update(source.encode())
        t = career.texts[source]
        h.update(t.encode() if isinstance(t, str) else bytes(t))
    h.update(career.fixes.to_json().encode())
    for x in extra:
        h.update(repr(x).encode())
    return h.hexdigest()


def on_career(career, key, make):
    """`make()` worked out once per career in memory (kept until its matches change): for a sum several pages ask for
    with the same matches."""
    stamp = (id(career.matches), len(career.matches))
    box = getattr(career, "_on_career", None)
    if box is None or box.get("_stamp") != stamp:
        box = {"_stamp": stamp}
        try:
            object.__setattr__(career, "_on_career", box)
        except Exception:   # noqa: BLE001 - a career that can't hold it: worked out every time
            return make()
    if key not in box:
        box[key] = make()
    return box[key]


def ids_key(ids) -> tuple:
    """A set of matches as a key (the same matches in any order are the same key)."""
    return tuple(sorted(set(map(str, ids))))


def reset() -> None:
    """Forget what's in memory (tests)."""
    with _lock:
        _memos.clear()
        _dirty.clear()
