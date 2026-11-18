"""Formats ticked together (your answers of 17 November): the Player page counts the ticked formats together; where they
rank among everyone and runs above average go by each format's own average, weighted by their innings in it; the parts
that only mean one format show one block per format; seasons are April-to-March years; ticks for formats the player
never played are dropped (ticks carried over from another page)."""

import numpy as np
import pandas as pd
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


# ------------------------------------------------------------------ Teams, Team v team, Rivalries, the match finder
from server import matchpage as MP           # noqa: E402
from server import rivalriespage as RV       # noqa: E402
from server import teampage as TPG           # noqa: E402
from server import tvtpage as TV             # noqa: E402


def _team_two(career):
    """A team with games in two or more competitions, and its two most played."""
    m = career.matches
    for t in (set(m.home) | set(m.away)):
        secs = m[(m.home == t) | (m.away == t)].section.value_counts()
        if len(secs) >= 2:
            return t, list(secs.index[:2])
    pytest.skip("no team in two competitions")


def test_team_record_counted_together(career):
    team, two = _team_two(career)
    both = TPG.page(career, "|".join(two), "", team, "all", "Overview")
    one = [TPG.page(career, s, "", team, "all", "Overview") for s in two]
    kp = lambda p, k: next(x["v"] for x in p["head"]["kpis"] if x["k"] == k)  # noqa: E731
    assert int(kp(both, "Played")) == sum(int(kp(p, "Played")) for p in one)
    assert both["ticked"] == [s for s in TPG.in_order(career.matches, two)] and " + " in both["name"]
    assert not both["body"]["missing"]
    # against the average team: each competition's own average team, weighted by the team's games in it
    row = next(r for r in both["body"]["vs_average"]["rows"] if r["label"] == "Win %")
    ids = {s: career.matches[career.matches.section == s].match_id for s in two}
    tabs = {s: TPG.A.team_table(career, ids[s]) for s in two}
    w = {s: int(tabs[s].set_index("team").loc[team].played) if team in set(tabs[s].team) else 0 for s in two}
    ref = sum(tabs[s].win_pct.mean() * w[s] for s in two) / sum(w.values())
    me = TPG.A.team_table(career, pd.Index(pd.concat(ids.values()))).set_index("team").loc[team].win_pct
    assert row["value"] == pytest.approx((me - ref) / abs(ref) * 100, abs=0.01)
    for tab in TPG.TABS[1:]:
        assert not (TPG.page(career, "|".join(two), "", team, "all", tab)["body"] or {}).get("missing"), tab


def test_team_v_team_runs_above_average_each_formats_own(career):
    team, two = _team_two(career)
    both = TV.page(career, "|".join(two), "", team, "", "any", "", [team])
    if both["none"]:
        pytest.skip(both["none"])
    one = {s: TV.page(career, s, "", team, both["b"], "any", "", [team]) for s in two}
    got = {r["player"]: r["value"] for r in both["body"]["above"]["rows"]}
    each: dict = {}
    for s, p in one.items():
        if p.get("body") and p["body"].get("above"):
            for r in p["body"]["above"]["rows"]:
                each[r["player"]] = each.get(r["player"], 0) + r["value"]
    shared = [k for k in got if k in each]
    assert shared
    for k in shared:
        assert got[k] == pytest.approx(each[k], abs=0.05), k


def test_rivalries_and_the_match_finder_counted_together(career):
    secs = MP.ticked_of(career, "")
    two = secs[:2]
    both = RV.page(career, {"section": "|".join(two)}, [])
    one = [RV.page(career, {"section": s}, []) for s in two]
    assert both["ticked"] == two and len(both["pairs"]) >= max(len(p["pairs"]) for p in one)
    f = MP.finder(career, "|".join(two), "", [])
    assert f["ticked"] == two and len(f["matches"]) == sum(len(MP.finder(career, s, "", [])["matches"]) for s in two)
    assert MP.finder(career, "All sections", "", [])["section"] == "All sections"
    # the best games: each match keeps its rank within its own competition
    bg = MP.best_games(career, "|".join(two), top=50)
    own = {r["id"]: r["rank"] for s in two for r in MP.best_games(career, s, top=500)["rows"]}
    assert bg["rows"] and all(r["rank"] == own[r["id"]] for r in bg["rows"])
