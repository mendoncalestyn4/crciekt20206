"""Attributes out of 20, the way Football Manager shows a player, and a scout's report in words.

Each attribute is where the player ranks among everyone with enough cricket in the same competition (Tests with
Tests, the Ranji Trophy with itself; never across formats): 20 the best there, 10 the middle, 1 the worst. A short
record is settled before it's ranked (a few dismissals, wickets or innings at the usual level there added, as everywhere
on the site), so seven good innings can't top a list built on thirty; the words show the numbers as they are.

Batting (batters with 8 innings in first-class cricket, 5 in white-ball cricket):
- Run-scoring: the average.
- Tempo: the strike rate.
- Boundary hitting: runs from fours and sixes per 100 balls.
- Consistency: how often they pass a decent score (50 first-class, 30 one-day, 20 T20).
- Big scores: of the innings past that decent score, how many go on to a big one (100 first-class, 50 white-ball);
  not rated until there are two such innings.
- Against the best: the average against the stronger half of the teams there.

Bowling (bowlers with 100 overs in first-class cricket, 30 in one-day, 15 in T20):
- Wicket-taking: balls per wicket.
- Control: runs per over.
- Pressure: dot balls (white-ball scorecards print them) or maidens (first-class ones print those).
- Top-order hunter: the share of their wickets that are the top three (rated from three wickets).
- Match-winning spells: hauls (3 wickets in T20, 4 in one-day, 5 in first-class) per innings bowled.
- Against the best: the bowling average against the stronger half.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .analysis import role_labels, team_strength
from .players import SHRINK
from .stats import KIND, bars_for

ENOUGH_INNS = {"multi": 8, "one": 5, "t20": 5}
ENOUGH_BALLS = {"multi": 600, "one": 180, "t20": 90}
SETTLE_INNS = 5          # innings (or wickets) at the usual rate added to a share before ranking it
SETTLE_STARTS = 3        # decent scores at the usual rate added before ranking how often they become big ones
MIN_STARTS = 2           # decent scores needed before "Big scores" is rated at all
MIN_WICKETS = 3          # wickets needed before "Top-order hunter" is rated at all

BAT = ["Run-scoring", "Tempo", "Boundary hitting", "Consistency", "Big scores", "Against the best"]
BOWL = ["Wicket-taking", "Control", "Pressure", "Top-order hunter", "Match-winning spells", "Against the best"]
WHERE = {"Openers (1-2)": "when opening", "No. 3": "at number 3", "4 and 5": "at 4 or 5", "6 and 7": "at 6 or 7",
         "8 to 11": "at 8 or lower"}


def _memo(career, key, make):
    stamp = (id(career.matches), len(career.matches))
    box = getattr(career, "_attributes", None)
    if box is None or box.get("_stamp") != stamp:
        box = {"_stamp": stamp}
        try:
            career._attributes = box
        except AttributeError:
            return make()
    if key not in box:
        box[key] = make()
    return box[key]


def _score(values: pd.Series, lower_better: bool) -> pd.Series:
    """1-20 from the rank among everyone (the middle of a tie), 20 the best."""
    p = values.rank(pct=True, method="average", ascending=not lower_better)
    return np.clip(np.ceil(p * 20), 1, 20).astype(int)


def _settle(num: pd.Series, den: pd.Series, k: float) -> pd.Series:
    """num/den with k of den added at the pool's own rate."""
    rate = num.sum() / max(den.sum(), 1e-9)
    return (num + k * rate) / (den + k)


def table(career, section: str) -> dict:
    """Every qualified batter's and bowler's attributes in one competition: {"bat": frame, "bowl": frame, "kind"}.
    Each frame has the attribute scores (1-20), the numbers behind them, and the innings or balls they rest on."""
    return _memo(career, ("table", section), lambda: _table(career, section))


def _table(career, section: str) -> dict:
    m = career.matches[career.matches.section == section]
    kind = KIND.get(m.format.mode().iloc[0], "t20") if len(m) else "t20"
    bars = bars_for(kind)
    ids = set(m.match_id)
    strength = team_strength(career, list(ids))
    median = float(np.median(list(strength.values()))) if strength else 0.0
    strong = {t for t, v in strength.items() if v > median}
    opp = {}
    for r in m.itertuples():
        opp[(r.match_id, r.home)], opp[(r.match_id, r.away)] = r.away, r.home

    # ---------------------------------------------------------------- batting
    b = career.batting[career.batting.match_id.isin(ids) & career.batting.did_bat].copy()
    b["opp"] = [opp.get(k) for k in zip(b.match_id, b.team)]
    b["vs_strong"] = b.opp.isin(strong)
    b["decent"] = b.runs >= bars["decent"]
    b["big"] = b.runs >= bars["big"]
    b["boundary_runs"] = 4 * b.fours + 6 * b.sixes
    g = b.groupby("player")
    bt = g.agg(innings=("runs", "size"), runs=("runs", "sum"), outs=("out", "sum"), balls=("balls", "sum"),
               boundary_runs=("boundary_runs", "sum"), decent=("decent", "sum"), big=("big", "sum"))
    s = b[b.vs_strong].groupby("player").agg(s_runs=("runs", "sum"), s_outs=("out", "sum"))
    bt = bt.join(s).fillna({"s_runs": 0, "s_outs": 0})
    bt = bt[bt.innings >= ENOUGH_INNS[kind]]
    k = SHRINK[kind]
    if len(bt):
        avg = bt.runs.sum() / max(bt.outs.sum(), 1)
        bt["average"] = (bt.runs + k * avg) / (bt.outs + k)
        bt["strike_rate"] = bt.runs / bt.balls.replace(0, np.nan) * 100
        bt["boundary_per_100"] = bt.boundary_runs / bt.balls.replace(0, np.nan) * 100
        bt["decent_pct"] = _settle(bt.decent, bt.innings, SETTLE_INNS) * 100
        bt["big_pct"] = _settle(bt.big, bt.decent, SETTLE_STARTS) * 100
        s_avg = bt.s_runs.sum() / max(bt.s_outs.sum(), 1)
        bt["strong_average"] = (bt.s_runs + k * s_avg) / (bt.s_outs + k)
        # as they are, for the words (the settled ones only decide the rank)
        bt["raw_average"] = bt.runs / bt.outs.replace(0, np.nan)
        bt["raw_strong"] = bt.s_runs / bt.s_outs.replace(0, np.nan)
        for name, col in zip(BAT, ["average", "strike_rate", "boundary_per_100", "decent_pct", "big_pct", "strong_average"]):
            bt[name] = _score(bt[col].fillna(0), False).astype(float)
        # too few starts to say how often they become big scores: no score rather than the pool's own rate
        bt.loc[bt.decent < MIN_STARTS, "Big scores"] = np.nan
        bt["overall"] = bt[BAT].mean(axis=1)

    # ---------------------------------------------------------------- bowling
    w = career.bowling[career.bowling.match_id.isin(ids) & (career.bowling.balls > 0)].copy()
    w["opp"] = [opp.get(k) for k in zip(w.match_id, w.team)]
    w["vs_strong"] = w.opp.isin(strong)
    w["haul"] = w.wickets >= bars["haul"]
    gw = w.groupby("player")
    wt = gw.agg(innings=("balls", "size"), balls=("balls", "sum"), runs=("runs", "sum"), wickets=("wickets", "sum"),
                hauls=("haul", "sum"))
    dots = w.dots.notna().mean() > 0.5 if "dots" in w else False
    if dots:
        wt = wt.join(w.groupby("player").dots.sum().rename("pressure_n"))
    else:
        wt = wt.join(w.groupby("player").maidens.sum().rename("pressure_n"))
    sw = w[w.vs_strong].groupby("player").agg(s_runs=("runs", "sum"), s_wkts=("wickets", "sum"))
    wt = wt.join(sw).fillna({"s_runs": 0, "s_wkts": 0, "pressure_n": 0})
    top3 = career.batting[career.batting.match_id.isin(ids) & career.batting.out & (career.batting.bowler != "")]
    wt = wt.join(top3[top3.position <= 3].groupby("bowler").size().rename("top3")).fillna({"top3": 0})
    wt = wt[wt.balls >= ENOUGH_BALLS[kind]]
    if len(wt):
        b_avg = wt.runs.sum() / max(wt.wickets.sum(), 1)
        b_sr = wt.balls.sum() / max(wt.wickets.sum(), 1)
        wt["bowl_average"] = (wt.runs + k * b_avg) / (wt.wickets + k)
        wt["balls_per_wicket"] = (wt.balls + k * b_sr) / (wt.wickets + k)
        wt["economy"] = wt.runs / wt.balls * 6
        overs = wt.balls / 6
        wt["pressure"] = (wt.pressure_n / wt.balls * 100) if dots else (wt.pressure_n / overs * 100)
        wt["top3_pct"] = _settle(wt.top3, wt.wickets, SETTLE_INNS) * 100
        wt["haul_pct"] = _settle(wt.hauls, wt.innings, SETTLE_INNS) * 100
        s_avg = wt.s_runs.sum() / max(wt.s_wkts.sum(), 1)
        wt["strong_average"] = (wt.s_runs + k * s_avg) / (wt.s_wkts + k)
        wt["raw_bpw"] = wt.balls / wt.wickets.replace(0, np.nan)
        wt["raw_strong"] = wt.s_runs / wt.s_wkts.replace(0, np.nan)
        for name, col, low in zip(BOWL, ["balls_per_wicket", "economy", "pressure", "top3_pct", "haul_pct", "strong_average"],
                                  [True, True, False, False, False, True]):
            wt[name] = _score(wt[col].fillna(wt[col].median()), low).astype(float)
        wt.loc[wt.wickets < MIN_WICKETS, "Top-order hunter"] = np.nan
        wt["overall"] = wt[BOWL].mean(axis=1)
    return dict(bat=bt, bowl=wt, kind=kind, dots=bool(dots), strong=sorted(strong), bars=bars)


def _text(name: str, r, t: dict) -> str:
    """The number behind an attribute, in words."""
    bars = t["bars"]

    def num(v, d=1, none="–"):
        return none if v is None or not np.isfinite(v) else f"{v:.{d}f}"
    words = {
        "Run-scoring": lambda: f"average {num(r.raw_average, none='never out')}",
        "Tempo": lambda: f"strike rate {r.strike_rate:.0f}",
        "Boundary hitting": lambda: f"{r.boundary_per_100:.0f} runs in fours and sixes per 100 balls",
        "Consistency": lambda: f"passes {bars['decent']} in {r.decent / r.innings * 100:.0f}% of innings",
        "Big scores": lambda: (f"{int(r.big)} of their {int(r.decent)} scores of {bars['decent']}+ went on to {bars['big']}"
                               if r.decent else f"no score of {bars['decent']}+ yet"),
        "bat:Against the best": lambda: f"average {num(r.raw_strong)} against the stronger half",
        "Wicket-taking": lambda: (f"a wicket every {num(r.raw_bpw, 0)} balls" if np.isfinite(r.raw_bpw) else "no wicket yet"),
        "Control": lambda: f"{r.economy:.2f} runs an over",
        "Pressure": lambda: f"{r.pressure:.0f}% dot balls" if t["dots"] else f"{r.pressure:.0f} maidens per 100 overs",
        "Top-order hunter": lambda: f"{int(r.top3)} of their {int(r.wickets)} wickets are the top three",
        "Match-winning spells": lambda: f"{bars['haul']}+ wickets in {int(r.hauls)} of {int(r.innings)} innings",
        "bowl:Against the best": lambda: f"average {num(r.raw_strong)} against the stronger half",
    }
    return words[name]()


def player(career, section: str, name: str) -> dict:
    """One player's attributes in one competition: {"bat": [...], "bowl": [...], "bat_overall", "bowl_overall",
    "pool": {...}, "short": why there's none}; each attribute {name, score, text}."""
    t = table(career, section)
    out: dict = dict(section=section, kind=t["kind"], bat=[], bowl=[], bat_overall=None, bowl_overall=None,
                     pool=dict(bat=int(len(t["bat"])), bowl=int(len(t["bowl"]))), short={})
    for job, names in (("bat", BAT), ("bowl", BOWL)):
        frame = t[job]
        if name in frame.index:
            r = frame.loc[name]
            out[job] = [dict(name=n, score=None if pd.isna(r[n]) else int(r[n]),
                             text=_text(f"{job}:{n}" if n == "Against the best" else n, r, t)) for n in names]
            out[f"{job}_overall"] = round(float(r.overall), 1)
    m = career.matches[career.matches.section == section]
    ids = set(m.match_id)
    inns = int((career.batting.match_id.isin(ids) & career.batting.did_bat & (career.batting.player == name)).sum())
    balls = int(career.bowling[career.bowling.match_id.isin(ids) & (career.bowling.player == name)].balls.sum())
    if not out["bat"] and inns:
        out["short"]["bat"] = f"{inns} of the {ENOUGH_INNS[t['kind']]} innings needed"
    if not out["bowl"] and balls:
        out["short"]["bowl"] = f"{balls // 6} of the {ENOUGH_BALLS[t['kind']] // 6} overs needed"
    return out


STRONG = {"Run-scoring": "scores heavily", "Tempo": "scores quickly", "Boundary hitting": "clears the rope and finds the fence",
          "Consistency": "gets going almost every time", "Big scores": "turns starts into big scores",
          "bat:Against the best": "scores against the best sides", "Wicket-taking": "takes wickets often",
          "Control": "hard to score off", "Pressure": "builds pressure", "Top-order hunter": "gets the top order out",
          "Match-winning spells": "wins matches with big hauls", "bowl:Against the best": "does it against the best sides"}
WEAK = {"Run-scoring": "doesn't score enough", "Tempo": "slow scorer", "Boundary hitting": "rarely finds the boundary",
        "Consistency": "too often out cheaply", "Big scores": "gets in, then gets out",
        "bat:Against the best": "struggles against the best sides", "Wicket-taking": "goes long spells without a wicket",
        "Control": "expensive", "Pressure": "lets the batters off the hook", "Top-order hunter": "mostly gets the tail out",
        "Match-winning spells": "rarely takes a big haul", "bowl:Against the best": "struggles against the best sides"}


def scout_report(career, section: str, name: str) -> dict:
    """A scout's report in words, from the attributes and a few facts: the verdict, strengths (15 or more out of
    20), weaknesses (6 or less), and what to watch for."""
    a = player(career, section, name)
    t = table(career, section)
    jobs = [j for j in ("bat", "bowl") if a[j]]
    if not jobs:
        return dict(verdict="", strengths=[], weaknesses=[], notes=[],
                    none=f"Not enough cricket in {section} yet for a report.")
    # the main job: the better overall, and bowling for anyone who bowls a lot and bats low
    main = max(jobs, key=lambda j: a[f"{j}_overall"])
    roles = role_labels(career, career.matches[career.matches.section == section].match_id, t["kind"]).set_index("player")
    role = roles.role.get(name, "") if name in roles.index else ""
    if role == "Bowler" and "bowl" in jobs:
        main = "bowl"
    ov = a[f"{main}_overall"]
    who = {"bat": "batter", "bowl": "bowler"}[main]
    if "bat" in jobs and "bowl" in jobs and (role == "All-rounder" or min(a["bat_overall"], a["bowl_overall"]) >= 11):
        who = "all-rounder"
        ov = (a["bat_overall"] + a["bowl_overall"]) / 2
    verdict = (f"One of the best {who}s in {section}" if ov >= 15 else f"A good, reliable {who} at this level" if ov >= 12
               else f"A squad {who}: does a job in {section}" if ov >= 8 else f"Struggling as a {who} at this level")
    strengths, weaknesses = [], []
    for job in jobs:
        for x in a[job]:
            key = f"{job}:{x['name']}" if x["name"] == "Against the best" else x["name"]
            if x["score"] is None:
                continue
            if x["score"] >= 15:
                strengths.append((x["score"], f"{STRONG[key].capitalize()} ({x['text']}, {x['score']}/20)"))
            elif x["score"] <= 6 and (job == main or who == "all-rounder"):
                weaknesses.append((-x["score"], f"{WEAK[key].capitalize()} ({x['text']}, {x['score']}/20)"))
    notes = []
    ids = career.matches[career.matches.section == section].match_id
    if "bat" in jobs and (main == "bat" or who == "all-rounder"):
        from .analysis import nemesis, position_record
        n = nemesis(career, ids, name)
        if len(n) and n.dismissals.iloc[0] >= 3:
            notes.append(f"Has fallen to {n.bowler.iloc[0]} {int(n.dismissals.iloc[0])} times: keep them apart.")
        pr = position_record(career, ids, name)
        pr = pr[pr.innings >= 3].assign(edge=lambda d: d.average - d.section_average).dropna(subset=["edge"])
        if len(pr) > 1:
            top = pr.sort_values("edge", ascending=False).iloc[0]
            notes.append(f"Best {WHERE.get(top.group, top.group)}: average {top.average:.1f} there in "
                         f"{top.innings:.0f} innings, against {top.section_average:.1f} for the average batter there.")
    return dict(verdict=verdict + ".", role=role, overall=round(ov, 1), main=main,
                strengths=[s for _, s in sorted(strengths, reverse=True)[:3]],
                weaknesses=[s for _, s in sorted(weaknesses, reverse=True)[:2]], notes=notes[:2], none="")
