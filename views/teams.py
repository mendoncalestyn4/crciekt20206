import numpy as np
import pandas as pd
import streamlit as st

from ccstats import analysis as A
from ccstats import extras as E
from ccstats import teamdeep as TD
from ccstats import teamplay as TP
from ccstats import winprob as WP
from ui.theme import colours
from ccstats.stats import Scope, bars_for, kind_of
from ui import state
from ui.xi import best_xi_cached, team_sheet
from ui.charts import _n, ordinal, signed, pct, CONFIG, bars, fmt, race_chart, say
from ui.theme import chart_note, html_table, kpis, match_link, page_header, player_link, safe_section

career = state.current()
if career is None:
    st.info("Load a career on the Home page first.")
    st.stop()

m = career.matches
page_header("Teams", "Team record", "Pick a section and a team. Every comparison is against the average of all the teams in that section.")
c1, c2, c3, c4 = st.columns([1.9, 1, 1.5, 1.7])
sections = m.section.value_counts()
state.recall("tm_section", "section", list(sections.index))
section = c1.selectbox("Section", list(sections.index), key="tm_section", on_change=state.remember("tm_section", "section"), format_func=lambda s: f"{s} · {sections[s]} matches")
seasons = sorted(m[m.section == section].season.unique(), reverse=True)
state.recall("tm_season", "season", ["All seasons"] + seasons)
season = c2.selectbox("Season", ["All seasons"] + seasons, key="tm_season", on_change=state.remember("tm_season", "season"))
scope = Scope(sections=[section], seasons=[] if season == "All seasons" else [season])
ids = scope.match_ids(m)
here = m[m.match_id.isin(ids)]
base_kind = kind_of(here)  # t20 / one / multi: the bars for close games, good starts and so on
teams = sorted(set(here.home) | set(here.away))
state.recall("tm_team", "team", teams)
team = c3.selectbox("Team", teams, key="tm_team", on_change=state.remember("tm_team", "team"))
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
# ---------------------------------------------------------------- 99 · batting and bowling ratings
with safe_section("ratings"):
    ur = state.memo(TD.unit_ratings, career, ids)
    if team in set(ur.team):
        u = ur.set_index("team").loc[team]
        st.markdown(f"**Batting rating {u.batting:.0f}** ({ordinal(u.batting_rank)} of {len(ur)}) · **Bowling rating "
                    f"{u.bowling:.0f}** ({ordinal(u.bowling_rank)} of {len(ur)}) · 1000 = average, recent games count most. "
                    + ("The weaker half needs the work." if abs(u.batting - u.bowling) >= 50 else "Well balanced."))

tab_over, tab_win, tab_opp, tab_season, tab_series, tab_squad, tab_res = st.tabs(
    ["Overview", "How they win", "Opponents and stages", "Season", "Series and Tests", "Squad", "Results"])
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
        parts = []
        good = max(rows, key=lambda r: r[1]) if rows else None
        bad = min(rows, key=lambda r: r[1]) if rows else None
        for r in [x for x in (good, bad) if x is not None and (x is good or x[1] < 0)]:
            label, d, vt, at, better = r
            word = ("better" if d >= 0 else "worse")
            parts.append(f"<b>{abs(d):.0f}% {word}</b> than the average team on {label.lower()} ({team} {vt}, average "
                         f"team {at}" + ("" if better == "high" else "; lower is better here") + ")")
        chart_note(f"{team} are " + ", and ".join(parts) + "." if parts else "Not enough games yet.",
                   f"Shows at a glance where {team} are strong and weak against the other {len(table) - 1} teams. Each "
                   "bar is how much better (+, blue) or worse (−, red) they are than the average team; for runs "
                   "conceded and economy lower is better, so conceding less shows blue.")

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
            if len(my_bat):
                team_runs = bat_t[bat_t.team == team].runs.sum()
                chart_note(f"{my_bat.player.iloc[0]} has {my_bat.runs.iloc[0]} runs, {my_bat.runs.iloc[0] / team_runs * 100:.0f}% "
                           f"of {team}'s {team_runs} runs; the top {len(my_bat)} together make "
                           f"{my_bat.runs.sum() / team_runs * 100:.0f}%.",
                           "Who carries the batting, and how much the team leans on its top run-scorers.")
    with right:
        with st.container(border=True):
            st.markdown("**Top wicket-takers**")
            st.plotly_chart(bars(my_bowl.player, my_bowl.wickets, "Wickets", notes=[f"average {fmt(a, 1)} · economy {fmt(e, 2)}" for a, e in zip(my_bowl.average, my_bowl.economy)]),
                            width="stretch", config=CONFIG, key="tm_topbowl")
            if len(my_bowl):
                team_w = bowl_t[bowl_t.team == team].wickets.sum()
                chart_note(f"{my_bowl.player.iloc[0]} has {int(my_bowl.wickets.iloc[0])} wickets, "
                           f"{my_bowl.wickets.iloc[0] / team_w * 100:.0f}% of {team}'s {int(team_w)}; the top "
                           f"{len(my_bowl)} take {my_bowl.wickets.sum() / team_w * 100:.0f}%.",
                           "Who takes the wickets, and whether the attack is spread or rests on one or two bowlers.")

    left, right = st.columns(2, gap="medium")
    with left:
        with st.container(border=True):
            st.markdown("**Batting depth** · share of the team's runs")
            dep = A.batting_depth(career, tm.match_id, team)
            all_dep = pd.concat([A.batting_depth(career, ids, t).assign(team=t) for t in teams])
            ref = all_dep.groupby("group", sort=False).share.mean()
            st.plotly_chart(bars(dep.group, dep.share, "% of runs", 0, notes=[f"{r} runs · average team {ref.get(g, 0):.0f}%" for g, r in zip(dep.group, dep.runs)]),
                            width="stretch", config=CONFIG, key="tm_depth")
            if len(dep) and dep.runs.sum():
                top_g = dep.sort_values("share", ascending=False).iloc[0]
                chart_note(f"{top_g.share:.0f}% of {team}'s runs come from the {top_g.group.lower()} (the average team: "
                           f"{ref.get(top_g.group, 0):.0f}%). The tail (8-11) makes {dep.share.iloc[-1]:.0f}%.",
                           "Shows how deep the batting goes: if the top order makes most of the runs, early wickets hurt "
                           "this team more than most.")
    with right:
        with st.container(border=True):
            st.markdown("**Average partnership for each wicket**")
            pw = A.partnership_by_wicket(career, tm.match_id, team)
            st.plotly_chart(bars([f"{ordinal(w)} wicket" for w in pw.wicket],
                                 pw.average, "Average stand (runs)", 1, notes=[f"{n} stands · best {b}" for n, b in zip(pw.stands, pw.best)]),
                            width="stretch", config=CONFIG, key="tm_pship")
            if len(pw):
                b_ = pw.sort_values("average", ascending=False).iloc[0]
                n_ = int(b_.wicket)
                chart_note(f"Their best stand is for the {ordinal(n_)} "
                           f"wicket: {b_.average:.1f} runs on average over {int(b_.stands)} stands (best {int(b_.best)}). "
                           f"The opening stand averages {pw.average.iloc[0]:.1f}.",
                           "Shows which partnerships hold the innings together and where it tends to fall apart.")

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
                i_max = int(np.argmax(np.abs(diffs))) if diffs else 0
                chart_note((f"{team}'s biggest difference is {labels[i_max].lower()}: {diffs[i_max]:+.0f}% against "
                            "the average team.") if diffs else "Not enough games yet.",
                           "Shows how they play, not how well: a team can win either way. Each bar compares this "
                           "team's figure with the average of all teams in the section.")
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
                    avg_x = disc.extras_per_match.mean()
                    chart_note(f"{team} give away {fmt(r.extras_per_match, 1)} extras a match ({fmt(r.wides_per_match, 1)} "
                               f"wides, {fmt(r.no_balls_per_match, 1)} no-balls), "
                               f"{(r.extras_per_match - avg_x) / avg_x * 100:+.0f}% against the average of {fmt(avg_x, 1)}: "
                               f"{int(list(disc.team).index(team)) + 1} of {len(disc)} for discipline.",
                               "Free runs given away. A few extras a match can be the difference in a close game.")

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

# ---------------------------------------------------------------- 135 · squad changes
with tab_squad, safe_section("best XI"):
    team_sheet(best_xi_cached(career, ids, team),
               f"{'All-time' if season == 'All seasons' else season} XI · {team} in {section}", show_team=False)

with tab_squad, safe_section("squad changes"):
    sc = state.memo(TD.squad_changes, career, ids, team)
    intl_ = sc.attrs.get("international", False)
    st.markdown(f"**Who came in and who went out** · {'series to series' if intl_ else 'season to season'}")
    if sc.empty:
        st.caption("Only one " + ("series" if intl_ else "season") + " so far: nothing to compare yet.")
    else:
        for (a_, b_), g_ in sc.groupby(["from", "to"], sort=False):
            with st.container(border=True):
                st.markdown(f"**{a_} → {b_}**")
                ins = g_[g_.change == "in"]
                outs = g_[g_.change == "out"]
                c1_, c2_ = st.columns(2)
                with c1_:
                    st.markdown(f"🟢 In ({len(ins)})")
                    if len(ins):
                        html_table([[player_link(r.player), r.games, r.runs, r.wickets] for r in ins.itertuples()],
                                   ["Player", "Games", "Runs", "Wkts"], numeric={1, 2, 3}, raw={0})
                with c2_:
                    st.markdown(f"🔴 Out ({len(outs)})")
                    if len(outs):
                        html_table([[player_link(r.player), r.games, r.runs, r.wickets] for r in outs.itertuples()],
                                   ["Player", "Games", "Runs", "Wkts"], numeric={1, 2, 3}, raw={0})
        st.caption("In: their figures in the new " + ("series" if intl_ else "season") + ". Out: their figures in the "
                   "last one they played.")

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
                         f"{pct(me_bf.bf_win_pct)}", f"{pct(a1['win_pct'])}"],
                        [second, f"{int(me_bf.ch_played)}",
                         TP.wdl(dict(won=int(me_bf.ch_won), lost=int(me_bf.ch_lost), drawn=int(me_bf.ch_drawn),
                                     tied=int(me_bf.ch_tied), no_result=int(me_bf.ch_no_result))),
                         f"{pct(me_bf.ch_win_pct)}", f"{pct(a2['win_pct'])}"]]
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
            st.markdown(f"**Close games** · won or lost by under {bars_for(base_kind)['close_runs']} runs or by 1-2 "
                        "wickets, or tied")
            html_table([["Close games", TP.wdl(cg["close"]), f"{pct(cg['close']['win_pct'])}"],
                        ["Other games", TP.wdl(cg["other"]), f"{pct(cg['other']['win_pct'])}"]],
                       ["", "Record", "Win %"], numeric={2})
            if len(cg["rows"]):
                rows = [[f"{r.date:%d %b %Y}", r.opponent, {"W": "Won", "L": "Lost", "T": "Tied"}.get(r.outcome, r.outcome),
                         (_n(int(r.margin_runs), "run") if pd.notna(r.margin_runs) else
                          _n(int(r.margin_wickets), "wkt") if pd.notna(r.margin_wickets) else "tie")]
                        for r in cg["rows"].sort_values("date", ascending=False).head(8).itertuples()]
                html_table(rows, ["Date", "Opponent", "", "Margin"])
    with right, safe_section("openers' start"):
        ss = state.memo(TP.start_split, career, ids, team)
        sa = state.memo(TP.start_split, career, ids, "")
        with st.container(border=True):
            st.markdown("**The openers' start** · result when the first wicket fell…")
            gb, bb_ = ss["good_bar"], ss["bad_bar"]
            rows = [[label, TP.wdl(ss[k]), f"{pct(ss[k]['win_pct'])}", f"{pct(sa[k]['win_pct'])}"]
                    for k, label in (("good", f"at {gb} or more"), ("middle", f"between {bb_} and {gb - 1}"),
                                     ("bad", f"under {bb_}"))]
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
                                 f"{pct(r.chase_pct)}" if r.chase_played else "–", f"{pct(a_.chase_pct)}",
                                 f"{r.defend_won}/{r.defend_played}" if r.defend_played else "–",
                                 f"{pct(r.defend_pct)}" if r.defend_played else "–", f"{pct(a_.defend_pct)}"])
                html_table(rows, ["Target" if multi else "Total", "Chased (won/played)", "Win %", "Every team",
                                  "Defended (won/played)", "Win %", "Every team"], numeric={2, 3, 5, 6})
                st.caption("Chasing: batting last. Defending: setting the target. 'Every team' is the same for all sides "
                           f"in {section}.")

    # ---------------------------------------------------------------- 96 · dominance
    with safe_section("dominance"), st.container(border=True):
        dm = state.memo(TD.dominance, career, ids)
        st.markdown("**How they win and lose** · thrashings, comfortable results and scrapes")
        if team in set(dm.team):
            r_ = dm.set_index("team").loc[team]
            b_ = bars_for(base_kind)
            html_table([["Wins", int(r_.won_thrashing), int(r_.won_comfortable), int(r_.won_scrape)],
                        ["Defeats", int(r_.lost_thrashing), int(r_.lost_comfortable), int(r_.lost_scrape)]],
                       ["", "Thrashing", "Comfortable", "Scrape"], numeric={1, 2, 3})
            rank_ = int(list(dm.team).index(team)) + 1
            st.caption(f"Thrashing: {b_['thrash_runs']}+ runs or {b_['thrash_wkts']}+ wickets"
                       + (" (or an innings)" if base_kind == "multi" else "") + f". Scrape: under {b_['close_runs']} runs "
                       f"or 1-2 wickets. Dominance index {r_['index']:+.0f} (thrashings won minus heavy defeats, per 100 "
                       f"games): {rank_} of {len(dm)} here."
                       + (f" Draws: {int(r_.drawn)}." if r_.drawn else ""))
    # ---------------------------------------------------------------- 133 · comebacks
    with safe_section("comebacks"), st.container(border=True):
        with st.spinner("Working out the win chance through every match…"):
            cb_all = state.memo(WP.comebacks, career, ids)
        cb = cb_all[cb_all.winner == team]
        against = cb_all[cb_all.loser == team]
        st.markdown(f"**Comebacks** · {team} wins from a losing position (their chance fell under 25%)")
        if cb.empty:
            st.caption("No comeback wins yet.")
        else:
            html_table([[match_link(r.match_id, f"{r.date:%d %b %Y}"), r.loser, f"{r.low:.0f}%", r.at, r.result]
                        for r in cb.itertuples()], ["Match", "Against", "Lowest chance", "When", "Result"],
                       numeric={2}, raw={0})
        st.caption(f"{len(cb)} comeback win{'s' if len(cb) != 1 else ''} for {team}, and {len(against)} game"
                   f"{'s' if len(against) != 1 else ''} they lost from a winning position. The chance is from "
                   "the Matches page's win-chance line: games in the same spot (innings, wickets down, lead).")

# ---------------------------------------------------------------- 5, 6, 30, 31 · opponents and stages
with tab_opp:
    left, right = st.columns(2, gap="medium")
    with left, safe_section("league and knockouts"):
        sr = state.memo(TP.stage_record, career, ids, team)
        with st.container(border=True):
            st.markdown("**League games and knockouts**")
            rows = [[r.stage, r.played, TP.wdl(r._asdict()), f"{pct(r.win_pct)}"] for r in sr.itertuples() if r.played]
            html_table(rows, ["", "Played", "Record", "Win %"], numeric={1, 3})
    with right, safe_section("bounce back"):
        ar = state.memo(TP.after_result, career, ids, team)
        with st.container(border=True):
            st.markdown("**Bouncing back** · their next game after…")
            rows = [[r.after, r.played, TP.wdl(r._asdict()), f"{pct(r.win_pct)}"] for r in ar.itertuples()]
            if rows:
                html_table(rows, ["", "Games", "Record", "Win %"], numeric={1, 3})
            else:
                st.caption("Not enough games yet.")
    with safe_section("opponents"):
        op = state.memo(TP.opponents, career, ids, team)
        with st.container(border=True):
            st.markdown("**Every opponent** · ⭐ favourite and 👻 bogey team (met at least twice)")
            rows = [[("⭐ " if r.favourite else "👻 " if r.bogey else "") + r.opponent, r.played, TP.wdl(r._asdict()),
                     f"{pct(r.win_pct)}", f"{r.last:%d %b %Y}"] for r in op.itertuples()]
            html_table(rows, ["Opponent", "Played", "Record", "Win %", "Last met"], numeric={1, 3},
                       row_class=["hi" if r.favourite or r.bogey else "" for r in op.itertuples()])
    with safe_section("fortress"), st.container(border=True):
        fz = state.memo(TD.fortress, career, ids)
        st.markdown("**Home fortress** · home record against the average home side here")
        if fz.empty:
            st.caption("No home games here (neutral venues).")
        else:
            html_table([[r.team, TP.wdl(r._asdict()), pct(r.win_pct), signed(r.vs) + (" pts" if np.isfinite(r.vs) else "")]
                        for r in fz.itertuples()], ["Team", "Home record", "Home win %", "v average home side"],
                       numeric={2, 3}, row_class=["hi" if r.team == team else "" for r in fz.itertuples()])
            st.caption(f"The average home side here wins {pct(fz.attrs['average'])}. A fortress is well above that: "
                       "winning there is worth more.")
    with safe_section("revenge"):
        rv = state.memo(TP.revenge, career, ids, team)
        with st.container(border=True):
            st.markdown("**Revenge games** · against a side that beat them the last time they met")
            html_table([["Revenge games", TP.wdl(rv["revenge"]), f"{pct(rv['revenge']['win_pct'])}"],
                        ["Every other game", TP.wdl(rv["other"]), f"{pct(rv['other']['win_pct'])}"]],
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
                    mine_r = race[race.team == team].sort_values("round")
                    chart_note(f"{team} are {int(mine_r.position.iloc[-1])} of {race.team.nunique()} after "
                               f"{int(mine_r.played.iloc[-1])} games; their best was {int(mine_r.position.min())} and "
                               f"their lowest {int(mine_r.position.max())}.",
                               f"Shows how the season unfolded: when {team} climbed or slipped. Positions follow the league "
                               "table (points, then net run rate). Hover a line for points.")
    with safe_section("early and late season"):
        sh = state.memo(TP.season_halves, career, ids, team)
        with st.container(border=True):
            st.markdown("**Early or late starters** · league games in the first and second half of each season")
            if sh.empty:
                st.caption("No league games yet.")
            else:
                rows = [[r.season, TP.wdl(r.early), f"{pct(r.early['win_pct'])}", TP.wdl(r.late),
                         f"{pct(r.late['win_pct'])}"] for r in sh.itertuples()]
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
                    rows = [[r.start, r.series, f"{r.won}–{r.drawn}–{r.lost}", f"{pct(r.win_pct)}",
                             f"{pct(every.get(r.start, np.nan))}"] for r in fb.itertuples()]
                    html_table(rows, ["", "Series", "Won–drawn–lost", "Series won", "Every team"], numeric={1, 3, 4})
        with right, safe_section("deciders and dead rubbers"):
            si = state.memo(TP.situations, career, ids, team)
            with st.container(border=True):
                st.markdown("**Deciders and dead rubbers**")
                rows = [[r.situation, r.played, TP.wdl(r._asdict()), f"{pct(r.win_pct)}"] for r in si.itertuples() if r.played]
                if rows:
                    html_table(rows, ["", "Games", "Record", "Win %"], numeric={1, 3})
                else:
                    st.caption("No series games yet.")
                st.caption("Decider: the last game with the series level. Dead rubber: the series was already won.")
    if multi:
        with safe_section("second innings"), st.container(border=True):
            si2 = state.memo(TD.second_innings, career, ids)
            st.markdown("**Second innings and fourth-innings chases**")
            html_table([[r.team, r.second_innings, fmt(r.second_avg, 0), r.cheap, r.chases,
                         f"{r.chase_won}–{r.chase_drawn}–{r.chase_lost}"] for r in si2.itertuples()],
                       ["Team", "2nd innings", "Average", "Bowled out under 200", "4th-innings chases", "Won–drawn–lost"],
                       numeric={1, 2, 3, 4}, row_class=["hi" if r.team == team else "" for r in si2.itertuples()])
            st.caption("Second innings: each team's second time batting in a match (after a follow-on too). "
                       "Chases: batting in the 4th innings, with how those games ended.")
        with safe_section("follow-on and declarations"):
            fo = state.memo(TP.follow_on_and_declarations, career, ids, team)
            with st.container(border=True):
                st.markdown("**Follow-on and declarations** · what happened next")
                if fo.empty:
                    st.caption("No follow-ons or declarations yet.")
                else:
                    html_table([[r.situation, r.times, f"{r.won}–{r.drawn}–{r.lost}", f"{pct(r.win_pct)}"]
                                for r in fo.itertuples()], ["", "Times", "Won–drawn–lost", "Win %"], numeric={1, 3})
    if not has_series and not multi:
        st.info("Bilateral series and multi-day games only: this section has neither.")
