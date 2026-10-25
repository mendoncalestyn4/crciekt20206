"""Every team in the game, before it has played a match.

A new save has few scorecards, so a team that hasn't played yet is in no list the scorecards make.  This is the
game's own list of teams (names.py, and any new names from the game's name files), with the competitions each one
plays in, so every page can offer a team from the start (My team, Team vs team, Teams, Opponent preview, Fixtures,
search) and then say plainly that it hasn't played yet.

Only competitions whose sides are certain are filled in ahead of time: the international formats, every franchise
league (its sides are the game's own) and the domestic competitions every side of the country plays in.  A County
Championship division, a tour side or a competition only some sides play lists the teams that have played in it.
"""

from __future__ import annotations

from . import names as NM

# the game's own names, which stay the same whatever a team is called in the game's name file
LEAGUES: dict[str, tuple[str, tuple[str, ...]]] = {
    "Indian Premier League": ("India", ("Bangalore", "Chennai", "Delhi", "Gujarat", "Hyderabad", "Kolkata", "Lucknow",
                                        "Mumbai", "Punjab", "Rajasthan")),
    "Big Bash League": ("Australia", ("Adelaide", "Brisbane", "Hobart", "Melbourne Green", "Melbourne Red", "Perth",
                                      "Sydney Green", "Sydney Pink")),
    "SA20": ("South Africa", ("Cape Town", "Durban", "Eastern Cape", "Johannesburg", "Paarl", "Pretoria")),
    "Caribbean Premier League": ("West Indies", ("Antigua and Barbuda", "Barbados", "Guyana", "Jamaica",
                                                 "Leeward Islands", "Trinidad and Tobago", "Windward Islands")),
    "Pakistan Super League": ("Pakistan", ("Hyderabad PL", "Islamabad", "Karachi", "Lahore", "Multan", "Peshawar",
                                           "Quetta", "Rawalpindi")),
    "Bangladesh Premier League": ("Bangladesh", ("Chittagong", "Dhaka", "Noakhali", "Rajshahi", "Rangpur", "Sylhet")),
    "Lanka Premier League": ("Sri Lanka", ("Colombo", "Dambulla", "Galle", "Jaffna", "Kandy")),
    "The Hundred": ("England", ("Birmingham", "Cardiff", "Leeds", "London Blue", "London Green", "Manchester",
                                "Nottingham", "Southampton")),
}
# domestic competitions every domestic side of the country plays in (the County Championship only as a whole: which
# division a county is in shows once it has played)
EVERY_SIDE = {
    "County Championship": "England", "T20 Blast": "England", "One-Day Cup": "England",
    "Ranji Trophy": "India", "Vijay Hazare Trophy": "India", "Syed Mushtaq Ali Trophy": "India",
    "Sheffield Shield": "Australia", "Marsh One-Day Cup": "Australia",
    "Plunket Shield": "New Zealand", "Ford Trophy": "New Zealand", "Super Smash": "New Zealand",
}
# sides that are in no league: tour sides, an academy, an under-19 side (they show once they've played)
NO_LEAGUE = {("Australia", "Cricket Australia XI"), ("Australia", "Australian Chairman's XI"),
             ("Australia", "Prime Minister's XI"), ("South Africa", "SA Under-19s"),
             ("West Indies", "West Indies Academy")}
# Afghanistan's sides: which play its franchise league and which its domestic competitions isn't certain, so they
# show once they've played
UNSURE_COUNTRIES = {"Afghanistan"}
TEST_NATIONS = {"Afghanistan", "Australia", "Bangladesh", "England", "India", "Ireland", "New Zealand", "Pakistan",
                "South Africa", "Sri Lanka", "West Indies", "Zimbabwe"}
INTERNATIONAL_SECTIONS = ("Tests", "ODIs", "T20Is")

# (country, the game's name) -> the name scorecards print; later names (from the game's name files) replace earlier
_names: dict[tuple[str, str], str] = {}
# (country, the game's name) -> the names it had before (scorecards from before a rename print those)
_before: dict[tuple[str, str], set[str]] = {}


def learn(teams: list[tuple[str, str, str]]) -> None:
    """Take in (country, the game's name, the name scorecards print) from the game's team file."""
    for country, shipped, real in teams:
        if shipped:
            old = _names.get((country, shipped))
            if old and old != (real or shipped):
                _before.setdefault((country, shipped), set()).add(old)
            _names[(country, shipped)] = real or shipped


learn(NM.TEAMS)


def _world_xi(shipped: str, real: str) -> bool:
    return shipped.startswith("World XI") or real.startswith("World XI")


def every_team() -> list[str]:
    """Every team in the game by the name scorecards print (the World XIs left out), A to Z."""
    return sorted({real for (country, shipped), real in _names.items() if not _world_xi(shipped, real)})


def nations() -> set[str]:
    return {real for (country, shipped), real in _names.items() if country == "International" and not _world_xi(shipped, real)}


def _league_of(country: str, shipped: str) -> str:
    return next((lg for lg, (c, sides) in LEAGUES.items() if c == country and shipped in sides), "")


def _domestic(country: str, shipped: str) -> bool:
    return (country not in ("International", "") and country not in UNSURE_COUNTRIES
            and (country, shipped) not in NO_LEAGUE and (country, _names.get((country, shipped), "")) not in NO_LEAGUE
            and not _league_of(country, shipped))


def expected(section: str, competition: str = "") -> set[str]:
    """The teams that belong in a section before they've played in it (the name scorecards print).  `competition`:
    the section's competition, when the section is one part of it (a County Championship division) nobody is added."""
    if section == "Tests":
        return {real for (country, shipped), real in _names.items() if country == "International" and shipped in TEST_NATIONS}
    if section in ("ODIs", "T20Is"):
        return nations()
    comp = competition or section
    if section != comp:  # one division of a league: who is in it shows once they've played
        return set()
    if comp in LEAGUES:
        country, sides = LEAGUES[comp]
        return {_names[(country, s)] for s in sides if (country, s) in _names}
    if comp in EVERY_SIDE:
        country = EVERY_SIDE[comp]
        return {real for (c, shipped), real in _names.items() if c == country and _domestic(c, shipped)}
    return set()


def aliases(team: str) -> set[str]:
    """A team's names: the one scorecards print now, the game's own and any it had before a rename (a scorecard from
    before then prints that)."""
    out = {team}
    for key, real in _names.items():
        if real == team:
            out |= {key[1]} | _before.get(key, set())
    return out


def unplayed(section: str, played: set[str], competition: str = "") -> list[str]:
    """The teams expected in a section that haven't played in it, under any of their names, A to Z."""
    return sorted(t for t in expected(section, competition) if not (aliases(t) & played))


def section_teams(matches, section: str, shown=None) -> tuple[list[str], set[str]]:
    """(every team in the section, A to Z: those that have played and those still to play; the ones still to play).
    `matches`: the section's matches (any season), which say its competition; `shown`: the part of them on screen (one
    season, say), when a team counts as still to play there until it has played in that part."""
    shown = matches if shown is None else shown
    played = set(shown.home) | set(shown.away)
    comp = section if section in INTERNATIONAL_SECTIONS else (
        str(matches.competition.iloc[0]) if len(matches) and "competition" in matches else section)
    todo = set(unplayed(section, played, comp))
    return sorted(played | todo), todo


def rivals(team: str) -> list[str]:
    """The teams a side plays in its own competitions, by the name scorecards print: every nation for a nation, the
    league for a franchise, the country's domestic sides for a domestic side; none for a side in no league.  The name
    scorecards print is looked for first: "Delhi" is the Ranji side, though the IPL side's own name is Delhi too."""
    entries = list(_names.items())
    found = [e for e in entries if e[1] == team] or [e for e in entries if e[0][1] == team]
    for (country, shipped), real in found[:1]:
        if country == "International":
            return sorted(nations() - {team})
        lg = _league_of(country, shipped)
        if lg:
            return sorted(expected(lg) - {team})
        if _domestic(country, shipped):
            return sorted({r for (c, s), r in _names.items() if c == country and _domestic(c, s)} - {team})
    return []


def home_sections(team: str) -> list[str]:
    """The sections a team belongs to before it has played (its league, or every competition its country's sides all
    play, or the international formats)."""
    out = [s for s in INTERNATIONAL_SECTIONS if team in expected(s)]
    out += [lg for lg in LEAGUES if team in expected(lg)]
    out += [comp for comp in EVERY_SIDE if team in expected(comp)]
    return out
