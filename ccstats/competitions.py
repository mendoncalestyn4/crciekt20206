"""Work out which competition, format, stage and season a match belongs to.

The second header line of a scorecard carries almost everything::

    1st Test Match (of 3) - 9 Oct 2026          international series
    World Cup 20 - Final - 11 Mar 2026          ICC event + stage
    Indian Premier League - Qualifier 2 - ...   franchise league + stage
    County Championship - D1 - 24 Sep 2026      domestic league + division
    T20 Blast - Qtr-Final - 15 Jul 2026         domestic cup + stage

Cricket Captain 2026 uses the real competition names, so the title decides
the competition.  Cricket Captain 2025 used generic names ("FC League",
"One Day Cup") for some domestic competitions; for those the teams' country
picks the real competition.  The shape of the match (overs, balls, innings)
is only used when a title is not recognised at all.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta

from . import names as NM
from .parser import Match

# --------------------------------------------------------------------------- #
# Vocabulary
# --------------------------------------------------------------------------- #

TEST, ODI, T20I = "Test", "ODI", "T20I"
FIRST_CLASS, LIST_A, T20, HUNDRED = "First-class", "List A", "T20", "The Hundred"
FORMATS = [TEST, ODI, T20I, FIRST_CLASS, LIST_A, T20, HUNDRED]

INTERNATIONAL, DOMESTIC, FRANCHISE = "International", "Domestic", "Franchise"
# not part of anyone's international or domestic record: World XI games, and tour (warm-up) games
EXHIBITION, TOUR = "Exhibition", "Tour"
WORLD_XI_SECTION, TOUR_SECTION = "World XI", "Tour matches"

COUNTRIES = {
    "England", "Australia", "India", "Pakistan", "South Africa", "New Zealand", "Sri Lanka",
    "West Indies", "Bangladesh", "Zimbabwe", "Afghanistan", "Ireland", "Scotland",
    "Netherlands", "Nepal", "Namibia", "Oman", "UAE", "United Arab Emirates", "USA",
    "United States", "Canada", "Kenya", "Hong Kong", "Papua New Guinea", "Uganda", "Italy",
}

# Domestic sides by country.  Only needed for CC2025's generic titles.
DOMESTIC_TEAMS = {
    "India": {
        "Andhra", "Arunachal Pradesh", "Assam", "Baroda", "Bengal", "Bihar", "Chandigarh",
        "Chhattisgarh", "Delhi", "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Hyderabad",
        "Jammu & Kashmir", "Jammu and Kashmir", "Jharkhand", "Karnataka", "Kerala",
        "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Mumbai",
        "Nagaland", "Odisha", "Puducherry", "Punjab", "Railways", "Rajasthan", "Saurashtra",
        "Services", "Sikkim", "Tamil Nadu", "Tripura", "Uttar Pradesh", "Uttarakhand",
        "Vidarbha",
    },
    "England": {
        "Derbyshire", "Durham", "Essex", "Glamorgan", "Gloucestershire", "Hampshire", "Kent",
        "Lancashire", "Leicestershire", "Middlesex", "Northamptonshire", "Nottinghamshire",
        "Somerset", "Surrey", "Sussex", "Warwickshire", "Worcestershire", "Yorkshire",
    },
    "Australia": {
        "New South Wales", "Queensland", "South Australia", "Tasmania", "Victoria",
        "Western Australia",
    },
    "New Zealand": {
        "Auckland", "Canterbury", "Central Districts", "Northern Districts", "Otago",
        "Wellington",
    },
}

# title (lower case) -> (competition, format, level, country)
KNOWN = {
    # ICC events
    "world cup": ("ODI World Cup", ODI, INTERNATIONAL, ""),
    "world cup 20": ("T20 World Cup", T20I, INTERNATIONAL, ""),
    "t20 world cup": ("T20 World Cup", T20I, INTERNATIONAL, ""),
    "champions trophy": ("Champions Trophy", ODI, INTERNATIONAL, ""),
    "world test championship final": ("World Test Championship Final", TEST, INTERNATIONAL, ""),
    "world test championship": ("World Test Championship Final", TEST, INTERNATIONAL, ""),  # "… - Final - date"
    "asia cup": ("Asia Cup", "", INTERNATIONAL, ""),
    # England
    "county championship": ("County Championship", FIRST_CLASS, DOMESTIC, "England"),
    "t20 blast": ("T20 Blast", T20, DOMESTIC, "England"),
    "vitality blast": ("T20 Blast", T20, DOMESTIC, "England"),
    "one-day cup": ("One-Day Cup", LIST_A, DOMESTIC, "England"),
    "metro bank one day cup": ("One-Day Cup", LIST_A, DOMESTIC, "England"),
    "the hundred": ("The Hundred", HUNDRED, FRANCHISE, "England"),
    # India
    "ranji trophy": ("Ranji Trophy", FIRST_CLASS, DOMESTIC, "India"),
    "duleep trophy": ("Duleep Trophy", FIRST_CLASS, DOMESTIC, "India"),
    "irani cup": ("Irani Cup", FIRST_CLASS, DOMESTIC, "India"),
    "irani trophy": ("Irani Cup", FIRST_CLASS, DOMESTIC, "India"),
    "vijay hazare trophy": ("Vijay Hazare Trophy", LIST_A, DOMESTIC, "India"),
    "syed mushtaq ali trophy": ("Syed Mushtaq Ali Trophy", T20, DOMESTIC, "India"),
    "indian premier league": ("Indian Premier League", T20, FRANCHISE, "India"),
    # Rest of the world
    "sheffield shield": ("Sheffield Shield", FIRST_CLASS, DOMESTIC, "Australia"),
    "marsh one-day cup": ("Marsh One-Day Cup", LIST_A, DOMESTIC, "Australia"),
    "big bash league": ("Big Bash League", T20, FRANCHISE, "Australia"),
    "plunket shield": ("Plunket Shield", FIRST_CLASS, DOMESTIC, "New Zealand"),
    "ford trophy": ("Ford Trophy", LIST_A, DOMESTIC, "New Zealand"),
    "super smash": ("Super Smash", T20, DOMESTIC, "New Zealand"),
    "sa20": ("SA20", T20, FRANCHISE, "South Africa"),
    "pakistan super league": ("Pakistan Super League", T20, FRANCHISE, "Pakistan"),
    "quaid-e-azam trophy": ("Quaid-e-Azam Trophy", FIRST_CLASS, DOMESTIC, "Pakistan"),
    "caribbean premier league": ("Caribbean Premier League", T20, FRANCHISE, "West Indies"),
    "bangladesh premier league": ("Bangladesh Premier League", T20, FRANCHISE, "Bangladesh"),
    "lanka premier league": ("Lanka Premier League", T20, FRANCHISE, "Sri Lanka"),
    "major league cricket": ("Major League Cricket", T20, FRANCHISE, "USA"),
    "ilt20": ("ILT20", T20, FRANCHISE, "UAE"),
}

# --------------------------------------------------------------------------- #
# The game's own names, and the real names you can give them (see names.py)
# --------------------------------------------------------------------------- #

# The competitions in the game's name file the list above doesn't have: their format and level ("" = from the
# scorecard itself: Pakistan's President's Trophy is played as the game sees fit)
REAL_FORMATS = {
    "CSA 4-Day Series": (FIRST_CLASS, DOMESTIC), "CSA One-Day Cup": (LIST_A, DOMESTIC),
    "CSA T20 Challenge": (T20, DOMESTIC), "CSA T20 Knock-Out": (T20, DOMESTIC),
    "West Indies Championship": (FIRST_CLASS, DOMESTIC), "Super50 Cup": (LIST_A, DOMESTIC),
    "President's Trophy": ("", DOMESTIC), "Pakistan Cup": (LIST_A, DOMESTIC), "National T20 Cup": (T20, DOMESTIC),
    "National Cricket League": (FIRST_CLASS, DOMESTIC), "Dhaka Premier Division Cricket League": (LIST_A, DOMESTIC),
    "NCL T20": (T20, DOMESTIC), "Ahmad Shah Abdali First Class Tournament": (FIRST_CLASS, DOMESTIC),
    "Ghazi Amanullah Khan Regional One Day To": (LIST_A, DOMESTIC),  # the game cuts names at 40 letters
    "Shpageeza Cricket League": (T20, FRANCHISE), "Inter-Provincial Championship": (FIRST_CLASS, DOMESTIC),
    "Inter-Provincial Cup": (LIST_A, DOMESTIC), "Inter-Provincial Trophy": (T20, DOMESTIC),
    "Major League Tournament": (FIRST_CLASS, DOMESTIC), "Major Clubs Limited Over Tournament": (LIST_A, DOMESTIC),
    "Major Clubs T20 Tournament": (T20, DOMESTIC), "Logan Cup": (FIRST_CLASS, DOMESTIC),
    "Pro50 Championship": (LIST_A, DOMESTIC), "Domestic T20 Competition": (T20, DOMESTIC),
}
KNOWN["ghazi amanullah khan regional one day tournament"] = ("Ghazi Amanullah Khan Regional One Day To", LIST_A,
                                                             DOMESTIC, "Afghanistan")

# a real name used by more than one country ("National T20 Cup": Pakistan's and Afghanistan's): (name) -> {country:
# entry}; each country's is a competition of its own, named with the country
SHARED: dict[str, dict[str, tuple]] = {}
# the game's own names (lower case) -> {country: the real competition's key in KNOWN or SHARED}.  Most are used by
# several countries ("FC League", "One Day Cup", "20 Over Trophy", "Domestic 20 Over"), so the teams' country picks
SHIPPED: dict[str, dict[str, str]] = {}
# the format of a game's own name when the country can't be told (Cricket Captain 2025 used some of these)
SHIPPED_FORMAT = {"fc league": FIRST_CLASS, "one day cup": LIST_A, "20 over trophy": T20, "domestic 20 over": T20}

WORLD_XI: set[str] = set()


def learn_names(competitions: list[tuple[str, str, str]], teams: list[tuple[str, str, str]]) -> None:
    """Take in names from the game's name files: (country, the game's name, the name scorecards print)."""
    by_country_real: dict[str, set[str]] = {}
    for country, shipped, real in competitions:
        by_country_real.setdefault(real.lower(), set()).add(country)
    for country, shipped, real in competitions:
        key = real.lower()
        if (len(by_country_real[key]) > 1 or key in SHARED) and key not in KNOWN:  # once shared, always shared
            fmt, level = REAL_FORMATS.get(real, ("", DOMESTIC))
            SHARED.setdefault(key, {})[country] = (f"{real} ({country})", fmt, level, country)
        elif key not in KNOWN:
            # a name the site doesn't have: the competition the game's own name was in this country (renamed again:
            # it carries on as the same competition), else a new one with its known format
            base = SHIPPED.get(shipped.lower(), {}).get(country)
            was = KNOWN.get(base) or SHARED.get(base, {}).get(country)
            if was:
                KNOWN[key] = was
            else:
                fmt, level = REAL_FORMATS.get(real, ("", DOMESTIC))
                KNOWN[key] = (real, fmt, level, country)
        if shipped.lower() not in KNOWN:  # "English FC League" is the County Championship whatever it's called
            SHIPPED.setdefault(shipped.lower(), {})[country] = key
    for country, shipped, real in teams:
        world = shipped.startswith("World XI") or real.startswith("World XI")  # "World XI A", whatever it's called
        for name in {shipped, real}:
            if country == "International":
                (WORLD_XI if world else COUNTRIES).add(name)
            elif country:
                DOMESTIC_TEAMS.setdefault(country, set()).add(name)


# Cricket Captain 2025's generic titles for England and Australia ("FC League", "One Day Cup")
SHIPPED["fc league"] = {"England": "county championship", "Australia": "sheffield shield"}
SHIPPED["one day cup"] = {"England": "one-day cup"}
learn_names(NM.COMPETITIONS, NM.TEAMS)

INTERNATIONAL_RE = re.compile(
    r"^(?:(?P<no>\d+)(?:st|nd|rd|th)|only)\s+(?P<kind>test match|test|one day international|odi|"
    r"20 over international|t20 international|t20i)(?:\s*\(of\s+(?P<of>\d+)\))?$",
    re.I,
)
INTERNATIONAL_KIND = {
    "test match": TEST, "test": TEST, "one day international": ODI, "odi": ODI,
    "20 over international": T20I, "t20 international": T20I, "t20i": T20I,
}

# stage text (lower case) -> (display name, is knockout)
STAGES = {
    "group match": ("Group", False), "group": ("Group", False),
    "north": ("North Group", False), "south": ("South Group", False),
    "d1": ("Division 1", False), "d2": ("Division 2", False),
    "division 1": ("Division 1", False), "division 2": ("Division 2", False),
    "qtr-final": ("Quarter-final", True), "quarter-final": ("Quarter-final", True),
    "quarter final": ("Quarter-final", True),
    "semi-final": ("Semi-final", True), "semi final": ("Semi-final", True),
    "final": ("Final", True),
    "qualifier 1": ("Qualifier 1", True), "qualifier 2": ("Qualifier 2", True),
    "eliminator": ("Eliminator", True),
    # The Hundred's eliminator (2nd v 3rd) is titled "Preliminary-Final" by the game
    "preliminary-final": ("Eliminator", True), "preliminary final": ("Eliminator", True),
    "play-off": ("Eliminator", True), "playoff": ("Eliminator", True),
}


# --------------------------------------------------------------------------- #
# Classification
# --------------------------------------------------------------------------- #


@dataclass
class Classification:
    competition: str  # "Ranji Trophy", "Test", "ODI World Cup", ...
    format: str  # Test, ODI, T20I, First-class, List A, T20, The Hundred
    level: str  # International, Domestic, Franchise
    country: str = ""  # home of a domestic/franchise competition
    stage: str = ""  # "Division 1", "North Group", "Semi-final", ...
    knockout: bool = False
    recognised: bool = True  # False when we fell back to guessing from the scorecard
    # The first-named team is the home side, except at ICC events (World
    # Cups etc.) where the scorecard doesn't say who hosted: treat as neutral.
    neutral: bool = False


def _team_country(team: str) -> str:
    if team in COUNTRIES:
        return team
    for name in (team.strip(), re.sub(r"\s+CC$", "", team.strip())):  # the game's own "Kerala CC", "Mumbai CC"
        for country, teams in list(DOMESTIC_TEAMS.items()):  # (a copy: names can be learned meanwhile)
            if name in teams:
                return country
    return ""


def _named(key: str, match: Match) -> tuple | None:
    """(competition, format, level, country) for a title the site knows, by its real name or the game's own."""
    if key in KNOWN:
        return KNOWN[key]
    if key not in SHIPPED and key not in SHARED:
        return None
    country = _team_country(match.team1) or _team_country(match.team2)
    if key in SHIPPED:
        to = SHIPPED[key]
        target = to.get(country) or (next(iter(to.values())) if len(to) == 1 else None)
        if target is None:  # the game's own name, from a country the site can't tell: keep it, with its format
            return (f"{match.title.split(' - ')[0].strip()} ({country})" if country else
                    match.title.split(" - ")[0].strip(), SHIPPED_FORMAT.get(key, ""), DOMESTIC, country)
        key = target
        if key in KNOWN:
            return KNOWN[key]
    by_country = SHARED.get(key, {})
    if country in by_country:
        return by_country[country]
    any_ = next(iter(by_country.values()), None)  # a shared name from a country the site can't tell
    return (match.title.split(" - ")[0].strip(), any_[1], any_[2], "") if any_ else None


def _domestic_format(fmt: str) -> str:
    """A World XI or tour game titled like an international ("1st Test Match"): kept out of international
    records, so a Test is first-class, an ODI a one-day game, a T20I a T20."""
    return {TEST: FIRST_CLASS, ODI: LIST_A, T20I: T20}.get(fmt, fmt)


def _shape_format(match: Match) -> str:
    """Best guess from the scorecard itself: balls vs overs, innings, length."""
    if any(i.counted_in_balls for i in match.innings):
        return HUNDRED
    if len(match.innings) > 2:
        return FIRST_CLASS
    max_balls = max((i.balls for i in match.innings), default=0)
    if max_balls <= 20 * 6:
        return T20
    if max_balls <= 50 * 6:
        return LIST_A
    return FIRST_CLASS


def classify(match: Match) -> Classification:
    parts = [p.strip() for p in match.title.split(" - ") if p.strip()]
    name = parts[0] if parts else ""
    stage_raw = parts[1] if len(parts) > 1 else ""
    stage, knockout = STAGES.get(stage_raw.lower(), (stage_raw, False))
    both_countries = match.team1 in COUNTRIES and match.team2 in COUNTRIES
    im = INTERNATIONAL_RE.match(name)
    key = name.lower()
    named = _named(key, match)

    # 0. a World XI game, or a country against a side that isn't one (Prime Minister's XI, SA Under-19s, a county):
    #    in a section of their own, one per format, outside every international and domestic record.  A side the
    #    site doesn't know in an international ("1st Test Match", "T20 World Cup") is a country it hasn't been told
    #    about, so that stays an international
    world = any(t.strip().startswith("World XI") or t.strip() in WORLD_XI for t in (match.team1, match.team2))
    other = match.team2 if match.team1 in COUNTRIES else match.team1
    international_title = bool(im) or bool(named and named[2] == INTERNATIONAL)
    tour = (not world and (match.team1 in COUNTRIES) != (match.team2 in COUNTRIES)
            and (not international_title or bool(_team_country(other))))
    if world or tour:
        fmt = _domestic_format(INTERNATIONAL_KIND[im.group("kind").lower()]) if im else _shape_format(match)
        if named and named[1] and named[2] != INTERNATIONAL:
            fmt = named[1]
        return Classification(f"{WORLD_XI_SECTION if world else TOUR_SECTION} · {fmt}", fmt,
                              EXHIBITION if world else TOUR, "", stage, knockout)

    # 1. bilateral internationals: "2nd One Day International (of 5)"
    if m := im:
        fmt = INTERNATIONAL_KIND[m.group("kind").lower()]
        return Classification(fmt, fmt, INTERNATIONAL, stage=stage, knockout=knockout)

    # 2. competition names the site knows: real ones, and the game's own (by the teams' country where several
    #    countries share one)
    if named:
        comp, fmt, level, country = named
        if not fmt:  # e.g. Asia Cup is played as ODI or T20I; Pakistan's President's Trophy as the game sees fit
            shape = _shape_format(match)
            fmt = (T20I if shape == T20 else ODI) if level == INTERNATIONAL else shape
        if comp.endswith(" Final") and not stage:  # "World Test Championship Final - 16 Jun 2027" is itself a final
            stage, knockout = "Final", True
        return Classification(comp, fmt, level, country, stage, knockout,
                              neutral=level == INTERNATIONAL)

    # 3. unknown title: keep the name, infer the format from the scorecard
    shape = _shape_format(match)
    if both_countries:
        fmt = {FIRST_CLASS: TEST, LIST_A: ODI, T20: T20I}.get(shape, shape)
        return Classification(name or "Other", fmt, INTERNATIONAL, "", stage, knockout,
                               recognised=False)
    country = _team_country(match.team1) or _team_country(match.team2)
    return Classification(name or "Other", shape, DOMESTIC, country, stage, knockout,
                          recognised=False)


# Bilateral internationals are named by format; give them a clear name.
BILATERAL_SECTION = {TEST: "Tests (bilateral series)", ODI: "ODIs (bilateral series)", T20I: "T20Is (bilateral series)"}
# Every international match counts in its format's section, as in real career records.
INTERNATIONAL_SECTION = {TEST: "Tests", ODI: "ODIs", T20I: "T20Is"}


def event_of(competition: str, stage: str) -> str:
    """The competition as it is run: its own table, bracket and champion.
    Bilateral series, the ODI World Cup and the Champions Trophy are separate
    events, and a league with divisions (County Championship) is one per division."""
    name = BILATERAL_SECTION.get(competition, competition)
    if stage.startswith("Division"):
        return f"{name} · {stage}"
    return name


def shown_name(section: str, event: str) -> str:
    """What a match is called on screen: its competition ("ODI World Cup"), or
    just the format for a match in a bilateral series ("ODIs")."""
    return section if event in BILATERAL_SECTION.values() else event


def with_stage(name: str, stage) -> str:
    """'Indian Premier League · Final'. A stage the name already says isn't said twice: a County Championship game's
    stage is its division, and the name is 'County Championship · Division 1' already."""
    stage = "" if stage is None or stage != stage else str(stage)  # (stage != stage: a missing value, NaN)
    return f"{name} · {stage}" if stage and stage not in name.split(" · ") else name


def section_of(competition: str, stage: str, fmt: str = "", level: str = "") -> str:
    """The unit stats are kept within.  International matches are pooled by
    format: every Test (bilateral series and the World Test Championship Final)
    is in "Tests", every ODI (bilateral, World Cup, Champions Trophy, Asia Cup)
    in "ODIs" and every T20I in "T20Is".  Nothing else is merged: each domestic
    and franchise competition, and each County Championship division, is its own
    section."""
    if level == INTERNATIONAL and fmt in INTERNATIONAL_SECTION:
        return INTERNATIONAL_SECTION[fmt]
    return event_of(competition, stage)


# --------------------------------------------------------------------------- #
# Seasons, series and playoff fix-ups (need the whole collection of matches)
# --------------------------------------------------------------------------- #

SEASON_GAP = timedelta(days=120)  # a longer break than this starts a new season


def season_label(start: date, end: date) -> str:
    if start.year == end.year:
        return str(start.year)
    return f"{start.year}/{str(end.year)[-2:]}"


def assign_seasons(items: list[tuple[str, date]]) -> list[str]:
    """Given (competition, date) pairs, return a season label for each.

    Seasons are found from the fixture calendar: within a competition, a gap
    of more than SEASON_GAP starts a new season.  That handles competitions
    that cross the new year (Ranji Trophy Oct-Feb -> "2026/27") the same way
    as ones that don't (IPL Mar-May -> "2026") without hard-coding dates."""
    labels = [""] * len(items)
    by_comp: dict[str, list[int]] = {}
    for idx, (comp, d) in enumerate(items):
        by_comp.setdefault(comp, []).append(idx)
    for idxs in by_comp.values():
        idxs.sort(key=lambda i: items[i][1])
        groups: list[list[int]] = []
        for i in idxs:
            if groups and items[i][1] - items[groups[-1][-1]][1] <= SEASON_GAP:
                groups[-1].append(i)
            else:
                groups.append([i])
        for g in groups:
            label = season_label(items[g[0]][1], items[g[-1]][1])
            for i in g:
                labels[i] = label
    return labels


def assign_series(matches: list[tuple[str, str, str, int | None, int | None, date]]) -> list[str]:
    """Group bilateral internationals into series.

    Each item is (format, team1, team2, match_no, series_length, date).  A
    series is the same two teams, same format and series length, with match
    numbers increasing and no big gap.  Returns a series id per item ('' for
    items that are not part of a numbered series)."""
    ids = [""] * len(matches)
    open_series: dict[tuple, tuple[str, int, date]] = {}
    order = sorted(range(len(matches)), key=lambda i: matches[i][5])
    counter = 0
    for i in order:
        fmt, t1, t2, no, of, d = matches[i]
        if no is None or no != no:  # no match number (NaN from a table counts as none)
            continue
        key = (fmt, frozenset((t1, t2)))
        prev = open_series.get(key)
        # the same series: match numbers go up, no long gap, and the lengths agree
        # where both are printed ("Only Test Match" then "2nd Test Match" print none)
        if prev and no > prev[1] and d - prev[2] <= timedelta(days=60) and (of is None or prev[3] is None or of == prev[3]):
            sid = prev[0]
            of = of if of is not None else prev[3]
        else:
            counter += 1
            sid = f"{fmt}-{counter}"
        open_series[key] = (sid, no, d, of)
        ids[i] = sid
    return ids


def fix_playoff_stages(games: list[dict]) -> None:
    """Cricket Captain titles the IPL Eliminator "Qualifier 1" too.

    `games` are the playoff matches of one competition-season as dicts with
    keys stage, teams (set), loser, date.  Where two games are both called
    Qualifier 1, the real one is the game whose loser goes on to play
    Qualifier 2; the other is renamed Eliminator (falling back to the later
    date if Qualifier 2 is missing)."""
    q1 = [g for g in games if g["stage"] == "Qualifier 1"]
    if len(q1) != 2:
        return
    q2 = next((g for g in games if g["stage"] == "Qualifier 2"), None)
    real = None
    if q2 is not None:
        real = next((g for g in q1 if g["loser"] in q2["teams"]), None)
    if real is None:
        real = min(q1, key=lambda g: g["date"])
    for g in q1:
        if g is not real:
            g["stage"] = "Eliminator"
