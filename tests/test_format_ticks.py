"""Formats ticked together (your answers of 17 November): the Player page counts the ticked formats together; where they
rank among everyone and runs above average go by each format's own average, weighted by their innings in it; the parts
that only mean one format show one block per format; seasons are April-to-March years; ticks for formats the player
never played are dropped (ticks carried over from another page)."""

import numpy as np
import pytest

from ccstats import playerdeep as PD
from ccstats import seasonal as SN
from ccstats.loader import Career
from server import playerpage as PP
from serverkit import FIXTURES


@pytest.fixture(scope="module")
def career():
    c = Career.build("Test career", [(f.name, f.read_bytes()) for f in FIXTURES])
    c.count_fielding = False   # as the new site opens it
    return c


def _players(career, n=12):
    """Players with innings in two or more formats, most formats first."""
    b = career.batting[career.batting.did_bat].merge(career.matches[["match_id", "section"]])
    k = b.groupby("player").section.nunique()
    return list(k[k >= 2].sort_values(ascending=False).index[:n])


def test_counted_together_adds_up_to_each_format(career):
    checked = 0
    for p in _players(career):
        secs = PP.page(career, p)["sections"]
        both = PP.page(career, p, "|".join(secs[:2]))
        assert both["ticked"] == secs[:2] and both["section"] == " + ".join(secs[:2]) and not both["missing"]
        one = [PP.page(career, p, s) for s in secs[:2]]
        bats = [x["batting"]["kpis"] for x in one if x["batting"]]
        if both["batting"]:
            for k in ("innings", "runs", "hundreds", "fifties"):
                assert both["batting"]["kpis"][k] == sum(x[k] for x in bats), (p, k)
            # the average counted again straight from the scorecards: runs over times out, every ticked format
            ids = set(career.matches[career.matches.section.isin(secs[:2])].match_id)
            mine = career.batting[(career.batting.player == p) & career.batting.did_bat & career.batting.match_id.isin(ids)]
            if mine.out.sum():
                assert both["batting"]["kpis"]["average"] == pytest.approx(mine.runs.sum() / mine.out.sum(), abs=0.01)
            checked += 1
        bowls = [x["bowling"]["kpis"] for x in one if x["bowling"]]
        if both["bowling"]:
            assert both["bowling"]["kpis"]["wickets"] == sum(x["wickets"] for x in bowls), p
    assert checked >= 5


def test_seasons_are_april_to_march_years(career):
    p = _players(career)[0]
    secs = PP.page(career, p)["sections"][:2]
    d = PP.page(career, p, "|".join(secs))
    m = career.matches
    year = SN.april_seasons(m[m.section.isin(secs)])
    want = sorted({PP.year_label(year[i]) for i in set(career.batting[career.batting.player == p].match_id)
                   | set(career.bowling[career.bowling.player == p].match_id) if i in year.index}, reverse=True)
    assert d["seasons"] == ["All seasons"] + want
    one = PP.page(career, p, "|".join(secs), want[0])
    assert one["season"] == want[0]
    if one["batting"]:
        ids = {i for i in year.index if PP.year_label(year[i]) == want[0]}
        bat = career.batting[(career.batting.player == p) & career.batting.did_bat & career.batting.match_id.isin(ids)]
        assert one["batting"]["kpis"]["runs"] == int(bat.runs.sum())


def test_ticks_for_formats_never_played_are_dropped(career):
    p = _players(career)[0]
    d = PP.page(career, p)
    never = next(s for s in career.matches.section.unique() if s not in d["sections"])
    x = PP.page(career, p, f"{d['sections'][0]}|{never}")
    assert x["ticked"] == [d["sections"][0]] and "each" not in x   # one format: the page as it always was
    assert PP.page(career, p, never)["ticked"] == d["ticked"]      # none of them: the format they played most


def test_one_block_per_format_where_it_only_means_one_format(career):
    for p in _players(career, 30):
        d = PP.page(career, p)
        kinds = {}
        for s in d["sections"]:
            ids = career.matches[career.matches.section == s].match_id
            kinds[s] = PD.kind_of_ids(career, ids)
        mixed = [s for s in d["sections"] if kinds[s] != kinds[d["sections"][0]]]
        if not mixed or not d["batting"]:
            continue
        pick = [d["sections"][0], mixed[0]]
        x = PP.page(career, p, "|".join(pick))
        if not x["batting"]:
            continue
        assert x["one_length"] is False
        for k in PP.EACH_ALWAYS_BAT + PP.EACH_LENGTH_BAT:
            assert x["batting"][k] is None and k in x["batting"]["each"], k
            assert {e["section"] for e in x["batting"]["each"][k]} <= set(pick)
        assert x["story"]["rank"] is None and len(x["story"]["each"]["rank"]) >= 1
        assert {e["section"] for e in x["each"]["profile"]} <= set(pick)
        return
    pytest.skip("no player with two formats of different lengths")


def test_v_the_average_goes_by_each_formats_own_weighted_by_innings(career):
    """Where they rank: each format's own percentile, weighted by their innings in it."""
    checked = 0
    for p in _players(career, 30):
        d = PP.page(career, p)
        secs = d["sections"][:2]
        x = PP.page(career, p, "|".join(secs))
        if not (x["batting"] and x["batting"]["compare"]):
            continue
        one = {s: PP.page(career, p, s)["batting"] for s in secs}
        parts = [(one[s]["compare"], one[s]["kpis"]["innings"]) for s in secs if one[s] and one[s]["compare"]]
        for k, v in x["batting"]["compare"]["values"].items():
            got = [(c["values"][k], w) for c, w in parts if k in c["values"]]
            assert v == round(sum(a * w for a, w in got) / sum(w for _, w in got)), (p, k)
        checked += 1
    assert checked >= 2


def test_danger_bands_of_one_length_put_together_fairly(career):
    """Two formats of the same length: their own share from all their dismissals; every batter's share each format's
    own, weighted by their dismissals in it."""
    for p in _players(career, 60):
        d = PP.page(career, p)
        by_kind: dict = {}
        for s in d["sections"]:
            by_kind.setdefault(PD.kind_of_ids(career, career.matches[career.matches.section == s].match_id), []).append(s)
        same = next((v for v in by_kind.values() if len(v) >= 2), None)
        if not same:
            continue
        x = PP.page(career, p, "|".join(same[:2]))
        if not (x["batting"] and x["batting"]["danger"]):
            continue
        assert x["one_length"] is True and "danger" not in x["batting"]["each"]
        frames = [PD.danger_zones(career, career.matches[career.matches.section == s].match_id, p) for s in same[:2]]
        frames = [f for f in frames if f.attrs["dismissals"]]
        n = sum(f.attrs["dismissals"] for f in frames)
        for i, row in enumerate(x["batting"]["danger"]["rows"]):
            assert row["me"] == pytest.approx(sum(f.outs.iloc[i] for f in frames) / n * 100, abs=0.01)
            assert row["all"] == pytest.approx(sum(np.nan_to_num(f.all_pct.iloc[i]) * f.attrs["dismissals"] for f in frames) / n, abs=0.01)
        return
    pytest.skip("no player with two formats of one length")
