"""Compare players (stage 3): the current site's page (views/compare.py), up to four players side by side, every stat
as its own chart with the average marked, and how each career has built up. New (your answers 12, 15, 16, 22):
the competition dropdown with tick boxes (several counted together, runs above average and runs saved each worked
out in its own competition and added up), and "plays like": the three players most like the one picked, inside one
competition, for batters and bowlers; clicking one adds them (with four already picked: "remove one first"). The sums
are in the engine (ccstats/leaders.py, compare.py, analysis.py); this only turns them into what the page shows."""

from __future__ import annotations

import numpy as np

from ccstats import analysis as A
from ccstats import compare as CP
from ccstats import leaders as L
from ccstats.stats import Scope

from . import styleguide as SG
from .cache import kept
from .teampage import choices, fmt, secs_of

BAT_FIELDS = [("Inns", "innings", 0), ("Runs", "runs", 0), ("Avg", "average", 2), ("SR", "strike_rate", 1),
              ("HS", "high_score_text", None), ("100", "hundreds", 0), ("50", "fifties", 0), ("0", "ducks", 0),
              ("4s", "fours", 0), ("6s", "sixes", 0), ("Bdry %", "boundary_pct", 1), ("Runs above avg", "runs_above_average", 1)]
BOWL_FIELDS = [("Inns", "innings", 0), ("Wkts", "wickets", 0), ("Avg", "average", 2), ("Econ", "economy", 2),
               ("SR", "strike_rate", 1), ("BBI", "best", None), ("4w+", "hauls", 0), ("Runs saved", "runs_saved", 1)]


def _list(q, key) -> list[str]:
    return [x for x in str(q.get(key, "")).split("|") if x]


def compare_page(career, q: dict, mine: list[str]) -> dict:
    ch = choices(career)
    if not ch:
        return SG.clean(dict(choices=[], none=SG.NO_MATCHES))
    every = [c["section"] for c in ch]
    ticked = [s for s in every if s in set(secs_of(q.get("section", "")))] or [every[0]]
    seasons = sorted({s for c in ch if c["section"] in set(ticked) for s in c["seasons"]}, reverse=True)
    season = str(q.get("season", ""))
    season = season if season in seasons else ""
    disc = q.get("disc") if q.get("disc") in L.DISCS else "Batting"
    picked, like = tuple(_list(q, "players")), str(q.get("like", ""))
    key = ("compare", tuple(ticked), season, disc, picked, like)
    body = kept(career, key, lambda: _body(career, ticked, season, disc, list(picked), like))
    head = dict(choices=[dict(section=c["section"], matches=c["matches"]) for c in ch], ticked=ticked, section="|".join(ticked),
                seasons=seasons, season=season, discs=list(L.DISCS), disc=disc)
    return SG.clean({**head, **body})


def _body(career, ticked, season, disc, picked, like) -> dict:
    m = career.matches
    real = [s for s in m[m.section.isin(ticked)].season.unique() if str(s) == season]
    scope = Scope(sections=ticked, seasons=real)
    table, base = L.tables(career, scope, disc)
    table = table[table.innings > 0]
    names = sorted(table.player)
    chosen = [p for p in dict.fromkeys(picked) if p in set(names)][:4]
    if not picked or not chosen:
        chosen = list(table.sort_values("runs" if disc == "Batting" else "wickets", ascending=False).player.head(2))
    where = " + ".join(ticked) + (f" {season}" if season else "")
    one = len(ticked) == 1
    out: dict = dict(names=names, players=chosen, where=where, one=one)
    if len(chosen) < 2:
        out["few"] = "Pick at least two players."
    rows = table.set_index("player").loc[chosen] if chosen else table.iloc[0:0]
    fields = BAT_FIELDS if disc == "Batting" else BOWL_FIELDS
    def shown(v, d):   # whole numbers with a comma for thousands, as everywhere else on the site
        if d is None:
            return str(v)
        t = fmt(v, d)
        return f"{int(round(float(v))):,}" if d == 0 and t != "–" else (f"{float(v):,.{d}f}" if t != "–" else t)
    out["summary"] = dict(cols=[""] + chosen, rows=[[label] + [shown(rows.loc[p, col], d)
                                                            for p in chosen] for label, col, d in fields],
                          num=list(range(1, len(chosen) + 1)), hi=[], links=[])
    # one chart per stat (the stat-by-stat page's definitions), the average marked when one competition is picked
    charts = []
    for st in L.stats_for(base, disc):
        vals = [(p, rows.loc[p, st.column]) for p in chosen]
        ok = [(p, float(v)) for p, v in vals if v is not None and np.isfinite(float(v))]
        ref = st.reference if one and st.reference is not None and np.isfinite(st.reference) else None
        if ok:
            bp, bv = (max if st.better == "high" else min)(ok, key=lambda x: x[1])
            vs = f" ({(bv - ref) / abs(ref) * 100:+.0f}% on the average of {fmt(ref, max(st.decimals, 1))})" if ref else ""
            best = f"{bp}, {fmt(bv, st.decimals)}{vs}"
        else:
            best = ""
        charts.append(dict(id=st.id, label=st.label, better="higher is better" if st.better == "high" else "lower is better",
                           reference=round(float(ref), 4) if ref is not None else None, dec=st.decimals,
                           rows=[dict(player=p, value=round(float(v), 4) if v is not None and np.isfinite(float(v)) else 0,
                                      text=shown(float(v), st.decimals) if v is not None and np.isfinite(float(v)) else "–") for p, v in vals],
                           **SG.lines(f"{st.label} of the players picked in {where}"
                                      + (", the competition's average dashed." if ref is not None else "."),
                                      best, st.definition, best_label="Best of them")))
    out["charts"] = charts
    if not one:
        out["combined"] = ("Several competitions are counted together: runs above average and runs saved are each worked out "
                           "against its own competition's average and added up; the other figures are the plain totals, so "
                           "no average line is drawn.")
    # how each career has built up
    ids = list(scope.match_ids(m))
    what = "runs" if disc == "Batting" else "wickets"
    curves, ends = [], []
    for p in chosen:
        d = A.batting_innings(career, ids, p) if disc == "Batting" else A.bowling_spells(career, ids, p)
        y = d[what].cumsum().astype(int).tolist()
        curves.append(dict(player=p, points=y))
        if y:
            ends.append((p, y[-1], len(y)))
    if ends:
        lead = max(ends, key=lambda x: x[1])
        rate = max(ends, key=lambda x: x[1] / x[2])
        best = (f"{lead[0]}, {lead[1]} {what} in {lead[2]} innings; {rate[0]} gets there fastest, "
                f"{rate[1] / rate[2]:.{2 if what == 'wickets' else 1}f} an innings")
    else:
        best = ""
    out["curves"] = dict(series=curves, what=what, **SG.lines(
        f"Each player's total {what} in {where} after every innings.", best,
        "Shows how each career has built up. A steeper line means more per innings; where a line ends shows how many "
        "innings they've played.", best_label="Most so far"))
    # plays like (answers 15, 16): inside the one competition where the player has played most here
    like = like if like in set(chosen) else (chosen[0] if chosen else "")
    if like:
        b = career.batting if disc == "Batting" else career.bowling
        played = b[b.match_id.isin(ids) & (b.player == like)]
        counts = played.match_id.map(m.set_index("match_id").section).value_counts()
        sec = counts.index[0] if len(counts) else ticked[0]
        pl = CP.plays_like(career, sec, real, like, disc)
        feats = CP.FEATURES[disc]
        own = CP.figures_of(career, sec, real, like, disc)
        def said(r):
            return " · ".join(f"{lab} {r[c]:.0f}" if c in ("position", "order") else f"{lab} {r[c]:.{2 if c == 'economy' else 1}f}"
                              for c, lab in feats)
        out["like"] = dict(player=like, section=sec, full=len(chosen) >= 4,
                           own=said(own) if own else "",
                           rows=[dict(player=r.player, team=r.teams, alike=f"{r.alike:.0f}%", figures=said(r._asdict()),
                                      picked=r.player in set(chosen)) for r in pl.itertuples()],
                           none="" if len(pl) else (f"{like} hasn't enough in {sec} yet to judge how they play "
                                                    f"({'3 dismissals' if disc == 'Batting' else '3 wickets'})."),
                           note=("Matched inside " + sec + " only, on "
                                 + ("average, strike rate, share of runs in fours and sixes and usual batting position."
                                    if disc == "Batting" else "average, economy, strike rate and usual place in the bowling order "
                                    "(the new ball or later).")
                                 + " 100% = every one of those the same."))
    return out
