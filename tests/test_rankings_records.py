"""Player ratings, team Elo, records and the New record! alerts."""

from pathlib import Path

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

from ccstats import rankings as R
from ccstats import records as RC
from ccstats.demo_league import generate
from ccstats.loader import Career
from ccstats.stats import Scope

ROOT = Path(__file__).parent.parent
FIXTURES = sorted((Path(__file__).parent / "fixtures").glob("*.txt"))


@pytest.fixture(scope="module")
def career():
    return Career.build("rr", [(p.name, p.read_bytes()) for p in FIXTURES])


@pytest.fixture(scope="module")
def demo():
    return Career.build("demo", [(n, t.encode()) for n, t in generate()])


def test_elo_is_zero_sum_and_starts_at_1500(demo, career):
    for c in (demo, career):
        for section in c.matches.section.unique():
            table, hist = R.team_elo(c, section)
            if table.empty:
                continue
            assert abs(table.elo.mean() - 1500) < 1e-6, section
            first = hist.groupby("team").before.first()
            assert (first == 1500).all()
            # every team's rating after one match is its rating before the next
            for team, g in hist.groupby("team"):
                assert np.allclose(g.before.iloc[1:].to_numpy(), g.after.iloc[:-1].to_numpy())


def test_elo_winner_goes_up(demo):
    _, hist = R.team_elo(demo, "Indian Premier League")
    m = demo.matches.set_index("match_id")
    for r in hist.itertuples():
        w = m.loc[r.match_id, "winner"]
        if w == r.team:
            assert r.after > r.before
        elif w:
            assert r.after < r.before


def test_player_ratings(demo):
    t = R.player_ratings(demo, "Indian Premier League")
    bat, bowl = R.innings_points(demo, "Indian Premier League")
    assert (t.batting_innings.where(t.batting.notna(), R.MIN_INNINGS) >= R.MIN_INNINGS).all()
    # 500 = the average of the better half
    b = t.batting.dropna()
    assert abs(b[b >= b.median()].mean() - 500) < 2
    # the rating is the recency-weighted points: check one player by hand
    p = t.sort_values("batting").player.iloc[-1]
    pts = bat[bat.player == p].points.to_numpy(float)
    w = R.DECAY ** np.arange(len(pts) - 1, -1, -1)
    raw_all = bat.groupby("player").points.apply(lambda s: R._weighted(s.to_numpy(float)) if len(s) >= R.MIN_INNINGS else np.nan)
    assert abs(t.set_index("player").batting[p] - round((pts * w).sum() / w.sum() / R._scale(raw_all) * 500)) <= 1
    # the history ends on the table's rating
    h = R.rating_history(demo, "Indian Premier League", [p])
    assert abs(h.rating.iloc[-1] - t.set_index("player").batting[p]) <= 1
    assert ((t.all_round - (t.batting * t.bowling / 1000).round()).dropna().abs() <= 0).all()


def test_records_hand_checked(career):
    ids = Scope(sections=["T20 Blast"]).match_ids(career.matches)
    r = RC.records(career, ids)
    hs = r["Highest individual scores"].iloc[0]
    assert (hs.holder, hs.value) == ("M Savage", "104* (51)")
    lo = r["Lowest completed totals"].iloc[0]
    assert (lo.holder, lo.value, lo.against) == ("Northamptonshire", "96", "Somerset")
    tests = RC.records(career, Scope(sections=["Tests"]).match_ids(career.matches))
    assert tests["Best bowling in a match"].iloc[0][["holder", "value"]].tolist() == ["S Khan", "9/232"]
    assert tests["Biggest wins by runs"].iloc[0][["holder", "value"]].tolist() == ["England", "299 runs"]


def test_records_are_sorted_and_ranked(career):
    for section in career.matches.section.unique():
        for name, t in RC.records(career, Scope(sections=[section]).match_ids(career.matches)).items():
            asc = name.startswith("Lowest")
            s = list(t["sort"])
            assert s == sorted(s, reverse=not asc), (section, name)
            assert t["rank"].iloc[0] == 1 and list(t["rank"]) == sorted(t["rank"])


def test_partnerships_add_up_to_the_totals(career):
    """Every stand in an innings, unbroken one included, adds up to the runs off the bat plus extras."""
    ids = Scope(sections=["T20 Blast"]).match_ids(career.matches)
    t = RC.records(career, ids, top=10_000)["Highest partnerships"]
    inn = career.innings[career.innings.match_id.isin(ids)]
    per_match = t.groupby("match_id").apply(lambda g: g["sort"].sum(), include_groups=False)
    assert (per_match.sort_index() == inn.groupby("match_id").runs.sum().sort_index()).all()


def test_new_record_alert_when_a_match_breaks_one(career):
    src = RC.records(career, Scope(sections=["T20 Blast"]).match_ids(career.matches))["Highest individual scores"].source.iloc[0]
    others = [(p.name, p.read_bytes()) for p in FIXTURES if p.name != src]
    before = Career.build("rr", others)
    assert src not in set(before.matches.source)
    after = before.add_files([(src, (Path(__file__).parent / "fixtures" / src).read_bytes())])
    msgs = RC.new_records(after, [src])
    assert any("Highest individual scores: M Savage 104*" in s for s in msgs)
    assert any("Highest team totals: Glamorgan 230/5" in s for s in msgs)
    assert all("T20 Blast" in s for s in msgs)
    # re-adding an old match that holds no record says nothing
    held = {t.source.iloc[0] for k, t in RC.records(career, Scope(sections=["T20 Blast"]).match_ids(career.matches), top=1).items()
            if "season" not in k}
    # ...nor one that holds the best stand for a wicket (50 or more, not shared)
    from ccstats import partnerships as P
    blast = career.matches[career.matches.section == "T20 Blast"]
    st_ = P.stands(career, blast.match_id).merge(blast[["match_id", "source"]], on="match_id")
    for _, g in st_.groupby("wicket"):
        g = g.sort_values("runs", ascending=False)
        if len(g) >= 2 and g.runs.iloc[0] >= 50 and g.runs.iloc[1] < g.runs.iloc[0]:
            held.add(g.source.iloc[0])
    quiet = [s for s in blast.source if s not in held]
    assert quiet
    assert RC.new_records(career, quiet) == []


@pytest.mark.parametrize("page,keys", [("rankings.py", ["rk_section"]), ("records.py", ["rc_section"])])
@pytest.mark.parametrize("which", ["career", "demo"])
def test_pages_every_section(page, keys, which, career, demo):
    c = career if which == "career" else demo
    for section in c.matches.section.unique():
        for kind in (["Batting", "Bowling", "All-round"] if page == "rankings.py" else [None]):
            at = AppTest.from_file(str(ROOT / "views" / page), default_timeout=60)
            at.session_state["career_obj"] = c
            for k in keys:
                at.session_state[k] = section
            if kind:
                at.session_state["rk_kind"] = kind
            at.run()
            assert not at.exception, (page, section, kind, at.exception)
