"""Stage 3, Leaders and records: Stat by stat.

- parity: the page ranks the same players with the same figures as the current site's page (views/stat_by_stat.py,
  its own lines copied here), for every competition, both disciplines and every stat;
- counted another way: the leader's runs and wickets added up again straight from the scorecards;
- several competitions ticked: runs above average and runs saved are each competition's own, added up;
- the three lines under both charts, no fielding, the agreed competition order, and junk in the address."""

from __future__ import annotations

import numpy as np
import pytest

from ccstats import deep as D
from ccstats.competitions import ordered as in_order
from ccstats.loader import Career
from ccstats.stats import Scope, player_tables, rank, stat_definitions
from server import leaderspage as LP
from serverkit import FIXTURES

MINS = {"Batting": {"t20": [0, 20, 30, 60, 100], "one": [0, 40, 60, 120, 200], "multi": [0, 60, 100, 200, 400]},
        "Bowling": {"t20": [0, 20, 36, 60, 120], "one": [0, 30, 60, 120, 240], "multi": [0, 60, 120, 240, 480]}}


@pytest.fixture(scope="module")
def career():
    c = Career.build("Test career", [(f.name, f.read_bytes()) for f in FIXTURES])
    c.count_fielding = False   # as the new site opens it
    return c


def _old(career, section: str, disc: str, stat_id: str, best: bool = True):
    """The current site's page, as written there: the table, the default minimum, the pool and the ranking."""
    bat, bowl, fld, base = player_tables(career, Scope(sections=[section]))
    defs = stat_definitions(base)[{"Batting": "bat", "Bowling": "bowl"}[disc]]
    table = {"Batting": bat, "Bowling": bowl}[disc]
    options = MINS[disc][base.kind]
    default_min = next((v for v in reversed(options[:3]) if (table["balls"] >= v).sum() >= 12), options[0])
    stat = next(s for s in defs if s.id == stat_id)
    pool = table[table[stat.column].notna() & (table["balls"] >= default_min)]
    return rank(pool, stat, best=best), stat, default_min, pool


def _sections(career):
    return list(in_order(career.matches, career.matches.section.unique()))


def test_every_ranking_matches_the_current_sites(career):
    checked = 0
    for sec in _sections(career):
        for disc in ("Batting", "Bowling"):
            _, base = (None, player_tables(career, Scope(sections=[sec]))[3])
            for s in stat_definitions(base)[{"Batting": "bat", "Bowling": "bowl"}[disc]]:
                for view in ("Best", "Worst"):
                    d = LP.stat_by_stat(career, dict(section=sec, disc=disc, stat=s.id, view=view, top="all"), [])
                    ranked, stat, mn, pool = _old(career, sec, disc, s.id, best=view == "Best")
                    if pool.empty:
                        assert d["none"].startswith("Nobody qualifies"), (sec, disc, s.id)
                        continue
                    assert d["minimum"]["value"] == mn
                    got = [(r["player"], round(r["value"], 2)) for r in d["bars"]["rows"]]
                    want = [(p, round(float(v), 2)) for p, v in zip(ranked.player, ranked[stat.column])]
                    assert got == want, (sec, disc, s.id, view)
                    assert len(d["table"]["rows"]) == len(ranked)
                    checked += 1
    assert checked > 50


def test_the_full_figures_are_the_current_sites(career):
    sec = _sections(career)[0]
    d = LP.stat_by_stat(career, dict(section=sec, disc="Batting", stat="runs"), [])
    ranked, _, _, pool = _old(career, sec, "Batting", "runs")
    cols = d["table"]["cols"]
    pctl = D.percentiles(pool, "runs", "high")
    for row, (i, r) in zip(d["table"]["rows"], ranked.head(10).iterrows()):
        x = dict(zip(cols, row))
        assert (x["Player"], x["Mat"], x["Inns"], x["NO"], x["Runs"], x["BF"], x["HS"]) == (
            r.player, r.matches, r.innings, r.not_outs, r.runs, r.balls, r.high_score_text)
        assert x["Avg"] == ("–" if np.isnan(r.average) else f"{r.average:.1f}")
        assert x["Rank %"] == D.top_text(pctl.get(i))
        assert (x["100"], x["50"], x["0"], x["4s"], x["6s"]) == (r.hundreds, r.fifties, r.ducks, r.fours, r.sixes)


def test_the_leaders_counted_again_from_the_scorecards(career):
    """The top run-scorer's runs and the top wicket-taker's wickets, added up again from every innings."""
    for sec in _sections(career):
        ids = set(career.matches[career.matches.section == sec].match_id)
        d = LP.stat_by_stat(career, dict(section=sec, disc="Batting", stat="runs", min="0"), [])
        if d.get("bars"):
            top = d["bars"]["rows"][0]
            b = career.batting[career.batting.match_id.isin(ids) & career.batting.did_bat]
            assert top["value"] == b[b.player == top["player"]].runs.sum() == b.groupby("player").runs.sum().max()
        d = LP.stat_by_stat(career, dict(section=sec, disc="Bowling", stat="wickets", min="0"), [])
        if d.get("bars"):
            top = d["bars"]["rows"][0]
            w = career.bowling[career.bowling.match_id.isin(ids)]
            assert top["value"] == w[w.player == top["player"]].wickets.sum() == w.groupby("player").wickets.sum().max()


def test_several_competitions_are_each_measured_against_their_own_average(career):
    secs = _sections(career)[:2]
    for disc, stat in (("Batting", "runs_above_average"), ("Bowling", "runs_saved")):
        d = LP.stat_by_stat(career, dict(section="|".join(secs), disc=disc, stat=stat, top="all", min="0"), [])
        assert d["ticked"] == secs
        each = {}
        for s in secs:
            bat, bowl, _, _ = player_tables(career, Scope(sections=[s]))
            t = bat if disc == "Batting" else bowl
            for p, v in zip(t.player, t[stat]):
                if np.isfinite(v):
                    each[p] = each.get(p, 0.0) + float(v)
        for r in d["bars"]["rows"]:
            assert r["value"] == pytest.approx(each[r["player"]], abs=0.05), (disc, r)   # the page sends one decimal
        assert "each against its own average" in d["statdef"]["note"]


def test_both_charts_have_their_three_lines_and_no_fielding(career):
    d = LP.stat_by_stat(career, {}, ["England"])
    assert d["discs"] == ["Batting", "Bowling"]   # no Fielding (your decision of 14 November)
    assert [c["section"] for c in d["choices"]] == _sections(career)   # Tests, ODIs, T20Is, franchise, domestic
    for part in ("bars", "dots"):
        for k in ("is_", "best", "for_"):
            assert d[part][k].strip(), (part, k)
    top = d["bars"]["rows"][0]
    assert d["bars"]["best"].startswith(top["player"])
    assert all(c not in d["table"]["cols"] for c in ("Ct", "St", "Catches", "Stumpings"))


def test_find_a_player_and_nobody_qualifying(career):
    d = LP.stat_by_stat(career, dict(top="10"), [])
    last = d["names"][-1]
    d = LP.stat_by_stat(career, dict(find=last, min="0", top="all"), [])
    assert last in d["found"]
    assert any(r["hi"] for r in d["bars"]["rows"]) or "isn't on these charts" in d["found"]
    d = LP.stat_by_stat(career, dict(only="Nobody At All"), [])
    assert d["only"] == []
    d = LP.stat_by_stat(career, dict(pos="8 to 11", min=str(MINS["Batting"]["multi"][-1])), [])
    assert d.get("none") or d["bars"]["rows"]


@pytest.mark.parametrize("q", [dict(section="junk"), dict(disc="Fielding"), dict(min="abc", top="9"),
                               dict(stat="catches"), dict(measure="nonsense"), dict(seasons="1066|zz"),
                               dict(single="1", posn="0|12|x"), dict(view="Middling", find="<script>"),
                               dict(how="bowled")])   # "How out" is gone (your choice of 24 November): ignored
def test_junk_in_the_address_gives_the_normal_page(career, q):
    d = LP.stat_by_stat(career, q, [])
    assert d["ticked"] and d["disc"] in ("Batting", "Bowling") and d["view"] in ("Best", "Worst")
    assert d.get("bars") or d.get("none")
    assert d.get("find", "") in ("", *d.get("names", []))


# --------------------------------------------------------------------------- Records
from ccstats import leaders as L   # noqa: E402
from ccstats import records as RC   # noqa: E402
from ccstats import seasonal as SN   # noqa: E402


def test_the_record_books_are_the_current_sites(career):
    """Every record list, for every competition and season, is the current site's (views/records.py), Top 5/10/20."""
    m = career.matches
    for sec in _sections(career):
        for season in ["", *sorted(m[m.section == sec].season.unique())]:
            for top in (5, 10, 20):
                d = LP.records_page(career, dict(section=sec, season=season, top=str(top)), [])
                ids = Scope(sections=[sec], seasons=[season] if season else []).match_ids(m)
                old = RC.records(career, ids, top=top)
                got = {t["title"]: t for g in d["groups"] for t in g["tables"]}
                assert set(got) == set(old), (sec, season)
                for name, t in old.items():
                    rows = got[name]["rows"]
                    assert [r[0] for r in rows] == [str(x) for x in t["rank"]]
                    assert [r[1].replace(" 🆕", "") for r in rows] == [str(x) for x in t.holder]
                    assert [r[2] for r in rows] == [str(x) for x in t.value]
                    near = SN.near_miss(name, t)
                    assert got[name]["near"].endswith(near) if near else got[name]["near"] == ""


def test_the_best_stand_for_each_wicket_counted_again(career):
    """Each wicket's best stand, found again straight from the fall of wickets and the totals of every innings."""
    m = career.matches
    for sec in _sections(career):
        ids = set(m[m.section == sec].match_id)
        d = LP.records_page(career, dict(section=sec), [])
        best: dict[int, int] = {}
        for (mid, inn), f in career.fow[career.fow.match_id.isin(ids)].groupby(["match_id", "innings_no"]):
            f = f.sort_values("wicket")
            prev = 0
            for w, s in zip(f.wicket, f.score):
                best[int(w)] = max(best.get(int(w), 0), int(s) - prev)
                prev = int(s)
            tot = career.innings[(career.innings.match_id == mid) & (career.innings.innings_no == inn)]
            if len(tot) and len(f) < 10:   # the stand still going at the end of the innings
                w = len(f) + 1
                best[w] = max(best.get(w, 0), int(tot.runs.iloc[0]) - prev)
        for x in d["stands"]:
            assert int(x["rows"][0]["runs"].rstrip("*")) == best[x["wicket"]], (sec, x["wicket"])
            assert [r["place"] for r in x["rows"]] == sorted(r["place"] for r in x["rows"]) and len(x["rows"]) <= 5


def test_every_teams_longest_runs_match_the_teams_page(career):
    """The longest winning and losing runs in the every-team table equal each team's own streaks chart (Teams)."""
    m = career.matches
    sec = _sections(career)[0]
    d = LP.records_page(career, dict(section=sec), [])
    cols = d["runs"]["cols"]
    for row in d["runs"]["rows"]:
        x = dict(zip(cols, row))
        one = LP.records_page(career, dict(section=sec, team=x["Team"]), [])["streaks"]
        runs = one["streaks"]
        longest = lambda o: max((r["end"] - r["start"] + 1 for r in runs if r["o"] == o), default=0)  # noqa: E731
        assert (x["Longest winning run"], x["Longest losing run"]) == (longest("W"), longest("L")), x["Team"]
        assert x["Played"] == len(one["results"]) == x["Won"] + x["Lost"] + sum(r["outcome"] not in "WL" for r in one["results"])


def test_records_timeline_best_games_and_junk(career):
    d = LP.records_page(career, {}, ["England"])
    tl = d["timeline"]
    steps = SN.record_timeline(career, Scope(sections=d["ticked"]).match_ids(career.matches))
    steps = steps[steps.record == tl["pick"]]
    assert [p["label"] for p in tl["points"]] == list(steps.value)
    assert all(a["y"] < b["y"] for a, b in zip(tl["points"], tl["points"][1:])) or tl["pick"].startswith("Lowest")
    for k in ("is_", "best", "for_"):
        assert tl[k] and d["streaks"][k]
    assert [g["rating"] for g in d["games"]] == sorted((g["rating"] for g in d["games"]), reverse=True)
    for q in (dict(section="junk", season="1066", top="7", team="Nobody", record="Most catches"),):
        x = LP.records_page(career, q, [])
        assert x["ticked"] and x["season"] == "" and x["top"] == "10" and x["team"] in x["teams"]
        assert x["timeline"]["pick"] in x["timeline"]["names"]
    assert not any("catch" in t["title"].lower() for g in d["groups"] for t in g["tables"])   # no fielding records
