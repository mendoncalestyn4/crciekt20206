"""Deeper team numbers, with format-specific rules: how dominant the wins are,
separate batting and bowling ratings, clutch players, partnership chemistry,
strike-rate pressure, home fortresses, squad changes, Test second innings and
fourth-innings chases, and Test bowlers' match pattern."""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import teamplay as TP
from .players import innings, kind_of_ids, spells
from .stats import KIND, bars_for

# --------------------------------------------------------------------------- #
# 96 · dominance
# --------------------------------------------------------------------------- #


def margin_class(r, kind: str) -> str:
    """'thrashing' / 'comfortable' / 'scrape' for a result with a winner (format bars)."""
    b = bars_for(kind)
    if r.innings_win:
        return "thrashing"
    if pd.notna(r.margin_runs):
        if r.margin_runs >= b["thrash_runs"]:
            return "thrashing"
        if r.margin_runs < b["close_runs"]:
            return "scrape"
        return "comfortable"
    if pd.notna(r.margin_wickets):
        if r.margin_wickets >= b["thrash_wkts"]:
            return "thrashing"
        if r.margin_wickets <= 2:
            return "scrape"
        return "comfortable"
    return "scrape"  # won a tie on a super over


def dominance(career, ids) -> pd.DataFrame:
    """One row per team: wins and defeats split into thrashings, comfortable and
    scrapes (by the format's bars), plus draws and ties."""
    m = career.matches[career.matches.match_id.isin(ids)]
    rows = []
    for r in m.itertuples():
        kind = KIND.get(r.format, "t20")
        winner = r.winner or r.tiebreak_winner
        for team in (r.home, r.away):
            if winner:
                cls = margin_class(r, kind)
                rows.append((team, ("won_" if winner == team else "lost_") + cls))
            elif r.result_type == "draw":
                rows.append((team, "drawn"))
            elif r.result_type == "tie":
                rows.append((team, "tied"))
    d = pd.DataFrame(rows, columns=["team", "what"])
    t = d.groupby(["team", "what"]).size().unstack(fill_value=0)
    for c in ("won_thrashing", "won_comfortable", "won_scrape", "lost_thrashing", "lost_comfortable", "lost_scrape",
              "drawn", "tied"):
        if c not in t:
            t[c] = 0
    t["won"] = t.won_thrashing + t.won_comfortable + t.won_scrape
    t["lost"] = t.lost_thrashing + t.lost_comfortable + t.lost_scrape
    # +1 for each thrashing, -1 for each heavy defeat, per game played
    t["index"] = (t.won_thrashing - t.lost_thrashing) / (t.won + t.lost + t.drawn + t.tied).replace(0, np.nan) * 100
    return t.reset_index().sort_values("index", ascending=False).reset_index(drop=True)


# --------------------------------------------------------------------------- #
# 99 · batting and bowling ratings
# --------------------------------------------------------------------------- #

DECAY = 0.85  # each match counts this much of the one after it


def unit_ratings(career, ids) -> pd.DataFrame:
    """A batting and a bowling rating for every team (1000 = average).

    Each match, the team's runs per wicket is compared with what that opponent's
    bowlers usually allow (and its run rate with the opponent's usual economy in
    white-ball cricket, averaged with the runs per wicket).  Bowling is the same
    the other way round.  Recent matches count most."""
    m = career.matches[career.matches.match_id.isin(ids)].sort_values(["date", "match_id"])
    inn = career.innings[career.innings.match_id.isin(m.match_id)]
    if inn.empty:
        return pd.DataFrame(columns=["team", "batting", "bowling", "matches", "batting_rank", "bowling_rank"])
    kind = kind_of_ids(career, ids)
    white = kind != "multi"
    agg = inn.groupby(["match_id", "team", "opposition"]).agg(r=("runs", "sum"), w=("wickets", "sum"),
                                                              b=("balls", "sum")).reset_index()
    agg = agg[(agg.b > 0) | (agg.r > 0)]  # an innings that never started (abandoned game) isn't a performance
    order = {mid: i for i, mid in enumerate(m.match_id)}  # oldest first, so the most recent match counts most
    agg = agg.assign(o=agg.match_id.map(order)).sort_values(["o", "team"], kind="stable").drop(columns="o")
    tot_for = agg.groupby("team")[["r", "w", "b"]].sum()
    tot_against = agg.groupby("opposition")[["r", "w", "b"]].sum()
    rpw_bat = tot_for.r / tot_for.w.clip(lower=1)          # what each team usually scores per wicket
    rpw_conc = tot_against.r / tot_against.w.clip(lower=1)  # what each team's bowlers usually allow
    rr_bat = tot_for.r / tot_for.b.clip(lower=1) * 6
    rr_conc = tot_against.r / tot_against.b.clip(lower=1) * 6
    perf_bat: dict[str, list] = {}
    perf_bowl: dict[str, list] = {}
    for r in agg.itertuples():
        rpw = r.r / max(r.w, 1)
        bat = rpw / rpw_conc.get(r.opposition, rpw)
        bowl = rpw_bat.get(r.team, rpw) / rpw if rpw else np.nan  # what this batting side usually makes
        if white and r.b:
            rr = r.r / r.b * 6
            bat = 0.5 * bat + 0.5 * rr / rr_conc.get(r.opposition, rr)
            bowl = 0.5 * bowl + 0.5 * rr_bat.get(r.team, rr) / rr if rr else bowl
        perf_bat.setdefault(r.team, []).append(bat)
        perf_bowl.setdefault(r.opposition, []).append(bowl)
    rows = []
    for team in perf_bat:
        def ew(vals):
            v = np.array([x for x in vals if np.isfinite(x)], dtype=float)
            if not len(v):
                return np.nan
            w = DECAY ** np.arange(len(v))[::-1]
            return float((v * w).sum() / w.sum() * 1000)
        rows.append(dict(team=team, batting=ew(perf_bat[team]), bowling=ew(perf_bowl.get(team, [])),
                         matches=len(perf_bat[team])))
    d = pd.DataFrame(rows)
    d["batting_rank"] = d.batting.rank(ascending=False, method="min").astype(int)
    d["bowling_rank"] = d.bowling.rank(ascending=False, method="min").astype(int)
    return d.sort_values("batting", ascending=False).reset_index(drop=True)


# --------------------------------------------------------------------------- #
# 127 · clutch
# --------------------------------------------------------------------------- #


def pressure_games(career, ids) -> tuple[set, set]:
    """(match ids that were big games: knockouts, close games, series deciders;
    (match, innings) pairs batted under pressure: the 4th innings of a multi-day game)."""
    g = TP.games(career, ids)
    big = set(g[g.knockout | g.close].match_id)
    s = TP.series_games(career, ids)
    big |= set(s[s.decider].match_id)
    inn = career.innings[career.innings.match_id.isin(ids) & (career.innings.innings_no == 4)]
    return big, set(zip(inn.match_id, inn.innings_no))


def clutch(career, ids, min_innings: int = 3) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(batters, bowlers): figures in big games (and, in multi-day cricket, the 4th
    innings) against everything else.  Batters: those who usually bat in the top 7."""
    kind = kind_of_ids(career, ids)
    big, fourth = pressure_games(career, ids)
    inn = innings(career, ids)
    inn["clutch"] = inn.match_id.isin(big) | pd.Series([(a, b) in fourth for a, b in zip(inn.match_id, inn.innings_no)],
                                                       index=inn.index)
    rows = []
    for p, g in inn.groupby("player"):
        if g.position.median() > 7:  # batters and all-rounders: a tail-ender's runs in a final aren't the story
            continue
        a, b = g[g.clutch], g[~g.clutch]
        if len(a) < min_innings or len(b) < min_innings:
            continue
        avg = lambda x: x.runs.sum() / max(x.out.sum(), 1)  # noqa: E731
        rows.append(dict(player=p, team=g.team.iloc[-1], clutch_innings=len(a), clutch_avg=avg(a),
                         clutch_sr=a.runs.sum() / max(a.balls.sum(), 1) * 100, other_avg=avg(b),
                         other_sr=b.runs.sum() / max(b.balls.sum(), 1) * 100))
    bat = pd.DataFrame(rows, columns=["player", "team", "clutch_innings", "clutch_avg", "clutch_sr", "other_avg", "other_sr"])
    bat["lift"] = (bat.clutch_avg / bat.other_avg.replace(0, np.nan) - 1) * 100
    sp = spells(career, ids)
    sp["clutch"] = sp.match_id.isin(big) | pd.Series([(a, b) in fourth for a, b in zip(sp.match_id, sp.innings_no)],
                                                     index=sp.index)
    rows = []
    for p, g in sp.groupby("player"):
        a, b = g[g.clutch], g[~g.clutch]
        if len(a) < min_innings or len(b) < min_innings:
            continue
        rows.append(dict(player=p, team=g.team.iloc[-1], clutch_innings=len(a), clutch_wpi=a.wickets.mean(),
                         clutch_econ=a.runs.sum() / max(a.balls.sum(), 1) * 6, other_wpi=b.wickets.mean(),
                         other_econ=b.runs.sum() / max(b.balls.sum(), 1) * 6,
                         clutch_avg=a.runs.sum() / a.wickets.sum() if a.wickets.sum() else np.nan,
                         other_avg=b.runs.sum() / b.wickets.sum() if b.wickets.sum() else np.nan))
    bowl = pd.DataFrame(rows, columns=["player", "team", "clutch_innings", "clutch_wpi", "clutch_econ", "other_wpi",
                                       "other_econ", "clutch_avg", "other_avg"])
    bowl["lift"] = (bowl.clutch_wpi / bowl.other_wpi.replace(0, np.nan) - 1) * 100
    bat.attrs["kind"] = bowl.attrs["kind"] = kind
    return (bat.sort_values("lift", ascending=False).reset_index(drop=True),
            bowl.sort_values("lift", ascending=False).reset_index(drop=True))


# --------------------------------------------------------------------------- #
# 128 · partnership chemistry · 131 · strike-rate pressure
# --------------------------------------------------------------------------- #


def chemistry(career, ids, team: str = "", min_stands: int = 3) -> pd.DataFrame:
    """Named pairs: their average stand against what the average pair makes for the
    same wickets here (so openers are compared with opening stands)."""
    from . import partnerships as P
    s = P.stands(career, ids)
    by_wkt = s.groupby("wicket").runs.mean()
    k = s[s.known]
    if team:
        k = k[k.team == team]
    k = k.assign(pair=[" & ".join(sorted([a, b])) for a, b in zip(k.batter1, k.batter2)],
                 expected=k.wicket.map(by_wkt))
    g = k.groupby(["pair", "team"]).agg(stands=("runs", "size"), average=("runs", "mean"), expected=("expected", "mean"),
                                        best=("runs", "max")).reset_index()
    g = g[g.stands >= min_stands]
    g["chemistry"] = (g.average / g.expected.replace(0, np.nan) - 1) * 100
    return g.sort_values("chemistry", ascending=False).reset_index(drop=True)


def sr_pressure(career, ids, min_innings: int = 3) -> pd.DataFrame:
    """White-ball only.  For each batter: their partners' strike rate in innings in
    which they shared a stand with this batter, against the same partners' strike
    rate in their other innings.  (The scorecards don't split a stand's runs, so this
    is the partners' whole innings.)  Batters who usually bat in the top 7."""
    from . import partnerships as P
    if kind_of_ids(career, ids) == "multi":
        return pd.DataFrame(columns=["player", "team", "innings", "partner_sr_with", "partner_sr_without", "effect"])
    s = P.stands(career, ids)
    s = s[s.known]
    inn = innings(career, ids).set_index(["match_id", "innings_no", "player"])
    shared = {}
    for r in s.itertuples():
        for me, other in ((r.batter1, r.batter2), (r.batter2, r.batter1)):
            shared.setdefault(me, set()).add((r.match_id, r.innings_no, other))
    rows = []
    pos = innings(career, ids).groupby("player").position.median()
    for me, keys in shared.items():
        if pos.get(me, 99) > 7:  # batters and all-rounders only
            continue
        partners = {k[2] for k in keys}
        with_r = with_b = wo_r = wo_b = 0
        n = 0
        for p in partners:
            if p not in inn.index.get_level_values(2):
                continue
            pin = inn.xs(p, level=2)
            mine = {(a, b) for a, b, q in keys if q == p}
            for (mid, no), row in pin.iterrows():
                if (mid, no) in mine:
                    with_r += row.runs
                    with_b += row.balls
                    n += 1
                else:
                    wo_r += row.runs
                    wo_b += row.balls
        if n >= min_innings and with_b and wo_b and wo_r:  # partners who never scored otherwise: nothing to compare with
            a, b = with_r / with_b * 100, wo_r / wo_b * 100
            rows.append(dict(player=me, innings=n, partner_sr_with=a, partner_sr_without=b, effect=(a / b - 1) * 100))
    d = pd.DataFrame(rows, columns=["player", "innings", "partner_sr_with", "partner_sr_without", "effect"])
    team_of = innings(career, ids).groupby("player").team.last()
    d.insert(1, "team", d.player.map(team_of))
    return d.sort_values("effect").reset_index(drop=True)


# --------------------------------------------------------------------------- #
# 132 · home fortress
# --------------------------------------------------------------------------- #


def fortress(career, ids) -> pd.DataFrame:
    """Each team's home record against the average home side here."""
    g = TP.games(career, ids)
    home = g[g.venue == "home"]
    avg = TP.record(home)["win_pct"]
    rows = []
    for team, x in home.groupby("team"):
        rec = TP.record(x)
        rows.append(dict(team=team, **rec, vs=rec["win_pct"] - avg if np.isfinite(rec["win_pct"]) else np.nan))
    d = pd.DataFrame(rows, columns=["team", "played", "won", "lost", "drawn", "tied", "no_result", "win_pct", "decided", "vs"])
    d.attrs["average"] = avg
    return d.sort_values("win_pct", ascending=False).reset_index(drop=True)


# --------------------------------------------------------------------------- #
# 135 · squad changes
# --------------------------------------------------------------------------- #


def squad_changes(career, ids, team: str) -> pd.DataFrame:
    """Who came in and who went out: season to season for a league side, series to
    series for an international side.  One row per change, with their runs and
    wickets in the period before (leavers) or after (arrivals)."""
    m = career.matches[career.matches.match_id.isin(ids) & ((career.matches.home == team) | (career.matches.away == team))]
    if m.empty:
        return pd.DataFrame(columns=["from", "to", "player", "change", "runs", "wickets", "games"])
    intl = (m.level == "International").all()  # bilateral series and World Cups alike
    if intl:
        m = m.assign(period=np.where(m.series_id != "", m.series_id, m.event + " " + m.season))
        order = m.groupby("period").date.min().sort_values()
        def opponents_in(p):
            g_ = m[m.period == p]
            return ", ".join(sorted((set(g_.home) | set(g_.away)) - {team}))
        label = {p: f"{m[m.period == p].event.iloc[0]} v {opponents_in(p)} ({d:%b %Y})" for p, d in order.items()}
    else:
        m = m.assign(period=m.season)
        order = m.groupby("period").date.min().sort_values()
        label = {p: str(p) for p in order.index}
    b = career.batting[career.batting.match_id.isin(m.match_id) & (career.batting.team == team)]
    w = career.bowling[career.bowling.match_id.isin(m.match_id) & (career.bowling.team == team)]
    per = m.set_index("match_id").period
    b = b.assign(period=b.match_id.map(per))
    w = w.assign(period=w.match_id.map(per))
    squads = {p: set(b[b.period == p].player) for p in order.index}
    rows = []
    periods = list(order.index)
    for a, c in zip(periods, periods[1:]):
        left, came = squads[a] - squads[c], squads[c] - squads[a]
        for p, kind_, src in [(x, "out", a) for x in sorted(left)] + [(x, "in", c) for x in sorted(came)]:
            bb, ww = b[(b.period == src) & (b.player == p)], w[(w.period == src) & (w.player == p)]
            rows.append({"from": label[a], "to": label[c], "player": p, "change": kind_, "runs": int(bb.runs.sum()),
                         "wickets": int(ww.wickets.sum()), "games": int(bb.match_id.nunique())})
    d = pd.DataFrame(rows, columns=["from", "to", "player", "change", "runs", "wickets", "games"])
    d.attrs["international"] = bool(intl)
    return d


# --------------------------------------------------------------------------- #
# 138 · Tests: second innings and fourth-innings chases
# --------------------------------------------------------------------------- #


def second_innings(career, ids) -> pd.DataFrame:
    """Each team's second innings in multi-day games: average, how often bowled out
    cheaply (under 200), and their record chasing in the 4th innings."""
    m = career.matches[career.matches.match_id.isin(ids)]
    inn = career.innings[career.innings.match_id.isin(m.match_id)]
    g = TP.games(career, ids).set_index(["match_id", "team"]).outcome
    rows = []
    for team in sorted(set(inn.team)):
        sec = inn[(inn.team == team) & (inn.team_innings == 2)]
        fourth = inn[(inn.team == team) & (inn.innings_no == 4)]
        outs = [g.get((r.match_id, team), "") for r in fourth.itertuples()]
        rows.append(dict(team=team, second_innings=len(sec), second_avg=sec.runs.mean() if len(sec) else np.nan,
                         cheap=int((sec.all_out & (sec.runs < 200)).sum()),
                         chases=len(fourth), chase_won=outs.count("W"), chase_drawn=outs.count("D"),
                         chase_lost=outs.count("L")))
    return pd.DataFrame(rows, columns=["team", "second_innings", "second_avg", "cheap", "chases", "chase_won", "chase_drawn",
                                       "chase_lost"])


# --------------------------------------------------------------------------- #
# 139 · Test bowlers: first spell v second, striking in both innings
# --------------------------------------------------------------------------- #


def bowler_match_pattern(career, ids, min_matches: int = 2) -> pd.DataFrame:
    """Multi-day bowlers: average in their first bowling innings of a match against
    their second (does the wearing pitch help them?), how often they took wickets
    in both innings, and their best match figures."""
    w = career.bowling[career.bowling.match_id.isin(ids) & (career.bowling.balls > 0)].sort_values(["match_id", "innings_no"])
    rows = []
    for p, g in w.groupby("player"):
        both = g.groupby("match_id").filter(lambda x: len(x) >= 2)
        if both.match_id.nunique() < min_matches:
            continue
        first = both.groupby("match_id").head(1)
        second = both.groupby("match_id").nth(1)
        bm = g.groupby("match_id")[["wickets", "runs"]].sum().assign(k=lambda x: x.wickets * 1000 - x.runs)
        b0 = bm.sort_values("k").iloc[-1]
        struck = both.groupby("match_id").wickets.apply(lambda x: (x > 0).all())
        rows.append(dict(player=p, team=g.team.iloc[-1], matches=both.match_id.nunique(),
                         first_avg=first.runs.sum() / first.wickets.sum() if first.wickets.sum() else np.nan,
                         second_avg=second.runs.sum() / second.wickets.sum() if second.wickets.sum() else np.nan,
                         both_pct=struck.mean() * 100, best_match=f"{int(b0.wickets)}/{int(b0.runs)}"))
    d = pd.DataFrame(rows, columns=["player", "team", "matches", "first_avg", "second_avg", "both_pct", "best_match"])
    d["change"] = (d.second_avg / d.first_avg - 1) * 100
    return d.sort_values("matches", ascending=False).reset_index(drop=True)
