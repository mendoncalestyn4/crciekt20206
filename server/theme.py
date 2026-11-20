"""The new site's colours: the chosen style (idea 4) in your national side's colours.

The approved mock-up is India's: a light-brown rail on a dark-blue page, tiles a shade lighter than the page, gold
"LED" numbers. Every colour of it is the page's own blue at another lightness, so a dark page of any colour (India's,
or the night look when you play as no national side) gets the same steps from its own colour. A light page (most
national sides) keeps its light tiles and dark words, with the numbers and marks in a deep gold that reads on it.

tokens() gives every colour the website draws with; the website turns them into CSS variables."""

from __future__ import annotations

import colorsys

from ccstats.colours import DAY, NIGHT, TEAM_COLOURS, _hex, _mix, _readable, _rgb, contrast, nation_of, team_palette

# the mock-up's colours (India's): every one is the page's blue at another lightness; another dark page gets each of
# them moved by as much as its page differs from India's (hue and lightness shifted, saturation in proportion)
MOCK_PAGE, MOCK_RAIL, MOCK_RAIL_INK = "#0f2557", "#dab16f", "#3b2a10"
MOCK = {"tile": "#162f68", "tile2": "#1b3878", "edge": "#24427f", "deep": "#0a1b40", "track": "#0d214c",
        "meter": "#13245a", "ppl": "#102a5e", "ppl_edge": "#2a4785", "split": "#203c78", "other": "#3a5aa0",
        "ink": "#f3f6fc", "dim": "#9fb0d6", "soft": "#c9d5f2", "blue": "#7aa2ff"}
WORDS = ("ink", "dim", "soft", "blue")   # words keep their lightness (they must read), only their hue moves
# the colours that mean something in charts (never team colours): won, lost, the gold numbers, the second colour
FIXED = {"win": "#45c08a", "loss": "#ee6a6a", "orange": "#ee7660", "led": "#ffc65a", "led_ink": "#1b1300",
         "warm": "#ff8a3d", "cream": "#f1efe6", "grey": "#8a97b5", "violet": "#c58bff", "teal": "#5ee0d0"}


def _hsl(h: str) -> tuple[float, float, float]:
    r, g, b = (v / 255 for v in _rgb(h))
    hue, light, sat = colorsys.rgb_to_hls(r, g, b)
    return hue, sat, light


def _from_hsl(hue: float, sat: float, light: float) -> str:
    r, g, b = colorsys.hls_to_rgb(hue, max(0.0, min(1.0, light)), max(0.0, min(1.0, sat)))
    return _hex((r * 255, g * 255, b * 255))


def _shift(colour: str, frm: str, to: str, keep_light: bool = False) -> str:
    """colour, moved as far as `to` is from `frm`: hue and lightness shifted, saturation in proportion."""
    if frm.lower() == to.lower():
        return colour
    h, s, v = _hsl(colour)
    fh, fs, fv = _hsl(frm)
    th, ts, tv = _hsl(to)
    return _from_hsl((h + th - fh) % 1.0, s * (ts / fs if fs else 1.0), v if keep_light else v + tv - fv)


def _dark(page: str) -> dict:
    """The mock-up's colours on a dark page of any colour (India's page gives exactly the mock-up's)."""
    return {k: _shift(v, MOCK_PAGE, page, keep_light=k in WORDS) for k, v in MOCK.items()}


def _rail_ink(sidebar: str, fallback: str) -> str:
    """The rail's words: a deep shade of the rail's own colour on a light rail (the mock-up's brown on gold), a pale
    one on a dark rail; the plain ink if that wouldn't read."""
    if _hsl(sidebar)[2] > 0.45:
        ink = _shift(MOCK_RAIL_INK, MOCK_RAIL, sidebar, keep_light=True)
    else:
        hue, sat, _ = _hsl(sidebar)
        ink = _from_hsl(hue, sat * 0.3, 0.93)
    return ink if contrast(ink, sidebar) >= 4.5 else fallback


def tokens(nation: str | None) -> dict:
    """Every colour the website draws with, for a national side (None: the night look)."""
    pal = team_palette(nation) if nation else None
    if pal is None:                       # no national side: the night look, a dark page with a gold rail
        page, sidebar, main = NIGHT["page"], "#dab16f", "#368ee2"
        dark, side_ink = True, "#15181f"
    else:
        page, sidebar, main = pal["page"], pal["sidebar"], TEAM_COLOURS[nation][2]
        dark, side_ink = not pal["light"], pal["side_ink"]
    t = dict(FIXED, nation=nation if pal else None, dark=dark, page=page, rail=sidebar,
             rail_ink=_rail_ink(sidebar, side_ink), main=main,
             # the rail's mark for the page you're on: the page colour, with the page's words
             rail_on=page)
    # the two-tone line on top of each tile: the side's main colour, then its rail colour (India: blue, then gold);
    # the second colour of the pair when the rail is too close to the main one to tell apart
    second = sidebar if contrast(sidebar, main) >= 1.5 else (TEAM_COLOURS[nation][3] if pal else "#dab16f")
    t["line"] = [main, second]
    if dark:
        t.update(_dark(page))
        t.update(gold=sidebar if pal else "#dab16f", glow=True, dimn="#e9d7ae")   # dimn: the quieter numbers
        t["rail_on_ink"] = "#ffffff"
    else:                                 # a light page: light tiles, dark words, deep gold numbers
        tile = pal["panel"]
        # boxes inside a tile take the page's own colour (your choice of 14 November, every team's light look: no
        # muddy mix of the main colour into the page), set apart from the tile by their thin edge
        t.update(tile=tile, tile2=page, edge=pal["panel_edge"], deep=_mix(page, main, 0.16),
                 track=_mix(tile, main, 0.12), meter=_mix(tile, main, 0.16), ppl=_mix(page, main, 0.04),
                 ppl_edge=_mix(page, main, 0.30), split=pal["grid"], other=_mix(tile, main, 0.38),
                 ink=pal["ink"], dim=pal["muted"], soft=pal["ink2"], blue=_readable(DAY["s1"], tile, 3.0),
                 gold=_readable(sidebar, tile, 3.0), glow=False, rail_on_ink=pal["ink"], dimn=pal["ink2"])
        # (the charts' blue is a real blue for every side, never the team's own colour: "better" in blue and "worse" in
        # red must never be the same colour, as they were for a side in red, nor called blue when drawn green)
        t["led"] = _readable(FIXED["led"], tile, 4.5)        # the gold numbers, deep enough to read on a light tile
        t["led_ink"] = "#ffffff" if contrast("#ffffff", t["led"]) >= 4.5 else "#1b1300"
        t["win"] = _readable(FIXED["win"], tile, 3.0)       # marks (lamps, bars) need 3:1 against the tile
        t["loss"] = _readable(FIXED["loss"], tile, 3.0)
        t["orange"] = _readable(FIXED["orange"], tile, 3.0)
        # the other chart colours (pie slices, the season's extra lines, drawn games, everyone else): deep enough to
        # see on a light tile; the pale cream of the dark look would vanish there, so its slice is violet instead
        for k in ("warm", "grey", "violet", "teal"):
            t[k] = _readable(FIXED[k], tile, 3.0)
        t["cream"] = t["violet"]
    return t


def for_teams(teams) -> dict:
    """The colours for the teams you play as: the first national side's, or the night look."""
    return tokens(nation_of(list(teams or [])))
