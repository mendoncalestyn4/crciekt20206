"""On this day (stage 5, your answers of 26 November), on My team: what happened to your team on this date in earlier
seasons, by the game's calendar ("today" is the date of the career's latest match, the date at the top of every page).
Shown only when something happened on exactly that day and month in an earlier year; otherwise nothing at all.

What counts: every match your team played that day (its result), and its players' hundreds and five-wicket hauls
(four in a T20) in those matches."""

from __future__ import annotations

import pandas as pd

from .stats import KIND

HAUL = {"multi": 5, "one": 5, "t20": 4}


def today(career) -> pd.Timestamp | None:
    d = career.matches.date.dropna()
    return d.max() if len(d) else None


def on_this_day(career, team: str, when: pd.Timestamp | None = None) -> list[dict]:
    """Earlier years' matches of `team` on this day and month, newest first, each with its big moments."""
    when = today(career) if when is None else pd.Timestamp(when)
    if when is None:
        return []
    m = career.matches
    g = m[((m.home == team) | (m.away == team)) & m.date.notna()]
    g = g[(g.date.dt.month == when.month) & (g.date.dt.day == when.day) & (g.date.dt.year < when.year)]
    out = []
    for r in g.sort_values(["date", "match_id"], ascending=[False, True]).itertuples():
        kind = KIND.get(r.format, "one")
        bat = career.batting[(career.batting.match_id == r.match_id) & (career.batting.team == team)]
        bowl = career.bowling[(career.bowling.match_id == r.match_id) & (career.bowling.team == team)]
        moments = [f"{b.player} {int(b.runs)}{'*' if not bool(b.out) else ''}" for b in
                   bat[bat.runs >= 100].sort_values("runs", ascending=False).itertuples()]
        moments += [f"{w.player} {int(w.wickets)}/{int(w.runs)}" for w in
                    bowl[bowl.wickets >= HAUL[kind]].sort_values(["wickets", "runs"], ascending=[False, True]).itertuples()]
        opp = r.away if r.home == team else r.home
        word = ("won" if r.winner == team else "lost" if r.loser == team else
                "no result" if r.result_type == "no result" else "drew" if r.result_type == "draw" else "tied")
        out.append(dict(id=r.match_id, date=r.date, years=int(when.year - r.date.year), section=r.section,
                        opponent=opp, outcome=word, result=str(r.result or ""), moments=moments))
    return out
