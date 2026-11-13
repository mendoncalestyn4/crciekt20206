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
    arrives when wicket p-2 falls, and the fall of wickets gives that score.
    Kept with the career until its scorecards change (two seconds on a big one)."""
    stamp = (id(career.batting), len(career.batting), id(career.fow), len(career.fow))
    kept = getattr(career, "_entry_scores", None)
    if kept is None or kept[0] != stamp:
        kept = (stamp, _entry_scores(career))
        try:
            career._entry_scores = kept
        except AttributeError:
            pass
    return kept[1]


def _entry_scores(career) -> pd.DataFrame:
    fow = career.fow.drop_duplicates(["match_id", "innings_no", "wicket"]).set_index(["match_id", "innings_no", "wicket"]).score
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


def _overs(balls: int) -> str:
    return f"{balls // 6}" + (f".{balls % 6}" if balls % 6 else "")


def batting_record(career, ids, player: str, by: str = "section") -> pd.DataFrame:
    """A player's standard batting figures, one row per section (or season).
    The columns are the same whatever the format, so every section reads alike."""
    b = career.batting[career.batting.match_id.isin(ids) & (career.batting.player == player)]
    b = b.merge(career.matches[["match_id", "section", "season"]], on="match_id")
    f = career.fielding[career.fielding.match_id.isin(ids) & career.fielding.resolved & (career.fielding.player == player)]
    f = f.merge(career.matches[["match_id", "section", "season"]], on="match_id")
    rows = []
    for key, g in b.groupby(by, sort=False):
        d = g[g.did_bat]
        outs = int(d.out.sum())
        runs, balls = int(d.runs.sum()), int(d.balls.sum())
        top = d.assign(_r=d.runs * 2 + ~d.out).sort_values("_r").tail(1)
        mine_f = f[f[by] == key]
        rows.append({by: key, "Mat": g.match_id.nunique(), "Inns": len(d), "NO": len(d) - outs, "Runs": runs,
                     "HS": f"{int(top.runs.iloc[0])}{'' if top.out.iloc[0] else '*'}" if len(d) else "–",
                     "Avg": runs / outs if outs else np.nan, "BF": balls, "SR": runs / balls * 100 if balls else np.nan,
                     "100": int((d.runs >= 100).sum()), "50": int(((d.runs >= 50) & (d.runs < 100)).sum()),
                     "0": int(((d.runs == 0) & d.out).sum()), "4s": int(d.fours.sum()), "6s": int(d.sixes.sum()),
                     "Ct": int((mine_f.kind == "caught").sum()), "St": int((mine_f.kind == "stumped").sum())})
    cols = [by, "Mat", "Inns", "NO", "Runs", "HS", "Avg", "BF", "SR", "100", "50", "0", "4s", "6s", "Ct", "St"]
    return pd.DataFrame(rows, columns=cols)


def bowling_record(career, ids, player: str, by: str = "section") -> pd.DataFrame:
    """A player's standard bowling figures, one row per section (or season),
    with the same columns in every format. Maidens are only printed on
    longer-format cards and dot balls only on T20 cards, so the other one
    shows as blank."""
    mat = career.matches[["match_id", "section", "season"]]
    appeared = career.batting[career.batting.match_id.isin(ids) & (career.batting.player == player)].merge(mat, on="match_id")
    w = career.bowling[career.bowling.match_id.isin(ids) & (career.bowling.player == player)].merge(mat, on="match_id")
    rows = []
    for key, g in w.groupby(by, sort=False):
        d = g[g.balls > 0]
        if d.empty:
            continue
        balls, runs, wkts = int(d.balls.sum()), int(d.runs.sum()), int(d.wickets.sum())
        best = d.assign(_k=d.wickets * 1000 - d.runs).sort_values("_k").iloc[-1]
        bm = d.groupby("match_id")[["wickets", "runs"]].sum().assign(_k=lambda x: x.wickets * 1000 - x.runs)
        bm_row = bm.sort_values("_k").iloc[-1]
        mdn = d.maidens.dropna()
        dots = d.dots.dropna()
        rows.append({by: key, "Mat": appeared[appeared[by] == key].match_id.nunique(), "Inns": len(d),
                     "Overs": _overs(balls), "Balls": balls,
                     "Mdns": int(mdn.sum()) if len(mdn) else np.nan, "Dots": int(dots.sum()) if len(dots) else np.nan,
                     "Runs": runs, "Wkts": wkts, "BBI": f"{int(best.wickets)}/{int(best.runs)}",
                     "BBM": f"{int(bm_row.wickets)}/{int(bm_row.runs)}",
                     "Avg": runs / wkts if wkts else np.nan, "Econ": runs / balls * 6,
                     "SR": balls / wkts if wkts else np.nan,
                     "4w": int(((d.wickets >= 4) & (d.wickets < 5)).sum()), "5w": int((d.wickets >= 5).sum()),
                     "10m": int((bm.wickets >= 10).sum())})
    cols = [by, "Mat", "Inns", "Overs", "Balls", "Mdns", "Dots", "Runs", "Wkts", "BBI", "BBM", "Avg", "Econ", "SR", "4w", "5w", "10m"]
    return pd.DataFrame(rows, columns=cols)


def how_out(inns: pd.DataFrame) -> pd.Series:
    out = inns[inns.out]
    return out.how_out.value_counts()


def consistency(inns: pd.DataFrame, fmt_kind: str) -> dict:
    """How reliably a batter gets going: share of innings past a 'decent score'
    (20 in T20, 30 in one-day, 50 in multi-day), and how often 50s become 100s."""
    from .stats import bars_for
    if inns.empty:
        return {}
    bar = bars_for(fmt_kind)["decent"]
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
    """The team's stands for each wicket (1st, 2nd, …): how many, the average and the best, unbroken stands at the
    end of an innings included (see partnerships.by_wicket)."""
    from . import partnerships as P
    s = P.stands(career, ids)
    return P.by_wicket(s[s.team == team])


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
    """Share of the team's bat runs from the top order (1-3), middle (4-7) and tail (8-11); no share at all (not 0%)
    for a team without a run here, so it never pulls down an average of teams."""
    b = career.batting[career.batting.match_id.isin(ids) & (career.batting.team == team) & career.batting.did_bat]
    group = pd.cut(b.position, [0, 3, 7, 11], labels=["Top order (1-3)", "Middle order (4-7)", "Tail (8-11)"])
    t = b.groupby(group, observed=False).runs.sum()
    return pd.DataFrame({"group": t.index.astype(str), "runs": t.values,
                         "share": (t / t.sum() * 100).values if t.sum() else np.nan})


STRENGTH_PRIOR = 4  # games: every side starts as if it had won 2 and lost 2


def team_strength(career, ids) -> dict[str, float]:
    """Win % of every team in the selected matches (used to split opponents into the stronger and weaker half),
    pulled towards 50% as if each side had already won 2 and lost 2, so one win in one game doesn't make a side
    strong: 1 from 1 is 60%, 9 from 12 is 69%."""
    m = career.matches[career.matches.match_id.isin(ids)]
    out = {}
    for team in set(m.home) | set(m.away):
        mine = m[(m.home == team) | (m.away == team)]
        out[team] = float(((mine.winner == team).sum() + STRENGTH_PRIOR / 2) / (len(mine) + STRENGTH_PRIOR) * 100)
    return out


def opposition_strength(inns: pd.DataFrame, strength: dict[str, float]) -> pd.Series:
    """'Stronger half' / 'Weaker half' for each row's opposition."""
    if not strength:
        return pd.Series([], dtype=str)
    median = float(np.median(list(strength.values())))
    return inns.opposition.map(lambda t: "Stronger half" if strength.get(t, 0) > median else "Weaker half")


def keepers(career, ids, team: str | None = None) -> pd.DataFrame:
    """Players who have made a stumping, i.e. wicketkeepers. The scorecards
    don't mark the keeper, so a stumping is the only reliable sign."""
    f = career.fielding[career.fielding.match_id.isin(ids) & career.fielding.resolved & (career.fielding.kind == "stumped")]
    if team:
        f = f[f.team == team]
    return (f.groupby(["player", "team"]).size().rename("stumpings").reset_index()
            .sort_values("stumpings", ascending=False).reset_index(drop=True))


def position_record(career, ids, player: str) -> pd.DataFrame:
    """A player's batting at each position group, next to the average batter
    at that position in the same matches."""
    from .stats import POSITION_GROUPS
    b = career.batting[career.batting.match_id.isin(ids) & career.batting.did_bat]
    rows = []
    for label, pos in POSITION_GROUPS.items():
        here = b[b.position.isin(pos)]
        me = here[here.player == player]
        if me.empty:
            continue
        outs, all_outs = int(me.out.sum()), int(here.out.sum())
        rows.append(dict(group=label, innings=len(me), runs=int(me.runs.sum()), outs=outs,
                         average=me.runs.sum() / outs if outs else np.nan,
                         strike_rate=me.runs.sum() / me.balls.sum() * 100 if me.balls.sum() else np.nan,
                         section_average=here.runs.sum() / all_outs if all_outs else np.nan))
    return pd.DataFrame(rows, columns=["group", "innings", "runs", "outs", "average", "strike_rate", "section_average"])


# balls bowled per match that make someone "a bowler" in each format
BOWLER_BALLS = {"t20": 9, "one": 24, "multi": 60}


def role_labels(career, ids, kind: str, min_matches: int = 3) -> pd.DataFrame:
    """A role for each player in the selected matches, from what they actually
    did there, plus a few style tags measured against the other players.

    role: Opener / Top order / Middle order / Finisher (limited overs) or Lower order / Tail
          for batters; Bowler; All-rounder; with Wicketkeeper for anyone who made a stumping."""
    cols = ["player", "role", "tags", "usual_position", "matches"]
    bat = career.batting[career.batting.match_id.isin(ids)]
    if bat.empty:
        return pd.DataFrame(columns=cols)
    bowl = career.bowling[career.bowling.match_id.isin(ids)]
    batted = bat[bat.did_bat]
    matches = bat.groupby("player").match_id.nunique()
    pos = bat.groupby("player").position.median()  # where they're listed, batting or not
    b = batted.groupby("player").agg(inns=("runs", "size"), runs=("runs", "sum"), balls=("balls", "sum"), outs=("out", "sum"),
                                     bdry=("fours", "sum"), six=("sixes", "sum"))
    b["bdry_runs"] = 4 * b.bdry + 6 * b.six
    w = bowl[bowl.balls > 0].groupby("player").agg(spells=("balls", "size"), balls=("balls", "sum"), runs=("runs", "sum"),
                                                   wkts=("wickets", "sum"))
    top7 = batted[batted.position <= 7]
    per_inns_top7 = top7.runs.sum() / len(top7) if len(top7) else 0
    stumpers = set(career.fielding[career.fielding.match_id.isin(ids) & career.fielding.resolved
                                   & (career.fielding.kind == "stumped")].player)
    limited = kind != "multi"
    # style thresholds among regulars
    reg_b = b[b.inns >= 5].copy()
    reg_b["avg"] = reg_b.runs / reg_b.outs.replace(0, np.nan)
    reg_b["sr"] = reg_b.runs / reg_b.balls.replace(0, np.nan) * 100
    reg_b["bpct"] = reg_b.bdry_runs / reg_b.runs.replace(0, np.nan)
    reg_w = w[w.spells >= 5].copy()
    reg_w["sr"] = reg_w.balls / reg_w.wkts.replace(0, np.nan)
    reg_w["econ"] = reg_w.runs / reg_w.balls * 6
    q = lambda s, p: s.quantile(p) if s.notna().any() else np.nan  # noqa: E731
    rows = []
    for p, n in matches.items():
        if n < min_matches:
            continue
        up = float(pos.get(p, 11))
        bowls = p in w.index and w.balls[p] / n >= BOWLER_BALLS[kind]
        rpi = b.runs[p] / b.inns[p] if p in b.index and b.inns[p] else 0
        bats = up <= 7.5 and rpi >= 0.6 * per_inns_top7
        if bowls and bats:
            role = "All-rounder"
        elif bowls:
            role = "Bowler"
        elif up <= 2.5:  # opened in at least half their games
            role = "Opener"
        elif up <= 3:
            role = "Top order"
        elif up <= 5:
            role = "Middle order"
        elif up <= 7:
            role = "Finisher" if limited else "Lower order"
        else:
            role = "Tail"
        tags = []
        if p in stumpers:
            tags.append("Wicketkeeper")
        if p in reg_b.index:
            r = reg_b.loc[p]
            if limited and r.bpct >= q(reg_b.bpct, 0.75) and r.sr >= q(reg_b.sr, 0.5):
                tags.append("Big hitter")
            if r.avg >= q(reg_b.avg, 0.75) and r.sr < q(reg_b.sr, 0.5):
                tags.append("Anchor")
        if p in reg_w.index:
            r = reg_w.loc[p]
            if r.sr <= q(reg_w.sr, 0.25):
                tags.append("Strike bowler")
            if limited and r.econ <= q(reg_w.econ, 0.25):
                tags.append("Economist")
        rows.append(dict(player=p, role=role, tags=tags, usual_position=up, matches=int(n)))
    return pd.DataFrame(rows, columns=cols)


BALL_QUOTA = {"T20": 120, "T20I": 120, "The Hundred": 100, "ODI": 300, "List A": 300}
NRR_COLUMNS = ["match_id", "innings_no", "team", "opposition", "runs", "balls"]


def nrr_innings(career, ids) -> pd.DataFrame:
    """Each limited-overs innings as it counts for net run rate, by the ICC's rules as far as a scorecard shows them:
    a game with no result doesn't count; a side bowled out is charged its full overs (in a game shortened by rain,
    the overs it was allowed); and in a game decided by the rain rule, the side batting first is credited with the
    rain-rule par score (the other side's runs and the margin) off the overs the other side faced or was allowed.
    Where a chase was won against a revised target the scorecard doesn't give that target, so both sides keep
    their own runs and overs."""
    m = career.matches[career.matches.match_id.isin(ids) & career.matches.format.isin(list(BALL_QUOTA))
                       & (career.matches.result_type != "no result")]
    if m.empty:
        return pd.DataFrame(columns=NRR_COLUMNS)
    inn = career.innings[career.innings.match_id.isin(m.match_id)].sort_values(["match_id", "innings_no"])
    bw = career.bowling[career.bowling.match_id.isin(m.match_id)]
    most = bw.groupby(["match_id", "innings_no"]).balls.max()  # the most balls any one bowler sent down
    rain = m.set_index("match_id")["rain"] if "rain" in m else pd.Series(False, index=m.match_id)
    info = m.set_index("match_id")
    rows = []
    for mid, g in inn.groupby("match_id", sort=False):
        r = info.loc[mid]
        quota = BALL_QUOTA[r.format]
        g = list(g.itertuples())
        shortened = bool(rain.get(mid, False))

        def cut_short(i):  # stopped short of its overs, not bowled out, and not a chase that got there
            return (not i.all_out and i.balls < quota
                    and not (i is g[-1] and r.result_type == "win" and r.winner == i.team))

        def allowed(i):
            if not i.all_out:
                return int(i.balls)
            if not shortened:
                return quota
            others = [o for o in g if o is not i and cut_short(o)]
            if others:  # a game shortened for both sides
                return int(others[0].balls)
            mx = most.get((mid, i.innings_no), np.nan)
            return int(max(i.balls, min(quota, 5 * mx))) if mx == mx and mx > 0 else quota

        figs = {i.innings_no: [int(i.runs), allowed(i)] for i in g}
        if (len(g) == 2 and str(r.margin_note).startswith("Rain-affected") and r.result_type == "win"
                and r.margin_runs == r.margin_runs):
            t1, t2 = g
            par = int(t2.runs) + int(r.margin_runs) if r.winner == t1.team else int(t2.runs) - int(r.margin_runs)
            figs[t1.innings_no] = [par, allowed(t2)]
        for i in g:
            rows.append((mid, i.innings_no, i.team, i.opposition, *figs[i.innings_no]))
    return pd.DataFrame(rows, columns=NRR_COLUMNS)


def team_table(career, ids, venue: str = "all") -> pd.DataFrame:
    """One row per team in the selected matches: results, runs per wicket,
    run rates and (limited overs) net run rate. `venue` = all / home / away,
    from each team's own point of view."""
    m = career.matches[career.matches.match_id.isin(ids)]
    inn = career.innings[career.innings.match_id.isin(ids)].merge(m[["match_id", "format", "home", "away", "neutral"]], on="match_id")
    nrr_inn = nrr_innings(career, ids)
    rows = []
    for team in sorted(set(m.home) | set(m.away)):
        mine = m[(m.home == team) | (m.away == team)]
        if venue == "home":
            mine = mine[(mine.home == team) & ~mine.neutral]
        elif venue == "away":
            mine = mine[(mine.away == team) & ~mine.neutral]
        if mine.empty:
            continue
        i = inn[inn.match_id.isin(mine.match_id)]
        bat, bowl = i[i.team == team], i[i.opposition == team]
        # a first innings is only comparable when the game ran its course (not shortened by rain, not abandoned)
        whole = mine[(mine.result_type != "no result") & ~mine.get("rain", pd.Series(False, index=mine.index))]
        first = bat[(bat.innings_no == 1) & bat.match_id.isin(whole.match_id)]
        q = nrr_inn[nrr_inn.match_id.isin(mine.match_id)]
        nrr_for, nrr_against = q[q.team == team], q[q.opposition == team]
        limited = mine.format.isin(list(BALL_QUOTA)).all()
        n = len(mine)
        rows.append(dict(
            team=team, played=n, won=int((mine.winner == team).sum()),
            lost=int(((mine.winner != team) & (mine.winner != "")).sum()),
            drawn=int((mine.result_type == "draw").sum()), tied=int((mine.result_type == "tie").sum()),
            win_pct=float((mine.winner == team).mean() * 100),
            rpw_for=bat.runs.sum() / max(bat.wickets.sum(), 1), rpw_against=bowl.runs.sum() / max(bowl.wickets.sum(), 1),
            rr_for=bat.runs.sum() / max(bat.balls.sum(), 1) * 6, rr_against=bowl.runs.sum() / max(bowl.balls.sum(), 1) * 6,
            nrr=(nrr_for.runs.sum() / max(nrr_for.balls.sum(), 1) - nrr_against.runs.sum() / max(nrr_against.balls.sum(), 1)) * 6
            if limited else np.nan,
            first_innings_avg=first.runs.mean() if len(first) else np.nan,
            wkts_per_match=bowl.wickets.sum() / n))
    return pd.DataFrame(rows, columns=["team", "played", "won", "lost", "drawn", "tied", "win_pct", "rpw_for", "rpw_against",
                                       "rr_for", "rr_against", "nrr", "first_innings_avg", "wkts_per_match"])
