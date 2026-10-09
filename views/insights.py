import numpy as np
import plotly.graph_objects as go
import streamlit as st

from ccstats import insights as I
from ccstats import teamplay as TP
from ccstats import winprob as WP
from ccstats.stats import Scope, kind_of, ordinal
from ui import state
from ui.theme import counted
from ui.charts import pct, CONFIG, _axis, _layout, bars, fmt
from ui.theme import kpis, chart_note, colours, html_table, page_header, safe_section

career = state.current()
if career is None:
    st.info("Load a career on the Home page first.")
    st.stop()
state.stop_if_no_matches(career)

m = career.matches
page_header("Insights", "The bigger picture",
            "Questions about a whole competition: what total wins games, how much home matters, how scoring changes from "
            "season to season, and who has suddenly got better.")
tab_total, tab_chase, tab_home, tab_seasons, tab_break, tab_tests = st.tabs(
    ["Is this total enough?", "Chase calculator", "Home advantage", "Season by season", "Breakout players",
     "Innings by innings"])
sections = m.section.value_counts()
c = colours()

# ---------------------------------------------------------------- total enough
with tab_total:
    c1, c2 = st.columns([2, 1])
    state.recall("in_t_section", "section", list(sections.index))
    section = c1.selectbox("Section", list(sections.index), key="in_t_section", on_change=state.remember("in_t_section", "section"),
                           format_func=lambda s: counted(s, sections[s]))
    seasons = sorted(m[m.section == section].season.unique(), reverse=True)
    state.recall("in_t_season", "season", ["All seasons"] + seasons)
    season = c2.selectbox("Season", ["All seasons"] + seasons, key="in_t_season", on_change=state.remember("in_t_season", "season"))
    ids = Scope(sections=[section], seasons=[] if season == "All seasons" else [season]).match_ids(m)
    table, size = I.total_enough(career, ids)
    if table.empty:
        st.info("No finished matches here yet.")
    else:
        kind = kind_of(m[m.match_id.isin(ids)])
        what = "first-innings score" if kind == "multi" else "score batting first"
        default = int(np.median(I.first_innings(career, ids).runs))
        score = st.number_input(f"Type a {what}", min_value=0, max_value=1500, value=default, step=5, key="in_t_score")
        ch = I.chance_with(career, ids, int(score))
        a, b = ch["at_least"], ch["below"]
        st.markdown(
            f"<div class='board'><div class='label'>{section}{'' if season == 'All seasons' else ' ' + season}</div>"
            f"<div class='line'><span class='score'>{pct(a['pct'])}</span><span class='vs'>won with {score} or more "
            f"({a['won']} of {a['matches']})</span></div>"
            f"<div class='res'>With less than {score}: won {b['won']} of {b['matches']} "
            f"({pct(b['pct'])})</div></div>", unsafe_allow_html=True)
        st.write("")
        # ---------------------------------------------------------------- 52 · both sides of a score
        with safe_section("score chances"):
            here_t = m[m.match_id.isin(ids)]
            teams_t = sorted(set(here_t.home) | set(here_t.away))
            mine_t = [t for t in state.my_teams(career) if t in teams_t]
            tcol, _ = st.columns([1.5, 2])
            team_t = tcol.selectbox("Only this team's games (optional)", ["Every team"] + teams_t, key="in_t_team",
                                    index=(teams_t.index(mine_t[0]) + 1) if mine_t else 0)
            sc = TP.score_chances(career, ids, int(score), "" if team_t == "Every team" else team_t)
            who = "" if team_t == "Every team" else f"{team_t} "
            band = f"first-innings scores from {sc['low']} to {sc['high']}" if sc.get("band") else ""
            left, right = st.columns(2, gap="medium")
            for box, key_, title in ((left, "batting_first", f"{who}batted first and made {score}"),
                                     (right, "bowling_first", f"{who}kept them to {score} and "
                                                              f"{'batted second' if kind == 'multi' else 'chased'}")):
                r = sc.get(key_)
                with box:
                    with st.container(border=True):
                        st.markdown(f"**If {title}**")
                        if not r or not r["played"]:
                            st.caption("No games with a score like this yet.")
                            continue
                        few = " · few matches, treat with care" if r["decided"] < 8 else ""
                        if kind == "multi":
                            st.markdown(f"<div class='kpi'><span>Won · drawn · lost</span><strong>{pct(r['win_pct'])} "
                                        f"<span class='small'>{r['won']}–{r['drawn']}–{r['lost']}</span></strong></div>",
                                        unsafe_allow_html=True)
                        else:
                            st.markdown(f"<div class='kpi'><span>Chance of winning</span><strong>{pct(r['win_pct'])}"
                                        f"</strong></div>", unsafe_allow_html=True)
                        st.caption(f"Won {r['won']} of {r['decided']} ({band}){few}."
                                   + (f" {r['tied']} tied and {r['no_result']} with no result left out."
                                      if r["tied"] or r["no_result"] else ""))
            st.caption("Built from matches whose first-innings score was close to the one you typed "
                       f"(within {sc.get('band', 0)} runs either way)."
                       + (" Ties and no-results are left out, so the two sides add up to 100%." if kind != "multi" else
                          " Multi-day games can be drawn, so each side shows won-drawn-lost."))
        with st.container(border=True):
            st.markdown(f"**Win % batting first, by {what}** · bands of {size} runs")
            st.plotly_chart(bars(table.band[::-1], table.win_pct[::-1], "Win % for the side batting first", 0,
                                 texts=[f"{p:.0f}% · won {w} of {n}" for p, w, n in
                                        zip(table.win_pct[::-1], table.won[::-1], table.matches[::-1])],
                                 x_range=[0, 128],  # room for the text after a 100% bar
                                 notes=[f"{w} won, {l} lost" + (f", {d} drawn" if d else "") + (f", {t} tied" if t else "")
                                        + f" · {n} matches" for w, l, d, t, n in
                                        zip(table.won[::-1], table.lost[::-1], table.drawn[::-1], table.tied[::-1], table.matches[::-1])]),
                            width="stretch", config=CONFIG, key="in_t_bars")
            solid = table[table.matches >= 3]
            par = solid.iloc[0:0]
            for i in range(len(solid) - 1, -1, -1):  # from the top down, while every band wins half or more
                if solid.win_pct.iloc[i] < 50:
                    break
                par = solid.iloc[i:i + 1]
            if len(par):
                p0 = par.iloc[0]
                shows = (f"From {p0.band} upwards the side batting first wins more often than not: {p0.win_pct:.0f}% "
                         f"({p0.won} of {p0.matches}) in that band.")
            else:
                shows = "No band with 3 or more matches has the side batting first winning half its games yet."
            big = table.iloc[-1]
            shows += f" The highest band, {big.band}, won {big.win_pct:.0f}% ({big.won} of {big.matches})."
            chart_note(shows, "Tells you what a winning score looks like here, so you know when you have enough and when "
                              "to keep pushing. Highest scores at the top; hover a bar for how many matches it rests "
                              "on (one or two matches is a small sample)."
                       + (" In multi-day cricket many matches are drawn, so the win % stays lower." if kind == "multi" else ""))

        # ---------------------------------------------------------------- 109 · par by opponent strength
        with safe_section("par by opponent"), st.container(border=True):
            pbs = I.par_by_strength(career, ids)
            st.markdown(f"**Is it enough against a good side?** · win % batting first by {what}, against the stronger "
                        "and the weaker half of the teams (ranked by win % here)")
            rows = [[r.band, f"{pct(r.stronger_pct)} ({r.stronger_n})" if r.stronger_n else "–",
                     f"{pct(r.weaker_pct)} ({r.weaker_n})" if r.weaker_n else "–"] for r in pbs.itertuples()]
            if rows:
                html_table(rows, [what[0].upper() + what[1:], "v stronger half", "v weaker half"], numeric={1, 2})
                sp = pbs[(pbs.stronger_n >= 3) & (pbs.stronger_pct >= 50)]
                wp = pbs[(pbs.weaker_n >= 3) & (pbs.weaker_pct >= 50)]
                st.caption((f"Against the stronger half you need about {int(sp.low.min())}+ to win more often than not"
                            if len(sp) else "Against the stronger half no band (3+ games) wins half its games yet")
                           + (f"; against the weaker half about {int(wp.low.min())}+." if len(wp) else ".")
                           + " Matches in brackets.")

# ---------------------------------------------------------------- 108 · chase calculator
with tab_chase:
    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
    state.recall("in_c_section", "section", list(sections.index))
    section_c = c1.selectbox("Section", list(sections.index), key="in_c_section", on_change=state.remember("in_c_section", "section"),
                             format_func=lambda s: counted(s, sections[s]))
    ids_c = Scope(sections=[section_c]).match_ids(m)
    kind_c = kind_of(m[m.match_id.isin(ids_c)])
    defaults = {"t20": (181, 60), "one": (281, 120), "multi": (250, 80)}[kind_c]
    target = c2.number_input("Target", 1, 1000, defaults[0], key=f"in_c_target_{kind_c}")
    score_c = c3.number_input("Score now", 0, 1000, defaults[1], key=f"in_c_score_{kind_c}")
    wk_c = c4.number_input("Wickets down", 0, 9, 3, key="in_c_wkts")
    with safe_section("chase calculator"):
        st_c = state.memo(WP.states, career, ids_c)
        if score_c >= target:
            st.success("That's the target reached: the chase is won.")
        else:
            ch = WP.chase_chance(st_c, kind_c, int(target), int(score_c), int(wk_c))
            need = target - score_c
            with st.container(border=True):
                if not ch["n"]:
                    st.caption("No games like this yet.")
                else:
                    if kind_c == "multi":
                        kpis([("Chasers win", pct(ch["win"])), ("Draw", pct(ch["draw"])), ("Defenders win", pct(ch["lose"]))])
                    else:
                        kpis([("Chasers win", pct(ch["win"])), ("Defenders win", pct(ch["lose"]))])
                    lo_w, hi_w = ch["wickets_used"]
                    wtxt = f"{lo_w} down" if lo_w == hi_w else f"{lo_w}-{hi_w} down"
                    st.markdown(f"Needing **{need}** with **{10 - wk_c} wickets** left: from {ch['n']} {section_c} "
                                f"chases in the same spot ({wtxt}, needing within {ch['band']:.0f} runs of {need}).")
                    rows = []
                    for w_ in sorted({max(0, wk_c - 1), wk_c, min(9, wk_c + 1)}):
                        c_ = WP.chase_chance(st_c, kind_c, int(target), int(score_c), w_)
                        rows.append([f"{w_} down", pct(c_["win"])] + ([pct(c_["draw"])] if kind_c == "multi" else []) +
                                    [c_["n"]])
                    html_table(rows, ["Wickets", "Chasers win"] + (["Draw"] if kind_c == "multi" else []) + ["Games"],
                               numeric={1, 2, 3})
                    st.caption("How much one wicket either way is worth. The scorecards have no overs, so this is runs "
                               "and wickets only: early in a chase it can't tell a quick start from a slow one."
                               + (" In a Test the draw depends on time left, which the scorecards don't show either."
                                  if kind_c == "multi" else ""))

# ---------------------------------------------------------------- home advantage
with tab_home:
    h = I.home_advantage(career)
    if h.empty:
        st.info("No home-and-away matches yet (ICC events are played at neutral venues).")
    else:
        h = h.assign(section=[f"{s} ({n})" for s, n in zip(h.section, h.matches)])
        with st.container(border=True):
            st.markdown("**Home wins against away wins, in every section** · finished matches at home grounds, "
                        "number of matches in brackets")
            fig = go.Figure([
                go.Bar(y=h.section, x=h.home_pct, name="Home side won", orientation="h", marker=dict(color=c["s1"]),
                       text=[f"{p:.0f}%" for p in h.home_pct], textposition="inside",
                       customdata=[f"{w} of {n}" for w, n in zip(h.home_wins, h.matches)],
                       hovertemplate="<b>%{y}</b><br>Home side won %{customdata} (%{text})<extra></extra>"),
                go.Bar(y=h.section, x=h.away_pct, name="Away side won", orientation="h", marker=dict(color=c["s2"]),
                       text=[f"{p:.0f}%" for p in h.away_pct], textposition="inside",
                       customdata=[f"{w} of {n}" for w, n in zip(h.away_wins, h.matches)],
                       hovertemplate="<b>%{y}</b><br>Away side won %{customdata} (%{text})<extra></extra>"),
                go.Bar(y=h.section, x=100 - h.home_pct - h.away_pct, name="Draw or tie", orientation="h",
                       marker=dict(color=c["dim"]), hovertemplate="<b>%{y}</b><br>Draw or tie: %{x:.0f}%<extra></extra>"),
            ])
            fig.update_layout(**_layout(c, barmode="stack", height=max(240, 44 * len(h) + 90), showlegend=True,
                                        legend=dict(orientation="h", y=1.08, x=0, font=dict(color=c["ink"]), traceorder="normal"),
                                        xaxis=_axis(c, "% of matches", range=[0, 100]),
                                        yaxis=dict(type="category", autorange="reversed", automargin=True,
                                                   tickfont=dict(size=12, color=c["ink"])),
                                        margin=dict(l=10, r=16, t=40, b=10)))
            st.plotly_chart(fig, width="stretch", config=CONFIG, key="in_h_bars")
            hi = h.sort_values("home_pct", ascending=False).iloc[0]
            lo = h.sort_values("home_pct").iloc[0]
            chart_note(f"Home sides win most in {hi.section}: {hi.home_pct:.0f}% against {hi.away_pct:.0f}% for away "
                       f"sides; least in {lo.section}: {lo.home_pct:.0f}% against {lo.away_pct:.0f}%.",
                       "Shows how much playing at home is worth in each competition, so you know how much to read into "
                       "a home or away result. The first-named team on a scorecard is the home side; World Cups and "
                       "other ICC events are left out because they're at neutral grounds.")

# ---------------------------------------------------------------- season by season
with tab_seasons:
    state.recall("in_s_section", "section", list(sections.index))
    section_s = st.selectbox("Section", list(sections.index), key="in_s_section", on_change=state.remember("in_s_section", "section"),
                             format_func=lambda s: counted(s, sections[s]))
    bs = I.by_season(career, section_s)
    if len(bs) < 2:
        st.info(f"Only one season of {section_s} so far. Come back after the next one to see how the game changes.")
    kind = kind_of(m[m.section == section_s])
    measures = [("Runs per wicket", "runs_per_wicket", 1), ("Run rate (runs per over)", "run_rate", 2),
                ("Sixes per match", "sixes_per_match", 1), ("Share of runs in boundaries (%)", "boundary_pct", 1),
                ("Average first-innings score", "first_innings_avg", 0),
                ("Win % batting first", "bat_first_win_pct", 0)]
    PURPOSE = {"runs_per_wicket": "Is batting getting easier or harder? More runs per wicket = a batter's game.",
               "run_rate": "How fast teams score, so you know what scoring rate keeps you in a game.",
               "sixes_per_match": "How much big hitting there is: more sixes usually means higher totals.",
               "boundary_pct": "How much of the scoring comes in fours and sixes rather than running.",
               "first_innings_avg": "The typical score batting first: a quick guide to par.",
               "bat_first_win_pct": "Whether batting first or chasing pays off more, season by season."}
    cols = st.columns(2, gap="medium")
    for i, (label, col, dec) in enumerate(measures):
        with cols[i % 2]:
            with st.container(border=True):
                st.markdown(f"**{label}**")
                fig = go.Figure(go.Scatter(x=[str(s) for s in bs.season], y=bs[col], mode="lines+markers+text",
                                           line=dict(color=c["s1"], width=2.5), marker=dict(size=9, color=c["s1"]),
                                           text=[fmt(v, dec) for v in bs[col]], textposition="top center",
                                           textfont=dict(size=11, color=c["ink2"]),
                                           customdata=[f"{n} matches" for n in bs.matches],
                                           hovertemplate="%{x}: %{text}<br>%{customdata}<extra></extra>"))
                top = float(np.nanmax(bs[col])) if bs[col].notna().any() else 1
                fig.update_layout(**_layout(c, height=260, xaxis=_axis(c, "Season", type="category"),
                                            yaxis=_axis(c, label, range=[0, top * 1.25 or 1]),
                                            margin=dict(l=10, r=16, t=16, b=10)))
                st.plotly_chart(fig, width="stretch", config=CONFIG, key=f"in_s_{col}")
                vals = bs[["season", col]].dropna()
                if len(vals) >= 2:
                    a0, a1 = vals.iloc[0], vals.iloc[-1]
                    ch = (a1[col] - a0[col]) / a0[col] * 100 if a0[col] else 0
                    shows = (f"{fmt(a0[col], dec)} in {a0.season}, {fmt(a1[col], dec)} in {a1.season} "
                             f"({ch:+.0f}%).")
                elif len(vals):
                    shows = f"{fmt(vals.iloc[0][col], dec)} in {vals.iloc[0].season}, the only season so far."
                else:
                    shows = "No figures yet."
                chart_note(shows, PURPOSE.get(col, "How this has changed from season to season."))

# ---------------------------------------------------------------- breakouts
with tab_break:
    c1, c2, c3 = st.columns([2, 1, 1])
    state.recall("in_b_section", "section", list(sections.index))
    section_b = c1.selectbox("Section", list(sections.index), key="in_b_section", on_change=state.remember("in_b_section", "section"),
                             format_func=lambda s: counted(s, sections[s]))
    seasons_b = sorted(m[m.section == section_b].season.unique(), reverse=True)
    state.recall("in_b_season", "season", seasons_b)
    season_b = c2.selectbox("Season", seasons_b, key="in_b_season", on_change=state.remember("in_b_season", "season"))
    earlier_b = any(s < season_b for s in seasons_b)
    min_inns = c3.selectbox("Minimum innings in both", [3, 5, 8, 10], index=1, key="in_b_min", disabled=not earlier_b,
                            help="Innings needed in this season and in the earlier ones." + (
                                "" if earlier_b else " Needs an earlier season of this competition to compare with."))
    bat, bowl = I.breakouts(career, section_b, season_b, min_inns)
    if bat.empty and bowl.empty and not any(s < season_b for s in seasons_b):
        st.info(f"{season_b} is the first season of {section_b} here, so there's nothing earlier to compare with.")
    else:
        left, right = st.columns(2, gap="medium")
        for box, d, title, unit in ((left, bat, "Batters", "runs above average per innings"),
                                    (right, bowl, "Bowlers", "runs saved per innings")):
            with box:
                with st.container(border=True):
                    st.markdown(f"**{title} who improved most** · {unit}, {season_b} against their earlier seasons")
                    top = d[d.jump > 0].head(10) if len(d) else d
                    if top.empty:
                        st.caption(f"Nobody with {min_inns}+ innings in both periods improved.")
                    else:
                        st.plotly_chart(bars(top.player, top.jump, f"Improvement ({unit})", 1, signed=True,
                                             notes=[f"{season_b}: {fmt(n, 1)} ({ni} inns) · before: {fmt(b, 1)} ({bi} inns)"
                                                    for n, ni, b, bi in zip(top.now, top.now_innings, top.before, top.before_innings)]),
                                        width="stretch", config=CONFIG, key=f"in_b_{title}")
                        r0 = top.iloc[0]
                        chart_note(f"{r0.player} improved most: {fmt(r0.now, 1)} {unit} in {season_b} against "
                                   f"{fmt(r0.before, 1)} before ({r0.jump:+.1f}).",
                                   f"Spots the {title.lower()} who have stepped up this season, so you can give them a "
                                   "bigger role (or sign them).")
        st.caption("Each season is measured against that season's own average, so a year when everyone scored more "
                   "doesn't make everyone look improved. Hover a bar for the before-and-after figures.")

# ---------------------------------------------------------------- 35, 36 · innings by innings
with tab_tests:
    multi_secs = [x for x in sections.index if kind_of(m[m.section == x]) == "multi"]
    if not multi_secs:
        st.info("No multi-day cricket (Tests or first-class) yet.")
    else:
        section_m = st.selectbox("Section", multi_secs, key="in_m_section",
                                 format_func=lambda s: counted(s, sections[s]))
        ids_m = Scope(sections=[section_m]).match_ids(m)
        ib = TP.innings_by_number(career, ids_m)
        with st.container(border=True):
            st.markdown("**Each innings of the match** · how much harder batting gets as the pitch wears")
            if ib.empty:
                st.caption("No innings yet.")
            else:
                first = ib.runs_per_wicket.iloc[0]
                st.plotly_chart(bars([f"{ordinal(n)} innings"
                                      for n in ib.innings], ib.runs_per_wicket, "Runs per wicket", 1,
                                     texts=[f"{v:.1f} ({(v - first) / first * 100:+.0f}% v the 1st)" if i else f"{v:.1f}"
                                            for i, v in enumerate(ib.runs_per_wicket)],
                                     notes=[f"{n} innings · average total {t:.0f} · run rate {r:.2f} · all out {a:.0f}%"
                                            for n, t, r, a in zip(ib.innings_played, ib.average_total, ib.run_rate,
                                                                  ib.all_out_pct)]),
                                width="stretch", config=CONFIG, key="in_m_bars")
                last_ = ib.iloc[-1]
                chart_note(f"The {ordinal(last_.innings)} "
                           f"innings averages {last_.runs_per_wicket:.1f} runs per wicket against {first:.1f} in the 1st "
                           f"({(last_.runs_per_wicket - first) / first * 100:+.0f}%).",
                           "Shows how much harder batting gets as the pitch wears, which tells you how big a "
                           "fourth-innings target really is and whether to bat first.")
        fl = WP.first_innings_lead(career, ids_m)
        with st.container(border=True):
            st.markdown("**First-innings lead** · what happened to the side that led after the first innings")
            if fl.matches.sum() == 0:
                st.caption("No finished games yet.")
            else:
                html_table([[r.band, r.matches, pct(r.won), pct(r.drawn), pct(r.lost)] for r in fl.itertuples() if r.matches],
                           ["Lead", "Games", "Won", "Drawn", "Lost"], numeric={1, 2, 3, 4})
                big = fl[(fl.matches >= 3)].sort_values("won", ascending=False).head(1)
                if len(big):
                    st.caption(f"A lead of {big.band.iloc[0]} won {big.won.iloc[0]:.0f}% of {int(big.matches.iloc[0])} "
                               "games. Bigger leads also mean fewer draws, because the side behind has to bat twice to "
                               "catch up.")
        fo = TP.follow_on_and_declarations(career, ids_m)
        with st.container(border=True):
            st.markdown("**Follow-on and declarations** · how often each led to a win")
            if fo.empty:
                st.caption("No follow-ons or declarations yet.")
            else:
                html_table([[r.situation, r.times, f"{r.won}–{r.drawn}–{r.lost}", f"{pct(r.win_pct)}"]
                            for r in fo.itertuples()], ["", "Times", "Won–drawn–lost", "Win %"], numeric={1, 3})
                st.caption("A follow-on is spotted when the side batting second batted again straight away. Won-drawn-lost "
                           "is from the point of view of the side in that row.")
