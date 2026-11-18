"""Rivalries (stage 2): every pair of teams that have met in a competition, the record between them, and who has done
best in those games, as the current site's Rivalries page shows it."""

from __future__ import annotations

from ccstats import extras as E
from ccstats.stats import Scope

from . import styleguide as SG
from .cache import kept
from .teampage import choices, fmt, named, secs_of, table


def page(career, q: dict, mine: list[str]) -> dict:
    m = career.matches
    ch = choices(career)
    if not ch:   # a career made before any game was played
        return SG.clean(dict(choices=[], section="", pairs=[], pick="",
                             none=SG.NO_MATCHES))
    # the competitions ticked, in the agreed order (several are counted together: your answer of 17 November)
    ticked = [c["section"] for c in ch if c["section"] in set(secs_of(q.get("section", "")))] or [ch[0]["section"]]
    section = "|".join(ticked)
    ids = Scope(sections=ticked).match_ids(m)
    rv = kept(career, ("rivalries", section), lambda: E.rivalries(career, ids))
    out = dict(choices=ch, section=section, ticked=ticked, name=named(section), none="", pairs=[], pick="")
    if rv.empty:
        out["none"] = "No matches here yet."
        return SG.clean(out)
    show = rv.head(30)
    out["table"] = table(["Rivalry", "Played", "Won", "Last 5 (oldest first)", "Run now", "Longest run", "Last met"],
                         [[f"{r.team_a} v {r.team_b}", int(r.played), f"{r.wins_a} – {r.wins_b}" + (f" ({r.other} other)" if r.other else ""),
                           " ".join({"A": "◀", "B": "▶", "–": "·"}[x] for x in r.last5), _run(r.current_team, r.current_n),
                           _run(r.longest_team, r.longest_n), f"{r.last:%d %b %Y}"] for r in show.itertuples()], num={1})
    out["table"]["badges"] = [0]
    out["table"]["note"] = ("Won: wins for the first-named team – wins for the second. Last 5: ◀ = the first-named team won, "
                            "▶ = the second-named team won, · = draw, tie or no result. Runs: wins in a row; a draw or a tie "
                            "ends a run, a no-result is skipped.")
    keys = [f"{a}|{b}" for a, b in zip(rv.team_a, rv.team_b)]
    out["pairs"] = [dict(key=k, label=f"{a} v {b} ({p})") for k, a, b, p in zip(keys, rv.team_a, rv.team_b, rv.played)]
    pick = q.get("pick", "")
    if pick not in keys:   # one of your teams' rivalries first, else the most played
        pick = next((k for k in keys if set(k.split("|")) & set(mine)), keys[0])
    out["pick"] = pick
    a, b = pick.split("|")
    r = rv[(rv.team_a == a) & (rv.team_b == b)].iloc[0]
    out["close"] = dict(kept(career, ("rivalry", section, pick), lambda: _close(career, ids, a, b)))   # a copy: the kept one stays as it is
    out["close"]["streak"] = dict(
        now=(f"{r.current_team} have won the last {r.current_n}" if r.current_n > 1 else
             f"{r.current_team} won the last one" if r.current_n == 1 else
             "No run going: their last game (no-results aside) was a draw or a tie"),
        longest=(f"Longest run: {r.longest_team}, {r.longest_n} in a row ({r.longest_from:%d %b %Y} to {r.longest_to:%d %b %Y})"
                 if r.longest_n > 1 else f"Longest run: {r.longest_team}, 1 (never two in a row)" if r.longest_n == 1
                 else "No wins yet: every game a draw, a tie or no result"),
        note="Wins in a row; a draw or a tie ends a run, a no-result is skipped.")
    return SG.clean(out)


def _run(team: str, n: int) -> str:
    return f"{team} {n}" if n else "–"


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
