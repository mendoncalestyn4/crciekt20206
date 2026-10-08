"""Section-wide questions: is this total enough, home advantage, how the game
changes from season to season, and players who have broken out."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .stats import Scope, kind_of, player_tables

BUCKET = {"t20": 10, "one": 20, "multi": 50}


def first_innings(career, ids) -> pd.DataFrame:
    """The first innings of every finished match with how the side batting first got on (a game shortened by rain
    is left out: its first innings wasn't made over the full overs, or the result came from the rain rule)."""
    m = career.matches[career.matches.match_id.isin(ids) & (career.matches.result_type != "no result")]
    if "rain" in m:
        m = m[~m.rain.astype(bool)]
    inn = career.innings[career.innings.match_id.isin(m.match_id) & (career.innings.innings_no == 1)]
    d = inn[["match_id", "team", "runs", "wickets", "all_out"]].merge(
        m[["match_id", "winner", "result_type", "tiebreak_winner", "format"]], on="match_id")
    d["outcome"] = np.select([d.winner == d.team, d.winner != "", d.result_type == "draw"], ["won", "lost", "drawn"], "tied")
    return d


def total_enough(career, ids) -> tuple[pd.DataFrame, int]:
    """Win % batting first, by first-innings score band."""
    d = first_innings(career, ids)
    size = BUCKET[kind_of(career.matches[career.matches.match_id.isin(ids)])]
    cols = ["band", "low", "matches", "won", "lost", "drawn", "tied", "win_pct"]
    if d.empty:
        return pd.DataFrame(columns=cols), size
    d["low"] = (d.runs // size) * size
    g = d.groupby("low").outcome.value_counts().unstack(fill_value=0)
    for c in ("won", "lost", "drawn", "tied"):
        if c not in g:
            g[c] = 0
    g["matches"] = g[["won", "lost", "drawn", "tied"]].sum(axis=1)
    g["win_pct"] = g.won / g.matches * 100
    g = g.reset_index()
    g["band"] = [f"{lo}–{lo + size - 1}" for lo in g.low]
    return g[cols], size


def chance_with(career, ids, score: int) -> dict:
    """How sides batting first did with `score` or more, and with less."""
    d = first_innings(career, ids)
    hi, lo = d[d.runs >= score], d[d.runs < score]
    f = lambda x: dict(matches=len(x), won=int((x.outcome == "won").sum()),  # noqa: E731
                       pct=float((x.outcome == "won").mean() * 100) if len(x) else np.nan)
    return {"at_least": f(hi), "below": f(lo)}


def home_advantage(career) -> pd.DataFrame:
    """Home and away wins in every section played at home grounds."""
    m = career.matches[~career.matches.neutral & (career.matches.result_type != "no result")]
    rows = []
    for sec, g in m.groupby("section"):
        home, away = int((g.winner == g.home).sum()), int((g.winner == g.away).sum())
        rows.append(dict(section=sec, matches=len(g), home_wins=home, away_wins=away, other=len(g) - home - away,
                         home_pct=home / len(g) * 100, away_pct=away / len(g) * 100))
    return pd.DataFrame(rows, columns=["section", "matches", "home_wins", "away_wins", "other", "home_pct", "away_pct"]) \
        .sort_values("matches", ascending=False)


def by_season(career, section: str) -> pd.DataFrame:
    """Scoring in each season of one section."""
    m = career.matches[career.matches.section == section]
    rows = []
    for season, g in m.groupby("season"):
        inn = career.innings[career.innings.match_id.isin(g.match_id)]
        bat = career.batting[career.batting.match_id.isin(g.match_id) & career.batting.did_bat]
        fi = first_innings(career, g.match_id)
        decided = fi[fi.outcome.isin(["won", "lost"])]
        runs, wkts, balls = inn.runs.sum(), inn.wickets.sum(), inn.balls.sum()
        bdry = (4 * bat.fours + 6 * bat.sixes).sum()
        rows.append(dict(season=season, matches=len(g), runs_per_wicket=runs / wkts if wkts else np.nan,
                         run_rate=runs / balls * 6 if balls else np.nan, sixes_per_match=bat.sixes.sum() / len(g),
                         boundary_pct=bdry / bat.runs.sum() * 100 if bat.runs.sum() else np.nan,
                         first_innings_avg=fi.runs.mean() if len(fi) else np.nan,
                         bat_first_win_pct=(decided.outcome == "won").mean() * 100 if len(decided) else np.nan))
    return pd.DataFrame(rows, columns=["season", "matches", "runs_per_wicket", "run_rate", "sixes_per_match", "boundary_pct",
                                       "first_innings_avg", "bat_first_win_pct"]).sort_values("season")


def breakouts(career, section: str, season: str, min_innings: int = 5) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Players whose season was much better than their earlier seasons in the
    same section, per innings: runs above average (batters) and runs saved
    (bowlers).  Both measures use each season's own average, so a high-scoring
    season doesn't flatter everyone."""
    m = career.matches[career.matches.section == section]
    earlier = sorted(s for s in m.season.unique() if s < season)
    if not earlier:
        return pd.DataFrame(), pd.DataFrame()
    now_b, now_w, _, _ = player_tables(career, Scope(sections=[section], seasons=[season]))
    parts_b, parts_w = [], []
    for s in earlier:  # each earlier season measured against its own average, then added up
        b, w, _, _ = player_tables(career, Scope(sections=[section], seasons=[s]))
        parts_b.append(b[["player", "innings", "runs_above_average"]])
        parts_w.append(w[["player", "innings", "runs_saved"]])
    before_b = pd.concat(parts_b).groupby("player").sum()
    before_w = pd.concat(parts_w).groupby("player").sum()

    def compare(now, before, col, label):
        now = now[now.innings >= min_innings].set_index("player")
        before = before[before.innings >= min_innings]
        both = now.index.intersection(before.index)
        out = pd.DataFrame({"now_innings": now.innings[both], "now": now[col][both] / now.innings[both],
                            "before_innings": before.innings[both], "before": before[col][both] / before.innings[both]})
        out["jump"] = out.now - out.before
        out["teams"] = now.teams[both]
        return out.sort_values("jump", ascending=False).reset_index().rename(columns={"index": "player"})

    return compare(now_b, before_b, "runs_above_average", "bat"), compare(now_w, before_w, "runs_saved", "bowl")


def par_by_strength(career, ids) -> pd.DataFrame:
    """Win % batting first by first-innings score band (twice the usual band width),
    split by whether the side bowling first is in the stronger or weaker half
    (teams ranked by win % in these matches)."""
    from .analysis import team_strength
    d = first_innings(career, ids)
    if d.empty:
        return pd.DataFrame(columns=["band", "low", "stronger_n", "stronger_pct", "weaker_n", "weaker_pct"])
    m = career.matches.set_index("match_id")
    d["opponent"] = [m.away[a] if m.home[a] == t else m.home[a] for a, t in zip(d.match_id, d.team)]
    strength = team_strength(career, ids)
    med = float(np.median(list(strength.values()))) if strength else 0
    d["stronger"] = d.opponent.map(lambda t: strength.get(t, 0) > med)
    size = BUCKET[kind_of(career.matches[career.matches.match_id.isin(ids)])] * 2
    d["low"] = (d.runs // size) * size
    rows = []
    for lo, g in d.groupby("low"):
        a, b = g[g.stronger], g[~g.stronger]
        rows.append(dict(band=f"{lo}–{lo + size - 1}", low=lo, stronger_n=len(a),
                         stronger_pct=(a.outcome == "won").mean() * 100 if len(a) else np.nan,
                         weaker_n=len(b), weaker_pct=(b.outcome == "won").mean() * 100 if len(b) else np.nan))
    return pd.DataFrame(rows)
