"""Numbers kept with each career until its matches change. The slow sums (every match's excitement rating, the
marks out of 10, scouting) are worked out once and then every page reuses them; two pages asking for the same thing
at once wait for one answer instead of working it out twice."""

from __future__ import annotations

import threading

_lock = threading.Lock()


def kept(career, key, make):
    """`make()`, worked out once per career (and again when its matches change)."""
    stamp = (id(career.matches), len(career.matches))
    with _lock:
        box = getattr(career, "_kept", None)
        if box is None or box["stamp"] != stamp:
            box = {"stamp": stamp, "values": {}, "locks": {}}
            try:
                career._kept = box
            except AttributeError:   # a career that can't hold it: work it out every time
                return make()
        if key in box["values"]:
            return box["values"][key]
        one = box["locks"].setdefault(key, threading.Lock())
    with one:
        if key not in box["values"]:
            box["values"][key] = make()
        return box["values"][key]
