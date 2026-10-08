"""The look: a night match under floodlights (dark) and a day match (light).

Chart data colours come from a colour-blind-safe palette (blue / orange,
blue-red for above/below average); the gold and pitch green are only used
for the page itself, never to mean something in a chart.
"""

from __future__ import annotations

from contextlib import contextmanager

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


@contextmanager
def safe_section(name: str):
    """Run one part of a page; if it fails, show a short note there and carry on
    with the rest of the page.  (st.stop / reruns are not errors and pass through.)"""
    try:
        yield
    except Exception as e:  # noqa: BLE001 - shown to the user, never hidden
        st.warning(f"The {name} part couldn't be shown for this selection. The rest of the page is fine.")
        with st.expander("Details (send this to fix it)"):
            st.code(f"{type(e).__name__}: {e}")


def is_night() -> bool:
    """The site always has the night look (.streamlit/config.toml sets the one dark theme), whatever the
    computer or browser is set to, so the page, its tables and its charts all match it."""
    return True


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
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  font-weight: 800; font-variant-numeric: tabular-nums; color: {ink}; text-shadow: {glow}; }
.kpi strong .small { font-size: .66em; letter-spacing: .04em; }

/* ---------- scoreboard strip (latest result) ---------- */
.board {
  border: 1px solid {panel_edge}; border-radius: 16px; padding: 14px 18px; display: grid; gap: 6px;
  background:
    radial-gradient(circle at 1px 1px, {accent_soft} 1px, transparent 1.5px) 0 0 / 9px 9px,
    linear-gradient(180deg, {panel}, {surface});
}
.board .label { font-family: 'Barlow Condensed', sans-serif; letter-spacing: .08em;
  font-size: 14px; font-weight: 700; color: {accent}; }  /* normal capitals: "T20Is", not "T20IS" */
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
.ko-col { flex: 1 0 220px; display: flex; flex-direction: column; gap: 8px; }
.ko-cards { flex: 1; display: flex; flex-direction: column; justify-content: space-around; gap: 12px; }
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
a.btnlink { display: inline-block; padding: 7px 14px; border-radius: 10px; border: 1px solid {accent}; color: {accent} !important;
  font-weight: 700; text-decoration: none !important; white-space: nowrap; }
a.btnlink:hover { background: {accent_soft}; }

/* ---------- small tables with links ---------- */
.tblwrap { overflow-x: auto; }
table.tbl { width: 100%; border-collapse: collapse; font-size: 13.5px; font-variant-numeric: tabular-nums; }
table.tbl th { text-align: left; font-family: 'Barlow Condensed', sans-serif; letter-spacing: .08em; text-transform: uppercase;
  font-size: 12px; color: {muted}; font-weight: 700; padding: 4px 8px; border-bottom: 1px solid {panel_edge}; white-space: nowrap; }
table.tbl td { padding: 5px 8px; border-bottom: 1px solid {grid}; color: {ink2}; vertical-align: top; }
table.tbl td.num, table.tbl th.num { text-align: right; }
table.tbl tr.hi td { color: {ink}; font-weight: 700; background: {accent_soft}; }
table.tbl tr.dim td { opacity: .45; }
table.tbl a { color: {ink} !important; text-decoration: none; border-bottom: 1px dotted {muted}; }
table.tbl a:hover { color: {accent} !important; border-bottom-color: {accent}; }
.tick { color: {good}; font-weight: 800; }
.chartnote { font-size: 13.5px; color: {ink2}; margin: 2px 0 6px; line-height: 1.45; display: grid; gap: 3px; }
.chartnote b { color: {ink}; }
/* ---------- match cards ---------- */
.mcards { display: grid; grid-template-columns: repeat(auto-fill, minmax(290px, 1fr)); gap: 10px; }
.mcard { border: 1px solid {panel_edge}; border-radius: 12px; padding: 9px 12px; background: {panel}; font-size: 13.5px; }
.mcard .top { display: flex; justify-content: space-between; gap: 8px; color: {muted}; font-size: 12px; }
.mcard .side { display: flex; justify-content: space-between; gap: 8px; color: {ink}; font-weight: 600; margin-top: 3px; }
.mcard .side b { font-variant-numeric: tabular-nums; }
.mcard .who { color: {ink2}; font-size: 12.5px; margin: 0 0 2px; }
.mcard .story { color: {ink2}; margin-top: 5px; font-size: 13px; }
.mcard a { color: {accent} !important; font-size: 12.5px; text-decoration: none; font-weight: 700; }
.form { display: inline-flex; gap: 4px; }
.form span { display: inline-block; min-width: 22px; text-align: center; border-radius: 6px; padding: 0 4px; font-weight: 800;
  font-family: 'Barlow Condensed', sans-serif; font-size: 15px; }
.form .W { background: {pos}; color: #fff; } .form .L { background: {neg}; color: #fff; }
.form .D, .form .T, .form .NR { background: {mid}; color: {ink}; }
/* ---------- calendar ---------- */
table.cal { width: 100%; border-collapse: separate; border-spacing: 4px; table-layout: fixed; }
table.cal th { font-size: 11.5px; color: {muted}; font-weight: 700; text-align: center; letter-spacing: .1em; }
table.cal td { height: 64px; vertical-align: top; border: 1px solid {grid}; border-radius: 8px; padding: 3px 5px;
  font-size: 11.5px; color: {ink2}; background: {panel}; overflow: hidden; }
table.cal td.out { opacity: .35; }
table.cal td .d { font-size: 11px; color: {muted}; }
table.cal td a { display: block; text-decoration: none; color: {ink} !important; border-radius: 4px; padding: 1px 3px;
  margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
table.cal td a.W { background: rgba(57,135,229,.25); } table.cal td a.L { background: rgba(230,103,103,.25); }
table.cal td a.D, table.cal td a.T, table.cal td a.NR { background: {mid}; }
table.cal td a.UP { border: 1px dashed {muted}; color: {muted} !important; }
table.cal.mini { border-spacing: 2px; } table.cal.mini td { height: 34px; font-size: 10px; padding: 1px 3px; }
table.cal.mini td a { font-size: 10px; padding: 0 2px; margin-top: 1px; }
.grade { display: inline-block; min-width: 34px; text-align: center; border-radius: 8px; padding: 2px 6px;
  font-family: 'Barlow Condensed', sans-serif; font-weight: 800; font-size: 20px; }
.grade.A { background: {pos}; color: #fff; } .grade.B { background: rgba(57,135,229,.45); color: {ink}; }
.grade.C { background: {mid}; color: {ink}; } .grade.D { background: rgba(230,103,103,.45); color: {ink}; }
.grade.E { background: {neg}; color: #fff; }
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


def esc(v) -> str:
    import html
    return html.escape(str(v))


def player_link(name: str) -> str:
    from urllib.parse import quote
    return f"<a href='player?player={quote(str(name))}' target='_self'>{esc(name)}</a>"


def match_link(mid: str, text: str) -> str:
    return f"<a href='match?match={esc(mid)}' target='_self'>{esc(text)}</a>"


def html_table(rows: list[list], columns: list[str], numeric: set[int] | None = None, row_class: list[str] | None = None,
               raw: set[int] | None = None) -> None:
    """A small table whose cells can hold links. `raw`: column numbers whose cells are
    already HTML (links); everything else is escaped. `numeric` columns are right-aligned."""
    numeric, raw = numeric or set(), raw or set()
    head = "".join(f"<th class='{'num' if i in numeric else ''}'>{esc(c)}</th>" for i, c in enumerate(columns))
    body = []
    for k, r in enumerate(rows):
        cls = row_class[k] if row_class else ""
        cells = "".join(f"<td class='{'num' if i in numeric else ''}'>{v if i in raw else esc(v)}</td>"
                        for i, v in enumerate(r))
        body.append(f"<tr class='{cls}'>{cells}</tr>")
    st.markdown(f"<div class='tblwrap'><table class='tbl'><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody>"
                "</table></div>", unsafe_allow_html=True)


def form_strip(outcomes: list[str]) -> str:
    return "<span class='form'>" + "".join(f"<span class='{o}'>{o}</span>" for o in outcomes) + "</span>" if outcomes else "–"


def chart_note(shows: str, purpose: str) -> None:
    """Under every chart: what this chart says right now (with its numbers), then what the chart is for."""
    st.markdown(f"<div class='chartnote'><div><b>What it shows:</b> {shows}</div>"
                f"<div><b>What it's for:</b> {purpose}</div></div>", unsafe_allow_html=True)
