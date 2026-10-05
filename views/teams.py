import numpy as np
import pandas as pd
import streamlit as st

from ccstats import analysis as A
from ccstats import extras as E
from ccstats import teamplay as TP
from ui.theme import colours
from ccstats.stats import Scope
from ui import state
from ui.charts import CONFIG, bars, fmt, race_chart, say
from ui.theme import explain_list, html_table, kpis, page_header, safe_section

career = state.current()
if career is None:
    st.info("Load a career on the Home page first.")
    st.stop()

m = career.matches
page_header("Teams", "Team record", "Pick a section and a team. Every comparison is against the average of all the teams in that section.")
c1, c2, c3, c4 = st.columns([1.9, 1, 1.5, 1.7])
sections = m.section.value_counts()
section = c1.selectbox("Section", list(sections.index), key="tm_section", format_func=lambda s: f"{s} · {sections[s]} matches")
seasons = sorted(m[m.section == section].season.unique(), reverse=True)
season = c2.selectbox("Season", ["All seasons"] + seasons, key="tm_season")
scope = Scope(sections=[section], seasons=[] if season == "All seasons" else [season])
ids = scope.match_ids(m)
here = m[m.match_id.isin(ids)]
teams = sorted(set(here.home) | set(here.away))
team = c3.selectbox("Team", teams, key="tm_team")
venue_label = c4.segmented_control("Venue", ["Overall", "Home", "Away"], default="Overall", key="tm_venue") or "Overall"
venue = venue_label.lower().replace("overall", "all")

table = A.team_table(career, ids, venue)
if team not in set(table.team):
    if venue != "all" and here.neutral.all():
        st.info(f"{section} matches are played at neutral venues, so there are no home or away games. Choose Overall.")
    else:
        st.info(f"{team} have no {venue_label.lower()} matches here.")
    st.stop()
me = table.set_index("team").loc[team]
limited = np.isfinite(me.nrr)

tm = A.team_matches(career, ids, team)
if venue != "all":
    tm = tm[tm.venue == venue]
sk = A.streaks(list(tm.outcome))
cur = sk["current"]
kpis([("Played", f"{int(me.played)}"), ("Won–Lost", f"{int(me.won)}–{int(me.lost)}"), ("Win %", f"{me.win_pct:.0f}%")]
     + ([("Net run rate", f"{me.nrr:+.2f}")] if limited else [("Drawn", f"{int(me.drawn)}")])
     + [("Current run", f"{cur[1]} {dict(W='won', L='lost', D='drawn', T='tied', NR='no result').get(cur[0], '')}" if cur[0] else "–"),
        ("Last 5", f"<span class='small'>{' '.join(sk['last5'])}</span>" if sk["last5"] else "–")])  # fits the tile
st.caption(f"Longest winning run: {sk['longest_win']} · longest losing run: {sk['longest_loss']}")

tab_over, tab_win, tab_opp, tab_season, tab_series, tab_res = st.tabs(
    ["Overview", "How they win", "Opponents and stages", "Season", "Series and Tests", "Results"])
with tab_over:
    keep = A.keepers(career, ids, team)
    if len(keep):
        st.markdown("🧤 **Wicketkeeper" + ("s" if len(keep) > 1 else "") + ":** " +
                    ", ".join(f"{p} ({n} stumping{'s' * (n != 1)})" for p, n in zip(keep.player, keep.stumpings)))
        st.caption("The scorecards don't mark the keeper, so anyone who has made a stumping for this team is flagged as one.")

    # ---------------------------------------------------------------- against the average team
    avg = table.mean(numeric_only=True)
    measures = [("Win %", "win_pct", "high"), ("Runs per wicket (batting)", "rpw_for", "high"),
                ("Run rate (batting)", "rr_for", "high"), ("Avg score batting first", "first_innings_avg", "high"),
                ("Runs per wicket conceded", "rpw_against", "low"), ("Economy (bowling)", "rr_against", "low"),
                ("Wickets taken per match", "wkts_per_match", "high")]
    labels, diffs, notes, texts, rows = [], [], [], [], []
    dec = {"win_pct": 0, "first_innings_avg": 0}
    for label, col, better in measures:
        v, a = me[col], avg[col]
        if not (np.isfinite(v) and np.isfinite(a)) or a == 0:
            continue
        d = (v - a) / abs(a) * 100 * (1 if better == "high" else -1)
        labels.append(label)
        diffs.append(d)
        vt, at = fmt(v, dec.get(col, 1)), fmt(a, dec.get(col, 1))
        texts.append(f"{d:+.0f}% · {vt} v {at}")
        notes.append(f"{team}: {vt} · average team: {at}" + ("" if better == "high" else " · lower is better"))
        rows.append((label, d, vt, at, better))
    with st.container(border=True):
        st.markdown(f"**{team} against the average team in {section}** · % better (blue) or worse (red) than the average of all {len(table)} teams")
        st.plotly_chart(bars(labels, diffs, "% better than the average team", 0, notes=notes, signed=True, texts=texts),
                        width="stretch", config=CONFIG, key="tm_vsavg")
        # explain the numbers with this team's own figures
        ex = []
        good = max(rows, key=lambda r: r[1]) if rows else None
        bad = min(rows, key=lambda r: r[1]) if rows else None
        for r in [x for x in (good, bad) if x is not None and (x is good or x[1] < 0)]:
            label, d, vt, at, better = r
            word = ("better" if d >= 0 else "worse")
            how = ("higher" if (d >= 0) == (better == "high") else "lower")
            ex.append(("", f"<b>{d:+.0f}% on {label.lower()}</b>: {team} {vt}, the average team {at}. {team} are {abs(d):.0f}% "
                           f"{how}, which is {word}" + ("" if better == "high" else " because lower is better here") + "."))
        ex.append(("", "<b>The number on each bar</b> is how much better (+, blue) or worse (−, red) this team is than the "
                       f"average of all {len(table)} teams, then the team's figure v the average team's."))
        ex.append(("", "<b>Runs per wicket conceded and economy</b>: lower is better, so conceding less than average is a "
                       "plus and shows blue."))
        explain_list(ex)

    left, right = st.columns(2, gap="medium")
    bat_t, bowl_t, _, _ = state.tables(career, scope, by_team=True)
    my_bat = bat_t[bat_t.team == team].sort_values("runs", ascending=False).head(6)
    my_bowl = bowl_t[(bowl_t.team == team) & (bowl_t.wickets > 0)].sort_values(["wickets", "average"], ascending=[False, True]).head(6)
    my_bat = my_bat[my_bat.runs > 0]
    with left:
        with st.container(border=True):
            st.markdown("**Top run-scorers**")
            st.plotly_chart(bars(my_bat.player, my_bat.runs, "Runs", notes=[f"average {fmt(a, 1)} · strike rate {fmt(s, 1)}" for a, s in zip(my_bat.average, my_bat.strike_rate)]),
                            width="stretch", config=CONFIG, key="tm_topbat")
    with right:
        with st.container(border=True):
            st.markdown("**Top wicket-takers**")
            st.plotly_chart(bars(my_bowl.player, my_bowl.wickets, "Wickets", notes=[f"average {fmt(a, 1)} · economy {fmt(e, 2)}" for a, e in zip(my_bowl.average, my_bowl.economy)]),
                            width="stretch", config=CONFIG, key="tm_topbowl")

    left, right = st.columns(2, gap="medium")
    with left:
        with st.container(border=True):
            st.markdown("**Batting depth** · share of the team's runs")
            dep = A.batting_depth(career, tm.match_id, team)
            all_dep = pd.concat([A.batting_depth(career, ids, t).assign(team=t) for t in teams])
            ref = all_dep.groupby("group", sort=False).share.mean()
            st.plotly_chart(bars(dep.group, dep.share, "% of runs", 0, notes=[f"{r} runs · average team {ref.get(g, 0):.0f}%" for g, r in zip(dep.group, dep.runs)]),
                            width="stretch", config=CONFIG, key="tm_depth")
    with right:
        with st.container(border=True):
            st.markdown("**Average partnership for each wicket**")
            pw = A.partnership_by_wicket(career, tm.match_id, team)
            st.plotly_chart(bars([f"{int(w)}{'st' if w == 1 else 'nd' if w == 2 else 'rd' if w == 3 else 'th'} wicket" for w in pw.wicket],
                                 pw.average, "Average stand (runs)", 1, notes=[f"{n} stands · best {b}" for n, b in zip(pw.stands, pw.best)]),
                            width="stretch", config=CONFIG, key="tm_pship")

    left, right = st.columns(2, gap="medium")
    with left:
        with st.container(border=True):
            st.markdown("**Opening pairs** · the two players who opened, and their stands")
            op = A.opening_partnerships(career, tm.match_id, team)
            if op.empty:
                st.caption("No innings yet.")
            else:
                g = op.groupby("pair").agg(stands=("runs", "size"), runs=("runs", "sum"), average=("runs", "mean"),
                                           best=("runs", "max")).sort_values("runs", ascending=False).reset_index()
                st.dataframe(g.rename(columns={"pair": "Openers", "stands": "Innings", "runs": "Runs", "average": "Average", "best": "Best"}),
                             hide_index=True, width="stretch", column_config={"Average": st.column_config.NumberColumn(format="%.1f")})
    with right:
        with st.container(border=True):
            st.markdown("**Collapses** · 4 or more wickets lost for 30 runs or fewer")
            col = A.collapses(career, tm.match_id, team)
            if col.empty:
                st.caption("No collapses. Nice.")
            else:
                st.dataframe(pd.DataFrame({"Date": col.date.dt.strftime("%d %b %y"),
                                           "Against": [a if h == team else h for h, a in zip(col.home, col.away)],
                                           "Slide": [f"{f} → {t}" for f, t in zip(col.from_score, col.to_score)],
                                           "Lost": [f"{w} for {r}" for w, r in zip(col.wickets, col.runs)],
                                           "Total": col.total}), hide_index=True, width="stretch",
                             column_config={"Date": st.column_config.TextColumn(width=80),
                                            "Against": st.column_config.TextColumn(width=115),
                                            "Slide": st.column_config.TextColumn(width=120),
                                            "Lost": st.column_config.TextColumn(width=70),
                                            "Total": st.column_config.TextColumn(width=60)})

    # ---------------------------------------------------------------- team style
    style = E.team_style(career, ids)
    if team in set(style.team):
        s_me = style.set_index("team").loc[team]
        s_avg = style.mean(numeric_only=True)
        labels, diffs, texts = [], [], []
        for label, col, higher in E.STYLE:
            v, a = s_me[col], s_avg[col]
            if not (np.isfinite(v) and np.isfinite(a)) or a == 0:
                continue
            labels.append(label)
            diffs.append((v - a) / abs(a) * 100)
            texts.append(f"{(v - a) / abs(a) * 100:+.0f}% · {fmt(v, 1)} v {fmt(a, 1)}")
        left, right = st.columns([1.3, 1], gap="medium")
        with left:
            with st.container(border=True):
                st.markdown(f"**How {team} play** · more (right) or less (left) than the average team, not better or worse")
                st.plotly_chart(bars(labels, diffs, "% more or less than the average team", 0, texts=texts,
                                     colour=colours()["s2"], x_range=[min(min(diffs), 0) - (max(diffs) - min(min(diffs), 0)) * 1.1 - 8,
                                                                      max(max(diffs), 0) + (max(max(diffs), 0) - min(diffs)) * 0.9 + 8]),
                                width="stretch", config=CONFIG, key="tm_style")
                st.caption("This is style, not quality: a team can win either way. Each bar compares this team's figure "
                           "with the average of all teams in the section.")
        # ---------------------------------------------------------------- discipline (extras)
        disc = E.discipline(career, ids)
        with right:
            with st.container(border=True):
                st.markdown("**Discipline** · extras given away per match (fewest first)")
                d = disc.head(12)
                st.plotly_chart(bars([t + ("  ◀" if t == team else "") for t in d.team], d.extras_per_match, "Extras per match", 1,
                                     notes=[f"wides {fmt(w, 1)} · no-balls {fmt(n, 1)} · byes {fmt(b, 1)} · leg byes {fmt(lb, 1)} per match"
                                            for w, n, b, lb in zip(d.wides_per_match, d.no_balls_per_match, d.byes_per_match,
                                                                   d.leg_byes_per_match)]),
                                width="stretch", config=CONFIG, key="tm_disc")
                if team in set(disc.team):
                    r = disc.set_index("team").loc[team]
                    st.caption(f"{team}: {fmt(r.extras_per_match, 1)} extras a match ({fmt(r.wides_per_match, 1)} wides, "
                               f"{fmt(r.no_balls_per_match, 1)} no-balls), {int(list(disc.team).index(team)) + 1} of {len(disc)} "
                               f"for discipline. Section average {fmt(disc.extras_per_match.mean(), 1)}.")

    with st.container(border=True):
        st.markdown(f"**Every team in {section}**" + ("" if venue == "all" else f" · {venue_label.lower()} games only"))
        show = table.sort_values(["win_pct", "nrr" if limited else "rpw_for"], ascending=False)
        cols = {"team": "Team", "played": "P", "won": "W", "lost": "L", "drawn": "D", "tied": "T", "win_pct": "Win %",
                "rpw_for": "Runs/wkt", "rpw_against": "Conceded/wkt", "rr_for": "Run rate", "rr_against": "Economy"}
        if limited:
            cols["nrr"] = "NRR"
        st.dataframe(show[list(cols)].rename(columns=cols), hide_index=True, width="stretch", column_config={
            c: st.column_config.NumberColumn(format="%.2f") for c in ("Runs/wkt", "Conceded/wkt", "Run rate", "Economy", "NRR")}
            | {"Win %": st.column_config.NumberColumn(format="%.0f")})

games_all = state.memo(TP.games, career, ids)
mine_g = games_all[games_all.team == team]
multi = TP.is_multi(games_all)
second = "Batting second" if multi else "Chasing"

with tab_res:
    with st.container(border=True):
        st.markdown("**Results**")
        res = tm.sort_values("date", ascending=False)
        bf = mine_g.set_index("match_id").batted_first
        table_res = pd.DataFrame({"Date": res.date.dt.strftime("%d %b %Y"), "Opponent": res.opponent,
                                  "Venue": res.venue.map(say), "Stage": res.stage,
                                  "Batted": ["Batted first" if bf.get(x, False) else second for x in res.match_id],
                                  "Result": res.result, "": res.outcome})
        if not res.stage.astype(bool).any():
            table_res = table_res.drop(columns="Stage")
        st.dataframe(table_res, hide_index=True, width="stretch")

# ---------------------------------------------------------------- 1, 2, 3, 23 · how they win
with tab_win:
    with safe_section("batting first or chasing"):
        bft, avg_bf = state.memo(TP.bat_first_table, career, ids)
        me_bf = bft.set_index("team").loc[team] if team in set(bft.team) else None
        with st.container(border=True):
            st.markdown(f"**Batting first or {second.lower()}** · {team} against every team in {section}")
            if me_bf is None:
                st.caption("No games yet.")
            else:
                a1, a2 = avg_bf["first"], avg_bf["second"]
                rows = [["Batting first", f"{int(me_bf.bf_played)}",
                         TP.wdl(dict(won=int(me_bf.bf_won), lost=int(me_bf.bf_lost), drawn=int(me_bf.bf_drawn),
                                     tied=int(me_bf.bf_tied), no_result=int(me_bf.bf_no_result))),
                         f"{fmt(me_bf.bf_win_pct, 0)}%", f"{fmt(a1['win_pct'], 0)}%"],
                        [second, f"{int(me_bf.ch_played)}",
                         TP.wdl(dict(won=int(me_bf.ch_won), lost=int(me_bf.ch_lost), drawn=int(me_bf.ch_drawn),
                                     tied=int(me_bf.ch_tied), no_result=int(me_bf.ch_no_result))),
                         f"{fmt(me_bf.ch_win_pct, 0)}%", f"{fmt(a2['win_pct'], 0)}%"]]
                html_table(rows, ["", "Played", "W–D–L" if multi else "W–L", f"{team} win %", "Every team"],
                           numeric={1, 3, 4})
                better = "batting first" if (me_bf.bf_win_pct or 0) >= (me_bf.ch_win_pct or 0) else second.lower()
                st.caption(f"{team} win more often {better}. 'Every team' is how often the side batting first (or "
                           f"second) wins in {section}." + (" Win % here counts draws as games not won." if multi else
                                                            " Ties and no-results are left out of win %."))
    left, right = st.columns(2, gap="medium")
    with left, safe_section("close games"):
        cg = state.memo(TP.close_games, career, ids, team)
        with st.container(border=True):
            st.markdown("**Close games** · won or lost by under 10 runs or by 1-2 wickets, or tied")
            html_table([["Close games", TP.wdl(cg["close"]), f"{fmt(cg['close']['win_pct'], 0)}%"],
                        ["Other games", TP.wdl(cg["other"]), f"{fmt(cg['other']['win_pct'], 0)}%"]],
                       ["", "Record", "Win %"], numeric={2})
            if len(cg["rows"]):
                rows = [[f"{r.date:%d %b %Y}", r.opponent, {"W": "Won", "L": "Lost", "T": "Tied"}.get(r.outcome, r.outcome),
                         (f"{int(r.margin_runs)} runs" if pd.notna(r.margin_runs) else
                          f"{int(r.margin_wickets)} wkts" if pd.notna(r.margin_wickets) else "tie")]
                        for r in cg["rows"].sort_values("date", ascending=False).head(8).itertuples()]
                html_table(rows, ["Date", "Opponent", "", "Margin"])
    with right, safe_section("openers' start"):
        ss = state.memo(TP.start_split, career, ids, team)
        sa = state.memo(TP.start_split, career, ids, "")
        with st.container(border=True):
            st.markdown("**The openers' start** · result when the first wicket fell…")
            rows = [[label, TP.wdl(ss[k]), f"{fmt(ss[k]['win_pct'], 0)}%", f"{fmt(sa[k]['win_pct'], 0)}%"]
                    for k, label in (("good", "at 50 or more"), ("middle", "between 20 and 49"), ("bad", "under 20"))]
            html_table(rows, ["First wicket fell", "Record", f"{team} win %", "Every team"], numeric={2, 3})
            st.caption("Their first innings of each game. A good start is worth this much to them.")
    with safe_section("targets"):
        tb = state.memo(TP.target_buckets, career, ids, team)
        ta = state.memo(TP.target_buckets, career, ids, "")
        with st.container(border=True):
            label = "fourth-innings target" if multi else "first-innings total"
            st.markdown(f"**Chasing and defending by the size of the {label}**")
            if tb.empty:
                st.caption("No games yet.")
            else:
                rows = []
                for r, a_ in zip(tb.itertuples(), ta.itertuples()):
                    if not (r.chase_played or r.defend_played):
                        continue
                    rows.append([r.bucket, f"{r.chase_won}/{r.chase_played}" if r.chase_played else "–",
                                 f"{fmt(r.chase_pct, 0)}%" if r.chase_played else "–", f"{fmt(a_.chase_pct, 0)}%",
                                 f"{r.defend_won}/{r.defend_played}" if r.defend_played else "–",
                                 f"{fmt(r.defend_pct, 0)}%" if r.defend_played else "–", f"{fmt(a_.defend_pct, 0)}%"])
                html_table(rows, ["Target" if multi else "Total", "Chased (won/played)", "Win %", "Every team",
                                  "Defended (won/played)", "Win %", "Every team"], numeric={2, 3, 5, 6})
                st.caption("Chasing: batting last. Defending: setting the target. 'Every team' is the same for all sides "
                           f"in {section}.")

# ---------------------------------------------------------------- 5, 6, 30, 31 · opponents and stages
with tab_opp:
    left, right = st.columns(2, gap="medium")
    with left, safe_section("league and knockouts"):
        sr = state.memo(TP.stage_record, career, ids, team)
        with st.container(border=True):
            st.markdown("**League games and knockouts**")
            rows = [[r.stage, r.played, TP.wdl(r._asdict()), f"{fmt(r.win_pct, 0)}%"] for r in sr.itertuples() if r.played]
            html_table(rows, ["", "Played", "Record", "Win %"], numeric={1, 3})
    with right, safe_section("bounce back"):
        ar = state.memo(TP.after_result, career, ids, team)
        with st.container(border=True):
            st.markdown("**Bouncing back** · their next game after…")
            rows = [[r.after, r.played, TP.wdl(r._asdict()), f"{fmt(r.win_pct, 0)}%"] for r in ar.itertuples()]
            if rows:
                html_table(rows, ["", "Games", "Record", "Win %"], numeric={1, 3})
            else:
                st.caption("Not enough games yet.")
    with safe_section("opponents"):
        op = state.memo(TP.opponents, career, ids, team)
        with st.container(border=True):
            st.markdown("**Every opponent** · ⭐ favourite and 👻 bogey team (met at least twice)")
            rows = [[("⭐ " if r.favourite else "👻 " if r.bogey else "") + r.opponent, r.played, TP.wdl(r._asdict()),
                     f"{fmt(r.win_pct, 0)}%", f"{r.last:%d %b %Y}"] for r in op.itertuples()]
            html_table(rows, ["Opponent", "Played", "Record", "Win %", "Last met"], numeric={1, 3},
                       row_class=["hi" if r.favourite or r.bogey else "" for r in op.itertuples()])
    with safe_section("revenge"):
        rv = state.memo(TP.revenge, career, ids, team)
        with st.container(border=True):
            st.markdown("**Revenge games** · against a side that beat them the last time they met")
            html_table([["Revenge games", TP.wdl(rv["revenge"]), f"{fmt(rv['revenge']['win_pct'], 0)}%"],
                        ["Every other game", TP.wdl(rv["other"]), f"{fmt(rv['other']['win_pct'], 0)}%"]],
                       ["", "Record", "Win %"], numeric={2})

# ---------------------------------------------------------------- 7, 29 · season
with tab_season:
    with safe_section("league race"):
        evs = here[~here.knockout & (here.home.eq(team) | here.away.eq(team))]
        options = sorted({(e, s_) for e, s_ in zip(evs.event, evs.season)}, key=lambda x: (x[1], x[0]), reverse=True)
        options = [o for o in options if o[0] not in ("ODIs (bilateral series)", "T20Is (bilateral series)",
                                                      "Tests (bilateral series)")]
        with st.container(border=True):
            st.markdown("**The league race** · position after each match day")
            if not options:
                st.caption("No league games here (bilateral series have no league table).")
            else:
                ev = st.selectbox("Competition and season", options, format_func=lambda o: f"{o[0]} {o[1]}", key="tm_race")
                race_ids = m[(m.event == ev[0]) & (m.season == ev[1])].match_id
                race = state.memo(TP.position_race, career, race_ids)
                grp = race[race.team == team].group.iloc[-1] if (race.team == team).any() else None
                if grp is None:
                    st.caption("No table for this one.")
                else:
                    race = race[race.group == grp]
                    st.plotly_chart(race_chart(race, team), width="stretch", config=CONFIG, key="tm_race_chart")
                    st.caption(f"{grp}: the same order as the league table (points, then net run rate). Hover a line for points.")
    with safe_section("early and late season"):
        sh = state.memo(TP.season_halves, career, ids, team)
        with st.container(border=True):
            st.markdown("**Early or late starters** · league games in the first and second half of each season")
            if sh.empty:
                st.caption("No league games yet.")
            else:
                rows = [[r.season, TP.wdl(r.early), f"{fmt(r.early['win_pct'], 0)}%", TP.wdl(r.late),
                         f"{fmt(r.late['win_pct'], 0)}%"] for r in sh.itertuples()]
                html_table(rows, ["Season", "First half", "Win %", "Second half", "Win %"], numeric={2, 4},
                           row_class=[""] * (len(rows) - 1) + ["hi"])

# ---------------------------------------------------------------- 32-36 · series and Tests
with tab_series:
    has_series = (here.series_id != "").any()
    if has_series:
        left, right = st.columns(2, gap="medium")
        with left, safe_section("first blood"):
            fb = state.memo(TP.first_blood, career, ids, team)
            fa = state.memo(TP.first_blood, career, ids, "")
            with st.container(border=True):
                st.markdown("**First blood** · how their series went after the first match")
                if fb.empty:
                    st.caption("No finished series yet.")
                else:
                    every = fa.set_index("start").win_pct
                    rows = [[r.start, r.series, f"{r.won}–{r.drawn}–{r.lost}", f"{fmt(r.win_pct, 0)}%",
                             f"{fmt(every.get(r.start, np.nan), 0)}%"] for r in fb.itertuples()]
                    html_table(rows, ["", "Series", "Won–drawn–lost", "Series won", "Every team"], numeric={1, 3, 4})
        with right, safe_section("deciders and dead rubbers"):
            si = state.memo(TP.situations, career, ids, team)
            with st.container(border=True):
                st.markdown("**Deciders and dead rubbers**")
                rows = [[r.situation, r.played, TP.wdl(r._asdict()), f"{fmt(r.win_pct, 0)}%"] for r in si.itertuples() if r.played]
                if rows:
                    html_table(rows, ["", "Games", "Record", "Win %"], numeric={1, 3})
                else:
                    st.caption("No series games yet.")
                st.caption("Decider: the last game with the series level. Dead rubber: the series was already won.")
    if multi:
        with safe_section("follow-on and declarations"):
            fo = state.memo(TP.follow_on_and_declarations, career, ids, team)
            with st.container(border=True):
                st.markdown("**Follow-on and declarations** · what happened next")
                if fo.empty:
                    st.caption("No follow-ons or declarations yet.")
                else:
                    html_table([[r.situation, r.times, f"{r.won}–{r.drawn}–{r.lost}", f"{fmt(r.win_pct, 0)}%"]
                                for r in fo.itertuples()], ["", "Times", "Won–drawn–lost", "Win %"], numeric={1, 3})
    if not has_series and not multi:
        st.info("Bilateral series and multi-day games only: this section has neither.")
