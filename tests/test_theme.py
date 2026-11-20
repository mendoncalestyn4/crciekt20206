"""Your national side's colours on the site: every country has them, every word reads, and Streamlit's own parts
take them and give them back."""

from streamlit import config

from ccstats import fixtures as FX
from ui import theme as T


def test_every_national_side_has_its_colours():
    assert set(T.TEAM_COLOURS) == FX.NATIONS
    for nation in FX.NATIONS:
        c = T.team_palette(nation)
        assert c["nation"] == nation and c["light"] == (nation != "India")  # India's page is dark blue
        assert set(T.NIGHT) <= set(c)  # every colour the pages and charts use


def test_every_word_reads_on_every_team_colour():
    for nation in FX.NATIONS:
        c = T.team_palette(nation)
        for words, on, need in (("ink", "page", 7), ("ink2", "page", 7), ("muted", "page", 4.5), ("accent", "page", 4.5),
                                ("ink", "panel", 7), ("muted", "panel", 4.5), ("side_ink", "sidebar", 5.5),
                                ("accent_side", "sidebar", 4.5)):
            assert T.contrast(c[words], c[on]) >= need, (nation, words, on)


def test_the_colours_are_the_ones_matched_to_the_shirts():
    sidebar, page, main, second = T.TEAM_COLOURS["Australia"]
    assert (sidebar, page) == ("#0d3b1e", "#f5f3b5")  # dark green trim, a pale yellow page
    india = T.team_palette("India")
    assert india["sidebar"] == "#dab16f" and india["side_ink"] == "#15181f"  # a light sidebar has dark words
    assert india["page"] == "#0f2557" and india["ink"] == T.NIGHT["ink"] and not india["light"]  # light words
    assert T.contrast(india["accent"], india["page"]) >= 4.5  # orange headings on the dark blue
    assert T.team_palette("England")["side_ink"] == "#f4f7fb"


def test_no_national_side_keeps_the_night_look():
    try:
        assert T.team_look([]) is None and T.team_look(["Nottinghamshire"]) is None
        assert T.team_palette("Nottinghamshire") is None
        assert T.colours() is T.NIGHT and T.is_night()
        assert T.team_look(["Nottinghamshire", "India", "England"])["nation"] == "India"  # the first national side
    finally:
        T.team_look([])  # the other tests' pages and charts have the night look


def test_streamlit_takes_the_team_colours_and_gives_back_its_own(monkeypatch):
    start = {k: config.get_option(k) for k in [*T.STREAMLIT_KEYS, "theme.base", "theme.linkColor"]}
    look = {}
    monkeypatch.setattr(T, "_session_look", lambda: look.get("c"))
    monkeypatch.setattr(T, "_STARTING", {})
    try:
        look["c"] = T.team_palette("England")
        assert T.apply_streamlit_colours()  # changed: the page runs once more to show them
        assert config.get_option("theme.base") == "light"
        assert config.get_option("theme.sidebar.backgroundColor") == "#15295e"
        assert config.get_option("theme.backgroundColor") == "#eff3f9"
        assert not T.apply_streamlit_colours()  # nothing more to change, so no more runs
        look["c"] = None
        assert T.apply_streamlit_colours()
        assert {k: config.get_option(k) for k in start} == start
    finally:
        for k, v in start.items():
            config.set_option(k, v, "<test>")
