"""Helpers on the processor's other cores for getting every page ready (your pick of 14 November: "using the whole
processor"). Each helper reads the same career from the same files, works out players' pages with exactly the same code
as the server, and hands the answers back; the server keeps them like any other. The helpers run at low priority, so
the pages you open always come first."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_site = None


def _lower_priority() -> None:
    try:
        if hasattr(os, "nice"):
            os.nice(10)
        elif sys.platform == "win32":
            import ctypes
            k = ctypes.windll.kernel32
            k.SetPriorityClass(k.GetCurrentProcess(), 0x4000)   # below normal
    except Exception:   # noqa: BLE001 - a helper at normal priority still works
        pass


def start(home: str, name: str) -> None:
    """Each helper's start: the same career, as the server sees it (home and away from your schedule included)."""
    global _site
    _lower_priority()
    from ccstats import keep as KEEP
    from ccstats.local import CareerStore
    from .site import Site
    KEEP.DIR = Path(home) / "kept"
    _site = Site(CareerStore(Path(home)))
    _site.current_name = name


def players(names: list[str], stamp: str) -> list:
    """Each player's page as the server first opens it: [(key, answer)]; nothing if the career isn't the one the
    server is getting ready (a new match arrived meanwhile)."""
    from . import playerpage
    from .cache import _stamp
    c = _site.career()
    if c is None or _stamp(c) != stamp:
        return []
    out = []
    for p in names:
        try:
            picks = playerpage.picks(c, p, "", "")
            out.append((("player", p) + picks, playerpage.page(c, p, *picks)))
        except Exception:   # noqa: BLE001 - a page that can't be worked out here is worked out when it's asked for
            pass
    return out


def helpers() -> int:
    """How many helpers: every core but one (kept for the server and your browser), at most three (each holds the
    career in memory)."""
    if os.environ.get("STATS_PACK_HELPERS", "").isdigit():   # set by the tests (0: none), never needed otherwise
        return int(os.environ["STATS_PACK_HELPERS"])
    return max(0, min(3, (os.cpu_count() or 1) - 1))
