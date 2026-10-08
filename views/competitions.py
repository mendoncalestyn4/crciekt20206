import html

import pandas as pd
import streamlit as st

from ccstats import odds as OD
from ccstats import players as PL
from ccstats import seasonal as SN
from ccstats import tables as T
from ccstats import teamplay as TP
from ui import state
from ui.charts import odds_chart
from ui.theme import chart_note, html_table, page_header, safe_section

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
state.recall("cp2_event", "event", list(events.index))
event = c1.selectbox("Competition", list(events.index), key="cp2_event", on_change=state.remember("cp2_event", "event"), format_func=lambda s: f"{s} · {events[s]} matches")
seasons = sorted(m[m.event == event].season.unique(), reverse=True)
state.recall("cp2_season", "season", seasons)
season = c2.selectbox("Season", seasons, key="cp2_season", on_change=state.remember("cp2_season", "season"))
ids = pd.Index(m[(m.event == event) & (m.season == season)].match_id)
inn = career.innings[career.innings.match_id.isin(ids)]


def score(mid, team):
    parts = [f"{r.runs}" if r.all_out else f"{r.runs}/{r.wickets}{'d' if r.declared else ''}"
             for r in inn[(inn.match_id == mid) & (inn.team == team)].sort_values("innings_no").itertuples()]
    return " & ".join(parts) or "–"


shown_any = False


def chance(v: float) -> str:
    """A chance in %, never rounded to a certainty it isn't."""
    if v != v:
        return ""
    return "<1%" if 0 < v < 0.5 else ">99%" if 99.5 <= v < 100 else f"{v:.0f}%"

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
            if not bilateral:  # 118 · table extras
                ex = SN.table_extras(career, ids, t, label).set_index("team")
                t = t.assign(form=t.team.map(ex.form), home_rec=t.team.map(ex.home), away_rec=t.team.map(ex.away),
                             ppg=t.points / t.played.replace(0, float("nan")), rr_for=t.team.map(ex.rr_for),
                             rr_against=t.team.map(ex.rr_against), moved=[SN.moved_text(v) for v in t.team.map(ex.moved)])
                cols["form"] = "Last 5"
                if not m[m.match_id.isin(ids)].neutral.all():
                    cols["home_rec"] = "Home W–L"
                    cols["away_rec"] = "Away W–L"
                if t.points.notna().any():
                    cols["ppg"] = "Pts/game"
                if limited:
                    cols["rr_for"] = "RR for"
                    cols["rr_against"] = "RR against"
                cols["moved"] = "Move"
            st.dataframe(t[list(cols)].rename(columns=cols), width="stretch",
                         column_config={"NRR": st.column_config.NumberColumn(format="%+.3f"),
                                        "Pts": st.column_config.NumberColumn(format="%d"),
                                        "Runs/wkt": st.column_config.NumberColumn(format="%.2f"),
                                        "Conceded/wkt": st.column_config.NumberColumn(format="%.2f"),
                                        "Pts/game": st.column_config.NumberColumn(format="%.2f"),
                                        "RR for": st.column_config.NumberColumn(format="%.2f"),
                                        "RR against": st.column_config.NumberColumn(format="%.2f")})
            st.caption(rule + ("" if not limited else " Net run rate: runs scored per over minus runs conceded per over; "
                                                      "a side bowled out counts as having used its full overs (in a "
                                                      "game shortened by rain, the overs it was allowed). Abandoned "
                                                      "games don't count, and in a game decided by the rain rule the "
                                                      "side batting first is credited with the rain-rule par score.")
                       + " Won batting 1st / chasing: wins out of games played that way."
                       + ("" if bilateral else " Last 5: newest on the right. RR: runs per over scored and conceded. "
                          "Move: places gained (▲) or lost (▼) since the match day before the latest one."))
    if not bilateral and (any(len(t) < 3 for _, t, _ in leagues) or len(leagues) > 1):
        st.caption("Groups come from the group names on the scorecards (a team's row counts all its league games, "
                   "cross-group ones too). Where the scorecards don't name them, they're worked out from who played "
                   "whom, so they only separate cleanly once each team has played a couple of games.")

# ---------------------------------------------------------------- title race (idea 3)
if leagues and not bilateral and not any(x in event for x in ("World XI", "Tour matches")):
    with safe_section("title race"):
        st.subheader("Title race", anchor=False)
        ko_ = TP.has_knockouts(career, event)
        d_ = TP.qualification_defaults(career, event, season)
        many = d_["groups"] > 1
        if many:
            o1, o2, o4, o3 = st.columns([1, 1, 1, 1.4])
        else:
            (o1, o2, o3), o4 = st.columns([1, 1, 1.4]), None
        games_ = int(o1.number_input("League games per team", 1, 60, d_["games"], key=f"cp_od_games_{event}_{season}"))
        places_ = int(o2.number_input("Places that go through (per group)", 1, 16, d_["places"],
                                      key=f"cp_od_places_{event}_{season}", disabled=not ko_))
        extra_ = int(o4.number_input("…and the best next-placed sides", 0, 8, int(d_.get("extra", 0)),
                                     key=f"cp_od_extra_{event}_{season}", disabled=not ko_,
                                     help="The Blast also takes the two best third-placed sides.")) if many else 0
        now = state.memo(OD.odds_with_change, career, event, season, games_, places_, extra=extra_)
        hist = state.memo(OD.odds_history, career, event, season, games_, places_, extra=extra_)
        col = "title" if ko_ else "top"
        what = "the title" if ko_ else "topping the table"
        teams_ = sorted(set(hist.team)) if len(hist) else []
        mine_ = [t for t in state.my_teams(career) if t in teams_]
        fav = hist[hist.date == hist.date.max()].sort_values(col, ascending=False).team.iloc[0] if len(hist) else ""
        pick = o3.selectbox("Team in colour", teams_, index=teams_.index(mine_[0] if mine_ else fav) if teams_ else 0,
                            key=f"cp_od_team_{event}_{season}") if teams_ else ""
        if now["state"] == "open":
            t = now["table"].copy()
            ch = now.get("change") or {}
            t = t.sort_values(["group", col], ascending=[True, False])
            for grp, g in t.groupby("group", sort=False):
                with st.container(border=True):
                    if now["groups"] > 1:
                        st.markdown(f"**{grp}**")
                    rows = []
                    for r in g.itertuples():
                        delta = ch.get(r.team, float("nan"))
                        move = ("" if delta != delta else f"▲ {delta:.0f}" if delta >= 0.5 else
                                f"▼ {-delta:.0f}" if delta <= -0.5 else "–")
                        row = [r.team, r.played, f"{r.points:.0f}", r.left]
                        row += [chance(r.playoffs), chance(r.title)] if ko_ else [chance(r.top)]
                        rows.append(row + [move])
                    head = ["Team", "Played", "Pts", "Left"] + (["Through", "Title"] if ko_ else ["Top"]) + ["Change"]
                    html_table(rows, head, numeric={1, 2, 3}, row_class=["hi" if x == pick else "" for x in g.team])
            since = now.get("since")
            st.caption("Chances from playing the rest of the league season out 4,000 times. "
                       + (f"Change: since before the games of {since:%d %b}. " if since is not None else ""))
        elif now["state"] == "league over":
            st.caption("The league stage is over" + (" (see the knockouts below)." if ko_ else "."))
        if len(hist) and hist.date.nunique() > 1:
            st.plotly_chart(odds_chart(hist, col, what, pick), width="stretch", key=f"cp_od_chart_{event}_{season}")
            mine_h = hist[hist.team == pick].sort_values("date")
            best = mine_h.loc[mine_h[col].idxmax()]
            fav_days = hist.loc[hist.groupby("date")[col].idxmax()].team.value_counts()
            chart_note(f"{pick}: {chance(mine_h[col].iloc[0])} after the first match day, at best {chance(best[col])} "
                       f"(after {best.date:%d %b}), {chance(mine_h[col].iloc[-1])} now. {fav_days.index[0]} were the "
                       f"favourites most often ({fav_days.iloc[0]} of {hist.date.nunique()} match days).",
                       f"See when the race for {what} turned, and how much each result moved a side's chances.")
        st.caption("How it's worked out: each game still to play is decided by the two sides' team ratings (the Elo on "
                   "the Rankings page), with this competition's share of " + ("no results" if limited else "draws")
                   + ". The scorecards don't hold the fixture list, so the games left are worked out from the games "
                   "per team above and who has met whom least. Ties on points go to wins, then net run rate."
                   + (" The knockouts are played the way this competition plays them." if ko_ else "")
                   + " The chart shows each side's chance after every match day; sides that never had a 5% chance "
                   "are left out.")

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

# ---------------------------------------------------------------- 136 · World Test Championship
wtc = SN.wtc_matches(career)
if len(wtc) and m[m.match_id.isin(ids)].format.iloc[0] == "Test" and not m[m.match_id.isin(ids)].knockout.all():
    shown_any = True
    st.subheader("World Test Championship", anchor=False)
    cycles = sorted(wtc.cycle.unique(), reverse=True)
    here_cycle = SN.wtc_cycle(m[m.match_id.isin(ids)].date.max())
    cyc = st.selectbox("Cycle", cycles, index=cycles.index(here_cycle) if here_cycle in cycles else 0, key="cp2_wtc",
                       format_func=lambda y: f"{y}–{str(y + 2)[-2:]}")
    wt = SN.wtc_table(career, cyc)
    with st.container(border=True):
        st.dataframe(pd.DataFrame({"Team": wt.team, "Series": wt.series, "P": wt.played, "W": wt.won, "L": wt.lost,
                                   "D": wt.drawn, "T": wt.tied, "Pts": wt.points, "Of": wt.available, "PCT %": wt.pct}),
                     width="stretch", column_config={"PCT %": st.column_config.NumberColumn(format="%.2f")})
        if len(wt) >= 2:
            a_, b_ = wt.iloc[0], wt.iloc[1]
            st.markdown(f"**Heading for the final:** {a_.team} ({a_.pct:.1f}%) and {b_.team} ({b_.pct:.1f}%).")
        st.caption("The real system: 12 points for a win, 6 for a tie, 4 for a draw, ranked by the percentage of the "
                   "points played for that were won (PCT). Only Tests between the nine WTC sides count (Australia, "
                   "Bangladesh, England, India, New Zealand, Pakistan, South Africa, Sri Lanka, West Indies), in "
                   "two-year cycles from June of an odd year; the top two meet in the final. Over-rate penalties "
                   "aren't on the scorecards, so they aren't taken off.")

if not shown_any:
    st.info("No league, knockout or series matches in this competition and season yet.")
