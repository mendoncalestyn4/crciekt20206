import copy
import html

import pandas as pd
import streamlit as st

from ccstats import checks
from ccstats import local as L
from ccstats import names as NM
from ccstats.loader import Fixes
from ui import state
from ui.theme import page_header

career = state.current()
if career is None:
    st.info("Load a career on the Home page first.")
    st.stop()

page_header("Data check", "Check and fix",
            "The scorecards leave a few things unclear. Each one is explained below, with a one-click fix where there's a "
            "safe answer. Nothing changes until you click, and every change can be undone under Your changes.")


def apply(fixes: Fixes, message: str) -> None:
    with st.spinner("Updating every stat with your change…"):
        state.show(career.with_fixes(fixes))
    st.session_state["dc_done"] = message
    st.rerun()


def fixes_copy() -> Fixes:
    return copy.deepcopy(career.fixes)


def note(text: str) -> str:
    return f"<span style='opacity:.72;font-size:13.5px'>{text}</span>"


done = st.session_state.pop("dc_done", None)
if done:
    st.success(done)

unc = checks.uncredited(career)
sug = unc[unc.suggestion != ""]
shared = checks.shared_names(career)
merges = checks.merge_suggestions(career)
conflicts = checks.replay_conflicts(career)
left = career.leftovers
bad_cards = career.problems.match_id.nunique()
failed_files = [r for r in career.report if r.status == "failed"]
fx = career.fixes
n_changes = (len(fx.merges) + len(fx.splits) + len(fx.credits) + len(fx.include) + len(fx.exclude))

# ---------------------------------------------------------------- what needs you
todo, fine = [], []
if len(unc):
    todo.append(f"👉 **{len(unc)} catches or stumpings** don't say which fielder took them"
                + (f" ({len(sug)} can be sorted in one click)" if len(sug) else "") + " → *Unclear catches*")
if len(shared):
    todo.append(f"👉 **{len(shared)} names** are used by two different players, so their stats are mixed together "
                "(one click to keep them apart) → *Name shared by 2 players*")
if len(merges):
    todo.append(f"👉 **{len(merges)} players** may appear under two names → *Player with 2 names*")
if len(conflicts):
    todo.append(f"👉 **{conflicts.match_id.nunique()} knockout games** look like leftovers from a replayed season → *Games left out*")
if bad_cards or failed_files:
    todo.append(f"👉 **{bad_cards + len(failed_files)} scorecards** have a problem → *Scorecards*")
if not bad_cards and not failed_files:
    fine.append(f"✅ All {len(career.matches):,} scorecards add up")
if not len(shared):
    fine.append("✅ No name is used by two players")
if not len(merges):
    fine.append("✅ No player appears under two names")
if len(left):
    fine.append(f"ℹ️ {len(left)} game{'s' if len(left) > 1 else ''} left out on purpose (from an earlier playthrough"
                f"{' or by you' if (~left.auto).any() else ''}) → *Games left out*")
# competitions the site doesn't know by name (a rename it hasn't been told about): each is a section of its own
unknown = career.matches[~career.matches.recognised.astype(bool)] if "recognised" in career.matches else career.matches[:0]
if len(unknown):
    names_ = sorted(unknown.competition.unique())
    fine.append(f"ℹ️ {len(unknown)} game{'s' if len(unknown) > 1 else ''} in competitions the site doesn't know by name "
                f"({', '.join(names_[:4])}{' …' if len(names_) > 4 else ''}): each is a section of its own, with its format "
                "read from the scorecards. Renamed one in the game? Keep your name files beside the Scorecards folder "
                "(see the guide)")
try:
    _folder = (state.settings_of(career.name) or L.CareerSettings(name="")).folder
    _files = NM.find_edit_files(_folder, also=tuple(L.game_install_folders()))
except (OSError, ValueError, TypeError):  # settings that can't be read: say nothing about name files
    _files = {}
if _files:
    fine.append("ℹ️ Names from your name files in " + ", ".join(sorted({f"`{p.parent}`" for p in _files.values()})))
with st.container(border=True):
    st.markdown("**What needs you**" if todo else "**Nothing needs you** 🎉")
    if todo:
        st.markdown("\n".join(f"- {t}" for t in todo))
    st.markdown(" · ".join(fine))

tabs = st.tabs([f"Unclear catches · {len(unc)}", f"Name shared by 2 players · {len(shared)}",
                f"Player with 2 names · {len(merges)}", f"Games left out · {len(left)}",
                f"Scorecards · {bad_cards + len(failed_files)}", f"Your changes · {n_changes}"])
t_catch, t_shared, t_merge, t_left, t_cards, t_changes = tabs

# ---------------------------------------------------------------- unclear catches
with t_catch:
    st.markdown("**Who took the catch?** The scorecard prints only the fielder's surname, like *c Mendis*. When a side "
                "has two players with that surname (Sri Lanka's Kusal and Kamindu Mendis are both *K Mendis*), it can't "
                "say which one took it. Until you choose, the catch counts for the team but for neither player.")
    st.markdown(note("Already sorted out for you: a catcher can't be the bowler (that's printed <i>c & b</i>), a stumping "
                     "is always the wicketkeeper, and a catch by a substitute fielder (<i>c Sub</i>) counts for the team "
                     "but for no player, as in real cricket."), unsafe_allow_html=True)
    if unc.empty:
        st.success("Every catch and stumping is credited to a player.")
    else:
        if len(sug):
            with st.container(border=True):
                st.markdown(f"**{len(sug)} of these have a clear answer**, usually the side's wicketkeeper or the player who "
                            "takes most of that side's catches. The reason is shown under each one below.")
                if st.button(f"Accept all {len(sug)} suggestions", type="primary", key="dc_accept_all"):
                    f = fixes_copy()
                    f.credits.update(dict(zip(sug.credit_key, sug.suggestion)))
                    f.suggested = sorted(set(f.suggested) | set(sug.credit_key))
                    apply(f, f"Done: {len(sug)} catches and stumpings credited as suggested. "
                             "You can undo them under Your changes.")
        st.markdown(f"**Or choose yourself.** {'The suggestion is already picked where there is one. ' if len(sug) else ''}"
                    "Leave any you're not sure about.")
        show = unc.head(40)
        with st.form("dc_credits"):
            picks = {}
            h1, h2 = st.columns([3, 2])
            h1.markdown("**The dismissal**")
            h2.markdown("**Who took it?**")
            for r in show.itertuples():
                c1, c2 = st.columns([3, 2], vertical_alignment="center")
                verb = "c" if r.kind == "caught" else "st"
                lines = [f"**{r.match}**",
                         f"{html.escape(r.batter)} **{verb} {html.escape(r.printed)}** b {html.escape(r.bowler)}",
                         note(f"{html.escape(r.team)} had " + " and ".join(map(html.escape, r.likely)) if len(r.likely) > 1
                              else f"{html.escape(r.team)} fielding")]
                if r.suggestion:
                    lines.append(note(f"💡 Suggested: <b>{html.escape(r.suggestion)}</b>, because {html.escape(r.reason)}"))
                c1.markdown("  \n".join(lines), unsafe_allow_html=True)
                options = ["Not sure: leave it"] + r.candidates
                picks[r.credit_key] = c2.selectbox("Who took it?", options, key=f"dc_c_{r.credit_key}",
                                                   index=options.index(r.suggestion) if r.suggestion in options else 0,
                                                   label_visibility="collapsed")
            if st.form_submit_button("Save my choices", type="primary"):
                chosen = {k: v for k, v in picks.items() if v != "Not sure: leave it"}
                if chosen:
                    f = fixes_copy()
                    f.credits.update(chosen)
                    f.suggested = [k for k in f.suggested if k not in chosen]  # picked by hand now
                    apply(f, f"Saved: {len(chosen)} catch{'es' if len(chosen) > 1 else ''} credited.")
        if len(unc) > len(show):
            st.caption(f"Showing the first {len(show)} of {len(unc)}. Save these and the next ones appear.")

# ---------------------------------------------------------------- one name, two players
with t_shared:
    st.markdown("**Two different players with the same name.** The game prints only an initial and surname, so two "
                "players can end up with the same name, like *R Patel* at Leicestershire and *R Patel* at Surrey. The "
                "site then adds their runs and wickets together as if they were one person. A player can't play for two "
                "teams in the same season of a competition, so each name below is almost certainly two people.")
    if shared.empty:
        st.success("No name is used by two players.")
    else:
        big = shared.loc[shared.games.map(lambda g: sum(g.values())).idxmax()]  # the best-known case as the example
        with st.container(border=True):
            st.markdown(f"**Keep all {len(shared)} apart.** Each name stays with the team it played most games for, and "
                        "the player at the other team gets the team added to their name, e.g. "
                        f"*{big.player} ({big.separate[0]})*.")
            if st.button(f"Keep all {len(shared)} apart", type="primary", key="dc_split_all"):
                f = fixes_copy()
                have = {(x["player"], x["team"]) for x in f.splits}
                f.splits += [{"player": r.player, "team": t, "new_name": f"{r.player} ({t})"}
                             for r in shared.itertuples() for t in r.separate if (r.player, t) not in have]
                apply(f, f"Done: {len(shared)} names now belong to one player each. You can undo any of them under "
                         "Your changes.")
        for i, r in enumerate(shared.itertuples()):
            c1, c2 = st.columns([5, 1], vertical_alignment="center")
            played = " and ".join(f"{html.escape(t)} ({r.games[t]} game{'s' if r.games[t] != 1 else ''})" for t in r.teams)
            after = ", ".join(f"<b>{html.escape(r.player)} ({html.escape(t)})</b>" for t in r.separate)
            c1.markdown(f"**{html.escape(r.player)}** played for {played}, in {html.escape(', '.join(r.where))}  \n"
                        + note(f"After: <b>{html.escape(r.player)}</b> at {html.escape(r.keep)}, and {after}"),
                        unsafe_allow_html=True)
            if c2.button("Keep apart", key=f"dc_s_{i}"):
                f = fixes_copy()
                f.splits += [{"player": r.player, "team": t, "new_name": f"{r.player} ({t})"} for t in r.separate]
                apply(f, f"Done: {r.player} at {r.keep} and {', '.join(f'{r.player} ({t})' for t in r.separate)} "
                         "are now separate players.")
    with st.expander("Separate any other name yourself"):
        st.caption("For a name the site didn't spot: pick the player, the team where it's really someone else, and the "
                   "name to show for them.")
        players = sorted(set(career.batting.player) | set(career.bowling.player))
        p = st.selectbox("Player", players, index=None, key="dc_sp", placeholder="Pick a player")
        if p:
            teams = sorted(set(career.batting[career.batting.player == p].team))
            c1, c2 = st.columns(2)
            t = c1.selectbox("The one playing for", teams, key="dc_spt")
            new = c2.text_input("Show them as", value=f"{p} ({t})", key=f"dc_spn_{t}")
            if st.button("Make them a separate player", disabled=not new.strip() or new.strip() == p, key="dc_sp_go"):
                f = fixes_copy()
                f.splits.append({"player": p, "team": t, "new_name": new.strip()})
                apply(f, f"Done: {p} at {t} is now {new.strip()}.")

# ---------------------------------------------------------------- one player, two names
with t_merge:
    st.markdown("**One player under two names.** Sometimes the same player shows up under two slightly different names. "
                "The names below look like one player: same initial and surname, same team, and never in the same match "
                "together.")
    if merges.empty:
        st.success("No player appears under two names.")
    for i, r in enumerate(merges.itertuples()):
        c1, c2 = st.columns([5, 1], vertical_alignment="center")
        c1.markdown(f"**{html.escape(r.other)}** ({r.other_matches} games) and **{html.escape(r.keep)}** ({r.keep_matches} "
                    f"games) · {html.escape(r.teams)}  \n"
                    + note(f"After: all {r.other_matches + r.keep_matches} games count for <b>{html.escape(r.keep)}</b>"),
                    unsafe_allow_html=True)
        if c2.button("Same player", key=f"dc_m_{i}"):
            f = fixes_copy()
            f.merges[r.other] = r.keep
            apply(f, f"Done: {r.other}'s games now count for {r.keep}.")
    with st.expander("Join any two names yourself"):
        players = sorted(set(career.batting.player) | set(career.bowling.player))
        c1, c2 = st.columns(2)
        a = c1.selectbox("This name…", players, index=None, key="dc_ma", placeholder="Pick a player")
        b = c2.selectbox("…is the same player as", [p for p in players if p != a], index=None, key="dc_mb",
                         placeholder="Pick a player")
        together = bool(a and b and set(career.batting[career.batting.player == a].match_id)
                        & set(career.batting[career.batting.player == b].match_id))
        if together:
            st.warning(f"{a} and {b} played in the same match, so they can't be one player.")
        if st.button("Count them as one player", disabled=not (a and b) or together, key="dc_m_go"):
            f = fixes_copy()
            f.merges[a] = b
            apply(f, f"Done: {a}'s games now count for {b}.")

# ---------------------------------------------------------------- games left out
with t_left:
    st.markdown("**Games from an earlier playthrough.** When you reload a save and play part of a season again, the game "
                "saves each replayed match over its old file. But a knockout with different teams gets a new file, so "
                "the old game stays in your Scorecards folder. That's how one IPL season can end up with three finals. "
                "The site spots these from when each file was saved and leaves them out of every stat. Nothing to do, "
                "unless one of them should count.")
    if left.empty:
        st.success("Every match counts: none are from an earlier playthrough.")
    for i, r in enumerate(left.itertuples()):
        c1, c2 = st.columns([5, 1], vertical_alignment="center")
        c1.markdown(f"**{r.date:%d %b %Y} · {html.escape(r.competition)}{' · ' + r.stage if r.stage else ''} · "
                    f"{html.escape(r.home)} v {html.escape(r.away)}** · {html.escape(r.result)}  \n"
                    + note(html.escape(r.reason)), unsafe_allow_html=True)
        if c2.button("Count it", key=f"dc_inc_{i}"):
            f = fixes_copy()
            if r.auto:
                f.include = sorted(set(f.include) | {r.match_id})
            f.exclude = [x for x in f.exclude if x != r.match_id]
            apply(f, f"Done: {r.home} v {r.away} ({r.date:%d %b %Y}) counts again.")
    if len(conflicts):
        st.warning("These knockout games can't all be from one playthrough (two finals, or a team in two knockouts on the "
                   "same day), and their files came without the save times that tell which is older. Leave out the ones "
                   "from the earlier playthrough.")
        for i, r in enumerate(conflicts.itertuples()):
            c1, c2 = st.columns([5, 1], vertical_alignment="center")
            c1.markdown(f"**{r.group}** · {r.date:%d %b %Y} · {r.stage} · {r.home} v {r.away} · {r.result}")
            if c2.button("Leave out", key=f"dc_exc_{i}"):
                f = fixes_copy()
                f.exclude = sorted(set(f.exclude) | {r.match_id})
                apply(f, f"Done: {r.home} v {r.away} ({r.date:%d %b %Y}) is left out.")
    with st.expander("Leave out any other match"):
        mm = career.matches.sort_values("date", ascending=False)
        labels = {r.match_id: f"{r.date:%d %b %Y} · {r.home} v {r.away} · {r.event} · {r.result}" for r in mm.itertuples()}
        pick = st.selectbox("Match", list(labels), format_func=labels.get, index=None, key="dc_exc_pick",
                            placeholder="Type to search")
        if st.button("Leave it out", disabled=pick is None, key="dc_exc_go"):
            f = fixes_copy()
            f.exclude = sorted(set(f.exclude) | {pick})
            f.include = [x for x in f.include if x != pick]
            apply(f, "Done: that match is left out of every stat. It's listed above if you want it back.")

# ---------------------------------------------------------------- scorecards
with t_cards:
    st.markdown("**Every scorecard is checked when it's read:** the batters' runs plus extras make the total, the bowlers' "
                "runs, overs and wickets match the innings, and the dismissals match the fall of wickets.")
    if failed_files:
        st.error(f"{len(failed_files)} file(s) couldn't be read, so they aren't in any stat.")
        st.dataframe(pd.DataFrame([(r.source, r.message) for r in failed_files], columns=["File", "Why"]),
                     hide_index=True, width="stretch")
    if career.problems.empty:
        st.success(f"All {len(career.matches):,} scorecards add up.")
    else:
        st.warning("These scorecards have numbers that don't add up. They're still counted.")
        st.dataframe(career.problems.rename(columns={"source": "File", "problem": "What doesn't add up"})
                     [["File", "What doesn't add up"]], hide_index=True, width="stretch")

# ---------------------------------------------------------------- your changes
with t_changes:
    if not n_changes:
        st.caption("You haven't changed anything yet.")
    bat = career.batting.set_index(["match_id", "innings_no", "position"])
    games = career.matches.set_index("match_id")

    def game(mid: str) -> str:
        return f"{games.date[mid]:%d %b %Y} {games.home[mid]} v {games.away[mid]}" if mid in games.index else "a match"

    def row(text: str, key: str, label: str = "Undo") -> bool:
        c1, c2 = st.columns([5, 1], vertical_alignment="center")
        c1.markdown(text, unsafe_allow_html=True)
        return c2.button(label, key=key)

    if fx.suggested and row(f"**{len(fx.suggested)} catches and stumpings** credited from the suggestions (💡 below)",
                            "dc_undo_sug", "Undo all"):
        f = fixes_copy()
        for k in f.suggested:
            f.credits.pop(k, None)
        f.suggested = []
        apply(f, "Undone: the suggested catches are uncredited again.")
    for i, s in enumerate(list(fx.splits)):
        if row(f"**{html.escape(s['player'])}** at {html.escape(s['team'])} is a separate player: "
               f"**{html.escape(s['new_name'])}**", f"dc_us_{i}"):
            f = fixes_copy()
            f.splits = [x for x in f.splits if x != s]
            apply(f, f"Undone: {s['new_name']} is {s['player']} again.")
    for i, (a, b) in enumerate(list(fx.merges.items())):
        if row(f"**{html.escape(a)}** counts as **{html.escape(b)}**", f"dc_um_{i}"):
            f = fixes_copy()
            f.merges.pop(a)
            apply(f, f"Undone: {a} is a separate player again.")
    for i, mid in enumerate(list(fx.exclude)):
        if row(f"You left out **{html.escape(game(mid))}**", f"dc_ue_{i}"):
            f = fixes_copy()
            f.exclude = [x for x in f.exclude if x != mid]
            apply(f, "Undone: that match counts again.")
    for i, mid in enumerate(list(fx.include)):
        if row(f"You count **{html.escape(game(mid))}** again (it looked like it was from an earlier playthrough)",
               f"dc_ui_{i}"):
            f = fixes_copy()
            f.include = [x for x in f.include if x != mid]
            apply(f, "Undone: that game is left out again.")
    for i, (k, v) in enumerate(list(fx.credits.items())):
        mid, inn, pos = k.split("|")
        try:
            b = bat.loc[(mid, int(inn), int(pos))]
            what, by = f"{html.escape(b.player)} {html.escape(b.dismissal)}", ("stumped" if b.how_out == "stumped" else "caught")
        except (KeyError, ValueError):
            what, by = "a dismissal", "taken"
        if row(f"{'💡 ' if k in fx.suggested else ''}{html.escape(game(mid))}: {what} → {by} by **{html.escape(v)}**",
               f"dc_uc_{i}"):
            f = fixes_copy()
            f.credits.pop(k)
            f.suggested = [x for x in f.suggested if x != k]
            apply(f, "Undone: that catch is uncredited again.")
