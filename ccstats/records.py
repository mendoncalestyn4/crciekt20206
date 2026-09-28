"""Records for one section (or one section and season), and the "New record!"
check for matches that have just been added."""

from __future__ import annotations

import pandas as pd

from .analysis import _overs


def _label(m: pd.DataFrame) -> pd.DataFrame:
    return m[["match_id", "date", "season", "home", "away", "source"]]


def records(career, ids, top: int = 10) -> dict[str, pd.DataFrame]:
    """Top-`top` lists.  Every frame has: rank, holder, value (text), sort, team,
    against, date, match_id, source. Ranks share a place on equal values."""
    m = career.matches[career.matches.match_id.isin(ids)]
    lab = _label(m)
    inn = career.innings[career.innings.match_id.isin(ids)].merge(lab, on="match_id")
    bat = career.batting[career.batting.match_id.isin(ids) & career.batting.did_bat].merge(lab, on="match_id")
    bowl = career.bowling[career.bowling.match_id.isin(ids) & (career.bowling.balls > 0)].merge(lab, on="match_id")
    out: dict[str, pd.DataFrame] = {}

    def finish(name, d, holder, value, sort, team, against, ascending=False):
        if d.empty:
            return
        f = pd.DataFrame({"holder": list(holder), "value": list(value), "sort": list(sort), "team": list(team),
                          "against": list(against), "date": list(d.date), "match_id": list(d.match_id),
                          "source": list(d.source)})
        f = f.sort_values(["sort", "date"], ascending=[ascending, True]).head(top)  # equal: the earlier one first
        f.insert(0, "rank", f["sort"].rank(method="min", ascending=ascending).astype(int))
        out[name] = f.reset_index(drop=True)

    # ---- team
    tot = inn.assign(txt=[f"{r}" if a else f"{r}/{w}{'d' if dec else ''}" for r, w, a, dec in
                          zip(inn.runs, inn.wickets, inn.all_out, inn.declared)])
    finish("Highest team totals", tot, tot.team, tot.txt, tot.runs, tot.team, tot.opposition)
    lo = tot[tot.all_out]
    finish("Lowest completed totals", lo, lo.team, lo.txt, lo.runs, lo.team, lo.opposition, ascending=True)
    w = m[(m.result_type == "win") & m.margin_runs.notna()].merge(lab[["match_id"]], on="match_id")
    w = w.assign(loser_=w.loser)
    finish("Biggest wins by runs", w, w.winner, [f"{int(r)} runs" for r in w.margin_runs], w.margin_runs, w.winner, w.loser_)
    inns_w = m[(m.result_type == "win") & m.innings_win.fillna(False).astype(bool)]
    if len(inns_w):
        finish("Innings wins", inns_w, inns_w.winner, [f"inns & {int(r)} runs" if pd.notna(r) else "an innings" for r in inns_w.margin_runs],
               inns_w.margin_runs.fillna(0), inns_w.winner, inns_w.loser)
    # ---- batting
    finish("Highest individual scores", bat, bat.player, [f"{r}{'' if o else '*'} ({b})" for r, o, b in zip(bat.runs, bat.out, bat.balls)],
           bat.runs * 2 + (~bat.out), bat.team, bat.opposition)
    six = bat[bat.sixes > 0]
    finish("Most sixes in an innings", six, six.player, [f"{s} ({r}{'' if o else '*'})" for s, r, o in zip(six.sixes, six.runs, six.out)],
           six.sixes, six.team, six.opposition)
    season_runs = bat.groupby(["player", "season"]).agg(runs=("runs", "sum"), inns=("runs", "size"), team=("team", "last"),
                                                        date=("date", "max"), match_id=("match_id", "last"),
                                                        source=("source", "last")).reset_index()
    finish("Most runs in a season", season_runs, season_runs.player,
           [f"{r} ({n} inns, {s})" for r, n, s in zip(season_runs.runs, season_runs.inns, season_runs.season)],
           season_runs.runs, season_runs.team, [""] * len(season_runs))
    # ---- bowling
    fig = bowl.assign(k=bowl.wickets * 1000 - bowl.runs)
    finish("Best bowling in an innings", fig, fig.player,
           [f"{w}/{r} ({_overs(b) if not c else str(b) + ' balls'})" for w, r, b, c in zip(fig.wickets, fig.runs, fig.balls, fig.counted_in_balls)],
           fig.k, fig.team, fig.opposition)
    if m.format.isin(["Test", "First-class"]).any():
        bm = bowl.groupby(["match_id", "player"]).agg(wickets=("wickets", "sum"), runs=("runs", "sum"), team=("team", "first"),
                                                      opposition=("opposition", "first"), date=("date", "first"),
                                                      source=("source", "first")).reset_index()
        finish("Best bowling in a match", bm, bm.player, [f"{w}/{r}" for w, r in zip(bm.wickets, bm.runs)],
               bm.wickets * 1000 - bm.runs, bm.team, bm.opposition)
    season_w = bowl.groupby(["player", "season"]).agg(wickets=("wickets", "sum"), runs=("runs", "sum"), team=("team", "last"),
                                                      date=("date", "max"), match_id=("match_id", "last"),
                                                      source=("source", "last")).reset_index()
    finish("Most wickets in a season", season_w, season_w.player,
           [f"{w} (avg {r / w:.1f}, {s})" if w else f"0 ({s})" for w, r, s in zip(season_w.wickets, season_w.runs, season_w.season)],
           season_w.wickets * 100000 - season_w.runs, season_w.team, [""] * len(season_w))
    # ---- partnerships (from the fall of wickets; unbroken stands at the end of an innings count too)
    fow = career.fow[career.fow.match_id.isin(ids)].sort_values(["match_id", "innings_no", "wicket"])
    stands = []
    for (mid, no), g in fow.groupby(["match_id", "innings_no"]):
        prev = 0
        for wk, sc in zip(g.wicket, g.score):
            stands.append((mid, no, int(wk), int(sc - prev), False))
            prev = sc
    fell = fow.groupby(["match_id", "innings_no"]).score.agg(["max", "size"])
    for r in inn[~inn.all_out].itertuples():
        k = (r.match_id, r.innings_no)
        last, n = (int(fell.loc[k, "max"]), int(fell.loc[k, "size"])) if k in fell.index else (0, 0)
        stands.append((r.match_id, r.innings_no, n + 1, int(r.runs - last), True))
    if stands:
        st_ = pd.DataFrame(stands, columns=["match_id", "innings_no", "wicket", "runs", "unbroken"]).merge(
            inn[["match_id", "innings_no", "team", "opposition", "date", "source"]], on=["match_id", "innings_no"])
        suffix = {1: "st", 2: "nd", 3: "rd"}
        finish("Highest partnerships", st_, [f"{t}, {w}{suffix.get(w, 'th')} wicket" for t, w in zip(st_.team, st_.wicket)],
               [f"{r}{'*' if u else ''}" for r, u in zip(st_.runs, st_.unbroken)], st_.runs, st_.team, st_.opposition)
    return out


def recent_sources(career, n: int = 10) -> list[str]:
    """The files of the n most recently played matches."""
    return list(career.matches.sort_values(["date", "match_id"]).source.tail(n))


def new_records(career, sources: list[str]) -> list[str]:
    """Records set by the newly added scorecards: in each section, any list
    whose number 1 comes from one of these files (and wasn't shared)."""
    if not sources:
        return []
    new = career.matches[career.matches.source.isin(sources)]
    msgs = []
    for section in new.section.unique():
        ids = career.matches[career.matches.section == section].match_id
        if len(ids) < 5:  # the first few matches of a section set every record; not worth shouting about
            continue
        for name, t in records(career, ids, top=2).items():
            if t.empty or "season" in name:  # a season total grows every match; only one-match records get an alert
                continue
            first = t.iloc[0]
            if first.source in sources and (len(t) < 2 or t.iloc[1]["rank"] != 1):
                who = f"{first.holder} {first.value}"
                msgs.append(f"New record in {section}! {name}: {who}" + (f" v {first.against}" if first.against else ""))
    return msgs
