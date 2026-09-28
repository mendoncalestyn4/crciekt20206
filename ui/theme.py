"""Colours, CSS and small HTML helpers shared by every page."""

from __future__ import annotations

import streamlit as st

# Validated chart palette (light / dark steps of the same hues).
LIGHT = dict(surface="#fcfcfb", page="#f9f9f7", ink="#0b0b0b", ink2="#52514e", muted="#898781", grid="#e1e0d9",
             axis="#c3c2b7", s1="#2a78d6", s2="#eb6834", pos="#2a78d6", neg="#e34948", mid="#f0efec", dim="#c9c8c1",
             shade="rgba(42,120,214,0.08)", good="#006300", chip="#eef3fb")
DARK = dict(surface="#1a1a19", page="#0d0d0d", ink="#ffffff", ink2="#c3c2b7", muted="#898781", grid="#2c2c2a",
            axis="#383835", s1="#3987e5", s2="#d95926", pos="#3987e5", neg="#e66767", mid="#383835", dim="#4a4945",
            shade="rgba(57,135,229,0.13)", good="#0ca30c", chip="#1c2a3d")


def colours() -> dict:
    try:
        dark = st.context.theme.type == "dark"
    except Exception:
        dark = False
    return DARK if dark else LIGHT


CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700&display=swap');
.block-container { padding-top: 2.2rem; max-width: 1280px; }
h1, h2, h3 { letter-spacing: .01em; }
.eyebrow { font-size: 12px; letter-spacing: .08em; text-transform: uppercase; opacity: .7; font-weight: 600; margin-bottom: -6px; }
.lede { font-size: 15px; opacity: .8; max-width: 72ch; }
.explain { list-style: none; padding: 0; margin: 4px 0 0; display: grid; gap: 6px; font-size: 13px; }
.explain li { display: grid; grid-template-columns: 18px 1fr; gap: 8px; align-items: start; opacity: .92; }
.explain .sw { width: 14px; height: 14px; border-radius: 3px; margin-top: 3px; border: 1px solid VAR_AXIS; }
.explain .sw.shade { background: VAR_SHADE; border-color: VAR_S1; }
.explain .sw.line { border: 0; border-top: 2px dashed VAR_MUTED; height: 0; margin-top: 10px; border-radius: 0; }
.explain .sw.dot { border-radius: 50%; border: 0; background: VAR_S1; }
.explain .sw.dot.neg { background: VAR_NEG; }
.explain .sw.dot.orange { background: VAR_S2; }
.statdef { font-size: 14.5px; }
.statdef .note { opacity: .65; font-size: 13px; }
.chip { display: inline-flex; align-items: center; gap: 6px; padding: 2px 10px; border-radius: 999px; font-size: 12px; font-weight: 600; }
.chip.demo { border: 1px dashed VAR_MUTED; }
.kpi { border: 1px solid VAR_GRID; border-radius: 12px; padding: 12px 14px; background: VAR_SURFACE; }
.kpi span { display: block; font-size: 11px; letter-spacing: .07em; text-transform: uppercase; opacity: .65; font-weight: 600; }
.kpi strong { font-size: 26px; font-variant-numeric: tabular-nums; }
.side-status { font-size: 13px; line-height: 1.4; }
.side-status b { font-size: 14px; }
</style>
"""


def inject_css() -> None:
    c = colours()
    css = (CSS.replace("VAR_AXIS", c["axis"]).replace("VAR_SHADE", c["shade"]).replace("VAR_S1", c["s1"])
           .replace("VAR_S2", c["s2"]).replace("VAR_NEG", c["neg"]).replace("VAR_MUTED", c["muted"])
           .replace("VAR_GRID", c["grid"]).replace("VAR_SURFACE", c["surface"]))
    st.markdown(css, unsafe_allow_html=True)


def page_header(eyebrow: str, title: str, lede: str = "") -> None:
    st.markdown(f'<div class="eyebrow">{eyebrow}</div>', unsafe_allow_html=True)
    st.title(title, anchor=False)
    if lede:
        st.markdown(f'<p class="lede">{lede}</p>', unsafe_allow_html=True)


def kpis(items: list[tuple[str, str]]) -> None:
    cols = st.columns(len(items))
    for col, (label, value) in zip(cols, items):
        col.markdown(f'<div class="kpi"><span>{label}</span><strong>{value}</strong></div>', unsafe_allow_html=True)


def explain_list(rows: list[tuple[str, str]]) -> None:
    """rows: (swatch class, html text)."""
    items = "".join(f'<li><span class="sw {sw}"></span><span>{txt}</span></li>' for sw, txt in rows)
    st.markdown(f'<ul class="explain">{items}</ul>', unsafe_allow_html=True)
