"""Player ratings and team Elo, kept separately for every section.

Player rating
    Each innings gets points: batting = runs, adjusted for scoring speed in
    limited-overs cricket (runs x strike rate / the section's strike rate);
    bowling = wickets x the section's runs-per-wicket plus runs saved against
    the section's economy.  A rating is a weighted average of a player's
    innings with the most recent counting most (each older innings counts
    DECAY times the one after it), scaled so that 500 is the average of the
    better half of the section's regulars and 1000 is twice that.

Team Elo
    Every team starts at 1500.  After each match the winner takes points from
    the loser: more for beating a stronger side, fewer for beating a weaker
    one.  A draw or tie moves the two ratings towards each other.  Points
    are only swapped, never created, so the average stays 1500.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .stats import Scope, player_tables

DECAY = 0.9
MIN_INNINGS = 5
ELO_START, ELO_K, ELO_K_KNOCKOUT = 1500.0, 20.0, 32.0


def _weighted(values: np.ndarray) -> float:
    w = DECAY ** np.arange(len(values) - 1, -1, -1)  # newest innings weight 1
    return float((values * w).sum() / w.sum())


def _scale(raw: pd.Series) -> float:
    """What a rating of 500 stands for: the average of the better half of the
    qualified players (the specialists), so tail-enders' batting doesn't set the bar."""
    raw = raw.dropna()
    if raw.empty:
        return np.nan
    return float(raw[raw >= raw.median()].mean())


def innings_points(career, section: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Points for every batting innings and every bowling spell in a section."""
    ids = Scope(sections=[section]).match_ids(career.matches)
    _, _, _, base = player_tables(career, Scope(sections=[section]))
    dates = career.matches.set_index("match_id").date
    bat = career.batting[career.batting.match_id.isin(ids) & career.batting.did_bat].copy()
    if base.kind == "multi" or not np.isfinite(base.strike_rate) or base.strike_rate == 0:
        bat["points"] = bat.runs.astype(float)
    else:
        sr = np.where(bat.balls > 0, bat.runs / bat.balls.replace(0, np.nan) * 100, base.strike_rate)
        bat["points"] = bat.runs * np.clip(sr / base.strike_rate, 0.5, 2.0)
    bowl = career.bowling[career.bowling.match_id.isin(ids) & (career.bowling.balls > 0)].copy()
    wicket = base.bowl_average if np.isfinite(base.bowl_average) else 25.0
    econ = base.economy if np.isfinite(base.economy) else 6.0
    bowl["points"] = bowl.wickets * wicket + (bowl.balls * econ / 6 - bowl.runs)
    for d in (bat, bowl):
        d["date"] = d.match_id.map(dates)
    return bat.sort_values(["date", "innings_no"]), bowl.sort_values(["date", "innings_no"])


def player_ratings(career, section: str, min_innings: int = MIN_INNINGS) -> pd.DataFrame:
    """Current batting, bowling and all-round rating for every player with
    `min_innings` or more innings (batting or bowling) in the section."""
    bat, bowl = innings_points(career, section)
    rows: dict[str, dict] = {}
    for kind, d in (("batting", bat), ("bowling", bowl)):
        for p, g in d.groupby("player"):
            if len(g) >= min_innings:
                r = rows.setdefault(p, {"player": p, "team": g.team.iloc[-1]})
                r[f"{kind}_raw"] = _weighted(g.points.to_numpy(float))
                r[f"{kind}_innings"] = len(g)
                r["team"] = g.team.iloc[-1]
    t = pd.DataFrame(list(rows.values()))
    cols = ["player", "team", "batting", "bowling", "all_round", "batting_innings", "bowling_innings"]
    if t.empty:
        return pd.DataFrame(columns=cols)
    for kind in ("batting", "bowling"):
        if f"{kind}_raw" not in t:
            t[f"{kind}_raw"], t[f"{kind}_innings"] = np.nan, 0
        mean = _scale(t[f"{kind}_raw"])
        t[kind] = (t[f"{kind}_raw"] / mean * 500).clip(lower=0).round() if mean and mean > 0 else np.nan
    t["all_round"] = (t.batting * t.bowling / 1000).round()
    t[["batting_innings", "bowling_innings"]] = t[["batting_innings", "bowling_innings"]].fillna(0).astype(int)
    return t[cols]


def rating_history(career, section: str, players: list[str], kind: str = "batting") -> pd.DataFrame:
    """A player's rating after each innings (unscaled points average, then scaled
    by the section's current mean so it lines up with the table)."""
    bat, bowl = innings_points(career, section)
    d = bat if kind == "batting" else bowl
    # the same scale as the table: rating = raw / (mean raw of the qualified players) * 500
    pts = d.groupby("player").points.apply(lambda s: _weighted(s.to_numpy(float)) if len(s) >= MIN_INNINGS else np.nan)
    raw_mean = _scale(pts) if pts.notna().any() else None
    rows = []
    for p in players:
        g = d[d.player == p]
        for i in range(1, len(g) + 1):
            v = _weighted(g.points.to_numpy(float)[:i])
            rows.append(dict(player=p, innings=i, date=g.date.iloc[i - 1],
                             rating=max(0.0, v / raw_mean * 500) if raw_mean else np.nan))
    return pd.DataFrame(rows, columns=["player", "innings", "date", "rating"])


def team_elo(career, section: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(current table, history).  History has one row per team per match."""
    m = career.matches[career.matches.section == section].sort_values(["date", "match_id"])
    rating: dict[str, float] = {}
    peak: dict[str, float] = {}
    played: dict[str, int] = {}
    hist = []
    for r in m.itertuples():
        if r.result_type == "no result":
            continue
        a, b = r.home, r.away
        ra, rb = rating.get(a, ELO_START), rating.get(b, ELO_START)
        ea = 1 / (1 + 10 ** ((rb - ra) / 400))
        sa = 1.0 if r.winner == a else 0.0 if r.winner == b else 0.5
        k = ELO_K_KNOCKOUT if r.knockout else ELO_K
        delta = k * (sa - ea)
        rating[a], rating[b] = ra + delta, rb - delta
        for t, before in ((a, ra), (b, rb)):
            played[t] = played.get(t, 0) + 1
            peak[t] = max(peak.get(t, ELO_START), rating[t])
            hist.append(dict(match_id=r.match_id, date=r.date, team=t, before=before, after=rating[t],
                             opponent=b if t == a else a, result=r.result))
    table = pd.DataFrame([dict(team=t, elo=v, played=played[t], peak=peak[t]) for t, v in rating.items()],
                         columns=["team", "elo", "played", "peak"]).sort_values("elo", ascending=False).reset_index(drop=True)
    table.index = table.index + 1
    return table, pd.DataFrame(hist, columns=["match_id", "date", "team", "before", "after", "opponent", "result"])


# --------------------------------------------------------------------------- every team by runs and wickets
TOTAL_COLUMNS = ["team", "matches", "runs", "wickets", "runs_per_match", "wickets_per_match", "runs_rank", "wickets_rank"]


def team_totals(career, ids, upto=None) -> pd.DataFrame:
    """Every team in these matches (up to a date, that day included, when given): matches played, runs scored off the
    bat (extras are no one's, as in every share on the site), wickets taken (every wicket that fell to them, run-outs
    included), each per match, and the rank by each (1 the most; equal totals share a rank)."""
    m = career.matches[career.matches.match_id.isin(ids)]
    if upto is not None:
        m = m[m.date <= pd.Timestamp(upto)]
    if m.empty:
        return pd.DataFrame(columns=TOTAL_COLUMNS)
    mids = set(m.match_id)
    played = pd.concat([m.home, m.away]).value_counts()
    b = career.batting[career.batting.match_id.isin(mids) & career.batting.did_bat]
    runs = b.groupby("team").runs.sum()
    inn = career.innings[career.innings.match_id.isin(mids)]
    wkts = inn.groupby("opposition").wickets.sum()      # the wickets each side took: its opponents' innings
    d = pd.DataFrame({"team": played.index, "matches": played.values.astype(int)})
    d["runs"] = d.team.map(runs).fillna(0).astype(int)
    d["wickets"] = d.team.map(wkts).fillna(0).astype(int)
    d["runs_per_match"] = d.runs / d.matches
    d["wickets_per_match"] = d.wickets / d.matches
    d["runs_rank"] = d.runs.rank(method="min", ascending=False).astype(int)
    d["wickets_rank"] = d.wickets.rank(method="min", ascending=False).astype(int)
    return d.sort_values(["runs", "team"], ascending=[False, True]).reset_index(drop=True)[TOTAL_COLUMNS]
