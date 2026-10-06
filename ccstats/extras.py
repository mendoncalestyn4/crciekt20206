"""The second wave of features: streaks and career journeys, Player of the Match,
deadly duos, rivalries, "on pace for", extras, chasing, par scores, headlines,
all-round match performances, team style, opponent previews and the honours board.

Everything works on a set of match ids (one section, usually) so, like the rest
of the site, competitions are never mixed."""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import analysis as A
from .stats import Scope, kind_of, player_tables



# --------------------------------------------------------------------------- #
# 5 · streaks and career journey
# --------------------------------------------------------------------------- #


def _longest(flags) -> tuple[int, int]:
    """(longest run of True, current run of True at the end)."""
    best = run = 0
    for f in flags:
        run = run + 1 if f else 0
        best = max(best, run)
    return best, run


def batting_streaks(inns: pd.DataFrame, kind: str) -> list[dict]:
    """Longest and current runs for a player's innings (oldest first)."""
    if inns.empty:
        return []
    from .stats import bars_for
    b = bars_for(kind)
    runs, out = inns.runs.to_numpy(), inns.out.to_numpy()
    rows = []
    marks = list(dict.fromkeys([b["decent"], b["big"]]))  # a decent score and a big one: 20 and 50 in T20, 50 and 100 in Tests
    for label, flags in ([(f"Innings in a row with {m}+", runs >= m) for m in marks] +
                         [("Innings in a row reaching double figures", runs >= 10),
                         ("Innings in a row without a duck", ~((runs == 0) & out)),
                         ("Ducks in a row", (runs == 0) & out)]):
        best, now = _longest(flags)
        rows.append(dict(streak=label, longest=best, current=now))
    return rows


def bowling_streaks(spells: pd.DataFrame, kind: str = "t20") -> list[dict]:
    """Wicket streaks; the steps follow the format (1+, 2+, 3+ in T20; 1+, 2+, 4+ one-day; 1+, 3+, 5+ in Tests)."""
    from .stats import bars_for
    if spells.empty:
        return []
    w = spells.wickets.to_numpy()
    rows = []
    steps = bars_for(kind)["wicket_steps"]
    for label, flags in ([("Innings in a row taking a wicket" if k == 1 else f"Innings in a row with {k}+ wickets", w >= k)
                          for k in steps] + [("Wicketless innings in a row", w == 0)]):
        best, now = _longest(flags)
        rows.append(dict(streak=label, longest=best, current=now))
    return rows


def journey(career, player: str) -> pd.DataFrame:
    """Every team and competition a player has turned out in, in date order."""
    b = career.batting[career.batting.player == player]
    w = career.bowling[career.bowling.player == player]
    m = career.matches.set_index("match_id")
    rows = []
    apps = b.groupby(["match_id", "team"]).size().reset_index()[["match_id", "team"]]
    # by competition as it's run, so a World Cup shows as its own stop on the journey
    apps = apps.assign(date=apps.match_id.map(m.date), section=apps.match_id.map(m.event),
                       season=apps.match_id.map(m.season))
    for (team, section, season), g in apps.groupby(["team", "section", "season"]):
        ids = set(g.match_id)
        bb = b[b.match_id.isin(ids) & b.did_bat]
        ww = w[w.match_id.isin(ids)]
        rows.append(dict(first=g.date.min(), last=g.date.max(), team=team, section=section, season=season,
                         matches=len(ids), runs=int(bb.runs.sum()), wickets=int(ww.wickets.sum())))
    return pd.DataFrame(rows, columns=["first", "last", "team", "section", "season", "matches", "runs", "wickets"]) \
        .sort_values("first").reset_index(drop=True)


# --------------------------------------------------------------------------- #
# 9 · Player of the Match
# --------------------------------------------------------------------------- #


def player_of_match(career, ids) -> pd.DataFrame:
    """Awards per player, with how many came in knockouts and finals."""
    m = career.matches[career.matches.match_id.isin(ids) & (career.matches.player_of_match != "")]
    if m.empty:
        return pd.DataFrame(columns=["player", "team", "awards", "knockouts", "finals", "matches", "rate"])
    played = career.batting[career.batting.match_id.isin(ids)].groupby("player").match_id.nunique()
    team_of = {}
    for r in m.itertuples():
        t = career.batting[(career.batting.match_id == r.match_id) & (career.batting.player == r.player_of_match)].team
        team_of.setdefault(r.player_of_match, t.iloc[0] if len(t) else "")
    g = m.groupby("player_of_match").agg(awards=("match_id", "size"), knockouts=("knockout", "sum"),
                                         finals=("stage", lambda s: int((s == "Final").sum()))).reset_index()
    g = g.rename(columns={"player_of_match": "player"})
    g["team"] = g.player.map(team_of)
    g["matches"] = g.player.map(played).fillna(0).astype(int)
    g["rate"] = np.where(g.matches > 0, g.awards / g.matches.replace(0, np.nan) * 100, np.nan)
    g["knockouts"] = g.knockouts.astype(int)
    return g.sort_values(["awards", "rate"], ascending=False).reset_index(drop=True)[
        ["player", "team", "awards", "knockouts", "finals", "matches", "rate"]]


# --------------------------------------------------------------------------- #
# 11 · deadly duos (catcher + bowler)
# --------------------------------------------------------------------------- #


def deadly_duos(career, ids) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(fielder-and-bowler pairs, caught-and-bowled)."""
    f = career.fielding[career.fielding.match_id.isin(ids) & career.fielding.resolved]
    pairs = f[f.player != f.bowler]
    duo = (pairs.groupby(["player", "bowler", "team", "kind"]).size().rename("wickets").reset_index()
           .sort_values("wickets", ascending=False).reset_index(drop=True))
    cab = (f[(f.player == f.bowler) & (f.kind == "caught")].groupby(["bowler", "team"]).size().rename("wickets")
           .reset_index().sort_values("wickets", ascending=False).reset_index(drop=True))
    return duo, cab


# --------------------------------------------------------------------------- #
# 12 · rivalries
# --------------------------------------------------------------------------- #


def rivalries(career, ids) -> pd.DataFrame:
    """Every pair of teams that have met: record, and the last few results."""
    m = career.matches[career.matches.match_id.isin(ids)].sort_values("date")
    rows = []
    for pair, g in m.groupby(m.apply(lambda r: tuple(sorted((r.home, r.away))), axis=1)):
        a, b = pair
        wa, wb = int((g.winner == a).sum()), int((g.winner == b).sum())
        last = "".join("A" if w == a else "B" if w == b else "–" for w in g.winner.tail(5))
        rows.append(dict(team_a=a, team_b=b, played=len(g), wins_a=wa, wins_b=wb, other=len(g) - wa - wb,
                         last5=last, last=g.date.max()))
    return pd.DataFrame(rows, columns=["team_a", "team_b", "played", "wins_a", "wins_b", "other", "last5", "last"]) \
        .sort_values(["played", "last"], ascending=False).reset_index(drop=True)


def rivalry_players(career, ids, a: str, b: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Top run-scorers and wicket-takers in games between two teams."""
    m = career.matches[career.matches.match_id.isin(ids)]
    games = m[((m.home == a) & (m.away == b)) | ((m.home == b) & (m.away == a))].match_id
    bat = career.batting[career.batting.match_id.isin(games) & career.batting.did_bat]
    bowl = career.bowling[career.bowling.match_id.isin(games)]
    tb = bat.groupby(["player", "team"]).agg(runs=("runs", "sum"), innings=("runs", "size"), outs=("out", "sum")).reset_index()
    tb["average"] = np.where(tb.outs > 0, tb.runs / tb.outs.replace(0, np.nan), np.nan)
    tw = bowl.groupby(["player", "team"]).agg(wickets=("wickets", "sum"), runs=("runs", "sum"), balls=("balls", "sum")).reset_index()
    tw["average"] = np.where(tw.wickets > 0, tw.runs / tw.wickets.replace(0, np.nan), np.nan)
    return (tb.sort_values("runs", ascending=False).reset_index(drop=True),
            tw[tw.wickets > 0].sort_values(["wickets", "runs"], ascending=[False, True]).reset_index(drop=True))


# --------------------------------------------------------------------------- #
# 13 · on pace for
# --------------------------------------------------------------------------- #


def season_in_progress(career, section: str) -> tuple[str, int, int] | None:
    """(latest season, matches so far, matches in a full season) when the latest
    season of a section looks unfinished: fewer matches than the season before
    and no final yet.  None when there's nothing to go on."""
    m = career.matches[career.matches.section == section]
    seasons = sorted(m.season.unique())
    if len(seasons) < 2:
        return None
    cur, prev = seasons[-1], seasons[-2]
    now, full = int((m.season == cur).sum()), int((m.season == prev).sum())
    # a final ends a league's season; a World Cup final doesn't end a year of international cricket
    final = (m.season == cur) & (m.stage == "Final") & (m.level != "International")
    if now >= full or final.any():
        return None
    return cur, now, full


def on_pace(career, section: str, min_matches: int = 2) -> pd.DataFrame:
    """Runs and wickets each player is on course for this season, from their
    per-team-match rate and how many matches their team played last season,
    against the section's season record."""
    info = season_in_progress(career, section)
    cols = ["player", "team", "what", "so_far", "matches", "projected", "record", "record_holder", "beats_record"]
    if info is None:
        return pd.DataFrame(columns=cols)
    cur, _, _ = info
    m = career.matches[career.matches.section == section]
    seasons = sorted(m.season.unique())
    prev_ids = m[m.season == seasons[-2]]
    team_games_prev = pd.concat([prev_ids.home, prev_ids.away]).value_counts()
    team_games_now = pd.concat([m[m.season == cur].home, m[m.season == cur].away]).value_counts()
    bat, bowl, _, _ = player_tables(career, Scope(sections=[section], seasons=[cur]), by_team=True)
    # season records from finished seasons
    rows = []
    for what, table, col in (("runs", bat, "runs"), ("wickets", bowl, "wickets")):
        hist = []
        for s in seasons[:-1]:
            t = player_tables(career, Scope(sections=[section], seasons=[s]))[0 if what == "runs" else 1]
            if len(t):
                top = t.sort_values(col, ascending=False).iloc[0]
                hist.append((int(top[col]), top.player, s))
        rec = max(hist) if hist else (0, "", "")
        for r in table.itertuples():
            played, full = team_games_now.get(r.team, 0), team_games_prev.get(r.team, 0)
            if played < min_matches or not full or played >= full:
                continue
            so_far = int(getattr(r, col))
            proj = so_far / played * full
            rows.append(dict(player=r.player, team=r.team, what=what, so_far=so_far, matches=int(played),
                             projected=round(proj), record=rec[0], record_holder=f"{rec[1]} ({rec[2]})" if rec[1] else "",
                             beats_record=proj > rec[0] > 0))
    return pd.DataFrame(rows, columns=cols).sort_values("projected", ascending=False).reset_index(drop=True)


# --------------------------------------------------------------------------- #
# 15 · extras and discipline
# --------------------------------------------------------------------------- #


def discipline(career, ids) -> pd.DataFrame:
    """Extras each team conceded (as the fielding side), per match."""
    inn = career.innings[career.innings.match_id.isin(ids)]
    g = inn.groupby("opposition").agg(matches=("match_id", "nunique"), extras=("extras", "sum"), wides=("wides", "sum"),
                                      no_balls=("no_balls", "sum"), byes=("byes", "sum"), leg_byes=("leg_byes", "sum"),
                                      balls=("balls", "sum")).reset_index().rename(columns={"opposition": "team"})
    for c in ("extras", "wides", "no_balls", "byes", "leg_byes"):
        g[f"{c}_per_match"] = g[c] / g.matches
    g["extras_per_100_balls"] = np.where(g.balls > 0, g.extras / g.balls.replace(0, np.nan) * 100, np.nan)
    return g.sort_values("extras_per_match").reset_index(drop=True)


# --------------------------------------------------------------------------- #
# 16 · chasing
# --------------------------------------------------------------------------- #


def chasing(career, ids, min_innings: int = 2) -> pd.DataFrame:
    """Batting in chases (limited-overs sections, and 4th innings in multi-day),
    split into chases that were won and ones that were lost."""
    m = career.matches[career.matches.match_id.isin(ids)]
    last_inn = career.innings[career.innings.match_id.isin(ids)].groupby("match_id").innings_no.max()
    b = career.batting[career.batting.match_id.isin(ids) & career.batting.did_bat].copy()
    b = b[b.innings_no == b.match_id.map(last_inn)]  # the chasing innings is the last one
    b = b[b.innings_no > 1]
    win = m.set_index("match_id").winner
    b["result"] = np.where(b.match_id.map(win) == b.team, "won", np.where(b.match_id.map(win) == "", "other", "lost"))
    b = b[b.result != "other"]
    rows = []
    for p, g in b.groupby("player"):
        if len(g) < min_innings:
            continue
        won, lost = g[g.result == "won"], g[g.result == "lost"]
        def avg(x):
            return x.runs.sum() / x.out.sum() if x.out.sum() else np.nan
        rows.append(dict(player=p, team=" / ".join(sorted(set(g.team))), innings=len(g), runs=int(g.runs.sum()),
                         average=avg(g), strike_rate=g.runs.sum() / g.balls.sum() * 100 if g.balls.sum() else np.nan,
                         won_innings=len(won), won_average=avg(won), not_out_in_wins=int((~won.out).sum()),
                         lost_innings=len(lost), lost_average=avg(lost)))
    return pd.DataFrame(rows, columns=["player", "team", "innings", "runs", "average", "strike_rate", "won_innings",
                                       "won_average", "not_out_in_wins", "lost_innings", "lost_average"]) \
        .sort_values("runs", ascending=False).reset_index(drop=True)


# --------------------------------------------------------------------------- #
# 22 · par score at each wicket
# --------------------------------------------------------------------------- #


def par_by_wicket(career, ids) -> pd.DataFrame:
    """The typical (median) score when each wicket fell in these matches, and
    in how many innings that wicket fell."""
    f = career.fow[career.fow.match_id.isin(ids)]
    g = f.groupby("wicket").score.agg(["median", "size"]).reset_index().rename(columns={"median": "par", "size": "innings"})
    return g


# --------------------------------------------------------------------------- #
# 25 · all-round match performances
# --------------------------------------------------------------------------- #


def all_round_matches(career, ids, top: int = 20) -> pd.DataFrame:
    """Best single-match efforts with bat and ball together.  A wicket is worth
    the section's runs per wicket, so 4 wickets in a T20 is worth about as much
    as 4 x ~25 runs; batting and bowling then add up."""
    m = career.matches[career.matches.match_id.isin(ids)]
    inn = career.innings[career.innings.match_id.isin(ids)]
    rpw = inn.runs.sum() / max(inn.wickets.sum(), 1)
    bat = career.batting[career.batting.match_id.isin(ids) & career.batting.did_bat]
    bowl = career.bowling[career.bowling.match_id.isin(ids)]
    tb = bat.groupby(["match_id", "player", "team"]).agg(runs=("runs", "sum"), scores=("runs", lambda s: " & ".join(map(str, s))),
                                                         outs=("out", "sum")).reset_index()
    tw = bowl.groupby(["match_id", "player", "team"]).agg(wickets=("wickets", "sum"), conceded=("runs", "sum")).reset_index()
    t = tb.merge(tw, on=["match_id", "player", "team"], how="outer").fillna({"runs": 0, "wickets": 0, "conceded": 0, "scores": ""})
    t = t[(t.runs > 0) & (t.wickets > 0)]  # both bat and ball
    t["score"] = t.runs + t.wickets * rpw
    t = t.merge(m[["match_id", "date", "home", "away", "winner", "section"]], on="match_id")
    t["against"] = np.where(t.team == t.home, t.away, t.home)
    t["won"] = t.winner == t.team
    t["figures"] = [f"{s} runs & {int(w)}/{int(c)}" for s, w, c in zip(t.scores, t.wickets, t.conceded)]
    out = t.sort_values(["score", "date"], ascending=[False, True]).head(top).reset_index(drop=True)
    out.attrs["wicket_value"] = rpw
    return out[["player", "team", "against", "date", "figures", "runs", "wickets", "score", "won", "match_id"]]


# --------------------------------------------------------------------------- #
# 27 · team style
# --------------------------------------------------------------------------- #

STYLE = [  # (label, column, higher is ...)
    ("Share of runs in boundaries", "boundary_pct", "more boundary-heavy"),
    ("Sixes per match", "sixes_per_match", "more sixes"),
    ("Share of runs from the top 3", "top3_pct", "leans more on the top order"),
    ("Run rate", "run_rate", "scores faster"),
    ("Wickets per match (bowling)", "wkts_per_match", "takes more wickets"),
    ("Economy (bowling)", "economy", "concedes faster"),
    ("Share of wickets bowled or lbw", "bowled_lbw_pct", "more wickets that hit the stumps"),
    ("Share of wickets to catches", "caught_pct", "more wickets from catches"),
]


def team_style(career, ids) -> pd.DataFrame:
    """How each team plays, one row per team."""
    bat = career.batting[career.batting.match_id.isin(ids) & career.batting.did_bat]
    inn = career.innings[career.innings.match_id.isin(ids)]
    m = career.matches[career.matches.match_id.isin(ids)]
    rows = []
    for team in sorted(set(m.home) | set(m.away)):
        n = int(((m.home == team) | (m.away == team)).sum())
        b = bat[bat.team == team]
        i_for, i_against = inn[inn.team == team], inn[inn.opposition == team]
        took = career.batting[career.batting.match_id.isin(ids) & (career.batting.opposition == team) & career.batting.out]
        runs_bat = b.runs.sum()
        rows.append(dict(
            team=team, matches=n,
            boundary_pct=(4 * b.fours + 6 * b.sixes).sum() / runs_bat * 100 if runs_bat else np.nan,
            sixes_per_match=b.sixes.sum() / n if n else np.nan,
            top3_pct=b[b.position <= 3].runs.sum() / runs_bat * 100 if runs_bat else np.nan,
            run_rate=i_for.runs.sum() / i_for.balls.sum() * 6 if i_for.balls.sum() else np.nan,
            wkts_per_match=i_against.wickets.sum() / n if n else np.nan,
            economy=i_against.runs.sum() / i_against.balls.sum() * 6 if i_against.balls.sum() else np.nan,
            bowled_lbw_pct=took.how_out.isin(["bowled", "lbw"]).mean() * 100 if len(took) else np.nan,
            caught_pct=(took.how_out == "caught").mean() * 100 if len(took) else np.nan))
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# 32 · opponent preview
# --------------------------------------------------------------------------- #


def opponent_preview(career, ids, opponent: str, recent: int = 5) -> dict:
    """What to expect from a team: recent results, players in form, how their
    batters get out, how often they collapse."""
    tm = A.team_matches(career, ids, opponent)
    kind = kind_of(career.matches[career.matches.match_id.isin(ids)])
    recent_ids = list(tm.match_id.tail(recent * 2))  # their last few games for form
    bat = career.batting[career.batting.match_id.isin(recent_ids) & (career.batting.team == opponent) & career.batting.did_bat]
    bowl = career.bowling[career.bowling.match_id.isin(recent_ids) & (career.bowling.team == opponent)]
    fb = bat.groupby("player").agg(innings=("runs", "size"), runs=("runs", "sum"), outs=("out", "sum"),
                                   balls=("balls", "sum"), best=("runs", "max")).reset_index()
    fb["average"] = np.where(fb.outs > 0, fb.runs / fb.outs.replace(0, np.nan), np.nan)
    fb["strike_rate"] = np.where(fb.balls > 0, fb.runs / fb.balls.replace(0, np.nan) * 100, np.nan)
    fw = bowl.groupby("player").agg(innings=("balls", "size"), wickets=("wickets", "sum"), runs=("runs", "sum"),
                                    balls=("balls", "sum")).reset_index()
    fw["economy"] = np.where(fw.balls > 0, fw.runs / fw.balls.replace(0, np.nan) * 6, np.nan)
    fw["average"] = np.where(fw.wickets > 0, fw.runs / fw.wickets.replace(0, np.nan), np.nan)
    allbat = career.batting[career.batting.match_id.isin(ids) & (career.batting.team == opponent) & career.batting.out]
    how = allbat.how_out.value_counts(normalize=True) * 100
    col = A.collapses(career, tm.match_id, opponent)
    inns_count = int((career.innings.match_id.isin(tm.match_id) & (career.innings.team == opponent)).sum())
    return dict(matches=tm, recent=tm.tail(recent), kind=kind,
                batters=fb.sort_values("runs", ascending=False).reset_index(drop=True),
                bowlers=fw[fw.balls > 0].sort_values(["wickets", "economy"], ascending=[False, True]).reset_index(drop=True),
                how_out=how, collapses=len(col), innings=inns_count,
                depth=A.batting_depth(career, tm.match_id, opponent))


# --------------------------------------------------------------------------- #
# 37 · honours board
# --------------------------------------------------------------------------- #


def honours(career) -> pd.DataFrame:
    """Every finished competition-season: champions, runners-up, top run-scorer,
    top wicket-taker, Player of the Match in the final.  Champions come from
    the final; a competition without knockouts (a league, or a bilateral series)
    has its table leader or series winner."""
    from .tables import BILATERAL, league_tables
    m = career.matches
    # one row per competition as it's run (the ODI World Cup, not the whole ODIs section)
    has_knockouts = set(m[m.knockout].event)  # competitions decided by a final
    latest = m.groupby("event").season.max()
    rows = []
    for (event, season), g in m.groupby(["event", "season"]):
        if g.competition.iloc[0] in BILATERAL:
            continue  # bilateral series aren't a competition with a champion (see Competitions → Series)
        ids = g.match_id
        champ = runner = potm = ""
        how = ""
        teams: list[str] = []
        final = g[g.stage == "Final"].sort_values("date")
        if len(final) == 1:
            f = final.iloc[0]
            champ = f.winner or f.tiebreak_winner
            runner = (f.away if champ == f.home else f.home) if champ else ""
            potm, how = f.player_of_match, "won the final"
            if not champ and f.format == "Test" and f.result_type in ("draw", "tie"):
                # a drawn or tied World Test Championship Final: the two sides share the title
                teams, champ, how = [f.home, f.away], f"{f.home} and {f.away}", "final drawn: title shared"
        elif len(final) > 1 or event in has_knockouts:
            continue  # two finals (files from different saves), or the final isn't played yet
        else:  # a league with no final (e.g. the County Championship): the table decides
            tables = league_tables(career, ids)
            if len(tables) == 1 and len(tables[0][1]) > 1:
                t = tables[0][1]
                done = season != latest[event]  # a later season exists, so this one is over
                champ, runner = t.team.iloc[0], t.team.iloc[1]
                how = "top of the table" if done else "leading so far (season in progress)"
        if not champ:
            continue
        # the event's own matches only: a World Cup's top scorer, not the whole year's ODIs
        bat, bowl, _, _ = player_tables(career, Scope(sections=[g.section.iloc[0]], competitions=[g.competition.iloc[0]],
                                                      seasons=[season]))
        tb = bat.sort_values("runs", ascending=False).iloc[0] if len(bat) else None
        tw = bowl.sort_values(["wickets", "average"], ascending=[False, True]).iloc[0] if len(bowl) else None
        rows.append(dict(section=event, season=season, champions=champ, champion_teams=teams or [champ],
                         runners_up=runner, how=how,
                         top_runs=f"{tb.player} ({int(tb.runs)})" if tb is not None else "",
                         top_wickets=f"{tw.player} ({int(tw.wickets)})" if tw is not None and tw.wickets > 0 else "",
                         final_potm=potm, date=g.date.max()))
    return pd.DataFrame(rows, columns=["section", "season", "champions", "champion_teams", "runners_up", "how", "top_runs",
                                       "top_wickets", "final_potm", "date"]) \
        .sort_values(["date"], ascending=False).reset_index(drop=True)


def trophy_cabinet(career, team: str) -> pd.DataFrame:
    h = honours(career)
    mine = h.champion_teams.map(lambda t: team in t)  # a shared title counts for both sides
    return h[mine & ~h.how.str.contains("so far")][["section", "season", "how", "runners_up"]]


# --------------------------------------------------------------------------- #
# 23 · headlines
# --------------------------------------------------------------------------- #


def _short_label(r) -> str:
    """'Indian Premier League, 25 Apr' for a headline's match."""
    from .competitions import shown_name
    return f"{shown_name(r.section, r.event)}, {r.date.day} {r.date:%b}"


def headlines(career, n_matches: int = 10, limit: int = 8, max_records: int = 3, team: str = "") -> list[str]:
    """Short news lines about the most recently played matches, newest first.

    "Most recent" is the order you played them in (when the game saved each file),
    not the match date: the game saves some scorecards dated months ahead.  Every
    line names its match; new records are mixed in with their match and capped at
    `max_records`, so one record-breaking game can't push everything else out.
    With `team`: that team's most recent games only."""
    from . import partnerships as P
    from .records import new_record_lines, played_order
    order = played_order(career)
    if team:  # only this team's games
        order = order[(order.home == team) | (order.away == team)]
    recent = order.tail(n_matches)
    by_date = career.matches.sort_values(["date", "match_id"])
    rec_lines = new_record_lines(career, list(recent.source), min_matches=2)
    recs_by_src: dict[str, list[str]] = {}
    for src, msg in rec_lines:
        section, rest = msg.removeprefix("New record in ").split("! ", 1)
        recs_by_src.setdefault(src, []).append(f"🏅 New {section} record · {rest}")
    out: list[str] = []
    n_recs = 0
    for r in recent[::-1].itertuples():
        tag = f" ({_short_label(r)})"
        stage = f" in the {r.stage.lower()}" if r.knockout and r.stage else ""
        lines = []
        for line in recs_by_src.get(r.source, []):
            if n_recs < max_records:
                lines.append(line + tag)
                n_recs += 1
        bat = career.batting[(career.batting.match_id == r.match_id) & career.batting.did_bat]
        bowl = career.bowling[career.bowling.match_id == r.match_id]
        season_ids = by_date[(by_date.section == r.section) & (by_date.season == r.season) & (by_date.date <= r.date)].match_id
        for b in bat[bat.runs >= 100].itertuples():
            n = int(((career.batting.match_id.isin(season_ids)) & (career.batting.player == b.player)
                     & (career.batting.runs >= 100)).sum())
            line = f"💯 {b.player} hits {b.runs}{'' if b.out else '*'} for {b.team} v {b.opposition}{stage}"
            if n > 1:
                line += f" — {n}{P.suffix(n)} hundred in {r.section} in {r.season}"
            lines.append(line)
        from .stats import KIND, bars_for
        kind_r = KIND.get(r.format, "t20")
        for w in bowl[bowl.wickets >= bars_for(kind_r)["headline_haul"]].itertuples():  # 4-fors make news in a T20
            lines.append(f"🎯 {w.player} takes {w.wickets}/{w.runs} for {w.team} v {w.opposition}{stage}")
        if kind_r == "multi":  # ten in the match
            tm_ = bowl.groupby(["player", "team", "opposition"])[["wickets", "runs"]].sum().reset_index()
            for w in tm_[tm_.wickets >= 10].itertuples():
                lines.append(f"🔟 {w.player} takes {w.wickets}/{w.runs} in the match for {w.team} v {w.opposition}{stage}")
        for s_ in P.stands(career, [r.match_id]).query("runs >= 100").itertuples():
            said = f"{s_.batter1} & {s_.batter2}" if s_.known else s_.team
            score = f"{s_.runs}{'*' if s_.unbroken else ''}"
            if any(("stand" in ln or "partnerships" in ln) and said in ln and f" {score} " in ln for ln in lines):
                continue  # already a record line for this stand
            who = f"{s_.batter1} and {s_.batter2} put on" if s_.known else f"{s_.team} put on"
            lines.append(f"🤝 {who} {s_.runs}{'*' if s_.unbroken else ''} for the {s_.wicket}{P.suffix(s_.wicket)} "
                         f"wicket for {s_.team} v {s_.opposition}{stage}")
        finals = career.matches[(career.matches.event == r.event) & (career.matches.season == r.season)
                                & (career.matches.stage == "Final")]
        if r.knockout and r.stage == "Final" and (r.winner or r.tiebreak_winner) and len(finals) == 1:
            lines.append(f"🏆 {r.winner or r.tiebreak_winner} win the {r.event} {r.season}")
        for c in A.collapses(career, [r.match_id], r.home).itertuples():
            lines.append(f"📉 {r.home} collapse from {c.from_score} to {c.to_score} v {r.away}")
        for c in A.collapses(career, [r.match_id], r.away).itertuples():
            lines.append(f"📉 {r.away} collapse from {c.from_score} to {c.to_score} v {r.home}")
        out += [ln if ln.endswith(tag) else ln + tag for ln in lines]
        if len(out) >= limit:
            break
    return out[:limit]
