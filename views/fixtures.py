import calendar
import datetime as dt

import numpy as np
import pandas as pd
import streamlit as st

from ccstats import catalogue as CAT
from ccstats import fixtures as FX
from ccstats import planning as PLN
from ccstats import seasonal as SN
from ui import calendar_view as CV
from ui import logos, state
from ui.charts import fmt
from ui.theme import (chart_note, colours, esc, form_strip, html_table, kpis, match_link, page_header, player_link,
                      safe_section)
from ccstats.stats import ordinal, poss

career = state.current()
if career is None:
    st.info("Load a career on the Home page first.")
    st.stop()

m = career.matches
page_header("Fixtures", "Your schedule",
            "Add your schedule once. Every match ticks itself off when the game saves its scorecard, and the series "
            "chances, WTC race, milestones and goals update with it.")

all_teams = sorted(set(m.home) | set(m.away))
mine = state.my_teams(career, unplayed=True)  # a country picked before its first match too
team_opts = mine + [t for t in all_teams if t not in mine]
if not team_opts:
    st.info("No matches yet.")
    st.stop()
c1, c2 = st.columns([1.4, 3])
team = c1.selectbox("Schedule for", team_opts, key="fx_team",
                    help="Your teams first (pick them under My team in the sidebar).")
schedule = state.fixtures(career)
# what you scheduled, plus everything the team has played since your schedule starts that isn't in it
tracked = state.memo(FX.track, career, schedule, auto=(team,))
state.add_forecasts(career, PLN.take_forecasts(career, tracked, team, state.forecasts(career)))  # 10 · before ball one
mine_rows = tracked[tracked.team == team] if len(tracked) else tracked
scheduled_any = any(r.get("team") == team for r in schedule)
national = team in FX.NATIONS
formats_here = ["Test", "ODI", "T20I"] if national else ["T20", "The Hundred", "List A", "First-class"]
# the sides this team plays, before they've played (a new save): every nation for a nation; a franchise's league or a
# county's (state's) fellow sides, then any nation for a tour game. A side that has played under another name (a
# scorecard from before a rename) is listed by that name only
rivals_ = {t for t in CAT.rivals(team) if t in all_teams or not (CAT.aliases(t) & set(all_teams))}
extra_opps = [t for t in (sorted(FX.NATIONS) if national else sorted(rivals_) + sorted(FX.NATIONS))
              if t not in team_opts and t != team]
# the opponent boxes: a franchise's or a county's own competition first (played or not), then everyone else
opp_list = [t for t in team_opts + extra_opps if t != team]
if not national:
    opp_list = sorted(rivals_) + [t for t in opp_list if t not in rivals_]
latest = m.date.max()
year_now = int(latest.year) if pd.notna(latest) else dt.date.today().year

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
    "added has ✏️ Change and 🗑️ Delete (and a deleted one can be put back).\n\n"
    "**Forgot something?** No problem: any match your team plays that isn't in your schedule is added by itself "
    "(marked *auto-added*), with the rest of its series. In a tournament, the semi-final and final are added once "
    "you're through to them.")

tabs = st.tabs(["Schedule", "Add matches", "Change or delete", "Series", "Calendar", "WTC race", "Milestones", "Goals"])
t_sched, t_add, t_edit, t_series, t_cal, t_wtc, t_miles, t_goals = tabs


def when_text(r) -> str:
    """The scorecard's date; the date you gave; 'about 12 Jun 2026' worked out from the match before or after it
    in the series; else the month."""
    if r["status"] == "played":
        return f"{pd.Timestamp(r['played_date']):%d %b %Y}"
    if r["date"]:
        return f"{pd.Timestamp(r['date']):%d %b %Y}"
    if str(r.get("estimated")) == "True" and pd.notna(r.get("anchor")):
        return f"about {pd.Timestamp(r['anchor']):%d %b %Y}"
    return FX.month_label(r["month"]) or "date to come"


def first_date(prefix: str, n: int, given: list[str] = ()):
    """The first date in a series' date boxes (as typed so far, or as saved before the boxes were opened)."""
    for j in range(n):
        key = f"{prefix}_{j + 1}"
        d = st.session_state.get(key) if key in st.session_state else (
            pd.Timestamp(given[j]).date() if j < len(given) and given[j] else None)
        if d:
            return d
    return None


def date_boxes(prefix: str, n: int, given: list[str], fmt_: str) -> list[str]:
    """A date box for each match of a series (left empty: not known yet). 'YYYY-MM-DD', or '' for each."""
    out, per_row = [], 5
    for start in range(0, n, per_row):
        cols = st.columns(per_row)
        for j in range(start, min(n, start + per_row)):
            key = f"{prefix}_{j + 1}"
            if key not in st.session_state and j < len(given) and given[j]:
                st.session_state[key] = pd.Timestamp(given[j]).date()
            d = cols[j - start].date_input(f"{ordinal(j + 1)} {fmt_}", value=None, key=key, format="DD/MM/YYYY")
            out.append(d.strftime("%Y-%m-%d") if d else "")
    return out


def venue_word(v: str) -> str:
    return {"home": "at home", "away": "away", "neutral": "neutral venue"}.get(v, "")


def stage_of(r) -> str:
    s = r.get("stage")
    return s if isinstance(s, str) else ""


def next_title(r) -> str:
    """'v England · Test · match 2', or 'T20 World Cup 2027 Final v India' for a knockout game."""
    name = r["series"].replace(FX.AUTO, "").split(" · ")[0]
    if stage_of(r):
        return f"{name} {stage_of(r)} · " + (f"v {r['opponent']}" if r["opponent"] else "opponent to be decided")
    return (f"v {r['opponent']} · {r['format']}" if r["opponent"] else name) + (f" · match {int(r['no'])}" if r["no"] else "")


def go_preview(opp: str, fmt_: str, venue: str) -> None:
    intl = fmt_ in FX.INTL
    secs = SN.international_sections(career)
    if intl and secs:
        st.session_state["op_section"] = "Internationals"
        if fmt_ in secs:
            st.session_state["op_format"] = secs[fmt_]
    else:  # the team's own section in that format (or, before its first game in it, any section in it)
        mine_f = m[(m.format == fmt_) & ((m.home == team) | (m.away == team))]
        any_f = mine_f if len(mine_f) else m[m.format == fmt_]
        if len(any_f):
            st.session_state["op_section"] = any_f.sort_values("date").section.iloc[-1]
    st.session_state["op_mine"] = team
    st.session_state["op_opp"] = opp
    st.session_state["op_pred_where"] = st.session_state["op_where"] = \
        {"home": "Home", "away": "Away"}.get(venue, "Neutral")
    st.switch_page("views/opponent.py")


def preview_any() -> None:
    """Preview any opponent: the ones still to come in your schedule first, then every other side."""
    todo_ = mine_rows[mine_rows.status.isin(["next", "to come"]) & (mine_rows.opponent.fillna("") != "")] \
        if len(mine_rows) else mine_rows
    sched_o = list(dict.fromkeys(todo_.opponent)) if len(todo_) else []
    pool = set(all_teams) | (FX.NATIONS if national else rivals_)
    if national:
        pool &= FX.NATIONS
    rest = sorted(pool - set(sched_o) - {team})
    opts = [t for t in sched_o if t != team] + rest
    if not opts:
        return
    with st.container(border=True):
        st.markdown("**🔎 Preview any opponent** · your history against them, their form, key players and a plan")
        p1, p2, p3 = st.columns([2.2, 1.2, 1], vertical_alignment="bottom")
        o = p1.selectbox("Team to preview", opts, key="fx_any_opp",
                         format_func=lambda t: t + ("  ·  in your schedule" if t in sched_o else ""))
        their = todo_[todo_.opponent == o] if len(todo_) else todo_
        f_default = their.format.iloc[0] if len(their) else None
        if f_default is None:
            last_ = m[((m.home == team) | (m.away == team)) & m.format.isin(formats_here)].sort_values("date")
            f_default = last_.format.iloc[-1] if len(last_) else formats_here[0]
        if st.session_state.get("fx_any_fmt_for") != (team, o):  # a new team: its scheduled (or your latest) format
            st.session_state["fx_any_fmt_for"] = (team, o)
            st.session_state["fx_any_fmt"] = f_default if f_default in formats_here else formats_here[0]
        f = p2.selectbox("Format", formats_here, key="fx_any_fmt")
        if p3.button("Preview →", key="fx_any_go", width="stretch"):
            go_preview(o, f, their.venue.iloc[0] if len(their) and their.format.iloc[0] == f else "")


LEVEL_ICON = {"easy": "🟢", "even": "⚪", "hard": "🔴"}


def schedule_check() -> None:
    """1 · Anything that looks wrong in what you added for this team, each with a one-click fix where there is one."""
    issues = PLN.check(career, schedule, tracked, team)
    if not issues:
        if scheduled_any:
            st.caption("🔍 Schedule check: nothing looks wrong.")
        return
    with st.container(border=True):
        st.markdown(f"**🔍 Schedule check** · {len(issues)} thing{'s' if len(issues) != 1 else ''} to look at")
        for j, x in enumerate(issues):
            a_, b_ = st.columns([5, 1.1], vertical_alignment="center")
            a_.markdown(f"⚠️ {esc(x['text'])}")
            if x["fix"]:
                label = "🗑️ Delete it" if x["fix"].get("delete") else "✅ Fix it"
                if b_.button(label, key=f"fx_fix_{j}_{_key(x['series'] + x['kind'])}", width="stretch"):
                    _save(PLN.apply_fix(schedule, team, x["series"], x["fix"]), f"Fixed: {x['series']}",
                          (team, f"Fixed: {x['series']}", schedule))
            else:
                b_.caption("Change it on the **Change or delete** tab")


def rivalry_text(opp: str, fmt_: str) -> str:
    """14 · '👻 Bogey team: 1–4 against them in ODIs' / '😊 Favourite opponent …', or ''."""
    rv = PLN.rivalry(career, team, opp, fmt_)
    if not rv:
        return ""
    games = FX.plural(fmt_, 2).split(" ", 1)[1]
    return (f"👻 **Bogey team:** {esc(team)} are {rv['text']} against them in {games}" if rv["kind"] == "bogey" else
            f"😊 **Favourite opponent:** {esc(team)} are {rv['text']} against them in {games}")


def season_outlook() -> None:
    """3 · 4 · How hard what's left of the season looks, fixture by fixture, and the record you're heading for."""
    from ui.charts import CONFIG, _axis, _layout
    import plotly.graph_objects as go
    ch_all = PLN.chances(career, tracked, team)
    if ch_all.empty:
        return
    sy = CV.season_of(ch_all.anchor.min())
    start, end = pd.Timestamp(year=sy, month=4, day=1), pd.Timestamp(year=sy + 1, month=4, day=1)
    pr = PLN.projection(career, tracked, team, start, end)
    ch = pr["chances"]
    if ch.empty:
        return
    now = pr["now"]
    with st.container(border=True):
        st.markdown(f"**📈 The season ahead · {CV.season_label(sy)}** · {len(ch)} match{'es' if len(ch) != 1 else ''} "
                    "left with a known opponent")
        drawn = lambda d: f" ({d:.0f} D)" if round(d) else ""  # noqa: E731
        kpis([("Record so far", f"{now['W']}–{now['L']}" + drawn(now["D"])),
              ("Heading for", f"{pr['exp_won']:.0f}–{pr['exp_lost']:.0f}" + drawn(pr["exp_drawn"])),
              ("Likely wins", f"{pr['low']} to {pr['high']}"),
              ("Easy · even · hard", " · ".join(str(int((ch.level == k).sum())) for k in ("easy", "even", "hard")))])
        tough = PLN.toughest_run(ch)
        if tough and tough["hard"]:
            what = ", ".join(f"v {r.opponent} ({r.format} {int(r.no)})" for r in tough["rows"].itertuples())
            rr = tough["rows"]
            st.markdown(f"**Toughest run:** {esc(what)} ({esc(rr.when.iloc[0])} to {esc(rr.when.iloc[-1])}): your chance "
                        f"of winning averages {rr.win.mean():.0f}%.")
        c_ = colours()
        col = {"easy": c_["good"], "even": c_["muted"], "hard": c_["neg"]}
        labels = [f"{r.when} · v {r.opponent} · {r.format} {int(r.no)}" for r in ch.itertuples()]
        share = ch.win.reset_index(drop=True)
        fig = go.Figure(go.Bar(x=share[::-1], y=labels[::-1], orientation="h",
                               marker=dict(color=[col[x] for x in ch.level][::-1], line=dict(width=0)),
                               text=[f"{v:.0f}%" for v in share][::-1], textposition="outside", cliponaxis=False,
                               textfont=dict(size=11, color=c_["ink2"]),
                               customdata=[f"win {w:.0f}%" + (f" · draw {d:.0f}%" if d >= 0.5 else "") + f" · lose {lo:.0f}%"
                                           for w, d, lo in zip(ch.win, ch.draw, ch.lose)][::-1],
                               hovertemplate="<b>%{y}</b><br>%{customdata}<extra></extra>"))
        fig.update_layout(**_layout(c_, height=max(220, 26 * len(ch) + 80), bargap=0.3,
                                    xaxis=_axis(c_, "Chance of winning (%)", range=[0, 108]),
                                    yaxis=dict(showgrid=False, tickfont=dict(size=11, color=c_["ink"]), automargin=True),
                                    margin=dict(l=10, r=30, t=10, b=10)))
        st.plotly_chart(fig, width="stretch", config=CONFIG, key="fx_outlook")
        hardest = ch.iloc[int(np.argmin(share.to_numpy()))]
        chart_note(f"{int((ch.level == 'easy').sum())} easy, {int((ch.level == 'even').sum())} even and "
                   f"{int((ch.level == 'hard').sum())} hard; the hardest is v {esc(hardest.opponent)} "
                   f"({esc(hardest.when)}, {hardest.win:.0f}% to win).",
                   "Shows which games to rest players for and which to go all out in. Green: easy (you win 60% or more "
                   "of the games that end in a result), grey: even, red: hard (40% or less); in a Test the draws are "
                   "left out of that, so a 35% win chance with many draws can still be even. Each game's chance is the "
                   "same one Opponent preview gives (Elo ratings, form, head to head and venue).")
        bf = pr["by_format"]
        if bf:
            html_table([[f_, f"{v['won']}–{v['lost']}" + (f" ({v['drawn']} D)" if v["drawn"] else ""), v["left"],
                         f"{v['exp_won']:.0f}–{v['exp_lost']:.0f}"] for f_, v in bf.items()],
                       ["Format", "Record so far", "Left", "Heading for"], numeric={2})
        st.caption("Heading for: your record so far plus each game left counted by its chance (so it can say 9–5 "
                   "when every game left is close). Likely wins: 8 times in 10 the season ends inside this range."
                   + (f" {pr['unknown']} tournament game{'s' if pr['unknown'] != 1 else ''} with no opponent yet "
                      + ("isn't" if pr["unknown"] == 1 else "aren't") + " counted." if pr["unknown"] else ""))


def series_extras(s: dict, i: str) -> None:
    """7 · 8 · 12 · 16 · 23 · 24 for one series: conditions where it's played, who travels well, your past series
    with them, records in reach, your note, and making it a goal."""
    opp, fmt_ = s["opponent"], s["format"]
    games = FX.plural(fmt_, 2).split(" ", 1)[1]
    host = opp if s["venue"] == "away" else team if s["venue"] == "home" else None
    left, right = st.columns(2, gap="medium")
    with left:
        # 12 · past series with them
        h = PLN.series_history(career, team, opp, fmt_)
        done_ = [r for r in h["rows"] if r["result"] != "under way"]
        st.markdown(f"**📜 {esc(team)} v {esc(opp)}: past {esc(fmt_)} series**")
        if done_:
            st.markdown("  \n".join(f"{r['start']:%b %Y} · {venue_word(r['venue']) or r['venue']} · "
                                    f"**{r['result']}** {r['score']}" for r in done_[-5:]))
            line = f"Series: won {h['won']}, lost {h['lost']}" + (f", drawn {h['drawn']}" if h["drawn"] else "")
            if s["venue"] == "away" and h["away"]["series"]:
                line += f" · in {esc(opp)}: won {h['away']['won']} of {h['away']['series']}"
            st.caption(line + ".")
        else:
            st.caption("No series between them in this format yet: this is the first.")
        # 16 · records in reach
        recs = PLN.series_records(career, team, opp, fmt_, int(s["total"]))
        if recs:
            st.markdown("**🏆 Records in reach**  \n" + "  \n".join(esc(x) for x in recs[:5]))
    with right:
        # 7 · conditions where it's played
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
                st.markdown(f"**🌍 {games} in {esc(host)}** (their home games) against everywhere")
                html_table(rows_, ["", f"In {host}", "Everywhere"], numeric={1, 2})
                bf_there = th["bat_first_win"]
                if np.isfinite(bf_there):
                    st.caption(("Bat first if you win the toss: " if bf_there >= 55 else
                                "Chase if you win the toss: " if bf_there <= 45 else "Toss matters little: ")
                               + f"batting first wins {bf_there:.0f}% there.")
            else:
                st.caption(f"Not enough {games} in {host} yet to say what conditions are like.")
        # 8 · who travels well
        if s["venue"] == "away":
            tv = PLN.travellers(career, team, fmt_, host=opp)
            if tv["away_games"] < 3:
                tv = PLN.travellers(career, team, fmt_)
            if len(tv["bat"]) or len(tv["bowl"]):
                st.markdown(f"**🧳 Who travels well** · {esc(team)} {esc(tv['label'])} against at home")
                bits = [f"{player_link(r.player)} averages {fmt(r.avg_away, 1)} {esc(tv['label'])} ({fmt(r.avg_home, 1)} "
                        f"at home)" for r in tv["bat"].head(2).itertuples() if np.isfinite(r.diff) and r.diff >= 5]
                bits += [f"{player_link(r.player)} takes wickets at {fmt(r.avg_away, 1)} {esc(tv['label'])} "
                         f"({fmt(r.avg_home, 1)} at home)" for r in tv["bowl"].head(2).itertuples()
                         if np.isfinite(r.diff) and r.diff >= 3]
                worse = [f"{player_link(r.player)} ({fmt(r.avg_away, 1)} {esc(tv['label'])} v {fmt(r.avg_home, 1)})"
                         for r in tv["bat"].tail(2).itertuples() if np.isfinite(r.diff) and r.diff < -10]
                if bits:
                    st.markdown("  \n".join(bits), unsafe_allow_html=True)
                if worse:
                    st.markdown("Struggle away: " + ", ".join(worse), unsafe_allow_html=True)
                if not bits and not worse:
                    st.caption("Nobody's record changes much away from home.")
    # 23 · your note
    note_key = f"fx_note_{i}_{_key(s['series'])}"
    old = state.series_note(career, team, s["series"])
    n1, n2 = st.columns([5, 1], vertical_alignment="bottom")
    txt = n1.text_input("📝 Your note on this series", value=old, key=note_key, max_chars=300,
                        placeholder="e.g. rest the strike bowler for the 3rd; try the new opener")
    if n2.button("Save note", key=f"{note_key}_save", width="stretch", disabled=txt.strip() == old):
        state.set_series_note(career, team, s["series"], txt)
        st.toast("Note saved", icon="📝")
        st.rerun()
    # 24 · make it a goal
    gl_ = state.goals(career)
    if not any(g.get("kind") == "series" and g.get("team") == team and g.get("series") == s["series"] for g in gl_):
        if st.button("🎯 Make winning this series a goal", key=f"fx_goal_{i}_{_key(s['series'])}"):
            state.set_goals(career, gl_ + [dict(id=FX.new_id(), kind="series", team=team, series=s["series"])])
            st.toast("Goal added: see the Goals tab", icon="🎯")
            st.rerun()


def series_review_box(match_ids) -> None:
    """After a series: every player of yours with advice (use more, keep, think about dropping) against their own
    usual level, and the series against your previous ones in the format."""
    from ccstats import teamreport as TR
    rv = TR.series_review(career, list(match_ids), team)
    if not rv:
        return
    pl = rv["players"]
    st.markdown(f"**🧑‍🏫 Series review: {esc(team)}**")
    for verdict, icon in (("use more", "📈 Use more"), ("think about dropping", "📉 Think about dropping")):
        g = pl[pl.verdict == verdict]
        if len(g):
            st.markdown(f"**{icon}:** " + "; ".join(f"{player_link(r.player)} ({esc(r.why)})" for r in g.itertuples()),
                        unsafe_allow_html=True)
    keep = pl[pl.verdict == "keep"]
    if len(keep):
        st.markdown("**✅ Keep:** " + ", ".join(player_link(p) for p in keep.player), unsafe_allow_html=True)
    rows_ = [["This series", f"{rv['now']['won']}–{rv['now']['lost']}", fmt(rv["now"]["rpw_for"], 1),
              fmt(rv["now"]["rpw_against"], 1)]]
    rows_ += [[esc(e["label"]), f"{e['won']}–{e['lost']}", fmt(e["rpw_for"], 1), fmt(e["rpw_against"], 1)]
              for e in reversed(rv["earlier"])]
    if len(rows_) > 1:
        html_table(rows_, [f"{rv['format']} series", "Won–lost", "Runs per wicket made", "Runs per wicket given"],
                   numeric={2, 3}, raw={0})
    st.caption("Use more: among your best by impact a match in this series and above their own usual level (all their "
               f"earlier {rv['format']}s). Think about dropping: played twice or more, among your lowest and below their "
               "usual level: a batter averaging under 20 here, or a bowler giving away a quarter more per wicket than "
               "usual (or no wickets). A guide from the scorecards: you know their form in the nets.")


def _key(text: str) -> str:
    import hashlib
    return hashlib.md5(f"{team}|{text}".encode()).hexdigest()[:10]


def _save(rows: list[dict], message: str, undo: tuple | None = None) -> None:
    """Save the schedule. undo: (team, what was done, the whole schedule before it), for the Undo button."""
    state.set_fixtures(career, rows)
    st.session_state.pop("fx_editing", None)
    st.session_state.pop("fx_confirm", None)
    if undo is not None:
        st.session_state["fx_undo"] = undo
    st.toast(message, icon="📅")
    st.rerun()


def undo_box(where: str) -> None:
    """What was just deleted, changed or fixed for this team, with a button that puts the schedule back as it was."""
    undo = st.session_state.get("fx_undo")
    if undo and undo[0] == team:
        u1, u2 = st.columns([4, 1], vertical_alignment="center")
        u1.info(f"{undo[1]}.")
        if u2.button("↩️ Undo", key=f"fx_undo_btn{where}", width="stretch"):
            st.session_state.pop("fx_undo", None)
            _save(list(undo[2]), "Put back as it was")


def edit_panel() -> None:
    """Everything you added for this team, one series or tournament a row: change it or delete it."""
    items = FX.schedule_items(schedule, team)
    undo_box("")
    if not items:
        st.info(f"Nothing added for {team} yet. Add a series or tournament on the **Add matches** tab; it shows here "
                "to change or delete.")
        return
    st.markdown(f"**What you added for {team}** · press ✏️ to change a series (opponent, format, how many, home or "
                "away, month or date) or 🗑️ to delete it")
    st.caption("Matches already played keep their results: they're matched to their scorecards again after a change. "
               "Series marked 🆕 auto-added on the Schedule tab come from the scorecards, so they aren't listed here.")
    status = {}
    if len(tracked):
        for sr, g in tracked[tracked.team == team].groupby("series"):
            status[sr] = (int((g.status == "played").sum()), len(g))
    for it in items:
        k = _key(it["series"])
        played, total = status.get(it["series"], (0, it["n"]))
        when = (pd.Timestamp(it["date"]).strftime("%d %b %Y") if it["date"] else FX.month_label(it["month"])) or "no month"
        with st.container(border=True):
            a, b_, c = st.columns([5, 1, 1], vertical_alignment="center")
            icon = "🏆" if it["kind"] == "tournament" else "🏏"
            a.markdown(f"{icon} **{esc(it['series'])}**  \n<span class='small'>{played} of {total} played · {esc(when)}"
                       + (f" · {venue_word(it['venue'])}" if venue_word(it["venue"]) else "") + "</span>",
                       unsafe_allow_html=True)
            if b_.button("✏️ Change", key=f"fx_ch_{k}", width="stretch"):
                st.session_state["fx_editing"] = it["series"]
                st.session_state.pop("fx_confirm", None)
            if c.button("🗑️ Delete", key=f"fx_del_{k}", width="stretch"):
                st.session_state["fx_confirm"] = it["series"]
                st.session_state.pop("fx_editing", None)
            if st.session_state.get("fx_confirm") == it["series"]:
                st.warning(f"Delete **{it['series']}** ({it['n']} match{'es' if it['n'] != 1 else ''}) from your schedule? "
                           "Results already played stay in your career.")
                d1, d2, _ = st.columns([1.4, 1, 3])
                if d1.button("Yes, delete it", type="primary", key=f"fx_yes_{k}", width="stretch"):
                    rows, gone = FX.delete_item(schedule, team, it["series"])
                    _save(rows, f"Deleted {it['series']}", (team, f"Deleted: {it['series']}", schedule))
                if d2.button("Cancel", key=f"fx_no_{k}", width="stretch"):
                    st.session_state.pop("fx_confirm", None)
                    st.rerun()
            if st.session_state.get("fx_editing") == it["series"]:
                change_form(it, k)
    with st.expander(f"Delete {poss(team)} whole schedule"):
        st.caption(f"Takes every series and tournament you added for {team} out of the schedule (results already "
                   "played stay in your career). You can put it back straight after with Undo.")
        sure = st.checkbox(f"Yes, delete all {len(items)} of them", key="fx_del_all_sure")
        if st.button("Delete the whole schedule", disabled=not sure, key="fx_del_all"):
            rows, gone = FX.delete_item(schedule, team)
            st.session_state.pop("fx_del_all_sure", None)
            _save(rows, f"Deleted {poss(team)} schedule",
                  (team, f"Deleted: {poss(team)} whole schedule ({len(items)} items)", schedule))


def change_form(it: dict, k: str) -> None:
    """A series or tournament's details, filled in as they are now; Save puts the changed one in its place."""
    months = list(range(1, 13))
    y0 = int(it["month"][:4]) if it["month"] else year_now
    years = sorted(set(range(year_now - 1, year_now + 4)) | {y0})
    m0 = int(it["month"][5:7]) if it["month"] else (int(latest.month) if pd.notna(latest) else 1)
    fmts = formats_here + ([it["format"]] if it["format"] and it["format"] not in formats_here else [])
    with st.container(border=True):
        st.markdown(f"**Change {esc(it['series'])}**")
        wrong = ""  # dates out of match order
        if it["kind"] == "series":
            opps = list(opp_list)
            if national:
                opps = [t for t in opps if t in FX.NATIONS]
            if it["opponent"] and it["opponent"] not in opps:
                opps = [it["opponent"]] + opps
            e1, e2, e3 = st.columns(3)
            opp = e1.selectbox("Opponent", opps, index=opps.index(it["opponent"]) if it["opponent"] in opps else 0,
                               key=f"fx_e_opp_{k}")
            fmt_ = e2.selectbox("Format", fmts, index=fmts.index(it["format"]) if it["format"] in fmts else 0,
                                key=f"fx_e_fmt_{k}")
            n = e3.number_input("How many matches", 1, 10, int(it["n"]), key=f"fx_e_n_{k}")
            f1, f2, f3, f4 = st.columns([1.3, 1, 1, 1.4], vertical_alignment="bottom")
            wheres = ["Home", "Away", "Neutral"]
            st.session_state.setdefault(f"fx_e_ven_{k}", (it["venue"] or "home").title())
            ven = f1.segmented_control("Where", wheres, required=True, key=f"fx_e_ven_{k}") or "Home"
            st.session_state.setdefault(f"fx_e_know_{k}", any(it.get("dates") or [it["date"]]))
            typed = first_date(f"fx_e_d_{k}", int(n), it.get("dates") or [it["date"]]) \
                if st.session_state.get(f"fx_e_know_{k}") else None
            if typed:  # the month is the first date's: no box saying otherwise
                f2.markdown(f"**Month**  \n{typed:%B %Y} · from your dates")
                mo, yr = typed.month, typed.year
            else:
                mo = f2.selectbox("Month", months, index=m0 - 1, format_func=lambda x: calendar.month_name[x],
                                  key=f"fx_e_mo_{k}")
                yr = f3.selectbox("Year", years, index=years.index(y0), key=f"fx_e_yr_{k}")
            know = f4.toggle("I know the dates", key=f"fx_e_know_{k}",
                             help="The date of each match from the game's fixture list. Leave any you don't know "
                                  "empty: it's worked out from the match before it.")
            dates = date_boxes(f"fx_e_d_{k}", int(n), it.get("dates") or [it["date"]], fmt_) if know else []
            wrong = FX.dates_in_order(dates)
            if wrong:
                st.error(wrong + " Put the dates in match order.")
            new_rows = FX.make_series(team, opp, fmt_, int(n), ven.lower(), f"{yr:04d}-{mo:02d}", dates=dates)
        else:
            e1, e2 = st.columns(2)
            name0 = it["series"].split(" · ")[0]
            names = FX.TOURNAMENTS + ([name0] if name0 not in FX.TOURNAMENTS else [])
            name = e1.selectbox("Tournament", names, index=names.index(name0), key=f"fx_e_tn_{k}")
            fmt_ = e2.selectbox("Format", fmts, index=fmts.index(it["format"]) if it["format"] in fmts else 0,
                                key=f"fx_e_tfmt_{k}")
            f1, f2, f3 = st.columns(3)
            mo = f1.selectbox("Month it starts", months, index=m0 - 1, format_func=lambda x: calendar.month_name[x],
                              key=f"fx_e_tmo_{k}")
            yr = f2.selectbox("Year", years, index=years.index(y0), key=f"fx_e_tyr_{k}")
            games = f3.number_input("Games you'll play (0 = don't know)", 0, 15, int(it["games"]), key=f"fx_e_tg_{k}")
            new_rows = FX.make_tournament(team, FX.canonical_tournament(name), fmt_, f"{yr:04d}-{mo:02d}", int(games))
        given = sum(bool(r["date"]) for r in new_rows)
        st.caption(f"Becomes: **{esc(new_rows[0]['series'])}**" + (f" ({len(new_rows)} matches" if len(new_rows) > 1 else "")
                   + (f", {given} with a date" if given and len(new_rows) > 1 else "") + (")" if len(new_rows) > 1 else ""))
        s1, s2, _ = st.columns([1, 1, 3])
        if s1.button("Save", type="primary", key=f"fx_e_save_{k}", width="stretch", disabled=bool(wrong)):
            others = [r for r in schedule if not (r["team"] == team and r["series"] == it["series"])]
            if any(r["team"] == team and r["series"] == new_rows[0]["series"] for r in others):
                st.warning("You already have a series exactly like that in the schedule: change something, or delete one.")
            else:
                _save(FX.replace_item(schedule, team, it["series"], new_rows), f"Changed to {new_rows[0]['series']}",
                      (team, f"Changed: {it['series']} is now {new_rows[0]['series']}", schedule))
        if s2.button("Cancel", key=f"fx_e_cancel_{k}", width="stretch"):
            st.session_state.pop("fx_editing", None)
            st.rerun()


# ================================================================ schedule
with t_sched:
    if mine_rows.empty:
        st.info(f"No schedule for {team} yet.")
        preview_any()
        st.markdown(HOW_TO)
    else:
        if not scheduled_any:
            st.info(f"Nothing scheduled for {team} yet, so these are the matches they've played this year, added from "
                    "the scorecards. Add what's coming on the **Add matches** tab to see it here too.")
        with safe_section("schedule"):
            sm = FX.summary(tracked, team)
            rec = sm["record"]
            nx = sm["next"]
            kpis([("Played", f"{sm['played']} of {sm['total']}"),
                  ("Won–lost", f"{rec['W']}–{rec['L']}" + (f" ({rec['D']} D)" if rec["D"] else "")),
                  ("To come", f"{sm['to_come']}"),
                  ("Next", esc(f"v {nx['opponent']}" if nx is not None and nx["opponent"] else
                               (stage_of(nx) or nx["series"].replace(FX.AUTO, "").split(" · ")[0]) if nx is not None
                               else "–"))])
            undo_box("_s")
            schedule_check()
            # ---------------------------------------------------------- 144 · next match
            if nx is not None:
                with st.container(border=True):
                    nfmt, nopp, nven = nx["format"], nx["opponent"], nx["venue"]
                    if nopp:
                        logos.heading(nopp, teams=(team, nopp))
                    st.markdown(f"**⏭ Next match:** {esc(next_title(nx))} · "
                                + (f"{venue_word(nven)} · " if venue_word(nven) else "") + when_text(nx), unsafe_allow_html=True)
                    if nopp:
                        pr = state.memo(FX.format_ids, career, team, nfmt)
                        from ccstats import winprob as WP
                        p = state.memo(WP.predict, career, pr, team, nopp, nven if nven in ("home", "away") else "neutral")
                        st.markdown(f"🔮 **{team} {p['win']:.0f}%**" + (f" · draw {p['draw']:.0f}%" if p["multi"] else "")
                                    + f" · **{nopp} {p['lose']:.0f}%**")
                        their = PLN.form(career, nopp, nfmt)
                        bits = ([f"Their last {len(their)}: {form_strip(their)}"] if their else []) + \
                            ([rivalry_text(nopp, nfmt)] if rivalry_text(nopp, nfmt) else [])
                        if bits:
                            st.markdown(" · ".join(bits), unsafe_allow_html=True)
                        for line in PLN.streaks(career, team, nopp, nfmt, nven):
                            st.markdown(esc(line))
                        kb = FX.key_battle(career, team, nopp, nfmt)
                        if kb:
                            st.markdown("⚔️ Key battles: " + "; ".join(kb) + ".")
                    note = state.series_note(career, team, nx["series"])
                    if note:
                        st.markdown(f"📝 **Your note:** {esc(note)}")
                    if nopp and st.button(f"Full preview of {nopp} →", key="fx_go_preview"):
                        go_preview(nopp, nfmt, nven)
            preview_any()
            # ---------------------------------------------------------- 141 · tracker
            if sm["missing"]:
                st.warning(f"⚠️ {sm['missing']} fixture{'s' if sm['missing'] != 1 else ''} should have been played by now but "
                           "no scorecard matches. Check the month and opponent in the table below, or whether the game "
                           "saved the scorecard.")
            st.markdown("**Every fixture** · ✅ played · ⏭ next · ⏳ to come · ⚠️ no scorecard found · 🆕 auto-added")
            icon = {"played": "✅", "next": "⏭", "to come": "⏳", "no scorecard": "⚠️"}
            rows = []
            ch_ = PLN.chances(career, tracked, team)
            chance_of = {(r.series, int(r.no)): r for r in ch_.itertuples()}
            c_ = colours()
            form_of: dict = {}
            for _, r in mine_rows.iterrows():
                res = ""
                stage = stage_of(r)
                if r["status"] == "played":
                    res = match_link(r["match_id"], f"{r['outcome']} · {r['result']}")
                elif stage:
                    res = esc(f"{stage} to come")
                elif r["kind"] == "tournament":
                    gl_ = int(r["games_left"]) if pd.notna(r.get("games_left")) and r.get("games_left") else 0
                    res = esc(f"{gl_} more game{'s' if gl_ != 1 else ''} planned" if gl_ else "games to come")
                no = (f"{int(r['no'])}" if r["no"] else "") + (f" · {stage}" if stage else "")
                if stage == "Final" and r["status"] == "played" and r["outcome"] == "W":
                    no += " 🏆"
                is_auto = str(r.get("auto")) == "True"
                series = (logos.team(r["opponent"], 36) if r["kind"] == "match" and r["opponent"] else "") + \
                    (esc(r["series"].replace(FX.AUTO, "")) + " <span title='auto-added: not in your schedule, so "
                          "added from the scorecards'>🆕</span>" if is_auto else esc(r["series"]))
                if str(r.get("venue_fixed")) == "True":
                    planned, real = venue_word(r.get("venue_planned", "")), venue_word(r["venue"])
                    series += (f" <span title='You put this series {esc(planned)}, but its scorecards show {esc(team)} "
                               f"{esc(real)}: the scorecards are used. Change Home/away in the table below to match.'>"
                               f"📍 {esc(real)}</span>")
                opp = r["opponent"] if r["kind"] == "tournament" else ""
                if r["kind"] == "tournament" and stage and not opp and r["status"] != "played":
                    opp = "to be decided"
                chance, their_form = "", ""
                k_ = (r["series"], int(r["no"] or 0))
                if r["status"] in ("next", "to come") and k_ in chance_of:  # 3 · 13 · how hard, and their form
                    x = chance_of[k_]
                    tone = {"easy": c_["good"], "hard": c_["neg"]}.get(x.level, c_["ink2"])
                    chance = (f"<span style='color:{tone}' title='win {x.win:.0f}%"
                              + (f", draw {x.draw:.0f}%" if x.draw >= 0.5 else "") + f", lose {x.lose:.0f}%'>"
                              f"{LEVEL_ICON[x.level]} {x.win:.0f}% · {x.level}</span>")
                    fk = (x.opponent, x.format)
                    if fk not in form_of:
                        form_of[fk] = form_strip(PLN.form(career, x.opponent, x.format))
                        rv = PLN.rivalry(career, team, x.opponent, x.format)
                        if rv:
                            form_of[fk] += (f" <span title='{'Bogey team' if rv['kind'] == 'bogey' else 'Favourite opponent'}: "
                                            f"{esc(team)} are {rv['text']} against them'>"
                                            f"{'👻' if rv['kind'] == 'bogey' else '😊'}</span>")
                    their_form = form_of[fk]
                rows.append([icon.get(r["status"], ""), series, no, opp, when_text(r), chance, their_form, res])
            html_table(rows, ["", "Series", "Match", "Opponent", "When", "Your chance", "Their form", "Result"],
                       raw={1, 5, 6, 7})
            st.caption("A match is ticked off when the game saves its scorecard: it's matched by the two teams, the "
                       "format and its place in the series, so dates don't need to be exact. Click a result for its "
                       "scorecard. Home and away come from the scorecards (the side named first is at home); 📍 marks a series "
                       "you put at the other venue (hover it). Mark a series neutral if it was played at a neutral ground. "
                       "🆕 Auto-added: played but not in your schedule (or more matches than you put in), so added "
                       "from the scorecards with the rest of its series. "
                       "In a tournament, the next knockout game (semi-final, final …) appears once you're through to "
                       "it, against the winner of the other tie when that's been played. Your chance: of winning that "
                       "game (hover for the draw and defeat), 🟢 easy · ⚪ even · 🔴 hard. Their form: the opponent's "
                       "last 5 in that format; 👻 a bogey team (you've won 30% or less against them), 😊 a favourite "
                       "opponent (70% or more).")
            season_outlook()
# ================================================================ change or delete what you added
with t_edit:
    with safe_section("change or delete"):
        edit_panel()
    # ---------------------------------------------------------- 3 · edit the schedule like a table
    with safe_section("edit schedule"), st.expander("Match by match (advanced): change any cell, add or delete rows",
                                                    expanded=False):
        mine_fx = [r for r in schedule if r["team"] == team]
        st.caption("Change any cell, add a row at the bottom, or select rows and press delete (the bin icon). "
                   "Then press **Save changes**. Month: like 'Jan 2027'. Date: only if you know it. Matches already "
                   "played keep their result whatever you change here. Auto-added matches aren't in this table (they "
                   "come from the scorecards); add the series here yourself to set its home or away.")
        df = pd.DataFrame(mine_fx, columns=FX.COLUMNS)
        show = pd.DataFrame({
            "id": df.id.astype(str), "series": df.series.astype(str), "opponent": df.opponent.astype(str),
            "format": df.format.astype(str), "no": pd.to_numeric(df["no"], errors="coerce").astype("Int64"),
            "venue": df.venue.astype(str), "month": [FX.month_label(x) for x in df.month],
            "date": pd.to_datetime(pd.Series([x or None for x in df.date], dtype=object)),
            "games": pd.to_numeric(df.games, errors="coerce").astype("Int64")}).reset_index(drop=True)
        show["month"] = show["month"].astype(str)
        edited = st.data_editor(
            show, num_rows="dynamic", hide_index=True, width="stretch", key=f"fx_editor_{team}",
            column_config={
                "id": None,  # kept, not shown: it ties each row to its saved fixture
                "series": st.column_config.TextColumn("Series", help="Matches with the same series name are one series"),
                "opponent": st.column_config.SelectboxColumn("Opponent", options=[""] + [t for t in all_teams + extra_opps
                                                                                           if t != team],
                                                             help="Leave empty for a tournament"),
                "format": st.column_config.SelectboxColumn("Format", options=FX.FORMATS, required=True),
                "no": st.column_config.NumberColumn("Match", min_value=0, max_value=20, step=1,
                                                    help="1 for the 1st Test, 2 for the 2nd …"),
                "venue": st.column_config.SelectboxColumn("Home/away", options=["home", "away", "neutral", ""]),
                "month": st.column_config.TextColumn("Month", help="e.g. Jan 2027"),
                "date": st.column_config.DateColumn("Date", help="Only if you know it"),
                "games": st.column_config.NumberColumn("Games (tournament)", min_value=0, max_value=20, step=1)})
        if st.button("Save changes", key="fx_save_edit"):
            new_rows, bad = [], []
            for i, r in edited.iterrows():
                if not str(r.get("series") or "").strip() and not str(r.get("opponent") or "").strip():
                    continue
                month = ""
                mtxt = str(r.get("month") or "").strip()
                if mtxt:
                    mm = FX.RE_MON_YEAR.search(mtxt.lower()) or FX.RE_YEAR_MON.search(mtxt)
                    if not mm:
                        bad.append(f"row {i + 1}: can't read the month '{mtxt}' (write it like Jan 2027)")
                        continue
                    month = (f"{int(mm.group(2)):04d}-{FX._mon_num(mm.group(1)):02d}" if mm.re is FX.RE_MON_YEAR
                             else f"{int(mm.group(1)):04d}-{int(mm.group(2)):02d}")
                d = r.get("date")
                date = pd.Timestamp(d).strftime("%Y-%m-%d") if d is not None and pd.notna(d) else ""
                rid = r.get("id") if pd.notna(r.get("id")) else ""
                new_rows.append(dict(id=rid if isinstance(rid, str) and rid else FX.new_id(), team=team,
                                     series=str(r.get("series") or "").strip() or
                                     FX.series_label(r.get("opponent") or "", r.get("format") or "", 1, r.get("venue") or "",
                                                     month, date),
                                     opponent=str(r.get("opponent") or ""), format=r.get("format") or formats_here[0],
                                     no=int(r.get("no") or 0) if pd.notna(r.get("no")) else 0,
                                     venue=str(r.get("venue") or ""), date=date, month=month or (date[:7] if date else ""),
                                     games=int(r.get("games") or 0) if pd.notna(r.get("games")) else 0))
            if bad:
                st.error("Not saved: " + "; ".join(bad))
            else:
                state.set_fixtures(career, [r for r in schedule if r["team"] != team] + new_rows)
                st.toast("Schedule saved", icon="📅")
                st.rerun()

# ================================================================ add matches
with t_add, safe_section("add matches"):
    st.markdown(HOW_TO)
    kind = st.segmented_control("What are you adding?", ["Series or match", "Tournament"], default="Series or match",
                                required=True, key="fx_kind") or "Series or match"
    months = list(range(1, 13))
    years = list(range(year_now - 1, year_now + 4))
    if kind == "Series or match":
        with st.container(border=True):
            a1, a2 = st.columns(2)
            opps = list(opp_list)
            if national:
                opps = [t for t in opps if t in FX.NATIONS]
            # one box per team: another team's box starts at the top of its own list (its own league first)
            opp = a1.selectbox("Opponent", opps, key=f"fx_opp::{team}")
            ffmt = a2.segmented_control("Format", formats_here, default=formats_here[0], required=True, key="fx_fmt") or formats_here[0]
            b1, b2 = st.columns(2)
            n = b1.pills("How many matches", list(range(1, 8)), default=3, required=True, key="fx_n") or 1
            ven = b2.segmented_control("Where", ["Home", "Away", "Neutral"], default="Home", required=True, key="fx_venue") or "Home"
            d1, d2, d3 = st.columns([1, 1, 1.3], vertical_alignment="bottom")
            typed = first_date("fx_d", int(n)) if st.session_state.get("fx_know") else None
            if typed:  # the month is the first date's: no box saying otherwise
                d1.markdown(f"**Month**  \n{typed:%B %Y} · from your dates")
                mo, yr = typed.month, typed.year
            else:
                mo = d1.selectbox("Month", months, index=max(0, int(latest.month) - 1) if pd.notna(latest) else 0,
                                  format_func=lambda x: calendar.month_name[x], key="fx_month")
                yr = d2.selectbox("Year", years, index=years.index(year_now) if year_now in years else 0, key="fx_year")
            know = d3.toggle("I know the dates", key="fx_know",
                             help="Type the date of each match from the game's fixture list. Leave any you don't know "
                                  "empty: it's worked out from the match before it.")
            dates = date_boxes("fx_d", int(n), [], ffmt) if know else []
            wrong = FX.dates_in_order(dates)
            if wrong:
                st.error(wrong + " Put the dates in match order.")
            preview = FX.make_series(team, opp, ffmt, int(n), ven.lower(), f"{yr:04d}-{mo:02d}", dates=dates)
            given = sum(bool(d) for d in dates)
            st.caption(f"Adds: **{preview[0]['series']}** ({len(preview)} match{'es' if len(preview) != 1 else ''}"
                       + (f", {given} with a date" if given else "") + ")."
                       + (" The month comes from the first date you gave." if given else ""))
            if st.button("Add series", type="primary", key="fx_add_series", disabled=bool(wrong)):
                rows, added = FX.merge(schedule, preview)
                if added:
                    state.set_fixtures(career, rows)
                    for k_ in [k_ for k_ in st.session_state if str(k_).startswith("fx_d_")]:
                        del st.session_state[k_]  # the next series starts with empty date boxes
                    st.toast(f"Added {preview[0]['series']}", icon="📅")
                    st.rerun()
                else:
                    st.warning("That series is already in the schedule.")
    else:
        with st.container(border=True):
            a1, a2 = st.columns(2)
            pick = a1.selectbox("Tournament", FX.TOURNAMENTS + ["Other…"], key="fx_tname")
            name = a1.text_input("Name", key="fx_tother", placeholder="e.g. Asia Cup") if pick == "Other…" else pick
            tf_default = FX.TOURNAMENT_FORMAT.get(pick, formats_here[0])
            tfmt = a2.segmented_control("Format", formats_here, default=tf_default if tf_default in formats_here
                                        else formats_here[0], required=True, key="fx_tfmt") or formats_here[0]
            b1, b2, b3 = st.columns(3)
            tmo = b1.selectbox("Month it starts", months, index=max(0, int(latest.month) - 1) if pd.notna(latest) else 0,
                               format_func=lambda x: calendar.month_name[x], key="fx_tmonth")
            tyr = b2.selectbox("Year", years, index=years.index(year_now) if year_now in years else 0, key="fx_tyear")
            games = b3.number_input("Games you'll play (0 = don't know)", 0, 15, 0, key="fx_tgames")
            if st.button("Add tournament", type="primary", key="fx_add_tour", disabled=not name):
                canon = FX.canonical_tournament(name)
                rows, added = FX.merge(schedule, FX.make_tournament(team, canon, tfmt, f"{tyr:04d}-{tmo:02d}", int(games)))
                if added:
                    state.set_fixtures(career, rows)
                    st.toast(f"Added {canon}", icon="🏆")
                    st.rerun()
                else:
                    st.warning("That tournament is already in the schedule.")
            st.caption("Every match you play in it is ticked off as its scorecard arrives, whoever you play.")
    with st.expander("⌨️ Faster: type your whole year, one series per line"):
        st.markdown("Examples you can copy and change:\n"
                    "```\nEngland 3 Tests away Jan 2027\nAustralia 5 ODIs home Mar 2027\nNZ 3 T20Is away Apr 2027\n"
                    "T20 World Cup Jun 2027\n12 Feb 2027 ODI v Sri Lanka home\n```\n"
                    "Opponent (full name or short like NZ, SA, WI), how many and which format, home / away / neutral, "
                    "and the month. Dates are optional.")
        txt = st.text_area("Your schedule", key="fx_text", height=160, label_visibility="collapsed",
                           placeholder="England 3 Tests away Jan 2027")
        if st.button("Read these lines", key="fx_read"):
            if not (txt or "").strip():
                st.session_state.pop("fx_parsed", None)
                st.warning("Type at least one line first, like the examples above.")
            else:
                rows_, errs_ = FX.parse_lines(txt, team, all_teams + [t for t in extra_opps if t not in all_teams])
                st.session_state["fx_parsed"] = (rows_, errs_)
        parsed = st.session_state.get("fx_parsed")
        if parsed:
            rows_, errs_ = parsed
            for e in errs_:
                st.warning(f"Skipped: {e}")
            if rows_:
                labels_ = list(dict.fromkeys(r["series"] for r in rows_))
                st.markdown("**Will add:**\n" + "\n".join(f"- {esc(x)}" for x in labels_))
                if st.button(f"Add these {len(labels_)}", type="primary", key="fx_add_text"):
                    rows, added = FX.merge(schedule, rows_)
                    state.set_fixtures(career, rows)
                    st.session_state.pop("fx_parsed", None)
                    st.toast(f"Added {added} matches", icon="📅")
                    st.rerun()

# ================================================================ series: live, previews, reports
with t_series, safe_section("series"):
    groups = FX.series_groups(tracked, team) if len(tracked) else []
    if not groups:
        st.info("Add a series on the Add matches tab to see its chances, preview and report here.")
    live = [s for s in groups if s["state"] == "under way"]
    coming = [s for s in groups if s["state"] == "to come"]
    done = [s for s in groups if s["state"] == "done"]
    # ---------------------------------------------------------- 148 · live series situation
    for s in live:
        with st.container(border=True):
            logos.heading(s["opponent"], teams=(team, s["opponent"]))
            o = FX.series_outlook(career, team, s)
            lead = ("level" if s["won"] == s["lost"] else f"{team} lead" if s["won"] > s["lost"] else f"{s['opponent']} lead")
            st.markdown(f"**🔴 Under way: {esc(s['series'])}** · {lead} {s['won']}–{s['lost']}"
                        + (f" ({s['drawn']} drawn)" if s["drawn"] else "") + f" · {o['left']} to play")
            st.markdown(f"**{o['need'].capitalize()}.** Chances from here: **{team} {o['odds']['A']:.0f}%**"
                        + (f" · level {o['odds']['level']:.0f}%" if o["odds"]["level"] >= 0.5 else "")
                        + f" · **{s['opponent']} {o['odds']['B']:.0f}%**")
            st.caption("Likeliest final scores: " + ", ".join(f"{a}–{b} ({v:.0f}%)" for (a, b), v in
                                                             list(o["scorelines"].items())[:4])
                       + ". Each game is worked out from the Elo ratings, form, head to head and venue (see Opponent "
                       "preview); every combination of the games left is counted.")
            with st.expander("More: past series, conditions, who travels well, records in reach, your note"):
                series_extras(s, f"l{live.index(s)}")
    # ---------------------------------------------------------- 19 · the way through a tournament
    for j, tu in enumerate(PLN.tournaments_under_way(career, tracked, team)):
        from ccstats import odds as OD
        with st.container(border=True):
            name = tu["series"].replace(FX.AUTO, "").split(" · ")[0]
            st.markdown(f"**🏆 Under way: {esc(name)}** · {tu['won']}–{tu['lost']} from {tu['played']} game"
                        f"{'s' if tu['played'] != 1 else ''}"
                        + (f" · next: {esc(tu['next_stage'])}" + (f" v {esc(tu['next_opponent'])}" if tu["next_opponent"]
                                                                   else "") if tu["next_stage"] else ""))
            od = state.memo(OD.season_odds, career, tu["event"], tu["season"])
            tb = od["table"]
            mine_t = tb[tb.team == team] if len(tb) else tb
            if od["state"] == "open" and len(mine_t):
                r_ = mine_t.iloc[0]
                grp = tb[tb.group == r_.group].reset_index(drop=True)
                pos = int(grp.index[grp.team == team][0]) + 1
                bits = [f"{ordinal(pos)} in "
                        + (f"{esc(r_.group)}" if od["groups"] > 1 else "the table")
                        + f" with {r_.points:g} points, {int(r_.left)} league game{'s' if r_.left != 1 else ''} left"]
                if np.isfinite(r_.playoffs):
                    bits.append(f"chance of the knockouts **{r_.playoffs:.0f}%**")
                if np.isfinite(r_.title):
                    bits.append(f"of winning it **{r_.title:.0f}%**")
                st.markdown(" · ".join(bits))
                st.caption("The rest of the league played out 4,000 times from the team ratings (as on the Team "
                           "planner page), with the competition's own points and knockout format.")
            elif tu["next_stage"]:
                st.caption(f"Through to the {tu['next_stage'].lower()}: the league is over.")
    # ---------------------------------------------------------- 145 · series preview · 146 · picks
    for i, s in enumerate(coming[:3]):
        with st.expander(f"🔮 Preview: {s['series']}", expanded=i == 0):
            logos.heading(s["opponent"], teams=(team, s["opponent"]))
            o = FX.series_outlook(career, team, s)
            st.markdown(f"**Before ball one:** {team} win the series **{o['odds']['A']:.0f}%**"
                        + (f" · drawn {o['odds']['level']:.0f}%" if o["odds"]["level"] >= 0.5 else "")
                        + f" · {s['opponent']} win it **{o['odds']['B']:.0f}%**")
            st.caption("Likeliest scores: " + ", ".join(f"{a}–{b} ({v:.0f}%)" for (a, b), v in
                                                       list(o["scorelines"].items())[:4]))
            fh = FX.form_and_h2h(career, team, s["opponent"], s["format"])
            h = fh["h2h"]
            st.markdown(f"Form in {s['format']}s · {esc(team)} {form_strip(fh['form'][team])} · "
                        f"{esc(s['opponent'])} {form_strip(fh['form'][s['opponent']])}"
                        + (f" · head to head {h['won']}–{h['lost']}" + (f" ({h['drawn']} drawn)" if h["drawn"] else "")
                           if h["played"] else " · never met in this format"), unsafe_allow_html=True)
            w1, w2 = st.columns(2)
            for col, side in ((w1, team), (w2, s["opponent"])):
                pw = FX.players_to_watch(career, side, s["format"])
                bits = [f"{player_link(p)} {int(v)} runs" for p, v in pw["bat"].items()] + \
                       [f"{player_link(p)} {int(v)} wkts" for p, v in pw["bowl"].items()]
                col.markdown(f"**{esc(side)} to watch** (last {pw['matches']} {s['format']}s): " + (", ".join(bits) or "–"),
                             unsafe_allow_html=True)
            kb = FX.key_battle(career, team, s["opponent"], s["format"])
            if kb:
                st.markdown("⚔️ " + "; ".join(kb) + ".")
            ids_ = FX.format_ids(career, team, s["format"])
            pb, pw_ = SN.picks_against(career, ids_, team, s["opponent"])
            good = list(pb[pb.verdict.str.startswith("Pick")].player) + list(pw_[pw_.verdict.str.startswith("Pick")].player)
            doubt = list(pb[pb.verdict.str.startswith("Think")].player) + list(pw_[pw_.verdict.str.startswith("Think")].player)
            if good or doubt:
                st.markdown((f"**Pick:** {', '.join(dict.fromkeys(good))}. " if good else "")
                            + (f"**Think again:** {', '.join(dict.fromkeys(doubt))}." if doubt else ""))
            elif not pb.empty or not pw_.empty:
                st.caption("Nobody in your squad stands out against them either way yet.")
            st.divider()
            series_extras(s, f"c{i}")
            if st.button(f"Full preview of {s['opponent']} →", key=f"fx_prev_{i}"):
                go_preview(s["opponent"], s["format"], s["venue"])
    # ---------------------------------------------------------- 152 · series reports
    if done:
        st.markdown("### Series reports")
        fc_ = PLN.forecast_check(tracked, team, state.forecasts(career))
        if fc_:
            right_, exact_ = sum(x["right"] for x in fc_), sum(x["exact"] for x in fc_)
            st.markdown(f"**🔮 Forecasts made before ball one:** the favourite was right in {right_} of {len(fc_)} "
                        f"series" + (f", and the exact score came up {exact_} time{'s' if exact_ != 1 else ''}" if exact_
                                     else "") + ".")
        fc_by = {x["series"]: x for x in fc_}
    for s in reversed(done):
        with st.expander(f"📋 {s['series']} · {s['won']}–{s['lost']}" + (f" ({s['drawn']} D)" if s["drawn"] else "")):
            rep = FX.series_report(career, s, team)
            if not rep:
                continue
            st.markdown(f"**{rep['result']}** · {rep['first']:%d %b} to {rep['last']:%d %b %Y}")
            x = fc_by.get(s["series"])
            if x:
                f_ = x["forecast"]
                st.markdown(f"🔮 Forecast before ball one ({f_.get('made', '')}): {esc(team)} {f_['win']:.0f}%"
                            + (f" · level {f_['draw']:.0f}%" if f_.get("draw", 0) >= 0.5 else "")
                            + f" · {esc(s['opponent'])} {f_['lose']:.0f}%"
                            + (f", likeliest {f_['likely']}" if f_.get("likely") else "")
                            + f". Result {x['result']}: " + ("✅ the favourite won" if x["right"] else "❌ an upset")
                            + (", exact score ✓" if x["exact"] else "") + ".")
            if rep["pos"] is not None:
                p = rep["pos"]
                st.markdown(f"🏅 **Player of the Series: {player_link(p.player)}** ({esc(p.team)}) · {int(p.runs)} runs, "
                            f"{int(p.wickets)} wickets", unsafe_allow_html=True)
            r1, r2 = st.columns(2)
            r1.markdown("**Most runs**  \n" + "  \n".join(f"{esc(pl)} ({esc(tm)}) {int(v)}" for (pl, tm), v in rep["top_bat"].items()))
            r2.markdown("**Most wickets**  \n" + "  \n".join(f"{esc(pl)} ({esc(tm)}) {int(v)}" for (pl, tm), v in rep["top_bowl"].items()))
            bits = []
            if rep["best_bat"] is not None:
                b = rep["best_bat"]
                bits.append(f"Best innings: {b.player} {b.runs}{'' if b.out else '*'} ({b.balls})")
            if rep["best_bowl"] is not None:
                b = rep["best_bowl"]
                bits.append(f"best bowling: {b.player} {b.wickets}/{b.runs}")
            for t_, (a, b) in rep["elo"].items():
                bits.append(f"{t_} Elo {a:.0f} → {b:.0f} ({b - a:+.0f})")
            st.markdown(" · ".join(esc(x) for x in bits))
            for x in rep["records"][:4]:
                st.markdown(f"🏆 {esc(x)}")
            for x in rep["milestones"][:4]:
                st.markdown(f"🎯 {esc(x)}")
            st.markdown("Matches: " + " · ".join(match_link(r.match_id, f"{r.date:%d %b}") for r in rep["matches"].itertuples()),
                        unsafe_allow_html=True)
            series_review_box(rep["matches"].match_id)

# ================================================================ 143 · year calendar
with t_cal, safe_section("calendar"):
    team_dates = m[(m.home == team) | (m.away == team)].date
    todo_rows = mine_rows[mine_rows.status.isin(["to come", "next"])] if len(mine_rows) else mine_rows
    seasons_ = CV.seasons_for(list(team_dates) + [a for a in (todo_rows.anchor if len(todo_rows) else []) if pd.notna(a)])
    if not seasons_:
        st.info(f"No matches or fixtures for {team} yet. Add your schedule on the Add matches tab.")
    else:
        # opens on the season of your next fixture, else of your latest game
        nxt_ = todo_rows.anchor.min() if len(todo_rows) and todo_rows.anchor.notna().any() else None
        now_ = CV.season_of(nxt_) if nxt_ is not None else (CV.season_of(team_dates.max()) if len(team_dates) else seasons_[0])
        if st.session_state.get("fx_cal_season") not in seasons_:
            st.session_state["fx_cal_season"] = now_ if now_ in seasons_ else seasons_[0]
        cy = st.selectbox("Season", seasons_, format_func=CV.season_label, key="fx_cal_season")
        days, notes = CV.team_chips(career, team, tracked, int(cy))
        st.markdown(CV.season_html(int(cy), days, notes, CV.today_in_game(career)), unsafe_allow_html=True)
        played_y = int((((m.home == team) | (m.away == team)) & (m.date.map(CV.season_of) == int(cy))).sum())
        to_come_ = sum(len(v) for v in notes.values())
        st.caption(f"{team} in {CV.season_label(int(cy))}: {played_y} match{'es' if played_y != 1 else ''} played. "
                   "W blue: won · L red: lost · grey: drawn, tied or no result · dashed: still to come. T = Test, "
                   "O = ODI, 20 = T20 (and the first letters of the opponent). A series still to come whose dates you "
                   "didn't give is in the yellow box at the top of its month; give the first match's date when you add "
                   "it and it's on its day too. The outlined day is the latest match played. Click a result for its "
                   "scorecard.")
        if to_come_ == 0 and not any("UP" in c for v in days.values() for c in v):
            st.caption("Nothing still to come this season in your schedule: add it on the **Add matches** tab.")

# ================================================================ 149 · WTC race
with t_wtc, safe_section("WTC race"):
    race = FX.wtc_race(career, tracked, team) if len(tracked) else (FX.wtc_race(career, FX.track(career, []), team)
                                                                   if team in SN.WTC_TEAMS else None)
    if race is None:
        st.info(f"{team} aren't one of the nine World Test Championship sides, or no WTC Tests have been played yet.")
    else:
        t = race["table"]
        st.markdown(f"**World Test Championship {race['cycle']}–{str(race['cycle'] + 2)[-2:]}** · "
                    f"{team} have {race['remaining']} Test{'s' if race['remaining'] != 1 else ''} left in your schedule")
        html_table([[i, esc(r.team), r.played, r.won, r.lost, r.drawn, r.points, fmt(r.pct, 1)]
                    for i, r in zip(t.index, t.itertuples())], ["#", "Team", "P", "W", "L", "D", "Pts", "PCT %"],
                   numeric={0, 2, 3, 4, 5, 6, 7}, raw={1}, row_class=["hi" if x == team else "" for x in t.team])
        if race["remaining"]:
            k = race["need"]
            line = (f"To finish above **{race['bar_team']}** ({race['bar']:.1f}%, the side in the top two after you) "
                    + (f"{team} need **{k} win{'s' if k != 1 else ''} from {race['remaining']}** Tests"
                       if k is not None else f"{team} can't get there with the Tests left") + ". ")
            line += f"Best possible: {race['best']:.1f}%."
            if np.isfinite(race["chance"]):
                line += (f" Chance of finishing in the top two: **{race['chance']:.0f}%** "
                         f"(projected PCT {race['expected']:.1f}%).")
            st.markdown(line)
            todo = race["todo"]
            st.caption("Your Tests still to come: " + ", ".join(f"v {o} ({venue_word(v) or '?'})" for o, v in
                                                                zip(todo.opponent, todo.venue))
                       + ". The other sides' remaining Tests aren't in your schedule, so their percentages are taken as "
                       "they stand now. Each of your Tests is worked out from the ratings, as on Opponent preview.")
        else:
            st.caption("Add your Tests for this cycle on the Add matches tab to see what you need to reach the final.")

# ================================================================ 150 · milestone countdown
with t_miles, safe_section("milestones"):
    mc = FX.milestone_countdown(career, tracked, team) if len(mine_rows) else pd.DataFrame()
    if mc.empty:
        st.info("Add fixtures to see which milestones your players could reach in them.")
    else:
        within = mc[mc.within]
        st.markdown(f"**Milestones in reach in your schedule** · {len(within)} of your players' next round numbers "
                    "could fall in the matches you have left")
        html_table([[player_link(r.player), r.format, f"{r.next:,} {r.what}", f"{r.needed:,}", fmt(r.per_match, 1),
                     esc(r.when) if r.within else f"needs about {r.games_needed} games; {r.games_left} left"]
                    for r in mc.head(25).itertuples()],
                   ["Player", "Format", "Next milestone", "Still needs", "Per match", "Around"],
                   numeric={3, 4}, raw={0, 5})
        st.caption("Per match: their average per match in that format so far (everyone who played in your last 5 "
                   "matches in it). 'Around' is the fixture they'd reach it in if they keep that rate: a guide, not a "
                   "promise.")

# ================================================================ 151 · season goals
with t_goals, safe_section("goals"):
    gl = state.goals(career)
    mine_g = [g for g in gl if g.get("team") == team or g.get("kind") == "player"]
    if mine_g:
        for g in mine_g:
            pg = FX.goal_progress(career, tracked, g)
            with st.container(border=True):
                a, b = st.columns([6, 1])
                badge = {"achieved": "✅", "missed": "❌", "on course": "🟢", "at risk": "🟠", "under way": "🔵",
                         "to come": "⏳"}.get(pg["status"], "•")
                a.markdown(f"{badge} **{esc(FX.goal_label(g))}**  \n{esc(pg['text'])}")
                a.progress(float(min(max(pg["done"], 0.0), 1.0)))
                if b.button("Remove", key=f"fx_goal_del_{g['id']}"):
                    state.set_goals(career, [x for x in gl if x.get("id") != g["id"]])
                    st.rerun()
    else:
        st.info("No goals yet. Add one below and watch its progress bar move with every match.")
    # ---------------------------------------------------------- 24 · ready-made goals from your schedule
    sugg = PLN.suggested_goals(career, tracked, team, gl)
    if sugg:
        with st.container(border=True):
            st.markdown("**💡 Suggested goals** · from your schedule, one click to add")
            for j, g in enumerate(sugg[:6]):
                a_, b_ = st.columns([5, 1], vertical_alignment="center")
                a_.markdown(esc(FX.goal_label(g)))
                if b_.button("Add", key=f"fx_sugg_{j}_{_key(FX.goal_label(g))}", width="stretch"):
                    state.set_goals(career, gl + [dict(g, id=FX.new_id())])
                    st.toast("Goal added", icon="🎯")
                    st.rerun()
            if len(sugg) > 1:
                if st.button(f"Add all {len(sugg[:6])}", key="fx_sugg_all"):
                    state.set_goals(career, gl + [dict(g, id=FX.new_id()) for g in sugg[:6]])
                    st.toast(f"{len(sugg[:6])} goals added", icon="🎯")
                    st.rerun()
    with st.container(border=True):
        st.markdown("**Add a goal**")
        gk = st.selectbox("Goal", list(FX.GOAL_KINDS), format_func=FX.GOAL_KINDS.get, key="fx_goal_kind")
        goal = dict(id=FX.new_id(), kind=gk, team=team)
        ok = True
        if gk == "series":
            opts_ = [s["series"] for s in FX.series_groups(tracked, team)] if len(tracked) else []
            if opts_:
                goal["series"] = st.selectbox("Series", opts_, key="fx_goal_series")
            else:
                st.caption("Add a series on the Add matches tab first.")
                ok = False
        elif gk == "wtc":
            if team not in SN.WTC_TEAMS:
                st.caption(f"{team} aren't a World Test Championship side.")
                ok = False
        elif gk == "player":
            g1, g2, g3, g4 = st.columns([2, 1, 1, 1])
            squad = sorted(set(career.batting[(career.batting.team == team)].player))
            goal["player"] = g1.selectbox("Player", squad, key="fx_goal_player") if squad else ""
            goal["format"] = g2.selectbox("Format", formats_here, key="fx_goal_fmt")
            goal["what"] = g3.selectbox("Of", ["runs", "wickets"], key="fx_goal_what")
            goal["target"] = int(g4.number_input("Target", 1, 20000, 1000, key="fx_goal_target"))
            yr_ = st.selectbox("Counting", ["Their whole career"] + [str(y) for y in years], key="fx_goal_year")
            goal["year"] = "" if yr_.startswith("Their") else yr_
            ok = bool(goal["player"])
        else:
            g1, g2, g3 = st.columns(3)
            goal["format"] = g1.selectbox("Format", formats_here, key="fx_goal_wfmt")
            goal["target"] = int(g2.number_input("Wins", 1, 100, 10, key="fx_goal_wins"))
            goal["year"] = g3.selectbox("In", [str(y) for y in years], index=1, key="fx_goal_wyear")
        if st.button("Add goal", type="primary", key="fx_goal_add", disabled=not ok):
            state.set_goals(career, gl + [goal])
            st.toast("Goal added", icon="🎯")
            st.rerun()
