import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ccstats import analysis as A
from ccstats.stats import WICKET_VALUE, Scope
from ui import state
from ui.charts import player_profile, CONFIG, _axis, _layout, fmt
from ui.theme import colours, explain_list, page_header

career = state.current()
if career is None:
    st.info("Load a career on the Home page first.")
    st.stop()

m = career.matches
page_header("Team vs team", "Head to head",
            "Pick a section and two teams. Switch between overall, home and away (each team's own), or only the games they played against each other.")
r1 = st.columns([2, 1, 1.5, 1.5])
sections = m.section.value_counts()
section = r1[0].selectbox("Section", list(sections.index), key="tv_section", format_func=lambda s: f"{s} · {sections[s]} matches")
seasons = sorted(m[m.section == section].season.unique(), reverse=True)
season = r1[1].selectbox("Season", ["All seasons"] + seasons, key="tv_season")
base_scope = Scope(sections=[section], seasons=[] if season == "All seasons" else [season])
here = m[m.match_id.isin(base_scope.match_ids(m))]
teams = sorted(set(here.home) | set(here.away))
if len(teams) < 2:
    st.info("This section needs at least two teams.")
    st.stop()
a = r1[2].selectbox("Team A", teams, key="tv_a")
b = r1[3].selectbox("Team B", [t for t in teams if t != a], key="tv_b")
r2 = st.columns([1.7, 2.6, 1.7])
venue_label = r2[0].segmented_control("Venue", ["Overall", "Home", "Away"], default="Overall", key="tv_venue") or "Overall"
which = r2[1].segmented_control("Matches", ["All matches", "Only against each other"], default="All matches", key="tv_which") or "All matches"
venue = venue_label.lower().replace("overall", "all")
h2h = which != "All matches"


def scope_for(team, other):
    return Scope(sections=[section], seasons=base_scope.seasons, team=team, venue=venue, opponent=other if h2h else "")


ids_a, ids_b = scope_for(a, b).match_ids(m), scope_for(b, a).match_ids(m)
if venue != "all" and here.neutral.all():
    st.info(f"{section} matches are played at neutral venues, so there are no home or away games. Choose Overall.")
    st.stop()
if len(ids_a) == 0 or len(ids_b) == 0:
    st.info("One of the teams has no matches with these settings.")
    st.stop()

c = colours()
col_a, col_b = c["s1"], c["s2"]
rec_a = A.team_table(career, ids_a).set_index("team").loc[a]
rec_b = A.team_table(career, ids_b).set_index("team").loc[b]
limited = np.isfinite(rec_a.nrr) and np.isfinite(rec_b.nrr)


def high_total(team, ids):
    i = career.innings[career.innings.match_id.isin(ids) & (career.innings.team == team)]
    return int(i.runs.max()) if len(i) else 0


def tile(col, team, r, other, colour):
    win = lambda x, y: f"color:{c['good']}" if x > y else ""
    extra = (f"<div><span>Net run rate</span><strong style='{win(r.nrr, other.nrr)}'>{r.nrr:+.2f}</strong></div>" if limited
             else f"<div><span>Drawn</span><strong>{int(r.drawn)}</strong></div>")
    col.markdown(
        f"<div class='kpi' style='border-top:3px solid {colour}'><span style='font-size:22px;letter-spacing:.02em;color:{c['ink']}'>{team}</span>"
        f"<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:6px 12px;margin-top:8px'>"
        f"<div><span>Played</span><strong>{int(r.played)}</strong></div>"
        f"<div><span>Won–Lost</span><strong style='{win(r.won, other.won)}'>{int(r.won)}–{int(r.lost)}</strong></div>"
        f"<div><span>Win %</span><strong style='{win(r.win_pct, other.win_pct)}'>{r.win_pct:.0f}</strong></div>{extra}"
        f"<div><span>Highest</span><strong>{high_total(team, ids_a if team == a else ids_b)}</strong></div></div></div>",
        unsafe_allow_html=True)


t1, t2 = st.columns(2, gap="medium")
tile(t1, a, rec_a, rec_b, col_a)
tile(t2, b, rec_b, rec_a, col_b)
st.write("")

# ---------------------------------------------------------------- tale of the tape
rows = [("Win %", "win_pct", "high", 0), ("Runs per wicket (batting)", "rpw_for", "high", 1), ("Run rate (batting)", "rr_for", "high", 2),
        ("Avg score batting first", "first_innings_avg", "high", 0), ("Runs per wicket conceded", "rpw_against", "low", 1),
        ("Economy (bowling)", "rr_against", "low", 2), ("Wickets taken per match", "wkts_per_match", "high", 1)]
labels, ax, bx, at, bt, aop, bop = [], [], [], [], [], [], []
a_wins = b_wins = 0
for label, col, better, d in rows:
    va, vb = rec_a[col], rec_b[col]
    if not (np.isfinite(va) and np.isfinite(vb)):
        continue
    top = max(abs(va), abs(vb)) or 1
    a_better = va != vb and ((better == "high") == (va > vb))
    b_better = va != vb and not a_better
    a_wins += a_better
    b_wins += b_better
    labels.append(label)
    ax.append(-va / top); bx.append(vb / top)
    at.append(("✓ " if a_better else "") + fmt(va, d)); bt.append(fmt(vb, d) + (" ✓" if b_better else ""))
    aop.append(1 if a_better else 0.45); bop.append(1 if b_better else 0.45)
left, right = st.columns([1.1, 1], gap="medium")
with left:
    with st.container(border=True):
        st.markdown("**Tale of the tape**")
        verdict = (f"Level: {a_wins} measures each." if a_wins == b_wins else
                   f"{a if a_wins > b_wins else b} come out ahead on {max(a_wins, b_wins)} of {a_wins + b_wins} measures.")
        st.markdown(f"<p class='statdef'><b>{verdict}</b></p>", unsafe_allow_html=True)
        fig = go.Figure([
            go.Bar(x=ax[::-1], y=labels[::-1], orientation="h", name=a, marker=dict(color=col_a, opacity=aop[::-1]),
                   text=at[::-1], textposition="outside", cliponaxis=False, textfont=dict(size=12, color=c["ink"]),
                   hovertemplate=f"{a}: %{{text}}<extra></extra>"),
            go.Bar(x=bx[::-1], y=labels[::-1], orientation="h", name=b, marker=dict(color=col_b, opacity=bop[::-1]),
                   text=bt[::-1], textposition="outside", cliponaxis=False, textfont=dict(size=12, color=c["ink"]),
                   hovertemplate=f"{b}: %{{text}}<extra></extra>")])
        fig.update_layout(**_layout(c, barmode="overlay", bargap=0.35, height=60 + 48 * len(labels), showlegend=True,
                                    legend=dict(orientation="h", x=0.5, xanchor="center", y=1.08),
                                    xaxis=dict(range=[-1.7, 1.7], showticklabels=False, showgrid=False, zeroline=True,
                                               zerolinecolor=c["axis"], fixedrange=True),
                                    yaxis=dict(showgrid=False, tickfont=dict(size=12, color=c["ink"]), automargin=True, fixedrange=True),
                                    margin=dict(l=10, r=10, t=36, b=10)))
        st.plotly_chart(fig, width="stretch", config=CONFIG, key="tv_tape")
        st.caption("Each row is one measure. The longer bar is the bigger number; the tick marks the better team "
                   "(for runs conceded and economy, lower is better).")
with right:
    with st.container(border=True):
        st.markdown("**Head to head**")
        meet = here[((here.home == a) & (here.away == b)) | ((here.home == b) & (here.away == a))]
        if venue == "home":
            meet = meet[(meet.home == a) & ~meet.neutral]
        elif venue == "away":
            meet = meet[(meet.away == a) & ~meet.neutral]
        aw, bw = int((meet.winner == a).sum()), int((meet.winner == b).sum())
        if meet.empty:
            st.caption("They haven't met with these settings.")
        else:
            st.markdown(f"**{len(meet)} meeting{'s' * (len(meet) != 1)}:** {a} {aw} – {bw} {b}"
                        + (f", {len(meet) - aw - bw} other" if len(meet) - aw - bw else ""))
            show = meet.sort_values("date", ascending=False)
            st.dataframe(pd.DataFrame({"Date": show.date.dt.strftime("%d %b %Y"), "Match": [f"{h} v {w}" for h, w in zip(show.home, show.away)],
                                       "Stage": show.stage, "Result": show.result}), hide_index=True, width="stretch")

# ---------------------------------------------------------------- players
_, _, _, base = state.tables(career, base_scope)  # the section's averages
ta = state.tables(career, scope_for(a, b), by_team=True)
tb = state.tables(career, scope_for(b, a), by_team=True)
bat_a, bowl_a = ta[0][ta[0].team == a].copy(), ta[1][ta[1].team == a].copy()
bat_b, bowl_b = tb[0][tb[0].team == b].copy(), tb[1][tb[1].team == b].copy()
kind = base.kind
for d in (bat_a, bat_b):
    d["runs_above_average"] = (d.runs - d.outs * base.average) if kind == "multi" else (d.runs - d.balls * base.strike_rate / 100)
for d in (bowl_a, bowl_b):
    d["runs_saved"] = (d.wickets * base.bowl_average - d.runs) if kind == "multi" else (
        (d.balls * base.economy / 6 - d.runs) + (d.wickets - d.balls / base.bowl_strike_rate) * WICKET_VALUE[kind])


def two_team_scatter(key, da, db, x, y, x_label, y_label, slope, line_label, hover):
    alld = pd.concat([da, db])
    xmax = max(1.0, float(alld[x].max() if len(alld) else 1)) * 1.08
    ymax = max(1.0, float(alld[y].max() if len(alld) else 1)) * 1.15
    fig = go.Figure()
    for d, colour, team in ((da, col_a, a), (db, col_b, b)):
        fig.add_trace(go.Scatter(x=d[x], y=d[y], mode="markers", name=team, marker=dict(size=11, color=colour, line=dict(color=c["surface"], width=2)),
                                 customdata=[hover(r) for r in d.itertuples()], hovertemplate="%{customdata}<extra></extra>"))
    ann = []
    placed: list[tuple[float, float, int]] = []  # stack names whose dots sit close together
    top = pd.concat([d.sort_values(y, ascending=False).head(3) for d in (da, db)]).sort_values(y, ascending=False)
    for r in top.itertuples():
        nx, ny = getattr(r, x) / xmax, getattr(r, y) / ymax
        shift = 13
        for px, py, ps in placed:
            if abs(px - nx) < 0.14 and abs(py - ny) < 0.05:
                shift = max(shift, ps + 14)
        placed.append((nx, ny, shift))
        ann.append(dict(x=getattr(r, x), y=getattr(r, y), text=r.player, showarrow=False, yshift=shift,
                        font=dict(size=11, color=c["ink2"])))
    ann.append(dict(x=xmax * 0.3, y=slope * xmax * 0.3, xanchor="left", yanchor="top", xshift=6, showarrow=False,
                    text=line_label, font=dict(size=11, color=c["muted"])))
    fig.update_layout(**_layout(c, height=440, showlegend=True, legend=dict(orientation="h", y=1.08, x=0), annotations=ann,
                                shapes=[dict(type="path", path=f"M 0 0 L {xmax} {slope * xmax} L {xmax} {ymax * 3} L 0 {ymax * 3} Z",
                                             xref="x", yref="y", fillcolor=c["shade"], line=dict(width=0), layer="below"),
                                        dict(type="line", xref="x", yref="y", x0=0, y0=0, x1=xmax, y1=slope * xmax,
                                             line=dict(color=c["muted"], width=1, dash="dash"), layer="below")],
                                xaxis=_axis(c, x_label, range=[0, xmax]), yaxis=_axis(c, y_label, range=[0, ymax]),
                                margin=dict(l=10, r=16, t=40, b=10)))
    st.plotly_chart(fig, width="stretch", config=CONFIG, key=key)


st.subheader("Player by player", anchor=False)
left, right = st.columns(2, gap="medium")
with left:
    with st.container(border=True):
        st.markdown("**Batters: runs vs balls faced**")
        two_team_scatter("tv_bat", bat_a[bat_a.balls > 0], bat_b[bat_b.balls > 0], "balls", "runs", "Balls faced", "Runs",
                         base.strike_rate / 100, f"section strike rate {fmt(base.strike_rate, 1)}",
                         lambda r: f"<b>{r.player}</b> · {r.team}<br>{player_profile(r)}")
        explain_list([("dot", f"<b>Blue</b>: {a}. <b>Orange</b>: {b}."),
                      ("line", "<b>Dashed line</b>: the section's average scoring rate."),
                      ("shade", "<b>Shaded area (above the line)</b>: scores faster than the average batter in this section."),
                      ("", "<b>Further right</b>: faced more balls. Top-right dots are the big, quick scorers each side relies on.")])
with right:
    with st.container(border=True):
        st.markdown("**Bowlers: wickets vs balls bowled**")
        two_team_scatter("tv_bowl", bowl_a, bowl_b, "balls", "wickets", "Balls bowled", "Wickets", 1 / base.bowl_strike_rate,
                         f"a wicket every {fmt(base.bowl_strike_rate, 1)} balls",
                         lambda r: f"<b>{r.player}</b> · {r.team}<br>{player_profile(r)}")
        explain_list([("line", "<b>Dashed line</b>: the section's average wicket rate."),
                      ("shade", "<b>Shaded area (above the line)</b>: takes wickets more often than the average bowler."),
                      ("", "<b>Further right</b>: bowled more. Top-right dots are the main strike bowlers.")])


def team_bars(key, da, db, col, label, hover):
    sa, sb = da.sort_values(col, ascending=False), db.sort_values(col, ascending=False)
    rows_ = pd.concat([sb.iloc[::-1], sa.iloc[::-1]])
    lo, hi = min(0, rows_[col].min()), max(0, rows_[col].max())
    pad = (hi - lo) * 0.18 or 1
    fig = go.Figure(go.Bar(x=rows_[col], y=[f"{p} · {t}" for p, t in zip(rows_.player, rows_.team)], orientation="h",
                           marker=dict(color=[col_a if t == a else col_b for t in rows_.team], line=dict(width=0)),
                           text=[("+" if v > 0 else "") + fmt(v, 1) for v in rows_[col]], textposition="outside", cliponaxis=False,
                           textfont=dict(size=11, color=c["ink2"]), customdata=[hover(r) for r in rows_.itertuples()],
                           hovertemplate="%{customdata}<extra></extra>"))
    fig.update_layout(**_layout(c, bargap=0.3, height=max(360, 24 * len(rows_) + 70),
                                xaxis=_axis(c, label, zeroline=True, zerolinecolor=c["axis"], range=[lo - (pad if lo < 0 else 0), hi + pad]),
                                yaxis=dict(showgrid=False, tickfont=dict(size=11, color=c["ink"]), automargin=True),
                                margin=dict(l=10, r=40, t=10, b=10)))
    st.plotly_chart(fig, width="stretch", config=CONFIG, key=key)


left, right = st.columns(2, gap="medium")
with left:
    with st.container(border=True):
        st.markdown("**Every batter: runs above average**")
        team_bars("tv_raa", bat_a[bat_a.innings > 0], bat_b[bat_b.innings > 0], "runs_above_average", "Runs above average",
                  lambda r: f"<b>{r.player}</b> · {r.team}<br>{player_profile(r)}")
        st.caption("Runs scored minus what an average batter in this section would have made. Right of the line beat the average.")
with right:
    with st.container(border=True):
        st.markdown("**Every bowler: runs saved**")
        team_bars("tv_saved", bowl_a, bowl_b, "runs_saved", "Runs saved",
                  lambda r: f"<b>{r.player}</b> · {r.team}<br>{player_profile(r)}")
        st.caption("Runs kept below the section average, with extra wickets turned into runs. Right of the line beat the average.")

with st.container(border=True):
    st.markdown("**Top performers side by side**")
    top = lambda d, col: d.sort_values(col, ascending=False).head(5).reset_index(drop=True)
    ra, rb, wa, wb = top(bat_a, "runs"), top(bat_b, "runs"), top(bowl_a, "wickets"), top(bowl_b, "wickets")
    n = max(len(ra), len(rb), len(wa), len(wb))
    cell = lambda d, i, f: f(d.iloc[i]) if i < len(d) else ""
    st.dataframe(pd.DataFrame({
        f"{a} runs": [cell(ra, i, lambda r: f"{r.player} {r.runs}") for i in range(n)],
        f"{b} runs": [cell(rb, i, lambda r: f"{r.player} {r.runs}") for i in range(n)],
        f"{a} wickets": [cell(wa, i, lambda r: f"{r.player} {r.wickets}") for i in range(n)],
        f"{b} wickets": [cell(wb, i, lambda r: f"{r.player} {r.wickets}") for i in range(n)],
    }), hide_index=True, width="stretch")
