"""The look: your national side's colours (its sidebar and a light page, see TEAM_COLOURS), or a night match under
floodlights (dark) when you play as no national side.

Chart data colours come from a colour-blind-safe palette (blue / orange,
blue-red for above/below average); the team colours and the night look's gold
are only used for the page itself, never to mean something in a chart.
"""

from __future__ import annotations

from contextlib import contextmanager

import streamlit as st

from ccstats.colours import (  # noqa: F401 - the colours live in the engine; these names are kept for the pages
    DARK, DAY, LIGHT, NIGHT, TEAM_COLOURS, _hex, _lum, _mix, _readable, _rgb, _rgba, contrast, team_palette)
from ccstats.colours import nation_of as _nation_of


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


def team_look(teams) -> dict | None:
    """Use your national side's colours on every page for this browser session (the night look when you play as
    no national side). Returns the colours used, or None."""
    pal = team_palette(_nation_of(teams)) if teams else None
    try:
        st.session_state["_team_look"] = pal
    except Exception:  # noqa: BLE001 - outside a page (tests): nothing to remember
        pass
    return pal


def _session_look() -> dict | None:
    try:
        return st.session_state.get("_team_look")
    except Exception:  # noqa: BLE001
        return None


# Streamlit's own colours (its tables, buttons, boxes and sidebar): the settings, and the palette colour each takes
STREAMLIT_KEYS = {"theme.backgroundColor": "page", "theme.secondaryBackgroundColor": "field", "theme.textColor": "ink",
                  "theme.borderColor": "panel_edge", "theme.primaryColor": "accent",
                  "theme.dataframeHeaderBackgroundColor": "field", "theme.sidebar.backgroundColor": "sidebar",
                  "theme.sidebar.secondaryBackgroundColor": "side_field", "theme.sidebar.textColor": "side_ink",
                  "theme.sidebar.borderColor": "side_edge", "theme.sidebar.primaryColor": "accent_side",
                  "theme.sidebar.linkColor": "accent_side"}
# the ones the site starts with (.streamlit/config.toml), so they come back when you play as no national side
_STARTING: dict = {}


def _streamlit_colours(c: dict | None) -> dict:
    if c is None:
        return dict(_STARTING)
    out = {k: c[v] for k, v in STREAMLIT_KEYS.items()}
    out.update({"theme.base": "light" if c["light"] else "dark",
                "theme.linkColor": c["accent"] if c["light"] else "#7fb6f2"})
    return out


def apply_streamlit_colours() -> bool:
    """Give Streamlit's own parts (tables, buttons, boxes, the sidebar) this session's colours. They are sent with
    each run of the page, so True means they changed and the page should run once more to show them."""
    from streamlit import config
    if not _STARTING:
        for k in [*STREAMLIT_KEYS, "theme.base", "theme.linkColor"]:
            _STARTING[k] = config.get_option(k)
    want = _streamlit_colours(_session_look())
    changed = False
    for k, v in want.items():
        if config.get_option(k) != v:
            config.set_option(k, v, "<team colours>")
            changed = True
    return changed


def is_night() -> bool:
    """The night look (.streamlit/config.toml sets it), unless your national side's colours give the site a light
    page (see team_look)."""
    c = _session_look()
    return not (c and c.get("light"))


def colours() -> dict:
    return _session_look() or NIGHT


CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700;800&family=Barlow:wght@400;500;600&display=swap');

:root { --accent: {accent}; }
/* ---------- the ground: one plain colour ---------- */
[data-testid="stAppViewContainer"] { background: {page}; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebar"] { background: {sidebar}; }
.block-container { padding-top: 2.4rem; max-width: 1300px; }

/* ---------- logos ---------- */
img.logo { vertical-align: middle; object-fit: contain; display: inline-block; margin: 0 6px 2px 0; }
.logohead { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin: 4px 0 12px; font-size: 1.4rem; }
.logohead img.logo { margin: 0; }
.logohead .vs { color: {muted}; font-size: .95rem; margin: 0 6px; }
.logohead .sub { color: {muted}; font-size: .9rem; margin-left: 6px; }
.logohead .mine { display: inline-flex; align-items: center; gap: 10px; margin-right: 18px; }
.board .line img.logo { margin-right: 10px; }

/* ---------- type ---------- */
h1, h2, h3 { font-family: 'Barlow Condensed', 'Arial Narrow', sans-serif !important; letter-spacing: .01em; }
h1 { text-transform: uppercase; font-size: clamp(2.3rem, 4.6vw, 3.6rem) !important; line-height: .95 !important; }
h2 { text-transform: uppercase; font-size: 1.7rem !important; }
.eyebrow {
  display: inline-flex; align-items: center; gap: 8px; font-family: 'Barlow Condensed', sans-serif;
  font-size: 13px; letter-spacing: .18em; text-transform: uppercase; font-weight: 700; color: {accent};
  margin-bottom: -4px;
}
.eyebrow::before { content: ""; width: 8px; height: 8px; border-radius: 50%; background: {accent2}; box-shadow: {glow}; }
.lede { font-size: 15.5px; color: {ink2}; max-width: 74ch; }

/* ---------- panels ---------- */
[data-testid="stVerticalBlockBorderWrapper"] { background: {panel}; border-color: {panel_edge} !important; }
[data-testid="stExpander"] details { background: {panel}; border-color: {panel_edge} !important; }

/* ---------- scoreboard tiles ---------- */
.kpi {
  position: relative; border: 1px solid {panel_edge}; border-radius: 14px; padding: 12px 16px 10px;
  background: {panel}; overflow: hidden;
}
.kpi::after { content: ""; position: absolute; left: 16px; right: 16px; top: 0; height: 2px; background: {accent2}; opacity: .8; }
.kpi span { display: block; font-family: 'Barlow Condensed', sans-serif; font-size: 12px; letter-spacing: .14em;
  text-transform: uppercase; color: {muted}; font-weight: 700; }
.kpi { container-type: inline-size; }
/* a long figure (143,250 runs) shrinks to fit its tile instead of being cut off: --n is its number of characters */
.kpi strong { display: block; font-family: 'Barlow Condensed', sans-serif; line-height: 1.05;
  font-size: min(clamp(24px, 2.5vw, 38px), calc(150cqw / var(--n, 4)));
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  font-weight: 800; font-variant-numeric: tabular-nums; color: {ink}; text-shadow: {glow}; }
.kpi strong .small { font-size: .66em; letter-spacing: .04em; }

/* ---------- scoreboard strip (latest result) ---------- */
.board {
  border: 1px solid {panel_edge}; border-radius: 16px; padding: 14px 18px; display: grid; gap: 6px;
  background: {panel};
}
.board .label { font-family: 'Barlow Condensed', sans-serif; letter-spacing: .08em;
  font-size: 14px; font-weight: 700; color: {accent}; }  /* normal capitals: "T20Is", not "T20IS" */
.board .line { display: flex; flex-wrap: wrap; align-items: baseline; gap: 6px 18px;
  font-family: 'Barlow Condensed', sans-serif; font-size: 26px; font-weight: 700; color: {ink}; }
.board .line .score { font-variant-numeric: tabular-nums; color: {ink}; text-shadow: {glow}; }
.board .line .vs { color: {muted}; font-size: 18px; }
.board .res { color: {ink2}; font-size: 14.5px; }
.board.withcomp { grid-template-columns: 1fr auto; }  /* the competition's logo at the right */
.board.withcomp > div { grid-column: 1; }
.board.withcomp > .comp { grid-column: 2; grid-row: 1 / span 3; align-self: center; margin-left: 12px; }
.board .comp img.logo { margin: 0; }

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
.tblwrap { overflow-x: auto; container-type: inline-size; }
table.tbl { width: 100%; border-collapse: collapse; font-size: 13.5px; font-variant-numeric: tabular-nums; }
table.tbl th { text-align: left; font-family: 'Barlow Condensed', sans-serif; letter-spacing: .08em; text-transform: uppercase;
  font-size: 12px; color: {muted}; font-weight: 700; padding: 4px 7px; border-bottom: 1px solid {panel_edge};
  line-height: 1.15; vertical-align: bottom; }  /* long headings wrap, so a table fits a half-width box */
table.tbl td { padding: 5px 7px; border-bottom: 1px solid {grid}; color: {ink2}; vertical-align: top; }
table.tbl td.num { white-space: nowrap; }
table.tbl td.num, table.tbl th.num { text-align: right; }
table.tbl tr.hi td { color: {ink}; font-weight: 700; background: {accent_soft}; }
table.tbl tr.dim td { opacity: .45; }
table.tbl a { color: {ink} !important; text-decoration: none; border-bottom: 1px dotted {muted}; }
table.tbl a:hover { color: {accent} !important; border-bottom-color: {accent}; }
/* a table in a half-width box: a little tighter, so it fits without scrolling sideways */
@container (max-width: 520px) { table.tbl { font-size: 12.5px; } table.tbl td, table.tbl th { padding-left: 5px; padding-right: 5px; } }
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
table.cal td a.N { background: {mid}; cursor: help; }
table.cal td.today { border-color: {accent}; }
.calgrid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px 22px; align-items: start; }
.calgrid .mon h4 { font-size: 15px; font-weight: 700; margin: 0 0 2px; padding: 0; color: {ink}; }
.calgrid .mon.empty h4 { color: {muted}; }
.calgrid .tc { border: 1px dashed {accent}; background: {accent_soft}; border-radius: 8px; padding: 3px 8px; margin: 3px 0 2px;
  font-size: 12px; color: {ink}; line-height: 1.35; }
.calgrid .tc b { color: {accent}; }
.calgrid .ms { font-size: 11.5px; color: {ink2}; margin: 0 0 2px; line-height: 1.35; }
.grade { display: inline-block; min-width: 34px; text-align: center; border-radius: 8px; padding: 2px 6px;
  font-family: 'Barlow Condensed', sans-serif; font-weight: 800; font-size: 20px; }
.grade.A { background: {pos}; color: #fff; } .grade.B { background: rgba(57,135,229,.45); color: {ink}; }
.grade.C { background: {mid}; color: {ink}; } .grade.D { background: rgba(230,103,103,.45); color: {ink}; }
.grade.E { background: {neg}; color: #fff; }
</style>
"""


def inject_css() -> None:
    c = dict(colours())
    if "sidebar" not in c:  # the night look: the sidebar as .streamlit/config.toml has it
        c.update(accent_side="#f2b632", accent2=c["accent"], sidebar="#071020")
    css = CSS
    for k, v in c.items():
        if isinstance(v, str):
            css = css.replace("{" + k + "}", v)
    st.markdown(css, unsafe_allow_html=True)


def page_header(eyebrow: str, title: str, lede: str = "") -> None:
    st.markdown(f'<div class="eyebrow">{eyebrow}</div>', unsafe_allow_html=True)
    st.title(title, anchor=False)
    if lede:
        st.markdown(f'<p class="lede">{lede}</p>', unsafe_allow_html=True)


def kpis(items: list[tuple[str, str]]) -> None:
    import re
    cols = st.columns(len(items))
    for col, (label, value) in zip(cols, items):
        n = max(len(re.sub(r"<[^>]+>", "", str(value))), 4)  # its length as shown, so a long one can shrink to fit
        col.markdown(f'<div class="kpi"><span>{label}</span><strong style="--n:{n}">{value}</strong></div>',
                     unsafe_allow_html=True)


def scoreboard(label: str, home: str, home_score: str, away: str, away_score: str, result: str,
               event: str = "") -> None:
    """A match's result with the teams' emblems; event is its competition, whose logo (when your editor files have
    one) stands at the right: the World Test Championship's on every Test, a World Cup's only on its own games."""
    from ui import logos
    hl, al = logos.team(home, 64), logos.team(away, 64)
    cl = logos.comp(event, 80) if event else ""
    st.markdown(
        f'<div class="board{" withcomp" if cl else ""}"><div class="label">{label}</div>'
        f'<div class="line"><span>{hl}{home}</span><span class="score">{home_score}</span><span class="vs">v</span>'
        f'<span>{al}{away}</span><span class="score">{away_score}</span></div><div class="res">{result}</div>'
        + (f'<div class="comp">{cl}</div>' if cl else "") + '</div>',
        unsafe_allow_html=True)


def explain_list(rows: list[tuple[str, str]]) -> None:
    """rows: (swatch class, html text)."""
    items = "".join(f'<li><span class="sw {sw}"></span><span>{txt}</span></li>' for sw, txt in rows)
    st.markdown(f'<ul class="explain">{items}</ul>', unsafe_allow_html=True)


def counted(name: str, n: int) -> str:
    """'T20 Blast · 115 matches' in a box; a long name keeps its words and shows the count short, so it fits:
    'County Championship · Division 2 (32)'."""
    return f"{name} · {n} match{'' if n == 1 else 'es'}" if len(name) <= 24 else f"{name} ({n})"


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
