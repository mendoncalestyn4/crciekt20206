import streamlit as st

from ccstats import analysis as A
from ccstats.stats import POSITION_GROUPS, Scope, rank, stat_definitions
from ui import state
from ui.charts import CONFIG, dot_chart, fmt, ranked_bars
from ui.theme import explain_list, page_header

career = state.current()
if career is None:
    st.info("Load a career on the Home page first.")
    st.stop()

page_header("Stat by stat", "Who's best, who's worst",
            "Pick a section and a stat. The left chart ranks players on that one stat; the right chart shows where every "
            "qualifying player sits.")

m = career.matches
sections = m.section.value_counts()
labels = {s: f"{s} · {n} match{'es' if n > 1 else ''}" for s, n in sections.items()}

c1, c2, c3 = st.columns([2.2, 1.2, 1.3])
section = c1.selectbox("Section", list(sections.index), format_func=labels.get, key="sbs_section")
seasons = sorted(m[m.section == section].season.unique(), reverse=True)
season = c2.selectbox("Season", ["All seasons"] + seasons, key="sbs_season")
disc = c3.segmented_control("Discipline", ["Batting", "Bowling", "Fielding"], default="Batting", key="sbs_disc") or "Batting"

position = "Any"
if disc == "Batting":
    position = st.segmented_control(
        "Batting position", ["Any"] + list(POSITION_GROUPS), default="Any", key="sbs_pos",
        help="Only count innings played at these positions. The average line is then the average batter at that "
             "position, so openers are measured against openers.") or "Any"
scope = Scope(sections=[section], seasons=[] if season == "All seasons" else [season],
              positions=POSITION_GROUPS.get(position, []))
sec_ids = scope.match_ids(m)
teams_here = sorted(set(m[m.match_id.isin(sec_ids)].home) | set(m[m.match_id.isin(sec_ids)].away))
t1, t2 = st.columns([1.2, 2.6])
team = t1.selectbox("Team", ["All teams"] + teams_here, key="sbs_team")
# per player-and-team rows when one team is picked, so only their games for that team count;
# the average line always comes from the whole section
bat, bowl, fld, base = state.tables(career, scope, by_team=team != "All teams")
if team != "All teams":
    bat, bowl, fld = (t[t.team == team] for t in (bat, bowl, fld))
defs = stat_definitions(base)[{"Batting": "bat", "Bowling": "bowl", "Fielding": "field"}[disc]]
table = {"Batting": bat, "Bowling": bowl, "Fielding": fld}[disc]

MINS = {"Batting": {"t20": [0, 20, 30, 60, 100], "one": [0, 40, 60, 120, 200], "multi": [0, 60, 100, 200, 400]},
        "Bowling": {"t20": [0, 20, 36, 60, 120], "one": [0, 30, 60, 120, 240], "multi": [0, 60, 120, 240, 480]},
        "Fielding": {k: [1, 2, 3, 5] for k in ("t20", "one", "multi")}}
min_col = {"Batting": "balls", "Bowling": "balls", "Fielding": "matches"}[disc]
unit = {"Batting": "balls faced", "Bowling": "balls bowled", "Fielding": "matches"}[disc]
options = MINS[disc][base.kind]
# default: the stricter end of the list, as long as at least 12 players still qualify
default_min = next((v for v in reversed(options[:3]) if (table[min_col] >= v).sum() >= 12), options[0])

c4, c5, c6, c7 = st.columns([1.1, 1, 1.3, 1.6])
view = c4.segmented_control("Ranking", ["Best", "Worst"], default="Best", key="sbs_view",
                            disabled=disc == "Fielding") or "Best"
if disc == "Fielding":
    view = "Best"
top = c5.selectbox("Show", [10, 20, 50, 10_000], format_func=lambda v: "Everyone" if v == 10_000 else f"Top {v}", key="sbs_top")
minimum = c6.selectbox("Minimum to qualify", options, index=options.index(default_min),
                       format_func=lambda v: "Anyone" if v == 0 else f"{v}+ {unit}", key=f"sbs_min_{disc}_{base.kind}")
names = sorted(table.player.unique())
highlight = c7.selectbox("Find a player", ["—"] + names, key="sbs_find")
only = t2.multiselect("Only these players", names, key="sbs_only", placeholder="Everyone (or pick players to compare)")
highlight = "" if highlight == "—" else highlight

stat_label = st.pills("Stat", [s.label for s in defs], default=defs[0].label, key=f"sbs_stat_{disc}") or defs[0].label
stat = next(s for s in defs if s.label == stat_label)

best = view == "Best"
pool = table[table[stat.column].notna() & (table[min_col] >= minimum)]
if only:
    pool = pool[pool.player.isin(only)]
if stat.keepers_only:
    pool = pool[pool.stumpings > 0]
ranked = rank(pool, stat, best=best)
shown = ranked.head(top)

better = "Higher is better." if stat.better == "high" else "Lower is better."
where = {"Any": "", "Openers (1-2)": ", batting as openers", "No. 3": ", batting at no. 3"}.get(
    position, f", batting at {position}")
st.markdown(f"<p class='statdef'><b>{stat.label}</b>: {stat.definition} <span class='note'>{section}"
            f"{'' if season == 'All seasons' else ' ' + season}{where}: {len(pool)} players qualify "
            f"({'anyone' if not minimum else f'{minimum}+ {unit}'}). {better}</span></p>", unsafe_allow_html=True)

if pool.empty:
    st.warning("Nobody qualifies with these settings. Lower the minimum or pick another season.")
    st.stop()

left, right = st.columns(2, gap="medium")
with left:
    with st.container(border=True):
        st.markdown(f"**{view} {min(top, len(pool))} · {stat.label}**")
        st.plotly_chart(ranked_bars(shown, stat, best, highlight), width="stretch", config=CONFIG, key="sbs_bars")
with right:
    with st.container(border=True):
        d = stat.dot
        st.markdown(f"**Where everyone sits · {d.y_label} vs {d.x_label.lower()}**")
        st.plotly_chart(dot_chart(pool, shown, stat, best, highlight), width="stretch", config=CONFIG, key="sbs_dots")
        better_side = "below" if d.better_below else "above"
        explain_list([
            ("line", f"<b>Dashed line</b>: the average player in this section{where}: {d.line_label}. A dot on the line is exactly average."),
            ("shade", f"<b>Shaded area ({better_side} the line)</b>: {d.below if d.better_below else d.above} This is the better side."),
            ("", f"<b>{'Above' if d.better_below else 'Below'} the line</b>: {d.above if d.better_below else d.below}"),
            ("", f"<b>Further right</b>: {d.right} The further right a dot is, the more you can trust its position."),
            ("dot" + ("" if best else " neg"), "<b>Coloured dots</b>: the players ranked on the left (top 5 named). Grey dots: everyone else who qualifies."),
        ])

# full figures
if disc == "Batting":
    cols = {"player": "Player", "teams": "Team", "matches": "Mat", "innings": "Inns", "not_outs": "NO", "runs": "Runs",
            "balls": "Balls", "high_score_text": "HS", "average": "Avg", "strike_rate": "SR", "hundreds": "100s",
            "fifties": "50s", "ducks": "0s", "fours": "4s", "sixes": "6s", "boundary_pct": "Bdry %",
            "runs_above_average": "Runs above avg"}
elif disc == "Bowling":
    last = ("dot_pct", "Dot %") if base.has_dots else ("maidens", "Mdns")
    cols = {"player": "Player", "teams": "Team", "innings": "Inns", "balls": "Balls", "runs": "Runs", "wickets": "Wkts",
            "best": "BBI", "best_match": "BBM", "average": "Avg", "economy": "Econ", "strike_rate": "SR", last[0]: last[1],
            "hauls": "4w+", "five_fors": "5w", "runs_saved": "Runs saved"}
else:
    cols = {"player": "Player", "teams": "Team", "matches": "Mat", "catches": "Ct", "stumpings": "St", "dismissals": "Total"}
if base.kind != "multi":
    cols.pop("best_match", None)  # one innings each: best in a match is always the same as best in an innings
if stat.column not in cols:  # the ranked stat is always in the table (e.g. 50+ scores)
    cols = {**dict(list(cols.items())[:3]), stat.column: stat.label, **dict(list(cols.items())[3:])}
out = shown[list(cols)].rename(columns=cols).reset_index(drop=True)
out.index = out.index + 1
roles = A.role_labels(career, sec_ids, base.kind).set_index("player")
out.insert(2, "Role", [" · ".join([roles.role[p]] + list(roles.tags[p])) if p in roles.index else "–" for p in shown.player])
# decimals as text so a missing value reads "–" (never dismissed, no wicket) rather than "None"
two_dp = {"economy"}
for k, v in cols.items():
    if k in ("average", "strike_rate", "boundary_pct", "runs_above_average", "runs_saved", "dot_pct", "economy"):
        out[v] = [fmt(x, 2 if k in two_dp else 1) for x in out[v]]
with st.container(border=True):
    st.markdown(f"**Full figures for the players ranked above** · sorted by {stat.label.lower()}")
    st.dataframe(out.style.set_properties(subset=[cols[stat.column]], **{"font-weight": "700"}),
                 width="stretch", height=min(35 * (len(out) + 1) + 3, 720),
                 column_config={"Role": st.column_config.TextColumn("Role", width=104,
                                                                    help="From where they bat and how much they bowl in this section"),
                                "Player": st.column_config.TextColumn("Player", width=112),
                                "Team": st.column_config.TextColumn("Team", width=128)}
                 | {v: st.column_config.Column(v, width=54) for k, v in cols.items()
                    if k not in ("player", "teams")})
    st.download_button("Download this table (CSV)", out.to_csv(index_label="#").encode(),
                       file_name=f"{section} {stat.label}.csv".replace("/", "-"), key="sbs_dl")
