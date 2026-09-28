import pandas as pd
import streamlit as st

from ccstats import analysis as A
from ccstats import extras as E
from ccstats.stats import Scope
from ui import state
from ui.charts import CONFIG, bars, fmt
from ui.theme import kpis, page_header

career = state.current()
if career is None:
    st.info("Load a career on the Home page first.")
    st.stop()

m = career.matches
page_header("Opponent preview", "Know your opponent",
            "Pick the team you're about to play: their form, their dangermen, how their batters get out and how "
            "often they collapse. Add your own team to see the head to head.")
c1, c2, c3 = st.columns([2, 1.5, 1.5])
sections = m.section.value_counts()
section = c1.selectbox("Section", list(sections.index), key="op_section", format_func=lambda s: f"{s} · {sections[s]} matches")
ids = Scope(sections=[section]).match_ids(m)
here = m[m.match_id.isin(ids)]
teams = sorted(set(here.home) | set(here.away))
opp = c2.selectbox("Opponent", teams, key="op_opp")
mine = c3.selectbox("Your team (optional)", ["—"] + [t for t in teams if t != opp], key="op_mine")

pv = E.opponent_preview(career, ids, opp)
tm = pv["matches"]
rec = A.team_record(tm)
sk = A.streaks(list(tm.outcome))
form = "".join(pv["recent"].outcome) or "–"
kpis([("Played", f"{rec['played']}"), ("Won–Lost", f"{rec['won']}–{rec['lost']}"),
      ("Win %", fmt(rec["win_pct"], 0) + "%" if rec["played"] else "–"), ("Last 5", form),
      ("Collapses", f"{pv['collapses']}")])
st.caption("Last 5: W won, L lost, D drawn, T tied, oldest first. Collapses: innings where they lost 4 or more wickets for 30 runs or fewer, out of " f"{pv['innings']} innings. "
           "Form uses their most recent matches in this section.")

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

left, right = st.columns(2, gap="medium")
with left:
    with st.container(border=True):
        st.markdown("**How their batters get out** · share of dismissals")
        how = pv["how_out"]
        if how.empty:
            st.caption("Not dismissed yet.")
        else:
            st.plotly_chart(bars([h.title() for h in how.index], how.values, "% of dismissals", 0),
                            width="stretch", config=CONFIG, key="op_how")
            main = how.index[0]
            st.caption(f"Most often **{main}** ({how.iloc[0]:.0f}%). A high bowled/lbw share means attacking the stumps "
                       "works; a high caught share means they give catches.")
with right:
    with st.container(border=True):
        st.markdown("**Where their runs come from**")
        dep = pv["depth"]
        st.plotly_chart(bars(dep.group, dep.share, "% of their runs", 0, notes=[f"{r} runs" for r in dep.runs]),
                        width="stretch", config=CONFIG, key="op_depth")
        st.caption("If most runs come from the top order, early wickets hurt them most.")

if mine != "—":
    games = here[((here.home == mine) & (here.away == opp)) | ((here.home == opp) & (here.away == mine))].sort_values("date")
    with st.container(border=True):
        wins, losses = int((games.winner == mine).sum()), int((games.winner == opp).sum())
        st.markdown(f"**{mine} v {opp}** · {len(games)} meeting{'s' if len(games) != 1 else ''}: "
                    f"{mine} {wins} – {losses} {opp}")
        if len(games):
            st.dataframe(pd.DataFrame({"Date": games.date.dt.strftime("%d %b %Y"), "Stage": games.stage,
                                       "Result": games.result}).iloc[::-1], hide_index=True, width="stretch")
            runs, wkts = E.rivalry_players(career, ids, mine, opp)
            theirs_r, theirs_w = runs[runs.team == opp].head(3), wkts[wkts.team == opp].head(3)
            if len(theirs_r) or len(theirs_w):
                st.markdown("**Their best against you:** " + ", ".join(
                    [f"{p} {r} runs" for p, r in zip(theirs_r.player, theirs_r.runs)] +
                    [f"{p} {w} wickets" for p, w in zip(theirs_w.player, theirs_w.wickets)]))
        else:
            st.caption("They haven't met in this section yet.")
