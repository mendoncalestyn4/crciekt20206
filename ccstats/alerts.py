"""The new alerts (stage 4, your picks of 26 November): Goal reached!, Series won, Milestone reached, Career best,
Streaks (your winning run reaching 3, 5 or 10; a losing run reaching 3), Ranking moves (your team to No. 1 in a
format; one of your players into the top 10 of the ratings); and two names joined by themselves, sure to be one player
(your answer of 26 November). They pop up as new matches arrive, beside "New matches"
and "New record!". Each is said once: what has been said is remembered with the career (`seen`), so a restart or a
second look never says it again. Only your teams and their players are alerted on.

`check(career, added, my_teams, goals, seen)` -> (alerts, seen as it now stands). The first time it runs on a career
(nothing seen yet) it only notes where things stand, so an old career doesn't pop up a hundred alerts at once."""

from __future__ import annotations

import pandas as pd

STREAK_WINS = (3, 5, 10)
STREAK_LOSSES = (3,)
LASTING = ("goal|", "join|")   # said about something that stays true: remembered for good
MIN_BEST = 5       # a career best counts once the player has had this many innings (or bowled in this many matches)


def _outcome(r, team: str) -> str:
    from .fixtures import _outcome as out
    return out(r, team)


def check(career, added: list[str], my_teams: list[str], goals: list[dict], seen: dict | None) -> tuple[list[dict], dict]:
    seen = dict(seen or {})
    first = not seen.get("started")
    out: list[dict] = []
    m = career.matches
    new = m[m.source.isin(set(added))] if "source" in m else m.iloc[0:0]
    mine = [t for t in my_teams if t in set(m.home) | set(m.away)]
    order = list(seen.get("said", []))      # in the order said (oldest first)
    said = set(order)

    def note(key: str) -> None:
        if key not in said:
            said.add(key)
            order.append(key)

    def say(key: str, kind: str, title: str, text: str) -> None:
        if key in said:
            return
        note(key)
        if not first:
            out.append(dict(kind=kind, title=title, text=text))

    # ---------------------------------------------------------------- goals reached
    from .fixtures import goal_label, goal_progress, track
    try:
        tracked = track(career, [], auto=tuple(mine))
    except Exception:  # noqa: BLE001
        tracked = None
    for g in goals:
        if g.get("team") not in mine and g.get("kind") not in ("player", "topscorer", "average", "hauls"):
            continue
        try:
            pg = goal_progress(career, tracked, g)
        except Exception:  # noqa: BLE001 - a goal that can't be worked out is shown on its page, never alerted wrongly
            continue
        if pg["status"] == "achieved":
            say(f"goal|{g.get('id', goal_label(g))}", "goal", "Goal reached!", f"{goal_label(g)}: {pg['text']}")

    for team in mine:
        tm = m[(m.home == team) | (m.away == team)].sort_values(["date", "match_id"])
        here = new[(new.home == team) | (new.away == team)]
        # ------------------------------------------------------------ series won (and titles)
        for r in here.itertuples():
            n_games = int(r.series_length) if pd.notna(r.series_length) and r.series_length else 0   # not always printed
            if r.series_id and n_games >= 2:
                s = tm[tm.series_id == r.series_id]
                won = sum(_outcome(x, team) == "W" for x in s.itertuples())
                lost = sum(_outcome(x, team) == "L" for x in s.itertuples())
                n = n_games
                if won > n // 2 or (len(s) >= n and won > lost):
                    opp = r.away if r.home == team else r.home
                    say(f"series|{team}|{r.series_id}", "series", "Series won",
                        f"{team} win the {r.format} series against {opp} {won}–{lost}.")
            if r.knockout and r.stage == "Final" and _outcome(r, team) == "W":
                say(f"title|{team}|{r.event}|{r.season}", "series", "Title won!", f"{team} win the {r.event} {r.season}.")
        # ------------------------------------------------------------ streaks, format by format
        for fmt in here.format.unique():
            outs = [_outcome(x, team) for x in tm[tm.format == fmt].itertuples()]
            outs = [o for o in outs if o != "NR"]
            if not outs:
                continue
            run, last = 0, outs[-1]
            for o in reversed(outs):
                if o != last:
                    break
                run += 1
            n_played = len(outs)
            if last == "W" and run in STREAK_WINS:
                say(f"streak|{team}|{fmt}|W|{run}|{n_played}", "streak", "On a roll",
                    f"{team} have won {run} {fmt}s in a row.")
            if last == "L" and run in STREAK_LOSSES:
                say(f"streak|{team}|{fmt}|L|{run}|{n_played}", "streak", "A losing run",
                    f"{team} have lost {run} {fmt}s in a row.")
        # ------------------------------------------------------------ No. 1 in the team ratings
        from .rankings import team_elo
        for sec in here.section.unique():
            table, _ = team_elo(career, sec)
            top = table.team.iloc[0] if len(table) else ""
            key = f"top|{sec}"
            was = seen.get(key, "")
            seen[key] = top
            if top == team and was != team:
                say(f"no1|{team}|{sec}|{len(m)}", "rank", "No. 1!", f"{team} go to No. 1 in the {sec} team ratings.")
    # ---------------------------------------------------------------- your players: milestones, career bests, top 10
    from .players import milestones_reached
    from .rankings import player_ratings
    bat, bowl = career.batting, career.bowling
    for r in new.itertuples():
        teams_here = [t for t in mine if t in (r.home, r.away)]
        if not teams_here:
            continue
        sec_ids = m[m.section == r.section].match_id
        ours = set(bat[(bat.match_id == r.match_id) & bat.team.isin(teams_here)].player) | \
            set(bowl[(bowl.match_id == r.match_id) & bowl.team.isin(teams_here)].player)
        for line in milestones_reached(career, sec_ids, r.match_id):
            if any(line.startswith(p + " ") for p in ours):
                say(f"mile|{r.match_id}|{line}", "milestone", "Milestone reached", f"{line} ({r.section}).")
        # career bests in this format, against their own earlier innings (5 at least)
        fmt_ids = set(m[(m.format == r.format) & (m.date <= r.date)].match_id)
        for p in ours:
            pb = bat[bat.match_id.isin(fmt_ids) & (bat.player == p) & bat.did_bat]
            now = pb[pb.match_id == r.match_id]
            earlier = pb[(pb.match_id != r.match_id) & pb.match_id.isin(m[m.date < r.date].match_id)]
            if len(now) and len(earlier) >= MIN_BEST and int(now.runs.max()) > int(earlier.runs.max()):
                say(f"bestbat|{p}|{r.format}|{r.match_id}", "best", "Career best",
                    f"{p} makes {int(now.runs.max())}, a career best in {r.format}s (was {int(earlier.runs.max())}).")
            pw = bowl[bowl.match_id.isin(fmt_ids) & (bowl.player == p)]
            nw = pw[pw.match_id == r.match_id]
            ew = pw[(pw.match_id != r.match_id) & pw.match_id.isin(m[m.date < r.date].match_id)]
            if len(nw) and ew.match_id.nunique() >= MIN_BEST:
                best_now = nw.sort_values(["wickets", "runs"], ascending=[False, True]).iloc[0]
                best_was = ew.sort_values(["wickets", "runs"], ascending=[False, True]).iloc[0]
                if best_now.wickets > 0 and (best_now.wickets, -best_now.runs) > (best_was.wickets, -best_was.runs):
                    say(f"bestbowl|{p}|{r.format}|{r.match_id}", "best", "Career best",
                        f"{p} takes {int(best_now.wickets)}/{int(best_now.runs)}, career-best bowling in {r.format}s "
                        f"(was {int(best_was.wickets)}/{int(best_was.runs)}).")
    for sec in new.section.unique():
        try:
            pr = player_ratings(career, sec)
        except Exception:  # noqa: BLE001
            continue
        for kind in ("batting", "bowling"):
            if pr.empty or kind not in pr:
                continue
            top = list(pr.dropna(subset=[kind]).sort_values(kind, ascending=False).player.head(10))
            key = f"top10|{sec}|{kind}"
            was = set(seen.get(key, []))
            seen[key] = top
            for p in top:
                team = pr.set_index("player").team.get(p, "")
                if team in mine and p not in was and was:
                    say(f"top10|{sec}|{kind}|{p}|{len(m)}", "rank", "Into the top 10",
                        f"{p} is into the top 10 of the {sec} {kind} ratings ({ordinal(top.index(p) + 1)}).")
    # ---------------------------------------------------------------- names joined by themselves (sure to be one player)
    joins = getattr(career, "auto_joins", None)
    fresh = [r for r in (joins.itertuples() if joins is not None else []) if f"join|{r.other}|{r.keep}" not in said]
    if len(fresh) > 3:     # many at once: one alert, the list is on Data check
        for r in fresh:
            note(f"join|{r.other}|{r.keep}")
        if not first:
            out.append(dict(kind="names", title="Names joined",
                            text=f"{len(fresh)} pairs of names were joined, each sure to be one player. See them (and undo any) "
                                 "on Data check."))
    else:
        for r in fresh:
            say(f"join|{r.other}|{r.keep}", "names", "Names joined",
                f"{r.other} now counts as {r.keep} ({r.team}): sure to be one player. Undo on Data check if not.")
    # what's said about something that stays true (a goal reached, two names joined) is kept for good, or it would be
    # said again; of the rest (each about one match) the newest 3,000 are kept
    lasting = [k for k in order if k.startswith(LASTING)]
    rest = [k for k in order if not k.startswith(LASTING)]
    seen["said"] = lasting + rest[-3000:]
    seen["started"] = True
    return out, seen


def ordinal(n: int) -> str:
    from .stats import ordinal as o
    return o(n)
