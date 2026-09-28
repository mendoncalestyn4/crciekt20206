import copy

import pandas as pd
import streamlit as st

from ccstats import checks
from ccstats.loader import Fixes
from ui import state
from ui.theme import page_header

career = state.current()
if career is None:
    st.info("Load a career on the Home page first.")
    st.stop()

page_header("Data check", "Check and fix",
            "Things the scorecards leave unclear. Nothing here changes by itself: you decide, and every fix can be undone.")


def apply(fixes: Fixes, message: str) -> None:
    with st.spinner("Rebuilding the stats with your fix…"):
        state.show(career.with_fixes(fixes))
    st.session_state["dc_done"] = message
    st.rerun()


def fixes_copy() -> Fixes:
    return copy.deepcopy(career.fixes)


done = st.session_state.pop("dc_done", None)
if done:
    st.success(done)

unc = checks.uncredited(career)
merges = checks.merge_suggestions(career)
splits = checks.split_suggestions(career)
n_fixes = len(career.fixes.merges) + len(career.fixes.splits) + len(career.fixes.credits)
tabs = st.tabs([f"Scorecards ({len(career.problems.match_id.unique())} problems)",
                f"Unclear catches ({len(unc)})", f"Same player, two names? ({len(merges)})",
                f"Two players, one name? ({len(splits)})", f"Your fixes ({n_fixes})"])

# ---------------------------------------------------------------- scorecards
with tabs[0]:
    rep = pd.DataFrame([(r.source, r.status, r.message) for r in career.report], columns=["File", "Status", "Note"])
    if len(rep):
        counts = rep.Status.value_counts()
        st.markdown(" · ".join(f"**{v}** {k}" for k, v in counts.items()))
        bad = rep[rep.Status == "failed"]
        if len(bad):
            st.markdown("**Files that couldn't be read**")
            st.dataframe(bad[["File", "Note"]], hide_index=True, width="stretch")
    if career.problems.empty:
        st.success(f"All {len(career.matches)} scorecards pass the self-check: runs, extras, wickets, bowling and fall of "
                   "wickets all add up.")
    else:
        st.warning("These scorecards have numbers that don't add up. Their matches are still counted.")
        st.dataframe(career.problems.rename(columns={"source": "File", "problem": "Problem"})[["File", "Problem"]],
                     hide_index=True, width="stretch")

# ---------------------------------------------------------------- unclear catches
with tabs[1]:
    if unc.empty:
        st.success("Every catch and stumping is credited to a player.")
    else:
        st.caption("The scorecard prints only a surname, e.g. 'c Patel', and more than one player in the side has it. "
                   "Pick who took it; players with that surname are listed first. Leave it as it is if you're not sure: "
                   "it then isn't counted for anyone.")
        show = unc.head(40)
        with st.form("dc_credits"):
            picks = {}
            for r in show.itertuples():
                c1, c2 = st.columns([3, 2])
                verb = "c" if r.kind == "caught" else "st"
                c1.markdown(f"**{r.match}** · {r.team} fielding  \n{r.batter} {verb} {r.printed} b {r.bowler}")
                picks[r.credit_key] = c2.selectbox("Who took it?", ["Leave as it is"] + r.candidates, key=f"dc_c_{r.credit_key}",
                                                   label_visibility="collapsed")
            if st.form_submit_button("Save these", type="primary"):
                chosen = {k: v for k, v in picks.items() if v != "Leave as it is"}
                if chosen:
                    f = fixes_copy()
                    f.credits.update(chosen)
                    apply(f, f"Credited {len(chosen)} catch{'es' if len(chosen) > 1 else ''}/stumping{'s' if len(chosen) > 1 else ''}.")
        if len(unc) > len(show):
            st.caption(f"Showing the first {len(show)} of {len(unc)}. Save these to see the rest.")

# ---------------------------------------------------------------- merges
with tabs[2]:
    st.caption("Two names that could be one player: same surname and first initial, played for the same team, but never "
               "in the same match. Merging puts all their matches under one name.")
    if merges.empty:
        st.success("No likely duplicates found.")
    for i, r in enumerate(merges.itertuples()):
        c1, c2 = st.columns([4, 1], vertical_alignment="center")
        c1.markdown(f"**{r.other}** ({r.other_matches} matches) → **{r.keep}** ({r.keep_matches} matches) · {r.teams}")
        if c2.button("Merge", key=f"dc_m_{i}"):
            f = fixes_copy()
            f.merges[r.other] = r.keep
            apply(f, f"{r.other} is now counted as {r.keep}.")
    with st.expander("Merge any two names yourself"):
        players = sorted(set(career.batting.player) | set(career.bowling.player))
        c1, c2 = st.columns(2)
        a = c1.selectbox("This name…", players, index=None, key="dc_ma", placeholder="Pick a player")
        b = c2.selectbox("…is the same player as", [p for p in players if p != a], index=None, key="dc_mb",
                         placeholder="Pick a player")
        together = bool(a and b and set(career.batting[career.batting.player == a].match_id)
                        & set(career.batting[career.batting.player == b].match_id))
        if together:
            st.error(f"{a} and {b} played in the same match, so they can't be one player.")
        if st.button("Merge", disabled=not (a and b) or together, key="dc_m_go"):
            f = fixes_copy()
            f.merges[a] = b
            apply(f, f"{a} is now counted as {b}.")

# ---------------------------------------------------------------- splits
with tabs[3]:
    st.caption("A name that played for two different teams in one season of one competition. That's usually two "
               "different players with the same name (e.g. two 'A Sharma's). Splitting gives the one at a team its own name.")
    if splits.empty:
        st.success("No name turned out for two teams in the same season.")
    for i, r in enumerate(splits.itertuples()):
        c1, c2, c3 = st.columns([3, 2, 1], vertical_alignment="center")
        c1.markdown(f"**{r.player}** · {r.section} {r.season} · {' and '.join(r.teams)}")
        team = c2.selectbox("Give a separate name to the one at", r.teams, key=f"dc_st_{i}", label_visibility="collapsed")
        if c3.button("Split", key=f"dc_s_{i}"):
            f = fixes_copy()
            new = f"{r.player} ({team})"
            f.splits.append({"player": r.player, "team": team, "new_name": new})
            apply(f, f"{r.player} at {team} is now {new}, a separate player.")
    with st.expander("Split any name yourself"):
        players = sorted(set(career.batting.player) | set(career.bowling.player))
        p = st.selectbox("Player", players, index=None, key="dc_sp", placeholder="Pick a player")
        if p:
            teams = sorted(set(career.batting[career.batting.player == p].team))
            c1, c2 = st.columns(2)
            t = c1.selectbox("While playing for", teams, key="dc_spt")
            new = c2.text_input("New name", value=f"{p} ({t})", key=f"dc_spn_{t}")
            if st.button("Split", disabled=not new.strip() or new.strip() == p, key="dc_sp_go"):
                f = fixes_copy()
                f.splits.append({"player": p, "team": t, "new_name": new.strip()})
                apply(f, f"{p} at {t} is now {new.strip()}.")

# ---------------------------------------------------------------- your fixes
with tabs[4]:
    fx = career.fixes
    if not n_fixes:
        st.caption("No fixes yet.")
    for i, (a, b) in enumerate(list(fx.merges.items())):
        c1, c2 = st.columns([5, 1], vertical_alignment="center")
        c1.markdown(f"Merged **{a}** into **{b}**")
        if c2.button("Undo", key=f"dc_um_{i}"):
            f = fixes_copy()
            f.merges.pop(a)
            apply(f, f"Undone: {a} is separate again.")
    for i, s in enumerate(list(fx.splits)):
        c1, c2 = st.columns([5, 1], vertical_alignment="center")
        c1.markdown(f"Split **{s['player']}** at {s['team']} → **{s['new_name']}**")
        if c2.button("Undo", key=f"dc_us_{i}"):
            f = fixes_copy()
            f.splits = [x for x in f.splits if x != s]
            apply(f, f"Undone: {s['new_name']} is {s['player']} again.")
    for i, (k, v) in enumerate(list(fx.credits.items())):
        mid, inn, pos = k.split("|")
        row = career.matches[career.matches.match_id == mid]
        label = f"{row.date.iloc[0]:%d %b %Y} · {row.home.iloc[0]} v {row.away.iloc[0]}" if len(row) else mid
        c1, c2 = st.columns([5, 1], vertical_alignment="center")
        c1.markdown(f"Credited **{v}** with a dismissal · {label}, innings {inn}, batter at {pos}")
        if c2.button("Undo", key=f"dc_uc_{i}"):
            f = fixes_copy()
            f.credits.pop(k)
            apply(f, "Undone: that dismissal is uncredited again.")
