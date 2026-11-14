"""Season MVP table: one points score per player per season, like the IPL's Most Valuable Player list.

Two ways to count, both from the scorecards:

* Impact points (every format): the match impact used on the Player stories page.  Runs, plus in white-ball cricket
  half the runs above (or below) what the section's strike rate would have made off the same balls; each wicket worth
  the section's runs per wicket, plus in white-ball cricket the runs kept below the section's economy; a catch or
  stumping a quarter of a wicket.  The averages are the whole section's, so seasons compare.
* IPL MVP points (T20 and The Hundred, whose scorecards print dot balls): 3.5 a wicket, 1 a dot ball, 2.5 a four,
  3.5 a six, 2.5 a catch and 2.5 a stumping, as the IPL counts them.

The new site counts no fielding (your decision of 14 November), so there the fielding part is 0: the IPL points then
differ from the IPL's own formula.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .stats import fielding_credits

IPL_POINTS = dict(wicket=3.5, dot=1.0, four=2.5, six=3.5, catch=2.5, stumping=2.5)
MVP_COLUMNS = ["player", "team", "matches", "batting", "bowling", "fielding", "points", "per_match"]


def counts_dots(career, section: str) -> bool:
    """Do this section's scorecards print dot balls (T20 and The Hundred cards do, longer formats print maidens)?"""
    ids = career.matches[career.matches.section == section].match_id
    return bool(career.bowling[career.bowling.match_id.isin(ids)].dots.notna().any())


def season_mvp(career, section: str, season: str, how: str = "impact") -> pd.DataFrame:
    """One row per player who played in this section and season, most points first (MVP_COLUMNS).  A name that
    turns up for two teams in one season is two players (the game prints both the same way; see the Data check
    page), so each team's is counted on its own."""
    m = career.matches
    sec_ids = m[m.section == section].match_id
    ids = m[(m.section == section) & (m.season == season)].match_id
    if ids.empty:
        return pd.DataFrame(columns=MVP_COLUMNS)
    xi = career.batting[career.batting.match_id.isin(ids)]  # everyone listed in a team, batting or not
    played = xi.groupby(["player", "team"]).agg(matches=("match_id", "nunique"))
    if how == "ipl":
        b = xi[xi.did_bat].groupby(["player", "team"])[["fours", "sixes"]].sum()
        w = career.bowling[career.bowling.match_id.isin(ids)].groupby(["player", "team"])[["wickets", "dots"]].sum()
        f = fielding_credits(career, ids)
        fl = f.groupby(["player", "team", "kind"]).size().unstack(fill_value=0)
        d = played.join(b, how="left").join(w, how="left").join(fl, how="left").fillna(0)
        for col in ("fours", "sixes", "wickets", "dots", "caught", "stumped"):
            if col not in d:
                d[col] = 0
        p = IPL_POINTS
        d["batting"] = d.fours * p["four"] + d.sixes * p["six"]
        d["bowling"] = d.wickets * p["wicket"] + d.dots * p["dot"]
        d["fielding"] = d.caught * p["catch"] + d.stumped * p["stumping"]
    else:
        from .playerdeep import match_impact
        imp = match_impact(career, sec_ids)  # the section's averages
        imp = imp[imp.match_id.isin(ids)].groupby(["player", "team"])[["bat", "bowl", "field"]].sum()
        d = played.join(imp, how="left").fillna(0).rename(columns={"bat": "batting", "bowl": "bowling",
                                                                  "field": "fielding"})
    d["points"] = d.batting + d.bowling + d.fielding
    d["per_match"] = d.points / d.matches.replace(0, np.nan)
    d = d.reset_index()[MVP_COLUMNS]
    return d.sort_values(["points", "per_match", "player"], ascending=[False, False, True]).reset_index(drop=True)
