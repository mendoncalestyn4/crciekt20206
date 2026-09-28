"""The look: a night match under floodlights (dark) and a day match (light).

Chart data colours come from a colour-blind-safe palette (blue / orange,
blue-red for above/below average); the gold and pitch green are only used
for the page itself, never to mean something in a chart.
"""

from __future__ import annotations

import streamlit as st

NIGHT = dict(
    surface="#101b2f", page="#0a1322", ink="#eef2f8", ink2="#b9c4d6", muted="#7f8ca3", grid="#1f2c45",
    axis="#2d3d5c", s1="#3987e5", s2="#e0662f", pos="#3987e5", neg="#e66767", mid="#2a3550", dim="#3a4863",
    shade="rgba(57,135,229,0.14)", good="#3ccf7a", chip="#1a2b4a", accent="#f2b632", accent_soft="rgba(242,182,50,0.14)",
    stripe_a="#0a1322", stripe_b="#0c1628", glow="0 0 18px rgba(242,182,50,0.35)", panel="#101b2f", panel_edge="#22314d",
    side_ink="#e9eef6",
)
DAY = dict(
    surface="#fbfcf8", page="#f3f5ef", ink="#0f1b2d", ink2="#44516a", muted="#7c8697", grid="#e2e6da",
    axis="#c5ccba", s1="#2a78d6", s2="#eb6834", pos="#2a78d6", neg="#e34948", mid="#eceee7", dim="#c9cdc2",
    shade="rgba(42,120,214,0.08)", good="#1d6b45", chip="#e3efe7", accent="#1d6b45", accent_soft="rgba(29,107,69,0.10)",
    stripe_a="#f3f5ef", stripe_b="#eef1e8", glow="none", panel="#fbfcf8", panel_edge="#d5dacb",
    side_ink="#e9eef6",
)
# kept for older imports
DARK, LIGHT = NIGHT, DAY


def is_night() -> bool:
    try:
        return st.context.theme.type == "dark"
    except Exception:
        return False


def colours() -> dict:
    return NIGHT if is_night() else DAY


CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700;800&family=Barlow:wght@400;500;600&display=swap');

/* ---------- the ground: mown pitch stripes ---------- */
[data-testid="stAppViewContainer"] {
  background:
    repeating-linear-gradient(90deg, {stripe_a} 0 120px, {stripe_b} 120px 240px);
}
[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 2.4rem; max-width: 1300px; }

/* ---------- type ---------- */
h1, h2, h3 { font-family: 'Barlow Condensed', 'Arial Narrow', sans-serif !important; letter-spacing: .01em; }
h1 { text-transform: uppercase; font-size: clamp(2.3rem, 4.6vw, 3.6rem) !important; line-height: .95 !important; }
h2 { text-transform: uppercase; font-size: 1.7rem !important; }
.eyebrow {
  display: inline-flex; align-items: center; gap: 8px; font-family: 'Barlow Condensed', sans-serif;
  font-size: 13px; letter-spacing: .18em; text-transform: uppercase; font-weight: 700; color: {accent};
  margin-bottom: -4px;
}
.eyebrow::before { content: ""; width: 8px; height: 8px; border-radius: 50%; background: {accent}; box-shadow: {glow}; }
.lede { font-size: 15.5px; color: {ink2}; max-width: 74ch; }

/* ---------- panels ---------- */
[data-testid="stVerticalBlockBorderWrapper"] { background: {panel}; border-color: {panel_edge} !important; }
[data-testid="stExpander"] details { background: {panel}; border-color: {panel_edge} !important; }

/* ---------- scoreboard tiles ---------- */
.kpi {
  position: relative; border: 1px solid {panel_edge}; border-radius: 14px; padding: 12px 16px 10px;
  background: linear-gradient(180deg, {panel} 0%, {surface} 100%); overflow: hidden;
}
.kpi::after { content: ""; position: absolute; left: 16px; right: 16px; top: 0; height: 2px; background: {accent}; opacity: .8; }
.kpi span { display: block; font-family: 'Barlow Condensed', sans-serif; font-size: 12px; letter-spacing: .14em;
  text-transform: uppercase; color: {muted}; font-weight: 700; }
.kpi strong { display: block; font-family: 'Barlow Condensed', sans-serif; font-size: clamp(24px, 2.5vw, 38px); line-height: 1.05;
  white-space: nowrap;
  font-weight: 800; font-variant-numeric: tabular-nums; color: {ink}; text-shadow: {glow}; }

/* ---------- scoreboard strip (latest result) ---------- */
.board {
  border: 1px solid {panel_edge}; border-radius: 16px; padding: 14px 18px; display: grid; gap: 6px;
  background:
    radial-gradient(circle at 1px 1px, {accent_soft} 1px, transparent 1.5px) 0 0 / 9px 9px,
    linear-gradient(180deg, {panel}, {surface});
}
.board .label { font-family: 'Barlow Condensed', sans-serif; letter-spacing: .16em; text-transform: uppercase;
  font-size: 12px; font-weight: 700; color: {accent}; }
.board .line { display: flex; flex-wrap: wrap; align-items: baseline; gap: 6px 18px;
  font-family: 'Barlow Condensed', sans-serif; font-size: 26px; font-weight: 700; color: {ink}; }
.board .line .score { font-variant-numeric: tabular-nums; color: {ink}; text-shadow: {glow}; }
.board .line .vs { color: {muted}; font-size: 18px; }
.board .res { color: {ink2}; font-size: 14.5px; }

/* ---------- sidebar ---------- */
[data-testid="stSidebar"] * { color: {side_ink}; }
[data-testid="stSidebar"] .brand { font-family: 'Barlow Condensed', sans-serif; font-size: 26px; font-weight: 800;
  letter-spacing: .02em; text-transform: uppercase; line-height: 1; margin: 6px 0 14px; }
[data-testid="stSidebar"] .brand small { display: block; font-size: 12px; letter-spacing: .2em; color: {accent_side};
  font-weight: 700; margin-top: 4px; }
[data-testid="stSidebarNav"] a[aria-current="page"] { box-shadow: inset 3px 0 0 {accent_side}; }

/* ---------- controls ---------- */
[data-testid="stBaseButton-pills"][aria-checked="true"], button[kind="pillsActive"] { font-weight: 700; }
.statdef { font-size: 15px; }
.statdef .note { color: {muted}; font-size: 13px; }
.chip { display: inline-flex; align-items: center; gap: 6px; padding: 2px 10px; border-radius: 999px; font-size: 12px; font-weight: 600; }
.chip.demo { border: 1px dashed {muted}; }
/* ---------- knockout bracket ---------- */
.ko { display: flex; gap: 14px; overflow-x: auto; padding-bottom: 6px; align-items: stretch; }
.ko-col { flex: 1 0 220px; display: flex; flex-direction: column; justify-content: space-around; gap: 12px; }
.ko-round { font-family: 'Barlow Condensed', sans-serif; letter-spacing: .14em; text-transform: uppercase; font-size: 13px;
  font-weight: 700; color: {accent}; }
.ko-card { display: block; text-decoration: none !important; color: {ink} !important; border: 1px solid {panel_edge};
  border-radius: 12px; padding: 8px 12px; background: {panel}; }
.ko-card:hover { border-color: {accent}; }
.ko-date { font-size: 11.5px; color: {muted}; margin-bottom: 2px; }
.ko-team { display: flex; justify-content: space-between; gap: 10px; font-size: 14.5px; color: {ink2}; padding: 1px 0; }
.ko-team b { font-variant-numeric: tabular-nums; font-weight: 600; }
.ko-team.win { color: {ink}; font-weight: 700; }
.ko-team.win b { font-weight: 800; }
.ko-res { font-size: 12px; color: {muted}; margin-top: 3px; }
.ko-champ { font-family: 'Barlow Condensed', sans-serif; font-size: 22px; font-weight: 800; text-transform: uppercase;
  letter-spacing: .03em; color: {accent}; margin: 10px 0 0; }
.roles { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 8px; margin: 2px 0 6px; }
.roles .chip { background: {accent_soft}; color: {ink}; border: 1px solid {panel_edge}; font-family: 'Barlow Condensed', sans-serif;
  font-size: 14px; letter-spacing: .04em; text-transform: uppercase; }
.roles .note { color: {muted}; font-size: 13px; }

/* ---------- dot-chart legend ---------- */
.explain { list-style: none; padding: 0; margin: 4px 0 0; display: grid; gap: 7px; font-size: 13.5px; }
.explain li { display: grid; grid-template-columns: 18px 1fr; gap: 8px; align-items: start; color: {ink2}; }
.explain li b { color: {ink}; }
.explain .sw { width: 14px; height: 14px; border-radius: 3px; margin-top: 3px; border: 1px solid {axis}; }
.explain .sw.shade { background: {shade}; border-color: {s1}; }
.explain .sw.line { border: 0; border-top: 2px dashed {muted}; height: 0; margin-top: 10px; border-radius: 0; }
.explain .sw.dot { border-radius: 50%; border: 0; background: {s1}; }
.explain .sw.dot.neg { background: {neg}; }
.explain .sw.dot.orange { background: {s2}; }
.side-status { font-size: 13px; line-height: 1.4; }
</style>
"""


def inject_css() -> None:
    c = dict(colours())
    c["accent_side"] = "#f2b632"  # the sidebar is dark in both looks
    css = CSS
    for k, v in c.items():
        css = css.replace("{" + k + "}", v)
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


def scoreboard(label: str, home: str, home_score: str, away: str, away_score: str, result: str) -> None:
    st.markdown(
        f'<div class="board"><div class="label">{label}</div>'
        f'<div class="line"><span>{home}</span><span class="score">{home_score}</span><span class="vs">v</span>'
        f'<span>{away}</span><span class="score">{away_score}</span></div><div class="res">{result}</div></div>',
        unsafe_allow_html=True)


def explain_list(rows: list[tuple[str, str]]) -> None:
    """rows: (swatch class, html text)."""
    items = "".join(f'<li><span class="sw {sw}"></span><span>{txt}</span></li>' for sw, txt in rows)
    st.markdown(f'<ul class="explain">{items}</ul>', unsafe_allow_html=True)
