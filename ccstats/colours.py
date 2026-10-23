"""The site's colours: each national side's colours (TEAM_COLOURS) made into a full palette for the pages
(team_palette), and the night look used when you play as no national side.

Pure colour work with no page code in it, so the current site (ui/theme.py) and the new one (server/) share it.
Chart data colours come from a colour-blind-safe palette (blue / orange, blue-red for above/below average); the team
colours are only used for the page itself, never to mean something in a chart."""

from __future__ import annotations

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


def nation_of(teams) -> str | None:
    """The first national side among your teams (the one the site takes its colours from)."""
    return next((t for t in teams if t in TEAM_COLOURS), None)
