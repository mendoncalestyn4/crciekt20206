"""Competition tables: league standings, knockout brackets and bilateral series.

Everything works on one competition and one season (a set of match ids)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import analysis as A
from . import competitions as C

LIMITED = {"T20", "T20I", "ODI", "List A", "The Hundred"}
KNOCKOUT_ORDER = ["Quarter-final", "Qualifier 1", "Eliminator", "Qualifier 2", "Semi-final", "Final"]


def every_section(matches: pd.DataFrame) -> pd.DataFrame:
    """Every section of the career, most matches first: its matches, its seasons (A to Z), the first and latest
    match, its format and level (the current site's "Sections" table on My team, worked out here for both sites)."""
    cols = ["section", "matches", "seasons", "first", "last", "format", "level"]
    if matches.empty:
        return pd.DataFrame(columns=cols)
    sec = (matches.groupby("section")
           .agg(matches=("match_id", "size"), seasons=("season", lambda s: ", ".join(sorted(set(map(str, s))))),
                first=("date", "min"), last=("date", "max"), format=("format", "first"), level=("level", "first"))
           .sort_values("matches", ascending=False, kind="stable").reset_index())
    return sec[cols]


def points_rule(competition: str, fmt: str) -> tuple[str, dict]:
    """(description shown on the page, points per result).  Limited-overs leagues
    all use 2 for a win and 1 for a tie or no result.  First-class leagues only
    get points where the rules can be worked out from the scorecards."""
    if fmt in LIMITED:
        return "2 points for a win, 1 for a tie or no result. Ties on points are split by net run rate.", \
            dict(win=2, tie=1, nr=1, draw=0)
    if competition == "County Championship":
        return ("16 points for a win, 8 for a draw or a tie. The real table also has batting and bowling bonus points; "
                "those depend on the score after 110 overs, which the scorecards don't show, so they aren't included."), \
            dict(win=16, tie=8, draw=8, nr=8)
    if competition == "Ranji Trophy":
        return ("6 points for a win (7 for a win by an innings or 10 wickets), 3 for a draw with the first-innings lead, "
                "1 for a draw without it, 3 for a tie, 1 for no result."), \
            dict(win=6, bonus_win=7, tie=3, draw_lead=3, draw=1, nr=1)
    return "The scorecards don't tell us this competition's points system, so teams are ordered by wins, then fewest defeats.", {}


def _groups(matches: pd.DataFrame) -> list[tuple[str, pd.DataFrame, set]]:
    """Split league matches into groups: [(name, the group's matches, its teams)].

    Where the scorecards name the groups ("T20 Blast - North"), each team is in
    the group it played most of its named-group games in, and its table row counts
    all its league games, cross-group ones included (the Blast has some titled just
    "Group Match").  Otherwise groups are worked out from who played whom (teams in
    different groups never meet) and named Group A, B, …"""
    named = matches[~matches.stage.isin(["", "Group"]) & ~matches.stage.str.startswith("Division")]
    if len(named):
        count: dict[str, dict[str, int]] = {}
        for stage, h, a in zip(named.stage, named.home, named.away):
            for t in (h, a):
                count.setdefault(t, {}).setdefault(stage, 0)
                count[t][stage] += 1
        home = {t: max(c, key=c.get) for t, c in count.items()}
        everyone = set(matches.home) | set(matches.away)
        if set(home) == everyone and len(set(home.values())) > 1:
            out = []
            for g in sorted(set(home.values()), key=lambda g: named[named.stage == g].date.min()):
                teams = {t for t, gg in home.items() if gg == g}
                out.append((g, matches[matches.home.isin(teams) | matches.away.isin(teams)], teams))
            return out
    teams = sorted(set(matches.home) | set(matches.away))
    parent = {t: t for t in teams}

    def find(t):
        while parent[t] != t:
            parent[t] = parent[parent[t]]
            t = parent[t]
        return t

    for h, a in zip(matches.home, matches.away):
        parent[find(h)] = find(a)
    comps: dict[str, set] = {}
    for t in teams:
        comps.setdefault(find(t), set()).add(t)
    parts = sorted(comps.values(), key=lambda s: matches[matches.home.isin(s) | matches.away.isin(s)].date.min())

    def name_of(gm: pd.DataFrame) -> str:
        n = gm.stage[~gm.stage.isin(["", "Group"]) & ~gm.stage.str.startswith("Division")]
        return n.mode().iloc[0] if len(n) else ""

    if len(parts) == 1 or any(len(p) < 3 for p in parts):
        # one group, or too few games yet to tell the groups apart
        return [(name_of(matches) if len(parts) == 1 and name_of(matches) else "League", matches, set(teams))]
    out, letters = [], iter("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    for p in parts:
        gm = matches[matches.home.isin(p) | matches.away.isin(p)]
        out.append((name_of(gm) or f"Group {next(letters)}", gm, p))
    return out


# competitions with no league table and no champion, only each team's record: bilateral internationals, and
# tour games and World XI games
BILATERAL = {"Test", "ODI", "T20I"} | {f"{s} · {f}" for s in (C.WORLD_XI_SECTION, C.TOUR_SECTION) for f in C.FORMATS}
LEAGUE_GAMES = {"County Championship": 14}  # games per team in a full season, for leagues that end without a final


def league_finished(matches: pd.DataFrame) -> bool:
    """A league without a final is over once every team has played a full season's games."""
    if matches.empty:
        return False
    full = LEAGUE_GAMES.get(matches.competition.iloc[0])
    if not full:
        return False
    lg = matches[~matches.knockout]
    played = pd.concat([lg.home, lg.away]).value_counts()
    return bool(len(played) and (played >= full).all())


def league_tables(career, ids) -> list[tuple[str, pd.DataFrame, str]]:
    """[(group name, table, points rule)] for the league (non-knockout) matches.
    Bilateral internationals have no league: they get one table of every
    team's record, ordered by wins, with no points."""
    m = career.matches[career.matches.match_id.isin(ids) & ~career.matches.knockout].sort_values("date")
    if m.empty:
        return []
    comp, fmt = m.competition.iloc[0], m.format.iloc[0]
    bilateral = comp in BILATERAL
    rule_text, pts = points_rule(comp, fmt)
    if bilateral:
        kind = "Bilateral series" if comp in ("Test", "ODI", "T20I") else "Tour games and World XI games"
        rule_text, pts = (f"{kind} have no league table, so this is each team's record in them, ordered by "
                          "wins, then fewest defeats."), {}
    inn = career.innings[career.innings.match_id.isin(m.match_id)]
    first = inn[inn.team_innings == 1].groupby(["match_id", "team"]).runs.sum()
    out = []
    groups = [("Every team", m, set(m.home) | set(m.away))] if bilateral else _groups(m)
    for label, gm, members in groups:
        tt = A.team_table(career, gm.match_id).set_index("team")
        rows = []
        for team in tt.index:
            if team not in members:
                continue  # a cross-group opponent: it has its own group's table
            mine = gm[(gm.home == team) | (gm.away == team)]
            # a tie settled by a super over counts as a win for the side that won it
            so = (mine.result_type == "tie") & (mine.tiebreak_winner != "") if fmt in LIMITED else mine.result_type == "none"
            won = int((mine.winner == team).sum() + (so & (mine.tiebreak_winner == team)).sum())
            lost = int(((mine.winner != team) & (mine.winner != "")).sum() + (so & (mine.tiebreak_winner != team)).sum())
            tied = int(((mine.result_type == "tie") & ~so).sum())
            nr = int((mine.result_type == "no result").sum())
            drawn = int((mine.result_type == "draw").sum())
            points = np.nan
            if pts:
                if "bonus_win" in pts:  # Ranji
                    wins = mine[mine.winner == team]
                    big = int((wins.innings_win.fillna(False).astype(bool) | (wins.margin_wickets == 10)).sum())
                    draws = mine[mine.result_type == "draw"]
                    lead = 0
                    for mid, h, a in zip(draws.match_id, draws.home, draws.away):
                        opp = a if h == team else h
                        mine_r, opp_r = first.get((mid, team), np.nan), first.get((mid, opp), np.nan)
                        lead += int(mine_r > opp_r)
                    points = ((won - big) * pts["win"] + big * pts["bonus_win"] + lead * pts["draw_lead"]
                              + (drawn - lead) * pts["draw"] + tied * pts["tie"] + nr * pts["nr"])
                else:
                    points = won * pts["win"] + tied * pts["tie"] + nr * pts["nr"] + drawn * pts["draw"]
            rows.append(dict(team=team, played=len(mine), won=won, lost=lost, drawn=drawn, tied=tied, no_result=nr,
                             points=points, nrr=tt.nrr[team], rpw_for=tt.rpw_for[team], rpw_against=tt.rpw_against[team]))
        t = pd.DataFrame(rows)
        keys = (["points"] if pts else []) + ["won"] + (["nrr"] if fmt in LIMITED else []) + ["lost"]
        t = t.sort_values(keys, ascending=[False] * (len(keys) - 1) + [True]).reset_index(drop=True)
        t.index = t.index + 1
        out.append((label, t, rule_text))
    return out


def knockouts(career, ids) -> pd.DataFrame:
    """Knockout matches in bracket order (quarter-finals first, final last)."""
    m = career.matches[career.matches.match_id.isin(ids) & career.matches.knockout].copy()
    if m.empty:
        return m
    m["round"] = m.stage.map(lambda s: KNOCKOUT_ORDER.index(s) if s in KNOCKOUT_ORDER else len(KNOCKOUT_ORDER))
    m["through"] = np.where(m.winner != "", m.winner, m.tiebreak_winner)
    return m.sort_values(["round", "date"]).reset_index(drop=True)


def series_table(career, ids) -> pd.DataFrame:
    """One row per bilateral series: score line, drawn matches and the leading run-scorer and wicket-taker."""
    m = career.matches[career.matches.match_id.isin(ids) & (career.matches.series_id != "")]
    rows = []
    for sid, g in m.groupby("series_id", sort=False):
        g = g.sort_values("date")
        a, b = g.home.iloc[0], g.away.iloc[0]
        wa, wb = int((g.winner == a).sum()), int((g.winner == b).sum())
        length = int(g.series_length.max()) if g.series_length.notna().any() else len(g)
        bat = career.batting[career.batting.match_id.isin(g.match_id)].groupby("player").runs.sum()
        bowl = career.bowling[career.bowling.match_id.isin(g.match_id)].groupby("player").wickets.sum()
        if wa == wb:
            line = f"{a} {wa}–{wb} {b}"
        else:
            lead, trail = (a, b) if wa > wb else (b, a)
            line = f"{lead} {max(wa, wb)}–{min(wa, wb)} {trail}"
        done = len(g) >= length
        rows.append(dict(series_id=sid, start=g.date.min(), teams=f"{a} v {b}", score=line,
                         played=len(g), length=length, drawn=int((g.result_type == "draw").sum()),
                         result=("Series drawn" if wa == wb else f"{a if wa > wb else b} won the series") if done else
                         ("Level" if wa == wb else f"{a if wa > wb else b} lead") + f" · {len(g)} of {length} played",
                         top_runs=f"{bat.idxmax()} ({int(bat.max())})" if len(bat) else "–",
                         top_wickets=f"{bowl.idxmax()} ({int(bowl.max())})" if len(bowl) and bowl.max() > 0 else "–",
                         match_ids=list(g.match_id)))
    return pd.DataFrame(rows, columns=["series_id", "start", "teams", "score", "played", "length", "drawn", "result",
                                       "top_runs", "top_wickets", "match_ids"]).sort_values("start", ascending=False)
