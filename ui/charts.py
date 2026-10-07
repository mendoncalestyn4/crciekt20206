"""Plotly figures shared by the pages: one stat per chart, readable in both themes."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from ccstats.stats import Stat

from .theme import colours

FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'
# Only one button on each chart: a camera that saves the chart as a picture (shows when you hover the chart).
CONFIG = {"displayModeBar": "hover", "displaylogo": False, "modeBarButtons": [["toImage"]],
          "toImageButtonOptions": {"format": "png", "scale": 2, "filename": "cricket-captain-stats-chart"}}


def _axis(c, title, **extra):
    base = dict(title=dict(text=title, font=dict(size=12, color=c["ink2"]), standoff=8), gridcolor=c["grid"],
                zeroline=False, linecolor=c["axis"], showline=True, tickfont=dict(size=11, color=c["muted"]),
                automargin=True)
    base.update(extra)
    return base


def _layout(c, **extra):
    base = dict(paper_bgcolor=c["surface"], plot_bgcolor=c["surface"], font=dict(family=FONT, color=c["ink"], size=12),
                margin=dict(l=10, r=16, t=10, b=10), showlegend=False,
                modebar=dict(bgcolor="rgba(0,0,0,0)", color=c["muted"], activecolor=c["ink"]),
                hoverlabel=dict(bgcolor=c["surface"], bordercolor=c["axis"], font=dict(family=FONT, color=c["ink"], size=12)))
    base.update(extra)
    return base


def fmt(v, decimals: int) -> str:
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return "–"
    return f"{v:.{decimals}f}" if decimals else f"{int(round(v))}"


def pct(v, decimals: int = 0) -> str:
    """'54%', or '–' when there's nothing to show (never '–%' or 'nan%')."""
    t = fmt(v, decimals)
    return t if t == "–" else t + "%"


def signed(v, decimals: int = 0) -> str:
    """'+12' / '−3', or '–' when there's nothing to show."""
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return "–"
    return f"{v:+.{decimals}f}"


def label_backing(c: dict) -> str:
    """A see-through panel colour behind a name written over the dots, so it stays readable."""
    h = c["surface"].lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},0.78)"


def label_annotations(named, dots, x_range, y_range, c: dict, width_px: float = 400,
                      height_px: float = 350) -> list[dict]:
    """Annotations naming some dots, each placed right next to its own dot.

    named: [(x, y, text)] to label, most important first; dots: [(x, y)] for every
    dot on the chart.  Each name tries spots close around its dot (above, below,
    beside, diagonals) and takes the first that touches no other name and no dot;
    if every close spot is taken it moves further out, and then a thin line joins
    the name to its dot, so a name is never left floating away from its player."""
    (x0, x1), (y0, y1) = x_range, y_range

    def px(x, y):
        return (x - x0) / ((x1 - x0) or 1) * width_px, (y - y0) / ((y1 - y0) or 1) * height_px

    dot_px = [px(x, y) for x, y in dots]
    boxes: list[tuple[float, float, float, float]] = []  # placed names: centre x, centre y, half width, half height
    out = []
    for x, y, text in named:
        cx, cy = px(x, y)
        hw, hh = (6.3 * len(str(text)) + 8) / 2, 8
        best = None
        for ring in (1, 2, 3, 4):
            gap = 10 + (ring - 1) * 16
            for dx, dy in ((0, gap + hh), (0, -(gap + hh)), (gap + hw, 0), (-(gap + hw), 0),
                           (gap + hw, gap + hh), (-(gap + hw), gap + hh), (gap + hw, -(gap + hh)),
                           (-(gap + hw), -(gap + hh))):
                bx, by = cx + dx, cy + dy
                if bx - hw < -4 or bx + hw > width_px + 4 or by - hh < -6 or by + hh > height_px + 30:
                    continue  # off the chart
                if any(abs(bx - ox) < hw + ow + 3 and abs(by - oy) < hh + oh + 2 for ox, oy, ow, oh in boxes):
                    continue  # on another name
                covered = sum(1 for qx, qy in dot_px if abs(bx - qx) < hw + 5 and abs(by - qy) < hh + 5)
                if best is None or covered < best[0]:
                    best = (covered, dx, dy)
                if covered == 0:
                    break
            if best is not None and best[0] == 0:
                break
        if best is None:  # nowhere free: straight above, joined by a line
            best = (0, 0, 70 + 16 * len(out))
        _, dx, dy = best
        boxes.append((cx + dx, cy + dy, hw, hh))
        far = abs(dx) > hw + 14 or abs(dy) > hh + 14
        out.append(dict(x=x, y=y, text=text, showarrow=True, ax=dx, ay=-dy, axref="pixel", ayref="pixel",
                        arrowhead=0, arrowwidth=1, standoff=5,
                        arrowcolor=c["muted"] if far else "rgba(0,0,0,0)",
                        font=dict(size=11, color=c["ink2"]), bgcolor=label_backing(c), borderpad=1))
    return out


def say(word: str) -> str:
    """A label as it's written in cricket: "Run out", "LBW", "No result"."""
    return "LBW" if word.lower() == "lbw" else word[:1].upper() + word[1:]


def ranked_bars(rows: pd.DataFrame, stat: Stat, best: bool, highlight: str = "") -> go.Figure:
    c = colours()
    colour = c["s1"] if best else c["neg"]
    r = rows.iloc[::-1]
    labels = [p + ("  ◀" if p == highlight else "") for p in r.player]
    fig = go.Figure(go.Bar(
        x=r[stat.column], y=labels, orientation="h",
        marker=dict(color=[c["s2"] if p == highlight else colour for p in r.player], line=dict(width=0)),
        text=[fmt(v, stat.decimals) for v in r[stat.column]], textposition="outside", cliponaxis=False,
        textfont=dict(size=11, color=c["ink2"]),
        customdata=[f"<b>{row.player}</b> · {row.teams}<br><b>{stat.label}: {fmt(row[stat.column], stat.decimals)}</b>"
                    f"<br>{player_profile(row)}" for _, row in r.iterrows()],
        hovertemplate="%{customdata}<extra></extra>"))
    shapes, annotations = [], []
    if stat.reference is not None and np.isfinite(stat.reference):
        shapes.append(dict(type="line", x0=stat.reference, x1=stat.reference, xref="x", y0=0, y1=1, yref="paper",
                           line=dict(color=c["muted"], width=1, dash="dash"), layer="below"))
        annotations.append(dict(x=stat.reference, y=1, yref="paper", xanchor="left", yanchor="bottom", showarrow=False,
                                text=f"average {fmt(stat.reference, max(stat.decimals, 1))}", font=dict(size=11, color=c["muted"])))
    signed = stat.column in ("runs_above_average", "runs_saved")
    fig.update_layout(**_layout(
        c, bargap=0.3, shapes=shapes, annotations=annotations, height=max(360, 30 * len(r) + 90),
        xaxis=_axis(c, stat.label, zeroline=True, zerolinecolor=c["axis"], rangemode="normal" if signed else "tozero"),
        yaxis=dict(showgrid=False, showline=False, tickfont=dict(size=12, color=c["ink"]), automargin=True),
        margin=dict(l=10, r=52, t=24, b=10)))
    return fig


def _num(v, d=1):
    return fmt(v, d) if v is not None and not (isinstance(v, float) and np.isnan(v)) else "–"


def ordinal(n) -> str:
    """1st, 2nd, 3rd, 4th ... 11th, 12th, 13th, 21st."""
    n = int(n)
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _n(k, one: str, many: str | None = None) -> str:
    k = int(k)
    return f"{k} {one if k == 1 else (many or one + 's')}"


def player_profile(r) -> str:
    """Everything worth knowing about a player's row, for a hover box."""
    g = r.get if hasattr(r, "get") else (lambda k, default=None: getattr(r, k, default))
    if g("economy") is not None and g("wickets") is not None:  # bowling
        lines = [f"{int(g('innings'))} inns · {_n(g('wickets'), 'wicket')} · best {g('best')}",
                 f"average {_num(g('average'))} · economy {_num(g('economy'), 2)} · strike rate {_num(g('strike_rate'))}",
                 f"{_n(g('hauls'), 'four-for')} · runs saved {'+' if (g('runs_saved') or 0) > 0 else ''}{_num(g('runs_saved'))}"]
    elif g("strike_rate") is not None and g("runs") is not None:  # batting
        lines = [f"{int(g('innings'))} inns · {int(g('runs'))} runs · high score {g('high_score_text') or '–'}",
                 f"average {_num(g('average'))} · strike rate {_num(g('strike_rate'))}",
                 f"{_n(g('hundreds'), 'hundred')} · {_n(g('fifties'), 'fifty', 'fifties')} · {_n(g('fours'), 'four')} · {_n(g('sixes'), 'six', 'sixes')}",
                 f"runs above average {'+' if (g('runs_above_average') or 0) > 0 else ''}{_num(g('runs_above_average'))}"]
    else:  # fielding
        lines = [f"{_n(g('matches'), 'match', 'matches')} · {_n(g('catches'), 'catch', 'catches')} · {_n(g('stumpings'), 'stumping')}"]
    return "<br>".join(lines)


def dot_chart(pool: pd.DataFrame, ranked: pd.DataFrame, stat: Stat, best: bool, highlight: str = "",
              label_top: int = 5) -> go.Figure:
    """Every qualifying player as a dot; the ranked ones coloured; the average
    as a dashed line with the better side shaded."""
    c = colours()
    d = stat.dot
    x, y = pool[d.x].astype(float), pool[d.y].astype(float)
    xmax = max(1.0, float(x.max() if len(x) else 1)) * 1.08
    ymin, ymax = min(0.0, float(y.min() if len(y) else 0)), max(1.0, float(y.max() if len(y) else 1))
    pad = (ymax - ymin) * 0.1 or 1
    yr = [ymin - pad if ymin < 0 else 0, ymax + pad]
    slope = d.value
    if d.line == "slope" and not np.isfinite(slope):
        slope = float(y.sum() / x.sum()) if x.sum() else 0.0
    shapes, annotations = [], []
    if d.line == "flat":
        shapes += [dict(type="rect", xref="x", yref="y", x0=0, x1=xmax, y0=d.value, y1=yr[1], fillcolor=c["shade"],
                        line=dict(width=0), layer="below"),
                   dict(type="line", xref="paper", yref="y", x0=0, x1=1, y0=d.value, y1=d.value,
                        line=dict(color=c["muted"], width=1, dash="dash"), layer="below")]
        annotations.append(dict(x=1, xref="paper", y=d.value, xanchor="right", yanchor="bottom", showarrow=False,
                                text=d.line_label, font=dict(size=11, color=c["muted"])))
    else:
        y_end = slope * xmax
        far = yr[0] if d.better_below else yr[1] * 3
        shapes += [dict(type="path", path=f"M 0 0 L {xmax} {y_end} L {xmax} {far} L 0 {far} Z", xref="x", yref="y",
                        fillcolor=c["shade"], line=dict(width=0), layer="below"),
                   dict(type="line", xref="x", yref="y", x0=0, y0=0, x1=xmax, y1=y_end,
                        line=dict(color=c["muted"], width=1, dash="dash"), layer="below")]
        lx = xmax * 0.3
        annotations.append(dict(x=lx, y=slope * lx, xanchor="left", yanchor="top", xshift=6, showarrow=False,
                                text=d.line_label, font=dict(size=11, color=c["muted"])))
    top = set(ranked.player)
    colour = c["s1"] if best else c["neg"]
    # every dot's place in the full ranking of this stat, best first
    from ccstats.stats import rank as _rank
    place = {p: i + 1 for i, p in enumerate(_rank(pool, stat, best=True).player)}

    def trace(df, col, size, text=False):
        hover = []
        for _, r in df.iterrows():
            axes = "" if {d.x, d.y} <= {stat.column, "innings", "runs", "wickets", "matches", "catches"} else (
                f"<br>{d.x_label}: {fmt(r[d.x], 0 if float(r[d.x]).is_integer() else 1)} · "
                f"{d.y_label}: {fmt(r[d.y], 0 if float(r[d.y]).is_integer() else 1)}")
            hover.append(f"<b>{r.player}</b> · {r.teams}<br><b>{stat.label}: {fmt(r[stat.column], stat.decimals)}</b>"
                         f" · #{place.get(r.player, '–')} of {len(pool)}<br>{player_profile(r)}{axes}")
        return go.Scatter(x=df[d.x], y=df[d.y], mode="markers+text" if text else "markers",
                          text=list(df.player) if text else None, textposition="top center",
                          textfont=dict(size=11, color=c["ink"]),
                          marker=dict(size=size, color=col, line=dict(color=c["surface"], width=2)),
                          customdata=hover, hovertemplate="%{customdata}<extra></extra>")

    rest = pool[~pool.player.isin(top) & (pool.player != highlight)]
    ranked_dots = pool[pool.player.isin(top) & (pool.player != highlight)]
    hl = pool[pool.player == highlight]
    fig = go.Figure([trace(rest, c["dim"], 8), trace(ranked_dots, colour, 10)] + ([trace(hl, c["s2"], 13, True)] if len(hl) else []))
    # name the top few, each right next to its own dot
    named = ranked[ranked.player != highlight].head(label_top)
    annotations += label_annotations([(p[d.x], p[d.y], p.player) for _, p in named.iterrows()],
                                     list(zip(x, y)), (0, xmax), tuple(yr), c)
    # small counts (catches, 50s, hauls) get whole-number ticks; room at the top for stacked names
    ints = lambda s: len(s) and all(float(v).is_integer() for v in s)  # noqa: E731
    yextra = {"dtick": 1} if ints(y) and ymax <= 8 else {}
    xextra = {"dtick": 1} if ints(x) and xmax <= 9 else {}
    fig.update_layout(**_layout(c, height=460, shapes=shapes, annotations=annotations,
                                xaxis=_axis(c, d.x_label, range=[0, xmax], **xextra),
                                yaxis=_axis(c, d.y_label, range=yr, **yextra),
                                margin=dict(l=10, r=16, t=46, b=10)))
    return fig


def bars(labels, values, x_label: str, decimals: int = 0, colour: str | None = None, reference: float | None = None,
         reference_label: str = "average", notes=None, signed: bool = False, height: int | None = None,
         texts=None, x_range=None) -> go.Figure:
    """Horizontal bars for one measure, top of the list first. `notes` adds a
    hover line per bar (e.g. how many innings the figure rests on); `texts`
    replaces the number printed at the end of each bar."""
    c = colours()
    labels, values = list(labels)[::-1], list(values)[::-1]
    notes = list(notes)[::-1] if notes is not None else [""] * len(values)
    texts = list(texts)[::-1] if texts is not None else None
    col = colour or c["s1"]
    labels = [str(x) for x in labels]  # seasons like 2026 are labels, not numbers
    shown = [0 if v is None or (isinstance(v, float) and not np.isfinite(v)) else v for v in values]
    colours_ = [(c["pos"] if v >= 0 else c["neg"]) if signed else col for v in shown]
    fig = go.Figure(go.Bar(x=shown, y=labels, orientation="h", marker=dict(color=colours_, line=dict(width=0)),
                           text=texts or [("+" if signed and v is not None and v > 0 else "") + fmt(v, decimals) for v in values],
                           textposition="outside", cliponaxis=False, textfont=dict(size=11, color=c["ink2"]),
                           customdata=notes, hovertemplate="<b>%{y}</b>: %{text}<br>%{customdata}<extra></extra>"))
    shapes, annotations = [], []
    if reference is not None and np.isfinite(reference):
        shapes.append(dict(type="line", x0=reference, x1=reference, xref="x", y0=0, y1=1, yref="paper",
                           line=dict(color=c["muted"], width=1, dash="dash"), layer="below"))
        annotations.append(dict(x=reference, y=1, yref="paper", xanchor="left", yanchor="bottom", showarrow=False,
                                text=f"{reference_label} {fmt(reference, decimals or (0 if float(reference).is_integer() else 1))}",
                                font=dict(size=11, color=c["muted"])))
    # counts (wickets, dismissals, innings) never get half-way tick marks
    if signed and not x_range and shown:
        # room either side for the numbers, so a negative bar's text never runs into the names
        lo, hi = min(min(shown), 0), max(max(shown), 0)
        span = (hi - lo) or 1
        room = 0.55 if texts else 0.25  # longer labels ("+32% · 21.8 v 32.0") need more space
        x_range = [lo - span * (room + 0.1) if lo < 0 else 0, hi + span * room]
    counts = decimals == 0 and all(float(v).is_integer() for v in shown)
    small = counts and max((abs(v) for v in shown), default=0) <= 8
    fig.update_layout(**_layout(c, bargap=0.3, shapes=shapes, annotations=annotations,
                                height=height or max(220, 32 * len(values) + 80),
                                xaxis=_axis(c, x_label, zeroline=True, zerolinecolor=c["axis"],
                                            rangemode="normal" if signed else "tozero",
                                            **({"dtick": 1} if small else {"tickformat": ",d"} if counts else {}),
                                            **({"range": x_range} if x_range else {})),
                                yaxis=dict(type="category", showgrid=False, showline=False, tickfont=dict(size=12, color=c["ink"]),
                                           automargin=True),
                                margin=dict(l=10, r=52, t=24, b=10)))
    return fig


def paired_bars(labels, mine, other, mine_name: str, other_name: str, x_label: str, decimals: int = 1,
                notes=None) -> go.Figure:
    """Two bars per row: a player's figure next to the comparison (e.g. the
    average batter at that position). Top of the list first."""
    c = colours()
    labels = [str(x) for x in labels]
    notes = list(notes) if notes is not None else [""] * len(labels)
    fig = go.Figure()
    for vals, name, col in ((other, other_name, c["dim"]), (mine, mine_name, c["s1"])):
        vals = list(vals)
        fig.add_trace(go.Bar(y=labels, x=[0 if v is None or not np.isfinite(v) else v for v in vals], name=name,
                             orientation="h", marker=dict(color=col, line=dict(width=0)),
                             text=[fmt(v, decimals) for v in vals], textposition="outside", cliponaxis=False,
                             textfont=dict(size=11, color=c["ink2"]), customdata=notes,
                             hovertemplate=f"<b>%{{y}}</b> · {name}: %{{text}}<br>%{{customdata}}<extra></extra>"))
    fig.update_layout(**_layout(c, barmode="group", bargap=0.25, bargroupgap=0.05, showlegend=True,
                                legend=dict(orientation="h", y=1.12, x=0, traceorder="reversed", font=dict(color=c["ink"])),
                                height=max(220, 56 * len(labels) + 90),
                                xaxis=_axis(c, x_label, zeroline=True, zerolinecolor=c["axis"], rangemode="tozero"),
                                yaxis=dict(type="category", autorange="reversed", showgrid=False, showline=False,
                                           tickfont=dict(size=12, color=c["ink"]), automargin=True),
                                margin=dict(l=10, r=52, t=40, b=10)))
    return fig


def form_chart(runs, not_out, hover, window: int | None = None, y_label: str = "Runs") -> go.Figure:
    """Every innings as a bar; the average over the last `window` innings as a line;
    the average over all innings shown as a dashed line."""
    c = colours()
    runs, not_out = list(runs), list(not_out)
    if window is None:  # 10 innings for a long career, 5 for a short one
        window = 10 if len(runs) >= 20 else 5
    x = list(range(1, len(runs) + 1))
    outs = sum(1 for n in not_out if not n)
    career = sum(runs) / outs if outs else None
    roll = []
    for i in range(len(runs)):
        if i < window - 1:
            roll.append(None)
            continue
        w = slice(i - window + 1, i + 1)
        o = sum(1 for n in not_out[w] if not n)
        roll.append(sum(runs[w]) / o if o else None)
    fig = go.Figure([
        go.Bar(x=x, y=runs, marker=dict(color=c["dim"], line=dict(width=0)), customdata=list(hover),
               hovertemplate="Innings %{x}: %{customdata}<extra></extra>"),
        go.Scatter(x=x, y=roll, mode="lines", line=dict(color=c["s1"], width=2.5), connectgaps=False,
                   hovertemplate=f"Average over the last {window} innings: %{{y:.1f}}<extra></extra>"),
    ])
    shapes, annotations = [], []
    if career is not None:
        shapes.append(dict(type="line", x0=0, x1=1, xref="paper", y0=career, y1=career, yref="y",
                           line=dict(color=c["muted"], width=1, dash="dash"), layer="below"))
        annotations.append(dict(x=1, xref="paper", y=career, xanchor="right", yanchor="bottom", showarrow=False,
                                text=f"average {career:.1f}", font=dict(size=11, color=c["muted"])))
    fig.update_layout(**_layout(c, bargap=0.25, height=340, shapes=shapes, annotations=annotations,
                                xaxis=_axis(c, "Innings, in order", **({"dtick": 1} if len(runs) <= 15 else {})),
                                yaxis=_axis(c, y_label, **({"dtick": 1} if y_label == "Wickets" and max(runs, default=0) <= 8 else {}))))
    return fig


def wicket_timeline(innings: list[dict], par: list[tuple[int, float]] | None = None) -> go.Figure:
    """Score at each fall of wicket, one stepped line per innings.

    innings: [{"label": "Somerset 163/8", "fow": [(1, 6), (2, 16), ...], "total": 163, "all_out": False}]"""
    c = colours()
    palette = [c["s1"], c["s2"], "#1baf7a", "#e87ba4"]
    fig = go.Figure()
    top = 10
    for k, inn in enumerate(innings):
        xs = [0] + [w for w, _ in inn["fow"]]
        ys = [0] + [s for _, s in inn["fow"]]
        if not inn["all_out"]:
            xs.append(len(inn["fow"]) + 0.6)
            ys.append(inn["total"])
        top = max(top, max(ys))
        col = palette[k % len(palette)]
        hover = ["start"] + [f"{s} for {w}" for w, s in inn["fow"]] + ([f"{inn['total']} (end, not all out)"] if not inn["all_out"] else [])
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines+markers", name=inn["label"],
                                 line=dict(color=col, width=2.5, shape="vh"),
                                 marker=dict(size=8, color=col, line=dict(color=c["surface"], width=2)),
                                 customdata=hover, hovertemplate=f"<b>{inn['label']}</b><br>%{{customdata}}<extra></extra>"))
    if par:
        px = [0] + [w for w, _ in par]
        py = [0] + [s for _, s in par]
        top = max(top, max(py))
        fig.add_trace(go.Scatter(x=px, y=py, mode="lines", name="Par (typical score at each wicket)",
                                 line=dict(color=c["muted"], width=1.5, dash="dash", shape="vh"),
                                 hovertemplate="Par: %{y:.0f} when wicket %{x} falls<extra></extra>"))
    fig.update_layout(**_layout(c, height=420, showlegend=True,
                                legend=dict(orientation="h", y=1.1, x=0, font=dict(size=12, color=c["ink"])),
                                xaxis=_axis(c, "Wickets down", dtick=1, range=[-0.3, 10.8]),
                                yaxis=_axis(c, "Score", range=[0, top * 1.08]),
                                margin=dict(l=10, r=16, t=40, b=10)))
    return fig


def race_chart(race: pd.DataFrame, team: str) -> go.Figure:
    """League position after each match day: the chosen team in colour, the rest in grey."""
    c = colours()
    fig = go.Figure()
    n = int(race.position.max()) if len(race) else 1
    for t, g in sorted(race.groupby("team"), key=lambda x: x[0] == team):
        mine = t == team
        fig.add_trace(go.Scatter(
            x=g.date, y=g.position, mode="lines+markers" if mine else "lines", name=t,
            line=dict(color=c["s1"] if mine else c["dim"], width=3.5 if mine else 1.2, shape="hv"),
            marker=dict(size=6, color=c["s1"]), customdata=np.stack([g.points, g.played], axis=1),
            hovertemplate=f"<b>{t}</b><br>%{{x|%d %b}}: position %{{y}}<br>%{{customdata[0]}} points from "
                          "%{customdata[1]} games<extra></extra>"))
        last = g.iloc[-1]
        fig.add_annotation(x=last.date, y=last.position, text=t if mine else t.split()[0], showarrow=False, xanchor="left",
                           xshift=6, font=dict(size=11 if mine else 9, color=c["ink"] if mine else c["muted"]))
    fig.update_layout(**_layout(c, height=max(320, 26 * n + 80),
                                xaxis=_axis(c, "Match day"),
                                yaxis=_axis(c, "League position", autorange="reversed", dtick=1, range=[n + 0.5, 0.5]),
                                margin=dict(l=10, r=110, t=10, b=10)))
    return fig


def quadrant_chart(d: pd.DataFrame, x: str, y: str, x_label: str, y_label: str, x_ref: float, y_ref: float,
                   corners: tuple[str, str, str, str], label_top: int = 10, highlight: list[str] | None = None,
                   x_better_low: bool = False, y_better_low: bool = False) -> go.Figure:
    """Every player as a dot, split into four by the average lines. `corners`: names for
    top-right, top-left, bottom-right, bottom-left (in that order)."""
    c = colours()
    highlight = highlight or []
    xs, ys = d[x].astype(float), d[y].astype(float)
    good = ((xs <= x_ref) if x_better_low else (xs >= x_ref)) & ((ys <= y_ref) if y_better_low else (ys >= y_ref))
    col = [c["s2"] if p in highlight else (c["s1"] if g else c["dim"]) for p, g in zip(d.player, good)]
    fig = go.Figure(go.Scatter(x=xs, y=ys, mode="markers", marker=dict(size=9, color=col, line=dict(width=0)),
                               text=d.player, customdata=d.get("style", d.player),
                               hovertemplate="<b>%{text}</b><br>" + x_label + ": %{x:.1f}<br>" + y_label +
                                             ": %{y:.1f}<br>%{customdata}<extra></extra>"))
    x0, x1 = float(min(xs.min(), x_ref)), float(max(xs.max(), x_ref))
    y0, y1 = float(min(ys.min(), y_ref)), float(max(ys.max(), y_ref))
    px_, py_ = (x1 - x0) * 0.08 or 1, (y1 - y0) * 0.08 or 1
    xr, yr = (x0 - px_, x1 + px_), (y0 - py_, y1 + py_)
    shapes = [dict(type="line", x0=x_ref, x1=x_ref, y0=yr[0], y1=yr[1], line=dict(color=c["muted"], dash="dash", width=1)),
              dict(type="line", x0=xr[0], x1=xr[1], y0=y_ref, y1=y_ref, line=dict(color=c["muted"], dash="dash", width=1))]
    ann = []
    for (ax, ay, xa, ya), text in zip(((xr[1], yr[1], "right", "top"), (xr[0], yr[1], "left", "top"),
                                       (xr[1], yr[0], "right", "bottom"), (xr[0], yr[0], "left", "bottom")), corners):
        ann.append(dict(x=ax, y=ay, xanchor=xa, yanchor=ya, text=f"<b>{text}</b>", showarrow=False,
                        font=dict(size=11, color=c["muted"])))
    named = d.assign(_k=(xs - x_ref).abs() / ((x1 - x0) or 1) + (ys - y_ref).abs() / ((y1 - y0) or 1))
    named = pd.concat([named[named.player.isin(highlight)], named.sort_values("_k", ascending=False).head(label_top)]) \
        .drop_duplicates("player")
    ann += label_annotations([(getattr(r, x), getattr(r, y), r.player) for r in named.itertuples()],
                             list(zip(xs, ys)), xr, yr, c)
    fig.update_layout(**_layout(c, height=470, shapes=shapes, annotations=ann,
                                xaxis=_axis(c, x_label, range=list(xr)), yaxis=_axis(c, y_label, range=list(yr))))
    return fig


def funnel_chart(d: pd.DataFrame) -> go.Figure:
    """% of innings reaching each mark: the format's key marks in colour, the rest grey; dots for every batter here."""
    c = colours()
    x = [f"{m}+" for m in d.mark]
    col = [c["s1"] if h else c["dim"] for h in d.highlight]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=x, y=d.pct, marker=dict(color=col, line=dict(width=0)), name="This player",
                         text=[f"{v:.0f}%" if np.isfinite(v) else "" for v in d.pct], textposition="outside",
                         cliponaxis=False, textfont=dict(size=11, color=c["ink2"]),
                         customdata=np.stack([d.innings, d.from_prev.fillna(-1)], axis=1),
                         hovertemplate="<b>%{x}</b>: %{y:.0f}% of innings (%{customdata[0]})<extra></extra>"))
    fig.add_trace(go.Scatter(x=x, y=d.all_pct, mode="markers+lines", name="Every batter here",
                             line=dict(color=c["muted"], width=1, dash="dot"), marker=dict(size=7, color=c["muted"]),
                             hovertemplate="%{x}: every batter %{y:.0f}%<extra></extra>"))
    ann = []
    for xi, r in zip(x, d.itertuples()):
        if r.highlight and r.key_from and np.isfinite(r.from_key):
            ann.append(dict(x=xi, y=(r.pct if np.isfinite(r.pct) else 0), yshift=26, showarrow=False,
                            text=f"<b>{r.from_key:.0f}%</b> of {r.key_from}s", font=dict(size=10.5, color=c["s1"])))
    top = float(np.nanmax([d.pct.max(), d.all_pct.max(), 10]))
    fig.update_layout(**_layout(c, height=320, annotations=ann, showlegend=True, bargap=0.25,
                                legend=dict(orientation="h", y=1.14, x=0, font=dict(color=c["ink"])),
                                xaxis=_axis(c, "Score reached", type="category"),
                                yaxis=_axis(c, "% of innings", range=[0, top * 1.3]),
                                margin=dict(l=10, r=16, t=40, b=10)))
    return fig


def impact_chart(d: pd.DataFrame) -> go.Figure:
    """One bar per match: blue in wins, red otherwise; the dashed line is their average."""
    c = colours()
    x = list(range(1, len(d) + 1))
    fig = go.Figure(go.Bar(x=x, y=d.impact, marker=dict(color=[c["pos"] if w else c["neg"] for w in d.won], line=dict(width=0)),
                           customdata=[f"{r.date:%d %b %Y} v {r.opponent}: {int(r.runs)} runs, {int(r.wickets)} wkts"
                                       f"{', ' + str(int(r.dismissals)) + ' ct/st' if r.dismissals else ''}"
                                       for r in d.itertuples()],
                           hovertemplate="<b>%{y:.0f}</b> · %{customdata}<extra></extra>"))
    avg = float(d.impact.mean()) if len(d) else 0
    fig.add_hline(y=avg, line=dict(color=c["muted"], dash="dash", width=1))
    fig.update_layout(**_layout(c, height=280, bargap=0.2, xaxis=_axis(c, "Match (oldest first)"),
                                yaxis=_axis(c, "Match impact"), margin=dict(l=10, r=16, t=10, b=10)))
    return fig


def rank_chart(d: pd.DataFrame) -> go.Figure:
    c = colours()
    fig = go.Figure()
    for col, name, colour in (("runs_rank", "Rank by runs", c["s1"]), ("wickets_rank", "Rank by wickets", c["s2"])):
        if d[col].notna().any():
            fig.add_trace(go.Scatter(x=[str(s) for s in d.season], y=d[col], mode="lines+markers+text", name=name,
                                     text=[f"{int(v)}" if np.isfinite(v) else "" for v in d[col]], textposition="top center",
                                     line=dict(color=colour, width=2.5), marker=dict(size=9, color=colour)))
    arr = d[["runs_rank", "wickets_rank"]].to_numpy(dtype=float) if len(d) else np.array([1.0])
    top = float(np.nanmax(arr)) if np.isfinite(arr).any() else 1.0
    fig.update_layout(**_layout(c, height=260, showlegend=True, legend=dict(orientation="h", y=1.15, x=0),
                                xaxis=_axis(c, "Season", type="category"),
                                yaxis=_axis(c, "Rank in the section (1 = top)", autorange="reversed",
                                            range=[top + 1, 0.5] if np.isfinite(top) else None),
                                margin=dict(l=10, r=16, t=40, b=10)))
    return fig


def win_line_points(line: pd.DataFrame, result: str = "") -> pd.DataFrame:
    """The points the win-chance chart draws: the line as worked out, where a spot no
    earlier game reached keeps the point before it (said so in its hover), and, once
    the match is over, a last point at the result (100% for the winner)."""
    d = line[["label", "W", "D", "L", "T", "n"]].copy().reset_index(drop=True)
    blank = d.W.isna()
    d["note"] = [f"from {int(n)} similar game{'s' if int(n) != 1 else ''}" for n in d.n.fillna(0)]
    d.loc[blank, "note"] = "no earlier game reached this spot: kept from the point before"
    d[["W", "D", "L", "T"]] = d[["W", "D", "L", "T"]].ffill()
    d.loc[blank & d.W.isna(), "note"] = "no earlier game reached this spot"
    d[["W", "D", "L", "T"]] = d[["W", "D", "L", "T"]].bfill()
    out = line.attrs.get("outcome")
    if out in ("W", "D", "L", "T") and len(d):
        end = {k: 100.0 if k == out else 0.0 for k in "WDLT"}
        d = pd.concat([d, pd.DataFrame([dict(label=f"Result: {result}" if result else "Result", n=np.nan,
                                            note="the result", **end)])], ignore_index=True)
    return d


def win_chance_chart(line: pd.DataFrame, team1: str, team2: str, multi: bool, result: str = "") -> go.Figure:
    """The side batting first's chance at the start of each innings and after every wicket,
    ending at the result.  Multi-day: stacked won / drawn / lost (a tie counts with the draw)."""
    c = colours()
    pts = win_line_points(line, result)
    x = list(range(len(pts)))
    fig = go.Figure()
    if multi:
        pts = pts.assign(D=pts.D + pts["T"].fillna(0))
        for col, name, colour in (("W", f"{team1} win", c["s1"]), ("D", "Draw", c["dim"]), ("L", f"{team2} win", c["s2"])):
            fig.add_trace(go.Scatter(x=x, y=pts[col], mode="lines", name=name, stackgroup="one",
                                     line=dict(width=0.5, color=colour), fillcolor=colour,
                                     customdata=np.stack([pts.label, pts.note], axis=1),
                                     hovertemplate="%{customdata[0]}<br>" + name + ": %{y:.0f}% (%{customdata[1]})"
                                                   "<extra></extra>"))
    else:
        fig.add_trace(go.Scatter(x=x, y=pts.W, mode="lines+markers", name=f"{team1} win",
                                 line=dict(color=c["s1"], width=2.5), marker=dict(size=6),
                                 customdata=np.stack([pts.label, pts.note], axis=1),
                                 hovertemplate="%{customdata[0]}<br><b>%{y:.0f}%</b> for " + team1 +
                                               " (%{customdata[1]})<extra></extra>"))
        fig.add_hline(y=50, line=dict(color=c["muted"], dash="dash", width=1))
    # mark where each innings starts
    for i, (lab, no) in enumerate(zip(line.label, line.innings_no)):
        if lab.startswith("Start of innings") and i:
            fig.add_vline(x=i, line=dict(color=c["axis"], width=1, dash="dot"))
    fig.update_layout(**_layout(c, height=300, showlegend=True, legend=dict(orientation="h", y=1.15, x=0),
                                xaxis=_axis(c, "Each wicket, in order (dotted lines: a new innings)", showticklabels=False),
                                yaxis=_axis(c, f"% chance ({team1} batted first)", range=[0, 100]),
                                margin=dict(l=10, r=16, t=40, b=10)))
    return fig


def record_steps_chart(steps: pd.DataFrame, y: list[float], unit: str) -> go.Figure:
    """A record's history: a step up (or down, for lowest totals) each time it was beaten."""
    c = colours()
    fig = go.Figure()
    xs = list(steps.date) + ([steps.until.iloc[-1] if pd.notna(steps.until.iloc[-1]) else steps.date.max()] if len(steps) else [])
    ys = list(y) + ([y[-1]] if len(y) else [])
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=c["s1"], width=2.5, shape="hv"), hoverinfo="skip",
                             showlegend=False))
    fig.add_trace(go.Scatter(x=steps.date, y=y, mode="markers+text", marker=dict(size=10, color=c["s1"]),
                             # label where the number moves (and the record now); hover shows every step
                             text=[f"{v}" if i == len(y) - 1 or i == 0 or y[i] != y[i - 1] else ""
                                   for i, v in enumerate(steps.value)],
                             textposition="top left", textfont=dict(size=11),
                             customdata=np.stack([steps.holder, steps.value, steps.against.fillna("")], axis=1),
                             hovertemplate="<b>%{customdata[0]}</b> %{customdata[1]}<br>v %{customdata[2]}<br>%{x|%d %b %Y}"
                                           "<extra></extra>", showlegend=False))
    lo, hi = (min(y), max(y)) if len(y) else (0, 1)
    pad = max((hi - lo) * 0.25, 1)
    fig.update_layout(**_layout(c, height=300, xaxis=_axis(c, "Date"), yaxis=_axis(c, unit.capitalize(),
                                                                                    range=[lo - pad, hi + pad]),
                                margin=dict(l=10, r=16, t=20, b=10)))
    return fig
