"""Partnerships, with the two batters in each where the scorecard lets us tell.

A scorecard gives the batting order, each batter's runs and the fall of wickets
("1-49 2-57 ..."), but not who was out at each wicket.  Usually only one order of
dismissals fits the numbers: a batter can't be out at 2-57 having made 60, and
across the innings every batter's runs have to fit into the stands they were part
of.  We try every order of dismissals that fits; when all of them agree on who
batted together in a stand, the stand gets its two names, otherwise it is left
as "3rd wicket" without names.
"""

from __future__ import annotations

import pandas as pd

STAND_COLUMNS = ["match_id", "innings_no", "team", "opposition", "wicket", "runs", "start", "end", "unbroken",
                 "batter1", "batter2", "known"]
MAX_SOLUTIONS = 400  # stop looking after this many orders that fit (the stand then stays unnamed if they disagree)


def _fits(runs: list[int], spans: list[tuple[int, int]], stand_runs: list[int]) -> bool:
    """Can every batter's runs be shared out over the stands they batted in?
    Each stand holds at most its own runs.  Batters are at the crease for a run of
    consecutive stands, so filling each stand from the batter who leaves soonest is
    enough to decide it."""
    left = list(runs)
    for k, cap in enumerate(stand_runs):
        here = sorted((spans[i][1], i) for i in range(len(runs)) if spans[i][0] <= k <= spans[i][1] and left[i] > 0)
        for _, i in here:
            take = min(cap, left[i])
            left[i] -= take
            cap -= take
            if cap == 0:
                break
        for i in range(len(runs)):
            if spans[i][1] == k and left[i] > 0:
                return False
    return all(v == 0 for v in left)


def _solve(order: list[tuple[str, int, bool]], fall: list[int], total: int) -> list[tuple[str, str] | None]:
    """For each stand (one per wicket that fell, plus the unbroken one at the end if
    two batters were still in), the two batters if every fitting order agrees."""
    n = len(order)
    wkts = len(fall)
    bounds = [0] + fall + [total]
    stand_runs = [max(0, bounds[k + 1] - bounds[k]) for k in range(wkts + 1)]
    names = [o[0] for o in order]
    runs = [o[1] for o in order]
    outs = [o[2] for o in order]
    pairs_seen: list[set] = [set() for _ in range(wkts + 1)]
    found = 0

    def go(k: int, crease: list[int], nxt: int, enter: list[int], leave: list[int], pairs: list):
        nonlocal found
        if found >= MAX_SOLUTIONS:
            return
        if k == wkts:  # all wickets placed: whoever is left must be not out
            if any(outs[i] for i in crease):
                return
            if any(outs[i] for i in range(nxt, n)):  # someone out who never came in
                return
            spans = [(enter[i], leave[i] if leave[i] >= 0 else wkts) for i in range(nxt)]
            if not _fits(runs[:nxt], spans, stand_runs):
                return
            found += 1
            for j, p in enumerate(pairs):
                pairs_seen[j].add(p)
            if len(crease) == 2:
                pairs_seen[wkts].add(tuple(sorted(names[i] for i in crease)))
            return
        if len(crease) < 2:
            return
        here = tuple(sorted(names[i] for i in crease))
        for x in crease:
            if not outs[x] or runs[x] > fall[k] - bounds[enter[x]]:
                continue
            rest = [i for i in crease if i != x]
            leave2 = list(leave)
            leave2[x] = k
            enter2 = list(enter)
            nxt2 = nxt
            if nxt < n:
                rest.append(nxt)
                enter2[nxt] = k + 1
                nxt2 = nxt + 1
            go(k + 1, rest, nxt2, enter2, leave2, pairs + [here])

    if n < 2:
        return [None] * (wkts + 1)
    enter = [0] * n
    leave = [-1] * n
    go(0, [0, 1], 2, enter, leave, [])
    return [next(iter(s)) if len(s) == 1 else None for s in pairs_seen]


def stands(career, ids) -> pd.DataFrame:
    """One row per partnership in these matches: wicket (1 = opening stand), runs,
    score at the start and end, unbroken, and the two batters (`known` False when
    the scorecard can't tell who they were)."""
    ids = set(ids)
    cache = getattr(career, "_stands_cache", None)
    if cache is None:
        cache = _all_stands(career)
        try:
            object.__setattr__(career, "_stands_cache", cache)
        except Exception:
            pass
    return cache[cache.match_id.isin(ids)].reset_index(drop=True)


def _all_stands(career) -> pd.DataFrame:
    """Every stand in the career, worked out once (plain lists, one pass over each table)."""
    inn = career.innings
    bat = career.batting.sort_values(["match_id", "innings_no", "position"])
    fow = career.fow.sort_values(["match_id", "innings_no", "wicket"])
    falls: dict = {}
    for mid, no, sc in zip(fow.match_id, fow.innings_no, fow.score):
        falls.setdefault((mid, no), []).append(int(sc))
    did = bat[bat.did_bat]
    retired = set(zip(did.match_id[did.how_out.astype(str).str.contains("retired", case=False)],
                      did.innings_no[did.how_out.astype(str).str.contains("retired", case=False)]))
    orders: dict = {}
    for mid, no, p, x, o in zip(did.match_id, did.innings_no, did.player, did.runs, did.out):
        orders.setdefault((mid, no), []).append((p, int(x), bool(o)))
    batted = set(zip(bat.match_id, bat.innings_no))
    solved: dict = {}  # the same innings shape is only solved once
    rows = []
    for mid, no, team, opp, runs_, all_out in zip(inn.match_id, inn.innings_no, inn.team, inn.opposition, inn.runs,
                                                   inn.all_out):
        key = (mid, no)
        fall = falls.get(key, [])
        total = int(runs_)
        pairs: list = [None] * (len(fall) + 1)
        if key in batted:
            order = orders.get(key, [])
            if key not in retired and sum(o[2] for o in order) == len(fall) and fall == sorted(fall):
                sk = (tuple(order), tuple(fall), total)
                if sk not in solved:
                    try:
                        solved[sk] = _solve(order, fall, total)
                    except RecursionError:
                        solved[sk] = pairs
                pairs = solved[sk]
        bounds = [0] + fall
        for k, score in enumerate(fall):
            p = pairs[k]
            rows.append((mid, no, team, opp, k + 1, score - bounds[k], bounds[k], score,
                         False, p[0] if p else "", p[1] if p else "", p is not None))
        if not all_out and len(fall) < 10:
            p = pairs[len(fall)] if len(pairs) > len(fall) else None
            start = bounds[-1]
            rows.append((mid, no, team, opp, len(fall) + 1, total - start, start, total,
                         True, p[0] if p else "", p[1] if p else "", p is not None))
    return pd.DataFrame(rows, columns=STAND_COLUMNS)


def by_wicket(s: pd.DataFrame) -> pd.DataFrame:
    """Stands (from `stands`) summed up for each wicket, the way cricket counts them: an unbroken stand's runs count
    and it can be the best (best_unbroken: shown with a *), and the average is the runs over the stands that were
    broken, as a batting average is runs over dismissals (none broken yet: no average)."""
    cols = ["wicket", "stands", "broken", "runs", "average", "best", "best_unbroken"]
    if s.empty:
        return pd.DataFrame(columns=cols)
    s = s.sort_values(["runs", "unbroken"], ascending=[False, False])  # an unbroken stand first among equals
    g = s.groupby("wicket")
    d = pd.DataFrame({"stands": g.size(), "broken": g.unbroken.apply(lambda u: int((~u).sum())), "runs": g.runs.sum(),
                      "best": g.runs.first(), "best_unbroken": g.unbroken.first()}).reset_index()
    d["average"] = d.runs / d.broken.where(d.broken > 0)
    return d[cols]


def suffix(n: int) -> str:
    return "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


def pair_name(r) -> str:
    return f"{r.batter1} & {r.batter2}" if r.known else ""
