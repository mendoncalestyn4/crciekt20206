import numpy as np
import pandas as pd
import streamlit as st

from ccstats import analysis as A
from ccstats import extras as E
from ccstats import preview as PV
from ccstats import seasonal as SN
from ccstats import teamplay as TP
from ccstats import winprob as WP
from ui import state
from ui.charts import ordinal, _n, pct, CONFIG, bars, fmt, say, signed
from ui.theme import (chart_note, esc, form_strip, html_table, kpis, match_link, page_header, player_link, safe_section)

career = state.current()
if career is None:
    st.info("Load a career on the Home page first.")
    st.stop()

m = career.matches
page_header("Opponent preview", "Know your opponent",
            "Pick your team and the team you're about to play: your history against them, who gets whom out, their "
            "form, their key players and weak spots, and a plan to beat them.")

INTL = "Internationals"
intl_sections = [s for s in ("Tests", "ODIs", "T20Is") if s in set(m.section)]
counts = m.section.value_counts()
choices = [s for s in counts.index if s not in intl_sections]
if intl_sections:
    choices = [INTL] + choices
mine_default = state.my_teams(career)

c1, c2, c3, c4 = st.columns([1.7, 1.3, 1.5, 1.5])
state.recall("op_section", "section", choices)
pick = c1.selectbox("Competition", choices, key="op_section", on_change=state.remember("op_section", "section"),
                    format_func=lambda s: f"{s} · {int(counts[intl_sections].sum())} matches" if s == INTL
                    else f"{s} · {counts[s]} matches")
if pick == INTL:
    fmt_pick = c2.segmented_control("Format", intl_sections + ["All"], default=intl_sections[0], key="op_format") \
        or intl_sections[0]
    sections = intl_sections if fmt_pick == "All" else [fmt_pick]
else:
    sections = [pick]
    c2.caption(" ")
ids = m[m.section.isin(sections)].match_id
here = m[m.match_id.isin(ids)]
teams = sorted(set(here.home) | set(here.away))
if len(teams) < 2:
    st.info("Not enough teams here yet.")
    st.stop()
mine_opts = ["—"] + teams
default_mine = next((t for t in mine_default if t in teams), None)
if "op_mine" not in st.session_state or st.session_state["op_mine"] not in mine_opts:
    st.session_state["op_mine"] = default_mine or "—"
mine = c3.selectbox("Your team", mine_opts, key="op_mine")
opp_opts = [t for t in teams if t != mine]
opp = c4.selectbox("Opponent", opp_opts, key="op_opp")
mine = None if mine == "—" else mine
where_note = " + ".join(sections)

pv = state.memo(E.opponent_preview, career, ids, opp)
tm = pv["matches"]
rec = A.team_record(tm)
form = f"<span class='small'>{' '.join(pv['recent'].outcome)}</span>" if len(pv["recent"]) else "–"
kpis([("Played", f"{rec['played']}"), ("Won–Lost", f"{rec['won']}–{rec['lost']}"),
      ("Win %", fmt(rec["win_pct"], 0) + "%" if rec["played"] else "–"), ("Last 5", form),
      ("Collapses", f"{pv['collapses']}")])
st.caption(f"{opp} in {where_note}. Last 5: W won, L lost, D drawn, T tied, oldest first. Collapses: innings where they "
           f"lost 4 or more wickets for 30 runs or fewer, out of {pv['innings']} innings.")

# ---------------------------------------------------------------- 110 · predicted result
if mine:
    with safe_section("predicted result"), st.container(border=True):
        p1, p2 = st.columns([3, 1.4], vertical_alignment="center")
        where_p = p2.segmented_control("Where", ["Home", "Away", "Neutral"], default="Neutral", key="op_pred_where") \
            or "Neutral"
        pr = state.memo(WP.predict, career, ids, mine, opp, where_p.lower())
        parts = [f"**{mine} {pr['win']:.0f}%**"] + ([f"draw {pr['draw']:.0f}%"] if pr["multi"] else []) + \
            [f"**{opp} {pr['lose']:.0f}%**"]
        p1.markdown("**🔮 Predicted result** · " + " · ".join(parts))
        rows = [[name, why, (f"{val:.0f}%" if i == 0 else f"{val:+.1f}") ] for i, (name, why, val) in enumerate(pr["steps"])]
        html_table(rows, ["Step", "Why", f"{mine} chance (start, then change)"], numeric={2})
        st.caption("Built in steps: the Elo chance first, then small nudges for recent form, head to head and home "
                   "ground, each capped so no single one can swing it far."
                   + (" In multi-day cricket the draw share comes from how often games here are drawn." if pr["multi"] else ""))

# ---------------------------------------------------------------- 80 · game plan
if mine:
    with safe_section("game plan"):
        plan = state.memo(PV.game_plan, career, ids, mine, opp)
        with st.container(border=True):
            st.markdown(f"**📋 Game plan for {mine} v {opp}**")
            if plan:
                st.markdown("\n".join(f"- {p}" for p in plan))
            else:
                st.caption("Nothing stands out yet: not enough games for a clear pattern. Play a few more and it fills in.")

tab_h2h, tab_them, tab_sbs, tab_xi = st.tabs(["Head to head", f"About {opp}", "Side by side", "Your best XI v them"])

# ---------------------------------------------------------------- 54 · meetings
with tab_h2h:
    if not mine:
        st.info("Pick your team above to see your history against them.")
    else:
        with safe_section("head to head"):
            mt = state.memo(PV.meetings, career, ids, mine, opp)
            r = mt["record"]
            if not r["played"]:
                st.markdown(f"**{mine} and {opp} have never met in {where_note}.** Here is what to expect from them "
                            "instead: see the other tabs for their form, key players and weak spots.")
                other = m[((m.home == mine) & (m.away == opp)) | ((m.home == opp) & (m.away == mine))]
                if len(other):
                    st.caption(f"They have met {len(other)} time(s) in other competitions: "
                               + ", ".join(sorted(set(other.section))) + ".")
            else:
                kpis([("Meetings", f"{r['played']}"), (f"{mine} record", TP.wdl(r)),
                      ("Win %", fmt(r["win_pct"], 0) + "%"), ("Last 5", form_strip(mt["last5"]))])
                h = mt["how"]
                ty = mt["typical"]
                multi = TP.is_multi(TP.games(career, mt["games"].match_id))
                second = "batting second" if multi else "chasing"
                st.markdown(
                    f"**How the games were won:** {mine} {h['bat_first_wins'][mine]} batting first and "
                    f"{h['chasing_wins'][mine]} {second}; {opp} {h['bat_first_wins'][opp]} batting first and "
                    f"{h['chasing_wins'][opp]} {second}.  \n**Typical first-innings score:** {mine} "
                    f"{fmt(ty[mine], 0)}, {opp} {fmt(ty[opp], 0)}.")
                # key players side by side
                cols = st.columns(2, gap="medium")
                for col, team in zip(cols, (mine, opp)):
                    k = mt["key"][team]
                    with col:
                        with st.container(border=True):
                            st.markdown(f"**{team}'s key players in these games**")
                            rows, cls = [], []
                            for x in k["runs"].itertuples():
                                rows.append([player_link(x.player), f"{x.runs} runs", f"{x.innings} inns, best {x.best}"])
                                cls.append("" if x.player in k["current"] else "dim")
                            for x in k["wickets"].itertuples():
                                rows.append([player_link(x.player), _n(x.wickets, "wkt"), f"economy {fmt(x.economy, 2)}"])
                                cls.append("" if x.player in k["current"] else "dim")
                            for p, n in k["potm"].items():
                                rows.append([player_link(p), f"{n} × Player of the Match", ""])
                                cls.append("" if p in k["current"] else "dim")
                            if rows:
                                html_table(rows, ["Player", "", ""], raw={0}, row_class=cls)
                            else:
                                st.caption("No figures yet.")
                st.caption("Greyed out: not in that team's last 3 games, so maybe not playing now.")
                st.markdown("**Every meeting** · newest first")
                cards = []
                for cd in mt["cards"]:
                    sides = "".join(
                        f"<div class='side'><span>{esc(t)}</span><b>{esc(s['score'])}</b></div>"
                        f"<div class='who'>🏏 {esc(s['top_bat'])} · 🎯 {esc(s['top_bowl'])}</div>"
                        for t, s in cd["sides"].items())
                    stage = f" · {esc(cd['stage'])}" if cd["stage"] else ""
                    potm = f"<div class='who'>⭐ Player of the Match: {esc(cd['potm'])}</div>" if cd["potm"] else ""
                    cards.append(f"<div class='mcard'><div class='top'><span>{cd['date']:%d %b %Y} · {esc(cd['event'])}{stage}"
                                 f"</span>{match_link(cd['match_id'], 'Scorecard →')}</div>{sides}{potm}"
                                 f"<div class='story'>{esc(cd['story'])}</div></div>")
                st.markdown("<div class='mcards'>" + "".join(cards) + "</div>", unsafe_allow_html=True)

        # ---------------------------------------------------------------- 55 · match-ups
        st.write("")
        with safe_section("match-ups"):
            with st.container(border=True):
                st.markdown("**Who gets whom out** · dismissals by each bowler of each batter (run-outs left out)")
                t1, t2 = st.columns([2, 1.4])
                scope_mu = t1.segmented_control("Count", ["Only our meetings", "Every match these players faced each other"],
                                                default="Only our meetings", key="op_mu_scope") or "Only our meetings"
                current_only = t2.toggle("Current players only", key="op_mu_cur",
                                         help="Only players in each team's last 5 games here.")
                mu = state.memo(PV.matchups, career, ids, mine, opp, everywhere=scope_mu != "Only our meetings",
                                current_only=current_only)
                cols = st.columns(2, gap="medium")
                for col, key_, title, tag in ((cols[0], "their_bowlers", f"{opp}'s bowlers v your batters", "⚠️ Danger man"),
                                              (cols[1], "our_bowlers", f"Your bowlers v {opp}'s batters", "🎯 Best weapon")):
                    d = mu[key_].head(10)
                    with col:
                        st.markdown(f"**{title}**")
                        if d.empty:
                            st.caption("No dismissals between these players yet.")
                            continue
                        rows = [[player_link(x.bowler), player_link(x.player), x.dismissals, x.innings_met,
                                 f"{x.runs_when_out} ({x.balls_when_out})"] for x in d.itertuples()]
                        html_table(rows, ["Bowler", "Batter", "Out", "Innings met", "Runs (balls) in those innings"],
                                   numeric={2, 3}, raw={0, 1}, row_class=["hi"] + [""] * (len(rows) - 1))
                        st.caption(f"{tag}: {d.bowler.iloc[0]}, {_n(d.dismissals.iloc[0], 'time')} v {d.player.iloc[0]}.")
                st.caption("Innings met: innings where the batter batted and the bowler bowled at them. The scorecards don't "
                           "say which bowler each run came off, so the runs are the batter's whole score in the innings "
                           "that bowler got them out.")

# ---------------------------------------------------------------- their side
with tab_them:
    left, right = st.columns(2, gap="medium")
    with left:
        with st.container(border=True):
            st.markdown("**Batters in form** · runs in their last 10 matches")
            top = pv["batters"].head(6)
            if top.empty:
                st.caption("No innings yet.")
            else:
                st.plotly_chart(bars(top.player, top.runs, "Runs", notes=[
                    f"{i} innings · average {fmt(a, 1)} · strike rate {fmt(s, 1)} · best {b}"
                    for i, a, s, b in zip(top.innings, top.average, top.strike_rate, top.best)]),
                    width="stretch", config=CONFIG, key="op_bat")
                tot = pv["batters"].runs.sum()
                share = top.runs.iloc[0] / tot * 100 if tot else 0
                chart_note(f"{top.player.iloc[0]} has {top.runs.iloc[0]} runs in their last 10 games, {share:.0f}% of "
                           f"the {tot} runs {opp}'s batters made in that time.",
                           "Who is scoring for them right now: the batters to plan for and get out early.")
    with right:
        with st.container(border=True):
            st.markdown("**Bowlers in form** · wickets in their last 10 matches")
            top = pv["bowlers"].head(6)
            if top.empty:
                st.caption("No bowling yet.")
            else:
                st.plotly_chart(bars(top.player, top.wickets, "Wickets", notes=[
                    f"{i} innings · economy {fmt(e, 2)} · average {fmt(a, 1)}"
                    for i, e, a in zip(top.innings, top.economy, top.average)]),
                    width="stretch", config=CONFIG, key="op_bowl")
                totw = pv["bowlers"].wickets.sum()
                share = top.wickets.iloc[0] / totw * 100 if totw else 0
                chart_note(f"{top.player.iloc[0]} has {int(top.wickets.iloc[0])} wickets in their last 10 games, "
                           f"{share:.0f}% of the {int(totw)} {opp} took.",
                           "Who is taking their wickets right now: the bowlers to see off or play carefully.")

    left, right = st.columns(2, gap="medium")
    with left:
        with safe_section("key wicket"), st.container(border=True):
            kw = state.memo(PV.key_wicket, career, ids, opp)
            st.markdown("**🔑 Key wicket** · the batter whose score decides their results")
            if kw.empty:
                st.caption("Not enough games yet.")
            else:
                rows = [[player_link(x.player), x.innings, f"{pct(x.win_good)}", f"{pct(x.win_bad)}",
                         f"{x.gap:+.0f}"] for x in kw.head(5).itertuples()]
                html_table(rows, ["Batter", "Inns", f"Win % when {kw.attrs['bar']}+", "Win % when not", "Gap"],
                           numeric={1, 2, 3, 4}, raw={0}, row_class=["hi"] + [""] * (len(rows) - 1))
    with right:
        with safe_section("weak spot"), st.container(border=True):
            ws = state.memo(PV.weak_spot, career, ids, opp)
            st.markdown("**🩹 Weak spot** · their average stand for each wicket v every team here")
            ws = ws[ws.stands >= 2]
            if ws.empty:
                st.caption("Not enough innings yet.")
            else:
                st.plotly_chart(bars([f"{ordinal(w)} wicket"
                                      for w in ws.wicket], ws.vs, "% above or below the average stand", 0, signed=True,
                                     texts=[f"{v:+.0f}% · {a:.0f} v {b:.0f}" for v, a, b in zip(ws.vs, ws.average, ws["all"])],
                                     notes=[f"{n} stands" for n in ws.stands]),
                                width="stretch", config=CONFIG, key="op_weak")
                best_ = ws.sort_values("vs").iloc[-1]
                worst_ = ws.sort_values("vs").iloc[0]
                chart_note(f"Their {ordinal(best_.wicket)} "
                           f"wicket stand is {best_.vs:+.0f}% against every team's ({best_.average:.0f} v {best_['all']:.0f} "
                           f"runs); the {ordinal(worst_.wicket)} "
                           f"is {worst_.vs:+.0f}% ({worst_.average:.0f} v {worst_['all']:.0f}). Blue: better than "
                           "average; red: worse.",
                           "Finds where their batting order is soft, so you know which wicket to push hardest for.")

    left, right = st.columns(2, gap="medium")
    with left:
        with safe_section("attack to target"), st.container(border=True):
            at = state.memo(PV.attack_to_target, career, ids, opp)
            key = at.attrs.get("key", "economy")
            st.markdown("**🎯 Attack to target** · their regular bowlers, most expensive first")
            if at.empty:
                st.caption("No regular bowlers yet.")
            else:
                base = at.attrs[key]
                rows = [[player_link(x.player), x.innings, int(x.wickets), fmt(x.economy, 2), fmt(x.average, 1)]
                        for x in at.head(6).itertuples()]
                html_table(rows, ["Bowler", "Inns", "Wkts", "Econ", "Avg"], numeric={1, 2, 3, 4}, raw={0},
                           row_class=["hi" if (getattr(x, key) or 0) > base else "" for x in at.head(6).itertuples()])
                st.caption(f"Highlighted: worse than the average bowler here ({'economy' if key == 'economy' else 'average'} "
                           f"{fmt(base, 2 if key == 'economy' else 1)}).")
    with right:
        with safe_section("batting styles"), st.container(border=True):
            bs = state.memo(PV.batting_strip, career, ids, opp)
            st.markdown("**🏏 How their batters play** · average and strike rate against the average batter")
            if len(bs):
                rows = [[player_link(x.player), int(x.runs), fmt(x.average, 1), fmt(x.strike_rate, 1), x.style]
                        for x in bs.itertuples()]
                html_table(rows, ["Batter", "Runs", "Avg", "SR", "Style"], numeric={1, 2, 3}, raw={0})
            else:
                st.caption("No innings yet.")

    left, right = st.columns(2, gap="medium")
    with left:
        with safe_section("batting first or chasing"), st.container(border=True):
            ce = state.memo(PV.chase_extremes, career, ids, opp)
            second = "Batting second" if ce["multi"] else "Chasing"
            st.markdown(f"**Batting first or {second.lower()}**")
            html_table([["Batting first", TP.wdl(ce["first"]), f"{pct(ce['first']['win_pct'])}"],
                        [second, TP.wdl(ce["second"]), f"{pct(ce['second']['win_pct'])}"]],
                       ["", "W–L", "Win %"], numeric={2})
            notes = []
            if ce["best_chase"]:
                r_, w_, mid, o_ = ce["best_chase"]
                notes.append(f"Highest chase: {match_link(mid, f'{r_}/{w_} v {o_}')}")
            if ce["low_defend"]:
                r_, w_, mid, o_, allout = ce["low_defend"]
                total = f"{r_}" if allout else f"{r_}/{w_}"
                notes.append(f"Lowest total defended: {match_link(mid, total + ' v ' + o_)}")
            if notes:
                st.markdown(" · ".join(notes), unsafe_allow_html=True)
    with right:
        with safe_section("home and away"), st.container(border=True):
            vr = state.memo(PV.venue_record, career, ids, opp)
            st.markdown("**Home and away**")
            where = st.segmented_control("You are", ["Home", "Away", "Neutral"], default="Home", key="op_where") or "Home"
            theirs = {"Home": "away", "Away": "home", "Neutral": "neutral"}[where]
            r_ = vr[theirs]
            html_table([[f"{v.title()} games", TP.wdl(vr[v]), f"{pct(vr[v]['win_pct'])}"] for v in ("home", "away", "neutral")
                        if vr[v]["played"]], ["", "W–L", "Win %"], numeric={2},
                       row_class=["hi" if v == theirs else "" for v in ("home", "away", "neutral") if vr[v]["played"]])
            st.caption(f"With you at {where.lower()}, they are {'at a neutral ground' if theirs == 'neutral' else theirs}: "
                       + (f"{TP.wdl(r_)} there ({pct(r_['win_pct'])})." if r_["played"] else "no games like that yet."))

    left, right = st.columns(2, gap="medium")
    with left:
        with safe_section("big matches"), st.container(border=True):
            bm = state.memo(PV.big_matches, career, ids, opp)
            st.markdown("**🏆 Big-match record**")
            rows = [[label, TP.wdl(r_), f"{pct(r_['win_pct'])}"] for label, r_ in
                    (("Knockouts", bm["knockouts"]), ("Finals", bm["finals"]), ("Series deciders", bm["deciders"]))
                    if r_["played"]]
            if rows:
                html_table(rows, ["", "W–L", "Win %"], numeric={2})
            else:
                st.caption("No knockouts, finals or series deciders yet.")
    with right:
        with safe_section("trend"), st.container(border=True):
            tr = state.memo(PV.trend, career, ids, opp)
            st.markdown("**📈 Trend**")
            st.markdown(f"Last 5: {form_strip(tr['last'])}", unsafe_allow_html=True)
            parts = [f"Win % last 5: **{pct(tr['recent']['win_pct'])}** (before that {pct(tr['before']['win_pct'])})."]
            if np.isfinite(tr["elo_now"]):
                d = tr["elo_now"] - tr["elo_then"]
                parts.append(f"Elo rating **{tr['elo_now']:.0f}** ({d:+.0f} over the last 5), "
                             f"{tr['elo_rank']} of {tr['teams']} here.")
            st.markdown(" ".join(parts))

    left, right = st.columns(2, gap="medium")
    with left:
        with st.container(border=True):
            st.markdown("**How their batters get out** · share of dismissals")
            how = pv["how_out"]
            if how.empty:
                st.caption("Not dismissed yet.")
            else:
                st.plotly_chart(bars([say(h) for h in how.index], how.values, "% of dismissals", 0),
                                width="stretch", config=CONFIG, key="op_how")
                chart_note(f"{how.iloc[0]:.0f}% of their dismissals are {say(how.index[0]).lower()}"
                           + (f" and {how.iloc[1]:.0f}% {say(how.index[1]).lower()}" if len(how) > 1 else "") + ".",
                           "How to get them out: a high bowled or lbw share means attacking the stumps works; a high "
                           "caught share means set fields and wait for the mistake.")
    with right:
        with st.container(border=True):
            st.markdown("**Where their runs come from**")
            dep = pv["depth"]
            st.plotly_chart(bars(dep.group, dep.share, "% of their runs", 0, notes=[f"{r} runs" for r in dep.runs]),
                            width="stretch", config=CONFIG, key="op_depth")
            if len(dep):
                d0 = dep.sort_values("share", ascending=False).iloc[0]
                chart_note(f"{d0.share:.0f}% of their runs come from the {d0.group.lower()} ({d0.runs} runs).",
                           "If most runs come from the top order, early wickets hurt them most; if the middle or tail "
                           "score a lot, keep attacking after the top order is gone.")

# ---------------------------------------------------------------- 79 · side by side
with tab_sbs:
    if not mine:
        st.info("Pick your team above to compare the two sides.")
    else:
        with safe_section("side by side"):
            sb = state.memo(PV.side_by_side, career, ids, mine, opp)
            rows = []
            for x in sb.itertuples():
                a = fmt(x.mine, x.dec) if pd.notna(x.mine) else "–"
                b = fmt(x.theirs, x.dec) if pd.notna(x.theirs) else "–"
                if "%" in x.measure and pd.notna(x.mine):
                    a += "%"
                if "%" in x.measure and pd.notna(x.theirs):
                    b += "%"
                rows.append([x.measure, ("<span class='tick'>✓</span> " if x.better == "mine" else "") + esc(a),
                             ("<span class='tick'>✓</span> " if x.better == "theirs" else "") + esc(b)])
            with st.container(border=True):
                st.markdown(f"**{mine} v {opp}** in {where_note} · ✓ marks the better side on each")
                html_table(rows, ["", mine, opp], raw={1, 2}, numeric={1, 2})
                n1, n2 = int((sb.better == "mine").sum()), int((sb.better == "theirs").sum())
                st.caption(f"{mine} ahead on {n1}, {opp} on {n2}. Lower is better for runs per wicket conceded and economy.")

# ---------------------------------------------------------------- 112 · your best XI against them
def signed_pct(v) -> str:
    t = signed(v)
    return t if t == "–" else t + "%"


with tab_xi:
    if not mine:
        st.info("Pick your team above to see how your players do against them.")
    else:
        with safe_section("best XI against them"):
            pb, pw = state.memo(SN.picks_against, career, ids, mine, opp)
            multi_x = pb.attrs.get("kind") == "multi"
            st.markdown(f"**Your {pb.attrs.get('season', '')} squad against {opp}** · each player's record v them "
                        "against their own record here")
            if pb.empty and pw.empty:
                st.caption(f"None of your current squad has played {opp} here yet.")
            else:
                verdict_cls = lambda v: "hi" if v.startswith("Pick") else "dim" if v.startswith("Think") else ""  # noqa: E731
                with st.container(border=True):
                    st.markdown("**Batting**")
                    if multi_x:
                        rows = [[player_link(r.player), r.inns_vs, r.runs_vs, fmt(r.avg_vs, 1), fmt(r.avg, 1),
                                 signed_pct(r.change), r.verdict] for r in pb.itertuples()]
                        html_table(rows, ["Player", "Inns v them", "Runs", "Avg v them", "Avg overall", "Change",
                                          "Verdict"], numeric={1, 2, 3, 4, 5}, raw={0},
                                   row_class=[verdict_cls(r.verdict) for r in pb.itertuples()])
                    else:
                        rows = [[player_link(r.player), r.inns_vs, r.runs_vs, fmt(r.avg_vs, 1), fmt(r.sr_vs, 0),
                                 fmt(r.avg, 1), fmt(r.sr, 0), signed_pct(r.change), r.verdict] for r in pb.itertuples()]
                        html_table(rows, ["Player", "Inns v them", "Runs", "Avg v them", "SR v them", "Avg overall",
                                          "SR overall", "Change", "Verdict"], numeric={1, 2, 3, 4, 5, 6, 7}, raw={0},
                                   row_class=[verdict_cls(r.verdict) for r in pb.itertuples()])
                with st.container(border=True):
                    st.markdown("**Bowling**")
                    rows = [[player_link(r.player), r.spells_vs, r.wkts_vs, fmt(r.avg_vs, 1)]
                            + ([] if multi_x else [fmt(r.econ_vs, 2)]) + [fmt(r.avg, 1)]
                            + ([] if multi_x else [fmt(r.econ, 2)]) + [signed_pct(r.change), r.verdict]
                            for r in pw.itertuples()]
                    cols_ = (["Player", "Innings v them", "Wkts", "Avg v them"] + ([] if multi_x else ["Econ v them"])
                             + ["Avg overall"] + ([] if multi_x else ["Econ overall"]) + ["Change", "Verdict"])
                    html_table(rows, cols_, numeric=set(range(1, len(cols_) - 1)), raw={0},
                               row_class=[verdict_cls(r.verdict) for r in pw.itertuples()])
                lines_ = []
                for what_, d_ in (("batting", pb), ("bowling", pw)):
                    good_ = list(d_[d_.verdict.str.startswith("Pick")].player)
                    bad_ = list(d_[d_.verdict.str.startswith("Think")].player)
                    if good_ or bad_:
                        lines_.append(f"**{what_.capitalize()}:** " + (f"pick {', '.join(good_)}" if good_ else "")
                                      + ("; " if good_ and bad_ else "") + (f"think again about {', '.join(bad_)}" if bad_ else "")
                                      + ".")
                if lines_:
                    st.markdown("  \n".join(lines_))
                st.caption(("Measured on average, as in multi-day cricket." if multi_x else
                            "Batting measured on average × strike rate; bowling on average × economy (lower is better).")
                           + " Change: their figure v this opponent against their own figure here; Pick = 25% or more "
                           "better v them, Think again = 25% or more worse. Needs 2 innings v them. Squad = everyone who "
                           "played for you in your latest season here; batting lists those who usually bat in the top 7.")
