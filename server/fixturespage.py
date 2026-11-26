"""Fixtures (stage 4): your schedule, as the current site's Fixtures page (views/fixtures.py) shows it, with the same
engine functions and words, in the same 8 tabs: Schedule, Add matches, Change or delete, Series, Calendar, WTC race,
Milestones, Goals.

Your answers of 26 November: schedules are made only for your teams (every other team's matches come from the
scorecards by themselves); a franchise or county picks its competition, with opponents from that league; all four
ways of adding stay; a list of recent changes, each with its own undo; the old four goals plus ten new kinds;
goals suggested each season; how good the predictions are; the last time against each opponent coming up; the
tournament path. The sums are in the engine (ccstats/fixtures.py, planning.py, goals.py, winprob.py); this only turns
them into what the page shows, and changes the schedule, goals and notes in the same file the current site reads."""

from __future__ import annotations

import calendar as CAL
import datetime as dt
import time

import numpy as np
import pandas as pd

from ccstats import catalogue as CAT
from ccstats import fixtures as FX
from ccstats import goals as GL
from ccstats import planning as PLN
from ccstats import seasonal as SN
from ccstats import winprob as WP

from . import styleguide as SG
from .cache import kept
from .teampage import fmt, table

TABS = ["Schedule", "Add matches", "Change or delete", "Series", "Calendar", "WTC race", "Milestones", "Goals"]
VENUE_WORD = {"home": "at home", "away": "away", "neutral": "neutral venue"}
ICON = {"played": "✅", "next": "⏭", "to come": "⏳", "no scorecard": "⚠️"}
LEVEL_ICON = {"easy": "🟢", "even": "⚪", "hard": "🔴"}
BADGE = {"achieved": "✅", "missed": "❌", "on course": "🟢", "at risk": "🟠", "under way": "🔵", "to come": "⏳"}
HISTORY_KEPT = 20
# a franchise's or county's competitions and the format their matches are (your answer 3: pick the competition)
COMP_FORMAT = {**{lg: ("The Hundred" if lg == "The Hundred" else "T20") for lg in CAT.LEAGUES},
               "County Championship": "First-class", "T20 Blast": "T20", "One-Day Cup": "List A",
               "Ranji Trophy": "First-class", "Vijay Hazare Trophy": "List A", "Syed Mushtaq Ali Trophy": "T20",
               "Sheffield Shield": "First-class", "Marsh One-Day Cup": "List A", "Plunket Shield": "First-class",
               "Ford Trophy": "List A", "Super Smash": "T20"}

HOW_TO = (
    "**How to add your schedule**\n"
    "1. Open the **Add matches** tab.\n"
    "2. Pick the **opponent**, the **format**, **how many matches**, **home or away** and the **month**.\n"
    "3. Press **Add series**. Do the same for each series in your year (a World Cup goes under **Tournament**).\n"
    "4. Dates are up to you. Know them from the game's fixture list? Switch on **I know the dates** and type each "
    "match's date: your next match and the calendar are then exact. Leave any out and it's worked out from the "
    "match before it (shown as *about 12 Jun*). Either way, a match takes its real date from its scorecard once "
    "it's played.\n\n"
    "Made a mistake, or the game moved a series? Open the **Change or delete** tab: every series and tournament you "
    "added has ✏️ Change and 🗑️ Delete (and every change can be undone from the list of recent changes).\n\n"
    "**Forgot something?** No problem: any match your team plays that isn't in your schedule is added by itself "
    "(marked *auto-added*), with the rest of its series. In a tournament, the semi-final and final are added once "
    "you're through to them.")
SCHEDULE_CAPTION = (
    "A match is ticked off when the game saves its scorecard: it's matched by the two teams, the format and its place "
    "in the series, so dates don't need to be exact. Click a result for its scorecard. Home and away come from the "
    "scorecards (the side named first is at home); 📍 marks a series you put at the other venue (hover it). Mark a "
    "series neutral if it was played at a neutral ground. 🆕 Auto-added: played but not in your schedule (or more "
    "matches than you put in), so added from the scorecards with the rest of its series. In a tournament, the next "
    "knockout game (semi-final, final …) appears once you're through to it, against the winner of the other tie when "
    "that's been played. Your chance: of winning that game (hover for the draw and defeat), 🟢 easy · ⚪ even · 🔴 hard. "
    "Their form: the opponent's last 5 in that format; 👻 a bogey team (you've won 30% or less against them), 😊 a "
    "favourite opponent (70% or more). Last time: your last meeting in that format.")
TABLE_CAPTION = (
    "Change any cell, add a row at the bottom, or select rows and press delete (the bin icon). Then press **Save "
    "changes**. Month: like 'Jan 2027'. Date: only if you know it. Matches already played keep their result whatever "
    "you change here. Auto-added matches aren't in this table (they come from the scorecards); add the series here "
    "yourself to set its home or away.")


# --------------------------------------------------------------------------- the team, its opponents and formats
def _context(career, team: str) -> dict:
    m = career.matches
    all_teams = sorted(set(m.home) | set(m.away))
    national = team in FX.NATIONS
    rivals_ = {t for t in CAT.rivals(team) if t in all_teams or not (CAT.aliases(t) & set(all_teams))}
    if national:
        opps = sorted(t for t in (set(all_teams) | FX.NATIONS) if t in FX.NATIONS and t != team)
        formats = ["Test", "ODI", "T20I"]
        comps = []
    else:
        played_secs = list(m[(m.home == team) | (m.away == team)].section.unique())
        names = list(dict.fromkeys(CAT.home_sections(team) + [s for s in played_secs]))
        comps = []
        for c in names:
            here = m[m.section == c]
            f = here.format.mode().iloc[0] if len(here) else COMP_FORMAT.get(c.split(" · ")[0], "")
            if not f or f in FX.INTL:
                continue
            league = sorted((CAT.expected(c) | set(here.home) | set(here.away)) - {team})
            comps.append(dict(name=c, format=f, opponents=league or sorted(rivals_)))
        opps = sorted(rivals_) + [t for t in all_teams if t not in rivals_ and t != team]
        formats = ["T20", "The Hundred", "List A", "First-class"]
    latest = m.date.max()
    year_now = int(latest.year) if pd.notna(latest) else dt.date.today().year
    return dict(all_teams=all_teams, national=national, opponents=opps, formats=formats, competitions=comps,
                year_now=year_now, month_now=int(latest.month) if pd.notna(latest) else 1,
                years=list(range(year_now - 1, year_now + 4)), known=all_teams + [t for t in opps if t not in all_teams])


def _when(r) -> str:
    if r["status"] == "played":
        return f"{pd.Timestamp(r['played_date']):%d %b %Y}"
    if r["date"]:
        return f"{pd.Timestamp(r['date']):%d %b %Y}"
    if str(r.get("estimated")) == "True" and pd.notna(r.get("anchor")):
        return f"about {pd.Timestamp(r['anchor']):%d %b %Y}"
    return FX.month_label(r["month"]) or "date to come"


def _stage(r) -> str:
    s = r.get("stage")
    return s if isinstance(s, str) else ""


def _next_title(r) -> str:
    name = r["series"].replace(FX.AUTO, "").split(" · ")[0]
    if _stage(r):
        return f"{name} {_stage(r)} · " + (f"v {r['opponent']}" if r["opponent"] else "opponent to be decided")
    return (f"v {r['opponent']} · {r['format']}" if r["opponent"] else name) + (f" · match {int(r['no'])}" if r["no"] else "")


def _preview_link(career, team: str, opp: str, fmt_: str, venue: str) -> dict:
    """Where Opponent preview opens for this game: the international section for a Test, ODI or T20I, else the team's
    own section in that format (as the current site's "Full preview" button)."""
    m = career.matches
    if fmt_ in FX.INTL:
        secs = SN.international_sections(career)
        section = secs.get(fmt_, "")
    else:
        mine_f = m[(m.format == fmt_) & ((m.home == team) | (m.away == team))]
        any_f = mine_f if len(mine_f) else m[m.format == fmt_]
        section = any_f.sort_values("date").section.iloc[-1] if len(any_f) else ""
    return dict(section=section, mine=team, opp=opp, where={"home": "Home", "away": "Away"}.get(venue, "Neutral"))


def _tracked(career, sched: list[dict], team: str) -> pd.DataFrame:
    import json
    sig = json.dumps(sched, sort_keys=True, default=str)
    return kept(career, ("fx-track", team, sig), lambda: FX.track(career, sched, auto=(team,)))


# --------------------------------------------------------------------------- the page
def page(career, q: dict, mine: list[str], settings) -> dict:
    """The page for one of your teams and one tab. `settings`: the career's saved settings (schedule, goals, notes,
    forecasts, recent changes)."""
    teams = list(mine)
    tab = q.get("tab", "") if q.get("tab", "") in TABS else TABS[0]
    out: dict = dict(tabs=TABS, tab=tab, teams=teams, team="", how_to=HOW_TO, none="")
    if not teams:
        out["none"] = ("Pick the teams you play as first (Settings → Your teams): your schedule is made for your own "
                       "teams; every other team's matches come from the scorecards by themselves.")
        return SG.clean(out)
    team = q.get("team", "") if q.get("team", "") in teams else teams[0]
    out["team"] = team
    sched = list(settings.fixtures) if settings else []
    goals = list(settings.goals) if settings else []
    notes = dict(settings.notes) if settings else {}
    saved_fc = dict(settings.forecasts) if settings else {}
    tracked = _tracked(career, sched, team)
    mine_rows = tracked[tracked.team == team] if len(tracked) else tracked
    ctx = _context(career, team)
    out.update(national=ctx["national"], scheduled_any=any(r.get("team") == team for r in sched),
               formats=ctx["formats"], competitions=ctx["competitions"], opponents=ctx["opponents"],
               years=ctx["years"], year_now=ctx["year_now"], month_now=ctx["month_now"],
               tournaments=FX.TOURNAMENTS, tournament_format=FX.TOURNAMENT_FORMAT,
               history=_history(settings, team))
    body = {"Schedule": lambda: _schedule(career, team, tracked, mine_rows, sched, notes, out["scheduled_any"], ctx),
            "Add matches": lambda: {},
            "Change or delete": lambda: _change(career, team, tracked, sched, ctx),
            "Series": lambda: _series(career, team, tracked, notes, saved_fc, goals),
            "Calendar": lambda: _calendar(career, team, q, sched),
            "WTC race": lambda: _wtc(career, team, tracked),
            "Milestones": lambda: _milestones(career, team, tracked, mine_rows),
            "Goals": lambda: _goals(career, team, tracked, goals, ctx)}[tab]
    try:
        out["body"] = body()
    except Exception as e:  # noqa: BLE001 - a part that can't be shown never breaks the rest of the page
        out["body"] = dict(missing=f"Couldn't be worked out ({type(e).__name__}: {e}).")
    return SG.clean(out)


def new_forecasts(career, settings, team: str) -> dict:
    """The forecasts to keep for the team's series that haven't started (made once, before ball one)."""
    sched = list(settings.fixtures) if settings else []
    tracked = _tracked(career, sched, team)
    return PLN.take_forecasts(career, tracked, team, dict(settings.forecasts) if settings else {})


def _history(settings, team: str) -> list[dict]:
    rows = [h for h in (getattr(settings, "fixture_changes", None) or []) if h.get("team") == team]
    return [dict(id=h["id"], what=h["what"], at=h.get("when", "")) for h in reversed(rows)]


# --------------------------------------------------------------------------- Schedule
def _schedule(career, team, tracked, mine_rows, sched, notes, scheduled_any, ctx) -> dict:
    out: dict = {}
    if mine_rows is None or mine_rows.empty:
        out["empty"] = f"No schedule for {team} yet."
        out["preview_any"] = _preview_any(career, team, mine_rows, ctx)
        return out
    if not scheduled_any:
        out["info"] = (f"Nothing scheduled for {team} yet, so these are the matches they've played this year, added "
                       "from the scorecards. Add what's coming on the **Add matches** tab to see it here too.")
    sm = FX.summary(tracked, team)
    rec, nx = sm["record"], sm["next"]
    out["kpis"] = [["Played", f"{sm['played']} of {sm['total']}"],
                   ["Won–lost", f"{rec['W']}–{rec['L']}" + (f" ({rec['D']} D)" if rec["D"] else "")],
                   ["To come", f"{sm['to_come']}"],
                   ["Next", f"v {nx['opponent']}" if nx is not None and nx["opponent"] else
                    (_stage(nx) or nx["series"].replace(FX.AUTO, "").split(" · ")[0]) if nx is not None else "–"]]
    issues = PLN.check(career, sched, tracked, team)
    out["check"] = [dict(text=x["text"], series=x["series"], kind=x["kind"],
                         fix=("delete" if x["fix"].get("delete") else "fix") if x["fix"] else "") for x in issues]
    out["check_ok"] = bool(scheduled_any and not issues)
    if nx is not None:
        nfmt, nopp, nven = nx["format"], nx["opponent"], nx["venue"]
        card = dict(title=_next_title(nx), venue=VENUE_WORD.get(nven, ""), when=_when(nx), opponent=nopp or "",
                    note=notes.get(f"series::{team}::{nx['series']}", ""))
        if nopp:
            ids = FX.format_ids(career, team, nfmt)
            p = WP.predict(career, ids, team, nopp, nven if nven in ("home", "away") else "neutral")
            card["chance"] = dict(win=round(p["win"]), draw=round(p["draw"]), lose=round(p["lose"]), multi=bool(p["multi"]))
            card["form"] = PLN.form(career, nopp, nfmt)
            card["rivalry"] = _rivalry_text(career, team, nopp, nfmt)
            card["streaks"] = PLN.streaks(career, team, nopp, nfmt, nven)
            card["battles"] = FX.key_battle(career, team, nopp, nfmt)
            card["preview"] = _preview_link(career, team, nopp, nfmt, nven)
            card["last"] = _last(career, team, nopp, nfmt)
        out["next"] = card
    out["preview_any"] = _preview_any(career, team, mine_rows, ctx)
    if sm["missing"]:
        out["missing_warn"] = (f"⚠️ {sm['missing']} fixture{'s' if sm['missing'] != 1 else ''} should have been played by "
                               "now but no scorecard matches. Check the month and opponent in the table below, or "
                               "whether the game saved the scorecard.")
    ch = PLN.chances(career, tracked, team)
    chance_of = {(r.series, int(r.no)): r for r in ch.itertuples()}
    form_of: dict = {}
    rows = []
    for _, r in mine_rows.iterrows():
        stage = _stage(r)
        res, rid = "", None
        if r["status"] == "played":
            res, rid = f"{r['outcome']} · {r['result']}", r["match_id"]
        elif stage:
            res = f"{stage} to come"
        elif r["kind"] == "tournament":
            gl_ = int(r["games_left"]) if pd.notna(r.get("games_left")) and r.get("games_left") else 0
            res = f"{gl_} more game{'s' if gl_ != 1 else ''} planned" if gl_ else "games to come"
        no = (f"{int(r['no'])}" if r["no"] else "") + (f" · {stage}" if stage else "")
        if stage == "Final" and r["status"] == "played" and r["outcome"] == "W":
            no += " 🏆"
        venue_note = ""
        if str(r.get("venue_fixed")) == "True":
            planned, real = VENUE_WORD.get(r.get("venue_planned", ""), ""), VENUE_WORD.get(r["venue"], "")
            venue_note = (f"You put this series {planned}, but its scorecards show {team} {real}: the scorecards are "
                          f"used. Change Home/away in the table on the Change or delete tab to match.")
        opp = r["opponent"] if r["kind"] == "tournament" else ""
        if r["kind"] == "tournament" and stage and not opp and r["status"] != "played":
            opp = "to be decided"
        row = dict(icon=ICON.get(r["status"], ""), status=r["status"], series=r["series"].replace(FX.AUTO, ""),
                   auto=str(r.get("auto")) == "True", badge=r["opponent"] if r["kind"] == "match" and r["opponent"] else "",
                   venue_note=venue_note, venue_real=VENUE_WORD.get(r["venue"], "") if venue_note else "",
                   no=no, opponent=opp, when=_when(r), result=res, id=rid)
        k_ = (r["series"], int(r["no"] or 0))
        if r["status"] in ("next", "to come") and k_ in chance_of:
            x = chance_of[k_]
            row["chance"] = dict(win=round(x.win), draw=round(x.draw), lose=round(x.lose), level=x.level,
                                 icon=LEVEL_ICON[x.level])
            fk = (x.opponent, x.format)
            if fk not in form_of:
                rv = PLN.rivalry(career, team, x.opponent, x.format)
                form_of[fk] = dict(form=PLN.form(career, x.opponent, x.format),
                                   rivalry=(dict(kind=rv["kind"], icon="👻" if rv["kind"] == "bogey" else "😊",
                                                 tip=f"{'Bogey team' if rv['kind'] == 'bogey' else 'Favourite opponent'}: "
                                                     f"{team} are {rv['text']} against them") if rv else None),
                                   last=_last(career, team, x.opponent, x.format))
            row.update(form_of[fk])
        rows.append(row)
    out["rows"] = rows
    out["caption"] = SCHEDULE_CAPTION
    out["outlook"] = _outlook(career, team, tracked)
    return out


def _last(career, team, opp, fmt_) -> dict | None:
    lm = PLN.last_meeting(career, team, opp, fmt_)
    if not lm:
        return None
    bits = []
    if lm["top"]:
        bits.append(f"top score {lm['top']['player']} {lm['top']['runs']}")
    if lm["best"]:
        bits.append(f"best bowling {lm['best']['player']} {lm['best']['wickets']}/{lm['best']['runs']}")
    return dict(id=lm["match_id"], date=f"{pd.Timestamp(lm['date']):%d %b %Y}", outcome=lm["outcome"],
                result=lm["result"], text=f"{pd.Timestamp(lm['date']):%d %b %Y}: {lm['result']}"
                + (f" ({'; '.join(bits)})" if bits else ""),
                players=[x["player"] for x in (lm["top"], lm["best"]) if x])


def _rivalry_text(career, team, opp, fmt_) -> str:
    rv = PLN.rivalry(career, team, opp, fmt_)
    if not rv:
        return ""
    games = FX.plural(fmt_, 2).split(" ", 1)[1]
    return (f"👻 **Bogey team:** {team} are {rv['text']} against them in {games}" if rv["kind"] == "bogey" else
            f"😊 **Favourite opponent:** {team} are {rv['text']} against them in {games}")


def _preview_any(career, team, mine_rows, ctx) -> dict | None:
    m = career.matches
    todo = mine_rows[mine_rows.status.isin(["next", "to come"]) & (mine_rows.opponent.fillna("") != "")] \
        if mine_rows is not None and len(mine_rows) else None
    sched_o = list(dict.fromkeys(todo.opponent)) if todo is not None and len(todo) else []
    national = ctx["national"]
    rivals_ = set(CAT.rivals(team))
    pool = set(ctx["all_teams"]) | (FX.NATIONS if national else rivals_)
    if national:
        pool &= FX.NATIONS
    rest = sorted(pool - set(sched_o) - {team})
    opts = [t for t in sched_o if t != team] + rest
    if not opts:
        return None
    formats = ctx["formats"]
    defaults = {}
    for o in opts:
        their = todo[todo.opponent == o] if todo is not None and len(todo) else None
        f = their.format.iloc[0] if their is not None and len(their) else None
        if f is None:
            last_ = m[((m.home == team) | (m.away == team)) & m.format.isin(formats)].sort_values("date")
            f = last_.format.iloc[-1] if len(last_) else formats[0]
        v = their.venue.iloc[0] if their is not None and len(their) else ""
        defaults[o] = dict(format=f if f in formats else formats[0], venue=v)
    links = {o: {f: _preview_link(career, team, o, f, defaults[o]["venue"] if defaults[o]["format"] == f else "")
                 for f in formats} for o in opts}
    return dict(options=opts, scheduled=sched_o, formats=formats, defaults=defaults, links=links)


def _outlook(career, team, tracked) -> dict | None:
    ch_all = PLN.chances(career, tracked, team)
    if ch_all.empty:
        return None
    sy = SN.april_year(ch_all.anchor.min())
    start, end = pd.Timestamp(year=sy, month=4, day=1), pd.Timestamp(year=sy + 1, month=4, day=1)
    pr = PLN.projection(career, tracked, team, start, end)
    ch = pr["chances"]
    if ch.empty:
        return None
    now = pr["now"]

    def drawn(d):
        return f" ({d:.0f} D)" if round(d) else ""
    out = dict(title=f"The season ahead · {sy}–{str(sy + 1)[-2:]} (Apr {sy} – Mar {sy + 1})",
               left=f"{len(ch)} match{'es' if len(ch) != 1 else ''} left with a known opponent",
               kpis=[["Record so far", f"{now['W']}–{now['L']}" + drawn(now["D"])],
                     ["Heading for", f"{pr['exp_won']:.0f}–{pr['exp_lost']:.0f}" + drawn(pr["exp_drawn"])],
                     ["Likely wins", f"{pr['low']} to {pr['high']}"],
                     ["Easy · even · hard", " · ".join(str(int((ch.level == k).sum())) for k in ("easy", "even", "hard"))]])
    tough = PLN.toughest_run(ch)
    if tough and tough["hard"]:
        rr = tough["rows"]
        what = ", ".join(f"v {r.opponent} ({r.format} {int(r.no)})" for r in rr.itertuples())
        out["tough"] = (f"**Toughest run:** {what} ({rr.when.iloc[0]} to {rr.when.iloc[-1]}): your chance of winning "
                        f"averages {rr.win.mean():.0f}%.")
    out["bars"] = [dict(label=f"{r.when} · v {r.opponent} · {r.format} {int(r.no)}", value=round(float(r.win), 1),
                        level=r.level, tip=f"win {r.win:.0f}%" + (f" · draw {r.draw:.0f}%" if r.draw >= 0.5 else "")
                        + f" · lose {r.lose:.0f}%", team=r.opponent) for r in ch.itertuples()]
    hardest = ch.iloc[int(np.argmin(ch.win.to_numpy()))]
    out.update(SG.lines(f"Your chance of winning each game left in the season, {len(ch)} games, easiest to hardest by colour.",
                        f"v {hardest.opponent} ({hardest.when}), {hardest.win:.0f}% to win",
                        "Shows which games to rest players for and which to go all out in. Green: easy (you win 60% or "
                        "more of the games that end in a result), grey: even, red: hard (40% or less); in a Test the "
                        "draws are left out of that, so a 35% win chance with many draws can still be even. Each game's "
                        "chance is the same one Opponent preview gives (Elo ratings, form, head to head and venue).",
                        best_label="Hardest"))
    out["shows"] = (f"{int((ch.level == 'easy').sum())} easy, {int((ch.level == 'even').sum())} even and "
                    f"{int((ch.level == 'hard').sum())} hard; the hardest is v {hardest.opponent} ({hardest.when}, "
                    f"{hardest.win:.0f}% to win).")
    bf = pr["by_format"]
    if bf:
        out["by_format"] = table(["Format", "Record so far", "Left", "Heading for"],
                                 [[f_, f"{v['won']}–{v['lost']}" + (f" ({v['drawn']} D)" if v["drawn"] else ""), v["left"],
                                   f"{v['exp_won']:.0f}–{v['exp_lost']:.0f}"] for f_, v in bf.items()], num=[2])
    out["caption"] = ("Heading for: your record so far plus each game left counted by its chance (so it can say 9–5 "
                      "when every game left is close). Likely wins: 8 times in 10 the season ends inside this range."
                      + (f" {pr['unknown']} tournament game{'s' if pr['unknown'] != 1 else ''} with no opponent yet "
                         + ("isn't" if pr["unknown"] == 1 else "aren't") + " counted." if pr["unknown"] else ""))
    return out


# --------------------------------------------------------------------------- Change or delete
def _change(career, team, tracked, sched, ctx) -> dict:
    items = FX.schedule_items(sched, team)
    status: dict = {}
    if len(tracked):
        for sr, g in tracked[tracked.team == team].groupby("series"):
            status[sr] = (int((g.status == "played").sum()), len(g))
    rows = []
    for it in items:
        played, total = status.get(it["series"], (0, it["n"]))
        when = (pd.Timestamp(it["date"]).strftime("%d %b %Y") if it["date"] else FX.month_label(it["month"])) or "no month"
        rows.append(dict(series=it["series"], kind=it["kind"], icon="🏆" if it["kind"] == "tournament" else "🏏",
                         played=played, total=total, when=when, venue=it["venue"],
                         venue_word=VENUE_WORD.get(it["venue"], ""), opponent=it["opponent"], format=it["format"],
                         n=int(it["n"]), month=it["month"], date=it["date"], dates=list(it.get("dates") or []),
                         games=int(it.get("games") or 0)))
    mine_fx = [r for r in sched if r["team"] == team]
    grid = [dict(id=str(r.get("id", "")), series=str(r.get("series", "")), opponent=str(r.get("opponent", "")),
                 format=str(r.get("format", "")), no=int(r.get("no") or 0), venue=str(r.get("venue", "")),
                 month=FX.month_label(r.get("month", "")), date=str(r.get("date", "")),
                 games=int(r.get("games") or 0)) for r in mine_fx]
    return dict(items=rows, none="" if items else (f"Nothing added for {team} yet. Add a series or tournament on the "
                                                   "**Add matches** tab; it shows here to change or delete."),
                table=grid, table_caption=TABLE_CAPTION, table_opponents=[""] + [t for t in ctx["known"] if t != team],
                table_formats=FX.FORMATS)


# --------------------------------------------------------------------------- Series
def _series(career, team, tracked, notes, saved_fc, goals) -> dict:
    groups = FX.series_groups(tracked, team) if len(tracked) else []
    out: dict = dict(none="" if groups else "Add a series on the Add matches tab to see its chances, preview and report here.")
    live = [s for s in groups if s["state"] == "under way"]
    coming = [s for s in groups if s["state"] == "to come"]
    done = [s for s in groups if s["state"] == "done"]
    out["live"] = []
    for s in live:
        o = FX.series_outlook(career, team, s)
        lead = ("level" if s["won"] == s["lost"] else f"{team} lead" if s["won"] > s["lost"] else f"{s['opponent']} lead")
        out["live"].append(dict(series=s["series"], opponent=s["opponent"], lead=f"{lead} {s['won']}–{s['lost']}"
                                + (f" ({s['drawn']} drawn)" if s["drawn"] else ""), left=o["left"],
                                need=o["need"].capitalize(), odds=_odds(o), scorelines=_scorelines(o),
                                extras=_extras(career, team, s, notes, goals)))
    out["tournaments"] = []
    for tu in PLN.tournaments_under_way(career, tracked, team):
        name = tu["series"].replace(FX.AUTO, "").split(" · ")[0]
        x = dict(name=name, record=f"{tu['won']}–{tu['lost']} from {tu['played']} game{'s' if tu['played'] != 1 else ''}",
                 next=(f"next: {tu['next_stage']}" + (f" v {tu['next_opponent']}" if tu["next_opponent"] else ""))
                 if tu["next_stage"] else "")
        path = PLN.tournament_path(career, team, tu["event"], tu["season"])
        if path:
            x["path"] = _path_text(team, path)
        elif tu["next_stage"]:
            x["over"] = f"Through to the {tu['next_stage'].lower()}: the league is over."
        out["tournaments"].append(x)
    out["coming"] = []
    for s in coming[:3]:
        o = FX.series_outlook(career, team, s)
        fh = FX.form_and_h2h(career, team, s["opponent"], s["format"])
        h = fh["h2h"]
        watch = []
        for side in (team, s["opponent"]):
            pw = FX.players_to_watch(career, side, s["format"])
            watch.append(dict(team=side, matches=pw["matches"], bat=[[p, int(v)] for p, v in pw["bat"].items()],
                              bowl=[[p, int(v)] for p, v in pw["bowl"].items()]))
        ids_ = FX.format_ids(career, team, s["format"])
        pb, pw_ = SN.picks_against(career, ids_, team, s["opponent"])
        good = list(dict.fromkeys(list(pb[pb.verdict.str.startswith("Pick")].player) + list(pw_[pw_.verdict.str.startswith("Pick")].player)))
        doubt = list(dict.fromkeys(list(pb[pb.verdict.str.startswith("Think")].player) + list(pw_[pw_.verdict.str.startswith("Think")].player)))
        out["coming"].append(dict(
            series=s["series"], opponent=s["opponent"], format=s["format"], odds=_odds(o), scorelines=_scorelines(o),
            form={team: fh["form"][team], s["opponent"]: fh["form"][s["opponent"]]},
            h2h=(f"head to head {h['won']}–{h['lost']}" + (f" ({h['drawn']} drawn)" if h["drawn"] else "")) if h["played"]
            else "never met in this format", watch=watch, battles=FX.key_battle(career, team, s["opponent"], s["format"]),
            pick=good, think=doubt, nobody=not good and not doubt and (not pb.empty or not pw_.empty),
            extras=_extras(career, team, s, notes, goals), preview=_preview_link(career, team, s["opponent"], s["format"], s["venue"])))
    fc_ = PLN.forecast_check(tracked, team, saved_fc) if done else []
    if fc_:
        right_, exact_ = sum(x["right"] for x in fc_), sum(x["exact"] for x in fc_)
        out["forecasts"] = (f"**🔮 Forecasts made before ball one:** the favourite was right in {right_} of {len(fc_)} "
                            "series" + (f", and the exact score came up {exact_} time{'s' if exact_ != 1 else ''}" if exact_
                                        else "") + ".")
    fc_by = {x["series"]: x for x in fc_}
    out["done"] = []
    for s in reversed(done):
        rep = FX.series_report(career, s, team)
        if not rep:
            continue
        x = dict(series=s["series"], title=f"{s['series']} · {s['won']}–{s['lost']}" + (f" ({s['drawn']} D)" if s["drawn"] else ""),
                 result=rep["result"], span=f"{rep['first']:%d %b} to {rep['last']:%d %b %Y}")
        f = fc_by.get(s["series"])
        if f:
            f_ = f["forecast"]
            x["forecast"] = (f"🔮 Forecast before ball one ({f_.get('made', '')}): {team} {f_['win']:.0f}%"
                             + (f" · level {f_['draw']:.0f}%" if f_.get("draw", 0) >= 0.5 else "")
                             + f" · {s['opponent']} {f_['lose']:.0f}%" + (f", likeliest {f_['likely']}" if f_.get("likely") else "")
                             + f". Result {f['result']}: " + ("✅ the favourite won" if f["right"] else "❌ an upset")
                             + (", exact score ✓" if f["exact"] else "") + ".")
        if rep["pos"] is not None:
            p = rep["pos"]
            x["pos"] = dict(player=p.player, team=p.team, text=f"{int(p.runs)} runs, {int(p.wickets)} wickets")
        x["top_bat"] = [[pl, tm, int(v)] for (pl, tm), v in rep["top_bat"].items()]
        x["top_bowl"] = [[pl, tm, int(v)] for (pl, tm), v in rep["top_bowl"].items()]
        bits = []
        if rep["best_bat"] is not None:
            b = rep["best_bat"]
            bits.append(f"Best innings: {b.player} {b.runs}{'' if b.out else '*'} ({b.balls})")
        if rep["best_bowl"] is not None:
            b = rep["best_bowl"]
            bits.append(f"best bowling: {b.player} {b.wickets}/{b.runs}")
        for t_, (a, b) in rep["elo"].items():
            bits.append(f"{t_} Elo {a:.0f} → {b:.0f} ({b - a:+.0f})")
        x["bits"] = " · ".join(bits)
        x["records"] = list(rep["records"][:4])
        x["milestones"] = list(rep["milestones"][:4])
        x["matches"] = [dict(id=r.match_id, date=f"{r.date:%d %b}") for r in rep["matches"].itertuples()]
        x["review"] = _review(career, team, rep["matches"].match_id)
        out["done"].append(x)
    out["predictions"] = _predictions(career, team)
    return out


def _odds(o) -> dict:
    return dict(A=round(o["odds"]["A"]), B=round(o["odds"]["B"]), level=round(o["odds"].get("level", 0.0)),
                show_level=o["odds"].get("level", 0.0) >= 0.5)


def _scorelines(o) -> str:
    return ", ".join(f"{a}–{b} ({v:.0f}%)" for (a, b), v in list(o["scorelines"].items())[:4])


def _path_text(team, p) -> dict:
    where = f"{p['group']}" if p["group"] else "the table"
    lines = [f"{p['position']}{_th(p['position'])} of {p['of']} in {where} with {p['points']:g} points, "
             f"{p['left']} league game{'s' if p['left'] != 1 else ''} left; the top {p['places']} go through."]
    ch = f"Chance of the knockouts **{p['playoffs']:.0f}%**"
    if np.isfinite(p["title"]):
        ch += f" · of winning it **{p['title']:.0f}%**"
    lines.append(ch + ".")
    if p["need"] is not None:
        lines.append(("Already as good as through: through in 9 runs of 10 or more whatever happens."
                      if p["need"] == 0 else
                      f"**What you need:** win {p['need']} of the {p['left']} game{'s' if p['left'] != 1 else ''} left to be "
                      "through 9 times in 10."))
    elif p["left"]:
        lines.append("Even winning every game left isn't sure to be enough: it depends on the other results.")
    if p["likely"]:
        lines.append("Likeliest to be there with you: " + ", ".join(f"{x['team']} ({x['chance']:.0f}%)" for x in p["likely"]) + ".")
    return dict(lines=lines, by_wins=[[x["wins"], round(x["chance"])] for x in p["by_wins"]],
                caption="From the same 4,000 runs of the rest of the league as the chances (team ratings, the "
                        "competition's own points and knockout format): how often you go through with each number of "
                        "wins from your games left.")


def _th(n: int) -> str:
    from ccstats.stats import ordinal
    return ordinal(n)[len(str(n)):]


def _extras(career, team, s, notes, goals) -> dict:
    """Past series with them, records in reach, conditions where it's played, who travels well, your note, and
    making it a goal (the current site's "More" box)."""
    opp, fmt_ = s["opponent"], s["format"]
    games = FX.plural(fmt_, 2).split(" ", 1)[1]
    host = opp if s["venue"] == "away" else team if s["venue"] == "home" else None
    out: dict = {}
    h = PLN.series_history(career, team, opp, fmt_)
    done_ = [r for r in h["rows"] if r["result"] != "under way"]
    out["past_title"] = f"📜 {team} v {opp}: past {fmt_} series"
    if done_:
        out["past"] = [f"{r['start']:%b %Y} · {VENUE_WORD.get(r['venue'], r['venue'])} · **{r['result']}** {r['score']}"
                       for r in done_[-5:]]
        line = f"Series: won {h['won']}, lost {h['lost']}" + (f", drawn {h['drawn']}" if h["drawn"] else "")
        if s["venue"] == "away" and h["away"]["series"]:
            line += f" · in {opp}: won {h['away']['won']} of {h['away']['series']}"
        out["past_line"] = line + "."
    else:
        out["past_none"] = "No series between them in this format yet: this is the first."
    out["records"] = PLN.series_records(career, team, opp, fmt_, int(s["total"]))[:5]
    if host:
        cd = PLN.conditions(career, host, fmt_)
        if cd:
            th, ev = cd["there"], cd["everywhere"]
            rows_ = [["Games", th["games"], ev["games"]],
                     ["First-innings score", fmt(th["first"], 0), fmt(ev["first"], 0)],
                     ["Batting first wins", fmt(th["bat_first_win"], 0) + "%", fmt(ev["bat_first_win"], 0) + "%"],
                     ["Runs per wicket", fmt(th["runs_per_wicket"], 1), fmt(ev["runs_per_wicket"], 1)]]
            if th["multi"]:
                rows_.append(["Drawn", fmt(th["draws"], 0) + "%", fmt(ev["draws"], 0) + "%"])
            out["conditions_title"] = f"🌍 {games} in {host} (their home games) against everywhere"
            out["conditions"] = table(["", f"In {host}", "Everywhere"], rows_, num=[1, 2])
            bf = th["bat_first_win"]
            if np.isfinite(bf):
                out["toss"] = (("Bat first if you win the toss: " if bf >= 55 else "Chase if you win the toss: " if bf <= 45
                                else "Toss matters little: ") + f"batting first wins {bf:.0f}% there.")
        else:
            out["conditions_none"] = f"Not enough {games} in {host} yet to say what conditions are like."
    if s["venue"] == "away":
        tv = PLN.travellers(career, team, fmt_, host=opp)
        if tv["away_games"] < 3:
            tv = PLN.travellers(career, team, fmt_)
        if len(tv["bat"]) or len(tv["bowl"]):
            out["travel_title"] = f"🧳 Who travels well · {team} {tv['label']} against at home"
            good = [dict(player=r.player, text=f"averages {fmt(r.avg_away, 1)} {tv['label']} ({fmt(r.avg_home, 1)} at home)")
                    for r in tv["bat"].head(2).itertuples() if np.isfinite(r.diff) and r.diff >= 5]
            good += [dict(player=r.player, text=f"takes wickets at {fmt(r.avg_away, 1)} {tv['label']} ({fmt(r.avg_home, 1)} at home)")
                     for r in tv["bowl"].head(2).itertuples() if np.isfinite(r.diff) and r.diff >= 3]
            worse = [dict(player=r.player, text=f"({fmt(r.avg_away, 1)} {tv['label']} v {fmt(r.avg_home, 1)})")
                     for r in tv["bat"].tail(2).itertuples() if np.isfinite(r.diff) and r.diff < -10]
            out["travel_good"], out["travel_worse"] = good, worse
            if not good and not worse:
                out["travel_none"] = "Nobody's record changes much away from home."
    out["note"] = notes.get(f"series::{team}::{s['series']}", "")
    out["is_goal"] = any(g.get("kind") == "series" and g.get("team") == team and g.get("series") == s["series"] for g in goals)
    return out


def _review(career, team, match_ids) -> dict | None:
    from ccstats import teamreport as TR
    rv = TR.series_review(career, list(match_ids), team)
    if not rv:
        return None
    pl = rv["players"]
    out = dict(use_more=[dict(player=r.player, why=r.why) for r in pl[pl.verdict == "use more"].itertuples()],
               drop=[dict(player=r.player, why=r.why) for r in pl[pl.verdict == "think about dropping"].itertuples()],
               keep=list(pl[pl.verdict == "keep"].player))
    rows_ = [["This series", f"{rv['now']['won']}–{rv['now']['lost']}", fmt(rv["now"]["rpw_for"], 1),
              fmt(rv["now"]["rpw_against"], 1)]]
    rows_ += [[e["label"], f"{e['won']}–{e['lost']}", fmt(e["rpw_for"], 1), fmt(e["rpw_against"], 1)] for e in reversed(rv["earlier"])]
    if len(rows_) > 1:
        out["table"] = table([f"{rv['format']} series", "Won–lost", "Runs per wicket made", "Runs per wicket given"],
                             rows_, num=[2, 3])
    out["caption"] = ("Use more: among your best by impact a match in this series and above their own usual level (all "
                      f"their earlier {rv['format']}s). Think about dropping: played twice or more, among your lowest and "
                      "below their usual level: a batter averaging under 20 here, or a bowler giving away a quarter more "
                      "per wicket than usual (or no wickets). A guide from the scorecards: you know their form in the nets.")
    return out


def _predictions(career, team) -> dict | None:
    """How good the predictions are (your pick, 26 November): every match's chance as it stood before the match."""
    pr = kept(career, ("fx-predictions", team), lambda: WP.prediction_record(career, team))
    if not pr["rows"]:
        return None
    t = pr["total"]
    rows = [[r["format"], r["games"], r["right"], f"{r['pct']:.0f}%", r["upsets"],
             (f"{r['sure']:.0f}% of {r['sure_n']}" if r["sure_n"] else "–")] for r in pr["rows"]]
    best = max(pr["rows"], key=lambda r: (r["pct"], r["games"]))
    return dict(table=table(["Format", "Games", "Favourite won", "Right", "Upsets", "When 65%+ sure"], rows, num=[1, 2, 3, 4]),
                summary=f"Over {t['games']} {team} games with a winner, the side the chance favoured won {t['right']} "
                        f"({t['pct']:.0f}%).",
                bars=[dict(label=r["format"], value=round(r["pct"], 1), n=r["games"]) for r in pr["rows"]],
                **SG.lines(f"How often the side the site's chance favoured won {team}'s games, in each format.",
                           f"{best['format']}, right {best['pct']:.0f}% of {best['games']} games",
                           "How far to trust the chances on this page: each game's chance is worked out exactly as "
                           "the site works it out, from only the matches played before it (the ratings, form and head "
                           "to head as they stood then). Games with no winner (draws, ties, no result) are left out. "
                           "\"When 65%+ sure\": the games where the favourite had 65% or more of the win-or-lose chance.",
                           best_label="Most often right"))


# --------------------------------------------------------------------------- Calendar, WTC race, Milestones
def _calendar(career, team, q, sched) -> dict:
    from .seasonpage import _calendar as season_calendar
    return season_calendar(career, team, {"season": q.get("season", "")}, sched)


def _wtc(career, team, tracked) -> dict:
    race = FX.wtc_race(career, tracked, team) if len(tracked) else (
        FX.wtc_race(career, FX.track(career, []), team) if team in SN.WTC_TEAMS else None)
    if race is None:
        return dict(none=f"{team} aren't one of the nine World Test Championship sides, or no WTC Tests have been played yet.")
    t = race["table"]
    out = dict(title=f"World Test Championship {race['cycle']}–{str(race['cycle'] + 2)[-2:]}",
               left=f"{team} have {race['remaining']} Test{'s' if race['remaining'] != 1 else ''} left in your schedule",
               table=table(["#", "Team", "P", "W", "L", "D", "Pts", "PCT %"],
                           [[int(i), r.team, int(r.played), int(r.won), int(r.lost), int(r.drawn), int(r.points), fmt(r.pct, 1)]
                            for i, r in zip(t.index, t.itertuples())], num=[0, 2, 3, 4, 5, 6, 7],
                           hi=[i for i, x in enumerate(t.team) if x == team]))
    if race["remaining"]:
        k = race["need"]
        line = (f"To finish above **{race['bar_team']}** ({race['bar']:.1f}%, the side in the top two after you) "
                + (f"{team} need **{k} win{'s' if k != 1 else ''} from {race['remaining']}** Tests" if k is not None
                   else f"{team} can't get there with the Tests left") + ". ")
        line += f"Best possible: {race['best']:.1f}%."
        if np.isfinite(race["chance"]):
            line += f" Chance of finishing in the top two: **{race['chance']:.0f}%** (projected PCT {race['expected']:.1f}%)."
        out["line"] = line
        todo = race["todo"]
        out["caption"] = ("Your Tests still to come: " + ", ".join(f"v {o} ({VENUE_WORD.get(v, '') or '?'})"
                                                                 for o, v in zip(todo.opponent, todo.venue))
                          + ". The other sides' remaining Tests aren't in your schedule, so their percentages are taken "
                          "as they stand now. Each of your Tests is worked out from the ratings, as on Opponent preview.")
    else:
        out["caption"] = "Add your Tests for this cycle on the Add matches tab to see what you need to reach the final."
    return out


def _milestones(career, team, tracked, mine_rows) -> dict:
    mc = FX.milestone_countdown(career, tracked, team) if mine_rows is not None and len(mine_rows) else pd.DataFrame()
    if mc.empty:
        return dict(none="Add fixtures to see which milestones your players could reach in them.")
    within = mc[mc.within]
    return dict(title=f"Milestones in reach in your schedule · {len(within)} of your players' next round numbers could "
                      "fall in the matches you have left",
                table=table(["Player", "Format", "Next milestone", "Still needs", "Per match", "Around"],
                            [[r.player, r.format, f"{r.next:,} {r.what}", f"{r.needed:,}", fmt(r.per_match, 1),
                              r.when if r.within else f"needs about {r.games_needed} games; {r.games_left} left"]
                             for r in mc.head(25).itertuples()], num=[3, 4]),
                caption="Per match: their average per match in that format so far (everyone who played in your last 5 "
                        "matches in it). 'Around' is the fixture they'd reach it in if they keep that rate: a guide, not "
                        "a promise.")


# --------------------------------------------------------------------------- Goals
def _goals(career, team, tracked, goals, ctx) -> dict:
    mine_g = [g for g in goals if g.get("team") == team or g.get("kind") == "player"]
    rows = []
    for g in mine_g:
        pg = FX.goal_progress(career, tracked, g)
        rows.append(dict(id=g.get("id", ""), label=FX.goal_label(g), text=pg["text"], status=pg["status"],
                         badge=BADGE.get(pg["status"], "•"), done=round(float(min(max(pg["done"], 0.0), 1.0)), 3)))
    sugg = PLN.suggested_goals(career, tracked, team, goals) + GL.suggested(career, team, goals, tracked)
    seen, uniq = set(), []
    for g in sugg:
        k = GL._key(g)
        if k not in seen:
            seen.add(k)
            uniq.append(g)
    ch = GL.choices(career, team)
    series_opts = [s["series"] for s in FX.series_groups(tracked, team)] if len(tracked) else []
    kinds = [dict(v=k, label=v, group="Team") for k, v in FX.GOAL_KINDS.items() if k != "player"] + \
            [dict(v=k, label=v, group="Team") for k, v in GL.TEAM_KINDS.items()] + \
            [dict(v="player", label=FX.GOAL_KINDS["player"], group="Player")] + \
            [dict(v=k, label=v, group="Player") for k, v in GL.PLAYER_KINDS.items()]
    return dict(goals=rows, none="" if rows else "No goals yet. Add one below and watch its progress bar move with every match.",
                suggested=[dict(goal=g, label=FX.goal_label(g)) for g in uniq[:10]],
                kinds=kinds, series=series_opts, wtc=team in SN.WTC_TEAMS, choices=ch,
                formats=ctx["formats"], years=[str(y) for y in ctx["years"]])


# --------------------------------------------------------------------------- changes (the server saves them)
class Refused(ValueError):
    """A change that can't be made, with the reason in plain words (shown on the page)."""


def _months(text: str) -> str:
    """'Jan 2027' or '2027-01' -> '2027-01'; '' stays ''."""
    t = str(text or "").strip()
    if not t:
        return ""
    mm = FX.RE_MON_YEAR.search(t.lower()) or FX.RE_YEAR_MON.search(t)
    if not mm:
        raise Refused(f"can't read the month '{t}' (write it like Jan 2027)")
    return (f"{int(mm.group(2)):04d}-{FX._mon_num(mm.group(1)):02d}" if mm.re is FX.RE_MON_YEAR
            else f"{int(mm.group(1)):04d}-{int(mm.group(2)):02d}")


def _series_rows(team: str, b: dict) -> list[dict]:
    opp, fmt_ = str(b.get("opponent", "")), str(b.get("format", ""))
    n = int(b.get("n") or 1)
    if not opp or fmt_ not in FX.FORMATS or not 1 <= n <= 10:
        raise Refused("Pick the opponent, the format and how many matches (1 to 10).")
    venue = str(b.get("venue", "home")).lower()
    if venue not in ("home", "away", "neutral"):
        venue = "home"
    dates = [str(d or "") for d in (b.get("dates") or [])][:n]
    for d in dates:
        if d:
            try:
                pd.Timestamp(d)
            except ValueError:
                raise Refused(f"Can't read the date '{d}'.") from None
    wrong = FX.dates_in_order(dates)
    if wrong:
        raise Refused(wrong + " Put the dates in match order.")
    month = str(b.get("month", ""))
    first = next((d for d in dates if d), "")
    if first:
        month = first[:7]
    if not month:
        raise Refused("Pick the month.")
    rows = FX.make_series(team, opp, fmt_, n, venue, month, dates=dates)
    comp = str(b.get("competition", ""))
    if comp:
        for r in rows:
            r["competition"] = comp
    return rows


def _tournament_rows(team: str, b: dict) -> list[dict]:
    name = FX.canonical_tournament(str(b.get("name", "")).strip())
    fmt_ = str(b.get("format", ""))
    if not name or fmt_ not in FX.FORMATS:
        raise Refused("Pick the tournament and its format.")
    month = str(b.get("month", ""))
    if not month:
        raise Refused("Pick the month it starts.")
    return FX.make_tournament(team, name, fmt_, month, int(b.get("games") or 0))


def apply(career, settings, team: str, action: str, b: dict) -> tuple[dict, str]:
    """Make one change to the schedule, goals or a note (in `settings`, which the server then saves). Returns
    (what to send back, a short message). Every change to the schedule goes on the list of recent changes, each with
    its own undo (your answer 5)."""
    sched = list(settings.fixtures)
    before = [dict(r) for r in sched if r.get("team") == team]
    msg = ""
    hist = list(getattr(settings, "fixture_changes", None) or [])

    def record(what: str, remove, restore: list[dict]):
        hist.append(dict(id=FX.new_id(), team=team, what=what, remove=remove, restore=restore,
                         when=f"{dt.datetime.now():%d %b %H:%M}", at=time.time()))
        del hist[:-HISTORY_KEPT * 4]   # kept for every team together; each team sees its own last 20

    if action == "add_series":
        rows = _series_rows(team, b)
        new, added = FX.merge(sched, rows)
        if not added:
            raise Refused("That series is already in the schedule.")
        settings.fixtures = new
        record(f"Added {rows[0]['series']}", [rows[0]["series"]], [])
        msg = f"Added {rows[0]['series']}"
    elif action == "add_tournament":
        rows = _tournament_rows(team, b)
        new, added = FX.merge(sched, rows)
        if not added:
            raise Refused("That tournament is already in the schedule.")
        settings.fixtures = new
        record(f"Added {rows[0]['series']}", [rows[0]["series"]], [])
        msg = f"Added {rows[0]['series']}"
    elif action == "read_lines":
        txt = str(b.get("text", ""))
        if not txt.strip():
            raise Refused("Type at least one line first, like the examples above.")
        ctx = _context(career, team)
        rows, errs = FX.parse_lines(txt, team, ctx["known"])
        return dict(will=list(dict.fromkeys(r["series"] for r in rows)), skipped=errs, rows=rows), ""
    elif action == "add_lines":
        ctx = _context(career, team)
        rows, errs = FX.parse_lines(str(b.get("text", "")), team, ctx["known"])
        if not rows:
            raise Refused("Nothing to add: " + "; ".join(errs) if errs else "Nothing to add.")
        new, added = FX.merge(sched, rows)
        settings.fixtures = new
        names = list(dict.fromkeys(r["series"] for r in rows))
        record(f"Added {len(names)} from your typed lines", names, [])
        msg = f"Added {added} matches"
    elif action == "change":
        old = str(b.get("series", ""))
        items = {it["series"]: it for it in FX.schedule_items(sched, team)}
        if old not in items:
            raise Refused("That series isn't in the schedule any more.")
        rows = _tournament_rows(team, b) if items[old]["kind"] == "tournament" else _series_rows(team, b)
        others = [r for r in sched if not (r["team"] == team and r["series"] == old)]
        if any(r["team"] == team and r["series"] == rows[0]["series"] for r in others):
            raise Refused("You already have a series exactly like that in the schedule: change something, or delete one.")
        settings.fixtures = FX.replace_item(sched, team, old, rows)
        record(f"Changed: {old} is now {rows[0]['series']}", [rows[0]["series"]],
               [r for r in before if r["series"] == old])
        msg = f"Changed to {rows[0]['series']}"
    elif action == "delete":
        old = str(b.get("series", ""))
        new, gone = FX.delete_item(sched, team, old)
        if not gone:
            raise Refused("That series isn't in the schedule any more.")
        settings.fixtures = new
        record(f"Deleted: {old}", [], gone)
        msg = f"Deleted {old}"
    elif action == "delete_all":
        new, gone = FX.delete_item(sched, team)
        if not gone:
            raise Refused(f"Nothing added for {team} yet.")
        settings.fixtures = new
        n = len(FX.schedule_items(before, team))
        record(f"Deleted: {team}'s whole schedule ({n} items)", [], gone)
        msg = f"Deleted {team}'s schedule"
    elif action == "fix":
        tracked = _tracked(career, sched, team)
        issue = next((x for x in PLN.check(career, sched, tracked, team)
                      if x["series"] == b.get("series") and x["kind"] == b.get("kind") and x["fix"]), None)
        if issue is None:
            raise Refused("That's already been put right.")
        settings.fixtures = PLN.apply_fix(sched, team, issue["series"], issue["fix"])
        after = [r for r in settings.fixtures if r.get("team") == team]
        record(f"Fixed: {issue['series']}", "*", before)
        del after
        msg = f"Fixed: {issue['series']}"
    elif action == "save_table":
        new_rows, bad = [], []
        for i, r in enumerate(b.get("rows") or []):
            if not str(r.get("series") or "").strip() and not str(r.get("opponent") or "").strip():
                continue
            try:
                month = _months(r.get("month", ""))
            except Refused as e:
                bad.append(f"row {i + 1}: {e}")
                continue
            date = str(r.get("date") or "")
            if date:
                try:
                    date = pd.Timestamp(date).strftime("%Y-%m-%d")
                except ValueError:
                    bad.append(f"row {i + 1}: can't read the date '{date}'")
                    continue
            f_ = str(r.get("format") or "")
            if f_ not in FX.FORMATS:
                f_ = _context(career, team)["formats"][0]
            rid = str(r.get("id") or "") or FX.new_id()
            venue = str(r.get("venue") or "")
            new_rows.append(dict(id=rid, team=team, series=str(r.get("series") or "").strip() or
                                 FX.series_label(str(r.get("opponent") or ""), f_, 1, venue, month, date),
                                 opponent=str(r.get("opponent") or ""), format=f_, no=int(r.get("no") or 0),
                                 venue=venue if venue in ("home", "away", "neutral") else "", date=date,
                                 month=month or (date[:7] if date else ""), games=int(r.get("games") or 0)))
        if bad:
            raise Refused("Not saved: " + "; ".join(bad))
        settings.fixtures = [r for r in sched if r["team"] != team] + new_rows
        record("Saved the match-by-match table", "*", before)
        msg = "Schedule saved"
    elif action == "undo":
        hid = str(b.get("id", ""))
        h = next((x for x in hist if x["id"] == hid and x["team"] == team), None)
        if h is None:
            raise Refused("That change can't be undone any more.")
        keep = [r for r in sched if not (r.get("team") == team and (h["remove"] == "*" or r.get("series") in set(h["remove"])))]
        settings.fixtures = keep + [dict(r) for r in h["restore"]]
        hist = [x for x in hist if x["id"] != hid]
        msg = f"Undone: {h['what']}"
    elif action == "note":
        text = str(b.get("text", "")).strip()[:300]
        key = f"series::{team}::{b.get('series', '')}"
        notes = dict(settings.notes)
        if text:
            notes[key] = text
        else:
            notes.pop(key, None)
        settings.notes = notes
        msg = "Note saved"
    elif action == "goal_add":
        g = _goal_from(career, team, b.get("goal") or {})
        have = {GL._key(x) for x in settings.goals}
        if GL._key(g) in have:
            raise Refused("You already have that goal.")
        settings.goals = list(settings.goals) + [g]
        msg = "Goal added"
    elif action == "goals_add":
        added = 0
        goals = list(settings.goals)
        for x in (b.get("goals") or [])[:10]:
            g = _goal_from(career, team, x)
            if GL._key(g) not in {GL._key(y) for y in goals}:
                goals.append(g)
                added += 1
        settings.goals = goals
        msg = f"{added} goal{'s' if added != 1 else ''} added"
    elif action == "goal_remove":
        gid = str(b.get("id", ""))
        settings.goals = [x for x in settings.goals if x.get("id") != gid]
        msg = "Goal removed"
    else:
        raise Refused(f"Unknown change {action!r}.")
    settings.fixture_changes = hist
    return {}, msg


def _goal_from(career, team: str, g: dict) -> dict:
    """A goal as the form sent it, checked: its kind and every field it needs, nothing else kept."""
    k = str(g.get("kind", ""))
    last = career.matches.date.max()
    since = f"{last:%Y-%m-%d}" if pd.notna(last) else ""
    out: dict = dict(id=FX.new_id(), kind=k, team=team)

    def need(*fields):
        for f_ in fields:
            v = g.get(f_)
            if v is None or str(v) == "":
                raise Refused("Fill in every box for this goal.")
            out[f_] = v
    if k == "series":
        need("series")
    elif k == "wtc":
        if team not in SN.WTC_TEAMS:
            raise Refused(f"{team} aren't a World Test Championship side.")
    elif k == "player":
        need("player", "format", "what", "target")
        out["target"] = int(out["target"])
        out["year"] = str(g.get("year") or "")
    elif k == "wins":
        need("format", "target", "year")
        out["target"] = int(out["target"])
    elif k == "title":
        need("section", "season")
    elif k == "top":
        need("section", "season")
        out["n"] = int(g.get("n") or 0)
    elif k == "home" or k == "away":
        need("format", "season")
    elif k == "no1":
        need("section")
        out["since"] = since
    elif k == "rival":
        need("opponent", "format", "season")
    elif k == "streak":
        need("format", "season", "target")
        out["target"] = int(out["target"])
    elif k == "topscorer":
        need("player", "section", "season", "what")
    elif k == "average":
        need("player", "format", "season", "what", "target")
        out["target"] = float(out["target"])
    elif k == "hauls":
        need("player", "format", "season", "what", "target")
        out["target"] = int(out["target"])
    else:
        raise Refused("Pick what kind of goal it is.")
    for f_ in ("target", "n"):
        if f_ in out and (not np.isfinite(float(out[f_])) or float(out[f_]) < 0 or float(out[f_]) > 100000):
            raise Refused("That number is out of range.")
    return out
