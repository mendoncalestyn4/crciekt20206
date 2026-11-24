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


# --------------------------------------------------------------------------- the firsts timeline (answers 19, 26, 30)
def firsts(career, team: str) -> pd.DataFrame:
    """A team's firsts and its players' firsts, oldest first: date, kind (team / player), what, who, match_id, section.
    Kept with the career."""
    from .keep import on_career
    return on_career(career, ("hall_firsts", team), lambda: _firsts(career, team))


def _firsts(career, team: str) -> pd.DataFrame:
    from . import partnerships as P
    from .extras import honours
    from .players import player_of_series
    from .rankings import team_elo
    cols = ["date", "kind", "what", "who", "match_id", "section"]
    m = by_played(career, career.matches[(career.matches.home == team) | (career.matches.away == team)])
    if m.empty:
        return pd.DataFrame(columns=cols)
    ev: list[dict] = []
    seen: set = set()

    def add(key, date, kind, what, who="", mid="", section=""):
        if key in seen:
            return
        seen.add(key)
        ev.append(dict(date=date, kind=kind, what=what, who=who, match_id=mid, section=section))

    opp = m.away.where(m.home == team, m.home)
    m = m.assign(opp=opp, won=m.winner == team)
    inns = career.innings[career.innings.match_id.isin(m.match_id)]
    by_id = m.set_index("match_id")
    margin = lambda r: (f"by {int(r.margin_runs)} runs" if r.margin_runs == r.margin_runs and r.margin_runs and not r.innings_win   # noqa: E731
                        else f"by an innings and {int(r.margin_runs)} runs" if r.innings_win and r.margin_runs == r.margin_runs
                        else f"by {int(r.margin_wickets)} wickets" if r.margin_wickets == r.margin_wickets and r.margin_wickets else "")
    for r in m.itertuples():
        add(("match", r.section), r.date, "team", f"First match in {r.section}", f"v {r.opp}", r.match_id, r.section)
        if r.won:
            add(("win", r.section), r.date, "team", f"First win in {r.section}", f"v {r.opp} {margin(r)}".strip(), r.match_id, r.section)
            add(("beat", r.opp), r.date, "team", f"First win against {r.opp}", f"{r.section}, {margin(r)}".strip(", "), r.match_id, r.section)
            if r.margin_runs == r.margin_runs and r.margin_runs >= 100 and not r.innings_win:
                add(("big_runs",), r.date, "team", "First win by 100 runs or more", f"by {int(r.margin_runs)} runs v {r.opp}", r.match_id, r.section)
            if r.margin_wickets == r.margin_wickets and r.margin_wickets >= 10:
                add(("big_wkts",), r.date, "team", "First win by 10 wickets", f"v {r.opp}", r.match_id, r.section)
        if r.result_type == "tie":
            add(("tie",), r.date, "team", "First tie" + (" and super-over win" if r.tiebreak_winner == team else ""), f"v {r.opp}", r.match_id, r.section)
        elif r.tiebreak_winner == team:
            add(("super",), r.date, "team", "First super-over win", f"v {r.opp}", r.match_id, r.section)
        if r.stage == "Final":
            add(("final", r.event), r.date, "team", f"First final reached: {r.event}", f"v {r.opp}", r.match_id, r.section)
    # totals, chases and bowling a side out
    big = {"one": 300, "t20": 200, "multi": 500}
    fmt_kind = by_id.format.map(KIND)
    for r in inns.sort_values(["match_id", "innings_no"]).itertuples():
        x = by_id.loc[r.match_id]
        k = fmt_kind[r.match_id]
        if r.team == team and r.runs >= big.get(k, 999):
            add(("total", k), x.date, "team", f"First total of {big[k]} or more ({ {'one': 'one-day', 't20': 'T20', 'multi': 'Tests and first-class'}[k] })",
                f"{r.runs}{'' if r.all_out else '/' + str(r.wickets)} v {x.opp}", r.match_id, x.section)
        if r.team != team and r.all_out and r.runs < 100:
            add(("under100",), x.date, "team", "First time bowling a side out for under 100", f"{x.opp} {r.runs}", r.match_id, x.section)
        last = inns[inns.match_id == r.match_id].innings_no.max()
        if r.team == team and x.won and r.innings_no == last and r.runs >= 300:
            if k == "one" and r.innings_no == 2:
                add(("chase300",), x.date, "team", "First chase of 300 or more in a one-day game", f"{r.runs}/{r.wickets} v {x.opp}", r.match_id, x.section)
            if k == "multi" and r.innings_no == 4:
                add(("chase300t",), x.date, "team", "First fourth-innings chase of 300 or more", f"{r.runs}/{r.wickets} v {x.opp}", r.match_id, x.section)
    # series: the first won, away, in each country, and the first clean sweep
    for sid, g in m[m.series_id != ""].groupby("series_id", sort=False):
        g = g.sort_values("date")
        length = int(g.series_length.max()) if g.series_length.notna().any() else len(g)
        won, lost = int(g.won.sum()), int((g.winner == g.opp).sum())
        if len(g) < length or won <= lost:
            continue
        last = g.iloc[-1]
        host = g.home.iloc[0]
        what = f"v {last.opp}, {won}–{lost} ({last.section})"
        add(("series",), last.date, "team", "First series win", what, last.match_id, last.section)
        if host != team and not g.neutral.iloc[0]:
            add(("series_away",), last.date, "team", "First series win away", what, last.match_id, last.section)
            add(("series_in", host), last.date, "team", f"First series win in {host}", what, last.match_id, last.section)
        if won == length and length >= 2:
            add(("sweep",), last.date, "team", "First clean sweep", f"{won}–0 v {last.opp} ({last.section})", last.match_id, last.section)
    # titles
    h = honours(career)
    h = h[h.champion_teams.map(lambda t: team in t) & ~h.how.str.contains("so far")].sort_values("date")
    for r in h.itertuples():
        add(("title",), r.date, "team", "First title", f"{r.section} {r.season} ({r.how})", "", "")
    # top of the team ratings
    for sec in m.section.unique():
        _, hist = team_elo(career, sec)
        if hist.empty:
            continue
        rating: dict[str, float] = {}
        for (d, mid), g in hist.groupby(["date", "match_id"], sort=True):
            for x in g.itertuples():
                rating[x.team] = x.after
            if team in rating and len(rating) > 1 and rating[team] > max(v for t_, v in rating.items() if t_ != team):
                add(("elo", sec), d, "team", f"First time top of the team ratings in {sec}", f"{rating[team]:.0f}", mid, sec)
                break
    # the players
    b = career.batting[career.batting.match_id.isin(m.match_id) & (career.batting.team == team) & career.batting.did_bat]
    b = by_played(career, b).assign(date=lambda x: x.match_id.map(by_id.date), section=lambda x: x.match_id.map(by_id.section),
                                    opp=lambda x: x.match_id.map(by_id.opp))
    first_game = by_played(career, career.batting[career.batting.match_id.isin(m.match_id) & (career.batting.team == team)]) \
        .assign(section=lambda x: x.match_id.map(by_id.section)).groupby(["player", "section"]).match_id.first()
    for r in b.itertuples():
        s = f"{r.runs}{'' if r.out else '*'} v {r.opp}"
        if r.runs >= 50:
            add(("fifty",), r.date, "player", "First fifty", f"{r.player} {s}", r.match_id, r.section)
        if r.runs >= 100:
            add(("hundred",), r.date, "player", "First hundred", f"{r.player} {s}", r.match_id, r.section)
            add(("hundred", r.section), r.date, "player", f"First hundred in {r.section}", f"{r.player} {s}", r.match_id, r.section)
            if first_game.get((r.player, r.section)) == r.match_id:
                add(("debut100",), r.date, "player", "First hundred on debut", f"{r.player} {s} ({r.section})", r.match_id, r.section)
        if r.runs >= 150:
            add(("150",), r.date, "player", "First 150", f"{r.player} {s}", r.match_id, r.section)
        if r.runs >= 200:
            add(("200",), r.date, "player", "First double hundred", f"{r.player} {s}", r.match_id, r.section)
    w = career.bowling[career.bowling.match_id.isin(m.match_id) & (career.bowling.team == team) & (career.bowling.balls > 0)]
    w = by_played(career, w).assign(date=lambda x: x.match_id.map(by_id.date), section=lambda x: x.match_id.map(by_id.section),
                                    opp=lambda x: x.match_id.map(by_id.opp))
    for r in w.itertuples():
        if r.wickets >= 5:
            add(("fivefor",), r.date, "player", "First five-for", f"{r.player} {r.wickets}/{r.runs} v {r.opp}", r.match_id, r.section)
    tenm = w.groupby(["match_id", "player"], sort=False).agg(wickets=("wickets", "sum"), runs=("runs", "sum"), date=("date", "first"),
                                                             section=("section", "first"), opp=("opp", "first")).reset_index()
    for r in tenm[tenm.wickets >= 10].itertuples():
        add(("ten",), r.date, "player", "First 10 wickets in a match", f"{r.player} {r.wickets}/{r.runs} v {r.opp}", r.match_id, r.section)
    for r in m[m.player_of_match != ""].itertuples():
        if r.player_of_match in set(career.batting[(career.batting.match_id == r.match_id) & (career.batting.team == team)].player):
            add(("pom",), r.date, "player", "First Player of the Match", f"{r.player_of_match} v {r.opp}", r.match_id, r.section)
    st = P.stands(career, m.match_id)
    if len(st):
        st = by_played(career, st[st.team == team]).assign(date=lambda x: x.match_id.map(by_id.date), section=lambda x: x.match_id.map(by_id.section))
        for r in st.itertuples():
            who = f"{r.batter1} & {r.batter2}" if r.known else f"the {r.wicket}{P.suffix(r.wicket)} wicket"
            for n in (100, 200):
                if r.runs >= n:
                    add(("stand", n), r.date, "player", f"First {n} partnership", f"{who}, {r.runs}{'*' if r.unbroken else ''} v {r.opposition}",
                        r.match_id, r.section)
    # 1,000 runs and 50 wickets in a format, the running totals in each competition
    for sec, g in b.groupby("section", sort=False):
        c = g.assign(total=g.groupby("player").runs.cumsum())
        hit = c[c.total >= 1000]
        if len(hit):
            r = hit.iloc[0]
            add(("1000", sec), r.date, "player", f"First to 1,000 runs in {sec}", r.player, r.match_id, sec)
    for sec, g in w.groupby("section", sort=False):
        c = g.assign(total=g.groupby("player").wickets.cumsum())
        hit = c[c.total >= 50]
        if len(hit):
            r = hit.iloc[0]
            add(("50w", sec), r.date, "player", f"First to 50 wickets in {sec}", r.player, r.match_id, sec)
    # Player of the Series, No. 1 in the rankings, the Hall of fame
    for sec in m.section.unique():
        ps = player_of_series(career, career.matches[career.matches.section == sec].match_id)
        ps = ps[ps.team == team]
        if len(ps):
            ends = career.matches[career.matches.series_id.isin(ps.series_id)].groupby("series_id").date.max()
            ps = ps.assign(date=ps.series_id.map(ends)).sort_values("date")
            r = ps.iloc[0]
            add(("pos",), r.date, "player", "First Player of the Series", f"{r.player} ({sec})", "", sec)
    from . import ranking as RK
    for sec in m.section.unique():
        for what in RK.KINDS:
            h = RK.history(career, sec, what)
            top = h[(h["rank"] == 1) & (h.team == team)].sort_values("date")
            if len(top):
                r = top.iloc[0]
                add(("no1",), r.date, "player", "First player ranked No. 1", f"{r.player} ({sec}, {what})", "", sec)
        ind = inductions(career, sec)
        ind = ind[ind.team == team]
        if len(ind):
            r = ind.iloc[0]
            add(("hall",), r.date, "player", "First Hall of fame entry", f"{r.player} ({sec}: {r.route})", r.match_id, sec)
    out = pd.DataFrame(ev, columns=cols)
    return out.sort_values(["date", "kind"], kind="stable").reset_index(drop=True)
