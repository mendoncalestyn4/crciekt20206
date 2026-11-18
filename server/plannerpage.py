"""Team planner (stage 2): plan your next game, as the current site's Team planner shows it: what you need to qualify,
a batting order from where each player does best, how to use your bowlers, who's knocking on the door and which
partnerships work. Every number comes from the same engine functions with the same words."""

from __future__ import annotations

from ccstats import players as PL
from ccstats import preview as PV
from ccstats import teamplay as TP
from ccstats.stats import Scope

from . import styleguide as SG
from .cache import kept
from .teampage import choices, fmt, table

NAMES = ["Qualification", "Batting order", "Bowling plan", "Knocking on the door", "Partnerships"]


def page(career, q: dict, mine: list[str]) -> dict:
    m = career.matches
    ch = choices(career)
    if not ch:   # a career made before any game was played
        return SG.clean(dict(choices=[], section="", season="", teams=[], team="", tabs=[], tab="",
                             none=SG.NO_MATCHES, tip=""))
    secs = [c["section"] for c in ch]
    section = q.get("section", "")
    if section not in secs:   # a competition your team plays in
        section = next((s for s in secs if set(m[m.section == s].home) & set(mine) or set(m[m.section == s].away) & set(mine)),
                       secs[0])
    seasons = next(c["seasons"] for c in ch if c["section"] == section)
    season = q.get("season", "") if q.get("season", "") in seasons else "All seasons"
    ids = Scope(sections=[section], seasons=[] if season == "All seasons" else [season]).match_ids(m)
    here = m[m.match_id.isin(ids)]
    teams = sorted(set(here.home) | set(here.away))
    out = dict(choices=ch, section=section, season=season, teams=teams, team="", tabs=[], tab="", none="",
               tip="" if mine else "Tip: pick your team(s) on the current site (My team) and every page opens on them.")
    if not teams:
        out["none"] = "No matches here yet."
        return SG.clean(out)
    team = q.get("team", "")
    if team not in teams:
        team = next((t for t in mine if t in teams), teams[0])
    evs = here[~here.knockout & (here.home.eq(team) | here.away.eq(team))]
    options = sorted({(e, str(s_)) for e, s_ in zip(evs.event, evs.season)}, key=lambda x: (x[1], x[0]), reverse=True)
    options = [o for o in options if TP.has_knockouts(career, o[0])]
    names = NAMES if options else NAMES[1:] + NAMES[:1]
    tab = q.get("tab", "") if q.get("tab", "") in names else names[0]
    out.update(team=team, tabs=names, tab=tab)
    key = (section, season, team, tab)
    if tab == "Qualification":
        ev_label = q.get("event", "")
        labels = [f"{e} {s}" for e, s in options]
        ev = options[labels.index(ev_label)] if ev_label in labels else (options[0] if options else None)
        out["body"] = _qualification(career, team, options, ev, q.get("games", ""), q.get("places", ""))
    elif tab == "Batting order":
        recent = q.get("recent", "1") != "0"
        out["body"] = kept(career, ("planner",) + key + (recent,), lambda: _batting(career, ids, team, recent))
    else:
        out["body"] = kept(career, ("planner",) + key, lambda: {"Bowling plan": _bowling, "Knocking on the door": _knocking,
                                                               "Partnerships": _pairs}[tab](career, ids, team))
    return SG.clean(out)


def _parts():
    out = {"missing": {}}

    def part(name, fn):
        try:
            out[name] = SG.clean(fn())
        except Exception as e:  # noqa: BLE001 - one part that can't be worked out never stops the others
            out[name] = None
            out["missing"][name] = f"Couldn't be worked out ({type(e).__name__}: {e})"
    return out, part


def _int(v, lo, hi, default):
    try:
        return max(lo, min(hi, int(v)))
    except (TypeError, ValueError):
        return default


def _qualification(career, team, options, ev, games_q, places_q) -> dict:
    out, part = _parts()
    if not options:
        out["none"] = ("Nothing to qualify for here: no knockout stage (bilateral series, or a league the table decides). "
                       "The other tabs are for your next game.")
        return out

    def qual():
        d = TP.qualification_defaults(career, *ev)
        d = dict(d, places=d["places"] + (1 if d.get("extra") else 0))
        games, places = _int(games_q, 1, 60, d["games"]), _int(places_q, 1, 16, d["places"])
        q = kept(career, ("qualification", ev, games, places), lambda: TP.qualification(career, ev[0], ev[1], games, places))
        res = dict(events=[f"{e} {s}" for e, s in options], event=f"{ev[0]} {ev[1]}", games=games, places=places,
                   default_games=d["games"], default_places=d["places"], line="", table=None,
                   note=f"Guesses you can change above: {d['games']} league games each and {d['places']} going through, from "
                        "an earlier season of this competition where there is one. 'Through' and 'out' only when points alone "
                        "settle it (net run rate can split teams level on points). 'Needs' aims at the points the team in the "
                        "last qualifying place is on course for.")
        if q.empty:
            res["none"] = "No league table here yet."
            return res
        grp = q[q.team == team].group.iloc[0] if (q.team == team).any() else q.group.iloc[0]
        g = q[q.group == grp]
        me = g[g.team == team]
        if len(me):
            r = me.iloc[0]
            res["line"] = {"Through": f"✅ {team} are through on points alone.",
                           "Out": f"❌ {team} can't reach the top {places} any more.",
                           "Alive": f"🔶 {team} are still in it: {r.need} to reach the usual cut."}[r.status]
        res["table"] = table(["#", "Team", "Played", "Points", "Left", "Most possible", "Status", "Needs"],
                             [[int(r.position), r.team, int(r.played), fmt(r.points, 0), int(r.left), fmt(r.max_points, 0),
                               {"Through": "✅ Through", "Out": "❌ Out", "Alive": "🔶 Alive"}[r.status], r.need]
                              for r in g.itertuples()], num={0, 2, 3, 4, 5}, hi=[t == team for t in g.team])
        return res
    part("qualification", qual)
    return out


def _batting(career, ids, team, only_recent) -> dict:
    out, part = _parts()
    out["recent"] = only_recent

    def order_():
        order = PL.batting_order(career, ids, team)
        if order.empty:
            return dict(none="No innings yet.")
        recent = sorted(PV.recent_xi(career, ids, team, games=5))
        sug = PL.suggested_order(order, recent if only_recent else None)
        top7 = (table(["", "Player", "From innings at", "Runs v average", "Inns"],
                      [[r.slot, r.player, r.group, f"{r.vs_avg:+.1f}", int(r.innings)] for r in sug.itertuples()], num={3, 4})
                if len(sug) else None)
        show = order.sort_values(["player", "group"])
        if only_recent:
            show = show[show.player.isin(recent)]
        every = table(["Player", "Position", "Inns", "Runs per inns", "SR", "v average"],
                      [[r.player, r.group, int(r.innings), fmt(r.per_innings, 1), fmt(r.strike_rate, 1), f"{r.vs_avg:+.1f}"]
                       for r in show.itertuples()], num={2, 3, 4, 5}, hi=[r.group == r.best for r in show.itertuples()],
                      parts=[dict(runs=int(r.runs), bf=int(r.balls), inns=int(r.innings)) for r in show.itertuples()])
        return dict(none="", top7=top7, every=every)
    part("order", order_)
    return out


def _bowling(career, ids, team) -> dict:
    out, part = _parts()

    def plan():
        bp = PL.bowling_plan(career, ids, team)
        if bp.empty:
            return dict(none="No bowler has bowled 30+ balls yet.")
        by_avg = bp.attrs.get("by_average", False)
        t = table(["Bowler", "Inns", "Wkts", "Top 3", "4-7", "8-11", "Avg" if by_avg else "Econ", "SR", "Use as"],
                  [[r.player, int(r.innings), int(r.wickets), int(r.top), int(r.middle), int(r.tail),
                    fmt(r.economy, 2) if not by_avg else fmt(r.economy / 6 * r.strike_rate, 1) if r.wickets else "–",
                    fmt(r.strike_rate, 1), r.tags] for r in bp.itertuples()], num={1, 2, 3, 4, 5, 6, 7},
                  parts=[dict(bruns=int(r.runs), bballs=int(r.balls), wkts=int(r.wickets), binns=int(r.innings))
                         for r in bp.itertuples()])
        t["note"] = (f"Section average: {bp.attrs['average']:.1f} runs per wicket, a wicket every {bp.attrs['strike_rate']:.0f} "
                     "balls. In multi-day cricket the cost of each wicket matters more than the run rate, so 'cheap' and "
                     "'costly' go by bowling average. Top-order hunters for the new ball; tail cleaners to finish an innings "
                     "off." if by_avg else
                     f"Section average: economy {bp.attrs['economy']:.2f}, strike rate {bp.attrs['strike_rate']:.1f}. Top-order "
                     "hunters for the new ball; tail cleaners to finish an innings off; the cheap ones for the overs you need "
                     "to control.")
        return t
    part("plan", plan)
    return out


def _knocking(career, ids, team) -> dict:
    out, part = _parts()

    def kn_():
        kn = PL.knocking(career, ids, team)
        if kn.empty:
            return dict(none="Nobody on the fringes is outscoring the regulars right now.")
        t = table(["Player", "Mat", "Why"], [[r.player, int(r.games), r.why] for r in kn.itertuples()], num={1})
        t["note"] = "Small samples: a good game or two can put someone here, so treat it as a nudge."
        return t
    part("knocking", kn_)
    return out


def _pairs(career, ids, team) -> dict:
    out, part = _parts()

    def bat():
        bp = PL.batting_pairs(career, ids, team)
        if bp.empty:
            return dict(none="No pairs with 2+ stands yet.")
        return table(["Pair", "Stands", "Runs", "Avg", "Best", f"{bp.attrs.get('stand', 50)}+"],
                     [[r.pair, int(r.stands), int(r.runs), fmt(r.average, 1), int(r.best), int(r.big_stands)]
                      for r in bp.head(15).itertuples()], num={1, 2, 3, 4, 5},
                     parts=[dict(runs=int(r.runs), outs=int(r.broken), inns=int(r.stands), what="stands")
                            for r in bp.head(15).itertuples()])
    part("batting", bat)

    def bowl():
        wp = PL.bowling_pairs(career, ids, team)
        if wp.empty:
            return dict(none="No pairs yet.")
        return table(["Pair", "Inns", "Wkts", "Wkts/inns", "Econ"],
                     [[r.pair, int(r.innings), int(r.wickets), f"{r.per_innings:.1f}", fmt(r.economy, 2)] for r in wp.head(15).itertuples()],
                     num={1, 2, 3, 4}, parts=[dict(bruns=int(r.runs), bballs=int(r.balls), wkts=int(r.wickets), binns=int(r.innings))
                                              for r in wp.head(15).itertuples()])
    part("bowling", bowl)
    return out
