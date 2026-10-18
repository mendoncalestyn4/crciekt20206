"""The "My team" tab on the Home page."""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from ccstats import extras as E
from ccstats import fixtures as FX
from ccstats import myteam as MT
from ccstats import players as PL
from ccstats import seasonal as SN
from ccstats import teamplay as TP
from ccstats.competitions import shown_name, with_stage

from . import state
from .charts import _n, pct, fmt
from .theme import esc, form_strip, html_table, kpis, match_link, player_link, safe_section, scoreboard


def _score(career, mid, team):
    inn = career.innings[(career.innings.match_id == mid) & (career.innings.team == team)].sort_values("innings_no")
    return " & ".join(f"{r.runs}" if r.all_out else f"{r.runs}/{r.wickets}{'d' if r.declared else ''}"
                      for r in inn.itertuples()) or "–"


def render(career, team: str, key: str) -> None:
    m = career.matches
    secs = state.memo(MT.sections_of, career, team)
    if not secs:
        st.info(f"No matches for {team} yet: this tab fills in after their first game. Add their schedule on the "
                "**Fixtures** page meanwhile, and the next match and series previews show up here.")
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
        def odds_text(ch):
            if not ch:
                return ""
            pc = lambda v: "<1%" if 0 < v < 0.5 else ">99%" if 99.5 <= v < 100 else f"{v:.0f}%"  # noqa: E731
            return (f"; playoff chance {pc(ch['playoffs'])}, title {pc(ch['title'])}" if ch["knockouts"] else
                    f"; chance of topping the table {pc(ch['top'])}")
        st.caption(" · ".join(f"{b['section']}: {b['elo_text']}, {b['rank']} of {b['teams']} in the ratings"
                              + (f", {b['position'][2]} in {b['position'][0]}" if b["position"] else "")
                              + odds_text(b.get("chances"))
                              for b in bn[:4] if b.get("elo_text")) + ". ▲▼ = rating change over the last 5 games."
                   + (" Chances: the rest of the season played out 2,000 times (Competitions → Title race)."
                      if any(b.get("chances") for b in bn[:4]) else ""))

    # ---------------------------------------------------------------- latest result + last 5
    last = MT.last_game(career, team)
    if last is not None:
        scoreboard(f"Latest result · {with_stage(shown_name(last.section, last.event), last.stage)} · {last.date:%d %b %Y}",
                   last.home, _score(career, last.match_id, last.home), last.away, _score(career, last.match_id, last.away),
                   f"{last.result}" + (f" · Player of the match: {last.player_of_match}" if last.player_of_match else ""),
                   event=last.event)

    # ---------------------------------------------------------------- 115 · what changed
    with safe_section("after the match"):
        am = state.memo(SN.after_match, career, team)
        if am:
            lines = []
            if am.get("elo"):
                a, b = am["elo"]
                lines.append(f"**Rating:** Elo {a:.0f} → {b:.0f} ({b - a:+.0f})")
            pos = am.get("position")
            if pos and pos[1]:
                after_ = pos[1]
                where = f" in {after_[2]}" if after_[2] not in ("League", "Every team") else ""
                if pos[0]:
                    mv = pos[0][0] - after_[0]
                    lines.append(f"**Table:** {after_[0]} of {after_[1]}{where} "
                                 + (f"(up {mv})" if mv > 0 else f"(down {-mv})" if mv < 0 else "(no change)"))
                else:
                    lines.append(f"**Table:** {after_[0]} of {after_[1]}{where} after the first game")
            if am.get("series"):
                sr_ = am["series"]
                lead = ("level" if sr_["won"] == sr_["lost"] else "lead" if sr_["won"] > sr_["lost"] else "trail")
                left = sr_["length"] - sr_["played"]
                score_ = f"{sr_['won']}–{sr_['lost']}" + (f" ({sr_['drawn']} drawn)" if sr_["drawn"] else "")
                if left > 0:
                    lines.append(f"**Series:** you {lead} {score_} v {sr_['opponent']}, {left} to play")
                else:
                    res_ = "won" if sr_["won"] > sr_["lost"] else "lost" if sr_["won"] < sr_["lost"] else "drew"
                    lines.append(f"**Series:** you {res_} it {score_} v {sr_['opponent']}")
            if "lead" in am:
                ld = am["lead"]
                lines.append(f"**First-innings lead:** {ld:+d}" if ld else "**First innings:** level")
            for msg in am.get("records", [])[:3]:
                lines.append(f"🏆 {msg}")
            for msg in am.get("milestones", [])[:4]:
                lines.append(f"🎯 {msg}")
            for p, arrow, txt in am.get("form", [])[:5]:
                lines.append(f"{arrow} **{p}** {txt}")
            if lines:
                with st.container(border=True):
                    st.markdown(f"**What changed after the latest game** · v {am['opponent']}, {am['date']:%d %b %Y}  \n"
                                + "  \n".join(lines))
                    st.caption("Rating: Elo before and after this game. Table: league position before and after. ▲ a "
                               "big game for the player (well above their season average before it, or a haul); ▼ a "
                               "low score after a run of good ones. Next opponent: from your schedule (Fixtures "
                               "page); preview any side under Rivals below.")

    # ---------------------------------------------------------------- 144 / 148 · next up (from your schedule)
    with safe_section("next up"):
        sched = state.fixtures(career)
        # your schedule, plus what the team played since it starts that isn't in it (and the next knockout game)
        tr = state.memo(FX.track, career, sched, auto=(team,))
        mine_tr = tr[tr.team == team] if len(tr) else tr
        if len(mine_tr) and (any(r.get("team") == team for r in sched) or mine_tr.status.isin(["next"]).any()):
            from ccstats import winprob as WP
            sm = FX.summary(tr, team)
            nx = sm["next"]
            with st.container(border=True):
                lines = [f"**📅 Your schedule:** {sm['played']} of {sm['total']} played"]
                if nx is not None:
                    when = (f"{pd.Timestamp(nx['date']):%d %b %Y}" if nx["date"] else
                            f"about {pd.Timestamp(nx['anchor']):%d %b %Y}"
                            if str(nx.get("estimated")) == "True" and pd.notna(nx.get("anchor")) else
                            FX.month_label(nx["month"]))
                    name = nx["series"].replace(FX.AUTO, "").split(" · ")[0]
                    stage = nx.get("stage") if isinstance(nx.get("stage"), str) else ""
                    what = (f"{name} {stage}" + (f" v {nx['opponent']}" if nx["opponent"] else "") if stage else
                            f"v {nx['opponent']} · {nx['format']}" if nx["opponent"] else name)
                    line = f"**⏭ Next:** {what} · " + (f"{nx['venue']} · " if nx["venue"] else "") + when
                    if nx["opponent"]:
                        p = WP.predict(career, FX.format_ids(career, team, nx["format"]), team, nx["opponent"],
                                       nx["venue"] if nx["venue"] in ("home", "away") else "neutral")
                        line += (f" · 🔮 {team} {p['win']:.0f}%" + (f", draw {p['draw']:.0f}%" if p["multi"] else "")
                                 + f", {nx['opponent']} {p['lose']:.0f}%")
                    lines.append(line)
                for sg in FX.series_groups(tr, team):
                    if sg["state"] == "under way":
                        o = FX.series_outlook(career, team, sg)
                        lead = "level" if sg["won"] == sg["lost"] else ("you lead" if sg["won"] > sg["lost"] else "you trail")
                        lines.append(f"**🔴 {sg['series']}:** {lead} {sg['won']}–{sg['lost']}; {o['need']} "
                                     f"(chance {o['odds']['A']:.0f}%)")
                lines.append("<a href='fixtures' target='_self'>Open Fixtures: previews, WTC race, milestones and goals →</a>")
                st.markdown("  \n".join(lines), unsafe_allow_html=True)

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
            last5 = list(MT.in_played_order(career, tg[tg.team == team]).outcome.tail(5))
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
                rows += [[player_link(r.player), _n(r.wickets, "wkt"), f"econ {fmt(r.economy, 2)}", ""] for r in bowls.itertuples()]
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
                st.markdown(f"Batting first **{pct(r.bf_win_pct)}** ({int(r.bf_won)} of {int(r.bf_decided)}) · "
                            f"{second} **{pct(r.ch_win_pct)}** ({int(r.ch_won)} of {int(r.ch_decided)}).")
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
                     f"{pct(r.win_pct)}"] for r in op.head(6).itertuples()]
            if rows:
                html_table(rows, ["Opponent", "Played", "Record", "Win %"], numeric={1, 3})
            # ---------------------------------------------------------------- next opponent
            # whoever is next in your schedule first, then every other side here (met or not)
            here_ = m[m.section == section]
            sec_fmts = set(here_.format)
            up_ = state.memo(FX.upcoming, career, state.fixtures(career), (team,))
            sched_o = [o for o in dict.fromkeys(up_[up_.format.isin(sec_fmts)].opponent) if o != team] if len(up_) else []
            opps = sched_o + sorted((set(here_.home) | set(here_.away)) - {team} - set(sched_o))
            if opps:
                c1, c2 = st.columns([2, 1], vertical_alignment="bottom")
                if st.session_state.get(f"mt_next_{key}") not in opps:
                    st.session_state[f"mt_next_{key}"] = opps[0]
                nxt = c1.selectbox("Next opponent", opps, key=f"mt_next_{key}",
                                   format_func=lambda t: t + ("  ·  next match" if sched_o and t == sched_o[0] else
                                                              "  ·  in your schedule" if t in sched_o else ""),
                                   help="Your scheduled opponents first (Fixtures page), then every side here.")
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
            html_table([[f"{r.season}", r.section, TP.wdl(r._asdict()), f"{pct(r.win_pct)}", r.finish or "–"]
                        for r in hi.itertuples()], ["Season", "Section", "Record", "Win %", "Finished"], numeric={3})
        # ---------------------------------------------------------------- 116 · your notes
        with safe_section("notes"), st.container(border=True):
            nt = state.notes(career)
            mine_m = m[((m.home == team) | (m.away == team)) & m.source.isin(list(nt))].sort_values("date", ascending=False)
            st.markdown("**📝 Your match notes**")
            if mine_m.empty:
                st.caption("No notes yet. Open any match on the Matches page and write one under the score.")
            else:
                html_table([[f"{r.date:%d %b %Y}", match_link(r.match_id, f"{r.home} v {r.away}"), esc(nt[r.source])]
                            for r in mine_m.head(10).itertuples()], ["Date", "Match", "Note"], raw={1, 2})
    lg = MT.last_game(career, team)
    if lg is not None:
        st.markdown(f"Latest scorecard: {match_link(lg.match_id, f'{lg.home} v {lg.away}, {lg.date:%d %b %Y}')}",
                    unsafe_allow_html=True)
