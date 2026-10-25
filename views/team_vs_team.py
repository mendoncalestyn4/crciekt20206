import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ccstats import analysis as A
from ccstats import teamplay as TP
from ccstats.stats import WICKET_VALUE, Scope
from ui import logos, state
from ui.theme import counted
from ui.charts import player_profile, CONFIG, _axis, _layout, fmt, label_annotations
from ui.theme import chart_note, colours, explain_list, page_header
from ccstats.stats import poss

career = state.current()
if career is None:
    st.info("Load a career on the Home page first.")
    st.stop()
state.stop_if_no_matches(career)

m = career.matches
page_header("Team vs team", "Head to head",
            "Pick a section and two teams. Against each other: only their meetings, at any ground or one side's home. "
            "Against anyone: each team's own games, to size up two sides that haven't met (home games next to away "
            "games, as for a game at one team's ground).")
r1 = st.columns([2.2, 0.9, 1.45, 1.45])  # room for "County Championship · Division 2 (32)"
sections = m.section.value_counts()
state.recall("tv_section", "section", list(sections.index))
section = r1[0].selectbox("Section", list(sections.index), key="tv_section", on_change=state.remember("tv_section", "section"), format_func=lambda s: counted(s, sections[s]))
seasons = sorted(m[m.section == section].season.unique(), reverse=True)
state.recall("tv_season", "season", ["All seasons"] + seasons)
season = r1[1].selectbox("Season", ["All seasons"] + seasons, key="tv_season", on_change=state.remember("tv_season", "season"))
base_scope = Scope(sections=[section], seasons=[] if season == "All seasons" else [season])
here = m[m.match_id.isin(base_scope.match_ids(m))]
# every side that has played here, and the ones that belong here but haven't played yet (a new save)
teams, todo = state.section_teams(career, section, here)
if len(teams) < 2:
    st.info("This section needs at least two teams.")
    st.stop()
# Team A starts on your team, Team B on the side it has played most here (both stay as you pick them)
mine_here = [t for t in state.my_teams(career) if t in teams]
if st.session_state.get("tv_a") not in teams:
    st.session_state["tv_a"] = mine_here[0] if mine_here else teams[0]


def no_games_yet(t: str) -> str:
    return t + (" (0 games)" if t in todo else "")  # short: the team boxes are narrow


a = r1[2].selectbox("Team A", teams, key="tv_a", format_func=no_games_yet)
others = [t for t in teams if t != a]
if st.session_state.get("tv_b") not in others:
    met = pd.concat([here.away[here.home == a], here.home[here.away == a]]).value_counts()
    st.session_state["tv_b"] = met.index[0] if len(met) else next((t for t in others if t not in todo), others[0])
b = r1[3].selectbox("Team B", others, key="tv_b", format_func=no_games_yet)

meet_all = here[((here.home == a) & (here.away == b)) | ((here.home == b) & (here.away == a))]
n_met = len(meet_all)
where_scope = section + ("" if season == "All seasons" else f" in {season}")
# new teams (or section, season): their games against each other if they've met here, else each side's own games
if st.session_state.get("tv_pair") != (section, season, a, b):
    st.session_state["tv_pair"] = (section, season, a, b)
    st.session_state["tv_which"] = "Against each other" if n_met else "Against anyone"
    st.session_state["tv_ground_k"] = "all"
which = st.segmented_control(
    "Matches", ["Against each other", "Against anyone"], required=True, key="tv_which",
    help="Against each other: only the games between these two. Against anyone: each team's own games against "
         "everyone, to compare two sides that haven't met (or haven't met much).") or "Against each other"
h2h = which == "Against each other"
# where: against each other, at one side's home (the other away) with how many meetings there; against anyone, each
# side's own home or away games, as they would be for a game at one team's ground
grounds = ["all", "a_home", "b_home"] + (["neutral"] if here.neutral.any() else [])
if h2h:
    n_at = {"all": n_met, "a_home": int(((meet_all.home == a) & ~meet_all.neutral).sum()),
            "b_home": int(((meet_all.home == b) & ~meet_all.neutral).sum()), "neutral": int(meet_all.neutral.sum())}
    ground_words = {"all": f"All venues ({n_at['all']})", "a_home": f"At {poss(a)} home ({n_at['a_home']})",
                    "b_home": f"At {poss(b)} home ({n_at['b_home']})", "neutral": f"Neutral ({n_at['neutral']})"}
else:
    ground_words = {"all": "All venues", "a_home": f"{a} home · {b} away", "b_home": f"{a} away · {b} home",
                    "neutral": "Both at neutral grounds"}
ground_opts = [ground_words[g] for g in grounds]
if st.session_state.get("tv_ground") not in ground_opts:  # first time, other teams, or the other kind of match
    k0 = st.session_state.get("tv_ground_k", "all")
    st.session_state["tv_ground"] = ground_words[k0 if k0 in grounds else "all"]
# its own row: "Royal Challengers Bengaluru home · Chennai Super Kings away" needs the width
ground_label = st.segmented_control(
    "Where", ground_opts, required=True, key="tv_ground",
    help=("Their meetings, and how many there were at each ground." if h2h else
          f"{a} home · {b} away: {poss(a)} home games against anyone, next to {poss(b)} away games against anyone, as they "
          f"would be for a game at {poss(a)} ground.")) or ground_opts[0]
ground = {v: k for k, v in ground_words.items()}.get(ground_label, "all")
st.session_state["tv_ground_k"] = ground
venue_a, venue_b = {"all": ("all", "all"), "a_home": ("home", "away"), "b_home": ("away", "home"),
                    "neutral": ("neutral", "neutral")}[ground]


def scope_for(team, other):
    return Scope(sections=[section], seasons=base_scope.seasons, team=team, venue=venue_a if team == a else venue_b,
                 opponent=other if h2h else "")


ids_a, ids_b = scope_for(a, b).match_ids(m), scope_for(b, a).match_ids(m)
if ground != "all" and here.neutral.all():
    st.info(f"{section} matches are played at neutral venues, so there are no home or away games. Choose All venues.")
    st.stop()
if len(ids_a) == 0 or len(ids_b) == 0:
    where_ = {"home": " at home", "away": " away", "neutral": " at a neutral ground", "all": ""}
    if h2h:
        at_ = {"all": "", "a_home": f" at {poss(a)} home", "b_home": f" at {poss(b)} home", "neutral": " at a neutral ground"}
        st.info(f"**{a} and {b} haven't played each other in {where_scope}{at_[ground]} yet.** "
                + ("Choose another **Where** (the number is how many times they've met there), or " if n_met else
                   "Choose ")
                + "**Against anyone** to compare each team's own games.")
    else:
        missing = [(t, v) for t, ids_, v in ((a, ids_a, venue_a), (b, ids_b, venue_b)) if len(ids_) == 0]
        never = [t for t, _ in missing if t in todo]  # no game here at all yet: another Where won't help
        st.info(". ".join(f"**{t} haven't played{'' if t in never else where_[v]} in {where_scope} yet**"
                          for t, v in missing)
                + (". Their side fills in after their first game here" if never else "")
                + (". Choose another **Where**." if len(never) < len(missing) else "."))
    st.stop()
if not h2h:  # say plainly whose games these are: never a meeting that didn't happen
    side = {"all": ("all {t} games", "all {t} games"), "a_home": ("{t} home games", "{t} away games"),
            "b_home": ("{t} away games", "{t} home games"),
            "neutral": ("{t} games at neutral grounds", "{t} games at neutral grounds")}[ground]
    st.info(f"**Each team's own record against anyone:** {side[0].format(t=poss(a))} ({len(ids_a)}) next to "
            f"{side[1].format(t=poss(b))} ({len(ids_b)}), in {where_scope}. "
            + (f"They have played each other {'once' if n_met == 1 else f'{n_met} times'} here: choose **Against "
               "each other** for just " + ("that game." if n_met == 1 else "those.") if n_met else
               f"{a} and {b} haven't played each other here yet."))

c = colours()
col_a, col_b = c["s1"], c["s2"]
rec_a = A.team_table(career, ids_a).set_index("team").loc[a]
rec_b = A.team_table(career, ids_b).set_index("team").loc[b]
limited = np.isfinite(rec_a.nrr) and np.isfinite(rec_b.nrr)
# 1 · won batting first / chasing, for the tale of the tape
for rec, team, ids_ in ((rec_a, a, ids_a), (rec_b, b, ids_b)):
    bft_, _ = state.memo(TP.bat_first_table, career, ids_)
    row_ = bft_.set_index("team").loc[team] if team in set(bft_.team) else None
    rec["bf_pct"] = row_.bf_win_pct if row_ is not None else np.nan
    rec["ch_pct"] = row_.ch_win_pct if row_ is not None else np.nan


def high_total(team, ids):
    i = career.innings[career.innings.match_id.isin(ids) & (career.innings.team == team)]
    return int(i.runs.max()) if len(i) else 0


def games_of(team, venue, opp) -> str:
    """'home games v anyone', 'v Bangladesh, away': whose games a tile counts."""
    at = {"home": "at home", "away": "away", "neutral": "at neutral grounds", "all": ""}[venue]
    if h2h:
        return f"v {opp}" + (f", {at}" if at else "")
    return {"home": "home games v anyone", "away": "away games v anyone", "neutral": "neutral-ground games v anyone",
            "all": "all games v anyone"}[venue]


def tile(col, team, r, other, colour):
    win = lambda x, y: f"color:{c['good']}" if x > y else ""
    extra = (f"<div><span>Net run rate</span><strong style='{win(r.nrr, other.nrr)}'>{r.nrr:+.2f}</strong></div>" if limited
             else f"<div><span>Drawn</span><strong>{int(r.drawn)}</strong></div>")
    sub = games_of(team, venue_a if team == a else venue_b, b if team == a else a)
    col.markdown(
        f"<div class='kpi' style='border-top:3px solid {colour}'><span style='font-size:22px;letter-spacing:.02em;color:{c['ink']}'>"
        f"{logos.team(team, 64)}{team}</span>"
        f"<span style='display:block;font-size:13px;color:{c['muted']};margin-top:2px'>{sub}</span>"
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
        ("Economy (bowling)", "rr_against", "low", 2), ("Wickets taken per match", "wkts_per_match", "high", 1),
        ("Win % batting first", "bf_pct", "high", 0), ("Win % chasing" if limited else "Win % batting second", "ch_pct", "high", 0)]
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
        chart_note(f"{a} are better on {a_wins} of {a_wins + b_wins} measures, {b} on {b_wins}.",
                   "A quick verdict on which side is stronger, measure by measure. The longer bar is the bigger number; "
                   "the tick marks the better team (for runs conceded and economy, lower is better).")
with right:
    with st.container(border=True):
        st.markdown("**Head to head**")
        meet = here[((here.home == a) & (here.away == b)) | ((here.home == b) & (here.away == a))]
        if ground == "a_home":
            meet = meet[(meet.home == a) & ~meet.neutral]
        elif ground == "b_home":
            meet = meet[(meet.home == b) & ~meet.neutral]
        elif ground == "neutral":
            meet = meet[meet.neutral]
        aw, bw = int((meet.winner == a).sum()), int((meet.winner == b).sum())
        if meet.empty:
            at_ = {"all": "", "a_home": f" at {poss(a)} home", "b_home": f" at {poss(b)} home", "neutral": " at a neutral ground"}
            st.caption(f"{a} and {b} haven't played each other in {where_scope}{at_[ground]} yet.")
        else:
            st.markdown(f"**{len(meet)} meeting{'s' * (len(meet) != 1)}:** {a} {aw} – {bw} {b}"
                        + (f", {len(meet) - aw - bw} other" if len(meet) - aw - bw else ""))
            show = meet.sort_values("date", ascending=False)
            lines = [f"**{r.date:%d %b %Y}**{' · ' + r.stage if r.stage else ''} · {r.home} v {r.away}  \n{r.result}"
                     for r in show.head(8).itertuples()]
            st.markdown("\n\n".join(lines))
            if len(show) > 8:
                with st.expander(f"All {len(show)} meetings"):
                    st.dataframe(pd.DataFrame({"Date": show.date.dt.strftime("%d %b %Y"),
                                               "Match": [f"{h} v {w}" for h, w in zip(show.home, show.away)],
                                               "Result": show.result}), hide_index=True, width="stretch")

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
    # each side's top two are named, each joined to its own dot; every other dot shows its figures on hover
    top = pd.concat([d.sort_values(y, ascending=False).head(2) for d in (da, db)]).sort_values(y, ascending=False)
    ann = label_annotations([(getattr(r, x), getattr(r, y), r.player) for r in top.itertuples()],
                            list(zip(alld[x], alld[y])), (0, xmax), (0, ymax), c, height_px=330)
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
        fast = lambda d: (d[d.balls > 0].runs / d[d.balls > 0].balls * 100 > base.strike_rate).mean() * 100  # noqa: E731
        chart_note(f"{fast(bat_a):.0f}% of {poss(a)} batters and {fast(bat_b):.0f}% of {poss(b)} score faster than the section's "
                   f"{fmt(base.strike_rate, 1)} per 100 balls.",
                   "Compares the two batting line-ups player by player: who scores quickly and who has faced the most.")
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
        often = lambda d: (d[d.balls > 0].wickets / d[d.balls > 0].balls * base.bowl_strike_rate > 1).mean() * 100  # noqa: E731
        chart_note(f"{often(bowl_a):.0f}% of {poss(a)} bowlers and {often(bowl_b):.0f}% of {poss(b)} take wickets more often than "
                   f"one every {fmt(base.bowl_strike_rate, 1)} balls.",
                   "Compares the two attacks bowler by bowler: who takes wickets and who has done the most bowling.")
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
        pa, pb = (bat_a.runs_above_average > 0).mean() * 100, (bat_b.runs_above_average > 0).mean() * 100
        chart_note(f"{pa:.0f}% of {poss(a)} batters and {pb:.0f}% of {poss(b)} beat the average batter. Team totals: {a} "
                   f"{bat_a.runs_above_average.sum():+.0f}, {b} {bat_b.runs_above_average.sum():+.0f} runs.",
                   "Runs scored minus what an average batter in this section would have made: who is pulling their "
                   "weight. Right of the line beat the average.")
with right:
    with st.container(border=True):
        st.markdown("**Every bowler: runs saved**")
        team_bars("tv_saved", bowl_a, bowl_b, "runs_saved", "Runs saved",
                  lambda r: f"<b>{r.player}</b> · {r.team}<br>{player_profile(r)}")
        pa, pb = (bowl_a.runs_saved > 0).mean() * 100, (bowl_b.runs_saved > 0).mean() * 100
        chart_note(f"{pa:.0f}% of {poss(a)} bowlers and {pb:.0f}% of {poss(b)} beat the average bowler. Team totals: {a} "
                   f"{bowl_a.runs_saved.sum():+.0f}, {b} {bowl_b.runs_saved.sum():+.0f} runs saved.",
                   "Runs kept below the section average, with extra wickets turned into runs: which bowlers really "
                   "help. Right of the line beat the average.")

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
