import numpy as np
import pandas as pd
import streamlit as st

from ccstats import analysis as A
from ccstats import extras as E
from ccstats import players as PL
from ccstats.stats import Scope, bars_for
from ui import state
from ui.charts import pct, CONFIG, bars, fmt, form_chart, paired_bars, say
from ui.theme import chart_note, explain_list, html_table, kpis, match_link, page_header, safe_section

career = state.current()
if career is None:
    st.info("Load a career on the Home page first.")
    st.stop()

players = sorted(set(career.batting.player) | set(career.bowling.player))
wanted = st.query_params.get("player")
if wanted in players and "pl_player" not in st.session_state:
    st.session_state["pl_player"] = wanted
player = st.selectbox("Player", players, key="pl_player", placeholder="Type a name, e.g. S Gill", index=None)
if not player:
    page_header("Player", "Pick a player", "Type a name in the box above. Every player who has batted or bowled in this career is listed.")
    st.stop()

m = career.matches
mine_bat = career.batting[(career.batting.player == player)]
mine_bowl = career.bowling[(career.bowling.player == player)]
my_matches = m[m.match_id.isin(set(mine_bat.match_id) | set(mine_bowl.match_id))]
teams = sorted(set(mine_bat.team) | set(mine_bowl.team))
is_keeper = not A.keepers(career, my_matches.match_id)[lambda k: k.player == player].empty
page_header(" · ".join(teams) + (" · Wicketkeeper" if is_keeper else ""), player,
            f"{len(my_matches)} matches in {my_matches.section.nunique()} section{'s' if my_matches.section.nunique() != 1 else ''}. "
            "Pick a section below; every figure on this page is for that section only.")

# ---------------------------------------------------------------- career by section
BAT_HELP = {"Mat": "Matches played", "Inns": "Innings batted", "NO": "Not outs", "HS": "Highest score (* = not out)",
            "Avg": "Runs per dismissal", "BF": "Balls faced", "SR": "Runs per 100 balls", "100": "Hundreds",
            "50": "Fifties (50-99)", "0": "Ducks", "Ct": "Catches", "St": "Stumpings"}
BOWL_HELP = {"Mat": "Matches played", "Inns": "Innings bowled in", "Overs": "Six-ball overs (The Hundred's balls are converted)",
             "Mdns": "Maidens (only printed on longer-format cards)", "Dots": "Dot balls (only printed on T20 and Hundred cards)",
             "Wkts": "Wickets", "BBI": "Best bowling in an innings", "BBM": "Best bowling in a match",
             "Avg": "Runs per wicket", "Econ": "Runs per over", "SR": "Balls per wicket", "4w": "Four wickets in an innings",
             "5w": "Five or more wickets in an innings", "10m": "Ten or more wickets in a match"}


def record_table(df: pd.DataFrame, first: str, bowling: bool, key: str) -> None:
    """The standard batting or bowling table, identical in every section."""
    helps = BOWL_HELP if bowling else BAT_HELP
    cfg = {c: st.column_config.NumberColumn(c, help=h, format="%d") for c, h in helps.items()
           if c in df and c not in ("HS", "Overs", "BBI", "BBM", "Avg", "SR", "Econ")}
    cfg |= {c: st.column_config.TextColumn(c, help=helps[c]) for c in ("HS", "Overs", "BBI", "BBM") if c in df}
    # decimals as text so "never dismissed" / "no wicket" reads "–", not "None"
    dec = {"Avg": 2, "Econ": 2, "SR": 1}
    cfg |= {c: st.column_config.TextColumn(c, help=helps[c]) for c in dec if c in df}
    df = df.assign(**{c: [fmt(v, d) for v in df[c]] for c, d in dec.items() if c in df})
    # maidens / dots that the scorecard doesn't print show as a dash, not as 0
    cfg |= {c: st.column_config.TextColumn(c, help=helps[c]) for c in ("Mdns", "Dots") if c in df}
    df = df.assign(**{c: [("–" if pd.isna(v) else str(int(v))) for v in df[c]] for c in ("Mdns", "Dots") if c in df})
    df = df.drop(columns=["Balls"], errors="ignore")  # Overs says the same and keeps the table on screen
    cfg[first] = st.column_config.TextColumn(first.title())
    st.dataframe(df, hide_index=True, width="stretch", column_config=cfg, key=key)


all_ids = my_matches.match_id


def split_shows(t: pd.DataFrame, col: str, value: str, overall: float, what: str, low_better: bool = False,
                dec: int = 1) -> str:
    """'Best: X 45.2 (+31% on their 34.5 overall); worst: Y 20.1 (−42%).' for one split chart."""
    t = t[t[value].notna()]
    if t.empty or not np.isfinite(overall) or not overall:
        return f"Not enough {what} to compare yet."
    t = t.sort_values(value, ascending=low_better)
    hi, lo = t.iloc[0], t.iloc[-1]
    pc = lambda v: f"{(v - overall) / overall * 100:+.0f}%"  # noqa: E731
    out = f"Best {say(str(hi[col])).lower()}: {fmt(hi[value], dec)} ({pc(hi[value])} on their {fmt(overall, dec)} overall)"
    if len(t) > 1:
        out += f"; worst {say(str(lo[col])).lower()}: {fmt(lo[value], dec)} ({pc(lo[value])})"
    return out + "."
order = list(my_matches.section.value_counts().index)  # most-played section first


def by_order(df: pd.DataFrame) -> pd.DataFrame:
    return df.assign(_o=df.section.map(order.index)).sort_values("_o").drop(columns="_o").reset_index(drop=True)


bat_rec = by_order(A.batting_record(career, all_ids, player))
bowl_rec = by_order(A.bowling_record(career, all_ids, player))
with st.container(border=True):
    st.markdown("**Batting and fielding · every section**")
    record_table(bat_rec, "section", False, "pl_bat_rec")
    if len(bowl_rec):
        st.markdown("**Bowling · every section**")
        record_table(bowl_rec, "section", True, "pl_bowl_rec")
    else:
        st.caption("Hasn't bowled.")
    st.caption("Same columns in every section. Hover a column name for what it means. Maidens are only printed on "
               "longer-format scorecards and dot balls only on T20 and Hundred scorecards, so one of them is blank.")

with st.expander("Career journey · every team and competition, in order"):
    j = E.journey(career, player)
    st.dataframe(pd.DataFrame({"From": j["first"].dt.strftime("%d %b %Y"), "To": j["last"].dt.strftime("%d %b %Y"),
                               "Team": j.team, "Section": j.section, "Season": j.season, "Matches": j.matches,
                               "Runs": j.runs, "Wickets": j.wickets}), hide_index=True, width="stretch")

c1, c2 = st.columns([2, 1])
section = c1.selectbox("Section", list(order), key="pl_section")
seasons = sorted(my_matches[my_matches.section == section].season.unique(), reverse=True)
season = c2.selectbox("Season", ["All seasons"] + seasons, key="pl_season")
scope = Scope(sections=[section], seasons=[] if season == "All seasons" else [season])
ids = scope.match_ids(m)
bat_t, bowl_t, fld_t, base = state.tables(career, scope)
kind = base.kind
me_bat = bat_t[bat_t.player == player]
me_bowl = bowl_t[bowl_t.player == player]
me_fld = fld_t[fld_t.player == player]
inns = A.batting_innings(career, ids, player)
spells = A.bowling_spells(career, ids, player)
strength = A.team_strength(career, ids)

roles = A.role_labels(career, ids, kind).set_index("player")
if player in roles.index:
    r = roles.loc[player]
    chips = " ".join(f"<span class='chip'>{t}</span>" for t in [r.role] + list(r.tags))
    st.markdown(f"<p class='roles'>{chips}<span class='note'>Role in {section}{'' if season == 'All seasons' else ' ' + season}, "
                f"from where they bat (usually no. {r.usual_position:.0f}) and how much they bowl</span></p>",
                unsafe_allow_html=True)

tab_names = []
if len(inns):
    tab_names.append("Batting")
if len(spells):
    tab_names.append("Bowling")
tab_names.append("Fielding")
is_bowler = (roles.loc[player, "role"] == "Bowler" if player in roles.index  # too few games for a role: where they bat
             else inns.empty or inns.position.median() >= 8)
if is_bowler and "Bowling" in tab_names:
    # a bowler's page opens on their bowling, then fielding; batting comes last
    tab_names = ["Bowling", "Fielding"] + [t for t in tab_names if t not in ("Bowling", "Fielding")]
tab_names.append("Story")
tabs = dict(zip(tab_names, st.tabs(tab_names)))

# ================================================================ batting
if "Batting" in tabs:
    with tabs["Batting"], safe_section("batting"):
        b = me_bat.iloc[0]
        kpis([("Innings", f"{b.innings}"), ("Runs", f"{b.runs:,}"), ("Average", fmt(b.average, 2)),
              ("Strike rate", fmt(b.strike_rate, 1)), ("High score", b.high_score_text),
              ("100s / 50s", f"{b.hundreds} / {b.fifties}")])
        st.write("")
        with st.container(border=True):
            st.markdown("**Form: every innings**")
            hover = [f"{r.runs}{'' if r.out else '*'} off {r.balls} v {r.opposition} · {r.date:%d %b %Y}" for r in inns.itertuples()]
            st.plotly_chart(form_chart(inns.runs, ~inns.out, hover), width="stretch", config=CONFIG, key="pl_form")
            explain_list([("", "<b>Grey bars</b>: runs in each innings, oldest on the left."),
                          ("dot", "<b>Blue line</b>: average over the last 10 innings (5 for a shorter career). Rising means in form, falling means out of form."),
                          ("line", "<b>Dashed line</b>: average over every innings shown.")])
            n_ = min(10, len(inns))
            last_ = inns.tail(n_)
            recent_avg = last_.runs.sum() / max(last_.out.sum(), 1)
            chart_note(f"{len(inns)} innings. Their last {n_} average {recent_avg:.1f} against {fmt(b.average, 1)} "
                       f"overall ({(recent_avg - b.average) / b.average * 100:+.0f}%)." if np.isfinite(b.average) and b.average
                       else f"{len(inns)} innings, never dismissed.",
                       "Shows whether they are in form right now, not just how good they are over the whole career.")

        left, right = st.columns(2, gap="medium")
        with left:
            with st.container(border=True):
                st.markdown("**Season by season · runs**")
                ss = A.split_batting(inns, "season").sort_values("season", ascending=False)
                st.plotly_chart(bars(ss.season, ss.runs, "Runs", notes=[f"{i} innings · average {fmt(a, 1)}" for i, a in zip(ss.innings, ss.average)]),
                                width="stretch", config=CONFIG, key="pl_seasons")
                bs_ = ss.sort_values("runs", ascending=False).iloc[0]
                chart_note(f"Most runs in {bs_.season}: {bs_.runs} ({bs_.runs / max(ss.runs.sum(), 1) * 100:.0f}% of their "
                           f"{ss.runs.sum()} here), average {fmt(bs_.average, 1)}.",
                           "Shows whether they are getting better or fading, season by season.")
        with right:
            with st.container(border=True):
                st.markdown("**How they get out**")
                ho = A.how_out(inns)
                if ho.empty:
                    st.caption("Never dismissed.")
                else:
                    st.plotly_chart(bars([say(h) for h in ho.index], ho.values, "Dismissals"), width="stretch",
                                    config=CONFIG, key="pl_howout")
                    chart_note(f"{ho.iloc[0] / ho.sum() * 100:.0f}% of their {int(ho.sum())} dismissals are "
                               f"{say(ho.index[0]).lower()}.",
                               "How bowlers get them out: a weakness to work on with your own players, or to attack in an "
                               "opponent.")
        with st.container(border=True):
            st.markdown(f"**Every season in {section}** · the same columns as the table at the top")
            record_table(A.batting_record(career, ids, player, by="season").sort_values("season", ascending=False),
                         "season", False, "pl_bat_seasons")

        st.subheader("Average in different situations", anchor=False)
        st.caption(f"Each chart splits the same innings one way. The dashed line is their overall average ({fmt(b.average, 1)}).")
        sp = [("Batting first or chasing", inns.assign(s=np.where(inns.batting_first, "Batting first", "Chasing")), "s"),
              ("In wins, defeats and draws", inns.assign(s=inns.outcome.map(say)), "s"),
              ("Home or away", inns.assign(s=inns.venue.map(say)), "s"),
              ("Against stronger or weaker teams", inns.assign(s=A.opposition_strength(inns, strength)), "s")]
        cols = st.columns(2, gap="medium")
        for i, (title, d, col) in enumerate(sp):
            t = A.split_batting(d, col)
            with cols[i % 2]:
                with st.container(border=True):
                    st.markdown(f"**{title}**")
                    st.plotly_chart(bars(t[col], t.average, "Average", 1, reference=b.average,
                                         notes=[f"{n} innings, {r} runs, strike rate {fmt(s, 1)}" for n, r, s in zip(t.innings, t.runs, t.strike_rate)]),
                                    width="stretch", config=CONFIG, key=f"pl_split_{i}")
                    chart_note(split_shows(t, col, "average", b.average, "innings"),
                               {0: "Shows whether they are better at setting a total or chasing one.",
                                1: "Shows whether their runs come when the team wins, or when the game is already lost.",
                                2: "Shows how much home conditions help them.",
                                3: "Shows whether they score against the good sides too, or fill their boots against the weak ones."}[i])
        with st.container(border=True):
            st.markdown("**Stronger and weaker teams** · teams ranked by their win % in this section; the top half are the stronger teams. "
                        f"Stronger half: {', '.join(sorted(t for t, v in strength.items() if v > np.median(list(strength.values())))) or '–'}.")

        pr = A.position_record(career, ids, player)
        if len(pr):
            with st.container(border=True):
                st.markdown("**Average at each batting position** · compared with the average batter at that position")
                st.plotly_chart(paired_bars(pr.group, pr.average, pr.section_average, player, "Average batter there",
                                            "Average", 1,
                                            notes=[f"{n} innings, {r} runs, strike rate {fmt(s, 1)}"
                                                   for n, r, s in zip(pr.innings, pr.runs, pr.strike_rate)]),
                                width="stretch", config=CONFIG, key="pl_positions")
                best = pr[pr.innings >= 3].assign(edge=lambda d: d.average - d.section_average).dropna(subset=["edge"])
                if len(best) > 1:
                    top = best.sort_values("edge", ascending=False).iloc[0]
                    edge_pct = (top.average - top.section_average) / top.section_average * 100 if top.section_average else 0
                    chart_note(f"Best position: {top.group}, where they average {fmt(top.average, 1)} against "
                               f"{fmt(top.section_average, 1)} for the average batter there ({edge_pct:+.0f}%, at least 3 innings).",
                               "Tells you where to bat them: blue is them, grey the average batter in that position.")
                else:
                    chart_note("They have batted in only one position with 3+ innings so far.",
                               "Tells you where to bat them: blue is them, grey the average batter in that position.")

        # came in at
        st.subheader("When they came in", anchor=False)
        ci = inns.dropna(subset=["came_in_score"]).copy()
        bar_ = bars_for(kind)  # pressure and platform depend on the format: 3 down for 40 in a T20 is trouble, 250 a platform in a Test
        press, plat = bar_["pressure_score"], bar_["platform"]
        pressure_label = f"Under pressure (3+ down for {press} or fewer)"
        ci["situation"] = np.select(
            [ci.came_in_wickets == 0, (ci.came_in_wickets >= 3) & (ci.came_in_score <= press), ci.came_in_score >= plat],
            ["Opening the innings", pressure_label, f"Big platform ({plat}+ on the board)"],
            "Normal")
        left, right = st.columns(2, gap="medium")
        with left:
            with st.container(border=True):
                st.markdown("**Average by the situation they walked into**")
                t = A.split_batting(ci, "situation")
                st.plotly_chart(bars(t.situation, t.average, "Average", 1, reference=b.average,
                                     notes=[f"{n} innings" for n in t.innings]), width="stretch", config=CONFIG, key="pl_situation")
                if len(ci):
                    wk = float(ci.came_in_wickets.mean())
                    chart_note(split_shows(t, "situation", "average", b.average, "innings")
                               + f" On average they came in at {ci.came_in_score.mean():.0f} for "
                                 f"{fmt(wk, 0 if wk.is_integer() else 1)}.",
                               "Shows whether they handle pressure. The score comes from the fall of wickets: the number "
                               "5 walks in when the 3rd wicket falls.")
        with right:
            with st.container(border=True):
                st.markdown(f"**Best rescue innings** · came in with 3 or more down for {press} or fewer")
                r = ci[ci.situation.str.startswith("Under")].sort_values("runs", ascending=False).head(5)
                if r.empty:
                    st.caption("No innings started in that kind of trouble yet.")
                else:
                    st.dataframe(pd.DataFrame({"Came in at": [f"{int(s)}/{int(w)}" for s, w in zip(r.came_in_score, r.came_in_wickets)],
                                               "Score": [f"{x}{'' if o else '*'}" for x, o in zip(r.runs, r.out)],
                                               "Balls": r.balls, "Against": r.opposition,
                                               "Date": r.date.dt.strftime("%d %b %Y")}), hide_index=True, width="stretch")

        left, right = st.columns(2, gap="medium")
        with left:
            with st.container(border=True):
                st.markdown("**Consistency**")
                cs = A.consistency(inns, kind)
                kpis([(f"{cs['bar']}+ scores", f"{cs['past_bar_pct']:.0f}%"), ("Single figures", f"{cs['single_figures_pct']:.0f}%")])
                st.write("")
                kpis([("Golden ducks", f"{cs['golden_ducks']}"),
                      ("50s → 100s", "–" if np.isnan(cs["conversion_pct"]) else f"{cs['conversion_pct']:.0f}%")])
                st.caption(f"'{cs['bar']}+ scores' is how often they pass {cs['bar']}, a decent score in this format. 'Single figures' "
                           "is how often they're out for under 10. A golden duck is out first ball. '50s → 100s' is how often a "
                           "fifty is turned into a hundred.")
        with right:
            with st.container(border=True):
                st.markdown("**Nemesis** · bowlers who have dismissed them most")
                n = A.nemesis(career, ids, player).head(6)
                if n.empty:
                    st.caption("No bowler has dismissed them yet.")
                else:
                    st.plotly_chart(bars(n.bowler, n.dismissals, "Times dismissed"), width="stretch", config=CONFIG, key="pl_nemesis")
                    outs_ = int(inns.out.sum())
                    chart_note(f"{n.bowler.iloc[0]} has got them out {n.dismissals.iloc[0]} times, "
                               f"{n.dismissals.iloc[0] / max(outs_, 1) * 100:.0f}% of their {outs_} dismissals.",
                               "The bowlers who have their number: keep them away from these bowlers, or bring these "
                               "bowlers on when this batter comes in.")

        left, right = st.columns(2, gap="medium")
        with left:
            with st.container(border=True):
                st.markdown("**Streaks** · innings in a row")
                srows = E.batting_streaks(inns, kind)
                st.dataframe(pd.DataFrame({"Streak": [r["streak"] for r in srows],
                                           "Longest": [r["longest"] for r in srows],
                                           "Current": [r["current"] for r in srows]}),
                             hide_index=True, width="stretch")
                st.caption("Current = the run they're on now, counting back from their latest innings here.")
        with right:
            with st.container(border=True):
                st.markdown("**When chasing** · batting in the last innings of the match")
                ch = E.chasing(career, ids, min_innings=1)
                ch = ch[ch.player == player]
                if ch.empty:
                    st.caption("Hasn't batted in a chase here yet.")
                else:
                    r = ch.iloc[0]
                    kpis([("Chases won", f"{r.won_innings}"), ("Average in wins", fmt(r.won_average, 1))])
                    st.write("")
                    kpis([("Chases lost", f"{r.lost_innings}"), ("Average in defeats", fmt(r.lost_average, 1))])
                    st.caption(f"Not out at the end of {r.not_out_in_wins} winning chase"
                               f"{'s' if r.not_out_in_wins != 1 else ''}: still there when the runs were knocked off.")

        with st.container(border=True):
            st.markdown("**Against each team** · average")
            t = A.split_batting(inns, "opposition").sort_values("runs", ascending=False)
            st.plotly_chart(bars(t.opposition, t.average, "Average", 1, reference=b.average,
                                 notes=[f"{n} innings, {r} runs, best {h}" for n, r, h in zip(t.innings, t.runs, t.high)]),
                            width="stretch", config=CONFIG, key="pl_vs")
            chart_note(split_shows(t[t.innings >= 2] if (t.innings >= 2).any() else t, "opposition", "average", b.average,
                                   "innings") + " (teams they have batted against at least twice)",
                       "Shows which opponents they like and which ones keep them quiet.")

# ================================================================ bowling
if "Bowling" in tabs:
    with tabs["Bowling"], safe_section("bowling"):
        w = me_bowl.iloc[0]
        kpis([("Wickets", f"{w.wickets}"), ("Average", fmt(w.average, 2)), ("Economy", fmt(w.economy, 2)),
              ("Strike rate", fmt(w.strike_rate, 1)), ("Best", w.best), ("4+ hauls", f"{w.hauls}")])
        st.write("")
        with st.container(border=True):
            st.markdown("**Form: wickets in every innings bowled**")
            hover = [f"{r.wickets}/{r.runs} v {r.opposition} · {r.date:%d %b %Y}" for r in spells.itertuples()]
            # a wicket-rate line: wickets per innings over the last 10 (every spell counts, no not-outs)
            st.plotly_chart(form_chart(spells.wickets, [False] * len(spells), hover, y_label="Wickets"),
                            width="stretch", config=CONFIG, key="pl_bform")
            explain_list([("", "<b>Grey bars</b>: wickets in each innings bowled."),
                          ("dot", "<b>Blue line</b>: wickets per innings over the last 10 (5 for a shorter career)."),
                          ("line", "<b>Dashed line</b>: wickets per innings over everything shown.")])
            n_ = min(10, len(spells))
            rw_, aw_ = spells.tail(n_).wickets.mean(), spells.wickets.mean()
            chart_note(f"{len(spells)} innings bowled. Their last {n_} average {rw_:.2f} wickets an innings against "
                       f"{aw_:.2f} overall" + (f" ({(rw_ - aw_) / aw_ * 100:+.0f}%)." if aw_ else "."),
                       "Shows whether they are taking wickets right now, not just over the whole career.")
        left, right = st.columns(2, gap="medium")
        with left:
            with st.container(border=True):
                st.markdown("**Season by season · wickets**")
                ss = A.split_bowling(spells, "season").sort_values("season", ascending=False)
                st.plotly_chart(bars(ss.season, ss.wickets, "Wickets", notes=[f"average {fmt(a, 1)} · economy {fmt(e, 2)}" for a, e in zip(ss.average, ss.economy)]),
                                width="stretch", config=CONFIG, key="pl_bseasons")
                bw_ = ss.sort_values("wickets", ascending=False).iloc[0]
                chart_note(f"Most wickets in {bw_.season}: {int(bw_.wickets)} "
                           f"({bw_.wickets / max(ss.wickets.sum(), 1) * 100:.0f}% of their {int(ss.wickets.sum())} here), "
                           f"economy {fmt(bw_.economy, 2)}.",
                           "Shows whether they are getting better or fading, season by season.")
        with right:
            with st.container(border=True):
                st.markdown("**How they take wickets**")
                wt = A.wicket_types(career, ids, player)
                if wt.empty:
                    st.caption("No wickets yet.")
                else:
                    st.plotly_chart(bars([say(h) for h in wt.index], wt.values, "Wickets"), width="stretch", config=CONFIG, key="pl_wtypes")
                    chart_note(f"{wt.iloc[0] / wt.sum() * 100:.0f}% of their {int(wt.sum())} wickets are "
                               f"{say(wt.index[0]).lower()}.",
                               "How they get batters out: bowled and lbw mean they hit the stumps; catches mean they "
                               "need the fielders, so set the field for them.")
        with st.container(border=True):
            st.markdown(f"**Every season in {section}** · the same columns as the table at the top")
            record_table(A.bowling_record(career, ids, player, by="season").sort_values("season", ascending=False),
                         "season", True, "pl_bowl_seasons")
        left, right = st.columns(2, gap="medium")
        with left:
            with st.container(border=True):
                st.markdown("**Quality of wickets** · where in the order their victims bat")
                q = A.wicket_quality(career, ids, player)
                if q:
                    st.plotly_chart(bars(["Top order (1-3)", "Middle order (4-7)", "Tail (8-11)"],
                                         [q["top_order"], q["middle_order"], q["tail"]], "Wickets"),
                                    width="stretch", config=CONFIG, key="pl_quality")
                    chart_note(f"{q['top_seven_pct']:.0f}% of their {q['total']} wickets are specialist batters (positions "
                               f"1-7): {q['top_order']} top order, {q['middle_order']} middle order, {q['tail']} tail.",
                               "Shows whether their wickets are the ones that matter or mostly tail-enders.")
                else:
                    st.caption("No wickets yet.")
        with right:
            with st.container(border=True):
                st.markdown("**Bunnies** · batters they have dismissed most")
                bn = A.bunnies(career, ids, player).head(6)
                if bn.empty:
                    st.caption("No wickets yet.")
                else:
                    st.plotly_chart(bars(bn.player, bn.dismissals, "Times dismissed"), width="stretch", config=CONFIG, key="pl_bunnies")
                    tw_ = int(spells.wickets.sum())
                    chart_note(f"They have got {bn.player.iloc[0]} out {bn.dismissals.iloc[0]} times, "
                               f"{bn.dismissals.iloc[0] / max(tw_, 1) * 100:.0f}% of their {tw_} wickets.",
                               "The batters they have the wood on: bring them on when these batters come in.")
        with st.container(border=True):
            st.markdown("**Streaks** · innings bowled in a row")
            srows = E.bowling_streaks(spells, kind)
            st.dataframe(pd.DataFrame({"Streak": [r["streak"] for r in srows], "Longest": [r["longest"] for r in srows],
                                       "Current": [r["current"] for r in srows]}), hide_index=True, width="stretch")
        cols = st.columns(2, gap="medium")
        for i, (title, d, col) in enumerate([
                ("Bowling first or second", spells.assign(s=np.where(spells.batting_first, "Their side batted first", "Their side bowled first")), "s"),
                ("Against each team", spells, "opposition")]):
            t = A.split_bowling(d, col).sort_values("wickets", ascending=False)
            with cols[i]:
                with st.container(border=True):
                    st.markdown(f"**{title}** · economy")
                    st.plotly_chart(bars(t[col], t.economy, "Economy (runs per over)", 2, reference=w.economy,
                                         notes=[f"{wk} wickets, average {fmt(a, 1)}" for wk, a in zip(t.wickets, t.average)]),
                                    width="stretch", config=CONFIG, key=f"pl_bsplit_{i}")
                    chart_note(split_shows(t[t.balls >= 12] if (t.balls >= 12).any() else t, col, "economy", w.economy,
                                           "overs", low_better=True, dec=2) + " Lower is better.",
                               "Shows whether they bowl better defending a total or chasing one." if i == 0 else
                               "Shows which teams they keep quiet and which ones get after them.")

# ================================================================ fielding
with tabs["Fielding"], safe_section("fielding"):
    if len(me_fld):
        f = me_fld.iloc[0]
        kpis([("Matches", f"{f.matches}"), ("Catches", f"{f.catches}"), ("Stumpings", f"{f.stumpings}")])
    else:
        st.caption("No fielding record in this section.")
    st.caption("Catches and stumpings are credited under the player's own name, so 'c de Kock' counts for Q de Kock. "
               "Run outs aren't credited to fielders because the scorecard doesn't name them.")

# ================================================================ story
with tabs["Story"]:
    left, right = st.columns([1.1, 1], gap="medium")
    with left, safe_section("career firsts"), st.container(border=True):
        fi = state.memo(PL.firsts, career, player)
        st.markdown("**Career firsts** · every competition")
        if fi.empty:
            st.caption("Nothing yet.")
        else:
            html_table([[f"{r.date:%d %b %Y}", r.what, r.detail, match_link(r.match_id, f"v {r.against}")]
                        for r in fi.itertuples()], ["Date", "", "", "Match"], raw={3})
    with right:
        with safe_section("team wins"), st.container(border=True):
            st.markdown(f"**When {player} fires** · their team's win % in {section}"
                        f"{'' if season == 'All seasons' else ' ' + season}")
            wb, ww = state.memo(PL.win_when, career, ids, 1)
            rows = []
            for d, label in ((wb, f"{wb.attrs.get('big', 50)}+ with the bat"), (ww, f"{ww.attrs.get('haul', 3)}+ wickets")):
                r = d[d.player == player]
                if len(r):
                    r = r.iloc[0]
                    rows.append([label, r.times, f"{pct(r.pct_when)}", f"{pct(r.pct_other)}"])
            if rows:
                html_table(rows, ["", "Times", "Win % then", "Win % otherwise"], numeric={1, 2, 3})
            else:
                st.caption(f"No {wb.attrs.get('big', 50)}+ scores or {ww.attrs.get('haul', 3)}-wicket hauls here yet.")
        with safe_section("quirks"), st.container(border=True):
            st.markdown("**Odd ones**")
            q = state.memo(PL.quirks, career, ids)
            nine = q["nineties"][q["nineties"].player == player]
            pairs = q["pairs"][q["pairs"].player == player]
            nots = q["not_outs"][q["not_outs"].player == player]
            ci, cp = state.memo(PL.carried, career, ids, 1)
            share = cp[cp.player == player]
            ah = state.memo(PL.after_hundred, career, ids)
            ah = ah[ah.player == player]
            lines = []
            if len(nine):
                lines.append(f"😬 Out in the nineties {nine.times.iloc[0]} time(s): {nine.scores.iloc[0]}.")
            if len(pairs):
                lines.append(f"🥚🥚 {pairs.pairs.iloc[0]} pair(s): out for 0 in both innings.")
            if len(nots):
                lines.append(f"🛡️ Not out in {nots.not_outs.iloc[0]} of {nots.innings.iloc[0]} innings ({nots.pct.iloc[0]:.0f}%).")
            if len(share):
                lines.append(f"🏋️ Makes {share.share.iloc[0]:.1f}% of their team's runs in the innings they bat.")
            if len(ah):
                lines.append(f"💯➡️ After a hundred: {ah.next_scores.iloc[0]} (average {fmt(ah.next_avg.iloc[0], 1)} "
                             f"against {fmt(ah.average.iloc[0], 1)} overall).")
            st.markdown("  \n".join(lines) if lines else "Nothing unusual yet.")
    with safe_section("compare seasons"), st.container(border=True):
        st.markdown(f"**Compare two seasons** · {section}")
        all_seasons = sorted(my_matches[my_matches.section == section].season.unique(), reverse=True)
        if len(all_seasons) < 2:
            st.caption("Only one season in this section so far.")
        else:
            s1, s2 = st.columns(2)
            a_ = s1.selectbox("Season", all_seasons, index=0, key="pl_cmp_a")
            b_ = s2.selectbox("Against", [x for x in all_seasons if x != a_], index=0, key="pl_cmp_b")
            sec_ids = m[m.section == section].match_id
            br = A.batting_record(career, sec_ids, player, by="season").set_index("season")
            wr = A.bowling_record(career, sec_ids, player, by="season").set_index("season")
            rows = []
            for col, dec, better in (("Mat", 0, None), ("Inns", 0, None), ("Runs", 0, "high"), ("Avg", 2, "high"),
                                     ("SR", 1, "high"), ("100", 0, "high"), ("50", 0, "high")):
                va = br[col].get(a_, np.nan) if col in br else np.nan
                vb = br[col].get(b_, np.nan) if col in br else np.nan
                rows.append(["Batting " + col, va, vb, dec, better])
            if len(wr):
                for col, dec, better in (("Wkts", 0, "high"), ("Avg", 2, "low"), ("Econ", 2, "low"), ("SR", 1, "low")):
                    rows.append(["Bowling " + col, wr[col].get(a_, np.nan), wr[col].get(b_, np.nan), dec, better])
            out = []
            for label, va, vb, dec, better in rows:
                fa = fmt(float(va), dec) if pd.notna(va) else "–"
                fb = fmt(float(vb), dec) if pd.notna(vb) else "–"
                if better and pd.notna(va) and pd.notna(vb) and va != vb:
                    if (va > vb) == (better == "high"):
                        fa = "<span class='tick'>✓</span> " + fa
                    else:
                        fb = "<span class='tick'>✓</span> " + fb
                out.append([label, fa, fb])
            html_table(out, ["", a_, b_], raw={1, 2}, numeric={1, 2})
            st.caption("✓ marks the better season on each (for bowling average, economy and strike rate, lower is better).")
