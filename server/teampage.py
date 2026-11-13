"""The Teams page (stage 2): one team's record in one competition (and season), overall or home or away, with every
part the current site's Teams page shows, each worked out by the same engine functions with the same words. One tab
is worked out at a time (the comebacks need the win chance through every match), and each part on its own: one that
can't be worked out says why and never stops the others."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ccstats import aim as AIM
from ccstats import partnerships as PS
from ccstats import analysis as A
from ccstats import catalogue as CAT
from ccstats import extras as E
from ccstats import seasonal as SN
from ccstats import teamdeep as TD
from ccstats import teamplay as TP
from ccstats import winprob as WP
from ccstats.stats import Scope, bars_for, kind_of, ordinal, player_tables, poss

from . import styleguide as SG
from .cache import kept

TABS = ["Overview", "How they win", "Opponents and stages", "Season", "Series and Tests", "Squad", "Results"]
BILATERAL = ("ODIs (bilateral series)", "T20Is (bilateral series)", "Tests (bilateral series)")
WORD = dict(W="won", L="lost", D="drawn", T="tied", NR="no result")


# --------------------------------------------------------------------------- small helpers, as the current site has them
def fmt(v, decimals: int) -> str:
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return "–"
    return f"{v:.{decimals}f}" if decimals else f"{int(round(v))}"


def pct(v, decimals: int = 0) -> str:
    t = fmt(v, decimals)
    return t if t == "–" else t + "%"


def signed(v, decimals: int = 0) -> str:
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return "–"
    return f"{v:+.{decimals}f}"


def _n(k, one: str, many: str | None = None) -> str:
    k = int(k)
    return f"{k} {one if k == 1 else (many or one + 's')}"


def say(word: str) -> str:
    return "LBW" if word.lower() == "lbw" else word[:1].upper() + word[1:]


TEAM_COLUMNS = {"Team", "Against", "Opponent", "Champions", "Runners-up", "Rivalry"}   # columns that name teams


def table(cols, rows, num=(), hi=None, links=None) -> dict:
    """A plain table: column names, rows of text, which columns are numbers, the rows to light up, and a match to open
    from each row (the first column links to it). Columns that name teams (by their heading) show each team's badge."""
    cols = list(cols)
    return SG.clean(dict(cols=cols, rows=[list(r) for r in rows], num=sorted(num), hi=list(hi) if hi else [],
                         links=list(links) if links else [],
                         badges=[i for i, c in enumerate(cols) if c in TEAM_COLUMNS and i not in set(num)]))


# --------------------------------------------------------------------------- the pickers
def choices(career) -> dict:
    """Every competition (most matches first) with its seasons (newest first) and teams (A to Z, those still to play
    marked)."""
    def make():
        m = career.matches
        counts = m.section.value_counts()
        out = []
        for sec, n in counts.items():
            here = m[m.section == sec]
            teams, todo = CAT.section_teams(here, sec, here)
            out.append(dict(section=sec, matches=int(n), seasons=sorted(map(str, here.season.unique()), reverse=True),
                            teams=list(teams), todo=sorted(todo), neutral=bool(here.neutral.all())))
        return out
    return kept(career, ("team_choices",), make)


def where(career, section: str, season: str, team: str, venue: str):
    """The matches picked (ids), those of them on screen (here), this team's own (tids, home or away only when asked),
    the scope for the player tables, the kind of cricket."""
    m = career.matches
    scope = Scope(sections=[section], seasons=[] if season in ("", "All seasons") else [season])
    ids = scope.match_ids(m)
    here = m[m.match_id.isin(ids)]
    if venue == "all":
        tids = ids
    else:
        tids = pd.Index(here[((here.home == team) if venue == "home" else (here.away == team)) & ~here.neutral].match_id)
    scope_t = scope if venue == "all" else Scope(sections=[section], seasons=scope.seasons, team=team, venue=venue)
    return ids, here, tids, scope_t, kind_of(here)


# --------------------------------------------------------------------------- the top of the page
def head(career, section: str, season: str, team: str, venue: str) -> dict:
    """The record (played, won-lost, win %, net run rate or drawn, the current run, the last five, the longest runs),
    the batting and bowling ratings, and a plain reason when there's nothing to show."""
    m = career.matches
    label = {"all": "Overall", "home": "Home", "away": "Away"}[venue]
    ids, here, tids, _, _ = where(career, section, season, team, venue)
    every, todo = CAT.section_teams(m[m.section == section], section, here)
    when = "" if season in ("", "All seasons") else f" in {season}"
    if team in todo or team not in every:
        played = m[(m.home == team) | (m.away == team)].section.value_counts()
        return dict(none=f"{team} haven't played in {section}{when} yet. Their record here fills in after their first game"
                    + (". In this career they have played: " + ", ".join(f"{s} ({n})" for s, n in played.items()) + "."
                       if len(played) else "."), elsewhere=list(played.index[:4]))
    tbl = kept(career, ("team_table", tuple(ids), venue), lambda: A.team_table(career, ids, venue))
    if team not in set(tbl.team):
        if venue != "all" and here.neutral.all():
            return dict(none=f"{section} matches are played at neutral venues, so there are no home or away games. "
                             "Choose Overall.", elsewhere=[])
        other = [v for v in ("Overall", "Home", "Away") if v != label]
        return dict(none=f"{team} haven't played {'at home' if venue == 'home' else 'away'} in {section}"
                         f"{'' if season in ('', 'All seasons') else ' ' + season} yet. Choose {other[0]} or {other[1]}.",
                    elsewhere=[])
    me = tbl.set_index("team").loc[team]
    limited = bool(np.isfinite(me.nrr))
    tm = A.team_matches(career, ids, team)
    if venue != "all":
        tm = tm[tm.venue == venue]
    sk = A.streaks(list(tm.outcome))
    cur = sk["current"]
    kpis = [("Played", f"{int(me.played)}"), ("Won–Lost", f"{int(me.won)}–{int(me.lost)}"), ("Win %", f"{me.win_pct:.0f}%")]
    kpis += [("Net run rate", f"{me.nrr:+.2f}")] if limited else [("Drawn", f"{int(me.drawn)}")]
    kpis += [("Current run", f"{cur[1]} {WORD.get(cur[0], '')}" if cur[0] else "–")]
    out = dict(none="", kpis=[dict(k=k, v=v) for k, v in kpis], last5=list(sk["last5"]),
               runs=f"Longest winning run: {sk['longest_win']} · longest losing run: {sk['longest_loss']}",
               venue_note="", ratings="", limited=limited)
    if venue != "all":
        out["venue_note"] = (f"{label} games only: everything about {team} on this page counts their {len(tids)} "
                             f"{label.lower()} game{'s' if len(tids) != 1 else ''} here: results, players, how they win, "
                             "opponents, series. The tables of every team (ratings, how teams play, discipline) and the "
                             "'every team' columns still count every game here.")
    try:
        ur = kept(career, ("unit_ratings", tuple(ids)), lambda: TD.unit_ratings(career, ids))
        if team in set(ur.team):
            u = ur.set_index("team").loc[team]
            out["ratings"] = (f"Batting rating {u.batting:.0f} ({ordinal(u.batting_rank)} of {len(ur)}) · Bowling rating "
                              f"{u.bowling:.0f} ({ordinal(u.bowling_rank)} of {len(ur)}) · 1000 = average, recent games "
                              "count most" + (", every game here. " if venue != "all" else ". ")
                              + ("The weaker half needs the work." if abs(u.batting - u.bowling) >= 50 else "Well balanced."))
    except Exception as e:  # noqa: BLE001 - the ratings are one line; the record still shows
        out["ratings"] = f"Ratings couldn't be worked out ({type(e).__name__}: {e})"
    return SG.clean(out)


# --------------------------------------------------------------------------- the tabs
class _Parts:
    """Each part worked out on its own: one that fails is named in `missing` and the rest still show."""

    def __init__(self):
        self.out: dict = {"missing": {}}

    def __call__(self, name, fn):
        try:
            self.out[name] = SG.clean(fn())
        except Exception as e:  # noqa: BLE001
            self.out[name] = None
            self.out["missing"][name] = f"Couldn't be worked out ({type(e).__name__}: {e})"


def overview(career, section, season, team, venue) -> dict:
    ids, here, tids, scope_t, _ = where(career, section, season, team, venue)
    tbl = kept(career, ("team_table", tuple(ids), venue), lambda: A.team_table(career, ids, venue))
    me = tbl.set_index("team").loc[team]
    limited = bool(np.isfinite(me.nrr))
    tm = A.team_matches(career, ids, team)
    if venue != "all":
        tm = tm[tm.venue == venue]
    teams, _ = CAT.section_teams(career.matches[career.matches.section == section], section, here)
    P = _Parts()

    def keepers():
        k = A.keepers(career, tids, team)
        return [dict(player=p, stumpings=int(n)) for p, n in zip(k.player, k.stumpings)]
    P("keepers", keepers)

    def vs_average():
        avg = tbl.mean(numeric_only=True)
        measures = [("Win %", "win_pct", "high"), ("Runs per wicket (batting)", "rpw_for", "high"),
                    ("Run rate (batting)", "rr_for", "high"), ("Avg score batting first", "first_innings_avg", "high"),
                    ("Runs per wicket conceded", "rpw_against", "low"), ("Economy (bowling)", "rr_against", "low"),
                    ("Wickets taken per match", "wkts_per_match", "high")]
        dec = {"win_pct": 0, "first_innings_avg": 0}
        rows = []
        for label, col, better in measures:
            v, a = me[col], avg[col]
            if not (np.isfinite(v) and np.isfinite(a)) or a == 0:
                continue
            d = (v - a) / abs(a) * 100 * (1 if better == "high" else -1)
            vt, at = fmt(v, dec.get(col, 1)), fmt(a, dec.get(col, 1))
            rows.append(dict(label=label, value=d, text=f"{d:+.0f}% · {vt} v {at}",
                             note=f"{team}: {vt} · average team: {at}" + ("" if better == "high" else " · lower is better"),
                             vt=vt, at=at, better=better))
        parts = []
        good = max(rows, key=lambda r: r["value"]) if rows else None
        bad = min(rows, key=lambda r: r["value"]) if rows else None
        for r in [x for x in (good, bad) if x is not None and (x is good or x["value"] < 0)]:
            word = "better" if r["value"] >= 0 else "worse"
            parts.append(f"{abs(r['value']):.0f}% {word} than the average team on {r['label'].lower()} ({team} {r['vt']}, "
                         f"average team {r['at']}" + ("" if r["better"] == "high" else "; lower is better here") + ")")
        return dict(title=f"{team} against the average team in {section}", right=f"% better or worse than the average of "
                    f"all {len(tbl)} teams", rows=[{k: r[k] for k in ("label", "value", "text", "note")} for r in rows],
                    shows=f"{team} are " + ", and ".join(parts) + "." if parts else "Not enough games yet.",
                    for_=f"Shows at a glance where {team} are strong and weak against the other {len(tbl) - 1} teams. Each "
                         "bar is how much better (+, blue) or worse (−, red) they are than the average team; for runs "
                         "conceded and economy lower is better, so conceding less shows blue.")
    P("vs_average", vs_average)

    bat_t, bowl_t, _, _ = kept(career, ("player_tables_by_team", repr(scope_t)),
                               lambda: player_tables(career, scope_t, by_team=True))

    def top_bat():
        mb = bat_t[bat_t.team == team].sort_values("runs", ascending=False).head(6)
        mb = mb[mb.runs > 0]
        out = dict(rows=[dict(player=r.player, team=team, runs=int(r.runs), note=f"average {fmt(r.average, 1)} · strike rate "
                              f"{fmt(r.strike_rate, 1)}") for r in mb.itertuples()], shows="", for_="")
        if len(mb):
            team_runs = bat_t[bat_t.team == team].runs.sum()
            out["shows"] = (f"{mb.player.iloc[0]} has {mb.runs.iloc[0]} runs, {mb.runs.iloc[0] / team_runs * 100:.0f}% of "
                            f"{poss(team)} {team_runs} runs; the top {len(mb)} together make "
                            f"{mb.runs.sum() / team_runs * 100:.0f}%.")
            out["for_"] = "Who carries the batting, and how much the team leans on its top run-scorers."
        return out
    P("top_bat", top_bat)

    def top_bowl():
        mw = bowl_t[(bowl_t.team == team) & (bowl_t.wickets > 0)].sort_values(["wickets", "average"],
                                                                              ascending=[False, True]).head(6)
        out = dict(rows=[dict(player=r.player, team=team, wickets=int(r.wickets), note=f"average {fmt(r.average, 1)} · "
                              f"economy {fmt(r.economy, 2)}") for r in mw.itertuples()], shows="", for_="")
        if len(mw):
            team_w = bowl_t[bowl_t.team == team].wickets.sum()
            out["shows"] = (f"{mw.player.iloc[0]} has {int(mw.wickets.iloc[0])} wickets, "
                            f"{mw.wickets.iloc[0] / team_w * 100:.0f}% of {poss(team)} {int(team_w)}; the top {len(mw)} "
                            f"take {mw.wickets.sum() / team_w * 100:.0f}%.")
            out["for_"] = "Who takes the wickets, and whether the attack is spread or rests on one or two bowlers."
        return out
    P("top_bowl", top_bowl)

    def depth():
        dep = A.batting_depth(career, tm.match_id, team)
        if not dep.runs.sum():
            return None
        all_dep = kept(career, ("all_depth", tuple(ids), tuple(teams)),
                       lambda: pd.concat([A.batting_depth(career, ids, t).assign(team=t) for t in teams]))
        ref = all_dep.groupby("group", sort=False).share.mean()
        out = dict(rows=[dict(label=g, value=s, note=f"{r} runs · average team {ref.get(g, 0):.0f}%", runs=int(r),
                              ref=float(ref.get(g, 0))) for g, s, r in zip(dep.group, dep.share, dep.runs)], shows="", for_="")
        if len(dep) and dep.runs.sum():
            top_g = dep.sort_values("share", ascending=False).iloc[0]
            out["shows"] = (f"{top_g.share:.0f}% of {poss(team)} runs come from the {top_g.group.lower()} (the average "
                            f"team: {ref.get(top_g.group, 0):.0f}%). The tail (8-11) makes {dep.share.iloc[-1]:.0f}%.")
            out["for_"] = ("Shows how deep the batting goes: if the top order makes most of the runs, early wickets hurt "
                           "this team more than most.")
        return out
    P("depth", depth)

    def stands():
        pw = A.partnership_by_wicket(career, tm.match_id, team)
        pw = pw[pw.average.notna()]
        best_txt = [f"{int(b)}{'*' if u else ''}" for b, u in zip(pw.best, pw.best_unbroken)]
        out = dict(rows=[dict(label=f"{ordinal(int(w))} wicket", value=a, note=f"{int(n)} stands · best {b}")
                         for w, a, n, b in zip(pw.wicket, pw.average, pw.stands, best_txt)], shows="", for_="")
        if len(pw):
            i_ = pw.average.idxmax()
            b_ = pw.loc[i_]
            out["shows"] = (f"Their best stand is for the {ordinal(int(b_.wicket))} wicket: {b_.average:.1f} runs on "
                            f"average over {int(b_.stands)} stands (best {best_txt[list(pw.index).index(i_)]})."
                            + (f" The opening stand averages {pw.average.iloc[0]:.1f}." if int(pw.wicket.iloc[0]) == 1 else ""))
            out["for_"] = ("Shows which partnerships hold the innings together and where it tends to fall apart. An "
                           "unbroken stand (*) counts its runs; the average is over the stands that were broken, as a "
                           "batting average is over the times out.")
        return out
    P("stands", stands)

    def openers():
        op = A.opening_partnerships(career, tm.match_id, team)
        if op.empty:
            return None
        g = op.groupby("pair").agg(stands=("runs", "size"), runs=("runs", "sum"), average=("runs", "mean"),
                                   best=("runs", "max")).sort_values("runs", ascending=False).reset_index()
        return table(["Openers", "Innings", "Runs", "Average", "Best"],
                     [[r.pair, int(r.stands), int(r.runs), f"{r.average:.1f}", int(r.best)] for r in g.itertuples()],
                     num={1, 2, 3, 4})
    P("openers", openers)

    def collapses():
        col = A.collapses(career, tm.match_id, team)
        if col.empty:
            return None
        return table(["Date", "Against", "Slide", "Lost", "Total"],
                     [[f"{d:%d %b %y}", a if h == team else h, f"{f} → {t}", f"{w} for {r}", tot]
                      for d, h, a, f, t, w, r, tot in zip(col.date, col.home, col.away, col.from_score, col.to_score,
                                                          col.wickets, col.runs, col.total)],
                     links=list(col.match_id) if "match_id" in col.columns else None)
    P("collapses", collapses)

    def big_stands():
        """The team's biggest partnerships here, next to the collapses."""
        bs = PS.big_stands(career, tm.match_id, team)
        if bs.empty:
            return None
        def pair(a, b):
            return f"{a} & {b}" if a and b else "– (the scorecard can't tell who)"
        return table(["Date", "Against", "Wicket", "Stand", "Batters"],
                     [[f"{d:%d %b %y}", o, ordinal(int(w)), f"{int(r)}{'*' if u else ''}", pair(a, b)]
                      for d, o, w, r, u, a, b in zip(bs.date, bs.opposition, bs.wicket, bs.runs, bs.unbroken, bs.batter1, bs.batter2)],
                     num={3}, links=list(bs.match_id))
    P("big_stands", big_stands)

    rs = SG.in_played_order(career, SG.results(career, team, tm.match_id))
    scope_words = f"{section}" + ("" if season in ("", "All seasons") else f" in {season}")

    def strength():
        """Against stronger and weaker sides: every match placed by both sides' rating (Elo) just before it."""
        rows = SG.strength(career, team, rs)
        if not rows:
            return None
        up = [r for r in rows if r["gap"] > 0]
        down = [r for r in rows if r["gap"] < 0]
        def rec(x, word):
            return (f"against sides rated {word} them they won {sum(r['outcome'] == 'W' for r in x)} of {len(x)}" if x else
                    f"they haven't played a side rated {word} them")
        return dict(rows=rows, lanes=[section],
                    shows=f"In {scope_words}, {rec(up, 'above')}; {rec(down, 'below')}. Each dot is a match, placed by how "
                          f"much stronger (right) or weaker (left) the other side was rated just before it.",
                    for_="Whether they beat the strong sides or only the weak ones, and their best win and worst defeat by "
                         "the ratings.")
    P("strength", strength)

    def venues_():
        """Home, away and neutral, then country by country (or ground by ground)."""
        if not rs:
            return None
        v = SG.venues(rs, team)
        unit = "country" if v["nation"] else "ground"
        v.update(shows=f"{poss(team)} record at home, away and on neutral grounds in {scope_words}, then {unit} by {unit}: "
                       f"each bar every match there in order, green won, red lost.",
                 for_="How much they rely on home, and where they travel well or badly.")
        return v
    P("venues", venues_)

    def streaks():
        """Every match in order, the longest runs marked, and the run they're on."""
        if not rs:
            return None
        return dict(results=rs, streaks=SG.runs_of([r["outcome"] for r in rs]),
                    shows=f"Every {team} match in {scope_words} in the order played, with the longest winning and losing "
                          f"runs marked, and the run they're on now.",
                    for_="Form at a glance: whether they're on a run, and how long their best and worst runs lasted.")
    P("streaks", streaks)

    def carry():
        sh = AIM.team_shares(career, tm.match_id, team)
        tr, tw = sh.attrs["team_runs"], sh.attrs["team_wickets"]
        if sh.empty or not (tr or tw):
            return None
        sh = sh.assign(load=sh.run_share + sh.wicket_share)
        top = sh[(sh.run_share >= 5) | (sh.wicket_share >= 5)].sort_values(["load", "player"], ascending=[False, True]).head(12)
        if top.empty:
            top = sh.sort_values(["load", "player"], ascending=[False, True]).head(5)
        g = table(["Player", "Matches", "Runs", "Share of the runs", "Wickets", "Share of the wickets"],
                  [[p, int(n), int(r), pct(rs, 1), int(w), pct(ws, 1)]
                   for p, n, r, rs, w, ws in zip(top.player, top.matches, top.runs, top.run_share, top.wickets, top.wicket_share)],
                  num={1, 2, 3, 4, 5})
        bat, bowl = sh.sort_values("runs", ascending=False), sh.sort_values("wickets", ascending=False)
        bits = []
        if tr and len(bat) and bat.runs.iloc[0] > 0:
            three = bat.run_share.head(3).sum()
            bits.append(f"{bat.player.iloc[0]} makes {bat.run_share.iloc[0]:.0f}% of {poss(team)} runs, and the top three "
                        f"batters {three:.0f}% between them.")
        if tw and len(bowl) and bowl.wickets.iloc[0] > 0:
            bits.append(f"{bowl.player.iloc[0]} takes {bowl.wicket_share.iloc[0]:.0f}% of the wickets.")
        both = sh[(sh.run_share >= 10) & (sh.wicket_share >= 10)]
        if len(both):
            bits.append(f"{' and '.join(both.player.head(2))} {'does' if len(both) == 1 else 'do'} both: at least 10% of "
                        "the runs and of the wickets.")
        g.update(shows=" ".join(bits), for_=(f"Shows who {team} lean on. The team's runs are the runs its batters made off "
                                             f"the bat ({tr} here: extras are no one's) and its wickets are those its bowlers "
                                             f"took ({tw}), so a player's share is the same as on their own page. Players "
                                             "with 5% of either are listed, the biggest load first."))
        return g
    P("carry", carry)

    def contribution():
        """Every player of the team here: their share of its runs off the bat and of its wickets (sorted on the page)."""
        sh = AIM.team_shares(career, tm.match_id, team)
        tr, tw = sh.attrs["team_runs"], sh.attrs["team_wickets"]
        if sh.empty or not (tr or tw):
            return None
        # the shares to one place here, once (as "Who carries the team" writes them), so the page never rounds twice
        rows = [dict(player=p, matches=int(n), runs=int(r), run_share=round(float(rs), 1), wickets=int(w),
                     wicket_share=round(float(ws), 1))
                for p, n, r, rs, w, ws in zip(sh.player, sh.matches, sh.runs, sh.run_share, sh.wickets, sh.wicket_share)]
        top = sh.head(5)
        return dict(rows=rows, team_runs=int(tr), team_wickets=int(tw),
                    shows=f"All {len(sh)} players {team} used in {scope_words}: {tr} runs off the bat and {tw} wickets "
                          f"between them. The top five run-scorers make {top.run_share.sum():.0f}% of the runs.",
                    for_="Everyone's part, not only the main players: who chips in, and how much rests on a few. Click a "
                         "column to sort by it.")
    P("contribution", contribution)

    def usual():
        u = AIM.usual_by_wicket(career, tm.match_id, team)
        if u.empty:
            return None
        rows, gaps = [], []
        for r in u.itertuples():
            gap = float(r.usual - r.opp_usual) if pd.notna(r.opp_usual) else np.nan
            gaps.append(gap)
            rows.append([f"{ordinal(int(r.wicket))} wicket", int(r.usual), int(r.opp_usual) if pd.notna(r.opp_usual) else "–", signed(gap, 0),
                         int(r.best), int(r.worst), int(r.innings)])
        g = table(["Wicket", f"{team} usually", "Their opponents", "Difference", "Highest", "Lowest", "Innings"], rows,
                  num={1, 2, 3, 4, 5, 6})
        known = [(i, x) for i, x in enumerate(gaps) if np.isfinite(x)]
        bits = [f"{poss(team)} {ordinal(int(u.wicket.iloc[0]))} wicket usually falls at {int(u.usual.iloc[0])}"
                + (f" (their opponents': {int(u.opp_usual.iloc[0])})." if pd.notna(u.opp_usual.iloc[0]) else ".")]
        if known:
            i_lo = min(known, key=lambda k: k[1])[0]
            i_hi = max(known, key=lambda k: k[1])[0]
            if gaps[i_hi] > 0:
                bits.append(f"They're furthest ahead at the {ordinal(int(u.wicket.iloc[i_hi]))} wicket ({signed(gaps[i_hi], 0)}).")
            if gaps[i_lo] < 0:
                bits.append(f"They're furthest behind at the {ordinal(int(u.wicket.iloc[i_lo]))} wicket ({signed(gaps[i_lo], 0)}).")
        rising = []      # the line stops where the usual score would dip (each wicket's middle score is of other innings)
        for r in u.itertuples():
            if rising and int(r.usual) <= rising[-1][1]:
                break
            rising.append((int(r.wicket), int(r.usual)))
        g["line"] = (f"In {scope_words} {team} are usually "
                     + ", ".join(f"{v}/{w}" for w, v in rising) + ("…" if rising[-1][0] < 10 else "")
                     + (" (their opponents " + ", ".join(f"{int(r.opp_usual)}/{int(r.wicket)}" for r in u.itertuples()
                                                         if pd.notna(r.opp_usual) and int(r.wicket) <= rising[-1][0]) + ")"
                        if u.opp_usual.notna().any() else ""))
        g.update(shows=" ".join(bits), for_=("Shows where the innings usually stands as each wicket falls, against the "
                                             "teams they played in the same games: the typical (middle) score, so one "
                                             "huge stand doesn't pull it about. Only wickets that fell in at least 30% of "
                                             "their innings are listed."))
        return g
    P("usual", usual)

    style = kept(career, ("team_style", tuple(ids)), lambda: E.team_style(career, ids))

    def how_they_play():
        if team not in set(style.team):
            return None
        s_me = style.set_index("team").loc[team]
        s_avg = style.mean(numeric_only=True)
        rows = []
        for label, col, _ in E.STYLE:
            v, a = s_me[col], s_avg[col]
            if not (np.isfinite(v) and np.isfinite(a)) or a == 0:
                continue
            d = (v - a) / abs(a) * 100
            rows.append(dict(label=label, value=d, text=f"{d:+.0f}% · {fmt(v, 1)} v {fmt(a, 1)}"))
        i_max = int(np.argmax([abs(r["value"]) for r in rows])) if rows else 0
        return dict(rows=rows, every=venue != "all",
                    shows=(f"{poss(team)} biggest difference is {rows[i_max]['label'].lower()}: {rows[i_max]['value']:+.0f}% "
                           "against the average team.") if rows else "Not enough games yet.",
                    for_="Shows how they play, not how well: a team can win either way. Each bar compares this team's "
                         "figure with the average of all teams in the section.")
    P("how_they_play", how_they_play)

    def discipline():
        if team not in set(style.team):
            return None
        disc = kept(career, ("discipline", tuple(ids)), lambda: E.discipline(career, ids))
        d = disc.head(12)
        out = dict(every=venue != "all", rows=[dict(player=t, team=t, extras=x, note=f"wides {fmt(w, 1)} · no-balls "
                                                    f"{fmt(n, 1)} · byes {fmt(b, 1)} · leg byes {fmt(lb, 1)} per match")
                                               for t, x, w, n, b, lb in zip(d.team, d.extras_per_match, d.wides_per_match,
                                                                            d.no_balls_per_match, d.byes_per_match,
                                                                            d.leg_byes_per_match)],
                   shows="", for_="Free runs given away. A few extras a match can be the difference in a close game.")
        if team in set(disc.team):
            r = disc.set_index("team").loc[team]
            avg_x = disc.extras_per_match.mean()
            out["shows"] = (f"{team} give away {fmt(r.extras_per_match, 1)} extras a match ({fmt(r.wides_per_match, 1)} "
                            f"wides, {fmt(r.no_balls_per_match, 1)} no-balls), "
                            f"{(r.extras_per_match - avg_x) / avg_x * 100:+.0f}% against the average of {fmt(avg_x, 1)}: "
                            f"{int(list(disc.team).index(team)) + 1} of {len(disc)} for discipline.")
        return out
    P("discipline", discipline)

    def every_team():
        show = tbl.sort_values(["win_pct", "nrr" if limited else "rpw_for"], ascending=False)
        cols = {"team": "Team", "played": "P", "won": "W", "lost": "L", "drawn": "D", "tied": "T", "win_pct": "Win %",
                "rpw_for": "Runs/wkt", "rpw_against": "Conceded/wkt", "rr_for": "Run rate", "rr_against": "Economy"}
        if limited:
            cols["nrr"] = "NRR"
        two = {"rpw_for", "rpw_against", "rr_for", "rr_against", "nrr"}
        rows = [[r[c] if c == "team" else fmt(r[c], 2) if c in two else fmt(r[c], 0) for c in cols]
                for _, r in show.iterrows()]
        out = table(list(cols.values()), rows, num=set(range(1, len(cols))), hi=[t == team for t in show.team])
        out["title"] = f"Every team in {section}" + ("" if venue == "all" else f" · {venue.replace('all', 'overall')} "
                                                                                  "games only")
        return out
    P("every_team", every_team)
    return P.out


def _games(career, ids):
    return kept(career, ("tp_games", tuple(ids)), lambda: TP.games(career, ids))


def how_they_win(career, section, season, team, venue) -> dict:
    ids, here, tids, _, base_kind = where(career, section, season, team, venue)
    games_all = _games(career, ids)
    multi = TP.is_multi(games_all)
    second = "Batting second" if multi else "Chasing"
    P = _Parts()

    def bat_first():
        _, avg_bf = kept(career, ("bat_first", tuple(ids)), lambda: TP.bat_first_table(career, ids))
        bft = kept(career, ("bat_first", tuple(tids)), lambda: TP.bat_first_table(career, tids))[0]
        if team not in set(bft.team):
            return dict(title=f"Batting first or {second.lower()}", none="No games yet.")
        r = bft.set_index("team").loc[team]
        a1, a2 = avg_bf["first"], avg_bf["second"]
        rows = [["Batting first", f"{int(r.bf_played)}",
                 TP.wdl(dict(won=int(r.bf_won), lost=int(r.bf_lost), drawn=int(r.bf_drawn), tied=int(r.bf_tied),
                             no_result=int(r.bf_no_result))), pct(r.bf_win_pct), pct(a1["win_pct"])],
                [second, f"{int(r.ch_played)}",
                 TP.wdl(dict(won=int(r.ch_won), lost=int(r.ch_lost), drawn=int(r.ch_drawn), tied=int(r.ch_tied),
                             no_result=int(r.ch_no_result))), pct(r.ch_win_pct), pct(a2["win_pct"])]]
        better = "batting first" if (r.bf_win_pct or 0) >= (r.ch_win_pct or 0) else second.lower()
        out = table(["", "Played", "W–D–L" if multi else "W–L", f"{team} win %", "Every team"], rows, num={1, 3, 4})
        out.update(title=f"Batting first or {second.lower()}", right=f"{team} against every team in {section}",
                   note=f"{team} win more often {better}. 'Every team' is how often the side batting first (or second) "
                        f"wins in {section}." + (" Win % here counts draws as games not won." if multi else
                                                 " Ties and no-results are left out of win %."))
        return out
    P("bat_first", bat_first)

    def close():
        cg = kept(career, ("close", tuple(tids), team), lambda: TP.close_games(career, tids, team))
        out = table(["", "Record", "Win %"], [["Close games", TP.wdl(cg["close"]), pct(cg["close"]["win_pct"])],
                                              ["Other games", TP.wdl(cg["other"]), pct(cg["other"]["win_pct"])]], num={2})
        out["right"] = f"won or lost by under {bars_for(base_kind)['close_runs']} runs or by 1-2 wickets, or tied"
        g = cg["rows"]
        out["games"] = table(["Date", "Opponent", "", "Margin"], [
            [f"{r.date:%d %b %Y}", r.opponent, {"W": "Won", "L": "Lost", "T": "Tied"}.get(r.outcome, r.outcome),
             (_n(int(r.margin_runs), "run") if pd.notna(r.margin_runs) else
              _n(int(r.margin_wickets), "wkt") if pd.notna(r.margin_wickets) else "tie")]
            for r in g.sort_values("date", ascending=False).head(8).itertuples()],
            links=list(g.sort_values("date", ascending=False).head(8).match_id)) if len(g) else None
        return out
    P("close", close)

    def start():
        ss = kept(career, ("start", tuple(tids), team), lambda: TP.start_split(career, tids, team))
        sa = kept(career, ("start", tuple(ids), ""), lambda: TP.start_split(career, ids, ""))
        gb, bb_ = ss["good_bar"], ss["bad_bar"]
        rows = [[label, TP.wdl(ss[k]), pct(ss[k]["win_pct"]), pct(sa[k]["win_pct"])]
                for k, label in (("good", f"at {gb} or more"), ("middle", f"between {bb_} and {gb - 1}"),
                                 ("bad", f"under {bb_}"))]
        out = table(["First wicket fell", "Record", f"{team} win %", "Every team"], rows, num={2, 3})
        out["note"] = "Their first innings of each game. A good start is worth this much to them."
        return out
    P("start", start)

    def targets():
        tb = kept(career, ("targets", tuple(tids), team), lambda: TP.target_buckets(career, tids, team))
        ta = kept(career, ("targets", tuple(ids), ""), lambda: TP.target_buckets(career, ids, ""))
        label = "fourth-innings target" if multi else "first-innings total"
        if tb.empty:
            return dict(title=f"Chasing and defending by the size of the {label}", none="No games yet.")
        rows = []
        for r, a_ in zip(tb.itertuples(), ta.itertuples()):
            if not (r.chase_played or r.defend_played):
                continue
            rows.append([r.bucket, f"{r.chase_won}/{r.chase_played}" if r.chase_played else "–",
                         pct(r.chase_pct) if r.chase_played else "–", pct(a_.chase_pct),
                         f"{r.defend_won}/{r.defend_played}" if r.defend_played else "–",
                         pct(r.defend_pct) if r.defend_played else "–", pct(a_.defend_pct)])
        out = table(["Target" if multi else "Total", "Chased (won/played)", "Win %", "Every team", "Defended (won/played)",
                     "Win %", "Every team"], rows, num={2, 3, 5, 6})
        out.update(title=f"Chasing and defending by the size of the {label}",
                   note=f"Chasing: batting last. Defending: setting the target. 'Every team' is the same for all sides in "
                        f"{section}.")
        return out
    P("targets", targets)

    def dominance():
        dm = kept(career, ("dominance", tuple(ids)), lambda: TD.dominance(career, ids))
        dm_t = dm if venue == "all" else kept(career, ("dominance", tuple(tids)), lambda: TD.dominance(career, tids))
        if team not in set(dm_t.team):
            return None
        r_ = dm_t.set_index("team").loc[team]
        b_ = bars_for(base_kind)
        out = table(["", "Thrashing", "Comfortable", "Scrape"],
                    [["Wins", int(r_.won_thrashing), int(r_.won_comfortable), int(r_.won_scrape)],
                     ["Defeats", int(r_.lost_thrashing), int(r_.lost_comfortable), int(r_.lost_scrape)]], num={1, 2, 3})
        rank_ = int(list(dm.team).index(team)) + 1 if team in set(dm.team) else None
        label = {"home": "home", "away": "away"}.get(venue, "")
        out["note"] = (f"Thrashing: {b_['thrash_runs']}+ runs or {b_['thrash_wkts']}+ wickets"
                       + (" (or an innings)" if base_kind == "multi" else "") + f". Scrape: under {b_['close_runs']} runs "
                       f"or 1-2 wickets. Dominance index {r_['index']:+.0f} (thrashings won minus heavy defeats, per 100 "
                       + (f"games): {rank_} of {len(dm)} here." if venue == "all" or rank_ is None else f"{label} games).")
                       + (f" Draws: {int(r_.drawn)}." if r_.drawn else ""))
        return out
    P("dominance", dominance)

    def comebacks():
        cb_all = kept(career, ("comebacks", tuple(tids)), lambda: WP.comebacks(career, tids))
        cb = cb_all[cb_all.winner == team]
        against = cb_all[cb_all.loser == team]
        out = table(["Match", "Against", "Lowest chance", "When", "Result"],
                    [[f"{r.date:%d %b %Y}", r.loser, f"{r.low:.0f}%", r.at, r.result] for r in cb.itertuples()],
                    num={2}, links=list(cb.match_id))
        out["right"] = f"{team} wins from a losing position (their chance fell under 25%)"
        out["note"] = (f"{len(cb)} comeback win{'s' if len(cb) != 1 else ''} for {team}, and {len(against)} game"
                       f"{'s' if len(against) != 1 else ''} they lost from a winning position. The chance is from the "
                       "Matches page's win-chance line: games in the same spot (innings, wickets down, lead).")
        return out
    P("comebacks", comebacks)
    return P.out


def opponents(career, section, season, team, venue) -> dict:
    ids, here, tids, _, _ = where(career, section, season, team, venue)
    P = _Parts()

    def stages():
        sr = kept(career, ("stage_record", tuple(tids), team), lambda: TP.stage_record(career, tids, team))
        return table(["", "Played", "Record", "Win %"],
                     [[r.stage, int(r.played), TP.wdl(r._asdict()), pct(r.win_pct)] for r in sr.itertuples() if r.played],
                     num={1, 3})
    P("stages", stages)

    def bounce():
        ar = kept(career, ("after_result", tuple(ids), team, venue), lambda: TP.after_result(career, ids, team, venue=venue))
        rows = [[r.after, int(r.played), TP.wdl(r._asdict()), pct(r.win_pct)] for r in ar.itertuples()]
        return table(["", "Games", "Record", "Win %"], rows, num={1, 3}) if rows else None
    P("bounce", bounce)

    def every_opponent():
        op = kept(career, ("opponents", tuple(tids), team), lambda: TP.opponents(career, tids, team))
        return table(["Opponent", "Played", "Record", "Win %", "Last met"],
                     [[("⭐ " if r.favourite else "👻 " if r.bogey else "") + r.opponent, int(r.played), TP.wdl(r._asdict()),
                       pct(r.win_pct), f"{r.last:%d %b %Y}"] for r in op.itertuples()],
                     num={1, 3}, hi=[bool(r.favourite or r.bogey) for r in op.itertuples()])
    P("opponents", every_opponent)

    def fortress():
        fz = kept(career, ("fortress", tuple(ids)), lambda: TD.fortress(career, ids))
        if fz.empty:
            return dict(none="No home games here (neutral venues).")
        out = table(["Team", "Home record", "Home win %", "v average home side"],
                    [[r.team, TP.wdl(r._asdict()), pct(r.win_pct), signed(r.vs) + (" pts" if np.isfinite(r.vs) else "")]
                     for r in fz.itertuples()], num={2, 3}, hi=[r.team == team for r in fz.itertuples()])
        out["note"] = (f"The average home side here wins {pct(fz.attrs['average'])}. A fortress is well above that: "
                       "winning there is worth more.")
        return out
    P("fortress", fortress)

    def revenge():
        rv = kept(career, ("revenge", tuple(ids), team, venue), lambda: TP.revenge(career, ids, team, venue=venue))
        return table(["", "Record", "Win %"], [["Revenge games", TP.wdl(rv["revenge"]), pct(rv["revenge"]["win_pct"])],
                                              ["Every other game", TP.wdl(rv["other"]), pct(rv["other"]["win_pct"])]],
                     num={2})
    P("revenge", revenge)
    return P.out


def season_tab(career, section, season, team, venue, race: str = "") -> dict:
    ids, here, tids, _, _ = where(career, section, season, team, venue)
    m = career.matches
    P = _Parts()

    def league_race():
        evs = here[~here.knockout & (here.home.eq(team) | here.away.eq(team))]
        options = sorted({(e, str(s_)) for e, s_ in zip(evs.event, evs.season)}, key=lambda x: (x[1], x[0]), reverse=True)
        options = [o for o in options if o[0] not in BILATERAL]
        if not options:
            return dict(options=[], picked="", none="No league games here (bilateral series have no league table).",
                        lines=[], shows="", for_="")
        labels = [f"{e} {s}" for e, s in options]
        pick = options[labels.index(race)] if race in labels else options[0]
        race_ids = m[(m.event == pick[0]) & (m.season.astype(str) == pick[1])].match_id
        rc = kept(career, ("position_race", pick), lambda: TP.position_race(career, race_ids))
        out = dict(options=labels, picked=f"{pick[0]} {pick[1]}", none="", lines=[], shows="", for_="")
        grp = rc[rc.team == team].group.iloc[-1] if (rc.team == team).any() else None
        if grp is None:
            out["none"] = "No table for this one."
            return out
        rc = rc[rc.group == grp]
        out["lines"] = [dict(team=t, points=[dict(round=int(r["round"]), position=int(r.position),
                                                  points=r.points if "points" in rc.columns else None,
                                                  played=int(r.played)) for _, r in g.sort_values("round").iterrows()])
                        for t, g in rc.groupby("team", sort=False)]
        mine = rc[rc.team == team].sort_values("round")
        out["shows"] = (f"{team} are {int(mine.position.iloc[-1])} of {rc.team.nunique()} after {int(mine.played.iloc[-1])} "
                        f"games; their best was {int(mine.position.min())} and their lowest {int(mine.position.max())}.")
        out["for_"] = (f"Shows how the season unfolded: when {team} climbed or slipped. Positions follow the league table "
                       "(points, then net run rate). Hover a line for points.")
        return out
    P("race", league_race)

    def halves():
        sh = kept(career, ("season_halves", tuple(tids), team), lambda: TP.season_halves(career, tids, team))
        if sh.empty:
            return None
        rows = [[str(r.season), TP.wdl(r.early), pct(r.early["win_pct"]), TP.wdl(r.late), pct(r.late["win_pct"])]
                for r in sh.itertuples()]
        return table(["Season", "First half", "Win %", "Second half", "Win %"], rows, num={2, 4},
                     hi=[False] * (len(rows) - 1) + [True])
    P("halves", halves)
    return P.out


def series_tab(career, section, season, team, venue) -> dict:
    ids, here, tids, _, _ = where(career, section, season, team, venue)
    multi = TP.is_multi(_games(career, ids))
    has_series = bool((here.series_id.astype(object).fillna("") != "").any())
    P = _Parts()
    P.out.update(has_series=has_series, multi=bool(multi))
    if has_series:
        def first_blood():
            fb = kept(career, ("first_blood", tuple(tids), team), lambda: TP.first_blood(career, tids, team))
            fa = kept(career, ("first_blood", tuple(ids), ""), lambda: TP.first_blood(career, ids, ""))
            if fb.empty:
                return None
            every = fa.set_index("start").win_pct
            return table(["", "Series", "Won–drawn–lost", "Series won", "Every team"],
                         [[r.start, int(r.series), f"{r.won}–{r.drawn}–{r.lost}", pct(r.win_pct),
                           pct(every.get(r.start, np.nan))] for r in fb.itertuples()], num={1, 3, 4})
        P("first_blood", first_blood)

        def deciders():
            si = kept(career, ("situations", tuple(tids), team), lambda: TP.situations(career, tids, team))
            rows = [[r.situation, int(r.played), TP.wdl(r._asdict()), pct(r.win_pct)] for r in si.itertuples() if r.played]
            return table(["", "Games", "Record", "Win %"], rows, num={1, 3}) if rows else None
        P("deciders", deciders)
    if multi:
        def second_innings():
            si2 = kept(career, ("second_innings", tuple(ids)), lambda: TD.second_innings(career, ids))
            return table(["Team", "2nd innings", "Average", "Bowled out under 200", "4th-innings chases", "Won–drawn–lost"],
                         [[r.team, int(r.second_innings), fmt(r.second_avg, 0), int(r.cheap), int(r.chases),
                           f"{r.chase_won}–{r.chase_drawn}–{r.chase_lost}"] for r in si2.itertuples()],
                         num={1, 2, 3, 4}, hi=[r.team == team for r in si2.itertuples()])
        P("second_innings", second_innings)

        def follow_on():
            fo = kept(career, ("follow_on", tuple(tids), team), lambda: TP.follow_on_and_declarations(career, tids, team))
            if fo.empty:
                return None
            return table(["", "Times", "Won–drawn–lost", "Win %"],
                         [[r.situation, int(r.times), f"{r.won}–{r.drawn}–{r.lost}", pct(r.win_pct)] for r in fo.itertuples()],
                         num={1, 3})
        P("follow_on", follow_on)
    return P.out


XI_HOW = {"t20": "Batters on average × strike rate, a finisher (batting 5–7) on runs per innings × strike rate, bowlers on "
                 "wickets (each worth the section's runs per wicket) plus runs kept below the section's economy.",
          "one": "Batters on average × strike rate; bowlers on wickets (each worth the section's runs per wicket) plus "
                 "runs kept below the section's economy.",
          "multi": "Batters on average; bowlers on wickets, worth more the lower their average and strike rate against the "
                   "section's, plus 2 for each five-for."}


def squad_tab(career, section, season, team, venue) -> dict:
    ids, here, tids, _, _ = where(career, section, season, team, venue)
    P = _Parts()

    def best_xi():
        xi = kept(career, ("best_xi", tuple(tids), team), lambda: SN.best_xi(career, tids, team))
        title = (f"{'All-time' if season in ('', 'All seasons') else season} XI · {team} in {section}"
                 + (f" · {venue} games" if venue != "all" else ""))
        if xi.empty:
            return dict(title=title, none="Not enough games yet to pick an XI.")
        out = table(["", "Role", "Player", "Why"], [[i + 1, r.slot, r.player, r.why] for i, r in enumerate(xi.itertuples())],
                    num={0})
        out.update(title=title, note=f"Picked by role: 2 openers, the middle order, a keeper (made a stumping), an all-rounder "
                   f"(bats in the top 8; runs per innings × bowling) and 4 bowlers. {XI_HOW[xi.attrs.get('kind', 't20')]} "
                   f"Needs {xi.attrs.get('need', 2)}+ games here. 'Best available': not enough players in that role, so the "
                   "best of the rest.")
        return out
    P("best_xi", best_xi)

    def changes():
        sc = kept(career, ("squad_changes", tuple(tids), team), lambda: TD.squad_changes(career, tids, team))
        intl = bool(sc.attrs.get("international", False))
        unit = "series" if intl else "season"
        out = dict(right="series to series" if intl else "season to season", steps=[],
                   none=f"Only one {unit} so far: nothing to compare yet." if sc.empty else "",
                   note=f"In: their figures in the new {unit}. Out: their figures in the last one they played.")
        for (a_, b_), g_ in (sc.groupby(["from", "to"], sort=False) if len(sc) else []):
            def rows(g):
                return [[r.player, int(r.games), int(r.runs), int(r.wickets)] for r in g.itertuples()]
            ins, outs = g_[g_.change == "in"], g_[g_.change == "out"]
            out["steps"].append(dict(title=f"{a_} → {b_}",
                                     ins=table(["Player", "Games", "Runs", "Wkts"], rows(ins), num={1, 2, 3}),
                                     outs=table(["Player", "Games", "Runs", "Wkts"], rows(outs), num={1, 2, 3})))
        return out
    P("changes", changes)
    return P.out


def results_tab(career, section, season, team, venue) -> dict:
    ids, here, tids, _, _ = where(career, section, season, team, venue)
    games_all = _games(career, ids)
    second = "Batting second" if TP.is_multi(games_all) else "Chasing"
    P = _Parts()

    def results():
        tm = A.team_matches(career, ids, team)
        if venue != "all":
            tm = tm[tm.venue == venue]
        res = tm.sort_values("date", ascending=False)
        bf = games_all[games_all.team == team].set_index("match_id").batted_first
        stage = bool(res.stage.astype(bool).any())
        cols = ["Date", "Opponent", "Venue"] + (["Stage"] if stage else []) + ["Batted", "Result", ""]
        rows = [[f"{r.date:%d %b %Y}", r.opponent, say(r.venue)] + ([r.stage] if stage else [])
                + ["Batted first" if bf.get(r.match_id, False) else second, r.result, r.outcome] for r in res.itertuples()]
        return table(cols, rows, links=list(res.match_id))
    P("results", results)
    return P.out


TAB_FN = {"Overview": overview, "How they win": how_they_win, "Opponents and stages": opponents, "Series and Tests": series_tab,
          "Squad": squad_tab, "Results": results_tab}


def page(career, section: str, season: str, team: str, venue: str, tab: str, race: str = "") -> dict:
    """The pickers, the top of the page and one tab."""
    tab = tab if tab in TABS else "Overview"
    venue = venue if venue in ("all", "home", "away") else "all"
    season = season or "All seasons"
    top = kept(career, ("team_head", section, season, team, venue), lambda: head(career, section, season, team, venue))
    out = dict(section=section, season=season, team=team, venue=venue, tab=tab, tabs=TABS, head=top, body=None)
    if not top.get("none"):
        if tab == "Season":
            out["body"] = kept(career, ("team_tab", section, season, team, venue, tab, race),
                               lambda: season_tab(career, section, season, team, venue, race))
        else:
            out["body"] = kept(career, ("team_tab", section, season, team, venue, tab),
                               lambda: TAB_FN[tab](career, section, season, team, venue))
    return out
