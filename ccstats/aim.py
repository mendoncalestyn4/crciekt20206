"""Three stage 2 pieces from what the scorecards record exactly.

- Who carries the team: each player's runs out of all the team's runs (the totals as printed, extras included) and
  their wickets out of all the wickets the team's bowlers took, in these matches (the same counting as the Player
  page's share of the team).
- The usual score at each wicket: the team's typical (median) score when each wicket fell, against their opponents' in
  the same games, with the highest and lowest.
- The score to aim for: how many to make batting first to win. From every finished one-innings game here (not
  shortened by rain), how a side batting first got on is fitted against its total, the two sides' ratings (Elo) just
  before the game and where it was played (home, away or neutral): the total that makes it an even game, and the one
  that gives a 70% chance, for this side against that one there.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .insights import first_innings
from .rankings import team_elo
from .stats import kind_of

MIN_GAMES = 30          # finished first innings needed before a score to aim for is given
VENUES = ("home", "away", "neutral")


# --------------------------------------------------------------------------- who carries the team
def team_shares(career, ids, team: str) -> pd.DataFrame:
    """Every player of the team in these matches: matches, runs and their share of the team's runs, wickets and their
    share of the team's wickets, most runs first. Columns: player, matches, runs, run_share, wickets, wicket_share
    (shares in %); attrs team_runs, team_wickets, team_matches."""
    cols = ["player", "matches", "runs", "run_share", "wickets", "wicket_share"]
    mids = set(career.matches[career.matches.match_id.isin(ids)
                              & ((career.matches.home == team) | (career.matches.away == team))].match_id)
    inn = career.innings[career.innings.match_id.isin(mids) & (career.innings.team == team)]
    bat = career.batting[career.batting.match_id.isin(mids) & (career.batting.team == team)]
    bowl = career.bowling[career.bowling.match_id.isin(mids) & (career.bowling.team == team)]
    team_runs, team_wkts = int(inn.runs.sum()), int(bowl.wickets.sum())
    if bat.empty:
        out = pd.DataFrame(columns=cols)
    else:
        played = bat.groupby("player").match_id.nunique()
        runs = bat[bat.did_bat].groupby("player").runs.sum().reindex(played.index, fill_value=0)
        wkts = bowl.groupby("player").wickets.sum().reindex(played.index, fill_value=0)
        out = pd.DataFrame({"player": played.index, "matches": played.values.astype(int), "runs": runs.values.astype(int),
                            "wickets": wkts.values.astype(int)})
        out["run_share"] = out.runs / team_runs * 100 if team_runs else 0.0
        out["wicket_share"] = out.wickets / team_wkts * 100 if team_wkts else 0.0
        out = out.sort_values(["runs", "wickets", "player"], ascending=[False, False, True]).reset_index(drop=True)[cols]
    out.attrs.update(team_runs=team_runs, team_wickets=team_wkts, team_matches=len(mids))
    return out


# --------------------------------------------------------------------------- the usual score at each wicket
def usual_by_wicket(career, ids, team: str) -> pd.DataFrame:
    """For each wicket: the team's median score when it fell (and in how many innings), the highest and lowest, and
    the opponents' median in the same games (medians as whole runs, a half rounded up). Only wickets that fell in at least 30% of the team's innings (later ones
    fall too rarely for a fair usual). Columns: wicket, usual, innings, best, worst, opp_usual, opp_innings."""
    cols = ["wicket", "usual", "innings", "best", "worst", "opp_usual", "opp_innings"]
    mids = set(career.matches[career.matches.match_id.isin(ids)
                              & ((career.matches.home == team) | (career.matches.away == team))].match_id)
    f = career.fow[career.fow.match_id.isin(mids)]
    mine, theirs = f[f.team == team], f[f.team != team]
    n_inns = career.innings[career.innings.match_id.isin(mids) & (career.innings.team == team)].shape[0]
    if mine.empty or not n_inns:
        return pd.DataFrame(columns=cols)
    g = mine.groupby("wicket").score.agg(usual="median", innings="size", best="max", worst="min")
    o = theirs.groupby("wicket").score.agg(opp_usual="median", opp_innings="size")
    out = g.join(o, how="left").reset_index()
    out = out[out.innings >= 0.3 * n_inns]
    # whole runs, halves always rounded up (both sides alike, so the difference between them stays exact)
    out["usual"] = np.floor(out.usual + 0.5).astype(int)
    out["opp_usual"] = np.floor(out.opp_usual + 0.5).astype("Int64")
    return out[cols].reset_index(drop=True)


# --------------------------------------------------------------------------- the score to aim for
def _games(career, ids) -> pd.DataFrame:
    """Finished first innings (won or lost; draws, ties and rain games left out) with the batting side's venue and the
    two sides' ratings just before the game."""
    d = first_innings(career, ids)
    d = d[d.outcome.isin(["won", "lost"])]
    if d.empty:
        return d.assign(venue=[], elo_diff=[], won=[])
    m = career.matches.set_index("match_id")
    d = d.assign(section=d.match_id.map(m.section), home=d.match_id.map(m.home), away=d.match_id.map(m.away),
                 neutral=d.match_id.map(m.neutral).astype(bool), date=d.match_id.map(m.date))
    d["opp"] = np.where(d.team == d.home, d.away, d.home)
    d["venue"] = np.where(d.neutral, "neutral", np.where(d.team == d.home, "home", "away"))
    before = pd.concat([team_elo(career, s)[1] for s in d.section.unique()]).set_index(["match_id", "team"]).before
    d["elo_diff"] = [before.get((mid, t), np.nan) - before.get((mid, o), np.nan) for mid, t, o in zip(d.match_id, d.team, d.opp)]
    d = d[d.elo_diff.notna()]
    d["won"] = (d.outcome == "won").astype(float)
    return d


def _fit(X: np.ndarray, y: np.ndarray, ridge: float = 1.0, steps: int = 50) -> np.ndarray:
    """Logistic regression by Newton's method, with a small ridge on everything but the intercept (so a handful of
    away games can't push their term anywhere silly)."""
    w = np.zeros(X.shape[1])
    pen = np.full(X.shape[1], ridge)
    pen[0] = 0.0
    for _ in range(steps):
        p = 1 / (1 + np.exp(-np.clip(X @ w, -30, 30)))  # clipped: a side that always wins can't overflow it
        g = X.T @ (y - p) - pen * w
        H = (X * (p * (1 - p))[:, None]).T @ X + np.diag(pen)
        step = np.linalg.solve(H, g)
        w = w + step
        if np.max(np.abs(step)) < 1e-8:
            break
    return w


def model(career, ids) -> dict | None:
    """The fit for these matches (one section), or None when there's too little to go on. When the ratings come out
    pointing the wrong way (a stronger side needing more runs, which only a small or odd sample gives) they're left
    out and the fit is made again on the total and the ground alone."""
    d = _games(career, ids)
    if len(d) < MIN_GAMES or d.won.nunique() < 2:
        return None
    mu, sd = float(d.runs.mean()), float(d.runs.std()) or 1.0
    X = np.column_stack([np.ones(len(d)), (d.runs - mu) / sd, d.elo_diff / 100, d.venue.eq("home"), d.venue.eq("away")]).astype(float)
    y = d.won.to_numpy()
    w = _fit(X, y)
    rated = True
    if w[2] <= 0:
        keep = [0, 1, 3, 4]
        w = np.insert(_fit(X[:, keep], y), 2, 0.0)
        rated = False
    if w[1] <= 0:   # more runs must mean more wins, or the fit says nothing about totals
        return None
    return dict(w=w, mu=mu, sd=sd, games=len(d), low=int(d.runs.min()), high=int(d.runs.max()), rated=rated)


def chance(fit: dict, runs: float, elo_diff: float, venue: str) -> float:
    w = fit["w"]
    z = w[0] + w[1] * (runs - fit["mu"]) / fit["sd"] + w[2] * elo_diff / 100 + w[3] * (venue == "home") + w[4] * (venue == "away")
    return 1 / (1 + math.exp(-z)) * 100


def total_for(fit: dict, p: float, elo_diff: float, venue: str) -> float:
    """The first-innings total that gives a p (0-1) chance of winning."""
    w = fit["w"]
    z = math.log(p / (1 - p))
    rest = w[0] + w[2] * elo_diff / 100 + w[3] * (venue == "home") + w[4] * (venue == "away")
    return fit["mu"] + (z - rest) / w[1] * fit["sd"]


def score_to_aim(career, ids, me: str, opp: str) -> dict:
    """For `me` against `opp`, at home, away and on a neutral ground: the total for an even game and for a 70% chance
    when batting first; the score `opp` usually sets against `me` there; and every real game between them there."""
    m = career.matches[career.matches.match_id.isin(ids)]
    secs = list(m.section.unique())
    out: dict = dict(none="", section="", games=0, rated=False, venues={})
    if len(secs) != 1:
        out["none"] = "Pick one format to see the score to aim for: totals from different formats are never mixed."
        return out
    section = secs[0]
    out["section"] = section
    if kind_of(m) == "multi":
        out["none"] = ("Not for multi-day cricket: a first-innings total doesn't decide the match there (the follow-on, "
                       "declarations and draws do).")
        return out
    fit = model(career, ids)
    if fit is None:
        out["none"] = f"Not enough finished games here yet to work it out (it needs {MIN_GAMES})."
        return out
    out["games"] = fit["games"]
    out["rated"] = fit["rated"]
    elo = team_elo(career, section)[0].set_index("team").elo
    diff = float(elo.get(me, 1500) - elo.get(opp, 1500))
    d = first_innings(career, ids)
    mm = career.matches.set_index("match_id")
    for venue in VENUES:
        even, seventy = total_for(fit, 0.5, diff, venue), total_for(fit, 0.7, diff, venue)
        res = dict(even=int(round(even)), seventy=int(round(seventy)), beyond=bool(seventy > fit["high"]),
                   below=bool(even < fit["low"]))
        # their first innings against us, with the ground from our side (our home is their away)
        theirs_venue = {"home": "away", "away": "home", "neutral": "neutral"}[venue]
        g = _at(d[(d.team == opp) & d.match_id.map(lambda x: me in (mm.home[x], mm.away[x])).astype(bool)], mm, opp, theirs_venue)
        res["they_set"] = int(round(float(g.runs.median()))) if len(g) else None
        res["they_set_n"] = int(len(g))
        if not len(g):
            a = _at(d[d.team == opp], mm, opp, theirs_venue)
            res["they_usual"] = int(round(float(a.runs.median()))) if len(a) else None
            res["they_usual_n"] = int(len(a))
        meet = m[((m.home == me) & (m.away == opp)) | ((m.home == opp) & (m.away == me))]
        meet = _at(meet, mm, me, venue).sort_values("date", ascending=False)
        inn = career.innings[career.innings.match_id.isin(meet.match_id)]
        res["meetings"] = [dict(id=x, date=f"{dt:%d %b %Y}", first=_first(inn, x), result=r)
                           for x, dt, r in zip(meet.match_id, meet.date, meet.result)]
        out["venues"][venue] = res
    return out


def _at(df: pd.DataFrame, mm, team: str, venue: str) -> pd.DataFrame:
    """The rows of matches played at `venue` from `team`'s side (a mask by row, so an empty table stays a table)."""
    return df[df.match_id.map(lambda x: _venue(mm, x, team) == venue).astype(bool)]


def _venue(mm, mid, team) -> str:
    if bool(mm.neutral[mid]):
        return "neutral"
    return "home" if mm.home[mid] == team else "away"


def _first(inn, mid) -> str:
    """'India 175/6 · England 160' : each side's innings in order."""
    g = inn[inn.match_id == mid].sort_values("innings_no")
    return " · ".join(f"{r.team} {r.runs}" + ("" if r.all_out else f"/{r.wickets}") for r in g.itertuples())
