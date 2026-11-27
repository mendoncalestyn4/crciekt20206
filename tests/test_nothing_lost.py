"""The nothing-lost crawl, automatic (your yes of 26 November; the weekly run): every page and tab of the new site
opened and read, and every line of the old site's checklist (design/INVENTORY.md) found before must still be found
(tests/frozen/nothing_lost.json, made by tools/nothing_lost.py; the lines reworded or moved are listed in
design/NOTHING_LOST_CRAWL.md and read again at the switch-over)."""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.weekly
def test_nothing_found_before_is_lost_now():
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "nothing_lost.py"), "--check"], capture_output=True,
                       text=True, cwd=ROOT, timeout=7000)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
