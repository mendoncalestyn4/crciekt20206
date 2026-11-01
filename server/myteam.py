"""My team (the home page): your side's season at a glance, the latest result and what it changed, what's next from
your schedule, the marks out of 10 after its latest series with who to bring in, form in every format, and one
competition in detail (the season so far, the report card, stars, the squad, headlines, milestones, how you win,
rivals, trophies, records, season by season, your notes).

Every number comes from the engine; this module only picks and arranges them, with the same words as the current
site's My team tab (ui/myteam_view.py). Each part is worked out on its own: one that can't be (too few matches, a
schedule that can't be read) comes back empty with the reason, and the rest of the page is still drawn."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ccstats import catalogue as CAT
from ccstats import depth as DP
from ccstats import extras as E
from ccstats import fixtures as FX
from ccstats import marks as MK
from ccstats import myteam as MT
from ccstats import players as PL
from ccstats import scouting as SC
from ccstats import seasonal as SN
from ccstats import teamplay as TP
from ccstats import winprob as WP
from ccstats.competitions import shown_name, with_stage

from . import styleguide as SG
from .cache import kept


def pct(v) -> str:
    return "–" if v is None or not np.isfinite(v) else f"{v:.0f}%"


def teams_by_latest(career, mine: list[str]) -> list[str]:
    """Your teams with a match, the one that played last first (My team opens on it)."""
    last = {}
    for t in mine:
        g = MT.last_game(career, t)
        if g is not None:
            last[t] = g.saved_at if "saved_at" in g else g.date
    return sorted(last, key=lambda t: last[t], reverse=True)


def _odds_text(ch) -> str:
    if not ch:
        return ""
    pc = lambda v: "<1%" if 0 < v < 0.5 else ">99%" if 99.5 <= v < 100 else f"{v:.0f}%"  # noqa: E731
    return (f"; playoff chance {pc(ch['playoffs'])}, title {pc(ch['title'])}" if ch["knockouts"] else
            f"; chance of topping the table {pc(ch['top'])}")


def banner(career, team: str) -> dict:
    bn = kept(career, ("banner", team), lambda: MT.banner(career, team))
    tiles, caps = [], []
    for b in bn:
        elo = (f"Elo {b['elo']:.0f} {'▲' if b['moved'] > 0 else '▼' if b['moved'] < 0 else '▬'}{abs(b['moved']):.0f}"
               if np.isfinite(b["elo"]) else "")
        tiles.append(SG.clean(dict(section=b["section"], season=b["season"], record=dict(b["record"]), elo=b["elo"],
                                   moved=b["moved"], rank=b["rank"], teams=b["teams"],
                                   position=list(b["position"]) if b["position"] else None)))
        if elo:
            caps.append(f"{b['section']}: {elo}, {b['rank']} of {b['teams']} in the ratings"
                        + (f", {b['position'][2]} in {b['position'][0]}" if b["position"] else "")
                        + _odds_text(b.get("chances")))
    caption = (" · ".join(caps) + ". ▲▼ = rating change over the last 5 games."
               + (" Chances: the rest of the season played out 2,000 times (Seasons → title race)."
                  if any(b.get("chances") for b in bn) else "")) if caps else ""
    return dict(tiles=tiles, caption=caption)


def latest(career, team: str) -> dict | None:
    rs = SG.results(career, team)
    if not rs:
        return None
    r = SG.in_played_order(career, rs)[-1]
    meta = career.matches.set_index("match_id").loc[r["id"]]
    name = with_stage(shown_name(meta.section, meta.event), meta.stage)
    which = (f"{r['section'].rstrip('s')} {int(r['no'])} of {int(r['of'])}" if r["no"] and r["of"] else name)
    return dict(result=r, kicker=f"{which} · {pd.Timestamp(r['date']):%d %b %Y}", name=name,
                report=WP.match_report(career, r["id"]))


def after(career, team: str) -> dict | None:
    """What changed after the latest game, in the current site's words."""
    am = kept(career, ("after", team), lambda: SN.after_match(career, team))
    if not am:
        return None
    lines = []
    if am.get("elo"):
        a, b = am["elo"]
        lines.append(dict(k="Rating", text=f"Elo {a:.0f} → {b:.0f} ({b - a:+.0f})", up=b > a))
    pos = am.get("position")
    if pos and pos[1]:
        after_ = pos[1]
        where = f" in {after_[2]}" if after_[2] not in ("League", "Every team") else ""
        if pos[0]:
            mv = pos[0][0] - after_[0]
            lines.append(dict(k="Table", text=f"{after_[0]} of {after_[1]}{where} "
                              + (f"(up {mv})" if mv > 0 else f"(down {-mv})" if mv < 0 else "(no change)"),
                              up=mv > 0 if mv else None))
        else:
            lines.append(dict(k="Table", text=f"{after_[0]} of {after_[1]}{where} after the first game", up=None))
    if am.get("series"):
        s = am["series"]
        lead = "level" if s["won"] == s["lost"] else "lead" if s["won"] > s["lost"] else "trail"
        left = s["length"] - s["played"]
        score = f"{s['won']}–{s['lost']}" + (f" ({s['drawn']} drawn)" if s["drawn"] else "")
        if left > 0:
            lines.append(dict(k="Series", text=f"you {lead} {score} v {s['opponent']}, {left} to play", up=None))
        else:
            res = "won" if s["won"] > s["lost"] else "lost" if s["won"] < s["lost"] else "drew"
            lines.append(dict(k="Series", text=f"you {res} it {score} v {s['opponent']}", up=None))
    if "lead" in am:
        ld = am["lead"]
        lines.append(dict(k="First-innings lead" if ld else "First innings", text=f"{ld:+d}" if ld else "level",
                          up=ld > 0 if ld else None))
    news = [f"🏆 {x}" for x in am.get("records", [])[:3]] + [f"🎯 {x}" for x in am.get("milestones", [])[:4]]
    form = [dict(player=p, arrow=arrow, text=txt) for p, arrow, txt in am.get("form", [])[:5]]
    return SG.clean(dict(opponent=am["opponent"], date=am["date"], lines=lines, news=news, form=form,
                         match_id=am["match_id"]))


def next_up(career, team: str, sched: list) -> dict | None:
    """Your schedule: played so far, the next match (with the chances), any series under way."""
    tr = FX.track(career, sched, auto=(team,))
    mine = tr[tr.team == team] if len(tr) else tr
    if not (len(mine) and (any(r.get("team") == team for r in sched) or mine.status.isin(["next"]).any())):
        return None
    sm = FX.summary(tr, team)
    out = dict(played=int(sm["played"]), total=int(sm["total"]), next=None, under_way=[])
    nx = sm["next"]
    if nx is not None:
        when = (f"{pd.Timestamp(nx['date']):%d %b %Y}" if nx["date"] else
                f"about {pd.Timestamp(nx['anchor']):%d %b %Y}"
                if str(nx.get("estimated")) == "True" and pd.notna(nx.get("anchor")) else FX.month_label(nx["month"]))
        name = nx["series"].replace(FX.AUTO, "").split(" · ")[0]
        stage = nx.get("stage") if isinstance(nx.get("stage"), str) else ""
        what = (f"{name} {stage}" + (f" v {nx['opponent']}" if nx["opponent"] else "") if stage else
                f"v {nx['opponent']} · {nx['format']}" if nx["opponent"] else name)
        chance = None
        if nx["opponent"]:
            p = WP.predict(career, FX.format_ids(career, team, nx["format"]), team, nx["opponent"],
                           nx["venue"] if nx["venue"] in ("home", "away") else "neutral")
            chance = dict(win=p["win"], draw=p["draw"] if p["multi"] else None, lose=p["lose"])
        out["next"] = dict(what=what, venue=nx["venue"] or "", when=when, opponent=nx["opponent"] or "", chance=chance)
    for sg in FX.series_groups(tr, team):
        if sg["state"] == "under way":
            o = FX.series_outlook(career, team, sg)
            lead = "level" if sg["won"] == sg["lost"] else ("you lead" if sg["won"] > sg["lost"] else "you trail")
            out["under_way"].append(f"{sg['series']}: {lead} {sg['won']}–{sg['lost']}; {o['need']} "
                                    f"(chance {o['odds']['A']:.0f}%)")
    return SG.clean(out)


def report_card(career, team: str) -> dict | None:
    """The marks out of 10 after the latest series or tournament, ranked, and who to bring in for anyone struggling."""
    rep = kept(career, ("marks", team), lambda: MK.team_report(career, team))
    if not rep:
        return None
    s = rep[0]
    section = career.matches.set_index("match_id").section.get(s["players"][0]["best_match"], "")
    advice = []
    try:
        for r in SC.replacements(career, team, section):
            advice.append(SG.clean(dict(player=r["player"], role=r["role"], why=r["why"], verdict=r["verdict"],
                                        elsewhere=r["elsewhere"], own=r["own"], picks=r["picks"])))
    except Exception:  # noqa: BLE001 - no advice is better than no report card
        advice = []
    return SG.clean(dict(series=s["series"], label=s["label"], format=s["format"], among=MK.among(s["reference"]),
                         section=section, start=s["start"],
                         end=s["end"], players=[{k: p[k] for k in ("player", "mark", "rank", "of", "games", "line",
                                                                     "best", "best_match")} for p in s["players"]],
                         earlier=[dict(label=x["label"], series=x["series"], format=x["format"],
                                       top=[dict(player=p["player"], mark=p["mark"]) for p in x["players"][:3]])
                                  for x in rep[1:6]],
                         advice=advice))


def forms(career, team: str, rs_season: list[dict]) -> list[dict]:
    """The form line in each format this season (oldest first), most played first."""
    by: dict[str, list[dict]] = {}
    for r in rs_season:
        by.setdefault(r["section"], []).append(r)
    return [dict(section=s, results=x, form=SG.form(x)) for s, x in sorted(by.items(), key=lambda kv: -len(kv[1]))]


def series_list(rs_season: list[dict], team: str) -> list[dict]:
    """This season's series and tournaments, newest first: who against, where, the score."""
    out: dict[str, dict] = {}
    for r in rs_season:
        key = r["series"] or f"{r['event']}"
        s = out.setdefault(key, dict(key=key, opp=r["opp"] if r["series"] else "", event=r["event"], section=r["section"],
                                     start=r["date"], end=r["date"], won=0, lost=0, other=0, played=0,
                                     tournament=not r["series"]))
        s["end"] = max(s["end"], r["date"])
        s["played"] += 1
        s["won" if r["outcome"] == "W" else "lost" if r["outcome"] == "L" else "other"] += 1
    return sorted(out.values(), key=lambda s: s["end"], reverse=True)


def section_block(career, team: str, section: str, notes: dict, sched: list) -> dict:
    """One competition in detail, this season."""
    m = career.matches
    season = MT.latest_season(career, team, section)
    ids_all = m[m.section == section].match_id
    out: dict = dict(section=section, season=SG.clean(season), missing={})

    def piece(name, fn):
        try:
            out[name] = SG.clean(fn())
        except Exception as e:  # noqa: BLE001 - one part that can't be worked out never stops the others
            out[name] = None
            out["missing"][name] = f"Couldn't be worked out ({type(e).__name__}: {e})"

    tg = kept(career, ("games", section), lambda: TP.games(career, ids_all))
    last5 = list(MT.in_played_order(career, tg[tg.team == team]).outcome.tail(5))

    def so_far():
        sp = MT.same_point(career, team, section)
        line = ""
        if sp:
            line = f"After {sp['n']} game{'s' if sp['n'] != 1 else ''}: {TP.wdl(sp['now'])}"
            if sp["then"] is not None:
                d = sp["now"]["won"] - sp["then"]["won"]
                line += (f". At the same point of {sp['last_season']}: {TP.wdl(sp['then'])} "
                         f"({'+' if d > 0 else ''}{d} win{'s' if abs(d) != 1 else ''}).")
        return dict(last5=last5, line=line, card=[dict(subject=s, grade=g, why=w)
                                                  for s, g, w in MT.report_card(career, team, section, season)])
    piece("so_far", so_far)
    sq = MT.squad(career, team, section, season)
    piece("squad", lambda: SG.rows(sq, ["player", "games", "runs", "average", "strike_rate", "wickets", "economy",
                                        "last5", "form", "recent"]))
    piece("stars", lambda: dict(
        bat=SG.rows(sq.sort_values("runs", ascending=False).head(3), ["player", "runs", "average", "form"]),
        bowl=SG.rows(sq[sq.wickets > 0].sort_values("wickets", ascending=False).head(3), ["player", "wickets", "economy"])))
    piece("alerts", lambda: MT.alerts(career, team, section, season))
    piece("headlines", lambda: E.headlines(career, n_matches=8, limit=6, team=team))

    def milestones():
        names = set(sq.player)
        mw = PL.milestone_watch(career, ids_all)
        mw = mw[mw.player.isin(names)]
        rw = PL.record_watch(career, section)
        rw = rw[rw.chaser.isin(names)]
        return ([dict(player=r.player, chasing=f"{r.next:,} {r.what}", needs=f"needs {r.needed:,}") for r in mw.head(6).itertuples()]
                + [dict(player=r.chaser, chasing=f"{r.record} record ({r.record_value:,})", needs=f"needs {r.needed:,}")
                   for r in rw.itertuples()])
    piece("milestones", milestones)

    def how_you_win():
        bft, avg = TP.bat_first_table(career, ids_all)
        if team not in set(bft.team):
            return None
        r = bft.set_index("team").loc[team]
        second = "batting second" if avg["multi"] else "chasing"
        g = tg[(tg.team == team) & tg.batted_first & tg.first_score.notna()]
        won = g[g.outcome == "W"]
        extra = (f"Your lowest total defended: {int(won.first_score.min())}. Your typical winning total batting first: "
                 f"{int(won.first_score.median())}." if len(won) >= 2 and not avg["multi"] else "")
        return dict(first=dict(pct=pct(r.bf_win_pct), won=int(r.bf_won), decided=int(r.bf_decided)),
                    second=dict(word=second, pct=pct(r.ch_win_pct), won=int(r.ch_won), decided=int(r.ch_decided)),
                    extra=extra)
    piece("how_you_win", how_you_win)

    def rivals():
        op = TP.opponents(career, ids_all, team)
        up = FX.upcoming(career, sched, (team,))
        fmts = set(m[m.section == section].format)
        sched_o = [o for o in dict.fromkeys(up[up.format.isin(fmts)].opponent) if o != team] if len(up) else []
        every, todo = CAT.section_teams(m[m.section == section], section)
        opps = sched_o + [t for t in every if t != team and t not in sched_o]
        return dict(rows=[dict(opponent=r.opponent, played=int(r.played), record=TP.wdl(r._asdict()), win_pct=pct(r.win_pct),
                               favourite=bool(r.favourite), bogey=bool(r.bogey)) for r in op.head(6).itertuples()],
                    next=[dict(team=t, note="next match" if sched_o and t == sched_o[0] else "in your schedule"
                               if t in sched_o else "no games yet" if t in todo else "") for t in opps])
    piece("rivals", rivals)
    piece("trophies", lambda: SG.rows(E.trophy_cabinet(career, team), ["section", "season", "how", "runners_up"]))
    piece("records", lambda: [dict(what=a, detail=b) for a, b in MT.team_records(career, team, section)])
    return out


def page(career, team: str, section: str, mine: list[str], notes: dict, sched: list) -> dict:
    """The whole page for one of your teams (`section`: the competition in detail; the latest one when empty)."""
    teams = teams_by_latest(career, mine)
    out: dict = dict(teams=teams, team=team, missing={})
    secs = MT.sections_of(career, team)
    if not secs:
        out["missing"]["everything"] = (f"No matches for {team} yet: this page fills in after their first game. Add their "
                                        "schedule on Fixtures meanwhile, and the next match shows up here.")
        return out
    section = section if section in secs else secs[0]
    out.update(sections=secs, section=section)

    def piece(name, fn):
        try:
            out[name] = SG.clean(fn())
        except ValueError as e:   # not enough in the career for it yet: said in plain words
            out[name] = None
            out["missing"][name] = str(e)
        except Exception as e:  # noqa: BLE001 - one part that can't be worked out never stops the others
            out[name] = None
            out["missing"][name] = f"Couldn't be worked out ({type(e).__name__}: {e})"

    piece("banner", lambda: banner(career, team))
    piece("ticker", lambda: SG.results(career, team)[:12])
    piece("latest", lambda: latest(career, team))
    piece("after", lambda: after(career, team))
    piece("next_up", lambda: next_up(career, team, sched))
    piece("report", lambda: report_card(career, team))
    piece("season", lambda: kept(career, ("calendar", team), lambda: SG.calendar(career, team)))
    rs = (out.get("season") or {}).get("results", [])
    piece("forms", lambda: forms(career, team, rs))
    piece("series", lambda: series_list(rs, team))
    piece("venues", lambda: SG.venues(rs, team))
    piece("winners", lambda: SG.match_winners(rs, team))
    piece("scores", lambda: SG.scores(rs))
    piece("history", lambda: SG.rows(MT.history(career, team), ["season", "section", "played", "won", "lost", "drawn",
                                                                "tied", "no_result", "win_pct", "finish"]))

    def my_notes():
        m = career.matches
        g = m[((m.home == team) | (m.away == team)) & m.source.isin(list(notes))].sort_values("date", ascending=False)
        return [dict(id=r.match_id, date=r.date, home=r.home, away=r.away, note=notes[r.source]) for r in g.head(10).itertuples()]
    piece("notes", my_notes)
    piece("block", lambda: section_block(career, team, section, notes, sched))
    # squad depth in the competition picked below (who starts, the backups, who's waiting in domestic cricket)
    piece("depth", lambda: kept(career, ("depth", team, section), lambda: DP.squad_depth(career, team, section)))
    piece("career", lambda: kept(career, ("whole career",), lambda: whole_career(career)))
    return out


def scouting(career, team: str) -> dict:
    """The Scouting tab on My team: for each competition the team plays, its players struggling after the latest series
    there (poor for two series running, or three: one bad series doesn't count), with who could come in, their numbers
    at this level and as they are, and the verdict (ccstats/scouting.py, as the report card's "Who to bring in")."""
    marks = MK.series_marks(career)
    mine = marks[marks.team == team]
    mine = mine.assign(section=mine.best_match.map(career.matches.set_index("match_id").section))
    out = []
    for sec in MT.sections_of(career, team):
        done = mine[mine.section == sec].sort_values("end")
        row = dict(section=sec, series=done.label.iloc[-1] if len(done) else "", advice=[], none="")
        if done.empty:
            row["none"] = "No series or tournament finished here yet, so nobody has marks to judge."
        else:
            try:
                for r in kept(career, ("replacements", team, sec), lambda: SC.replacements(career, team, sec)):
                    row["advice"].append(dict(player=r["player"], role=r["role"], why=r["why"], verdict=r["verdict"],
                                              elsewhere=r["elsewhere"], own=r["own"], picks=r["picks"]))
            except Exception as e:  # noqa: BLE001 - one competition that can't be worked out never stops the others
                row["none"] = f"Couldn't be worked out ({type(e).__name__}: {e})"
            if not row["advice"] and not row["none"]:
                row["none"] = ("Nobody is struggling: no one has had two poor series running (4 or less in both) or three "
                               "(4 or less on average). One bad series alone doesn't count.")
        out.append(row)
    return SG.clean(dict(team=team, sections=out))


def whole_career(career) -> dict:
    """The current site's "Everything" tab, at the foot of My team: the career's numbers and the headlines from the 10
    matches played most recently anywhere (the table of every competition comes with Competitions in stage 2; the
    latest results anywhere are on Matches)."""
    m = career.matches
    return dict(matches=len(m), sections=int(m.section.nunique()), seasons=int(m.season.nunique()),
                players=int(career.batting.player.nunique()), runs=int(career.innings.runs.sum()),
                wickets=int(career.innings.wickets.sum()), headlines=E.headlines(career))
