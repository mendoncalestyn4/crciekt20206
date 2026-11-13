"""Rivalries (stage 2): every pair of teams that have met in a competition, the record between them, and who has done
best in those games, as the current site's Rivalries page shows it."""

from __future__ import annotations

from ccstats import extras as E
from ccstats.stats import Scope

from . import styleguide as SG
from .cache import kept
from .teampage import choices, fmt, table


def page(career, q: dict, mine: list[str]) -> dict:
    m = career.matches
    ch = choices(career)
    if not ch:   # a career made before any game was played
        return SG.clean(dict(choices=[], section="", pairs=[], pick="",
                             none=SG.NO_MATCHES))
    secs = [c["section"] for c in ch]
    section = q.get("section", "")
    if section not in secs:
        section = secs[0]
    ids = Scope(sections=[section]).match_ids(m)
    rv = kept(career, ("rivalries", section), lambda: E.rivalries(career, ids))
    out = dict(choices=ch, section=section, none="", pairs=[], pick="")
    if rv.empty:
        out["none"] = "No matches here yet."
        return SG.clean(out)
    show = rv.head(30)
    out["table"] = table(["Rivalry", "Played", "Won", "Last 5 (oldest first)", "Last met"],
                         [[f"{a} v {b}", int(p), f"{wa} – {wb}" + (f" ({o} other)" if o else ""),
                           " ".join({"A": "◀", "B": "▶", "–": "·"}[x] for x in last), f"{d:%d %b %Y}"]
                          for a, b, p, wa, wb, o, last, d in zip(show.team_a, show.team_b, show.played, show.wins_a, show.wins_b,
                                                                  show.other, show.last5, show["last"])], num={1})
    out["table"]["note"] = ("Won: wins for the first-named team – wins for the second. Last 5: ◀ = the first-named team won, "
                            "▶ = the second-named team won, · = draw, tie or no result.")
    keys = [f"{a}|{b}" for a, b in zip(rv.team_a, rv.team_b)]
    out["pairs"] = [dict(key=k, label=f"{a} v {b} ({p})") for k, a, b, p in zip(keys, rv.team_a, rv.team_b, rv.played)]
    pick = q.get("pick", "")
    if pick not in keys:   # one of your teams' rivalries first, else the most played
        pick = next((k for k in keys if set(k.split("|")) & set(mine)), keys[0])
    out["pick"] = pick
    a, b = pick.split("|")
    out["close"] = kept(career, ("rivalry", section, pick), lambda: _close(career, ids, a, b))
    return SG.clean(out)


def _close(career, ids, a, b) -> dict:
    m = career.matches
    out: dict = {"missing": {}, "a": a, "b": b}

    def part(name, fn):
        try:
            out[name] = SG.clean(fn())
        except Exception as e:  # noqa: BLE001 - one part that can't be worked out never stops the others
            out[name] = None
            out["missing"][name] = f"Couldn't be worked out ({type(e).__name__}: {e})"
    runs, wkts = E.rivalry_players(career, ids, a, b)

    def most_runs():
        top = runs.head(10)
        if top.empty:
            return None
        tr = int(runs.runs.sum())
        return dict(rows=[dict(player=p, team=t, runs=int(r), note=f"{i} innings · average {fmt(av, 1)}")
                          for p, t, r, i, av in zip(top.player, top.team, top.runs, top.innings, top.average)],
                    shows=f"{top.player.iloc[0]} has {top.runs.iloc[0]} runs in these games, "
                          f"{top.runs.iloc[0] / max(tr, 1) * 100:.0f}% of the {tr} scored by everyone in them.",
                    for_="The batters who love this fixture.")
    part("runs", most_runs)

    def most_wickets():
        top = wkts.head(10)
        if top.empty:
            return None
        tw = int(wkts.wickets.sum())
        return dict(rows=[dict(player=p, team=t, wickets=int(w), note=f"average {fmt(av, 1)} · {bl} balls")
                          for p, t, w, av, bl in zip(top.player, top.team, top.wickets, top.average, top.balls)],
                    shows=f"{top.player.iloc[0]} has {int(top.wickets.iloc[0])} wickets in these games, "
                          f"{top.wickets.iloc[0] / max(tw, 1) * 100:.0f}% of the {tw} taken.",
                    for_="The bowlers who do the damage in this fixture.")
    part("wickets", most_wickets)

    def meetings():
        g = m[m.match_id.isin(ids) & (((m.home == a) & (m.away == b)) | ((m.home == b) & (m.away == a)))].sort_values(
            "date", ascending=False)
        return table(["Date", "Stage", "Home", "Away", "Result"],
                     [[f"{d:%d %b %Y}", s or "", h, w, r] for d, s, h, w, r in zip(g.date, g.stage, g.home, g.away, g.result)],
                     links=list(g.match_id))
    part("meetings", meetings)
    return out
