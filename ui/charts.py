"""Plotly figures shared by the pages: one stat per chart, readable in both themes."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from ccstats.stats import Stat

from .theme import colours

FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'
CONFIG = {"displayModeBar": False}


def _axis(c, title, **extra):
    base = dict(title=dict(text=title, font=dict(size=12, color=c["ink2"]), standoff=8), gridcolor=c["grid"],
                zeroline=False, linecolor=c["axis"], showline=True, tickfont=dict(size=11, color=c["muted"]),
                automargin=True)
    base.update(extra)
    return base


def _layout(c, **extra):
    base = dict(paper_bgcolor=c["surface"], plot_bgcolor=c["surface"], font=dict(family=FONT, color=c["ink"], size=12),
                margin=dict(l=10, r=16, t=10, b=10), showlegend=False,
                hoverlabel=dict(bgcolor=c["surface"], bordercolor=c["axis"], font=dict(family=FONT, color=c["ink"], size=12)))
    base.update(extra)
    return base


def fmt(v, decimals: int) -> str:
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return "–"
    return f"{v:.{decimals}f}" if decimals else f"{int(round(v))}"


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
        customdata=[f"<b>{p}</b> · {t}" for p, t in zip(r.player, r.teams)],
        hovertemplate="%{customdata}<br>" + stat.label + ": %{text}<extra></extra>"))
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

    def trace(df, col, size, text=False):
        hover = [f"<b>{p}</b> · {t}<br>{d.x_label}: {fmt(a, 0 if float(a).is_integer() else 1)}"
                 f"<br>{d.y_label}: {fmt(b, 0 if float(b).is_integer() else 1)}<br>{stat.label}: {fmt(v, stat.decimals)}"
                 for p, t, a, b, v in zip(df.player, df.teams, df[d.x], df[d.y], df[stat.column])]
        return go.Scatter(x=df[d.x], y=df[d.y], mode="markers+text" if text else "markers",
                          text=list(df.player) if text else None, textposition="top center",
                          textfont=dict(size=11, color=c["ink"]),
                          marker=dict(size=size, color=col, line=dict(color=c["surface"], width=2)),
                          customdata=hover, hovertemplate="%{customdata}<extra></extra>")

    rest = pool[~pool.player.isin(top) & (pool.player != highlight)]
    ranked_dots = pool[pool.player.isin(top) & (pool.player != highlight)]
    hl = pool[pool.player == highlight]
    fig = go.Figure([trace(rest, c["dim"], 8), trace(ranked_dots, colour, 10)] + ([trace(hl, c["s2"], 13, True)] if len(hl) else []))
    # name the top few; stack names whose dots sit on top of each other
    placed: list[tuple[float, float, int]] = []
    for _, p in ranked[ranked.player != highlight].head(label_top).iterrows():
        nx, ny = p[d.x] / xmax, (p[d.y] - yr[0]) / (yr[1] - yr[0])
        shift = 13
        for px, py, ps in placed:
            if abs(px - nx) < 0.08 and abs(py - ny) < 0.04:
                shift = max(shift, ps + 16)
        placed.append((nx, ny, shift))
        annotations.append(dict(x=p[d.x], y=p[d.y], text=p.player, showarrow=False, yshift=shift,
                                font=dict(size=11, color=c["ink2"])))
    fig.update_layout(**_layout(c, height=460, shapes=shapes, annotations=annotations,
                                xaxis=_axis(c, d.x_label, range=[0, xmax]), yaxis=_axis(c, d.y_label, range=yr)))
    return fig


def bars(labels, values, x_label: str, decimals: int = 0, colour: str | None = None, reference: float | None = None,
         reference_label: str = "average", notes=None, signed: bool = False, height: int | None = None) -> go.Figure:
    """Horizontal bars for one measure, top of the list first. `notes` adds a
    hover line per bar (e.g. how many innings the figure rests on)."""
    c = colours()
    labels, values = list(labels)[::-1], list(values)[::-1]
    notes = list(notes)[::-1] if notes is not None else [""] * len(values)
    col = colour or c["s1"]
    colours_ = [(c["pos"] if v >= 0 else c["neg"]) if signed else col for v in values]
    fig = go.Figure(go.Bar(x=values, y=labels, orientation="h", marker=dict(color=colours_, line=dict(width=0)),
                           text=[("+" if signed and v > 0 else "") + fmt(v, decimals) for v in values],
                           textposition="outside", cliponaxis=False, textfont=dict(size=11, color=c["ink2"]),
                           customdata=notes, hovertemplate="<b>%{y}</b>: %{text}<br>%{customdata}<extra></extra>"))
    shapes, annotations = [], []
    if reference is not None and np.isfinite(reference):
        shapes.append(dict(type="line", x0=reference, x1=reference, xref="x", y0=0, y1=1, yref="paper",
                           line=dict(color=c["muted"], width=1, dash="dash"), layer="below"))
        annotations.append(dict(x=reference, y=1, yref="paper", xanchor="left", yanchor="bottom", showarrow=False,
                                text=f"{reference_label} {fmt(reference, max(decimals, 1))}", font=dict(size=11, color=c["muted"])))
    fig.update_layout(**_layout(c, bargap=0.3, shapes=shapes, annotations=annotations,
                                height=height or max(220, 32 * len(values) + 80),
                                xaxis=_axis(c, x_label, zeroline=True, zerolinecolor=c["axis"],
                                            rangemode="normal" if signed else "tozero"),
                                yaxis=dict(showgrid=False, showline=False, tickfont=dict(size=12, color=c["ink"]), automargin=True),
                                margin=dict(l=10, r=52, t=24, b=10)))
    return fig


def form_chart(runs, not_out, hover, window: int = 10, y_label: str = "Runs") -> go.Figure:
    """Every innings as a bar; the average over the last `window` innings as a line;
    the average over all innings shown as a dashed line."""
    c = colours()
    runs, not_out = list(runs), list(not_out)
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
                                xaxis=_axis(c, "Innings, in order"), yaxis=_axis(c, y_label)))
    return fig


def wicket_timeline(innings: list[dict]) -> go.Figure:
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
    fig.update_layout(**_layout(c, height=420, showlegend=True,
                                legend=dict(orientation="h", y=1.1, x=0, font=dict(size=12, color=c["ink"])),
                                xaxis=_axis(c, "Wickets down", dtick=1, range=[-0.3, 10.8]),
                                yaxis=_axis(c, "Score", range=[0, top * 1.08]),
                                margin=dict(l=10, r=16, t=40, b=10)))
    return fig
