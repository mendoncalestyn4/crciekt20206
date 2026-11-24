"""Hall of fame (stage 3, your answers 19, 20, 23, 26, 30, 31): real inductions with a plaque, who's next in, the best
batting duos, and a timeline of firsts. The Player of the Match and All-round matches tabs are the current site's
(ccstats/extras.py); Deadly duos and every other fielding piece are taken out (answer 20).

**Inductions** (answer 23), each competition on its own, growing with the length of game: T20 cricket (The Hundred
too) 1,500 runs, 75 wickets or 10 Player of the Match awards; one-day 2,500 runs or 100 wickets; Tests and first-class
4,000 runs or 150 wickets; and all-rounders 1,000 runs and 50 wickets in any format. A player is inducted on the day
he first reaches one, in the match he did it in."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .records import by_played
from .stats import KIND

BARS = {"t20": dict(runs=1500, wickets=75, pom=10), "one": dict(runs=2500, wickets=100),
        "multi": dict(runs=4000, wickets=150)}
ALL_ROUND = dict(runs=1000, wickets=50)


def kind_of(career, section: str) -> str:
    m = career.matches[career.matches.section == section]
    return KIND.get(m.format.mode().iloc[0], "t20") if len(m) else "t20"


def _running(career, section: str) -> pd.DataFrame:
    """Each player's runs, wickets and Player of the Match awards in the competition after each of his matches, in the
    order the matches were played: player, team, match_id, date, runs, wickets, pom (each a running total)."""
    m = by_played(career, career.matches[career.matches.section == section])
    ids = list(m.match_id)
    order = {mid: i for i, mid in enumerate(ids)}
    b = career.batting[career.batting.match_id.isin(ids)]
    played = b[["match_id", "team", "player"]].drop_duplicates()
    runs = b[b.did_bat].groupby(["match_id", "player"]).runs.sum()
    w = career.bowling[career.bowling.match_id.isin(ids)]
    wk = w.groupby(["match_id", "player"]).wickets.sum()
    bowled = w[["match_id", "team", "player"]].drop_duplicates()
    played = pd.concat([played, bowled]).drop_duplicates(["match_id", "player"])
    pom = m.set_index("match_id").player_of_match
    d = played.assign(runs=[int(runs.get((a, p), 0)) for a, p in zip(played.match_id, played.player)],
                      wickets=[int(wk.get((a, p), 0)) for a, p in zip(played.match_id, played.player)],
                      pom=[int(pom.get(a, "") == p) for a, p in zip(played.match_id, played.player)],
                      _o=played.match_id.map(order), date=played.match_id.map(m.set_index("match_id").date))
    d = d.sort_values(["_o", "player"]).reset_index(drop=True)
    g = d.groupby("player")
    for c in ("runs", "wickets", "pom"):
        d[c] = g[c].cumsum()
    d["matches"] = g.cumcount() + 1
    return d.drop(columns="_o")


def routes(kind: str) -> list[tuple[str, dict]]:
    """Every way in for this kind of cricket: (label, {figure: needed})."""
    b = BARS[kind]
    out = [(f"{b['runs']:,} runs", dict(runs=b["runs"])), (f"{b['wickets']} wickets", dict(wickets=b["wickets"]))]
    if "pom" in b:
        out.append((f"{b['pom']} Player of the Match awards", dict(pom=b["pom"])))
    out.append((f"{ALL_ROUND['runs']:,} runs and {ALL_ROUND['wickets']} wickets", dict(ALL_ROUND)))
    return out


def inductions(career, section: str) -> pd.DataFrame:
    """Everyone inducted in a competition, earliest first: player, team, date, match_id, route (what took him in),
    also (other routes reached since), and his figures there now."""
    from .keep import on_career
    return on_career(career, ("hall_inductions", section), lambda: _inductions(career, section))


def _inductions(career, section: str) -> pd.DataFrame:
    cols = ["player", "team", "date", "match_id", "route", "also", "runs", "wickets", "pom", "matches"]
    d = _running(career, section)
    if d.empty:
        return pd.DataFrame(columns=cols)
    kind = kind_of(career, section)
    rows = []
    last = d.groupby("player").tail(1).set_index("player")
    for label, need in routes(kind):
        ok = np.ones(len(d), dtype=bool)
        for k, v in need.items():
            ok &= d[k].to_numpy() >= v
        first = d[ok].groupby("player").head(1)
        for r in first.itertuples():
            rows.append(dict(player=r.player, team=r.team, date=r.date, match_id=r.match_id, route=label))
    if not rows:
        return pd.DataFrame(columns=cols)
    a = pd.DataFrame(rows).sort_values(["date", "player"], kind="stable")
    out = []
    for p, g in a.groupby("player", sort=False):
        g = g.sort_values("date", kind="stable")
        f = g.iloc[0]
        now = last.loc[p]
        out.append(dict(player=p, team=f.team, date=f.date, match_id=f.match_id, route=f.route,
                        also=" · ".join(g.route.iloc[1:]), runs=int(now.runs), wickets=int(now.wickets), pom=int(now.pom),
                        matches=int(now.matches)))
    return pd.DataFrame(out, columns=cols).sort_values(["date", "player"]).reset_index(drop=True)


def next_in(career, section: str, n: int = 8) -> pd.DataFrame:
    """The players closest to being inducted (not in yet), with what each still needs on his nearest route:
    player, team, share (how far along, 0-1), needs ("312 runs")."""
    d = _running(career, section)
    cols = ["player", "team", "share", "needs", "runs", "wickets", "pom"]
    if d.empty:
        return pd.DataFrame(columns=cols)
    inside = set(inductions(career, section).player)
    now = d.groupby("player").tail(1)
    now = now[~now.player.isin(inside)]
    rows = []
    for r in now.itertuples():
        best = None
        for label, need in routes(kind_of(career, section)):
            share = min(getattr(r, k) / v for k, v in need.items())
            left = [f"{v - getattr(r, k):,} {'Player of the Match awards' if k == 'pom' else k}"
                    for k, v in need.items() if getattr(r, k) < v]
            if best is None or share > best[0]:
                best = (share, " and ".join(left) + (" (for " + label + ")" if len(need) > 1 else ""))
        rows.append(dict(player=r.player, team=r.team, share=best[0], needs=best[1], runs=int(r.runs),
                         wickets=int(r.wickets), pom=int(r.pom)))
    out = pd.DataFrame(rows, columns=cols)
    return out.sort_values(["share", "player"], ascending=[False, True]).head(n).reset_index(drop=True)


def plaque(career, section: str, player: str) -> dict:
    """His best moments in the competition: the three highest innings and the two best bowling figures, each with its
    match, and his figures."""
    ids = set(career.matches[career.matches.section == section].match_id)
    meta = career.matches.set_index("match_id")
    b = career.batting[career.batting.match_id.isin(ids) & career.batting.did_bat & (career.batting.player == player)]
    w = career.bowling[career.bowling.match_id.isin(ids) & (career.bowling.player == player) & (career.bowling.balls > 0)]
    best_bat = b.assign(k=b.runs * 2 + (~b.out)).sort_values(["k", "match_id"], ascending=[False, True]).head(3)
    best_bowl = w.assign(k=w.wickets * 1000 - w.runs).sort_values(["k", "match_id"], ascending=[False, True]).head(2)
    moments = [dict(what=f"{int(r.runs)}{'' if r.out else '*'} v {r.opposition}", date=meta.date[r.match_id], id=r.match_id)
               for r in best_bat.itertuples() if r.runs > 0]
    moments += [dict(what=f"{int(r.wickets)}/{int(r.runs)} v {r.opposition}", date=meta.date[r.match_id], id=r.match_id)
                for r in best_bowl.itertuples() if r.wickets > 0]
    outs = int(b.out.sum())
    return dict(moments=moments, runs=int(b.runs.sum()), average=(b.runs.sum() / outs) if outs else None,
                wickets=int(w.wickets.sum()), bowl_average=(w.runs.sum() / w.wickets.sum()) if w.wickets.sum() else None)


def duos(career, ids, n: int = 15) -> pd.DataFrame:
    """The best batting duos (answer 19, in place of Deadly duos): the pairs with the most runs together, from the
    fall of wickets where the card says who batted together. pair, team, stands, runs, average (over the stands that
    were broken, as every partnership average on the site), best, fifty_plus, hundred_plus."""
    from . import partnerships as P
    cols = ["pair", "team", "stands", "runs", "average", "best", "fifty_plus", "hundred_plus"]
    st = P.stands(career, ids)
    st = st[st.known] if len(st) else st
    if st.empty:
        return pd.DataFrame(columns=cols)
    st = st.assign(pair=[" & ".join(sorted((a, b))) for a, b in zip(st.batter1, st.batter2)])
    g = st.groupby(["pair", "team"])
    out = g.agg(stands=("runs", "size"), runs=("runs", "sum"), broken=("unbroken", lambda u: int((~u).sum())),
                fifty_plus=("runs", lambda r: int((r >= 50).sum())), hundred_plus=("runs", lambda r: int((r >= 100).sum())))
    best = st.sort_values(["runs", "unbroken"], ascending=[False, True]).groupby(["pair", "team"]).head(1).set_index(["pair", "team"])
    out["best"] = [f"{int(best.runs[i])}{'*' if best.unbroken[i] else ''}" for i in out.index]
    out["average"] = np.where(out.broken > 0, out.runs / out.broken.replace(0, np.nan), np.nan)
    out = out.reset_index().sort_values(["runs", "stands", "pair"], ascending=[False, True, True]).head(n)
    return out[cols].reset_index(drop=True)
