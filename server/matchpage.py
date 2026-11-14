"""The Matches section's numbers: finding a match, the best games (the match excitement rating), and one match in
full (the summary, the report and its excitement, the win chance through the match, wicket by wicket, the scorecard,
your side's best and worst, your notes).

Every number comes from the engine; this module only picks and arranges them, with the same words as the current
site's Matches page (views/match.py)."""

from __future__ import annotations

import pandas as pd

from ccstats import excitement as X
from ccstats import extras as E
from ccstats import partnerships as PT
from ccstats import teamreport as TR
from ccstats import winprob as W
from ccstats.competitions import shown_name, with_stage
from ccstats.stats import poss

from . import styleguide as SG
from .cache import kept

BEST = 15


def name_of(r) -> str:
    """'ODI World Cup · Final' or 'ODIs'."""
    return with_stage(shown_name(r.section, r.event), r.stage)


def label(r) -> str:
    """'05 Jan 2029 · Mumbai CC v Sikkim · Vijay Hazare Trophy · Mumbai CC won by 1 wicket'."""
    return f"{r.date:%d %b %Y} · {r.home} v {r.away} · {name_of(r)} · {r.result}"


def finder(career, section: str = "", team: str = "", mine: list[str] | None = None) -> dict:
    """The choices (every section; the teams in the one picked) and the matches they leave, newest first. With no
    section asked for, the one your team played in last."""
    m = career.matches.sort_values(["date", "match_id"], ascending=False)
    sections = sorted(m.section.unique())
    if not section:
        played = m[m.home.isin(mine or []) | m.away.isin(mine or [])]
        section = played.section.iloc[0] if len(played) else "All sections"
    pool = m if section == "All sections" else m[m.section == section]
    teams = sorted(set(pool.home) | set(pool.away))
    if team and team != "All teams":
        pool = pool[(pool.home == team) | (pool.away == team)]
    # our score v theirs: the team's latest matches in the competition picked (one competition: formats never mixed)
    scores = None
    if team and team != "All teams" and section != "All sections" and len(pool):
        rs = SG.in_played_order(career, SG.results(career, team, pool.match_id))[-14:]
        scores = dict(results=rs, summary=SG.scores(rs, team), team=team)
    return dict(section=section, team=team or "All teams", sections=["All sections"] + sections,
                teams=["All teams"] + teams, scores=scores,
                matches=[dict(id=r.match_id, label=label(r), date=SG.clean(r.date), home=r.home, away=r.away,
                              section=r.section, event=r.event, name=name_of(r), result=r.result) for r in pool.itertuples()])


def ratings(career, section: str) -> pd.DataFrame:
    """Every match's excitement rating in a section (kept: a few seconds for a big section)."""
    def make():
        ids = career.matches[career.matches.section == section].match_id
        return X.rate(career, ids)
    return kept(career, ("excitement", section), make)


def all_ratings(career) -> pd.DataFrame:
    parts = [ratings(career, s) for s in sorted(career.matches.section.unique())]
    parts = [p for p in parts if len(p)]
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=X.RATING_COLUMNS)


def best_games(career, section: str, team: str = "", top: int = BEST) -> dict:
    """The most exciting matches: in a section (ranked within it), or in every section; one team's if one is picked
    (its best `top`, not the section's best that it happened to play in)."""
    d = all_ratings(career) if section == "All sections" else ratings(career, section)
    if team and team != "All teams":
        d = d[(d.home == team) | (d.away == team)]
    d = d.sort_values(["rating", "date"], ascending=[False, False]).head(top)
    meta = career.matches.set_index("match_id")
    return dict(section=section, team=team or "All teams", rows=[SG.clean(dict(
        id=r.match_id, rating=r.rating, rank=r.rank, of=r.of, home=r.home, away=r.away, date=r.date,
        section=r.section, event=meta.event[r.match_id], name=name_of(meta.loc[r.match_id]),
        result=r.result, why=r.why, finish=r.finish, comeback=r.comeback, stakes=r.stakes, show=r.show))
        for r in d.itertuples()])


def _rain(r) -> str:
    """Why a rain game looks odd, as the current site says it."""
    if not bool(r.rain):
        return ""
    if r.result_type == "no result":
        why = "Abandoned because of rain: it counts as no result, and it's left out of net run rate."
    elif str(r.margin_note).startswith("Rain-affected"):
        why = (f"Shortened by rain and decided by the rain rule (DLS), so the margin isn't the difference in the "
               f"totals: {r.margin_note.split(';', 1)[-1].strip().rstrip('.')}.")
    else:
        why = "Shortened by rain: the sides didn't get their full overs."
    return (f"{why} Games like this aren't used for par scores, \"Is this total enough?\", lowest total defended or the "
            "win chances of other games; the players' runs and wickets count as normal.")


def _win_chance(career, row, line, kind: str) -> dict | None:
    if len(line) <= 1:
        return None
    if not line.W.notna().any():
        return dict(none=f"Win chance through the match: not enough other {row.section} games yet to compare this one with.")
    multi = kind == "multi"
    t1, t2 = line.attrs["team1"], line.attrs["team2"]
    pts = W.line_points(line, row.result, multi)
    starts = [i for i, lab in enumerate(line.label) if lab.startswith("Start of innings") and i]
    sw, low = W.biggest_swing(line), W.lowest_for_winner(line)
    shows = (f"The biggest swing came at {sw['at']}: {poss(t1)} chance went from {sw['before']:.0f}% to "
             f"{sw['after']:.0f}%." if sw else "")
    if low:
        shows += f" The winner's lowest point was {low[0]:.0f}% at {low[1]}."
    return dict(team1=t1, team2=t2, multi=multi, starts=starts,
                points=[SG.clean(dict(label=p.label, W=p.W, D=(p.D + (p.T if pd.notna(p.T) else 0)) if multi else p.D,
                                      L=p.L, note=p.note)) for p in pts.itertuples()],
                shows=shows or "Not enough similar games yet.",
                for_=(f"Shows how the game swung. Each point is how often {row.section} games in the same spot (same "
                      "innings, same wickets down, a similar lead) ended in a win" + (", draw or defeat" if multi else "")
                      + ". The scorecards have no overs, so it uses runs and wickets only; hover a point for how many "
                      "games it rests on. The last point is the result."))


def _wickets(career, mid: str, row, inns: pd.DataFrame) -> dict:
    """Wicket by wicket: every innings as a climbing bar per wicket (the score at the fall, the stand, who was in),
    the par (the usual score at each wicket in the section) and the biggest stand."""
    st = PT.stands(career, [mid])
    out = []
    for r in inns.itertuples():
        s = st[st.innings_no == r.innings_no].sort_values("wicket")
        steps = [dict(wicket=int(x.wicket), score=int(x.end), start=int(x.start), stand=int(x.runs),
                      unbroken=bool(x.unbroken), batters=[x.batter1, x.batter2] if x.known else [])
                 for x in s.itertuples()]
        total = f"{r.runs}" if r.all_out else f"{r.runs}/{r.wickets}"
        out.append(dict(innings_no=int(r.innings_no), team=r.team, total=total, all_out=bool(r.all_out),
                        label=f"{r.team} {total}" + (" (2nd inns)" if r.team_innings == 2 else ""), steps=steps))
    sec_ids = career.matches[career.matches.section == row.section].match_id
    par = None
    if len(sec_ids) >= 5:
        p = E.par_by_wicket(career, sec_ids)
        n_inns = int(career.innings.match_id.isin(sec_ids).sum())
        p = p[p.innings >= 0.3 * n_inns]   # later wickets fall in too few innings for a fair par
        par = [dict(wicket=int(w), par=float(v), innings=int(n)) for w, v, n in zip(p.wicket, p.par, p.innings)]
    big = ""
    if len(st):
        b = st.sort_values("runs", ascending=False).iloc[0]
        n = int(b.wicket)
        who = f" by {b.batter1} and {b.batter2}" if b.known else ""
        tot = career.innings[(career.innings.match_id == mid) & (career.innings.team == b.team)].runs.sum()
        big = (f"The biggest stand was {b.runs}{'*' if b.unbroken else ''} for the {n}{PT.suffix(n)} wicket{who} for "
               f"{b.team}, {b.runs / max(tot, 1) * 100:.0f}% of their runs in the match.")
    return dict(innings=out, par=par, section=row.section, shows=big,
                for_="Shows how each innings was built and where it fell apart, wicket by wicket.")


def _extras_text(r) -> str:
    parts = [f"{k} {int(v)}" for k, v in (("b", r.byes), ("lb", r.leg_byes), ("w", r.wides), ("nb", r.no_balls)) if v]
    return f"Extras {int(r.extras)}" + (f" ({', '.join(parts)})" if parts else "")


def page(career, match_id: str, mine: list[str], notes: dict) -> dict:
    """One match in full."""
    meta = career.matches.set_index("match_id")
    if match_id not in meta.index:
        raise KeyError(match_id)
    row = career.matches[career.matches.match_id == match_id].iloc[0]
    inns = career.innings[career.innings.match_id == match_id].sort_values("innings_no")
    card = SG.scorecard(career, match_id)
    # each innings as the scorecard prints it: its length, extras, total, and whether it followed on
    first_team = inns.team.iloc[0] if len(inns) else ""
    for c, r in zip(card["cards"], inns.itertuples()):
        tot = f"{r.runs} all out" if r.all_out else f"{r.runs}/{r.wickets}{' declared' if r.declared else ''}"
        length = f"{r.balls} balls" if r.counted_in_balls else f"{c['overs']} overs"
        c.update(team_innings=int(r.team_innings), length=length, total_text=tot, extras_text=_extras_text(r),
                 counted_in_balls=bool(r.counted_in_balls),
                 followed_on=bool(r.team_innings == 2 and r.innings_no == 3 and r.team != first_team),
                 how_fell={str(k): int(v) for k, v in career.batting[(career.batting.match_id == match_id)
                           & (career.batting.innings_no == r.innings_no) & career.batting.out]
                           .how_out.value_counts().items()})
    series = (f" · Match {int(row.series_match_no)}" + (f" of {int(row.series_length)}" if pd.notna(row.series_length) else "")
              if pd.notna(row.series_match_no) else "")
    # the report, with the turning point from the win chance
    sec_ids = career.matches[career.matches.section == row.section].match_id
    states = kept(career, ("states", row.section), lambda: W.states(career, sec_ids))
    kind = W.kind_of_ids(career, sec_ids)
    line = W.match_line(career, match_id, states, kind)
    rt = ratings(career, row.section).set_index("match_id")
    ex = None
    if match_id in rt.index:
        x = rt.loc[match_id]
        ex = SG.clean(dict(rating=x.rating, rank=x["rank"], of=x["of"], why=x.why, finish=x.finish,
                           comeback=x.comeback, stakes=x.stakes, show=x.show))
    bat = career.batting[(career.batting.match_id == match_id) & career.batting.did_bat]
    bowl = career.bowling[career.bowling.match_id == match_id]
    top_bat = bat.sort_values(["runs", "balls"], ascending=[False, True]).head(3)
    top_bowl = bowl.assign(k=bowl.wickets * 1000 - bowl.runs).sort_values("k", ascending=False).head(3)
    sides = []
    for side in [t for t in mine if t in (row.home, row.away)]:
        c = TR.match_card(career, match_id, side)
        if c:
            sides.append(dict(team=side, best=[dict(player=p, figures=f) for p, f, _ in c["best"]],
                              worst=[dict(player=p, figures=f) for p, f, _ in c["worst"]]))
    return SG.clean(dict(
        id=match_id, kicker=f"{name_of(row)}{series} · {row.date:%d %b %Y}", name=name_of(row), series=series.strip(" ·"),
        date=row.date, section=row.section, event=row.event, stage=row.stage or "", home=row.home, away=row.away,
        home_score=SG.score_of(career, match_id, row.home), away_score=SG.score_of(career, match_id, row.away),
        result=row.result + (f" (super over: {row.super_over})" if row.super_over else ""),
        player_of_match=row.player_of_match or "", rain=_rain(row), source=row.source,
        corrected=list(career.corrections[career.corrections.match_id == match_id].correction)
        if hasattr(career, "corrections") else [],
        note=notes.get(row.source, ""), match=card, report=W.match_report(career, match_id, line), excitement=ex,
        win=_win_chance(career, row, line, kind), wickets=_wickets(career, match_id, row, inns), sides=sides,
        top_scores=[dict(player=r.player, team=r.team, score=f"{r.runs}{'' if r.out else '*'}", balls=int(r.balls))
                    for r in top_bat.itertuples()],
        best_bowling=[dict(player=r.player, team=r.team, figures=f"{r.wickets}/{r.runs}",
                           overs=f"{r.balls} balls" if r.counted_in_balls else SG.overs(r.balls))
                      for r in top_bowl.itertuples()]))
