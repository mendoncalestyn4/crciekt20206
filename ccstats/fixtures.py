"""Your schedule.  You add series and tournaments on the Fixtures page (with the
pickers, or typed one per line); each fixture is ticked off when its scorecard
turns up, matched by teams, format and order (dates are optional: a fixture takes
its exact date from its scorecard).  On top of that: the next match, series
previews and live series situations, the World Test Championship race with your
remaining Tests, milestone countdowns, season goals, series reports, a year
calendar, and home / away taken from your schedule."""

from __future__ import annotations

import copy
import math
import re
import uuid
from itertools import product

import numpy as np
import pandas as pd

from .competitions import KNOWN
from .stats import ordinal

FORMATS = ["Test", "ODI", "T20I", "T20", "The Hundred", "List A", "First-class"]
INTL = {"Test", "ODI", "T20I"}
NATIONS = {"Afghanistan", "Australia", "Bangladesh", "England", "India", "Ireland", "New Zealand", "Pakistan",
           "South Africa", "Sri Lanka", "West Indies", "Zimbabwe", "Scotland", "Netherlands", "Nepal", "Namibia",
           "Oman", "United Arab Emirates", "USA", "Canada", "Papua New Guinea", "Uganda", "Hong Kong", "Kenya"}
ABBR = {"eng": "England", "aus": "Australia", "ind": "India", "nz": "New Zealand", "sa": "South Africa",
        "rsa": "South Africa", "wi": "West Indies", "sl": "Sri Lanka", "pak": "Pakistan", "ban": "Bangladesh",
        "bang": "Bangladesh", "afg": "Afghanistan", "ire": "Ireland", "zim": "Zimbabwe", "sco": "Scotland",
        "ned": "Netherlands", "uae": "United Arab Emirates", "nep": "Nepal"}
TOURNAMENTS = ["T20 World Cup", "ODI World Cup", "Champions Trophy", "Asia Cup", "World Test Championship Final"]
TOURNAMENT_FORMAT = {"T20 World Cup": "T20I", "ODI World Cup": "ODI", "Champions Trophy": "ODI",
                     "World Test Championship Final": "Test"}
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
COLUMNS = ["id", "team", "series", "opponent", "format", "no", "venue", "date", "month", "games"]


def new_id() -> str:
    return uuid.uuid4().hex[:10]


def month_label(month: str) -> str:
    """'2027-01' -> 'Jan 2027'."""
    if not month:
        return ""
    y, mo = month.split("-")
    return f"{MONTHS[int(mo) - 1]} {y}"


def plural(fmt: str, n: int) -> str:
    word = {"Test": "Test", "ODI": "ODI", "T20I": "T20I", "T20": "T20", "The Hundred": "Hundred game",
            "List A": "one-day game", "First-class": "first-class game"}.get(fmt, fmt)
    return f"{n} {word}{'' if n == 1 else 's'}"


def series_label(opponent: str, fmt: str, n: int, venue: str, month: str, date: str = "") -> str:
    when = month_label(month) if month else ""
    if n == 1 and date:
        when = pd.Timestamp(date).strftime("%d %b %Y")
    bits = [f"v {opponent}", plural(fmt, n)] + ([venue] if venue else []) + ([when] if when else [])
    return " · ".join(bits)


def make_series(team: str, opponent: str, fmt: str, n: int, venue: str = "", month: str = "", date: str = "") -> list[dict]:
    """Rows for a series of n matches (1 = a one-off)."""
    if date and not month:
        month = pd.Timestamp(date).strftime("%Y-%m")
    label = series_label(opponent, fmt, n, venue, month, date)
    return [dict(id=new_id(), team=team, series=label, opponent=opponent, format=fmt, no=k, venue=venue,
                 date=date if k == 1 else "", month=month, games=0) for k in range(1, n + 1)]


def make_tournament(team: str, name: str, fmt: str, month: str = "", games: int = 0) -> list[dict]:
    label = name + (f" · {month_label(month)}" if month else "")
    # no venue: a tournament's home and away (a World Cup at home, an IPL home game) come from the scorecards
    return [dict(id=new_id(), team=team, series=label, opponent="", format=fmt, no=0, venue="", date="",
                 month=month, games=int(games or 0))]


# --------------------------------------------------------------------------- #
# typing it instead: one series, match or tournament per line
# --------------------------------------------------------------------------- #

MON_NAMES = "jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec"
_FMT_WORDS = r"(tests?|odis?|t20is?|t20s?|one-?day(?:ers?)?|hundred|list a|first-class|fc)"
RE_ISO = re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b")
RE_DMY = re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?[\s/.-]+((?:{MON_NAMES})[a-z]*\.?|\d{{1,2}})[\s/.-]+(\d{{4}})\b")
RE_MON_YEAR = re.compile(rf"\b((?:{MON_NAMES}))[a-z]*\.?\s+(\d{{4}})\b")
RE_YEAR_MON = re.compile(r"\b(\d{4})-(\d{1,2})\b")


def _mon_num(word: str) -> int:
    return [x.lower() for x in MONTHS].index(word[:3].lower()) + 1


def _fmt_of(word: str) -> str:
    w = word.lower()
    if w.startswith("test"):
        return "Test"
    if w.startswith("odi") or w.startswith("one"):
        return "ODI"
    if w.startswith("t20i"):
        return "T20I"
    if w.startswith("t20"):
        return "T20"
    if "hundred" in w:
        return "The Hundred"
    if w == "list a":
        return "List A"
    return "First-class"


TOURNEY_RE = re.compile(r"\b(cup|trophy|championship|league|tournament|wtc|final|qualifier[12]?|eliminator[12]?)\b")
_NOT_TEAM = {"test", "tests", "odis", "t20s", "t20is", "home", "away", "neutral", "match", "matches", "games", "series"}
_TRAILING_FMT = re.compile(r"tests?|odis?|t20is?|t20s?|fc|first-class")
# a format word followed by one of these starts a name ("T20 World Cup", "T20 Blast", "ODI Super League")
_NAME_AFTER_FMT = {"world", "blast", "cup", "league", "challenge", "championship", "bash", "trophy", "series", "super",
                   "final", "qualifier", "smash", "cricket", "competition"}
_KNOWN_KEYS = sorted(KNOWN, key=lambda k: (-len(k), k))  # the longest name first ("t20 world cup" before "world cup")
_KNOWN_NAMES = {v[0] for v in KNOWN.values()}  # the site's own competition names
_ALIASES = {"ipl": "indian premier league", "psl": "pakistan super league", "bbl": "big bash league",
            "cpl": "caribbean premier league", "bpl": "bangladesh premier league", "lpl": "lanka premier league",
            "mlc": "major league cricket"}
# a stage names no event of its own (a tournament's knockout games come with it by themselves); "Qualifier 1"
# is joined up first ("qualifier1") so its number is never read as a day or a match count
_STAGE_NO = re.compile(r"\b(qualifier|eliminator)\s+([12])\b(?!\s*(?:matches|match|games|game)\b)")
_STAGE_WORDS = re.compile(r"(?<![a-z])(?:(?:semi|quarter)[- ]?)?finals?(?![a-z])|(?<![a-z])(?:qualifier|eliminator)[12](?![0-9])"
                          r"|(?<![a-z])eliminator(?![a-z])|(?<![a-z])play-?offs?(?![a-z])")
_PLACEHOLDER = r"\b(?:tbc|tba|tbd|opponent|opposition|winner)\b|\?+"  # "v TBC", "v ?": the opponent isn't known yet
_MODIFIERS = r"u19|u-19|under-19|under 19|legends|women's|womens|women|emerging|youth|masters|veterans"


def _exact_team(text: str, known: list[str]) -> tuple[str, str]:
    """(team, text without it): a full team name (longest first), else a short form (NZ, SA, WI)."""
    low = f" {text} "
    for t in sorted(set(known), key=lambda t: (-len(t), t)):  # longest first, then A-Z: the same every run
        mm = re.search(rf"(?<![a-z]){re.escape(t.lower())}(?![a-z])", low)
        if mm:
            return t, low[:mm.start()] + " " + low[mm.end():]
    for w in low.split():
        if w in ABBR and ABBR[w] in known:
            return ABBR[w], re.sub(rf"(?<![a-z]){re.escape(w)}(?![a-z])", " ", low)
    return "", low


def _guess_team(parts: list[str], known: list[str]) -> tuple[str, str, list[str]]:
    """A team from one word of these parts of the line ("Kolkata", "Austral"): the first word of 4+ letters
    that starts a word of exactly one team's name.  (team, that word, the teams a word could mean when it
    fits several and no word fits one)."""
    unsure: list[str] = []
    for part in parts:
        for w in part.split():
            if len(w) < 4 or w in _NOT_TEAM or not re.fullmatch(r"[a-z][a-z'.-]*", w):
                continue
            hits = sorted({t for t in known if any(x.startswith(w) for x in t.lower().split())})
            if len(hits) == 1:
                return hits[0], w, []
            if len(hits) > 1 and not unsure:
                unsure = hits
    return "", "", unsure


def _tidy(text: str) -> str:
    """Lower case; short forms spelt out (IPL, PSL, BBL …); brackets gone; "T20I World Cup" is the T20 World Cup;
    a stage's number joined to it ("qualifier1")."""
    s = f" {text.lower()} "
    s = re.sub(r"[\[\]·,;|–—]", " ", s)  # round brackets stay until "(h)" / "(a)" are read
    s = re.sub(rf"\b({'|'.join(_ALIASES)})\b", lambda mm: _ALIASES[mm.group(1)], s)
    s = re.sub(r"\bt20is?(?=\s+world\b)", "t20", s)
    return _STAGE_NO.sub(r"\1\2", s)


def _known_competition(s: str) -> tuple[str, tuple | None, tuple | None, str]:
    """In tidied text: (its title, the competition's entry when the title is exactly a competition the site knows,
    the competition named in it at all, the text without that name).  "U19 World Cup", "Legends World Cup"
    and an international "… Qualifier" are events of their own: titled so, with no entry; a sponsor's name
    ("Royal London", "Vitality") is dropped.  ("World Cup 2027" isn't "World Cup 20", the T20 one.)"""
    km = next((mm for k in _KNOWN_KEYS for mm in [re.search(rf"(?<![a-z0-9]){re.escape(k)}(?![a-z0-9])", s)] if mm), None)
    if not km:
        return "", None, None, s
    key = km.group(0)
    base = KNOWN[key]
    rest = re.sub(rf"(?<![a-z0-9]){re.escape(key)}(?![a-z0-9])", " ", s)
    mod = re.search(rf"\b({_MODIFIERS})\s+(?:[a-z0-9-]+\s+)?{re.escape(key)}", s)
    qual = base[2] == "International" and re.search(r"\bqualifiers?\b", rest)
    if mod or qual:
        title = " ".join(x for x in ((mod.group(1).capitalize() if mod else ""), base[0], "Qualifier" if qual else "") if x)
        return title, None, base, rest
    return base[0], base, base, rest


def canonical_tournament(name: str) -> str:
    """The site's name for a tournament name typed anywhere (the picker's "Other…" too): "IPL" -> Indian
    Premier League, "Vitality Blast" -> T20 Blast, "U19 World Cup" -> U19 ODI World Cup; a name the site
    doesn't know is kept as typed, without any stage ("Big Bash semi-final" -> Big Bash)."""
    title, _, _, _ = _known_competition(re.sub(r"[()]", " ", _tidy(name)))
    if title:
        return title
    plain = re.sub(r"(?i)\b((?:semi|quarter)[- ]?finals?|finals?|play-?offs?|eliminator(?:\s*[12])?|qualifier\s*[12])\b",
                   " ", name)
    return " ".join(plain.split()) or " ".join(name.split())


def parse_line(line: str, team: str, known: list[str]) -> tuple[list[dict], str]:
    """Rows for one typed line, or an explanation of what's missing.

    A competition the site knows is found by its name first (its words are never a team's).  The opponent: a
    full team name or a short form (NZ, SA) anywhere else in the line; otherwise one word of it ("Kolkata",
    "Austral"), looked for only in the parts of the line that aren't a tournament's name.  Beside a known
    competition with no "v", a country is where it's played, never the opponent ("T20 World Cup in India",
    "IPL in India"); in a league a franchise or county named is ("IPL Mumbai Indians").  A line with "v" and
    a number of matches ("… v Austral 3 Tests") is a series.  Without an opponent it's a tournament; a format
    typed with it ("IPL T20", "Asia Cup (T20I)") is used as typed, and format words inside a name ("T20 World
    Cup", "One-Day Cup") only help work it out.  A stage ("final", "Qualifier 1") names no event of its own."""
    raw = line.strip()
    if not raw or raw.startswith("#"):
        return [], ""
    s = _tidy(raw)
    date = month = ""
    try:
        if (m := RE_ISO.search(s)):
            date = pd.Timestamp(int(m.group(1)), int(m.group(2)), int(m.group(3))).strftime("%Y-%m-%d")
            s = s.replace(m.group(0), " ")
        elif (m := RE_DMY.search(s)):
            mo = m.group(2)
            date = pd.Timestamp(int(m.group(3)), int(mo) if mo.isdigit() else _mon_num(mo),
                                int(m.group(1))).strftime("%Y-%m-%d")
            s = s.replace(m.group(0), " ")
    except (ValueError, IndexError):
        return [], f"couldn't read the date in “{raw}”"
    if date:
        month = date[:7]
    elif (m := RE_MON_YEAR.search(s)):
        month = f"{int(m.group(2)):04d}-{_mon_num(m.group(1)):02d}"
        s = s.replace(m.group(0), " ")
    elif (m := RE_YEAR_MON.search(s)) and 1 <= int(m.group(2)) <= 12:
        month = f"{int(m.group(1)):04d}-{int(m.group(2)):02d}"
        s = s.replace(m.group(0), " ")
    venue = ""
    mv = re.search(r"\b(home|away|neutral)\b|\((h|a|n)\)|(?:^|\s)@(?=\s)", s)
    if mv:
        venue = {"h": "home", "a": "away", "n": "neutral"}.get((mv.group(2) or ""), mv.group(1) or "away")
        s = s.replace(mv.group(0), " ")
    s = re.sub(r"[()]", " ", s)  # "Asia Cup (T20I)"
    fmt, n = "", None
    mc = re.search(rf"\b(\d+|{'|'.join(WORDS)})\s*(?:x\s*)?{_FMT_WORDS}\b", s)
    if mc:
        n = int(mc.group(1)) if mc.group(1).isdigit() else WORDS[mc.group(1)]
        fmt = _fmt_of(mc.group(2))
        s = s.replace(mc.group(0), " ")
    games = 0
    mg = re.search(r"\b(\d+)\s*(?:matches|match|games|game)\b", s)
    if mg:
        games = int(mg.group(1))
        s = s.replace(mg.group(0), " ")
    s = re.sub(rf"(?<![a-z]){re.escape(team.lower())}(?![a-z])", " ", s)  # your own team isn't the opponent
    others = sorted(set(known) - {team}, key=lambda t: (-len(t), t))  # longest first, then A-Z: the same every run
    title, comp, named_comp, team_text = _known_competition(s)
    parts = re.split(r"\b(?:v|vs|versus|against)\b", team_text)
    has_v = len(parts) > 1
    later = " ".join(parts[1:])
    placeholder = has_v and re.match(rf"\s*(?:{_PLACEHOLDER})", later)  # "final v TBC", "v ?"
    opp, rest = "", team_text
    if not placeholder:
        if named_comp and not has_v:
            # beside a known competition: a country is where it's played; in a league, a franchise or county
            # named is the opponent ("IPL Mumbai Indians Apr 2027")
            if named_comp[2] != "International":
                clubs = [t for t in others if t not in NATIONS]
                opp, rest = _exact_team(re.sub(rf"\b({'|'.join(map(re.escape, ABBR))})\b", " ", team_text), clubs)
        else:
            opp, rest = _exact_team(team_text, others)
            if not opp:
                guess, word, unsure = _guess_team([x for x in parts if not TOURNEY_RE.search(x)], others)
                if guess:
                    opp, rest = guess, re.sub(rf"(?<![a-z]){re.escape(word)}(?![a-z])", " ", team_text)
                elif unsure:
                    return [], f"“{raw}” could mean {' or '.join(unsure[:3])}: write more of the name"
                elif has_v and (n or games) and later.strip():
                    return [], f"couldn't find the team after “v” in “{raw}”: check the spelling of the opponent"
    if opp:
        if not fmt:
            mf = re.search(rf"\b{_FMT_WORDS}\b", rest)  # a format typed on the line comes first…
            if mf:
                fmt = _fmt_of(mf.group(1))
            elif named_comp and named_comp[1]:  # …else the competition's ("IPL Mumbai Indians 1 match": a T20)
                fmt = named_comp[1]
        if not fmt:
            return [], f"say the format (Tests, ODIs or T20Is) in “{raw}”"
        if fmt == "T20" and opp in NATIONS:  # a T20 between countries is a T20I; a franchise game stays T20
            fmt = "T20I"
        if fmt == "T20I" and opp not in NATIONS:
            fmt = "T20"
        n = n or games or 1
        if n > 10:
            return [], f"{n} matches in one series? Check “{raw}”"
        return make_series(team, opp, fmt, n, venue, month, date), ""
    # a tournament: a format word typed with it is used as typed; one that starts a name is part of the name
    tokens = s.split()
    typed, name_tokens = fmt, []
    for i, w in enumerate(tokens):
        nxt = tokens[i + 1] if i + 1 < len(tokens) else ""
        if _TRAILING_FMT.fullmatch(w) and nxt not in _NAME_AFTER_FMT:
            typed = typed or _fmt_of(w)
            if w in {"t20i", "t20is"} and not fmt:  # "T20I" beats a "T20" typed earlier
                typed = "T20I"
            continue
        name_tokens.append(w)
    if not title:
        # the name is the part of the line that reads like one (before "v", or after it: "v TBC … Cup"), without
        # a stage or a placeholder
        text = " ".join(name_tokens)
        bits = re.split(r"\b(?:v|vs|versus|against)\b", text)
        name_bit = next((b for b in bits if TOURNEY_RE.search(b)), bits[0] if bits[0].strip() else " ".join(bits))
        name_bit = _STAGE_WORDS.sub(" ", re.sub(rf"(?:{_PLACEHOLDER})", " ", name_bit))
        name = " ".join(w for w in re.sub(r"\b(the|in|at|of|for)\b", " ", name_bit).split() if w)
        staged = bool(_STAGE_WORDS.search(text))  # "Big Bash semi-final": a tournament's name before its stage
        if not name or not (staged or re.search(r"cup|trophy|championship|league|tournament|wtc|series|games|qualifier", name)):
            return [], (f"say which tournament in “{raw}”" if TOURNEY_RE.search(text) else
                        f"couldn't find a team or a tournament in “{raw}”: check the spelling of the opponent")
        if "wtc" in name.split() or "test championship" in name:
            name = "world test championship final"
        title = " ".join(w.upper() if re.fullmatch(r"t20i?|odi|wtc|ipl", w) else w.capitalize() for w in name.split())
        comp = KNOWN.get(name) or KNOWN.get(f"the {name}")
        if comp:
            title = comp[0]
    known_t = next((t for t in TOURNAMENTS if t.lower() == title.lower()), title)
    tf = typed or TOURNAMENT_FORMAT.get(known_t) or (named_comp[1] if named_comp and named_comp[1] else "") or (
        "T20I" if "T20" in title else "Test" if "Test" in title or "WTC" in title
        else "ODI" if "Cup" in title or "Trophy" in title else "")
    if tf == "T20" and team in NATIONS:
        tf = "T20I"
    icc = known_t in TOURNAMENT_FORMAT or "World Cup" in title or bool(named_comp and named_comp[2] == "International")
    if not typed and team not in NATIONS and not icc:
        # worked out from the name for a franchise or county: its own formats (a county's "One-Day Cup" is List A)
        tf = {"T20I": "T20", "ODI": "List A", "Test": "First-class"}.get(tf, tf)
    if not tf:
        return [], f"say the format for “{raw}” (e.g. add ODI or T20I)"
    return make_tournament(team, known_t, tf, month, games or (n or 0)), ""


def parse_lines(text: str, team: str, known: list[str]) -> tuple[list[dict], list[str]]:
    rows, errors = [], []
    for line in text.splitlines():
        r, e = parse_line(line, team, known)
        rows += r
        if e:
            errors.append(e)
    return rows, errors


def merge(existing: list[dict], new: list[dict]) -> tuple[list[dict], int]:
    """Add new rows, skipping any series already in the schedule (same team, label and match number)."""
    have = {(r["team"], r["series"], int(r["no"])) for r in existing}
    added = [r for r in new if (r["team"], r["series"], int(r["no"])) not in have]
    return existing + added, len(added)


# --------------------------------------------------------------------------- #
# 141 · ticking fixtures off as their scorecards arrive
# --------------------------------------------------------------------------- #

BILATERAL = {"Test", "ODI", "T20I"}


def _month_start(month: str):
    return pd.Timestamp(f"{month}-01") if month else pd.NaT


def _outcome(r, team: str) -> str:
    win = r.winner or (r.tiebreak_winner if r.result_type == "tie" else "")
    if win == team:
        return "W"
    if win:
        return "L"
    return {"draw": "D", "tie": "T"}.get(r.result_type, "NR")


def _score(career, mid: str, team: str) -> str:
    inn = career.innings[(career.innings.match_id == mid) & (career.innings.team == team)].sort_values("innings_no")
    return " & ".join(f"{r.runs}" if r.all_out else f"{r.runs}/{r.wickets}{'d' if r.declared else ''}"
                      for r in inn.itertuples()) or "–"


KO_NEXT = {"Quarter-final": "Semi-final", "Semi-final": "Final", "Qualifier 1": "Final", "Qualifier 2": "Final"}
AUTO = " · auto-added"


def _through(r) -> str:
    """Who went through: the winner, or the side a drawn or tied knockout was settled for."""
    return r.winner or r.tiebreak_winner or ""


def knockout_next(career, mine: pd.DataFrame, team: str) -> tuple[str, str] | None:
    """After the team's latest match in a tournament (`mine`: their matches in it):
    (the knockout game they play next, who against if that's decided yet), or None
    when there's none to come (knocked out, the final played, or still in the group).
    The opponent comes from the other knockout games already in the files: the
    other semi-final's winner, the Eliminator's winner for Qualifier 2, and so on."""
    if mine.empty:
        return None
    last = mine.sort_values(["date", "match_id"]).iloc[-1]
    if not last.knockout or last.stage == "Final":
        return None
    m = career.matches
    ev = m[(m.event == last.event) & (m.season == last.season) & m.knockout]
    won = _through(last) == team
    if won:
        nxt = KO_NEXT.get(last.stage)
        if last.stage == "Eliminator":  # IPL: on to Qualifier 2; The Hundred: straight to the final
            sec = m[(m.section == last.section) & m.stage.isin(["Qualifier 1", "Qualifier 2"])]
            nxt = "Qualifier 2" if len(sec) else "Final"
        if not nxt:
            return None
    elif last.stage == "Qualifier 1":
        nxt = "Qualifier 2"  # the loser of Qualifier 1 gets a second go
    else:
        return None  # knocked out (or a knockout with no result we can't settle)

    def winner_of(stage):  # the other side through from that stage (the team itself is never its own opponent)
        w = {_through(r) for r in ev[ev.stage == stage].itertuples()} - {"", team}
        return w.pop() if len(w) == 1 else ""

    def loser_of(stage):
        g = ev[ev.stage == stage]
        lo = {(r.away if _through(r) == r.home else r.home) for r in g.itertuples() if _through(r)} - {team}
        return lo.pop() if len(lo) == 1 else ""

    opp = ""
    if nxt == "Final" and last.stage == "Semi-final":
        opp = winner_of("Semi-final")
    elif nxt == "Final" and last.stage == "Qualifier 1":
        opp = winner_of("Qualifier 2")
    elif nxt == "Final" and last.stage == "Qualifier 2":
        opp = winner_of("Qualifier 1")
    elif nxt == "Qualifier 2" and last.stage == "Qualifier 1":
        opp = winner_of("Eliminator")
    elif nxt == "Qualifier 2" and last.stage == "Eliminator":
        opp = loser_of("Qualifier 1")
    return nxt, opp


def _auto_since(career, fx: pd.DataFrame, team: str, anchor_of):
    """From when a team's unscheduled matches are added to its schedule: the start of
    the year of its latest match (or of the season that match is in, if that began
    earlier), or the start of its schedule if that's earlier still."""
    mine = fx[fx.team == team]
    anchors = [a - pd.Timedelta(days=15) for a in (anchor_of(r) for _, r in mine.iterrows()) if pd.notna(a)]
    m = career.matches
    g = m[(m.home == team) | (m.away == team)]
    if g.empty:
        return min(anchors) if anchors else None
    last = g.sort_values("date").iloc[-1]
    season_start = g[(g.section == last.section) & (g.season == last.season)].date.min()
    return min([pd.Timestamp(year=last.date.year, month=1, day=1), season_start] + anchors)


def _event_ok(title: str, words: list[str], event: str) -> bool:
    """Is this competition-as-run (an event) the tournament in the schedule called `title`?"""
    if title in _KNOWN_NAMES:  # exactly that competition (or a division of it: "County Championship · Division 1")
        return event == title or event.startswith(title + " ·")
    ev = event.lower()
    if not all(w in ev for w in words):
        return False
    # "World Cup" isn't the U19 World Cup or a qualifier: a word that makes another event must be in the name too
    extra = re.findall(rf"\b(qualifier|{_MODIFIERS})\b", ev)
    return all(x in title.lower() for x in extra)


def track(career, fixtures: list[dict], auto=()) -> pd.DataFrame:
    """One row per fixture (tournaments: one row per match played so far, plus one
    for the games still to come), with: status (played / next / to come), the
    match it was matched to, the result from the team's side and the scores.

    Nothing the team plays is left out: a scheduled series that turns out longer in
    the game gets its extra matches, a tournament gets its next knockout game
    (semi-final, final …) once the team is through to it, and for the teams in
    `auto` every match they've played this year (or since their schedule starts, if
    earlier) that isn't in it is added (series by series, tournament by tournament),
    marked auto-added."""
    cols = COLUMNS + ["kind", "status", "match_id", "played_date", "outcome", "result", "score", "anchor", "stage",
                      "auto"]
    auto = [t for t in dict.fromkeys(auto or ()) if t]
    if not fixtures and not auto:
        return pd.DataFrame(columns=cols)
    m = career.matches.copy()
    fx = pd.DataFrame(fixtures or [], columns=COLUMNS)
    fx["no"] = pd.to_numeric(fx["no"], errors="coerce").fillna(0).astype(int)
    fx["games"] = pd.to_numeric(fx["games"], errors="coerce").fillna(0).astype(int)
    fx = fx.fillna("")
    claimed: set[str] = set()
    hit: dict[str, str] = {}
    extra: dict[tuple, tuple[list, int]] = {}  # (team, series) -> (matches beyond the fixtures, the series' length)
    out_rows = []

    def anchor_of(r):
        if r["date"]:
            return pd.Timestamp(r["date"])
        return _month_start(r["month"])

    # bilateral series and one-off matches, earliest first (undated last)
    groups = []
    for key, g in fx[fx.opponent != ""].groupby(["team", "series", "opponent", "format"], sort=False):
        g = g.sort_values("no")
        a = anchor_of(g.iloc[0])
        groups.append((a if pd.notna(a) else pd.Timestamp.max, key, g))
    for _, (team, _series, opp, fmt), g in sorted(groups, key=lambda x: x[0]):
        a = anchor_of(g.iloc[0])
        cand = m[(((m.home == team) & (m.away == opp)) | ((m.home == opp) & (m.away == team))) & (m.format == fmt)
                 & ~m.match_id.isin(claimed)].sort_values(["date", "match_id"])
        if cand.empty:
            continue
        window = 4 if g.iloc[0]["date"] else 45
        picked = []
        series_c = cand[cand.series_id != ""]
        if fmt in BILATERAL and len(series_c):
            starts = series_c.groupby("series_id").date.min().sort_values()
            if pd.notna(a):
                near = (starts - a).abs()
                near = near[near <= pd.Timedelta(days=window + (31 if not g.iloc[0]["date"] else 0))]
                sid = near.idxmin() if len(near) else None
            else:
                sid = starts.index[0]
            if sid is not None:
                in_series = series_c[series_c.series_id == sid].sort_values(["series_match_no", "date"])
                picked = list(in_series.match_id)
                length = int(pd.to_numeric(in_series.series_length, errors="coerce").max() or 0) \
                    if in_series.series_length.notna().any() else 0
                if len(picked) > len(g) or length > len(g):  # the game's series is longer than the one scheduled
                    extra[(team, _series)] = (picked[len(g):], length)
                    claimed.update(picked[len(g):])
        if not picked:  # no series id (a league, or a one-off): each fixture takes the next match in its window
            lo = a - pd.Timedelta(days=window) if pd.notna(a) else pd.Timestamp.min
            hi = a + pd.Timedelta(days=window + (31 if not g.iloc[0]["date"] else 0) + 7 * len(g)) if pd.notna(a) \
                else pd.Timestamp.max
            picked = list(cand[(cand.date >= lo) & (cand.date <= hi)].match_id)
        for (_, r), mid in zip(g.iterrows(), picked):
            hit[r["id"]] = mid
            claimed.add(mid)
    info = m.set_index("match_id")

    def played(row: dict, mid: str, team: str, opp: str) -> dict:
        mr = info.loc[mid]
        row.update(match_id=mid, status="played", played_date=mr.date, outcome=_outcome(mr, team), result=mr.result,
                   score=f"{team} {_score(career, mid, team)} · {opp} {_score(career, mid, opp)}",
                   stage=mr.stage if mr.knockout else "")
        return row

    def to_come(row: dict) -> dict:
        row.update(match_id="", status="to come", played_date=pd.NaT, outcome="", result="", score="")
        row.setdefault("stage", "")
        return row

    for (team, series), g in fx[fx.opponent != ""].groupby(["team", "series"], sort=False):
        for _, r in g.iterrows():
            mid = hit.get(r["id"], "")
            row = {k: r[k] for k in COLUMNS}
            row.update(kind="match", auto=False)
            out_rows.append(played(row, mid, team, r["opponent"]) if mid else to_come(row))
        if (team, series) in extra:
            more, length = extra[(team, series)]
            base = {k: g.sort_values("no").iloc[-1][k] for k in COLUMNS}
            last_no = int(g.no.max() or len(g))
            for k in range(1, max(len(more), length - len(g)) + 1):
                row = dict(base, id=f"{base['id']}+{k}", no=last_no + k, date="", kind="match", auto=True)
                out_rows.append(played(row, more[k - 1], team, base["opponent"]) if k <= len(more) else to_come(row))
    # tournaments: every match the team plays in it (not a bilateral series), in the month's window
    def tournament_rows(r: dict, cand: pd.DataFrame, is_auto: bool) -> None:
        team = r["team"]
        cand = cand.sort_values(["date", "match_id"])
        for i, mid in enumerate(cand.match_id, start=1):
            claimed.add(mid)
            mr = info.loc[mid]
            opp = mr.away if mr.home == team else mr.home
            row = dict(r, id=f"{r['id']}:{i}", opponent=opp, no=i, kind="tournament", auto=is_auto)
            out_rows.append(played(row, mid, team, opp))
        ko = knockout_next(career, cand, team)
        row = dict(r, kind="tournament", no=len(cand) + 1, opponent="", auto=is_auto)
        if ko:  # through to the next knockout game: it's on the schedule, against whoever is known
            row.update(id=f"{r['id']}:{len(cand) + 1}", opponent=ko[1], stage=ko[0], date="",
                       month=f"{cand.date.max():%Y-%m}")
            out_rows.append(to_come(row))
            return
        if cand.knockout.any():  # out, or the final played: nothing more to come
            return
        n_group = len(cand)
        left = max(int(r["games"]) - n_group, 0) if r["games"] else (0 if n_group else 1)
        if left:
            row["games_left"] = left
            out_rows.append(to_come(row))

    played_by_team: dict[str, pd.DataFrame] = {}
    taken_eds: set[tuple] = set()  # (team, event, season) a tournament row already has
    for _, r in fx[fx.opponent == ""].iterrows():
        a = anchor_of(r)
        team = r["team"]
        every = m[((m.home == team) | (m.away == team)) & (m.format == r["format"]) & ~m.competition.isin(BILATERAL)]
        title = r["series"].split("·")[0].strip()
        words = [w for w in re.findall(r"[a-z0-9]+", title.lower()) if w not in ("the", "final", "odi")]
        # a tournament is found by its name: a competition the site knows by exactly that competition ("ODI World
        # Cup" is never its qualifier); another by all the words of its name. A name matching no competition here
        # claims nothing (its row shows "no scorecard" once its month has passed, so a wrong name is noticed).
        hit = np.array([_event_ok(title, words, ev) for ev in every.event], dtype=bool)  # (a list could pick columns)
        named_all = every[hit] if words else every.iloc[0:0]
        named = named_all[~named_all.match_id.isin(claimed)]
        cand = named.iloc[0:0]
        if pd.notna(a):
            # the month says which edition: the one with games around it; then all of that edition's games
            # (the IPL typed as "Mar 2026" keeps its May playoffs)
            near = named_all[(named_all.date >= a - pd.Timedelta(days=15)) & (named_all.date <= a + pd.Timedelta(days=75))]
            eds = set(zip(near.event, near.season))
            if eds and all((team, e, s_) in taken_eds for e, s_ in eds):
                continue  # the same tournament as a row above (e.g. typed twice with different months)
            cand = named[np.array([(e, s_) in eds for e, s_ in zip(named.event, named.season)], dtype=bool)]
        elif words and len(named):
            # no month: only an edition the team is in the middle of: one of its games among the team's last 8
            # played and within 60 days of the last one (a county's Blast runs alongside its Championship games),
            # and not over for them (knocked out, or the final played). Otherwise it's the next edition that's
            # meant, so it waits as to come.
            if team not in played_by_team:
                from .records import by_played
                played_by_team[team] = by_played(career, m[(m.home == team) | (m.away == team)])
            recent = set(played_by_team[team].match_id.tail(8))
            last_day = played_by_team[team].date.tail(8).max() if len(played_by_team[team]) else pd.NaT
            last_ed = named.sort_values(["date", "match_id"]).iloc[-1]
            ed = named[(named.event == last_ed.event) & (named.season == last_ed.season)]
            mine_ed = m[(m.event == last_ed.event) & (m.season == last_ed.season) & ((m.home == team) | (m.away == team))]
            over = mine_ed.knockout.any() and knockout_next(career, mine_ed, team) is None
            recent_enough = pd.notna(last_day) and ed.date.max() >= last_day - pd.Timedelta(days=60)
            cand = ed if set(ed.match_id) & recent and recent_enough and not over else named.iloc[0:0]
            if not cand.empty and (team, last_ed.event, last_ed.season) in taken_eds:
                continue  # the same tournament as a row above
        taken_eds.update((team, e, s_) for e, s_ in zip(cand.event, cand.season))
        tournament_rows({k: r[k] for k in COLUMNS}, cand, False)
    # whatever the team played from the start of its schedule that isn't in it: added, series by series
    for team in auto:
        since = _auto_since(career, fx, team, anchor_of)
        if since is None:
            continue
        rest = m[((m.home == team) | (m.away == team)) & ~m.match_id.isin(claimed)]
        bilateral = rest[rest.competition.isin(BILATERAL)]
        for sid in bilateral.series_id.where(bilateral.series_id != "", bilateral.match_id).unique():
            # the whole series, so a match already in the schedule elsewhere isn't taken for a missing one
            g = (m[m.series_id == sid] if (m.series_id == sid).any() else m[m.match_id == sid]).sort_values(
                ["date", "match_id"])
            if g.date.max() < since:
                continue
            first = g.iloc[0]
            opp = first.away if first.home == team else first.home
            venue = "neutral" if first.neutral else ("home" if first.home == team else "away")
            nos = pd.to_numeric(g.series_match_no, errors="coerce")
            numbered = bool(nos.notna().all() and nos.is_unique)
            length = int(max(pd.to_numeric(g.series_length, errors="coerce").max() if g.series_length.notna().any()
                             else 0, nos.max() if numbered else 0, len(g)))
            month = f"{first.date:%Y-%m}"
            label = series_label(opp, first.format, length, venue, month) + AUTO
            base = dict(id=f"auto:{team}:{sid}", team=team, series=label, opponent=opp, format=first.format, no=0,
                        venue=venue, date="", month=month, games=0)
            by_no = {int(n): mid for n, mid in zip(nos, g.match_id)} if numbered else \
                {k: mid for k, mid in enumerate(g.match_id, start=1)}
            top = max(by_no)
            when = {k: info.loc[mid].date for k, mid in by_no.items()}
            for k in range(1, length + 1):
                row = dict(base, id=f"{base['id']}:{k}", no=k, kind="match", auto=True)
                mid = by_no.get(k)
                if mid in claimed:
                    continue  # it's in the schedule already, as another fixture
                if mid:
                    out_rows.append(played(row, mid, team, opp))
                    claimed.add(mid)
                else:
                    row = to_come(row)
                    if k < top:  # a later match of the series is in: this one was played, its file isn't
                        row["status"] = "no scorecard"
                        prev = [j for j in when if j < k]
                        row["_anchor"] = (when[max(prev)] + pd.Timedelta(days=k - max(prev)) if prev else
                                          when[min(when)] - pd.Timedelta(days=min(when) - k))
                    out_rows.append(row)
        others = rest[~rest.competition.isin(BILATERAL)]
        for (event, season), g in others.groupby(["event", "season"], sort=False):
            if g.date.max() < since:
                continue
            first = g.sort_values("date").iloc[0]
            r = dict(id=f"auto:{team}:{event}:{season}", team=team, series=f"{event} {season}{AUTO}", opponent="",
                     format=first.format, no=0, venue="neutral" if first.neutral else "", date="",
                     month=f"{first.date:%Y-%m}", games=0)
            tournament_rows(r, g, True)
    if not out_rows:
        return pd.DataFrame(columns=cols)
    t = pd.DataFrame(out_rows)
    for c in cols:
        if c not in t:
            t[c] = np.nan
    # the order: played by date; to come by its date, else its month (+ its number), else after everything
    def key(r):
        if r["status"] == "played":
            return r["played_date"]
        if "_anchor" in r and pd.notna(r["_anchor"]):
            return r["_anchor"]
        if r["date"]:
            return pd.Timestamp(r["date"])
        if r["month"]:
            return _month_start(r["month"]) + pd.Timedelta(days=int(r["no"] or 0))
        return pd.Timestamp("2200-01-01") + pd.Timedelta(days=int(r["no"] or 0))
    t["anchor"] = [key(r) for _, r in t.iterrows()]
    t = t.drop(columns=["_anchor"], errors="ignore")
    # a fixture still to come can't be before a match already played in the same series (a knockout game
    # follows the last one within days; the next match of a series by its number)
    for (team, series), g in t.groupby(["team", "series"]):
        done = g[g.status == "played"]
        if len(done):
            last = done.anchor.max()
            for i in g[(g.status == "to come")].index:
                if t.at[i, "anchor"] <= last:
                    gap = 1 if t.at[i, "kind"] == "tournament" else int(t.at[i, "no"] or 1) - int(
                        done.no.max() if done.no.notna().any() else 0)
                    t.at[i, "anchor"] = last + pd.Timedelta(days=max(gap, 1))
    t = t.sort_values(["team", "anchor", "no"]).reset_index(drop=True)
    # a fixture whose time has long gone with no scorecard (wrong month or opponent, or a file the game didn't save)
    for team, g in t.groupby("team"):
        last = m[(m.home == team) | (m.away == team)].date.max()
        if pd.isna(last):
            continue
        stale = g[(g.status == "to come") & (g.anchor < last - pd.Timedelta(days=30))]
        t.loc[stale.index, "status"] = "no scorecard"
    for team, g in t.groupby("team"):
        todo = g[g.status == "to come"]
        if len(todo):
            t.loc[todo.index[0], "status"] = "next"
    return t[cols + [c for c in t.columns if c not in cols]]


def summary(tracked: pd.DataFrame, team: str) -> dict:
    g = tracked[tracked.team == team]
    nx = g[g.status == "next"]
    return dict(played=int((g.status == "played").sum()), total=len(g),
                to_come=int(g.status.isin(["to come", "next"]).sum()), missing=int((g.status == "no scorecard").sum()),
                next=nx.iloc[0] if len(nx) else None,
                record={o: int((g.outcome == o).sum()) for o in ("W", "L", "D", "T", "NR")})


def series_groups(tracked: pd.DataFrame, team: str) -> list[dict]:
    """One entry per series in the schedule: its rows, score, and whether it's
    to come, under way or done."""
    out = []
    g = tracked[(tracked.team == team) & (tracked.kind == "match")]
    for (series, opp, fmt), x in g.groupby(["series", "opponent", "format"], sort=False):
        x = x.sort_values("no")
        w, lo = int((x.outcome == "W").sum()), int((x.outcome == "L").sum())
        d = int((x.outcome == "D").sum())
        played = int((x.status == "played").sum())
        left = int(x.status.isin(["to come", "next"]).sum())  # overdue ones with no scorecard aren't still to play
        state = ("under way" if played else "to come") if left else ("done" if played else "missed")
        out.append(dict(series=series, opponent=opp, format=fmt, rows=x, won=w, lost=lo, drawn=d, played=played,
                        total=len(x), left=left, state=state, start=x.anchor.min(), venue=x.venue.iloc[0]))
    return sorted(out, key=lambda s: s["start"])


# --------------------------------------------------------------------------- #
# 154 · home and away from your schedule
# --------------------------------------------------------------------------- #


def with_venues(career, tracked: pd.DataFrame):
    """A copy of the career where every match in your schedule has the home side
    your schedule gives (the scorecards don't name the ground).  Matches not in
    your schedule are untouched.  Returns the same career when nothing changes."""
    if tracked is None or tracked.empty:
        return career
    # series only: a tournament row's venue (older schedules saved "neutral") never overrides its scorecards
    played = tracked[(tracked.match_id != "") & tracked.match_id.notna() & tracked.venue.isin(["home", "away", "neutral"])
                     & (tracked.kind == "match")]
    if played.empty:
        return career
    m = career.matches.copy()
    pos = {mid: i for i, mid in zip(m.index, m.match_id)}
    changed = False
    for r in played.itertuples():
        i = pos.get(r.match_id)
        if i is None:
            continue
        home, away, team = m.at[i, "home"], m.at[i, "away"], r.team
        if r.venue == "neutral":
            if not m.at[i, "neutral"]:
                m.at[i, "neutral"] = True
                changed = True
            continue
        if m.at[i, "neutral"]:
            m.at[i, "neutral"] = False
            changed = True
        if (r.venue == "home" and away == team) or (r.venue == "away" and home == team):
            m.at[i, "home"], m.at[i, "away"] = away, home
            changed = True
    if not changed:
        return career
    c2 = copy.copy(career)
    c2.matches = m
    inn = career.innings.copy()
    hm = m.set_index("match_id")
    inn["home"] = [(t == hm.home.get(mid)) and not bool(hm.neutral.get(mid, False)) for mid, t in zip(inn.match_id, inn.team)]
    c2.innings = inn
    c2._venue_base = career
    return c2


# --------------------------------------------------------------------------- #
# 144 / 145 / 146 / 148 · next match, series preview, live series situation
# --------------------------------------------------------------------------- #


def format_ids(career, team: str, fmt: str):
    """The matches a prediction for this team and format should be based on: the
    international section for Tests / ODIs / T20Is, otherwise the team's section
    in that format (e.g. the IPL)."""
    m = career.matches
    x = m[(m.format == fmt) & ((m.home == team) | (m.away == team))]
    if x.empty:
        x = m[m.format == fmt]
    if x.empty:
        return m.iloc[0:0].match_id
    sec = x.section.mode().iloc[0]
    return m[m.section == sec].match_id


def scorelines(p_win: float, p_draw: float, n: int, start: tuple[int, int] = (0, 0)) -> dict:
    """Exact chance of every final series score (wins, defeats) after n more games."""
    p_lose = max(0.0, 1 - p_win - p_draw)
    out: dict[tuple[int, int], float] = {}
    for combo in product("WDL", repeat=max(n, 0)):
        pr = 1.0
        a, b = start
        for c in combo:
            pr *= {"W": p_win, "D": p_draw, "L": p_lose}[c]
            a += c == "W"
            b += c == "L"
        out[(a, b)] = out.get((a, b), 0.0) + pr
    return {k: v * 100 for k, v in sorted(out.items(), key=lambda kv: -kv[1]) if v > 1e-9}


def series_outlook(career, team: str, s: dict) -> dict:
    """Chances for a series in the schedule, from now: win / level / lose, the
    likeliest scores, and what's needed ("win 1 of the last 2")."""
    from . import winprob as WP
    ids = format_ids(career, team, s["format"])
    venue = s["venue"] if s["venue"] in ("home", "away") else "neutral"
    pr = WP.predict(career, ids, team, s["opponent"], venue)
    left = s.get("left", s["total"] - s["played"])
    pw, pd_ = pr["win"] / 100, pr["draw"] / 100
    odds = WP.series_odds(pw, pd_, s["won"], s["lost"], left)
    lines = scorelines(pw, pd_, left, (s["won"], s["lost"]))
    a, b = s["won"], s["lost"]
    if left == 0:
        need = ""
    elif a > b + left:
        need = "the series is already won"
    elif b > a + left:
        need = "the series can't be won now"
    else:
        k = next((k for k in range(left + 1) if a + k > b + (left - k)), None)
        k_draw = next((k for k in range(left + 1) if a + k >= b + (left - k)), None)
        if k is not None:
            need = ("win the last match to take the series" if left == 1 and k == 1 else
                    f"win {k} of the last {left} to take the series" if k < left else
                    f"win all {left} left to take the series" if left > 1 else "")
            if k == 0:
                need = "the series is already won"
        else:
            need = f"win {k_draw} of the last {left} to make sure of at least a share"
        if a + left > b and a <= b and k_draw is not None and k_draw < (k if k is not None else 99):
            need += f" ({_n_word(k_draw)} {'win' if k_draw == 1 else 'wins'} at least shares it)" if k_draw else ""
    return dict(predict=pr, left=left, odds=odds, scorelines=lines, need=need)


def _n_word(n: int) -> str:
    return {0: "no", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}.get(n, str(n))


def key_battle(career, team: str, opp: str, fmt: str) -> list[str]:
    """Who has got whom out most in this format (between the current squads)."""
    from . import preview as PV
    ids = format_ids(career, team, fmt)
    try:
        mu = PV.matchups(career, ids, team, opp, everywhere=False)
        if all(mu[k].empty for k in mu):
            mu = PV.matchups(career, ids, team, opp, everywhere=True)
    except Exception:  # noqa: BLE001 - no meetings yet
        return []
    out = []
    for label, side in (("their_bowlers", opp), ("our_bowlers", team)):
        d = mu.get(label)
        if d is not None and len(d) and d.dismissals.iloc[0] >= 2:
            r = d.iloc[0]
            out.append(f"{r.bowler} ({side}) has got {r.player} out {int(r.dismissals)} times")
    return out


def form_and_h2h(career, team: str, opp: str, fmt: str) -> dict:
    from . import teamplay as TP
    ids = format_ids(career, team, fmt)
    from .records import by_played
    g = by_played(career, TP.games(career, ids))
    return dict(form={t: list(g[g.team == t].outcome.tail(5)) for t in (team, opp)},
                h2h=TP.record(g[(g.team == team) & (g.opponent == opp)]))


def players_to_watch(career, team: str, fmt: str, last: int = 10) -> dict:
    """The side's leading run-scorers and wicket-takers in their last `last` matches in this format."""
    m = career.matches
    from .records import by_played
    mine = by_played(career, m[(m.format == fmt) & ((m.home == team) | (m.away == team))].sort_values("date")).tail(last).match_id
    b = career.batting[career.batting.match_id.isin(mine) & (career.batting.team == team) & career.batting.did_bat]
    w = career.bowling[career.bowling.match_id.isin(mine) & (career.bowling.team == team)]
    return dict(bat=b.groupby("player").runs.sum().sort_values(ascending=False).head(2),
                bowl=w.groupby("player").wickets.sum().sort_values(ascending=False).head(2), matches=len(mine))


# --------------------------------------------------------------------------- #
# 149 · the World Test Championship race with your remaining Tests
# --------------------------------------------------------------------------- #


def wtc_race(career, tracked: pd.DataFrame, team: str) -> dict | None:
    """The table now, your Tests still to come in this cycle, the most you can
    reach, what you need to finish in the top two (the others' remaining Tests
    aren't in your schedule, so their percentages stay as they are now), and the
    chance of doing it, Test by Test from the ratings."""
    from . import seasonal as SN
    from . import winprob as WP
    if team not in SN.WTC_TEAMS:
        return None
    w = SN.wtc_matches(career)
    if w.empty:
        return None
    cycle = int(w.cycle.max())
    table = SN.wtc_table(career, cycle)
    todo = tracked[(tracked.team == team) & (tracked.format == "Test") & tracked.status.isin(["to come", "next"])
                   & tracked.opponent.isin(SN.WTC_TEAMS)]
    end = pd.Timestamp(year=cycle + 2, month=6, day=1)
    todo = todo[todo.anchor < end]
    me = table[table.team == team]
    pts, n = (int(me.points.iloc[0]), int(me.played.iloc[0])) if len(me) else (0, 0)
    r_ = len(todo)
    others = table[table.team != team].pct.sort_values(ascending=False)
    bar = float(others.iloc[1]) if len(others) >= 2 else 0.0
    ids = format_ids(career, team, "Test")
    probs = []
    for o, v in zip(todo.opponent, todo.venue):
        p = WP.predict(career, ids, team, o, v if v in ("home", "away") else "neutral")
        probs.append((p["win"] / 100, p["draw"] / 100, p["lose"] / 100))
    total = 12 * (n + r_)
    best = (pts + 12 * r_) / total * 100 if total else np.nan
    need = next((k for k in range(r_ + 1) if total and (pts + 12 * k) / total * 100 > bar), None)
    # chance of finishing above the bar: every result of the remaining Tests (capped at 12 for speed)
    chance, expected = np.nan, np.nan
    if r_ and total and r_ <= 12:
        chance = 0.0
        for combo in product(range(3), repeat=r_):
            pr, p_ = 1.0, pts
            for (pw, pdw, pl), c in zip(probs, combo):
                pr *= (pw, pdw, pl)[c]
                p_ += (12, 4, 0)[c]
            if p_ / total * 100 > bar:
                chance += pr
        chance *= 100
        expected = (pts + sum(12 * pw + 4 * pdw for pw, pdw, _ in probs)) / total * 100
    elif not r_ and total:
        chance = 100.0 if (pts / total * 100 > bar) else 0.0
        expected = pts / total * 100
    return dict(cycle=cycle, table=table, todo=todo, points=pts, played=n, remaining=r_, best=best, bar=bar,
                bar_team=table[table.team != team].sort_values("pct", ascending=False).team.iloc[1]
                if len(others) >= 2 else "", need=need, chance=chance, expected=expected)


# --------------------------------------------------------------------------- #
# 150 · milestone countdown by fixture
# --------------------------------------------------------------------------- #


def milestone_countdown(career, tracked: pd.DataFrame, team: str) -> pd.DataFrame:
    """For your players: the next round number in each format they play, how far
    away it is, their rate per match there, and the fixture in your schedule they'd
    reach it in at that rate (if it's within the matches left)."""
    from .players import STEPS
    cols = ["player", "format", "what", "now", "next", "needed", "per_match", "games_left", "when", "within"]
    todo = tracked[(tracked.team == team) & tracked.status.isin(["to come", "next"])]
    rows = []
    m = career.matches
    for fmt, fx in todo.groupby("format"):
        fx = fx.sort_values("anchor")
        from .records import by_played
        mine = by_played(career, m[(m.format == fmt) & ((m.home == team) | (m.away == team))].sort_values("date"))
        if mine.empty:
            continue
        recent = set(mine.tail(5).match_id)  # the current squad: played in the last 5 matches
        b = career.batting[career.batting.match_id.isin(mine.match_id) & (career.batting.team == team)]
        squad = set(b[b.match_id.isin(recent)].player)
        w = career.bowling[career.bowling.match_id.isin(mine.match_id) & (career.bowling.team == team)]
        games_p = b.groupby("player").match_id.nunique()
        for what, d, col in (("runs", b[b.did_bat], "runs"), ("wickets", w, "wickets")):
            tot = d.groupby("player")[col].sum()
            for p in squad:
                now = int(tot.get(p, 0))
                nxt = next((s for s in STEPS[what] if s > now), None)
                gp = int(games_p.get(p, 0))
                if nxt is None or gp < 3 or now < min(STEPS[what]) * 0.4:
                    continue
                rate = now / gp
                if rate <= 0:
                    continue
                need = nxt - now
                k = math.ceil(need / rate)
                within = k <= len(fx)
                when = ""
                if within:
                    f = fx.iloc[k - 1]
                    when = f"{f['series']}, match {int(f['no'])}" if f["kind"] == "match" else f"{f['series']}"
                rows.append(dict(player=p, format=fmt, what=what, now=now, next=nxt, needed=need, per_match=rate,
                                 games_left=len(fx), when=when, within=within, games_needed=k))
    d = pd.DataFrame(rows, columns=cols + ["games_needed"])
    return d.sort_values(["within", "games_needed", "needed"], ascending=[False, True, True]).reset_index(drop=True)


# --------------------------------------------------------------------------- #
# 151 · season goals
# --------------------------------------------------------------------------- #

GOAL_KINDS = {"series": "Win a series", "wtc": "Reach the World Test Championship final",
              "player": "A player reaches a number", "wins": "Win a number of matches"}


def goal_progress(career, tracked: pd.DataFrame, goal: dict) -> dict:
    """(done 0-1, text, status) for one goal."""
    kind = goal.get("kind")
    team = goal.get("team", "")
    if kind == "series":
        gs = [s for s in series_groups(tracked, team) if s["series"] == goal.get("series")]
        if not gs:
            return dict(done=0.0, text="That series isn't in the schedule any more.", status="unknown")
        s = gs[0]
        if s["state"] == "done":
            ok = s["won"] > s["lost"]
            return dict(done=1.0 if ok else 0.0, text=f"{s['won']}–{s['lost']}" + (" — won it" if ok else " — not won"),
                        status="achieved" if ok else "missed")
        if s["state"] == "to come":
            return dict(done=0.0, text=f"Starts {s['start']:%b %Y}" if s["start"].year < 2100 else "To come",
                        status="to come")
        if s["state"] == "missed":
            return dict(done=0.0, text="Its time has gone with no scorecards: check its month and opponent.",
                        status="unknown")
        o = series_outlook(career, team, s)
        return dict(done=s["won"] / (s["total"] // 2 + 1), text=f"{s['won']}–{s['lost']}, {o['need']} "
                    f"(chance {o['odds']['A']:.0f}%)", status="under way")
    if kind == "wtc":
        race = wtc_race(career, tracked, team)
        if race is None:
            return dict(done=0.0, text="Not a World Test Championship side.", status="unknown")
        t = race["table"].reset_index(drop=True)
        pos = int(t.index[t.team == team][0]) + 1 if team in set(t.team) else None
        ch = race["chance"]
        now = f"{ordinal(pos)} now" if pos else "not in the table yet"
        need = (f"; needs {race['need']} win{'s' if race['need'] != 1 else ''} from {race['remaining']} Tests left"
                if race["remaining"] and race["need"] is not None else "")
        if not np.isfinite(ch):
            return dict(done=0.0, text=now + need, status="unknown")
        return dict(done=ch / 100, text=f"{now}; chance of finishing in the top two: {ch:.0f}%{need}",
                    status="achieved" if not race["remaining"] and ch >= 100 else "on course" if ch >= 50 else "at risk")
    if kind == "player":
        p, fmt, what, target = goal.get("player"), goal.get("format"), goal.get("what", "runs"), int(goal.get("target") or 0)
        m = career.matches
        ids = m[m.format == fmt].match_id
        if goal.get("year"):
            ids = m[(m.format == fmt) & (m.date.dt.year == int(goal["year"]))].match_id
        if what == "runs":
            now = int(career.batting[career.batting.match_id.isin(ids) & (career.batting.player == p)].runs.sum())
        else:
            now = int(career.bowling[career.bowling.match_id.isin(ids) & (career.bowling.player == p)].wickets.sum())
        done = min(now / target, 1.0) if target else 0.0
        return dict(done=done, text=f"{now:,} of {target:,} {what}" + (f" in {goal['year']}" if goal.get("year") else ""),
                    status="achieved" if done >= 1 else "under way")
    if kind == "wins":
        fmt, target, year = goal.get("format"), int(goal.get("target") or 0), goal.get("year")
        m = career.matches
        g = m[(m.format == fmt) & ((m.home == team) | (m.away == team))]
        if year:
            g = g[g.date.dt.year == int(year)]
        won = int(sum(_outcome(r, team) == "W" for r in g.itertuples()))
        done = min(won / target, 1.0) if target else 0.0
        return dict(done=done, text=f"{won} of {target} {fmt} wins" + (f" in {year}" if year else ""),
                    status="achieved" if done >= 1 else "under way")
    return dict(done=0.0, text="", status="unknown")


def goal_label(goal: dict) -> str:
    k = goal.get("kind")
    if k == "series":
        return f"{goal.get('team')}: win the series {goal.get('series')}"
    if k == "wtc":
        return f"{goal.get('team')}: reach the World Test Championship final"
    if k == "player":
        return (f"{goal.get('player')}: {int(goal.get('target') or 0):,} {goal.get('format')} {goal.get('what')}"
                + (f" in {goal['year']}" if goal.get("year") else " in their career"))
    if k == "wins":
        return f"{goal.get('team')}: {goal.get('target')} {goal.get('format')} wins" + (f" in {goal['year']}" if goal.get("year") else "")
    return "Goal"


# --------------------------------------------------------------------------- #
# 152 · series report
# --------------------------------------------------------------------------- #


def series_report(career, s: dict, team: str) -> dict:
    """For a finished series: the result, Player of the Series, leading players,
    the best innings and figures, how the ratings moved, and records and
    milestones set during it."""
    from . import players as PL
    from . import records as RC
    from .rankings import team_elo
    mids = [x for x in s["rows"].match_id if x]
    m = career.matches[career.matches.match_id.isin(mids)].sort_values("date")
    if m.empty:
        return {}
    b = career.batting[career.batting.match_id.isin(mids) & career.batting.did_bat]
    w = career.bowling[career.bowling.match_id.isin(mids) & (career.bowling.balls > 0)]
    pos = PL.player_of_series(career, mids)
    top_b = b.groupby(["player", "team"]).runs.sum().sort_values(ascending=False).head(3)
    top_w = w.groupby(["player", "team"]).wickets.sum().sort_values(ascending=False).head(3)
    hs = b.sort_values(["runs", "balls"], ascending=[False, True]).head(1)
    bb = w.assign(k=w.wickets * 1000 - w.runs).sort_values("k", ascending=False).head(1)
    sec = m.section.iloc[0]
    _, hist = team_elo(career, sec)
    elo = {}
    for t in (team, s["opponent"]):
        h = hist[hist.match_id.isin(mids) & (hist.team == t)].sort_values("date")
        if len(h):
            elo[t] = (float(h.before.iloc[0]), float(h.after.iloc[-1]))
    recs = [msg for _, msg in RC.new_record_lines(career, list(m.source))]
    sec_ids = career.matches[career.matches.section == sec].match_id
    miles = [x for mid in m.match_id for x in PL.milestones_reached(career, sec_ids, mid)]
    a, l_ = s["won"], s["lost"]
    result = (f"{team} won the series {a}–{l_}" if a > l_ else f"{s['opponent']} won the series {l_}–{a}" if l_ > a
              else f"Series drawn {a}–{l_}")
    return dict(result=result + (f" ({s['drawn']} drawn)" if s["drawn"] else ""), pos=pos.iloc[0] if len(pos) else None,
                top_bat=top_b, top_bowl=top_w, best_bat=hs.iloc[0] if len(hs) else None,
                best_bowl=bb.iloc[0] if len(bb) else None, elo=elo, records=recs, milestones=miles,
                matches=m, first=m.date.min(), last=m.date.max())


# --------------------------------------------------------------------------- #
# 143 · year calendar
# --------------------------------------------------------------------------- #


def calendar_entries(career, tracked: pd.DataFrame, team: str, year: int) -> tuple[dict, dict]:
    """({date: [entries]} for a year: every match the team played, plus dated
    fixtures to come; {month: [entries]} for fixtures known only by month)."""
    m = career.matches
    days: dict = {}
    g = m[((m.home == team) | (m.away == team)) & (m.date.dt.year == year)]
    for r in g.itertuples():
        opp = r.away if r.home == team else r.home
        venue = "neutral" if r.neutral else ("home" if r.home == team else "away")
        days.setdefault(r.date.normalize(), []).append(dict(kind="played", outcome=_outcome(r, team), opponent=opp,
                                                            format=r.format, venue=venue, match_id=r.match_id,
                                                            result=r.result))
    months: dict = {}
    todo = tracked[(tracked.team == team) & tracked.status.isin(["to come", "next"])]
    for _, r in todo.iterrows():
        label = r["opponent"] or r["series"].split(" · ")[0]
        e = dict(kind="to come", outcome="", opponent=label, format=r["format"], venue=r["venue"], match_id="",
                 result="", series=r["series"], no=int(r["no"] or 0))
        if r["date"] and pd.Timestamp(r["date"]).year == year:
            days.setdefault(pd.Timestamp(r["date"]).normalize(), []).append(e)
        elif r["month"] and int(r["month"][:4]) == year:
            months.setdefault(int(r["month"][5:7]), []).append(e)
    return days, months
