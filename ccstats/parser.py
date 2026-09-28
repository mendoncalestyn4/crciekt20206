"""Parser for Cricket Captain text scorecards.

Cricket Captain can save (or autosave) a plain-text scorecard for every match.
The exact layout has drifted between editions, so this parser is deliberately
tolerant: it looks for the structural landmarks every scorecard has (a
"Team A v Team B" line, "<Team> 1st Innings" headers, batting rows ending in
numbers, "Extras", "Total", a bowling table) rather than fixed columns.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import date

# --------------------------------------------------------------------------- #
# Data classes
# --------------------------------------------------------------------------- #


@dataclass
class BattingEntry:
    player: str
    position: int
    dismissal: str = ""
    how_out: str = "dnb"  # caught, bowled, lbw, stumped, run out, not out, ...
    bowler: str = ""
    fielder: str = ""
    runs: int = 0
    balls: int = 0
    fours: int = 0
    sixes: int = 0
    minutes: int | None = None
    not_out: bool = False
    did_bat: bool = False
    captain: bool = False
    keeper: bool = False


@dataclass
class BowlingEntry:
    player: str
    balls: int
    maidens: int
    runs: int
    wickets: int
    wides: int = 0
    no_balls: int = 0


@dataclass
class FallOfWicket:
    wicket: int
    score: int
    batter: str = ""
    over: str = ""


@dataclass
class Innings:
    team: str
    number: int  # 1..4, the order in the match
    team_innings: int  # 1 or 2 for that team
    batting: list[BattingEntry] = field(default_factory=list)
    bowling: list[BowlingEntry] = field(default_factory=list)
    fow: list[FallOfWicket] = field(default_factory=list)
    extras: int = 0
    byes: int = 0
    leg_byes: int = 0
    wides: int = 0
    no_balls: int = 0
    penalties: int = 0
    total: int | None = None
    wickets: int | None = None
    balls: int | None = None
    declared: bool = False
    bowling_team: str = ""


@dataclass
class Match:
    match_id: str
    source: str
    team1: str = ""
    team2: str = ""
    competition: str = ""
    match_title: str = ""
    venue: str = ""
    date: date | None = None
    toss: str = ""
    result: str = ""
    winner: str = ""
    result_type: str = ""  # win, draw, tie, no result
    margin_runs: int | None = None
    margin_wickets: int | None = None
    innings_win: bool = False
    player_of_match: str = ""
    format: str = ""
    innings: list[Innings] = field(default_factory=list)
    raw: str = ""


class ScorecardError(ValueError):
    """Raised when a file does not look like a scorecard."""


# --------------------------------------------------------------------------- #
# Regexes & vocab
# --------------------------------------------------------------------------- #

MONTHS = {
    m: i + 1
    for i, m in enumerate(
        ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
    )
}

INNINGS_RE = re.compile(
    r"^(?P<team>[A-Za-z][\w .'&()/-]*?)\s*[-–:,]?\s*"
    r"(?:(?P<ord>1st|2nd|first|second)\s+)?innings\b(?P<rest>.*)$",
    re.I,
)
TEAMS_RE = re.compile(r"^(?P<a>.+?)\s+(?:v|vs|v\.|vs\.|versus)\s+(?P<b>.+?)$", re.I)
EXTRAS_RE = re.compile(r"^extras\b", re.I)
TOTAL_RE = re.compile(r"^total\b", re.I)
FOW_RE = re.compile(r"^(?:fall of wickets?|fow)\b", re.I)
DNB_LINE_RE = re.compile(r"^(?:did not bat|dnb|yet to bat)\s*[:\-]\s*(?P<names>.+)$", re.I)
NUM_TOKEN = r"(?:\d+(?:\.\d+)?|-)"
TRAILING_NUMS_RE = re.compile(rf"^(?P<body>.*?\S)\s+(?P<nums>{NUM_TOKEN}(?:\s+{NUM_TOKEN})*)\s*$")
BOWL_ROW_RE = re.compile(
    r"^(?P<name>.*?[A-Za-z].*?)\s+(?P<o>\d+(?:\.\d)?)\s+(?P<m>\d+)\s+(?P<r>\d+)\s+(?P<w>\d+)"
    r"(?P<rest>(?:\s+[\d.\-]+)*)\s*$"
)

# A dismissal always starts with one of these lowercase tokens.  Player names
# use capitalised initials, so a lone lowercase "c"/"b"/"st" is unambiguous.
DISMISSAL_START_RE = re.compile(
    r"(?:(?<=\s)|^)(?:c\s*&\s*b\b|c\s+and\s+b\b|c\s|b\s|lbw\b|st\s|run\s+out\b|not\s+out\b|"
    r"retired\b|hit\s+wi?c?ke?t\b|handled\b|obstruct\w*\b|timed\s+out\b|absent\b|"
    r"did\s+not\s+bat\b|dnb\b|hit\s+the\s+ball\s+twice\b|yet\s+to\s+bat\b)"
)

INTERNATIONAL_TEAMS = {
    "england", "australia", "india", "pakistan", "south africa", "new zealand",
    "sri lanka", "west indies", "bangladesh", "zimbabwe", "afghanistan", "ireland",
    "scotland", "netherlands", "nepal", "namibia", "oman", "uae",
    "united arab emirates", "usa", "united states", "canada", "kenya", "hong kong",
    "papua new guinea", "png", "jersey", "uganda", "italy",
}

FORMAT_ORDER = ["Test", "ODI", "T20I", "First Class", "List A", "T20", "The Hundred", "Other"]
FORMAT_FAMILY = {
    "Test": "Multi-day",
    "First Class": "Multi-day",
    "ODI": "One-day",
    "List A": "One-day",
    "T20I": "T20",
    "T20": "T20",
    "The Hundred": "T20",
    "Other": "Other",
}

META_KEYS = {
    "venue": "venue", "ground": "venue", "at": "venue", "stadium": "venue",
    "date": "date", "dates": "date", "played": "date", "match date": "date",
    "toss": "toss",
    "result": "result",
    "competition": "competition", "series": "competition", "tournament": "competition",
    "event": "competition", "league": "competition",
    "match": "match_title", "fixture": "match_title",
    "format": "format", "type": "format", "match type": "format",
    "player of the match": "player_of_match", "man of the match": "player_of_match",
    "player of match": "player_of_match", "potm": "player_of_match", "mom": "player_of_match",
}

# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #


def overs_to_balls(overs: str | float | int | None, balls_per_over: int = 6) -> int:
    if overs is None or overs == "":
        return 0
    s = str(overs).strip()
    if "." in s:
        whole, part = s.split(".", 1)
        return int(whole or 0) * balls_per_over + int(part[:1] or 0)
    return int(float(s)) * balls_per_over


def balls_to_overs(balls: int | float | None) -> str:
    if balls is None or balls != balls:  # NaN
        return ""
    balls = int(balls)
    return f"{balls // 6}" if balls % 6 == 0 else f"{balls // 6}.{balls % 6}"


def clean_name(raw: str) -> tuple[str, bool, bool]:
    """Strip captain/keeper markers. Returns (name, captain, keeper)."""
    s = raw.strip()
    captain = keeper = False
    for pat in (r"\(c\)", r"\(capt\.?\)", r"\(captain\)"):
        if re.search(pat, s, re.I):
            captain = True
            s = re.sub(pat, "", s, flags=re.I)
    for pat in (r"\(wk\)", r"\(w/k\)", r"\(keeper\)"):
        if re.search(pat, s, re.I):
            keeper = True
            s = re.sub(pat, "", s, flags=re.I)
    if "*" in s:
        captain = True
        s = s.replace("*", "")
    if "†" in s or "+" in s:
        keeper = True
        s = s.replace("†", "").replace("+", "")
    s = re.sub(r"\s+", " ", s).strip(" -–,")
    return s, captain, keeper


def parse_date(text: str) -> date | None:
    text = text.replace(",", " ")
    # 12th April 2024 / 12-15 April 2024 / 12 Apr 2024
    m = re.search(
        r"(\d{1,2})(?:st|nd|rd|th)?(?:\s*[-–/&]\s*\d{1,2}(?:st|nd|rd|th)?)*\s+"
        r"([A-Za-z]{3,9})\.?\s+(\d{4})",
        text,
    )
    if m and m.group(2)[:3].lower() in MONTHS:
        try:
            return date(int(m.group(3)), MONTHS[m.group(2)[:3].lower()], int(m.group(1)))
        except ValueError:
            pass
    # April 12th 2024
    m = re.search(r"([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?\s+(\d{4})", text)
    if m and m.group(1)[:3].lower() in MONTHS:
        try:
            return date(int(m.group(3)), MONTHS[m.group(1)[:3].lower()], int(m.group(2)))
        except ValueError:
            pass
    # 2024-04-12
    m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", text)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass
    # 12/04/2024 (day first, the game is British)
    m = re.search(r"(\d{1,2})[/.](\d{1,2})[/.](\d{4})", text)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if mo > 12 and d <= 12:
            d, mo = mo, d
        try:
            return date(y, mo, d)
        except ValueError:
            pass
    return None


def _split_cols(line: str) -> list[str]:
    return [c for c in re.split(r"\t+|\s{2,}", line.strip()) if c]


def _header_columns(line: str) -> list[str] | None:
    """Recognise a batting/bowling column-header line and return its numeric
    column keys in order, e.g. ['r', 'b', '4s', '6s']."""
    tokens = re.findall(r"[A-Za-z0-9/]+", line.lower())
    mapping = {
        "r": "r", "runs": "r", "b": "b", "balls": "b", "bf": "b", "m": "m", "mins": "m",
        "min": "m", "minutes": "m", "4s": "4s", "fours": "4s", "4": "4s", "6s": "6s",
        "sixes": "6s", "6": "6s", "sr": "sr", "s/r": "sr", "o": "o", "overs": "o", "ov": "o",
        "md": "md", "mdns": "md", "maidens": "md", "w": "w", "wkts": "w", "wickets": "w",
        "wd": "wd", "wides": "wd", "nb": "nb", "noballs": "nb", "econ": "econ", "er": "econ",
        "ave": "ave", "dots": "dots", "0s": "dots",
    }
    cols = [mapping[t] for t in tokens if t in mapping]
    if len(cols) >= 2 and len(cols) >= len(tokens) - 3:
        return cols
    return None


# --------------------------------------------------------------------------- #
# Dismissal parsing
# --------------------------------------------------------------------------- #


def parse_dismissal(text: str) -> dict:
    t = re.sub(r"\s+", " ", text.strip())
    low = t.lower()
    out = {"how_out": "other", "bowler": "", "fielder": "", "not_out": False, "did_bat": True}

    def strip_marks(s: str) -> str:
        return s.replace("†", "").replace("+", "").replace("*", "").strip(" ()")

    if not low or low in {"did not bat", "dnb", "yet to bat"}:
        out.update(how_out="dnb", did_bat=False)
    elif low.startswith("absent"):
        out.update(how_out="absent", did_bat=False)
    elif low.startswith("not out"):
        out.update(how_out="not out", not_out=True)
    elif low.startswith("retired"):
        hurt = "hurt" in low or "not out" in low or "ill" in low
        out.update(how_out="retired hurt" if hurt else "retired out", not_out=hurt)
    elif m := re.match(r"c\s*(?:&|and)\s*b\s+(.+)", t, re.I):
        b = strip_marks(m.group(1))
        out.update(how_out="caught", bowler=b, fielder=b)
    elif m := re.match(r"c\s+(.+?)\s+b\s+(.+)", t):
        f = m.group(1)
        out.update(how_out="caught", fielder=strip_marks(f), bowler=strip_marks(m.group(2)))
        if f.strip().startswith(("†", "+")):
            out["how_out"] = "caught"  # keeper catch; fielder resolved later
    elif m := re.match(r"st\s+(.+?)\s+b\s+(.+)", t):
        out.update(how_out="stumped", fielder=strip_marks(m.group(1)), bowler=strip_marks(m.group(2)))
    elif m := re.match(r"lbw(?:\s+b\s+(.+))?", t, re.I):
        out.update(how_out="lbw", bowler=strip_marks(m.group(1) or ""))
    elif m := re.match(r"hit\s+wi?c?ke?t(?:\s+b\s+(.+))?", t, re.I):
        out.update(how_out="hit wicket", bowler=strip_marks(m.group(1) or ""))
    elif m := re.match(r"run\s+out\s*(.*)", t, re.I):
        f = strip_marks(m.group(1).split("/")[0])
        out.update(how_out="run out", fielder=f)
    elif m := re.match(r"b\s+(.+)", t):
        out.update(how_out="bowled", bowler=strip_marks(m.group(1)))
    elif low.startswith("timed out"):
        out["how_out"] = "timed out"
    elif low.startswith(("obstruct", "handled", "hit the ball")):
        out["how_out"] = "obstructing"
    return out


# --------------------------------------------------------------------------- #
# Row parsers
# --------------------------------------------------------------------------- #


def _parse_batting_row(line: str, cols: list[str], position: int) -> BattingEntry | None:
    stripped = line.strip()
    m = TRAILING_NUMS_RE.match(stripped)
    if m:
        body, nums = m.group("body"), m.group("nums").split()
    else:
        body, nums = stripped, []

    dm = DISMISSAL_START_RE.search(body, 1)
    if dm is None:
        # maybe the batting row was tab/space-columned with no dismissal keyword
        parts = _split_cols(body)
        if len(parts) >= 2:
            name_raw, dismissal = parts[0], " ".join(parts[1:])
        elif not nums:
            return None
        else:
            name_raw, dismissal = body, ""
    else:
        name_raw, dismissal = body[: dm.start()], body[dm.start():]

    name, captain, keeper = clean_name(name_raw)
    if not name or not re.search(r"[A-Za-z]", name):
        return None

    info = parse_dismissal(dismissal)
    entry = BattingEntry(
        player=name, position=position, dismissal=dismissal.strip(), how_out=info["how_out"],
        bowler=info["bowler"], fielder=info["fielder"], not_out=info["not_out"],
        did_bat=info["did_bat"], captain=captain, keeper=keeper,
    )
    if not nums:
        if info["did_bat"] and info["how_out"] != "other":
            # a dismissal without figures - treat as batted for 0
            pass
        else:
            entry.did_bat = False
            entry.how_out = "dnb" if info["how_out"] in ("other", "dnb") else info["how_out"]
        return entry

    use_cols = cols if cols else ["r", "b", "4s", "6s"]
    values: dict[str, float] = {}
    # right-align numbers to known columns when counts differ
    if len(nums) < len(use_cols):
        use_cols = use_cols[: len(nums)]
    elif len(nums) > len(use_cols):
        use_cols = use_cols + [f"x{i}" for i in range(len(nums) - len(use_cols))]
    for k, v in zip(use_cols, nums):
        if v == "-":
            continue
        try:
            values[k] = float(v)
        except ValueError:
            pass
    entry.runs = int(values.get("r", 0))
    entry.balls = int(values.get("b", 0))
    entry.fours = int(values.get("4s", 0))
    entry.sixes = int(values.get("6s", 0))
    if "m" in values:
        entry.minutes = int(values["m"])
    if entry.how_out in ("dnb", "absent"):
        entry.did_bat = entry.balls > 0 or entry.runs > 0
    return entry


def _parse_bowling_row(line: str, cols: list[str] | None) -> BowlingEntry | None:
    m = BOWL_ROW_RE.match(line.strip())
    if not m:
        return None
    name, _, _ = clean_name(m.group("name"))
    if not name or name.lower().startswith(("total", "extras", "bowling", "fall")):
        return None
    rest = m.group("rest").split()
    wides = no_balls = 0
    extra_cols = [c for c in (cols or []) if c not in ("o", "md", "r", "w")]
    if not extra_cols:
        extra_cols = ["wd", "nb"] if all(re.fullmatch(r"\d+", x) for x in rest) else []
    for k, v in zip(extra_cols, rest):
        try:
            if k == "wd":
                wides = int(float(v))
            elif k == "nb":
                no_balls = int(float(v))
        except ValueError:
            pass
    return BowlingEntry(
        player=name,
        balls=overs_to_balls(m.group("o")),
        maidens=int(m.group("m")),
        runs=int(m.group("r")),
        wickets=int(m.group("w")),
        wides=wides,
        no_balls=no_balls,
    )


def _parse_extras(line: str, inn: Innings) -> None:
    body = re.sub(r"^extras\b", "", line.strip(), flags=re.I)
    for key, attr in (("lb", "leg_byes"), ("nb", "no_balls"), ("b", "byes"), ("w", "wides"),
                      ("wd", "wides"), ("p", "penalties"), ("pen", "penalties")):
        m = re.search(rf"(?<![A-Za-z]){key}\s*(\d+)", body, re.I)
        if m:
            setattr(inn, attr, int(m.group(1)))
    body_no_paren = re.sub(r"\(.*?\)", " ", body)
    nums = re.findall(r"\d+", body_no_paren)
    if nums:
        inn.extras = int(nums[-1])
    else:
        inn.extras = inn.byes + inn.leg_byes + inn.wides + inn.no_balls + inn.penalties


def _parse_total(line: str, inn: Innings) -> None:
    body = re.sub(r"^total\b", "", line.strip(), flags=re.I)
    low = body.lower()
    inn.declared = bool(re.search(r"\bdec", low))
    if m := re.search(r"(\d+)\s*/\s*(\d+)", body):
        inn.total, inn.wickets = int(m.group(1)), int(m.group(2))
        body = body.replace(m.group(0), " ")
    if m := re.search(r"(\d+(?:\.\d)?)\s*(?:overs|over|ov|ovs)\b", body, re.I):
        inn.balls = overs_to_balls(m.group(1))
        body = body.replace(m.group(0), " ")
    elif m := re.search(r"(\d+)\s*balls\b", body, re.I):
        inn.balls = int(m.group(1))
        body = body.replace(m.group(0), " ")
    if inn.wickets is None:
        if "all out" in low:
            inn.wickets = 10
        elif m := re.search(r"(\d+)\s*(?:wkts?|wickets?)\b", body, re.I):
            inn.wickets = int(m.group(1))
            body = body.replace(m.group(0), " ")
    body = re.sub(r"\d+\s*mins?\b", " ", body, flags=re.I)
    if inn.total is None:
        nums = re.findall(r"\d+", body)
        if nums:
            inn.total = int(nums[-1])


def _parse_fow(text: str, inn: Innings) -> None:
    for m in re.finditer(
        r"(\d+)\s*-\s*(\d+)(?:\s*\(([^)]*)\))?", text
    ):
        wkt, score = int(m.group(1)), int(m.group(2))
        if not 1 <= wkt <= 10:
            continue
        batter = over = ""
        if m.group(3):
            inner = m.group(3)
            if om := re.search(r"(\d+(?:\.\d)?)\s*(?:ov|overs?)", inner):
                over = om.group(1)
                inner = inner.replace(om.group(0), "")
            batter = clean_name(inner.strip(" ,"))[0]
        inn.fow.append(FallOfWicket(wkt, score, batter, over))


# --------------------------------------------------------------------------- #
# Main entry point
# --------------------------------------------------------------------------- #


def _normalise_team(name: str, teams: list[str]) -> str:
    n = name.strip()
    for t in teams:
        if t and n.lower() == t.lower():
            return t
    for t in teams:
        if t and (n.lower().startswith(t.lower()) or t.lower().startswith(n.lower())):
            return t
    return n


def detect_format(competition: str, match_title: str, explicit: str,
                  teams: list[str], max_balls: int, n_innings: int) -> str:
    text = f"{explicit} {competition} {match_title}".lower()
    intl = all(t.lower() in INTERNATIONAL_TEAMS for t in teams if t) and any(teams)
    if "hundred" in text:
        return "The Hundred"
    if re.search(r"\btest\b", text):
        return "Test"
    if re.search(r"\bodi\b|one[- ]day international", text):
        return "ODI"
    if re.search(r"\bt20i\b|twenty20 international|t20 international|t20 world cup", text):
        return "T20I"
    if re.search(r"first[- ]class|championship|shield|ranji|plunket|quaid|currie|red ball|4[- ]day|four[- ]day|3[- ]day", text):
        return "First Class"
    if re.search(r"list a|one[- ]day|50[- ]over|royal london|metro bank|marsh cup|vijay hazare|ford trophy", text):
        return "ODI" if intl else "List A"
    if re.search(r"t20|twenty20|blast|ipl|premier league|big bash|bbl|psl|cpl|sa20|super smash", text):
        return "T20I" if intl else "T20"
    if re.search(r"world cup|champions trophy", text):
        return "ODI" if intl else "List A"
    # infer from length of the innings
    if n_innings > 2 or max_balls > 50 * 6:
        return "Test" if intl else "First Class"
    if max_balls and max_balls <= 20 * 6:
        return "T20I" if intl else "T20"
    if max_balls:
        return "ODI" if intl else "List A"
    return "Other"


def parse_result(result: str, teams: list[str]) -> dict:
    low = result.lower()
    out = {"winner": "", "result_type": "", "margin_runs": None, "margin_wickets": None,
           "innings_win": False}
    if not result:
        return out
    if "no result" in low or "abandon" in low:
        out["result_type"] = "no result"
    elif "tied" in low or re.search(r"\btie\b", low):
        out["result_type"] = "tie"
        # super over winners
        for t in teams:
            if t and re.search(rf"{re.escape(t.lower())}\s+(?:won|win)", low):
                out["winner"] = t
    elif "drawn" in low or re.search(r"\bdraw\b", low):
        out["result_type"] = "draw"
    else:
        for t in sorted(teams, key=len, reverse=True):
            if t and re.search(rf"{re.escape(t.lower())}\s+(?:won|win|beat)", low):
                out["winner"] = t
                break
        if out["winner"]:
            out["result_type"] = "win"
        if m := re.search(r"by\s+(\d+)\s+runs?", low):
            out["margin_runs"] = int(m.group(1))
        if m := re.search(r"by\s+(\d+)\s+wick", low):
            out["margin_wickets"] = int(m.group(1))
        if "innings" in low:
            out["innings_win"] = True
    return out


def parse_scorecard(text: str, source: str = "") -> Match:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("﻿", "")
    lines = [ln.rstrip() for ln in text.split("\n")]
    norm = re.sub(r"\s+", " ", text).strip().lower()
    if not norm:
        raise ScorecardError("empty file")
    match = Match(match_id=hashlib.sha1(norm.encode()).hexdigest()[:12], source=source, raw=text)
    meta: dict[str, str] = {}
    header_free: list[str] = []

    innings: list[Innings] = []
    cur: Innings | None = None
    section = "header"  # header | batting | bowling | fow | footer
    bat_cols: list[str] = []
    bowl_cols: list[str] | None = None
    pending_bowling_team = ""
    pos = 0

    def is_meta(line: str) -> bool:
        m = re.match(r"^\s*([A-Za-z][A-Za-z ]{1,24}?)\s*[:\-–]\s+(.+)$", line)
        if m and m.group(1).strip().lower() in META_KEYS:
            key = META_KEYS[m.group(1).strip().lower()]
            meta.setdefault(key, m.group(2).strip())
            return True
        return False

    i = 0
    while i < len(lines):
        raw = lines[i]
        line = raw.strip()
        i += 1
        if not line or set(line) <= set("-=_*~ "):
            continue

        im = INNINGS_RE.match(line)
        if im and not re.search(r"\bbowling\b", line, re.I) and len(im.group("team")) <= 40 \
                and not TOTAL_RE.match(line) and not EXTRAS_RE.match(line):
            team = im.group("team").strip(" -–:,")
            if team.lower() in {"the", "an", "an innings", "by an"} or "won" in team.lower():
                pass
            else:
                prior = sum(1 for x in innings if x.team.lower() == team.lower())
                cur = Innings(team=team, number=len(innings) + 1, team_innings=prior + 1)
                innings.append(cur)
                section, pos, bowl_cols = "batting", 0, None
                bat_cols = _header_columns(im.group("rest") or "") or []
                continue

        if section == "header":
            if is_meta(line):
                continue
            if not (match.team1 or match.team2) and (tm := TEAMS_RE.match(line)):
                a, b = tm.group("a").strip(), tm.group("b").strip()
                b = re.split(r"\s+(?:at|,)\s+", b, maxsplit=1)
                if len(b) > 1:
                    meta.setdefault("venue", b[1].strip())
                match.team1, match.team2 = a.strip(" -–,"), b[0].strip(" -–,")
                continue
            header_free.append(line)
            continue

        # ---- inside a match body ----
        if is_meta(line):
            continue
        if re.search(r"\bbowling\b", line, re.I) and not TRAILING_NUMS_RE.match(line):
            section = "bowling"
            bowl_cols = _header_columns(line)
            pending_bowling_team = re.sub(r"\bbowling\b.*$", "", line, flags=re.I).strip(" -–:,")
            if cur is not None and pending_bowling_team:
                cur.bowling_team = pending_bowling_team
            continue
        if section != "bowling" and (hc := _header_columns(line)) and ("o" in hc and "w" in hc):
            section, bowl_cols = "bowling", hc
            continue
        if section == "batting" and (hc := _header_columns(line)) and not re.search(r"\d", line):
            bat_cols = hc
            continue
        if FOW_RE.match(line):
            section = "fow"
            if cur is not None:
                body = re.sub(r"^(?:fall of wickets?|fow)\s*[:\-]?", "", line, flags=re.I)
                # FOW can wrap onto following lines
                while i < len(lines) and re.match(r"^\s*\(?\d+\s*-\s*\d+", lines[i]):
                    body += " " + lines[i]
                    i += 1
                _parse_fow(body, cur)
            continue
        if cur is None:
            continue
        if EXTRAS_RE.match(line):
            _parse_extras(line, cur)
            continue
        if TOTAL_RE.match(line):
            _parse_total(line, cur)
            section = "after_total"
            continue
        if m := DNB_LINE_RE.match(line):
            for nm in re.split(r",|;", m.group("names")):
                name, c, k = clean_name(nm)
                if name:
                    pos += 1
                    cur.batting.append(BattingEntry(player=name, position=pos, how_out="dnb",
                                                    captain=c, keeper=k))
            continue

        if section == "batting":
            pos += 1
            entry = _parse_batting_row(line, bat_cols, pos)
            if entry is None:
                pos -= 1
            else:
                cur.batting.append(entry)
            continue
        if section == "after_total":
            # "did not bat" rows can follow the total in some layouts
            entry = _parse_batting_row(line, bat_cols, pos + 1)
            if entry and not entry.did_bat and entry.how_out == "dnb" and len(entry.player.split()) <= 4:
                pos += 1
                cur.batting.append(entry)
            elif BOWL_ROW_RE.match(line):
                section = "bowling"
                if (b := _parse_bowling_row(line, bowl_cols)):
                    cur.bowling.append(b)
            continue
        if section == "bowling":
            b = _parse_bowling_row(line, bowl_cols)
            if b is not None:
                cur.bowling.append(b)
            continue
        if section == "fow":
            if re.match(r"^\(?\d+\s*-\s*\d+", line):
                _parse_fow(line, cur)
            continue

    # footer meta can appear after the last innings
    for ln in lines:
        s = ln.strip()
        low = s.lower()
        if "result" not in meta and re.search(r"\bwon by\b|\bmatch drawn\b|\bmatch tied\b|\bno result\b|\babandoned\b|\bbeat\b.*\bby\b", low) \
                and len(s) < 140 and not s.lower().startswith("toss"):
            meta["result"] = re.sub(r"^result\s*[:\-]\s*", "", s, flags=re.I)
        if "toss" not in meta and "toss" in low and len(s) < 140:
            meta["toss"] = re.sub(r"^toss\s*[:\-]\s*", "", s, flags=re.I)

    if not innings:
        raise ScorecardError("no innings found")

    # ---------------- teams ----------------
    innings_teams: list[str] = []
    for inn in innings:
        if inn.team.lower() not in [t.lower() for t in innings_teams]:
            innings_teams.append(inn.team)
    if not match.team1:
        match.team1 = innings_teams[0]
        match.team2 = innings_teams[1] if len(innings_teams) > 1 else ""
    teams = [match.team1, match.team2]
    for inn in innings:
        inn.team = _normalise_team(inn.team, teams)
        other = [t for t in teams if t != inn.team]
        inn.bowling_team = other[0] if other else inn.bowling_team

    # ---------------- header fields ----------------
    match.venue = meta.get("venue", "")
    match.toss = meta.get("toss", "")
    match.result = meta.get("result", "")
    match.player_of_match = clean_name(meta.get("player_of_match", ""))[0]
    match.match_title = meta.get("match_title", "")
    match.competition = meta.get("competition", "")
    date_src = meta.get("date", "") or " ".join(header_free) or text[:600]
    match.date = parse_date(date_src) or parse_date(" ".join(header_free)) or parse_date(source)

    leftovers = [h for h in header_free if not parse_date(h) and "toss" not in h.lower()
                 and not re.search(r"won by|drawn|tied|no result", h.lower())
                 and not h.lower().startswith(("cricket captain", "scorecard", "match scorecard"))]
    if not match.competition and leftovers:
        match.competition = leftovers[0]
    if not match.match_title and len(leftovers) > 1:
        match.match_title = leftovers[1]
    if not match.venue:
        for h in leftovers[1:]:
            if "," in h or re.search(r"ground|oval|park|stadium|lord|road|bowl", h, re.I):
                match.venue = h
                break
    if match.venue:
        # "Lord's, London - 12 June 2024" -> "Lord's, London"
        match.venue = re.split(r"\s+[-–]\s+|\s+on\s+\d", match.venue)[0].strip()

    # ---------------- derive innings totals when missing ----------------
    for inn in innings:
        batted = [b for b in inn.batting if b.did_bat]
        if inn.total is None:
            inn.total = sum(b.runs for b in batted) + inn.extras
        if inn.wickets is None:
            inn.wickets = sum(1 for b in batted if not b.not_out)
        if inn.balls is None and inn.bowling:
            inn.balls = sum(b.balls for b in inn.bowling)

    # resolve short bowler names in dismissals ("b Cummins") to the bowling card
    for inn in innings:
        bowlers = [b.player for b in inn.bowling]
        for b in inn.batting:
            if b.bowler:
                b.bowler = resolve_name(b.bowler, bowlers)

    max_balls = max((inn.balls or 0) for inn in innings)
    match.format = detect_format(match.competition, match.match_title, meta.get("format", ""),
                                 teams, max_balls, len(innings))
    res = parse_result(match.result, teams)
    for k, v in res.items():
        setattr(match, k, v)
    match.innings = innings
    return match


def resolve_name(short: str, candidates: list[str]) -> str:
    """Map a dismissal name like 'Cummins' or 'PJ Cummins' to a full scorecard name."""
    s = short.strip()
    if not s or not candidates:
        return s
    low = s.lower()
    for c in candidates:
        if c.lower() == low:
            return c
    ends = [c for c in candidates if c.lower().endswith(" " + low) or c.lower().split()[-1] == low.split()[-1]]
    if len(ends) == 1:
        return ends[0]
    if len(ends) > 1:
        # disambiguate by initials
        initials = low.split()[0] if len(low.split()) > 1 else ""
        for c in ends:
            if initials and c.lower().startswith(initials[0]):
                return c
        return ends[0]
    return s
