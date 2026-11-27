"""The 20-season career (stage 5, item 7; in the weekly run, so a normal test run is no slower): about 12,800 made-up
matches of every kind (tests/longcareer.py) read exactly as your scorecards are.

- every scorecard reads cleanly (nothing that doesn't add up, nothing put right by a guess), every season of every
  competition is there, and no two different players are taken for one;
- the same number on every page (the checks of test_same_number.py, run on this career);
- every page answers, and in good time, with 20 seasons in it (each answer's time is printed), and every number on
  those pages is as frozen (tests/frozen/long.json.gz: the career is made the same way every time);
- the second, separately written reader agrees with the site on every one of its scorecards."""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

import pytest

import longcareer as LC
import test_same_number as SN
import test_second_counter as SC
from ccstats.loader import Career

pytestmark = pytest.mark.weekly
SEASONS = 20
SLOWEST = 60.0      # seconds: the most any one answer may take, asked cold with 20 seasons in the career


@pytest.fixture(scope="module")
def files(tmp_path_factory):
    d = tmp_path_factory.mktemp("long")
    out = []
    for name, text in LC.generate(seasons=SEASONS):
        f = d / name
        f.write_text(text, encoding="utf-8")
        out.append(f)
    return out


@pytest.fixture(scope="module")
def career(files):
    c = Career.build("Long career", [(f.name, f.read_bytes()) for f in files])
    c.count_fielding = False
    return c


def test_every_card_reads_cleanly_and_every_season_is_there(career, files):
    assert len(career.matches) == len(files) > 12000
    assert career.problems.empty, career.problems.head().to_string()
    assert career.guesses.empty and career.leftovers.empty
    assert career.auto_joins.empty and career.auto_splits.empty, (career.auto_joins.to_string(), career.auto_splits.to_string())
    seasons = career.matches.groupby("section").season.nunique()
    assert len(seasons) == 14 and (seasons == SEASONS).all(), seasons.to_dict()
    # careers come and go: players debut and retire through the 20 seasons
    first = career.batting.merge(career.matches[["match_id", "date"]]).groupby("player").date.agg(["min", "max"])
    assert (first["min"].dt.year > 2030).sum() > 500 and (first["max"].dt.year < 2040).sum() > 500


@pytest.mark.parametrize("check", [n for n in dir(SN) if n.startswith("test_")])
def test_the_same_number_everywhere_on_20_seasons(career, check):
    getattr(SN, check)(career)


def test_the_second_reader_agrees_on_every_card(career, files):
    SC.FILES = files
    SC.test_every_line_counted_the_same(career)
    SC.test_averages_strike_rates_and_economy_from_my_own_counts(career)


def test_every_page_answers_in_good_time_and_as_frozen(files):
    import gzip
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
    import freeze
    from test_frozen import differences
    urls = freeze.long_urls()
    live = freeze.long_site(files)
    took: list[tuple[float, str]] = []
    answers: dict = {}
    try:
        for u in urls:
            t = time.perf_counter()
            for _ in range(1200):                     # the career is still being read at first: wait for it
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{live.port}{u}", timeout=600) as r:
                        answers[u] = freeze.clean(json.loads(r.read()))
                    break
                except urllib.error.HTTPError as e:
                    if e.code == 503:
                        time.sleep(0.5)
                        continue
                    raise AssertionError(f"{u}: {e.code} {e.read()[:200]!r}")
            took.append((time.perf_counter() - t, u))
    finally:
        live.stop()
    took.sort(reverse=True)
    print("\nslowest answers with 20 seasons:\n" + "\n".join(f"  {s:6.1f}s  {u}" for s, u in took[:15]), file=sys.stderr)
    slow = [(round(s, 1), u) for s, u in took[1:] if s > SLOWEST]      # (the first waits for the career to be read)
    assert not slow, slow
    kept = freeze.FROZEN / "long.json.gz"
    if kept.is_file():
        with gzip.open(kept, "rt", encoding="utf-8") as f:
            frozen = json.load(f)
        moved = {u: d for u in frozen if (d := differences(frozen[u], answers.get(u)))}
        assert not moved, ("numbers moved on the 20-season career (if meant: python tools/freeze.py save-long \"why\"):\n"
                           + "\n".join(f"{u}\n    " + "\n    ".join(d) for u, d in list(moved.items())[:10]))
