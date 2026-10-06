import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ccstats import analysis as A
from ccstats.stats import Scope, stat_definitions
from ui import state
from ui.charts import CONFIG, _axis, _layout, fmt
from ui.theme import chart_note, colours, page_header

career = state.current()
if career is None:
    st.info("Load a career on the Home page first.")
    st.stop()

page_header("Compare players", "Side by side",
            "Pick a section and up to four players. Each chart shows one stat, with the section average as a dashed line.")
m = career.matches
c1, c2, c3 = st.columns([2, 1, 1])
sections = m.section.value_counts()
state.recall("cp_section", "section", list(sections.index))
section = c1.selectbox("Section", list(sections.index), key="cp_section", on_change=state.remember("cp_section", "section"),
                       format_func=lambda s: f"{s} · {sections[s]} matches")
seasons = sorted(m[m.section == section].season.unique(), reverse=True)
state.recall("cp_season", "season", ["All seasons"] + seasons)
season = c2.selectbox("Season", ["All seasons"] + seasons, key="cp_season", on_change=state.remember("cp_season", "season"))
disc = c3.segmented_control("Discipline", ["Batting", "Bowling"], default="Batting", key="cp_disc") or "Batting"
scope = Scope(sections=[section], seasons=[] if season == "All seasons" else [season])
bat, bowl, _, base = state.tables(career, scope)
table = bat if disc == "Batting" else bowl
table = table[table.innings > 0]
defs = stat_definitions(base)["bat" if disc == "Batting" else "bowl"]

default = list(table.sort_values("runs" if disc == "Batting" else "wickets", ascending=False).player.head(2))
chosen = st.multiselect("Players (up to 4)", sorted(table.player), default=default, max_selections=4, key=f"cp_players_{disc}_{section}_{season}")
if len(chosen) < 2:
    st.info("Pick at least two players.")
    st.stop()

c = colours()
palette = [c["s1"], c["s2"], "#1baf7a", "#eda100"]  # fixed order: the first player you pick is always blue
colour_of = {p: palette[i] for i, p in enumerate(chosen)}
rows = table.set_index("player").loc[chosen]

# ---------------------------------------------------------------- summary table
if disc == "Batting":
    fields = [("Innings", "innings", 0), ("Runs", "runs", 0), ("Average", "average", 2), ("Strike rate", "strike_rate", 1),
              ("High score", "high_score_text", None), ("100s", "hundreds", 0), ("50s", "fifties", 0), ("Ducks", "ducks", 0),
              ("4s", "fours", 0), ("6s", "sixes", 0), ("Boundary %", "boundary_pct", 1), ("Runs above average", "runs_above_average", 1)]
else:
    fields = [("Innings", "innings", 0), ("Wickets", "wickets", 0), ("Average", "average", 2), ("Economy", "economy", 2),
              ("Strike rate", "strike_rate", 1), ("Best", "best", None), ("4+ hauls", "hauls", 0), ("Runs saved", "runs_saved", 1)]
summary = pd.DataFrame({p: [rows.loc[p, col] if d is None else fmt(rows.loc[p, col], d) for _, col, d in fields] for p in chosen},
                       index=[f[0] for f in fields])
with st.container(border=True):
    st.markdown(f"**{section}{'' if season == 'All seasons' else ' ' + season}**")
    st.dataframe(summary, width="stretch", height=35 * (len(summary) + 1) + 3)  # every row visible

# ---------------------------------------------------------------- one chart per stat
st.subheader("Stat by stat", anchor=False)
cols = st.columns(2, gap="medium")
for i, stat in enumerate(defs):
    vals = rows[stat.column]
    with cols[i % 2]:
        with st.container(border=True):
            better = "higher is better" if stat.better == "high" else "lower is better"
            st.markdown(f"**{stat.label}** · {better}")
            fig = go.Figure(go.Bar(
                x=[v if pd.notna(v) else 0 for v in vals], y=chosen, orientation="h",
                marker=dict(color=[colour_of[p] for p in chosen], line=dict(width=0)),
                text=[fmt(v, stat.decimals) for v in vals], textposition="outside", cliponaxis=False,
                textfont=dict(size=12, color=c["ink2"]), hovertemplate="<b>%{y}</b>: %{text}<extra></extra>"))
            shapes, ann = [], []
            if stat.reference is not None and np.isfinite(stat.reference):
                shapes.append(dict(type="line", x0=stat.reference, x1=stat.reference, xref="x", y0=0, y1=1, yref="paper",
                                   line=dict(color=c["muted"], width=1, dash="dash"), layer="below"))
                ann.append(dict(x=stat.reference, y=1, yref="paper", xanchor="left", yanchor="bottom", showarrow=False,
                                text=f"section average {fmt(stat.reference, max(stat.decimals, 1))}",
                                font=dict(size=11, color=c["muted"])))
            finite = [float(v) for v in vals if pd.notna(v)]
            signed = stat.column in ("runs_above_average", "runs_saved")
            extra = {}
            if stat.decimals == 0 and max(finite, default=0) <= 8:
                extra["dtick"] = 1  # counts never get half-way ticks
            if not any(finite):
                extra["range"] = [0, 1]  # everyone on 0: keep the axis starting at 0
            fig.update_layout(**_layout(c, height=70 + 42 * len(chosen), bargap=0.35, shapes=shapes, annotations=ann,
                                        xaxis=_axis(c, stat.label, zeroline=True, zerolinecolor=c["axis"],
                                                    rangemode="normal" if signed else "tozero", **extra),
                                        yaxis=dict(autorange="reversed", showgrid=False, tickfont=dict(size=12, color=c["ink"]),
                                                   automargin=True),
                                        margin=dict(l=10, r=52, t=24, b=10)))
            st.plotly_chart(fig, width="stretch", config=CONFIG, key=f"cp_{stat.id}")
            ok = [(p, float(v)) for p, v in zip(chosen, vals) if pd.notna(v)]
            if ok:
                bp, bv = (max if stat.better == "high" else min)(ok, key=lambda x: x[1])
                ref = stat.reference
                vs = (f" ({(bv - ref) / abs(ref) * 100:+.0f}% on the section average of {fmt(ref, max(stat.decimals, 1))})"
                      if ref is not None and np.isfinite(ref) and ref else "")
                shows = f"{bp} is best on this one: {fmt(bv, stat.decimals)}{vs}."
            else:
                shows = "No figures yet for these players."
            chart_note(shows, f"{stat.definition}")

# ---------------------------------------------------------------- career curves
ids = scope.match_ids(m)
with st.container(border=True):
    what = "runs" if disc == "Batting" else "wickets"
    st.markdown(f"**Career so far · total {what} after each innings**")
    fig = go.Figure()
    for p in chosen:
        d = A.batting_innings(career, ids, p) if disc == "Batting" else A.bowling_spells(career, ids, p)
        y = d[what].cumsum().tolist()
        fig.add_trace(go.Scatter(x=list(range(1, len(y) + 1)), y=y, mode="lines", name=p,
                                 line=dict(color=colour_of[p], width=2.5),
                                 hovertemplate=f"<b>{p}</b><br>after innings %{{x}}: %{{y}} {what}<extra></extra>"))
        if y:
            fig.add_annotation(x=len(y), y=y[-1], text=p, xanchor="left", xshift=6, showarrow=False,
                               font=dict(size=12, color=colour_of[p]))
    fig.update_layout(**_layout(c, height=380, showlegend=True, legend=dict(orientation="h", y=1.1, x=0),
                                xaxis=_axis(c, "Innings played"), yaxis=_axis(c, f"Total {what}"),
                                margin=dict(l=10, r=90, t=40, b=10)))
    st.plotly_chart(fig, width="stretch", config=CONFIG, key="cp_curve")
    ends = []
    for p in chosen:
        d = A.batting_innings(career, ids, p) if disc == "Batting" else A.bowling_spells(career, ids, p)
        if len(d):
            ends.append((p, int(d[what].sum()), len(d)))
    if ends:
        lead = max(ends, key=lambda x: x[1])
        rate = max(ends, key=lambda x: x[1] / x[2])
        shows = (f"{lead[0]} has the most {what}: {lead[1]} in {lead[2]} innings. "
                 f"{rate[0]} gets there fastest: {rate[1] / rate[2]:.{2 if what == 'wickets' else 1}f} an innings.")
    else:
        shows = "No innings yet."
    chart_note(shows, "Shows how each career has built up. A steeper line means more per innings; where a line ends "
                      "shows how many innings they've played.")
