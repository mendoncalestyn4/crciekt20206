"""Player and team statistics from a career's tables.

Everything is worked out for a *scope*: the set of matches the user picked
(one competition, one format, a season, a team, home or away).  Averages
used as baselines - "the average batter", "the average bowler" - always come
from the same scope, so an IPL ranking is measured against the IPL.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .competitions import FIRST_CLASS, HUNDRED, LIST_A, ODI, T20, T20I, TEST

KIND = {TEST: "multi", FIRST_CLASS: "multi", ODI: "one", LIST_A: "one", T20: "t20", T20I: "t20", HUNDRED: "t20"}
WICKET_VALUE = {"t20": 8, "one": 14}  # runs a wicket is worth when turning wickets into runs saved
BALL_QUOTA = {T20: 120, T20I: 120, HUNDRED: 100, ODI: 300, LIST_A: 300}


# --------------------------------------------------------------------------- #
# Scope
# --------------------------------------------------------------------------- #


@dataclass
class Scope:
    sections: list[str] = field(default_factory=list)  # empty = any; normally exactly one
    competitions: list[str] = field(default_factory=list)  # empty = any
    formats: list[str] = field(default_factory=list)
    seasons: list[str] = field(default_factory=list)
    team: str = ""
    venue: str = "all"  # all / home / away / neutral (from `team`'s point of view)
    opponent: str = ""
    stages: str = "all"  # all / league / knockout
    positions: list[int] = field(default_factory=list)  # batting positions to count (empty = all); batting only
    events: list[str] = field(default_factory=list)  # competitions as run, e.g. "ODI World Cup" (empty = any)
    # row filters: which players' rows count (the matches stay the same, so the average player is still the section's)
    teams: list[str] = field(default_factory=list)  # only rows for these teams (empty = any)
    venues: list[str] = field(default_factory=list)  # home / away / neutral, from the player's own team (empty = any)
    how_out: list[str] = field(default_factory=list)  # batting only: innings ending this way ("not out" included)
    only: tuple = ()  # only these matches (empty = any): an April-to-March year of one competition, when formats are ticked together

    def match_ids(self, matches: pd.DataFrame) -> pd.Index:
        m = matches
        if self.only:
            m = m[m.match_id.isin(set(self.only))]
        if self.sections:
            m = m[m.section.isin(self.sections)]
        if self.competitions:
            m = m[m.competition.isin(self.competitions)]
        if self.events:
            m = m[m.event.isin(self.events)]
        if self.formats:
            m = m[m.format.isin(self.formats)]
        if self.seasons:
            m = m[m.season.isin(self.seasons)]
        if self.stages != "all":
            m = m[m.knockout == (self.stages == "knockout")]
        if self.team:
            m = m[(m.home == self.team) | (m.away == self.team)]
            if self.venue == "home":
                m = m[(m.home == self.team) & ~m.neutral]
            elif self.venue == "away":
                m = m[(m.away == self.team) & ~m.neutral]
            elif self.venue == "neutral":
                m = m[m.neutral]
            if self.opponent:
                m = m[(m.home == self.opponent) | (m.away == self.opponent)]
        return pd.Index(m.match_id)


def counts_fielding(career) -> bool:
    """Whether catches and stumpings count in this career's figures. The new site leaves fielding out of everything
    (your decision of 14 November: nothing shown, and nothing counted in marks, impact or MVP points); it marks the
    careers it opens with count_fielding = False. The old site counts them as before."""
    return bool(getattr(career, "count_fielding", True))


def fielding_credits(career, ids) -> pd.DataFrame:
    """The catches and stumpings credited to a player in these matches, for figures that count them: none when the
    career doesn't count fielding (see counts_fielding). Who keeps wicket is still read from the stumpings
    themselves, quietly."""
    f = career.fielding
    f = f[f.match_id.isin(ids) & f.resolved]
    return f if counts_fielding(career) else f.iloc[:0]


def venue_of(rows: pd.DataFrame, matches: pd.DataFrame) -> pd.Series:
    """home / away / neutral for each row (batting, bowling or fielding), from that row's team."""
    info = matches.set_index("match_id")[["home", "neutral"]]
    home = rows.match_id.map(info.home)
    neutral = rows.match_id.map(info.neutral).fillna(False).astype(bool)
    return pd.Series(np.where(neutral, "neutral", np.where(rows.team == home, "home", "away")), index=rows.index)


def _rows(df: pd.DataFrame, scope: "Scope", matches: pd.DataFrame) -> pd.DataFrame:
    """Rows kept by the scope's venue filter (this one changes the average player too)."""
    if scope.venues and len(df):
        df = df[venue_of(df, matches).isin(scope.venues)]
    return df


POSITION_GROUPS = {"Openers (1-2)": [1, 2], "No. 3": [3], "4 and 5": [4, 5], "6 and 7": [6, 7],
                   "8 to 11": [8, 9, 10, 11]}


# What counts as a good day differs by format: a 50 is a big innings in a T20 but only a start in a Test, and
# three wickets is a haul in a T20 but five is the mark in a Test.  Every feature reads its bars from here.
BARS = {
    "t20": dict(thrash_runs=40, thrash_wkts=7, decent=20, big=50, boom=30, low=10, haul=3, headline_haul=4, wicket_steps=(1, 2, 3), close_runs=10,
                good_start=50, bad_start=15, stand=50, platform=100, pressure_score=40, bowl_measure="economy"),
    "one": dict(thrash_runs=75, thrash_wkts=7, decent=30, big=50, boom=50, low=10, haul=4, headline_haul=5, wicket_steps=(1, 2, 4), close_runs=20,
                good_start=60, bad_start=20, stand=50, platform=150, pressure_score=60, bowl_measure="economy"),
    "multi": dict(thrash_runs=150, thrash_wkts=8, decent=50, big=100, boom=100, low=10, haul=5, headline_haul=5, wicket_steps=(1, 3, 5), close_runs=50,
                  good_start=100, bad_start=25, stand=100, platform=250, pressure_score=80, bowl_measure="average"),
}


def bars_for(kind: str) -> dict:
    """The bars for one kind of cricket (t20 / one / multi)."""
    return BARS.get(kind, BARS["t20"])


def kind_of(matches: pd.DataFrame) -> str:
    """multi / one / t20 for the formats in play (the most common one wins)."""
    if matches.empty:
        return "t20"
    return KIND.get(matches.format.mode().iloc[0], "t20")


# --------------------------------------------------------------------------- #
# Aggregation
# --------------------------------------------------------------------------- #


@dataclass
class Baseline:
    kind: str
    matches: int
    strike_rate: float  # runs per 100 balls
    average: float  # runs per dismissal
    runs_per_innings: float
    six_rate: float  # sixes per ball
    boundary_share: float  # share of runs in 4s and 6s
    fifty_rate: float  # 50+ scores per innings
    duck_rate: float
    economy: float
    bowl_strike_rate: float
    bowl_average: float
    dot_rate: float | None
    maiden_rate: float | None  # maidens per over
    haul_rate: float  # 4+ wicket innings per innings bowled
    catches_per_match: float
    has_dots: bool


def _safe(a, b):
    return a / b if b else np.nan


def player_tables(career, scope: Scope | None = None, by_team: bool = False) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Baseline]:
    """Batting, bowling and fielding tables (one row per player, or per
    player and team when `by_team`) plus the scope's baseline."""
    scope = scope or Scope()
    ids = scope.match_ids(career.matches)
    matches = career.matches[career.matches.match_id.isin(ids)]
    kind = kind_of(matches)
    keys = ["player", "team"] if by_team else ["player"]

    bat = _rows(career.batting[career.batting.match_id.isin(ids)], scope, matches)
    if scope.positions:  # innings at these positions only; the baseline is then the average batter there too
        bat = bat[bat.position.isin(scope.positions)]
    if scope.how_out:  # innings that ended this way only (the baseline too)
        bat = bat[bat.how_out.isin(scope.how_out)]
    bat_scope = bat
    if scope.team:
        bat_scope = bat_scope[bat_scope.team == scope.team]
    if scope.teams:
        bat_scope = bat_scope[bat_scope.team.isin(scope.teams)]
    batted = bat_scope[bat_scope.did_bat]

    # ---------------- batting
    all_batted = bat[bat.did_bat]
    tot_runs, tot_balls, tot_outs, tot_inns = all_batted.runs.sum(), all_batted.balls.sum(), all_batted.out.sum(), len(all_batted)
    base_sr = _safe(tot_runs, tot_balls) * 100
    base_avg = _safe(tot_runs, tot_outs)

    appearances = bat_scope.groupby(keys).agg(matches=("match_id", "nunique"),
                                             teams=("team", lambda s: " / ".join(sorted(set(s)))))
    g = batted.assign(
        fifty=(batted.runs >= 50) & (batted.runs < 100), hundred=batted.runs >= 100,
        duck=(batted.runs == 0) & batted.out, bdry=4 * batted.fours + 6 * batted.sixes,
        notout=~batted.out,
    ).groupby(keys)
    b = g.agg(innings=("runs", "size"), runs=("runs", "sum"), balls=("balls", "sum"), outs=("out", "sum"),
              not_outs=("notout", "sum"), fours=("fours", "sum"), sixes=("sixes", "sum"), fifties=("fifty", "sum"),
              hundreds=("hundred", "sum"), ducks=("duck", "sum"), boundary_runs=("bdry", "sum"))
    # highest score, not-outs winning ties
    hs = batted.assign(_rank=batted.runs * 2 + (~batted.out)).sort_values("_rank").groupby(keys).tail(1)
    hs = hs.set_index(keys)[["runs", "out"]].rename(columns={"runs": "high_score", "out": "high_score_out"})
    b = appearances.join(b, how="left").join(hs, how="left").fillna(
        {c: 0 for c in ["innings", "runs", "balls", "outs", "not_outs", "fours", "sixes", "fifties", "hundreds", "ducks", "boundary_runs"]})
    for c in ["innings", "runs", "balls", "outs", "not_outs", "fours", "sixes", "fifties", "hundreds", "ducks", "boundary_runs"]:
        b[c] = b[c].astype(int)
    b["average"] = np.where(b.outs > 0, b.runs / b.outs.replace(0, np.nan), np.nan)
    b["strike_rate"] = np.where(b.balls > 0, b.runs / b.balls.replace(0, np.nan) * 100, np.nan)
    b["fifty_plus"] = b.fifties + b.hundreds
    b["boundary_pct"] = np.where(b.runs > 0, b.boundary_runs / b.runs.replace(0, np.nan) * 100, np.nan)
    b["runs_above_average"] = (b.runs - b.outs * base_avg) if kind == "multi" else (b.runs - b.balls * base_sr / 100)
    b["high_score_text"] = [
        "" if pd.isna(h) else f"{int(h)}{'' if o else '*'}" for h, o in zip(b.high_score, b.high_score_out)]
    b = b.reset_index()

    # ---------------- bowling
    all_bowl = _rows(career.bowling[career.bowling.match_id.isin(ids)], scope, matches)
    bowl = all_bowl
    if scope.team:
        bowl = bowl[bowl.team == scope.team]
    if scope.teams:
        bowl = bowl[bowl.team.isin(scope.teams)]
    tb_runs, tb_balls, tb_wkts = all_bowl.runs.sum(), all_bowl.balls.sum(), all_bowl.wickets.sum()
    base_econ = _safe(tb_runs, tb_balls) * 6
    base_bsr = _safe(tb_balls, tb_wkts)
    base_bavg = _safe(tb_runs, tb_wkts)
    dots_known = all_bowl[all_bowl.dots.notna()]
    mdn_known = all_bowl[all_bowl.maidens.notna()]
    bw = bowl[bowl.balls > 0].copy()
    bw["dot_balls"] = np.where(bw.dots.notna(), bw.balls, 0)
    bw["maiden_overs"] = np.where(bw.maidens.notna(), bw.balls / 6, 0)
    bw["haul"] = bw.wickets >= 4
    bw["five"] = bw.wickets >= 5
    bw["_best"] = bw.wickets * 1000 - bw.runs
    gb = bw.groupby(keys)
    w = gb.agg(innings=("balls", "size"), balls=("balls", "sum"), runs=("runs", "sum"), wickets=("wickets", "sum"),
               dots=("dots", "sum"), dot_balls=("dot_balls", "sum"), maidens=("maidens", "sum"),
               maiden_overs=("maiden_overs", "sum"), hauls=("haul", "sum"), five_fors=("five", "sum"),
               counted_in_balls=("counted_in_balls", "max"), teams=("team", lambda s: " / ".join(sorted(set(s)))))
    best = bw.sort_values("_best").groupby(keys).tail(1).set_index(keys)
    w["best"] = [f"{int(best.loc[i, 'wickets'])}/{int(best.loc[i, 'runs'])}" for i in w.index]
    # best match figures (multi-day matters most)
    bm = bw.groupby(keys + ["match_id"])[["wickets", "runs"]].sum().reset_index()
    bm["_best"] = bm.wickets * 1000 - bm.runs
    bm = bm.sort_values("_best").groupby(keys).tail(1).set_index(keys)
    w["best_match"] = [f"{int(bm.loc[i, 'wickets'])}/{int(bm.loc[i, 'runs'])}" for i in w.index]
    w["ten_in_match"] = bw.groupby(keys + ["match_id"]).wickets.sum().ge(10).groupby(level=keys).sum() if len(bw) else 0
    w["economy"] = w.runs / w.balls * 6
    w["strike_rate"] = np.where(w.wickets > 0, w.balls / w.wickets.replace(0, np.nan), np.nan)
    w["average"] = np.where(w.wickets > 0, w.runs / w.wickets.replace(0, np.nan), np.nan)
    w["dot_pct"] = np.where(w.dot_balls > 0, w.dots / w.dot_balls.replace(0, np.nan) * 100, np.nan)
    if kind == "multi":
        w["runs_saved"] = w.wickets * base_bavg - w.runs
    else:
        w["runs_saved"] = (w.balls * base_econ / 6 - w.runs) + (w.wickets - w.balls / base_bsr) * WICKET_VALUE[kind]
    for c in ["innings", "balls", "runs", "wickets", "hauls", "five_fors"]:
        w[c] = w[c].astype(int)
    w = w.reset_index()

    # ---------------- fielding
    fld = _rows(career.fielding[career.fielding.match_id.isin(ids) & career.fielding.resolved], scope, matches)
    if scope.team:
        fld = fld[fld.team == scope.team]
    if scope.teams:
        fld = fld[fld.team.isin(scope.teams)]
    fk = fld.assign(catch=fld.kind == "caught", stump=fld.kind == "stumped").groupby(keys).agg(
        catches=("catch", "sum"), stumpings=("stump", "sum"))
    f = appearances[["matches", "teams"]].join(fk, how="left").fillna({"catches": 0, "stumpings": 0})
    f["catches"] = f.catches.astype(int)
    f["stumpings"] = f.stumpings.astype(int)
    f["dismissals"] = f.catches + f.stumpings
    f = f.reset_index()

    tot_fifty = ((all_batted.runs >= 50)).sum()
    base = Baseline(
        kind=kind, matches=len(matches), strike_rate=base_sr, average=base_avg,
        runs_per_innings=_safe(tot_runs, tot_inns), six_rate=_safe(all_batted.sixes.sum(), tot_balls),
        boundary_share=_safe((4 * all_batted.fours + 6 * all_batted.sixes).sum(), tot_runs),
        fifty_rate=_safe(tot_fifty, tot_inns), duck_rate=_safe(((all_batted.runs == 0) & all_batted.out).sum(), tot_inns),
        economy=base_econ, bowl_strike_rate=base_bsr, bowl_average=base_bavg,
        dot_rate=_safe(dots_known.dots.sum(), dots_known.balls.sum()) if len(dots_known) else None,
        maiden_rate=_safe(mdn_known.maidens.sum(), mdn_known.balls.sum() / 6) if len(mdn_known) else None,
        haul_rate=_safe((all_bowl.wickets >= 4).sum(), (all_bowl.balls > 0).sum()),
        catches_per_match=_safe(f.catches.sum(), f.matches.sum()), has_dots=len(dots_known) > 0,
    )
    return b, w, f, base


# --------------------------------------------------------------------------- #
# Stat definitions shared by every page
# --------------------------------------------------------------------------- #


@dataclass
class DotChart:
    x: str  # column for the x axis
    y: str  # column for the y axis
    x_label: str
    y_label: str
    line: str  # "slope" (through the origin) or "flat"
    value: float  # slope, or the y value of a flat line
    line_label: str
    above: str
    below: str
    right: str
    better_below: bool = False


@dataclass
class Stat:
    id: str
    label: str
    column: str
    better: str  # "high" or "low"
    decimals: int
    definition: str
    dot: DotChart
    reference: float | None = None  # average line on the ranking chart
    keepers_only: bool = False


def _f1(v):
    return "–" if v is None or not np.isfinite(v) else f"{v:.1f}"


def stat_definitions(base: Baseline) -> dict[str, list[Stat]]:
    k = base.kind
    bat = [
        Stat("runs", "Runs", "runs", "high", 0, "Total runs scored. Rewards volume, so players who bat often rise to the top.",
             DotChart("innings", "runs", "Innings batted", "Runs", "slope", base.runs_per_innings,
                      f"{_f1(base.runs_per_innings)} runs per innings", "More runs per innings than the average batter.",
                      "Fewer runs per innings than average.", "Has batted more often.")),
        Stat("average", "Average", "average", "high", 1,
             "Runs per dismissal. Higher is better. Batters never dismissed have no average and are left out.",
             DotChart("outs", "runs", "Times dismissed", "Runs", "slope", base.average, f"average {_f1(base.average)}",
                      "Scores more runs per dismissal than average: a better average.", "Gets out more cheaply than average.",
                      "Has been dismissed more often, so the average rests on more innings."), reference=base.average),
        Stat("strike_rate", "Strike rate", "strike_rate", "high", 1,
             "Runs per 100 balls faced. Higher is better." + (" In multi-day cricket it matters much less than the average." if k == "multi" else ""),
             DotChart("balls", "runs", "Balls faced", "Runs", "slope", base.strike_rate / 100, f"strike rate {_f1(base.strike_rate)}",
                      "Scores faster than the average batter.", "Scores slower than average.", "Has faced more balls."),
             reference=base.strike_rate),
        Stat("fifty_plus", "50+ scores", "fifty_plus", "high", 0, "Innings of 50 or more, hundreds included.",
             DotChart("innings", "fifty_plus", "Innings batted", "50+ scores", "slope", base.fifty_rate,
                      f"one every {_f1(1 / base.fifty_rate) if base.fifty_rate else '–'} innings",
                      "Reaches 50 more often than average.", "Reaches 50 less often than average.", "Has batted more often.")),
        Stat("sixes", "Sixes", "sixes", "high", 0, "Total sixes hit.",
             DotChart("balls", "sixes", "Balls faced", "Sixes", "slope", base.six_rate,
                      f"a six every {_f1(1 / base.six_rate) if base.six_rate else '–'} balls",
                      "Hits sixes more often than average.", "Hits sixes less often than average.", "Has faced more balls.")),
        Stat("boundary_pct", "Boundary %", "boundary_pct", "high", 1,
             "Share of a batter's runs that came from fours and sixes. High means a big hitter, low means someone who runs ones and twos.",
             DotChart("runs", "boundary_runs", "Runs", "Runs from fours and sixes", "slope", base.boundary_share,
                      f"{_f1(base.boundary_share * 100)}% from boundaries", "More of their runs come in boundaries than average.",
                      "More of their runs come from running.", "Has scored more runs."), reference=base.boundary_share * 100),
        Stat("ducks", "Ducks", "ducks", "low", 0, "Dismissed without scoring. Lower is better, so 'Best' shows the fewest.",
             DotChart("innings", "ducks", "Innings batted", "Ducks", "slope", base.duck_rate, "average duck rate",
                      "Out for nought more often than average.", "Out for nought less often than average.",
                      "Has batted more often.", better_below=True)),
        Stat("runs_above_average", "Runs above average", "runs_above_average", "high", 1,
             ("Runs scored minus what an average batter would score for the same number of dismissals." if k == "multi" else
              "Runs scored minus what an average batter would score from the same balls. Rewards scoring a lot and scoring fast."),
             DotChart("balls", "runs_above_average", "Balls faced", "Runs above average", "flat", 0.0, "0 = exactly average",
                      "Better than the average batter in this selection.", "Worse than average.",
                      "Has faced more balls, so the figure is more reliable.")),
    ]
    bowl = [
        Stat("wickets", "Wickets", "wickets", "high", 0, "Total wickets taken.",
             DotChart("balls", "wickets", "Balls bowled", "Wickets", "slope", _safe(1, base.bowl_strike_rate),
                      f"a wicket every {_f1(base.bowl_strike_rate)} balls", "Takes wickets more often than the average bowler.",
                      "Takes wickets less often than average.", "Has bowled more.")),
        Stat("economy", "Economy", "economy", "low", 2, "Runs conceded per over. Lower is better.",
             DotChart("balls", "runs", "Balls bowled", "Runs conceded", "slope", base.economy / 6, f"economy {base.economy:.2f}",
                      "Concedes runs faster than average: expensive.", "Concedes fewer runs than average: tight.",
                      "Has bowled more.", better_below=True), reference=base.economy),
        Stat("strike_rate", "Strike rate", "strike_rate", "low", 1,
             "Balls bowled per wicket. Lower is better. Bowlers without a wicket are left out.",
             DotChart("balls", "wickets", "Balls bowled", "Wickets", "slope", _safe(1, base.bowl_strike_rate),
                      f"a wicket every {_f1(base.bowl_strike_rate)} balls", "Better strike rate: wickets come more often than average.",
                      "Worse strike rate than average.", "Has bowled more."), reference=base.bowl_strike_rate),
        Stat("average", "Average", "average", "low", 1,
             "Runs conceded per wicket. Lower is better. Bowlers without a wicket are left out.",
             DotChart("runs", "wickets", "Runs conceded", "Wickets", "slope", _safe(1, base.bowl_average),
                      f"average {_f1(base.bowl_average)}", "Better average: more wickets for the runs given away.",
                      "Worse average: wickets cost more runs.", "Has conceded more runs, usually from bowling more."),
             reference=base.bowl_average),
        (Stat("dot_pct", "Dot-ball %", "dot_pct", "high", 1,
              "Share of balls that went for no runs. Higher is better. Taken from the D column in T20 and Hundred scorecards.",
              DotChart("dot_balls", "dots", "Balls bowled", "Dot balls", "slope", base.dot_rate or 0,
                       f"{_f1((base.dot_rate or 0) * 100)}% dots", "Bowls more dot balls than average.",
                       "Bowls fewer dot balls than average.", "Has bowled more."), reference=(base.dot_rate or 0) * 100)
         if base.has_dots else
         Stat("maidens", "Maidens", "maidens", "high", 0,
              "Overs without a run conceded. Longer formats list maidens where T20 cards list dot balls.",
              DotChart("maiden_overs", "maidens", "Overs bowled", "Maidens", "slope", base.maiden_rate or 0,
                       "average maiden rate", "Bowls maidens more often than average.", "Bowls maidens less often.",
                       "Has bowled more."))),
        Stat("hauls", "4+ wicket hauls", "hauls", "high", 0, "Innings with four or more wickets.",
             DotChart("innings", "hauls", "Innings bowled", "4+ wicket hauls", "slope", base.haul_rate, "average rate",
                      "Takes big hauls more often than average.", "Takes big hauls less often.", "Has bowled in more innings.")),
        Stat("runs_saved", "Runs saved", "runs_saved", "high", 1,
             ("Runs an average bowler would have conceded for the same wickets, minus the runs actually conceded." if k == "multi" else
              f"Runs kept below the average for the balls bowled, plus extra wickets (each worth {WICKET_VALUE.get(k, 8)} runs in this format)."),
             DotChart("balls", "runs_saved", "Balls bowled", "Runs saved", "flat", 0.0, "0 = exactly average",
                      "Better than the average bowler in this selection.", "Worse than average.",
                      "Has bowled more, so the figure is more reliable.")),
    ]
    field_ = [
        Stat("catches", "Catches", "catches", "high", 0,
             "Catches taken, credited under the fielder's own name (so 'c de Kock' counts for Q de Kock).",
             DotChart("matches", "catches", "Matches played", "Catches", "slope", base.catches_per_match,
                      f"{base.catches_per_match:.2f} catches per match" if np.isfinite(base.catches_per_match) else "average per match",
                      "Takes more catches per match than average.", "Takes fewer catches per match.", "Has played more matches.")),
        Stat("stumpings", "Stumpings", "stumpings", "high", 0, "Stumpings, wicketkeepers only.",
             DotChart("matches", "stumpings", "Matches played", "Stumpings", "slope", np.nan, "average per match",
                      "Stumps more often than the average keeper.", "Stumps less often.", "Has played more matches."),
             keepers_only=True),
        Stat("dismissals", "Catches + stumpings", "dismissals", "high", 0,
             "Every dismissal a player had a hand in as a fielder or keeper.",
             DotChart("matches", "dismissals", "Matches played", "Catches + stumpings", "slope", np.nan, "average per match",
                      "Involved in more dismissals per match than average.", "Involved in fewer.", "Has played more matches.")),
    ]
    return {"bat": bat, "bowl": bowl, "field": field_}


def rank(table: pd.DataFrame, stat: Stat, best: bool = True, minimum: tuple[str, float] | None = None) -> pd.DataFrame:
    """Qualifying players sorted best (or worst) first on one stat."""
    t = table[table[stat.column].notna()]
    if minimum:
        t = t[t[minimum[0]] >= minimum[1]]
    if stat.keepers_only:
        t = t[t.stumpings > 0]
    ascending = (stat.better == "low") == best
    # Equal values: a "more is better" figure reached in fewer balls ranks higher (7 wickets in 66 balls
    # beats 7 in 96); a "less is better" figure kept up over more balls ranks higher (no ducks in 20
    # innings beats none in 2).  Fielding stats use matches the same way.
    tiebreak = "balls" if "balls" in t else "matches"
    tb_ascending = (stat.better == "high") == best
    return t.sort_values([stat.column, tiebreak, "player"], ascending=[ascending, tb_ascending, True])


def poss(name) -> str:
    """"England's", "West Indies'" (a name ending in s takes just the apostrophe)."""
    name = str(name)
    return name + ("'" if name.endswith(("s", "S")) else "'s")


def ordinal(n) -> str:
    """1st, 2nd, 3rd, 4th ... 11th, 12th, 13th, 21st, 22nd, 101st."""
    n = int(n)
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"
