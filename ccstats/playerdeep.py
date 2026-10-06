"""Deeper player numbers, each with format-specific rules: danger zones,
conversion funnel, fastest to milestones, rank over time, match impact,
bowling with and without wickets, achievements, batter v bowler, the career
card and the all-format view."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .players import innings, kind_of_ids, spells
from .stats import KIND

# --------------------------------------------------------------------------- #
# 89 · danger zones
# --------------------------------------------------------------------------- #

ZONES = {"t20": [(0, 9), (10, 19), (20, 29), (30, 49), (50, None)],
         "one": [(0, 9), (10, 29), (30, 49), (50, 99), (100, None)],
         "multi": [(0, 9), (10, 29), (30, 49), (50, 99), (100, 149), (150, None)]}


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

FUNNEL = {"t20": ([10, 20, 30, 40, 50, 75, 100], [20, 50]),
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


def match_impact(career, ids) -> pd.DataFrame:
    """One number per player per match.  Batting: runs, and in white-ball cricket
    half the runs above (or below) what the section's strike rate would have made
    off the same balls.  Bowling: wickets worth the section's runs per wicket, plus
    in white-ball cricket the runs kept below the section's economy.  Fielding: a
    catch or stumping is a quarter of a wicket."""
    kind = kind_of_ids(career, ids)
    m = career.matches[career.matches.match_id.isin(ids)]
    inn_all = career.innings[career.innings.match_id.isin(ids)]
    rpw = inn_all.runs.sum() / max(inn_all.wickets.sum(), 1)
    b = career.batting[career.batting.match_id.isin(ids) & career.batting.did_bat]
    w = career.bowling[career.bowling.match_id.isin(ids) & (career.bowling.balls > 0)]
    f = career.fielding[career.fielding.match_id.isin(ids) & career.fielding.resolved]
    sr = b.runs.sum() / max(b.balls.sum(), 1)
    econ = w.runs.sum() / max(w.balls.sum(), 1)
    white = kind != "multi"
    bat = b.assign(pts=b.runs + ((b.runs - b.balls * sr) * 0.5 if white else 0)) \
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
    """Badges earned in these matches (all of them by default): player, badge, date, match."""
    m = career.matches if ids is None else career.matches[career.matches.match_id.isin(ids)]
    ids = m.match_id
    info = m.set_index("match_id")
    kind_of = info.format.map(lambda f: KIND.get(f, "t20"))
    b = career.batting[career.batting.match_id.isin(ids) & career.batting.did_bat].copy()
    w = career.bowling[career.bowling.match_id.isin(ids) & (career.bowling.balls > 0)].copy()
    b["kind"] = b.match_id.map(kind_of)
    w["kind"] = w.match_id.map(kind_of)
    b["date"] = b.match_id.map(info.date)
    w["date"] = w.match_id.map(info.date)
    rows = []

    def add(player, team, badge, mid, date, detail=""):
        rows.append(dict(player=player, team=team, badge=badge, match_id=mid, date=date, detail=detail))

    for r in b.itertuples():
        star = "" if r.out else "*"
        if r.kind == "t20":
            if r.runs >= 50 and r.balls <= 20:
                add(r.player, r.team, "Fifty off 20 balls or fewer", r.match_id, r.date, f"{r.runs}{star} ({r.balls})")
            if r.runs >= 100:
                add(r.player, r.team, "T20 hundred", r.match_id, r.date, f"{r.runs}{star} ({r.balls})")
            if r.runs >= 100 and r.balls <= 50:
                add(r.player, r.team, "Hundred at a strike rate of 200+", r.match_id, r.date, f"{r.runs}{star} ({r.balls})")
        elif r.kind == "one":
            if r.runs >= 150:
                add(r.player, r.team, "150 in a one-day game", r.match_id, r.date, f"{r.runs}{star}")
            if r.runs >= 200:
                add(r.player, r.team, "One-day double hundred", r.match_id, r.date, f"{r.runs}{star}")
        else:
            if r.runs >= 200:
                add(r.player, r.team, "Double hundred", r.match_id, r.date, f"{r.runs}{star}")
            if r.runs >= 300:
                add(r.player, r.team, "Triple hundred", r.match_id, r.date, f"{r.runs}{star}")
    for r in w.itertuples():
        if r.kind == "t20" and r.wickets >= 5:
            add(r.player, r.team, "5-for in a T20", r.match_id, r.date, f"{r.wickets}/{r.runs}")
        elif r.kind == "one" and r.wickets >= 5:
            add(r.player, r.team, "One-day five-for", r.match_id, r.date, f"{r.wickets}/{r.runs}")
        elif r.kind == "multi" and r.wickets >= 7:
            add(r.player, r.team, "Seven in an innings", r.match_id, r.date, f"{r.wickets}/{r.runs}")
    # multi-day match feats
    mb = b[b.kind == "multi"]
    mw = w[w.kind == "multi"]
    for (mid, p), g in mb.groupby(["match_id", "player"]):
        if len(g) >= 2 and (g.runs >= 100).sum() >= 2:
            add(p, g.team.iloc[0], "Hundred in both innings", mid, g.date.iloc[0], " & ".join(map(str, g.runs)))
        if len(g) >= 2 and ((g.runs == 0) & g.out).sum() >= 2:
            add(p, g.team.iloc[0], "Pair", mid, g.date.iloc[0], "0 & 0")
    for (mid, p), g in mw.groupby(["match_id", "player"]):
        if g.wickets.sum() >= 10:
            add(p, g.team.iloc[0], "Ten in a match", mid, g.date.iloc[0], f"{int(g.wickets.sum())}/{int(g.runs.sum())}")
        if len(g) >= 2 and (g.wickets >= 5).sum() >= 2:
            add(p, g.team.iloc[0], "Five-for in both innings", mid, g.date.iloc[0],
                " & ".join(f"{a}/{c}" for a, c in zip(g.wickets, g.runs)))
    # carried the bat: an opener not out when the innings was all out
    inn = career.innings[career.innings.match_id.isin(ids)].set_index(["match_id", "innings_no"])
    for r in b[(b.position <= 2) & ~b.out & (b.kind != "t20")].itertuples():
        k = (r.match_id, r.innings_no)
        if k in inn.index and bool(inn.loc[k, "all_out"]):
            add(r.player, r.team, "Carried the bat", r.match_id, r.date, f"{r.runs}* of {int(inn.loc[k, 'runs'])}")
    # hundred and five-for in the same match (any format)
    hb = set(zip(b[b.runs >= 100].match_id, b[b.runs >= 100].player))
    hw = set(zip(w[w.wickets >= 5].match_id, w[w.wickets >= 5].player))
    for mid, p in hb & hw:
        add(p, b[(b.match_id == mid) & (b.player == p)].team.iloc[0], "Hundred and five-for in the same match", mid,
            info.date[mid])
    # a hundred in a player's first game for a team in this section, when the team had already played 3+
    # games here without them (so it's a real debut, not just the start of your career's records)
    sec = info.section
    allb = career.batting[career.batting.match_id.isin(ids)].assign(date=lambda x: x.match_id.map(info.date),
                                                                  section=lambda x: x.match_id.map(sec))
    team_games = allb.drop_duplicates(["match_id", "team"]).sort_values("date")
    first = b.assign(section=b.match_id.map(sec)).sort_values("date").groupby(["player", "team", "section"]).head(1)
    for r in first[first.runs >= 100].itertuples():
        before = team_games[(team_games.team == r.team) & (team_games.section == r.section) & (team_games.date < r.date)]
        if len(before) >= 3:
            add(r.player, r.team, "Hundred on debut", r.match_id, r.date, f"{r.runs}{'' if r.out else '*'}")
    # big games
    finals = set(m[m.stage == "Final"].match_id)
    for r in b[b.match_id.isin(finals) & (b.runs >= 100)].itertuples():
        add(r.player, r.team, "Hundred in a final", r.match_id, r.date, f"{r.runs}{'' if r.out else '*'}")
    for r in m[m.match_id.isin(finals) & (m.player_of_match != "")].itertuples():
        t = b[(b.match_id == r.match_id) & (b.player == r.player_of_match)].team
        add(r.player_of_match, t.iloc[0] if len(t) else "", "Player of the Match in a final", r.match_id, r.date)
    # streaks: big scores in a row (format bar)
    from .stats import bars_for
    for (p, sec_), g in b.assign(section=b.match_id.map(sec)).sort_values(["date", "innings_no"]).groupby(["player", "section"]):
        bar = bars_for(g.kind.iloc[0])["big"]
        run = 0
        for r in g.itertuples():
            run = run + 1 if r.runs >= bar else 0
            if run == 3:
                add(p, r.team, f"Three {bar}s in a row", r.match_id, r.date, sec_)
    d = pd.DataFrame(rows, columns=["player", "team", "badge", "match_id", "date", "detail"])
    return d.sort_values("date", ascending=False).reset_index(drop=True)


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
            rows.append(dict(badge=f"Clean sweep {len(g)}–0", detail=f"v {g.opponent.iloc[0]}", date=g.date.max()))
    for (ev, se), g in m[~m.knockout & ((m.home == team) | (m.away == team))].groupby(["event", "season"]):
        if len(g) >= 5 and g.level.iloc[0] != "International" and not (g.loser == team).any():
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


# --------------------------------------------------------------------------- #
# 140 · all formats side by side · 134 · career card
# --------------------------------------------------------------------------- #


def all_formats(career, player: str) -> pd.DataFrame:
    """One row per section the player has played: batting and bowling against
    that section's average (so the formats can be compared), and the best one."""
    from .stats import Scope, player_tables
    secs = career.matches[career.matches.match_id.isin(
        set(career.batting[career.batting.player == player].match_id))].section.value_counts().index
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
        score = np.nanmax([r["bat_vs"] if r["matches"] >= 3 else np.nan,
                           r["bowl_vs"] if r["wickets"] >= 5 else np.nan]) if (r["matches"] >= 3 or r["wickets"] >= 5) else np.nan
        r["score"] = score if np.isfinite(score) else np.nan
        rows.append(r)
    d = pd.DataFrame(rows)
    if len(d) and d.score.notna().any():
        d["best"] = d.score == d.score.max()
    else:
        d["best"] = False
    return d
