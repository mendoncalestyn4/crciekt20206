import html

import pandas as pd
import streamlit as st

from ccstats import tables as T
from ccstats.stats import Scope
from ui import state
from ui.theme import page_header

career = state.current()
if career is None:
    st.info("Load a career on the Home page first.")
    st.stop()

m = career.matches
page_header("Competitions", "Tables, brackets and series",
            "The league table, the knockout bracket and every series for one competition and season.")
c1, c2 = st.columns([2, 1])
sections = m.section.value_counts()
section = c1.selectbox("Section", list(sections.index), key="cp2_section", format_func=lambda s: f"{s} · {sections[s]} matches")
seasons = sorted(m[m.section == section].season.unique(), reverse=True)
season = c2.selectbox("Season", seasons, key="cp2_season")
ids = Scope(sections=[section], seasons=[season]).match_ids(m)
inn = career.innings[career.innings.match_id.isin(ids)]


def score(mid, team):
    parts = [f"{r.runs}" if r.all_out else f"{r.runs}/{r.wickets}{'d' if r.declared else ''}"
             for r in inn[(inn.match_id == mid) & (inn.team == team)].sort_values("innings_no").itertuples()]
    return " & ".join(parts) or "–"


shown_any = False

# ---------------------------------------------------------------- league
leagues = T.league_tables(career, ids)
if leagues:
    shown_any = True
    bilateral = m[m.match_id.isin(ids)].competition.iloc[0] in T.BILATERAL
    st.subheader("Every team's record" if bilateral else "League table" + ("s" if len(leagues) > 1 else ""), anchor=False)
    limited = m[m.match_id.isin(ids)].format.iloc[0] in T.LIMITED
    for label, t, rule in leagues:
        with st.container(border=True):
            if len(leagues) > 1 or label not in ("League", "Every team"):
                st.markdown(f"**{label}**")
            cols = {"team": "Team", "played": "P", "won": "W", "lost": "L"}
            if t.drawn.any() or not limited:
                cols["drawn"] = "D"
            if t.tied.any():
                cols["tied"] = "T"
            if t.no_result.any():
                cols["no_result"] = "NR"
            if t.points.notna().any():
                cols["points"] = "Pts"
            if limited:
                cols["nrr"] = "NRR"
            else:
                cols["rpw_for"] = "Runs/wkt"
                cols["rpw_against"] = "Conceded/wkt"
            st.dataframe(t[list(cols)].rename(columns=cols), width="stretch",
                         column_config={"NRR": st.column_config.NumberColumn(format="%+.3f"),
                                        "Pts": st.column_config.NumberColumn(format="%d"),
                                        "Runs/wkt": st.column_config.NumberColumn(format="%.2f"),
                                        "Conceded/wkt": st.column_config.NumberColumn(format="%.2f")})
            st.caption(rule + ("" if not limited else " Net run rate: runs scored per over minus runs conceded per over; "
                                                      "a side bowled out counts as having used its full overs."))
    if not bilateral and (any(len(t) < 3 for _, t, _ in leagues) or len(leagues) > 1):
        st.caption("Groups are worked out from who played whom (teams in different groups never meet), so they only "
                   "separate cleanly once each team has played a couple of games.")

# ---------------------------------------------------------------- knockouts
ko = T.knockouts(career, ids)
if len(ko):
    shown_any = True
    st.subheader("Knockouts", anchor=False)
    rounds = list(dict.fromkeys(ko.stage))
    cols_html = []
    for rnd in rounds:
        cards = []
        for r in ko[ko.stage == rnd].itertuples():
            lines = []
            for team in (r.home, r.away):
                win = team == r.through
                lines.append(f"<div class='ko-team{' win' if win else ''}'><span>{html.escape(team)}</span>"
                             f"<b>{html.escape(score(r.match_id, team))}</b></div>")
            cards.append(f"<a class='ko-card' href='match?match={r.match_id}' target='_self'>"
                         f"<div class='ko-date'>{r.date:%d %b %Y}</div>{''.join(lines)}"
                         f"<div class='ko-res'>{html.escape(r.result)}</div></a>")
        cols_html.append(f"<div class='ko-col'><div class='ko-round'>{html.escape(rnd)}</div>"
                         f"<div class='ko-cards'>{''.join(cards)}</div></div>")
    st.markdown(f"<div class='ko'>{''.join(cols_html)}</div>", unsafe_allow_html=True)
    champ = ko[ko.stage == "Final"]
    if len(champ) == 1 and champ.through.iloc[0]:
        st.markdown(f"<p class='ko-champ'>🏆 {html.escape(champ.through.iloc[0])} · {html.escape(section)} {season} champions</p>",
                    unsafe_allow_html=True)
    st.caption("Click a match to open its scorecard. The side that went through is highlighted.")

# ---------------------------------------------------------------- series
ser = T.series_table(career, ids)
if len(ser):
    shown_any = True
    st.subheader("Series", anchor=False)
    st.dataframe(pd.DataFrame({"Started": ser.start.dt.strftime("%d %b %Y"), "Series": ser.teams, "Score": ser.score,
                               "Result": ser.result, "Drawn": ser.drawn, "Most runs": ser.top_runs,
                               "Most wickets": ser.top_wickets}), hide_index=True, width="stretch")
    for r in ser.itertuples():
        with st.expander(f"{r.teams} · {r.score} · {r.result}"):
            g = m[m.match_id.isin(r.match_ids)].sort_values("date")
            st.dataframe(pd.DataFrame({
                "Match": [f"{int(n)} of {int(o)}" if pd.notna(n) else "" for n, o in zip(g.series_match_no, g.series_length)],
                "Date": g.date.dt.strftime("%d %b %Y"),
                g.home.iloc[0]: [score(i, g.home.iloc[0]) for i in g.match_id],
                g.away.iloc[0]: [score(i, g.away.iloc[0]) for i in g.match_id],
                "Result": g.result}), hide_index=True, width="stretch")

if not shown_any:
    st.info("No league, knockout or series matches in this section and season yet.")
