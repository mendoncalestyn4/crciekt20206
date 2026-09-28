"""Parser for Cricket Captain text scorecards.

Cricket Captain 2026 writes one plain-text file per match, e.g.::

    ************************************************************
    India v West Indies
    1st One Day International (of 3) - 1 Oct 2026
    ************************************************************

    West Indies - 1st Innings                 R    B    4s  6s
    ------------------------------------------------------------
    J Greaves       lbw b Yadav               16   21   2   -
    ...
    R Gaikwad                                   <- did not bat
    ------------------------------------------------------------
    Extras: (nb2)                             2
    TOTAL: (all out, 49.2 overs)              255

                    O      M     R      W     Econ    <- "D" (dots) in T20s; "B" (balls) in The Hundred
    ------------------------------------------------------------
    A Singh         10     0     52     1     5.20
    ------------------------------------------------------------
    Fall of Wickets:
    1-37  2-57  3-110 ...

    ************************************************************
    India won by 7 wickets
    Man of the match: S Gill
    ************************************************************

The parser keys off these landmarks rather than exact column positions so
that small layout differences between game editions still parse.
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
    how_out: str = "dnb"  # caught, bowled, lbw, stumped, run out, not out, dnb, ...
    bowler: str = ""  # full name from the bowling card once resolved
    fielder: str = ""  # full name from the fielding side's XI once resolved
    fielder_resolved: bool = False  # False: printed name matches 0 or 2+ players
    runs: int = 0
    balls: int = 0
    fours: int = 0
    sixes: int = 0
    not_out: bool = False
    did_bat: bool = False


@dataclass
class BowlingEntry:
    player: str
    balls: int
    runs: int
    wickets: int
    maidens: int | None = None  # shown in ODI / multi-day cards
    dots: int | None = None  # shown instead of maidens in T20 cards


@dataclass
class Innings:
    team: str
    number: int  # batting order in the match, 1..4 (see _fix_follow_on)
    team_innings: int  # 1st or 2nd innings for this team
    listed: int = 0  # position in the file (the game lists innings in team order)
    bowling_team: str = ""
    batting: list[BattingEntry] = field(default_factory=list)
    bowling: list[BowlingEntry] = field(default_factory=list)
    fow: list[tuple[int, int]] = field(default_factory=list)  # (wicket, score)
    extras: int = 0
    byes: int = 0
    leg_byes: int = 0
    wides: int = 0
    no_balls: int = 0
    penalties: int = 0
    total: int = 0
    wickets: int = 0
    balls: int = 0
    all_out: bool = False
    counted_in_balls: bool = False  # The Hundred: "(6 wkts, 100 balls)"
    declared: bool = False
    follow_on: bool = False


@dataclass
class Match:
    match_id: str
    source: str
    team1: str = ""
    team2: str = ""
    title: str = ""  # "1st One Day International (of 3)" / "Indian Premier League"
    series_match_no: int | None = None
    series_length: int | None = None
    date: date | None = None
    result: str = ""
    winner: str = ""
    result_type: str = ""  # win, draw, tie, no result
    margin_runs: int | None = None
    margin_wickets: int | None = None
    innings_win: bool = False
    margin_note: str = ""  # set when the game's printed margin disagrees with the scores
    player_of_match: str = ""
    innings: list[Innings] = field(default_factory=list)


class ScorecardError(ValueError):
    """Raised when a file does not look like a Cricket Captain scorecard."""


# --------------------------------------------------------------------------- #
# Patterns
# --------------------------------------------------------------------------- #

MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}

RULE_RE = re.compile(r"^[\s*=\-_~]+$")
TEAMS_RE = re.compile(r"^(?P<a>.+?)\s+(?:v|vs\.?|versus)\s+(?P<b>.+?)$")
INNINGS_RE = re.compile(
    r"^(?P<team>.+?)\s*[-–:]\s*(?P<ord>1st|2nd|first|second)?\s*innings\b(?P<rest>.*)$", re.I)
EXTRAS_RE = re.compile(r"^extras\b", re.I)
TOTAL_RE = re.compile(r"^total\b", re.I)
FOW_RE = re.compile(r"^fall of wickets?\b", re.I)
FOW_PAIR_RE = re.compile(r"(\d+)\s*-\s*(\d+)")
POTM_RE = re.compile(r"^(?:man|player) of the match\s*[:\-]\s*(?P<name>.+)$", re.I)
RESULT_RE = re.compile(
    r"\bwon\b|\bbeat\b|\bdrawn\b|\bdraw\b|\btied\b|\bno result\b|\babandoned\b", re.I)
SERIES_RE = re.compile(r"^(?P<no>\d+)(?:st|nd|rd|th)\s+(?P<name>.+?)\s*\(of\s+(?P<of>\d+)\)", re.I)
NUM = r"(?:\d+(?:\.\d+)?|-)"
TRAILING_NUMS_RE = re.compile(rf"^(?P<body>.*?\S)\s+(?P<nums>{NUM}(?:\s+{NUM})*)\s*$")

# A dismissal starts with one of these lowercase tokens.  Names are written
# "Initial Surname" with capitals, so a lone lowercase "c"/"b"/"st" is safe.
DISMISSAL_START_RE = re.compile(
    r"(?<=\s)(?:c\s*&\s*b\b|c\s+and\s+b\b|c\s|b\s|lbw\b|st\s|run\s+out\b|not\s+out\b|"
    r"retired\b|rtrd\b|retd\b|ret'd\b|hit\s+wi?c?ke?t\b|handled\b|obstruct\w*|timed\s+out\b|absent\b|"
    r"hit\s+the\s+ball\s+twice\b)"
)

BAT_COLS = {"r": "r", "runs": "r", "b": "b", "balls": "b", "4s": "4s", "6s": "6s",
            "m": "m", "mins": "m", "sr": "sr"}
BOWL_COLS = {"o": "o", "overs": "o", "b": "balls", "balls": "balls", "m": "m", "md": "m", "mdns": "m", "d": "d", "dots": "d",
             "r": "r", "runs": "r", "w": "w", "wkts": "w", "econ": "econ", "er": "econ",
             "wd": "wd", "nb": "nb"}


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def overs_to_balls(overs: str | float | int | None) -> int:
    if overs in (None, "", "-"):
        return 0
    s = str(overs).strip()
    if "." in s:
        whole, part = s.split(".", 1)
        return int(whole or 0) * 6 + int(part[:1] or 0)
    return int(float(s)) * 6


def balls_to_overs(balls: int | float | None) -> str:
    if balls is None or balls != balls:  # None / NaN
        return ""
    balls = int(balls)
    return f"{balls // 6}" if balls % 6 == 0 else f"{balls // 6}.{balls % 6}"


def parse_date(text: str) -> date | None:
    m = re.search(r"(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]{3,9})\.?,?\s+(\d{4})", text)
    if m and m.group(2)[:3].lower() in MONTHS:
        try:
            return date(int(m.group(3)), MONTHS[m.group(2)[:3].lower()], int(m.group(1)))
        except ValueError:
            return None
    # file names: 1_oct_2026-ind_v_wi_1st_odi.txt
    m = re.search(r"(\d{1,2})_([a-z]{3})_(\d{4})", text.lower())
    if m and m.group(2) in MONTHS:
        try:
            return date(int(m.group(3)), MONTHS[m.group(2)], int(m.group(1)))
        except ValueError:
            return None
    return None


def _to_int(tok: str) -> int:
    return 0 if tok in ("-", "") else int(float(tok))


def _header_cols(text: str, vocab: dict[str, str]) -> list[str]:
    toks = text.lower().split()
    return [vocab[t] for t in toks if t in vocab]


def parse_dismissal(text: str) -> dict:
    t = re.sub(r"\s+", " ", text.strip())
    low = t.lower()
    out = {"how_out": "other", "bowler": "", "fielder": "", "not_out": False, "did_bat": True}
    if not low:
        out.update(how_out="dnb", did_bat=False)
    elif low.startswith("absent"):
        out.update(how_out="absent", did_bat=False)
    elif low.startswith("not out"):
        out.update(how_out="not out", not_out=True)
    elif low.startswith(("retired", "rtrd", "retd", "ret'd")):
        hurt = bool(re.search(r"hurt|\bht\b|\bill\b|not out", low))
        out.update(how_out="retired hurt" if hurt else "retired out", not_out=hurt)
    elif m := re.match(r"c\s*(?:&|and)\s*b\s+(.+)", t, re.I):
        out.update(how_out="caught", bowler=m.group(1), fielder=m.group(1))
    elif m := re.match(r"c\s+(.+?)\s+b\s+(.+)", t):
        out.update(how_out="caught", fielder=m.group(1), bowler=m.group(2))
    elif m := re.match(r"st\s+(.+?)\s+b\s+(.+)", t):
        out.update(how_out="stumped", fielder=m.group(1), bowler=m.group(2))
    elif m := re.match(r"lbw(?:\s+b\s+(.+))?", t, re.I):
        out.update(how_out="lbw", bowler=m.group(1) or "")
    elif m := re.match(r"hit\s+wi?c?ke?t(?:\s+b\s+(.+))?", t, re.I):
        out.update(how_out="hit wicket", bowler=m.group(1) or "")
    elif m := re.match(r"run\s+out\s*\(?([^)]*)\)?", t, re.I):
        out.update(how_out="run out", fielder=m.group(1).split("/")[0].strip())
    elif m := re.match(r"b\s+(.+)", t):
        out.update(how_out="bowled", bowler=m.group(1))
    elif low.startswith("timed out"):
        out["how_out"] = "timed out"
    elif low.startswith(("obstruct", "handled", "hit the ball")):
        out["how_out"] = "obstructing"
    for k in ("bowler", "fielder"):
        out[k] = out[k].replace("†", "").replace("*", "").strip()
    return out


def _surname_matches(short: str, full: str) -> bool:
    """'Khan' ~ 'S Khan';  "K'r Reddy" ~ 'N Kumar Reddy';  "G'sworthy" ~ 'L Goldsworthy'."""
    s = short.lower().strip()
    parts = full.lower().split()
    surname = " ".join(parts[1:]) if len(parts) > 1 else parts[0]
    if s in (surname, full.lower()) or parts[-1] == s.split()[-1] and "'" not in s:
        return True
    if "'" in s:
        head, tail = s.split("'", 1)
        target = surname.replace(" ", "").replace("-", "")
        return target.startswith(head.replace(" ", "")) and target.endswith(tail.replace(" ", ""))
    return False


def resolve_candidates(short: str, candidates: list[str]) -> list[str]:
    s = short.strip()
    if not s:
        return []
    exact = [c for c in candidates if c.lower() == s.lower()]
    return exact or [c for c in candidates if _surname_matches(s, c)]


def resolve_name(short: str, candidates: list[str]) -> str:
    """Map a dismissal name ('Khan', "K'r Reddy") to a full name from the card.

    Returns '' when there is no unique match (e.g. 'Khan' with S Khan and
    U Khan in the same XI)."""
    hits = resolve_candidates(short, candidates)
    return hits[0] if len(hits) == 1 else ""


def _assign_bowlers(inn: "Innings") -> None:
    """Credit each dismissal to a bowler on the card.  Where a surname is
    shared ('b Joseph' with S Joseph and A Joseph bowling) use the bowlers'
    wicket counts to work out who must have taken it."""
    remaining = {b.player: b.wickets for b in inn.bowling}
    pending = []
    for e in inn.batting:
        if not e.bowler:
            continue
        hits = resolve_candidates(e.bowler, list(remaining))
        if len(hits) == 1:
            e.bowler = hits[0]
            remaining[hits[0]] -= 1
        else:
            pending.append((e, hits))
    for e, hits in pending:
        able = [h for h in hits if remaining.get(h, 0) > 0]
        if len(able) == 1:
            e.bowler = able[0]
            remaining[able[0]] -= 1


def _assign_fielders(match: "Match") -> None:
    """Credit catches and stumpings to the same full name the fielder bats and
    bowls under.  The dismissal only prints a surname ("st de Kock", "c DKock",
    "c van Beek", "c H' Shanto"); the fielding side's XI comes from its own
    batting card (every player is listed there, including those who did not
    bat), so resolving against it keeps a keeper's stumpings, catches, runs and
    wickets on one player."""
    squads: dict[str, list[str]] = {}
    for inn in match.innings:
        squad = squads.setdefault(inn.team, [])
        squad.extend(b.player for b in inn.batting if b.player not in squad)
    for inn in match.innings:  # a side that never batted: fall back to its bowlers
        squad = squads.setdefault(inn.bowling_team, [])
        squad.extend(b.player for b in inn.bowling if b.player not in squad)
    for inn in match.innings:
        xi = squads.get(inn.bowling_team, [])
        for e in inn.batting:
            if not e.fielder:
                continue
            if re.match(r"c\s*(?:&|and)\s*b\b", e.dismissal, re.I):
                hits = [e.bowler] if e.bowler in xi else []
            else:
                hits = resolve_candidates(e.fielder, xi)
                # "c Taylor b Taylor": a caught-and-bowled is written "c & b",
                # so the catcher is the other Taylor
                if len(hits) > 1 and e.bowler in hits:
                    hits = [h for h in hits if h != e.bowler]
            if len(hits) == 1:
                e.fielder, e.fielder_resolved = hits[0], True


def validate_match(match: "Match") -> list[str]:
    """Self-check a parsed scorecard.  Every number on a Cricket Captain card
    is tied to others (runs to the total, 4s and 6s to runs, bowling figures
    to the total, wickets to the fall of wickets), so a column read wrongly
    shows up as a broken sum.  Returns a list of problems; empty means clean."""
    problems = []
    for inn in match.innings:
        where = f"{inn.team} innings {inn.team_innings}"
        batted = [b for b in inn.batting if b.did_bat]
        for b in batted:
            if 4 * b.fours + 6 * b.sixes > b.runs:
                problems.append(f"{where}: {b.player} has more boundary runs than runs")
            if b.fours + b.sixes > b.balls:
                problems.append(f"{where}: {b.player} has more boundaries than balls faced")
        if sum(b.runs for b in batted) + inn.extras != inn.total:
            problems.append(f"{where}: batting runs + extras do not add up to the total")
        extras = inn.byes + inn.leg_byes + inn.wides + inn.no_balls + inn.penalties
        if extras and extras != inn.extras:
            problems.append(f"{where}: extras breakdown does not match the extras total")
        if inn.bowling:
            if sum(b.runs for b in inn.bowling) + inn.byes + inn.leg_byes + inn.penalties != inn.total:
                problems.append(f"{where}: bowling runs do not add up to the total")
            if sum(b.balls for b in inn.bowling) != inn.balls:
                problems.append(f"{where}: bowlers' overs do not add up to the innings overs")
            run_outs = sum(b.how_out in ("run out", "timed out", "obstructing", "retired out") for b in batted)
            if sum(b.wickets for b in inn.bowling) + run_outs != inn.wickets:
                problems.append(f"{where}: bowlers' wickets do not match the wickets that fell")
        if sum(1 for b in batted if not b.not_out) != inn.wickets:
            problems.append(f"{where}: dismissals do not match the wickets in the total")
        if len(inn.fow) != inn.wickets:
            problems.append(f"{where}: fall of wickets does not match the wickets in the total")
    return problems


def parse_result(result: str, teams: list[str]) -> dict:
    low = result.lower()
    out = {"winner": "", "result_type": "", "margin_runs": None, "margin_wickets": None,
           "innings_win": False}
    if not low:
        return out
    if "no result" in low or "abandon" in low:
        out["result_type"] = "no result"
        return out
    winner = ""
    for t in sorted((t for t in teams if t), key=len, reverse=True):
        if re.search(rf"^{re.escape(t.lower())}\s+(?:won|win|beat)", low):
            winner = t
            break
    if "tied" in low or re.search(r"\btie\b", low):
        out["result_type"] = "tie"
        out["winner"] = winner  # super over / bowl-out winner, if stated
        return out
    if "drawn" in low or re.search(r"\bdraw\b", low):
        out["result_type"] = "draw"
        return out
    out["winner"] = winner
    out["result_type"] = "win" if winner else ""
    if m := re.search(r"by\s+(\d+)\s+runs?", low):
        out["margin_runs"] = int(m.group(1))
    if m := re.search(r"by\s+(\d+)\s+wick", low):
        out["margin_wickets"] = int(m.group(1))
    out["innings_win"] = "innings" in low
    return out


# --------------------------------------------------------------------------- #
# Section parsers
# --------------------------------------------------------------------------- #


def _batting_row(line: str, cols: list[str], position: int) -> BattingEntry | None:
    s = line.strip()
    m = TRAILING_NUMS_RE.match(s)
    body, nums = (m.group("body"), m.group("nums").split()) if m else (s, [])
    dm = DISMISSAL_START_RE.search(body)
    name = (body[: dm.start()] if dm else body).strip()
    dismissal = body[dm.start():].strip() if dm else ""
    if not re.search(r"[A-Za-z]", name):
        return None
    info = parse_dismissal(dismissal)
    e = BattingEntry(player=re.sub(r"\s+", " ", name), position=position, dismissal=dismissal,
                     how_out=info["how_out"], bowler=info["bowler"], fielder=info["fielder"],
                     not_out=info["not_out"], did_bat=info["did_bat"])
    if nums:
        vals = dict(zip(cols or ["r", "b", "4s", "6s"], nums))
        e.runs = _to_int(vals.get("r", "0"))
        e.balls = _to_int(vals.get("b", "0"))
        e.fours = _to_int(vals.get("4s", "0"))
        e.sixes = _to_int(vals.get("6s", "0"))
        if not e.did_bat and (e.runs or e.balls):
            e.did_bat = True
    elif e.did_bat and not dismissal:
        e.did_bat, e.how_out = False, "dnb"
    return e


def _bowling_row(line: str, cols: list[str]) -> BowlingEntry | None:
    m = TRAILING_NUMS_RE.match(line.strip())
    if not m or not re.search(r"[A-Za-z]", m.group("body")):
        return None
    nums = m.group("nums").split()
    cols = cols or ["o", "m", "r", "w", "econ"]
    if len(nums) < 4:
        return None
    vals = dict(zip(cols, nums))
    return BowlingEntry(
        player=re.sub(r"\s+", " ", m.group("body").strip()),
        balls=_to_int(vals["balls"]) if "balls" in vals else overs_to_balls(vals.get("o")),
        runs=_to_int(vals.get("r", "0")),
        wickets=_to_int(vals.get("w", "0")),
        maidens=_to_int(vals["m"]) if "m" in vals else None,
        dots=_to_int(vals["d"]) if "d" in vals else None,
    )


def _extras(line: str, inn: Innings) -> None:
    body = re.sub(r"^extras\s*:?", "", line.strip(), flags=re.I)
    inner = " ".join(re.findall(r"\(([^)]*)\)", body))
    for key, attr in (("lb", "leg_byes"), ("nb", "no_balls"), ("b", "byes"), ("w", "wides"),
                      ("p", "penalties")):
        if mm := re.search(rf"(?<![a-z]){key}\s*(\d+)", inner, re.I):
            setattr(inn, attr, int(mm.group(1)))
    nums = re.findall(r"\d+", re.sub(r"\(.*?\)", " ", body))
    inn.extras = int(nums[-1]) if nums else (
        inn.byes + inn.leg_byes + inn.wides + inn.no_balls + inn.penalties)


def _total(line: str, inn: Innings) -> None:
    body = re.sub(r"^total\s*:?", "", line.strip(), flags=re.I)
    low = body.lower()
    inn.declared = bool(re.search(r"\bdec", low))
    inn.all_out = "all out" in low
    inside = " ".join(re.findall(r"\(([^)]*)\)", body))
    if mm := re.search(r"(\d+(?:\.\d)?)\s*(?:overs?|ov)\b", inside, re.I):
        inn.balls = overs_to_balls(mm.group(1))
    elif mm := re.search(r"(\d+)\s*balls?\b", inside, re.I):
        inn.balls = int(mm.group(1))
        inn.counted_in_balls = True
    if inn.all_out:
        inn.wickets = 10
    elif mm := re.search(r"(\d+)\s*(?:wkts?|wickets?)", inside, re.I):
        inn.wickets = int(mm.group(1))
    nums = re.findall(r"\d+", re.sub(r"\(.*?\)", " ", body))
    if nums:
        inn.total = int(nums[-1])


# --------------------------------------------------------------------------- #
# Main entry point
# --------------------------------------------------------------------------- #


def parse_scorecard(text: str, source: str = "") -> Match:
    text = text.replace("﻿", "").replace("\r\n", "\n").replace("\r", "\n")
    norm = re.sub(r"\s+", " ", text).strip().lower()
    if not norm:
        raise ScorecardError("empty file")
    match = Match(match_id=hashlib.sha1(norm.encode()).hexdigest()[:12], source=source)
    lines = text.split("\n")

    header: list[str] = []
    cur: Innings | None = None
    section = "header"  # header | batting | bowling | fow | footer
    bat_cols: list[str] = []
    bowl_cols: list[str] = []
    pos = 0

    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if RULE_RE.match(line):
            # a row of *** after the innings closes it; the batting "----"
            # rules are ignored.
            if line.startswith("*") and section in ("bowling", "fow"):
                section = "footer"
            continue

        im = INNINGS_RE.match(line)
        if im and not TOTAL_RE.match(line):
            team = im.group("team").strip()
            prior = sum(1 for x in match.innings if x.team == team)
            cur = Innings(team=team, number=len(match.innings) + 1, team_innings=prior + 1,
                          listed=len(match.innings) + 1)
            cur.follow_on = "follow" in im.group("rest").lower()
            match.innings.append(cur)
            bat_cols = _header_cols(im.group("rest"), BAT_COLS)
            section, pos = "batting", 0
            continue

        if section == "header":
            header.append(line)
            continue

        if cur is not None and section in ("batting", "bowling", "fow", "footer"):
            if EXTRAS_RE.match(line):
                _extras(line, cur)
                continue
            if TOTAL_RE.match(line):
                _total(line, cur)
                section = "after_total"
                continue
            if FOW_RE.match(line):
                section = "fow"
                cur.fow.extend((int(a), int(b)) for a, b in FOW_PAIR_RE.findall(line))
                continue

        hdr = _header_cols(line, BOWL_COLS)
        if ("o" in hdr or "balls" in hdr) and "w" in hdr and not re.search(r"\d", line):
            section, bowl_cols = "bowling", hdr
            continue

        if section == "batting" and cur is not None:
            pos += 1
            if (e := _batting_row(line, bat_cols, pos)) is not None:
                cur.batting.append(e)
            else:
                pos -= 1
        elif section == "bowling" and cur is not None:
            if (b := _bowling_row(line, bowl_cols)) is not None:
                cur.bowling.append(b)
        elif section == "fow" and cur is not None and FOW_PAIR_RE.match(line):
            cur.fow.extend((int(a), int(b)) for a, b in FOW_PAIR_RE.findall(line))
        elif section in ("footer", "after_total", "fow"):
            if pm := POTM_RE.match(line):
                match.player_of_match = pm.group("name").strip()
            elif RESULT_RE.search(line) and not match.result:
                match.result = line

    if not match.innings:
        raise ScorecardError("no innings found - is this a Cricket Captain scorecard?")

    # ---- header: "A v B" then "<title> - <date>" ----
    for h in header:
        if not match.team1 and (tm := TEAMS_RE.match(h)):
            match.team1, match.team2 = tm.group("a").strip(), tm.group("b").strip()
        elif match.team1 and not match.title:
            title, _, when = h.rpartition(" - ")
            if title and parse_date(when):
                match.title, match.date = title.strip(), parse_date(when)
            else:
                match.title, match.date = h, parse_date(h)
    if not match.team1:
        seen = list(dict.fromkeys(i.team for i in match.innings))
        match.team1, match.team2 = seen[0], (seen[1] if len(seen) > 1 else "")
    if match.date is None:
        match.date = parse_date(source)
    if sm := SERIES_RE.match(match.title):
        match.series_match_no, match.series_length = int(sm.group("no")), int(sm.group("of"))

    teams = [match.team1, match.team2]
    for inn in match.innings:
        inn.bowling_team = next((t for t in teams if t and t != inn.team), "")
        _assign_bowlers(inn)
    _assign_fielders(match)

    match.__dict__.update(parse_result(match.result, teams))
    _fix_follow_on(match)
    _check_margin(match)
    return match


def _check_margin(match: Match) -> None:
    """Work the margin out from the scores rather than trusting the printed
    result: one CC2026 scorecard says "India won by 127 runs" for 377 v 200.
    Rain-adjusted results (D/L, DLS, revised target) are left as printed."""
    if match.result_type != "win" or not match.innings or re.search(r"d/?l|dls|revised|target", match.result, re.I):
        return
    agg: dict[str, int] = {}
    for inn in match.innings:
        agg[inn.team] = agg.get(inn.team, 0) + inn.total
    loser = next((t for t in (match.team1, match.team2) if t != match.winner), "")
    last = match.innings[-1]
    if match.margin_wickets is not None and last.team == match.winner:
        real = 10 - last.wickets
        if real != match.margin_wickets:
            match.margin_note = f"The game printed {match.margin_wickets} wickets; the scores give {real}."
            match.margin_wickets = real
    elif match.margin_runs is not None and loser in agg:
        real = agg[match.winner] - agg[loser]
        if real != match.margin_runs and real > 0:
            match.margin_note = f"The game printed {match.margin_runs} runs; the scores give {real}."
            match.margin_runs = real


def _fix_follow_on(match: Match) -> None:
    """Put the innings in the order they were batted.

    The game lists a four-innings match in team order (A, B, A, B) even when
    B followed on, so the order in the file is then A, B, A, B although the
    batting order was A, B, B, A.  The result settles it: a side that wins
    "by N wickets" batted last, a side that loses "by N runs" batted last,
    and in a draw the side batting last is the one not bowled out."""
    inns = match.innings
    if len(inns) != 4 or inns[0].team != inns[2].team or inns[1].team == inns[0].team:
        return
    a1, b1, a2, b2 = inns
    if a1.total - b1.total < 150:  # too small a lead to enforce the follow-on
        return
    last = None
    if match.result_type == "win" and match.margin_wickets is not None:
        last = match.winner
    elif match.result_type == "win" and match.margin_runs is not None:
        last = b1.team if match.winner == a1.team else a1.team
    elif match.result_type in ("draw", "") and not a2.all_out and b2.all_out:
        last = a1.team
    if last == a1.team:
        b2.follow_on = True
        match.innings = [a1, b1, b2, a2]
        for i, inn in enumerate(match.innings, 1):
            inn.number = i
