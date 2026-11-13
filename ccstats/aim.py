"""Three stage 2 pieces from what the scorecards record exactly.

- Who carries the team: each player's runs out of all the team's runs (the totals as printed, extras included) and
  their wickets out of all the wickets the team's bowlers took, in these matches (the same counting as the Player
  page's share of the team).
- The usual score at each wicket: the team's typical (median) score when each wicket fell, against their opponents' in
  the same games, with the highest and lowest.
- The score to aim for: how many to make batting first to win against a team, at home, away or neutral, the way the
  plan sets out (section 14, below); in multi-day cricket the first-innings totals that won, drew and lost instead.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .insights import first_innings



# --------------------------------------------------------------------------- who carries the team
def team_shares(career, ids, team: str) -> pd.DataFrame:
    """Every player of the team in these matches: matches, runs and their share of the team's runs off the bat (extras
    are no one's, so the shares add up to 100%), wickets and their
    share of the team's wickets, most runs first. Columns: player, matches, runs, run_share, wickets, wicket_share
    (shares in %); attrs team_runs, team_wickets, team_matches."""
    cols = ["player", "matches", "runs", "run_share", "wickets", "wicket_share"]
    mids = set(career.matches[career.matches.match_id.isin(ids)
                              & ((career.matches.home == team) | (career.matches.away == team))].match_id)
    inn = career.innings[career.innings.match_id.isin(mids) & (career.innings.team == team)]
    bat = career.batting[career.batting.match_id.isin(mids) & (career.batting.team == team)]
    bowl = career.bowling[career.bowling.match_id.isin(mids) & (career.bowling.team == team)]
    team_runs, team_wkts = int(bat[bat.did_bat].runs.sum()), int(bowl.wickets.sum())   # runs off the bat: extras are no one's
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
# How it's worked out (the plan, section 14, as checked on 25 October):
# - the chance of winning against the total made batting first, from every finished game without rain; how fast it
#   rises is shared by all cricket of the same length (T20Is with the IPL, the Blast and the Hundred; ODIs with the
#   domestic one-day cups), and each competition keeps its own level of totals;
# - what playing at home is worth, in runs, from every team's home and away games there: it starts near nothing and
#   grows only as the games show it;
# - how well a team bats, and how well a team bowls, in runs above or below the usual first-innings total there,
#   pulled towards the usual until there are enough games (5 games count half).
# Each game's own adjustment comes from other games only (the side batting first's bowling from the games it bowled
# first, the side chasing's batting from the games it batted first), so how often it calls past games right is each
# game judged from all the others (the curve is fitted again without the game, too).
LENGTH = {"T20": "t20", "T20I": "t20", "The Hundred": "t20", "ODI": "one", "List A": "one", "Test": "multi",
          "First-class": "multi"}
HALF = 5        # games that count half: a team's batting or bowling from n games counts n / (n + 5) of the way
HOME_HALF = 30  # home and away games that count half for what home is worth
FEW = 10        # fewer games than this behind a target: "few games, treat with care"
VENUES = ("home", "away", "neutral")
LOGIT70 = math.log(0.7 / 0.3)


def _first_innings_all(career) -> pd.DataFrame:
    """Every finished, rain-free one-innings game's first innings, with its section and length of game, the two sides,
    where it was from the side batting first's view, and whether that side won (draws, ties and no-results out)."""
    m = career.matches
    d = first_innings(career, set(m.match_id))
    d = d[d.outcome.isin(["won", "lost"])].copy()
    mm = m.set_index("match_id")
    d["section"] = d.match_id.map(mm.section)
    d["length"] = d.format.map(LENGTH).fillna("t20")
    d = d[d.length != "multi"]
    home, away = d.match_id.map(mm.home), d.match_id.map(mm.away)
    d["opp"] = np.where(d.team == home, away, home)
    neutral = d.match_id.map(mm.neutral).astype(bool)
    d["venue"] = np.where(neutral, "neutral", np.where(d.team == home, "home", "away"))
    d["won"] = (d.outcome == "won").astype(float)
    d["runs"] = d.runs.astype(float)
    return d.reset_index(drop=True)


def _fit(z: np.ndarray, sec: np.ndarray, n_sec: int, y: np.ndarray, start=None, ridge: float = 1.0) -> np.ndarray:
    """Chance of winning = 1 / (1 + e^-(slope × z + level of the competition)): one slope, a level for each competition
    (kept near nought with a small pull, so a competition with few games leans on the rest). Newton's method."""
    w = np.zeros(1 + n_sec) if start is None else start.copy()
    X = np.zeros((len(z), 1 + n_sec))
    X[:, 0] = z
    X[np.arange(len(z)), 1 + sec] = 1.0
    pen = np.full(1 + n_sec, ridge)
    pen[0] = 0.0
    for _ in range(60):
        p = 1 / (1 + np.exp(-np.clip(X @ w, -30, 30)))
        g = X.T @ (y - p) - pen * w
        H = (X * (p * (1 - p))[:, None]).T @ X + np.diag(pen) + 1e-9 * np.eye(len(w))
        step = np.linalg.solve(H, g)
        w = w + step
        if np.max(np.abs(step)) < 1e-9:
            break
    return w


def _strengths(d: pd.DataFrame) -> dict:
    """Per competition: the usual first-innings total; each team's batting (its first-innings totals) and bowling (the
    totals made against it when it bowled first) in runs above or below the usual, pulled to the usual (n / (n + 5)),
    with how many games each rests on; and what home is worth in runs (n / (n + 30) of what the games show)."""
    out = {}
    for sec, g in d.groupby("section"):
        usual = float(g.runs.mean())
        dev = g.runs - usual
        bat = dev.groupby(g.team).agg(["sum", "size"])
        bowl = dev.groupby(g.opp).agg(["sum", "size"])
        hv = g[g.venue != "neutral"]
        if len(hv) and (hv.venue == "home").any() and (hv.venue == "away").any():
            raw = (float((hv.runs[hv.venue == "home"] - usual).mean()) - float((hv.runs[hv.venue == "away"] - usual).mean())) / 2
            home = raw * len(hv) / (len(hv) + HOME_HALF)
        else:
            home = 0.0
        out[sec] = dict(usual=usual, home=home, home_games=int(len(hv)),
                        bat={t: (float(r["sum"]) / (r["size"] + HALF), int(r["size"])) for t, r in bat.iterrows()},
                        bowl={t: (float(r["sum"]) / (r["size"] + HALF), int(r["size"])) for t, r in bowl.iterrows()})
    return out


def _adjusted(d: pd.DataFrame, st: dict) -> np.ndarray:
    """Each first-innings total as an even-sides total: made against a strong bowling side and the chasers' batting
    taken out, and home counted (home worth +, away −): the total that would mean the same on level terms."""
    out = np.empty(len(d))
    for i, r in enumerate(d.itertuples()):
        s = st[r.section]
        bowl = s["bowl"].get(r.team, (0.0, 0))[0]      # the setters' own bowling (from the games they bowled first)
        bat = s["bat"].get(r.opp, (0.0, 0))[0]         # the chasers' batting (from the games they batted first)
        v = 1 if r.venue == "home" else -1 if r.venue == "away" else 0
        out[i] = r.runs - bowl - bat + v * s["home"]
    return out


def model(career, length: str) -> dict | None:
    """The fit for one length of game (every competition of it in the career), or None with too few games for it."""
    d = _first_innings_all(career)
    d = d[d.length == length].reset_index(drop=True)
    if len(d) < 2 or d.won.nunique() < 2:
        return None
    st = _strengths(d)
    secs = sorted(d.section.unique())
    si = {s: i for i, s in enumerate(secs)}
    sec = d.section.map(si).to_numpy()
    mean_s = d.groupby("section").runs.transform("mean").to_numpy()
    sd = float(d.runs.std()) or 1.0
    adj = _adjusted(d, st)
    z = (adj - mean_s) / sd           # each competition's totals about its own usual
    z0 = (d.runs.to_numpy() - mean_s) / sd
    y = d.won.to_numpy()
    w = _fit(z, sec, len(secs), y)
    w0 = _fit(z0, sec, len(secs), y)
    if w[0] <= 0:                     # more runs must mean more wins, or the fit says nothing about totals
        return None
    # each game judged from all the others: the curve fitted again without it (its adjustment already is)
    right = np.zeros(len(d), bool)
    right0 = np.zeros(len(d), bool)
    keep = np.ones(len(d), bool)
    for i in range(len(d)):
        keep[i] = False
        wi = _fit(z[keep], sec[keep], len(secs), y[keep], start=w)
        wi0 = _fit(z0[keep], sec[keep], len(secs), y[keep], start=w0)
        keep[i] = True
        right[i] = ((wi[0] * z[i] + wi[1 + sec[i]]) > 0) == (y[i] == 1)
        right0[i] = ((wi0[0] * z0[i] + wi0[1 + sec[i]]) > 0) == (y[i] == 1)
    d = d.assign(right=right, right0=right0)
    return dict(w=w, sd=sd, secs=si, st=st, games=d.groupby("section").size().to_dict(),
                right=d.groupby("section").right.mean().to_dict(), right0=d.groupby("section").right0.mean().to_dict(),
                low=d.groupby("section").runs.min().to_dict(), high=d.groupby("section").runs.max().to_dict())


def targets(fit: dict, section: str, me: str, opp: str, venue: str) -> dict:
    """For `me` batting first against `opp` at `venue`: the total for an even game and for a 70% chance, and the games
    each part rests on."""
    s = fit["st"][section]
    a = fit["w"][1 + fit["secs"][section]]
    slope = fit["w"][0]
    bowl, n_bowl = s["bowl"].get(me, (0.0, 0))      # how well you bowl (when you bowl second, after setting a total)
    bat, n_bat = s["bat"].get(opp, (0.0, 0))        # how well they bat (chasing it)
    v = 1 if venue == "home" else -1 if venue == "away" else 0
    def total(logit):
        return s["usual"] + (logit - a) / slope * fit["sd"] + bowl + bat - v * s["home"]
    return dict(even=total(0.0), seventy=total(LOGIT70), my_bowling=bowl, my_bowling_n=n_bowl, their_batting=bat,
                their_batting_n=n_bat, home=s["home"], home_games=s["home_games"], games=int(fit["games"][section]))


def score_to_aim(career, ids, me: str, opp: str, fits=None) -> dict:
    """For `me` against `opp`, at home, away and on a neutral ground. One-day and T20 cricket: the total for an even
    game and for a 70% chance batting first, how sure it is, the score `opp` usually sets against `me` there and every
    real game between them there. Multi-day cricket: the first-innings totals `me` made against `opp` in games won,
    drawn and lost, home and away. `fits`, if given, hands back the fit for a length of game (so a site can keep it
    between pages: it is the slow part)."""
    m = career.matches[career.matches.match_id.isin(ids)]
    secs = list(m.section.unique())
    out: dict = dict(none="", section="", kind="", venues={})
    if len(secs) != 1:
        out["none"] = "Pick one format to see the score to aim for: totals from different formats are never mixed."
        return out
    section = secs[0]
    out["section"] = section
    length = LENGTH.get(m.format.mode().iloc[0], "t20") if len(m) else "t20"
    mm = career.matches.set_index("match_id")
    meet_all = m[((m.home == me) & (m.away == opp)) | ((m.home == opp) & (m.away == me))]
    if length == "multi":
        out["kind"] = "multi"
        inn = career.innings[career.innings.match_id.isin(meet_all.match_id) & (career.innings.team == me)
                             & (career.innings.team_innings == 1)]
        for venue in VENUES:
            meet = _at(meet_all, mm, me, venue).sort_values("date", ascending=False)
            games = []
            for r in meet.itertuples():
                x = inn[inn.match_id == r.match_id]
                if x.empty or r.result_type == "no result":
                    continue
                res = "won" if r.winner == me else "lost" if r.winner == opp else "drawn" if r.result_type == "draw" else "tied"
                t = x.iloc[0]
                games.append(dict(id=r.match_id, date=f"{r.date:%d %b %Y}", total=int(t.runs), wickets=int(t.wickets),
                                  all_out=bool(t.all_out), declared=bool(t.declared), result=res, text=r.result))
            typ = {}
            for res in ("won", "drawn", "lost"):
                xs = [g["total"] for g in games if g["result"] == res]
                typ[res] = dict(typical=int(round(float(np.median(xs)))) if xs else None, n=len(xs))
            out["venues"][venue] = dict(typical=typ, games=games)
        return out
    out["kind"] = "limited"
    fit = (fits or (lambda n: model(career, n)))(length)
    if fit is None or section not in fit["secs"]:
        out["none"] = "No finished games here yet to work it out from."
        return out
    d = first_innings(career, ids)
    out.update(games=int(fit["games"][section]), right=float(fit["right"][section] * 100),
               right_alone=float(fit["right0"][section] * 100), home=float(fit["st"][section]["home"]))
    for venue in VENUES:
        t = targets(fit, section, me, opp, venue)
        res = dict(even=int(round(t["even"])), seventy=int(round(t["seventy"])),
                   beyond=bool(t["seventy"] > fit["high"][section]), below=bool(t["even"] < fit["low"][section]),
                   my_bowling=t["my_bowling"], my_bowling_n=t["my_bowling_n"], their_batting=t["their_batting"],
                   their_batting_n=t["their_batting_n"],
                   few=bool(min(t["my_bowling_n"], t["their_batting_n"], t["games"]) < FEW))
        # their first innings against us, with the ground from our side (our home is their away)
        theirs_venue = {"home": "away", "away": "home", "neutral": "neutral"}[venue]
        g = _at(d[(d.team == opp) & d.match_id.map(lambda x: me in (mm.home[x], mm.away[x])).astype(bool)], mm, opp, theirs_venue)
        res["they_set"] = int(round(float(g.runs.median()))) if len(g) else None
        res["they_set_n"] = int(len(g))
        if not len(g):
            a = _at(d[d.team == opp], mm, opp, theirs_venue)
            res["they_usual"] = int(round(float(a.runs.median()))) if len(a) else None
            res["they_usual_n"] = int(len(a))
        meet = _at(meet_all, mm, me, venue).sort_values("date", ascending=False)
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
