"""The same number on every page; totals built from their parts (your pick of 14 November). One figure, taken from every
page that shows it, must be the same everywhere: a player's runs and wickets in a competition (the Player page's top
numbers, its every-competition table and its season-by-season table, the team record's top run-scorers and every
player's contribution); a team's games and wins (its record, its results, Rivalries, the points table); a match's top
scores (its page and its scorecard)."""

import pytest

from ccstats.loader import Career
from server import comppage as CP
from server import matchpage as MP
from server import playerpage as PP
from server import rivalriespage as RV
from server import styleguide as SG
from server import teampage as TPG
from serverkit import FIXTURES


@pytest.fixture(scope="module")
def career():
    c = Career.build("Same number", [(f.name, f.read_bytes()) for f in FIXTURES])
    c.count_fielding = False
    return c


def _num(v) -> float:
    return float(str(v).replace(",", "").rstrip("*")) if v not in (None, "", "–") else 0.0


def test_a_players_runs_and_wickets_are_the_same_on_every_part_of_the_player_page(career):
    checked = 0
    for p in sorted(set(career.batting[career.batting.did_bat].player))[::5]:
        d = PP.page(career, p)
        sec = d["section"]
        if d["batting"]:
            k = d["batting"]["kpis"]
            row = next(r for r in d["bat_table"]["rows"] if r["section"] == sec)
            seasons = d["batting"]["season_table"]["rows"]
            assert _num(row["Runs"]) == k["runs"] == sum(_num(r["Runs"]) for r in seasons), p
            assert _num(row["Inns"]) == k["innings"] == sum(_num(r["Inns"]) for r in seasons), p
            assert _num(row["100"]) == k["hundreds"] and _num(row["50"]) == k["fifties"], p
            checked += 1
        if d["bowling"]:
            k = d["bowling"]["kpis"]
            row = next(r for r in d["bowl_table"]["rows"] if r["section"] == sec)
            seasons = d["bowling"]["season_table"]["rows"]
            assert _num(row["Wkts"]) == k["wickets"] == sum(_num(r["Wkts"]) for r in seasons), p
            assert _num(row["Runs"]) == k["runs"] == sum(_num(r["Runs"]) for r in seasons), p
    assert checked >= 20


def test_a_teams_top_scorers_and_contributions_match_each_players_own_figures(career):
    m = career.matches
    checked = 0
    for sec in m.section.value_counts().index[:4]:
        here = m[m.section == sec]
        for team in sorted(set(here.home) | set(here.away))[:3]:
            body = TPG.page(career, sec, "", team, "all", "Overview")["body"]
            if not body or not body.get("top_bat"):
                continue
            ids = set(here.match_id)
            bat = career.batting[career.batting.match_id.isin(ids) & (career.batting.team == team)]
            for r in body["top_bat"]["rows"]:
                assert r["runs"] == int(bat[bat.player == r["player"]].runs.sum()), (sec, team, r["player"])
            for r in (body.get("contribution") or {}).get("rows", []):
                assert r["runs"] == int(bat[bat.player == r["player"]].runs.sum()), (sec, team, r["player"])
            # the parts add up to the whole: every player's runs off the bat are the team's runs off the bat
            if body.get("contribution"):
                assert sum(r["runs"] for r in body["contribution"]["rows"]) == body["contribution"]["team_runs"]
            checked += 1
    assert checked >= 4


def test_a_teams_games_are_the_same_in_its_record_its_results_and_rivalries(career):
    m = career.matches
    checked = 0
    for sec in m.section.value_counts().index[:4]:
        here = m[m.section == sec]
        for team in sorted(set(here.home) | set(here.away))[:3]:
            p = TPG.page(career, sec, "", team, "all", "Overview")
            if p["head"].get("none"):
                continue
            kp = {x["k"]: x["v"] for x in p["head"]["kpis"]}
            mine = here[(here.home == team) | (here.away == team)]
            won = int((mine.winner == team).sum())
            assert int(kp["Played"]) == len(mine), (sec, team)
            assert kp["Won–Lost"].split("–")[0] == str(won), (sec, team)
            res = SG.results(career, team, mine.match_id)
            assert len(res) == len(mine) and sum(r["outcome"] == "W" for r in res) == won, (sec, team)
            rv = RV.page(career, {"section": sec}, [])
            played = sum(int(x["label"].rsplit("(", 1)[1].rstrip(")")) for x in rv["pairs"]
                         if team in x["key"].split("|"))
            assert played == len(mine), (sec, team)
            checked += 1
    assert checked >= 6


def test_the_points_table_is_the_teams_own_record(career):
    """The league table on Competitions: each team's played and won are those of its own games in that season."""
    m = career.matches
    checked = 0
    for ch in CP.choices(career)[:6]:
        for season in ch["seasons"][:2]:
            d = CP.page(career, {"event": ch["event"], "season": season}, [])
            for g in (d.get("league") or {}).get("groups", []) if d.get("league") else []:
                cols = g["cols"]
                if "P" not in cols or "W" not in cols:
                    continue
                for row in g["rows"]:
                    team = str(row[cols.index("Team")] if "Team" in cols else row[0]).replace("🏆 ", "").strip()
                    games = m[(m.event == ch["event"]) & (m.season.astype(str) == season) & ~m.knockout
                              & ((m.home == team) | (m.away == team))]
                    if games.empty:
                        continue
                    assert int(row[cols.index("P")]) == len(games), (ch["event"], season, team)
                    assert int(row[cols.index("W")]) == int((games.winner == team).sum()), (ch["event"], season, team)
                    checked += 1
    assert checked >= 5


def test_a_matchs_top_scores_are_its_scorecards(career):
    for mid in career.matches.match_id[::6]:
        d = MP.page(career, mid, [], {})
        card = {(b["player"], b["runs"]) for c in d["match"]["cards"] for b in c["bat"] if b["did_bat"]}
        for r in d["top_scores"]:
            assert (r["player"], int(str(r["score"]).rstrip("*"))) in card, (mid, r)
        best = max((b["runs"] for c in d["match"]["cards"] for b in c["bat"] if b["did_bat"]), default=0)
        assert not d["top_scores"] or int(str(d["top_scores"][0]["score"]).rstrip("*")) == best, mid
