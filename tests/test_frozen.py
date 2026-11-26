"""The frozen copy (stage 5, kept for good): every page's answer for the test career, asked again on every test run and
compared with the copy kept in tests/frozen/ (made by tools/freeze.py). Any number that moves fails, naming the page
and the first places it moved; a change that is meant is frozen again with its reason (tests/frozen/CHANGES.md)."""

from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FROZEN = ROOT / "tests" / "frozen"
sys.path.insert(0, str(ROOT / "tools"))
import freeze  # noqa: E402

pytestmark = pytest.mark.skipif(not (FROZEN / "fixtures.json.gz").is_file(), reason="no frozen copy yet")


def differences(a, b, where="", out=None, limit=8):
    out = [] if out is None else out
    if len(out) >= limit:
        return out
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append(f"{where}.{k}: {'new' if k not in a else 'gone'}")
            else:
                differences(a[k], b[k], f"{where}.{k}", out, limit)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f"{where}: {len(a)} items, now {len(b)}")
        for i, (x, y) in enumerate(zip(a, b)):
            differences(x, y, f"{where}[{i}]", out, limit)
    elif a != b:
        out.append(f"{where}: {str(a)[:60]!r} → {str(b)[:60]!r}")
    return out


def test_every_number_on_every_page_is_as_frozen():
    with gzip.open(FROZEN / "fixtures.json.gz", "rt", encoding="utf-8") as f:
        kept = json.load(f)
    live = freeze.site()
    try:
        now = freeze.ask(live, list(kept))
    finally:
        live.stop()
    moved = {u: d for u in kept if (d := differences(kept[u], now.get(u)))}
    assert not moved, ("numbers moved (if meant: python tools/freeze.py save \"why\"):\n" +
                       "\n".join(f"{u}\n    " + "\n    ".join(d) for u, d in list(moved.items())[:10]))
