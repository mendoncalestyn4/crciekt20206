"""Check a plotly figure (its JSON spec) for misplaced or wrong marks:
- every dot / bar end / line point is inside the axis range that's shown (nothing cut off)
- the number printed on a bar equals the bar's length
- a name label with a (hidden) pointer sits exactly on a dot of the chart
- no two bars of one trace share a category (they'd sit on top of each other)
- stacked % areas add up to 100 at every point
- no NaN / inf among the plotted values of bars and dots
- x / y / text arrays line up
"""
from __future__ import annotations

import base64
import json
import math
import re

import numpy as np
import pandas as pd

DT = {"f8": "<f8", "f4": "<f4", "i1": "i1", "i2": "<i2", "i4": "<i4", "u1": "u1", "u2": "<u2", "u4": "<u4", "i8": "<i8",
      "u8": "<u8"}


def arr(v):
    """A plotly data array (plain list or typed {'dtype','bdata'}) as a python list."""
    if v is None:
        return None
    if isinstance(v, dict) and "bdata" in v:
        a = np.frombuffer(base64.b64decode(v["bdata"]), dtype=DT[v["dtype"]])
        if "shape" in v:
            shp = [int(s) for s in str(v["shape"]).split(",")]
            a = a.reshape(shp)
        return a.tolist()
    if isinstance(v, (list, tuple)):
        return list(v)
    return None


def num(v):
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    return None


def to_axis_value(v, kind):
    """A data value in the axis' own units (dates as ms since epoch, log as log10)."""
    if v is None:
        return None
    if kind == "date":
        try:
            return pd.Timestamp(v).value / 1e6
        except Exception:  # noqa: BLE001
            return None
    x = num(v)
    if x is None:
        try:
            x = float(v)
        except (TypeError, ValueError):
            return None
    if kind == "log":
        return math.log10(x) if x > 0 else -math.inf
    return x


def axis_kind(layout, ref, values):
    ax = layout.get(ref, {}) or {}
    t = ax.get("type")
    if t in ("date", "log", "category", "linear"):
        return t
    vals = [v for v in (values or []) if v is not None]
    if vals and all(isinstance(v, str) for v in vals):
        if all(re.match(r"^\d{4}-\d{2}-\d{2}", v) for v in vals):
            return "date"
        try:
            [float(v) for v in vals]
            return "linear"
        except ValueError:
            return "category"
    return "linear"


NUM_RE = re.compile(r"^[+\-−]?\d[\d,]*(\.\d+)?%?$")


def parse_text_number(t):
    """'54%', '+12', '1,234', '7.5' -> (value, decimals); anything else -> None."""
    if not isinstance(t, str):
        return None
    s = t.strip().replace("−", "-")
    s = re.sub(r"<[^>]+>", "", s)
    if not NUM_RE.match(s):
        return None
    s2 = s.rstrip("%").replace(",", "")
    dec = len(s2.split(".")[1]) if "." in s2 else 0
    try:
        return float(s2), dec
    except ValueError:
        return None


def check_fig(spec: str | dict) -> list[str]:
    fig = json.loads(spec) if isinstance(spec, str) else spec
    layout = fig.get("layout", {}) or {}
    out = []
    marker_points = []  # (x, y) of every dot, for label checks
    stacks: dict = {}
    for k, tr in enumerate(fig.get("data", [])):
        typ = tr.get("type", "scatter")
        name = tr.get("name") or f"trace {k}"
        x, y = arr(tr.get("x")), arr(tr.get("y"))
        if typ not in ("bar", "scatter", "scattergl"):
            continue
        xref = "xaxis" + (tr.get("xaxis", "x")[1:] or "")
        yref = "yaxis" + (tr.get("yaxis", "y")[1:] or "")
        n = max(len(x or []), len(y or []))
        if x is not None and y is not None and len(x) != len(y):
            out.append(f"{name}: {len(x)} x values but {len(y)} y values")
            continue
        text = arr(tr.get("text"))
        if isinstance(tr.get("text"), str):
            text = None
        if text is not None and len(text) != n and len(text) > 0:
            out.append(f"{name}: {len(text)} labels for {n} points")
        xk, yk = axis_kind(layout, xref, x), axis_kind(layout, yref, y)
        if typ == "bar":
            horiz = tr.get("orientation") == "h"
            cats, vals = (y, x) if horiz else (x, y)
            cat_kind, val_kind = (yk, xk) if horiz else (xk, yk)
            if cats is not None and cat_kind == "category":
                seen = [str(c) for c in cats]
                dup = {c for c in seen if seen.count(c) > 1}
                if dup:
                    out.append(f"{name}: two bars on the same row {sorted(dup)[:3]}")
            for i, v in enumerate(vals or []):
                fv = num(v)
                if fv is None or not math.isfinite(fv):
                    out.append(f"{name}: bar {i} has no value ({v!r})")
                    continue
                if text is not None and i < len(text):
                    p = parse_text_number(text[i])
                    if p is not None:
                        pv, dec = p
                        tol = 0.5 * 10 ** (-dec) + 1e-9
                        if str(text[i]).strip().endswith("%") and abs(fv) <= 1.0001 and abs(pv) > 1.5:
                            fv = fv * 100  # a fraction shown as a percentage
                        if abs(pv - fv) > tol and abs(pv - fv) > abs(fv) * 1e-9:
                            out.append(f"{name}: bar {i} ({cats[i] if cats else i}) is {fv:g} long but says {text[i]!r}")
            # the value axis must show every bar end
            ax = layout.get("xaxis" if horiz else "yaxis", {}) or {}
            rng = ax.get("range")
            if rng and len(rng) == 2 and all(r is not None for r in rng) and val_kind != "category":
                lo, hi = sorted(to_axis_value(r, val_kind) for r in rng)
                span = (hi - lo) or 1
                for i, v in enumerate(vals or []):
                    fv = to_axis_value(v, val_kind)
                    if fv is not None and math.isfinite(fv) and not (lo - span * 1e-6 <= fv <= hi + span * 1e-6):
                        if layout.get("barmode") != "stack":
                            out.append(f"{name}: bar {i} ({v}) is outside the axis {rng}")
            continue
        # scatter
        mode = tr.get("mode", "markers+lines")
        has_markers = "markers" in mode or "text" in mode
        lines = "lines" in mode
        for i in range(n):
            xv = x[i] if x is not None else i
            yv = y[i] if y is not None else i
            if yv is None or (isinstance(yv, float) and not math.isfinite(yv)) or xv is None:
                if has_markers and not lines:
                    out.append(f"{name}: dot {i} has no position ({xv!r}, {yv!r})")
                continue
            if has_markers:
                marker_points.append((xk, yk, xv, yv))
        if tr.get("stackgroup"):
            for i in range(n):
                key = (tr["stackgroup"], str(x[i] if x is not None else i))
                stacks[key] = stacks.get(key, 0.0) + (num(y[i]) or 0.0)
        # range check for every point
        for ref, vals, kind in ((xref, x, xk), (yref, y, yk)):
            ax = layout.get(ref, {}) or {}
            rng = ax.get("range")
            if not rng or len(rng) != 2 or kind == "category" or vals is None or any(r is None for r in rng):
                continue
            lo, hi = sorted(to_axis_value(r, kind) for r in rng)
            span = (hi - lo) or 1
            for i, v in enumerate(vals):
                fv = to_axis_value(v, kind)
                if fv is None or not math.isfinite(fv):
                    continue
                if tr.get("stackgroup"):
                    continue
                if not (lo - span * 1e-6 <= fv <= hi + span * 1e-6):
                    out.append(f"{name}: point {i} ({v}) is outside the {ref} range {rng}")
                    break
    for key, total in stacks.items():
        if abs(total - 100) > 0.6 and total > 0:
            out.append(f"stacked areas add to {total:.2f}, not 100, at {key[1]}")
    # labels joined to dots must sit on a dot
    for a in layout.get("annotations", []) or []:
        if a.get("showarrow") and a.get("axref") == "pixel" and a.get("xref", "x") == "x" and a.get("yref", "y") == "y":
            ax_, ay_ = a.get("x"), a.get("y")
            hit = False
            for xk, yk, px, py in marker_points:
                vx, vy = to_axis_value(px, xk) if xk != "category" else px, to_axis_value(py, yk) if yk != "category" else py
                tx, ty = to_axis_value(ax_, xk) if xk != "category" else ax_, to_axis_value(ay_, yk) if yk != "category" else ay_
                if xk == "category":
                    okx = str(vx) == str(tx)
                else:
                    okx = vx is not None and tx is not None and abs(vx - tx) <= 1e-6 * max(1, abs(vx))
                if yk == "category":
                    oky = str(vy) == str(ty)
                else:
                    oky = vy is not None and ty is not None and abs(vy - ty) <= 1e-6 * max(1, abs(vy))
                if okx and oky:
                    hit = True
                    break
            if not hit:
                out.append(f"label {a.get('text')!r} at ({ax_}, {ay_}) isn't on any dot")
        # a label in data coordinates must be on the chart
        if not a.get("showarrow") and a.get("xref", "x") == "x" and a.get("yref", "y") == "y":
            for ref, val in (("xaxis", a.get("x")), ("yaxis", a.get("y"))):
                rng = (layout.get(ref, {}) or {}).get("range")
                kind = (layout.get(ref, {}) or {}).get("type", "linear")
                if rng and val is not None and kind not in ("category",) and all(r is not None for r in rng):
                    lo, hi = sorted(to_axis_value(r, kind) for r in rng)
                    fv = to_axis_value(val, kind)
                    span = (hi - lo) or 1
                    if fv is not None and not (lo - span * 0.02 <= fv <= hi + span * 0.02):
                        out.append(f"note {a.get('text')!r} at {ref[0]}={val} is off the chart {rng}")
    return out


def title_of(spec: str | dict) -> str:
    fig = json.loads(spec) if isinstance(spec, str) else spec
    lay = fig.get("layout", {})
    xt = ((lay.get("xaxis") or {}).get("title") or {}).get("text", "")
    yt = ((lay.get("yaxis") or {}).get("title") or {}).get("text", "")
    return f"[{xt} | {yt}]"
