import html

import pandas as pd
import streamlit as st

from ccstats import players as PL
from ccstats import tables as T
from ccstats import teamplay as TP
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
# A competition as it's run (the ODI World Cup, bilateral ODI series, each County Championship division),
# which is finer than the stats sections: every ODI is in the ODIs section, but the World Cup has its own table.
events = m.event.value_counts()
event = c1.selectbox("Competition", list(events.index), key="cp2_event", format_func=lambda s: f"{s} · {events[s]} matches")
seasons = sorted(m[m.event == event].season.unique(), reverse=True)
season = c2.selectbox("Season", seasons, key="cp2_season")
ids = pd.Index(m[(m.event == event) & (m.season == season)].match_id)
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
            # batting first or chasing: wins each way in these games
            gm = state.memo(TP.games, career, ids)
            gm = gm[~gm.knockout]
            t = t.assign(bat_first=[f"{int(((gm.team == x) & gm.batted_first & (gm.outcome == 'W')).sum())}/"
                                    f"{int(((gm.team == x) & gm.batted_first).sum())}" for x in t.team],
                         chased=[f"{int(((gm.team == x) & ~gm.batted_first & (gm.outcome == 'W')).sum())}/"
                                 f"{int(((gm.team == x) & ~gm.batted_first).sum())}" for x in t.team])
            cols["bat_first"] = "Won batting 1st"
            cols["chased"] = "Won chasing" if limited else "Won batting 2nd"
            st.dataframe(t[list(cols)].rename(columns=cols), width="stretch",
                         column_config={"NRR": st.column_config.NumberColumn(format="%+.3f"),
                                        "Pts": st.column_config.NumberColumn(format="%d"),
                                        "Runs/wkt": st.column_config.NumberColumn(format="%.2f"),
                                        "Conceded/wkt": st.column_config.NumberColumn(format="%.2f")})
            st.caption(rule + ("" if not limited else " Net run rate: runs scored per over minus runs conceded per over; "
                                                      "a side bowled out counts as having used its full overs.")
                       + " Won batting 1st / chasing: wins out of games played that way.")
    if not bilateral and (any(len(t) < 3 for _, t, _ in leagues) or len(leagues) > 1):
        st.caption("Groups come from the group names on the scorecards (a team's row counts all its league games, "
                   "cross-group ones too). Where the scorecards don't name them, they're worked out from who played "
                   "whom, so they only separate cleanly once each team has played a couple of games.")

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
        st.markdown(f"<p class='ko-champ'>🏆 {html.escape(champ.through.iloc[0])} · {html.escape(event)} {season} champions</p>",
                    unsafe_allow_html=True)
    elif len(champ) == 1 and champ.format.iloc[0] == "Test" and champ.result_type.iloc[0] in ("draw", "tie"):
        f = champ.iloc[0]  # a drawn World Test Championship Final: the title is shared
        st.markdown(f"<p class='ko-champ'>🏆 {html.escape(f.home)} and {html.escape(f.away)} share the {html.escape(event)} "
                    f"{season} title</p>", unsafe_allow_html=True)
    st.caption("Click a match to open its scorecard. The side that went through is highlighted.")

# ---------------------------------------------------------------- series
ser = T.series_table(career, ids)
if len(ser):
    shown_any = True
    st.subheader("Series", anchor=False)
    pos = state.memo(PL.player_of_series, career, ids).set_index("series_id")
    st.dataframe(pd.DataFrame({"Started": ser.start.dt.strftime("%d %b %Y"), "Series": ser.teams, "Score": ser.score,
                               "Result": ser.result, "Drawn": ser.drawn, "Most runs": ser.top_runs,
                               "Most wickets": ser.top_wickets,
                               "Player of the Series": [f"{pos.player[s_]} ({pos.runs[s_]} runs, {pos.wickets[s_]} wkts)"
                                                        if s_ in pos.index else "–" for s_ in ser.series_id]}),
                 hide_index=True, width="stretch")
    st.caption("Player of the Series: the most impact over the series (runs, plus each wicket worth the section's "
               "runs per wicket).")
    for r in ser.itertuples():
        with st.expander(f"{r.teams} · {r.score} · {r.result}"):
            g = m[m.match_id.isin(r.match_ids)].sort_values("date")
            st.dataframe(pd.DataFrame({
                "Match": [(f"{int(n)}" + (f" of {int(o)}" if pd.notna(o) else "")) if pd.notna(n) else ""
                          for n, o in zip(g.series_match_no, g.series_length)],
                "Date": g.date.dt.strftime("%d %b %Y"),
                g.home.iloc[0]: [score(i, g.home.iloc[0]) for i in g.match_id],
                g.away.iloc[0]: [score(i, g.away.iloc[0]) for i in g.match_id],
                "Result": g.result}), hide_index=True, width="stretch")

if not shown_any:
    st.info("No league, knockout or series matches in this competition and season yet.")
