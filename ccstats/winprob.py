"""Win chance from the state of a match, learnt from every finished match in the
same section.

A state is: which innings it is (1-4), whether the side batting first is the one
batting, how many wickets are down in this innings, and how far ahead the side
batting first is ("lead": its runs so far minus the other side's).  Every match
gives one state at the start of each innings and one each time a wicket fell.
The chance of an outcome in a new state is how often matches in a similar state
(same innings, same side batting, same wickets down, a lead within a few runs)
ended that way.  Multi-day games have three outcomes (won, drawn, lost); one-day
games have two (ties are shown as such).  The scorecards give no overs, so the
chance can only use runs and wickets, never balls left."""

from __future__ import annotations

from itertools import product

import numpy as np
import pandas as pd

from .stats import KIND

BAND = {"t20": 10, "one": 20, "multi": 30}  # runs either side of the lead counted as 'similar'
MIN_GAMES = 8
PRIOR_WEIGHT = 5  # small samples are pulled towards the usual result for that innings, so 9 games can't say "100%"
STATE_COLUMNS = ["match_id", "innings_no", "t1_batting", "wickets", "lead", "score", "outcome", "team1", "team2"]


def _outcome(r, team1: str) -> str:
    """W / D / L / T from the side batting first's point of view."""
    if r.winner == team1:
        return "W"
    if r.winner:
        return "L"
    if r.result_type == "draw":
        return "D"
    if r.result_type == "tie":
        if r.tiebreak_winner:
            return "W" if r.tiebreak_winner == team1 else "L"
        return "T"
    return ""


def states(career, ids) -> pd.DataFrame:
    """Every state of every finished match in these ids."""
    m = career.matches[career.matches.match_id.isin(ids) & (career.matches.result_type != "no result")]
    inn = career.innings[career.innings.match_id.isin(m.match_id)].sort_values(["match_id", "innings_no"])
    fow = career.fow[career.fow.match_id.isin(m.match_id)].sort_values(["match_id", "innings_no", "wicket"])
    falls = {k: list(zip(g.wicket, g.score)) for k, g in fow.groupby(["match_id", "innings_no"])}
    by_match = {k: g for k, g in inn.groupby("match_id")}
    rows = []
    for r in m.itertuples():
        g = by_match.get(r.match_id)
        if g is None or g.empty:
            continue
        team1 = g.team.iloc[0]
        team2 = r.away if team1 == r.home else r.home
        out = _outcome(r, team1)
        if not out:
            continue
        done = {team1: 0, team2: 0}
        for i in g.itertuples():
            t1_bat = i.team == team1
            base = done[team1] - done[team2]
            sign = 1 if t1_bat else -1
            rows.append((r.match_id, i.innings_no, t1_bat, 0, base, 0, out, team1, team2))
            for wk, sc in falls.get((r.match_id, i.innings_no), []):
                rows.append((r.match_id, i.innings_no, t1_bat, int(wk), base + sign * int(sc), int(sc), out, team1, team2))
            done[i.team] = done.get(i.team, 0) + int(i.runs)
    return pd.DataFrame(rows, columns=STATE_COLUMNS)


def kind_of_ids(career, ids) -> str:
    m = career.matches[career.matches.match_id.isin(ids)]
    return KIND.get(m.format.mode().iloc[0], "t20") if len(m) else "t20"


def _index(st_: pd.DataFrame) -> dict:
    """The states grouped by (innings, side batting) as numpy arrays, built once per table."""
    cached = st_.attrs.get("_index")
    idx = cached[1] if cached is not None and cached[0] == (len(st_), id(st_)) else None  # never a filtered copy's
    if idx is None:
        idx = {}
        codes = {"W": 0, "D": 1, "L": 2, "T": 3}
        mids = pd.factorize(st_.match_id)[0] if len(st_) else np.array([], dtype=int)
        for key, g in st_.assign(_m=mids).groupby(["innings_no", "t1_batting"]):
            idx[key] = (g.wickets.to_numpy(), g.lead.to_numpy(dtype=float), g.outcome.map(codes).to_numpy(),
                        g._m.to_numpy(), g.match_id.to_numpy())
        st_.attrs["_index"] = ((len(st_), id(st_)), idx)
    return idx


def chance(st_: pd.DataFrame, innings_no: int, t1_batting: bool, wickets: int, lead: float, kind: str,
           exclude: str | None = None) -> dict:
    """{W, D, L, T (% for the side batting first), n (matches used), band, wickets_used}."""
    empty = dict(W=np.nan, D=np.nan, L=np.nan, T=np.nan, n=0, band=BAND[kind], wickets_used=(wickets, wickets))
    grp = _index(st_).get((innings_no, bool(t1_batting)))
    if grp is None:
        return empty
    wk, ld, oc, mi, mid = grp
    keep = np.ones(len(wk), dtype=bool) if exclude is None else (mid != exclude)
    # the usual result for this innings (each match once), for pulling small samples towards
    _, first = np.unique(mi[keep], return_index=True)
    prior = np.bincount(oc[keep][first], minlength=4) / max(len(first), 1)
    band = BAND[kind]
    sel = None
    used_w = (wickets, wickets)
    for wspread in (0, 1, 2):
        pool = keep & (np.abs(wk - wickets) <= wspread)
        b = band
        for _ in range(5):
            cand = pool & (np.abs(ld - lead) <= b)
            n_matches = len(np.unique(mi[cand]))
            if n_matches >= MIN_GAMES:
                break
            b *= 1.6
        if n_matches >= MIN_GAMES:
            sel, band, used_w = cand, b, (wickets - wspread, wickets + wspread)
            break
        sel, band = cand, b
    if sel is None or not sel.any():
        return empty
    _, firsts = np.unique(mi[sel], return_index=True)  # one state per match
    outs = oc[sel][firsts]
    n = len(outs)
    c = np.bincount(outs, minlength=4)
    k = PRIOR_WEIGHT
    pc = {o: (c[i] + k * prior[i]) / (n + k) * 100 for i, o in enumerate("WDLT")}
    return dict(**pc, n=n, band=band, wickets_used=used_w)


# --------------------------------------------------------------------------- #
# 100 · the win-chance line of one match
# --------------------------------------------------------------------------- #


def _own_states(section_states: pd.DataFrame, match_id: str):
    """This match's rows of the section's states (grouped once and kept with them), or None if it isn't there."""
    groups = section_states.attrs.get("_by_match")
    if groups is None or groups[0] != len(section_states):
        groups = (len(section_states), {k: g for k, g in section_states.groupby("match_id", sort=False)})
        section_states.attrs["_by_match"] = groups
    g = groups[1].get(match_id)
    return None if g is None else g.reset_index(drop=True)


def match_line(career, match_id: str, section_states: pd.DataFrame, kind: str) -> pd.DataFrame:
    """The chance for the side batting first at the start of each innings and after every wicket of this match."""
    own = _own_states(section_states, match_id)
    if own is None:  # not one of the section's matches: work it out on its own
        own = states(career, [match_id])
    if own.empty:
        return pd.DataFrame(columns=["step", "label", "innings_no", "wickets", "score", "W", "D", "L", "T", "n"])
    rows = []
    t2 = own.team2.iloc[0]
    t1 = own.team1.iloc[0]
    for i, s in enumerate(own.itertuples()):
        ch = chance(section_states, s.innings_no, s.t1_batting, s.wickets, s.lead, kind, exclude=match_id)
        side = t1 if s.t1_batting else t2
        label = (f"Start of innings {s.innings_no} ({side})" if s.wickets == 0 else
                 f"{side} {s.score}/{s.wickets}")
        rows.append(dict(step=i, label=label, innings_no=s.innings_no, wickets=s.wickets, score=s.score, **ch))
    d = pd.DataFrame(rows)
    d.attrs.update(team1=t1, team2=t2, outcome=own.outcome.iloc[0])
    return d


def biggest_swing(line: pd.DataFrame) -> dict | None:
    """The step where the side batting first's chance moved most."""
    w = line.W.to_numpy(dtype=float)
    if len(w) < 2 or not np.isfinite(w).any():
        return None
    diffs = np.diff(np.nan_to_num(w, nan=np.nanmean(w)))
    i = int(np.argmax(np.abs(diffs)))
    return dict(at=line.label.iloc[i + 1], before=w[i], after=w[i + 1], change=diffs[i])


def lowest_for_winner(line: pd.DataFrame) -> tuple[float, str] | None:
    """The winner's lowest chance during the match (a comeback when it was low)."""
    out = line.attrs.get("outcome")
    if out not in ("W", "L") or line.empty:
        return None
    ch = line.W if out == "W" else line.L
    ch = ch.astype(float)
    if not np.isfinite(ch).any():
        return None
    i = int(np.nanargmin(ch.to_numpy()))
    return float(ch.iloc[i]), line.label.iloc[i]


# --------------------------------------------------------------------------- #
# 108 · chase calculator
# --------------------------------------------------------------------------- #


def chase_chance(st_: pd.DataFrame, kind: str, target: int, score: int, wickets: int) -> dict:
    """The chasing side's chance: last innings, target and runs so far.  One-day games:
    the 2nd innings.  Multi-day games: the 4th innings (the side batting first
    batted 1st and 3rd in the usual order)."""
    if kind == "multi":
        innings_no, t1_bat = 4, False
    else:
        innings_no, t1_bat = 2, False
    lead = (target - 1) - score  # the side batting first's runs minus the chasers'
    ch = chance(st_, innings_no, t1_bat, wickets, lead, kind)
    # from the chasing side's point of view
    return dict(win=ch["L"], draw=ch["D"], lose=ch["W"], tie=ch["T"], n=ch["n"], band=ch["band"],
                wickets_used=ch["wickets_used"])


# --------------------------------------------------------------------------- #
# 137 · first-innings lead (multi-day)
# --------------------------------------------------------------------------- #

LEAD_BANDS = [(0, 49), (50, 99), (100, 199), (200, 299), (300, None)]


def first_innings_lead(career, ids) -> pd.DataFrame:
    """For each size of first-innings lead: how often the side with the lead won, drew and lost."""
    m = career.matches[career.matches.match_id.isin(ids) & (career.matches.result_type != "no result")]
    inn = career.innings[career.innings.match_id.isin(m.match_id) & (career.innings.team_innings == 1)]
    first = inn.pivot_table(index="match_id", columns="team", values="runs", aggfunc="sum")
    rows = []
    for r in m.itertuples():
        if r.match_id not in first.index:
            continue
        a, b = first.loc[r.match_id].get(r.home, np.nan), first.loc[r.match_id].get(r.away, np.nan)
        if not (np.isfinite(a) and np.isfinite(b)) or a == b:
            continue
        leader, lead = (r.home, a - b) if a > b else (r.away, b - a)
        out = "W" if r.winner == leader else "L" if r.winner else "D" if r.result_type == "draw" else "T"
        rows.append((leader, lead, out))
    d = pd.DataFrame(rows, columns=["leader", "lead", "outcome"])
    out = []
    for lo, hi in LEAD_BANDS:
        x = d[(d.lead >= lo) & ((d.lead <= hi) if hi is not None else True)]
        n = len(x)
        c = x.outcome.value_counts()
        out.append(dict(band=f"{lo}+" if hi is None else f"{lo}–{hi}", matches=n,
                        won=c.get("W", 0) / n * 100 if n else np.nan, drawn=c.get("D", 0) / n * 100 if n else np.nan,
                        lost=c.get("L", 0) / n * 100 if n else np.nan))
    return pd.DataFrame(out)


# --------------------------------------------------------------------------- #
# 110 · predicted result · 125 · series predictor
# --------------------------------------------------------------------------- #


def draw_rate(career, ids) -> float:
    m = career.matches[career.matches.match_id.isin(ids) & (career.matches.result_type != "no result")]
    return float((m.result_type == "draw").mean()) if len(m) else 0.0


def predict(career, ids, mine: str, opp: str, venue: str = "neutral") -> dict:
    """A chance for each side (and a draw in multi-day cricket), built in steps
    that are all shown: Elo ratings, then recent form, head to head, and home
    ground, each nudge capped so none can swing it far on its own."""
    from . import teamplay as TP
    from .rankings import team_elo
    m = career.matches[career.matches.match_id.isin(ids)]
    steps = []
    secs = m.section.unique()
    ra = rb = 1500.0
    if len(secs) == 1:
        table, _ = team_elo(career, secs[0])
        e = table.set_index("team").elo
        ra, rb = float(e.get(mine, 1500.0)), float(e.get(opp, 1500.0))
    p = 1 / (1 + 10 ** ((rb - ra) / 400))
    steps.append(("Ratings", f"Elo {ra:.0f} v {rb:.0f}", p * 100))
    g = TP.games(career, ids)
    last = {t: g[g.team == t].tail(5) for t in (mine, opp)}
    wa, wb = int((last[mine].outcome == "W").sum()), int((last[opp].outcome == "W").sum())
    adj = float(np.clip((wa - wb) * 0.015, -0.06, 0.06))
    p = float(np.clip(p + adj, 0.03, 0.97))
    steps.append(("Form", f"won {wa} of their last {len(last[mine])} v {wb} of {len(last[opp])}", adj * 100))
    h = g[(g.team == mine) & (g.opponent == opp)]
    hrec = TP.record(h)
    if hrec["decided"] >= 3 and np.isfinite(hrec["win_pct"]):
        adj = float(np.clip((hrec["win_pct"] - 50) / 100 * 0.1, -0.05, 0.05))
        p = float(np.clip(p + adj, 0.03, 0.97))
        steps.append(("Head to head", f"{TP.wdl(hrec)} in {hrec['played']} meetings", adj * 100))
    if venue in ("home", "away"):
        home = g[(g.venue == "home")]
        hw = TP.record(home)["win_pct"]
        adv = (hw - 50) / 100 if np.isfinite(hw) else 0.0
        adj = float(np.clip(adv * 0.5 * (1 if venue == "home" else -1), -0.06, 0.06))
        p = float(np.clip(p + adj, 0.03, 0.97))
        steps.append(("Venue", f"{'at home' if venue == 'home' else 'away'} (home sides win {hw:.0f}% here)", adj * 100))
    multi = TP.is_multi(g)
    d = draw_rate(career, ids) if multi else 0.0
    return dict(win=p * (1 - d) * 100, draw=d * 100, lose=(1 - p) * (1 - d) * 100, steps=steps, multi=multi)


def series_odds(p_win: float, p_draw: float, wins_a: int, wins_b: int, left: int) -> dict:
    """Chance of each series result with `left` games to play, each game won by A
    with p_win, drawn with p_draw (exact, every combination of the remaining games)."""
    p_lose = max(0.0, 1 - p_win - p_draw)
    out = {"A": 0.0, "B": 0.0, "level": 0.0}
    for combo in product("WDL", repeat=max(left, 0)):
        pr = 1.0
        a, b = wins_a, wins_b
        for c in combo:
            pr *= {"W": p_win, "D": p_draw, "L": p_lose}[c]
            a += c == "W"
            b += c == "L"
        out["A" if a > b else "B" if b > a else "level"] += pr
    return {k: v * 100 for k, v in out.items()}


# --------------------------------------------------------------------------- #
# 102 · match rating · 101 · match report
# --------------------------------------------------------------------------- #


def match_rating(career, match_id: str, line: pd.DataFrame | None = None) -> tuple[float, list[str]]:
    """0-10 for how exciting a match was, with the reasons."""
    from .stats import bars_for
    r = career.matches.set_index("match_id").loc[match_id]
    kind = KIND.get(r.format, "t20")
    bar = bars_for(kind)
    pts, why = 0.0, []
    if r.result_type == "tie" or r.super_over:
        pts += 3.5
        why.append("tied" + (" and a super over" if r.super_over else ""))
    elif pd.notna(r.margin_runs) and r.winner:
        close = bar["close_runs"]
        if r.margin_runs < close:
            pts += 3 * (1 - r.margin_runs / close) + 1
            why.append(f"won by only {int(r.margin_runs)} run{'s' if r.margin_runs != 1 else ''}")
    elif pd.notna(r.margin_wickets) and r.winner and r.margin_wickets <= 2:
        pts += 3 if r.margin_wickets == 1 else 2
        why.append(f"won by {int(r.margin_wickets)} wicket{'s' if r.margin_wickets > 1 else ''}")
    if r.result_type == "draw":
        inn = career.innings[career.innings.match_id == match_id].sort_values("innings_no")
        if len(inn) == 4 and inn.wickets.iloc[-1] >= 8:
            pts += 3
            why.append(f"drawn with {int(inn.wickets.iloc[-1])} down")
    if line is not None:
        low = lowest_for_winner(line)
        if low and np.isfinite(low[0]) and low[0] < 30:
            pts += 2.5 * (1 - low[0] / 30)
            why.append(f"a comeback from {low[0]:.0f}% at {low[1]}")
    if r.knockout:
        pts += 2 if r.stage == "Final" else 1
        why.append("a final" if r.stage == "Final" else "a knockout")
    b = career.batting[(career.batting.match_id == match_id)]
    w = career.bowling[career.bowling.match_id == match_id]
    if (b.runs >= 100).any():
        pts += 0.5
        why.append("a hundred")
    if (w.wickets >= bar["headline_haul"]).any():
        pts += 0.5
        why.append(f"a {int(w.wickets.max())}-wicket haul")
    inn = career.innings[career.innings.match_id == match_id]
    if kind != "multi" and len(inn) == 2 and inn.runs.min() >= (180 if kind == "t20" else 320):
        pts += 1
        why.append("both sides scored big")
    return float(min(10.0, round(pts, 1))), why


def match_report(career, match_id: str, line: pd.DataFrame | None = None) -> str:
    """A few sentences on how the match went, from its facts."""
    from . import partnerships as P
    from .analysis import collapses
    r = career.matches.set_index("match_id").loc[match_id]
    inn = career.innings[career.innings.match_id == match_id].sort_values("innings_no")
    if inn.empty:
        return ""
    bat = career.batting[(career.batting.match_id == match_id) & career.batting.did_bat]
    bowl = career.bowling[career.bowling.match_id == match_id]
    stands = P.stands(career, [match_id])
    sents = []
    first = inn.iloc[0]

    def tot(i):
        return f"{i.runs}" if i.all_out else f"{i.runs}/{i.wickets}{' declared' if i.declared else ''}"

    # the first innings: a collapse and recovery, or a big score
    col = collapses(career, [match_id], first.team)
    col = col[col.innings_no == first.innings_no]
    big = stands[(stands.innings_no == first.innings_no)].sort_values("runs", ascending=False).head(1)
    top1 = bat[bat.innings_no == first.innings_no].sort_values("runs", ascending=False).head(1)
    s = f"{first.team} made {tot(first)}"
    lead_by = (f", led by {top1.player.iloc[0]}'s {top1.runs.iloc[0]}{'' if top1.out.iloc[0] else '*'}"
               if len(top1) and top1.runs.iloc[0] >= 30 else "")
    if len(col):
        c0 = col.iloc[0]
        end_score = int(c0.to_score.split("/")[0])
        if end_score >= first.runs - 5:  # the slide came at the very end of the innings
            s += f"{lead_by}, losing {c0.wickets} wickets for {c0.runs} at the end"
        else:
            s += f" after sliding from {c0.from_score} to {c0.to_score}"
            if len(big) and big.runs.iloc[0] >= 50 and big.end.iloc[0] > end_score:
                b0 = big.iloc[0]
                s += (f", rescued by a {b0.runs}-run stand between {b0.batter1} and {b0.batter2}" if b0.known
                      else f", rescued by a {b0.runs}-run stand")
    else:
        s += lead_by
    sents.append(s + ".")
    # the best bowling of the match
    wb = bowl.groupby(["player", "team"])[["wickets", "runs"]].sum().reset_index().sort_values(
        ["wickets", "runs"], ascending=[False, True])
    if len(wb) and wb.wickets.iloc[0] >= 3:
        x = wb.iloc[0]
        sents.append(f"{x.player} took {int(x.wickets)}/{int(x.runs)} for {x.team}.")
    # the rest of the innings
    for i in inn.iloc[1:].itertuples():
        t = bat[bat.innings_no == i.innings_no].sort_values("runs", ascending=False).head(1)
        lead = f", led by {t.player.iloc[0]}'s {t.runs.iloc[0]}{'' if t.out.iloc[0] else '*'}" if len(t) and t.runs.iloc[0] >= 30 else ""
        sents.append(f"{i.team} replied with {tot(i)}{lead}." if i.innings_no == 2 else f"{i.team} then made {tot(i)}{lead}.")
    # the result, and the turning point
    res = r.result
    if line is not None and len(line) > 2:
        sw = biggest_swing(line)
        if sw and abs(sw["change"]) >= 15:
            team1 = line.attrs["team1"]
            poss = team1 + ("'" if team1.endswith("s") else "'s")
            sents.append(f"The turning point came at {sw['at']}: {poss} chance went from {sw['before']:.0f}% to "
                         f"{sw['after']:.0f}%.")
    sents.append(f"{res}." if not res.endswith(".") else res)
    if r.player_of_match:
        sents.append(f"Player of the Match: {r.player_of_match}.")
    if r.series_id:
        sm = career.matches[(career.matches.series_id == r.series_id) & (career.matches.date <= r.date)]
        a, b = r.home, r.away
        wa, wb_ = int((sm.winner == a).sum()), int((sm.winner == b).sum())
        if len(sm) > 1 or (pd.notna(r.series_length) and r.series_length > 1):
            lead_ = (f"{a} lead the series {wa}–{wb_}" if wa > wb_ else f"{b} lead the series {wb_}–{wa}" if wb_ > wa
                     else f"the series is level at {wa}–{wb_}")
            sents.append(lead_[0].upper() + lead_[1:] + ".")
    return " ".join(sents)


def best_matches(career, ids, top: int = 15) -> pd.DataFrame:
    """Every match in these ids rated for excitement, best first."""
    m = career.matches[career.matches.match_id.isin(ids)]
    if m.empty:
        return pd.DataFrame(columns=["match_id", "date", "home", "away", "result", "rating", "why"])
    kind = kind_of_ids(career, ids)
    st_ = states(career, ids)
    rows = []
    for r in m.itertuples():
        line = match_line(career, r.match_id, st_, kind)
        score, why = match_rating(career, r.match_id, line)
        rows.append(dict(match_id=r.match_id, date=r.date, home=r.home, away=r.away, result=r.result, stage=r.stage,
                         rating=score, why=", ".join(why)))
    return pd.DataFrame(rows).sort_values(["rating", "date"], ascending=[False, False]).head(top).reset_index(drop=True)


def comebacks(career, ids, team: str = "", below: float = 25.0) -> pd.DataFrame:
    """Wins where the winner's chance fell under `below` % at some point."""
    m = career.matches[career.matches.match_id.isin(ids) & (career.matches.winner != "")]
    if team:
        m = m[m.winner == team]
    kind = kind_of_ids(career, ids)
    st_ = states(career, ids)
    rows = []
    for r in m.itertuples():
        line = match_line(career, r.match_id, st_, kind)
        low = lowest_for_winner(line)
        if low and np.isfinite(low[0]) and low[0] < below:
            rows.append(dict(match_id=r.match_id, date=r.date, winner=r.winner, loser=r.loser, low=low[0], at=low[1],
                             result=r.result))
    return pd.DataFrame(rows, columns=["match_id", "date", "winner", "loser", "low", "at", "result"]).sort_values("low") \
        .reset_index(drop=True)
