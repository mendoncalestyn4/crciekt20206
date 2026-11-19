"""Scouting: the best players who could come into your side, their domestic numbers converted to the level of the
cricket they'd play, and who to bring in when one of your players is struggling.

**Who belongs to which country.** The scorecards print only initials and a surname, so one printed name can be
several men (an Indian "A Sharma" and a Victorian one). A player capped by a country (he has played for its national
side in this career) belongs to it; an uncapped one to the country whose domestic sides he plays for, the
competitions that take no overseas players first (England's county cricket takes them). A name is **shared** when it
shows two men for sure: capped by two countries, domestic cricket in two countries, capped by one country while
playing domestic cricket that takes no overseas players in another, or two sides in one competition and season.

**Who can be suggested for a national side (100% safe, your rule of 14 November).** All three must hold:
(1) a name that has played for any other national side is never suggested (so a player who switched countries never
is); (2) a player who has only played in franchise leagues is never suggested (they take overseas players, so they
can't prove a country); (3) a shared name counts only the games that prove the country (that side's own domestic
cricket that takes no overseas players): its franchise games count for nobody, and it's marked "shared name".
Franchise and domestic sides aren't affected: they can take anyone.

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

**One man, one place.** If the best pick for two struggling players is the same man, he goes in for the one he'd
improve on by more (the weaker of the two); the other is told his next best pick still free, and why.
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
POOR = 4                 # a poor series: a mark of 4 or less (5-6 is usual)
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
    """player, country (to show), capped (played for that national side), how (in words), shared (the name is two men
    for sure), nations (every national side that capped the name), homes (every country whose domestic cricket he
    played), closed (those of them whose domestic cricket takes no overseas players)."""
    return _memo(career, "countries", lambda: _countries(career))


def _two_sides(career) -> set:
    """Names that played for two sides in one competition and season: two men (until they're split by name)."""
    m = career.matches[["match_id", "section", "season", "level"]]
    rows = career.batting[["match_id", "team", "player"]].drop_duplicates().merge(m, on="match_id")
    rows = rows[rows.level.isin(["International", "Domestic", "Franchise"])]
    n = rows.groupby(["player", "section", "season"]).team.nunique()
    return set(n[n > 1].index.get_level_values("player"))


def _countries(career) -> pd.DataFrame:
    m = career.matches[["match_id", "level", "country"]]
    rows = career.batting[["match_id", "team", "player"]].drop_duplicates().merge(m, on="match_id")
    rows["country"] = np.where(rows.level == "International", rows.team, rows.country)
    n = rows.groupby(["player", "level", "country"]).match_id.nunique().rename("games").reset_index()
    two = _two_sides(career)
    # one pass over every name (most games first in each level, ties by country A to Z, as a stable sort of the
    # grouped rows gives), instead of sorting each name's few rows on their own
    n = n.sort_values(["player", "level", "games", "country"], ascending=[True, True, False, True], kind="stable")
    lists: dict = {}
    for p, lv, ct in zip(n.player, n.level, n.country):
        lists.setdefault(p, {"International": [], "Domestic": [], "Franchise": []}).setdefault(lv, []).append(ct)
    out = []
    for p, by in lists.items():
        nat, dom, fr = by["International"], by["Domestic"], by["Franchise"]
        closed = [x for x in dom if x not in NO_OVERSEAS_FIRST]
        nations, homes, shut = tuple(nat), tuple(dom), tuple(closed)
        shared = (len(nations) > 1 or len(homes) > 1 or bool(nations and set(shut) - set(nations)) or p in two)
        if nat:
            country, capped, how = nat[0], True, "played for " + " and ".join(nations)
        elif dom:
            pick = closed or dom
            country, capped, how = pick[0], False, "domestic cricket in " + " and ".join(homes)
        elif fr:
            country, capped, how = fr[0], False, "only franchise cricket"
        else:
            continue
        if shared:
            how += " (a shared name: more than one player)"
        out.append((p, country, capped, how, shared, nations, homes, shut))
    return pd.DataFrame(out, columns=["player", "country", "capped", "how", "shared", "nations", "homes", "closed"])


def national_ok(c, team: str) -> bool:
    """Whether a player (a row of countries()) can be suggested for `team`'s national side: never capped by another
    country, proven to be the team's (capped by it, or its domestic cricket; for a shared name only domestic cricket
    that takes no overseas players proves it), never franchise cricket alone."""
    nations = c["nations"] if isinstance(c["nations"], tuple) else ()
    if any(x != team for x in nations):
        return False
    if team in nations:
        return True
    proof = c["closed"] if bool(c["shared"]) else c["homes"]
    return isinstance(proof, tuple) and team in proof


def proving_sections(career, team: str) -> set:
    """The competitions whose games prove a shared name is `team`'s: its own country's domestic cricket that takes no
    overseas players (none for England, whose county cricket takes them)."""
    if team in NO_OVERSEAS_FIRST:
        return set()
    s = sections(career)
    return set(s[(s.level == "Domestic") & (s.country == team)].index)


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
    j = bt.merge(bf, left_index=True, right_index=True, suffixes=("_t", "_f"), how="inner")
    j1 = j[(j.outs_t >= 3) & (j.outs_f >= 3)]
    r_avg, n_avg = _ratio(j1.runs_t / j1.outs_t, j1.runs_f / j1.outs_f, np.minimum(j1.outs_t, j1.outs_f))
    j2 = j[(j.balls_t >= 60) & (j.balls_f >= 60)]
    r_sr, n_sr = _ratio(j2.runs_t / j2.balls_t, j2.runs_f / j2.balls_f, np.minimum(j2.balls_t, j2.balls_f))
    wt, wf = _bowl(career, t_ids), _bowl(career, f_ids)
    k = wt.merge(wf, left_index=True, right_index=True, suffixes=("_t", "_f"), how="inner")
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


def _keepers_in(career, ids) -> set:
    f = career.fielding
    return set(f[f.match_id.isin(ids) & f.resolved & (f.kind == "stumped")].player)


def _spinners_in(career, ids) -> set:
    b = career.batting
    return set(b[b.match_id.isin(ids) & (b.how_out == "stumped")].bowler.dropna())


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
    national = sections(career).level[target] == "International"
    who = countries(career).set_index("player")
    shared = set(who.index[who.shared]) if national else set()
    proving = proving_sections(career, team) if national else set()
    rows_b, rows_w, ids_all, ids_sure, bases = [], [], [], [], []
    for f in feeders(career, team, target):
        conv = conversion(career, target, f)
        ids = _window(career, f)
        ids_all += list(ids)
        sure = f in proving
        if sure:
            ids_sure += list(ids)
        b = _bat(career, ids)
        b["c_runs"] = b.runs * (1 - conv["bat"])
        b["c_balls"] = b.balls * (1 - conv["bat"]) / (1 - conv["sr"])
        w = _bowl(career, ids)
        w["c_runs"] = w.runs * (1 + conv["bowl"])
        w["c_balls"] = w.balls * (1 + conv["bowl"]) / (1 + conv["econ"])
        if not sure:   # a shared name's games here could be another man's: they count for nobody
            b, w = b[~b.index.isin(shared)], w[~w.index.isin(shared)]
        rows_b.append(b)
        rows_w.append(w)
        base = _base(career, ids)
        bases.append(dict(avg=base["avg"] * (1 - conv["bat"]), rpb=base["rpb"] * (1 - conv["sr"]),
                          bowl_avg=base["bowl_avg"] * (1 + conv["bowl"]), bowl_rpb=base["bowl_rpb"] * (1 + conv["econ"]),
                          weight=len(ids)))
    if not rows_b:
        return pd.DataFrame()
    b = pd.concat(rows_b).groupby(level=0).sum()
    w = pd.concat(rows_w).groupby(level=0).sum()
    d = b.add_prefix("bat_").join(w.add_prefix("bowl_"), how="outer").astype("float64").fillna(0)
    wsum = sum(x["weight"] for x in bases)
    base = {k: sum(x[k] * x["weight"] for x in bases) / wsum for k in ("avg", "rpb", "bowl_avg", "bowl_rpb")}
    d = _settled(d, base, kind, "bat_c_runs", "bat_c_balls", "bowl_c_runs", "bowl_c_balls")
    d = d[(d.bat_inns > 0) | (d.bowl_balls > 0)]
    roles = role_labels(career, pd.Index(ids_all), kind).set_index("player")
    side = _last_side(career, pd.Index(ids_all))
    keepers, spinners = _keepers(career), _spinners(career)
    if shared:
        # a shared name's role, keeping, spin and latest side come from its sure games only
        sure = pd.Index(ids_sure)
        r2 = role_labels(career, sure, kind).set_index("player")
        roles = _swap(roles, r2, shared)
        side = _swap(side, _last_side(career, sure), shared)
        keepers = (keepers - shared) | (_keepers_in(career, sure) & shared)
        spinners = (spinners - shared) | (_spinners_in(career, sure) & shared)
    d = d.join(roles[["role", "usual_position"]], how="left")
    d["keeper"] = d.index.isin(keepers)
    d["spinner"] = d.index.isin(spinners)
    d = d.join(who, how="left")
    d = d.join(side, how="left")
    enough = ENOUGH[kind]
    d["enough_bat"] = d.bat_inns >= enough["inns"]
    d["enough_bowl"] = d.bowl_balls >= enough["balls"]
    d.attrs["base"] = base
    return d


def _swap(a: pd.DataFrame, b: pd.DataFrame, names: set) -> pd.DataFrame:
    """`a` with the rows of `names` taken from `b` instead (left out where `b` has none)."""
    keep, take = a[~a.index.isin(names)], b[b.index.isin(names)]
    parts = [x for x in (keep, take) if len(x)]
    return pd.concat(parts) if len(parts) > 1 else parts[0] if parts else a.iloc[:0]


def _last_side(career, ids) -> pd.DataFrame:
    """The team each player last played for in these matches, and in which competition."""
    m = career.matches[career.matches.match_id.isin(ids)]
    pos = {mid: i for i, mid in enumerate(by_played(career, m).match_id)}
    b = career.batting[career.batting.match_id.isin(ids)][["match_id", "team", "player"]].drop_duplicates()
    b = b.assign(at=b.match_id.map(pos), where=b.match_id.map(m.set_index("match_id").section)).sort_values("at")
    return b.groupby("player")[["team", "where"]].last().rename(columns={"team": "side"})


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
    their main job: poor for two series running (4 or less in both), or over their last three (4 or less on average,
    and never better than 5). One bad series alone is not enough: everyone has one. A tail-ender who doesn't bowl
    isn't judged on their batting."""
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
        if len(marks) == 3 and np.mean(marks) <= POOR and max(marks) <= POOR + 1:
            why = f"poor for three series running: {', '.join(f'{x}/10' for x in marks)} (latest first)"
        elif len(marks) >= 2 and max(marks[:2]) <= POOR:
            why = f"poor for two series running: {', '.join(f'{x}/10' for x in marks[:2])} (latest first)"
        else:
            continue
        out.append(dict(player=r.player, mark=int(r.mark), marks=marks, why=why, line=r.line, series=now,
                        label=r.label, role=role))
    return out


def taken(career, team: str, target: str) -> set:
    """In a franchise league, the players who played for another side in its latest season: they're under contract
    there, so they can't come in (your own squad's players can)."""
    s = sections(career)
    if target not in s.index or s.level[target] != "Franchise":
        return set()
    m = career.matches[career.matches.section == target]
    latest = by_played(career, m).season.iloc[-1]
    b = career.batting[career.batting.match_id.isin(m[m.season == latest].match_id)]
    return set(b[b.team != team].player) - set(b[b.team == team].player)


def candidates(career, team: str, target: str) -> pd.DataFrame:
    """Who can come in: the feeder competitions' players who are eligible (a national side: only players surely its
    own, see national_ok; a franchise: anyone not under contract at another side in the league), and aren't in your side's latest
    series."""
    pool = converted(career, team, target)
    if pool.empty:
        return pool
    _, in_side = _latest_side(career, team, target)
    if sections(career).level[target] == "International":
        pool = pool[[national_ok(r, team) for _, r in pool.iterrows()]]
    pool = pool[~pool.index.isin(taken(career, team, target))]
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
                        **_who(c), **lines(c, kind, job)))
    out.sort(key=lambda x: x["gain"], reverse=True)
    return out[:top]


def share(wants: list[list[dict]]) -> dict[str, int]:
    """One man can't come in for two players. `wants` holds each struggling player's picks, best first (player, gain,
    clears); the answer says which of them each brought-in man goes in for (his place in `wants`). When two would
    bring in the same man, the one he'd improve on by more (the weaker of the two) gets him, and the other moves on to
    his next best still free, round after round. Only a man who clears the bar is brought in: a player whose best free
    pick doesn't clear it keeps his place."""
    gone: dict[str, int] = {}
    left = set(range(len(wants)))
    while left:
        first: dict[str, list] = {}
        for i in sorted(left):
            nxt = next((p for p in wants[i] if p["player"] not in gone), None)
            if nxt is None or not nxt["clears"]:
                left.discard(i)
                continue
            first.setdefault(nxt["player"], []).append((nxt["gain"], -i))
        for man, rivals in first.items():
            i = -max(rivals)[1]       # the biggest gain; level, the one listed first
            gone[man] = i
            left.discard(i)
    return gone


def _going_elsewhere(lost: list[tuple[str, str]]) -> str:
    """Why a struggling player isn't given his best pick, in a sentence: 'Their best pick, X, goes in for A instead, a
    bigger step up there.', or for several 'Their best picks go in for others instead, bigger steps up there: X for A,
    Y for B and Z for C.'"""
    if not lost:
        return ""
    if len(lost) == 1:
        return f"Their best pick, {lost[0][0]}, goes in for {lost[0][1]} instead, a bigger step up there."
    parts = [f"{x} for {a}" for x, a in lost]
    return f"Their best picks go in for others instead, bigger steps up there: {', '.join(parts[:-1])} and {parts[-1]}."


def replacements(career, team: str, target: str, top: int = 3, at: int = 0) -> list[dict]:
    """For each struggling player: who to bring in, best first, and the verdict ("Replace X with Y", or keep him
    because no one is 10% better yet). A man who would be the best pick for two of them goes in for one (see share);
    the other is shown his next best, and `elsewhere` says why."""
    kind = sections(career).kind[target] if target in sections(career).index else "t20"
    own = own_numbers(career, team, target) if target in sections(career).index else pd.DataFrame()
    flagged = struggling(career, team, target, at)
    # enough picks that each still has `top` once the ones going in for the others are taken out
    wants = [picks_for(career, team, target, f["player"], f["role"], top + len(flagged) - 1) for f in flagged]
    gone = share(wants)
    out = []
    for i, f in enumerate(flagged):
        free = [p for p in wants[i] if gone.get(p["player"], i) == i]
        # the men who'd clear the bar for him but go in for someone else, ahead of his first free pick
        lost = []
        for p in wants[i]:
            if gone.get(p["player"], i) == i:
                break
            if p["clears"]:
                lost.append(p["player"])
        elsewhere = _going_elsewhere([(x, flagged[gone[x]]["player"]) for x in lost])
        picks = free[:top]
        me = own.loc[f["player"]]
        if picks and picks[0]["clears"]:
            verdict = f"Replace {f['player']} with {picks[0]['player']}"
        elif lost:
            verdict = f"Keep {f['player']} for now: no one else is 10% better" + (
                f" (closest: {picks[0]['player']})" if picks else "")
        elif picks:
            verdict = f"Keep {f['player']} for now: no one is 10% better yet (closest: {picks[0]['player']})"
        else:
            verdict = f"Keep {f['player']} for now: no one in the same role has played enough domestic cricket"
        out.append(dict(**f, keeper=bool(me.keeper), own=lines(me, kind, _job(f["role"])), picks=picks, verdict=verdict,
                        elsewhere=elsewhere, lost=[dict(player=x, goes_to=flagged[gone[x]]["player"]) for x in lost]))
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


def _who(r) -> dict:
    """Where a candidate comes from: country (and how that was decided), capped or not, a shared name or not, their
    latest side."""
    def flag(v):
        return bool(v) if pd.notna(v) else False

    def text(v):
        return v if isinstance(v, str) else ""
    # by name, not as attributes: a row's .where is pandas' own where()
    return dict(country=text(r["country"]), capped=flag(r["capped"]), shared=flag(r["shared"]), how=text(r["how"]),
                side=text(r["side"]), where=text(r["where"]))


def index(d, job: str, kind: str):
    """How good at the job in one number, higher better, from the settled numbers: the average (times the runs a ball
    in white-ball cricket); one over the bowling average (times the balls a run); an all-rounder's both, multiplied
    and square-rooted. The gain against a fixed player rises with it."""
    white = kind != "multi"
    bat = d.avg * (d.sr / 100 if white else 1)
    bowl = 1 / (d.bowl_avg * (d.econ / 6 if white else 1))
    return bat if job == "bat" else bowl if job == "bowl" else np.sqrt(bat * bowl)


GROUPS = {"Openers": ({"Opener"}, "bat", False), "Top and middle order": ({"Top order", "Middle order"}, "bat", False),
          "Wicketkeepers": (BATTING_ROLES, "bat", True), "All-rounders": ({"All-rounder"}, "both", False),
          "Bowlers": ({"Bowler"}, "bowl", False)}
ROLE_OF_JOB = {"bat": "Opener", "bowl": "Bowler", "both": "All-rounder"}   # any role with that job


def shortlist(career, team: str, target: str, per_role: int = 5) -> dict:
    """The scouting tab: for each kind of player, the best eligible ones not in your side now (settled, converted
    numbers, with enough cricket behind them), your own players of that kind in the latest series to compare, and
    whether each clears the bar against the weakest of them."""
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
        c = c.assign(_score=index(c, job, kind)).sort_values("_score", ascending=False).head(per_role)
        o = o.assign(_score=index(o, job, kind)).sort_values("_score", ascending=False)
        scored = o[o._score.notna()]
        weakest = scored.iloc[-1] if len(scored) else None
        picks = []
        for p, r in c.iterrows():
            g = _gain_for(r, weakest, ROLE_OF_JOB[job], kind) if weakest is not None else np.nan
            picks.append(dict(player=p, gain=g if np.isfinite(g) else None, clears=bool(np.isfinite(g) and g >= BAR),
                              keeper=bool(r.keeper), spinner=bool(r.spinner), role=r.role, **_who(r), **lines(r, kind, job)))
        out[name] = dict(job=job, picks=picks, weakest=weakest.name if weakest is not None else "",
                         yours=[dict(player=p, role=r.role, **lines(r, kind, job)) for p, r in o.iterrows()])
    return out
