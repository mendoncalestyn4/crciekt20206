"""Planning the season from your schedule: how hard each fixture is, the record you're heading for, conditions
where you're touring, who travels well, your history with an opponent (past series, form, streaks, records you
could break), a check of the schedule for mistakes, goals to aim at, and the forecasts made before each series
(kept, so you can see how they turned out).

Everything comes from the scorecards: the chances are the same ones the Opponent preview and series odds use
(Elo ratings, then nudges for form, head to head and home ground)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import fixtures as FX
from . import teamplay as TP
from .stats import poss

EASY, HARD = 60.0, 40.0  # your share of the decided results: 60% or more easy, 40% or less hard


def a_or_an(word: str) -> str:
    """'an ODI', 'a Test', 'a T20I'."""
    return ("an " if word[:1].upper() in "AEIO" or word.startswith("ODI") else "a ") + word


# --------------------------------------------------------------------------- the team's games, in played order
def team_games(career, team: str, fmt: str | None = None) -> pd.DataFrame:
    """One row per match the team played (in this format), from their side, in the order they were played."""
    from .records import by_played
    m = career.matches
    x = m[(m.home == team) | (m.away == team)]
    if fmt:
        x = x[x.format == fmt]
    g = TP.games(career, x.match_id)
    return by_played(career, g[g.team == team]).reset_index(drop=True)


def form(career, team: str, fmt: str, last: int = 5) -> list[str]:
    """W / L / D / T / NR for the side's last games in this format, oldest first."""
    return list(team_games(career, team, fmt).outcome.tail(last))


# --------------------------------------------------------------------------- 3 · how hard each fixture is
def level_of(win: float, lose: float) -> str:
    share = win / (win + lose) * 100 if win + lose > 0 else 50.0
    return "easy" if share >= EASY else "hard" if share <= HARD else "even"


def chances(career, tracked: pd.DataFrame, team: str) -> pd.DataFrame:
    """The team's fixtures still to come with a known opponent, in order, with the chance of each result and how
    hard it looks: easy (you win 60% or more of the decided results), even, or hard (40% or less)."""
    from . import winprob as WP
    cols = ["series", "opponent", "format", "no", "venue", "anchor", "status", "win", "draw", "lose", "level"]
    if tracked is None or tracked.empty:
        return pd.DataFrame(columns=cols)
    t = tracked[(tracked.team == team) & tracked.status.isin(["next", "to come"])
                & (tracked.opponent.fillna("") != "")].sort_values(["anchor", "no"])
    rows, memo = [], {}
    for _, r in t.iterrows():
        venue = r["venue"] if r["venue"] in ("home", "away") else "neutral"
        key = (r["format"], r["opponent"], venue)
        if key not in memo:
            ids = FX.format_ids(career, team, r["format"])
            memo[key] = WP.predict(career, ids, team, r["opponent"], venue) if len(ids) else None
        p = memo[key]
        if p is None:
            continue
        rows.append(dict(series=r["series"], opponent=r["opponent"], format=r["format"], no=r["no"], venue=r["venue"],
                         anchor=r["anchor"], status=r["status"], win=p["win"], draw=p["draw"], lose=p["lose"],
                         level=level_of(p["win"], p["lose"])))
    return pd.DataFrame(rows, columns=cols)


def toughest_run(ch: pd.DataFrame, k: int = 3) -> dict | None:
    """The k fixtures in a row (in order) with the lowest average share of wins: the hardest stretch to come."""
    if len(ch) < k:
        return None
    share = (ch.win / (ch.win + ch.lose).replace(0, np.nan) * 100).fillna(50.0).to_numpy()
    means = [share[i:i + k].mean() for i in range(len(ch) - k + 1)]
    i = int(np.argmin(means))
    part = ch.iloc[i:i + k]
    return dict(rows=part, share=float(means[i]), hard=int((part.level == "hard").sum()),
                start=part.anchor.iloc[0], end=part.anchor.iloc[-1])


# --------------------------------------------------------------------------- 4 · the record you're heading for
def _wins_spread(ps: list[float]) -> np.ndarray:
    """Chance of 0..n wins from games won with these chances (one after another, each on its own)."""
    dist = np.zeros(len(ps) + 1)
    dist[0] = 1.0
    for p in ps:
        dist[1:] = dist[1:] * (1 - p) + dist[:-1] * p
        dist[0] *= 1 - p
    return dist


def projection(career, tracked: pd.DataFrame, team: str, start: pd.Timestamp, end: pd.Timestamp) -> dict:
    """The team's record so far between start and end (a season: April to March), plus what the fixtures still
    to come in it add on average: expected wins, defeats and draws, and the likely range of wins (8 times in 10
    the final number is inside it). Tournament games with no opponent yet can't be counted (said in `unknown`)."""
    g = team_games(career, team)
    g = g[(g.date >= start) & (g.date < end)]
    now = {k: int((g.outcome == k).sum()) for k in ("W", "L", "D", "T", "NR")}
    ch = chances(career, tracked, team)
    ch = ch[(ch.anchor >= start) & (ch.anchor < end)] if len(ch) else ch
    unknown = 0
    if tracked is not None and len(tracked):
        tt = tracked[(tracked.team == team) & tracked.status.isin(["next", "to come"])
                     & (tracked.opponent.fillna("") == "") & (tracked.anchor >= start) & (tracked.anchor < end)]
        unknown = int(sum(int(x) if pd.notna(x) and x else 1 for x in tt.get("games_left", pd.Series(dtype=float))))
    pw = list(ch.win / 100) if len(ch) else []
    dist = _wins_spread(pw)
    cum = np.cumsum(dist)
    lo = int(np.searchsorted(cum, 0.1)) if len(pw) else 0
    hi = int(np.searchsorted(cum, 0.9)) if len(pw) else 0
    by_fmt = {}
    for fmt in sorted(set(g.format) | (set(ch.format) if len(ch) else set())):
        gf = g[g.format == fmt]
        cf = ch[ch.format == fmt] if len(ch) else ch
        by_fmt[fmt] = dict(won=int((gf.outcome == "W").sum()), lost=int((gf.outcome == "L").sum()),
                           drawn=int((gf.outcome == "D").sum()), left=len(cf),
                           exp_won=int((gf.outcome == "W").sum()) + float(cf.win.sum() / 100) if len(cf) else
                           float((gf.outcome == "W").sum()),
                           exp_lost=int((gf.outcome == "L").sum()) + float(cf.lose.sum() / 100) if len(cf) else
                           float((gf.outcome == "L").sum()))
    return dict(now=now, played=len(g), left=len(ch), unknown=unknown,
                exp_won=now["W"] + float(ch.win.sum() / 100) if len(ch) else float(now["W"]),
                exp_lost=now["L"] + float(ch.lose.sum() / 100) if len(ch) else float(now["L"]),
                exp_drawn=now["D"] + float(ch.draw.sum() / 100) if len(ch) else float(now["D"]),
                low=now["W"] + lo, high=now["W"] + hi, by_format=by_fmt, chances=ch)


# --------------------------------------------------------------------------- 7 · conditions where you're going
def conditions(career, host: str, fmt: str, min_games: int = 3) -> dict | None:
    """What cricket is like in the host's country in this format (their home games, not neutral ones), next to
    the format as a whole: the average first-innings score, how often batting first wins, runs per wicket and, in
    multi-day cricket, how often it's a draw. None if fewer than min_games there."""
    m = career.matches
    allg = m[m.format == fmt]
    there = allg[(allg.home == host) & ~allg.neutral]
    if len(there) < min_games:
        return None

    def stats(ids):
        g = TP.games(career, ids)
        first = g[g.batted_first]
        rec = TP.record(first)
        inn = career.innings[career.innings.match_id.isin(ids)]
        wk = inn.wickets.sum()
        multi = TP.is_multi(g) if len(g) else False
        return dict(games=len(ids), first=float(first.first_score.mean()) if len(first) else np.nan,
                    bat_first_win=rec["win_pct"], runs_per_wicket=float(inn.runs.sum() / wk) if wk else np.nan,
                    draws=float((first.outcome == "D").mean() * 100) if multi and len(first) else np.nan, multi=multi)
    return dict(host=host, format=fmt, there=stats(there.match_id), everywhere=stats(allg.match_id))


# --------------------------------------------------------------------------- 8 · who travels well
def travellers(career, team: str, fmt: str, host: str | None = None, min_inns: int = 3, min_balls: int = 120) -> dict:
    """The side's players at home and away in this format (or, with host, in that country against everywhere
    else): batting average and bowling average in each, and the difference. Only players with enough of both."""
    m = career.matches
    mine = m[(m.format == fmt) & ((m.home == team) | (m.away == team))]
    if host and host != team:
        away_ids = set(mine[(mine.home == host) & ~mine.neutral].match_id)
        label = f"in {host}"
    else:
        away_ids = set(mine[(mine.away == team) & ~mine.neutral].match_id)
        label = "away"
    home_ids = set(mine[(mine.home == team) & ~mine.neutral].match_id) if not host or host == team else \
        set(mine.match_id) - away_ids
    bat = career.batting[career.batting.match_id.isin(mine.match_id) & (career.batting.team == team)
                         & career.batting.did_bat]
    bowl = career.bowling[career.bowling.match_id.isin(mine.match_id) & (career.bowling.team == team)]

    def bat_side(ids):
        b = bat[bat.match_id.isin(ids)].groupby("player").agg(inns=("runs", "size"), runs=("runs", "sum"),
                                                                outs=("out", "sum"))
        b["avg"] = b.runs / b.outs.replace(0, np.nan)
        return b

    def bowl_side(ids):
        w = bowl[bowl.match_id.isin(ids)].groupby("player").agg(balls=("balls", "sum"), runs=("runs", "sum"),
                                                                 wkts=("wickets", "sum"))
        w["avg"] = w.runs / w.wkts.replace(0, np.nan)
        return w
    bh, ba = bat_side(home_ids), bat_side(away_ids)
    b = bh.join(ba, lsuffix="_home", rsuffix="_away", how="inner")
    b = b[(b.inns_home >= min_inns) & (b.inns_away >= min_inns)].copy()
    b["diff"] = b.avg_away - b.avg_home
    wh, wa = bowl_side(home_ids), bowl_side(away_ids)
    w = wh.join(wa, lsuffix="_home", rsuffix="_away", how="inner")
    w = w[(w.balls_home >= min_balls) & (w.balls_away >= min_balls)].copy()
    w["diff"] = w.avg_home - w.avg_away  # positive: cheaper wickets away, so better on the road
    return dict(label=label, bat=b.reset_index().sort_values("diff", ascending=False),
                bowl=w.reset_index().sort_values("diff", ascending=False), away_games=len(away_ids),
                home_games=len(home_ids))


# --------------------------------------------------------------------------- 12 · past series with them
def series_history(career, team: str, opp: str, fmt: str) -> dict:
    """Every series the two have played in this format, oldest first ("won 2–1 at home", with the season), and
    the team's record in series in the opponent's country."""
    m = career.matches
    x = m[(m.format == fmt) & (((m.home == team) & (m.away == opp)) | ((m.home == opp) & (m.away == team)))]
    rows = []
    for sid, g in x.groupby(x.series_id.where(x.series_id != "", x.match_id), sort=False):
        g = g.sort_values("date")
        w, lo = int((g.winner == team).sum()), int((g.winner == opp).sum())
        d = len(g) - w - lo
        first = g.iloc[0]
        venue = "neutral" if first.neutral else ("home" if first.home == team else "away")
        length = int(pd.to_numeric(g.series_length, errors="coerce").max()) if \
            pd.to_numeric(g.series_length, errors="coerce").notna().any() else len(g)
        result = ("under way" if len(g) < length and max(w, lo) <= length // 2 else
                  "won" if w > lo else "lost" if lo > w else "drawn")
        score = f"{w}–{lo}" + (f" ({d} drawn)" if d and fmt in ("Test", "First-class") else
                              f" ({d} no result)" if d else "")
        rows.append(dict(series_id=sid, start=first.date, season=first.season, venue=venue, games=len(g), won=w,
                         lost=lo, other=d, result=result, score=score))
    rows.sort(key=lambda r: r["start"])
    away = [r for r in rows if r["venue"] == "away" and r["result"] != "under way"]
    return dict(rows=rows, won=sum(r["result"] == "won" for r in rows), lost=sum(r["result"] == "lost" for r in rows),
                drawn=sum(r["result"] == "drawn" for r in rows),
                away=dict(series=len(away), won=sum(r["result"] == "won" for r in away)))


# --------------------------------------------------------------------------- 14 · favourite opponents, bogey teams
def rivalry(career, team: str, opp: str, fmt: str | None = None, min_decided: int = 3) -> dict | None:
    """'favourite' when you've won 70% or more of the decided games against them, 'bogey' at 30% or less (at
    least min_decided decided games); with the record."""
    g = team_games(career, team, fmt)
    g = g[g.opponent == opp]
    rec = TP.record(g) if len(g) else None
    if not rec or rec["decided"] < min_decided or not np.isfinite(rec["win_pct"]):
        return None
    kind = "favourite" if rec["win_pct"] >= 70 else "bogey" if rec["win_pct"] <= 30 else None
    return dict(kind=kind, record=rec, text=TP.wdl(rec)) if kind else None


# --------------------------------------------------------------------------- 15 · streaks on the line
def _run(outcomes: list[str], ok) -> int:
    n = 0
    for o in reversed(outcomes):
        if o in ("NR",):
            continue
        if not ok(o):
            break
        n += 1
    return n


def streaks(career, team: str, opp: str, fmt: str, venue: str = "") -> list[str]:
    """The runs going into the next game: wins or defeats in a row in this format, unbeaten at home (or away),
    and the last few results against this opponent."""
    g = team_games(career, team, fmt)
    if g.empty:
        return []
    word = FX.plural(fmt, 2).split(" ", 1)[1]  # "ODIs", "Tests", "Hundred games"
    out = []
    o = list(g.outcome)
    w, lo = _run(o, lambda x: x == "W"), _run(o, lambda x: x == "L")
    unbeaten = _run(o, lambda x: x != "L")
    if w >= 3:
        out.append(f"🔥 {team} have won their last {w} {word}")
    elif lo >= 3:
        out.append(f"😬 {team} have lost their last {lo} {word}")
    elif unbeaten >= 5:
        out.append(f"🛡️ {team} are unbeaten in {unbeaten} {word}")
    if venue in ("home", "away"):
        gv = list(g[g.venue == venue].outcome)
        ub, lv = _run(gv, lambda x: x != "L"), _run(gv, lambda x: x == "L")
        where = "at home" if venue == "home" else "away"
        if ub >= 4:
            out.append(f"🏟️ unbeaten in {ub} {word} {where}")
        elif lv >= 3:
            out.append(f"🧳 lost the last {lv} {word} {where}")
    h = list(g[g.opponent == opp].outcome)
    hw, hl = _run(h, lambda x: x == "W"), _run(h, lambda x: x == "L")
    if hw >= 2:
        out.append(f"✅ won the last {hw} against {opp}")
    elif hl >= 2:
        out.append(f"⚠️ lost the last {hl} against {opp}")
    return out


# --------------------------------------------------------------------------- 16 · records in reach this series
def series_records(career, team: str, opp: str, fmt: str, games: int = 3) -> list[str]:
    """Series records in this format that a side could reach in this series: most runs and most wickets in one
    series (any teams), most in a series between these two, and each side's highest total against the other. With
    what the team's in-form player would need a game to get there."""
    m = career.matches
    x = m[(m.format == fmt) & (m.series_id != "")]
    if x.empty:
        return []
    out = []
    bat = career.batting[career.batting.match_id.isin(x.match_id)].merge(x[["match_id", "series_id"]], on="match_id")
    bowl = career.bowling[career.bowling.match_id.isin(x.match_id)].merge(x[["match_id", "series_id"]], on="match_id")
    runs = bat.groupby(["series_id", "player", "team"]).runs.sum().sort_values(ascending=False)
    wkts = bowl.groupby(["series_id", "player", "team"]).wickets.sum().sort_values(ascending=False)
    pair = x[((x.home == team) & (x.away == opp)) | ((x.home == opp) & (x.away == team))]
    pw = FX.players_to_watch(career, team, fmt)
    if len(runs):
        (_, p, t), v = runs.index[0], int(runs.iloc[0])
        line = f"🏏 Most runs in {a_or_an(fmt)} series: {v} by {p} ({t})"
        if len(pw["bat"]) and games:
            need = v / games
            line += f". {pw['bat'].index[0]} would need about {need:.0f} a game over {games} to beat it"
        out.append(line)
    if len(wkts):
        (_, p, t), v = wkts.index[0], int(wkts.iloc[0])
        line = f"🎯 Most wickets in {a_or_an(fmt)} series: {v} by {p} ({t})"
        if len(pw["bowl"]) and games:
            line += f". {pw['bowl'].index[0]} would need about {v / games:.1f} a game"
        out.append(line)
    if len(pair):
        rp = runs[runs.index.get_level_values(0).isin(pair.series_id)]
        if len(rp):
            (_, p, t), v = rp.index[0], int(rp.iloc[0])
            out.append(f"🤝 Most runs in {a_or_an(fmt)} series between {team} and {opp}: {v} by {p} ({t})")
        inn = career.innings[career.innings.match_id.isin(m[(m.format == fmt) & (
            ((m.home == team) & (m.away == opp)) | ((m.home == opp) & (m.away == team)))].match_id)]
        for side, other in ((team, opp), (opp, team)):
            i = inn[inn.team == side]
            if len(i):
                top = i.sort_values("runs", ascending=False).iloc[0]
                out.append(f"📈 {poss(side)} highest {fmt} total against {other}: {int(top.runs)}"
                           + ("" if top.all_out or top.wickets >= 10 else f"/{int(top.wickets)}"))
    return out


# --------------------------------------------------------------------------- 1 · check the schedule for mistakes
def check(career, fixtures: list[dict], tracked: pd.DataFrame, team: str) -> list[dict]:
    """Likely mistakes in what you added for this team, each with what to do about it:
    - the same series added twice (same opponent and format within a month)
    - two series on the same days (from the dates you gave)
    - a series whose time has gone with no scorecard, and the game played that opponent in that format at
      another time (it was put in the wrong month): move it there
    - a date before a match of the series that was already played (it's ignored)
    - a series put at the other venue (home / away) from what its scorecards show
    Each: dict(kind, series, text, fix) where fix is None or {"month": "YYYY-MM"} / {"venue": "home"} /
    {"delete": True} / {"clear_dates": True}."""
    items = FX.schedule_items(fixtures, team)
    out = []
    series_items = [it for it in items if it["kind"] == "series"]
    # the same series twice
    for i, a in enumerate(series_items):
        for b in series_items[i + 1:]:
            if a["opponent"] == b["opponent"] and a["format"] == b["format"] and a["month"] and b["month"]:
                gap = abs((pd.Timestamp(a["month"] + "-01") - pd.Timestamp(b["month"] + "-01")).days)
                if gap <= 31:
                    out.append(dict(kind="twice", series=b["series"],
                                    text=f"{b['series']} looks like {a['series']} added twice: delete one?",
                                    fix={"delete": True}))
    # two series on the same days (only dates you typed)
    spans = []
    for it in series_items:
        ds = [pd.Timestamp(d) for d in it.get("dates", []) if d]
        if ds:
            spans.append((min(ds), max(ds), it))
    for i, (a0, a1, a) in enumerate(spans):
        for b0, b1, b in spans[i + 1:]:
            if a0 <= b1 and b0 <= a1:
                out.append(dict(kind="overlap", series=b["series"],
                                text=f"{a['series']} and {b['series']} have dates on the same days "
                                     f"({max(a0, b0):%d %b}–{min(a1, b1):%d %b}): change one of them?", fix=None))
    if tracked is None or tracked.empty:
        return out
    mine = tracked[tracked.team == team]
    auto = mine[mine.auto.astype(str) == "True"]
    for it in series_items:
        rows = mine[(mine.series == it["series"]) & (mine.kind == "match")]
        if rows.empty:
            continue
        missed = rows[rows.status == "no scorecard"]
        if len(missed) and not (rows.status == "played").any():
            # the game played them at another time? (an auto-added series of the same opponent and format)
            near = auto[(auto.opponent == it["opponent"]) & (auto.format == it["format"]) & (auto.status == "played")]
            if len(near):
                when = pd.Timestamp(near.anchor.min())
                out.append(dict(kind="moved", series=it["series"],
                                text=f"No scorecards for {it['series']}, but {team} played {FX.plural(it['format'], 2).split(' ', 1)[1]} "
                                     f"against {it['opponent']} in {when:%b %Y} (added from the scorecards): move "
                                     f"it to {when:%b %Y}?", fix={"month": f"{when:%Y-%m}"}))
            else:
                out.append(dict(kind="missing", series=it["series"],
                                text=f"No scorecards for {it['series']} although its time has gone: check the "
                                     "month and the opponent, or delete it.", fix=None))
        # matched to games two months or more from the month it was put in: offer the right month
        played = rows[rows.status == "played"]
        if len(played) and it["month"] and not any(it.get("dates", [])):
            first = pd.Timestamp(played.played_date.min())
            put = pd.Timestamp(it["month"] + "-01")
            if abs((first.year - put.year) * 12 + first.month - put.month) >= 2:
                out.append(dict(kind="month", series=it["series"],
                                text=f"{it['series']} was played from {first:%d %b %Y}, not in {put:%b %Y}: change "
                                     f"its month to {first:%b %Y}?", fix={"month": f"{first:%Y-%m}"}))
        # a date given for a match before one of the series already played
        if len(played):
            last = pd.Timestamp(played.played_date.max())
            early = [r for r in it["rows"] if r.get("date") and pd.Timestamp(r["date"]) <= last
                     and int(r.get("no") or 0) > int(played.no.max())]
            if early:
                r = early[0]
                out.append(dict(kind="early", series=it["series"],
                                text=f"{it['series']}: you gave match {int(r['no'])} the date {pd.Timestamp(r['date']):%d %b %Y}, "
                                     f"but match {int(played.no.max())} was only played on {last:%d %b %Y}. That date is "
                                     "ignored: clear it, or put the right one in.", fix={"clear_dates": True}))
        if rows.venue_fixed.astype(str).eq("True").any():
            real = rows.venue.iloc[0]
            out.append(dict(kind="venue", series=it["series"],
                            text=f"{it['series']} is down as {it['venue']}, but its scorecards show {team} {real}: "
                                 f"make it {real}?", fix={"venue": real}))
    return out


def apply_fix(fixtures: list[dict], team: str, series: str, fix: dict) -> list[dict]:
    """The schedule with one check's fix made: moved to another month, venue changed, its dates cleared, or deleted."""
    if fix.get("delete"):
        return FX.delete_item(fixtures, team, series)[0]
    it = next((x for x in FX.schedule_items(fixtures, team) if x["series"] == series), None)
    if it is None or it["kind"] != "series":
        return fixtures
    month = fix.get("month", it["month"])
    venue = fix.get("venue", it["venue"])
    dates = [] if fix.get("clear_dates") or "month" in fix else it.get("dates", [])
    new = FX.make_series(team, it["opponent"], it["format"], it["n"], venue, month, dates=dates)
    return FX.replace_item(fixtures, team, series, new)


# --------------------------------------------------------------------------- 24 · goals to aim at
def suggested_goals(career, tracked: pd.DataFrame, team: str, goals: list[dict]) -> list[dict]:
    """Ready-made goals from the schedule that aren't set yet: win each series still to come (or under way),
    reach the World Test Championship final (a Test side with Tests to come)."""
    have = {(g.get("kind"), g.get("team"), g.get("series", "")) for g in goals}
    out = []
    if tracked is None or tracked.empty:
        return out
    for s in FX.series_groups(tracked, team):
        if s["state"] in ("to come", "under way") and ("series", team, s["series"]) not in have:
            out.append(dict(kind="series", team=team, series=s["series"]))
    if team in FX.NATIONS and ("wtc", team, "") not in have:
        mine = tracked[(tracked.team == team) & (tracked.format == "Test") & tracked.status.isin(["next", "to come"])]
        if len(mine):
            out.append(dict(kind="wtc", team=team))
    return out


# --------------------------------------------------------------------------- 10 · forecasts made before each series
def forecast_key(team: str, series: str) -> str:
    return f"{team}||{series}"


def take_forecasts(career, tracked: pd.DataFrame, team: str, saved: dict) -> dict:
    """Forecasts for the team's series that haven't started and haven't got one yet (made now, from the chances
    before ball one): {key: {made, win, draw, lose, likely, games, opponent, format}}."""
    new = {}
    if tracked is None or tracked.empty:
        return new
    today = career.matches.date.max()
    for s in FX.series_groups(tracked, team):
        k = forecast_key(team, s["series"])
        if s["state"] != "to come" or k in saved:
            continue
        o = FX.series_outlook(career, team, s)
        likely = next(iter(o["scorelines"]), None)
        new[k] = dict(made=f"{today:%Y-%m-%d}" if pd.notna(today) else "", win=round(float(o["odds"]["A"]), 1),
                      draw=round(float(o["odds"].get("level", 0.0)), 1), lose=round(float(o["odds"]["B"]), 1),
                      likely=f"{likely[0]}–{likely[1]}" if likely else "", games=int(s["total"]),
                      opponent=s["opponent"], format=s["format"])
    return new


def forecast_check(tracked: pd.DataFrame, team: str, saved: dict) -> list[dict]:
    """For each finished series with a forecast: what was forecast and what happened, and whether the forecast's
    favourite won (a level forecast counts as right when the series was drawn) and the exact score came true."""
    out = []
    if tracked is None or tracked.empty:
        return out
    for s in FX.series_groups(tracked, team):
        f = saved.get(forecast_key(team, s["series"]))
        if not f or s["state"] != "done":
            continue
        fav = "you" if f["win"] > f["lose"] else "them" if f["lose"] > f["win"] else "level"
        res = "you" if s["won"] > s["lost"] else "them" if s["lost"] > s["won"] else "level"
        out.append(dict(series=s["series"], forecast=f, result=f"{s['won']}–{s['lost']}", favourite=fav, winner=res,
                        right=fav == res, exact=f.get("likely") == f"{s['won']}–{s['lost']}"))
    return out
