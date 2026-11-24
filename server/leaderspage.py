"""Leaders and records (stage 3): Stat by stat, Records, Hall of fame and Rankings.

Stat by stat is the current site's page (views/stat_by_stat.py) in the new style: every qualifying player ranked on
one stat, where everyone sits against the average player, and the full figures. The sums are in the engine
(ccstats/leaders.py); this only turns them into what the page shows. Fielding is gone (your decision of 14 November);
every competition is its own tick box and any can be ticked together, each measured against its own average (your
answers of 13 and 19 November)."""

from __future__ import annotations

import numpy as np

from ccstats import analysis as A
from ccstats import deep as D
from ccstats import leaders as L
from ccstats.stats import Scope, ordinal

from . import styleguide as SG
from .cache import kept
from .teampage import choices, fmt, secs_of, table

TOPS = {"10": 10, "20": 20, "50": 50, "all": 10_000}


def _list(q: dict, key: str) -> list[str]:
    return [x for x in str(q.get(key, "")).split("|") if x]


def _value(v, decimals: int) -> str:
    return fmt(v, decimals) if decimals or v is None or not np.isfinite(v) else f"{int(round(v)):,}"


def stat_by_stat(career, q: dict, mine: list[str]) -> dict:
    ch = choices(career)
    if not ch:   # a career made before any game was played
        return SG.clean(dict(choices=[], none=SG.NO_MATCHES))
    every = [c["section"] for c in ch]
    ticked = [s for s in every if s in set(secs_of(q.get("section", "")))] or [every[0]]
    m = career.matches
    here = m[m.section.isin(ticked)]
    seasons = sorted(map(str, here.season.unique()), reverse=True)
    picked_seasons = [s for s in seasons if s in set(_list(q, "seasons"))]
    disc = q.get("disc") if q.get("disc") in L.DISCS else "Batting"
    in_seasons = here[here.season.astype(str).isin(picked_seasons)] if picked_seasons else here
    events = sorted(in_seasons.event.unique())
    picked_events = [e for e in events if e in set(_list(q, "events"))]
    in_events = in_seasons[in_seasons.event.isin(picked_events)] if picked_events else in_seasons
    teams = sorted(set(in_events.home) | set(in_events.away))
    picked_teams = [t for t in teams if t in set(_list(q, "teams"))]
    picked_venues = [v for v in L.VENUES if v in set(_list(q, "venues"))]
    single = q.get("single") == "1" and disc == "Batting"
    picked_groups = [g for g in L.GROUPS if g in set(_list(q, "pos"))] if disc == "Batting" and not single else []
    picked_single = sorted({int(x) for x in _list(q, "posn") if x.isdigit() and 1 <= int(x) <= 11}) if single else []
    view = "Worst" if q.get("view") == "Worst" else "Best"
    top = q.get("top") if q.get("top") in TOPS else "10"
    try:
        minimum = int(q.get("min", ""))
    except ValueError:
        minimum = None
    only = tuple(sorted(set(_list(q, "only"))))
    scope = Scope(sections=ticked, seasons=picked_seasons, events=picked_events,
                  positions=L.positions_of(picked_groups, picked_single),
                  venues=[L.VENUES[v] for v in picked_venues], teams=picked_teams)
    key = ("statbystat", repr(scope), disc, q.get("stat", ""), view, top, minimum, only, q.get("measure", ""),
           q.get("find", ""), tuple(mine))
    picks = dict(choices=[dict(section=c["section"], matches=c["matches"]) for c in ch], ticked=ticked,
                 section="|".join(ticked), seasons=seasons, picked_seasons=picked_seasons, discs=list(L.DISCS), disc=disc,
                 events=events, picked_events=picked_events, teams=teams, picked_teams=picked_teams,
                 venues=list(L.VENUES), picked_venues=picked_venues, groups=L.GROUPS if disc == "Batting" else [], picked_groups=picked_groups,
                 single=single, picked_single=picked_single, view=view, tops=list(TOPS), top=top)
    body = kept(career, key, lambda: _board(career, scope, disc, q, view, top, minimum, only, mine, ticked,
                                            picked_events, picked_seasons, picked_teams, picked_venues,
                                            picked_groups, picked_single))
    return SG.clean({**picks, **body})


def _where(groups, single, venues) -> str:
    """", batting as openers, home games": what the filters picked, as the page says it ("How out" is gone: your
    choice of 24 November)."""
    where = ""
    if single:
        where = ", batting at no. " + ", ".join(str(x) for x in single)
    elif groups:
        where = ", batting " + " + ".join(("as openers" if g == "Openers (1-2)" else f"at {g.lower()}") for g in groups)
    if venues:
        where += ", " + " / ".join(v.lower() for v in venues) + " games"
    return where


def _board(career, scope, disc, q, view, top, minimum, only, mine, ticked, events, seasons, teams, venues,
           groups, single) -> dict:
    best = view == "Best"
    b = L.board(career, scope, disc, q.get("stat", ""), best=best, minimum=minimum, only=only,
                measure=q.get("measure", "all"))
    stat, raw, unit = b.stat, b.raw, L.UNIT[disc]
    n_top = TOPS[top]
    names = sorted(b.table.player.unique()) if len(b.table) else []
    find = q.get("find", "") if q.get("find", "") in set(names) else ""
    out: dict = dict(stats=[dict(id=s.id, label=s.label) for s in L.stats_for(b.base, disc)], stat=raw.id,
                     measures=[dict(id=k, label=L.MEASURES[k]) for k in b.measures], measure=b.measure,
                     minimum=dict(options=[dict(v=v, label="Anyone" if v == 0 else f"{v}+ {unit}") for v in b.options],
                                  value=b.minimum),
                     names=names, find=find, only=[p for p in only if p in set(names)])
    where = _where(groups, single, venues)
    title = " + ".join(ticked) + (" (each against its own average)" if len(ticked) > 1 else "")
    if events:
        title += " · " + ", ".join(events)
    if seasons:
        title += " " + ", ".join(sorted(seasons))
    if teams:
        title += " · for " + ", ".join(teams)
    pool, ranked = b.pool, b.ranked
    out["statdef"] = dict(label=stat.label, definition=stat.definition,
                          note=f"{title}{where}: {len(pool)} players qualify "
                               f"({'anyone' if not b.minimum else f'{b.minimum}+ {unit}'}). "
                               f"{'Higher is better.' if stat.better == 'high' else 'Lower is better.'}")
    if pool.empty:
        out["none"] = "Nobody qualifies with these settings. Lower the minimum or pick another season."
        return out
    shown = ranked.head(n_top)
    # Find a player: where they rank, or why they aren't on the charts
    if find:
        rk = ranked.reset_index(drop=True)
        hit = rk.index[rk.player == find]
        row = b.table[b.table.player == find]
        if len(hit):
            pos = int(hit[0]) + 1
            out["found"] = (f"🔎 {find}: {ordinal(pos)} of {len(rk)} on {stat.label.lower()} "
                            f"({_value(rk.at[hit[0], stat.column], stat.decimals)}), highlighted on both charts"
                            + (f" (outside the top {n_top} in the bar chart: pick a bigger Show to see their bar)."
                               if pos > n_top else "."))
        else:
            if only and find not in only:
                why = "they're not in Only these players"
            elif len(row) and row[stat.column].isna().all():
                why = f"they have no {stat.label.lower()} figure yet"
            elif len(row) and int(row["balls"].max()) < b.minimum:
                why = (f"{int(row['balls'].max())} {unit} so far, under the minimum of {b.minimum}: set Minimum to "
                       "qualify lower to see them")
            else:
                why = "they don't qualify with these settings"
            out["found"] = f"🔎 {find} isn't on these charts: {why}."
    # the ranking chart
    r0 = shown.iloc[0]
    v0 = float(r0[stat.column])
    ref = stat.reference
    vs = (f", {(v0 - ref) / abs(ref) * 100:+.0f}% on the average of {fmt(ref, max(stat.decimals, 1))}"
          if ref is not None and np.isfinite(ref) and ref else "")
    lower = stat.better == "low"
    word = "best" if best else "worst"
    out["bars"] = dict(
        title=f"{view} {min(n_top, len(pool))} · {stat.label}",
        rows=[dict(player=r.player, team=r.teams, value=float(getattr(r, stat.column)),
                   text=_value(float(getattr(r, stat.column)), stat.decimals), hi=r.player == find)
              for r in shown.itertuples()],
        reference=ref if ref is not None and np.isfinite(ref) else None,
        decimals=stat.decimals, lower=lower,
        **SG.lines(f"Every qualifying player in {title}{where} ranked on {stat.label.lower()}, the {word} "
                   f"{min(n_top, len(pool))} shown.",
                   SG.best_line(zip(pool.player, pool[stat.column]), fmt=lambda v: _value(v, stat.decimals),
                                lower=lower == best) + (vs if len(pool) else ""),
                   f"{stat.definition} Ranks who is {word} at this one thing.",
                   best_label="Who's best" if best else "Who's worst"),
        shows=f"{'Top' if best else 'Bottom'}: {r0.player} with {_value(v0, stat.decimals)}{vs}. {len(pool)} players "
              "qualify.")
    # where everyone sits
    d = stat.dot
    share, _ = L.better_side(b)
    named = set(shown.player.head(4))
    lit = set(shown.player)
    out["dots"] = dict(
        title=f"Where everyone sits · {d.y_label} vs {d.x_label.lower()}",
        x_label=d.x_label, y_label=d.y_label, line=d.line, value=float(d.value) if np.isfinite(d.value) else None,
        better_below=d.better_below, decimals=stat.decimals,
        points=[dict(player=p, team=t, x=float(x), y=float(y), ranked=p in lit, named=p in named, hi=p == find)
                for p, t, x, y in zip(pool.player, pool.teams, pool[d.x], pool[d.y])
                if np.isfinite(float(x)) and np.isfinite(float(y))],
        **SG.lines(f"Every qualifying player: {d.y_label.lower()} against {d.x_label.lower()}, with the average "
                   f"player's line ({d.line_label}).",
                   f"{share:.0f}% of the {len(pool)} qualifying players are on the better side of the line",
                   "Shows everyone at once, so you can tell a great figure from a lucky one: the further right a dot, "
                   "the more games it rests on.", best_label="On the better side"),
        shows=f"{share:.0f}% of the {len(pool)} qualifying players are on the better side of the average line "
              f"({d.line_label}).",
        explain=[["line", f"Dashed line: the average player in {'these competitions' if len(ticked) > 1 else 'this competition'}"
                          f"{where}: {d.line_label}. A dot on the line is exactly average."],
                 ["shade", f"Shaded area ({'below' if d.better_below else 'above'} the line): "
                           f"{d.below if d.better_below else d.above} This is the better side."],
                 ["", f"{'Above' if d.better_below else 'Below'} the line: {d.above if d.better_below else d.below}"],
                 ["", f"Further right: {d.right} The further right a dot is, the more you can trust its position."],
                 ["dot" if best else "dot neg", "Coloured dots: the players ranked on the left (the top 4 named; "
                                                "point at any dot for its figures). Grey dots: everyone else who "
                                                "qualifies."]])
    out["table"] = _figures(career, scope, b, shown, pool, disc, mine, seasons)
    out["csv"] = f"{' + '.join(ticked)} {stat.label}.csv".replace("/", "-")
    return out


def _figures(career, scope, b, shown, pool, disc, mine, seasons) -> dict:
    """The full figures for the players ranked above, with where each figure sits among everyone (Rank %), the same
    figure the season before (one season picked) and each player's role."""
    stat = b.stat
    base = b.base
    if disc == "Batting":
        cols = [("player", "Player"), ("teams", "Team"), ("matches", "Mat"), ("innings", "Inns"), ("not_outs", "NO"),
                ("runs", "Runs"), ("balls", "BF"), ("high_score_text", "HS"), ("average", "Avg"),
                ("strike_rate", "SR"), ("hundreds", "100"), ("fifties", "50"), ("ducks", "0"), ("fours", "4s"),
                ("sixes", "6s"), ("boundary_pct", "Bdry %"), ("runs_above_average", "Runs above avg")]
    else:
        last = ("dot_pct", "Dot %") if base.has_dots else ("maidens", "Mdns")
        cols = [("player", "Player"), ("teams", "Team"), ("innings", "Inns"), ("overs", "Overs"), ("runs", "Runs"),
                ("wickets", "Wkts"), ("best", "BBI"), ("best_match", "BBM"), ("average", "Avg"), ("economy", "Econ"),
                ("strike_rate", "SR"), last, ("hauls", "4w+"), ("five_fors", "5w"), ("runs_saved", "Runs saved")]
        if base.kind != "multi":
            cols = [c for c in cols if c[0] != "best_match"]   # one innings each: the best match is the best innings
    keys = [k for k, _ in cols]
    if stat.column not in keys:   # the ranked figure is always in the table (50+ scores, a fair index)
        label = stat.label if stat.column != "fair" else ("% v average" if "%" in stat.label else "v average")
        cols = cols[:3] + [(stat.column, label)] + cols[3:]
    spot = next(i for i, (k, _) in enumerate(cols) if k == stat.column)
    pctl = D.percentiles(pool, stat.column, stat.better)
    heads = [h for _, h in cols]
    heads.insert(spot + 1, "Rank %")
    prev_col = None
    if len(seasons) == 1 and stat.column != "fair":
        ch, prev = D.change_since(career, scope, disc, stat.column)
        if prev:
            prev_col = (ch, prev)
            heads.insert(spot + 2, f"v {prev}")
    roles = A.role_labels(career, scope.match_ids(career.matches), base.kind).set_index("player")
    heads.insert(2, "Role")
    dec = {"average": 1, "strike_rate": 1, "boundary_pct": 1, "runs_above_average": 1, "runs_saved": 1, "dot_pct": 1,
           "economy": 2}
    rows, parts, hi = [], [], []
    for i, r in zip(shown.index, shown.itertuples()):
        row = []
        for k, _ in cols:
            v = getattr(r, k, None) if k != "overs" else None
            if k == "overs":
                row.append(SG.overs(int(r.balls)))
            elif k == "fair":
                row.append(f"{v:+.0f}%" if "%" in stat.label and v is not None and np.isfinite(v) else fmt(v, 1))
            elif k in dec:
                row.append(fmt(v, dec[k]))
            elif k in ("player", "teams", "high_score_text", "best", "best_match"):
                row.append(v if v not in (None, "") else "–")
            else:
                row.append(int(v) if v is not None and np.isfinite(float(v)) else "–")
        row.insert(spot + 1, D.top_text(pctl.get(i)))
        if prev_col:
            change = prev_col[0].get(r.player, np.nan)
            if change is None or not np.isfinite(change):
                text = "–"
            else:
                good = (change > 0) == (stat.better == "high")
                text = (("▲ " if good else "▼ ") + (f"{change:+.{stat.decimals}f}" if stat.decimals else f"{change:+.0f}")
                        if change else "▬ 0")
            row.insert(spot + 2, text)
        role = " · ".join([roles.role[r.player]] + list(roles.tags[r.player])) if r.player in roles.index else "–"
        row.insert(2, role)
        rows.append(row)
        if disc == "Batting":
            parts.append(dict(runs=int(r.runs), outs=int(r.outs), bf=int(r.balls), inns=int(r.innings)))
        else:
            parts.append(dict(bruns=int(r.runs), wkts=int(r.wickets), bballs=int(r.balls), binns=int(r.innings)))
        hi.append(any(t in set(mine) for t in str(r.teams).split(" / ")))
    num = [i for i, h in enumerate(heads) if h not in ("Player", "Team", "Role", "Rank %", "HS", "BBI", "BBM")
           and not h.startswith("v ")]
    t = table(heads, rows, num=num, hi=hi, parts=parts)
    t["bold"] = heads.index(next(h for k, h in cols if k == stat.column))
    t["note"] = ("Rank %: where the figure sits among everyone who qualifies (top 5% = better than 95% of them). "
                 + ("v last season: the same figure the season before (▲ better, ▼ worse)." if prev_col else
                    "Pick one season to see each figure against the season before."))
    t["title"] = f"Full figures for the players ranked above · sorted by {stat.label.lower()}"
    return t
