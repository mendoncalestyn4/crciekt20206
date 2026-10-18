"""The look: your national side's colours (its sidebar and a light page, see TEAM_COLOURS), or a night match under
floodlights (dark) when you play as no national side.

Chart data colours come from a colour-blind-safe palette (blue / orange,
blue-red for above/below average); the team colours and the night look's gold
are only used for the page itself, never to mean something in a chart.
"""

from __future__ import annotations

from contextlib import contextmanager

import streamlit as st

NIGHT = dict(
    surface="#101b2f", page="#0a1322", ink="#eef2f8", ink2="#b9c4d6", muted="#7f8ca3", grid="#1f2c45",
    axis="#2d3d5c", s1="#3987e5", s2="#e0662f", pos="#3987e5", neg="#e66767", mid="#2a3550", dim="#3a4863",
    shade="rgba(57,135,229,0.14)", good="#3ccf7a", chip="#1a2b4a", accent="#f2b632", accent_soft="rgba(242,182,50,0.14)",
    glow="0 0 18px rgba(242,182,50,0.35)", panel="#101b2f", panel_edge="#22314d",
    side_ink="#e9eef6",
)
DAY = dict(
    surface="#fbfcf8", page="#f3f5ef", ink="#0f1b2d", ink2="#44516a", muted="#7c8697", grid="#e2e6da",
    axis="#c5ccba", s1="#2a78d6", s2="#eb6834", pos="#2a78d6", neg="#e34948", mid="#eceee7", dim="#c9cdc2",
    shade="rgba(42,120,214,0.08)", good="#1d6b45", chip="#e3efe7", accent="#1d6b45", accent_soft="rgba(29,107,69,0.10)",
    glow="none", panel="#fbfcf8", panel_edge="#d5dacb",
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


# Each national side's colours, matched to its shirt (the 2023 World Cup kits, measured from their photos), its logo
# and team colours as encycolorpedia.com lists them, or its flag: (the sidebar, the page, the main colour for buttons,
# headings and links, the second colour for the marks by them)
TEAM_COLOURS = {
    "Afghanistan": ("#035d9a", "#ebf4f9", "#0472b4", "#d63d4d"),
    "Australia": ("#0d3b1e", "#e7e245", "#0d3b1e", "#b8962e"),
    "Bangladesh": ("#1f5a41", "#eff4f2", "#2b644b", "#e65b56"),
    "Bermuda": ("#0b2a6b", "#eff3f8", "#1f4fa0", "#e0322a"),
    "Canada": ("#8f101c", "#fdf4f4", "#c8102e", "#5c6670"),
    "Denmark": ("#8f1730", "#fcf3f5", "#c8102e", "#5c6670"),
    "England": ("#15295e", "#eff3f9", "#3864b5", "#c42032"),
    "Hong Kong": ("#a5101a", "#fdf4f3", "#de2910", "#5c6670"),
    "India": ("#dab16f", "#0f2557", "#368ee2", "#ee7660"),
    "Ireland": ("#1e5a2a", "#ebfbf2", "#1e7a3a", "#afca0b"),
    "Italy": ("#2f5e3a", "#f1f4f1", "#2f6e3e", "#ce2b37"),
    "Kenya": ("#0b5d2a", "#eef7f1", "#0b7a3a", "#c8102e"),
    "Malaysia": ("#0a1f7a", "#fff8db", "#0a1f7a", "#cc0001"),
    "Namibia": ("#003580", "#eff4f9", "#003580", "#e0a800"),
    "Nepal": ("#003893", "#eff4f9", "#003893", "#dc143c"),
    "Netherlands": ("#ef6a46", "#fef3f0", "#1c86b0", "#ef6a46"),
    "New Zealand": ("#111111", "#f1f1f2", "#1a1a1a", "#9a979c"),
    "Nigeria": ("#00623b", "#edf7f3", "#008751", "#5c6670"),
    "Oman": ("#9e1b1f", "#fdf3f4", "#db161b", "#008000"),
    "Pakistan": ("#1f4a3f", "#eff8f3", "#386359", "#5ebe88"),
    "Papua New Guinea": ("#161616", "#fff9de", "#ce1126", "#d4a90a"),
    "Saudi Arabia": ("#005430", "#edf5f1", "#006c35", "#5c6670"),
    "Scotland": ("#1b2a63", "#f6f4fa", "#0065bd", "#7b5fb3"),
    "Singapore": ("#a5121c", "#fef5f5", "#ef3340", "#5c6670"),
    "South Africa": ("#236252", "#eff6f4", "#2c7965", "#e2c22a"),
    "Sri Lanka": ("#1e2f6b", "#eff2f8", "#3b57a6", "#e3a90f"),
    "UAE": ("#00602b", "#edf5f0", "#00732f", "#e5242b"),
    "USA": ("#0a2357", "#eff3f8", "#1f4fa0", "#d0213a"),
    "Uganda": ("#1a1a1a", "#fffadc", "#1a1a1a", "#d90000"),
    "West Indies": ("#6d0f2c", "#fff5de", "#7b1e3a", "#d99a00"),
    "Zimbabwe": ("#b40224", "#fff9e1", "#b40224", "#329633"),
}


def _rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _hex(rgb) -> str:
    return "#" + "".join(f"{max(0, min(255, round(v))):02x}" for v in rgb)


def _mix(a: str, b: str, t: float) -> str:
    """a with t of b mixed in."""
    ra, rb = _rgb(a), _rgb(b)
    return _hex(x + (y - x) * t for x, y in zip(ra, rb))


def _rgba(h: str, alpha: float) -> str:
    r, g, b = _rgb(h)
    return f"rgba({r},{g},{b},{alpha})"


def _lum(h: str) -> float:
    def lin(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(v) for v in _rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    """The WCAG contrast of two colours (1 to 21)."""
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _readable(colour: str, on: str, need: float = 4.5) -> str:
    """colour, mixed towards white or black (whichever the background is not) until it reads on that background."""
    toward = "#ffffff" if _lum(on) < 0.2 else "#000000"
    for i in range(21):
        c = _mix(colour, toward, i / 20)
        if contrast(c, on) >= need:
            return c
    return toward


def team_palette(nation: str) -> dict | None:
    """The site's colours for a national side: the sidebar and page in its colours, its main colour for buttons,
    headings and links, its second colour for the marks by them. Words are dark on a light page and light on a dark
    one (and light or dark on the sidebar, whichever reads), and chart colours stay the colour-blind-safe blue and
    orange. None for a team without colours."""
    if nation not in TEAM_COLOURS:
        return None
    sidebar, page, main, second = TEAM_COLOURS[nation]
    side_ink = max(("#15181f", "#f4f7fb"), key=lambda ink: contrast(ink, sidebar))
    toward = "#ffffff" if side_ink != "#15181f" else "#000000"  # sidebar boxes: a little lighter (or darker)
    light = _lum(page) >= 0.2
    if light:
        accent = _readable(main, page, 4.8)
        c = dict(DAY)
        c.update(surface=_mix(page, "#ffffff", 0.6), panel=_mix(page, "#ffffff", 0.6),
                 panel_edge=_mix(page, main, 0.20), grid=_mix(page, main, 0.10), axis=_mix(page, main, 0.30),
                 mid=_mix(page, main, 0.12), dim=_mix(page, main, 0.30), chip=_mix(page, main, 0.10),
                 field=_mix(page, "#ffffff", 0.6), ink="#0f1b2d", ink2=_readable("#3d4a61", page, 7.0),
                 muted=_readable("#5d687c", page, 4.6))
    else:  # a dark page: its boxes a little lighter, light words, the second colour for headings and buttons
        accent = _readable(second, page, 4.8)
        c = dict(NIGHT)
        c.update(surface=_mix(page, "#ffffff", 0.06), panel=_mix(page, "#ffffff", 0.06),
                 panel_edge=_mix(page, "#ffffff", 0.16), grid=_mix(page, "#ffffff", 0.10),
                 axis=_mix(page, "#ffffff", 0.22), mid=_mix(page, "#ffffff", 0.14), dim=_mix(page, "#ffffff", 0.25),
                 chip=_mix(page, "#ffffff", 0.10), field=_mix(page, "#ffffff", 0.09),
                 ink2=_readable("#b9c4d6", _mix(page, "#ffffff", 0.06), 7.0),  # (read on the boxes too)
                 muted=_readable("#8a97ad", _mix(page, "#ffffff", 0.06), 4.6))
    c.update(page=page, accent=accent,
             # the second colour for marks that aren't words (the line on a tile, the dot by a heading), when it shows
             accent2=second if contrast(second, page) >= 1.6 else accent,
             accent_soft=_rgba(accent, 0.10 if light else 0.16), glow="none", light=light, nation=nation,
             sidebar=sidebar, side_ink=side_ink, side_field=_mix(sidebar, toward, 0.14),
             side_edge=_mix(sidebar, toward, 0.26),
             # the sidebar's marks (the page you're on): whichever of the two colours reads on it, made to read
             accent_side=_readable(max((second, main), key=lambda x: contrast(x, sidebar)), sidebar, 4.5))
    return c


def _nation_of(teams) -> str | None:
    """The first national side among your teams (the one the site takes its colours from)."""
    return next((t for t in teams if t in TEAM_COLOURS), None)


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
