"""Title and playoff odds: the standings they start from, chances that add up, certainties that are certain, the
history ending on the real champion, the knockout formats, and the Competitions page."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from ccstats import odds as O
from ccstats import teamplay as TP
from ccstats.demo_league import generate
from ccstats.extras import honours
from ccstats.loader import Career
from ccstats.tables import league_tables

HERE = Path(__file__).parent
IPL = "Indian Premier League"


@pytest.fixture(scope="module")
def demo():
    return Career.build("demo", [(n, t.encode()) for n, t in generate()])


@pytest.fixture(scope="module")
def fixtures():
    return Career.build("fx", [(p.name, p.read_bytes()) for p in sorted((HERE / "fixtures").glob("*.txt"))])


def halfway(c, season):
    lg = c.matches[(c.matches.event == IPL) & (c.matches.season == season) & ~c.matches.knockout]
    days = sorted(lg.date.unique())
    return pd.Timestamp(days[len(days) // 2])


def test_the_standings_are_the_league_tables(demo, fixtures):
    checked = 0
    for c in (demo, fixtures):
        m = c.matches
        for (ev, se), g in m[~m.knockout].groupby(["event", "season"]):
            if g.competition.iloc[0] in ("Test", "ODI", "T20I"):
                continue
            mine = O._Season(c, ev, se, None, None).table().set_index("team")
            for _, t, _ in league_tables(c, g.match_id):
                for r in t.itertuples():
                    x = mine.loc[r.team]
                    assert (x.played, x.won, x.lost) == (r.played, r.won, r.lost), (ev, r.team)
                    assert x.points == (r.points if r.points == r.points else 0), (ev, r.team)
                    if r.nrr == r.nrr:
                        assert x.nrr == pytest.approx(r.nrr), (ev, r.team)
                    checked += 1
    assert checked > 20


def test_the_shape_comes_from_the_season_before(demo):
    d = TP.qualification_defaults(demo, IPL, "2027")
    assert (d["games"], d["places"], d["extra"]) == (18, 4, 0)  # 10 sides home and away, the top four go through


def test_the_chances_add_up(demo):
    r = O.season_odds(demo, IPL, "2027", before=halfway(demo, "2027"))
    t = r["table"]
    assert r["state"] == "open" and len(t) == 10
    assert t.title.sum() == pytest.approx(100)
    assert t.top.sum() == pytest.approx(100)
    assert t.playoffs.sum() == pytest.approx(400)
    assert ((t[["title", "top", "playoffs"]] >= 0) & (t[["title", "top", "playoffs"]] <= 100)).all().all()
    assert (t.title <= t.playoffs + 1e-9).all() and (t.top <= t.playoffs + 1e-9).all()
    # the same question gives the same answer
    again = O.season_odds(demo, IPL, "2027", before=halfway(demo, "2027"))
    assert again["table"].equals(t)


def test_certain_places_are_certain(demo):
    """Late in the season, a side the planner says is through on points alone is through in every simulation, and
    one that can't catch the top four never is."""
    lg = demo.matches[(demo.matches.event == IPL) & (demo.matches.season == "2027") & ~demo.matches.knockout]
    days = sorted(lg.date.unique())
    seen = set()
    for cut in days[-12:]:
        sub = Career.build("cut", [], existing={s: t for s, t in demo.texts.items()
                                                if s in set(demo.matches[demo.matches.date < cut].source)})
        q = TP.qualification(sub, IPL, "2027", 18, 4).set_index("team")
        odds = O.season_odds(sub, IPL, "2027", 18, 4)
        if odds["state"] != "open":
            continue
        t = odds["table"].set_index("team")
        for team, r in q.iterrows():
            if r.status == "Through":
                assert t.playoffs[team] == 100, (cut, team)
                seen.add("through")
            elif r.status == "Out":
                assert t.playoffs[team] == 0 and t.title[team] == 0, (cut, team)
                seen.add("out")
    assert seen == {"through", "out"}


def test_a_finished_league_stage_and_the_history(demo):
    assert O.season_odds(demo, IPL, "2026")["state"] == "league over"
    h = O.odds_history(demo, IPL, "2026", sims=500)
    end = h[h.date == h.date.max()]
    champ = honours(demo).query("section == @IPL and season == '2026'").champion_teams.iloc[0][0]
    assert end.set_index("team").title[champ] == 100 and end.title.sum() == 100
    for _, day in h.groupby("date"):
        assert day.title.sum() == pytest.approx(100)


def test_the_blast_takes_the_two_best_thirds():
    """Three groups, two through from each and the two best thirds: the field is seeded winners, runners-up, then
    the best thirds, and a quarter-final pairs 1 v 8."""
    # one simulation, three groups of three sides; keys: higher is better
    order = [(np.array([[0, 1, 2]]), np.array([[30.0, 20.0, 15.0]])),
             (np.array([[3, 4, 5]]), np.array([[40.0, 25.0, 9.0]])),
             (np.array([[6, 7, 8]]), np.array([[35.0, 18.0, 12.0]]))]
    field = [int(f[0]) for f in O._seeded(order, 2, 2)]
    assert field == [3, 6, 0, 4, 1, 7, 2, 8]  # winners by record, then runners-up, then the two best thirds
    rng = np.random.default_rng(1)
    elo = np.array([1500.0] * 8 + [9999.0])  # side 8 can't lose a knockout game
    assert O._title(rng, elo, order, 2, 2)[0] == 8
    elo = np.array([1500.0] * 5 + [9999.0, 1500, 1500, 1500])  # side 5 finished 3rd but isn't one of the best thirds
    assert O._title(rng, elo, order, 2, 2)[0] != 5


def test_the_competitions_page_shows_the_race(demo):
    cut = halfway(demo, "2027")
    sub = Career.build("cut", [], existing={s: t for s, t in demo.texts.items()
                                            if s in set(demo.matches[demo.matches.date < cut].source)})
    at = AppTest.from_file(str(HERE.parent / "views" / "competitions.py"), default_timeout=120)
    at.session_state["career_obj"] = sub
    at.session_state["cp2_event"] = IPL
    at.session_state["cp2_season"] = "2027"
    at.run()
    assert not at.exception, at.exception
    assert any(s.value == "Title race" for s in at.subheader)
    text = " ".join(m.value for m in at.markdown)
    assert "Through" in text and "Title" in text
    assert any("What it shows" in m.value for m in at.markdown)
