import streamlit as st

from ccstats import players as PL
from ccstats import preview as PV
from ccstats import teamplay as TP
from ccstats.stats import Scope
from ui import state
from ui.charts import fmt
from ui.theme import html_table, page_header, player_link, safe_section

career = state.current()
if career is None:
    st.info("Load a career on the Home page first.")
    st.stop()

m = career.matches
page_header("Team planner", "Plan your next game",
            "For the team you manage: what you need to qualify, a batting order from where each player does best, how "
            "to use your bowlers, who's knocking on the door and which partnerships work.")
sections = m.section.value_counts()
mine_all = state.my_teams(career)
# open on a section where your team plays
default_sec = next((s for s in sections.index if set(m[m.section == s].home) & set(mine_all)
                    or set(m[m.section == s].away) & set(mine_all)), sections.index[0])
state.recall("pl_section_t", "section", [s_ for s_ in sections.index if s_ == default_sec or not mine_all])
if "pl_section_t" not in st.session_state:
    st.session_state["pl_section_t"] = default_sec
c1, c2, c3 = st.columns([2, 1, 1.6])
section = c1.selectbox("Section", list(sections.index), key="pl_section_t", on_change=state.remember("pl_section_t", "section"), format_func=lambda s: f"{s} · {sections[s]} matches")
seasons = sorted(m[m.section == section].season.unique(), reverse=True)
state.recall("pl_season_t", "season", ["All seasons"] + seasons)
season = c2.selectbox("Season", ["All seasons"] + seasons, key="pl_season_t", on_change=state.remember("pl_season_t", "season"))
ids = Scope(sections=[section], seasons=[] if season == "All seasons" else [season]).match_ids(m)
here = m[m.match_id.isin(ids)]
teams = sorted(set(here.home) | set(here.away))
if not teams:
    st.info("No matches here yet.")
    st.stop()
default_team = next((t for t in mine_all if t in teams), teams[0])
if st.session_state.get("pl_team_t") not in teams:
    st.session_state["pl_team_t"] = default_team
team = c3.selectbox("Team", teams, key="pl_team_t")  # the planner is for the team you manage: no remembered team
if not mine_all:
    st.caption("Tip: pick your team(s) under **My team** in the sidebar and every page opens on them.")

tabs = st.tabs(["Qualification", "Batting order", "Bowling plan", "Knocking on the door", "Partnerships"])

# ---------------------------------------------------------------- 58
with tabs[0], safe_section("qualification"):
    evs = here[~here.knockout & (here.home.eq(team) | here.away.eq(team))]
    options = sorted({(e, s_) for e, s_ in zip(evs.event, evs.season)}, key=lambda x: (x[1], x[0]), reverse=True)
    options = [o for o in options if TP.has_knockouts(career, o[0])]
    if not options:
        st.info("Nothing to qualify for here: no knockout stage (bilateral series, or a league the table decides).")
    else:
        q1, q2, q3 = st.columns([2, 1, 1])
        ev = q1.selectbox("Competition", options, format_func=lambda o: f"{o[0]} {o[1]}", key="pl_q_event")
        d = TP.qualification_defaults(career, *ev)
        # where the best next-placed sides also go through (the Blast's best thirds), that place can still be enough
        d = dict(d, places=d["places"] + (1 if d.get("extra") else 0))
        games = q2.number_input("League games per team", 1, 60, d["games"], key=f"pl_q_games_{ev}")
        places = q3.number_input("Places that go through (per group)", 1, 16, d["places"], key=f"pl_q_places_{ev}")
        q = state.memo(TP.qualification, career, ev[0], ev[1], int(games), int(places))
        if q.empty:
            st.caption("No league table here yet.")
        else:
            grp = q[q.team == team].group.iloc[0] if (q.team == team).any() else q.group.iloc[0]
            g = q[q.group == grp]
            me = g[g.team == team]
            if len(me):
                r = me.iloc[0]
                msg = {"Through": f"✅ **{team} are through** on points alone.",
                       "Out": f"❌ **{team} can't reach the top {places}** any more.",
                       "Alive": f"🔶 **{team} are still in it**: {r.need} to reach the usual cut."}[r.status]
                st.markdown(msg)
            rows = [[r.position, r.team, r.played, fmt(r.points, 0), r.left, fmt(r.max_points, 0),
                     {"Through": "✅ Through", "Out": "❌ Out", "Alive": "🔶 Alive"}[r.status], r.need]
                    for r in g.itertuples()]
            html_table(rows, ["#", "Team", "Played", "Points", "Left", "Most possible", "Status", "Needs"],
                       numeric={0, 2, 3, 4, 5}, row_class=["hi" if t == team else "" for t in g.team])
            st.caption(f"Guesses you can change above: {d['games']} league games each and {d['places']} going through, "
                       "from an earlier season of this competition where there is one. 'Through' and 'out' only when "
                       "points alone settle it (net run rate can split teams level on points). 'Needs' aims at the "
                       "points the team in the last qualifying place is on course for.")

# ---------------------------------------------------------------- 59
with tabs[1], safe_section("batting order"):
    order = state.memo(PL.batting_order, career, ids, team)
    recent = sorted(PV.recent_xi(career, ids, team, games=5))
    if order.empty:
        st.caption("No innings yet.")
    else:
        only_recent = st.toggle("Only players from the last 5 games", value=True, key="pl_bo_recent")
        sug = PL.suggested_order(order, recent if only_recent else None)
        left, right = st.columns([1, 1.6], gap="medium")
        with left, st.container(border=True):
            st.markdown("**Suggested top 7**")
            if sug.empty:
                st.caption("Not enough innings at each position yet.")
            else:
                html_table([[r.slot, player_link(r.player), r.group, f"{r.vs_avg:+.1f}", r.innings] for r in sug.itertuples()],
                           ["", "Player", "From innings at", "Runs v average", "Inns"], numeric={3, 4}, raw={1})
                st.caption("Each slot goes to the player who beats the average batter there by most (2+ innings there).")
        with right, st.container(border=True):
            st.markdown("**Every batter by position** · runs per innings against the average batter there")
            show = order.sort_values(["player", "group"])
            if only_recent:
                show = show[show.player.isin(recent)]
            html_table([[player_link(r.player), r.group, r.innings, fmt(r.per_innings, 1), fmt(r.strike_rate, 1),
                         f"{r.vs_avg:+.1f}"] for r in show.itertuples()],
                       ["Player", "Position", "Inns", "Runs per inns", "SR", "v average"], numeric={2, 3, 4, 5}, raw={0},
                       row_class=["hi" if r.group == r.best else "" for r in show.itertuples()])
            st.caption("Highlighted: each player's best position.")

# ---------------------------------------------------------------- 60
with tabs[2], safe_section("bowling plan"):
    bp = state.memo(PL.bowling_plan, career, ids, team)
    with st.container(border=True):
        st.markdown("**How to use your bowlers** · where their wickets come from, and what they cost")
        if bp.empty:
            st.caption("No bowler has bowled 30+ balls yet.")
        else:
            by_avg = bp.attrs.get("by_average", False)
            html_table([[player_link(r.player), r.innings, r.wickets, r.top, r.middle, r.tail,
                         fmt(r.economy, 2) if not by_avg else fmt(r.economy / 6 * r.strike_rate, 1) if r.wickets else "–",
                         fmt(r.strike_rate, 1), r.tags] for r in bp.itertuples()],
                       ["Bowler", "Inns", "Wkts", "Top 3", "4-7", "8-11", "Avg" if by_avg else "Econ", "SR", "Use as"],
                       numeric={1, 2, 3, 4, 5, 6, 7}, raw={0})
            if by_avg:
                st.caption(f"Section average: {bp.attrs['average']:.1f} runs per wicket, a wicket every "
                           f"{bp.attrs['strike_rate']:.0f} balls. In multi-day cricket the cost of each wicket matters "
                           "more than the run rate, so 'cheap' and 'costly' go by bowling average. Top-order hunters for "
                           "the new ball; tail cleaners to finish an innings off.")
            else:
                st.caption(f"Section average: economy {bp.attrs['economy']:.2f}, strike rate {bp.attrs['strike_rate']:.1f}. "
                           "Top-order hunters for the new ball; tail cleaners to finish an innings off; the cheap ones "
                           "for the overs you need to control.")

# ---------------------------------------------------------------- 63
with tabs[3], safe_section("knocking on the door"):
    kn = state.memo(PL.knocking, career, ids, team)
    with st.container(border=True):
        st.markdown("**Knocking on the door** · played under 40% of the games but did well when picked")
        if kn.empty:
            st.caption("Nobody on the fringes is outscoring the regulars right now.")
        else:
            html_table([[player_link(r.player), r.games, r.why] for r in kn.itertuples()], ["Player", "Games", "Why"],
                       numeric={1}, raw={0})
            st.caption("Small samples: a good game or two can put someone here, so treat it as a nudge.")

# ---------------------------------------------------------------- 65
with tabs[4], safe_section("partnerships"):
    left, right = st.columns(2, gap="medium")
    with left, st.container(border=True):
        bpairs = state.memo(PL.batting_pairs, career, ids, team)
        st.markdown("**Batting partners** · 2+ stands together")
        if bpairs.empty:
            st.caption("No pairs with 2+ stands yet.")
        else:
            html_table([[r.pair, r.stands, r.runs, f"{r.average:.1f}", r.best, r.big_stands] for r in bpairs.head(15).itertuples()],
                       ["Pair", "Stands", "Runs", "Avg", "Best", f"{bpairs.attrs.get('stand', 50)}+"], numeric={1, 2, 3, 4, 5})
    with right, st.container(border=True):
        wpairs = state.memo(PL.bowling_pairs, career, ids, team)
        st.markdown("**Bowling partners** · bowled in the same innings 3+ times")
        if wpairs.empty:
            st.caption("No pairs yet.")
        else:
            html_table([[r.pair, r.innings, r.wickets, f"{r.per_innings:.1f}", fmt(r.economy, 2)] for r in wpairs.head(15).itertuples()],
                       ["Pair", "Inns", "Wkts", "Wkts/inns", "Econ"], numeric={1, 2, 3, 4})
