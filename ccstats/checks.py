"""Things worth a second look on the data check page.

Nothing here changes any data. These are *suggestions*; a fix only happens
when the user confirms it, and it is then stored in the career's Fixes."""

from __future__ import annotations

import re
from itertools import combinations

import pandas as pd


def _base(name: str) -> str:
    return re.sub(r"\s*\(\d+\)$", "", name).strip()


def _surname(name: str) -> str:
    parts = _base(name).replace("'", " ").split()
    return parts[-1].lower() if parts else ""


def _initial(name: str) -> str:
    return _base(name)[:1].upper()


def uncredited(career) -> pd.DataFrame:
    """Catches and stumpings the scorecard didn't make clear (e.g. 'c Khan' with
    two Khans in the side), with the players who could have taken them."""
    f = career.fielding[~career.fielding.resolved]
    cols = ["credit_key", "match_id", "date", "match", "innings_no", "team", "printed", "kind", "batter", "bowler", "candidates"]
    if f.empty:
        return pd.DataFrame(columns=cols)
    m = career.matches.set_index("match_id")
    xi = career.batting.groupby(["match_id", "team"]).player.apply(list)
    rows = []
    for r in f.itertuples():
        mm = m.loc[r.match_id]
        side = list(dict.fromkeys(xi.get((r.match_id, r.team), [])))  # both innings list the same XI
        sur = _surname(r.printed)
        likely = [p for p in side if _surname(p) == sur or sur in p.lower().replace("'", "")]
        rows.append(dict(credit_key=r.credit_key, match_id=r.match_id, date=mm.date,
                         match=f"{mm.date:%d %b %Y} · {mm.home} v {mm.away}", innings_no=r.innings_no, team=r.team,
                         printed=r.printed, kind=r.kind, batter=r.batter, bowler=r.bowler,
                         candidates=likely + [p for p in side if p not in likely]))
    return pd.DataFrame(rows, columns=cols).sort_values(["date", "innings_no"]).reset_index(drop=True)


def merge_suggestions(career) -> pd.DataFrame:
    """Pairs of names that might be one player: same surname and first initial,
    at least one team in common, and never in the same match together."""
    appear = pd.concat([career.batting[["match_id", "team", "player"]], career.bowling[["match_id", "team", "player"]]])
    matches_of = appear.groupby("player").match_id.apply(set)
    teams_of = appear.groupby("player").team.apply(set)
    by_key: dict[tuple, list[str]] = {}
    for p in matches_of.index:
        by_key.setdefault((_surname(p), _initial(p)), []).append(p)
    rows = []
    for names in by_key.values():
        for a, b in combinations(sorted(names), 2):
            shared = teams_of[a] & teams_of[b]
            if not shared or matches_of[a] & matches_of[b]:
                continue
            ma, mb = len(matches_of[a]), len(matches_of[b])
            keep, other = (a, b) if ma >= mb else (b, a)
            rows.append(dict(keep=keep, other=other, keep_matches=max(ma, mb), other_matches=min(ma, mb),
                             teams=", ".join(sorted(shared))))
    return pd.DataFrame(rows, columns=["keep", "other", "keep_matches", "other_matches", "teams"])


def split_suggestions(career) -> pd.DataFrame:
    """Names that turned out for two or more different teams in the same section
    and season - maybe two different players with the same name."""
    appear = pd.concat([career.batting[["match_id", "team", "player"]], career.bowling[["match_id", "team", "player"]]])
    appear = appear.drop_duplicates().merge(career.matches[["match_id", "section", "season"]], on="match_id")
    g = appear.groupby(["player", "section", "season"]).team.apply(lambda s: sorted(set(s)))
    rows = [dict(player=p, section=sec, season=season, teams=teams)
            for (p, sec, season), teams in g.items() if len(teams) > 1]
    return pd.DataFrame(rows, columns=["player", "section", "season", "teams"])
