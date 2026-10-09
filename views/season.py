import calendar

import pandas as pd
import streamlit as st

from ccstats import fixtures as FX
from ccstats import rankings as R
from ccstats import tables as T
from ccstats import winprob as WP
from ccstats.competitions import shown_name
from ui import calendar_view as CV
from ui import state
from ui.charts import _n
from ui.theme import colours, esc, html_table, page_header, safe_section

career = state.current()
if career is None:
    st.info("Load a career on the Home page first.")
    st.stop()
state.stop_if_no_matches(career)

m = career.matches
page_header("Season", "Calendar and series",
            "A whole season (April to March) on one calendar: every result, and your fixtures still to come; every "
            "bilateral series and how it stands, and how far each competition has got this season.")
teams = sorted(set(m.home) | set(m.away))
mine = state.my_teams(career)
c1, c2 = st.columns([1.6, 2])
team = c1.selectbox("Team", ["All teams"] + teams, key="se_team",
                    index=(teams.index(mine[0]) + 1) if mine else 0)
games = m if team == "All teams" else m[(m.home == team) | (m.away == team)]

tab_cal, tab_series, tab_progress = st.tabs(["Calendar", "Series tracker", "Season progress"])

# ---------------------------------------------------------------- calendar
with tab_cal, safe_section("calendar"):
    # your schedule's fixtures still to come (Fixtures page), for the team picked
    tracked = (state.memo(FX.track, career, state.fixtures(career), auto=(team,))
               if team != "All teams" else None)
    todo_ = tracked[(tracked.team == team) & tracked.status.isin(["to come", "next"])] if tracked is not None and len(tracked) else None
    seasons_ = CV.seasons_for(list(games.date) + (list(todo_.anchor.dropna()) if todo_ is not None else []))
    if not seasons_:
        st.info("No matches yet.")
    else:
        v1, v2 = st.columns([1.3, 2.7], vertical_alignment="bottom")
        st.session_state.setdefault("se_view", "Whole season")
        view = v1.segmented_control("Show", ["Whole season", "One month"], required=True, key="se_view") or "Whole season"
    if seasons_ and view == "Whole season":
        nxt_ = todo_.anchor.min() if todo_ is not None and len(todo_) and todo_.anchor.notna().any() else None
        latest_ = games.date.max() if len(games) else None
        now_ = CV.season_of(nxt_) if nxt_ is not None else (CV.season_of(latest_) if latest_ is not None else seasons_[0])
        if st.session_state.get("se_season") not in seasons_:
            st.session_state["se_season"] = now_ if now_ in seasons_ else seasons_[0]
        sy = int(v2.selectbox("Season", seasons_, format_func=CV.season_label, key="se_season"))
        if team == "All teams":
            days, notes = CV.all_teams_chips(career, sy), {}
        else:
            days, notes = CV.team_chips(career, team, tracked, sy)
        st.markdown(CV.season_html(sy, days, notes, CV.today_in_game(career)), unsafe_allow_html=True)
        in_season = games[games.date.map(CV.season_of) == sy]
        if team != "All teams":
            w = int((in_season.winner == team).sum())
            lost = int(((in_season.winner != team) & (in_season.winner != "")).sum())
            st.caption(f"{team} in {CV.season_label(sy)}: played {len(in_season)}, won {w}, lost {lost}. W blue: won · "
                       "L red: lost · grey: drawn, tied or no result · dashed: still to come (from your schedule on the "
                       "Fixtures page; a series without dates is in the yellow box at the top of its month). T = Test, "
                       "O = ODI, 20 = T20. Click a result for its scorecard.")
        else:
            st.caption(f"{len(in_season)} matches in {CV.season_label(sy)}. Hover a day for its games; pick a team to "
                       "see its results and fixtures to come.")
    elif seasons_:
        # your fixtures still to come: on their day when the schedule has the date, else listed under the month
        up_days, up_notes = {}, {}
        for _, r in (todo_.iterrows() if todo_ is not None else []):
            a_ = r["anchor"]
            if pd.isna(a_):
                continue
            who = r["opponent"] or r["series"].replace(FX.AUTO, "").split(" · ")[0]
            if r["date"]:
                d_ = pd.Timestamp(r["date"])
                up_days.setdefault((d_.year, d_.month, d_.day), []).append(
                    f"<a class='UP' title='{esc(r['series'].replace(FX.AUTO, ''))} · to come'>⏳ v {esc(who)}</a>")
            else:
                up_notes.setdefault((a_.year, a_.month), {}).setdefault(r["series"].replace(FX.AUTO, ""), 0)
                up_notes[(a_.year, a_.month)][r["series"].replace(FX.AUTO, "")] += 1
        months = sorted({(d.year, d.month) for d in games.date} | {k[:2] for k in up_days} | set(up_notes), reverse=True)
        if st.session_state.get("se_month") not in months:  # the month of the latest game, else the next fixture
            st.session_state["se_month"] = ((games.date.max().year, games.date.max().month) if len(games)
                                            else months[-1])
        ym = v2.selectbox("Month", months, format_func=lambda x: f"{calendar.month_name[x[1]]} {x[0]}", key="se_month")
        y, mo = ym
        cal = calendar.Calendar(firstweekday=0)
        by_day = {}
        in_month = games[(games.date.dt.year == y) & (games.date.dt.month == mo)] if len(games) else games
        for r in in_month.sort_values(["date", "match_id"]).itertuples():
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
                inner = (f"<div class='d'>{d.day}</div>" + "".join(by_day.get(d.day, []))
                         + "".join(up_days.get((y, mo, d.day), [])) if d.month == mo else f"<div class='d'>{d.day}</div>")
                cells.append(f"<td class='{'' if d.month == mo else 'out'}'>{inner}</td>")
            rows.append("<tr>" + "".join(cells) + "</tr>")
        head = "".join(f"<th>{d}</th>" for d in ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"))
        st.markdown(f"<table class='cal'><thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table>",
                    unsafe_allow_html=True)
        for name_, n_ in up_notes.get((y, mo), {}).items():
            st.markdown(f"⏳ **{esc(name_)}** · {n_} match{'es' if n_ != 1 else ''} to come, dates to come")
        month_games = games[(games.date.dt.year == y) & (games.date.dt.month == mo)] if len(games) else games
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
                st.markdown("**Still going** · with each side's chance of winning the series")
                rows_ = []
                for r in live.itertuples():
                    g_ = m[m.match_id.isin(r.match_ids)]
                    a_, b_ = g_.home.iloc[0], g_.away.iloc[0]
                    wa_, wb_ = int((g_.winner == a_).sum()), int((g_.winner == b_).sum())
                    sec_ids_ = m[m.section == r.section].match_id
                    elo_, _ = state.memo(R.team_elo, career, r.section)
                    e_ = elo_.set_index("team").elo
                    p_ = 1 / (1 + 10 ** ((e_.get(b_, 1500) - e_.get(a_, 1500)) / 400))
                    d_ = WP.draw_rate(career, sec_ids_) if r.section == "Tests" else 0.0
                    odds = WP.series_odds(p_ * (1 - d_), d_, wa_, wb_, int(r.length - r.played))
                    chance_ = f"{a_} {odds['A']:.0f}% · " + (f"drawn {odds['level']:.0f}% · " if odds["level"] >= 0.5 else "") + \
                        f"{b_} {odds['B']:.0f}%"
                    rows_.append([f"{r.start:%d %b %Y}", r.section, r.teams, r.score, f"{r.played} of {r.length}",
                                  chance_, r.top_runs, r.top_wickets])
                html_table(rows_, ["Started", "Format", "Series", "Score", "Played", "Series chances", "Top runs",
                                   "Top wickets"])
                st.caption("Series chances: every way the games left could go, each game won by the side with the higher "
                           "Elo rating more often (and drawn as often as Tests here are drawn).")
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
            played = f"{n} of about {full} matches" if full else f"{_n(n, 'match', 'matches')} so far"
            bars_html.append([f"{esc(name)} {season}", played, bar, esc(stage), esc(leader)])
        html_table(bars_html, ["Competition", "Played", "Progress", "Stage", "Top of the table"], raw={2})
        st.caption("'About' uses the number of matches in the last full season of the same competition; a first season "
                   "shows matches so far.")
