"""Deeper player numbers, each with format-specific rules: danger zones,
conversion funnel, fastest to milestones, rank over time, match impact,
bowling with and without wickets, achievements, batter v bowler, the career
card and the all-format view."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .players import innings, kind_of_ids, spells
from .stats import KIND, fielding_credits

# --------------------------------------------------------------------------- #
# 89 · danger zones
# --------------------------------------------------------------------------- #

ZONES = {"t20": [(0, 9), (10, 19), (20, 49), (50, None)],  # T20: 20-49 is the band that matters (got in, out before 50)
         "one": [(0, 9), (10, 29), (30, 49), (50, 99), (100, None)],
         "multi": [(0, 9), (10, 29), (30, 49), (50, 99), (100, 149), (150, None)]}


KEY_ZONE = {"t20": (20, 49)}  # highlighted on the Players page


def zone_label(lo: int, hi: int | None) -> str:
    return f"{lo}+" if hi is None else f"{lo}–{hi}"


def danger_zones(career, ids, player: str) -> pd.DataFrame:
    """Share of the player's dismissals in each score band, against every batter in these matches."""
    kind = kind_of_ids(career, ids)
    inn = innings(career, ids)
    out = inn[inn.out]
    mine = out[out.player == player]
    rows = []
    for lo, hi in ZONES[kind]:
        sel = (lambda d: d[(d.runs >= lo) & ((d.runs <= hi) if hi is not None else True)])
        n_me, n_all = len(sel(mine)), len(sel(out))
        rows.append(dict(zone=zone_label(lo, hi), outs=n_me, pct=n_me / len(mine) * 100 if len(mine) else np.nan,
                         all_pct=n_all / len(out) * 100 if len(out) else np.nan))
    d = pd.DataFrame(rows)
    d.attrs.update(dismissals=len(mine), kind=kind)
    return d


# --------------------------------------------------------------------------- #
# 90 · conversion funnel
# --------------------------------------------------------------------------- #

FUNNEL = {"t20": ([10, 20, 30, 40, 50], [20, 50]),  # in T20 the fifty is the big score: 100s are counted on their own
          "one": ([10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 150], [30, 50, 80, 100]),
          "multi": ([10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 150, 200], [50, 80, 100])}


def funnel(career, ids, player: str) -> pd.DataFrame:
    """For every mark: % of the player's innings reaching it, % of the innings that
    reached the previous mark going on to this one, and the same for every batter
    here.  `highlight` marks the format's key marks (20 and 50 in T20; 30, 50, 80,
    100 in one-day; 50, 80, 100 in Tests); `from_key` is the conversion from the
    previous key mark."""
    kind = kind_of_ids(career, ids)
    marks, keys = FUNNEL[kind]
    inn = innings(career, ids)
    mine = inn[inn.player == player]
    rows = []
    prev = None
    prev_key = None
    for mk in marks:
        me = int((mine.runs >= mk).sum())
        al = int((inn.runs >= mk).sum())
        row = dict(mark=mk, innings=me, pct=me / len(mine) * 100 if len(mine) else np.nan,
                   all_pct=al / len(inn) * 100 if len(inn) else np.nan,
                   from_prev=(me / prev[0] * 100 if prev and prev[0] else np.nan),
                   all_from_prev=(al / prev[1] * 100 if prev and prev[1] else np.nan),
                   highlight=mk in keys, from_key=np.nan, all_from_key=np.nan, key_from="")
        if mk in keys and prev_key is not None:
            row.update(from_key=me / prev_key[1] * 100 if prev_key[1] else np.nan,
                       all_from_key=al / prev_key[2] * 100 if prev_key[2] else np.nan, key_from=str(prev_key[0]))
        if mk in keys:
            prev_key = (mk, me, al)
        rows.append(row)
        prev = (me, al)
    d = pd.DataFrame(rows)
    d.attrs.update(innings=len(mine), kind=kind, keys=keys)
    if kind == "t20":  # hundreds on their own: how many, and how often a fifty went on to one
        f_me, f_all = int((mine.runs >= 50).sum()), int((inn.runs >= 50).sum())
        h_me, h_all = int((mine.runs >= 100).sum()), int((inn.runs >= 100).sum())
        d.attrs.update(hundreds=h_me, fifties=f_me, fifty_to_100=h_me / f_me * 100 if f_me else np.nan,
                       all_fifty_to_100=h_all / f_all * 100 if f_all else np.nan)
    return d


# --------------------------------------------------------------------------- #
# 91 · fastest to milestones
# --------------------------------------------------------------------------- #

MILESTONES = {"t20": dict(runs=[500, 1000, 2000], wickets=[25, 50, 100], unit="innings"),
              "one": dict(runs=[1000, 2000, 5000], wickets=[50, 100, 150], unit="innings"),
              "multi": dict(runs=[1000, 2000, 5000, 10000], wickets=[50, 100, 200, 300], unit="matches")}


def fastest(career, ids) -> pd.DataFrame:
    """For each milestone: every player who got there, with the innings (matches
    in multi-day cricket, as in real records) it took, fastest first."""
    kind = kind_of_ids(career, ids)
    ms = MILESTONES[kind]
    inn = innings(career, ids)
    sp = spells(career, ids)
    if ms["unit"] == "matches":
        # every match played counts, batted / bowled in it or not (as in real Test records)
        dates = career.matches.set_index("match_id").date
        played = career.batting[career.batting.match_id.isin(ids)][["match_id", "team", "player"]].drop_duplicates()
        played = played.assign(date=played.match_id.map(dates)).sort_values(["date", "match_id"])
    rows = []
    for what, d, col in (("runs", inn, "runs"), ("wickets", sp, "wickets")):
        tot = d.groupby(["player", "match_id"])[col].sum()
        for p, g in d.groupby("player"):
            if ms["unit"] == "matches":
                per = played[played.player == p]
                per = per.assign(v=[tot.get((p, x), 0) for x in per.match_id])[["v", "date", "team"]]
            else:
                per = g.assign(v=g[col])[["v", "date", "team"]]
            run = per.v.cumsum().to_numpy()
            for target in ms[what]:
                hit = np.argmax(run >= target) if (run >= target).any() else None
                if hit is not None:
                    rows.append(dict(what=what, milestone=target, player=p, team=per.team.iloc[hit],
                                     taken=int(hit + 1), date=per.date.iloc[hit]))
    df = pd.DataFrame(rows, columns=["what", "milestone", "player", "team", "taken", "date"])
    df["rank"] = df.groupby(["what", "milestone"]).taken.rank(method="min").astype(int) if len(df) else []
    df = df.sort_values(["what", "milestone", "taken", "date"]).reset_index(drop=True)
    df.attrs.update(unit=ms["unit"], kind=kind)
    return df


# --------------------------------------------------------------------------- #
# 92 · rank over time
# --------------------------------------------------------------------------- #


def rank_by_season(career, section: str, player: str) -> pd.DataFrame:
    """The player's rank in the section each season, by runs and by wickets (of everyone who batted or bowled)."""
    m = career.matches[career.matches.section == section]
    rows = []
    for season, g in m.groupby("season"):
        inn = innings(career, g.match_id)
        sp = spells(career, g.match_id)
        runs = inn.groupby("player").runs.sum().rank(ascending=False, method="min")
        wk = sp.groupby("player").wickets.sum()
        wk = wk[wk > 0].rank(ascending=False, method="min")
        rows.append(dict(season=season, runs_rank=runs.get(player, np.nan), runs_of=len(runs),
                         wickets_rank=wk.get(player, np.nan), wickets_of=len(wk),
                         runs=int(inn[inn.player == player].runs.sum()), wickets=int(sp[sp.player == player].wickets.sum())))
    return pd.DataFrame(rows, columns=["season", "runs_rank", "runs_of", "wickets_rank", "wickets_of", "runs", "wickets"])


# --------------------------------------------------------------------------- #
# 94 · match impact
# --------------------------------------------------------------------------- #


FIFTY_BONUS, HUNDRED_BONUS = 15, 10  # T20 match impact, in runs


def match_impact(career, ids) -> pd.DataFrame:
    """One number per player per match.  Batting: runs, and in white-ball cricket
    half the runs above (or below) what the section's strike rate would have made
    off the same balls.  Bowling: wickets worth the section's runs per wicket, plus
    in white-ball cricket the runs kept below the section's economy.  Fielding: a
    catch or stumping is a quarter of a wicket.  In T20 the fifty is the big score: reaching 50 is worth
    FIFTY_BONUS more, and a hundred a smaller HUNDRED_BONUS on top (it's rare, so it doesn't swamp the rest)."""
    kind = kind_of_ids(career, ids)
    m = career.matches[career.matches.match_id.isin(ids)]
    inn_all = career.innings[career.innings.match_id.isin(ids)]
    rpw = inn_all.runs.sum() / max(inn_all.wickets.sum(), 1)
    b = career.batting[career.batting.match_id.isin(ids) & career.batting.did_bat]
    w = career.bowling[career.bowling.match_id.isin(ids) & (career.bowling.balls > 0)]
    f = fielding_credits(career, ids)   # none on the new site (no fielding anywhere)
    sr = b.runs.sum() / max(b.balls.sum(), 1)
    econ = w.runs.sum() / max(w.balls.sum(), 1)
    white = kind != "multi"
    bonus = ((b.runs >= 50) * FIFTY_BONUS + (b.runs >= 100) * HUNDRED_BONUS) if kind == "t20" else 0
    bat = b.assign(pts=b.runs + ((b.runs - b.balls * sr) * 0.5 if white else 0) + bonus) \
        .groupby(["match_id", "team", "player"]).agg(bat=("pts", "sum"), runs=("runs", "sum")).reset_index()
    bowl = w.assign(pts=w.wickets * rpw + ((w.balls * econ - w.runs) if white else 0)) \
        .groupby(["match_id", "team", "player"]).agg(bowl=("pts", "sum"), wickets=("wickets", "sum"),
                                                     conceded=("runs", "sum")).reset_index()
    fld = f.groupby(["match_id", "team", "player"]).size().rename("dismissals").reset_index()
    fld["field"] = fld.dismissals * rpw * 0.25
    d = bat.merge(bowl, on=["match_id", "team", "player"], how="outer").merge(fld, on=["match_id", "team", "player"],
                                                                             how="outer")
    d = d.fillna({"bat": 0.0, "bowl": 0.0, "field": 0.0, "runs": 0, "wickets": 0, "conceded": 0, "dismissals": 0})
    d["impact"] = d.bat + d.bowl + d.field
    d = d.merge(m[["match_id", "date", "home", "away", "winner"]], on="match_id")
    d["opponent"] = np.where(d.team == d.home, d.away, d.home)
    d["won"] = d.winner == d.team
    d.attrs.update(rpw=rpw, kind=kind)
    return d.sort_values(["date", "match_id"]).reset_index(drop=True)


# --------------------------------------------------------------------------- #
# 95 · bowling with and without wickets
# --------------------------------------------------------------------------- #


def with_without(career, ids, player: str) -> dict:
    kind = kind_of_ids(career, ids)
    sp = spells(career, ids)
    mine = sp[sp.player == player]
    out = {}
    for label, g in (("with", mine[mine.wickets > 0]), ("without", mine[mine.wickets == 0])):
        balls = g.balls.sum()
        mdn = g.maidens.dropna()
        out[label] = dict(spells=len(g), wickets=int(g.wickets.sum()), runs=int(g.runs.sum()), balls=int(balls),
                          economy=g.runs.sum() / balls * 6 if balls else np.nan,
                          maidens_per_10=(mdn.sum() / (g.loc[mdn.index].balls.sum() / 6) * 10) if len(mdn) and balls else np.nan)
    out["kind"] = kind
    return out


# --------------------------------------------------------------------------- #
# 119 · achievements
# --------------------------------------------------------------------------- #


def achievements(career, ids=None) -> pd.DataFrame:
    """Badges earned in these matches (all of them by default): player, badge, date, match.
    Worked out on whole columns at once (a big career has tens of thousands of innings)."""
    from .stats import bars_for
    m = career.matches if ids is None else career.matches[career.matches.match_id.isin(ids)]
    ids = m.match_id
    info = m.set_index("match_id")
    kind_of = info.format.map(lambda f: KIND.get(f, "t20"))
    b = career.batting[career.batting.match_id.isin(ids) & career.batting.did_bat]
    w = career.bowling[career.bowling.match_id.isin(ids) & (career.bowling.balls > 0)]
    b = b.assign(kind=b.match_id.map(kind_of), date=b.match_id.map(info.date), section=b.match_id.map(info.section))
    w = w.assign(kind=w.match_id.map(kind_of), date=w.match_id.map(info.date))
    parts = []

    def add(df, badge, detail):
        if len(df):
            parts.append(pd.DataFrame({"player": df.player.to_numpy(), "team": df.team.to_numpy(), "badge": badge,
                                       "match_id": df.match_id.to_numpy(), "date": df.date.to_numpy(),
                                       "detail": list(detail)}))

    def score(df, balls=False):
        st_ = np.where(df.out.to_numpy(bool), "", "*")
        txt = [f"{r}{s}" for r, s in zip(df.runs, st_)]
        return [f"{t} ({x})" for t, x in zip(txt, df.balls)] if balls else txt

    # ---- batting feats by format
    t20 = b[b.kind == "t20"]
    x = t20[(t20.runs >= 50) & (t20.balls <= 20)]
    add(x, "Fifty off 20 balls or fewer", score(x, True))
    x = t20[t20.runs >= 100]
    add(x, "T20 hundred", score(x, True))
    x = t20[(t20.runs >= 100) & (t20.balls <= 50)]
    add(x, "Hundred at a strike rate of 200+", score(x, True))
    one = b[b.kind == "one"]
    for bar_, badge in ((150, "150 in a one-day game"), (200, "One-day double hundred")):
        x = one[one.runs >= bar_]
        add(x, badge, score(x))
    multi = b[b.kind == "multi"]
    for bar_, badge in ((200, "Double hundred"), (300, "Triple hundred")):
        x = multi[multi.runs >= bar_]
        add(x, badge, score(x))
    # ---- bowling feats by format
    for k, bar_, badge in (("t20", 5, "5-for in a T20"), ("one", 5, "One-day five-for"), ("multi", 7, "Seven in an innings")):
        x = w[(w.kind == k) & (w.wickets >= bar_)]
        add(x, badge, [f"{a}/{c}" for a, c in zip(x.wickets, x.runs)])
    # ---- multi-day match feats
    mb = b[b.kind == "multi"]
    if len(mb):
        g = mb.assign(h=mb.runs >= 100, z=(mb.runs == 0) & mb.out).groupby(["match_id", "player"], sort=False).agg(
            n=("runs", "size"), hundreds=("h", "sum"), ducks=("z", "sum"), team=("team", "first"), date=("date", "first"),
            detail=("runs", lambda r: " & ".join(map(str, r)))).reset_index()
        x = g[(g.n >= 2) & (g.hundreds >= 2)]
        add(x, "Hundred in both innings", x.detail)
        x = g[(g.n >= 2) & (g.ducks >= 2)]
        add(x, "Pair", ["0 & 0"] * len(x))
    mw = w[w.kind == "multi"]
    if len(mw):
        g = mw.assign(f=mw.wickets >= 5, fig=[f"{a}/{c}" for a, c in zip(mw.wickets, mw.runs)]).groupby(
            ["match_id", "player"], sort=False).agg(n=("wickets", "size"), wk=("wickets", "sum"), rs=("runs", "sum"),
                                                    fives=("f", "sum"), team=("team", "first"), date=("date", "first"),
                                                    figs=("fig", lambda f: " & ".join(f))).reset_index()
        x = g[g.wk >= 10]
        add(x, "Ten in a match", [f"{int(a)}/{int(c)}" for a, c in zip(x.wk, x.rs)])
        x = g[(g.n >= 2) & (g.fives >= 2)]
        add(x, "Five-for in both innings", x.figs)
    # ---- carried the bat: an opener not out when the innings was all out
    inn = career.innings[career.innings.match_id.isin(ids)][["match_id", "innings_no", "all_out", "runs"]]
    cand = b[(b.position <= 2) & ~b.out & (b.kind != "t20")].merge(inn.rename(columns={"runs": "total"}),
                                                                    on=["match_id", "innings_no"])
    x = cand[cand.all_out.astype(bool)]
    add(x, "Carried the bat", [f"{r}* of {int(t)}" for r, t in zip(x.runs, x.total)])
    # ---- hundred and five-for in the same match (any format)
    hb = set(zip(b[b.runs >= 100].match_id, b[b.runs >= 100].player))
    hw = set(zip(w[w.wickets >= 5].match_id, w[w.wickets >= 5].player))
    both = hb & hw
    if both:
        first_row = b.drop_duplicates(["match_id", "player"]).set_index(["match_id", "player"]).team
        x = pd.DataFrame([(mid, p, first_row[(mid, p)], info.date[mid]) for mid, p in both],
                         columns=["match_id", "player", "team", "date"])
        add(x, "Hundred and five-for in the same match", [""] * len(x))
    # ---- a hundred in a player's first game for a team in this section, when the team had already played 3+
    # games here without them (so it's a real debut, not just the start of your career's records)
    sec = info.section
    allb = career.batting[career.batting.match_id.isin(ids)]
    team_games = allb.drop_duplicates(["match_id", "team"]).assign(date=lambda x: x.match_id.map(info.date),
                                                                   section=lambda x: x.match_id.map(sec))
    # the debut is the first game they played (batting or not), and a hundred in either innings of it counts
    allw = career.bowling[career.bowling.match_id.isin(ids)]
    appear = pd.concat([allb[["match_id", "player", "team"]], allw[["match_id", "player", "team"]]]).drop_duplicates()
    appear = appear.assign(date=appear.match_id.map(info.date), section=appear.match_id.map(sec))
    debut = appear.sort_values(["date", "match_id"], kind="stable").groupby(["player", "team", "section"]).head(1)
    debut_games = set(zip(debut.match_id, debut.player, debut.team))
    in_debut = b[np.array([k in debut_games for k in zip(b.match_id, b.player, b.team)], dtype=bool)]  # (an empty list would pick columns)
    first = in_debut.sort_values(["runs", "innings_no"], ascending=[False, True], kind="stable") \
        .drop_duplicates(["match_id", "player", "team"])
    rows = []
    for r in first[first.runs >= 100].itertuples():
        before = team_games[(team_games.team == r.team) & (team_games.section == r.section) & (team_games.date < r.date)]
        if len(before) >= 3:
            rows.append((r.player, r.team, r.match_id, r.date, f"{r.runs}{'' if r.out else '*'}"))
    if rows:
        x = pd.DataFrame(rows, columns=["player", "team", "match_id", "date", "detail"])
        add(x, "Hundred on debut", x.detail)
    # ---- big games
    finals = set(m[m.stage == "Final"].match_id)
    x = b[b.match_id.isin(finals) & (b.runs >= 100)]
    add(x, "Hundred in a final", score(x))
    potm = m[m.match_id.isin(finals) & (m.player_of_match != "")]
    if len(potm):
        team_of = b.drop_duplicates(["match_id", "player"]).set_index(["match_id", "player"]).team
        x = pd.DataFrame({"player": potm.player_of_match.to_numpy(), "match_id": potm.match_id.to_numpy(),
                          "date": potm.date.to_numpy(),
                          "team": [team_of.get((a, p), "") for a, p in zip(potm.match_id, potm.player_of_match)]})
        add(x, "Player of the Match in a final", [""] * len(x))
    # ---- streaks: three big scores in a row (the format's bar), counted once per run
    s_ = b.sort_values(["date", "innings_no"], kind="stable")
    s_ = s_.assign(_o=np.arange(len(s_))).sort_values(["player", "section", "_o"], kind="stable")
    bar_of = {k: bars_for(k)["big"] for k in ("t20", "one", "multi")}
    first_kind = s_.groupby(["player", "section"], sort=False).kind.transform("first")
    bars = first_kind.map(bar_of).to_numpy()
    runs = s_.runs.to_numpy()
    pl, se = s_.player.to_numpy(), s_.section.to_numpy()
    hits = []
    run = 0
    for i in range(len(s_)):
        if i == 0 or pl[i] != pl[i - 1] or se[i] != se[i - 1]:
            run = 0
        run = run + 1 if runs[i] >= bars[i] else 0
        if run == 3:
            hits.append(i)
    if hits:
        x = s_.iloc[hits]
        add(x, "", x.section)
        parts[-1]["badge"] = [f"Three {int(bv)}s in a row" for bv in bars[hits]]  # the bar of that section's format
    cols = ["player", "team", "badge", "match_id", "date", "detail"]
    d = pd.concat(parts, ignore_index=True)[cols] if parts else pd.DataFrame(columns=cols)
    return d.sort_values(["date", "badge", "player"], ascending=[False, True, True], kind="stable").reset_index(drop=True)


def team_achievements(career, team: str) -> pd.DataFrame:
    """Badges for a team you manage: clean sweeps, unbeaten league seasons, titles."""
    from .extras import honours
    from .teamplay import series_games
    m = career.matches
    rows = []
    s = series_games(career, m[(m.home == team) | (m.away == team)].match_id)
    s = s[s.team == team]
    for sid, g in s.groupby("series_id"):
        if g.complete.all() and len(g) >= 3 and (g.outcome == "W").all():
            sec = m.set_index("match_id").section.get(g.match_id.iloc[0], "")
            rows.append(dict(badge=f"Clean sweep {len(g)}–0", detail=f"v {g.opponent.iloc[0]}, {sec}", date=g.date.max()))
    for (ev, se), g in m[~m.knockout & ((m.home == team) | (m.away == team))].groupby(["event", "season"]):
        if len(g) >= 5 and g.level.iloc[0] not in ("International", "Exhibition", "Tour") and not (g.loser == team).any():
            rows.append(dict(badge="Unbeaten league season", detail=f"{ev} {se}", date=g.date.max()))
    h = honours(career)
    for r in h[h.champion_teams.map(lambda t: team in t) & ~h.how.str.contains("so far")].itertuples():
        rows.append(dict(badge="Champions", detail=f"{r.section} {r.season}", date=r.date))
    return pd.DataFrame(rows, columns=["badge", "detail", "date"]).sort_values("date", ascending=False).reset_index(drop=True)


# --------------------------------------------------------------------------- #
# 120 · batter v bowler
# --------------------------------------------------------------------------- #


def batter_v_bowler(career, batter: str, bowler: str, ids=None) -> dict:
    """Every innings in which the batter batted while the bowler bowled at their side."""
    bat = career.batting[career.batting.did_bat & (career.batting.player == batter)]
    bowl = career.bowling[(career.bowling.player == bowler) & (career.bowling.balls > 0)]
    if ids is not None:
        bat = bat[bat.match_id.isin(ids)]
        bowl = bowl[bowl.match_id.isin(ids)]
    met = bat.merge(bowl[["match_id", "innings_no", "team", "wickets", "runs"]].rename(
        columns={"team": "bowl_team", "wickets": "bowl_wkts", "runs": "bowl_runs"}), on=["match_id", "innings_no"])
    met = met[met.bowl_team != met.team]
    met = met.merge(career.matches[["match_id", "date", "section"]], on="match_id").sort_values("date")
    got = met[met.out & (met.bowler == bowler)]
    return dict(innings=met, dismissals=len(got), meetings=len(met),
                runs=int(met.runs.sum()), runs_when_out=int(got.runs.sum()))


def faced(career, ids=None, batter: str = "", bowler: str = "") -> pd.DataFrame:
    """Every bowler a batter has met (bowling at their side while they batted), or every batter a bowler has
    bowled at: innings met, how often that bowler got them out, and the batter's runs in those innings.
    Most dismissals first (then most meetings)."""
    bat = career.batting[career.batting.did_bat]
    bowl = career.bowling[career.bowling.balls > 0]
    if ids is not None:
        bat = bat[bat.match_id.isin(ids)]
        bowl = bowl[bowl.match_id.isin(ids)]
    if batter:
        bat = bat[bat.player == batter]
    if bowler:
        bowl = bowl[bowl.player == bowler]
    met = bat.merge(bowl[["match_id", "innings_no", "team", "player"]].rename(
        columns={"team": "bowl_team", "player": "bowl_player"}), on=["match_id", "innings_no"])
    met = met[met.bowl_team != met.team]
    cols = ["name", "innings", "dismissals", "runs"]
    if met.empty:
        return pd.DataFrame(columns=cols)
    met = met.assign(got=met.out & (met.bowler == met.bowl_player))
    key = "bowl_player" if batter else "player"
    g = (met.groupby(key).agg(innings=("match_id", "size"), dismissals=("got", "sum"), runs=("runs", "sum"))
         .reset_index().rename(columns={key: "name"}))
    g["dismissals"] = g.dismissals.astype(int)
    return g.sort_values(["dismissals", "innings", "name"], ascending=[False, False, True]).reset_index(drop=True)[cols]


# --------------------------------------------------------------------------- #
# 140 · all formats side by side · 134 · career card
# --------------------------------------------------------------------------- #


def judged_on(role) -> str:
    """What a player is judged on in a competition, from their role there: a bowler on bowling, an all-rounder on the
    better of the two ("both"), every batting role on batting; no role (under 3 matches there) the better of the two."""
    if role == "Bowler":
        return "bowl"
    if role == "All-rounder" or not isinstance(role, str) or not role:
        return "both"
    return "bat"


def format_score(job: str, bat_vs: float, matches: int, bowl_vs: float, wickets: int) -> tuple[float, str]:
    """How far above the average player there they are at their job (in %), and which side it came from ("bat" or
    "bowl"; "" for none). Batting counts from 3 matches, bowling from 5 wickets; "both" takes the better (batting if
    level)."""
    bat = bat_vs if matches >= 3 and np.isfinite(bat_vs) else np.nan
    bowl = bowl_vs if wickets >= 5 and np.isfinite(bowl_vs) else np.nan
    sides = [(v, k) for v, k in ((bat, "bat"), (bowl, "bowl")) if np.isfinite(v) and (job == "both" or job == k)]
    return max(sides, key=lambda x: x[0]) if sides else (np.nan, "")


def roles_in(career, section: str) -> dict:
    """Each player's role in one competition (analysis.role_labels on its matches), kept with the career until its
    matches change."""
    from .analysis import role_labels
    stamp = (id(career.matches), len(career.matches))
    box = getattr(career, "_roles_in", None)
    if box is None or box.get("_stamp") != stamp:
        box = {"_stamp": stamp}
        try:
            career._roles_in = box
        except AttributeError:
            pass
    if section not in box:
        m = career.matches[career.matches.section == section]
        r = role_labels(career, pd.Index(m.match_id), KIND.get(m.format.iloc[0], "multi")) if len(m) else pd.DataFrame()
        box[section] = dict(zip(r.player, r.role)) if len(r) else {}
    return box[section]


def all_formats(career, player: str) -> pd.DataFrame:
    """One row per section the player has played: batting and bowling against
    that section's average (so the formats can be compared), and the best one,
    each judged on what they're picked for there (see judged_on)."""
    from .competitions import ordered
    from .stats import Scope, player_tables
    secs = ordered(career.matches, career.matches[career.matches.match_id.isin(   # the agreed order (14 November)
        set(career.batting[career.batting.player == player].match_id))].section.unique())
    rows = []
    for sec in secs:
        bat, bowl, _, base = player_tables(career, Scope(sections=[sec]))
        b = bat[bat.player == player]
        w = bowl[bowl.player == player]
        r = dict(section=sec, matches=int(b.matches.iloc[0]) if len(b) else 0, runs=int(b.runs.iloc[0]) if len(b) else 0,
                 average=b.average.iloc[0] if len(b) else np.nan, strike_rate=b.strike_rate.iloc[0] if len(b) else np.nan,
                 hundreds=int(b.hundreds.iloc[0]) if len(b) else 0, wickets=int(w.wickets.iloc[0]) if len(w) else 0,
                 bowl_average=w.average.iloc[0] if len(w) else np.nan, economy=w.economy.iloc[0] if len(w) else np.nan)
        r["bat_vs"] = (r["average"] / base.average - 1) * 100 if np.isfinite(r["average"]) and base.average else np.nan
        r["sr_vs"] = (r["strike_rate"] / base.strike_rate - 1) * 100 if np.isfinite(r["strike_rate"]) and base.strike_rate else np.nan
        r["bowl_vs"] = ((base.bowl_average / r["bowl_average"] - 1) * 100
                        if np.isfinite(r["bowl_average"]) and r["bowl_average"] and np.isfinite(base.bowl_average) else np.nan)
        r["job"] = judged_on(roles_in(career, sec).get(player))
        r["score"], r["judged"] = format_score(r["job"], r["bat_vs"], r["matches"], r["bowl_vs"], r["wickets"])
        rows.append(r)
    d = pd.DataFrame(rows)
    if len(d) and d.score.notna().any():
        d["best"] = d.score == d.score.max()
    else:
        d["best"] = False
    return d
