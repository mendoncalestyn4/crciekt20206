"""Things worth a second look on the data check page.

Nothing here changes any data. These are *suggestions*; a fix only happens
when the user confirms it, and it is then stored in the career's Fixes."""

from __future__ import annotations

import re
from itertools import combinations

import pandas as pd

from .parser import resolve_candidates
from .stats import poss


def _base(name: str) -> str:
    return re.sub(r"\s*\(\d+\)$", "", name).strip()


def _surname(name: str) -> str:
    parts = _base(name).replace("'", " ").split()
    return parts[-1].lower() if parts else ""


def _initial(name: str) -> str:
    return _base(name)[:1].upper()


def uncredited(career) -> pd.DataFrame:
    """Catches and stumpings the scorecard didn't make clear (e.g. 'c Khan' with
    two Khans in the side), with the players who could have taken them and, where
    the rest of the career gives good evidence, a suggestion and the reason for it.

    The scorecard only prints a surname, so these can't be settled for certain;
    the suggestion is what the evidence points to:
      * a stumping is always the wicketkeeper, and a keeper takes far more catches
        than anyone else, so a candidate who keeps wicket for the side (has made a
        stumping for them) and didn't bowl in that innings is suggested;
      * otherwise, for a catch, the candidate who has taken clearly more of the
        side's clear catches that season.
    No suggestion is made when the evidence is even."""
    f = career.fielding[~career.fielding.resolved]
    cols = ["credit_key", "match_id", "date", "match", "innings_no", "team", "printed", "kind", "batter", "bowler",
            "candidates", "likely", "suggestion", "reason"]
    if f.empty:
        return pd.DataFrame(columns=cols)
    m = career.matches.set_index("match_id")
    xi = career.batting.groupby(["match_id", "team"]).player.apply(list)
    bowled = career.bowling.groupby(["match_id", "innings_no"]).player.apply(set)
    clear = career.fielding[career.fielding.resolved].merge(career.matches[["match_id", "section", "season"]], on="match_id")
    stumpers = clear[clear.kind == "stumped"]
    catches = clear[clear.kind == "caught"]
    rows = []
    for r in f.itertuples():
        mm = m.loc[r.match_id]
        side = list(dict.fromkeys(xi.get((r.match_id, r.team), [])))  # both innings list the same XI
        cands = resolve_candidates(r.printed, side)
        if r.kind == "caught" and r.bowler in cands and len(cands) > 1:
            cands = [c for c in cands if c != r.bowler]  # caught-and-bowled is printed "c & b"
        in_attack = bowled.get((r.match_id, r.innings_no), set())
        suggestion = reason = ""
        # the wicketkeeper: proven in this match, then this season, then ever, for this side
        st_team = stumpers[stumpers.team == r.team]
        for scope, label in ((st_team[st_team.match_id == r.match_id], "made a stumping in this match"),
                             (st_team[(st_team.section == mm.section) & (st_team.season == mm.season)],
                              f"keeps wicket for {r.team} this season (has made stumpings)"),
                             (st_team, f"keeps wicket for {r.team} (has made stumpings for them)")):
            keepers = [c for c in cands if c in set(scope.player) and c not in in_attack]
            if len(keepers) == 1:
                suggestion = keepers[0]
                reason = f"{keepers[0]} {label}; " + ("only the keeper makes stumpings" if r.kind == "stumped"
                                                      else "the keeper takes the most catches")
                break
        if not suggestion and r.kind == "stumped" and len(cands) > 1:
            # a keeper doesn't bowl: whoever bowled at any point in this match isn't the stumper
            in_match = set().union(*[bowled.get((r.match_id, n), set()) for n in range(1, 5)])
            keepers = [c for c in cands if c not in in_match]
            if len(keepers) == 1:
                suggestion = keepers[0]
                reason = f"the other {r.printed} bowled in this match, and only the wicketkeeper makes stumpings"
        if not suggestion and r.kind == "caught" and len(cands) > 1:
            season = catches[(catches.team == r.team) & (catches.section == mm.section) & (catches.season == mm.season)]
            counts = season.player.value_counts()
            ranked = sorted(cands, key=lambda c: counts.get(c, 0), reverse=True)
            top, second = counts.get(ranked[0], 0), counts.get(ranked[1], 0)
            if top >= 2 and top >= 2 * max(second, 1):
                suggestion = ranked[0]
                reason = (f"{ranked[0]} has taken {top} of {poss(r.team)} clear catches this season, "
                          + ", ".join(f"{c} {counts.get(c, 0)}" for c in ranked[1:]))
        rows.append(dict(credit_key=r.credit_key, match_id=r.match_id, date=mm.date,
                         match=f"{mm.date:%d %b %Y} · {mm.home} v {mm.away}", innings_no=r.innings_no, team=r.team,
                         printed=r.printed, kind=r.kind, batter=r.batter, bowler=r.bowler,
                         candidates=cands + [p for p in side if p not in cands], likely=cands,
                         suggestion=suggestion, reason=reason))
    return pd.DataFrame(rows, columns=cols).sort_values(["date", "innings_no"]).reset_index(drop=True)


def merge_suggestions(career) -> pd.DataFrame:
    """Pairs of names that might be one player and wait for your click (lookalike.py: the same initial and surname,
    a missing or extra initial, near-spellings on the same team, a move between teams with the very same surname;
    never two names in the same match). The pairs sure to be one player are joined already (career.auto_joins).
    Columns: keep, other, keep_matches, other_matches, teams, why, and the numbers of each."""
    from . import lookalike as LA
    p = LA.pairs(LA.from_tables(career.batting, career.bowling, career.matches), career.fixes.keep_apart)
    p = p[~p.sure.astype(bool)].rename(columns={"team": "teams"})
    return p.reset_index(drop=True)


def split_suggestions(career) -> pd.DataFrame:
    """Names that turned out for two or more different teams in the same section
    and season - maybe two different players with the same name."""
    appear = pd.concat([career.batting[["match_id", "team", "player"]], career.bowling[["match_id", "team", "player"]]])
    appear = appear.drop_duplicates().merge(career.matches[["match_id", "section", "season"]], on="match_id")
    g = appear.groupby(["player", "section", "season"]).team.apply(lambda s: sorted(set(s)))
    rows = [dict(player=p, section=sec, season=season, teams=teams)
            for (p, sec, season), teams in g.items() if len(teams) > 1]
    return pd.DataFrame(rows, columns=["player", "section", "season", "teams"])


def replay_conflicts(career) -> pd.DataFrame:
    """Knockout games that can't all belong to one playthrough of a season, among
    the games still counted: two finals, or one team in two knockouts on the same
    day.  (With file times these are set aside automatically; this is for careers
    whose files came without them.)"""
    m = career.matches[career.matches.knockout]
    rows = []
    for (event, season), g in m.groupby(["event", "season"]):
        flagged = set()
        finals = g[g.stage == "Final"]
        if len(finals) > 1:
            flagged |= set(finals.match_id)
        for day, d in g.groupby("date"):
            teams = list(d.home) + list(d.away)
            clash = {t for t in teams if teams.count(t) > 1}
            flagged |= set(d[d.home.isin(clash) | d.away.isin(clash)].match_id)
        for r in g[g.match_id.isin(flagged)].itertuples():
            rows.append(dict(match_id=r.match_id, group=f"{event} {season}", date=r.date, stage=r.stage,
                             home=r.home, away=r.away, result=r.result))
    return pd.DataFrame(rows, columns=["match_id", "group", "date", "stage", "home", "away", "result"])


def shared_names(career) -> pd.DataFrame:
    """One row per name that turned out for two or more teams in the same season of a
    competition, so almost certainly two different players printed the same way
    ("R Patel" at Leicestershire and at Surrey).  With the usual fix: the name stays
    with the team it played most games for, and the player at each other team gets
    the team added to the name ("R Patel (Surrey)")."""
    cols = ["player", "teams", "games", "where", "keep", "separate"]
    sp = split_suggestions(career)
    if sp.empty:
        return pd.DataFrame(columns=cols)
    appear = pd.concat([career.batting[["match_id", "team", "player"]],
                        career.bowling[["match_id", "team", "player"]]]).drop_duplicates()
    rows = []
    for player, g in sp.groupby("player", sort=True):
        teams = sorted({t for ts in g.teams for t in ts})
        mine = appear[appear.player == player]
        games = {t: int(mine[mine.team == t].match_id.nunique()) for t in teams}
        order = sorted(teams, key=lambda t: (-games[t], t))
        rows.append(dict(player=player, teams=order, games=games,
                         where=list(dict.fromkeys(f"{s} {y}" for s, y in zip(g.section, g.season))),
                         keep=order[0], separate=order[1:]))
    return pd.DataFrame(rows, columns=cols)
