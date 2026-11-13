"""Competitions (stage 2): one competition as it's run (the ODI World Cup, bilateral ODI series, each County
Championship division) in one season: the league table, the title race, the knockouts, every series and the World Test
Championship, as the current site's Competitions page shows them. Every number comes from the same engine functions
with the same words."""

from __future__ import annotations

import pandas as pd

from ccstats import odds as OD
from ccstats import players as PL
from ccstats import seasonal as SN
from ccstats import tables as T
from ccstats import teamplay as TP

from . import styleguide as SG
from .cache import kept
from .teampage import fmt, table

LIMITED_NOTE = (" Net run rate: runs scored per over minus runs conceded per over; a side bowled out counts as having used "
                "its full overs (in a game shortened by rain, the overs it was allowed). Abandoned games don't count, and "
                "in a game decided by the rain rule the side batting first is credited with the rain-rule par score.")


def chance(v) -> str:
    """A chance in %, never rounded to a certainty it isn't."""
    if v is None or v != v:
        return ""
    return "<1%" if 0 < v < 0.5 else ">99%" if 99.5 <= v < 100 else f"{v:.0f}%"


def choices(career) -> list[dict]:
    """Every competition as it's run, the most matches first, with its seasons (newest first)."""
    m = career.matches
    counts = m.event.value_counts()
    return [dict(event=str(e), matches=int(n), seasons=[str(s) for s in sorted(m[m.event == e].season.unique(), reverse=True)])
            for e, n in counts.items()]


def _every(career) -> dict:
    """Every section of the career at a glance (the current site's "Sections" table, from My team)."""
    sec = T.every_section(career.matches)
    t = table(["Section", "Matches", "Seasons", "First match", "Latest match", "Format", "Level"],
              [[r.section, int(r.matches), r.seasons, f"{r.first:%d %b %Y}", f"{r.last:%d %b %Y}", r.format, r.level]
               for r in sec.itertuples()], num={1})
    t["note"] = ("A section is how the matches are grouped everywhere on the site: international matches by format (all "
                 "Tests, all ODIs, all T20Is, World Cups included), everything else, like the IPL, the T20 Blast and each "
                 "County Championship division, on its own.")
    return t


def page(career, q: dict, mine: list[str]) -> dict:
    m = career.matches
    ch = choices(career)
    out: dict = dict(choices=ch, event="", season="", none="")
    if not ch:
        out["none"] = SG.NO_MATCHES
        return out
    out["every"] = kept(career, ("every_section",), lambda: _every(career))
    events = [c["event"] for c in ch]
    event = q.get("event", "")
    if event not in events:   # the competition your team played in last, else the one with the most matches
        mm = m[m.home.isin(mine) | m.away.isin(mine)] if mine else m.iloc[0:0]
        event = str(mm.sort_values("date").event.iloc[-1]) if len(mm) else events[0]
    seasons = next(c["seasons"] for c in ch if c["event"] == event)
    season = q.get("season", "")
    if season not in seasons:
        mm = m[(m.event == event) & (m.home.isin(mine) | m.away.isin(mine))] if mine else m.iloc[0:0]
        season = str(mm.sort_values("date").season.iloc[-1]) if len(mm) else seasons[0]
    out.update(event=event, season=season)
    sval = next(s for s in m[m.event == event].season.unique() if str(s) == season)
    ids = pd.Index(m[(m.event == event) & (m.season == sval)].match_id)
    key = ("competition", event, season)
    body = kept(career, key, lambda: _body(career, event, sval, ids))
    out.update(body)
    each = (body.get("series") or {}).get("each") or []
    if each:   # the one series picked, match by match: worked out only for it (a season can hold 20 series)
        i = _int(q.get("series", ""), 0, len(each) - 1, 0)
        e = each[i]
        g = m[m.series_id == e["id"]]
        sides = [g.home.iloc[0], g.away.iloc[0]]
        wins = {t: int((g.winner == t).sum()) for t in sides}
        # told from your side when you play in it, else from the side that won (or leads) it
        side = next((t for t in mine if t in sides), None) or max(sides, key=lambda t: (wins[t], t == sides[0]))
        out["series_pick"] = i
        out["series_one"] = kept(career, ("series_one", e["id"], side), lambda: _series_one(career, dict(e, team=side)))
    if body.get("race_on"):
        out["race"] = _race(career, event, sval, q, mine)
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


def _score(inn, mid, team) -> str:
    parts = [f"{r.runs}" if r.all_out else f"{r.runs}/{r.wickets}{'d' if r.declared else ''}"
             for r in inn[(inn.match_id == mid) & (inn.team == team)].sort_values("innings_no").itertuples()]
    return " & ".join(parts) or "–"


def _body(career, event, season, ids) -> dict:
    m = career.matches
    here = m[m.match_id.isin(ids)]
    inn = career.innings[career.innings.match_id.isin(ids)]
    out, part = _parts()
    bilateral = here.competition.iloc[0] in T.BILATERAL
    limited = here.format.iloc[0] in T.LIMITED
    leagues = T.league_tables(career, ids)
    out["bilateral"] = bool(bilateral)
    out["race_on"] = bool(leagues and not bilateral and not any(x in event for x in ("World XI", "Tour matches")))

    def league():
        if not leagues:
            return None
        gm = TP.games(career, ids)
        gm = gm[~gm.knockout]
        groups = []
        for label, t, rule in leagues:
            cols = [("team", "Team"), ("played", "P"), ("won", "W"), ("lost", "L")]
            if t.drawn.any() or not limited:
                cols.append(("drawn", "D"))
            if t.tied.any():
                cols.append(("tied", "T"))
            if t.no_result.any():
                cols.append(("no_result", "NR"))
            if t.points.notna().any():
                cols.append(("points", "Pts"))
            cols += [("nrr", "NRR")] if limited else [("rpw_for", "Runs/wkt"), ("rpw_against", "Conceded/wkt")]
            t = t.assign(bat_first=[f"{int(((gm.team == x) & gm.batted_first & (gm.outcome == 'W')).sum())}/"
                                    f"{int(((gm.team == x) & gm.batted_first).sum())}" for x in t.team],
                         chased=[f"{int(((gm.team == x) & ~gm.batted_first & (gm.outcome == 'W')).sum())}/"
                                 f"{int(((gm.team == x) & ~gm.batted_first).sum())}" for x in t.team])
            cols += [("bat_first", "Won batting 1st"), ("chased", "Won chasing" if limited else "Won batting 2nd")]
            if not bilateral:
                ex = SN.table_extras(career, ids, t, label).set_index("team")
                t = t.assign(form=t.team.map(ex.form), home_rec=t.team.map(ex.home), away_rec=t.team.map(ex.away),
                             ppg=t.points / t.played.replace(0, float("nan")), rr_for=t.team.map(ex.rr_for),
                             rr_against=t.team.map(ex.rr_against), moved=[SN.moved_text(v) for v in t.team.map(ex.moved)])
                cols.append(("form", "Last 5"))
                if not here.neutral.all():
                    cols += [("home_rec", "Home W–L"), ("away_rec", "Away W–L")]
                if t.points.notna().any():
                    cols.append(("ppg", "Pts/game"))
                if limited:
                    cols += [("rr_for", "RR for"), ("rr_against", "RR against")]
                cols.append(("moved", "Move"))
            dec = {"nrr": 3, "rpw_for": 2, "rpw_against": 2, "ppg": 2, "rr_for": 2, "rr_against": 2, "points": 0}
            text = {"team", "bat_first", "chased", "form", "home_rec", "away_rec", "moved"}

            def cell(c, v):
                if c in text:
                    return "" if v is None or v != v else str(v)
                if c == "nrr":
                    return "–" if v != v else f"{v:+.3f}"
                return fmt(v, dec.get(c, 0))
            rows = [[cell(c, getattr(r, c)) for c, _ in cols] for r in t.itertuples()]
            g = table([h for _, h in cols], rows, num={i for i, (c, _) in enumerate(cols) if c not in text})
            g["label"] = label if (len(leagues) > 1 or label not in ("League", "Every team")) else ""
            g["teams"] = list(t.team)
            g["badges"] = [0]
            g["note"] = (rule + (LIMITED_NOTE if limited else "") + " Won batting 1st / chasing: wins out of games played "
                         "that way." + ("" if bilateral else " Last 5: newest on the right. RR: runs per over scored and "
                                        "conceded. Move: places gained (▲) or lost (▼) since the match day before the latest one."))
            groups.append(g)
        note = ""
        if not bilateral and (any(len(t) < 3 for _, t, _ in leagues) or len(leagues) > 1):
            note = ("Groups come from the group names on the scorecards (a team's row counts all its league games, "
                    "cross-group ones too). Where the scorecards don't name them, they're worked out from who played "
                    "whom, so they only separate cleanly once each team has played a couple of games.")
        return dict(title="Every team's record" if bilateral else "League table" + ("s" if len(leagues) > 1 else ""),
                    groups=groups, note=note)
    part("league", league)

    def knockouts():
        ko = T.knockouts(career, ids)
        if ko.empty:
            return None
        rounds = []
        for rnd in dict.fromkeys(ko.stage):
            cards = [dict(id=r.match_id, date=f"{r.date:%d %b %Y}", result=r.result,
                          teams=[dict(team=t, score=_score(inn, r.match_id, t), won=t == r.through) for t in (r.home, r.away)])
                     for r in ko[ko.stage == rnd].itertuples()]
            rounds.append(dict(round=rnd, cards=cards))
        champ, line = ko[ko.stage == "Final"], ""
        if len(champ) == 1 and champ.through.iloc[0]:
            line = f"🏆 {champ.through.iloc[0]} · {event} {season} champions"
        elif len(champ) == 1 and champ.format.iloc[0] == "Test" and champ.result_type.iloc[0] in ("draw", "tie"):
            f = champ.iloc[0]   # a drawn World Test Championship Final: the title is shared
            line = f"🏆 {f.home} and {f.away} share the {event} {season} title"
        return dict(rounds=rounds, champion=line)
    part("knockouts", knockouts)

    def series():
        ser = T.series_table(career, ids)
        if ser.empty:
            return None
        pos = PL.player_of_series(career, ids).set_index("series_id")
        t = table(["Started", "Series", "Score", "Result", "Drawn", "Most runs", "Most wickets", "Player of the Series"],
                  [[f"{r.start:%d %b %Y}", r.teams, r.score, r.result, int(r.drawn), r.top_runs, r.top_wickets,
                    f"{pos.player[r.series_id]} ({pos.runs[r.series_id]} runs, {pos.wickets[r.series_id]} wkts)"
                    if r.series_id in pos.index else "–"] for r in ser.itertuples()], num={4})
        t["badges"] = [1]
        t["note"] = ("Player of the Series: the most impact over the series (runs, plus each wicket worth the section's "
                     "runs per wicket).")
        each = []
        for r in ser.itertuples():
            g = m[m.match_id.isin(r.match_ids)].sort_values("date")
            h, a = g.home.iloc[0], g.away.iloc[0]
            each.append(dict(label=f"{r.teams} · {r.score} · {r.result}", team=h, id=r.series_id, teams=r.teams,
                             matches=table(
                ["Match", "Date", h, a, "Result"],
                [[(f"{int(n)}" + (f" of {int(o)}" if pd.notna(o) else "")) if pd.notna(n) else "", f"{d:%d %b %Y}",
                  _score(inn, i, h), _score(inn, i, a), res]
                 for n, o, d, i, res in zip(g.series_match_no, g.series_length, g.date, g.match_id, g.result)],
                links=list(g.match_id))))
        return dict(table=t, each=each)
    part("series", series)

    def wtc():
        w = SN.wtc_matches(career)
        if w.empty or here.format.iloc[0] != "Test" or here.knockout.all():
            return None
        cycles = sorted(int(c) for c in w.cycle.unique())[::-1]
        here_cycle = SN.wtc_cycle(here.date.max())
        tables = {}
        for cyc in cycles:
            wt = SN.wtc_table(career, cyc)
            t = table(["Team", "Series", "P", "W", "L", "D", "T", "Pts", "Of", "PCT %"],
                      [[r.team, int(r.series), int(r.played), int(r.won), int(r.lost), int(r.drawn), int(r.tied),
                        fmt(r.points, 0), fmt(r.available, 0), fmt(r.pct, 2)] for r in wt.itertuples()],
                      num={1, 2, 3, 4, 5, 6, 7, 8, 9})
            t["badges"] = [0]
            t["heading"] = (f"Heading for the final: {wt.team.iloc[0]} ({wt.pct.iloc[0]:.1f}%) and {wt.team.iloc[1]} "
                            f"({wt.pct.iloc[1]:.1f}%).") if len(wt) >= 2 else ""
            tables[str(cyc)] = t
        return dict(cycles=[dict(key=str(c), label=f"{c}–{str(c + 2)[-2:]}") for c in cycles],
                    cycle=str(here_cycle if here_cycle in cycles else cycles[0]), tables=tables,
                    note="The real system: 12 points for a win, 6 for a tie, 4 for a draw, ranked by the percentage of the "
                         "points played for that were won (PCT). Only Tests between the nine WTC sides count (Australia, "
                         "Bangladesh, England, India, New Zealand, Pakistan, South Africa, Sri Lanka, West Indies), in "
                         "two-year cycles from June of an odd year; the top two meet in the final. Over-rate penalties "
                         "aren't on the scorecards, so they aren't taken off.")
    part("wtc", wtc)
    return out


def _series_one(career, e: dict) -> dict:
    """One series in full: the ladder from one side's view (`team`), the most runs and wickets, and Team of the
    series (for a series of 2 or more matches)."""
    out, part = _parts()
    part("ladder", lambda: SG.series_of(career, e["id"], e["team"]))
    ids = list(career.matches[career.matches.series_id == e["id"]].match_id)
    part("xi", lambda: _series_xi(SN.best_xi(career, ids), f"Team of the series · {e['teams']}") if len(ids) >= 2 else None)
    out["team"] = e["team"]
    return SG.clean(out)


def _series_xi(xi, title) -> dict:
    """Team of the series, picked as Season review's Team of the Season is (by role, from the numbers)."""
    from .reviewpage import _xi
    out = _xi(xi, title)
    if not xi.empty:
        out["badges"] = [3]
    return out


def _int(v, lo, hi, default):
    try:
        return max(lo, min(hi, int(v)))
    except (TypeError, ValueError):
        return default


def _race(career, event, season, q, mine) -> dict:
    """The title race: everyone's chances now (played out 4,000 times) and after every match day."""
    out, part = _parts()

    def race():
        ko = TP.has_knockouts(career, event)
        d = TP.qualification_defaults(career, event, season)
        many = d["groups"] > 1
        games = _int(q.get("games"), 1, 60, d["games"])
        places = _int(q.get("places"), 1, 16, d["places"])
        extra = _int(q.get("extra"), 0, 8, int(d.get("extra", 0))) if many else 0
        k = (event, str(season), games, places, extra)
        now = kept(career, ("odds",) + k, lambda: OD.odds_with_change(career, event, season, games, places, extra=extra))
        hist = kept(career, ("odds-history",) + k, lambda: OD.odds_history(career, event, season, games, places, extra=extra))
        col, what = ("title", "the title") if ko else ("top", "topping the table")
        if now["state"] == "open" and len(hist):   # the latest point is the table's own (played out more times)
            latest = hist.date == hist.date.max()
            hist = hist.copy()
            hist.loc[latest, col] = hist.loc[latest, "team"].map(now["table"].set_index("team")[col]).values
        teams = sorted(set(hist.team)) if len(hist) else []
        fav = hist[hist.date == hist.date.max()].sort_values(col, ascending=False).team.iloc[0] if len(hist) else ""
        pick = q.get("pick", "")
        if pick not in teams:
            pick = next((t for t in mine if t in teams), fav)
        res = dict(knockouts=bool(ko), many=bool(many), games=games, places=places, extra=extra, default_games=d["games"],
                   default_places=d["places"], default_extra=int(d.get("extra", 0)), state=now["state"], what=what,
                   teams=teams, pick=pick, groups=[], lines=[], shows="", note="")
        if now["state"] == "open":
            t = now["table"].sort_values(["group", col], ascending=[True, False])
            ch = now.get("change") or {}
            for grp, g in t.groupby("group", sort=False):
                rows = []
                for r in g.itertuples():
                    delta = ch.get(r.team, float("nan"))
                    move = ("" if delta != delta else f"▲ {delta:.0f}" if delta >= 0.5 else
                            f"▼ {-delta:.0f}" if delta <= -0.5 else "–")
                    rows.append([r.team, int(r.played), f"{r.points:.0f}", int(r.left)]
                                + ([chance(r.playoffs), chance(r.title)] if ko else [chance(r.top)]) + [move])
                gt = table(["Team", "Played", "Pts", "Left"] + (["Through", "Title"] if ko else ["Top"]) + ["Change"],
                           rows, num={1, 2, 3}, hi=[x == pick for x in g.team])
                gt["label"] = str(grp) if now["groups"] > 1 else ""
                gt["badges"] = [0]
                res["groups"].append(gt)
            since = now.get("since")
            res["caption"] = ("Chances from playing the rest of the league season out 4,000 times. "
                              + (f"Change: since before the games of {since:%d %b}." if since is not None else ""))
        elif now["state"] == "league over":
            res["caption"] = "The league stage is over" + (" (see the knockouts below)." if ko else ".")
        if len(hist) and hist.date.nunique() > 1:
            res["lines"] = [dict(team=tm, points=[dict(date=f"{d:%Y-%m-%d}", chance=round(float(v), 1))
                                                  for d, v in zip(g.date, g[col])])
                            for tm, g in hist.sort_values("date").groupby("team")]
            # only the days the side has a chance worked out (a side can have none on some days: idxmax of nothing
            # would be an error in pandas 3)
            mine_h = hist[(hist.team == pick) & hist[col].notna()].sort_values("date")
            if len(mine_h):
                best = mine_h.loc[mine_h[col].idxmax()]
                known = hist.dropna(subset=[col])
                fav_days = known.loc[known.groupby("date")[col].idxmax()].team.value_counts()
                decided = now["state"] != "open" and mine_h[col].iloc[-1] in (0, 100)
                res["shows"] = (f"{pick}: {chance(mine_h[col].iloc[0])} after the first match day, at best "
                                f"{chance(best[col])} (after {best.date:%d %b}), {chance(mine_h[col].iloc[-1])} "
                                f"{'at the end' if decided else 'now'}. {fav_days.index[0]} were the favourites most "
                                f"often ({fav_days.iloc[0]} of {known.date.nunique()} match days).")
            res["for_"] = f"See when the race for {what} turned, and how much each result moved a side's chances."
        limited = career.matches[career.matches.event == event].format.iloc[0] in T.LIMITED
        res["note"] = ("How it's worked out: each game still to play is decided by the two sides' team ratings (the Elo on "
                       "the Rankings page), with this competition's share of " + ("no results" if limited else "draws")
                       + ". The scorecards don't hold the fixture list, so the games left are worked out from the games "
                       "per team above and who has met whom least. Ties on points go to wins, then net run rate."
                       + (" The knockouts are played the way this competition plays them." if ko else "")
                       + " The chart shows each side's chance after every match day; sides that never had a 5% chance "
                       "are left out.")
        return res
    part("race", race)
    return out
