import numpy as np
import pandas as pd
import streamlit as st

from ccstats import analysis as A
from ccstats import deep as D
from ccstats.stats import POSITION_GROUPS, Scope, ordinal, rank, stat_definitions
from ui import state
from ui.charts import CONFIG, dot_chart, fmt, ranked_bars
from ui.theme import chart_note, explain_list, page_header

career = state.current()
if career is None:
    st.info("Load a career on the Home page first.")
    st.stop()
state.stop_if_no_matches(career)

page_header("Stat by stat", "Who's best, who's worst",
            "Pick a section and a stat. The left chart ranks players on that one stat; the right chart shows where every "
            "qualifying player sits.")

m = career.matches
sections = m.section.value_counts()
labels = {s: f"{s} · {n} match{'es' if n > 1 else ''}" for s, n in sections.items()}

c1, c2, c3 = st.columns([2.1, 1.5, 1.5])  # room for all three discipline buttons
state.recall("sbs_section", "section", list(sections.index))
section = c1.selectbox("Section", list(sections.index), format_func=labels.get, key="sbs_section", on_change=state.remember("sbs_section", "section"))
combine = c1.toggle("Combine sections", key="sbs_combine",
                    help="Count several sections together. Every player is then measured against the average of the "
                         "chosen sections, so only combine sections of the same kind (e.g. two T20 leagues).")
chosen = [section]
if combine:
    others = [x for x in sections.index if x != section]
    chosen = [section] + st.multiselect("Sections to add", others, key="sbs_more_sections", format_func=labels.get,
                                        placeholder="Pick sections to add to " + section)
in_sections = m[m.section.isin(chosen)]
seasons = sorted(in_sections.season.unique(), reverse=True)
picked_seasons = c2.multiselect("Seasons", seasons, key="sbs_seasons", placeholder="All seasons")
disc = c3.segmented_control("Discipline", ["Batting", "Bowling", "Fielding"], default="Batting", required=True, key="sbs_disc") or "Batting"

f1, f2, f3, f4 = st.columns([1.4, 1.6, 1.1, 1.2])
events = sorted(in_sections.event.unique())
picked_events = f1.multiselect("Competitions", events, key="sbs_events", placeholder="All competitions",
                               disabled=len(events) < 2,
                               help="A section can hold more than one competition: e.g. ODIs has World Cups and "
                                    "bilateral series.")
base_scope = Scope(sections=chosen, seasons=picked_seasons, events=picked_events)
sec_ids = base_scope.match_ids(m)
here = m[m.match_id.isin(sec_ids)]
teams_here = sorted(set(here.home) | set(here.away))
picked_teams = f2.multiselect("Teams", teams_here, key="sbs_teams", placeholder="All teams",
                              help="Only the players' games for these teams count. The average player is still the "
                                   "whole section's.")
VENUES = {"Home": "home", "Away": "away", "Neutral": "neutral"}
picked_venues = f3.multiselect("Venue", list(VENUES), key="sbs_venues", placeholder="Anywhere",
                               help="From the player's own team: home games, away games or neutral grounds. The "
                                    "average player is then the average at these venues too.")
HOW = ["caught", "bowled", "lbw", "run out", "stumped", "not out", "retired hurt"]
picked_how = []
if disc == "Batting":
    picked_how = f4.multiselect("How out", HOW, key="sbs_how", placeholder="Any innings",
                                help="Only innings that ended this way (the average batter too).")

positions: list[int] = []
where = ""
if disc == "Batting":
    p1, p2 = st.columns([4, 1.2], vertical_alignment="bottom")
    single = p2.toggle("Single positions", key="sbs_pos_single", help="Pick positions 1 to 11 one by one instead of groups.")
    if single:
        picked_pos = p1.pills("Batting positions", [str(i) for i in range(1, 12)], selection_mode="multi",
                              key="sbs_pos_one", help="Only count innings at these positions. The average line is then "
                                                      "the average batter at these positions.") or []
        positions = sorted(int(x) for x in picked_pos)
        if positions:
            where = ", batting at no. " + ", ".join(str(x) for x in positions)
    else:
        picked_pos = p1.pills("Batting positions", list(POSITION_GROUPS), selection_mode="multi", key="sbs_pos",
                              help="Only count innings at these positions; pick more than one to combine them. The "
                                   "average line is then the average batter at these positions, so openers are "
                                   "measured against openers.") or []
        positions = sorted({x for g in picked_pos for x in POSITION_GROUPS.get(g, [])})
        if picked_pos:
            where = ", batting " + " + ".join(("as openers" if g == "Openers (1-2)" else f"at {g.lower()}")
                                               for g in sorted(picked_pos, key=list(POSITION_GROUPS).index))
scope = Scope(sections=chosen, seasons=picked_seasons, events=picked_events, positions=positions,
              venues=[VENUES[v] for v in picked_venues], how_out=picked_how if disc == "Batting" else [],
              teams=picked_teams)
if picked_how:
    where += ", innings ending " + " / ".join(picked_how)
if picked_venues:
    where += ", " + " / ".join(v.lower() for v in picked_venues) + " games"
bat, bowl, fld, base = state.tables(career, scope)
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
view = c4.segmented_control("Ranking", ["Best", "Worst"], default="Best", required=True, key="sbs_view",
                            disabled=disc == "Fielding") or "Best"
if disc == "Fielding":
    view = "Best"
top = c5.selectbox("Show", [10, 20, 50, 10_000], format_func=lambda v: "Everyone" if v == 10_000 else f"Top {v}", key="sbs_top")
minimum = c6.selectbox("Minimum to qualify", options, index=options.index(default_min),
                       format_func=lambda v: "Anyone" if v == 0 else f"{v}+ {unit}", key=f"sbs_min_{disc}_{base.kind}")
names = sorted(table.player.unique())
highlight = c7.selectbox("Find a player", ["—"] + names, key="sbs_find")
only = st.multiselect("Only these players", names, key="sbs_only", placeholder="Everyone (or pick players to compare)")
highlight = "" if highlight == "—" else highlight

stat_label = st.pills("Stat", [s.label for s in defs], default=defs[0].label, required=True, key=f"sbs_stat_{disc}") or defs[0].label
stat = next(s for s in defs if s.label == stat_label)
raw_stat = stat

# ---------------------------------------------------------------- 87 / 88 · fair: against each part's own average
season_list = picked_seasons or sorted(in_sections.season.unique())
measures = ["Everyone in this selection"]
if len(chosen) > 1:
    measures.append("Each section's own average")
if len(season_list) > 1:
    measures.append("Each season's own average")
measure = measures[0]
if len(measures) > 1:
    measure = st.segmented_control(
        "Measure against", measures, default=measures[0], required=True, key="sbs_measure",
        help="Each section's own average: every player is first compared with the average player of each section they "
             "played in, then that is combined, so a T20 strike rate and a Test strike rate can be added up fairly. "
             "Each season's own average: the same, season by season, so a high-scoring year doesn't flatter anyone.") \
        or measures[0]
if measure != measures[0]:
    split = "section" if measure.startswith("Each section") else "season"
    cache = st.session_state.setdefault("stats_cache", {})
    fkey = ("fair", career.name, id(career), repr(scope), disc, stat.id, split)
    if fkey not in cache:
        cache[fkey] = D.fair_index(career, scope, disc, stat.id, split)
    fair, funit = cache[fkey]
    table = table.assign(fair=table.player.map(fair))
    stat = D.fair_stat(stat, funit, split)

best = view == "Best"
pool = table[table[stat.column].notna() & (table[min_col] >= minimum)]
if only:
    pool = pool[pool.player.isin(only)]
if stat.keepers_only:
    pool = pool[pool.stumpings > 0]
ranked = rank(pool, stat, best=best)
shown = ranked.head(top)

better = "Higher is better." if stat.better == "high" else "Lower is better."
title = " + ".join(chosen) + (" (against the average of the chosen sections)" if len(chosen) > 1 else "")
if picked_events:
    title += " · " + ", ".join(picked_events)
if picked_seasons:
    title += " " + ", ".join(sorted(picked_seasons))
if picked_teams:
    title += " · for " + ", ".join(picked_teams)
st.markdown(f"<p class='statdef'><b>{stat.label}</b>: {stat.definition} <span class='note'>{title}"
            f"{where}: {len(pool)} players qualify "
            f"({'anyone' if not minimum else f'{minimum}+ {unit}'}). {better}</span></p>", unsafe_allow_html=True)

if pool.empty:
    st.warning("Nobody qualifies with these settings. Lower the minimum or pick another season.")
    st.stop()

# Find a player: where they rank, or why they aren't on the charts
if highlight:
    rk = ranked.reset_index(drop=True)
    hit = rk.index[rk.player == highlight]
    row = table[table.player == highlight]
    if len(hit):
        pos = int(hit[0]) + 1
        st.info(f"🔎 **{highlight}**: {ordinal(pos)} of {len(rk)} on {stat.label.lower()} "
                f"({fmt(rk.at[hit[0], stat.column], stat.decimals)}), highlighted on both charts"
                + (f" (outside the top {top} in the bar chart: pick a bigger Show to see their bar)." if pos > top else "."))
    else:
        if only and highlight not in only:
            why = "they're not in Only these players"
        elif len(row) and row[stat.column].isna().all():
            why = f"they have no {stat.label.lower()} figure yet"
        elif stat.keepers_only:
            why = "this stat counts wicketkeepers only"
        elif len(row) and int(row[min_col].max()) < minimum:
            why = (f"{int(row[min_col].max())} {unit} so far, under the minimum of {minimum}: set Minimum to qualify "
                   "lower to see them")
        else:
            why = "they don't qualify with these settings"
        st.info(f"🔎 **{highlight}** isn't on these charts: {why}.")

left, right = st.columns(2, gap="medium")
with left:
    with st.container(border=True):
        st.markdown(f"**{view} {min(top, len(pool))} · {stat.label}**")
        st.plotly_chart(ranked_bars(shown, stat, best, highlight), width="stretch", config=CONFIG, key="sbs_bars")
        r0 = shown.iloc[0]
        v0 = r0[stat.column]
        ref = stat.reference
        vs = (f", {(v0 - ref) / abs(ref) * 100:+.0f}% on the average of {fmt(ref, max(stat.decimals, 1))}"
              if ref is not None and np.isfinite(ref) and ref else "")
        chart_note(f"{'Top' if best else 'Bottom'}: {r0.player} with {fmt(v0, stat.decimals)}{vs}. "
                   f"{len(pool)} players qualify.",
                   f"{stat.definition} Ranks who is {'best' if best else 'worst'} at this one thing.")
with right:
    with st.container(border=True):
        d = stat.dot
        st.markdown(f"**Where everyone sits · {d.y_label} vs {d.x_label.lower()}**")
        st.plotly_chart(dot_chart(pool, shown, stat, best, highlight), width="stretch", config=CONFIG, key="sbs_dots")
        better_side = "below" if d.better_below else "above"
        xs, ys = pool[d.x].astype(float), pool[d.y].astype(float)
        line_y = xs * d.value if d.line == "slope" else pd.Series(d.value, index=pool.index)
        on_better = ((ys < line_y) if d.better_below else (ys > line_y)).mean() * 100
        chart_note(f"{on_better:.0f}% of the {len(pool)} qualifying players are on the better side of the average line "
                   f"({d.line_label}).",
                   "Shows everyone at once, so you can tell a great figure from a lucky one: the further right a dot, "
                   "the more games it rests on.")
        explain_list([
            ("line", f"<b>Dashed line</b>: the average player in {'these sections' if len(chosen) > 1 else 'this section'}{where}: {d.line_label}. A dot on the line is exactly average."),
            ("shade", f"<b>Shaded area ({better_side} the line)</b>: {d.below if d.better_below else d.above} This is the better side."),
            ("", f"<b>{'Above' if d.better_below else 'Below'} the line</b>: {d.above if d.better_below else d.below}"),
            ("", f"<b>Further right</b>: {d.right} The further right a dot is, the more you can trust its position."),
            ("dot" + ("" if best else " neg"), "<b>Coloured dots</b>: the players ranked on the left (the top 4 named; hover any dot for its figures). Grey dots: everyone else who qualifies."),
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
# 85 · how good each figure is among everyone who qualifies
pctl = D.percentiles(pool, stat.column, stat.better)
spot = cols[stat.column] if stat.column in cols else stat.label
out.insert(list(out.columns).index(spot) + 1, "Rank %", [D.top_text(pctl.get(i)) for i in shown.index])
# 86 · the same figure the season before (one season picked)
if len(picked_seasons) == 1 and stat.column != "fair":
    ch, prev = D.change_since(career, scope, disc, stat.column)
    if prev:
        def arrow(v):
            if v is None or not np.isfinite(v):
                return "–"
            good = (v > 0) == (stat.better == "high")
            return ("▲ " if good else "▼ ") + (f"{v:+.{stat.decimals}f}" if stat.decimals else f"{v:+.0f}") if v else "▬ 0"
        out.insert(list(out.columns).index("Rank %") + 1, f"v {prev}", [arrow(ch.get(p, np.nan)) for p in shown.player])
roles = A.role_labels(career, scope.match_ids(m), base.kind).set_index("player")
out.insert(2, "Role", [" · ".join([roles.role[p]] + list(roles.tags[p])) if p in roles.index else "–" for p in shown.player])
# decimals as text so a missing value reads "–" (never dismissed, no wicket) rather than "None"
two_dp = {"economy"}
for k, v in cols.items():
    if k in ("average", "strike_rate", "boundary_pct", "runs_above_average", "runs_saved", "dot_pct", "economy", "fair"):
        out[v] = ([f"{x:+.0f}%" if np.isfinite(x) else "–" for x in out[v]] if k == "fair" and "%" in v else
                  [fmt(x, 2 if k in two_dp else 1) for x in out[v]])
with st.container(border=True):
    st.markdown(f"**Full figures for the players ranked above** · sorted by {stat.label.lower()}")
    st.dataframe(out.style.set_properties(subset=[cols[stat.column]], **{"font-weight": "700"}),
                 width="stretch", height=min(35 * (len(out) + 1) + 3, 720),
                 column_config={"Role": st.column_config.TextColumn("Role", width=104,
                                                                    help="From where they bat and how much they bowl in this section"),
                                "Player": st.column_config.TextColumn("Player", width=112),
                                "Team": st.column_config.TextColumn("Team", width=128)}
                 | {v: st.column_config.Column(v, width=110 if k == "fair" else 54, help=stat.definition if k == "fair" else None)
                    for k, v in cols.items() if k not in ("player", "teams")})
    notes_ = ["Rank %: where the figure sits among everyone who qualifies (top 5% = better than 95% of them)."]
    if len(picked_seasons) == 1:
        notes_.append("v last season: the same figure the season before (▲ better, ▼ worse).")
    else:
        notes_.append("Pick one season to see each figure against the season before.")
    st.caption(" ".join(notes_))
    st.download_button("Download this table (CSV)", out.to_csv(index_label="#").encode(),
                       file_name=f"{' + '.join(chosen)} {stat.label}.csv".replace("/", "-"), key="sbs_dl")
