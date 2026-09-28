import numpy as np
import pandas as pd
import streamlit as st

from ccstats import analysis as A
from ccstats import extras as E
from ui.theme import colours
from ccstats.stats import Scope
from ui import state
from ui.charts import CONFIG, bars, fmt
from ui.theme import explain_list, kpis, page_header

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
        ("Last 5", " ".join(sk["last5"]) or "–")])
st.caption(f"Longest winning run: {sk['longest_win']} · longest losing run: {sk['longest_loss']}")

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
            st.dataframe(pd.DataFrame({"Date": col.date.dt.strftime("%d %b %Y"),
                                       "Against": [a if h == team else h for h, a in zip(col.home, col.away)],
                                       "Slide": [f"{f} → {t}" for f, t in zip(col.from_score, col.to_score)],
                                       "Lost": [f"{w} for {r}" for w, r in zip(col.wickets, col.runs)],
                                       "Finished on": col.total}), hide_index=True, width="stretch")

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
    st.markdown("**Results**")
    res = tm.sort_values("date", ascending=False)
    table_res = pd.DataFrame({"Date": res.date.dt.strftime("%d %b %Y"), "Opponent": res.opponent, "Venue": res.venue.str.title(),
                              "Stage": res.stage, "Result": res.result, "": res.outcome})
    if not res.stage.astype(bool).any():
        table_res = table_res.drop(columns="Stage")
    st.dataframe(table_res, hide_index=True, width="stretch")

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
