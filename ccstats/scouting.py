"""Scouting: the best players who could come into your side, their domestic numbers converted to the level of the
cricket they'd play, and who to bring in when one of your players is struggling.

**Who belongs to which country.** A player capped by a country (he has played for its national side in this career)
belongs to it; if two countries capped the name, the one he played for most (often two men sharing a name). An
uncapped player belongs to the country whose domestic sides he plays for; if he has played in two countries, the
competitions that take no overseas players win (England's county cricket takes them). Franchise leagues are full of
overseas players, so they decide nothing, except for a player who has played nowhere else (marked "going by the
league").

**The conversion.** A domestic average isn't a Test average. The gap is measured from the players who have played in
both (their averages here and there, weighted by how much they played), pulled towards a minimum when few players
are behind it, and never smaller than that minimum: first-class to Tests 25%, List A to ODIs and domestic T20 to T20Is
15%, any other step up (domestic T20 to a franchise league, the second division to the first) 10%; strike rate and
economy 10%. So a Ranji batting average of 50 counts as 37.5 in Tests at most, and a Ranji bowling average of 25 as
31.3 at least.

**Settled numbers.** A short record is mostly luck, so every average (yours and theirs) has a few dismissals (or
wickets) at the usual level of that cricket added before anything is compared: 5 in first-class cricket, 6 in
one-day, 8 in T20, as on the Players page. Seven innings at 72 then count for much less than thirty at 50.

**The bar.** A player is suggested in place of one of yours only if his settled, converted numbers beat your player's
settled numbers by 10% or more (in white-ball cricket average and strike rate together, or bowling average and economy
together), over enough cricket in the last two seasons: a first-class batter 8 innings, a bowler 100 overs; a
white-ball batter 5 innings, a bowler 30 overs in one-day cricket or 15 in T20.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .analysis import role_labels
from .marks import series_key, series_marks
from .players import SHRINK
from .records import by_played
from .stats import KIND

MIN_GAP_INTERNATIONAL = {"multi": 0.25, "one": 0.15, "t20": 0.15}
MIN_GAP_UP = 0.10        # any other step up a level
MIN_GAP_PACE = 0.10      # strike rate and economy
PULL = 10                # players' worth of the minimum added to every measured gap
BAR = 0.10               # how much better a replacement must be
SEASONS = 2
NO_OVERSEAS_FIRST = ("England",)   # domestic cricket here takes overseas players, so it counts last
ENOUGH = {"multi": dict(inns=8, balls=600), "one": dict(inns=5, balls=180), "t20": dict(inns=5, balls=90)}
# whose place each role can take
FITS = {"Opener": {"Opener"}, "Top order": {"Top order", "Opener", "Middle order"},
        "Middle order": {"Middle order", "Top order"},
        "Finisher": {"Finisher", "Lower order", "Middle order", "All-rounder"},
        "Lower order": {"Lower order", "Finisher", "Middle order", "All-rounder"},
        "All-rounder": {"All-rounder"}, "Bowler": {"Bowler"}}
BATTING_ROLES = {"Opener", "Top order", "Middle order", "Finisher", "Lower order"}


# --------------------------------------------------------------------------- kept with the career
def _memo(career, key, make):
    """Work something out once per career (it's kept until the career's matches change)."""
    stamp = (id(career.matches), len(career.matches))
    box = getattr(career, "_scouting", None)
    if box is None or box.get("_stamp") != stamp:
        box = {"_stamp": stamp}
        try:
            career._scouting = box
        except AttributeError:
            return make()
    if key not in box:
        box[key] = make()
    return box[key]


# --------------------------------------------------------------------------- who belongs where
def countries(career) -> pd.DataFrame:
    """player, country, capped (played for that national side), how (how it was decided), unsure."""
    return _memo(career, "countries", lambda: _countries(career))


def _countries(career) -> pd.DataFrame:
    m = career.matches[["match_id", "level", "country"]]
    rows = career.batting[["match_id", "team", "player"]].drop_duplicates().merge(m, on="match_id")
    rows["country"] = np.where(rows.level == "International", rows.team, rows.country)
    n = rows.groupby(["player", "level", "country"]).match_id.nunique().rename("games").reset_index()
    out = []
    for p, g in n.groupby("player"):
        nat = g[g.level == "International"].sort_values("games", ascending=False)
        dom = g[g.level == "Domestic"].sort_values("games", ascending=False)
        fr = g[g.level == "Franchise"].sort_values("games", ascending=False)
        if len(nat):
            out.append((p, nat.country.iloc[0], True, f"played for {nat.country.iloc[0]}", len(nat) > 1))
        elif len(dom):
            home = dom[~dom.country.isin(NO_OVERSEAS_FIRST)]
            pick = home if len(home) else dom
            out.append((p, pick.country.iloc[0], False, "domestic cricket", len(dom) > 1))
        elif len(fr):
            out.append((p, fr.country.iloc[0], False, "going by the league", True))
    return pd.DataFrame(out, columns=["player", "country", "capped", "how", "unsure"])


# --------------------------------------------------------------------------- which competitions feed which
def _level(section: str, level: str) -> float:
    base = {"International": 3.0, "Franchise": 2.0, "Domestic": 1.0}.get(level, 1.0)
    return base - (0.5 if "Division 2" in section else 0.0)


def sections(career) -> pd.DataFrame:
    """section, level, country, format, kind, rank (3 international, 2 franchise, 1 domestic, a half lower for a
    second division)."""
    def make():
        m = career.matches
        s = m.groupby("section").agg(level=("level", "first"), country=("country", "first"), format=("format", "first"))
        s["kind"] = s.format.map(KIND)
        s["rank"] = [_level(sec, r.level) for sec, r in s.iterrows()]
        return s
    return _memo(career, "sections", make)


def feeders(career, team: str, section: str) -> list[str]:
    """The competitions players for `team` in `section` come from: a national side's own country's domestic and
    franchise competitions of the same kind of cricket; a franchise's own league and its country's domestic ones; a
    domestic side's own competition and its country's others of the same kind at its level or below."""
    s = sections(career)
    if section not in s.index:
        return []
    me = s.loc[section]
    if me.level == "International":
        pool = s[(s.level != "International") & (s.country == team) & (s.kind == me.kind)]
        return list(pool.index)
    pool = s[(s.level != "International") & (s.country == me.country) & (s.kind == me.kind) & (s["rank"] <= me["rank"])]
    return [section] + [x for x in pool.index if x != section]


def target_of(career, team: str) -> list[str]:
    """The competitions your side plays in that can be scouted for: every section it has played in."""
    m = career.matches
    return list(dict.fromkeys(m[(m.home == team) | (m.away == team)].section))


# --------------------------------------------------------------------------- the conversion
def _window(career, section: str) -> pd.Index:
    """The section's matches in its last two seasons (as played)."""
    def make():
        m = career.matches[career.matches.section == section]
        seasons = list(dict.fromkeys(by_played(career, m).season[::-1]))[:SEASONS]
        return pd.Index(m[m.season.isin(seasons)].match_id)
    return _memo(career, ("window", section), make)


def _bat(career, ids) -> pd.DataFrame:
    b = career.batting[career.batting.match_id.isin(ids) & career.batting.did_bat]
    return b.groupby("player").agg(inns=("runs", "size"), runs=("runs", "sum"), outs=("out", "sum"), balls=("balls", "sum"),
                                   matches=("match_id", "nunique"))


def _bowl(career, ids) -> pd.DataFrame:
    w = career.bowling[career.bowling.match_id.isin(ids) & (career.bowling.balls > 0)]
    return w.groupby("player").agg(balls=("balls", "sum"), runs=("runs", "sum"), wickets=("wickets", "sum"),
                                   matches=("match_id", "nunique"))


def _base(career, ids) -> dict:
    """The usual level in these matches: the top seven's average and strike rate, the bowlers' average and economy."""
    b = career.batting[career.batting.match_id.isin(ids) & career.batting.did_bat & (career.batting.position <= 7)]
    w = career.bowling[career.bowling.match_id.isin(ids) & (career.bowling.balls > 0)]
    return dict(avg=b.runs.sum() / max(b.out.sum(), 1), rpb=b.runs.sum() / max(b.balls.sum(), 1),
                bowl_avg=w.runs.sum() / max(w.wickets.sum(), 1), bowl_rpb=w.runs.sum() / max(w.balls.sum(), 1))


def _ratio(a: pd.Series, b: pd.Series, w: pd.Series) -> tuple[float, int]:
    """The weighted geometric mean of a/b, and how many players it rests on."""
    ok = (a > 0) & (b > 0) & (w > 0)
    if not ok.any():
        return np.nan, 0
    return float(np.exp(np.average(np.log(a[ok] / b[ok]), weights=w[ok]))), int(ok.sum())


def _settle_gap(measured: float, n: int, minimum: float) -> float:
    """A gap (0.2 = 20% harder): the measured one pulled towards the minimum by PULL players, never below it."""
    if not np.isfinite(measured):
        return minimum
    pulled = (n * measured + PULL * minimum) / (n + PULL)
    return max(pulled, minimum)


def measure(career, t_ids, f_ids) -> tuple[dict, dict]:
    """The gaps measured from the players who played in both sets of matches (batting average, strike rate, bowling
    average, economy; 0.2 = 20% harder in the first), and how many players each rests on."""
    bt, bf = _bat(career, t_ids), _bat(career, f_ids)
    j = bt.join(bf, lsuffix="_t", rsuffix="_f", how="inner")
    j1 = j[(j.outs_t >= 3) & (j.outs_f >= 3)]
    r_avg, n_avg = _ratio(j1.runs_t / j1.outs_t, j1.runs_f / j1.outs_f, np.minimum(j1.outs_t, j1.outs_f))
    j2 = j[(j.balls_t >= 60) & (j.balls_f >= 60)]
    r_sr, n_sr = _ratio(j2.runs_t / j2.balls_t, j2.runs_f / j2.balls_f, np.minimum(j2.balls_t, j2.balls_f))
    wt, wf = _bowl(career, t_ids), _bowl(career, f_ids)
    k = wt.join(wf, lsuffix="_t", rsuffix="_f", how="inner")
    k1 = k[(k.wickets_t >= 4) & (k.wickets_f >= 4)]
    r_bowl, n_bowl = _ratio(k1.runs_t / k1.wickets_t, k1.runs_f / k1.wickets_f, np.minimum(k1.wickets_t, k1.wickets_f))
    k2 = k[(k.balls_t >= 120) & (k.balls_f >= 120)]
    r_econ, n_econ = _ratio(k2.runs_t / k2.balls_t, k2.runs_f / k2.balls_f, np.minimum(k2.balls_t, k2.balls_f))
    return (dict(bat=1 - r_avg, sr=1 - r_sr, bowl=r_bowl - 1, econ=r_econ - 1),
            dict(bat=n_avg, sr=n_sr, bowl=n_bowl, econ=n_econ))


def conversion(career, target: str, feeder: str) -> dict:
    """How a feeder competition's numbers become the target's: the gap for batting average, strike rate, bowling
    average and economy (each 0.25 = 25% harder), measured, the players behind each, the minimum, and the gap used."""
    return _memo(career, ("conversion", target, feeder), lambda: _conversion(career, target, feeder))


def _conversion(career, target: str, feeder: str) -> dict:
    if feeder == target:
        zero = dict(bat=0.0, sr=0.0, bowl=0.0, econ=0.0)
        return dict(feeder=feeder, target=target, minimum=0.0, pace_minimum=0.0, measured=zero,
                    players=dict(bat=0, sr=0, bowl=0, econ=0), **zero)
    s = sections(career)
    up = s["rank"][target] > s["rank"][feeder]
    kind = s.kind[target]
    minimum = (MIN_GAP_INTERNATIONAL[kind] if s.level[target] == "International" else MIN_GAP_UP) if up else 0.0
    pace_min = MIN_GAP_PACE if up else 0.0
    m = career.matches
    measured, players = measure(career, m[m.section == target].match_id, m[m.section == feeder].match_id)
    return dict(feeder=feeder, target=target, minimum=minimum, pace_minimum=pace_min, measured=measured, players=players,
                bat=_settle_gap(measured["bat"], players["bat"], minimum),
                sr=_settle_gap(measured["sr"], players["sr"], pace_min),
                bowl=_settle_gap(measured["bowl"], players["bowl"], minimum),
                econ=_settle_gap(measured["econ"], players["econ"], pace_min))


# --------------------------------------------------------------------------- roles, keepers, spinners
def _keepers(career) -> set:
    return _memo(career, "keepers", lambda: set(career.fielding[career.fielding.resolved
                                                               & (career.fielding.kind == "stumped")].player))


def _spinners(career) -> set:
    """Bowlers who have had a batter stumped: the only sign of spin a scorecard gives (no stumping says nothing)."""
    return _memo(career, "spinners", lambda: set(career.batting[career.batting.how_out == "stumped"].bowler.dropna()))


# --------------------------------------------------------------------------- settled numbers
def _settled(d: pd.DataFrame, base: dict, kind: str, runs: str, balls: str, conceded: str, bowled: str) -> pd.DataFrame:
    """Average, strike rate, bowling average and economy, each with SHRINK dismissals (or wickets) at the base level
    added, plus the indexes compared for the bar."""
    k = SHRINK[kind]
    d = d.copy()
    d["avg"] = (d[runs] + k * base["avg"]) / (d.bat_outs + k)
    # strike rate: the balls those k dismissals would take at the base level
    kb = k * base["avg"] / max(base["rpb"], 1e-9)
    d["sr"] = (d[runs] + kb * base["rpb"]) / (d[balls] + kb) * 100
    d["bowl_avg"] = (d[conceded] + k * base["bowl_avg"]) / (d.bowl_wickets + k)
    kw = k * base["bowl_avg"] / max(base["bowl_rpb"], 1e-9)
    d["econ"] = (d[conceded] + kw * base["bowl_rpb"]) / (d[bowled] + kw) * 6
    d["raw_avg"] = d.bat_runs / d.bat_outs.replace(0, np.nan)
    d["raw_sr"] = d.bat_runs / d.bat_balls.replace(0, np.nan) * 100
    d["raw_bowl_avg"] = d.bowl_runs / d.bowl_wickets.replace(0, np.nan)
    d["raw_econ"] = d.bowl_runs / d.bowl_balls.replace(0, np.nan) * 6
    return d


def converted(career, team: str, target: str) -> pd.DataFrame:
    """Every player in the feeder competitions' last two seasons, with his numbers there converted to the target's
    level (several competitions added together) and settled, his role there, country, keeper and spin marks."""
    return _memo(career, ("converted", team, target), lambda: _converted(career, team, target))


def _converted(career, team: str, target: str) -> pd.DataFrame:
    kind = sections(career).kind[target]
    rows_b, rows_w, ids_all, bases = [], [], [], []
    for f in feeders(career, team, target):
        conv = conversion(career, target, f)
        ids = _window(career, f)
        ids_all += list(ids)
        b = _bat(career, ids)
        b["c_runs"] = b.runs * (1 - conv["bat"])
        b["c_balls"] = b.balls * (1 - conv["bat"]) / (1 - conv["sr"])
        rows_b.append(b)
        w = _bowl(career, ids)
        w["c_runs"] = w.runs * (1 + conv["bowl"])
        w["c_balls"] = w.balls * (1 + conv["bowl"]) / (1 + conv["econ"])
        rows_w.append(w)
        base = _base(career, ids)
        bases.append(dict(avg=base["avg"] * (1 - conv["bat"]), rpb=base["rpb"] * (1 - conv["sr"]),
                          bowl_avg=base["bowl_avg"] * (1 + conv["bowl"]), bowl_rpb=base["bowl_rpb"] * (1 + conv["econ"]),
                          weight=len(ids)))
    if not rows_b:
        return pd.DataFrame()
    b = pd.concat(rows_b).groupby(level=0).sum()
    w = pd.concat(rows_w).groupby(level=0).sum()
    d = b.add_prefix("bat_").join(w.add_prefix("bowl_"), how="outer").fillna(0)
    wsum = sum(x["weight"] for x in bases)
    base = {k: sum(x[k] * x["weight"] for x in bases) / wsum for k in ("avg", "rpb", "bowl_avg", "bowl_rpb")}
    d = _settled(d, base, kind, "bat_c_runs", "bat_c_balls", "bowl_c_runs", "bowl_c_balls")
    roles = role_labels(career, pd.Index(ids_all), kind).set_index("player")
    d = d.join(roles[["role", "usual_position"]], how="left")
    d["keeper"] = d.index.isin(_keepers(career))
    d["spinner"] = d.index.isin(_spinners(career))
    d = d.join(countries(career).set_index("player"), how="left")
    enough = ENOUGH[kind]
    d["enough_bat"] = d.bat_inns >= enough["inns"]
    d["enough_bowl"] = d.bowl_balls >= enough["balls"]
    d.attrs["base"] = base
    return d


def own_numbers(career, team: str, target: str) -> pd.DataFrame:
    """Your players' own numbers in the target competition over its last two seasons (no conversion: it's the real
    thing), settled the same way, with their roles."""
    return _memo(career, ("own", team, target), lambda: _own_numbers(career, team, target))


def _own_numbers(career, team: str, target: str) -> pd.DataFrame:
    kind = sections(career).kind[target]
    ids = _window(career, target)
    m = career.matches[career.matches.match_id.isin(ids)]
    mine = pd.Index(m[(m.home == team) | (m.away == team)].match_id)
    bt = career.batting[career.batting.match_id.isin(mine) & (career.batting.team == team) & career.batting.did_bat]
    w = career.bowling[career.bowling.match_id.isin(mine) & (career.bowling.team == team) & (career.bowling.balls > 0)]
    b = bt.groupby("player").agg(inns=("runs", "size"), runs=("runs", "sum"), outs=("out", "sum"), balls=("balls", "sum"),
                                 matches=("match_id", "nunique"))
    k = w.groupby("player").agg(balls=("balls", "sum"), runs=("runs", "sum"), wickets=("wickets", "sum"),
                                matches=("match_id", "nunique"))
    d = b.add_prefix("bat_").join(k.add_prefix("bowl_"), how="outer").fillna(0)
    d = _settled(d, _base(career, ids), kind, "bat_runs", "bat_balls", "bowl_runs", "bowl_balls")
    roles = role_labels(career, mine, kind, min_matches=1).set_index("player")
    d = d.join(roles[["role", "usual_position"]], how="left")
    d["keeper"] = d.index.isin(_keepers(career))
    d["spinner"] = d.index.isin(_spinners(career))
    return d


# --------------------------------------------------------------------------- comparing two players
def gain(cand, mine, job: str, kind: str) -> float:
    """How much better the candidate is than your player at the job (0.1 = 10%): batting average (with the strike
    rate in white-ball cricket, the two ratios' geometric mean), bowling average (with the economy)."""
    if job == "bat":
        g = cand.avg / mine.avg
        if kind != "multi":
            g = np.sqrt(g * cand.sr / mine.sr)
    else:
        g = mine.bowl_avg / cand.bowl_avg
        if kind != "multi":
            g = np.sqrt(g * mine.econ / cand.econ)
    return float(g - 1)


def _job(role: str) -> str:
    return "both" if role == "All-rounder" else "bowl" if role == "Bowler" else "bat"


def _gain_for(c, me, role: str, kind: str) -> float:
    job = _job(role)
    if job == "both":
        gb, gw = gain(c, me, "bat", kind), gain(c, me, "bowl", kind)
        return float(np.mean([gb, gw])) if min(gb, gw) > -BAR else min(gb, gw)
    return gain(c, me, job, kind)


# --------------------------------------------------------------------------- struggling, and who to bring in
def _latest_side(career, team: str, target: str) -> tuple[str, set]:
    m = career.matches[(career.matches.section == target)
                       & ((career.matches.home == team) | (career.matches.away == team))]
    if m.empty:
        return "", set()
    key = series_key(m)
    latest = by_played(career, m.assign(series=key)).series.iloc[-1]
    ids = m[key == latest].match_id
    return latest, set(career.batting[career.batting.match_id.isin(ids) & (career.batting.team == team)].player)


def _marks(career) -> pd.DataFrame:
    return series_marks(career)   # kept with the career


def struggling(career, team: str, target: str, at: int = 0) -> list[dict]:
    """Your players in a series in this competition (`at`: 0 the latest, 1 the one before...) who are struggling at
    their main job: a very poor series (a mark of 2 or less over 2 games or more), or poor over his last three series
    (4 or less on average, and never better than 5). A tail-ender who doesn't bowl isn't judged on his batting."""
    s = _marks(career)
    m = career.matches[career.matches.section == target]
    s = s[(s.team == team) & s.series.isin(set(series_key(m)))]
    if s.empty:
        return []
    order = list(dict.fromkeys(by_played(career, m.assign(series=series_key(m))).series[::-1]))
    mine = [x for x in order if x in set(s.series)]
    if at >= len(mine):
        return []
    now, before = mine[at], set(mine[at:])
    own = own_numbers(career, team, target)
    out = []
    for r in s[s.series == now].itertuples():
        role = own.role.get(r.player) if r.player in own.index else None
        if not isinstance(role, str) or role not in FITS:
            continue
        his = s[(s.player == r.player) & s.series.isin(before)]
        his = his.set_index("series").reindex([x for x in mine if x in set(his.series)])
        marks = [int(x) for x in his.mark[:3]]
        if r.mark and r.mark <= 2 and r.games >= 2:
            why = f"a very poor series: {r.mark}/10 ({r.line})"
        elif len(marks) == 3 and np.mean(marks) <= 4 and max(marks) <= 5:
            why = f"poor for three series running: {', '.join(f'{x}/10' for x in marks)} (latest first)"
        else:
            continue
        out.append(dict(player=r.player, mark=int(r.mark), marks=marks, why=why, line=r.line, series=now,
                        label=r.label, role=role))
    return out


def candidates(career, team: str, target: str) -> pd.DataFrame:
    """Who can come in: the feeder competitions' players who are eligible (a national side: its own country's
    players) and aren't in your side's latest series."""
    pool = converted(career, team, target)
    if pool.empty:
        return pool
    _, in_side = _latest_side(career, team, target)
    if sections(career).level[target] == "International":
        pool = pool[pool.country == team]
    return pool[~pool.index.isin(in_side)]


def _enough(c, job: str) -> bool:
    if job == "bat":
        return bool(c.enough_bat)
    if job == "bowl":
        return bool(c.enough_bowl)
    return bool(c.enough_bat and c.enough_bowl)


def picks_for(career, team: str, target: str, player: str, role: str, top: int = 3) -> list[dict]:
    """The best players to take `player`'s place (same role, keeper for a keeper, spinner for a spinner), best first,
    each with how much better he is and whether that clears the bar."""
    kind = sections(career).kind[target]
    own = own_numbers(career, team, target)
    if player not in own.index:
        return []
    me = own.loc[player]
    pool = candidates(career, team, target)
    if pool.empty:
        return []
    cand = pool[pool.role.isin(FITS.get(role, {role}))]
    if bool(me.keeper) and role in BATTING_ROLES:
        cand = cand[cand.keeper]
    if role in ("Bowler", "All-rounder") and bool(me.spinner):
        cand = cand[cand.spinner]
    job = _job(role)
    out = []
    for p, c in cand.iterrows():
        if not _enough(c, job):
            continue
        g = _gain_for(c, me, role, kind)
        if not np.isfinite(g):
            continue
        out.append(dict(player=p, role=c.role, gain=g, clears=g >= BAR, keeper=bool(c.keeper), spinner=bool(c.spinner),
                        country=c.country, capped=bool(c.capped) if pd.notna(c.capped) else False,
                        unsure=bool(c.unsure) if pd.notna(c.unsure) else False, **lines(c, kind, job)))
    out.sort(key=lambda x: x["gain"], reverse=True)
    return out[:top]


def replacements(career, team: str, target: str, top: int = 3, at: int = 0) -> list[dict]:
    """For each struggling player: who to bring in, best first, and the verdict ("Replace X with Y", or keep him
    because no one is 10% better yet)."""
    kind = sections(career).kind[target] if target in sections(career).index else "t20"
    own = own_numbers(career, team, target) if target in sections(career).index else pd.DataFrame()
    out = []
    for f in struggling(career, team, target, at):
        picks = picks_for(career, team, target, f["player"], f["role"], top)
        me = own.loc[f["player"]]
        if picks and picks[0]["clears"]:
            verdict = f"Replace {f['player']} with {picks[0]['player']}"
        elif picks:
            verdict = f"Keep {f['player']} for now: no one is 10% better yet (closest: {picks[0]['player']})"
        else:
            verdict = f"Keep {f['player']} for now: no one in the same role has played enough domestic cricket"
        out.append(dict(**f, keeper=bool(me.keeper), own=lines(me, kind, _job(f["role"])), picks=picks, verdict=verdict))
    return out


def lines(r, kind: str, job: str = "both") -> dict:
    """The numbers in words: settled (and converted) as compared, and as they are; only the job compared ("bat",
    "bowl" or "both"), so a bowler's few innings don't show up as a batting average."""
    out = dict(bat="", bowl="", raw_bat="", raw_bowl="")
    if r.bat_inns > 0 and job != "bowl":
        out["bat"] = f"average {r.avg:.1f}" + (f", strike rate {r.sr:.0f}" if kind != "multi" else "")
        raw = f" at {r.raw_avg:.1f}" if np.isfinite(r.raw_avg) else " (never out)"
        out["raw_bat"] = f"{int(r.bat_runs)} runs in {int(r.bat_inns)} innings{raw}" + (
            f", strike rate {r.raw_sr:.0f}" if kind != "multi" and np.isfinite(r.raw_sr) else "")
    if r.bowl_balls > 0 and job != "bat":
        out["bowl"] = f"bowling average {r.bowl_avg:.1f}" + (f", economy {r.econ:.2f}" if kind != "multi" else "")
        raw = f" at {r.raw_bowl_avg:.1f}" if np.isfinite(r.raw_bowl_avg) else f" for {int(r.bowl_runs)}"
        out["raw_bowl"] = f"{int(r.bowl_wickets)} wkts{raw}" + (
            f", economy {r.raw_econ:.2f}" if kind != "multi" and np.isfinite(r.raw_econ) else "")
    return out


GROUPS = {"Openers": ({"Opener"}, "bat", False), "Top and middle order": ({"Top order", "Middle order"}, "bat", False),
          "Wicketkeepers": (BATTING_ROLES, "bat", True), "All-rounders": ({"All-rounder"}, "both", False),
          "Bowlers": ({"Bowler"}, "bowl", False)}


def shortlist(career, team: str, target: str, per_role: int = 5) -> dict:
    """The scouting tab: for each role, the best eligible players not in your side now (settled, converted numbers),
    your own players in that role to compare, and whether each clears the bar against the weakest of them."""
    pool = candidates(career, team, target)
    if pool.empty:
        return {}
    kind = sections(career).kind[target]
    own = own_numbers(career, team, target)
    _, in_side = _latest_side(career, team, target)
    own = own[own.index.isin(in_side)]
    out = {}
    for name, (roles, job, keepers) in GROUPS.items():
        c = pool[pool.role.isin(roles) & (pool.keeper if keepers else True)]
        o = own[own.role.isin(roles) & (own.keeper if keepers else True)]
        c = c[[_enough(r, job) for r in c.itertuples()]] if len(c) else c
        if job == "bat":
            score = c.avg * (c.sr / 100 if kind != "multi" else 1)
            mine = o.avg * (o.sr / 100 if kind != "multi" else 1)
        elif job == "bowl":
            score = -(c.bowl_avg * (c.econ if kind != "multi" else 1))
            mine = -(o.bowl_avg * (o.econ if kind != "multi" else 1))
        else:
            score = (c.avg.rank(pct=True) + (-c.bowl_avg).rank(pct=True)) if len(c) else c.avg
            mine = None
        c = c.assign(_score=score).sort_values("_score", ascending=False).head(per_role)
        weakest = o.loc[mine.idxmin()] if mine is not None and len(o) and mine.notna().any() else None
        picks = []
        for p, r in c.iterrows():
            g = _gain_for(r, weakest, "All-rounder" if job == "both" else ("Bowler" if job == "bowl" else "Opener"), kind) \
                if weakest is not None else np.nan
            picks.append(dict(player=p, gain=g, clears=bool(np.isfinite(g) and g >= BAR), capped=bool(r.capped),
                              unsure=bool(r.unsure), how=r.how, spinner=bool(r.spinner), country=r.country,
                              **lines(r, kind, job)))
        out[name] = dict(picks=picks, weakest=weakest.name if weakest is not None else "",
                         yours=[dict(player=p, **lines(r, kind, job)) for p, r in o.iterrows()])
    return out
