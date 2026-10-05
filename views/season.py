import calendar

import streamlit as st

from ccstats import tables as T
from ccstats.competitions import shown_name
from ui import state
from ui.theme import colours, esc, html_table, page_header, safe_section

career = state.current()
if career is None:
    st.info("Load a career on the Home page first.")
    st.stop()

m = career.matches
page_header("Season", "Results calendar and series",
            "Every result on a calendar, every bilateral series and how it stands, and how far each competition "
            "has got this season.")
teams = sorted(set(m.home) | set(m.away))
mine = state.my_teams(career)
c1, c2 = st.columns([1.6, 2])
team = c1.selectbox("Team", ["All teams"] + teams, key="se_team",
                    index=(teams.index(mine[0]) + 1) if mine else 0)
games = m if team == "All teams" else m[(m.home == team) | (m.away == team)]

tab_cal, tab_series, tab_progress = st.tabs(["Results calendar", "Series tracker", "Season progress"])

# ---------------------------------------------------------------- calendar
with tab_cal, safe_section("calendar"):
    if games.empty:
        st.info("No matches yet.")
    else:
        months = sorted({(d.year, d.month) for d in games.date}, reverse=True)
        ym = c2.selectbox("Month", months, format_func=lambda x: f"{calendar.month_name[x[1]]} {x[0]}", key="se_month")
        y, mo = ym
        cal = calendar.Calendar(firstweekday=0)
        by_day = {}
        for r in games[(games.date.dt.year == y) & (games.date.dt.month == mo)].sort_values(["date", "match_id"]).itertuples():
            if team == "All teams":
                cls = "NR"
                text = f"{r.home.split()[0]} v {r.away.split()[0]}"
            else:
                opp = r.away if r.home == team else r.home
                cls = "W" if r.winner == team else "L" if r.winner == opp else "D" if r.result_type == "draw" else \
                    "T" if r.result_type == "tie" else "NR"
                text = f"{cls} v {opp}"
            title = f"{shown_name(r.section, r.event)}: {r.result}"
            by_day.setdefault(r.date.day, []).append(
                f"<a class='{cls}' href='match?match={esc(r.match_id)}' target='_self' title='{esc(title)}'>{esc(text)}</a>")
        rows = []
        for week in cal.monthdatescalendar(y, mo):
            cells = []
            for d in week:
                inner = f"<div class='d'>{d.day}</div>" + "".join(by_day.get(d.day, [])) if d.month == mo else f"<div class='d'>{d.day}</div>"
                cells.append(f"<td class='{'' if d.month == mo else 'out'}'>{inner}</td>")
            rows.append("<tr>" + "".join(cells) + "</tr>")
        head = "".join(f"<th>{d}</th>" for d in ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"))
        st.markdown(f"<table class='cal'><thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table>",
                    unsafe_allow_html=True)
        month_games = games[(games.date.dt.year == y) & (games.date.dt.month == mo)]
        if team != "All teams" and len(month_games):
            w = int((month_games.winner == team).sum())
            lost = int(((month_games.winner != team) & (month_games.winner != "")).sum())
            st.caption(f"{team} in {calendar.month_name[mo]} {y}: played {len(month_games)}, won {w}, lost {lost}. "
                       "Blue: won · red: lost · grey: drawn, tied or no result. Click a game for its scorecard.")
        else:
            st.caption(f"{len(month_games)} matches in {calendar.month_name[mo]} {y}. Click a game for its scorecard; "
                       "pick a team to colour the results.")

# ---------------------------------------------------------------- series tracker
with tab_series, safe_section("series tracker"):
    bil = m[m.series_id != ""]
    if team != "All teams":
        bil = bil[(bil.home == team) | (bil.away == team)]
    if bil.empty:
        st.info("No bilateral series" + ("" if team == "All teams" else f" for {team}") + " yet.")
    else:
        sr = T.series_table(career, bil.match_id)
        sec_of = bil.groupby("series_id").section.first()
        sr = sr.assign(section=sr.series_id.map(sec_of))
        live = sr[sr.played < sr.length]
        done = sr[sr.played >= sr.length]
        if len(live):
            with st.container(border=True):
                st.markdown("**Still going**")
                html_table([[f"{r.start:%d %b %Y}", r.section, r.teams, r.score, f"{r.played} of {r.length}",
                             r.result.split(' · ')[0], r.top_runs, r.top_wickets] for r in live.itertuples()],
                           ["Started", "Format", "Series", "Score", "Played", "Now", "Top runs", "Top wickets"])
        with st.container(border=True):
            st.markdown("**Finished series** · newest first")
            if done.empty:
                st.caption("None finished yet.")
            else:
                html_table([[f"{r.start:%d %b %Y}", r.section, r.teams, r.score, r.result, r.top_runs, r.top_wickets]
                            for r in done.itertuples()],
                           ["Started", "Format", "Series", "Score", "Result", "Top runs", "Top wickets"],
                           row_class=["hi" if team != "All teams" and r.result.startswith(team) else "" for r in done.itertuples()])
        st.caption("A series counts as finished once all its matches (the number in the match titles, e.g. '3rd of 5') "
                   "are in. Player of the Series is on Player stories.")

# ---------------------------------------------------------------- season progress
with tab_progress, safe_section("season progress"):
    latest = m.groupby("event").season.max()
    rows = []
    for event, season in latest.items():
        g = m[(m.event == event) & (m.season == season)]
        if g.competition.iloc[0] in T.BILATERAL:
            continue
        older = m[(m.event == event) & (m.season < season)]
        full = int(older.groupby("season").size().max()) if len(older) else None
        ko = g[g.knockout]
        final = g[g.stage == "Final"]
        if len(final) == 1 and (final.winner.iloc[0] or final.tiebreak_winner.iloc[0]):
            stage = f"Finished: {final.winner.iloc[0] or final.tiebreak_winner.iloc[0]} won"
        elif len(ko):
            stage = f"Knockouts ({ko.sort_values('date').stage.iloc[-1]})"
        else:
            stage = "League stage"
        lt = T.league_tables(career, g.match_id)
        leader = ", ".join(t.team.iloc[0] for _, t, _ in lt if len(t)) if lt else "–"
        pct = min(len(g) / full * 100, 100) if full else None
        rows.append((shown_name(g.section.iloc[0], event), season, len(g), full, pct, stage, leader,
                     team == "All teams" or bool(((g.home == team) | (g.away == team)).any())))
    rows = [r for r in rows if r[7]]
    if not rows:
        st.info("No competitions running" + ("" if team == "All teams" else f" with {team}") + ".")
    else:
        bars_html = []
        for name, season, n, full, pct, stage, leader, _ in sorted(rows, key=lambda r: (-int(r[1]), r[0])):
            cc = colours()
            bar = (f"<div style='height:8px;border-radius:4px;background:{cc['mid']};overflow:hidden;min-width:80px'>"
                   f"<div style='height:8px;width:{pct:.0f}%;background:{cc['s1']}'></div></div>") if pct is not None else ""
            played = f"{n} of about {full} matches" if full else f"{n} matches so far"
            bars_html.append([f"{esc(name)} {season}", played, bar, esc(stage), esc(leader)])
        html_table(bars_html, ["Competition", "Played", "Progress", "Stage", "Top of the table"], raw={2})
        st.caption("'About' uses the number of matches in the last full season of the same competition; a first season "
                   "shows matches so far.")
