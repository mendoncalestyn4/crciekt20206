"""Season (stage 2): a whole season, April to March, on one calendar (every result, and your fixtures still to come);
every bilateral series and how it stands (with each side's chance of winning the ones still going); and how far each
competition has got: as the current site's Season page shows them, with the same engine functions and words."""

from __future__ import annotations

import calendar as CAL

import pandas as pd

from ccstats import fixtures as FX
from ccstats import rankings as R
from ccstats import tables as T
from ccstats import winprob as WP
from ccstats.competitions import shown_name

from . import styleguide as SG
from .cache import kept
from .teampage import table

TABS = ["Calendar", "Series tracker", "Season progress"]
SEASON_MONTHS = [4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3]   # April to March
SHORT = {"Test": "T", "ODI": "O", "T20I": "20", "T20": "20", "The Hundred": "100", "List A": "LA", "First-class": "FC"}
VENUE_WORD = {"home": "at home", "away": "away", "neutral": "neutral venue"}
ALL = "All teams"


def season_of(d) -> int:
    """The year a season starts in: April 2026 to March 2027 is the 2026 season."""
    d = pd.Timestamp(d)
    return d.year if d.month >= 4 else d.year - 1


def season_label(y: int) -> str:
    return f"{y}–{str(y + 1)[-2:]} (Apr {y} – Mar {y + 1})"


def page(career, q: dict, mine: list[str], sched: list[dict]) -> dict:
    m = career.matches
    teams = sorted(set(m.home) | set(m.away))
    team = q.get("team", "")
    if team != ALL and team not in teams:
        team = next((t for t in mine if t in teams), ALL)
    tab = q.get("tab", "") if q.get("tab", "") in TABS else TABS[0]
    out = dict(teams=[ALL] + teams, team=team, tabs=TABS, tab=tab, none="")
    if m.empty:
        out["none"] = "No matches yet."
        return out
    if tab == "Calendar":
        out["calendar"] = _calendar(career, team, q, sched)
    elif tab == "Series tracker":
        out["series"] = kept(career, ("series-tracker", team), lambda: _series(career, team))
    else:
        out["progress"] = kept(career, ("season-progress", team), lambda: _progress(career, team))
    return SG.clean(out)


def _tracked(career, team, sched):
    if team == ALL:
        return None
    try:
        t = FX.track(career, sched, auto=(team,))
    except Exception:  # noqa: BLE001 - a schedule that can't be read never stops the calendar
        return None
    return t[(t.team == team) & t.status.isin(["to come", "next"])] if len(t) else None


def _calendar(career, team, q, sched) -> dict:
    m = career.matches
    games = m if team == ALL else m[(m.home == team) | (m.away == team)]
    todo = _tracked(career, team, sched)
    dates = list(games.date) + (list(todo.anchor.dropna()) if todo is not None and "anchor" in todo else [])
    seasons = sorted({season_of(d) for d in dates if pd.notna(d)}, reverse=True)
    out: dict = dict(view="month" if q.get("view") == "month" else "season", seasons=[
        dict(key=str(y), label=season_label(y)) for y in seasons], season="", months=[], month="", today="")
    if not seasons:
        out["none"] = "No matches yet."
        return out
    latest = games.date.max() if len(games) else None
    nxt = todo.anchor.min() if todo is not None and len(todo) and todo.anchor.notna().any() else None
    now = season_of(nxt) if nxt is not None else season_of(latest) if latest is not None else seasons[0]
    y = int(q["season"]) if str(q.get("season", "")).isdigit() and int(q["season"]) in seasons else (now if now in seasons else seasons[0])
    out["season"] = str(y)
    if pd.notna(m.date.max()):
        out["today"] = f"{m.date.max():%Y-%m-%d}"
    months_all = sorted({(d.year, d.month) for d in games.date}
                        | ({(a.year, a.month) for a in todo.anchor.dropna()} if todo is not None else set()), reverse=True)
    out["months"] = [dict(key=f"{yy}-{mm:02d}", label=f"{CAL.month_name[mm]} {yy}") for yy, mm in months_all]
    if out["view"] == "month":
        keys = [x["key"] for x in out["months"]]
        mk = q.get("month", "") if q.get("month", "") in keys else (f"{latest:%Y-%m}" if latest is not None else keys[-1])
        out["month"] = mk
        yy, mm = int(mk[:4]), int(mk[5:])
        out["grid"] = [_month(career, team, games, todo, yy, mm)]
    else:
        out["grid"] = [_month(career, team, games, todo, yy, mm) for yy, mm in
                       [(y if mo >= 4 else y + 1, mo) for mo in SEASON_MONTHS]]
    span = games[games.date.map(lambda d: season_of(d) == y)] if out["view"] == "season" else \
        games[(games.date.dt.year == int(out["month"][:4])) & (games.date.dt.month == int(out["month"][5:]))]
    when = season_label(y) if out["view"] == "season" else CAL.month_name[int(out["month"][5:])] + " " + out["month"][:4]
    if team != ALL:
        w = int((span.winner == team).sum())
        lost = int(((span.winner != team) & (span.winner != "")).sum())
        out["caption"] = (f"{team} in {when}: played {len(span)}, won {w}, lost {lost}. Green: won · red: lost · grey: drawn, "
                          "tied or no result · dashed: still to come (from your schedule; a series without dates is listed at "
                          "the top of its month). T = Test, O = ODI, 20 = T20. Click a result for its scorecard.")
    else:
        out["caption"] = (f"{len(span)} matches in {when}. Hover a day for its games; pick a team to see its results and "
                          "fixtures to come.")
    return out


def _month(career, team, games, todo, yy: int, mm: int) -> dict:
    """One month: each day's chips (a result, a game to come, or for every team a count) and the month's notes."""
    g = games[(games.date.dt.year == yy) & (games.date.dt.month == mm)].sort_values(["date", "match_id"])
    days: dict[int, list[dict]] = {}
    notes: list[dict] = []
    if team == ALL:
        for d, x in (g.groupby(g.date.dt.day) if len(g) else []):
            tip = "\n".join(f"{r.home} v {r.away} · {r.result}" for r in x.itertuples())
            r0 = x.iloc[0]
            days[int(d)] = [dict(kind="N", text="1 game" if len(x) == 1 else f"{len(x)} games", tip=tip,
                                 id=r0.match_id if len(x) == 1 else None,
                                 games=[dict(id=r.match_id, text=f"{r.home} v {r.away}", result=r.result) for r in x.itertuples()])]
    else:
        for r in g.itertuples():
            opp = r.away if r.home == team else r.home
            o = FX._outcome(r, team)
            venue = "neutral" if r.neutral else ("home" if r.home == team else "away")
            days.setdefault(r.date.day, []).append(dict(
                kind=o, text=f"{o}" + ("" if o == "NR" else f" {SHORT.get(r.format, r.format[:2])}"), opp=opp,
                tip=f"v {opp} · {r.format} · {VENUE_WORD[venue]} · {r.result}", id=r.match_id,
                long=f"{o} v {opp}", event=shown_name(r.section, r.event)))
        # who they played that month: "v Afghanistan · Tests 0–1", "Indian Premier League 5–3"
        parts: dict = {}
        for r in g.itertuples():
            opp = r.away if r.home == team else r.home
            bilateral = r.competition in ("Test", "ODI", "T20I") or r.series_id
            who = f"v {opp}" if bilateral else shown_name(r.section, r.event)
            k = (who, FX.plural(r.format, 2).split(" ", 1)[1] if bilateral else "")
            parts.setdefault(k, []).append(FX._outcome(r, team))
        for (who, fm), outs in parts.items():
            w, lo = outs.count("W"), outs.count("L")
            other = [f"{outs.count(k)} {k}" for k in ("D", "T", "NR") if outs.count(k)]
            notes.append(dict(kind="played", text=f"{who}{' · ' + fm if fm else ''} {w}–{lo}" + (f" ({', '.join(other)})" if other else "")))
        if todo is not None and len(todo):
            by: dict = {}
            for _, r in todo.iterrows():
                who = r["opponent"] or ""
                if r["date"]:
                    d = pd.Timestamp(r["date"])
                    if (d.year, d.month) == (yy, mm):
                        days.setdefault(d.day, []).append(dict(
                            kind="UP", text=f"{SHORT.get(r['format'], str(r['format'])[:2])} {(who or r['series'])[:3]}",
                            tip=f"v {who} · {r['format']} · {VENUE_WORD.get(r['venue'], '')} · to come".replace(" ·  ·", " ·"),
                            id=None, long=f"⏳ v {who or r['series'].replace(FX.AUTO, '')}"))
                    continue
                anchor = r["anchor"] if pd.notna(r.get("anchor")) else (FX._month_start(r["month"]) if r["month"] else pd.NaT)
                if pd.notna(anchor) and (anchor.year, anchor.month) == (yy, mm):
                    by.setdefault(r["series"].replace(FX.AUTO, ""), []).append(r)
            for name, rows in by.items():
                stage = next((x.get("stage") for x in rows if isinstance(x.get("stage"), str) and x.get("stage")), "")
                left = len(rows)
                what = (f"{stage} to come" if stage else f"{left} match{'es' if left != 1 else ''} to come"
                        if rows[0]["kind"] == "match" else "to come")
                notes.append(dict(kind="tocome", text=f"⏳ {name} · {what}, dates to come"))
    first = (CAL.weekday(yy, mm, 1))   # Monday 0
    played = [c for v in days.values() for c in v if c["kind"] in ("W", "L", "D", "T", "NR")]
    return dict(key=f"{yy}-{mm:02d}", year=yy, month=mm, name=CAL.month_name[mm], first=first,
                days_in=CAL.monthrange(yy, mm)[1], days={str(k): v for k, v in days.items()}, notes=notes,
                won=sum(c["kind"] == "W" for c in played), lost=sum(c["kind"] == "L" for c in played),
                played=len(played) if team != ALL else int(len(g)))


def _series(career, team) -> dict:
    m = career.matches
    bil = m[m.series_id != ""]
    if team != ALL:
        bil = bil[(bil.home == team) | (bil.away == team)]
    if bil.empty:
        return dict(none="No bilateral series" + ("" if team == ALL else f" for {team}") + " yet.")
    sr = T.series_table(career, bil.match_id)
    sec_of = bil.groupby("series_id").section.first()
    sr = sr.assign(section=sr.series_id.map(sec_of))
    live, done = sr[sr.played < sr.length], sr[sr.played >= sr.length]
    out: dict = dict(none="", live=None, done=None)
    if len(live):
        rows = []
        for r in live.itertuples():
            g = m[m.match_id.isin(r.match_ids)]
            a, b = g.home.iloc[0], g.away.iloc[0]
            wa, wb = int((g.winner == a).sum()), int((g.winner == b).sum())
            elo, _ = R.team_elo(career, r.section)
            e = elo.set_index("team").elo
            p = 1 / (1 + 10 ** ((e.get(b, 1500) - e.get(a, 1500)) / 400))
            dr = WP.draw_rate(career, m[m.section == r.section].match_id) if r.section == "Tests" else 0.0
            odds = WP.series_odds(p * (1 - dr), dr, wa, wb, int(r.length - r.played))
            rows.append([f"{r.start:%d %b %Y}", r.section, r.teams, r.score, f"{r.played} of {r.length}",
                         f"{a} {odds['A']:.0f}% · " + (f"drawn {odds['level']:.0f}% · " if odds["level"] >= 0.5 else "")
                         + f"{b} {odds['B']:.0f}%", r.top_runs, r.top_wickets])
        out["live"] = table(["Started", "Format", "Series", "Score", "Played", "Series chances", "Top runs", "Top wickets"], rows)
        out["live"]["note"] = ("Series chances: every way the games left could go, each game won by the side with the higher "
                               "Elo rating more often (and drawn as often as Tests here are drawn).")
    out["done"] = table(["Started", "Format", "Series", "Score", "Result", "Top runs", "Top wickets"],
                        [[f"{r.start:%d %b %Y}", r.section, r.teams, r.score, r.result, r.top_runs, r.top_wickets]
                         for r in done.itertuples()],
                        hi=[team != ALL and r.result.startswith(team) for r in done.itertuples()]) if len(done) else None
    out["note"] = ("A series counts as finished once all its matches (the number in the match titles, e.g. '3rd of 5') are "
                   "in.")
    return out


def _progress(career, team) -> dict:
    m = career.matches
    rows = []
    for event, season in m.groupby("event").season.max().items():
        g = m[(m.event == event) & (m.season == season)]
        if g.competition.iloc[0] in T.BILATERAL:
            continue
        if team != ALL and not ((g.home == team) | (g.away == team)).any():
            continue
        older = m[(m.event == event) & (m.season < season)]
        full = int(older.groupby("season").size().max()) if len(older) else None
        ko, final = g[g.knockout], g[g.stage == "Final"]
        if len(final) == 1 and (final.winner.iloc[0] or final.tiebreak_winner.iloc[0]):
            stage = f"Finished: {final.winner.iloc[0] or final.tiebreak_winner.iloc[0]} won"
        elif len(ko):
            stage = f"Knockouts ({ko.sort_values('date').stage.iloc[-1]})"
        else:
            stage = "League stage"
        lt = T.league_tables(career, g.match_id)
        leader = ", ".join(t.team.iloc[0] for _, t, _ in lt if len(t)) if lt else "–"
        pct = min(len(g) / full * 100, 100) if full else None
        rows.append(dict(name=f"{shown_name(g.section.iloc[0], event)} {season}", event=str(event), season=str(season),
                         played=f"{len(g)} of about {full} matches" if full else f"{len(g)} match{'es' if len(g) != 1 else ''} so far",
                         pct=None if pct is None else round(pct, 1), stage=stage, leader=leader))
    rows.sort(key=lambda r: (-int(str(r["season"])[:4]), r["name"]))
    if not rows:
        return dict(none="No competitions running" + ("" if team == ALL else f" with {team}") + ".", rows=[])
    return dict(none="", rows=rows, note="'About' uses the number of matches in the last full season of the same "
                                         "competition; a first season shows matches so far.")
