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

from .parser import Match

# --------------------------------------------------------------------------- #
# Vocabulary
# --------------------------------------------------------------------------- #

TEST, ODI, T20I = "Test", "ODI", "T20I"
FIRST_CLASS, LIST_A, T20, HUNDRED = "First-class", "List A", "T20", "The Hundred"
FORMATS = [TEST, ODI, T20I, FIRST_CLASS, LIST_A, T20, HUNDRED]

INTERNATIONAL, DOMESTIC, FRANCHISE = "International", "Domestic", "Franchise"

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

# Cricket Captain 2025 generic titles -> real name by the teams' country
GENERIC = {
    "fc league": (FIRST_CLASS, {"India": "Ranji Trophy", "England": "County Championship",
                                "Australia": "Sheffield Shield", "New Zealand": "Plunket Shield"}),
    "one day cup": (LIST_A, {"India": "Vijay Hazare Trophy", "England": "One-Day Cup",
                             "Australia": "Marsh One-Day Cup", "New Zealand": "Ford Trophy"}),
}

INTERNATIONAL_RE = re.compile(
    r"^(?P<no>\d+)(?:st|nd|rd|th)\s+(?P<kind>test match|test|one day international|odi|"
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


def _team_country(team: str) -> str:
    if team in COUNTRIES:
        return team
    base = re.sub(r"\s+CC$", "", team.strip())  # CC2025: "Kerala CC", "Mumbai CC"
    for country, teams in DOMESTIC_TEAMS.items():
        if base in teams:
            return country
    return ""


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

    # 1. bilateral internationals: "2nd One Day International (of 5)"
    if m := INTERNATIONAL_RE.match(name):
        fmt = INTERNATIONAL_KIND[m.group("kind").lower()]
        return Classification(fmt, fmt, INTERNATIONAL, stage=stage, knockout=knockout)

    key = name.lower()
    # 2. real competition names (CC2026 and the named CC2025 ones)
    if key in KNOWN:
        comp, fmt, level, country = KNOWN[key]
        if not fmt:  # e.g. Asia Cup is played as ODI or T20I
            fmt = T20I if _shape_format(match) == T20 else ODI
        return Classification(comp, fmt, level, country, stage, knockout)

    # 3. CC2025 generic names: pick the real competition by the teams' country
    if key in GENERIC:
        fmt, by_country = GENERIC[key]
        country = _team_country(match.team1) or _team_country(match.team2)
        comp = by_country.get(country, f"{name} ({country})" if country else name)
        return Classification(comp, fmt, DOMESTIC, country, stage, knockout)

    # 4. unknown title: keep the name, infer the format from the scorecard
    shape = _shape_format(match)
    if both_countries:
        fmt = {FIRST_CLASS: TEST, LIST_A: ODI, T20: T20I}.get(shape, shape)
        return Classification(name or "Other", fmt, INTERNATIONAL, "", stage, knockout,
                               recognised=False)
    country = _team_country(match.team1) or _team_country(match.team2)
    return Classification(name or "Other", shape, DOMESTIC, country, stage, knockout,
                          recognised=False)


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
        if no is None:
            continue
        key = (fmt, frozenset((t1, t2)), of)
        prev = open_series.get(key)
        if prev and no > prev[1] and d - prev[2] <= timedelta(days=60):
            sid = prev[0]
        else:
            counter += 1
            sid = f"{fmt}-{counter}"
        open_series[key] = (sid, no, d)
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
