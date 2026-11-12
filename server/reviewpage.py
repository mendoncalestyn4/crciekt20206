"""Season review and Honours (stage 2), as the current site's pages show them.

Season review: each competition's season in one place (the champions, Team of the Season, the leading players, the
breakout players, the best matches, the biggest upset, the records broken, your teams' report cards, the most
valuable players); international cricket gets a calendar-year review, awards style. Honours: every competition's
winners season by season, and each team's trophy cabinet. Every number comes from the same engine functions."""

from __future__ import annotations

from ccstats import extras as E
from ccstats import mvp as MV
from ccstats import seasonal as SN

from . import styleguide as SG
from .cache import kept
from .teampage import XI_HOW, fmt, table

INTL = "International cricket"
IMPACT_NOTE = ("Impact: runs, plus half the runs above what the format's strike rate would have made off the same balls "
               "in white-ball cricket; each wicket worth the format's runs per wicket (plus runs kept below its economy in "
               "white-ball cricket); a catch or stumping a quarter of a wicket. International seasons are calendar years.")


def choices(career) -> list[dict]:
    """Every competition's season and every international year, the latest first."""
    m = career.matches
    intl = SN.international_sections(career)
    secs = set(intl.values())
    opts = [(g.date.max(), sec, str(se)) for (sec, se), g in m[~m.section.isin(secs)].groupby(["section", "season"])]
    if intl:
        opts += [(g.date.max(), INTL, str(se)) for se, g in m[m.section.isin(secs)].groupby("season")]
    return [dict(key=f"{sec}|{se}", section=sec, season=se, label=f"{sec} {se}") for _, sec, se in sorted(opts, reverse=True)]


def _xi(xi, title) -> dict:
    if xi is None or xi.empty:
        return dict(title=title, none="Not enough games yet to pick an XI.")
    out = table(["", "Role", "Player", "Team", "Why"],
                [[i + 1, r.slot, r.player, r.team, r.why] for i, r in enumerate(xi.itertuples())], num={0})
    out.update(title=title, note=f"Picked by role: 2 openers, the middle order, a keeper (made a stumping), an all-rounder "
               f"(bats in the top 8; runs per innings × bowling) and 4 bowlers. {XI_HOW[xi.attrs.get('kind', 't20')]} "
               f"Needs {xi.attrs.get('need', 2)}+ games here. 'Best available': not enough players in that role, so the "
               "best of the rest.")
    return out


def _parts():
    out = {"missing": {}}

    def part(name, fn):
        try:
            out[name] = SG.clean(fn())
        except Exception as e:  # noqa: BLE001 - one part that can't be worked out never stops the others
            out[name] = None
            out["missing"][name] = f"Couldn't be worked out ({type(e).__name__}: {e})"
    return out, part


def review(career, q: dict, mine: list[str]) -> dict:
    ch = choices(career)
    out: dict = dict(choices=ch, pick="", section="", season="", none="")
    if not ch:
        out["none"] = "No matches yet."
        return out
    keys = [c["key"] for c in ch]
    pick = q.get("pick", "")
    if pick not in keys:   # your team's latest competition season, else the latest of all
        m = career.matches
        mm = m[m.home.isin(mine) | m.away.isin(mine)].sort_values("date") if mine else m.iloc[0:0]
        intl = set(SN.international_sections(career).values())
        if len(mm):
            r = mm.iloc[-1]
            want = f"{INTL if r.section in intl else r.section}|{r.season}"
            pick = want if want in keys else keys[0]
        else:
            pick = keys[0]
    section, season = pick.split("|", 1)
    out.update(pick=pick, section=section, season=season)
    if section == INTL:
        out["year"] = kept(career, ("year-review", season), lambda: _year(career, season))
    else:
        how = "ipl" if q.get("points") == "ipl" else "impact"
        out["season_review"] = kept(career, ("season-review", section, season, tuple(mine)),
                                    lambda: _season(career, section, season, mine))
        out["mvp"] = kept(career, ("season-mvp", section, season, how), lambda: _mvp(career, section, season, how))
    return SG.clean(out)


def _sval(career, season):
    s = career.matches.season
    return next((v for v in s.unique() if str(v) == season), season)


def _year(career, season) -> dict:
    out, part = _parts()

    def year():
        yr = SN.year_review(career, _sval(career, season))
        res = dict(title=f"International cricket {season}", counts=[dict(label=f"{f}s", value=d["matches"]) for f, d in yr["formats"].items()],
                   cricketer=None, formats=[], note=IMPACT_NOTE)
        if len(yr["cricketer"]):
            res["cricketer"] = table(["", "Player", "Team", "Impact", "Runs", "Wkts", "Matches", "Formats"],
                                     [[i + 1, r.player, r.team, f"{r.impact:.0f}", int(r.runs), int(r.wickets), int(r.matches), r.formats]
                                      for i, r in enumerate(yr["cricketer"].itertuples())], num={0, 3, 4, 5, 6})
        for f, d in yr["formats"].items():
            p0, tb, tw = d["player"], d["top_bat"], d["top_bowl"]
            res["formats"].append(dict(
                format=f, matches=int(d["matches"]),
                player=table(["", "Player", "Team", "Impact", "Runs", "Wkts"],
                             [[i + 1, r.player, r.team, f"{r.impact:.0f}", int(r.runs), int(r.wickets)]
                              for i, r in enumerate(p0.itertuples())], num={0, 3, 4, 5}) if len(p0) else None,
                most=" · ".join(([f"Most runs: {tb.player.iloc[0]} {int(tb.runs.iloc[0])}"] if len(tb) else [])
                                + ([f"Most wickets: {tw.player.iloc[0]} {int(tw.wickets.iloc[0])}"] if len(tw) else [])),
                xi=_xi(d["xi"], f"{f} Team of the Year {season}")))
        return res
    part("year", year)
    return out


def _season(career, section, season, mine) -> dict:
    out, part = _parts()

    def rv_():
        rv = SN.season_review(career, section, _sval(career, season), mine)
        ch = rv["champions"]
        res = dict(title=f"{section} {season}" + (" · so far" if rv["status"] != "complete" else ""),
                   complete=rv["status"] == "complete", matches=int(rv["matches"]),
                   champion=", ".join(ch.champions) if len(ch) else "–",
                   champions=[dict(team=r.champions, how=r.how, runners_up=r.runners_up or "",
                                   section="" if r.section == section else r.section) for r in ch.itertuples()],
                   final=None, leaders=None, xi=_xi(rv["xi"], f"Team of the Season · {section} {season}"),
                   best=None, upset="", records=None, records_none="", report_cards=[])
        f = rv["final"]
        if f is not None:
            res["final"] = dict(id=f.match_id, teams=f"{f.home} v {f.away}", result=f.result, pom=f.player_of_match or "")
        rows = [["Runs", r.player, f"{int(r.runs)} at {fmt(r.average, 1)}"] for r in rv["top_bat"].itertuples()]
        rows += [["Wickets", r.player, f"{int(r.wickets)} at {fmt(r.average, 1)}"] for r in rv["top_bowl"].itertuples()]
        bb, bw = rv["breakout_bat"], rv["breakout_bowl"]
        if len(bb):
            r = bb.iloc[0]
            rows.append(["Breakout batter", r.player, f"{r.now:+.1f} runs an innings above average (was {r.before:+.1f})"])
        if len(bw):
            r = bw.iloc[0]
            rows.append(["Breakout bowler", r.player, f"{r.now:+.1f} runs saved an innings (was {r.before:+.1f})"])
        res["leaders"] = table(["", "Player", ""], rows) if rows else None
        bm = rv["best_match"]
        if len(bm):
            res["best"] = table(["Match", "Rating", "Date", "Why"],
                                [[f"{r.home} v {r.away}", f"{r.rating:.1f}", f"{r.date:%d %b}", r.why] for r in bm.itertuples()],
                                num={1}, links=list(bm.match_id))
        up = rv["upset"]
        if len(up):
            u = up.iloc[0]
            res["upset"] = dict(id=u.match_id, text=f"{u.winner} beat {u.loser}",
                                why=f"{u.date:%d %b} ({u.chance:.0f}% chance going in by Elo, {u.winner_elo:.0f} v {u.loser_elo:.0f})")
        rec = rv["records"]
        if len(rec):
            res["records"] = table(["Record", "Holder", "New record", "Date", "Old record"],
                                   [[r.record, r.holder, r.value, f"{r.date:%d %b}", f"{r.old_value} ({r.old_holder})"]
                                    for r in rec.itertuples()])
            res["records"]["note"] = ("Records that stood at the start of the season and were beaten during it (the latest "
                                      "new mark if it fell more than once).")
        else:
            res["records_none"] = ("The first season here sets every record, so nothing could be broken yet." if rv["first_season"]
                                   else "No records broken: every record from earlier seasons survived.")
        res["report_cards"] = [dict(team=t, card=[dict(subject=s, grade=g, why=w) for s, g, w in rc])
                               for t, rc in rv["report_cards"].items()]
        return res
    part("review", rv_)
    return out


def _mvp(career, section, season, how) -> dict:
    out, part = _parts()

    def mvp_():
        dots = bool(MV.counts_dots(career, section))
        how_ = how if dots else "impact"
        mvp = MV.season_mvp(career, section, _sval(career, season), how_)
        res = dict(points=how_, choose=dots, table=None, bars=[], shows="", for_="", note="")
        if mvp.empty:
            res["none"] = "No players yet."
            return res
        top = mvp.head(15)
        res["table"] = table(["#", "Player", "Team", "Matches", "Batting", "Bowling", "Fielding", "Points", "Per match"],
                             [[i, r.player, r.team, int(r.matches), fmt(r.batting, 0), fmt(r.bowling, 0), fmt(r.fielding, 0),
                               fmt(r.points, 0), fmt(r.per_match, 1)] for i, r in enumerate(top.itertuples(), start=1)],
                             num={0, 3, 4, 5, 6, 7, 8})
        res["bars"] = [dict(player=r.player, team=r.team, value=round(float(r.points)),
                            note=f"{r.matches} matches · batting {r.batting:.0f}, bowling {r.bowling:.0f}, fielding {r.fielding:.0f}")
                       for r in mvp.head(10).itertuples()]
        a, b = mvp.iloc[0], mvp.iloc[1] if len(mvp) > 1 else None
        best_pm = mvp[mvp.matches >= max(3, int(mvp.matches.max() * 0.5))].sort_values("per_match", ascending=False)
        res["shows"] = (f"{a.player} ({a.team}) lead on {a.points:.0f} points from {a.matches} matches"
                        + (f", {a.points - b.points:.0f} ahead of {b.player}" if b is not None else "")
                        + (f". Best per match among regulars: {best_pm.iloc[0].player} on {best_pm.iloc[0].per_match:.1f}"
                           if len(best_pm) else "") + ".")
        res["for_"] = "One number for who mattered most this season, with bat, ball and in the field together."
        res["note"] = ("IPL MVP points, as the IPL counts them: 3.5 a wicket, 1 a dot ball, 2.5 a four, 3.5 a six, 2.5 a "
                       "catch and 2.5 a stumping." if how_ == "ipl" else
                       "Impact points (the match impact on the Player stories page): runs, plus in white-ball cricket half "
                       "the runs above or below what this competition's usual strike rate would have made off the same "
                       "balls; each wicket worth this competition's runs per wicket, plus in white-ball cricket the runs "
                       "kept below its usual economy; a catch or stumping a quarter of a wicket. A name that plays for two "
                       "teams in one season is two players, so each team's is listed on its own.")
        return res
    part("mvp", mvp_)
    return out


def honours(career, q: dict, mine: list[str]) -> dict:
    tab = "Trophy cabinets" if q.get("tab") == "Trophy cabinets" else "Honours board"
    out: dict = dict(tabs=["Honours board", "Trophy cabinets"], tab=tab, none="")
    h = kept(career, ("honours",), lambda: E.honours(career))
    if h.empty:
        out["none"] = ("No competition has been decided yet. Champions appear once a final is played (or, for a league with "
                       "no final like the County Championship, once the season is over).")
        return out
    if tab == "Honours board":
        boards = []
        for section in h.drop_duplicates("section").section:
            g = h[h.section == section]
            t = table(["Season", "Champions", "How", "Runners-up", "Most runs", "Most wickets", "Player of the final"],
                      [[str(s), ("🏆 " + c) if "so far" not in w else c, w, ru or "", tr or "", tw or "", fp or ""]
                       for s, c, w, ru, tr, tw, fp in zip(g.season, g.champions, g.how, g.runners_up, g.top_runs,
                                                          g.top_wickets, g.final_potm)],
                      hi=[bool(set(ct) & set(mine)) for ct in g.champion_teams])
            t["title"] = section
            boards.append(t)
        out["boards"] = boards
        out["note"] = ("Champions come from the final. A league with no final (like the County Championship) is won by the "
                       "team top of the table once the season is over; until then it shows who is leading. Bilateral "
                       "series are on the Competitions page.")
    else:
        won = h[~h.how.str.contains("so far")].explode("champion_teams")
        counts = won.champion_teams.value_counts()
        if counts.empty:
            out["cabinet"] = None
            out["cabinet_none"] = "No titles decided yet."
        else:
            out["cabinet"] = table(["Team", "Titles", "Won"],
                                   [[t, int(n), ", ".join(f"{s} {y}" + (" (shared)" if "shared" in w else "")
                                                          for s, y, w in zip(won[won.champion_teams == t].section,
                                                                             won[won.champion_teams == t].season,
                                                                             won[won.champion_teams == t].how))]
                                    for t, n in counts.items()], num={1}, hi=[t in mine for t in counts.index])
    return SG.clean(out)
