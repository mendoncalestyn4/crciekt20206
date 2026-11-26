"""Names that may be one player (your answers of 26 November). Data check looks widely: the same initial and surname,
a missing or extra initial, and on the same team a surname spelt nearly the same (Harmer / Harper) or differing only in
its vowels (Smith / Smyth, Mohammed / Muhammad); and a move between teams (one name's games all before the other's) with
the very same surname, never between two national sides. Two names that played in the same match are never one player.

Every pair says why it was listed. Only pairs beyond doubt are joined by themselves (`sure`): the same team, never in
the same match, one name's last game for the team followed straight away by the other's first (at most `GAP` of the
team's games of that format between), and neither name has any other candidate. Each automatic join is listed and can
be undone (kept apart for good); anything less sure waits for your click.

Everything here works on an appearances table: one row per player per match (player, team, match_id, date, format,
runs, innings, wickets)."""

from __future__ import annotations

import re
import unicodedata
from itertools import combinations

import pandas as pd

from .fixtures import NATIONS

GAP = 2                         # at most this many of the team's games (of a format) between the old name and the new
JOIN_COLUMNS = ["other", "keep", "team", "why", "other_matches", "keep_matches", "other_runs", "keep_runs",
                "other_wickets", "keep_wickets", "other_innings", "keep_innings", "sure"]
APPEAR_COLUMNS = ["player", "team", "match_id", "date", "format", "runs", "innings", "wickets"]


# --------------------------------------------------------------------------- reading a printed name
def _plain(s: str) -> str:
    """Lower case, accents and punctuation gone: "O'Neill" and "ONeill", "Müller" and "Muller" read the same."""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z]", "", s.lower())


SUFFIXES = {"jr", "jnr", "junior", "sr", "snr", "senior", "ii", "iii", "iv"}


def suffix(name: str) -> str:
    """"Jr.", "Snr", "II"… at the end of a name ("" when none): father and son are two players."""
    words = name.split()
    return _plain(words[-1]) if len(words) > 1 and _plain(words[-1]) in SUFFIXES else ""


def parts(name: str) -> tuple[str, str, str] | None:
    """(initials as printed, first initial, surname) of a printed name; None for a name that can't be one player's
    own (a name the site itself made: "R Patel (Surrey)", "D Jansen (2)"). A hyphenated surname is one surname; a
    "Jr." or "Snr" at the end isn't part of it (see `suffix`)."""
    if not name or "(" in name or " or " in name:
        return None
    words = name.split()
    if suffix(name):
        words = words[:-1]
    if not words:
        return None
    # surnames of more than one word ("de Kock", "van der Merwe"): the words from the first lower-case one on
    low = next((i for i, w in enumerate(words) if i > 0 and w[:1].islower()), None)
    cut = low if low is not None else len(words) - 1
    first, sur = words[:cut], words[cut:]
    sur_key = _plain("".join(sur))
    if not sur_key:
        return None
    given = " ".join(first)
    return given, (_plain(given)[:1].upper() if given else ""), sur_key


def _one_apart(a: str, b: str) -> bool:
    """One letter added, taken away, changed, or two neighbours swapped."""
    if a == b:
        return False
    la, lb = len(a), len(b)
    if abs(la - lb) > 1:
        return False
    if la == lb:
        diff = [i for i in range(la) if a[i] != b[i]]
        return len(diff) == 1 or (len(diff) == 2 and diff[1] == diff[0] + 1 and a[diff[0]] == b[diff[1]]
                                  and a[diff[1]] == b[diff[0]])
    if la > lb:
        a, b = b, a
    for i in range(len(b)):
        if b[:i] + b[i + 1:] == a:
            return True
    return False


def _vowels_only(a: str, b: str) -> bool:
    """The same length, the same first letter, and different only where both have a vowel (y counts as one):
    "Mohammed" / "Muhammad", "Smith" / "Smyth", "Ahmad" / "Ahmed"."""
    v = set("aeiouy")
    return (len(a) == len(b) and len(a) >= 5 and a[0] == b[0] and a != b
            and all(x == y or (x in v and y in v) for x, y in zip(a, b)))


def why(a: str, b: str) -> str:
    """Why two printed names look like one player ("" when they don't)."""
    pa, pb = parts(a), parts(b)
    if not pa or not pb or a == b or suffix(a) != suffix(b):
        return ""
    (ga, ia, sa), (gb, ib, sb) = pa, pb
    if sa == sb:
        if not ia or not ib:
            return "the same surname, one name without an initial"
        if ia != ib:
            return ""
        if _plain(ga) == _plain(gb):
            return "the same name, printed a little differently"
        if _plain(ga).startswith(_plain(gb)) or _plain(gb).startswith(_plain(ga)):
            return "the same initial and surname, one with an extra initial or the first name in full"
        return "the same initial and surname"
    if ia and ia == ib and min(len(sa), len(sb)) >= 4:
        if _one_apart(sa, sb) and min(len(sa), len(sb)) >= 5:
            return f"surnames spelt nearly the same ({a.split()[-1]} / {b.split()[-1]})"
        if _vowels_only(sa, sb):
            return f"surnames that sound the same ({a.split()[-1]} / {b.split()[-1]})"
    return ""


# --------------------------------------------------------------------------- the pairs
def _candidates(names: list[str]) -> list[tuple[str, str, str]]:
    """Every pair of names that look alike, with why, found without comparing every name with every other: names are
    grouped by surname, by first initial and surname with the vowels hidden, and by first initial and surname with one
    letter dropped."""
    groups: dict[tuple, set] = {}
    for n in names:
        p = parts(n)
        if not p:
            continue
        _, ini, sur = p
        groups.setdefault(("s", sur), set()).add(n)
        if ini:
            groups.setdefault(("v", ini, len(sur), re.sub("[aeiouy]", "*", sur)), set()).add(n)
            for i in range(len(sur)):
                groups.setdefault(("d", ini, sur[:i] + sur[i + 1:]), set()).add(n)
            groups.setdefault(("d", ini, sur), set()).add(n)
    out, done = [], set()
    for g in groups.values():
        if len(g) < 2:
            continue
        for a, b in combinations(sorted(g), 2):
            if (a, b) in done:
                continue
            done.add((a, b))
            w = why(a, b)
            if w:
                out.append((a, b, w))
    return out


def pairs(appear: pd.DataFrame, keep_apart: list | None = None) -> pd.DataFrame:
    """Every pair of names that may be one player (JOIN_COLUMNS), each with why it was listed and whether it is beyond
    doubt (`sure`). Never two names in the same match; a pair at different teams only when one name's games all come
    before the other's (a move); pairs you chose to keep apart are left out."""
    if appear.empty:
        return _typed(pd.DataFrame(columns=JOIN_COLUMNS))
    apart = {frozenset(x) for x in (keep_apart or [])}
    by = appear.groupby("player")
    matches_of = by.match_id.apply(set)
    teams_of = by.team.apply(set)
    first, last = by.date.min(), by.date.max()
    found = []
    for a, b, w in _candidates(list(matches_of.index)):
        if frozenset((a, b)) in apart or matches_of[a] & matches_of[b]:
            continue
        shared = teams_of[a] & teams_of[b]
        apart_in_time = last[a] < first[b] or last[b] < first[a]
        if not shared and (not apart_in_time or (teams_of[a] | teams_of[b]) <= NATIONS or w.startswith("surnames")):
            continue        # a move: only with the very same surname, and never between two national sides
        found.append((a, b, w, shared, apart_in_time))
    # how many candidates each name has (a name with two possible partners is never joined by itself)
    count: dict[str, int] = {}
    for a, b, *_ in found:
        count[a] = count.get(a, 0) + 1
        count[b] = count.get(b, 0) + 1
    tot = appear.groupby("player").agg(matches=("match_id", "nunique"), runs=("runs", "sum"), wickets=("wickets", "sum"),
                                       innings=("innings", "sum"))
    rows = []
    for a, b, w, shared, apart_in_time in found:
        ma, mb = int(tot.matches[a]), int(tot.matches[b])
        # the name used more often stays; with the same number of games, the newer name
        keep, other = (a, b) if (ma, first[a]) >= (mb, first[b]) else (b, a)
        if not shared:
            w += "; moved team (one name's games all before the other's)"
        sure = bool(shared and apart_in_time and count[a] == 1 and count[b] == 1 and _straight_after(appear, a, b, shared))
        rows.append(dict(other=other, keep=keep, team=", ".join(sorted(shared)) if shared else
                         f"{', '.join(sorted(teams_of[other]))} → {', '.join(sorted(teams_of[keep]))}", why=w,
                         other_matches=int(tot.matches[other]), keep_matches=int(tot.matches[keep]),
                         other_runs=int(tot.runs[other]), keep_runs=int(tot.runs[keep]),
                         other_wickets=int(tot.wickets[other]), keep_wickets=int(tot.wickets[keep]),
                         other_innings=int(tot.innings[other]), keep_innings=int(tot.innings[keep]), sure=sure))
    out = _typed(pd.DataFrame(rows, columns=JOIN_COLUMNS))
    return out.sort_values(["sure", "keep_matches"], ascending=[False, False]).reset_index(drop=True)


def _typed(df: pd.DataFrame) -> pd.DataFrame:
    """The same column types with no rows as with some: `sure` yes/no, the counts whole numbers (with no rows, every
    column would be text, and picking rows by `sure` would pick columns instead)."""
    counts = [c for c in JOIN_COLUMNS if c.endswith(("_matches", "_runs", "_wickets", "_innings"))]
    return df.astype({"sure": bool, **{c: "int64" for c in counts}})


def _straight_after(appear: pd.DataFrame, a: str, b: str, shared: set) -> bool:
    """One name's last game for a team they share is followed straight away by the other's first, in some format both
    played for it: at most GAP of the team's games of that format between."""
    for team in shared:
        here = appear[appear.team == team]
        for fmt in set(here[here.player == a].format) & set(here[here.player == b].format):
            games = here[here.format == fmt].drop_duplicates("match_id").sort_values(["date", "match_id"])
            order = {mid: i for i, mid in enumerate(games.match_id)}
            ia = sorted(order[x] for x in here[(here.player == a) & (here.format == fmt)].match_id)
            ib = sorted(order[x] for x in here[(here.player == b) & (here.format == fmt)].match_id)
            old, new = (ia, ib) if ia[-1] < ib[0] else (ib, ia) if ib[-1] < ia[0] else (None, None)
            if old is not None and new[0] - old[-1] - 1 <= GAP:
                return True
    return False


def from_tables(batting: pd.DataFrame, bowling: pd.DataFrame, matches: pd.DataFrame) -> pd.DataFrame:
    """The appearances table from a career's own tables."""
    bat = batting.assign(innings=batting.did_bat.astype(bool).astype(int))[["player", "team", "match_id", "runs", "innings"]]
    bowl = bowling[["player", "team", "match_id", "wickets"]]
    a = pd.concat([bat.assign(wickets=0), bowl.assign(runs=0, innings=0)], ignore_index=True)
    a = a.groupby(["player", "team", "match_id"], as_index=False)[["runs", "innings", "wickets"]].sum()
    return a.merge(matches[["match_id", "date", "format"]], on="match_id")[APPEAR_COLUMNS]
