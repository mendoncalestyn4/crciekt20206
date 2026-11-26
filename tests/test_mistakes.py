"""Deliberate mistakes (stage 5, kept for good: your "add everything" of 26 November). Every test scorecard is read again
with one mistake put in on purpose, of each kind below, and the site's own checks must notice every one: either a sum
that no longer adds up (listed on the match), or the card put right by the site's fair guess (noted on the match), or
the result's margin flagged. A mistake that slips through silently fails the test.

The kinds: a batter's runs, a batter's fours, a bowler's runs, a bowler's wickets, a bowler's overs, the total, the
fall of wickets out of order, the result's margin, and a dismissal the site doesn't know."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from ccstats.parser import parse_scorecard, validate_match

HERE = Path(__file__).parent
FILES = sorted({f.name: f for d in ("fixtures", "fixtures_declare", "fixtures_rain", "fixtures_super")
                for f in (HERE / d).glob("*.txt")}.values())

BAT = re.compile(r"^(?P<head>\S.{41})(?P<r>\d+)(?P<gap>\s+)(?P<b>\d+)(?P<g2>\s+)(?P<f>[\d-]+)(?P<rest>\s+[\d-]+\s*)$")
BOWL = re.compile(r"^(?P<name>\S.{15})(?P<o>\s*[\d.]+)(?P<g1>\s+)(?P<m>[\d-]+)(?P<g2>\s+)(?P<r>\d+)(?P<g3>\s+)(?P<w>\d+)"
                  r"(?P<rest>\s+[\d.]+\s*)$")
TOTAL = re.compile(r"^(TOTAL:.*?)(\d+)\s*$")
FOW = re.compile(r"\b(\d+)-(\d+)\b")
MARGIN = re.compile(r"won by (\d+) (runs?|wickets?)")


def _first(lines, pat):
    for i, ln in enumerate(lines):
        m = pat.match(ln)
        if m:
            return i, m
    return None, None


def _put(m, key, value):
    """The line with one field changed, kept the same width where it can be."""
    s, e = m.span(key)
    old = m.string[s:e]
    new = str(value)
    pad = m.string[e:e + max(0, len(new) - len(old))]
    if len(new) > len(old) and pad.strip() == "" and len(pad) == len(new) - len(old):
        return m.string[:s] + new + m.string[e + len(pad):]
    return m.string[:s] + new.ljust(len(old)) + m.string[e:]


def batter_runs(lines):
    i, m = _first(lines, BAT)
    return None if i is None else (i, _put(m, "r", int(m["r"]) + 7))


def batter_fours(lines):
    i, m = _first(lines, BAT)
    return None if i is None else (i, _put(m, "f", 60))


def bowler_runs(lines):
    i, m = _first(lines, BOWL)
    return None if i is None or int(m["r"]) < 6 else (i, _put(m, "r", int(m["r"]) - 5))


def bowler_wickets(lines):
    i, m = _first(lines, BOWL)
    return None if i is None else (i, _put(m, "w", int(m["w"]) + 1))


def bowler_overs(lines):
    i, m = _first(lines, BOWL)
    if i is None:
        return None
    o = m["o"].strip()
    whole, _, part = o.partition(".")
    return i, _put(m, "o", " " * (len(m["o"]) - len(o)) + str(int(whole) + 1) + (f".{part}" if part else ""))


def total(lines):
    i, m = _first(lines, TOTAL)
    return None if i is None else (i, f"{m.group(1)}{int(m.group(2)) + 3}")


def fow_order(lines):
    for i, ln in enumerate(lines):
        if ln.startswith("Fall of Wickets") and i + 1 < len(lines):
            pairs = FOW.findall(lines[i + 1])
            if len(pairs) >= 2 and pairs[0][1] != pairs[1][1]:
                (w1, s1), (w2, s2) = pairs[0], pairs[1]
                new = lines[i + 1].replace(f"{w1}-{s1}", "@A@", 1).replace(f"{w2}-{s2}", f"{w2}-{s1}", 1)
                return i + 1, new.replace("@A@", f"{w1}-{s2}", 1)
    return None


def margin(lines):
    for i, ln in enumerate(lines):
        m = MARGIN.search(ln)
        if m and m.group(2).startswith("run"):
            return i, ln[:m.start(1)] + str(int(m.group(1)) + 11) + ln[m.end(1):]
    return None


def dismissal(lines):
    i, m = _first(lines, BAT)
    if i is None:
        return None
    ln = lines[i]
    return i, ln[:16] + "zapped Smith".ljust(26) + ln[42:]


KINDS = [batter_runs, batter_fours, bowler_runs, bowler_wickets, bowler_overs, total, fow_order, margin, dismissal]


def caught(m, clean) -> bool:
    return bool(validate_match(m) or m.guesses or (m.margin_note and m.margin_note != clean.margin_note)
                or m.corrections != clean.corrections)


@pytest.mark.parametrize("kind", KINDS, ids=[k.__name__ for k in KINDS])
def test_every_deliberate_mistake_is_caught(kind):
    tried, missed = 0, []
    for f in FILES:
        text = f.read_text(encoding="utf-8", errors="replace")
        clean = parse_scorecard(text, f.name)
        if validate_match(clean) or clean.guesses:
            continue                                   # (only cards that add up as they are)
        lines = text.split("\n")
        change = kind(lines)
        if change is None:
            continue
        i, new = change
        if new == lines[i]:
            continue
        lines[i] = new
        try:
            m = parse_scorecard("\n".join(lines), f.name)
        except Exception:  # noqa: BLE001 - a card the reader refuses is caught too (named on Data check)
            tried += 1
            continue
        tried += 1
        if not caught(m, clean):
            missed.append(f"{f.name}: {lines[i].strip()}")
    assert tried >= 10, f"only {tried} cards could take a {kind.__name__} mistake"
    assert not missed, f"{len(missed)} {kind.__name__} mistakes not caught: {missed[:5]}"
