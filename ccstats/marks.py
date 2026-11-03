"""Marks out of 10 for every player after each series or tournament, ranked: the report card on your own players.

Each match is measured against the match itself, so the same score can be worth a lot or a little:
- **batting:** the runs as a share of his own side's runs in the match, and of the average side's runs in it (half
  each). A lone hundred in 180 all out is a big share; one of four hundreds in 600 is a small one; forty in a game
  where both sides struggled counts for more than forty on a flat pitch. In white-ball cricket the speed counts too:
  half the runs above (or below) what the match's own run rate would have made off the same balls.
- **bowling:** the wickets as a share of the wickets his side took, and of the average side's (half each). In
  white-ball cricket the runs kept below (or let go above) the match's run rate count, at the match's runs per wicket.
- **fielding:** a catch or stumping is a quarter of a wicket.
A rain-shortened white-ball game counts for the share of its overs that were bowled; a game with no result doesn't
count, and neither does a game in which a player neither batted, bowled nor took a catch.

A player's series is their average match, as if they had also played one more match at the usual level, so one great
game counts for less than the same over a whole series (on a 1,544-match save a single game made a 9 or 10 in 5% of
cases, a full series in 7%; it still can: 9 wickets in your only Test is a 10). The mark is where that series ranks among every player's series in the same format in the
career (every team's, not just yours), on a bell curve: 5 or 6 is a usual series, 8 about the best one in seven,
9 the best one in fifteen, 10 the best one in forty; 1 to 3 the same at the bottom.
"""

from __future__ import annotations

from statistics import NormalDist

import numpy as np
import pandas as pd

from .analysis import BOWLER_BALLS
from .records import by_played
from .stats import BALL_QUOTA, KIND

SPEED = 0.5            # how much of the runs above the match's run rate count for a batter (white-ball)
CATCH = 0.25           # a catch or stumping, in wickets
SETTLE = 1.0           # matches at the usual level added to every player's series
ALL_ROUND = 0.35       # how much a good second string (an all-rounder's) adds to the first
MIN_REFERENCE = 30     # player-series needed in a format to mark against it; fewer and the format kind is used
PLURAL = {"Test": "Tests", "ODI": "ODIs", "T20I": "T20Is"}
COLUMNS = ["series", "team", "player", "games", "value", "settled", "mark", "rank", "of", "reference", "label", "start",
           "end", "format", "runs", "outs", "balls", "hundreds", "fifties", "wickets", "conceded", "balls_bowled",
           "best_bowling", "dismissals", "line", "best", "best_match"]


def series_key(matches: pd.DataFrame) -> pd.Series:
    """Which series or tournament each match belongs to: its series, or the competition as run that season (a World
    Cup, an IPL season, a Ranji Trophy season)."""
    sid = matches.series_id.astype(object).fillna("").astype(str)
    return sid.where(sid != "", matches.event.astype(str) + " " + matches.season.astype(str))


def match_values(career, ids=None) -> pd.DataFrame:
    """One row per player per match: his share of the match (batting, bowling, fielding) as described above."""
    m = career.matches
    if ids is not None:
        m = m[m.match_id.isin(ids)]
    m = m[m.result_type != "no result"]
    ids = pd.Index(m.match_id)
    inn = career.innings[career.innings.match_id.isin(ids)]
    tot = inn.groupby("match_id").agg(runs_m=("runs", "sum"), wkts_m=("wickets", "sum"), balls_m=("balls", "sum"))
    side = inn.groupby(["match_id", "team"]).agg(runs_own=("runs", "sum"), lost=("wickets", "sum")).reset_index()
    side = side.merge(tot, on="match_id")
    side["took"] = side.wkts_m - side.lost   # the wickets the other side lost
    side["runs_avg"] = side.runs_m / 2
    side["took_avg"] = side.wkts_m / 2
    meta = m.set_index("match_id")[["format", "rain"]]
    side = side.join(meta, on="match_id")
    side["white"] = side.format.map(KIND).ne("multi")
    side["rpb"] = side.runs_m / side.balls_m.replace(0, np.nan)
    side["rpw"] = side.runs_m / side.wkts_m.clip(lower=1)
    quota = side.format.map(BALL_QUOTA).astype(float)   # numbers even when nothing maps (pandas 3 keeps text otherwise)
    side["weight"] = np.where(side.rain & side.white & quota.notna(),
                              (side.balls_m / (2 * quota)).clip(upper=1.0), 1.0)
    # a side's own total is never taken as less than half the average side's, so one tiny total can't blow a share up
    side["bat_div"] = 0.5 * (1 / np.maximum(side.runs_own, 0.5 * side.runs_avg).clip(lower=1) + 1 / side.runs_avg.clip(lower=1))
    side["bowl_div"] = 0.5 * (1 / np.maximum(side.took, 0.5 * side.took_avg).clip(lower=1)
                              + 1 / side.took_avg.clip(lower=1))
    key = ["match_id", "team", "player"]
    b = career.batting[career.batting.match_id.isin(ids) & career.batting.did_bat]
    # hundreds and fifties innings by innings: two in a Test are two
    b = b.assign(hundred=b.runs >= 100, fifty=(b.runs >= 50) & (b.runs < 100))
    bat = b.groupby(key).agg(runs=("runs", "sum"), balls=("balls", "sum"), outs=("out", "sum"), top=("runs", "max"),
                             hundreds=("hundred", "sum"), fifties=("fifty", "sum")).reset_index()
    w = career.bowling[career.bowling.match_id.isin(ids) & (career.bowling.balls > 0)]
    bowl = w.groupby(key).agg(wickets=("wickets", "sum"), conceded=("runs", "sum"), balls_bowled=("balls", "sum"),
                              haul=("wickets", "max")).reset_index()
    f = career.fielding[career.fielding.match_id.isin(ids) & career.fielding.resolved]
    fld = f.groupby(key).size().rename("dismissals").reset_index()
    d = bat.merge(bowl, on=key, how="outer").merge(fld, on=key, how="outer")
    nums = ["runs", "balls", "outs", "top", "hundreds", "fifties", "wickets", "conceded", "balls_bowled", "haul", "dismissals"]
    d[nums] = d[nums].astype(float).fillna(0)   # an empty table merges in as text; these are all counts
    d = d.merge(side[["match_id", "team", "white", "rpb", "rpw", "weight", "bat_div", "bowl_div", "runs_own", "took"]],
                on=["match_id", "team"], how="inner")
    speed = np.where(d.white, SPEED * (d.runs - d.balls * d.rpb.fillna(0)), 0.0)
    saved = np.where(d.white, (d.balls_bowled * d.rpb.fillna(0) - d.conceded) / d.rpw, 0.0)
    d["bat"] = (d.runs + speed) * d.bat_div * d.weight
    d["bowl"] = (d.wickets + saved) * d.bowl_div * d.weight
    d["field"] = CATCH * d.dismissals * d.bowl_div * d.weight
    d["value"] = d.bat + d.bowl + d.field
    return d.reset_index(drop=True)


def _mark(z: np.ndarray) -> np.ndarray:
    return np.clip(np.floor(5.5 + 2 * z + 0.5), 1, 10).astype(int)


def _ordinal(n: int) -> str:
    return {1: "1st", 2: "2nd", 3: "3rd"}.get(n, f"{n}th")


def _figures(r) -> str:
    """'312 runs at 52.0 (1 hundred) · 9 wkts at 24.1 · 3 ct/st' for one player's series."""
    bits = []
    if r.balls > 0 or r.runs > 0:
        avg = f"at {r.runs / r.outs:.1f}" if r.outs else "never out"
        tons = f", {int(r.hundreds)} hundred{'s' if r.hundreds != 1 else ''}" if r.hundreds else (
            f", {int(r.fifties)} fift{'ies' if r.fifties != 1 else 'y'}" if r.fifties else "")
        bits.append(f"{int(r.runs)} run{'s' if r.runs != 1 else ''} {avg}{tons}")
    if r.balls_bowled > 0:
        bits.append(f"{int(r.wickets)} wkt{'s' if r.wickets != 1 else ''}"
                    + (f" at {r.conceded / r.wickets:.1f}" if r.wickets else f" for {int(r.conceded)}"))
    if r.dismissals:
        bits.append(f"{int(r.dismissals)} ct/st")
    return " · ".join(bits) or "did little"


def series_marks(career, ids=None) -> pd.DataFrame:
    """Every player's mark out of 10 in every series or tournament (all teams), ranked within his side's series.
    For the whole career it's kept with the career until its matches change (a few seconds on a big one)."""
    if ids is None:
        stamp = (id(career.matches), len(career.matches))
        kept = getattr(career, "_series_marks", None)
        if kept is None or kept[0] != stamp:
            kept = (stamp, _series_marks(career, None))
            try:
                career._series_marks = kept
            except AttributeError:
                pass
        return kept[1]
    return _series_marks(career, ids)


def _series_marks(career, ids) -> pd.DataFrame:
    m = career.matches if ids is None else career.matches[career.matches.match_id.isin(ids)]
    if m.empty:
        return pd.DataFrame(columns=COLUMNS)
    m = m.assign(series=series_key(m))
    v = match_values(career, m.match_id)
    if v.empty:
        return pd.DataFrame(columns=COLUMNS)
    meta = m.set_index("match_id")[["series", "date", "format", "level", "section", "event", "season",
                                    "series_match_no", "home", "away", "stage"]]
    v = v.join(meta, on="match_id")
    v["did"] = (v.balls > 0) | (v.runs > 0) | (v.outs > 0) | (v.balls_bowled > 0) | (v.dismissals > 0)
    v = v[v.did]
    # the reference: Tests with Tests, every other competition with itself
    v["reference"] = np.where(v.level == "International", v.format, v.section)
    pos = career.batting[career.batting.match_id.isin(v.match_id)].groupby(["match_id", "team", "player"]).position.min()
    v = v.join(pos, on=["match_id", "team", "player"])
    g = v.groupby(["series", "team", "player"])
    s = g.agg(games=("match_id", "nunique"), bat=("bat", "sum"), bowl=("bowl", "sum"), field=("field", "sum"),
              value=("value", "sum"), runs=("runs", "sum"), outs=("outs", "sum"), balls=("balls", "sum"),
              hundreds=("hundreds", "sum"), fifties=("fifties", "sum"), wickets=("wickets", "sum"),
              conceded=("conceded", "sum"), balls_bowled=("balls_bowled", "sum"), dismissals=("dismissals", "sum"),
              position=("position", "median"), start=("date", "min"), end=("date", "max"),
              format=("format", "first"), reference=("reference", "first")).reset_index()
    # too few series in a competition to rank against: its format kind (all T20 competitions together) instead
    counts = s.reference.value_counts()
    small = s.reference.map(counts) < MIN_REFERENCE
    s.loc[small, "reference"] = s.loc[small, "format"].map(KIND)
    # batters are marked against batters (the top seven) and bowlers against bowlers: a side's runs are shared by
    # eleven, its wickets by five or so, so one scale would always put the bowlers on top
    kind = s.format.map(KIND)
    s["is_batter"] = s.position.le(7) & ((s.balls > 0) | (s.outs > 0))
    s["is_bowler"] = s.balls_bowled / s.games >= kind.map(BOWLER_BALLS).astype(float)
    s["bat_v"], s["bowl_v"] = s.bat + s.field, s.bowl + s.field
    s["z_bat"], s["z_bowl"] = np.nan, np.nan
    for ref, idx in s.groupby("reference").groups.items():
        part = s.loc[idx]
        for col, who, z_col in (("bat_v", "is_batter", "z_bat"), ("bowl_v", "is_bowler", "z_bowl")):
            pool = part[part[who]]
            if pool.empty:
                continue
            usual = pool[col].sum() / pool.games.sum()
            settled = (part[col] + SETTLE * usual) / (part.games + SETTLE)
            ref_vals = np.sort(settled[part[who]].to_numpy())
            lo = np.searchsorted(ref_vals, settled.to_numpy(), side="left")
            hi = np.searchsorted(ref_vals, settled.to_numpy(), side="right")
            n = len(ref_vals)
            p = np.clip((lo + hi) / 2 / n, 0.5 / n, 1 - 0.5 / n)
            z = np.array([NormalDist().inv_cdf(x) for x in p])
            # anyone who batted is marked on it (a no. 8's hundred counts); bowling only for someone who bowled at
            # least half a bowler's share, so a part-timer's one lucky over doesn't decide his mark
            batted = (part.balls > 0) | (part.outs > 0)
            keep = batted if who == "is_batter" else (
                (part.balls_bowled / part.games >= kind.loc[idx].map(BOWLER_BALLS).astype(float) / 2)
                | ((part.balls_bowled > 0) & ~batted))   # bowling was all he did: it's what he's marked on
            s.loc[idx, z_col] = np.where(keep, z, np.nan)
    # someone who only fielded (a substitute) isn't marked
    s = s[s.z_bat.notna() | s.z_bowl.notna()].copy()
    zb, zw = s.z_bat.fillna(-9), s.z_bowl.fillna(-9)
    best, other = np.maximum(zb, zw), np.minimum(zb, zw)
    s["z"] = best + ALL_ROUND * np.clip(other, 0, None)
    s["settled"] = s.z
    s["mark"] = _mark(s.z.to_numpy())
    s["rank"] = s.groupby(["series", "team"]).z.rank(method="first", ascending=False, na_option="bottom").astype(int)
    s["of"] = s.groupby(["series", "team"]).player.transform("size")
    # the best bowling in the series, and the match he did most in
    s["best_bowling"] = ""
    hauls = v[v.balls_bowled > 0].sort_values(["wickets", "conceded"], ascending=[False, True])
    hb = hauls.groupby(["series", "team", "player"]).head(1).set_index(["series", "team", "player"])
    idx = s.set_index(["series", "team", "player"]).index
    s["best_bowling"] = [f"{int(hb.wickets[i])}/{int(hb.conceded[i])}" if i in hb.index else "" for i in idx]
    top = v.sort_values("value", ascending=False).groupby(["series", "team", "player"]).head(1)
    top = {(r.series, r.team, r.player): r for r in top.itertuples()}
    s["best_match"] = [top[i].match_id for i in idx]
    s["best"] = [_moment(top[i]) for i in idx]
    s["line"] = [_figures(r) for r in s.itertuples()]
    labels = _labels(m)
    s["label"] = s.apply(lambda r: labels.get((r.series, r.team), r.series), axis=1)
    return s[COLUMNS].sort_values(["start", "series", "team", "rank"]).reset_index(drop=True)


def _match_name(r) -> str:
    """'the 2nd Test v England' or 'v Chennai Super Kings (Final)'."""
    opp = r.away if r.team == r.home else r.home
    if r.level == "International" and pd.notna(r.series_match_no) and not str(r.series).startswith(str(r.event)):
        return f"in the {_ordinal(int(r.series_match_no))} {r.format} v {opp}"
    return f"v {opp}" + (f" ({r.stage})" if r.stage else "")


def _poss(team: str) -> str:
    return f"{team}'" if team.endswith("s") else f"{team}'s"


def _moment(r) -> str:
    """The match he did most in, in a few words: '150 of India's 290 in the 2nd Test v England'."""
    where = _match_name(r)
    if r.balls_bowled == 0 or (r.bat >= r.bowl and r.runs > 0):
        if r.runs == 0:
            return f"{int(r.dismissals)} ct/st {where}" if r.dismissals else f"0 {where}"
        return f"{int(r.runs)} of {_poss(r.team)} {int(r.runs_own)} {where}"
    took = int(r.took)
    return f"{int(r.wickets)}/{int(r.conceded)}, {int(r.wickets)} of the {took} wicket{'s' if took != 1 else ''} {r.team} took {where}"


def _labels(m: pd.DataFrame) -> dict:
    """(series, team) -> 'v England at home · 3 Tests · Nov 2028' or 'ODI World Cup 2027'."""
    out = {}
    for sid, g in m.groupby("series"):
        g = g.sort_values("date")
        first = g.iloc[0]
        for team in set(g.home) | set(g.away):
            mine = g[(g.home == team) | (g.away == team)]
            if mine.empty:
                continue
            if first.series_id:
                opp = first.away if first.home == team else first.home
                where = "" if first.neutral else (" at home" if first.home == team else " away")
                n = int(first.series_length) if pd.notna(first.series_length) else len(mine)
                fmt = PLURAL.get(first.format, first.format) if n != 1 else first.format
                out[(sid, team)] = f"v {opp}{where} · {n} {fmt} · {first.date:%b %Y}"
            else:
                out[(sid, team)] = f"{first.event} {first.season}"
    return out


def among(reference: str) -> str:
    """The group a series is marked against, in words: 'ODIs', 'the Ranji Trophy', 'all T20 cricket'."""
    if reference in KIND_WORDS:
        return KIND_WORDS[reference]
    if reference in INTERNATIONAL_FORMATS:
        return f"{reference}s"
    return reference if reference.startswith("The ") else f"the {reference}"


KIND_WORDS = {"multi": "all first-class cricket", "one": "all one-day cricket", "t20": "all T20 cricket"}
INTERNATIONAL_FORMATS = ("Test", "ODI", "T20I")


def team_report(career, team: str) -> list[dict]:
    """Your side's series, newest first: each with every player who played, ranked, with their mark and why."""
    s = series_marks(career)
    s = s[s.team == team]
    if s.empty:
        return []
    order = by_played(career, career.matches.assign(series=series_key(career.matches))[["match_id", "series"]])
    last_at = {k: i for i, k in enumerate(order.series)}
    out = []
    for sid, g in sorted(s.groupby("series"), key=lambda kv: -last_at.get(kv[0], -1)):
        g = g.sort_values("rank")
        out.append(dict(series=sid, label=g.label.iloc[0], format=g.format.iloc[0], reference=g.reference.iloc[0],
                        start=g.start.min(), end=g.end.max(), players=g.to_dict("records")))
    return out
