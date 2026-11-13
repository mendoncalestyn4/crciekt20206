"""Season review and Honours (stage 2), as the current site's pages show them.

Season review: each competition's season in one place (the champions, Team of the Season, the leading players, the
breakout players, the best matches, the biggest upset, the records broken, your teams' report cards, the most
valuable players); international cricket gets a calendar-year review, awards style. Honours: every competition's
winners season by season, and each team's trophy cabinet. Every number comes from the same engine functions."""

from __future__ import annotations

from ccstats import extras as E
from ccstats import mvp as MV
from ccstats import seasonal as SN
from ccstats import wrapped as WR
from ccstats.stats import ordinal

from . import matchpage
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
        out["none"] = SG.NO_MATCHES
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
    wview = "whole" if q.get("wview", "") == "whole" else ""
    out["wrapped"] = kept(career, ("wrapped", section, season, q.get("wteam", ""), q.get("wfmt", ""), tuple(mine), wview),
                          lambda: _wrapped(career, section, season, q.get("wteam", ""), q.get("wfmt", ""), mine, wview))
    if section == INTL:
        out["year"] = kept(career, ("year-review", season), lambda: _year(career, season))
    else:
        how = "ipl" if q.get("points") == "ipl" else "impact"
        out["season_review"] = kept(career, ("season-review", section, season, tuple(mine)),
                                    lambda: _season(career, section, season, mine))
        out["mvp"] = kept(career, ("season-mvp", section, season, how), lambda: _mvp(career, section, season, how))
        out["winners"] = kept(career, ("season-winners", section, season, tuple(mine)),
                              lambda: _winners(career, section, season, mine))
    return SG.clean(out)


def _winners(career, section, season, mine) -> dict:
    """The match-winners chart under the MVPs: who won the team's matches this season (its players of the match in
    its wins, and what they did each time); the team yours when you played here, else the side with the most wins."""
    out, part = _parts()

    def winners():
        m = career.matches
        here = m[(m.section == section) & (m.season == _sval(career, season))]
        teams = set(here.home) | set(here.away)
        if not teams:
            return None
        wins = here.winner.value_counts()
        team = next((t for t in mine if t in teams), None) or sorted(teams, key=lambda t: (-int(wins.get(t, 0)), t))[0]
        w = SG.match_winners(SG.results(career, team, here.match_id), team)
        return dict(w, team=team, yours=team in mine)
    part("winners", winners)
    return out


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
        # the season's best matches on the match excitement rating (the one the Matches pages use)
        rt = matchpage.ratings(career, section)
        sids = set(career.matches[(career.matches.section == section) & (career.matches.season == _sval(career, season))].match_id)
        bm = rt[rt.match_id.isin(sids)].sort_values(["rating", "date"], ascending=[False, False]).head(3)
        if len(bm):
            res["best"] = table(["Match", "Rating", "Date", "Why"],
                                [[f"{r.home} v {r.away}", f"{r.rating:.1f}", f"{r.date:%d %b}",
                                  f"{r.why} ({ordinal(int(r['rank']))} of {int(r['of'])} here)"] for _, r in bm.iterrows()],
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


def _cap(s: str) -> str:
    """The first letter a capital, the rest as it is (str.capitalize would lower every team's name after it)."""
    return s[:1].upper() + s[1:]


def _ord(n: int) -> str:
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def _wrapped(career, section, season, asked, fmt_pick, mine, view="") -> dict:
    """Your season, wrapped: one team's season as ten slides (ccstats.wrapped). International cricket is one format at
    a time (Tests, ODIs and T20Is are never mixed); the team is yours when you played here, else the side with the
    most matches."""
    out, part = _parts()

    def wrapped():
        team = asked
        m = career.matches
        formats, fmt = [], ""
        sec = section
        if section == INTL:
            intl = SN.international_sections(career)
            sv = _sval(career, season)
            formats = [f for f, s_ in intl.items() if ((m.section == s_) & (m.season == sv)).any()]
            if not formats:
                return dict(none="No international matches this year.", formats=[], format="", teams=[], team="")
            sv_ = _sval(career, season)
            yours = [f for f in formats if ((m.section == intl[f]) & (m.season == sv_) & (m.home.isin(mine) | m.away.isin(mine))).any()]
            fmt = fmt_pick if fmt_pick in formats else (yours or formats)[0]
            sec = intl[fmt]
        sv = _sval(career, season)
        here = m[(m.section == sec) & (m.season == sv)]
        played = (here.home.value_counts().add(here.away.value_counts(), fill_value=0)).sort_values(ascending=False)
        teams = sorted(played.index)
        if not teams:
            return dict(none="No matches here yet.", formats=formats, format=fmt, teams=[], team="")
        if team not in teams:
            yours = [t for t in mine if t in teams]
            team = yours[0] if yours else sorted(teams, key=lambda t: (-played[t], t))[0]
        whole = view == "whole"
        if whole:   # the whole April-to-March season, every format together (the owner's exception, this view only)
            dates = sorted(here.date)
            year = SN.april_year(dates[len(dates) // 2])
            w = WR.whole_season_wrapped(career, year, team, ratings_for=lambda s_: matchpage.ratings(career, s_))
            label = f"the whole {w['season']} season"
        else:
            w = WR.season_wrapped(career, sec, sv, team, ratings=matchpage.ratings(career, sec))
            label = f"{sec} {season}"
        slides = []

        def add(key, kicker, head, big="", unit="", lines=(), mid=None):
            slides.append(dict(key=key, kicker=kicker, head=head, big=big, unit=unit, lines=[x for x in lines if x], id=mid))

        r = w.get("record")
        if r:
            bits = [f"won {r['won']}", f"lost {r['lost']}"] + ([f"drawn {r['drawn']}"] if r["drawn"] else []) \
                + ([f"tied {r['tied']}"] if r["tied"] else []) + ([f"no result {r['no_result']}"] if r["no_result"] else [])
            add("record", "The season", f"{team} · {label}", str(r["played"]), "matches" if r["played"] != 1 else "match",
                [_cap(", ".join(bits)), f"Win rate {r['win_pct']:.0f}%"])
        x = w.get("runs")
        if x:
            add("runs", "Top run-scorer", x["player"], str(x["runs"]), "runs",
                [f"{x['innings']} innings" + (f" · average {x['average']:.1f}" if x["average"] is not None else " · never out"),
                 f"Best: {x['best']}"])
        x = w.get("wickets")
        if x:
            add("wickets", "Top wicket-taker", x["player"], str(x["wickets"]), "wickets",
                [f"Average {x['average']:.1f}" + (f" · economy {x['economy']:.2f}" if x["economy"] is not None else "")])
        x = w.get("score")
        if x:
            add("score", "Highest score", x["player"], f"{x['runs']}{'*' if x['notout'] else ''}", "runs",
                [f"off {x['balls']} balls" + (" · not out" if x["notout"] else ""), f"v {x['against']} · {x['date']}"], x["id"])
        x = w.get("bowling")
        if x:
            add("bowling", "Best bowling", x["player"], f"{x['wickets']}/{x['runs']}", "",
                [f"v {x['against']} · {x['date']}"], x["id"])
        x = w.get("stand")
        if x:
            add("stand", "Biggest stand", x["pair"] or f"{_ord(x['wicket'])} wicket", f"{x['runs']}{'*' if x['unbroken'] else ''}", "runs",
                [f"for the {_ord(x['wicket'])} wicket" + (" · unbroken" if x["unbroken"] else ""), f"v {x['against']} · {x['date']}"], x["id"])
        x = w.get("streak")
        if x:
            add("streak", "Longest winning run", f"{x['wins']} in a row" if x["wins"] > 1 else "One win at a time",
                str(x["wins"]), "wins" if x["wins"] != 1 else "win",
                [f"{x['start']} to {x['end']}" if x["wins"] > 1 else f"No two wins in a row yet · {x['end']}"])
        x = w.get("win")
        if x:
            also = x.get("also")
            add("win", "Biggest win", f"v {x['against']}", "", "",
                [x["result"], x["date"]] + ([f"Biggest chasing win: {also['result'].split(' won ', 1)[-1]} v {also['against']}"] if also else []),
                x["id"])
        x = w.get("game")
        if x:
            add("game", "Best game", x["teams"], f"{x['rating']:.1f}", "out of 10",
                [x["result"], _cap(x["why"]), f"{x['date']} · the {ordinal(x['rank'])} best of {x['of']} here" if x.get("rank") else x["date"]], x["id"])
        x = w.get("player")
        if x:
            add("player", "Player of the season", x["player"], f"{x['points']:.0f}", "impact points",
                [f"{x['matches']} match{'es' if x['matches'] != 1 else ''} · batting {x['batting']:.0f}, bowling {x['bowling']:.0f}, fielding {x['fielding']:.0f}"])
        note = ("Every figure is the team's own in this competition and season, from the scorecards as printed. "
                "Best game: the excitement rating out of 10 (Matches page). Player of the season: the most impact "
                "points (below). * not out or unbroken.")
        if whole:
            note = (f"The whole April-to-March season, every format {team} played added up: "
                    + ", ".join(w.get("sections", [])) + ". Runs, wickets and records count across them all (this view "
                    "only: everywhere else formats are kept apart). Best game: each match on its own competition's "
                    "excitement rating. Player of the season: impact points added up over every competition, each "
                    "counted against its own competition's averages. * not out or unbroken.")
        return dict(none="" if slides else f"{team} haven't played here yet.", formats=formats, format=fmt, teams=teams,
                    team=team, section=sec if not whole else "", season=season if not whole else w["season"], slides=slides,
                    view="whole" if whole else "", note=note)
    part("wrapped", wrapped)
    return out
