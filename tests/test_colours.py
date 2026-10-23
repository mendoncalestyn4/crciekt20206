"""The team colours live in the engine (ccstats/colours.py), shared by the current site and the new one."""

from ccstats import colours as C
from ui import theme


def test_the_current_site_uses_the_engines_colours():
    """ui/theme.py takes the colours from the engine, so the two sites can never drift apart."""
    assert theme.TEAM_COLOURS is C.TEAM_COLOURS
    assert theme.team_palette is C.team_palette
    assert theme.NIGHT is C.NIGHT and theme.DAY is C.DAY
    assert theme._nation_of is C.nation_of


def test_every_nation_has_a_full_readable_palette():
    """Every national side's palette has what the pages draw with, and its words read on its tiles and sidebar."""
    need = {"page", "sidebar", "side_ink", "ink", "ink2", "muted", "accent", "accent2", "panel", "panel_edge", "light",
            "accent_side", "side_field", "side_edge"}
    assert len(C.TEAM_COLOURS) == 31
    for nation in C.TEAM_COLOURS:
        pal = C.team_palette(nation)
        assert need <= set(pal), nation
        assert C.contrast(pal["ink"], pal["panel"]) >= 4.5, nation
        assert C.contrast(pal["ink2"], pal["panel"]) >= 4.5, nation
        assert C.contrast(pal["side_ink"], pal["sidebar"]) >= 4.5, nation
        assert C.contrast(pal["accent_side"], pal["sidebar"]) >= 4.5, nation
    assert C.team_palette("Kent") is None   # a county has no national colours


def test_the_colours_come_from_your_first_national_side():
    assert C.nation_of(["Kent", "India", "England"]) == "India"
    assert C.nation_of(["Kent", "Mumbai Indians"]) is None
    assert C.nation_of([]) is None
