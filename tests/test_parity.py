"""Parity (the plan, section 9 step 3): the new site's numbers equal the current site's for the same career.

Where the current site works a number out inside its page (views/), that page's own lines are copied here as they
are, and the new site's answer must match them exactly. Where both sites call the same engine function, the server
tests already check the new page against it."""

from __future__ import annotations

import pandas as pd
import pytest

from ccstats import tables as T
from ccstats.loader import Career
from server.app import create_app
from serverkit import FIXTURES, Live, make_pc


@pytest.fixture(scope="module")
def career():
    return Career.build("Test career", [(f.name, f.read_bytes()) for f in FIXTURES])


@pytest.fixture(scope="module")
def every(tmp_path_factory):
    """The stats server with a career of every test scorecard."""
    tmp = tmp_path_factory.mktemp("parity")
    pc = make_pc(tmp, files=FIXTURES)
    web = tmp / "dist"
    (web / "assets").mkdir(parents=True)
    (web / "index.html").write_text("<!doctype html><title>Stats Pack</title><div id=root></div>")
    s = Live(create_app(pc[0], web=web, watch_every=0))
    yield s
    s.stop()


def test_every_competition_table_matches_the_current_sites(career):
    """My team's "Sections" table on the current site (views/home.py), now Competitions' "Every competition"."""
    m = career.matches
    old = (m.groupby("section")    # views/home.py, as written there
           .agg(matches=("match_id", "size"), seasons=("season", lambda s: ", ".join(sorted(set(s)))),
                first=("date", "min"), last=("date", "max"), format=("format", "first"), level=("level", "first"))
           .sort_values("matches", ascending=False).reset_index())
    new = T.every_section(m)
    assert list(new.section) == list(old.section) or sorted(new.section) == sorted(old.section)
    o = old.set_index("section")
    for r in new.itertuples():
        x = o.loc[r.section]
        assert (r.matches, r.seasons, r.first, r.last, r.format, r.level) == (x.matches, x.seasons, x["first"], x["last"],
                                                                              x.format, x.level)
    # equal match counts keep the career's own order of sections, so the page doesn't shuffle between loads
    assert list(new.matches) == sorted(new.matches, reverse=True)


def test_every_competition_is_on_the_competitions_page(every):
    d = every.json("/api/competition")
    c = every.app.state.site.career()
    assert [r[0] for r in d["every"]["rows"]] == list(T.every_section(c.matches).section)
    assert d["every"]["cols"] == ["Section", "Matches", "Seasons", "First match", "Latest match", "Format", "Level"]
    assert sum(r[1] for r in d["every"]["rows"]) == len(c.matches)
    assert T.every_section(pd.DataFrame(columns=c.matches.columns)).empty
