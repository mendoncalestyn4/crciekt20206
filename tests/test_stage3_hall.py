"""Stage 3, Hall of fame (your answers 19, 20, 23, 26, 30, 31): inductions counted again from the scorecards, who's
next in, the best batting duos counted again from the fall of wickets, the firsts in date order and checked against
the matches, and no fielding anywhere."""

from __future__ import annotations

import pytest

from ccstats import demo_league as DL
from ccstats import hall as H
from ccstats.loader import Career
from ccstats.records import by_played
from server import leaderspage as LP
from serverkit import FIXTURES


@pytest.fixture(scope="module")
def league():
    files = DL.generate((2026, 2027, 2028))
    c = Career.build("Demo", [(n, t.encode() if isinstance(t, str) else t) for n, t in files])
    c.count_fielding = False
    return c


@pytest.fixture(scope="module")
def career():
    c = Career.build("Test career", [(f.name, f.read_bytes()) for f in FIXTURES])
    c.count_fielding = False
    return c


def test_inductions_counted_again(league):
    """Each inductee's figures, added up match by match from the scorecards, first reach the bar in the very match
    named; nobody else has reached any bar."""
    sec = league.matches.section.iloc[0]
    kind = H.kind_of(league, sec)
    m = by_played(league, league.matches[league.matches.section == sec])   # in the order played, as the site counts
    ind = H.inductions(league, sec).set_index("player")
    b, w = league.batting, league.bowling
    everyone = set(b[b.match_id.isin(m.match_id)].player)
    for p in everyone:
        runs = wkts = pom = 0
        first = None
        for r in m.itertuples():
            runs += int(b[(b.match_id == r.match_id) & (b.player == p) & b.did_bat].runs.sum())
            wkts += int(w[(w.match_id == r.match_id) & (w.player == p)].wickets.sum())
            pom += int(r.player_of_match == p)
            hit = [label for label, need in H.routes(kind)
                   if all({"runs": runs, "wickets": wkts, "pom": pom}[k] >= v for k, v in need.items())]
            if hit and first is None:
                first = (r.match_id, hit[0])
        if first is None:
            assert p not in ind.index, p
        else:
            assert ind.loc[p, "match_id"] == first[0] and first[1] in ind.loc[p, "route"] + " · " + ind.loc[p, "also"], p
    assert len(ind) > 0


def test_next_in_says_what_is_left(league):
    sec = league.matches.section.iloc[0]
    n = H.next_in(league, sec)
    inside = set(H.inductions(league, sec).player)
    assert len(n) and not set(n.player) & inside
    assert list(n.share) == sorted(n.share, reverse=True) and (n.share < 1).all()
    r = n.iloc[0]
    if r.needs.endswith("runs") and "and" not in r.needs:
        assert int(r.needs.split()[0].replace(",", "")) == H.BARS[H.kind_of(league, sec)]["runs"] - r.runs


def test_batting_duos_counted_again(career):
    """Each pair's runs together are its partnerships from the fall of wickets, added up."""
    from ccstats import partnerships as P
    ids = career.matches[career.matches.section == "ODIs"].match_id
    st = P.stands(career, ids)
    st = st[st.known]
    for r in H.duos(career, ids).itertuples():
        a, b = r.pair.split(" & ")
        mine = st[(st.team == r.team) & (((st.batter1 == a) & (st.batter2 == b)) | ((st.batter1 == b) & (st.batter2 == a)))]
        assert (r.runs, r.stands) == (mine.runs.sum(), len(mine))


def test_firsts_in_order_and_checked(career):
    f = H.firsts(career, "India")
    assert list(f.date) == sorted(f.date)
    m = career.matches
    india = m[(m.home == "India") | (m.away == "India")]
    for sec, g in india.groupby("section"):
        first_match = f[f.what == f"First match in {sec}"]
        assert len(first_match) == 1 and first_match.date.iloc[0] == g.date.min()
        wins = g[g.winner == "India"]
        first_win = f[f.what == f"First win in {sec}"]
        assert (len(first_win) == 1 and first_win.date.iloc[0] == wins.date.min()) if len(wins) else first_win.empty
    b = career.batting[career.batting.match_id.isin(india.match_id) & (career.batting.team == "India")]
    tons = b[b.runs >= 100]
    hundred = f[f.what == "First hundred"]
    if len(tons):
        assert hundred.date.iloc[0] == m.set_index("match_id").date[tons.match_id].min()


def test_hall_page_tabs_and_no_fielding(career):
    for tab in LP.HALL_TABS:
        d = LP.hall_page(career, dict(tab=tab, section="ODIs|T20Is"), ["India"])
        assert d["tab"] == tab
        if tab == "Inductions":
            assert d["ticked"] == ["ODIs"]   # one competition at a time
        if d.get("bars"):
            assert all(d["bars"][k] for k in ("is_", "best", "for_"))
    assert "Deadly duos" not in LP.HALL_TABS
    text = str(LP.hall_page(career, {}, []))
    assert "catch" not in text.lower() and "stump" not in text.lower()
    j = LP.hall_page(career, dict(tab="junk", team="Nobody", season="1066"), [])
    assert j["tab"] == "Inductions"
