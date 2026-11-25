"""Compare players (stage 3): "plays like", the three players most like the one picked (the plan's new feature 1 of
26 October; your answers 15 and 16 of 14 November).

Players are only ever matched inside the same competition (a T20I batter with T20I batters, an IPL batter with IPL
batters), on the figures that say how they play rather than how much:
- batting: average (3 dismissals at least), strike rate, the share of their runs in fours and sixes, and where they
  bat (their usual position);
- bowling: average and strike rate (3 wickets at least), economy, and when in the innings they bowl (their usual place
  in the bowling order: the new ball or later).
Each figure is put on the same footing (how far from the competition's middle player, in that figure's own spread),
and how alike two players are is 100% when every figure matches, falling the further apart they are
(100 × e^(-d²/2), d being the average gap in those spreads)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .stats import Scope, player_tables

FEATURES = {"Batting": [("average", "Avg"), ("strike_rate", "SR"), ("boundary_pct", "Bdry %"), ("position", "Usual position")],
            "Bowling": [("average", "Avg"), ("economy", "Econ"), ("strike_rate", "SR"), ("order", "Usual bowling order")]}


def _pool(career, section: str, seasons: list, disc: str) -> pd.DataFrame:
    """Every player in this competition (and seasons) with enough to judge how they play, and their figures."""
    bat, bowl, _, _ = player_tables(career, Scope(sections=[section], seasons=list(seasons)))
    ids = set(Scope(sections=[section], seasons=list(seasons)).match_ids(career.matches))
    if disc == "Batting":
        t = bat[(bat.outs >= 3) & bat.average.notna() & bat.strike_rate.notna()].copy()
        b = career.batting[career.batting.match_id.isin(ids) & career.batting.did_bat]
        t["position"] = t.player.map(b.groupby("player").position.median())
    else:
        t = bowl[(bowl.wickets >= 3) & bowl.average.notna() & bowl.economy.notna()].copy()
        w = career.bowling[career.bowling.match_id.isin(ids)]
        w = w.assign(order=w.groupby(["match_id", "innings_no"]).cumcount() + 1)   # the order the card lists them in
        t["order"] = t.player.map(w[w.balls > 0].groupby("player").order.median())
    cols = [c for c, _ in FEATURES[disc]]
    return t.dropna(subset=cols).reset_index(drop=True)


def plays_like(career, section: str, seasons: list, player: str, disc: str = "Batting", n: int = 3) -> pd.DataFrame:
    """The `n` players in `section` most like `player`: player, teams, alike (0-100) and the figures compared. Empty
    when the player hasn't enough here to judge (3 dismissals, or 3 wickets)."""
    cols = [c for c, _ in FEATURES[disc]]
    t = _pool(career, section, seasons, disc)
    out_cols = ["player", "teams", "alike"] + cols
    if player not in set(t.player) or len(t) < 2:
        return pd.DataFrame(columns=out_cols)
    x = t[cols].astype(float)
    spread = x.std(ddof=0).replace(0, np.nan)
    z = (x - x.median()) / spread
    z = z.fillna(0.0)
    me = z[t.player == player].iloc[0]
    d = np.sqrt(((z - me) ** 2).mean(axis=1))
    t = t.assign(alike=100 * np.exp(-(d ** 2) / 2))
    t = t[t.player != player].sort_values(["alike", "player"], ascending=[False, True]).head(n)
    return t[out_cols].reset_index(drop=True)


def figures_of(career, section: str, seasons: list, player: str, disc: str = "Batting") -> dict | None:
    """The player's own figures that plays-like compares (None when there aren't enough to judge)."""
    t = _pool(career, section, seasons, disc)
    row = t[t.player == player]
    return None if row.empty else {c: float(row.iloc[0][c]) for c, _ in FEATURES[disc]}
