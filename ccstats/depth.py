"""Squad depth and the inbox, the way Football Manager shows them.

**Squad depth:** for your side in one competition, each role with who started the latest series, the backups (your
players there in the last two seasons who didn't), and the best domestic players waiting (from Scouting, their
numbers converted to this level). Each of your players has their rating out of 20 there (the average of their
attributes, see attributes.py) and their latest marks.

**Inbox:** what happened lately, newest first, one message each: a series result, the player of the series by
marks, who is struggling and who could replace them, who is knocking on the door from domestic cricket, and
milestones in sight.
"""

from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd

from . import attributes as AT
from . import scouting as SC
from .marks import series_key, series_marks, team_report
from .players import milestone_watch
from .records import by_played

# (name, roles, job, the Scouting group that fills it, how many usually play)
ROLES = [("Openers", {"Opener"}, "bat", "Openers", 2),
         ("Top and middle order", {"Top order", "Middle order"}, "bat", "Top and middle order", 3),
         ("Wicketkeeper", None, "bat", "Wicketkeepers", 1),
         ("Finishers and lower order", {"Finisher", "Lower order", "Tail"}, "bat", None, 1),
         ("All-rounders", {"All-rounder"}, "both", "All-rounders", 1),
         ("Bowlers", {"Bowler"}, "bowl", "Bowlers", 4)]
KNOCKING = 0.25          # a domestic player this much better than your weakest in the role is "knocking on the door"


def _rating(a: dict, job: str) -> float | None:
    if job == "both":
        both = [a["bat_overall"], a["bowl_overall"]]
        return round(float(np.mean([x for x in both if x is not None])), 1) if any(x is not None for x in both) else None
    return a[f"{job}_overall"]


def squad_depth(career, team: str, section: str) -> dict:
    """Each role: starters (in the latest series), backups, and the best domestic players waiting."""
    own = SC.own_numbers(career, team, section)
    series, side = SC._latest_side(career, team, section)
    marks = series_marks(career)
    m = career.matches[career.matches.section == section]
    mine = marks[(marks.team == team) & marks.series.isin(set(series_key(m)))]
    # newest first in the order the series were played (as the marks and the struggling check order them)
    order = {r["series"]: i for i, r in enumerate(team_report(career, team))}
    groups = SC.shortlist(career, team, section) if section in SC.sections(career).index else {}
    placed: set = set()
    out = []

    def row(p, starts, rating, spinner=False, games=0):
        hist = mine[mine.player == p].assign(o=lambda d: d.series.map(order)).sort_values("o")
        return dict(player=p, starts=starts, rating=rating, spinner=spinner, marks=[int(x) for x in hist.mark.head(3)],
                    games=games)
    for name, roles, job, group, usual in ROLES:
        if roles is None:
            who = own[own.keeper.astype(bool) & own.role.isin(SC.BATTING_ROLES)]
        else:
            who = own[own.role.isin(roles)]
        who = who[~who.index.isin(placed)]
        rows = []
        for p, r in who.iterrows():
            rows.append(row(p, p in side, _rating(AT.player(career, section, p), job), bool(r.spinner),
                            int(r.bat_matches if job != "bowl" else r.bowl_matches)))
        placed |= set(who.index)
        rows.sort(key=lambda x: (not x["starts"], -(x["rating"] or 0)))
        waiting = []
        if group and group in groups:
            for x in groups[group]["picks"][:2]:
                waiting.append(dict(player=x["player"], side=x["side"], gain=x["gain"], clears=x["clears"],
                                    bat=x["bat"], bowl=x["bowl"], raw_bat=x["raw_bat"], raw_bowl=x["raw_bowl"]))
        out.append(dict(role=name, usual=usual, starters=[x for x in rows if x["starts"]],
                        backups=[x for x in rows if not x["starts"]][:4], waiting=waiting))
    # everyone in the side is shown: anyone without a role yet (they didn't bat or bowl in the last two seasons here)
    rest = sorted(side - placed)
    if rest:
        out.append(dict(role="No role yet", usual=0, starters=[row(p, True, None) for p in rest], backups=[], waiting=[]))
    return dict(section=section, series=series, roles=out)


OTHER = {"draw": "drawn", "tie": "tied", "no result": "no result"}


def _result(career, team: str, ids) -> dict:
    """The team's own games in a series or tournament (a tournament holds everyone's): won, lost, the rest by kind
    ("1 drawn, 1 no result"), the opponent when it was one side all through, and the last game's id as played."""
    m = career.matches[career.matches.match_id.isin(ids) & ((career.matches.home == team) | (career.matches.away == team))]
    won, lost = int((m.winner == team).sum()), int((m.loser == team).sum())
    rest = m[(m.winner != team) & (m.loser != team)].result_type.map(lambda k: OTHER.get(k, "other")).value_counts()
    opp = pd.concat([m.home, m.away])
    opp = opp[opp != team]
    return dict(won=won, lost=lost, other=", ".join(f"{n} {k}" for k, n in rest.items()),
                opp=opp.iloc[0] if len(opp) and opp.nunique() == 1 else "",
                bilateral=bool((m.series_id.fillna("").astype(str) != "").all()) and len(m) > 0,
                last=str(by_played(career, m).match_id.iloc[-1]) if len(m) else "")


def inbox(career, team: str, series: int = 8) -> list[dict]:
    """The latest news for `team`, newest first: {date, kind, title, body, player, match}."""
    rep = team_report(career, team)[:series]
    if not rep:
        return []
    m = career.matches.assign(series=series_key(career.matches))
    msgs = []
    advised: set = set()
    for i, s in enumerate(rep):
        ids = m[m.series == s["series"]].match_id
        g = m[m.series == s["series"]]
        section = g.section.iloc[0]
        when = str(s["end"])[:10]
        r = _result(career, team, ids)
        if r["opp"] and r["bilateral"]:
            word = "won" if r["won"] > r["lost"] else "lost" if r["lost"] > r["won"] else "drawn"
            title = f"Series {word} {r['won']}–{r['lost']} v {r['opp']}" + (f" ({r['other']})" if r["other"] else "")
        else:
            title = f"{s['label']}: {r['won']} won, {r['lost']} lost" + (f", {r['other']}" if r["other"] else "")
        top = s["players"][0]
        msgs.append(dict(date=when, kind="result", title=title, section=section, series=s["label"], player="",
                         match=r["last"],
                         body=f"{s['label']}. Best by marks: {top['player']} {top['mark']}/10 ({top['line']})."))
        # advice only for the latest series in each competition: it uses today's domestic numbers
        if section in advised:
            continue
        advised.add(section)
        try:
            for r in SC.replacements(career, team, section):
                pick = r["picks"][0] if r["picks"] else None
                msgs.append(dict(date=when, kind="struggling", title=r["verdict"], section=section, series=s["label"],
                                 player=r["player"], match="",
                                 body=f"{r['player']} ({r['role'].lower()}): {r['why']}." + (
                                     f" {pick['player']} ({pick['side']}): {pick['raw_bat'] or pick['raw_bowl']} in the last two "
                                     f"seasons, {pick['gain'] * 100:+.0f}% at this level." if pick else "")))
            for grp, v in SC.shortlist(career, team, section).items():
                for x in v["picks"][:1]:
                    if x["gain"] is not None and x["gain"] >= KNOCKING:
                        msgs.append(dict(date=when, kind="knocking", title=f"{x['player']} is knocking on the door",
                                         section=section, series=s["label"], player=x["player"], match="",
                                         body=f"{x['raw_bat'] or x['raw_bowl']} for {x['side']} in the last two seasons: "
                                              f"{x['gain'] * 100:.0f}% better than {v['weakest']}, your weakest of the "
                                              f"{grp.lower()} in {section}, even after the conversion."))
        except (KeyError, ValueError, IndexError):
            pass
        names = {p["player"] for p in s["players"]}
        mw = milestone_watch(career, m[m.section == section].match_id)
        for r in mw[mw.player.isin(names)].head(3).itertuples():
            msgs.append(dict(date=when, kind="milestone", title=f"{r.player} needs {r.needed:,} for {r.next:,} {r.what}",
                             section=section, series=s["label"], player=r.player, match="",
                             body=f"{r.next:,} {r.what} in {section}: {r.needed:,} to go."))
    rank = {"result": 0, "struggling": 1, "knocking": 2, "milestone": 3}
    msgs.sort(key=lambda x: (x["date"], -rank[x["kind"]]), reverse=True)
    for x in msgs:   # the same message keeps its id from one look to the next, so read and removed ones stay so
        x["team"] = team
        x["id"] = hashlib.sha1(f"{team}|{x['date']}|{x['kind']}|{x['title']}".encode()).hexdigest()[:12]
    return msgs
