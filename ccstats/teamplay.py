"""How teams win: batting first or chasing, close games, targets, knockouts,
opponents, the league race, starts, timing, bouncing back, revenge, series
situations and Test-match innings.

Everything works on a set of match ids (one section, usually) and gives each
team's figures next to the average of all teams in the same matches.  Win % in
limited-overs cricket leaves ties and no-results out (won / (won + lost)); in
multi-day cricket draws count (won / (won + drawn + lost)), and the W/D/L are
always shown alongside.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .stats import KIND, bars_for

GAME_COLUMNS = ["match_id", "date", "section", "event", "season", "format", "kind", "knockout", "stage", "series_id",
                "team", "opponent", "venue", "outcome", "batted_first", "first_score", "target", "own_first",
                "margin_runs", "margin_wickets", "close", "super_over"]
BOOL_COLUMNS = ("knockout", "batted_first", "close", "super_over", "first", "decider", "dead", "complete",
                "series_won", "series_lost", "series_drawn")


def _typed(d: pd.DataFrame) -> pd.DataFrame:
    """Yes/no columns as real booleans, so filtering an empty frame still picks rows."""
    return d.astype({c: bool for c in BOOL_COLUMNS if c in d.columns})


OUTCOME_WORD = {"W": "won", "L": "lost", "D": "drawn", "T": "tied", "NR": "no result"}


def games(career, ids) -> pd.DataFrame:
    """One row per team per match: who they played, where, the result from their
    side, whether they batted first, the first-innings score (and the target in a
    one-innings game), and whether it was a close game (won by under 10 runs or by
    1-2 wickets, or tied).  In a game shortened by rain the first-innings score and
    target are left blank: they weren't made over the full overs, so they don't
    compare with other totals (lowest total defended, chasing by target size)."""
    m = career.matches[career.matches.match_id.isin(ids)]
    if m.empty:
        return _typed(pd.DataFrame(columns=GAME_COLUMNS))
    inn = career.innings[career.innings.match_id.isin(m.match_id)]
    first = inn[inn.innings_no == 1].set_index("match_id")
    own_first = inn[inn.team_innings == 1].set_index(["match_id", "team"]).runs
    rows = []
    for r in m.itertuples():
        kind = KIND.get(r.format, "t20")
        bat1 = first.team.get(r.match_id, r.batted_first or "")
        score1 = np.nan if getattr(r, "rain", False) else first.runs.get(r.match_id, np.nan)
        close_runs = bars_for(kind)["close_runs"]  # under 10 runs in a T20, 20 in one-day, 50 in a Test
        close = bool(r.result_type == "tie" or (pd.notna(r.margin_runs) and r.margin_runs < close_runs and not r.innings_win)
                     or (pd.notna(r.margin_wickets) and r.margin_wickets <= 2))
        for team, opp in ((r.home, r.away), (r.away, r.home)):
            venue = "neutral" if r.neutral else ("home" if team == r.home else "away")
            if r.winner == team:
                out = "W"
            elif r.winner == opp:
                out = "L"
            elif r.result_type == "draw":
                out = "D"
            elif r.result_type == "tie":
                out = "T"
            else:
                out = "NR"
            rows.append((r.match_id, r.date, r.section, r.event, r.season, r.format, kind, bool(r.knockout), r.stage,
                         r.series_id, team, opp, venue, out, bat1 == team, score1,
                         score1 + 1 if kind != "multi" and pd.notna(score1) else np.nan,
                         own_first.get((r.match_id, team), np.nan), r.margin_runs, r.margin_wickets,
                         close and out in ("W", "L", "T"), r.super_over != ""))
    return _typed(pd.DataFrame(rows, columns=GAME_COLUMNS)).sort_values(["date", "match_id", "team"]).reset_index(drop=True)


def record(g: pd.DataFrame) -> dict:
    """Played, W, D, L, T, NR and win % (see the module note) for some rows of `games`."""
    c = g.outcome.value_counts()
    w, lo, d, t, nr = (int(c.get(k, 0)) for k in ("W", "L", "D", "T", "NR"))
    multi = len(g) and (g.kind == "multi").mean() > 0.5
    decided = w + lo + (d if multi else 0)
    return dict(played=len(g), won=w, lost=lo, drawn=d, tied=t, no_result=nr,
                win_pct=w / decided * 100 if decided else np.nan, decided=decided)


def wdl(rec: dict) -> str:
    """'5–3' or '5–2–3' (W–D–L) with ties and no-results added when there are any."""
    s = f"{rec['won']}–{rec['drawn']}–{rec['lost']}" if rec["drawn"] else f"{rec['won']}–{rec['lost']}"
    extra = []
    if rec["tied"]:
        extra.append(f"{rec['tied']} tied")
    if rec["no_result"]:
        extra.append(f"{rec['no_result']} NR")
    return s + (f" ({', '.join(extra)})" if extra else "")


def is_multi(g: pd.DataFrame) -> bool:
    return bool(len(g)) and (g.kind == "multi").mean() > 0.5


# --------------------------------------------------------------------------- #
# 1 · batting first or chasing
# --------------------------------------------------------------------------- #


def bat_first_table(career, ids) -> tuple[pd.DataFrame, dict]:
    """(one row per team: record batting first and batting second, and the
    competition's average: how often the side batting first wins)."""
    g = games(career, ids)
    rows = []
    for team, t in g.groupby("team"):
        a, b = record(t[t.batted_first]), record(t[~t.batted_first])
        rows.append(dict(team=team, **{f"bf_{k}": v for k, v in a.items()}, **{f"ch_{k}": v for k, v in b.items()}))
    cols = ["team"] + [f"{p}_{k}" for p in ("bf", "ch") for k in ("played", "won", "lost", "drawn", "tied", "no_result",
                                                                  "win_pct", "decided")]
    t = pd.DataFrame(rows, columns=cols)
    first = g[g.batted_first]
    return t, dict(first=record(first), second=record(g[~g.batted_first]), multi=is_multi(g))


def first_or_chase(row: pd.Series, multi: bool) -> str:
    """'Batted first' / 'Chased' (or 'Batted second' in a multi-day game) for one row of `games`."""
    return "Batted first" if row.batted_first else ("Batted second" if multi else "Chased")


# --------------------------------------------------------------------------- #
# 2 · close games · 3 · targets · 5 · league v knockout · 6 · opponents
# --------------------------------------------------------------------------- #


def close_games(career, ids, team: str) -> dict:
    g = games(career, ids)
    t = g[g.team == team]
    return dict(close=record(t[t.close]), other=record(t[~t.close]), rows=t[t.close])


TARGET_EDGES = {"T20": [140, 160, 180, 200], "T20I": [140, 160, 180, 200], "The Hundred": [120, 140, 160, 180],
                "ODI": [220, 260, 300, 340], "List A": [220, 260, 300, 340]}
MULTI_EDGES = [150, 250, 350]


def _bucket(v: float, edges: list[int]) -> str:
    if pd.isna(v):
        return ""
    if v < edges[0]:
        return f"Under {edges[0]}"
    for a, b in zip(edges, edges[1:]):
        if a <= v < b:
            return f"{a}–{b - 1}"
    return f"{edges[-1]}+"


def target_buckets(career, ids, team: str = "") -> pd.DataFrame:
    """Chasing and defending by the size of the total.  One-innings games: the
    first-innings total.  Multi-day games: the target set in the fourth innings
    (chasing = batting last).  One row per bucket: chasing and defending records
    for `team` (or every team when empty)."""
    g = games(career, ids)
    if g.empty:
        return pd.DataFrame()
    multi = is_multi(g)
    if multi:
        inn = career.innings[career.innings.match_id.isin(g.match_id)]
        last = inn[inn.innings_no == 4].set_index("match_id")
        before = inn[inn.innings_no < 4].groupby(["match_id", "team"]).runs.sum()
        rows = []
        for r in g.itertuples():
            if r.match_id not in last.index:
                continue
            chaser = last.team[r.match_id]
            opp = r.opponent if chaser == r.team else r.team
            target = before.get((r.match_id, opp), 0) - before.get((r.match_id, chaser), 0) + 1
            rows.append((r.Index, chaser == r.team, target))
        side = pd.DataFrame(rows, columns=["i", "chasing", "size"]).set_index("i")
        g = g.loc[side.index].assign(chasing=side.chasing, size=side["size"])
        edges = MULTI_EDGES
    else:
        g = g.assign(chasing=~g.batted_first, size=g.first_score)
        fmt = g.format.mode().iloc[0]
        edges = TARGET_EDGES.get(fmt, [140, 160, 180, 200])
    if team:
        g = g[g.team == team]
    g = g.assign(bucket=[_bucket(v, edges) for v in g["size"]])
    order = [f"Under {edges[0]}"] + [f"{a}–{b - 1}" for a, b in zip(edges, edges[1:])] + [f"{edges[-1]}+"]
    out = []
    for b in order:
        x = g[g.bucket == b]
        c, d = record(x[x.chasing]), record(x[~x.chasing])
        out.append(dict(bucket=b, chase_played=c["played"], chase_won=c["won"], chase_lost=c["lost"],
                        chase_drawn=c["drawn"], chase_pct=c["win_pct"], defend_played=d["played"], defend_won=d["won"],
                        defend_lost=d["lost"], defend_drawn=d["drawn"], defend_pct=d["win_pct"]))
    return pd.DataFrame(out)


def stage_record(career, ids, team: str) -> pd.DataFrame:
    """League games, knockouts, and finals."""
    g = games(career, ids)
    t = g[g.team == team]
    rows = []
    for label, x in (("League games", t[~t.knockout]), ("Knockouts (all)", t[t.knockout]),
                     ("Finals", t[t.knockout & (t.stage == "Final")])):
        rows.append(dict(stage=label, **record(x)))
    return pd.DataFrame(rows)


def opponents(career, ids, team: str, min_games: int = 2) -> pd.DataFrame:
    """Record against every opponent (most games first); `favourite` and `bogey`
    mark the best and worst record among those met at least `min_games` times."""
    g = games(career, ids)
    t = g[g.team == team]
    rows = [dict(opponent=o, **record(x), last=x.date.max()) for o, x in t.groupby("opponent")]
    d = pd.DataFrame(rows, columns=["opponent", "played", "won", "lost", "drawn", "tied", "no_result", "win_pct",
                                    "decided", "last"])
    d["favourite"] = False
    d["bogey"] = False
    q = d[(d.played >= min_games) & (d.decided > 0)]
    if len(q) >= 2:
        best = q.sort_values(["win_pct", "won"], ascending=[False, False]).index[0]
        worst = q.sort_values(["win_pct", "lost"], ascending=[True, False]).index[0]
        if d.win_pct[best] > d.win_pct[worst]:
            d.loc[best, "favourite"] = True
            d.loc[worst, "bogey"] = True
    return d.sort_values(["played", "win_pct"], ascending=[False, False]).reset_index(drop=True)


# --------------------------------------------------------------------------- #
# 7 · the league race
# --------------------------------------------------------------------------- #


def position_race(career, ids) -> pd.DataFrame:
    """League position after each match day, for every team in each group of one
    league competition and season (`ids` should be one competition and season).
    The groups are the season's final ones; the order is the league table's:
    points (or wins), then net run rate where there is one, then fewest defeats."""
    from .tables import BILATERAL, LIMITED, _groups, points_rule
    from .analysis import nrr_innings
    cols = ["date", "round", "group", "team", "position", "points", "played"]
    m = career.matches[career.matches.match_id.isin(ids) & ~career.matches.knockout].sort_values(["date", "match_id"])
    if m.empty or m.competition.iloc[0] in BILATERAL:
        return pd.DataFrame(columns=cols)
    comp, fmt = m.competition.iloc[0], m.format.iloc[0]
    _, pts = points_rule(comp, fmt)
    limited = fmt in LIMITED
    inn = career.innings[career.innings.match_id.isin(m.match_id)]
    first = inn[inn.team_innings == 1].groupby(["match_id", "team"]).runs.sum()
    by_match = {k: x for k, x in nrr_innings(career, m.match_id).groupby("match_id")}  # as net run rate counts them
    rows = []
    for label, gm, members in _groups(m):
        tally = {t: dict(points=0.0, won=0, lost=0, played=0, rf=0, bf=0, ra=0, ba=0) for t in members}
        days = sorted(gm.date.unique())
        for i, day in enumerate(days, start=1):
            for r in gm[gm.date == day].itertuples():
                x = by_match.get(r.match_id)
                for team, opp in ((r.home, r.away), (r.away, r.home)):
                    if team not in tally:
                        continue
                    t = tally[team]
                    t["played"] += 1
                    so = limited and r.result_type == "tie" and r.tiebreak_winner != ""
                    win = r.winner == team or (so and r.tiebreak_winner == team)
                    loss = r.winner == opp or (so and r.tiebreak_winner == opp)
                    t["won"] += win
                    t["lost"] += loss
                    if pts:
                        if win and "bonus_win" in pts:
                            big = bool(r.innings_win) or r.margin_wickets == 10
                            t["points"] += pts["bonus_win"] if big else pts["win"]
                        elif win:
                            t["points"] += pts["win"]
                        elif r.result_type == "tie" and not so:
                            t["points"] += pts["tie"]
                        elif r.result_type == "no result":
                            t["points"] += pts["nr"]
                        elif r.result_type == "draw":
                            lead = first.get((r.match_id, team), np.nan) > first.get((r.match_id, opp), np.nan)
                            t["points"] += pts.get("draw_lead", pts["draw"]) if lead else pts["draw"]
                    if x is not None and limited:
                        for inn_r in x.itertuples():
                            balls = inn_r.balls
                            if inn_r.team == team:
                                t["rf"] += inn_r.runs
                                t["bf"] += balls
                            elif inn_r.team == opp:
                                t["ra"] += inn_r.runs
                                t["ba"] += balls
            table = []
            for team, t in tally.items():
                if not t["played"]:
                    continue
                nrr = (t["rf"] / t["bf"] - t["ra"] / t["ba"]) * 6 if limited and t["bf"] and t["ba"] else 0.0
                table.append((team, t["points"] if pts else t["won"], t["won"], nrr, t["lost"], t["played"]))
            table.sort(key=lambda z: (-z[1], -z[2], -z[3], z[4], z[0]))
            for pos, z in enumerate(table, start=1):
                rows.append((pd.Timestamp(day), i, label, z[0], pos, z[1], z[5]))
    return pd.DataFrame(rows, columns=cols)


# --------------------------------------------------------------------------- #
# 23 · openers' start · 29 · early v late season · 30 · bounce back · 31 · revenge
# --------------------------------------------------------------------------- #


def opening_starts(career, ids) -> pd.DataFrame:
    """Each team's first innings of each match with its opening stand, and the result."""
    from . import partnerships as P
    g = games(career, ids)
    inn = career.innings[career.innings.match_id.isin(ids) & (career.innings.team_innings == 1)]
    s = P.stands(career, ids)
    open_ = s[s.wicket == 1].set_index(["match_id", "innings_no"]).runs
    inn = inn.assign(opening=[open_.get((a, b), np.nan) for a, b in zip(inn.match_id, inn.innings_no)])
    return g.merge(inn[["match_id", "team", "opening"]], on=["match_id", "team"], how="inner")


def start_split(career, ids, team: str = "", good: int | None = None, bad: int | None = None) -> dict:
    """Win % when the opening stand reached `good` and when the first wicket fell under `bad`
    (by default the format's bars: 50/15 in T20, 60/20 one-day, 100/25 in Tests)."""
    from .players import kind_of_ids
    b = bars_for(kind_of_ids(career, ids))
    good = b["good_start"] if good is None else good
    bad = b["bad_start"] if bad is None else bad
    o = opening_starts(career, ids)
    if team:
        o = o[o.team == team]
    return dict(good=record(o[o.opening >= good]), bad=record(o[o.opening < bad]),
                middle=record(o[(o.opening >= bad) & (o.opening < good)]), all=record(o), good_bar=good, bad_bar=bad)


def season_halves(career, ids, team: str) -> pd.DataFrame:
    """Record in the first and second half of each season's league games (and in all seasons together)."""
    g = games(career, ids)
    t = g[(g.team == team) & ~g.knockout]
    rows = []
    early, late = [], []
    for season, x in t.groupby("season"):
        x = x.sort_values("date")
        h = len(x) // 2
        e, lt = x.iloc[:len(x) - h], x.iloc[len(x) - h:]
        early.append(e)
        late.append(lt)
        rows.append(dict(season=season, early=record(e), late=record(lt)))
    total = dict(season="All seasons", early=record(pd.concat(early)) if early else record(t.iloc[:0]),
                 late=record(pd.concat(late)) if late else record(t.iloc[:0]))
    return pd.DataFrame(rows + [total]) if rows else pd.DataFrame(columns=["season", "early", "late"])


def after_result(career, ids, team: str = "", venue: str = "all") -> pd.DataFrame:
    """Record in the next game after a win, a loss and a draw (one section's games in date order); with `venue`
    (home / away), only next games played there."""
    g = games(career, ids)
    rows = []
    for tm, x in g.groupby("team"):
        if team and tm != team:
            continue
        x = x.sort_values(["date", "match_id"])
        prev = x.outcome.shift(1)
        rows.append(x.assign(prev=prev).iloc[1:])
    if not rows:
        return pd.DataFrame(columns=["after", "played", "won", "lost", "drawn", "tied", "no_result", "win_pct", "decided"])
    y = pd.concat(rows)
    if venue != "all":
        y = y[y.venue == venue]
    return pd.DataFrame([dict(after=f"After a {OUTCOME_WORD[k].replace('won', 'win').replace('lost', 'loss').replace('drawn', 'draw')}",
                              **record(y[y.prev == k])) for k in ("W", "L", "D") if (y.prev == k).any()],
                        columns=["after", "played", "won", "lost", "drawn", "tied", "no_result", "win_pct", "decided"])


def revenge(career, ids, team: str, venue: str = "all") -> dict:
    """Games against a side that beat them the last time they met, against the rest; with `venue` (home / away),
    only the games played there (the last meeting before each counts wherever it was)."""
    g = games(career, ids)
    t = g[g.team == team].sort_values(["date", "match_id"])
    last: dict[str, str] = {}
    flags = []
    for r in t.itertuples():
        flags.append(last.get(r.opponent) == "L")
        last[r.opponent] = r.outcome
    t = t.assign(revenge=flags)
    if venue != "all":
        t = t[t.venue == venue]
    return dict(revenge=record(t[t.revenge]), other=record(t[~t.revenge]), rows=t[t.revenge])


# --------------------------------------------------------------------------- #
# 32-34 · series: first blood, deciders, dead rubbers
# --------------------------------------------------------------------------- #


def series_games(career, ids) -> pd.DataFrame:
    """Each team's bilateral-series games with the series situation going in:
    match number, the score in the series before it, whether it was the first
    match, a decider (level with one to play, or the last match with the series
    still open) or a dead rubber (the series already won), and how the series ended."""
    g = games(career, ids)
    g = g[g.series_id != ""]
    m = career.matches.set_index("match_id")
    rows = []
    for sid, x in g.groupby("series_id"):
        mids = list(dict.fromkeys(x.sort_values(["date", "match_id"]).match_id))
        length = m.series_length.get(mids[0])
        length = int(length) if pd.notna(length) else len(mids)
        teams = sorted(set(x.team))
        if len(teams) != 2:
            continue
        wins = {t: 0 for t in teams}
        complete = len(mids) >= length
        final_w = {t: int(((x.team == t) & (x.outcome == "W")).sum()) for t in teams}
        series_winner = "" if final_w[teams[0]] == final_w[teams[1]] else max(teams, key=final_w.get)
        for no, mid in enumerate(mids, start=1):
            left = length - no + 1  # games left including this one
            for t in teams:
                o = teams[1] if t == teams[0] else teams[0]
                # dead: one side can't be caught even by winning every game left (this one included)
                dead = wins[t] > wins[o] + left or wins[o] > wins[t] + left
                decider = not dead and left == 1 and wins[t] == wins[o] and length > 1  # level, one to play
                row = x[(x.match_id == mid) & (x.team == t)].iloc[0]
                rows.append(dict(series_id=sid, match_id=mid, no=no, length=length, team=t, opponent=o,
                                 outcome=row.outcome, kind=row.kind, score_before=f"{wins[t]}–{wins[o]}",
                                 first=no == 1, decider=decider, dead=bool(dead), complete=complete,
                                 series_won=series_winner == t, series_lost=series_winner == o,
                                 series_drawn=complete and series_winner == "", date=row.date))
            mrow = x[x.match_id == mid]
            for t in teams:
                if ((mrow.team == t) & (mrow.outcome == "W")).any():
                    wins[t] += 1
    return _typed(pd.DataFrame(rows, columns=["series_id", "match_id", "no", "length", "team", "opponent", "outcome",
                                              "kind", "score_before", "first", "decider", "dead", "complete",
                                              "series_won", "series_lost", "series_drawn", "date"]))


def first_blood(career, ids, team: str = "") -> pd.DataFrame:
    """Finished series of 2+ matches: how the series went after winning, losing or drawing the first match."""
    s = series_games(career, ids)
    s = s[s["first"] & s.complete & (s.length > 1)]   # by name: .first is a pandas method before pandas 3
    if team:
        s = s[s.team == team]
    rows = []
    for k, label in (("W", "Won the first match"), ("L", "Lost the first match"), ("D", "Drew the first match")):
        x = s[s.outcome == k]
        if len(x):
            rows.append(dict(start=label, series=len(x), won=int(x.series_won.sum()), drawn=int(x.series_drawn.sum()),
                             lost=int(x.series_lost.sum()),
                             win_pct=float(x.series_won.mean() * 100)))
    return pd.DataFrame(rows, columns=["start", "series", "won", "drawn", "lost", "win_pct"])


def situations(career, ids, team: str) -> pd.DataFrame:
    """Record in deciders, dead rubbers and live games (series games only)."""
    s = series_games(career, ids)
    s = s[s.team == team]
    rows = []
    for label, x in (("Deciders", s[s.decider]), ("Dead rubbers", s[s.dead]), ("Other live games", s[~s.decider & ~s.dead])):
        rows.append(dict(situation=label, **record(x)))
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# 35-36 · Tests: innings by innings, follow-on and declarations
# --------------------------------------------------------------------------- #


def innings_by_number(career, ids) -> pd.DataFrame:
    """Runs per wicket, average total and run rate in the 1st, 2nd, 3rd and 4th innings (multi-day games)."""
    inn = career.innings[career.innings.match_id.isin(ids)]
    m = career.matches[career.matches.match_id.isin(ids)]
    multi = m[m.format.map(KIND) == "multi"].match_id
    inn = inn[inn.match_id.isin(multi)]
    rows = []
    for no in (1, 2, 3, 4):
        x = inn[inn.innings_no == no]
        if x.empty:
            continue
        rows.append(dict(innings=no, innings_played=len(x), runs_per_wicket=x.runs.sum() / max(x.wickets.sum(), 1),
                         average_total=x.runs.mean(), run_rate=x.runs.sum() / max(x.balls.sum(), 1) * 6,
                         all_out_pct=x.all_out.mean() * 100))
    return pd.DataFrame(rows, columns=["innings", "innings_played", "runs_per_wicket", "average_total", "run_rate",
                                       "all_out_pct"])


def follow_on_and_declarations(career, ids, team: str = "") -> pd.DataFrame:
    """Results when a side enforced the follow-on, and when a side declared (by innings)."""
    inn = career.innings[career.innings.match_id.isin(ids)].sort_values(["match_id", "innings_no"])
    g = games(career, ids).set_index(["match_id", "team"]).outcome
    rows = []
    for mid, x in inn.groupby("match_id"):
        order = list(x.team)
        if len(order) >= 3 and order[1] == order[2]:  # the side batting second batted again straight away
            enforcer = order[0]
            if not team or team == enforcer:
                rows.append(("Enforced the follow-on", g.get((mid, enforcer), "NR")))
            if not team or team == order[1]:
                rows.append(("Made to follow on", g.get((mid, order[1]), "NR")))
        for r in x[x.declared].itertuples():
            if not team or team == r.team:
                label = {1: "Declared in the 1st innings", 2: "Declared in the 2nd innings",
                         3: "Declared in the 3rd innings"}.get(r.innings_no, "Declared in the 4th innings")
                rows.append((label, g.get((mid, r.team), "NR")))
    d = pd.DataFrame(rows, columns=["situation", "outcome"])
    out = []
    for label, x in d.groupby("situation", sort=False):
        c = x.outcome.value_counts()
        n = len(x)
        out.append(dict(situation=label, times=n, won=int(c.get("W", 0)), drawn=int(c.get("D", 0)),
                        lost=int(c.get("L", 0)), win_pct=c.get("W", 0) / n * 100))
    return pd.DataFrame(out, columns=["situation", "times", "won", "drawn", "lost", "win_pct"])


# --------------------------------------------------------------------------- #
# 52 · what is this score worth?
# --------------------------------------------------------------------------- #

BAND = {"t20": 10, "one": 20, "multi": 40}


def score_chances(career, ids, score: int, team: str = "") -> dict:
    """With a first-innings score near `score` (within a band either side): how
    often the side that batted first and made it won, and how often the side
    that kept them to it and chased (bowled first) won.  Ties, no-results (and,
    in one-innings games, nothing else) are left out, so in limited-overs cricket
    the two add up to 100%.  Multi-day games show won/drawn/lost for each side.
    With a team: only that team's games on each side."""
    g = games(career, ids)
    if g.empty:
        return dict(band=0, n=0)
    kind = "multi" if is_multi(g) else g.kind.mode().iloc[0]
    band = BAND[kind]
    near = g[(g.first_score - score).abs() <= band]
    first = near[near.batted_first]
    second = near[~near.batted_first]
    if team:
        first, second = first[first.team == team], second[second.team == team]
    a, b = record(first), record(second)
    return dict(band=band, kind=kind, low=score - band, high=score + band, batting_first=a, bowling_first=b,
                matches=int(near.match_id.nunique()))


# --------------------------------------------------------------------------- #
# 58 · qualification scenarios
# --------------------------------------------------------------------------- #


# the game's own shapes, for a first season with nothing earlier to learn from: league games each, places that go
# through from each group, and how many of the best next-placed sides also go through (the Blast's two best thirds)
KNOWN_SHAPES = {"Indian Premier League": (14, 4, 0), "The Hundred": (8, 3, 0), "T20 Blast": (12, 2, 2),
                "County Championship": (14, 1, 0)}


def has_knockouts(career, event: str) -> bool:
    """Does this competition end in knockouts (so there's something to qualify for)?
    Yes if any season here had one, or it's a limited-overs league (they all do)."""
    from .tables import LIMITED
    m = career.matches[career.matches.event == event]
    return bool(m.knockout.any() or (m.format.isin(list(LIMITED)).all() and m.competition.iloc[0] not in
                                     ("Test", "ODI", "T20I")))


def qualification_defaults(career, event: str, season: str) -> dict:
    """Best guesses for a league's shape: league games per team, places that go through
    from each group, and how many of the best next-placed sides also go through
    (`extra`: the Blast's two best thirds), from an earlier season of the same
    competition where there is one, otherwise the game's usual shape, otherwise this
    season's groups (top 4 of one league, top 2 of each group)."""
    from .tables import _groups
    m = career.matches[(career.matches.event == event)]
    now = m[m.season == season]
    groups = _groups(now[~now.knockout]) if (~now.knockout).any() else []
    n_groups = max(len(groups), 1)
    sizes = [len(g[2]) for g in groups] or [len(set(now.home) | set(now.away))]
    earlier = sorted(s for s in m.season.unique() if s < season)
    games = places = extra = None
    for s in reversed(earlier):
        old = m[m.season == s]
        lg = old[~old.knockout]
        ko = old[old.knockout]
        if lg.empty:
            continue
        per = pd.concat([lg.home, lg.away]).value_counts()
        games = int(per.median())
        if len(ko):
            first_round = ko.sort_values("date")
            teams_ko = set(first_round.home) | set(first_round.away)
            places = max(1, len(teams_ko) // n_groups)
            extra = len(teams_ko) - places * n_groups if n_groups > 1 else 0
        break
    known = KNOWN_SHAPES.get(event) or (KNOWN_SHAPES.get(m.competition.iloc[0]) if len(m) else None)
    if games is None:
        per = pd.concat([now[~now.knockout].home, now[~now.knockout].away]).value_counts()
        rr = max(sizes) - 1
        games = int(max(per.max() if len(per) else 0, known[0] if known else rr))
    if places is None:
        places = known[1] if known else 4 if n_groups == 1 else 2
        extra = known[2] if known and n_groups > 1 else 0
    places = min(places, max(sizes) - 1 if max(sizes) > 1 else 1)
    return dict(games=games, places=places, extra=extra or 0, groups=n_groups)


def qualification(career, event: str, season: str, games: int, places: int) -> pd.DataFrame:
    """Where every team stands in the race for the `places` qualifying spots of
    each group, with `games` league games each: through, out, or what they need.
    Ties on points could still go either way on net run rate, so 'through' and
    'out' are only given when points alone settle it."""
    from .tables import BILATERAL, points_rule
    m = career.matches[(career.matches.event == event) & (career.matches.season == season)]
    race = position_race(career, m.match_id)
    if race.empty or m.competition.iloc[0] in BILATERAL:
        return pd.DataFrame(columns=["group", "position", "team", "played", "points", "left", "max_points", "status", "need"])
    _, pts = points_rule(m.competition.iloc[0], m.format.iloc[0])
    win = pts.get("win", 1) if pts else 1
    last = race[race["round"] == race.groupby("group")["round"].transform("max")]
    rows = []
    for grp, g in last.groupby("group", sort=False):
        g = g.sort_values("position")
        cut_rate = None
        if len(g) > places:
            q = g.iloc[places - 1]  # the team in the last qualifying place now
            cut_rate = q.points / q.played if q.played else 0
        for r in g.itertuples():
            left_ = max(games - r.played, 0)
            mx = r.points + left_ * win
            others = g[g.team != r.team]
            can_catch = int((others.points + (games - others.played).clip(lower=0) * win >= r.points).sum())
            ahead_for_sure = int((others.points > mx).sum())
            finished = bool((g.played >= games).all())  # every game played: the table is final
            if finished:
                status, need = ("Through", "") if r.position <= places else ("Out", "")
            elif len(g) <= places or can_catch < places:
                status, need = "Through", ""
            elif ahead_for_sure >= places:
                status, need = "Out", ""
            else:
                status = "Alive"
                cut = cut_rate * games if cut_rate is not None else r.points
                wins = int(np.ceil(max(cut - r.points, 0) / win))
                need = (f"about {wins} win{'s' if wins != 1 else ''} from {left_}" if wins <= left_ else
                        f"all {left_} wins and help from others") if left_ else "needs others to slip up"
            rows.append(dict(group=grp, position=int(r.position), team=r.team, played=int(r.played), points=r.points,
                             left=left_, max_points=mx, status=status, need=need))
    return pd.DataFrame(rows)
