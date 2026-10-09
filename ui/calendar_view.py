"""A cricket season on one screen: April to March, a small calendar per month, results and fixtures on their days,
and fixtures known only by their month in a box at the top of that month."""

from __future__ import annotations

import calendar
import datetime as dt

import pandas as pd

from .theme import esc

SEASON_MONTHS = [4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3]  # April to March


def season_of(d) -> int:
    """The year a season starts in: April 2026 to March 2027 is the 2026 season."""
    d = pd.Timestamp(d)
    return d.year if d.month >= 4 else d.year - 1


def season_label(y: int) -> str:
    return f"{y}–{str(y + 1)[-2:]} (Apr {y} – Mar {y + 1})"


def months_of(y: int) -> list[tuple[int, int]]:
    return [(y if mo >= 4 else y + 1, mo) for mo in SEASON_MONTHS]


def season_html(y: int, days: dict, notes: dict, today=None) -> str:
    """days: {date: [html chips]}; notes: {(year, month): [html blocks]}: what was played that month, and fixtures
    known only by their month."""
    cal = calendar.Calendar(firstweekday=0)
    head = "".join(f"<th>{d}</th>" for d in "MTWTFSS")
    boxes = []
    for yy, mo in months_of(y):
        rows = []
        for week in cal.monthdatescalendar(yy, mo):
            cells = []
            for d in week:
                if d.month != mo:
                    cells.append("<td class='out'></td>")
                    continue
                chips = days.get(d, [])
                cls = " class='today'" if today is not None and d == today else ""
                cells.append(f"<td{cls}><div class='d'>{d.day}</div>{''.join(chips)}</td>")
            rows.append("<tr>" + "".join(cells) + "</tr>")
        lines = notes.get((yy, mo), [])
        note = "".join(lines)
        busy = any(d.month == mo and d.year == yy for d in days) or lines
        boxes.append(f"<div class='mon{'' if busy else ' empty'}'><h4>{calendar.month_name[mo]} {yy}</h4>{note}"
                     f"<table class='cal mini'><thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>")
    return "<div class='calgrid'>" + "".join(boxes) + "</div>"


SHORT = {"Test": "T", "ODI": "O", "T20I": "20", "T20": "20", "The Hundred": "100", "List A": "LA", "First-class": "FC"}
VENUE_WORD = {"home": "at home", "away": "away", "neutral": "neutral venue"}


def team_chips(career, team: str, tracked: pd.DataFrame | None, y: int) -> tuple[dict, dict]:
    """A team's season: every match it played (W / L / D …, clickable) and its fixtures still to come (dashed;
    on their day when the date is known, otherwise in a box at the top of their month)."""
    from ccstats import fixtures as FX
    start, end = pd.Timestamp(year=y, month=4, day=1), pd.Timestamp(year=y + 1, month=4, day=1)
    m = career.matches
    g = m[((m.home == team) | (m.away == team)) & (m.date >= start) & (m.date < end)].sort_values(["date", "match_id"])
    days: dict = {}
    for r in g.itertuples():
        opp = r.away if r.home == team else r.home
        out = FX._outcome(r, team)
        venue = "neutral" if r.neutral else ("home" if r.home == team else "away")
        tip = f"v {opp} · {r.format} · {VENUE_WORD[venue]} · {r.result}"
        days.setdefault(r.date.date(), []).append(
            f"<a class='{out}' href='match?match={esc(r.match_id)}' target='_self' title='{esc(tip)}'>"
            f"{out}{'' if out == 'NR' else ' ' + esc(SHORT.get(r.format, r.format[:2]))}</a>")
    notes: dict = {}
    # who they played each month: "v Afghanistan · Test 0–1 · ODIs 2–1", "Indian Premier League · 5–3"
    for (yy, mo), x in (g.groupby([g.date.dt.year, g.date.dt.month], sort=True) if len(g) else []):
        parts: dict = {}
        for r in x.itertuples():
            opp = r.away if r.home == team else r.home
            bilateral = r.competition in ("Test", "ODI", "T20I") or r.series_id
            who = f"v {opp}" if bilateral else shown_event(r)
            k = (who, FX.plural(r.format, 2).split(" ", 1)[1] if bilateral else "")
            parts.setdefault(k, []).append(FX._outcome(r, team))
        bits = []
        for (who, fmt_), outs in parts.items():
            w, lo = outs.count("W"), outs.count("L")
            other = [f"{outs.count(k)} {k}" for k in ("D", "T", "NR") if outs.count(k)]
            score = f"{w}–{lo}" + (f" ({', '.join(other)})" if other else "")
            bits.append(f"{esc(who)}{' · ' + esc(fmt_) if fmt_ else ''} {score}")
        notes.setdefault((int(yy), int(mo)), []).append("<div class='ms'>" + " · ".join(bits) + "</div>")
    if tracked is not None and len(tracked):
        todo = tracked[(tracked.team == team) & tracked.status.isin(["to come", "next"])]
        by_month: dict = {}
        for _, r in todo.iterrows():
            who = r["opponent"] or ""
            if r["date"]:
                d = pd.Timestamp(r["date"])
                if start <= d < end:
                    tip = f"v {who} · {r['format']} · {VENUE_WORD.get(r['venue'], '')} · to come".replace(" ·  ·", " ·")
                    days.setdefault(d.date(), []).append(
                        f"<a class='UP' title='{esc(tip)}'>{esc(SHORT.get(r['format'], r['format'][:2]))} "
                        f"{esc((who or r['series'])[:3])}</a>")
                continue
            anchor = r["anchor"] if pd.notna(r.get("anchor")) else (FX._month_start(r["month"]) if r["month"] else pd.NaT)
            if pd.isna(anchor) or not (start <= anchor < end):
                continue
            key = (anchor.year, anchor.month)
            by_month.setdefault(key, {}).setdefault(r["series"].replace(FX.AUTO, ""), []).append(r)
        for key, series in by_month.items():
            for name, rows in series.items():
                stage = next((x.get("stage") for x in rows if isinstance(x.get("stage"), str) and x.get("stage")), "")
                left = len(rows)
                what = (f"{stage} to come" if stage else
                        f"{left} match{'es' if left != 1 else ''} to come" if rows[0]["kind"] == "match" else "to come")
                notes.setdefault(key, []).append(f"<div class='tc'>⏳ <b>{esc(name)}</b> · {esc(what)}, dates to come</div>")
    return days, notes


def all_teams_chips(career, y: int) -> dict:
    """Every match of a season by day: one chip per day saying how many (hover lists them)."""
    start, end = pd.Timestamp(year=y, month=4, day=1), pd.Timestamp(year=y + 1, month=4, day=1)
    m = career.matches
    g = m[(m.date >= start) & (m.date < end)].sort_values(["date", "match_id"])
    days: dict = {}
    for d, x in (g.groupby(g.date.dt.date) if len(g) else []):
        tip = "\n".join(f"{r.home} v {r.away} · {r.result}" for r in x.itertuples())
        if len(x) == 1:
            r = x.iloc[0]
            days[d] = [f"<a class='NR' href='match?match={esc(r.match_id)}' target='_self' title='{esc(tip)}'>1 game</a>"]
        else:
            days[d] = [f"<a class='N' title='{esc(tip)}'>{len(x)} games</a>"]
    return days


def shown_event(r) -> str:
    from ccstats.competitions import shown_name
    return shown_name(r.section, r.event)


def seasons_for(dates, extra_months=()) -> list[int]:
    """The seasons (by start year) with any of these dates or months ('2026-09'), newest first."""
    ys = {season_of(d) for d in dates if pd.notna(d)}
    for mth in extra_months:
        if mth:
            ys.add(season_of(pd.Timestamp(f"{mth}-01")))
    return sorted(ys, reverse=True)


def today_in_game(career) -> dt.date | None:
    """The day of the latest match: 'today' in the game."""
    d = career.matches.date.max()
    return None if pd.isna(d) else d.date()
