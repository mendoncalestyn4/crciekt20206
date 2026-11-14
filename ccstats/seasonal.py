"""Records over time, near misses, best XIs, ranking history, selection against an
opponent, the after-match summary, the end-of-season review, league table extras
and the World Test Championship table.  Format rules come from the format of the
matches (T20 / one-day / multi-day), as everywhere else."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from . import records as RC
from .players import innings, kind_of_ids, spells
from .stats import bars_for, counts_fielding

# --------------------------------------------------------------------------- #
# 104 · record timeline
# --------------------------------------------------------------------------- #

TIMELINE = ["Highest team totals", "Lowest completed totals", "Highest individual scores", "Best bowling in an innings",
            "Best bowling in a match", "Highest partnerships", "Most sixes in an innings", "Biggest wins by runs",
            "Most runs in a season", "Most wickets in a season"]


def record_timeline(career, ids) -> pd.DataFrame:
    """Every time a record was set or beaten, in match-date order.
    One row per step: record, holder, value, team, against, date, match_id, source,
    step (0 = the first mark), until (the date it was beaten, NaT if it still stands)."""
    full = RC.records(career, ids, top=10 ** 9)
    po = RC.played_order(career)
    pos = dict(zip(po.match_id, range(len(po))))
    rows = []
    for name in TIMELINE:
        t = full.get(name)
        if t is None or t.empty:
            continue
        low = name.startswith("Lowest")
        # by match date, as record books are (files saved out of order don't jumble it); same day: the order played.
        # A season total counts from the season's last game.
        key = list(zip(t.date, t.match_id.map(pos)))
        t = t.assign(_k=key).sort_values("_k", kind="stable")
        best = None
        steps = []
        # what has to be beaten: the score itself (150* only equals 150) and the wickets (fewer runs conceded don't
        # beat the same number of wickets in a season); best figures do count fewer runs (7/40 beats 7/50)
        plain = name in ("Highest individual scores", "Most wickets in a season")
        for r in t.itertuples():
            v = record_number(name, r.sort) if plain else r.sort
            if best is None or (v < best if low else v > best):  # equalling a record isn't beating it
                best = v
                steps.append(dict(record=name, holder=r.holder, value=r.value, team=r.team, against=r.against,
                                  date=r.date, match_id=r.match_id, source=r.source, sort=r.sort))
        for i, s in enumerate(steps):
            s["step"] = i
            s["until"] = steps[i + 1]["date"] if i + 1 < len(steps) else pd.NaT
        rows += steps
    return pd.DataFrame(rows, columns=["record", "holder", "value", "team", "against", "date", "match_id", "source", "sort",
                                       "step", "until"])


def record_number(name: str, sort: float) -> float:
    """The plain number a record stands on (runs, wickets, sixes), from its sort key."""
    if name == "Highest individual scores":
        return float(int(sort) // 2)
    if name in ("Best bowling in an innings", "Best bowling in a match"):
        return float(_split(sort, 1000)[0])
    if name == "Most wickets in a season":
        return float(_split(sort, 100000)[0])
    return float(sort)


RECORD_UNIT = {"Best bowling in an innings": "wickets", "Best bowling in a match": "wickets",
               "Most wickets in a season": "wickets", "Most sixes in an innings": "sixes"}


# --------------------------------------------------------------------------- #
# 105 · near misses
# --------------------------------------------------------------------------- #


def _split(k: float, unit: int) -> tuple[int, int]:
    """(wickets, runs) from a sort key wickets * unit - runs (runs < unit)."""
    w = -(-int(k) // unit)
    return w, w * unit - int(k)


def near_miss(name: str, t: pd.DataFrame) -> str:
    """'closest: 131 by Rahul (9 short)' for a record list (from records()), or ''
    when nobody else is on the list.  A shared record says so."""
    if t is None or len(t) < 2:
        return ""
    top = t[t["rank"] == 1]
    if len(top) > 1:
        return f"shared by {len(top)}: " + ", ".join(top.holder.astype(str))
    r0, r1 = t.iloc[0], t[t["rank"] > 1].iloc[0]
    s0, s1 = float(r0["sort"]), float(r1["sort"])
    if name == "Highest individual scores":
        g = int(s0 // 2 - s1 // 2)
        gap = f"{g} run{'s' if g != 1 else ''} short" if g else "the same score, but out"
    elif name in ("Best bowling in an innings", "Best bowling in a match", "Most wickets in a season"):
        unit = 100000 if "season" in name else 1000
        (w0, c0), (w1, c1) = _split(s0, unit), _split(s1, unit)
        gap = (f"{w0 - w1} wicket{'s' if w0 - w1 != 1 else ''} short" if w0 != w1
               else f"the same wickets for {c1 - c0} more run{'s' if c1 - c0 != 1 else ''}")
    elif name.startswith("Lowest"):
        g = int(s1 - s0)
        gap = f"{g} run{'s' if g != 1 else ''} more"
    else:
        unit = "six" if "sixes" in name else "run"
        g = int(s0 - s1)
        gap = f"{g} {unit}{'es' if unit == 'six' and g != 1 else 's' if g != 1 else ''} short"
    who = r1.holder
    return f"closest: {r1.value} by {who} ({gap})"


# --------------------------------------------------------------------------- #
# 106 · Team of the Season and all-time XIs
# --------------------------------------------------------------------------- #

# the slots, in team-sheet order
SHAPE = {"t20": [("Opener", 2), ("Middle order", 2), ("Finisher", 1), ("Keeper", 1), ("All-rounder", 1), ("Bowler", 4)],
         "one": [("Opener", 2), ("Middle order", 3), ("Keeper", 1), ("All-rounder", 1), ("Bowler", 4)],
         "multi": [("Opener", 2), ("Middle order", 3), ("Keeper", 1), ("All-rounder", 1), ("Bowler", 4)]}
MIDDLE = {"t20": (3, 5), "one": (3, 6), "multi": (3, 6)}
FINISH = (5, 7)


def _mode_group(pos: pd.Series) -> int:
    """The batting position a player usually took (the lower one on a tie)."""
    c = pos.value_counts()
    return int(min(c[c == c.max()].index))


def player_pool(career, ids, team: str = "") -> tuple[pd.DataFrame, dict]:
    """One row per player with their batting and bowling in these matches (for one
    team, or for everyone) and the measures the XI is picked on, plus the
    section averages (from every team, so the bar doesn't move with the team)."""
    kind = kind_of_ids(career, ids)
    b_all = innings(career, ids)
    w_all = spells(career, ids)
    inn = career.innings[career.innings.match_id.isin(ids)]
    base = dict(kind=kind,
                avg=b_all.runs.sum() / max(b_all.out.sum(), 1),
                sr=b_all.runs.sum() / max(b_all.balls.sum(), 1) * 100,
                bowl_avg=w_all.runs.sum() / max(w_all.wickets.sum(), 1),
                bowl_sr=w_all.balls.sum() / max(w_all.wickets.sum(), 1),
                econ=w_all.runs.sum() / max(w_all.balls.sum(), 1) * 6,
                rpw=inn.runs.sum() / max(inn.wickets.sum(), 1))
    xi = career.batting[career.batting.match_id.isin(ids)]
    b, w = b_all, w_all
    if team:
        xi, b, w = xi[xi.team == team], b[b.team == team], w[w.team == team]
    games = xi.groupby("player").match_id.nunique()
    last_team = xi.assign(d=xi.match_id.map(career.matches.set_index("match_id").date)).sort_values("d") \
        .groupby("player").team.last()
    f = career.fielding[career.fielding.match_id.isin(ids) & career.fielding.resolved]
    if team:
        f = f[f.team == team]
    stumpings = f[f.kind == "stumped"].groupby("player").size()
    catches = f[f.kind != "stumped"].groupby("player").size()
    bat = b.groupby("player").agg(inns=("runs", "size"), runs=("runs", "sum"), outs=("out", "sum"), balls=("balls", "sum"),
                                  hs=("runs", "max"), pos=("position", _mode_group),
                                  top=("position", lambda p: (p <= 2).mean()))
    bowl = w.groupby("player").agg(spells=("wickets", "size"), wkts=("wickets", "sum"), conceded=("runs", "sum"),
                                   bowled=("balls", "sum"), fivefor=("wickets", lambda x: int((x >= 5).sum())))
    d = pd.DataFrame(index=sorted(set(games.index)))
    d = d.join(bat).join(bowl)
    d["games"] = games
    d["team"] = last_team
    d["stumpings"] = stumpings.reindex(d.index).fillna(0).astype(int)
    d["catches"] = catches.reindex(d.index).fillna(0).astype(int)
    for c in ("inns", "runs", "outs", "balls", "spells", "wkts", "conceded", "bowled", "fivefor"):
        d[c] = d[c].fillna(0).astype(int)
    d["avg"] = d.runs / d.outs.clip(lower=1)
    d["sr"] = np.where(d.balls > 0, d.runs / d.balls.clip(lower=1) * 100, np.nan)
    d["bowl_avg"] = np.where(d.wkts > 0, d.conceded / d.wkts.clip(lower=1), np.nan)
    d["bowl_sr"] = np.where(d.wkts > 0, d.bowled / d.wkts.clip(lower=1), np.nan)
    d["econ"] = np.where(d.bowled > 0, d.conceded / d.bowled.clip(lower=1) * 6, np.nan)
    # batting: average in multi-day cricket; average x strike rate / 100 in white-ball cricket
    d["bat_score"] = d.avg if kind == "multi" else d.avg * d.sr.fillna(0) / 100
    base["bat_score"] = base["avg"] if kind == "multi" else base["avg"] * base["sr"] / 100
    # bowling: white ball = each wicket worth the section's runs per wicket + runs kept below the section's economy;
    # multi-day = wickets, worth more the lower the average and strike rate, + 2 a five-for
    if kind == "multi":
        ratio = (base["bowl_avg"] / d.bowl_avg + base["bowl_sr"] / d.bowl_sr) / 2
        d["bowl_score"] = (d.wkts * ratio.fillna(0) + 2 * d.fivefor).where(d.wkts > 0, 0.0)
    else:
        d["bowl_score"] = d.wkts * base["rpw"] + (d.bowled * base["econ"] / 6 - d.conceded)
    # per innings (for all-rounders and finishers: an average flattered by not-outs at no. 10 doesn't count)
    d["rpi"] = d.runs / d.inns.clip(lower=1)
    d["bat_rpi"] = d.rpi if kind == "multi" else d.rpi * d.sr.fillna(0) / 100
    rpi_all = b_all.runs.sum() / max(len(b_all), 1)
    base["bat_rpi"] = rpi_all if kind == "multi" else rpi_all * base["sr"] / 100
    # the bowling measure per spell for the section as a whole (the economy part adds up to 0 over everyone)
    n_sp = max(len(w_all), 1)
    base["bowl_per_spell"] = (w_all.wickets.sum() * base["rpw"] / n_sp if kind != "multi"
                              else (w_all.wickets.sum() + 2 * (w_all.wickets >= 5).sum()) / n_sp)
    d.index.name = "player"
    return d.reset_index(), base


def _bat_why(r, kind) -> str:
    sr = f", SR {r.sr:.0f}" if kind != "multi" and np.isfinite(r.sr) else ""
    where = f" (usually #{int(r.pos)})" if pd.notna(r.pos) else ""
    return f"{r.runs} runs at {r.avg:.1f}{sr} in {r.inns} inns{where}"


def _bowl_why(r, kind) -> str:
    if kind == "multi":
        ff = f", {r.fivefor} five-for{'s' if r.fivefor != 1 else ''}" if r.fivefor else ""
        return f"{r.wkts} wkt{'' if r.wkts == 1 else 's'} at {r.bowl_avg:.1f}, SR {r.bowl_sr:.0f}{ff}"
    return f"{r.wkts} wkt{'' if r.wkts == 1 else 's'}, econ {r.econ:.2f}" + (f", avg {r.bowl_avg:.1f}" if r.wkts else "")


def best_xi(career, ids, team: str = "") -> pd.DataFrame:
    """An XI picked by role from the numbers.  Openers and middle order on the
    batting measure (average in multi-day cricket; average x strike rate in white
    ball), a finisher (T20, batting 5-7) on runs per innings x strike rate, a keeper
    (made a stumping), an all-rounder (top 8 bat) on runs per innings x bowling,
    each against the section average, and 4 bowlers
    on the bowling measure.  Only players with enough games count (a third of the
    most games anyone played here, at least 2)."""
    d, base = player_pool(career, ids, team)
    cols = ["slot", "player", "team", "why", "games"]
    if d.empty:
        return pd.DataFrame(columns=cols)
    kind = base["kind"]
    most = int(d.games.max())
    need = max(2, math.ceil(most / 3))
    bat_ok = d[d.inns >= need]
    bowl_ok = d[d.spells >= need]
    taken: list[str] = []
    picks = []

    def take(pool: pd.DataFrame, by: list[str], slot: str, n: int, why) -> int:
        pool = pool[~pool.player.isin(taken)].sort_values(by + ["player"], ascending=[False] * len(by) + [True])
        got = 0
        for r in pool.head(n).itertuples():
            taken.append(r.player)
            picks.append(dict(slot=slot, player=r.player, team=r.team, why=why(r), games=int(r.games)))
            got += 1
        return got

    lo, hi = MIDDLE[kind]
    for slot, n in SHAPE[kind]:
        if slot == "Opener":
            got = take(bat_ok[bat_ok.top >= 0.5], ["bat_score", "runs"], slot, n, lambda r: _bat_why(r, kind))
        elif slot == "Middle order":
            got = take(bat_ok[bat_ok.pos.between(lo, hi)], ["bat_score", "runs"], slot, n, lambda r: _bat_why(r, kind))
        elif slot == "Finisher":  # runs per innings x strike rate, batting 5-7, with real volume
            fin = bat_ok[bat_ok.pos.between(*FINISH) & (bat_ok.balls >= 6 * need)]
            got = take(fin, ["bat_rpi", "runs"], slot, n, lambda r: _bat_why(r, kind))
        elif slot == "Keeper":
            keepers = d[(d.stumpings > 0)]
            already = [p for p in taken if p in set(keepers.player)]
            if already:  # the keeper is already in as a batter: say so, and pick one more batter
                for p_ in picks:
                    if p_["player"] == already[0]:
                        p_["slot"] += " · keeper"
                got = take(bat_ok[bat_ok.pos <= hi], ["bat_score", "runs"], "Extra batter", n,
                           lambda r: _bat_why(r, kind))
            else:
                k_ok = keepers[keepers.games >= need]
                # the keeper is found from stumpings quietly; with no fielding counted (the new site) his catches and
                # stumpings aren't said
                field = counts_fielding(career)
                got = take(k_ok if len(k_ok) else keepers, ["bat_score", "stumpings"], slot, n,
                           lambda r: (f"{r.stumpings + r.catches} dismissals ({r.stumpings} st), " if field else "")
                           + _bat_why(r, kind))
        elif slot == "All-rounder":  # bats in the top 8 and bowls: both halves against the section's average
            both = d[(d.inns >= need) & (d.spells >= need) & (d.wkts > 0) & (d.pos <= 8)]
            both = both.assign(ar=(both.bat_rpi / base["bat_rpi"]).clip(lower=0)
                               * (both.bowl_score / both.spells.clip(lower=1) / base["bowl_per_spell"]).clip(lower=0))
            got = take(both, ["ar", "wkts"], slot, n,
                       lambda r: f"{r.runs} runs ({r.rpi:.1f} an inns) · " + _bowl_why(r, kind))
        else:
            got = take(bowl_ok[bowl_ok.wkts > 0], ["bowl_score", "wkts"], slot, n, lambda r: _bowl_why(r, kind))
        if got < n:  # not enough of that role: the best of the rest at what the slot needs
            rest = d[~d.player.isin(taken)]
            if slot == "Bowler":
                take(rest[rest.spells > 0], ["bowl_score", "wkts"], slot + " (best available)", n - got,
                     lambda r: _bowl_why(r, kind))
            elif slot == "All-rounder":
                rest = rest[(rest.inns > 0) & (rest.spells > 0)]
                take(rest.assign(any_=rest.bat_rpi.rank(pct=True) + rest.bowl_score.rank(pct=True)), ["any_", "games"],
                     slot + " (best available)", n - got, lambda r: f"{r.runs} runs · " + _bowl_why(r, kind))
            else:
                take(rest[rest.inns > 0], ["bat_rpi", "runs"], slot + " (best available)", n - got,
                     lambda r: _bat_why(r, kind))
    out = pd.DataFrame(picks, columns=cols)
    out.attrs.update(need=need, kind=kind, base=base)
    return out


# --------------------------------------------------------------------------- #
# 107 · rankings history, combined international rating
# --------------------------------------------------------------------------- #


def ranking_history(career, section: str, what: str = "batting") -> tuple[pd.DataFrame, pd.DataFrame]:
    """(one row per player: peak rating and when, current rating, matches at No. 1;
    the No. 1 reigns in order).  The rating after every match is worked out as on
    the Rankings page at that moment (same points, same recent-form weighting, same
    scale), so the peak is the rating they really had then."""
    from . import rankings as R
    bat, bowl = R.innings_points(career, section)
    d = bat if what == "batting" else bowl
    cols = ["player", "team", "peak", "peak_date", "current", "at_no1", "innings"]
    if d.empty:
        return pd.DataFrame(columns=cols), pd.DataFrame(columns=["player", "from", "to", "matches"])
    m = career.matches[career.matches.section == section].sort_values(["date", "match_id"])
    s_: dict[str, float] = {}
    w_: dict[str, float] = {}
    n_: dict[str, int] = {}
    team: dict[str, str] = {}
    peak: dict[str, tuple[float, pd.Timestamp]] = {}
    at1: dict[str, int] = {}
    reigns = []
    by_match = {k: g for k, g in d.groupby("match_id", sort=False)}
    current = {}
    for mid, date in zip(m.match_id, m.date):
        g = by_match.get(mid)
        if g is None:
            continue
        for p, pts, tm in zip(g.player, g.points.astype(float), g.team):
            s_[p] = s_.get(p, 0.0) * R.DECAY + pts  # each older innings counts DECAY times the next one
            w_[p] = w_.get(p, 0.0) * R.DECAY + 1.0
            n_[p] = n_.get(p, 0) + 1
            team[p] = tm
        raw = pd.Series({p: s_[p] / w_[p] for p in s_ if n_[p] >= R.MIN_INNINGS}, dtype=float)
        scale = R._scale(raw)
        if not raw.size or not scale or scale <= 0:
            continue
        current = (raw / scale * 500).clip(lower=0)
        for p, v in current.items():
            if p not in peak or v > peak[p][0]:
                peak[p] = (float(v), date)
        top = current[current == current.max()].index
        for p in top:
            at1[p] = at1.get(p, 0) + 1
        leader = sorted(top)[0]
        if not reigns or reigns[-1]["player"] != leader:
            reigns.append({"player": leader, "from": date, "to": date, "matches": 1})
        else:
            reigns[-1]["to"] = date
            reigns[-1]["matches"] += 1
    rows = [dict(player=p, team=team[p], peak=v, peak_date=dt, current=float(current.get(p, np.nan)),
                 at_no1=at1.get(p, 0), innings=n_[p]) for p, (v, dt) in peak.items()]
    out = pd.DataFrame(rows, columns=cols).sort_values(["peak", "player"], ascending=[False, True]).reset_index(drop=True)
    return out, pd.DataFrame(reigns, columns=["player", "from", "to", "matches"])


def international_sections(career) -> dict[str, str]:
    """{'Test': section, 'ODI': section, 'T20I': section} for the international sections in this career."""
    m = career.matches[career.matches.level == "International"]
    out = {}
    for fmt in ("Test", "ODI", "T20I"):
        s = m[m.format == fmt].section
        if len(s):
            out[fmt] = s.mode().iloc[0]
    return out


def combined_international(career, what: str = "batting") -> pd.DataFrame:
    """One rating across Tests, ODIs and T20Is: each format's current rating,
    weighted by how many innings the player has had in that format."""
    from . import rankings as R
    secs = international_sections(career)
    parts = []
    for fmt, sec in secs.items():
        t = R.player_ratings(career, sec)
        if t.empty:
            continue
        t = t[t[what].notna()][["player", "team", what, f"{what}_innings"]]
        parts.append(t.rename(columns={what: fmt, f"{what}_innings": f"{fmt}_inns", "team": f"{fmt}_team"}))
    cols = ["player", "team", "Test", "ODI", "T20I", "combined", "formats", "innings"]
    if not parts:
        return pd.DataFrame(columns=cols)
    d = parts[0]
    for p in parts[1:]:
        d = d.merge(p, on="player", how="outer")
    num = pd.Series(0.0, index=d.index)
    den = pd.Series(0.0, index=d.index)
    nf = pd.Series(0, index=d.index)
    team = pd.Series("", index=d.index, dtype=object)
    for fmt in ("Test", "ODI", "T20I"):
        if fmt not in d:
            d[fmt] = np.nan
            continue
        ok = d[fmt].notna()
        inns = d[f"{fmt}_inns"].fillna(0)
        num += np.where(ok, d[fmt].fillna(0) * inns, 0)
        den += np.where(ok, inns, 0)
        nf += ok.astype(int)
        team = team.where(team != "", d[f"{fmt}_team"].astype(object).fillna(""))
    d["combined"] = (num / den.replace(0, np.nan)).round()
    d["formats"] = nf
    d["innings"] = den.astype(int)
    d["team"] = team
    return d[cols].sort_values(["combined", "player"], ascending=[False, True]).reset_index(drop=True)


# --------------------------------------------------------------------------- #
# 112 · your best XI against them
# --------------------------------------------------------------------------- #


def picks_against(career, ids, team: str, opponent: str, min_innings: int = 2) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Your squad (everyone who played for you in your latest season here) ranked
    by their record against this opponent, against their own record here.
    Batting lists those who usually bat in the top 7.
    Batting: average (multi-day) or average x strike rate / 100 (white ball).
    Bowling: average (multi-day) or average x economy / 6 (white ball, lower is better)."""
    kind = kind_of_ids(career, ids)
    m = career.matches[career.matches.match_id.isin(ids)]
    mine = m[(m.home == team) | (m.away == team)]
    bcols = ["player", "inns_vs", "runs_vs", "avg_vs", "sr_vs", "avg", "sr", "change", "verdict"]
    wcols = ["player", "spells_vs", "wkts_vs", "avg_vs", "econ_vs", "avg", "econ", "change", "verdict"]
    if mine.empty:
        return pd.DataFrame(columns=bcols), pd.DataFrame(columns=wcols)
    latest = mine.sort_values("date").season.iloc[-1]
    xi = career.batting[career.batting.match_id.isin(mine[mine.season == latest].match_id) & (career.batting.team == team)]
    squad = set(xi.player)
    b = innings(career, mine.match_id)
    b = b[(b.team == team) & b.player.isin(squad)]
    w = spells(career, mine.match_id)
    w = w[(w.team == team) & w.player.isin(squad)]

    def bat_measure(x):
        avg = x.runs.sum() / max(x.out.sum(), 1)
        sr = x.runs.sum() / max(x.balls.sum(), 1) * 100
        return avg, sr, (avg if kind == "multi" else avg * sr / 100)

    def bowl_measure(x):
        wk = x.wickets.sum()
        avg = x.runs.sum() / wk if wk else np.nan
        econ = x.runs.sum() / max(x.balls.sum(), 1) * 6
        return avg, econ, (avg if kind == "multi" else avg * econ / 6 if wk else np.nan)

    def verdict(change, n, better_high=True):
        if n < min_innings or not np.isfinite(change):
            return "Too few games v them"
        good = change >= 25 if better_high else change <= -25
        bad = change <= -25 if better_high else change >= 25
        return "Pick: does well v them" if good else "Think again: struggles v them" if bad else "As usual"

    rows = []
    for p, g in b.groupby("player"):
        v = g[g.opposition == opponent]
        if v.empty or g.position.median() > 7:  # batters and all-rounders only: a no. 10's runs don't pick the side
            continue
        a_v, s_v, m_v = bat_measure(v)
        a, s, m_ = bat_measure(g)
        ch = (m_v / m_ - 1) * 100 if m_ else np.nan
        rows.append(dict(player=p, inns_vs=len(v), runs_vs=int(v.runs.sum()), avg_vs=a_v, sr_vs=s_v, avg=a, sr=s, change=ch,
                         verdict=verdict(ch, len(v))))
    bat = pd.DataFrame(rows, columns=bcols).sort_values(["change", "player"], ascending=[False, True]).reset_index(drop=True)
    rows = []
    for p, g in w.groupby("player"):
        v = g[g.opposition == opponent]
        if v.empty:
            continue
        a_v, e_v, m_v = bowl_measure(v)
        a, e, m_ = bowl_measure(g)
        ch = (m_v / m_ - 1) * 100 if m_ and np.isfinite(m_v) and np.isfinite(m_) else np.nan
        rows.append(dict(player=p, spells_vs=len(v), wkts_vs=int(v.wickets.sum()), avg_vs=a_v, econ_vs=e_v, avg=a, econ=e,
                         change=ch, verdict=verdict(ch, len(v), better_high=False) if v.wickets.sum() or len(v) < min_innings
                         else ("Think again: no wickets v them" if len(v) >= min_innings else "Too few games v them")))
    bowl = pd.DataFrame(rows, columns=wcols).sort_values(["change", "player"]).reset_index(drop=True)
    bat.attrs["kind"] = bowl.attrs["kind"] = kind
    bat.attrs["season"] = latest
    return bat, bowl


# --------------------------------------------------------------------------- #
# 115 · after-match summary
# --------------------------------------------------------------------------- #


def table_position(career, ids, team: str) -> tuple[int, int, str] | None:
    """(position, teams, group) in the league table of these matches, or None."""
    from . import tables as T
    for label, t, _ in T.league_tables(career, ids):
        if team in set(t.team):
            return int(t.index[t.team == team][0]), len(t), label
    return None


def after_match(career, team: str, match_id: str | None = None) -> dict:
    """What changed for your team in its latest match (or the one given): result,
    Elo, league position, series score, first-innings lead (multi-day), records,
    milestones and the players who rose or fell against their season so far."""
    from . import players as PL
    from . import rankings as R
    from . import teamplay as TP
    m = career.matches
    po = RC.played_order(career)
    mine = po[(po.home == team) | (po.away == team)]
    if mine.empty:
        return {}
    r = mine[mine.match_id == match_id].iloc[0] if match_id in set(mine.match_id) else mine.iloc[-1]
    mid = r.match_id
    out: dict = dict(match_id=mid, date=r.date, section=r.section, event=r.event, season=r.season, result=r.result,
                     opponent=r.away if r.home == team else r.home, stage=r.stage,
                     outcome="W" if r.winner == team else "L" if r.winner else
                     "D" if r.result_type == "draw" else "T" if r.result_type == "tie" else "NR")
    kind = kind_of_ids(career, [mid])
    # Elo
    _, hist = R.team_elo(career, r.section)
    h = hist[(hist.match_id == mid) & (hist.team == team)]
    out["elo"] = (float(h.before.iloc[0]), float(h.after.iloc[0])) if len(h) else None
    # league position, before and after (league games of this event and season)
    if not r.knockout and r.level not in ("International", "Exhibition", "Tour"):
        lg = m[(m.event == r.event) & (m.season == r.season) & ~m.knockout]
        if mid in set(lg.match_id):
            # the table after this match day (every game that day, not just the ones listed before this one) and
            # after the match day before, as the league table page counts places moved
            after = table_position(career, lg[lg.date <= r.date].match_id, team)
            earlier = lg[lg.date < r.date]
            before = table_position(career, earlier.match_id, team) if len(earlier) else None
            out["position"] = (before, after)
    # series score after this match
    if r.series_id:
        sg = TP.series_games(career, m[m.series_id == r.series_id].match_id)
        sg = sg[sg.team == team].sort_values("no")
        if mid in set(sg.match_id):
            sg = sg[sg.no <= int(sg[sg.match_id == mid].no.iloc[0])]
        w_, l_, d_ = int((sg.outcome == "W").sum()), int((sg.outcome == "L").sum()), int((sg.outcome == "D").sum())
        length = int(r.series_length) if pd.notna(r.series_length) else len(sg)
        out["series"] = dict(won=w_, lost=l_, drawn=d_, played=len(sg), length=length, opponent=out["opponent"])
    # first-innings lead in a multi-day game
    if kind == "multi":
        inn = career.innings[career.innings.match_id == mid]
        f = inn[inn.team_innings == 1].groupby("team").runs.sum()
        if team in f.index and out["opponent"] in f.index:
            out["lead"] = int(f[team] - f[out["opponent"]])
    # records and milestones
    out["records"] = [msg for src, msg in RC.new_record_lines(career, [r.source])]
    sec_ids = m[m.section == r.section].match_id
    out["milestones"] = PL.milestones_reached(career, sec_ids, mid)
    # form: this match against the season so far (before it), for your players
    season_ids = m[(m.section == r.section) & (m.season == r.season)]
    season_ids = season_ids[season_ids.date < r.date].match_id
    b = innings(career, list(season_ids) + [mid])
    b = b[b.team == team]
    bars = bars_for(kind)
    form = []
    for p, g in b[b.match_id == mid].groupby("player"):
        before = b[(b.player == p) & (b.match_id != mid)]
        runs = int(g.runs.sum())
        if len(before) >= 2:
            avg = before.runs.sum() / max(before.out.sum(), 1)
            if runs >= max(bars["decent"], 1.5 * avg):
                form.append((p, "▲", f"{runs} (season average before this: {avg:.1f})"))
            elif before.runs.tail(3).mean() >= bars["decent"] and runs < bars["low"] and g.position.min() <= 7:
                form.append((p, "▼", f"{runs} after averaging {before.runs.tail(3).mean():.0f} in their last 3"))
    w = spells(career, [mid])
    for rr in w[(w.team == team) & (w.wickets >= bars["haul"])].itertuples():
        form.append((rr.player, "▲", f"{rr.wickets}/{rr.runs}"))
    out["form"] = form
    return out


# --------------------------------------------------------------------------- #
# 118 · league table extras
# --------------------------------------------------------------------------- #


def table_extras(career, ids, table: pd.DataFrame, label: str) -> pd.DataFrame:
    """For a league table (from tables.league_tables): last 5 results, home and away
    records, points per game, run rate for and against (white ball) and the change
    in position since the last match day."""
    from . import tables as T
    m = career.matches[career.matches.match_id.isin(ids) & ~career.matches.knockout].sort_values(["date", "match_id"])
    inn = career.innings[career.innings.match_id.isin(m.match_id)]
    rows = []
    last_day = m.date.max()
    before_ids = m[m.date < last_day].match_id
    prev = {}
    for lab, t, _ in (T.league_tables(career, before_ids) if len(before_ids) else []):
        if lab == label:
            prev = {tm: int(i) for i, tm in zip(t.index, t.team)}
    for pos, team in zip(table.index, table.team):
        g = m[(m.home == team) | (m.away == team)]
        # a tie settled by a super over counts as a win for the side that won it, as in the table
        win = [w or (tw if rt == "tie" else "") for w, tw, rt in zip(g.winner, g.tiebreak_winner, g.result_type)]
        g = g.assign(win_=win)
        res = ["W" if w == team else "L" if w else "D" if rt == "draw" else "T" if rt == "tie" else "N"
               for w, rt in zip(g.win_, g.result_type)]
        home = g[(g.home == team) & ~g.neutral]
        away = g[(g.away == team) & ~g.neutral]
        bat = inn[inn.team == team]
        bowl = inn[inn.opposition == team]
        p0 = prev.get(team)
        rows.append(dict(team=team, form=" ".join(res[-5:]),
                         home=f"{int((home.win_ == team).sum())}–{int(((home.win_ != team) & (home.win_ != '')).sum())}",
                         away=f"{int((away.win_ == team).sum())}–{int(((away.win_ != team) & (away.win_ != '')).sum())}",
                         rr_for=bat.runs.sum() / max(bat.balls.sum(), 1) * 6 if bat.balls.sum() else np.nan,
                         rr_against=bowl.runs.sum() / max(bowl.balls.sum(), 1) * 6 if bowl.balls.sum() else np.nan,
                         moved=(p0 - int(pos)) if p0 is not None else np.nan))
    d = pd.DataFrame(rows, columns=["team", "form", "home", "away", "rr_for", "rr_against", "moved"])
    d.attrs["last_day"] = last_day
    return d


def moved_text(v) -> str:
    if v is None or not np.isfinite(v):
        return "new"
    return "▲" + str(int(v)) if v > 0 else "▼" + str(int(-v)) if v < 0 else "▬"


# --------------------------------------------------------------------------- #
# 136 · World Test Championship
# --------------------------------------------------------------------------- #

WTC_TEAMS = {"Australia", "Bangladesh", "England", "India", "New Zealand", "Pakistan", "South Africa", "Sri Lanka",
             "West Indies"}
WTC_POINTS = dict(win=12, tie=6, draw=4, loss=0)


def wtc_cycle(date: pd.Timestamp) -> int:
    """The first year of the two-year cycle a date falls in: cycles run from June of
    an odd year (2025-27, 2027-29, ...) to the final two years later."""
    y = date.year
    start = y if y % 2 == 1 else y - 1
    if date < pd.Timestamp(year=start, month=6, day=1):
        start -= 2
    return start


def wtc_matches(career) -> pd.DataFrame:
    """Bilateral Tests between two of the nine WTC sides (the final itself doesn't count)."""
    m = career.matches
    t = m[(m.format == "Test") & (m.competition == "Test") & ~m.knockout & m.home.isin(WTC_TEAMS) & m.away.isin(WTC_TEAMS)]
    return t.assign(cycle=t.date.map(wtc_cycle))


def wtc_table(career, cycle: int) -> pd.DataFrame:
    """12 points for a win, 6 for a tie, 4 for a draw; ranked by the percentage of
    the points played for that were won (as the real table is)."""
    t = wtc_matches(career)
    t = t[t.cycle == cycle]
    rows = {}
    for r in t.itertuples():
        for team in (r.home, r.away):
            x = rows.setdefault(team, dict(team=team, played=0, won=0, lost=0, drawn=0, tied=0, nr=0, points=0, series=set()))
            if r.result_type == "no result":
                x["nr"] += 1  # an abandoned Test isn't played for
                continue
            x["played"] += 1
            x["series"].add(r.series_id)
            if r.winner == team:
                x["won"] += 1
                x["points"] += WTC_POINTS["win"]
            elif r.winner:
                x["lost"] += 1
            elif r.result_type == "tie":
                x["tied"] += 1
                x["points"] += WTC_POINTS["tie"]
            else:
                x["drawn"] += 1
                x["points"] += WTC_POINTS["draw"]
    d = pd.DataFrame(list(rows.values()), columns=["team", "played", "won", "lost", "drawn", "tied", "nr", "points", "series"])
    d["series"] = d.series.map(len)
    d["available"] = d.played * WTC_POINTS["win"]
    d["pct"] = d.points / d.available.replace(0, np.nan) * 100
    d = d.sort_values(["pct", "points", "won", "team"], ascending=[False, False, False, True]).reset_index(drop=True)
    d.index = d.index + 1
    return d


# --------------------------------------------------------------------------- #
# 117 · end-of-season review
# --------------------------------------------------------------------------- #


def season_status(career, section: str, season: str) -> str:
    """'complete' or 'in progress', the same call the honours board makes: a
    competition is complete once its final is played (or, for a league with no
    final, a later season exists or every team has played a full season).
    International cricket is by calendar year: the latest year is in progress
    while it has fewer games than the year before."""
    from .extras import honours, season_in_progress
    m = career.matches[career.matches.section == section]
    here = m[m.season == season]
    if here.empty:
        return "complete"
    if here.level.iloc[0] in ("International", "Exhibition", "Tour"):  # calendar years
        prog = season_in_progress(career, section)
        return "in progress" if prog is not None and prog[0] == season else "complete"
    h = honours(career)
    h = h[(h.season == season) & h.section.isin(set(here.event))]
    if h.empty:  # no champion yet: the final isn't in the files (an old season with a later one is still over)
        return "complete" if season != max(m.season) else "in progress"
    return "in progress" if h.how.str.contains("so far").any() else "complete"


def season_review(career, section: str, season: str, my_teams: list | None = None) -> dict:
    """Everything for one competition-season's review page."""
    from . import insights as I
    from . import myteam as MT
    from . import players as PL
    from . import winprob as WP
    from .extras import honours
    from .stats import Scope, player_tables
    m = career.matches
    sec_ids = m[m.section == section].match_id
    ids = m[(m.section == section) & (m.season == season)].match_id
    out: dict = dict(section=section, season=season, matches=len(ids), status=season_status(career, section, season))
    events = set(m[m.match_id.isin(ids)].event)
    h = honours(career)
    out["champions"] = h[h.section.isin(events) & (h.season == season)]
    final = m[m.match_id.isin(ids) & (m.stage == "Final")]
    out["final"] = final.iloc[0] if len(final) == 1 else None
    out["xi"] = best_xi(career, ids)
    bat, bowl, _, base = player_tables(career, Scope(sections=[section], seasons=[season]))
    out["top_bat"] = bat.sort_values(["runs", "average"], ascending=False).head(3)
    out["top_bowl"] = bowl[bowl.wickets > 0].sort_values(["wickets", "average"], ascending=[False, True]).head(3)
    out["best_match"] = WP.best_matches(career, sec_ids, top=3, only=ids)
    up = PL.upsets(career, section, top=10 ** 6)
    out["upset"] = up[up.match_id.isin(ids)].head(1)
    # records broken: the record as it stood before this season, beaten during it (the new mark, and the old one)
    tl = record_timeline(career, sec_ids)
    start = m[m.match_id.isin(ids)].date.min()
    rows = []
    for name, g in tl.groupby("record", sort=False):
        old = g[g.date < start]
        new = g[g.match_id.isin(ids)]
        if len(old) and len(new):
            o, n = old.iloc[-1], new.iloc[-1]
            rows.append(dict(record=name, holder=n.holder, value=n.value, date=n.date, match_id=n.match_id,
                             times=len(new), old_holder=o.holder, old_value=o.value))
    out["records"] = pd.DataFrame(rows, columns=["record", "holder", "value", "date", "match_id", "times", "old_holder",
                                                 "old_value"])
    out["first_season"] = not (m[(m.section == section)].date < start).any()
    bb, bw = I.breakouts(career, section, season)
    out["breakout_bat"] = bb.head(1) if len(bb) else bb
    out["breakout_bowl"] = bw.head(1) if len(bw) else bw
    cards = {}
    for t in my_teams or []:
        if t in set(m[m.match_id.isin(ids)].home) | set(m[m.match_id.isin(ids)].away):
            cards[t] = MT.report_card(career, t, section, season)
    out["report_cards"] = cards
    return out


def year_review(career, year: str) -> dict:
    """A calendar year of international cricket, ICC-awards style: player of the
    year in each format (most match impact), Team of the Year in each format, and
    the cricketer of the year across all three."""
    from . import playerdeep as PDp
    from .stats import Scope, player_tables
    m = career.matches
    secs = international_sections(career)
    out: dict = dict(year=year, formats={})
    total = []
    for fmt, sec in secs.items():
        ids = m[(m.section == sec) & (m.season == year)].match_id
        if not len(ids):
            continue
        imp = PDp.match_impact(career, ids)
        per = imp.groupby("player").agg(impact=("impact", "sum"), runs=("runs", "sum"), wickets=("wickets", "sum"),
                                        matches=("match_id", "nunique"), team=("team", "last")).reset_index()
        per = per.sort_values(["impact", "player"], ascending=[False, True]).reset_index(drop=True)
        per[["runs", "wickets"]] = per[["runs", "wickets"]].astype(int)
        bat, bowl, _, _ = player_tables(career, Scope(sections=[sec], seasons=[year]))
        out["formats"][fmt] = dict(section=sec, matches=len(ids), player=per.head(3), xi=best_xi(career, ids),
                                   top_bat=bat.sort_values("runs", ascending=False).head(1),
                                   top_bowl=bowl[bowl.wickets > 0].sort_values(["wickets", "average"],
                                                                                ascending=[False, True]).head(1))
        total.append(per.assign(fmt=fmt))
    if total:
        t = pd.concat(total)
        all_ = t.groupby("player").agg(impact=("impact", "sum"), runs=("runs", "sum"), wickets=("wickets", "sum"),
                                       matches=("matches", "sum"), team=("team", "last"),
                                       formats=("fmt", lambda x: ", ".join(x))).reset_index()
        all_[["runs", "wickets"]] = all_[["runs", "wickets"]].astype(int)
        out["cricketer"] = all_.sort_values(["impact", "player"], ascending=[False, True]).head(5).reset_index(drop=True)
    else:
        out["cricketer"] = pd.DataFrame()
    return out


# --------------------------------------------------------------------------- the season's year, April to March
def april_year(d) -> int:
    """The year an April-to-March season starts in: April 2026 to March 2027 is the 2026 season."""
    d = pd.Timestamp(d)
    return d.year if d.month >= 4 else d.year - 1


def april_seasons(matches: pd.DataFrame) -> pd.Series:
    """Match id -> the April-to-March season it belongs to. A series or a tournament goes whole to the season most of
    it is played in (by its middle match), so an IPL starting on 29 March stays with the rest of its season."""
    if matches.empty:
        return pd.Series(dtype=int)
    key = [("series", s) if s else ("event", e, str(se)) for s, e, se in zip(matches.series_id, matches.event, matches.season)]
    m = matches.assign(_k=key)
    mid = m.groupby("_k").date.apply(lambda d: sorted(d)[len(d) // 2])
    year = mid.map(april_year)
    return pd.Series([int(year[k]) for k in m._k], index=m.match_id.values)
