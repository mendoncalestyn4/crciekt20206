import pandas as pd
import streamlit as st

from ccstats import extras as E
from ccstats import partnerships as P
from ccstats import winprob as W
from ccstats.competitions import shown_name
from ccstats.parser import balls_to_overs
from ui import state
from ui.charts import CONFIG, fmt, win_chance_chart, wicket_timeline
from ui.theme import chart_note, explain_list, html_table, match_link, page_header, safe_section, scoreboard

career = state.current()
if career is None:
    st.info("Load a career on the Home page first.")
    st.stop()

m = career.matches.sort_values(["date", "match_id"], ascending=False)
inn_all = career.innings


def score_of(mid, team):
    parts = []
    for r in inn_all[(inn_all.match_id == mid) & (inn_all.team == team)].sort_values("innings_no").itertuples():
        parts.append(f"{r.runs}" if r.all_out else f"{r.runs}/{r.wickets}{'d' if r.declared else ''}")
    return " & ".join(parts) or "–"


page_header("Matches", "Find a match", "Narrow the list by section or team, then type to search: a team, a date, a stage like "
            "'Final', or a result.")
c1, c2 = st.columns(2)
section = c1.selectbox("Section", ["All sections"] + sorted(m.section.unique()), key="mt_section")
pool = m if section == "All sections" else m[m.section == section]
teams = sorted(set(pool.home) | set(pool.away))
team = c2.selectbox("Team", ["All teams"] + teams, key="mt_team")
if team != "All teams":
    pool = pool[(pool.home == team) | (pool.away == team)]

labels = {r.match_id: f"{r.date:%d %b %Y} · {r.home} v {r.away} · {shown_name(r.section, r.event)}"
                      f"{' · ' + r.stage if r.stage else ''} · {r.result}"
          for r in pool.itertuples()}
wanted = st.query_params.get("match")
if wanted in labels and "mt_match" not in st.session_state:
    st.session_state["mt_match"] = wanted
mid = st.selectbox(f"Match ({len(labels)} to choose from, newest first)", list(labels), format_func=labels.get,
                   key="mt_match", index=None, placeholder="Type to search, e.g. 'Final' or 'Kent'")
if not mid:
    # ---------------------------------------------------------------- 102 · the best games
    with safe_section("best games"), st.container(border=True):
        if section == "All sections":
            st.markdown("**Best games you've played** · pick a section above to see its most exciting matches")
        else:
            sec_ids = career.matches[career.matches.section == section].match_id
            with st.spinner("Rating every match…"):
                best = state.memo(W.best_matches, career, sec_ids, 15)
            if team != "All teams":
                best = best[(best.home == team) | (best.away == team)]
            st.markdown(f"**Best games you've played in {section}** · rated 0-10 for excitement")
            html_table([[f"{r.rating:.1f}", match_link(r.match_id, f"{r.home} v {r.away}"), f"{r.date:%d %b %Y}",
                         r.stage or "", r.why] for r in best.itertuples()],
                       ["Rating", "Match", "Date", "Stage", "Why"], numeric={0}, raw={1})
            st.caption("Points for a close finish, a tie or super over, a comeback (the winner's chance fell low), a "
                       "final or knockout, a hundred, a big haul and high scoring. The closeness and haul bars follow "
                       "the format.")
    st.stop()

row = m[m.match_id == mid].iloc[0]
st.divider()
stage = f" · {row.stage}" if row.stage else ""
series = (f" · Match {int(row.series_match_no)}" + (f" of {int(row.series_length)}" if pd.notna(row.series_length) else "")
          if pd.notna(row.series_match_no) else "")
scoreboard(f"{shown_name(row.section, row.event)}{stage}{series} · {row.date:%d %b %Y}", row.home, score_of(mid, row.home), row.away,
           score_of(mid, row.away), row.result + (f" (super over: {row.super_over})" if row.super_over else "")
           + (f" · Player of the match: {row.player_of_match}" if row.player_of_match else ""))
st.write("")

# ---------------------------------------------------------------- 100, 101, 102 · report, rating, win chance
with safe_section("match report"):
    sec_ids_ = career.matches[career.matches.section == row.section].match_id
    states_ = state.memo(W.states, career, sec_ids_)
    kind_ = W.kind_of_ids(career, sec_ids_)
    line = W.match_line(career, mid, states_, kind_)
    score_, why_ = W.match_rating(career, mid, line)
    with st.container(border=True):
        st.markdown(f"**Match report** · <span class='grade {'A' if score_ >= 6 else 'B' if score_ >= 4 else 'C'}'>"
                    f"{score_:.1f}</span> / 10 for excitement" + (f" ({', '.join(why_)})" if why_ else ""),
                    unsafe_allow_html=True)
        st.markdown(W.match_report(career, mid, line))
    if len(line) > 1:
        with st.container(border=True):
            t1, t2 = line.attrs["team1"], line.attrs["team2"]
            multi_ = kind_ == "multi"
            st.markdown(f"**Win chance through the match** · {'won / drawn / lost' if multi_ else 'chance'} for {t1}, "
                        "at the start of each innings and after every wicket")
            st.plotly_chart(win_chance_chart(line, t1, t2, multi_), width="stretch", config=CONFIG, key="mt_winchance")
            sw = W.biggest_swing(line)
            low = W.lowest_for_winner(line)
            shows = (f"The biggest swing came at {sw['at']}: {t1}'s chance went from {sw['before']:.0f}% to "
                     f"{sw['after']:.0f}%." if sw else "")
            if low:
                shows += f" The winner's lowest point was {low[0]:.0f}% at {low[1]}."
            chart_note(shows or "Not enough similar games yet.",
                       f"Shows how the game swung. Each point is how often {row.section} games in the same spot (same "
                       "innings, same wickets down, a similar lead) ended in a win"
                       + (", draw or defeat" if multi_ else "") + ". The scorecards have no overs, so it uses runs and "
                       "wickets only; hover a point for how many games it rests on.")

inns = inn_all[inn_all.match_id == mid].sort_values("innings_no")
bat = career.batting[career.batting.match_id == mid]
bowl = career.bowling[career.bowling.match_id == mid]
fow = career.fow[career.fow.match_id == mid]

# ---------------------------------------------------------------- wicket timeline
with st.container(border=True):
    st.markdown("**Wicket timeline** · the score each time a wicket fell")
    data = []
    for r in inns.itertuples():
        f = fow[fow.innings_no == r.innings_no].sort_values("wicket")
        tot = f"{r.runs}" if r.all_out else f"{r.runs}/{r.wickets}"
        data.append(dict(label=f"{r.team} {tot}" + (" (2nd inns)" if r.team_innings == 2 else ""),
                         fow=list(zip(f.wicket, f.score)), total=int(r.runs), all_out=bool(r.all_out)))
    sec_ids = m[m.section == row.section].match_id
    par = E.par_by_wicket(career, sec_ids)
    n_inns = int(career.innings.match_id.isin(sec_ids).sum())
    par = par[par.innings >= 0.3 * n_inns]  # later wickets fall in too few innings for a fair par
    st.plotly_chart(wicket_timeline(data, list(zip(par.wicket, par.par)) if len(sec_ids) >= 5 else None),
                    width="stretch", config=CONFIG, key="mt_timeline")
    notes = [("", "<b>Each step to the right</b> is one more wicket down. <b>The height of a step</b> is the partnership: runs added before the next wicket."),
             ("", "<b>Several short steps in a row</b> = a collapse. <b>One tall step</b> = a big stand that rebuilt the innings.")]
    if len(sec_ids) >= 5:
        notes.append(("line", f"<b>Grey dashed line: par</b>, the typical score when each wicket falls in {row.section}. "
                              "Above it = ahead of the game; below it = behind. It stops where too few innings get that far."))
    notes.append(("", "The scorecard gives the score at each wicket but not the over, so this shows wickets, not overs."))
    explain_list(notes)
    st_ = P.stands(career, [mid])
    if len(st_):
        big = st_.sort_values("runs", ascending=False).iloc[0]
        n_ = int(big.wicket)
        who = f" by {big.batter1} and {big.batter2}" if big.known else ""
        tot_ = career.innings[(career.innings.match_id == mid) & (career.innings.team == big.team)].runs.sum()
        chart_note(f"The biggest stand was {big.runs}{'*' if big.unbroken else ''} for the {n_}{P.suffix(n_)} wicket"
                   f"{who} for {big.team}, {big.runs / max(tot_, 1) * 100:.0f}% of their runs in the match.",
                   "Shows how each innings was built and where it fell apart, wicket by wicket.")

# ---------------------------------------------------------------- top performers
top_bat = bat[bat.did_bat].sort_values(["runs", "balls"], ascending=[False, True]).head(3)
top_bowl = bowl.assign(k=bowl.wickets * 1000 - bowl.runs).sort_values("k", ascending=False).head(3)
c1, c2 = st.columns(2, gap="medium")
with c1:
    with st.container(border=True):
        st.markdown("**Top scores**")
        st.dataframe(pd.DataFrame({"Batter": top_bat.player, "Team": top_bat.team,
                                   "Score": [f"{r}{'' if o else '*'}" for r, o in zip(top_bat.runs, top_bat.out)],
                                   "Balls": top_bat.balls}), hide_index=True, width="stretch")
with c2:
    with st.container(border=True):
        st.markdown("**Best bowling**")
        st.dataframe(pd.DataFrame({"Bowler": top_bowl.player, "Team": top_bowl.team,
                                   "Figures": [f"{w}/{r}" for w, r in zip(top_bowl.wickets, top_bowl.runs)],
                                   "Overs": [str(b) + " balls" if c else balls_to_overs(b) for b, c in zip(top_bowl.balls, top_bowl.counted_in_balls)]}),
                     hide_index=True, width="stretch")

# ---------------------------------------------------------------- full scorecard
st.subheader("Scorecard", anchor=False)
for r in inns.itertuples():
    tot = f"{r.runs} all out" if r.all_out else f"{r.runs}/{r.wickets}{' declared' if r.declared else ''}"
    length = f"{r.balls} balls" if r.counted_in_balls else f"{balls_to_overs(r.balls)} overs"
    fo = " · followed on" if r.team_innings == 2 and r.innings_no == 3 and inns.iloc[0].team != r.team else ""
    with st.expander(f"{r.team} · {'1st' if r.team_innings == 1 else '2nd'} innings · {tot} ({length}){fo}", expanded=True):
        b = bat[bat.innings_no == r.innings_no].sort_values("position")
        st.dataframe(pd.DataFrame({
            "Batter": b.player,
            "How out": [d if d else ("did not bat" if not db else "") for d, db in zip(b.dismissal, b.did_bat)],
            "R": [str(x) if db else "" for x, db in zip(b.runs, b.did_bat)],
            "B": [str(x) if db else "" for x, db in zip(b.balls, b.did_bat)],
            "4s": [str(x) if db else "" for x, db in zip(b.fours, b.did_bat)],
            "6s": [str(x) if db else "" for x, db in zip(b.sixes, b.did_bat)],
            "SR": [fmt(x / y * 100, 1) if db and y else "" for x, y, db in zip(b.runs, b.balls, b.did_bat)],
        }), hide_index=True, width="stretch", height=35 * (len(b) + 1) + 3)  # all eleven, no scrolling
        parts = [f"{k} {v}" for k, v in (("b", r.byes), ("lb", r.leg_byes), ("w", r.wides), ("nb", r.no_balls)) if v]
        st.caption(f"Extras {r.extras}" + (f" ({', '.join(parts)})" if parts else "") + f" · Total {tot} ({length})")
        w = bowl[bowl.innings_no == r.innings_no]
        dots = w.dots.notna().any()
        st.dataframe(pd.DataFrame({
            "Bowler": w.player,
            ("Balls" if r.counted_in_balls else "O"): [str(x) if r.counted_in_balls else balls_to_overs(x) for x in w.balls],
            ("Dots" if dots else "M"): [int(x) if pd.notna(x) else 0 for x in (w.dots if dots else w.maidens)],
            "R": w.runs, "W": w.wickets, "Econ": [fmt(x / y * 6, 2) if y else "–" for x, y in zip(w.runs, w.balls)],
        }), hide_index=True, width="stretch", height=35 * (len(w) + 1) + 3)
        f = fow[fow.innings_no == r.innings_no].sort_values("wicket")
        if len(f):
            prev, stands = 0, []
            for wk, sc in zip(f.wicket, f.score):
                stands.append(f"{wk}-{sc} (+{sc - prev})")
                prev = sc
            st.caption("Fall of wickets (partnership in brackets): " + ", ".join(stands))
