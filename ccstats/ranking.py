"""Rankings (stage 3): batters, bowlers and all-rounders ranked on the marks out of 10, as the official world rankings
rank them (your answers of 19 and 24 November).

- **The marks are the Player page's** (ccstats/marks.py): each player's batting and his bowling in every series or
  tournament marked out of 10 against every player's series in the career. A series still going counts with the
  matches played so far, marked on the same yardstick, so the rankings move after every match.
- **A player's rating** is his marks over the competition's last two seasons, each series counting for its games and
  **recent series counting more**: a series that ended a year before counts half (answer 28).
- **All-rounders**: ranked on batting rating × bowling rating, so only players good at both rise (answer 24); shown
  as its square root, on the same 1 to 10 scale as the marks (the order is the product's).
- **Who is ranked** (answer 25): at least 10 innings in the last two seasons in T20 cricket, 8 in one-day, Test and
  first-class cricket (bowlers: the same in innings bowled), from at least 3 different series or tournaments; in a
  competition played as one tournament a season (a domestic league, the IPL), from both seasons. Those close to it
  are listed as "not ranked yet", with what they still need.
- Several competitions ticked (answer 29): each player's rating in each, where he is ranked, combined by his innings
  in each, so the format he plays most counts most.
No fielding is counted (your decision of 14 November)."""

from __future__ import annotations

from statistics import NormalDist

import numpy as np
import pandas as pd

from .analysis import BOWLER_BALLS
from .marks import MIN_REFERENCE, SETTLE, _mark, match_values, series_key
from .records import by_played
from .stats import KIND

HALF_LIFE_DAYS = 365      # a series that ended a year ago counts half (answer 28)
MIN_INNS = {"t20": 10, "one": 8, "multi": 8}
NEAR = 0.6                # "not ranked yet": at least this share of the innings needed
KINDS = ("batting", "bowling", "all-round")


def states(career) -> pd.DataFrame:
    """Every player's series as it stood after each of his matches: one row per player per match, with his batting
    and bowling marks for the series so far (the Player page's marks once the series is over). Kept with the career."""
    from .keep import on_career
    return on_career(career, ("ranking_states",), lambda: _states(career))


def _states(career) -> pd.DataFrame:
    cols = ["series", "team", "player", "match_id", "date", "section", "season", "kind", "games", "bat_inns",
            "bowl_inns", "bat_mark", "bowl_mark"]
    m = career.matches[career.matches.result_type != "no result"]
    if m.empty:
        return pd.DataFrame(columns=cols)
    m = m.assign(series=series_key(m))
    v = match_values(career, m.match_id)
    if v.empty:
        return pd.DataFrame(columns=cols)
    meta = m.set_index("match_id")[["series", "date", "format", "level", "section", "season"]]
    v = v.join(meta, on="match_id")
    v = v[(v.balls > 0) | (v.runs > 0) | (v.outs > 0) | (v.balls_bowled > 0) | (v.dismissals > 0)]
    v = v.assign(reference=np.where(v.level == "International", v.format, v.section))
    bat = career.batting[career.batting.match_id.isin(v.match_id)]
    pos = bat.groupby(["match_id", "team", "player"]).position.min()
    inns = bat[bat.did_bat].groupby(["match_id", "team", "player"]).size().rename("bat_inns")
    bowl = career.bowling[career.bowling.match_id.isin(v.match_id) & (career.bowling.balls > 0)]
    binns = bowl.groupby(["match_id", "team", "player"]).size().rename("bowl_inns")
    v = v.join(pos, on=["match_id", "team", "player"]).join(inns, on=["match_id", "team", "player"]).join(
        binns, on=["match_id", "team", "player"])
    v[["bat_inns", "bowl_inns"]] = v[["bat_inns", "bowl_inns"]].fillna(0).astype(int)
    v["bat_v"], v["bowl_v"] = v.bat + v.field, v.bowl + v.field
    v["batted"] = (v.balls > 0) | (v.outs > 0)
    v = by_played(career, v)   # the order the matches were played
    key = ["series", "team", "player"]

    # the yardstick: every finished series as the Player page marks it (ccstats/marks.py, the same rules)
    g = v.groupby(key)
    s = g.agg(games=("match_id", "nunique"), bat_v=("bat_v", "sum"), bowl_v=("bowl_v", "sum"), balls=("balls", "sum"),
              outs=("outs", "sum"), balls_bowled=("balls_bowled", "sum"), position=("position", "median"),
              format=("format", "first"), reference=("reference", "first")).reset_index()
    counts = s.reference.value_counts()
    small = s.reference.map(counts) < MIN_REFERENCE
    s.loc[small, "reference"] = s.loc[small, "format"].map(KIND)
    kind = s.format.map(KIND)
    s["is_batter"] = s.position.le(7) & ((s.balls > 0) | (s.outs > 0))
    s["is_bowler"] = s.balls_bowled / s.games >= kind.map(BOWLER_BALLS).astype(float)
    yard: dict = {}
    for ref, idx in s.groupby("reference").groups.items():
        part = s.loc[idx]
        for col, who in (("bat_v", "is_batter"), ("bowl_v", "is_bowler")):
            pool = part[part[who]]
            if pool.empty:
                continue
            usual = pool[col].sum() / pool.games.sum()
            settled = (part[col] + SETTLE * usual) / (part.games + SETTLE)
            yard[(ref, col)] = (usual, np.sort(settled[part[who]].to_numpy()))
    v = v.drop(columns="reference").join(s.set_index(key)["reference"], on=key)   # the reference each series is marked against

    # each series as it stood after each match, marked on that yardstick
    c = v.groupby(key)
    st = v[key + ["match_id", "date", "section", "season", "format", "reference", "bat_inns", "bowl_inns"]].copy()
    st["games"] = c.cumcount() + 1
    for col in ("bat_v", "bowl_v", "balls_bowled"):
        st[col] = c[col].cumsum()
    st["batted"] = c.batted.cummax()
    st["bat_inns"] = c.bat_inns.cumsum()
    st["bowl_inns"] = c.bowl_inns.cumsum()
    st["kind"] = st.format.map(KIND)
    norm = NormalDist()
    for col, out in (("bat_v", "bat_mark"), ("bowl_v", "bowl_mark")):
        st[out] = np.nan
        for ref, idx in st.groupby("reference").groups.items():
            y = yard.get((ref, col))
            if y is None:
                continue
            usual, ref_vals = y
            part = st.loc[idx]
            settled = ((part[col] + SETTLE * usual) / (part.games + SETTLE)).to_numpy()
            lo = np.searchsorted(ref_vals, settled, side="left")
            hi = np.searchsorted(ref_vals, settled, side="right")
            n = len(ref_vals)
            p = np.clip((lo + hi) / 2 / n, 0.5 / n, 1 - 0.5 / n)
            z = np.array([norm.inv_cdf(x) for x in p])
            if col == "bat_v":
                keep = part.batted.to_numpy()
            else:   # as the Player page: bowling marked for half a bowler's share, or when bowling was all he did
                share = part.kind.map(BOWLER_BALLS).astype(float).to_numpy() / 2
                keep = (part.balls_bowled / part.games).to_numpy() >= share
                keep |= (part.balls_bowled.to_numpy() > 0) & ~part.batted.to_numpy()
            st.loc[idx, out] = np.where(keep, _mark(z), np.nan)
    return st[cols].reset_index(drop=True)


def _last_two(seasons: pd.Series) -> list:
    return sorted(seasons.unique())[-2:]


def table_at(st: pd.DataFrame, section: str, date, what: str) -> pd.DataFrame:
    """The rankings in one competition as they stood after the matches of `date`: player, team, rating, innings,
    series, seasons, qualified, needs (what a player not ranked yet still needs), rank (ranked players only)."""
    cols = ["player", "team", "rating", "bat", "bowl", "inns", "series", "seasons", "qualified", "needs", "rank"]
    here = st[(st.section == section) & (st.date <= date)]
    if here.empty:
        return pd.DataFrame(columns=cols)
    window = _last_two(here.season)
    here = here[here.season.isin(window)]
    last = here.groupby(["series", "team", "player"]).tail(1)
    kind = last.kind.iloc[0]
    age = (pd.Timestamp(date) - here.groupby(["series", "team", "player"]).date.transform("max")).dt.days
    last = last.assign(w=last.games * 0.5 ** (age.loc[last.index].clip(lower=0) / HALF_LIFE_DAYS))
    per_season = here.groupby("season").series.nunique()
    one_a_season = bool((per_season <= 1).all())
    need_series = 2 if one_a_season else 3
    need_inns = MIN_INNS.get(kind, 8)

    def rate(col):
        x = last[last[col].notna()]
        r = (x[col] * x.w).groupby(x.player).sum() / x.w.groupby(x.player).sum()
        return r

    bat, bowl = rate("bat_mark"), rate("bowl_mark")
    team = last.sort_values("date").groupby("player").team.last()
    agg = last.groupby("player").agg(bat_inns=("bat_inns", "sum"), bowl_inns=("bowl_inns", "sum"),
                                     series=("series", "nunique"), seasons=("season", "nunique"))
    t = agg.join(bat.rename("bat")).join(bowl.rename("bowl")).join(team)
    if what == "batting":
        t = t.assign(rating=t.bat, inns=t.bat_inns)
    elif what == "bowling":
        t = t.assign(rating=t.bowl, inns=t.bowl_inns)
    else:
        # ranked on batting × bowling, as the official rankings (answer 24); shown on the same 1 to 10 scale as the
        # marks (the square root of the product: the same order, a number that reads like the others)
        t = t.assign(rating=np.sqrt(t.bat * t.bowl), inns=np.minimum(t.bat_inns, t.bowl_inns))
    t = t[t.rating.notna()]
    many = t.seasons >= 2 if one_a_season else t.series >= need_series
    ok = (t.inns >= need_inns) & many
    if what == "all-round":
        ok &= (t.bat_inns >= need_inns) & (t.bowl_inns >= need_inns)

    def needs(r) -> str:
        bits = []
        short = need_inns - int(r.inns)
        if short > 0:
            bits.append(f"{short} more innings" + (" bowled" if what == "bowling" else ""))
        if one_a_season and r.seasons < 2:
            bits.append("a game in a second season")
        elif not one_a_season and r.series < need_series:
            k = need_series - int(r.series)
            bits.append(f"{k} more series or tournament{'s' if k > 1 else ''}")
        return ", ".join(bits)

    t = t.assign(qualified=ok, needs=[("" if q else needs(r)) for q, r in zip(ok, t.itertuples())]).reset_index()
    t = t.sort_values(["qualified", "rating", "inns", "player"], ascending=[False, False, False, True])
    ranked = t[t.qualified]
    t["rank"] = np.nan
    t.loc[ranked.index, "rank"] = ranked.rating.rank(method="min", ascending=False)
    return t[cols].reset_index(drop=True)


def history(career, section: str, what: str) -> pd.DataFrame:
    """The rankings after every match day of a competition: date, matches (played that day), player, rating, rank
    (ranked players only). Kept with the career."""
    from .keep import on_career
    return on_career(career, ("ranking_history", section, what), lambda: _history(career, section, what))


def _history(career, section: str, what: str) -> pd.DataFrame:
    st = states(career)
    here = st[st.section == section]
    m = career.matches[career.matches.section == section]
    rows = []
    per_day = m.groupby("date").size()
    for d in sorted(here.date.unique()):
        t = table_at(st, section, d, what)
        t = t[t.qualified]
        if len(t):
            rows.append(t.assign(date=d, matches=int(per_day.get(d, 0)))[["date", "matches", "player", "team", "rating", "rank"]])
    if not rows:
        return pd.DataFrame(columns=["date", "matches", "player", "team", "rating", "rank"])
    return pd.concat(rows, ignore_index=True)


def board(career, section: str, what: str) -> dict:
    """Now: the ranked table with each player's movement since before the competition's last match day, his peak
    (best rating and when) and his time at No. 1 (matches played in the competition while he was top); the players
    not ranked yet; and the No. 1 reigns."""
    st = states(career)
    here = st[st.section == section]
    if here.empty:
        return dict(table=pd.DataFrame(), near=pd.DataFrame(), reigns=[], latest=None)
    latest = here.date.max()
    now = table_at(st, section, latest, what)
    h = history(career, section, what)
    days = sorted(h.date.unique()) if len(h) else []
    before = h[h.date == days[-2]].set_index("player")["rank"] if len(days) >= 2 and days[-1] == latest else pd.Series(dtype=float)
    ranked = now[now.qualified].copy()
    ranked["moved"] = [None if p not in before.index else int(before[p] - r) for p, r in zip(ranked.player, ranked["rank"])]
    ranked["new"] = [p not in before.index for p in ranked.player]
    peak = h.sort_values(["rating", "date"], ascending=[False, True]).groupby("player").head(1).set_index("player")
    tops = h[h["rank"] == 1]
    at_one = tops.groupby("player").matches.sum()
    ranked["peak"] = ranked.player.map(peak.rating)
    ranked["peak_date"] = ranked.player.map(peak.date)
    ranked["at_one"] = ranked.player.map(at_one).fillna(0).astype(int)
    # the No. 1 reigns, oldest first: who was top, from when to when, matches at No. 1 (level at the top: both count)
    reigns = []
    for d in days:
        top = sorted(tops[tops.date == d].player)
        n = int(h[h.date == d].matches.iloc[0])
        if reigns and reigns[-1]["players"] == top:
            reigns[-1]["to"], reigns[-1]["matches"] = d, reigns[-1]["matches"] + n
        else:
            reigns.append(dict(players=top, start=d, to=d, matches=n))
    need = MIN_INNS.get(here.kind.iloc[0], 8)
    near = now[~now.qualified & (now.inns >= NEAR * need)].sort_values(["inns", "rating"], ascending=False)
    return dict(table=ranked.reset_index(drop=True), near=near.reset_index(drop=True), reigns=reigns, latest=latest,
                need=need, peaks=h.sort_values(["rating", "date"], ascending=[False, True]).groupby("player").head(1))


def combined(career, sections: list[str], what: str) -> pd.DataFrame:
    """Several competitions ticked (answer 29): each player's rating where he is ranked, combined by his innings in
    each, so the format he plays most counts most. player, team, rating, inns, parts ("Test 7.4 (12 inns) · ...")."""
    st = states(career)
    rows = []
    for sec in sections:
        here = st[st.section == sec]
        if here.empty:
            continue
        t = table_at(st, sec, here.date.max(), what)
        t = t[t.qualified]
        rows.append(t.assign(section=sec))
    if not rows:
        return pd.DataFrame(columns=["player", "team", "rating", "inns", "parts", "formats"])
    a = pd.concat(rows, ignore_index=True)
    g = a.assign(wr=a.rating * a.inns).groupby("player")
    out = pd.DataFrame({"rating": g.wr.sum() / g.inns.sum(), "inns": g.inns.sum(), "formats": g.section.nunique(),
                        "team": a.sort_values("inns").groupby("player").team.last()})
    parts: dict[str, list[str]] = {}
    for p_, s_, r_, i_ in zip(a.player, a.section, a.rating, a.inns):
        parts.setdefault(p_, []).append(f"{s_} {r_:.1f} ({int(i_)} inns)")
    out["parts"] = [" · ".join(parts[p_]) for p_ in out.index]
    out = out.reset_index().sort_values(["rating", "inns", "player"], ascending=[False, False, True]).reset_index(drop=True)
    out["rank"] = out.rating.rank(method="min", ascending=False).astype(int)
    return out


def breakdown(career, section: str, player: str, what: str, date=None) -> tuple[list[dict], float | None]:
    """How a rating is worked out ("how it's worked out" on hover): each series in the window with its mark, games
    and weight, and the rating they make. All-round: the batting and the bowling rating."""
    from .marks import _labels
    st = states(career)
    here = st[st.section == section]
    if here.empty:
        return [], None
    date = here.date.max() if date is None else date
    here = here[here.date <= date]
    here = here[here.season.isin(_last_two(here.season))]
    mine = here[here.player == player]
    if mine.empty:
        return [], None
    last = mine.groupby(["series", "team"]).tail(1)
    end = mine.groupby(["series", "team"]).date.transform("max").loc[last.index]
    age = (pd.Timestamp(date) - end).dt.days.clip(lower=0)
    m = career.matches[career.matches.match_id.isin(set(mine.match_id))]
    labels = _labels(m.assign(series=series_key(m)))
    rows = []
    for r, a in zip(last.itertuples(), age):
        w = r.games * 0.5 ** (a / HALF_LIFE_DAYS)
        rows.append(dict(series=labels.get((r.series, r.team), r.series), games=int(r.games), weight=float(w),
                         bat=None if r.bat_mark != r.bat_mark else int(r.bat_mark),
                         bowl=None if r.bowl_mark != r.bowl_mark else int(r.bowl_mark)))
    def avg(k):
        x = [(r[k], r["weight"]) for r in rows if r[k] is not None]
        return sum(v * w for v, w in x) / sum(w for _, w in x) if x else None
    if what == "batting":
        return rows, avg("bat")
    if what == "bowling":
        return rows, avg("bowl")
    b, w = avg("bat"), avg("bowl")
    return rows, (b * w) ** 0.5 if b is not None and w is not None else None
