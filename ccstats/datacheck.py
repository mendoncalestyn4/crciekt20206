"""Data check (stage 4): what the scorecards leave unclear, the changes you can make, and what each change does to the
numbers before you make it (the fix preview, your pick of 26 November).

Six parts (your answer 15): names shared by different players (split by themselves, each split can be undone), one
player under two names (joined only by your own click, never automatically; a pair that played in the same match can
never be joined), games left out, scorecards (what doesn't add up, what was put right, files that couldn't be read),
copies (a match saved twice, counted once) and your changes. No fielding: the old Team catches part is gone."""

from __future__ import annotations

import copy

import pandas as pd

from . import checks
from .loader import Fixes


# --------------------------------------------------------------------------- the lists
def _appear(career) -> pd.DataFrame:
    return pd.concat([career.batting[["match_id", "team", "player"]],
                      career.bowling[["match_id", "team", "player"]]]).drop_duplicates()


def players(career) -> list[str]:
    return sorted(set(career.batting.player) | set(career.bowling.player))


def teams_of(career, player: str) -> list[str]:
    a = _appear(career)
    return sorted(set(a[a.player == player].team))


def played_together(career, a: str, b: str) -> bool:
    ap = _appear(career)
    return bool(set(ap[ap.player == a].match_id) & set(ap[ap.player == b].match_id))


def copies(career) -> list[dict]:
    """Scorecards saved twice under different file names: counted once (the copy is left out)."""
    return [dict(file=r.source, same_as=r.message.removeprefix("same match as ").strip(), match_id=r.match_id)
            for r in getattr(career, "report", []) if r.status == "duplicate"]


def summary(career) -> dict:
    """What needs you, what's fine, and how many in each part."""
    shared = checks.shared_names(career)
    merges = checks.merge_suggestions(career)
    conflicts = checks.replay_conflicts(career)
    left = career.leftovers
    auto = career.auto_splits
    failed = [r for r in getattr(career, "report", []) if r.status == "failed"]
    fx = career.fixes
    dups = copies(career)
    todo, fine = [], []
    if len(merges):
        todo.append(f"**{len(merges)} players** may appear under two names → the Player with two names tab")
    joined = getattr(career, "auto_joins", None)
    if joined is not None and len(joined):
        fine.append(f"🔗 {len(joined)} pair{'s' if len(joined) > 1 else ''} of names joined by themselves, sure to be one "
                    "player each (can be undone) → the Player with two names tab")
    if len(shared):
        todo.append(f"**{len(shared)} names** are still used by two different players → the Shared names tab")
    if len(conflicts):
        todo.append(f"**{conflicts.match_id.nunique()} knockout games** look like leftovers from a replayed season → the Games left out tab")
    # scorecards (your answers of 26 November): one the site put right isn't listed at all, nor one it closed by its
    # best fair guess (that's a quiet note on the match's own page); only a file that isn't a scorecard is named
    if failed:
        todo.append(f"**{len(failed)} file{'s' if len(failed) != 1 else ''}** in the folder "
                    f"{'aren' if len(failed) != 1 else 'isn'}'t a scorecard the site can read → the Scorecards tab")
    else:
        fine.append(f"✅ All {len(career.matches):,} scorecards add up")
    if len(auto):
        fine.append(f"✅ {auto.player.nunique()} names shared by different players kept apart by themselves → the Shared names tab")
    if not len(merges) and (joined is None or not len(joined)):   # (a joined pair has its own line above)
        fine.append("✅ No player appears under two names")
    if len(left):
        why = [w for w, k in (("from an earlier playthrough", left.reason.str.startswith("From an earlier").any()),
                              ("printed impossibly by the game", left.reason.str.startswith("Left out by itself").any()),
                              ("by you", (~left.auto.astype(bool)).any())) if k]
        fine.append(f"ℹ️ {len(left)} game{'s' if len(left) > 1 else ''} left out on purpose ({', '.join(why[:-1])}"
                    f"{' or ' if len(why) > 1 else ''}{why[-1]}) → the Games left out tab")
    if dups:
        fine.append(f"ℹ️ {len(dups)} scorecard{'s' if len(dups) > 1 else ''} saved twice, counted once → the Copies tab")
    unknown = career.matches[~career.matches.recognised.astype(bool)] if "recognised" in career.matches else career.matches[:0]
    if len(unknown):
        names_ = sorted(unknown.competition.unique())
        fine.append(f"ℹ️ {len(unknown)} game{'s' if len(unknown) > 1 else ''} in competitions the site doesn't know by name "
                    f"({', '.join(names_[:4])}{' …' if len(names_) > 4 else ''}): each is a section of its own, with its "
                    "format read from the scorecards")
    n_changes = (len(fx.merges) + len(fx.splits) + len(fx.include) + len(fx.exclude) + len(fx.keep_together)
                 + len(fx.keep_apart) + (len(joined) if joined is not None else 0))
    counts = {"Shared names": int(auto.player.nunique()) + len(shared),
              "Player with two names": len(merges) + (len(joined) if joined is not None else 0),
              "Games left out": len(left) + int(conflicts.match_id.nunique()),
              "Scorecards": len(failed), "Copies": len(dups), "Your changes": n_changes}
    labels = {} if failed else {"Scorecards": "Scorecards ✓"}     # nothing to see: the tab says so, with no count
    return dict(todo=todo, fine=fine, counts=counts, labels=labels, needs_you=len(todo))


# --------------------------------------------------------------------------- the changes (a new Fixes each time)
class Refused(ValueError):
    """A change that can't be made, said in plain words."""


def change(career, action: str, b: dict) -> tuple[Fixes, str]:
    """The Data check choices after one change, and what to say about it. Two names are joined only by your click
    here, or by themselves when sure to be one player (your answer of 26 November), which `keep_apart` undoes."""
    f = copy.deepcopy(career.fixes)
    if action == "undo_auto_split":          # keep a name as one player after all
        p = str(b.get("player", ""))
        if p not in set(career.auto_splits.player):
            raise Refused("That name isn't split any more.")
        f.keep_together = sorted(set(f.keep_together) | {p})
        return f, f"Done: {p} counts as one player again, at every team."
    if action == "resplit":                  # split by itself again (undo of the above)
        p = str(b.get("player", ""))
        f.keep_together = [x for x in f.keep_together if x != p]
        return f, f"Done: {p} is kept apart again, one player at each team."
    if action == "split_shared":             # a name still shared (the automatic split was undone, or older careers)
        sh = checks.shared_names(career)
        rows = sh if b.get("all") else sh[sh.player == str(b.get("player", ""))]
        if rows.empty:
            raise Refused("That name is already kept apart.")
        have = {(x["player"], x["team"]) for x in f.splits}
        f.splits += [{"player": r.player, "team": t, "new_name": f"{r.player} ({t})"}
                     for r in rows.itertuples() for t in r.separate if (r.player, t) not in have]
        return f, (f"Done: {len(rows)} names now belong to one player each." if b.get("all") else
                   f"Done: {rows.player.iloc[0]} at {rows.keep.iloc[0]} and the others are now separate players.")
    if action == "split":                    # separate any other name yourself
        p, t, new = str(b.get("player", "")), str(b.get("team", "")), str(b.get("new_name", "")).strip()
        if p not in players(career) or t not in teams_of(career, p):
            raise Refused("Pick the player and the team where it's really someone else.")
        if not new or new == p:
            raise Refused("Give them a different name to show.")
        f.splits.append({"player": p, "team": t, "new_name": new})
        return f, f"Done: {p} at {t} is now {new}."
    if action == "join":                     # one player under two names: only by your click
        a, keep = str(b.get("name", "")), str(b.get("keep", ""))
        ps = set(players(career))
        if a not in ps or keep not in ps or a == keep:
            raise Refused("Pick two different names.")
        if played_together(career, a, keep):
            raise Refused(f"{a} and {keep} played in the same match, so they can't be one player.")
        f.merges[a] = keep
        return f, f"Done: {a}'s games now count for {keep}."
    if action == "keep_apart":               # a pair joined by themselves: two players after all
        a, keep = str(b.get("other", "")), str(b.get("keep", ""))
        j = career.auto_joins
        if j[(j.other == a) & (j.keep == keep)].empty:
            raise Refused("Those two names aren't joined any more.")
        f.keep_apart = f.keep_apart + [[a, keep]]
        return f, f"Done: {a} and {keep} are kept apart, two players."
    if action == "count_it":
        mid = str(b.get("match_id", ""))
        left = career.leftovers[career.leftovers.match_id == mid]
        if left.empty:
            raise Refused("That game already counts.")
        if bool(left.auto.iloc[0]):
            f.include = sorted(set(f.include) | {mid})
        f.exclude = [x for x in f.exclude if x != mid]
        r = left.iloc[0]
        return f, f"Done: {r.home} v {r.away} ({pd.Timestamp(r.date):%d %b %Y}) counts again."
    if action == "leave_out":
        mid = str(b.get("match_id", ""))
        hit = career.matches[career.matches.match_id == mid]
        if hit.empty:
            raise Refused("That match isn't in this career.")
        f.exclude = sorted(set(f.exclude) | {mid})
        f.include = [x for x in f.include if x != mid]
        r = hit.iloc[0]
        return f, f"Done: {r.home} v {r.away} ({r.date:%d %b %Y}) is left out of every figure."
    if action == "undo":                     # one of your changes
        kind, key = str(b.get("kind", "")), b.get("key")
        if kind == "split":
            f.splits = [x for x in f.splits if not (x["player"] == key.get("player") and x["team"] == key.get("team"))]
            return f, f"Undone: {key.get('new_name', '')} is {key.get('player', '')} again."
        if kind == "merge":
            f.merges.pop(str(key), None)
            return f, f"Undone: {key} is a separate player again."
        if kind == "exclude":
            f.exclude = [x for x in f.exclude if x != key]
            return f, "Undone: that match counts again."
        if kind == "include":
            f.include = [x for x in f.include if x != key]
            return f, "Undone: that game is left out again."
        if kind == "keep_together":
            f.keep_together = [x for x in f.keep_together if x != key]
            return f, f"Undone: {key} is kept apart again."
        if kind == "auto_join":            # a join made by itself: kept apart for good
            return change(career, "keep_apart", dict(other=key[0], keep=key[1]))
        if kind == "keep_apart":
            f.keep_apart = [x for x in f.keep_apart if list(x) != list(key)]
            return f, f"Undone: {key[0]} and {key[1]} are joined again (sure to be one player)."
        raise Refused("That change can't be undone.")
    raise Refused(f"Unknown change {action!r}.")


def your_changes(career) -> list[dict]:
    fx, m = career.fixes, career.matches.set_index("match_id")

    left = career.leftovers.set_index("match_id") if len(career.leftovers) else None

    def game(mid: str) -> str:
        """A match by its date and teams, whether it counts or is left out (a left-out one is no longer among the
        matches, so it's found among the games left out)."""
        if mid in m.index:
            return f"{m.date[mid]:%d %b %Y} {m.home[mid]} v {m.away[mid]}"
        if left is not None and mid in left.index:
            r = left.loc[mid]
            return f"{pd.Timestamp(r.date):%d %b %Y} {r.home} v {r.away}"
        return "a match no longer in your scorecards"
    out = [dict(kind="split", key=s, text=f"**{s['player']}** at {s['team']} is a separate player: **{s['new_name']}**")
           for s in fx.splits]
    out += [dict(kind="merge", key=a, text=f"**{a}** counts as **{b}**") for a, b in fx.merges.items()]
    out += [dict(kind="keep_together", key=p, text=f"**{p}** kept as one player (you undid the automatic split)")
            for p in fx.keep_together]
    j = getattr(career, "auto_joins", None)
    if j is not None:
        out += [dict(kind="auto_join", key=[r.other, r.keep], text=f"**{r.other}** joined to **{r.keep}** by itself at "
                     f"{r.team}: {r.why}, never in the same match, one name straight after the other") for r in j.itertuples()]
    out += [dict(kind="keep_apart", key=list(x), text=f"You kept **{x[0]}** and **{x[1]}** apart (they had been joined by "
                 "themselves)") for x in fx.keep_apart]
    out += [dict(kind="exclude", key=mid, text=f"You left out **{game(mid)}**") for mid in fx.exclude]
    out += [dict(kind="include", key=mid, text=f"You count **{game(mid)}** again (it had been left out by itself)")
            for mid in fx.include]
    return out


# --------------------------------------------------------------------------- the fix preview (your pick)
def _totals(career, bat: pd.DataFrame, bowl: pd.DataFrame) -> dict:
    """Matches played, innings batted, runs and wickets from some of a player's batting and bowling rows."""
    return dict(matches=int(pd.concat([bat.match_id, bowl.match_id]).nunique()), runs=int(bat.runs.sum()),
                wickets=int(bowl.wickets.sum()), innings=int(bat.did_bat.astype(bool).sum()))


def preview(career, action: str, b: dict) -> dict:
    """What a split or a join does to the numbers before you make it: each player's matches, runs and wickets before
    and after."""
    bat, bowl = career.batting, career.bowling
    if action in ("split", "split_shared", "undo_auto_split"):
        p = str(b.get("player", ""))
        if action == "undo_auto_split":
            rows = career.auto_splits[career.auto_splits.player == p]
            names = [p] + list(rows.new_name)
            before = [dict(name=n, **_totals(career, bat[bat.player == n], bowl[bowl.player == n])) for n in names]
            after = [dict(name=p, **_totals(career, bat[bat.player.isin(names)], bowl[bowl.player.isin(names)]))]
            return dict(before=before, after=after)
        if action == "split_shared":
            sh = checks.shared_names(career)
            r = sh[sh.player == p]
            teams = list(r.separate.iloc[0]) if len(r) else []
        else:
            teams = [str(b.get("team", ""))]
        new_names = {t: (str(b.get("new_name", "")).strip() or f"{p} ({t})") if action == "split" else f"{p} ({t})" for t in teams}
        mine_b, mine_w = bat[bat.player == p], bowl[bowl.player == p]
        before = [dict(name=p, **_totals(career, mine_b, mine_w))]
        after = [dict(name=p, **_totals(career, mine_b[~mine_b.team.isin(teams)], mine_w[~mine_w.team.isin(teams)]))]
        after += [dict(name=new_names[t], **_totals(career, mine_b[mine_b.team == t], mine_w[mine_w.team == t])) for t in teams]
        return dict(before=before, after=after)
    if action == "join":
        a, keep = str(b.get("name", "")), str(b.get("keep", ""))
        before = [dict(name=n, **_totals(career, bat[bat.player == n], bowl[bowl.player == n])) for n in (a, keep)]
        after = [dict(name=keep, **_totals(career, bat[bat.player.isin([a, keep])], bowl[bowl.player.isin([a, keep])]))]
        return dict(before=before, after=after, together=played_together(career, a, keep))
    if action == "keep_apart":             # a pair joined by itself, taken apart again: the numbers as read under each name
        a, keep = str(b.get("other", "")), str(b.get("keep", ""))
        j = career.auto_joins
        r = j[(j.other == a) & (j.keep == keep)]
        if r.empty:
            return dict(before=[], after=[])
        r = r.iloc[0]
        before = [dict(name=keep, **_totals(career, bat[bat.player == keep], bowl[bowl.player == keep]))]
        after = [dict(name=n, matches=int(r[f"{w}_matches"]), runs=int(r[f"{w}_runs"]), wickets=int(r[f"{w}_wickets"]),
                      innings=int(r[f"{w}_innings"])) for n, w in ((a, "other"), (keep, "keep"))]
        return dict(before=before, after=after)
    return dict(before=[], after=[])
