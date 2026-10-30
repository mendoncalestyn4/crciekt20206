"""The Players pages: your squads and everyone to search, then one player in full. The current site's Players page
(views/player.py) as data for the new one, every chart with what it shows and what it's for. New here: the player's
share of the team's runs and wickets, the matches they won for their side, and their marks out of 10 in every series.

Everything below the competition and season picker is for that competition only (Tests with Tests, the Ranji Trophy
with itself), as on the current site.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ccstats import analysis as A
from ccstats import attributes as AT
from ccstats import extras as E
from ccstats import marks as MK
from ccstats import players as PL
from ccstats import playerdeep as PD
from ccstats import teamdeep as TD
from ccstats.matchstory import pom_headline
from ccstats.records import by_played
from ccstats.stats import Scope, bars_for, player_tables

from . import myteam
from . import styleguide as SG
from .cache import kept

BAT_HELP = {"Mat": "Matches played", "Inns": "Innings batted", "NO": "Not outs", "Runs": "Runs", "HS": "Highest score (* = not out)",
            "Avg": "Runs per dismissal", "BF": "Balls faced", "SR": "Runs per 100 balls", "100": "Hundreds",
            "50": "Fifties (50-99)", "0": "Ducks", "4s": "Fours", "6s": "Sixes", "Ct": "Catches", "St": "Stumpings"}
BOWL_HELP = {"Mat": "Matches played", "Inns": "Innings bowled in", "Overs": "Six-ball overs (The Hundred's balls are converted)",
             "Mdns": "Maidens (only printed on longer-format cards)", "Dots": "Dot balls (only printed on T20 and Hundred cards)",
             "Runs": "Runs conceded", "Wkts": "Wickets", "BBI": "Best bowling in an innings", "BBM": "Best bowling in a match",
             "Avg": "Runs per wicket", "Econ": "Runs per over", "SR": "Balls per wicket", "4w": "Four wickets in an innings",
             "5w": "Five or more wickets in an innings", "10m": "Ten or more wickets in a match"}
DECIMALS = {"Avg": 2, "Econ": 2, "SR": 1}


def say(word: str) -> str:
    """A label as it's written in cricket: "Run out", "LBW"."""
    return "LBW" if word.lower() == "lbw" else word[:1].upper() + word[1:]


def fmt(v, d: int = 1) -> str:
    if v is None or (isinstance(v, (float, np.floating)) and not np.isfinite(v)):
        return "–"
    return f"{v:.{d}f}" if d else f"{int(round(v))}"


def count(n, one: str, many: str | None = None) -> str:
    return f"{int(n)} {one if int(n) == 1 else (many or one + 's')}"


# ------------------------------------------------------------------ the list of everyone, and your squads
def everyone(career) -> list[dict]:
    """Every player who has batted or bowled: their latest team, every team (latest last), matches, competitions."""
    def make():
        rows = pd.concat([career.batting[["match_id", "team", "player"]], career.bowling[["match_id", "team", "player"]]]).drop_duplicates()
        m = career.matches.set_index("match_id")
        pos = {mid: i for i, mid in enumerate(by_played(career, career.matches).match_id)}
        rows = rows.assign(at=rows.match_id.map(pos), section=rows.match_id.map(m.section)).sort_values("at")
        out = []
        for p, g in rows.groupby("player", sort=False):
            teams = list(dict.fromkeys(g.team[::-1]))[::-1]
            out.append(dict(player=p, team=teams[-1], teams=teams, matches=int(g.match_id.nunique()),
                            sections=list(g.drop_duplicates("match_id").section.value_counts().index)))
        return out
    return kept(career, ("everyone",), make)


def landing(career, mine: list[str]) -> dict:
    """The Players home: everyone to search, and each of your teams' squads in their latest competition and season."""
    squads = []
    for team in myteam.teams_by_latest(career, mine):
        m = career.matches[(career.matches.home == team) | (career.matches.away == team)]
        last = by_played(career, m).iloc[-1]
        ids = m[(m.section == last.section) & (m.season == last.season)].match_id
        b = career.batting[career.batting.match_id.isin(ids) & (career.batting.team == team)]
        w = career.bowling[career.bowling.match_id.isin(ids) & (career.bowling.team == team) & (career.bowling.balls > 0)]
        bt = b.groupby("player").agg(games=("match_id", "nunique"), runs=("runs", "sum"), outs=("out", "sum"))
        wt = w.groupby("player").agg(wickets=("wickets", "sum"), conceded=("runs", "sum"), balls=("balls", "sum"))
        d = bt.join(wt, how="outer").fillna(0)
        d["average"] = d.runs / d.outs.replace(0, np.nan)
        d["economy"] = d.conceded / d.balls.replace(0, np.nan) * 6
        d = d.sort_values(["games", "runs", "wickets"], ascending=False).reset_index()
        squads.append(dict(team=team, section=last.section, season=last.season,
                           players=SG.rows(d, ["player", "games", "runs", "average", "wickets", "economy"])))
    return SG.clean(dict(players=everyone(career), squads=squads))


# ------------------------------------------------------------------ pieces
def split_shows(t: pd.DataFrame, col: str, value: str, overall: float, what: str, low_better: bool = False,
                dec: int = 1) -> str:
    """'Best X: 45.2 (+31% on their 34.5 overall); worst Y: 20.1 (−42%).' for one split chart."""
    t = t[t[value].notna()]
    if t.empty or overall is None or not np.isfinite(overall) or not overall:
        return f"Not enough {what} to compare yet."
    t = t.sort_values(value, ascending=low_better)
    hi, lo = t.iloc[0], t.iloc[-1]
    pc = lambda v: f"{(v - overall) / overall * 100:+.0f}%"  # noqa: E731
    out = f"Best {say(str(hi[col])).lower()}: {fmt(hi[value], dec)} ({pc(hi[value])} on their {fmt(overall, dec)} overall)"
    if len(t) > 1:
        out += f"; worst {say(str(lo[col])).lower()}: {fmt(lo[value], dec)} ({pc(lo[value])})"
    return out + "."


def bars(t: pd.DataFrame, label: str, value: str, notes) -> list[dict]:
    return [dict(label=str(r[label]), value=SG.clean(r[value]), note=n) for (_, r), n in zip(t.iterrows(), notes)]


def table(df: pd.DataFrame, first: str, bowling: bool, fifties_first: bool = False) -> dict:
    """The standard batting or bowling table as text, the same columns everywhere (Balls dropped: Overs says it)."""
    helps = BOWL_HELP if bowling else BAT_HELP
    df = df.drop(columns=["Balls"], errors="ignore")
    cols = list(df.columns)
    if fifties_first and "50" in cols and "100" in cols:
        i, j = cols.index("100"), cols.index("50")
        cols[i], cols[j] = cols[j], cols[i]
    rows = []
    for _, r in df.iterrows():
        row = {}
        for c in cols:
            v = r[c]
            if c == first:
                row[c] = str(v)
            elif c in DECIMALS:
                row[c] = fmt(v, DECIMALS[c])
            elif c in ("Mdns", "Dots"):
                row[c] = "–" if pd.isna(v) else str(int(v))
            elif isinstance(v, str):
                row[c] = v
            else:
                row[c] = "–" if pd.isna(v) else str(int(v))
        rows.append(row)
    return dict(cols=cols, first=first, help={c: helps.get(c, "") for c in cols}, rows=rows)


def tables(career, section: str, season: str):
    """The batting, bowling and fielding tables for a competition (and season), kept with the career."""
    return kept(career, ("player_tables", section, season),
                lambda: player_tables(career, Scope(sections=[section], seasons=[season] if season else [])))


def _form(values, outs=None, labels=()) -> dict:
    """Every innings oldest first, the rolling line over the last 10 (5 for a career under 20 innings), as the
    current site draws it: nothing until a full window; for batting runs over dismissals, for bowling the mean."""
    v = [int(x) for x in values]
    n = len(v)
    w = 10 if n >= 20 else 5
    roll: list = []
    for i in range(n):
        if i + 1 < w:
            roll.append(None)
            continue
        part = v[i + 1 - w:i + 1]
        if outs is None:
            roll.append(round(float(np.mean(part)), 2))
        else:
            o = sum(outs[i + 1 - w:i + 1])
            roll.append(round(sum(part) / max(o, 1), 1))
    if outs is None:
        overall = round(float(np.mean(v)), 2) if n else None
    else:
        overall = round(sum(v) / max(sum(outs), 1), 1) if n else None
    return dict(values=v, rolling=roll, labels=list(labels), window=w, overall=overall)


# ------------------------------------------------------------------ the page
def page(career, player: str, section: str = "", season: str = "") -> dict:
    """Everything on one player's page; KeyError when they haven't batted or bowled."""
    bat_all = career.batting[career.batting.player == player]
    bowl_all = career.bowling[career.bowling.player == player]
    if bat_all.empty and bowl_all.empty:
        raise KeyError(player)
    m = career.matches
    mine_ids = set(bat_all.match_id) | set(bowl_all.match_id)
    my_matches = m[m.match_id.isin(mine_ids)]
    played = by_played(career, my_matches)
    team_of = pd.concat([bat_all[["match_id", "team"]], bowl_all[["match_id", "team"]]]).drop_duplicates("match_id").set_index("match_id").team
    teams = list(dict.fromkeys(team_of.reindex(played.match_id)[::-1].dropna()))[::-1]
    keeper = bool((A.keepers(career, my_matches.match_id).player == player).any())
    order = list(my_matches.section.value_counts().index)
    section = section if section in order else order[0]
    seasons = sorted(my_matches[my_matches.section == section].season.unique(), reverse=True)
    season = season if season in seasons else ""
    out: dict = dict(player=player, teams=teams, keeper=keeper, matches=len(my_matches), missing={},
                     section=section, season=season or "All seasons", sections=order, seasons=["All seasons"] + seasons)

    def piece(name, fn):
        try:
            out[name] = SG.clean(fn())
        except Exception as e:  # noqa: BLE001 - one part that can't be worked out never stops the others
            out[name] = None
            out["missing"][name] = f"Couldn't be worked out ({type(e).__name__}: {e})"

    by_order = lambda df: df.assign(_o=df.section.map(order.index)).sort_values("_o").drop(columns="_o")  # noqa: E731
    piece("card", lambda: _card(career, player, my_matches, bat_all, bowl_all))
    bat_rec = by_order(A.batting_record(career, my_matches.match_id, player))
    bowl_rec = by_order(A.bowling_record(career, my_matches.match_id, player))
    piece("bat_table", lambda: table(bat_rec, "section", False) if len(bat_rec) else None)
    piece("bowl_table", lambda: table(bowl_rec, "section", True) if len(bowl_rec) else None)
    piece("formats", lambda: _formats(career, player) if len(bat_rec) > 1 else None)
    piece("share", lambda: SG.rows(PL.team_share(career, player), ["section", "season", "team", "matches", "team_matches", "runs",
                                                                   "team_runs", "run_share", "wickets", "team_wickets", "wicket_share"]))
    piece("won", lambda: _won(career, player, my_matches, team_of))
    piece("marks", lambda: _marks(career, player))
    piece("journey", lambda: SG.rows(E.journey(career, player), ["first", "last", "team", "section", "season", "matches", "runs", "wickets"]))

    ids = m[(m.section == section) & ((m.season == season) if season else True)].match_id
    bat_t, bowl_t, fld_t, base = tables(career, section, season)
    kind = base.kind
    inns = A.batting_innings(career, ids, player)
    spells = A.bowling_spells(career, ids, player)
    roles = kept(career, ("roles", section, season), lambda: A.role_labels(career, ids, kind).set_index("player"))
    role = roles.loc[player] if player in roles.index else None
    out["role"] = SG.clean(dict(role=role.role, tags=list(role.tags), usual_position=role.usual_position)) if role is not None else None
    tabs = (["Batting"] if len(inns) else []) + (["Bowling"] if len(spells) else []) + ["Fielding"]
    is_bowler = role.role == "Bowler" if role is not None else (inns.empty or inns.position.median() >= 8)
    if is_bowler and "Bowling" in tabs:   # a bowler's page opens on their bowling, then fielding; batting comes last
        tabs = ["Bowling", "Fielding"] + [t for t in tabs if t not in ("Bowling", "Fielding")]
    out["tabs"] = tabs + ["Story"]
    out["batting"] = out["bowling"] = None
    if len(inns):
        piece("batting", lambda: _batting(career, player, section, season, ids, inns, bat_t, kind))
    if len(spells):
        piece("bowling", lambda: _bowling(career, player, section, season, ids, spells, bowl_t, kind))
    f = fld_t[fld_t.player == player]
    out["fielding"] = SG.clean(dict(matches=f.matches.iloc[0], catches=f.catches.iloc[0], stumpings=f.stumpings.iloc[0])) if len(f) else None
    piece("story", lambda: _story(career, player, section, season, ids, kind, my_matches))
    # attributes and the scout report: for the competition (every season of it), not one season
    piece("profile", lambda: kept(career, ("profile", section, player), lambda: AT.profile(career, section, player)))
    return out


def _card(career, player, my_matches, bat_all, bowl_all) -> dict:
    m = career.matches
    allb = bat_all[bat_all.did_bat].merge(m[["match_id", "date"]], on="match_id").sort_values(["date", "innings_no"])
    allw = bowl_all[bowl_all.balls > 0]
    hs = allb.assign(k=allb.runs * 2 + ~allb.out).sort_values("k").tail(1)
    bb = allw.assign(k=allw.wickets * 1000 - allw.runs).sort_values("k").tail(1)
    ach = kept(career, ("achievements",), lambda: PD.achievements(career))
    mine = ach[ach.player == player]
    grouped = mine.groupby("badge", sort=False).agg(times=("badge", "size"), detail=("detail", lambda x: " · ".join(map(str, x))))
    return dict(matches=len(my_matches), sections=int(my_matches.section.nunique()), runs=int(allb.runs.sum()),
                best_score=f"{int(hs.runs.iloc[0])}{'' if hs.out.iloc[0] else '*'}" if len(hs) else "–",
                wickets=int(allw.wickets.sum()),
                best_bowling=f"{int(bb.wickets.iloc[0])}/{int(bb.runs.iloc[0])}" if len(bb) else "–",
                badges=len(mine), last10=[int(x) for x in allb.runs.tail(10)],
                badge_list=[dict(badge=b, times=int(r.times), detail=r.detail) for b, r in grouped.head(6).iterrows()])


def _formats(career, player) -> dict | None:
    af = all_formats(career, player)
    if af.empty:
        return None
    best = af[af.best]
    return dict(rows=SG.rows(af, ["section", "matches", "runs", "average", "bat_vs", "strike_rate", "sr_vs", "wickets",
                                  "bowl_average", "bowl_vs", "best"]),
                shows=(f"Best format: {best.section.iloc[0]}, where they are {best.score.iloc[0]:+.0f}% better than the "
                       "average player.") if len(best) else "Not enough games in any format yet to compare.",
                for_="Compares formats fairly: a 35 average is great in T20 but ordinary in Tests, so each format is measured "
                     "against its own average (bowling: lower average is better, so + means better).")


def all_formats(career, player) -> pd.DataFrame:
    """PD.all_formats (every format against its own average), from the competition tables kept with the career rather
    than working each one out again (tests/test_playerpage.py checks the two agree)."""
    secs = career.matches[career.matches.match_id.isin(
        set(career.batting[career.batting.player == player].match_id))].section.value_counts().index
    rows = []
    for sec in secs:
        bat, bowl, _, base = tables(career, sec, "")
        b, w = bat[bat.player == player], bowl[bowl.player == player]
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
    d["best"] = (d.score == d.score.max()) if len(d) and d.score.notna().any() else False
    return d


def _won(career, player, my_matches, team_of) -> list[dict]:
    """The matches they were player of the match in a win for their side, newest first."""
    w = my_matches[(my_matches.player_of_match == player)]
    w = w[np.array([team_of.get(mid) == win for mid, win in zip(w.match_id, w.winner)], dtype=bool)]   # an empty list would pick columns
    w = by_played(career, w)[::-1]
    return [dict(id=r.match_id, section=r.section, opp=r.away if team_of.get(r.match_id) == r.home else r.home,
                 date=SG.clean(r.date), headline=pom_headline(career, r.match_id)) for r in w.itertuples()]


def _marks(career, player) -> list[dict]:
    s = MK.series_marks(career)
    s = s[s.player == player].sort_values("end", ascending=False)
    return SG.rows(s, ["series", "team", "label", "mark", "rank", "of", "line", "best", "best_match"])


# ------------------------------------------------------------------ batting
def _batting(career, player, section, season, ids, inns, bat_t, kind) -> dict:
    b = bat_t[bat_t.player == player].iloc[0]
    avg = float(b.average) if pd.notna(b.average) else None
    labels = [f"{r.runs}{'' if r.out else '*'} off {r.balls} v {r.opposition} · {r.date:%d %b %Y}" for r in inns.itertuples()]
    form = _form(inns.runs, list(inns.out.astype(int)), labels)
    n = min(form["window"], len(inns))
    last = inns.tail(n)
    recent = last.runs.sum() / max(last.out.sum(), 1)
    form["shows"] = (f"{len(inns)} innings. Their last {n} average {recent:.1f} against {fmt(avg)} overall "
                     f"({(recent - avg) / avg * 100:+.0f}%)." if avg else f"{len(inns)} innings, never dismissed.")
    form["for_"] = "Shows whether they are in form right now, not just how good they are over the whole career."
    out: dict = dict(kpis=dict(innings=int(b.innings), runs=int(b.runs), average=SG.clean(b.average), strike_rate=SG.clean(b.strike_rate),
                               high_score=b.high_score_text, hundreds=int(b.hundreds), fifties=int(b.fifties)), form=form)
    pool = bat_t[bat_t.innings >= 3]
    me = pool[pool.player == player]
    stats = {"Runs": "runs", "Average": "average", "Strike rate": "strike_rate", "Boundary %": "boundary_pct",
             "Runs above average": "runs_above_average"}
    out["compare"] = (dict(pool=int(len(pool)), values={k: round(float((pool[v] <= me[v].iloc[0]).mean() * 100))
                                                         for k, v in stats.items() if v in pool and pd.notna(me[v].iloc[0])})
                      if len(pool) >= 8 and len(me) else None)
    n4, n6 = int(inns.fours.sum()), int(inns.sixes.sum())
    out["runs_from"] = dict(fours=n4 * 4, sixes=n6 * 6, running=int(inns.runs.sum()) - n4 * 4 - n6 * 6, n4=n4, n6=n6)
    ss = A.split_batting(inns, "season").sort_values("season", ascending=False)
    top = ss.sort_values("runs", ascending=False).iloc[0]
    out["seasons"] = dict(rows=bars(ss, "season", "runs", [f"{i} innings · average {fmt(a)}" for i, a in zip(ss.innings, ss.average)]),
                          shows=f"Most runs in {top.season}: {top.runs} ({top.runs / max(ss.runs.sum(), 1) * 100:.0f}% of their "
                                f"{ss.runs.sum()} here), average {fmt(top.average)}.",
                          for_="Shows whether they are getting better or fading, season by season.")
    ho = A.how_out(inns)
    out["how_out"] = None if ho.empty else dict(
        rows=[dict(label=say(h), value=int(v)) for h, v in ho.items()],
        shows=f"{ho.iloc[0] / ho.sum() * 100:.0f}% of their {int(ho.sum())} dismissals are {say(ho.index[0]).lower()}.",
        for_="How bowlers get them out: a weakness to work on with your own players, or to attack in an opponent.")
    out["danger"] = _danger(career, ids, player)
    out["funnel"] = _funnel(career, ids, player)
    out["season_table"] = table(A.batting_record(career, ids, player, by="season").sort_values("season", ascending=False),
                                "season", False, fifties_first=kind == "t20")
    strength = kept(career, ("strength", section, season), lambda: A.team_strength(career, ids))
    splits = []
    for title, d, why in (
            ("Batting first or chasing", inns.assign(s=np.where(inns.batting_first, "Batting first", "Chasing")),
             "Shows whether they are better at setting a total or chasing one."),
            ("In wins, defeats and draws", inns.assign(s=inns.outcome.map(say)),
             "Shows whether their runs come when the team wins, or when the game is already lost."),
            ("Home or away", inns.assign(s=inns.venue.map(say)), "Shows how much home conditions help them."),
            ("Against stronger or weaker teams", inns.assign(s=A.opposition_strength(inns, strength)),
             "Shows whether they score against the good sides too, or fill their boots against the weak ones.")):
        t = A.split_batting(d, "s")
        splits.append(dict(title=title, rows=bars(t, "s", "average", [f"{n} innings, {r} runs, strike rate {fmt(s)}"
                                                                      for n, r, s in zip(t.innings, t.runs, t.strike_rate)]),
                           shows=split_shows(t, "s", "average", avg, "innings"), for_=why))
    med = np.median(list(strength.values())) if strength else 0
    out["splits"] = dict(overall=avg, rows=splits,
                         stronger=", ".join(sorted(t for t, v in strength.items() if v > med)) or "–")
    out["positions"] = _positions(career, ids, inns)
    out["came_in"] = _came_in(inns, kind, avg)
    cs = A.consistency(inns, kind)
    out["consistency"] = dict(bar=cs["bar"], past_bar_pct=cs["past_bar_pct"], single_figures_pct=cs["single_figures_pct"],
                              golden_ducks=cs["golden_ducks"], conversion_pct=SG.clean(cs["conversion_pct"]))
    nm = A.nemesis(career, ids, player).head(6)
    outs = int(inns.out.sum())
    out["nemesis"] = None if nm.empty else dict(
        rows=[dict(label=r.bowler, value=int(r.dismissals)) for r in nm.itertuples()],
        shows=f"{nm.bowler.iloc[0]} has got them out {count(nm.dismissals.iloc[0], 'time')}, "
              f"{nm.dismissals.iloc[0] / max(outs, 1) * 100:.0f}% of their {outs} dismissals.",
        for_="The bowlers who have their number: keep them away from these bowlers, or bring these bowlers on when this batter comes in.")
    out["streaks"] = E.batting_streaks(inns, kind)
    ch = kept(career, ("chasing", section, season), lambda: E.chasing(career, ids, min_innings=1))
    ch = ch[ch.player == player]
    out["chasing"] = None if ch.empty else SG.rows(ch, ["won_innings", "won_average", "lost_innings", "lost_average", "not_out_in_wins"])[0]
    t = A.split_batting(inns, "opposition").sort_values("runs", ascending=False)
    out["against"] = dict(rows=bars(t, "opposition", "average", [f"{n} innings, {r} runs, best {h}" for n, r, h in zip(t.innings, t.runs, t.high)]),
                          shows=split_shows(t[t.innings >= 2] if (t.innings >= 2).any() else t, "opposition", "average", avg, "innings")
                          + " (teams they have batted against at least twice)",
                          for_="Shows which opponents they like and which ones keep them quiet.")
    return out


def _positions(career, ids, inns) -> dict | None:
    """Every position they have batted at on its own (no. 3, no. 4, no. 5...): innings, runs, not outs, best score,
    average, strike rate, 50s and 100s, the average batter at that position here, and their edge on that batter,
    settled (attributes.position_table); their best is the biggest settled edge, from 2 innings there (as the scout
    report says it)."""
    if inns.empty:
        return None
    player = inns.player.iloc[0]
    t = AT.position_table(career, ids, player).set_index("position")
    best = AT.best_position(career, ids, player)
    rows = []
    for pos, g in inns.groupby("position"):
        r = t.loc[pos]
        rows.append(dict(position=int(pos), innings=len(g), runs=int(g.runs.sum()), not_outs=int((~g.out).sum()),
                         average=SG.clean(r.average), strike_rate=SG.clean(g.runs.sum() / g.balls.sum() * 100 if g.balls.sum() else None),
                         fifties=int(((g.runs >= 50) & (g.runs < 100)).sum()), hundreds=int((g.runs >= 100).sum()),
                         high=f"{int(g.runs.max())}{'' if g.loc[g.runs.idxmax(), 'out'] else '*'}",
                         all_average=SG.clean(r.all_average), edge=SG.clean(r.edge),
                         small=bool(len(g) < AT.SMALL), best=best is not None and best["position"] == int(pos)))
    if best:
        others = [x for x in rows if x["position"] != best["position"] and x["innings"] >= AT.BEST_FROM and x["edge"] is not None]
        shows = (f"Best at no. {best['position']}: {best['runs']} runs in {best['innings']} innings"
                 + (f" at {fmt(best['average'])}" if best["average"] is not None else ", never out")
                 + f", {best['edge']:+.0f}% on the average no. {best['position']} here ({fmt(best['all_average'])}), settled"
                 + (" (only a few innings there, so it may change)" if best["small"] else "")
                 + (f"; over a longer run, no. {best['proven']['position']} ({best['proven']['edge']:+.0f}% in "
                    f"{best['proven']['innings']} innings)" if best.get("proven") else "") + ". "
                 + " · ".join(f"no. {x['position']}: {x['edge']:+.0f}%" for x in others) + ("." if others else ""))
    elif len([x for x in rows if x["innings"] >= AT.BEST_FROM]) == 1:
        x = next(x for x in rows if x["innings"] >= AT.BEST_FROM)
        shows = f"Has batted twice or more only at no. {x['position']}, so there's no other position to compare it with."
    else:
        shows = "No position with 2 innings yet, so no best one to name."
    return dict(rows=[dict(label=f"No. {x['position']}", me=x["average"], all=x["all_average"], key=x["best"],
                           note=f"{x['innings']} innings, {x['runs']} runs, strike rate {fmt(x['strike_rate'])}") for x in rows],
                table=rows, best=best["position"] if best else None, shows=shows,
                for_="Tells you where to bat them: each position against the average batter there (gold is them, grey the "
                     "average batter at that position). 'They are' is settled: a few innings at the usual level for that "
                     "position are added before comparing, so two big scores count for a lot but can't decide it alone; "
                     "★ is their best, from 2 innings there.")


def _danger(career, ids, player) -> dict | None:
    dz = PD.danger_zones(career, ids, player)
    if dz.attrs.get("dismissals", 0) == 0:
        return None
    key_zone = PD.KEY_ZONE.get(dz.attrs.get("kind"))
    key_label = PD.zone_label(*key_zone) if key_zone else None
    key = ""
    if key_label in set(dz.zone):
        kz = dz[dz.zone == key_label].iloc[0]
        key = (f"Got in, out before 50 ({key_label}): {kz.pct:.0f}% of their dismissals ({int(kz.outs)} of {dz.attrs['dismissals']}), "
               f"every batter here {kz.all_pct:.0f}%" + (" · a weak spot" if kz.pct >= kz.all_pct + 5 else
                                                         " · better than most" if kz.pct <= kz.all_pct - 5 else ""))
    worst = dz.assign(gap=dz.pct - dz.all_pct).sort_values("gap", ascending=False).iloc[0]
    return dict(key=key, rows=[dict(label=r.zone, me=SG.clean(r.pct), all=SG.clean(r.all_pct), note=f"{int(r.outs)} dismissals",
                                    key=r.zone == key_label) for r in dz.itertuples()],
                shows=f"{dz.pct.iloc[0]:.0f}% of their {dz.attrs['dismissals']} dismissals come before 10 (every batter here: "
                      f"{dz.all_pct.iloc[0]:.0f}%). Their most dangerous band compared with others is {worst.zone}: "
                      f"{worst.pct:.0f}% against {worst.all_pct:.0f}%.",
                for_="Shows when to attack this batter (or when to protect your own): a big share early means they're vulnerable "
                     "before they're set. The bands follow the format.")


def _funnel(career, ids, player) -> dict | None:
    fn = PD.funnel(career, ids, player)
    if not fn.attrs.get("innings"):
        return None
    keys = fn.attrs.get("keys", [])
    conv = fn[fn.highlight & fn.key_from.astype(bool)]
    parts = [f"{r.from_key:.0f}% of their {r.key_from}s became {r.mark}s (everyone: {fmt(r.all_from_key, 0)}%)"
             for r in conv.itertuples() if np.isfinite(r.from_key)]
    first = fn[fn.mark == keys[0]].iloc[0] if keys else None
    lead = f"They reach {keys[0]} in {first.pct:.0f}% of innings (everyone: {first.all_pct:.0f}%). " if first is not None else ""
    extra = ""
    if fn.attrs.get("kind") == "t20":
        h, f = fn.attrs.get("hundreds", 0), fn.attrs.get("fifties", 0)
        extra = (f"Hundreds, on their own: {h} in {fn.attrs['innings']} innings"
                 + (f" · {fn.attrs['fifty_to_100']:.0f}% of their {f} fifties went on to 100 (everyone: {fmt(fn.attrs['all_fifty_to_100'], 0)}%)" if f else "")
                 + ". In T20 the fifty is the big score, so the chart stops there.")
    return dict(rows=[dict(mark=int(r.mark), pct=SG.clean(r.pct), all_pct=SG.clean(r.all_pct), highlight=bool(r.highlight))
                      for r in fn.itertuples()], extra=extra,
                shows=lead + ("; ".join(parts) + "." if parts else ""),
                for_="Shows whether they turn starts into big scores. Key marks: " + ", ".join(str(k) for k in keys)
                     + " in this format; the grey dots are every batter here.")


def _came_in(inns, kind, avg) -> dict:
    ci = inns.dropna(subset=["came_in_score"]).copy()
    bar = bars_for(kind)   # pressure and platform depend on the format: 3 down for 40 is trouble in a T20, 250 a platform in a Test
    press, plat = bar["pressure_score"], bar["platform"]
    pressure = f"Under pressure (3+ down for {press} or fewer)"
    ci["situation"] = np.select([ci.came_in_wickets == 0, (ci.came_in_wickets >= 3) & (ci.came_in_score <= press), ci.came_in_score >= plat],
                                ["Opening the innings", pressure, f"Big platform ({plat}+ on the board)"], "Normal")
    t = A.split_batting(ci, "situation")
    shows = split_shows(t, "situation", "average", avg, "innings")
    if len(ci):
        wk = float(ci.came_in_wickets.mean())
        shows += f" On average they came in at {ci.came_in_score.mean():.0f} for {fmt(wk, 0 if wk.is_integer() else 1)}."
    r = ci[ci.situation.str.startswith("Under")].sort_values("runs", ascending=False).head(5)
    return dict(rows=bars(t, "situation", "average", [f"{n} innings" for n in t.innings]), shows=shows,
                for_="Shows whether they handle pressure. The score comes from the fall of wickets: the number 5 walks in when the 3rd wicket falls.",
                press=press, rescue=[dict(at=f"{int(x.came_in_score)}/{int(x.came_in_wickets)}", score=f"{x.runs}{'' if x.out else '*'}",
                                          balls=int(x.balls), against=x.opposition, date=SG.clean(x.date)) for x in r.itertuples()])


# ------------------------------------------------------------------ bowling
def _bowling(career, player, section, season, ids, spells, bowl_t, kind) -> dict:
    w = bowl_t[bowl_t.player == player].iloc[0]
    labels = [f"{r.wickets}/{r.runs} v {r.opposition} · {r.date:%d %b %Y}" for r in spells.itertuples()]
    form = _form(spells.wickets, None, labels)
    n = min(form["window"], len(spells))
    rw, aw = spells.tail(n).wickets.mean(), spells.wickets.mean()
    form["shows"] = (f"{len(spells)} innings bowled. Their last {n} average {rw:.2f} wickets an innings against {aw:.2f} overall"
                     + (f" ({(rw - aw) / aw * 100:+.0f}%)." if aw else "."))
    form["for_"] = "Shows whether they are taking wickets right now, not just over the whole career."
    econ = float(w.economy) if pd.notna(w.economy) else None
    out: dict = dict(kpis=dict(wickets=int(w.wickets), average=SG.clean(w.average), economy=SG.clean(w.economy),
                               strike_rate=SG.clean(w.strike_rate), best=w.best, hauls=int(w.hauls)), form=form)
    ss = A.split_bowling(spells, "season").sort_values("season", ascending=False)
    top = ss.sort_values("wickets", ascending=False).iloc[0]
    out["seasons"] = dict(rows=bars(ss, "season", "wickets", [f"average {fmt(a)} · economy {fmt(e, 2)}" for a, e in zip(ss.average, ss.economy)]),
                          shows=f"Most wickets in {top.season}: {int(top.wickets)} ({top.wickets / max(ss.wickets.sum(), 1) * 100:.0f}% of "
                                f"their {int(ss.wickets.sum())} here), economy {fmt(top.economy, 2)}.",
                          for_="Shows whether they are getting better or fading, season by season.")
    wt = A.wicket_types(career, ids, player)
    out["how_wickets"] = None if wt.empty else dict(
        rows=[dict(label=say(h), value=int(v)) for h, v in wt.items()],
        shows=f"{wt.iloc[0] / wt.sum() * 100:.0f}% of their {int(wt.sum())} wickets are {say(wt.index[0]).lower()}.",
        for_="How they get batters out: bowled and lbw mean they hit the stumps; catches mean they need the fielders, so set the field for them.")
    out["match_pattern"] = None
    if kind == "multi":
        mp = kept(career, ("pattern", section, season), lambda: TD.bowler_match_pattern(career, ids, 1))
        me = mp[mp.player == player]
        if me.empty:
            out["match_pattern"] = dict(none="Hasn't bowled in both innings of a match yet.", first="", second="", both="", best="")
        else:
            r = me.iloc[0]
            out["match_pattern"] = dict(first=fmt(r.first_avg), second=fmt(r.second_avg), both=f"{r.both_pct:.0f}% of {r.matches} matches",
                                        best=r.best_match,
                                        shows=(f"Their average is {r.change:+.0f}% in the second innings ({fmt(r.second_avg)} against "
                                               f"{fmt(r.first_avg)}).") if np.isfinite(r.change) else "",
                                        for_="Shows whether they get better as the pitch wears (lower is better) and how often they strike in "
                                             "both innings: the ones to bowl on a final day.")
    ww = PD.with_without(career, ids, player)
    a, b = ww["with"], ww["without"]
    test = ww["kind"] == "multi"
    shows = for_ = ""
    if np.isfinite(a["economy"]) and np.isfinite(b["economy"]) and a["economy"]:
        d = (b["economy"] - a["economy"]) / a["economy"] * 100
        word = ("a strike bowler: when the wickets don't come, the runs do" if d > 15 else
                "a container: tight whether or not the wickets come" if d < 5 else "in between")
        shows = f"Economy {fmt(a['economy'], 2)} in spells with a wicket, {fmt(b['economy'], 2)} without ({d:+.0f}%): {word}."
        for_ = ("Tells a strike bowler from a containing one, so you know who to bowl when you must stop the runs."
                + (" In Tests, maidens show the control too." if test else ""))
    out["with_without"] = dict(rows=[dict(label="Took a wicket", spells=a["spells"], wickets=a["wickets"], economy=fmt(a["economy"], 2),
                                          maidens=fmt(a["maidens_per_10"], 1) if test else "–"),
                                     dict(label="Wicketless", spells=b["spells"], wickets=0, economy=fmt(b["economy"], 2),
                                          maidens=fmt(b["maidens_per_10"], 1) if test else "–")],
                               shows=shows, for_=for_)
    out["season_table"] = table(A.bowling_record(career, ids, player, by="season").sort_values("season", ascending=False), "season", True)
    q = A.wicket_quality(career, ids, player)
    out["quality"] = None if not q else dict(
        rows=[dict(label="Top order (1-3)", value=q["top_order"]), dict(label="Middle order (4-7)", value=q["middle_order"]),
              dict(label="Tail (8-11)", value=q["tail"])],
        shows=f"{q['top_seven_pct']:.0f}% of their {q['total']} wickets are specialist batters (positions 1-7): {q['top_order']} top "
              f"order, {q['middle_order']} middle order, {q['tail']} tail.",
        for_="Shows whether their wickets are the ones that matter or mostly tail-enders.")
    bn = A.bunnies(career, ids, player).head(6)
    tw = int(spells.wickets.sum())
    out["bunnies"] = None if bn.empty else dict(
        rows=[dict(label=r.player, value=int(r.dismissals)) for r in bn.itertuples()],
        shows=f"They have got {bn.player.iloc[0]} out {count(bn.dismissals.iloc[0], 'time')}, "
              f"{bn.dismissals.iloc[0] / max(tw, 1) * 100:.0f}% of their {tw} wickets.",
        for_="The batters they have the wood on: bring them on when these batters come in.")
    out["streaks"] = E.bowling_streaks(spells, kind)
    splits = []
    for i, (title, d, col) in enumerate([
            ("Bowling first or second", spells.assign(s=np.where(spells.batting_first, "Their side batted first", "Their side bowled first")), "s"),
            ("Against each team", spells, "opposition")]):
        t = A.split_bowling(d, col).sort_values("wickets", ascending=False)
        splits.append(dict(title=title, rows=bars(t, col, "economy", [f"{wk} wickets, average {fmt(a)}" for wk, a in zip(t.wickets, t.average)]),
                           shows=split_shows(t[t.balls >= 12] if (t.balls >= 12).any() else t, col, "economy",
                                             econ if econ is not None else np.nan,
                                             "overs", low_better=True, dec=2) + " Lower is better.",
                           for_="Shows whether they bowl better defending a total or chasing one." if i == 0 else
                                "Shows which teams they keep quiet and which ones get after them."))
    out["splits"] = dict(overall=econ, rows=splits)
    return out


# ------------------------------------------------------------------ story
def _story(career, player, section, season, ids, kind, my_matches) -> dict:
    out: dict = {}
    mi = kept(career, ("impact", section, season), lambda: PD.match_impact(career, ids))
    mine = mi[mi.player == player].sort_values("date")
    if mine.empty:
        out["impact"] = None
    else:
        best = mine.sort_values("impact", ascending=False).iloc[0]
        g = mi.groupby("player").impact
        need = min(3, len(mine))   # rank among players with as many games (up to 3), so one-off games don't count
        per = g.mean()[g.size() >= need]
        rank = int((per > mine.impact.mean()).sum()) + 1
        out["impact"] = dict(
            rows=[dict(label=f"v {r.opponent} · {r.date:%d %b %Y}", value=round(float(r.impact)), won=bool(r.won),
                       note=f"{int(r.runs)} runs, {count(r.wickets, 'wkt')}") for r in mine.itertuples()],
            shows=f"Average {mine.impact.mean():.0f} a match, number {rank} of the {len(per)} players here with {need}+ matches. "
                  f"Best: {best.impact:.0f} v {best.opponent} ({int(best.runs)} runs, {count(best.wickets, 'wkt')}). Green bars are wins.",
            for_="Puts batting, bowling and fielding on one scale: runs, plus each wicket worth the competition's runs per wicket"
                 + (", with scoring speed and economy counted in white-ball cricket." if mi.attrs["kind"] != "multi" else "."))
    rk = kept(career, ("rank_by_season", section, player), lambda: PD.rank_by_season(career, section, player))
    if rk.empty:
        out["rank"] = None
    else:
        r0 = rk.iloc[-1]
        bits = []
        if np.isfinite(r0.runs_rank):
            bits.append(f"{int(r0.runs_rank)} of {r0.runs_of} for runs")
        if np.isfinite(r0.wickets_rank):
            bits.append(f"{int(r0.wickets_rank)} of {r0.wickets_of} for wickets")
        peak = rk.runs_rank.min() if rk.runs_rank.notna().any() else rk.wickets_rank.min()
        out["rank"] = dict(rows=SG.rows(rk, ["season", "runs_rank", "runs_of", "wickets_rank", "wickets_of"]),
                           shows=f"In {r0.season}: " + (", ".join(bits) or "no runs or wickets") + (f". Peak: {int(peak)}." if np.isfinite(peak) else "."),
                           for_="A career story at a glance: when they peaked and whether they're climbing or fading.")
    fa = kept(career, ("fastest", section, season), lambda: PD.fastest(career, ids))
    unit = fa.attrs.get("unit", "innings")
    mf = fa[fa.player == player]
    out["milestones"] = dict(unit=unit, rows=[dict(milestone=f"{r.milestone:,} {r.what}", took=f"{r.taken} {unit}",
                                                   fastest=f"{r.rank} of {int(((fa.what == r.what) & (fa.milestone == r.milestone)).sum())}",
                                                   date=SG.clean(r.date)) for r in mf.itertuples()])
    ach = kept(career, ("achievements",), lambda: PD.achievements(career))
    ma = ach[(ach.player == player) & ach.match_id.isin(set(ids))]
    out["badges"] = [dict(badge=r.badge, detail=r.detail, id=r.match_id, date=SG.clean(r.date)) for r in ma.itertuples()]
    fi = kept(career, ("firsts", player), lambda: PL.firsts(career, player))
    out["firsts"] = [dict(date=SG.clean(r.date), what=r.what, detail=r.detail, id=r.match_id, against=r.against) for r in fi.itertuples()]
    wb, ww = kept(career, ("win_when", section, season), lambda: PL.win_when(career, ids, 1))
    rows = []
    for d, label in ((wb, f"{wb.attrs.get('big', 50)}+ with the bat"), (ww, f"{ww.attrs.get('haul', 3)}+ wickets")):
        r = d[d.player == player]
        if len(r):
            r = r.iloc[0]
            rows.append(dict(label=label, times=int(r.times), when=fmt(r.pct_when, 0) + "%", other=fmt(r.pct_other, 0) + "%"))
    out["fires"] = dict(rows=rows, none=f"No {wb.attrs.get('big', 50)}+ scores or {ww.attrs.get('haul', 3)}-wicket hauls here yet.")
    q = kept(career, ("quirks", section, season), lambda: PL.quirks(career, ids))
    _, cp = kept(career, ("carried", section, season), lambda: PL.carried(career, ids, 1))
    ah = kept(career, ("after_hundred", section, season), lambda: PL.after_hundred(career, ids))
    nine, pairs, nots = (q[k][q[k].player == player] for k in ("nineties", "pairs", "not_outs"))
    share, ah = cp[cp.player == player], ah[ah.player == player]
    lines = []
    if len(nine):
        lines.append(f"😬 Out in the nineties {count(nine.times.iloc[0], 'time')}: {nine.scores.iloc[0]}.")
    if len(pairs):
        lines.append(f"🥚🥚 {count(pairs.pairs.iloc[0], 'pair')}: out for 0 in both innings.")
    if len(nots):
        lines.append(f"🛡️ Not out in {nots.not_outs.iloc[0]} of {nots.innings.iloc[0]} innings ({nots.pct.iloc[0]:.0f}%).")
    if len(share):
        lines.append(f"🏋️ Makes {share.share.iloc[0]:.1f}% of their team's runs in the innings they bat.")
    if len(ah):
        lines.append(f"💯➡️ After a hundred: {ah.next_scores.iloc[0]} (average {fmt(ah.next_avg.iloc[0])} against {fmt(ah.average.iloc[0])} overall).")
    out["quirks"] = lines
    out["compare"] = _compare(career, player, section, my_matches)
    return out


def _compare(career, player, section, my_matches) -> dict | None:
    seasons = sorted(my_matches[my_matches.section == section].season.unique(), reverse=True)
    if len(seasons) < 2:
        return None
    sec_ids = career.matches[career.matches.section == section].match_id
    br = A.batting_record(career, sec_ids, player, by="season").set_index("season")
    wr = A.bowling_record(career, sec_ids, player, by="season").set_index("season")
    per: dict = {s: {} for s in seasons}
    for s in seasons:
        for col, dec, better in (("Mat", 0, None), ("Inns", 0, None), ("Runs", 0, "high"), ("Avg", 2, "high"),
                                 ("SR", 1, "high"), ("100", 0, "high"), ("50", 0, "high")):
            v = br[col].get(s, np.nan) if col in br else np.nan
            v = float(v) if pd.notna(v) else None
            per[s][f"Batting {col}"] = dict(v=v, text=fmt(v, dec) if v is not None else "–", better=better)
        if len(wr):
            for col, dec, better in (("Wkts", 0, "high"), ("Avg", 2, "low"), ("Econ", 2, "low"), ("SR", 1, "low")):
                v = wr[col].get(s, np.nan) if col in wr else np.nan
                v = float(v) if pd.notna(v) else None
                per[s][f"Bowling {col}"] = dict(v=v, text=fmt(v, dec) if v is not None else "–", better=better)
    return dict(seasons=seasons, per=per)

