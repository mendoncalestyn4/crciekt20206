"""The features asked for since stage 0, checked against their own logic (25 October):

- each wicket's stands on the Teams page counted unbroken stands nowhere, so a side's best stand for a wicket could be
  wrong (England's best 5th-wicket ODI stand showed 46, it was 91*); Teams and Opponent preview now count stands the
  same way, as cricket does (partnerships.by_wicket);
- the stronger and weaker half of the teams went by raw win %, so one win in one game put a side in the stronger
  half; each side now counts as if it had already won 2 and lost 2."""

from pathlib import Path

import pandas as pd
import pytest

from ccstats import analysis as A
from ccstats import partnerships as P
from ccstats import preview as PV
from ccstats.loader import Career

NEW = Path(__file__).parent / "fixtures_2026" / "new_playthrough.zip"


@pytest.fixture(scope="module")
def season():
    return Career.build("2026", [(NEW.name, NEW.read_bytes())])


def test_each_wickets_stands_are_counted_as_cricket_counts_them(season):
    m = season.matches
    seen_unbroken_best = False
    for sec in m.section.unique():
        ids = m[m.section == sec].match_id
        s = P.stands(season, ids)
        for team in sorted(set(s.team)):
            got = A.partnership_by_wicket(season, ids, team).set_index("wicket")
            for w, g in s[s.team == team].groupby("wicket"):
                broken = g[~g.unbroken]
                top = g.sort_values(["runs", "unbroken"], ascending=False).iloc[0]
                assert got.stands[w] == len(g) and got.runs[w] == g.runs.sum() and got.broken[w] == len(broken)
                assert got.best[w] == top.runs and bool(got.best_unbroken[w]) == bool(top.unbroken)
                if len(broken):
                    assert got.average[w] == pytest.approx(g.runs.sum() / len(broken))
                else:
                    assert pd.isna(got.average[w])
                seen_unbroken_best |= bool(top.unbroken) and top.runs > broken.runs.max() if len(broken) else False
    assert seen_unbroken_best  # the case that used to be wrong is in this season


def test_weak_spot_counts_stands_the_same_way(season):
    ids = season.matches[season.matches.section == "Indian Premier League"].match_id
    s = P.stands(season, ids)
    every = P.by_wicket(s).set_index("wicket").average
    for team in sorted(set(s.team)):
        ws = PV.weak_spot(season, ids, team)
        mine = P.by_wicket(s[s.team == team]).set_index("wicket").average.dropna()
        assert list(ws.wicket) == list(mine.index)
        for r in ws.itertuples():
            assert r.average == pytest.approx(mine[r.wicket]) and r.all == pytest.approx(every[r.wicket])


def test_one_win_in_one_game_doesnt_make_a_side_strong(season):
    m = season.matches
    ids = m[m.section == "Indian Premier League"].match_id
    s = A.team_strength(season, ids)
    for team, v in s.items():
        g = m[m.match_id.isin(ids) & ((m.home == team) | (m.away == team))]
        assert v == pytest.approx(((g.winner == team).sum() + 2) / (len(g) + 4) * 100)
    one = season.matches[season.matches.match_id.isin(ids)].iloc[:1]  # a side's only game, won
    won = one.winner.iloc[0]
    assert A.team_strength(season, one.match_id)[won] == pytest.approx(60.0)
