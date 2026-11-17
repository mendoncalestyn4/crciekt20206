"""Team vs team (stage 2): two teams in one competition (and season), against each other or each against anyone, at
any ground or one side's home, as the current site's Team vs team page shows them: each side's record, the tale of the
tape, their meetings, and player by player. Every number comes from the same engine functions with the same words."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ccstats import analysis as A
from ccstats import catalogue as CAT
from ccstats import teamplay as TP
from ccstats.stats import WICKET_VALUE, Scope, player_tables, poss

from . import styleguide as SG
from .cache import kept
from .teampage import _n, choices, fmt

GROUNDS = ("all", "a_home", "b_home", "neutral")


def _num(v, d=1):
    return fmt(v, d) if v is not None and not (isinstance(v, float) and np.isnan(v)) else "–"


def profile(r) -> list[str]:
    """Everything worth knowing about a player's row, line by line, as the current site's hover box has it."""
    g = r.get if hasattr(r, "get") else (lambda k, default=None: getattr(r, k, default))
    if g("economy") is not None and g("wickets") is not None:
        return [f"{int(g('innings'))} inns · {_n(g('wickets'), 'wicket')} · best {g('best')}",
                f"average {_num(g('average'))} · economy {_num(g('economy'), 2)} · strike rate {_num(g('strike_rate'))}",
                f"{_n(g('hauls'), 'four-for')} · runs saved {'+' if (g('runs_saved') or 0) > 0 else ''}{_num(g('runs_saved'))}"]
    return [f"{int(g('innings'))} inns · {int(g('runs'))} runs · high score {g('high_score_text') or '–'}",
            f"average {_num(g('average'))} · strike rate {_num(g('strike_rate'))}",
            f"{_n(g('hundreds'), 'hundred')} · {_n(g('fifties'), 'fifty', 'fifties')} · {_n(g('fours'), 'four')} · "
            f"{_n(g('sixes'), 'six', 'sixes')}",
            f"runs above average {'+' if (g('runs_above_average') or 0) > 0 else ''}{_num(g('runs_above_average'))}"]


def page(career, section: str, season: str, a: str, b: str, which: str, ground: str, mine: list[str]) -> dict:
    """The pickers' state (with the defaults: team A your team, team B the side it has met most; against each other if
    they have met, else against anyone), and everything below them, or a plain reason there's nothing."""
    m = career.matches
    ch = choices(career)
    secs = {c["section"]: c for c in ch}
    if section not in secs:
        section = ch[0]["section"]
    season = season if season in secs[section]["seasons"] else "All seasons"
    base_scope = Scope(sections=[section], seasons=[] if season == "All seasons" else [season])
    here = m[m.match_id.isin(base_scope.match_ids(m))]
    teams, todo = CAT.section_teams(m[m.section == section], section, here)
    out = dict(section=section, season=season, teams=list(teams), todo=sorted(todo), a=a, b=b, which=which, ground=ground,
               grounds=[], info="", none="")
    if len(teams) < 2:
        out["none"] = "This section needs at least two teams."
        return SG.clean(out)
    if a not in teams:
        mine_here = [t for t in mine if t in teams]
        a = mine_here[0] if mine_here else teams[0]
    others = [t for t in teams if t != a]
    if b not in others:
        met = pd.concat([here.away[here.home == a], here.home[here.away == a]]).value_counts()
        b = met.index[0] if len(met) else next((t for t in others if t not in todo), others[0])
    meet_all = here[((here.home == a) & (here.away == b)) | ((here.home == b) & (here.away == a))]
    n_met = len(meet_all)
    if which not in ("each", "any"):
        which = "each" if n_met else "any"
    h2h = which == "each"
    grounds = ["all", "a_home", "b_home"] + (["neutral"] if here.neutral.any() else [])
    if ground not in grounds:
        ground = "all"
    if h2h:
        n_at = {"all": n_met, "a_home": int(((meet_all.home == a) & ~meet_all.neutral).sum()),
                "b_home": int(((meet_all.home == b) & ~meet_all.neutral).sum()), "neutral": int(meet_all.neutral.sum())}
        words = {"all": f"All venues ({n_at['all']})", "a_home": f"At {poss(a)} home ({n_at['a_home']})",
                 "b_home": f"At {poss(b)} home ({n_at['b_home']})", "neutral": f"Neutral ({n_at['neutral']})"}
    else:
        words = {"all": "All venues", "a_home": f"{a} home · {b} away", "b_home": f"{a} away · {b} home",
                 "neutral": "Both at neutral grounds"}
    out.update(a=a, b=b, others=others, which=which, ground=ground, grounds=[dict(key=g, label=words[g]) for g in grounds],
               where_help=("Their meetings, and how many there were at each ground." if h2h else
                           f"{a} home · {b} away: {poss(a)} home games against anyone, next to {poss(b)} away games against "
                           f"anyone, as they would be for a game at {poss(a)} ground."))
    venue_a, venue_b = {"all": ("all", "all"), "a_home": ("home", "away"), "b_home": ("away", "home"),
                        "neutral": ("neutral", "neutral")}[ground]
    where_scope = section + ("" if season == "All seasons" else f" in {season}")

    def scope_for(team, other):
        return Scope(sections=[section], seasons=base_scope.seasons, team=team, venue=venue_a if team == a else venue_b,
                     opponent=other if h2h else "")
    ids_a, ids_b = scope_for(a, b).match_ids(m), scope_for(b, a).match_ids(m)
    if ground != "all" and here.neutral.all():
        out["none"] = f"{section} matches are played at neutral venues, so there are no home or away games. Choose All venues."
        return SG.clean(out)
    if len(ids_a) == 0 or len(ids_b) == 0:
        at_v = {"home": " at home", "away": " away", "neutral": " at a neutral ground", "all": ""}
        if h2h:
            at_ = {"all": "", "a_home": f" at {poss(a)} home", "b_home": f" at {poss(b)} home", "neutral": " at a neutral ground"}
            out["none"] = (f"{a} and {b} haven't played each other in {where_scope}{at_[ground]} yet. "
                           + ("Choose another Where (the number is how many times they've met there), or " if n_met else
                              "Choose ") + "Against anyone to compare each team's own games.")
        else:
            missing = [(t, v) for t, ids_, v in ((a, ids_a, venue_a), (b, ids_b, venue_b)) if len(ids_) == 0]
            never = [t for t, _ in missing if t in todo]
            out["none"] = (". ".join(f"{t} haven't played{'' if t in never else at_v[v]} in {where_scope} yet"
                                     for t, v in missing)
                           + (". Their side fills in after their first game here" if never else "")
                           + (". Choose another Where." if len(never) < len(missing) else "."))
        return SG.clean(out)
    if not h2h:
        side = {"all": ("all {t} games", "all {t} games"), "a_home": ("{t} home games", "{t} away games"),
                "b_home": ("{t} away games", "{t} home games"),
                "neutral": ("{t} games at neutral grounds", "{t} games at neutral grounds")}[ground]
        out["info"] = (f"Each team's own record against anyone: {side[0].format(t=poss(a))} ({len(ids_a)}) next to "
                       f"{side[1].format(t=poss(b))} ({len(ids_b)}), in {where_scope}. "
                       + (f"They have played each other {'once' if n_met == 1 else f'{n_met} times'} here: choose Against "
                          "each other for just " + ("that game." if n_met == 1 else "those.") if n_met else
                          f"{a} and {b} haven't played each other here yet."))
    key = (section, season, a, b, which, ground)
    out["body"] = kept(career, ("tvt", key), lambda: _body(career, here, base_scope, scope_for, a, b, ids_a, ids_b, venue_a,
                                                            venue_b, h2h, ground, where_scope))
    return SG.clean(out)


def _body(career, here, base_scope, scope_for, a, b, ids_a, ids_b, venue_a, venue_b, h2h, ground, where_scope) -> dict:
    out: dict = {"missing": {}}

    def part(name, fn):
        try:
            out[name] = SG.clean(fn())
        except Exception as e:  # noqa: BLE001 - one part that can't be worked out never stops the others
            out[name] = None
            out["missing"][name] = f"Couldn't be worked out ({type(e).__name__}: {e})"

    rec_a = A.team_table(career, ids_a).set_index("team").loc[a].copy()
    rec_b = A.team_table(career, ids_b).set_index("team").loc[b].copy()
    limited = bool(np.isfinite(rec_a.nrr) and np.isfinite(rec_b.nrr))
    for rec, team, ids_ in ((rec_a, a, ids_a), (rec_b, b, ids_b)):
        bft_, _ = kept(career, ("bat_first", tuple(ids_)), lambda ids_=ids_: TP.bat_first_table(career, ids_))
        row_ = bft_.set_index("team").loc[team] if team in set(bft_.team) else None
        rec["bf_pct"] = row_.bf_win_pct if row_ is not None else np.nan
        rec["ch_pct"] = row_.ch_win_pct if row_ is not None else np.nan

    def high_total(team, ids):
        i = career.innings[career.innings.match_id.isin(ids) & (career.innings.team == team)]
        return int(i.runs.max()) if len(i) else 0

    def games_of(team, venue, opp) -> str:
        at = {"home": "at home", "away": "away", "neutral": "at neutral grounds", "all": ""}[venue]
        if h2h:
            return f"v {opp}" + (f", {at}" if at else "")
        return {"home": "home games v anyone", "away": "away games v anyone", "neutral": "neutral-ground games v anyone",
                "all": "all games v anyone"}[venue]

    def tile(team, r, other):
        figs = [dict(k="Played", v=f"{int(r.played)}", up=False),
                dict(k="Won–Lost", v=f"{int(r.won)}–{int(r.lost)}", up=bool(r.won > other.won)),
                dict(k="Win %", v=f"{r.win_pct:.0f}", up=bool(r.win_pct > other.win_pct))]
        figs.append(dict(k="Net run rate", v=f"{r.nrr:+.2f}", up=bool(r.nrr > other.nrr)) if limited else
                    dict(k="Drawn", v=f"{int(r.drawn)}", up=False))
        figs.append(dict(k="Highest", v=f"{high_total(team, ids_a if team == a else ids_b)}", up=False))
        return dict(team=team, sub=games_of(team, venue_a if team == a else venue_b, b if team == a else a), figures=figs)
    part("tiles", lambda: [tile(a, rec_a, rec_b), tile(b, rec_b, rec_a)])

    def tape():
        rows = [("Win %", "win_pct", "high", 0), ("Runs per wicket (batting)", "rpw_for", "high", 1),
                ("Run rate (batting)", "rr_for", "high", 2), ("Avg score batting first", "first_innings_avg", "high", 0),
                ("Runs per wicket conceded", "rpw_against", "low", 1), ("Economy (bowling)", "rr_against", "low", 2),
                ("Wickets taken per match", "wkts_per_match", "high", 1), ("Win % batting first", "bf_pct", "high", 0),
                ("Win % chasing" if limited else "Win % batting second", "ch_pct", "high", 0)]
        got, a_wins, b_wins = [], 0, 0
        for label, col, better, d in rows:
            va, vb = rec_a[col], rec_b[col]
            if not (np.isfinite(va) and np.isfinite(vb)):
                continue
            top = max(abs(va), abs(vb)) or 1
            a_better = bool(va != vb and ((better == "high") == (va > vb)))
            b_better = bool(va != vb and not a_better)
            a_wins += a_better
            b_wins += b_better
            got.append(dict(label=label, a=va / top, b=vb / top, at=fmt(va, d), bt=fmt(vb, d), a_better=a_better,
                            b_better=b_better))
        verdict = (f"Level: {a_wins} measures each." if a_wins == b_wins else
                   f"{a if a_wins > b_wins else b} come out ahead on {max(a_wins, b_wins)} of {a_wins + b_wins} measures.")
        return dict(rows=got, verdict=verdict,
                    is_=f"{a} and {b} side by side on each measure; the tick marks the better side.", best_label="Ahead",
                    best=(f"level, {a_wins} measures each" if a_wins == b_wins else
                          f"{a if a_wins > b_wins else b}, better on {max(a_wins, b_wins)} of {a_wins + b_wins} measures"),
                    shows=f"{a} are better on {a_wins} of {a_wins + b_wins} measures, {b} on {b_wins}.",
                    for_="A quick verdict on which side is stronger, measure by measure. The longer bar is the bigger number; "
                         "the tick marks the better team (for runs conceded and economy, lower is better).")
    part("tape", tape)

    def meetings():
        meet = here[((here.home == a) & (here.away == b)) | ((here.home == b) & (here.away == a))]
        if ground == "a_home":
            meet = meet[(meet.home == a) & ~meet.neutral]
        elif ground == "b_home":
            meet = meet[(meet.home == b) & ~meet.neutral]
        elif ground == "neutral":
            meet = meet[meet.neutral]
        aw, bw = int((meet.winner == a).sum()), int((meet.winner == b).sum())
        if meet.empty:
            at_ = {"all": "", "a_home": f" at {poss(a)} home", "b_home": f" at {poss(b)} home", "neutral": " at a neutral ground"}
            return dict(none=f"{a} and {b} haven't played each other in {where_scope}{at_[ground]} yet.", line="", rows=[])
        show = meet.sort_values("date", ascending=False)
        return dict(none="", line=f"{len(meet)} meeting{'s' * (len(meet) != 1)}: {a} {aw} – {bw} {b}"
                    + (f", {len(meet) - aw - bw} other" if len(meet) - aw - bw else ""),
                    rows=[dict(id=r.match_id, date=r.date, stage=r.stage or "", match=f"{r.home} v {r.away}", result=r.result)
                          for r in show.itertuples()])
    part("meetings", meetings)

    def bat_first():
        """Both sides batting first and chasing, in the games picked above (the style guide's chart)."""
        sides = [dict(team=t, **SG.bat_first(career, t, ids_)) for t, ids_ in ((a, ids_a), (b, ids_b))]
        second = "batting second" if sides[0]["multi"] else "chasing"
        what = f"their meetings in {where_scope}" if h2h else f"each side's own games against anyone in {where_scope}"
        def better(x):
            sh = [(w, r["won"] / (r["won"] + r["lost"]) * 100) for w, r in (("batting first", x["first"]), (second, x["chase"]))
                  if r["won"] + r["lost"]]
            if not sh:
                return f"{x['team']}: no wins or defeats yet"
            top = max(sh, key=lambda t: t[1])
            if len(sh) == 2 and sh[0][1] == sh[1][1]:
                return f"{x['team']}: level, {top[1]:.0f}% won each way"
            return f"{x['team']}: {top[0]}, {top[1]:.0f}% won"
        return dict(sides=sides, is_=f"Each side's wins and defeats batting first and {second}, in {what}, with the totals that "
                                     "decided them.", best_label="Better at", best="; ".join(better(x) for x in sides),
                    shows=f"Each side's record batting first and {second}, in {what}, with the totals defended, "
                                       f"lost with, chased down and failed to chase.",
                    for_="Which side is happier setting a total and which chasing one: think about it at the toss.")
    part("bat_first", bat_first)

    _, _, _, base = kept(career, ("player_tables", repr(base_scope)), lambda: player_tables(career, base_scope))
    ta = kept(career, ("player_tables_by_team", repr(scope_for(a, b))), lambda: player_tables(career, scope_for(a, b), by_team=True))
    tb = kept(career, ("player_tables_by_team", repr(scope_for(b, a))), lambda: player_tables(career, scope_for(b, a), by_team=True))
    bat_a, bowl_a = ta[0][ta[0].team == a].copy(), ta[1][ta[1].team == a].copy()
    bat_b, bowl_b = tb[0][tb[0].team == b].copy(), tb[1][tb[1].team == b].copy()
    kind = base.kind
    for d in (bat_a, bat_b):
        d["runs_above_average"] = (d.runs - d.outs * base.average) if kind == "multi" else (d.runs - d.balls * base.strike_rate / 100)
    for d in (bowl_a, bowl_b):
        d["runs_saved"] = (d.wickets * base.bowl_average - d.runs) if kind == "multi" else (
            (d.balls * base.economy / 6 - d.runs) + (d.wickets - d.balls / base.bowl_strike_rate) * WICKET_VALUE[kind])

    def dots(da, db, x, y):
        return [dict(player=r.player, team=r.team, x=getattr(r, x), y=getattr(r, y), note=profile(r))
                for d in (da, db) for r in d.itertuples()]

    def bat_dots():
        fast = lambda d: (d[d.balls > 0].runs / d[d.balls > 0].balls * 100 > base.strike_rate).mean() * 100  # noqa: E731
        return dict(points=dots(bat_a[bat_a.balls > 0], bat_b[bat_b.balls > 0], "balls", "runs"), slope=base.strike_rate / 100,
                    line=f"section strike rate {fmt(base.strike_rate, 1)}", x="Balls faced", y="Runs",
                    is_=f"Every batter of both sides: runs (up) against balls faced (across), {a} gold and {b} blue.",
                    best_label="Most runs",
                    best=SG.best_line(zip(pd.concat([bat_a.player, bat_b.player]), pd.concat([bat_a.runs, bat_b.runs])),
                                      fmt=lambda v: f"{v:,.0f} runs"),
                    shows=f"{fast(bat_a):.0f}% of {poss(a)} batters and {fast(bat_b):.0f}% of {poss(b)} score faster than the "
                          f"section's {fmt(base.strike_rate, 1)} per 100 balls.",
                    for_="Compares the two batting line-ups player by player: who scores quickly and who has faced the most.",
                    keys=[f"Dashed line: the section's average scoring rate.",
                          "Shaded area (above the line): scores faster than the average batter in this section.",
                          "Further right: faced more balls. Top-right dots are the big, quick scorers each side relies on."])
    part("bat_dots", bat_dots)

    def bowl_dots():
        often = lambda d: (d[d.balls > 0].wickets / d[d.balls > 0].balls * base.bowl_strike_rate > 1).mean() * 100  # noqa: E731
        return dict(points=dots(bowl_a, bowl_b, "balls", "wickets"), slope=1 / base.bowl_strike_rate,
                    line=f"a wicket every {fmt(base.bowl_strike_rate, 1)} balls", x="Balls bowled", y="Wickets",
                    is_=f"Every bowler of both sides: wickets (up) against balls bowled (across), {a} gold and {b} blue.",
                    best_label="Most wickets",
                    best=SG.best_line(zip(pd.concat([bowl_a.player, bowl_b.player]), pd.concat([bowl_a.wickets, bowl_b.wickets])),
                                      fmt=lambda v: f"{v:,.0f} wicket{'s' if v != 1 else ''}", minimum=lambda _, v: v > 0),
                    shows=f"{often(bowl_a):.0f}% of {poss(a)} bowlers and {often(bowl_b):.0f}% of {poss(b)} take wickets more "
                          f"often than one every {fmt(base.bowl_strike_rate, 1)} balls.",
                    for_="Compares the two attacks bowler by bowler: who takes wickets and who has done the most bowling.",
                    keys=["Dashed line: the section's average wicket rate.",
                          "Shaded area (above the line): takes wickets more often than the average bowler.",
                          "Further right: bowled more. Top-right dots are the main strike bowlers."])
    part("bowl_dots", bowl_dots)

    def bars(da, db, col):
        sa, sb = da.sort_values(col, ascending=False), db.sort_values(col, ascending=False)
        return [dict(player=r.player, team=r.team, value=getattr(r, col), note=profile(r)) for d in (sa, sb) for r in d.itertuples()]

    def above():
        ba, bb = bat_a[bat_a.innings > 0], bat_b[bat_b.innings > 0]
        pa, pb = (bat_a.runs_above_average > 0).mean() * 100, (bat_b.runs_above_average > 0).mean() * 100
        return dict(rows=bars(ba, bb, "runs_above_average"),
                    is_="Every batter of both sides: runs made above (right) or below (left) what an average batter here would "
                        "have made.",
                    best=SG.best_line(zip(pd.concat([ba.player, bb.player]), pd.concat([ba.runs_above_average, bb.runs_above_average])),
                                      fmt=lambda v: f"{v:+,.0f} runs"),
                    shows=f"{pa:.0f}% of {poss(a)} batters and {pb:.0f}% of {poss(b)} beat the average batter. Team totals: "
                          f"{a} {bat_a.runs_above_average.sum():+.0f}, {b} {bat_b.runs_above_average.sum():+.0f} runs.",
                    for_="Runs scored minus what an average batter in this section would have made: who is pulling their "
                         "weight. Right of the line beat the average.")
    part("above", above)

    def saved():
        pa, pb = (bowl_a.runs_saved > 0).mean() * 100, (bowl_b.runs_saved > 0).mean() * 100
        return dict(rows=bars(bowl_a, bowl_b, "runs_saved"),
                    is_="Every bowler of both sides: runs saved against an average bowler here (right), or given away (left).",
                    best=SG.best_line(zip(pd.concat([bowl_a.player, bowl_b.player]), pd.concat([bowl_a.runs_saved, bowl_b.runs_saved])),
                                      fmt=lambda v: f"{v:+,.0f} runs"),
                    shows=f"{pa:.0f}% of {poss(a)} bowlers and {pb:.0f}% of {poss(b)} beat the average bowler. Team totals: "
                          f"{a} {bowl_a.runs_saved.sum():+.0f}, {b} {bowl_b.runs_saved.sum():+.0f} runs saved.",
                    for_="Runs kept below the section average, with extra wickets turned into runs: which bowlers really "
                         "help. Right of the line beat the average.")
    part("saved", saved)

    def top_side_by_side():
        top = lambda d, col: d.sort_values(col, ascending=False).head(5).reset_index(drop=True)  # noqa: E731
        ra, rb, wa, wb = top(bat_a, "runs"), top(bat_b, "runs"), top(bowl_a, "wickets"), top(bowl_b, "wickets")
        n = max(len(ra), len(rb), len(wa), len(wb))
        cell = lambda d, i, f: f(d.iloc[i]) if i < len(d) else ""  # noqa: E731
        return dict(cols=[f"{a} runs", f"{b} runs", f"{a} wickets", f"{b} wickets"],
                    rows=[[cell(ra, i, lambda r: f"{r.player} {r.runs}"), cell(rb, i, lambda r: f"{r.player} {r.runs}"),
                           cell(wa, i, lambda r: f"{r.player} {r.wickets}"), cell(wb, i, lambda r: f"{r.player} {r.wickets}")]
                          for i in range(n)], num=[], hi=[], links=[])
    part("top", top_side_by_side)
    return out
