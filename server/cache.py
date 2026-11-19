"""Numbers kept with each career until its matches change. The slow sums (every match's excitement rating, the
marks out of 10, scouting) are worked out once and then every page reuses them; two pages asking for the same thing
at once wait for one answer instead of working it out twice.

Kept on disk too (the speed work, your picks of 14 November): every answer is written to the careers' home and read
back at the next start, so a page worked out once opens at once ever after. The file is stamped with the career's
exact scorecards, its Data check choices, its matches as the site sees them (home and away from your schedule
included) and the site's own version (ccstats/keep.py): when any of those changes, nothing in it is used and every
answer is worked out afresh."""

from __future__ import annotations

import hashlib
import os
import pickle
import threading
import time

import pandas as pd

from ccstats import keep as KEEP

_lock = threading.Lock()
KEEP_FILES = 4          # answer files kept on disk (the newest: a career or two, and the one before the latest match)


def _stamp(career) -> str:
    """The career's fingerprint, worked out once per career object."""
    s = getattr(career, "_disk_stamp", None)
    if s is None:
        seen = pd.util.hash_pandas_object(career.matches.astype(str), index=False).to_numpy().tobytes()
        s = KEEP.stamp(career, hashlib.sha1(seen).hexdigest())
        try:
            object.__setattr__(career, "_disk_stamp", s)
        except Exception:   # noqa: BLE001
            pass
    return s


def _file(career):
    return KEEP.DIR / f"answers-{_stamp(career)[:20]}.pickle" if KEEP.DIR else None


def _load(career) -> dict:
    f = _file(career)
    if not f or not f.is_file():
        return {}
    try:
        with open(f, "rb") as fh:
            got = pickle.load(fh)
        return got["values"] if got.get("stamp") == _stamp(career) else {}
    except Exception:   # noqa: BLE001 - a damaged or half-written file: everything is worked out again
        return {}


def kept(career, key, make):
    """`make()`, worked out once per career (and again when its matches change)."""
    stamp = (id(career.matches), len(career.matches))
    with _lock:
        box = getattr(career, "_kept", None)
        if box is None or box["stamp"] != stamp:
            box = {"stamp": stamp, "values": {}, "locks": {}, "new": False, "saved": time.time()}
            try:
                career._kept = box
            except AttributeError:   # a career that can't hold it: work it out every time
                return make()
            box["values"] = _load(career)
        if key in box["values"]:
            return box["values"][key]
        one = box["locks"].setdefault(key, threading.Lock())
    with one:
        if key not in box["values"]:
            box["values"][key] = make()
            box["new"] = True
        return box["values"][key]


def save(career, every: float = 0) -> bool:
    """Write the career's kept answers to disk if anything new was worked out (and, with `every`, at most that often);
    True when written. Each answer that can't be written is simply left out (it's worked out again next time)."""
    box = getattr(career, "_kept", None)
    f = _file(career)
    if not f or box is None or not box["new"] or time.time() - box["saved"] < every:
        return False
    with _lock:
        values = dict(box["values"])
        box["new"], box["saved"] = False, time.time()
    keep = {}
    for k, v in values.items():
        try:
            pickle.dumps(v, protocol=pickle.HIGHEST_PROTOCOL)
            keep[k] = v
        except Exception:   # noqa: BLE001
            pass
    KEEP.DIR.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(f".{os.getpid()}.{threading.get_ident()}.tmp")
    with open(tmp, "wb") as fh:
        pickle.dump({"stamp": _stamp(career), "values": keep}, fh, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(tmp, f)
    old = sorted(KEEP.DIR.glob("answers-*.pickle"), key=lambda p: p.stat().st_mtime, reverse=True)[KEEP_FILES:]
    for p in old:
        try:
            p.unlink()
        except OSError:
            pass
    KEEP.save()
    return True


def put(career, key, value) -> None:
    """An answer worked out elsewhere (a helper on another core, from the same scorecards and code), kept like any
    other; one already kept is left as it is."""
    box = getattr(career, "_kept", None)
    if box is None:
        kept(career, ("_box",), lambda: True)
        box = getattr(career, "_kept", None)
        if box is None:
            return
    with _lock:
        if key not in box["values"]:
            box["values"][key] = value
            box["new"] = True


def ready(career, key) -> bool:
    """Whether an answer is already kept (in memory or read back from disk)."""
    box = getattr(career, "_kept", None)
    return box is not None and key in box["values"]


def aim_fits(career):
    """The score to aim for's fit for each length of game, kept with the career (the slow part, shared by Opponent
    preview and My team)."""
    from ccstats import aim as AIM
    return lambda length: kept(career, ("aim_model", length), lambda: AIM.model(career, length))
