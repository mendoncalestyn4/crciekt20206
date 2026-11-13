"""Player stories and deeper analysis: who wins games, milestones, quirks,
heroes in defeat, carrying the team, Player of the Series, form, firsts,
partnerships, runs above expected, quality-adjusted and settled averages, what
wins games, expected wins, match-winners, dependence, styles, consistency and
whether a run of form is real.

Everything works on a set of match ids (one section, usually), and every
comparison is with the average player in the same matches.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .stats import KIND, bars_for

SHRINK = {"t20": 8, "one": 6, "multi": 5}  # dismissals of "average" added when settling an average
RELIABLE = {"t20": 15, "one": 12, "multi": 10}  # dismissals before an average is called reliable


def kind_of_ids(career, ids) -> str:
    m = career.matches[career.matches.match_id.isin(ids)]
    if m.empty:
        return "t20"
    return KIND.get(m.format.mode().iloc[0], "t20")


def _outcomes(career, ids) -> pd.Series:
    """(match_id, team) -> W / L / D / T / NR."""
    m = career.matches[career.matches.match_id.isin(ids)]
    rows = {}
    for r in m.itertuples():
        for t, o in ((r.home, r.away), (r.away, r.home)):
            rows[(r.match_id, t)] = ("W" if r.winner == t else "L" if r.winner == o else "D" if r.result_type == "draw"
                                     else "T" if r.result_type == "tie" else "NR")
    return pd.Series(rows, dtype=object)


def innings(career, ids) -> pd.DataFrame:
    """Every innings batted, with the match, the team's result and the team's total."""
    b = career.batting[career.batting.match_id.isin(ids) & career.batting.did_bat]
    m = career.matches.set_index("match_id")
    out = _outcomes(career, ids)
    tot = career.innings.set_index(["match_id", "innings_no"]).runs
    b = b.assign(date=b.match_id.map(m.date), season=b.match_id.map(m.season), section=b.match_id.map(m.section),
                 result=[out.get((a, t), "NR") for a, t in zip(b.match_id, b.team)],
                 team_total=[tot.get((a, i), np.nan) for a, i in zip(b.match_id, b.innings_no)])
    return b.sort_values(["date", "match_id", "innings_no", "position"]).reset_index(drop=True)


def spells(career, ids) -> pd.DataFrame:
    w = career.bowling[career.bowling.match_id.isin(ids) & (career.bowling.balls > 0)]
    m = career.matches.set_index("match_id")
    out = _outcomes(career, ids)
    w = w.assign(date=w.match_id.map(m.date), season=w.match_id.map(m.season),
                 result=[out.get((a, t), "NR") for a, t in zip(w.match_id, w.team)])
    return w.sort_values(["date", "match_id", "innings_no"]).reset_index(drop=True)


def _win_pct(results: pd.Series, multi: bool) -> float:
    w, lo, d = (results == "W").sum(), (results == "L").sum(), (results == "D").sum()
    n = w + lo + (d if multi else 0)
    return w / n * 100 if n else np.nan


def _matches_of(career, ids) -> pd.DataFrame:
    """(match_id, team, player) for everyone who played (batted or not)."""
    b = career.batting[career.batting.match_id.isin(ids)]
    return b[["match_id", "team", "player"]].drop_duplicates()


# --------------------------------------------------------------------------- #
# 8 · team wins when a player fires
# --------------------------------------------------------------------------- #


def win_when(career, ids, min_times: int = 3) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(batters: team win % in matches where they made a big score (50+ in white-ball
    cricket, 100+ in Tests), against every other match they played; bowlers: the
    same for a haul in an innings (3+ wickets in T20, 4+ in one-day, 5+ in Tests)).
    The bars used are in each frame's attrs."""
    kind = kind_of_ids(career, ids)
    bar = bars_for(kind)
    multi = kind == "multi"
    out = _outcomes(career, ids)
    played = _matches_of(career, ids)
    played = played.assign(result=[out.get((a, t), "NR") for a, t in zip(played.match_id, played.team)])
    inn = innings(career, ids)
    big = set(zip(inn[inn.runs >= bar["big"]].match_id, inn[inn.runs >= bar["big"]].player))
    sp = spells(career, ids)
    haul = sp.groupby(["match_id", "player"]).wickets.max()
    hauls = set(haul[haul >= bar["haul"]].index)
    res = []
    for flagset, label in ((big, "fifty"), (hauls, "three_wkts")):
        rows = []
        p = played.assign(flag=[(a, b) in flagset for a, b in zip(played.match_id, played.player)])
        for player, g in p.groupby("player"):
            yes, no = g[g.flag], g[~g.flag]
            if len(yes) < min_times:
                continue
            rows.append(dict(player=player, team=" / ".join(sorted(set(g.team))), times=len(yes),
                             won_when=int((yes.result == "W").sum()), pct_when=_win_pct(yes.result, multi),
                             other_games=len(no), pct_other=_win_pct(no.result, multi)))
        d = pd.DataFrame(rows, columns=["player", "team", "times", "won_when", "pct_when", "other_games", "pct_other"])
        d["lift"] = d.pct_when - d.pct_other
        d = d.sort_values(["pct_when", "times"], ascending=False).reset_index(drop=True)
        d.attrs.update(big=bar["big"], haul=bar["haul"])
        res.append(d)
    return res[0], res[1]


# --------------------------------------------------------------------------- #
# 9 · milestones
# --------------------------------------------------------------------------- #

STEPS = {"runs": [250, 500, 750, 1000, 1500, 2000, 2500, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000],
         "wickets": [25, 50, 75, 100, 150, 200, 250, 300, 400, 500],
         "matches": [25, 50, 75, 100, 150, 200, 250, 300],
         "hundreds": [5, 10, 15, 20, 25, 30, 40, 50]}
CLOSE = {"runs": 0.12, "wickets": 0.12, "matches": 0.1, "hundreds": 0.0}  # how close counts as "on the way"


def _next_step(v: float, steps: list[int]) -> int | None:
    return next((s for s in steps if s > v), None)


def milestone_watch(career, ids) -> pd.DataFrame:
    """Players close to a round number in these matches: runs, wickets, matches, hundreds."""
    b = career.batting[career.batting.match_id.isin(ids)]
    w = career.bowling[career.bowling.match_id.isin(ids)]
    last_team = b.sort_values("match_id").groupby("player").team.last()
    tallies = {"runs": b[b.did_bat].groupby("player").runs.sum(), "wickets": w.groupby("player").wickets.sum(),
               "matches": b.groupby("player").match_id.nunique(),
               "hundreds": b[b.runs >= 100].groupby("player").size()}
    rows = []
    for what, t in tallies.items():
        for player, v in t.items():
            nxt = _next_step(v, STEPS[what])
            if nxt is None:
                continue
            need = nxt - v
            close = need <= max(1, nxt * CLOSE[what]) if what != "hundreds" else need == 1
            if close and v >= min(STEPS[what]) * 0.6:
                rows.append(dict(player=player, team=last_team.get(player, ""), what=what, now=int(v), next=nxt,
                                 needed=int(need)))
    d = pd.DataFrame(rows, columns=["player", "team", "what", "now", "next", "needed"])
    d["share"] = d.needed / d.next
    return d.sort_values(["share", "next"], ascending=[True, False]).drop(columns="share").reset_index(drop=True)


def milestones_reached(career, ids, match_id: str) -> list[str]:
    """Round numbers passed in one match (runs, wickets, matches, hundreds in these matches up to it)."""
    m = career.matches[career.matches.match_id.isin(ids)].sort_values(["date", "match_id"])
    upto = list(m.match_id)
    if match_id not in upto:
        return []
    upto = upto[:upto.index(match_id) + 1]
    b = career.batting[career.batting.match_id.isin(upto)]
    w = career.bowling[career.bowling.match_id.isin(upto)]
    here_b = b[b.match_id == match_id]
    here_w = w[w.match_id == match_id]
    out = []
    for p, x in here_b[here_b.did_bat].groupby("player"):
        total = int(b[(b.player == p) & b.did_bat].runs.sum())
        before = total - int(x.runs.sum())
        for s in STEPS["runs"]:
            if before < s <= total and s >= 500:
                out.append(f"{p} passes {s:,} runs")
        hundreds = int((b[b.player == p].runs >= 100).sum())
        if (x.runs >= 100).any() and hundreds in STEPS["hundreds"]:
            out.append(f"{p} makes hundred number {hundreds}")
    for p, x in here_w.groupby("player"):
        total = int(w[w.player == p].wickets.sum())
        before = total - int(x.wickets.sum())
        for s in STEPS["wickets"]:
            if before < s <= total and s >= 50:
                out.append(f"{p} reaches {s} wickets")
    for p in here_b.player.unique():
        n = int(b[b.player == p].match_id.nunique())
        if n in STEPS["matches"] and n >= 50:
            out.append(f"{p} plays match number {n}")
    return out


# --------------------------------------------------------------------------- #
# 11 · nervous nineties, pairs, not-outs · 12 · heroes in defeat · 13 · carried the team
# --------------------------------------------------------------------------- #


def quirks(career, ids) -> dict[str, pd.DataFrame]:
    inn = innings(career, ids)
    nine = inn[inn.out & (inn.runs >= 90) & (inn.runs <= 99)]
    nineties = (nine.groupby("player").agg(times=("runs", "size"), scores=("runs", lambda s: ", ".join(map(str, s))),
                                           team=("team", "last"))
                .sort_values("times", ascending=False).reset_index())
    ducks = inn[(inn.runs == 0) & inn.out]
    two = ducks.groupby(["match_id", "player"]).size()
    pair_keys = two[two >= 2].index
    pr = ducks.set_index(["match_id", "player"]).loc[list(pair_keys)].reset_index() if len(pair_keys) else ducks.iloc[:0]
    pairs = (pr.drop_duplicates(["match_id", "player"]).groupby("player").agg(pairs=("match_id", "size"), team=("team", "last"))
             .sort_values("pairs", ascending=False).reset_index())
    no = inn.groupby("player").agg(innings=("runs", "size"), not_outs=("out", lambda s: int((~s).sum())), team=("team", "last"))
    no["pct"] = no.not_outs / no.innings * 100
    not_outs = no[no.not_outs > 0].sort_values(["not_outs", "pct"], ascending=False).reset_index()
    return dict(nineties=nineties, pairs=pairs, not_outs=not_outs)


def heroes_in_defeat(career, ids, top: int = 15) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(best innings in a losing side, best bowling in a losing side)."""
    inn = innings(career, ids)
    lost = inn[inn.result == "L"].sort_values(["runs", "balls"], ascending=[False, True]).head(top)
    sp = spells(career, ids)
    sl = sp[sp.result == "L"].assign(k=lambda x: x.wickets * 1000 - x.runs).sort_values("k", ascending=False).head(top)
    return lost.reset_index(drop=True), sl.drop(columns="k").reset_index(drop=True)


def carried(career, ids, min_innings: int = 5) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(innings that made up the biggest share of the team's total, players whose
    runs are the biggest share of their team's totals over all their innings)."""
    inn = innings(career, ids)
    inn = inn[inn.team_total > 0]
    inn = inn.assign(share=inn.runs / inn.team_total * 100)
    kind = kind_of_ids(career, ids)
    floor = {"t20": 25, "one": 40, "multi": 50}[kind]
    top = inn[inn.runs >= floor].sort_values("share", ascending=False).head(15).reset_index(drop=True)
    g = inn.groupby("player").agg(innings=("runs", "size"), runs=("runs", "sum"), team_runs=("team_total", "sum"),
                                  team=("team", "last"))
    g = g[g.innings >= min_innings]
    g["share"] = g.runs / g.team_runs * 100
    return top, g.sort_values("share", ascending=False).reset_index()


# --------------------------------------------------------------------------- #
# 15 · biggest upsets
# --------------------------------------------------------------------------- #


def upsets(career, section: str, top: int = 15) -> pd.DataFrame:
    """Wins by the side with the much lower Elo rating going in, least likely first."""
    from .rankings import team_elo
    _, hist = team_elo(career, section)
    if hist.empty:
        return pd.DataFrame(columns=["match_id", "date", "winner", "loser", "winner_elo", "loser_elo", "chance", "result"])
    m = career.matches.set_index("match_id")
    rows = []
    for mid, g in hist.groupby("match_id"):
        if len(g) != 2:
            continue
        w = m.winner.get(mid, "")
        if not w:
            continue
        a = g[g.team == w]
        b = g[g.team != w]
        if a.empty or b.empty:
            continue
        rw, rl = float(a.before.iloc[0]), float(b.before.iloc[0])
        chance = 1 / (1 + 10 ** ((rl - rw) / 400)) * 100
        rows.append(dict(match_id=mid, date=a.date.iloc[0], winner=w, loser=b.team.iloc[0], winner_elo=rw, loser_elo=rl,
                         chance=chance, result=m.result.get(mid, "")))
    d = pd.DataFrame(rows, columns=["match_id", "date", "winner", "loser", "winner_elo", "loser_elo", "chance", "result"])
    return d[d.chance < 50].sort_values("chance").head(top).reset_index(drop=True)


# --------------------------------------------------------------------------- #
# 16 · Player of the Series
# --------------------------------------------------------------------------- #


def impact(career, ids) -> pd.DataFrame:
    """Impact points per player per match: runs, plus each wicket worth the
    section's runs per wicket (so a wicket and an average innings count the same)."""
    inn = career.innings[career.innings.match_id.isin(ids)]
    rpw = inn.runs.sum() / max(inn.wickets.sum(), 1)
    b = career.batting[career.batting.match_id.isin(ids) & career.batting.did_bat].groupby(
        ["match_id", "team", "player"]).runs.sum()
    w = career.bowling[career.bowling.match_id.isin(ids)].groupby(["match_id", "team", "player"]).wickets.sum()
    d = pd.concat([b.rename("runs"), w.rename("wickets")], axis=1).fillna(0).reset_index()
    d["points"] = d.runs + d.wickets * rpw
    d.attrs["rpw"] = rpw
    return d


def player_of_series(career, ids) -> pd.DataFrame:
    """One row per bilateral series: the player with the most impact points over the series."""
    m = career.matches[career.matches.match_id.isin(ids) & (career.matches.series_id != "")]
    if m.empty:
        return pd.DataFrame(columns=["series_id", "player", "team", "runs", "wickets", "points", "matches"])
    imp = impact(career, m.match_id)
    sid = m.set_index("match_id").series_id
    imp["series_id"] = imp.match_id.map(sid)
    g = imp.groupby(["series_id", "player", "team"]).agg(runs=("runs", "sum"), wickets=("wickets", "sum"),
                                                         points=("points", "sum"), matches=("match_id", "nunique")).reset_index()
    best = g.sort_values(["points", "runs"], ascending=False).groupby("series_id").head(1)
    best = best.assign(runs=best.runs.astype(int), wickets=best.wickets.astype(int))
    return best.reset_index(drop=True)


# --------------------------------------------------------------------------- #
# 18 · form guide · 48 · is the form real?
# --------------------------------------------------------------------------- #


def form_guide(career, ids, last: int = 5, min_innings: int = 6) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(batters: last `last` scores, their average v the player's own average;
    bowlers: last `last` figures, wickets per innings v their own)."""
    inn = innings(career, ids)
    rows = []
    for p, g in inn.groupby("player"):
        if len(g) < min_innings or g.position.median() > 7:  # batters only: a tail-ender's low scores are no news
            continue
        r = g.tail(last)
        avg = g.runs.sum() / max(g.out.sum(), 1)
        recent = r.runs.sum() / max(r.out.sum(), 1)
        rows.append(dict(player=p, team=g.team.iloc[-1], innings=len(g),
                         last=" ".join(f"{x}{'' if o else '*'}" for x, o in zip(r.runs, r.out)),
                         recent_avg=recent, career_avg=avg, recent_runs=int(r.runs.sum()),
                         trend=recent - avg, last_date=g.date.iloc[-1]))
    bat = pd.DataFrame(rows, columns=["player", "team", "innings", "last", "recent_avg", "career_avg", "recent_runs",
                                      "trend", "last_date"])
    sp = spells(career, ids)
    rows = []
    for p, g in sp.groupby("player"):
        if len(g) < min_innings:
            continue
        r = g.tail(last)
        rows.append(dict(player=p, team=g.team.iloc[-1], innings=len(g),
                         last=" ".join(f"{w}/{x}" for w, x in zip(r.wickets, r.runs)),
                         recent_wpi=r.wickets.mean(), career_wpi=g.wickets.mean(),
                         recent_econ=r.runs.sum() / r.balls.sum() * 6, career_econ=g.runs.sum() / g.balls.sum() * 6,
                         trend=r.wickets.mean() - g.wickets.mean(), last_date=g.date.iloc[-1]))
    bowl = pd.DataFrame(rows, columns=["player", "team", "innings", "last", "recent_wpi", "career_wpi", "recent_econ",
                                       "career_econ", "trend", "last_date"])
    return (bat.sort_values("trend", ascending=False).reset_index(drop=True),
            bowl.sort_values("trend", ascending=False).reset_index(drop=True))


def form_is_real(career, ids, last: int = 8, min_innings: int = 12) -> pd.DataFrame:
    """For batters with enough innings: is their recent run (last `last` innings)
    different from their usual scoring by more than luck would explain?  Compares
    the recent runs per innings with their earlier innings, allowing for how much
    their scores normally bounce around."""
    inn = innings(career, ids)
    rows = []
    for p, g in inn.groupby("player"):
        if len(g) < min_innings:
            continue
        recent, before = g.tail(last).runs, g.iloc[:-last].runs
        if len(before) < 4:
            continue
        sd = before.std(ddof=1)
        if not sd or not np.isfinite(sd):
            continue
        z = (recent.mean() - before.mean()) / (sd / np.sqrt(len(recent)))
        verdict = ("Real: hot" if z >= 2 else "Real: cold" if z <= -2 else "Maybe" if abs(z) >= 1 else "Probably luck")
        rows.append(dict(player=p, team=g.team.iloc[-1], recent=recent.mean(), before=before.mean(), innings=len(g),
                         z=z, verdict=verdict))
    d = pd.DataFrame(rows, columns=["player", "team", "recent", "before", "innings", "z", "verdict"])
    return d.reindex(d.z.abs().sort_values(ascending=False).index).reset_index(drop=True)


# --------------------------------------------------------------------------- #
# 20 · career firsts · 37 · after a hundred
# --------------------------------------------------------------------------- #


def team_share(career, player: str) -> pd.DataFrame:
    """The player's share of their team in each competition and season they played, newest first: their matches out
    of the team's, their runs out of all the runs the team's batters made (off the bat: extras are no one's) and their wickets
    out of all the wickets the team's bowlers took. Columns: section, season, team, matches, team_matches, runs,
    team_runs, run_share, wickets, team_wickets, wicket_share (shares in %)."""
    cols = ["section", "season", "team", "matches", "team_matches", "runs", "team_runs", "run_share", "wickets",
            "team_wickets", "wicket_share"]
    b = career.batting[career.batting.player == player]
    if b.empty:
        return pd.DataFrame(columns=cols)
    m = career.matches.set_index("match_id")
    played = b[["match_id", "team"]].drop_duplicates()
    played = played.assign(section=played.match_id.map(m.section), season=played.match_id.map(m.season),
                           date=played.match_id.map(m.date))
    out = []
    for (section, season, team), g in played.groupby(["section", "season", "team"]):
        mm = career.matches[(career.matches.section == section) & (career.matches.season == season)
                            & ((career.matches.home == team) | (career.matches.away == team))]
        ids = set(mm.match_id)
        inn = career.innings[career.innings.match_id.isin(ids) & (career.innings.team == team)]
        bowl = career.bowling[career.bowling.match_id.isin(ids) & (career.bowling.team == team)]
        mine_b = b[b.match_id.isin(ids) & (b.team == team) & b.did_bat]
        mine_w = bowl[bowl.player == player]
        bat_t = career.batting[career.batting.match_id.isin(ids) & (career.batting.team == team) & career.batting.did_bat]
        team_runs, team_wkts = int(bat_t.runs.sum()), int(bowl.wickets.sum())
        runs, wkts = int(mine_b.runs.sum()), int(mine_w.wickets.sum())
        out.append(dict(section=section, season=season, team=team, matches=int(g.match_id.nunique()),
                        team_matches=len(ids), runs=runs, team_runs=team_runs,
                        run_share=runs / team_runs * 100 if team_runs else np.nan, wickets=wkts, team_wickets=team_wkts,
                        wicket_share=wkts / team_wkts * 100 if team_wkts else np.nan, _last=g.date.max()))
    d = pd.DataFrame(out).sort_values("_last", ascending=False)
    return d[cols].reset_index(drop=True)


def firsts(career, player: str) -> pd.DataFrame:
    """A player's firsts across the whole career: first match (and first for each
    team and section), first fifty, hundred, wicket, three- and five-for, Player of the Match."""
    m = career.matches.set_index("match_id")
    b = career.batting[career.batting.player == player].assign(date=lambda x: x.match_id.map(m.date)).sort_values(["date", "innings_no"])
    w = career.bowling[career.bowling.player == player].assign(date=lambda x: x.match_id.map(m.date)).sort_values(["date", "innings_no"])
    rows = []

    def add(what, r, detail=""):
        if r is None:
            return
        rows.append(dict(date=r.date, what=what, detail=detail, match_id=r.match_id, section=m.section.get(r.match_id, ""),
                         against=r.opposition))

    first = lambda d: next(d.itertuples(), None)  # noqa: E731
    add("First match", first(b), f"for {b.team.iloc[0]}" if len(b) else "")
    for (team, section), g in b.groupby(["team", b.match_id.map(m.section)], sort=False):
        r = first(g)
        if r is not None and not (rows and rows[0]["match_id"] == r.match_id):
            add(f"First match in {section}", r, f"for {team}")
    bb = b[b.did_bat]
    add("First run", first(bb[bb.runs > 0]))
    for lo, label in ((50, "First fifty"), (100, "First hundred"), (150, "First 150"), (200, "First double hundred")):
        r = first(bb[bb.runs >= lo])
        add(label, r, f"{r.runs}{'' if r.out else '*'} ({r.balls} balls)" if r is not None else "")
    for lo, label in ((1, "First wicket"), (3, "First three-for"), (5, "First five-for")):
        r = first(w[w.wickets >= lo])
        add(label, r, f"{r.wickets}/{r.runs}" if r is not None else "")
    potm = career.matches[career.matches.player_of_match == player].sort_values("date")
    if len(potm):
        p = potm.iloc[0]
        opp = p.away if (b[b.match_id == p.match_id].team == p.home).any() else p.home
        rows.append(dict(date=p.date, what="First Player of the Match", detail="", match_id=p.match_id,
                         section=p.section, against=opp))
    return pd.DataFrame(rows, columns=["date", "what", "detail", "match_id", "section", "against"]) \
        .sort_values("date", kind="stable").reset_index(drop=True)


def after_hundred(career, ids, min_hundreds: int = 1) -> pd.DataFrame:
    """The innings straight after each hundred (in these matches), against the batter's average."""
    inn = innings(career, ids)
    rows = []
    for p, g in inn.groupby("player"):
        g = g.reset_index(drop=True)
        idx = list(g.index[g.runs >= 100])
        nxt = [i + 1 for i in idx if i + 1 < len(g)]
        if len(idx) < min_hundreds or not nxt:
            continue
        after = g.loc[nxt]
        rows.append(dict(player=p, team=g.team.iloc[-1], hundreds=len(idx), next_scores=", ".join(
            f"{x}{'' if o else '*'}" for x, o in zip(after.runs, after.out)),
            next_avg=after.runs.sum() / max(after.out.sum(), 1), average=g.runs.sum() / max(g.out.sum(), 1)))
    return pd.DataFrame(rows, columns=["player", "team", "hundreds", "next_scores", "next_avg", "average"]) \
        .sort_values("hundreds", ascending=False).reset_index(drop=True)


# --------------------------------------------------------------------------- #
# 38 · runs above expected · 39/40 · quality-adjusted and settled averages
# --------------------------------------------------------------------------- #


def runs_above_expected(career, ids, min_innings: int = 5) -> pd.DataFrame:
    """Each innings is compared with what the average batter made in these matches
    coming in at the same position with the same number of wickets down (grouped:
    0, 1, 2, 3-4, 5+).  Runs above expected = runs made minus that average."""
    from .analysis import entry_scores
    inn = innings(career, ids)
    e = entry_scores(career)
    inn = inn.merge(e, on=["match_id", "innings_no", "position"], how="left")
    wk = inn.came_in_wickets.fillna(0)
    inn["situation"] = np.select([wk == 0, wk == 1, wk == 2, wk <= 4], ["0", "1", "2", "3-4"], "5+")
    exp = inn.groupby(["position", "situation"]).runs.mean().rename("expected")
    inn = inn.join(exp, on=["position", "situation"])
    inn["above"] = inn.runs - inn.expected
    g = inn.groupby("player").agg(innings=("runs", "size"), runs=("runs", "sum"), expected=("expected", "sum"),
                                  above=("above", "sum"), team=("team", "last"),
                                  usual_position=("position", lambda s: int(s.mode().iloc[0])))
    g = g[g.innings >= min_innings]
    g["per_innings"] = g.above / g.innings
    return g.sort_values("above", ascending=False).reset_index()


def adjusted_averages(career, ids, min_innings: int = 5) -> pd.DataFrame:
    """Batting average three ways: as it is; adjusted for the bowling attacks
    faced (runs against an attack that concedes fewer runs per wicket than
    average count for more); and settled (a few average dismissals added, so a
    short record is pulled towards the section average until it has enough
    innings to stand on its own).  Tagged 'reliable' once there are enough dismissals."""
    kind = kind_of_ids(career, ids)
    inn = innings(career, ids)
    allinn = career.innings[career.innings.match_id.isin(ids)]
    conceded = allinn.groupby("opposition").agg(r=("runs", "sum"), w=("wickets", "sum"))
    rpw = allinn.runs.sum() / max(allinn.wickets.sum(), 1)
    attack = (conceded.r / conceded.w.replace(0, np.nan)).fillna(rpw)  # runs per wicket each side's bowlers give away
    inn = inn.assign(factor=inn.opposition.map(lambda t: rpw / attack.get(t, rpw) if attack.get(t, rpw) else 1.0))
    inn["adj_runs"] = inn.runs * inn.factor
    base = inn.runs.sum() / max(inn.out.sum(), 1)
    k = SHRINK[kind]
    g = inn.groupby("player").agg(innings=("runs", "size"), runs=("runs", "sum"), outs=("out", "sum"),
                                  adj_runs=("adj_runs", "sum"), team=("team", "last"))
    g = g[g.innings >= min_innings]
    g["average"] = g.runs / g.outs.replace(0, np.nan)
    g["adjusted"] = g.adj_runs / g.outs.replace(0, np.nan)
    g["settled"] = (g.runs + k * base) / (g.outs + k)
    g["tag"] = np.where(g.outs >= RELIABLE[kind], "reliable", "still settling")
    g.attrs["base"] = base
    return g.sort_values("settled", ascending=False).reset_index()


def adjusted_bowling(career, ids, min_innings: int = 5) -> pd.DataFrame:
    """Bowling average as it is, adjusted for the batting faced (wickets against
    a side that scores more per wicket are worth more), and settled."""
    kind = kind_of_ids(career, ids)
    sp = spells(career, ids)
    allinn = career.innings[career.innings.match_id.isin(ids)]
    scored = allinn.groupby("team").agg(r=("runs", "sum"), w=("wickets", "sum"))
    rpw = allinn.runs.sum() / max(allinn.wickets.sum(), 1)
    bat = (scored.r / scored.w.replace(0, np.nan)).fillna(rpw)
    sp = sp.assign(factor=sp.opposition.map(lambda t: rpw / bat.get(t, rpw) if bat.get(t, rpw) else 1.0))
    sp["adj_runs"] = sp.runs * sp.factor
    base = sp.runs.sum() / max(sp.wickets.sum(), 1)
    k = SHRINK[kind]
    g = sp.groupby("player").agg(innings=("runs", "size"), runs=("runs", "sum"), wickets=("wickets", "sum"),
                                 adj_runs=("adj_runs", "sum"), team=("team", "last"))
    g = g[g.innings >= min_innings]
    g["average"] = g.runs / g.wickets.replace(0, np.nan)
    g["adjusted"] = g.adj_runs / g.wickets.replace(0, np.nan)
    g["settled"] = (g.runs + k * base) / (g.wickets + k)
    g["tag"] = np.where(g.wickets >= RELIABLE[kind], "reliable", "still settling")
    return g.sort_values("settled").reset_index()


# --------------------------------------------------------------------------- #
# 42 · what wins games · 43 · expected wins
# --------------------------------------------------------------------------- #


def what_wins(career, ids) -> pd.DataFrame:
    """For each match with a winner: did the winners have more of each thing than
    the losers?  % of games where the side with more won (draws of the measure
    left out)."""
    from . import partnerships as P
    m = career.matches[career.matches.match_id.isin(ids) & (career.matches.winner != "")]
    if m.empty:
        return pd.DataFrame(columns=["measure", "games", "won_pct", "better"])
    inn = career.innings[career.innings.match_id.isin(m.match_id)]
    bat = career.batting[career.batting.match_id.isin(m.match_id) & career.batting.did_bat]
    bowl = career.bowling[career.bowling.match_id.isin(m.match_id)]
    st_ = P.stands(career, m.match_id)
    per = {}
    g_inn = inn.groupby(["match_id", "team"])
    per["Higher run rate"] = (g_inn.runs.sum() / g_inn.balls.sum().replace(0, np.nan) * 6, True)
    per["More fours"] = (bat.groupby(["match_id", "team"]).fours.sum(), True)
    per["More sixes"] = (bat.groupby(["match_id", "team"]).sixes.sum(), True)
    per["Higher top score (one batter)"] = (bat.groupby(["match_id", "team"]).runs.max(), True)
    stand = bars_for(kind_of_ids(career, ids))["stand"]
    per[f"More {stand}+ stands"] = (st_[st_.runs >= stand].groupby(["match_id", "team"]).size(), True)
    per["Best bowling figures (most wickets by one bowler)"] = (bowl.groupby(["match_id", "team"]).wickets.max(), True)
    ext = inn.assign(ex=inn.extras).groupby(["match_id", "opposition"]).ex.sum()
    ext.index = ext.index.set_names(["match_id", "team"])
    per["Fewer extras given away"] = (ext, False)
    if bowl.dots.notna().any():
        d = bowl[bowl.dots.notna()].groupby(["match_id", "team"]).agg(dots=("dots", "sum"), balls=("balls", "sum"))
        per["More dot balls bowled (share)"] = (d.dots / d.balls.replace(0, np.nan), True)
    per["Fewer wickets lost"] = (g_inn.wickets.sum(), False)
    rows = []
    wl = m[["match_id", "winner", "loser"]]
    for label, (series, more_is) in per.items():
        v = series.rename("v").reset_index()
        v.columns = ["match_id", "team", "v"]
        a = wl.merge(v.rename(columns={"team": "winner", "v": "a"}), on=["match_id", "winner"], how="left")
        a = a.merge(v.rename(columns={"team": "loser", "v": "b"}), on=["match_id", "loser"], how="left")
        a = a.fillna({"a": 0, "b": 0})
        a = a[a.a != a.b]
        if len(a):
            won = ((a.a > a.b) == more_is).sum()
            rows.append(dict(measure=label, games=len(a), won_pct=won / len(a) * 100))
    return pd.DataFrame(rows, columns=["measure", "games", "won_pct"]).sort_values("won_pct", ascending=False).reset_index(drop=True)


def expected_wins(career, ids) -> pd.DataFrame:
    """Pythagorean expected wins: each team's share of runs (per wicket in
    multi-day cricket) turned into an expected win %, with the power that fits
    these matches best.  Wins above expected = luck in close games, or knowing
    how to win them."""
    from .teamplay import games, record
    g = games(career, ids)
    if g.empty:
        return pd.DataFrame(columns=["team", "played", "won", "expected", "luck", "win_pct", "expected_pct"])
    inn = career.innings[career.innings.match_id.isin(ids)]
    multi = (g.kind == "multi").mean() > 0.5
    rows = []
    for team, t in g.groupby("team"):
        mine = inn[inn.match_id.isin(t.match_id)]
        f, a = mine[mine.team == team], mine[mine.team != team]
        if multi:
            rf, ra = f.runs.sum() / max(f.wickets.sum(), 1), a.runs.sum() / max(a.wickets.sum(), 1)
        else:
            rf, ra = f.runs.sum(), a.runs.sum()
        rec = record(t)
        rows.append(dict(team=team, played=rec["played"], decided=rec["decided"], won=rec["won"],
                         win_pct=rec["win_pct"], rf=rf, ra=ra))
    d = pd.DataFrame(rows)
    ratio = d.rf / d.ra.replace(0, np.nan)
    best, err = 2.0, np.inf
    for k in np.arange(1, 20.5, 0.5):
        e = ratio ** k / (1 + ratio ** k) * 100
        se = ((e - d.win_pct) ** 2 * d.decided).sum()
        if se < err:
            best, err = k, se
    d["expected_pct"] = ratio ** best / (1 + ratio ** best) * 100
    d["expected"] = d.expected_pct / 100 * d.decided
    d["luck"] = d.won - d.expected
    d.attrs["power"] = best
    return d.sort_values("luck", ascending=False).reset_index(drop=True)[
        ["team", "played", "decided", "won", "expected", "luck", "win_pct", "expected_pct"]]


# --------------------------------------------------------------------------- #
# 44 · match-winners · 45 · dependence
# --------------------------------------------------------------------------- #


def match_winners(career, ids) -> pd.DataFrame:
    """In every win, the player with the most impact points for the winners (see
    `impact`).  Per player: how many wins they were the main man in, and their
    share of their team's wins."""
    imp = impact(career, ids)
    m = career.matches[career.matches.match_id.isin(ids) & (career.matches.winner != "")]
    w = imp.merge(m[["match_id", "winner"]], on="match_id")
    w = w[w.team == w.winner]
    top = w.sort_values("points", ascending=False).groupby("match_id").head(1)
    wins = m.groupby("winner").size()
    g = top.groupby(["player", "team"]).agg(match_winning=("match_id", "size")).reset_index()
    g["team_wins"] = g.team.map(wins).fillna(0).astype(int)
    g["share"] = g.match_winning / g.team_wins.replace(0, np.nan) * 100
    return g.sort_values(["match_winning", "share"], ascending=False).reset_index(drop=True)


def dependence(career, ids, min_games: int = 5) -> pd.DataFrame:
    """For every team, its most important player: team win % when they made a big
    score or took a haul ('fired': 50+ or 3+ wickets in T20, 50+ or 4+ in one-day,
    100+ or 5+ in Tests) against when they didn't.  A big gap means the team leans
    on them."""
    kind = kind_of_ids(career, ids)
    bar = bars_for(kind)
    multi = kind == "multi"
    out = _outcomes(career, ids)
    played = _matches_of(career, ids)
    played = played.assign(result=[out.get((a, t), "NR") for a, t in zip(played.match_id, played.team)])
    b = career.batting[career.batting.match_id.isin(ids)]
    w = career.bowling[career.bowling.match_id.isin(ids)]
    fired = set(zip(b[b.runs >= bar["big"]].match_id, b[b.runs >= bar["big"]].player)) | set(
        zip(w[w.wickets >= bar["haul"]].match_id, w[w.wickets >= bar["haul"]].player))
    played["fired"] = [(a, p) in fired for a, p in zip(played.match_id, played.player)]
    rows = []
    for (team, player), g in played.groupby(["team", "player"]):
        yes, no = g[g.fired], g[~g.fired]
        if len(g) < min_games or len(yes) < 2 or len(no) < 2:
            continue
        rows.append(dict(team=team, player=player, games=len(g), fired=len(yes), pct_fired=_win_pct(yes.result, multi),
                         pct_not=_win_pct(no.result, multi)))
    d = pd.DataFrame(rows, columns=["team", "player", "games", "fired", "pct_fired", "pct_not"])
    d["gap"] = d.pct_fired - d.pct_not
    d = d.dropna(subset=["gap"]).sort_values("gap", ascending=False)
    d = d.groupby("team").head(1).reset_index(drop=True)
    d.attrs.update(big=bar["big"], haul=bar["haul"])
    return d


# --------------------------------------------------------------------------- #
# 46 · style maps · 47 · boom or bust
# --------------------------------------------------------------------------- #


def batting_styles(bat: pd.DataFrame, base) -> pd.DataFrame:
    """Quadrant for every batter in a stat table: average v strike rate against the section's."""
    d = bat[bat.average.notna() & bat.strike_rate.notna()].copy()
    hi_a, hi_s = d.average >= base.average, d.strike_rate >= base.strike_rate
    d["style"] = np.select([hi_a & hi_s, hi_a & ~hi_s, ~hi_a & hi_s], ["Scores lots, scores fast", "Scores lots, steadily",
                                                                        "Fast but out often"], "Slow and out often")
    return d


def bowling_styles(bowl: pd.DataFrame, base) -> pd.DataFrame:
    d = bowl[bowl.strike_rate.notna() & bowl.economy.notna()].copy()
    lo_s, lo_e = d.strike_rate <= base.bowl_strike_rate, d.economy <= base.economy
    d["style"] = np.select([lo_s & lo_e, lo_s & ~lo_e, ~lo_s & lo_e], ["Wicket-taker and tight", "Wicket-taker but costly",
                                                                        "Tight but few wickets"], "Costly and few wickets")
    return d


def boom_or_bust(career, ids, min_innings: int = 8) -> pd.DataFrame:
    """How a batter's scores are spread: % of low scores (under 10) and % of big
    ones (30+ in T20, 50+ in one-day, 100+ in Tests), and how much the scores bounce
    around (spread compared with their average).  Labels: boom or bust, steady, ..."""
    kind = kind_of_ids(career, ids)
    big = bars_for(kind)["boom"]
    inn = innings(career, ids)
    rows = []
    for p, g in inn.groupby("player"):
        if len(g) < min_innings:
            continue
        mean = g.runs.mean()
        cv = g.runs.std(ddof=0) / mean if mean else np.nan
        rows.append(dict(player=p, team=g.team.iloc[-1], innings=len(g), mean=mean,
                         low_pct=(g.runs < 10).mean() * 100, big_pct=(g.runs >= big).mean() * 100, spread=cv))
    d = pd.DataFrame(rows, columns=["player", "team", "innings", "mean", "low_pct", "big_pct", "spread"])
    if d.empty:
        return d.assign(label=[])
    lo, bg = d.low_pct.median(), d.big_pct.median()
    d["label"] = np.select([(d.low_pct > lo) & (d.big_pct > bg), (d.low_pct <= lo) & (d.big_pct > bg),
                            (d.low_pct <= lo) & (d.big_pct <= bg)],
                           ["Boom or bust", "Reliable and big", "Steady, rarely big"], "Struggling")
    d.attrs.update(big=big, low_median=lo, big_median=bg)
    return d.sort_values("spread", ascending=False).reset_index(drop=True)


# --------------------------------------------------------------------------- #
# 59 · batting order helper · 60 · bowling plan · 63 · knocking on the door · 65 · pairs
# --------------------------------------------------------------------------- #

GROUPS = {"Openers (1-2)": [1, 2], "No. 3": [3], "4 and 5": [4, 5], "6 and 7": [6, 7], "8 to 11": [8, 9, 10, 11]}


def batting_order(career, ids, team: str, min_innings: int = 2) -> pd.DataFrame:
    """For a team's batters: runs per innings and strike rate in each position
    group, against the section's average batter there.  `best` is the group where
    they beat that average by most (with at least `min_innings` there)."""
    inn = innings(career, ids)
    group_of = {p: g for g, ps in GROUPS.items() for p in ps}
    inn = inn.assign(group=inn.position.map(group_of))
    base = inn.groupby("group").agg(r=("runs", "sum"), n=("runs", "size"), b=("balls", "sum"))
    base_rpi = base.r / base.n
    mine = inn[inn.team == team]
    rows = []
    for (p, grp), g in mine.groupby(["player", "group"]):
        rows.append(dict(player=p, group=grp, innings=len(g), runs=int(g.runs.sum()),
                         per_innings=g.runs.mean(), strike_rate=g.runs.sum() / max(g.balls.sum(), 1) * 100,
                         average=g.runs.sum() / max(g.out.sum(), 1),
                         vs_avg=g.runs.mean() - base_rpi.get(grp, np.nan)))
    d = pd.DataFrame(rows, columns=["player", "group", "innings", "runs", "per_innings", "strike_rate", "average", "vs_avg"])
    if d.empty:
        return d.assign(best=[])
    q = d[d.innings >= min_innings]
    best = q.sort_values("vs_avg", ascending=False).groupby("player").head(1).set_index("player").group
    # "" where no group has enough innings (not fillna: with no one qualifying the column is numbers, not text)
    d["best"] = d.player.map(lambda p: best.get(p, ""))
    d.attrs["base"] = base_rpi.to_dict()
    return d


def suggested_order(order: pd.DataFrame, recent_players: list[str] | None = None) -> pd.DataFrame:
    """Fill the batting slots from the order table: each group takes the players
    who beat the average there by most, most innings there breaking ties."""
    if order.empty:
        return pd.DataFrame(columns=["slot", "player", "group", "vs_avg", "innings"])
    slots = [("1", "Openers (1-2)"), ("2", "Openers (1-2)"), ("3", "No. 3"), ("4", "4 and 5"), ("5", "4 and 5"),
             ("6", "6 and 7"), ("7", "6 and 7")]
    pool = order if not recent_players else order[order.player.isin(recent_players)]
    pool = pool[pool.innings >= 2].sort_values(["vs_avg", "innings"], ascending=False)
    used: set[str] = set()
    rows = []
    for slot, grp in slots:
        c = pool[(pool.group == grp) & ~pool.player.isin(used)]
        if c.empty:  # nobody has batted there: the best remaining batter anywhere in the top 7
            c = pool[~pool.player.isin(used) & pool.group.isin(list(GROUPS)[:4])]
        if c.empty:
            continue
        r = c.iloc[0]
        used.add(r.player)
        rows.append(dict(slot=slot, player=r.player, group=r.group, vs_avg=r.vs_avg, innings=int(r.innings)))
    return pd.DataFrame(rows, columns=["slot", "player", "group", "vs_avg", "innings"])


def bowling_plan(career, ids, team: str, min_balls: int = 30) -> pd.DataFrame:
    """For a team's bowlers: where their wickets come from (top order 1-3, middle
    4-7, tail 8-11), economy and strike rate against the section's, and a plain tag."""
    b = career.batting[career.batting.match_id.isin(ids) & career.batting.out & (career.batting.bowler != "")]
    w = career.bowling[career.bowling.match_id.isin(ids) & (career.bowling.team == team)]
    allw = career.bowling[career.bowling.match_id.isin(ids)]
    econ0 = allw.runs.sum() / max(allw.balls.sum(), 1) * 6
    sr0 = allw.balls.sum() / max(allw.wickets.sum(), 1)
    avg0 = allw.runs.sum() / max(allw.wickets.sum(), 1)
    by_average = bars_for(kind_of_ids(career, ids))["bowl_measure"] == "average"  # Tests: cost per wicket matters
    rows = []
    for p, g in w.groupby("player"):
        if g.balls.sum() < min_balls:
            continue
        mine = b[(b.bowler == p) & (b.opposition == team)]
        top, mid, tail = (mine.position <= 3).sum(), ((mine.position >= 4) & (mine.position <= 7)).sum(), (mine.position >= 8).sum()
        wk = int(g.wickets.sum())
        econ = g.runs.sum() / g.balls.sum() * 6
        sr = g.balls.sum() / wk if wk else np.nan
        tags = []
        if wk and top / max(top + mid + tail, 1) >= 0.45 and top >= 3:
            tags.append("Top-order hunter")
        if wk and tail / max(top + mid + tail, 1) >= 0.45 and tail >= 3:
            tags.append("Tail cleaner")
        if by_average:
            avg = g.runs.sum() / wk if wk else np.inf
            tags.append("Cheap wickets" if avg <= avg0 * 0.9 else "Costly wickets" if avg >= avg0 * 1.1
                        else "Around average cost")
        else:
            tags.append("Cheap" if econ <= econ0 * 0.95 else "Costly" if econ >= econ0 * 1.05 else "Around average cost")
        if np.isfinite(sr) and sr <= sr0 * 0.9:
            tags.append("Strikes often")
        rows.append(dict(player=p, innings=len(g), balls=int(g.balls.sum()), wickets=wk, top=int(top), middle=int(mid),
                         tail=int(tail), economy=econ, strike_rate=sr, tags=" · ".join(tags)))
    d = pd.DataFrame(rows, columns=["player", "innings", "balls", "wickets", "top", "middle", "tail", "economy",
                                    "strike_rate", "tags"])
    d = d.sort_values("wickets", ascending=False).reset_index(drop=True)
    d.attrs.update(economy=econ0, strike_rate=sr0, average=avg0, by_average=by_average)
    return d


def knocking(career, ids, team: str, share: float = 0.4) -> pd.DataFrame:
    """Players who played under `share` of the team's games here but did well
    when they did: runs per innings or wickets per innings above the team's
    regulars' (more games) median."""
    tm = career.matches[career.matches.match_id.isin(ids) & ((career.matches.home == team) | (career.matches.away == team))]
    n = len(tm)
    if not n:
        return pd.DataFrame(columns=["player", "games", "runs_per_inns", "wkts_per_inns", "why"])
    b = career.batting[career.batting.match_id.isin(tm.match_id) & (career.batting.team == team)]
    w = career.bowling[career.bowling.match_id.isin(tm.match_id) & (career.bowling.team == team) & (career.bowling.balls > 0)]
    games = b.groupby("player").match_id.nunique()
    rpi = b[b.did_bat].groupby("player").runs.mean()
    wpi = w.groupby("player").wickets.mean()
    regular = games[games >= n * share].index
    # the regulars who batted (or bowled): one who never did has no figure to set the bar (all their games abandoned)
    bar_r = rpi.reindex(regular).dropna().median()
    bar_w = wpi.reindex(regular).dropna().median()
    rows = []
    for p, k in games.items():
        if k >= n * share:
            continue
        why = []
        r, wk = rpi.get(p, np.nan), wpi.get(p, np.nan)
        if np.isfinite(r) and np.isfinite(bar_r) and r > bar_r and b[(b.player == p) & b.did_bat].shape[0] >= 1:
            why.append(f"{r:.1f} runs an innings (regulars {bar_r:.1f})")
        if np.isfinite(wk) and np.isfinite(bar_w) and wk > bar_w:
            why.append(f"{wk:.1f} wickets an innings (regulars {bar_w:.1f})")
        if why:
            rows.append(dict(player=p, games=int(k), runs_per_inns=r, wkts_per_inns=wk, why=" · ".join(why)))
    return pd.DataFrame(rows, columns=["player", "games", "runs_per_inns", "wkts_per_inns", "why"]) \
        .sort_values("games", ascending=False).reset_index(drop=True)


def batting_pairs(career, ids, team: str = "", min_stands: int = 2) -> pd.DataFrame:
    """Batting partners (only stands where the scorecard tells us who batted together)."""
    from . import partnerships as P
    s = P.stands(career, ids)
    s = s[s.known]
    if team:
        s = s[s.team == team]
    s = s.assign(pair=[" & ".join(sorted([a, b])) for a, b in zip(s.batter1, s.batter2)])
    stand = bars_for(kind_of_ids(career, ids))["stand"]
    g = s.groupby(["pair", "team"]).agg(stands=("runs", "size"), runs=("runs", "sum"), best=("runs", "max"),
                                        big_stands=("runs", lambda x: int((x >= stand).sum()))).reset_index()
    g["average"] = g.runs / g.stands
    g = g[g.stands >= min_stands].sort_values("runs", ascending=False).reset_index(drop=True)
    g.attrs["stand"] = stand
    return g


def bowling_pairs(career, ids, team: str = "", min_innings: int = 3) -> pd.DataFrame:
    """Two bowlers who bowled in the same innings: their combined wickets, runs and economy."""
    w = career.bowling[career.bowling.match_id.isin(ids) & (career.bowling.balls > 0)]
    if team:
        w = w[w.team == team]
    rows = []
    for (mid, no, tm), g in w.groupby(["match_id", "innings_no", "team"]):
        ps = list(g.itertuples())
        for i in range(len(ps)):
            for j in range(i + 1, len(ps)):
                a, b = sorted([ps[i], ps[j]], key=lambda r: r.player)
                rows.append((f"{a.player} & {b.player}", tm, a.wickets + b.wickets, a.runs + b.runs, a.balls + b.balls))
    d = pd.DataFrame(rows, columns=["pair", "team", "wickets", "runs", "balls"])
    g = d.groupby(["pair", "team"]).agg(innings=("wickets", "size"), wickets=("wickets", "sum"), runs=("runs", "sum"),
                                        balls=("balls", "sum")).reset_index()
    g["per_innings"] = g.wickets / g.innings
    g["economy"] = g.runs / g.balls.replace(0, np.nan) * 6
    return g[g.innings >= min_innings].sort_values(["per_innings", "economy"], ascending=[False, True]).reset_index(drop=True)


# --------------------------------------------------------------------------- #
# 64 · record watch
# --------------------------------------------------------------------------- #


def record_watch(career, section: str) -> pd.DataFrame:
    """Records that could fall soon in a section: the all-time career runs and
    wickets (players within 15%), and this season's runs and wickets (players
    within 25% while the season is on)."""
    from .extras import season_in_progress
    m = career.matches[career.matches.section == section]
    ids = m.match_id
    b = career.batting[career.batting.match_id.isin(ids) & career.batting.did_bat]
    w = career.bowling[career.bowling.match_id.isin(ids)]
    rows = []
    for what, t in (("Career runs", b.groupby("player").runs.sum()), ("Career wickets", w.groupby("player").wickets.sum())):
        if len(t) < 2:
            continue
        t = t.sort_values(ascending=False)
        holder, best = t.index[0], t.iloc[0]
        for p, v in t.iloc[1:6].items():
            if best and v >= best * 0.85:
                rows.append(dict(record=what, holder=holder, record_value=int(best), chaser=p, now=int(v),
                                 needed=int(best - v + 1)))
    info = season_in_progress(career, section)
    if info is not None:
        cur = info[0]
        bs = b.merge(m[["match_id", "season"]], on="match_id")
        ws = w.merge(m[["match_id", "season"]], on="match_id")
        for what, col, d in (("Runs in a season", "runs", bs), ("Wickets in a season", "wickets", ws)):
            per = d.groupby(["season", "player"])[col].sum()
            past = per[per.index.get_level_values(0) != cur]
            if past.empty or cur not in per.index.get_level_values(0):
                continue
            (s_, holder), best = past.idxmax(), past.max()
            now = per.xs(cur, level=0).sort_values(ascending=False)
            for p, v in now.head(5).items():
                if best and v >= best * 0.75:
                    rows.append(dict(record=what, holder=f"{holder} ({s_})", record_value=int(best), chaser=p,
                                     now=int(v), needed=int(best - v + 1)))
    return pd.DataFrame(rows, columns=["record", "holder", "record_value", "chaser", "now", "needed"])
