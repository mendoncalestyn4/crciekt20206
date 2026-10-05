"""The "My team" tab on the Home page."""

from __future__ import annotations

import numpy as np
import streamlit as st

from ccstats import extras as E
from ccstats import myteam as MT
from ccstats import players as PL
from ccstats import teamplay as TP
from ccstats.competitions import shown_name

from . import state
from .charts import fmt
from .theme import esc, form_strip, html_table, kpis, match_link, player_link, safe_section, scoreboard


def _score(career, mid, team):
    inn = career.innings[(career.innings.match_id == mid) & (career.innings.team == team)].sort_values("innings_no")
    return " & ".join(f"{r.runs}" if r.all_out else f"{r.runs}/{r.wickets}{'d' if r.declared else ''}"
                      for r in inn.itertuples()) or "–"


def render(career, team: str, key: str) -> None:
    m = career.matches
    secs = state.memo(MT.sections_of, career, team)
    if not secs:
        st.info(f"No matches for {team} yet.")
        return
    # ---------------------------------------------------------------- banner
    with safe_section("banner"):
        bn = state.memo(MT.banner, career, team)
        tiles = []
        for b in bn[:4]:
            pos = f" · {b['position'][2]} of {b['position'][3]}" if b["position"] else ""
            elo = (f"Elo {b['elo']:.0f} {'▲' if b['moved'] > 0 else '▼' if b['moved'] < 0 else '▬'}"
                   f"{abs(b['moved']):.0f}" if np.isfinite(b["elo"]) else "")
            tiles.append((f"{b['section']} {b['season']}",
                          f"{TP.wdl(b['record'])}<span class='small'>{pos}</span>"))
            b["elo_text"] = elo
        kpis(tiles)
        st.caption(" · ".join(f"{b['section']}: {b['elo_text']}, {b['rank']} of {b['teams']} in the ratings"
                              + (f", {b['position'][2]} in {b['position'][0]}" if b["position"] else "")
                              for b in bn[:4] if b.get("elo_text")) + ". ▲▼ = rating change over the last 5 games.")

    # ---------------------------------------------------------------- latest result + last 5
    last = MT.last_game(career, team)
    if last is not None:
        stage = f" · {last.stage}" if last.stage else ""
        scoreboard(f"Latest result · {shown_name(last.section, last.event)}{stage} · {last.date:%d %b %Y}",
                   last.home, _score(career, last.match_id, last.home), last.away, _score(career, last.match_id, last.away),
                   f"{last.result}" + (f" · Player of the match: {last.player_of_match}" if last.player_of_match else ""))

    section = st.selectbox("Section", secs, key=f"mt_sec_{key}",
                           help="Your team's sections, the one you played most recently first.")
    season = MT.latest_season(career, team, section)
    ids_all = m[m.section == section].match_id

    left, right = st.columns([1.15, 1], gap="medium")
    with left:
        # ---------------------------------------------------------------- season so far + report card
        with safe_section("season so far"), st.container(border=True):
            sp = state.memo(MT.same_point, career, team, section)
            tg = state.memo(TP.games, career, ids_all)
            last5 = list(tg[tg.team == team].outcome.tail(5))
            st.markdown(f"**{section} {season} so far** · last 5: {form_strip(last5)}", unsafe_allow_html=True)
            if sp:
                line = f"After {sp['n']} game{'s' if sp['n'] != 1 else ''}: **{TP.wdl(sp['now'])}**"
                if sp["then"] is not None:
                    d = (sp["now"]["won"] - sp["then"]["won"])
                    line += (f". At the same point of {sp['last_season']}: {TP.wdl(sp['then'])} "
                             f"({'+' if d > 0 else ''}{d} win{'s' if abs(d) != 1 else ''}).")
                st.markdown(line)
            rc = state.memo(MT.report_card, career, team, section, season)
            if rc:
                html_table([[s, f"<span class='grade {g}'>{g}</span>", esc(why)] for s, g, why in rc],
                           ["Report card", "Grade", "Why"], raw={1, 2})
                st.caption("Grades against the average team in this section this season: A well above, C about "
                           "average, E well below.")
    with right:
        # ---------------------------------------------------------------- stars
        with safe_section("stars"), st.container(border=True):
            sq = state.memo(MT.squad, career, team, section, season)
            st.markdown("**Your stars this season** · ▲▼ form over the last 3 innings")
            if sq.empty:
                st.caption("No games yet.")
            else:
                bats = sq.sort_values("runs", ascending=False).head(3)
                bowls = sq[sq.wickets > 0].sort_values("wickets", ascending=False).head(3)
                rows = [[player_link(r.player), f"{r.runs} runs", f"avg {fmt(r.average, 1)}", r.form] for r in bats.itertuples()]
                rows += [[player_link(r.player), f"{r.wickets} wkts", f"econ {fmt(r.economy, 2)}", ""] for r in bowls.itertuples()]
                html_table(rows, ["Player", "", "", "Form"], raw={0})
        # ---------------------------------------------------------------- alerts
        with safe_section("alerts"):
            al = state.memo(MT.alerts, career, team, section, season)
            if al:
                with st.container(border=True):
                    st.markdown("**Worth a look**  \n" + "  \n".join(al))

    # ---------------------------------------------------------------- squad
    with safe_section("squad"), st.expander(f"Squad · everyone who has played for {team} in {section} {season}", expanded=False):
        sq = state.memo(MT.squad, career, team, section, season)
        html_table([[player_link(r.player), r.games, r.runs, fmt(r.average, 1), fmt(r.strike_rate, 1), r.wickets,
                     fmt(r.economy, 2), r.last5, r.form] for r in sq.itertuples()],
                   ["Player", "Games", "Runs", "Avg", "SR", "Wkts", "Econ", "Last 5 scores", "Form"],
                   numeric={1, 2, 3, 4, 5, 6}, raw={0}, row_class=["" if r.recent else "dim" for r in sq.itertuples()])
        st.caption("Greyed out: not in the last 3 games.")

    left, right = st.columns(2, gap="medium")
    with left:
        # ---------------------------------------------------------------- headlines
        with safe_section("headlines"), st.container(border=True):
            news = state.memo(E.headlines, career, n_matches=8, limit=6, team=team)
            st.markdown(f"**📰 {team} headlines**")
            if news:
                st.markdown("\n".join(f"- {h}" for h in news))
            else:
                st.caption("Nothing big in your recent games.")
        # ---------------------------------------------------------------- milestones and records
        with safe_section("milestones"), st.container(border=True):
            st.markdown("**Milestones and records in sight**")
            squad_names = set(state.memo(MT.squad, career, team, section, season).player)
            mw = state.memo(PL.milestone_watch, career, ids_all)
            mw = mw[mw.player.isin(squad_names)]
            rw = state.memo(PL.record_watch, career, section)
            rw = rw[rw.chaser.isin(squad_names)]
            rows = [[player_link(r.player), f"{r.next:,} {r.what}", f"needs {r.needed:,}"] for r in mw.head(6).itertuples()]
            rows += [[player_link(r.chaser), f"{r.record} record ({r.record_value:,})", f"needs {r.needed:,}"]
                     for r in rw.itertuples()]
            if rows:
                html_table(rows, ["Player", "Chasing", ""], raw={0})
            else:
                st.caption("Nobody close to a milestone or a record right now.")
    with right:
        # ---------------------------------------------------------------- how you win
        with safe_section("how you win"), st.container(border=True):
            bft, avg = state.memo(TP.bat_first_table, career, ids_all)
            st.markdown("**How you win**")
            if team in set(bft.team):
                r = bft.set_index("team").loc[team]
                second = "batting second" if avg["multi"] else "chasing"
                st.markdown(f"Batting first **{fmt(r.bf_win_pct, 0)}%** ({int(r.bf_won)} of {int(r.bf_decided)}) · "
                            f"{second} **{fmt(r.ch_win_pct, 0)}%** ({int(r.ch_won)} of {int(r.ch_decided)}).")
                g = tg[(tg.team == team) & tg.batted_first & tg.first_score.notna()]
                won = g[g.outcome == "W"]
                if len(won) >= 2 and not avg["multi"]:
                    st.caption(f"Your lowest total defended: {int(won.first_score.min())}. Your typical winning total "
                               f"batting first: {int(won.first_score.median())}.")
        # ---------------------------------------------------------------- rivals
        with safe_section("rivals"), st.container(border=True):
            op = state.memo(TP.opponents, career, ids_all, team)
            st.markdown("**Rivals at a glance** · most-played opponents here")
            rows = [[("⭐ " if r.favourite else "👻 " if r.bogey else "") + r.opponent, r.played, TP.wdl(r._asdict()),
                     f"{fmt(r.win_pct, 0)}%"] for r in op.head(6).itertuples()]
            if rows:
                html_table(rows, ["Opponent", "Played", "Record", "Win %"], numeric={1, 3})
            # ---------------------------------------------------------------- next opponent
            opps = sorted(set(op.opponent))
            if opps:
                c1, c2 = st.columns([2, 1], vertical_alignment="bottom")
                nxt = c1.selectbox("Next opponent", opps, key=f"mt_next_{key}")
                if c2.button("Preview →", key=f"mt_go_{key}"):
                    intl = section in ("Tests", "ODIs", "T20Is")
                    st.session_state["op_section"] = "Internationals" if intl else section
                    if intl:
                        st.session_state["op_format"] = section
                    st.session_state["op_mine"] = team
                    st.session_state["op_opp"] = nxt
                    st.switch_page("views/opponent.py")

    left, right = st.columns(2, gap="medium")
    with left:
        # ---------------------------------------------------------------- trophies and records
        with safe_section("trophy cabinet"), st.container(border=True):
            tc = state.memo(E.trophy_cabinet, career, team)
            st.markdown("**🏆 Trophy cabinet**")
            if tc.empty:
                st.caption("No titles yet.")
            else:
                html_table([[f"{r.section} {r.season}", r.how, r.runners_up] for r in tc.itertuples()],
                           ["Title", "How", "Runners-up"])
            tr = state.memo(MT.team_records, career, team, section)
            if tr:
                st.markdown(f"**{team} records in {section}**")
                html_table([[a, b] for a, b in tr], ["", ""])
    with right:
        # ---------------------------------------------------------------- history
        with safe_section("history"), st.container(border=True):
            hi = state.memo(MT.history, career, team)
            st.markdown("**Season by season**")
            html_table([[f"{r.season}", r.section, TP.wdl(r._asdict()), f"{fmt(r.win_pct, 0)}%", r.finish or "–"]
                        for r in hi.itertuples()], ["Season", "Section", "Record", "Win %", "Finished"], numeric={3})
    lg = MT.last_game(career, team)
    if lg is not None:
        st.markdown(f"Latest scorecard: {match_link(lg.match_id, f'{lg.home} v {lg.away}, {lg.date:%d %b %Y}')}",
                    unsafe_allow_html=True)
