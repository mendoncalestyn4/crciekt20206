"""The game's name files: every competition and team is understood under its real
name and under the game's own name, national sides (associates too) are
internationals, World XI games and tour games have sections of their own, and a
name changed later in the game's files is picked up from those files."""
import copy
import os
from pathlib import Path

import pytest

from ccstats import competitions as C
from ccstats import fixtures as FX
from ccstats import local as L
from ccstats import names as NM
from ccstats.loader import Career
from ccstats.parser import parse_scorecard

HERE = Path(__file__).parent
FIXTURES = HERE / "fixtures"
NAME_FILES = HERE / "fixtures_names"

TEMPLATE = {  # a scorecard of each format, to put other teams and titles on
    "First-class": "24_sep_2026-som_v_sry_county_-_d1.txt",
    "List A": "16_jul_2026-eng_v_ind_2nd_odi.txt",
    "T20": "10_jul_2026-wrc_v_glc_blast_-_s.txt",
    "The Hundred": "1_aug_2026-brm_v_cdf_hundred.txt",
    "Test": "19_aug_2026-eng_v_pak_1st_tst.txt",
}


def match(fmt, team1, team2, title):
    m = parse_scorecard((FIXTURES / TEMPLATE[fmt]).read_text(), TEMPLATE[fmt])
    m.team1, m.team2, m.title = team1, team2, title
    return m


def card(fmt, team1, team2, title, when):
    """A whole scorecard text: the template's teams renamed everywhere, and a new title and date."""
    text = (FIXTURES / TEMPLATE[fmt]).read_text()
    m = parse_scorecard(text, TEMPLATE[fmt])
    lines = text.splitlines()
    at = lines.index(f"{m.team1} v {m.team2}")
    lines[at + 1] = f"{title} - {when}"
    text = "\n".join(lines) + "\n"
    for old, new in ((m.team1, "\x00one\x00"), (m.team2, "\x00two\x00"), ("\x00one\x00", team1), ("\x00two\x00", team2)):
        text = text.replace(old, new)
    return text


def teams_of(country):
    return [real for c, _, real in NM.TEAMS if c == country]


@pytest.fixture
def fresh_names():
    """Names learned in a test are forgotten after it.  Yields a function that forgets them there and then (what
    a new start of the site knows)."""
    saved = {k: copy.deepcopy(getattr(C, k)) for k in ("KNOWN", "SHARED", "SHIPPED", "COUNTRIES", "DOMESTIC_TEAMS",
                                                         "WORLD_XI")}
    nations, read = set(FX.NATIONS), dict(L._names_read)

    def forget():
        for k, v in saved.items():
            target = getattr(C, k)
            target.clear()
            target.update(copy.deepcopy(v))
        FX.NATIONS.clear()
        FX.NATIONS.update(nations)
        L._names_read.clear()
        L._names_read.update(read)
    yield forget
    forget()


# --------------------------------------------------------------------------- the files themselves
def test_the_built_in_lists_are_exactly_the_game_files():
    comps = NM.parse_comp_file((NAME_FILES / NM.COMP_FILE).read_text(encoding="utf-8-sig"))
    teams = NM.parse_team_file((NAME_FILES / NM.TEAM_FILE).read_text(encoding="utf-8-sig"))
    assert comps == NM.COMPETITIONS and len(comps) == 45
    assert teams == NM.TEAMS and len(teams) == 237


def test_names_are_read_as_the_game_prints_them():
    for country, shipped, real in NM.COMPETITIONS + NM.TEAMS:
        assert real == real.strip() and shipped == shipped.strip(), real  # Sri Lankan lines end in spaces
        assert country and real and shipped
        assert len(real) <= 40, real  # the game cuts names at 40 letters
    assert NM.parse_comp_file("England : 20 Over Trophy,T20 Blast,Blast\n# a note\n\nbad line\n") == [
        ("England", "20 Over Trophy", "T20 Blast")]
    # a line without a new name keeps the game's own
    assert NM.parse_comp_file("Ireland : FC League") == [("Ireland", "FC League", "FC League")]
    assert NM.parse_team_file("# === Ireland ===\nMunster,Munster Reds,MUN\n[x]\nLeinster\n") == [
        ("Ireland", "Munster", "Munster Reds"), ("Ireland", "Leinster", "Leinster")]


# --------------------------------------------------------------------------- every competition, both names
# real name -> (the site's name, format, level); the country is the file's.  "" = from the scorecard's shape
EXPECTED = {
    "County Championship": ("County Championship", "First-class", "Domestic"),
    "Metro Bank One Day Cup": ("One-Day Cup", "List A", "Domestic"),
    "T20 Blast": ("T20 Blast", "T20", "Domestic"),
    "The Hundred": ("The Hundred", "The Hundred", "Franchise"),
    "Sheffield Shield": ("Sheffield Shield", "First-class", "Domestic"),
    "Marsh One-Day Cup": ("Marsh One-Day Cup", "List A", "Domestic"),
    "Big Bash League": ("Big Bash League", "T20", "Franchise"),
    "Ranji Trophy": ("Ranji Trophy", "First-class", "Domestic"),
    "Vijay Hazare Trophy": ("Vijay Hazare Trophy", "List A", "Domestic"),
    "Syed Mushtaq Ali Trophy": ("Syed Mushtaq Ali Trophy", "T20", "Domestic"),
    "Indian Premier League": ("Indian Premier League", "T20", "Franchise"),
    "Plunket Shield": ("Plunket Shield", "First-class", "Domestic"),
    "Ford Trophy": ("Ford Trophy", "List A", "Domestic"),
    "Super Smash": ("Super Smash", "T20", "Domestic"),
    "CSA 4-Day Series": ("CSA 4-Day Series", "First-class", "Domestic"),
    "CSA One-Day Cup": ("CSA One-Day Cup", "List A", "Domestic"),
    "CSA T20 Challenge": ("CSA T20 Challenge", "T20", "Domestic"),
    "CSA T20 Knock-Out": ("CSA T20 Knock-Out", "T20", "Domestic"),
    "SA20": ("SA20", "T20", "Franchise"),
    "West Indies Championship": ("West Indies Championship", "First-class", "Domestic"),
    "Super50 Cup": ("Super50 Cup", "List A", "Domestic"),
    "Caribbean Premier League": ("Caribbean Premier League", "T20", "Franchise"),
    "Quaid-e-Azam Trophy": ("Quaid-e-Azam Trophy", "First-class", "Domestic"),
    "President's Trophy": ("President's Trophy", "", "Domestic"),
    "Pakistan Cup": ("Pakistan Cup", "List A", "Domestic"),
    "National T20 Cup": ("National T20 Cup ({country})", "T20", "Domestic"),
    "Pakistan Super League": ("Pakistan Super League", "T20", "Franchise"),
    "National Cricket League": ("National Cricket League", "First-class", "Domestic"),
    "Dhaka Premier Division Cricket League": ("Dhaka Premier Division Cricket League", "List A", "Domestic"),
    "NCL T20": ("NCL T20", "T20", "Domestic"),
    "Bangladesh Premier League": ("Bangladesh Premier League", "T20", "Franchise"),
    "Ahmad Shah Abdali First Class Tournament": ("Ahmad Shah Abdali First Class Tournament", "First-class",
                                                 "Domestic"),
    "Ghazi Amanullah Khan Regional One Day To": ("Ghazi Amanullah Khan Regional One Day To", "List A", "Domestic"),
    "Shpageeza Cricket League": ("Shpageeza Cricket League", "T20", "Franchise"),
    "Inter-Provincial Championship": ("Inter-Provincial Championship", "First-class", "Domestic"),
    "Inter-Provincial Cup": ("Inter-Provincial Cup", "List A", "Domestic"),
    "Inter-Provincial Trophy": ("Inter-Provincial Trophy", "T20", "Domestic"),
    "Major League Tournament": ("Major League Tournament", "First-class", "Domestic"),
    "Major Clubs Limited Over Tournament": ("Major Clubs Limited Over Tournament", "List A", "Domestic"),
    "Major Clubs T20 Tournament": ("Major Clubs T20 Tournament", "T20", "Domestic"),
    "Lanka Premier League": ("Lanka Premier League", "T20", "Franchise"),
    "Logan Cup": ("Logan Cup", "First-class", "Domestic"),
    "Pro50 Championship": ("Pro50 Championship", "List A", "Domestic"),
    "Domestic T20 Competition": ("Domestic T20 Competition", "T20", "Domestic"),
}


def test_every_competition_in_the_file_is_listed_here():
    assert {real for _, _, real in NM.COMPETITIONS} == set(EXPECTED)


@pytest.mark.parametrize("country,shipped,real", NM.COMPETITIONS, ids=[f"{c}:{r}" for c, _, r in NM.COMPETITIONS])
def test_every_competition_by_both_names(country, shipped, real):
    comp, fmt, level = EXPECTED[real]
    comp = comp.format(country=country)
    home, away = teams_of(country)[:2]
    shapes = [fmt] if fmt else ["First-class", "List A", "T20"]  # played as the game sees fit: its shape says
    for shape in shapes:
        for title in (real, shipped, f"{real} - Final", f"{shipped} - Semi-Final"):
            c = C.classify(match(shape, home, away, title))
            assert (c.competition, c.format, c.level, c.country) == (comp, shape, level, country), title
            assert c.recognised and not c.neutral
            assert c.knockout == ("Final" in title or "Semi" in title)
            assert C.section_of(c.competition, c.stage, c.format, c.level) == comp


def test_a_name_two_countries_use_is_two_competitions():
    pak = C.classify(match("T20", "Lahore Region Whites", "Karachi Whites", "National T20 Cup"))
    afg = C.classify(match("T20", teams_of("Afghanistan")[0], teams_of("Afghanistan")[1], "National T20 Cup"))
    assert pak.competition == "National T20 Cup (Pakistan)" and pak.country == "Pakistan"
    assert afg.competition == "National T20 Cup (Afghanistan)" and afg.country == "Afghanistan"
    # teams the site can't place: the name as printed, still a T20 competition
    who = C.classify(match("T20", "Some Side", "Other Side", "National T20 Cup"))
    assert (who.competition, who.format, who.country) == ("National T20 Cup", "T20", "")


def test_the_games_own_names_go_by_the_teams_country():
    for country, comp in (("India", "Ranji Trophy"), ("New Zealand", "Plunket Shield"), ("Zimbabwe", "Logan Cup"),
                          ("England", "County Championship"), ("Australia", "Sheffield Shield")):
        home, away = teams_of(country)[:2]
        assert C.classify(match("First-class", home, away, "FC League")).competition == comp
    # Cricket Captain 2025's county names ("Kerala CC") still count as their country's
    assert C.classify(match("First-class", "Kerala CC", "Mumbai CC", "FC League")).competition == "Ranji Trophy"
    # a country the site can't tell: the name as printed, with the format it always has
    c = C.classify(match("T20", "Some Side", "Other Side", "20 Over Trophy"))
    assert (c.competition, c.format, c.level) == ("20 Over Trophy", "T20", "Domestic")


def test_every_team_belongs_to_its_country():
    for country, shipped, real in NM.TEAMS:
        for name in (shipped, real):
            if country == "International":
                assert name in (C.WORLD_XI if name.startswith("World XI") else C.COUNTRIES), name
            else:
                assert C._team_country(name) == country, name
                assert name not in C.COUNTRIES, name


# --------------------------------------------------------------------------- national sides
NATIONS = sorted(real for c, _, real in NM.TEAMS if c == "International" and not real.startswith("World XI"))


def test_all_national_sides_are_known():
    assert len(NATIONS) == 31
    for side in ("Denmark", "Bermuda", "Malaysia", "Nigeria", "Saudi Arabia", "Singapore", "Italy", "UAE", "USA"):
        assert side in NATIONS and side in C.COUNTRIES and side in FX.NATIONS
    assert FX.NATIONS == set(NATIONS)


@pytest.mark.parametrize("a,b", list(zip(NATIONS, NATIONS[1:] + NATIONS[:1])))
def test_any_two_national_sides_play_internationals(a, b):
    for fmt, title, want in (("T20", "1st 20 Over International (of 3)", "T20I"),
                             ("List A", "2nd One Day International (of 3)", "ODI"),
                             ("Test", "1st Test Match (of 2)", "Test")):
        c = C.classify(match(fmt, a, b, title))
        assert (c.competition, c.format, c.level) == (want, want, "International")
        assert C.section_of(c.competition, c.stage, c.format, c.level) == {"T20I": "T20Is", "ODI": "ODIs",
                                                                           "Test": "Tests"}[want]
    c = C.classify(match("T20", a, b, "T20 World Cup - Group"))
    assert (c.competition, c.format, c.level, c.neutral) == ("T20 World Cup", "T20I", "International", True)


# --------------------------------------------------------------------------- World XI and tour games
def test_world_xi_games_have_a_section_of_their_own():
    for fmt, title, want in (("Test", "1st Test Match (of 1)", "First-class"),
                             ("List A", "Only One Day International", "List A"),
                             ("T20", "Only 20 Over International", "T20")):
        for a, b in (("World XI A", "World XI B"), ("World XI A", "India"), ("Australia", "World XI B")):
            c = C.classify(match(fmt, a, b, title))
            assert (c.competition, c.format, c.level) == (f"World XI · {want}", want, "Exhibition"), (a, b, title)
            assert C.section_of(c.competition, c.stage, c.format, c.level) == f"World XI · {want}"


def test_tour_games_have_a_section_of_their_own():
    for a, b in (("India", "Prime Minister's XI"), ("Cricket Australia XI", "England"), ("South Africa", "SA Under-19s"),
                 ("Somerset", "India"), ("Pakistan", "Mumbai Indians")):
        c = C.classify(match("First-class", a, b, "Tour Match"))
        assert (c.competition, c.format, c.level) == ("Tour matches · First-class", "First-class", "Tour"), (a, b)
        c = C.classify(match("T20", a, b, "Tour Match"))
        assert (c.competition, c.format, c.level) == ("Tour matches · T20", "T20", "Tour"), (a, b)
    # titled like an international, against a known tour side: still a tour game (a Test is a first-class game)
    c = C.classify(match("Test", "India", "Prime Minister's XI", "Only Test Match"))
    assert (c.competition, c.format, c.level) == ("Tour matches · First-class", "First-class", "Tour")


def test_a_side_the_site_has_not_heard_of_in_an_international_stays_international():
    # a national side renamed in the game's files the site hasn't read: still a Test, still a World Cup game
    c = C.classify(match("Test", "England", "Holland", "1st Test Match (of 2)"))
    assert (c.competition, c.level) == ("Test", "International")
    c = C.classify(match("T20", "Holland", "India", "T20 World Cup - Group"))
    assert (c.competition, c.level) == ("T20 World Cup", "International")
    # two sides that aren't countries: the competition decides, as before
    c = C.classify(match("T20", "Somerset", "Surrey", "T20 Blast"))
    assert (c.competition, c.level) == ("T20 Blast", "Domestic")


def test_a_career_keeps_world_xi_and_tour_games_apart():
    cards = [
        ("a.txt", card("Test", "England", "Pakistan", "1st Test Match (of 2)", "1 Jul 2027")),
        ("b.txt", card("Test", "England", "Pakistan", "2nd Test Match (of 2)", "12 Jul 2027")),
        ("c.txt", card("First-class", "Pakistan", "Somerset", "Tour Match", "20 Jun 2027")),
        ("d.txt", card("T20", "World XI A", "World XI B", "Only 20 Over International", "3 Dec 2027")),
        ("e.txt", card("T20", "World XI A", "World XI B", "Only 20 Over International", "8 Jan 2028")),
        ("f.txt", card("T20", "Denmark", "Bermuda", "1st 20 Over International (of 2)", "1 Feb 2028")),
    ]
    career = Career.build("names", [(n, t.encode()) for n, t in cards])
    assert not [r for r in career.report if r.status != "loaded"]
    m = career.matches.set_index("source")
    assert list(m.loc[["a.txt", "b.txt"], "section"]) == ["Tests", "Tests"]
    assert m.at["c.txt", "section"] == "Tour matches · First-class" and m.at["c.txt", "level"] == "Tour"
    assert list(m.loc[["d.txt", "e.txt"], "section"]) == ["World XI · T20"] * 2
    assert m.at["f.txt", "section"] == "T20Is"
    # calendar years, like internationals (December and January are two seasons)
    assert list(m.loc[["c.txt", "d.txt", "e.txt"], "season"]) == ["2027", "2027", "2028"]
    # the Test series is the two Tests only, and no Test player's record has the tour game in it
    assert m.loc[["a.txt", "b.txt"], "series_id"].nunique() == 1 and m.at["c.txt", "series_id"] == ""
    tests = set(career.matches[career.matches.section == "Tests"].match_id)
    assert tests == set(m.loc[["a.txt", "b.txt"], "match_id"])


# --------------------------------------------------------------------------- your schedule
def test_the_schedule_knows_every_national_side():
    known = sorted({"India", "Chennai Super Kings"} | FX.NATIONS)
    for line, opp, fmt in (("United Arab Emirates 3 T20s", "UAE", "T20I"), ("v UAE 2 ODIs", "UAE", "ODI"),
                           ("Italy 3 T20s", "Italy", "T20I"), ("v Denmark 2 ODIs", "Denmark", "ODI"),
                           ("v United States of America 2 T20s", "USA", "T20I"), ("Bermuda 1 T20", "Bermuda", "T20I"),
                           ("v Saudi Arabia 3 T20s", "Saudi Arabia", "T20I"), ("CSK 2 T20s", "Chennai Super Kings", "T20")):
        rows, err = FX.parse_line(line, "India", known)
        assert not err and rows, (line, err)
        assert {(r["opponent"], r["format"]) for r in rows} == {(opp, fmt)}, line


# --------------------------------------------------------------------------- a later rename, from the game's files
def write_names(folder, comps, teams):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / NM.COMP_FILE).write_text(comps, encoding="utf-8")
    (folder / NM.TEAM_FILE).write_text(teams, encoding="utf-8")


def test_a_rename_in_the_games_files_is_understood(tmp_path, fresh_names):
    game = tmp_path / "Cricket Captain 2026"
    scorecards = game / "Scorecards"
    scorecards.mkdir(parents=True)
    write_names(game, "England : 20 Over Trophy,County T20 Bash,Blast\nIndia : Domestic 20 Over,Mushtaq T20,SMAT\n",
                "# === International ===\nNetherlands,Holland,HOL\n# === England ===\nSomerset,Somerset Sabres,SOM\n")
    # before: names the site can't place
    assert not C.classify(match("T20", "Somerset Sabres", "Surrey", "County T20 Bash")).recognised
    assert NM.find_edit_files(scorecards) == {"comp": game / NM.COMP_FILE, "team": game / NM.TEAM_FILE}
    assert L.use_game_names(scorecards) is True
    assert L.use_game_names(scorecards) is False  # read once, until the files change
    # a renamed competition stays the same competition, so its records carry on under one name
    c = C.classify(match("T20", "Somerset Sabres", "Surrey", "County T20 Bash"))
    assert (c.competition, c.format, c.level, c.country, c.recognised) == ("T20 Blast", "T20", "Domestic", "England",
                                                                          True)
    smat = C.classify(match("T20", "Mumbai", "Delhi Capitals", "Mushtaq T20"))
    assert smat.competition == "Syed Mushtaq Ali Trophy"
    # a renamed country is a country: Holland v England is a T20I, Holland v a county a tour game
    assert "Holland" in C.COUNTRIES and "Holland" in FX.NATIONS
    assert C.classify(match("T20", "Holland", "Somerset Sabres", "Tour Match")).level == "Tour"
    assert C.classify(match("T20", "Holland", "England", "1st 20 Over International (of 3)")).competition == "T20I"
    # the file changes: read again
    write_names(game, "England : 20 Over Trophy,Blast 2028,Blast\n", "")
    os.utime(game / NM.COMP_FILE, ns=(1, 1))
    assert L.use_game_names(scorecards) is True
    assert C.classify(match("T20", "Somerset", "Surrey", "Blast 2028")).competition == "T20 Blast"


def test_a_shared_name_stays_shared_after_a_rename(tmp_path, fresh_names):
    # Afghanistan's T20 renamed: Pakistan's National T20 Cup keeps its name, so its section doesn't change
    write_names(tmp_path, "Pakistan : 20 Over Trophy,National T20 Cup,NT20\n"
                          "Afghanistan : Domestic 20 Over,Afghan T20 Cup,AT20\n", "")
    assert L.use_game_names(tmp_path / "Scorecards") is True
    pak = C.classify(match("T20", "Lahore Region Whites", "Karachi Whites", "National T20 Cup"))
    assert pak.competition == "National T20 Cup (Pakistan)"
    afg_teams = teams_of("Afghanistan")
    afg = C.classify(match("T20", afg_teams[0], afg_teams[1], "Afghan T20 Cup"))
    assert (afg.competition, afg.country) == ("National T20 Cup (Afghanistan)", "Afghanistan")


def test_bad_or_missing_name_files_change_nothing(tmp_path, fresh_names):
    before = copy.deepcopy(C.KNOWN)
    assert L.use_game_names(None) is False
    assert L.use_game_names(tmp_path / "nowhere" / "Scorecards") is False
    (tmp_path / NM.COMP_FILE).write_bytes(b"\xff\xfe\x00garbage\x00\n:::,,,\n")
    (tmp_path / NM.TEAM_FILE).mkdir()  # a folder where a file should be
    L.use_game_names(tmp_path / "Scorecards")
    assert all(C.KNOWN[k] == v for k, v in before.items())
    assert C.classify(match("T20", "Somerset", "Surrey", "T20 Blast")).competition == "T20 Blast"


def test_a_watched_career_reads_the_names_before_its_matches(tmp_path, fresh_names):
    game = tmp_path / "Cricket Captain 2026"
    scorecards = game / "Scorecards"
    scorecards.mkdir(parents=True)
    write_names(game, "England : 20 Over Trophy,County T20 Bash,Blast\n", "")
    (scorecards / "x.txt").write_text(card("T20", "Somerset", "Surrey", "County T20 Bash", "4 Jul 2027"))
    store = L.CareerStore(tmp_path / "home")
    result = L.Watcher(store).create("Mine", scorecards)
    assert list(result.career.matches.competition) == ["T20 Blast"]
    # loading it again after a new start of the site understands it the same way
    fresh_names()
    assert not C.classify(match("T20", "Somerset", "Surrey", "County T20 Bash")).recognised
    career, _ = store.load("Mine")
    assert list(career.matches.competition) == ["T20 Blast"]


def test_a_renamed_world_xi_is_still_a_world_xi(tmp_path, fresh_names):
    write_names(tmp_path, "", "# === International ===\nWorld XI A,Rest of the World,ROW\nIreland,Ireland,IRE\n")
    assert L.use_game_names(tmp_path / "Scorecards") is True
    assert "Rest of the World" in C.WORLD_XI and "Rest of the World" not in C.COUNTRIES
    assert "Rest of the World" not in FX.NATIONS
    c = C.classify(match("T20", "Rest of the World", "World XI B", "Only 20 Over International"))
    assert (c.competition, c.level) == ("World XI · T20", "Exhibition")


def test_the_data_check_page_says_which_names_it_could_not_place(monkeypatch, tmp_path):
    from streamlit.testing.v1 import AppTest
    cards = [("a.txt", card("T20", "Somerset", "Surrey", "Somerset Summer Bash", "4 Jul 2027")),
             ("b.txt", card("T20", "Somerset", "Surrey", "T20 Blast", "6 Jul 2027"))]
    career = Career.build("dc-names", [(n, t.encode()) for n, t in cards])
    monkeypatch.setattr(NM, "find_edit_files", lambda folder, also=(): {"comp": tmp_path / NM.COMP_FILE})
    at = AppTest.from_file(str(HERE.parent / "views" / "data_check.py"), default_timeout=60)
    at.session_state["career_obj"] = career
    at.run()
    assert not at.exception, at.exception
    text = " ".join(m.value for m in at.markdown)
    assert "1 game in competitions the site doesn't know by name (Somerset Summer Bash)" in text
    assert f"Names from your name files in `{tmp_path}`" in text
