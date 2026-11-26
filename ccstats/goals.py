"""The new goal kinds (stage 4, your picks of 26 November), next to the old four in fixtures.py.

Team goals: win a title, reach the knockouts or finish in the top N of a league, unbeaten at home, reach No. 1 in the
team ratings, beat a rival, win an away series, a win streak. Player goals: top run-scorer or wicket-taker in a
competition, a season average, a number of hundreds or five-fors.

A competition goal (title, top N, top scorer) counts that competition's own season, as the game names it. A format goal
(home, rival, away series, streak, average, hundreds) counts the April-to-March season the My team page uses, written
"2028–29". Each goal gives (done 0-1, a plain sentence, a status), the same as the old four: achieved, missed, on
course, at risk, under way, to come or unknown. Only what has been played counts; nothing is guessed except where it
says "chance".
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .stats import ordinal

TEAM_KINDS = {
    "title": "Win a title",
    "top": "Reach the knockouts or finish in the top places",
    "home": "Unbeaten at home",
    "no1": "Reach No. 1 in the team ratings",
    "rival": "Beat a rival",
    "away": "Win an away series",
    "streak": "Win matches in a row",
}
PLAYER_KINDS = {
    "topscorer": "Top run-scorer or wicket-taker",
    "average": "A season average",
    "hauls": "Hundreds or five-fors",
}
KINDS = {**TEAM_KINDS, **PLAYER_KINDS}
MIN_INNINGS = 5          # a season average needs this many innings (batting) or this many matches bowled in (bowling)


# --------------------------------------------------------------------------- seasons
def april_label(year) -> str:
    y = int(year)
    return f"{y}–{str(y + 1)[-2:]}"


def april_seasons_of(career) -> pd.Series:
    """Match id -> the April-to-March season year (a series or tournament goes whole to one season)."""
    from .keep import on_career
    from .seasonal import april_seasons
    return on_career(career, ("goal_april",), lambda: april_seasons(career.matches))


def _april_over(career, year: int) -> bool:
    """The April-to-March season is over in the game: a match has been played after it ended."""
    last = career.matches.date.max()
    return bool(pd.notna(last) and last >= pd.Timestamp(year=int(year) + 1, month=4, day=1))


def _team_games(career, team: str, fmt: str, year) -> pd.DataFrame:
    """The team's games in one format and April-to-March season, oldest first."""
    from .teamplay import games
    m = career.matches
    sea = april_seasons_of(career)
    ids = m[(m.format == fmt) & ((m.home == team) | (m.away == team))].match_id
    ids = [i for i in ids if int(sea.get(i, -1)) == int(year)]
    g = games(career, ids)
    return g[g.team == team].sort_values(["date", "match_id"]).reset_index(drop=True)


# --------------------------------------------------------------------------- what each goal says
def _games(fmt: str) -> str:
    """'Tests', 'ODIs', 'first-class games', 'one-day games'."""
    from .fixtures import plural
    return plural(fmt, 2).split(" ", 1)[1]


def label(goal: dict) -> str:
    k, t = goal.get("kind"), goal.get("team", "")
    sea = goal.get("season", "")
    if k == "title":
        return f"{t}: win the {goal.get('section')} {sea}"
    if k == "top":
        n = int(goal.get("n") or 0)
        where = f"the {goal.get('section')} {sea}"
        return f"{t}: reach the knockouts of {where}" if n == 0 else f"{t}: finish in the top {n} of {where}"
    if k == "home":
        return f"{t}: unbeaten at home in {_games(goal.get('format', ''))} in {april_label(sea)}"
    if k == "no1":
        return f"{t}: reach No. 1 in the {goal.get('section')} team ratings"
    if k == "rival":
        return f"{t}: beat {goal.get('opponent')} in {_games(goal.get('format', ''))} in {april_label(sea)}"
    if k == "away":
        return f"{t}: win an away {goal.get('format')} series in {april_label(sea)}"
    if k == "streak":
        return f"{t}: win {int(goal.get('target') or 0)} {_games(goal.get('format', ''))} in a row in {april_label(sea)}"
    p = goal.get("player", "")
    if k == "topscorer":
        what = "run-scorer" if goal.get("what") == "runs" else "wicket-taker"
        return f"{p}: top {what} in the {goal.get('section')} {sea}"
    if k == "average":
        bat = goal.get("what") == "batting"
        sign = "or more" if bat else "or less"
        return (f"{p}: {'batting' if bat else 'bowling'} average of {float(goal.get('target') or 0):g} {sign} "
                f"in {_games(goal.get('format', ''))} in {april_label(sea)}")
    if k == "hauls":
        what = "hundreds" if goal.get("what") == "hundreds" else "five-fors"
        n = int(goal.get("target") or 0)
        if n == 1:
            what = "a hundred" if what == "hundreds" else "a five-for"
            return f"{p}: {what} in {_games(goal.get('format', ''))} in {april_label(sea)}"
        return f"{p}: {n} {what} in {_games(goal.get('format', ''))} in {april_label(sea)}"
    return "Goal"


def _r(done: float, text: str, status: str) -> dict:
    return dict(done=float(min(max(done, 0.0), 1.0)), text=text, status=status)


def progress(career, goal: dict) -> dict:
    """(done 0-1, text, status) for one of the new goals."""
    k = goal.get("kind")
    try:
        fn = {"title": _title, "top": _top, "home": _home, "no1": _no1, "rival": _rival, "away": _away,
              "streak": _streak, "topscorer": _topscorer, "average": _average, "hauls": _hauls}[k]
    except KeyError:
        return _r(0, "", "unknown")
    return fn(career, goal)


# --------------------------------------------------------------------------- team goals
def _section_games(career, section: str, season: str) -> pd.DataFrame:
    m = career.matches
    return m[(m.section == section) & (m.season.astype(str) == str(season))]


def _status(career, section: str, season: str) -> str:
    from .seasonal import season_status
    here = _section_games(career, section, season)
    if here.empty:
        return "to come"
    return season_status(career, section, here.season.iloc[0])


def _title(career, goal: dict) -> dict:
    from .extras import honours
    team, sec, sea = goal.get("team", ""), goal.get("section", ""), str(goal.get("season", ""))
    here = _section_games(career, sec, sea)
    if here.empty:
        return _r(0, "Not started yet.", "to come")
    st = _status(career, sec, sea)
    h = honours(career)
    h = h[(h.season.astype(str) == sea) & h.section.isin(set(here.event) | {sec})]
    champs = set().union(*[set(x) for x in h.champion_teams]) if len(h) else set()
    if st == "complete":
        if team in champs:
            return _r(1, "Won it.", "achieved")
        who = ", ".join(sorted(champs)) or "someone else"
        return _r(0, f"Not won: {who} won it.", "missed")
    mine = here[(here.home == team) | (here.away == team)]
    if mine.empty:
        return _r(0, f"{team} haven't played in it yet.", "to come")
    from . import odds as OD
    ev = here.event.mode().iloc[0]
    try:
        od = OD.season_odds(career, ev, here.season.iloc[0])
        t = od["table"]
        row = t[t.team == team]
        ch = float(row.title.iloc[0]) if len(row) and np.isfinite(row.title.iloc[0]) else np.nan
    except Exception:  # noqa: BLE001 - no chance worked out (a series, a knockout-only event): the plain record only
        ch = np.nan
    w = sum(1 for r in mine.itertuples() if (r.winner or "") == team)
    rec = f"{w} won from {len(mine)} so far"
    if np.isfinite(ch):
        return _r(ch / 100, f"{rec}; chance of winning it {ch:.0f}%.", "on course" if ch >= 50 else "at risk")
    return _r(0, rec + ".", "under way")


def _top(career, goal: dict) -> dict:
    from . import tables as T
    team, sec, sea, n = goal.get("team", ""), goal.get("section", ""), str(goal.get("season", "")), int(goal.get("n") or 0)
    here = _section_games(career, sec, sea)
    if here.empty:
        return _r(0, "Not started yet.", "to come")
    st = _status(career, sec, sea)
    ko = here[here.knockout.astype(bool) & ((here.home == team) | (here.away == team))]
    league = here[~here.knockout.astype(bool)]
    pos, size, lead = None, 0, ""
    for name, table, _rule in T.league_tables(career, league.match_id):
        t = table.reset_index(drop=True)
        if team in set(t.team):
            pos, size = int(t.index[t.team == team][0]) + 1, len(t)
            lead = name
            break
    group = lead and lead not in (sec, "League", "Every team") and len(T.league_tables(career, league.match_id)) > 1
    where = f"{ordinal(pos)} of {size}" + (f" in {lead}" if group else "") if pos else ""
    if n == 0:   # reach the knockouts
        if len(ko):
            return _r(1, f"Through to the knockouts ({ko.sort_values('date').stage.iloc[0] or 'knockout'}).", "achieved")
        if st == "complete" or (len(here[here.knockout.astype(bool)]) and T.league_finished(league)):
            return _r(0, f"Didn't reach the knockouts{' (' + where + ')' if where else ''}.", "missed")
        if not pos:
            return _r(0, f"{team} haven't played in it yet.", "to come")
        return _r(max(0.0, 1 - (pos - 1) / max(size, 1)), f"{where} now.", "under way")
    if not pos:
        return _r(0, f"{team} haven't played in it yet.", "to come")
    over = st == "complete" or T.league_finished(league)
    if over:
        return (_r(1, f"Finished {where}.", "achieved") if pos <= n else _r(0, f"Finished {where}.", "missed"))
    return _r(1.0 if pos <= n else n / pos, f"{where} now.", "on course" if pos <= n else "at risk")


def _home(career, goal: dict) -> dict:
    team, fmt, year = goal.get("team", ""), goal.get("format", ""), int(goal.get("season") or 0)
    g = _team_games(career, team, fmt, year)
    g = g[g.venue == "home"]
    lost = int((g.outcome == "L").sum())
    rec = f"{int((g.outcome == 'W').sum())} won, {lost} lost" + (f", {int((g.outcome == 'D').sum())} drawn"
                                                                  if (g.outcome == "D").any() else "")
    if lost:
        first = g[g.outcome == "L"].iloc[0]
        return _r(0, f"Lost at home to {first.opponent} ({pd.Timestamp(first.date):%d %b %Y}). Home record: {rec}.", "missed")
    if g.empty:
        if _april_over(career, year):
            return _r(0, "No home games that season.", "missed")
        return _r(0, "No home games yet.", "to come")
    if _april_over(career, year):
        return _r(1, f"Unbeaten at home: {rec} in {len(g)} game{'s' if len(g) != 1 else ''}.", "achieved")
    return _r(1, f"Unbeaten so far: {rec} in {len(g)} home game{'s' if len(g) != 1 else ''}.", "on course")


def _no1(career, goal: dict) -> dict:
    from .rankings import team_elo
    team, sec = goal.get("team", ""), goal.get("section", "")
    since = pd.Timestamp(goal.get("since")) if goal.get("since") else None
    table, hist = team_elo(career, sec)
    if table.empty or team not in set(table.team):
        return _r(0, f"{team} have no rating in the {sec} yet.", "to come")
    pos = int(table.index[table.team == team][0])
    # reached at any time since the goal was set: the ratings replayed match by match
    rating: dict[str, float] = {}
    reached = None
    for r in hist.sort_values(["date", "match_id"]).itertuples():
        rating[r.team] = r.after
        if r.team == team and (since is None or r.date >= since):
            if max(rating.values()) <= rating[team] + 1e-9:
                reached = r.date
                break
    if reached is not None or pos == 1:
        when = f" on {pd.Timestamp(reached):%d %b %Y}" if reached is not None else ""
        return _r(1, f"Reached No. 1{when}." + (" Still No. 1." if pos == 1 else f" Now {ordinal(pos)}."), "achieved")
    top = float(table.elo.iloc[0])
    mine = float(table.elo.iloc[pos - 1])
    return _r(max(0.0, 1 - (top - mine) / 200), f"{ordinal(pos)} now, {top - mine:.0f} rating points behind "
              f"{table.team.iloc[0]}.", "under way")


def _rival(career, goal: dict) -> dict:
    team, opp, fmt, year = goal.get("team", ""), goal.get("opponent", ""), goal.get("format", ""), int(goal.get("season") or 0)
    g = _team_games(career, team, fmt, year)
    g = g[g.opponent == opp]
    w, lo = int((g.outcome == "W").sum()), int((g.outcome == "L").sum())
    d = int((g.outcome == "D").sum())
    rec = f"{w}–{lo}" + (f" ({d} drawn)" if d else "")
    if g.empty:
        if _april_over(career, year):
            return _r(0, f"Didn't play {opp} that season.", "missed")
        return _r(0, f"Not played {opp} yet.", "to come")
    if _april_over(career, year):
        return _r(1, f"Beat them: {rec}.", "achieved") if w > lo else _r(0, f"{rec} against them.", "missed")
    status = "on course" if w > lo else "at risk" if lo > w else "under way"
    return _r(w / max(w + lo, 1), f"{rec} against them so far.", status)


def _away_series(career, team: str, fmt: str, year: int) -> list[dict]:
    """The team's away series (not neutral, two games or more) in a format and season: won, lost, finished or not."""
    g = _team_games(career, team, fmt, year)
    g = g[g.series_id.fillna("").astype(str) != ""]
    m = career.matches.set_index("match_id")
    out = []
    for sid, s in g.groupby("series_id", sort=False):
        if not (s.venue == "away").mean() > 0.5:
            continue
        length = m.loc[s.match_id.iloc[0]].series_length
        length = int(length) if pd.notna(length) and length else len(s)
        if length < 2:
            continue
        w, lo = int((s.outcome == "W").sum()), int((s.outcome == "L").sum())
        out.append(dict(opponent=s.opponent.iloc[0], won=w, lost=lo, played=len(s), length=length,
                        done=len(s) >= length or w > length // 2 or lo > length // 2))
    return out


def _away(career, goal: dict) -> dict:
    team, fmt, year = goal.get("team", ""), goal.get("format", ""), int(goal.get("season") or 0)
    ss = _away_series(career, team, fmt, year)
    won = [s for s in ss if s["done"] and s["won"] > s["lost"]]
    if won:
        s = won[0]
        return _r(1, f"Won in {s['opponent']} {s['won']}–{s['lost']}.", "achieved")
    live = [s for s in ss if not s["done"]]
    if live:
        s = live[0]
        return _r(s["won"] / (s["length"] // 2 + 1), f"In {s['opponent']}: {s['won']}–{s['lost']} with "
                  f"{s['length'] - s['played']} to play.", "under way")
    if _april_over(career, year):
        return _r(0, "No away series won that season." if ss else "No away series that season.", "missed")
    done = "; ".join(f"{s['opponent']} {s['won']}–{s['lost']}" for s in ss)
    return _r(0, (f"Away series so far: {done}." if ss else "No away series played yet."), "to come" if not ss else "under way")


def _runs(outcomes: list[str]) -> tuple[int, int]:
    """(longest run of wins, the run going now). A no result doesn't break a run; anything else that isn't a win does."""
    best = cur = 0
    for o in outcomes:
        if o == "NR":
            continue
        cur = cur + 1 if o == "W" else 0
        best = max(best, cur)
    return best, cur


def _streak(career, goal: dict) -> dict:
    team, fmt, year, n = goal.get("team", ""), goal.get("format", ""), int(goal.get("season") or 0), int(goal.get("target") or 0)
    g = _team_games(career, team, fmt, year)
    best, cur = _runs(list(g.outcome))
    if n and best >= n:
        return _r(1, f"Won {best} in a row.", "achieved")
    if _april_over(career, year):
        return _r(best / n if n else 0, f"Best run that season: {best}.", "missed")
    if g.empty:
        return _r(0, "No games yet.", "to come")
    return _r(max(best, cur) / n if n else 0, f"Best run so far {best}; {cur} in a row now.", "under way")


# --------------------------------------------------------------------------- player goals
def _ids(career, fmt: str, year) -> list:
    m = career.matches
    sea = april_seasons_of(career)
    return [i for i in m[m.format == fmt].match_id if int(sea.get(i, -1)) == int(year)]


def _topscorer(career, goal: dict) -> dict:
    p, sec, sea, what = goal.get("player", ""), goal.get("section", ""), str(goal.get("season", "")), goal.get("what", "runs")
    here = _section_games(career, sec, sea)
    if here.empty:
        return _r(0, "Not started yet.", "to come")
    t = career.batting if what == "runs" else career.bowling
    col = "runs" if what == "runs" else "wickets"
    tot = t[t.match_id.isin(here.match_id)].groupby("player")[col].sum().sort_values(ascending=False)
    unit = "runs" if what == "runs" else "wickets"
    if tot.empty or tot.iloc[0] <= 0:
        return _r(0, f"No {unit} yet.", "to come")
    top, mine = int(tot.iloc[0]), int(tot.get(p, 0))
    leaders = sorted(tot[tot == top].index)
    over = _status(career, sec, sea) == "complete"
    if p in leaders:
        shared = f" (level with {', '.join(x for x in leaders if x != p)})" if len(leaders) > 1 else ""
        return _r(1, f"Top with {mine:,} {unit}{shared}.", "achieved" if over else "on course")
    rank = int((tot > mine).sum()) + 1
    text = f"{ordinal(rank)} with {mine:,} {unit}, {top - mine:,} behind {leaders[0]} ({top:,})."
    return _r(mine / top if top else 0, text, "missed" if over else "at risk")


def _average(career, goal: dict) -> dict:
    p, fmt, year, target = goal.get("player", ""), goal.get("format", ""), int(goal.get("season") or 0), float(goal.get("target") or 0)
    bat = goal.get("what") == "batting"
    ids = _ids(career, fmt, year)
    over = _april_over(career, year)
    if bat:
        b = career.batting[career.batting.match_id.isin(ids) & (career.batting.player == p) & career.batting.did_bat]
        n, runs, outs = len(b), int(b.runs.sum()), int(b.out.astype(bool).sum())
        avg = runs / outs if outs else np.nan
        shown = f"{avg:.2f}" if np.isfinite(avg) else "no average yet (never out)"
        text = f"Averaging {shown} from {n} innings ({runs:,} runs)"
        enough = n >= MIN_INNINGS
        good = np.isfinite(avg) and avg >= target
        done = (avg / target if np.isfinite(avg) and target else (1.0 if runs and not outs else 0.0))
    else:
        b = career.bowling[career.bowling.match_id.isin(ids) & (career.bowling.player == p)]
        n, runs, wk = b.match_id.nunique(), int(b.runs.sum()), int(b.wickets.sum())
        avg = runs / wk if wk else np.nan
        shown = f"{avg:.2f}" if np.isfinite(avg) else "no average yet (no wickets)"
        text = f"Averaging {shown} from {n} match{'es' if n != 1 else ''} ({wk} wickets)"
        enough = n >= MIN_INNINGS
        good = np.isfinite(avg) and avg <= target
        done = target / avg if np.isfinite(avg) and avg else 0.0
    if n == 0:
        return _r(0, "Not played yet.", "missed" if over else "to come")
    if not enough:
        done = min(done, 0.95)
    need = "" if enough else f"; needs {MIN_INNINGS - n} more {'innings' if bat else 'matches'} to count"
    text += need + "."
    if over:
        return _r(1, text, "achieved") if good and enough else _r(done, text, "missed")
    return _r(done, text, "on course" if good else "at risk")


def _hauls(career, goal: dict) -> dict:
    p, fmt, year, n = goal.get("player", ""), goal.get("format", ""), int(goal.get("season") or 0), int(goal.get("target") or 0)
    ids = _ids(career, fmt, year)
    if goal.get("what") == "hundreds":
        b = career.batting[career.batting.match_id.isin(ids) & (career.batting.player == p)]
        got, unit = int((b.runs >= 100).sum()), "hundred"
    else:
        b = career.bowling[career.bowling.match_id.isin(ids) & (career.bowling.player == p)]
        got, unit = int((b.wickets >= 5).sum()), "five-for"
    text = f"{got} {unit}{'s' if got != 1 else ''} of {n}"
    if n and got >= n:
        return _r(1, text + ".", "achieved")
    if _april_over(career, year):
        return _r(got / n if n else 0, text + ".", "missed")
    return _r(got / n if n else 0, text + " so far.", "under way" if got else "to come")


# --------------------------------------------------------------------------- the choices a goal can be made from
def choices(career, team: str) -> dict:
    """What the goal form offers for a team: its competitions (with their seasons, newest first), its formats with
    April-to-March seasons, its opponents, its players, and the rating sections."""
    m = career.matches
    mine = m[(m.home == team) | (m.away == team)]
    from .competitions import ordered
    secs = [s for s in ordered(m, list(mine.section.unique()))]
    leagues = [s for s in secs if mine[mine.section == s].level.iloc[0] not in ("International", "Exhibition", "Tour")
               or mine[mine.section == s].knockout.astype(bool).any()]
    by_sec = {s: [str(x) for x in sorted(mine[mine.section == s].season.unique(), key=str, reverse=True)] for s in secs}
    sea = april_seasons_of(career)
    years = sorted({int(sea.get(i)) for i in mine.match_id if i in sea.index}, reverse=True)
    last = m.date.max()
    if pd.notna(last):
        from .seasonal import april_year
        now = april_year(last)
        years = sorted(set(years) | {now, now + 1}, reverse=True)
    fmts = [f for f in ("Test", "ODI", "T20I", "First-class", "List A", "T20", "The Hundred") if (mine.format == f).any()]
    opps = sorted((set(mine.home) | set(mine.away)) - {team})
    b = career.batting[career.batting.team == team]
    order = b.groupby("player").match_id.nunique().sort_values(ascending=False)
    return dict(sections=secs, leagues=leagues, seasons=by_sec, years=[dict(v=str(y), label=april_label(y)) for y in years],
                formats=fmts, opponents=opps, players=list(order.index))


# --------------------------------------------------------------------------- suggested each season
def suggested(career, team: str, goals: list[dict], tracked: pd.DataFrame | None = None) -> list[dict]:
    """Goals worth setting for the season under way (or about to start), from what the team plays: win each
    competition it's in this season, reach its knockouts, unbeaten at home and an away series win in each format
    with games this season, beat the side it does worst against, and the top run-scorer and wicket-taker goals for
    its leading batter and bowler. Ones already set are left out."""
    from .seasonal import april_year
    m = career.matches
    last = m.date.max()
    if pd.isna(last):
        return []
    year = april_year(last)
    sea = april_seasons_of(career)
    mine = m[((m.home == team) | (m.away == team))]
    now = mine[[int(sea.get(i, -1)) == year for i in mine.match_id]]
    have = {_key(g) for g in goals}
    out: list[dict] = []

    def add(g: dict) -> None:
        if _key(g) not in have and _key(g) not in {_key(x) for x in out}:
            out.append(g)

    for sec in now.section.unique():
        s = now[now.section == sec]
        season = str(s.season.iloc[-1])
        if _status(career, sec, season) == "complete":
            continue
        if s.level.iloc[0] not in ("International", "Exhibition", "Tour"):
            add(dict(kind="title", team=team, section=sec, season=season))
            if s.knockout.astype(bool).sum() == 0 and len(m[(m.section == sec) & m.knockout.astype(bool)]):
                add(dict(kind="top", team=team, section=sec, season=season, n=0))
        t = career.batting[career.batting.match_id.isin(s.match_id) & (career.batting.team == team)]
        if len(t):
            add(dict(kind="topscorer", player=t.groupby("player").runs.sum().idxmax(), team=team, section=sec,
                     season=season, what="runs"))
        w = career.bowling[career.bowling.match_id.isin(s.match_id) & (career.bowling.team == team)]
        if len(w) and w.wickets.sum() > 0:
            add(dict(kind="topscorer", player=w.groupby("player").wickets.sum().idxmax(), team=team, section=sec,
                     season=season, what="wickets"))
    for fmt in now.format.unique():
        g = _team_games(career, team, fmt, year)
        if (g.venue == "home").any() and not (g[g.venue == "home"].outcome == "L").any():
            add(dict(kind="home", team=team, format=fmt, season=str(year)))
        if any(not s["done"] for s in _away_series(career, team, fmt, year)):
            add(dict(kind="away", team=team, format=fmt, season=str(year)))
    from .planning import rivalry
    for fmt in now.format.unique():
        opps = set(now[now.format == fmt].home) | set(now[now.format == fmt].away)
        for opp in sorted(opps - {team}):
            rv = rivalry(career, team, opp, fmt)
            if rv and rv["kind"] == "bogey":
                add(dict(kind="rival", team=team, opponent=opp, format=fmt, season=str(year)))
    return out


def _key(g: dict) -> tuple:
    return tuple(sorted((k, str(v)) for k, v in g.items() if k not in ("id", "since")))
