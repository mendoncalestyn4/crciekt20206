"""Deeper looks at one player or one team.

Everything here works from the career tables (see loader.py) for a set of
match ids chosen with a Scope, so it follows the same section / season /
home-away filters as the rest of the site.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

MATCH_COLS = ["match_id", "date", "season", "section", "format", "home", "away", "winner", "result_type", "neutral",
              "batted_first", "result"]


def _with_match(df: pd.DataFrame, career, ids) -> pd.DataFrame:
    d = df[df.match_id.isin(ids)].merge(career.matches[MATCH_COLS], on="match_id", how="left")
    d["venue"] = np.where(d.neutral, "neutral", np.where(d.team == d.home, "home", "away"))
    d["outcome"] = np.select([d.winner == d.team, d.winner.isin(["", None]) | d.winner.isna()], ["won", "no win"], "lost")
    d.loc[(d.outcome == "no win") & (d.result_type == "draw"), "outcome"] = "drawn"
    d.loc[(d.outcome == "no win") & (d.result_type == "tie"), "outcome"] = "tied"
    d.loc[d.outcome == "no win", "outcome"] = "no result"
    return d


# --------------------------------------------------------------------------- #
# Batting innings with context
# --------------------------------------------------------------------------- #


def entry_scores(career) -> pd.DataFrame:
    """Score and wickets down when each batter walked in.

    Openers (positions 1 and 2) come in at 0 for 0; the batter at position p
    arrives when wicket p-2 falls, and the fall of wickets gives that score."""
    fow = career.fow.set_index(["match_id", "innings_no", "wicket"]).score
    b = career.batting[["match_id", "innings_no", "position"]].copy()
    wk = (b.position - 2).clip(lower=0)
    keys = list(zip(b.match_id, b.innings_no, wk))
    b["came_in_wickets"] = wk
    b["came_in_score"] = [0 if w == 0 else fow.get(k, np.nan) for k, w in zip(keys, wk)]
    return b


def batting_innings(career, ids, player: str) -> pd.DataFrame:
    """Every innings a player batted in, oldest first, with match context."""
    bat = career.batting[(career.batting.player == player) & career.batting.did_bat]
    d = _with_match(bat, career, ids)
    e = entry_scores(career)
    d = d.merge(e, on=["match_id", "innings_no", "position"], how="left")
    d["batting_first"] = d.team == d.batted_first
    return d.sort_values(["date", "innings_no"]).reset_index(drop=True)


def bowling_spells(career, ids, player: str) -> pd.DataFrame:
    w = career.bowling[(career.bowling.player == player) & (career.bowling.balls > 0)]
    d = _with_match(w, career, ids)
    d["batting_first"] = d.team == d.batted_first  # did the bowler's side bat first
    return d.sort_values(["date", "innings_no"]).reset_index(drop=True)


def split_batting(inns: pd.DataFrame, by: str) -> pd.DataFrame:
    """Batting figures split by a column (venue, outcome, batting_first, opposition, season, section, ...)."""
    if inns.empty:
        return pd.DataFrame(columns=[by, "innings", "runs", "outs", "average", "strike_rate", "fifty_plus"])
    g = inns.assign(fp=inns.runs >= 50).groupby(by)
    t = g.agg(innings=("runs", "size"), runs=("runs", "sum"), balls=("balls", "sum"), outs=("out", "sum"),
              fifty_plus=("fp", "sum"), high=("runs", "max")).reset_index()
    t["average"] = np.where(t.outs > 0, t.runs / t.outs.replace(0, np.nan), np.nan)
    t["strike_rate"] = np.where(t.balls > 0, t.runs / t.balls.replace(0, np.nan) * 100, np.nan)
    return t


def split_bowling(spells: pd.DataFrame, by: str) -> pd.DataFrame:
    if spells.empty:
        return pd.DataFrame(columns=[by, "innings", "wickets", "runs", "balls", "average", "economy", "strike_rate"])
    t = spells.groupby(by).agg(innings=("balls", "size"), balls=("balls", "sum"), runs=("runs", "sum"),
                               wickets=("wickets", "sum")).reset_index()
    t["average"] = np.where(t.wickets > 0, t.runs / t.wickets.replace(0, np.nan), np.nan)
    t["economy"] = t.runs / t.balls * 6
    t["strike_rate"] = np.where(t.wickets > 0, t.balls / t.wickets.replace(0, np.nan), np.nan)
    return t


def how_out(inns: pd.DataFrame) -> pd.Series:
    out = inns[inns.out]
    return out.how_out.value_counts()


def consistency(inns: pd.DataFrame, fmt_kind: str) -> dict:
    """How reliably a batter gets going: share of innings past a 'decent score'
    (20 in T20, 30 in one-day and multi-day), and how often 50s become 100s."""
    if inns.empty:
        return {}
    bar = 20 if fmt_kind == "t20" else 30
    fifties = int(((inns.runs >= 50) & (inns.runs < 100)).sum())
    hundreds = int((inns.runs >= 100).sum())
    return {
        "bar": bar,
        "past_bar_pct": float((inns.runs >= bar).mean() * 100),
        "single_figures_pct": float(((inns.runs < 10) & inns.out).mean() * 100),
        "golden_ducks": int(((inns.runs == 0) & (inns.balls <= 1) & inns.out).sum()),
        "conversion_pct": float(hundreds / (fifties + hundreds) * 100) if fifties + hundreds else np.nan,
    }


# --------------------------------------------------------------------------- #
# Match-ups
# --------------------------------------------------------------------------- #


def nemesis(career, ids, player: str) -> pd.DataFrame:
    """Bowlers who have dismissed this batter, most often first."""
    b = career.batting[career.batting.match_id.isin(ids) & (career.batting.player == player) & career.batting.out
                       & (career.batting.bowler != "")]
    bowlers = set(career.bowling.player)
    b = b[b.bowler.isin(bowlers)]
    return (b.groupby("bowler").size().rename("dismissals").sort_values(ascending=False).reset_index()
            .rename(columns={"bowler": "bowler"}))


def bunnies(career, ids, player: str) -> pd.DataFrame:
    """Batters this bowler has dismissed, most often first, with their batting position."""
    b = career.batting[career.batting.match_id.isin(ids) & (career.batting.bowler == player) & career.batting.out]
    return (b.groupby("player").agg(dismissals=("runs", "size"), usual_position=("position", "median"))
            .sort_values("dismissals", ascending=False).reset_index())


def wicket_quality(career, ids, player: str) -> dict:
    """Which part of the order a bowler's wickets come from."""
    b = career.batting[career.batting.match_id.isin(ids) & (career.batting.bowler == player) & career.batting.out]
    if b.empty:
        return {}
    pos = b.position
    return {"top_order": int((pos <= 3).sum()), "middle_order": int(((pos >= 4) & (pos <= 7)).sum()),
            "tail": int((pos >= 8).sum()), "total": int(len(b)),
            "top_seven_pct": float((pos <= 7).mean() * 100)}


def wicket_types(career, ids, player: str) -> pd.Series:
    b = career.batting[career.batting.match_id.isin(ids) & (career.batting.bowler == player) & career.batting.out]
    return b.how_out.value_counts()


# --------------------------------------------------------------------------- #
# Teams
# --------------------------------------------------------------------------- #


def team_matches(career, ids, team: str) -> pd.DataFrame:
    m = career.matches[career.matches.match_id.isin(ids) & ((career.matches.home == team) | (career.matches.away == team))]
    m = m.sort_values(["date", "match_id"]).copy()
    m["opponent"] = np.where(m.home == team, m.away, m.home)
    m["venue"] = np.where(m.neutral, "neutral", np.where(m.home == team, "home", "away"))
    m["outcome"] = np.select([m.winner == team, m.winner == m.opponent, m.result_type == "draw", m.result_type == "tie"],
                             ["W", "L", "D", "T"], "NR")
    inn = career.innings[career.innings.match_id.isin(m.match_id)]
    for side, label in ((True, "for"), (False, "against")):
        x = inn[(inn.team == team) == side].groupby("match_id")
        m[f"runs_{label}"] = m.match_id.map(x.runs.sum())
        m[f"wkts_{label}"] = m.match_id.map(x.wickets.sum())
    return m.reset_index(drop=True)


def team_record(tm: pd.DataFrame) -> dict:
    n = len(tm)
    c = tm.outcome.value_counts()
    rf, ra = tm.runs_for.sum(), tm.runs_against.sum()
    wf, wa = tm.wkts_for.sum(), tm.wkts_against.sum()
    return {"played": n, "won": int(c.get("W", 0)), "lost": int(c.get("L", 0)), "drawn": int(c.get("D", 0)),
            "tied": int(c.get("T", 0)), "no_result": int(c.get("NR", 0)),
            "win_pct": float(c.get("W", 0) / n * 100) if n else np.nan,
            "runs_per_wicket_for": rf / wf if wf else np.nan, "runs_per_wicket_against": ra / wa if wa else np.nan}


def streaks(outcomes: list[str]) -> dict:
    """Current streak and the longest winning / losing runs."""
    best_w = best_l = run = 0
    last = None
    for o in outcomes:
        run = run + 1 if o == last else 1
        last = o
        if o == "W":
            best_w = max(best_w, run)
        if o == "L":
            best_l = max(best_l, run)
    current = (last, run) if last else (None, 0)
    return {"current": current, "longest_win": best_w, "longest_loss": best_l, "last5": outcomes[-5:]}


def opening_partnerships(career, ids, team: str) -> pd.DataFrame:
    """Opening stands with the two openers' names (positions 1 and 2)."""
    inn = career.innings[career.innings.match_id.isin(ids) & (career.innings.team == team)]
    bat = career.batting.set_index(["match_id", "innings_no", "position"]).player
    fow1 = career.fow[career.fow.wicket == 1].set_index(["match_id", "innings_no"]).score
    rows = []
    for _, r in inn.iterrows():
        k = (r.match_id, r.innings_no)
        stand = fow1.get(k, r.runs)  # no wicket fell: the whole innings was the opening stand
        unbroken = k not in fow1.index
        a, b = bat.get((*k, 1), ""), bat.get((*k, 2), "")
        rows.append(dict(match_id=r.match_id, innings_no=r.innings_no, pair=" & ".join(sorted([a, b])), runs=int(stand),
                         unbroken=unbroken))
    d = pd.DataFrame(rows, columns=["match_id", "innings_no", "pair", "runs", "unbroken"])
    return d.merge(career.matches[["match_id", "date", "home", "away", "section"]], on="match_id")


def partnership_by_wicket(career, ids, team: str) -> pd.DataFrame:
    """Average stand for each wicket (1st, 2nd, …) from the fall of wickets."""
    rows = []
    inn = career.innings[career.innings.match_id.isin(ids) & (career.innings.team == team)]
    fow = career.fow.groupby(["match_id", "innings_no"])
    for _, r in inn.iterrows():
        try:
            f = fow.get_group((r.match_id, r.innings_no)).sort_values("wicket")
        except KeyError:
            f = pd.DataFrame(columns=["wicket", "score"])
        prev = 0
        for w, s in zip(f.wicket, f.score):
            rows.append(dict(wicket=int(w), runs=int(s - prev)))
            prev = s
    d = pd.DataFrame(rows, columns=["wicket", "runs"])
    return d.groupby("wicket").runs.agg(["mean", "size", "max"]).reset_index().rename(
        columns={"mean": "average", "size": "stands", "max": "best"})


def collapses(career, ids, team: str, wickets: int = 4, runs: int = 30) -> pd.DataFrame:
    """Innings where the team lost `wickets` or more for `runs` or fewer (the
    longest such run in each innings)."""
    inn = career.innings[career.innings.match_id.isin(ids) & (career.innings.team == team)]
    fow = career.fow.groupby(["match_id", "innings_no"])
    out = []
    for _, r in inn.iterrows():
        try:
            f = fow.get_group((r.match_id, r.innings_no)).sort_values("wicket")
        except KeyError:
            continue
        scores = [0] + list(f.score)  # score when each wicket fell, with the start of the innings
        best = None
        for i in range(len(scores)):
            for j in range(len(scores) - 1, i, -1):
                if j - i >= wickets and scores[j] - scores[i] <= runs:
                    if best is None or (j - i, -(scores[j] - scores[i])) > (best[1] - best[0], -(best[3] - best[2])):
                        best = (i, j, scores[i], scores[j])
                    break
        if best:
            i, j, a, b = best
            out.append(dict(match_id=r.match_id, innings_no=r.innings_no, from_score=f"{a}/{i}", to_score=f"{b}/{j}",
                            wickets=j - i, runs=b - a, total=f"{r.runs}/{r.wickets}" if not r.all_out else str(r.runs)))
    d = pd.DataFrame(out, columns=["match_id", "innings_no", "from_score", "to_score", "wickets", "runs", "total"])
    return d.merge(career.matches[["match_id", "date", "home", "away", "section"]], on="match_id")


def batting_depth(career, ids, team: str) -> pd.DataFrame:
    """Share of the team's bat runs from the top order (1-3), middle (4-7) and tail (8-11)."""
    b = career.batting[career.batting.match_id.isin(ids) & (career.batting.team == team) & career.batting.did_bat]
    group = pd.cut(b.position, [0, 3, 7, 11], labels=["Top order (1-3)", "Middle order (4-7)", "Tail (8-11)"])
    t = b.groupby(group, observed=False).runs.sum()
    return pd.DataFrame({"group": t.index.astype(str), "runs": t.values,
                         "share": (t / t.sum() * 100).values if t.sum() else 0})


def team_strength(career, ids) -> dict[str, float]:
    """Win % of every team in the selected matches (used to split opponents
    into the stronger and weaker half)."""
    m = career.matches[career.matches.match_id.isin(ids)]
    out = {}
    for team in set(m.home) | set(m.away):
        mine = m[(m.home == team) | (m.away == team)]
        out[team] = float((mine.winner == team).mean() * 100) if len(mine) else 0.0
    return out


def opposition_strength(inns: pd.DataFrame, strength: dict[str, float]) -> pd.Series:
    """'Stronger half' / 'Weaker half' for each row's opposition."""
    if not strength:
        return pd.Series([], dtype=str)
    median = float(np.median(list(strength.values())))
    return inns.opposition.map(lambda t: "Stronger half" if strength.get(t, 0) > median else "Weaker half")
