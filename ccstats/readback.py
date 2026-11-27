"""Every scorecard read back (your pick of 14 November): what the site understood is written out again and compared, line
by line, with the card as the game printed it. Any difference is a misreading, even one whose sums still add up (4s and
6s swapped, a maiden read as a wicket), so each is flagged.

What's compared, innings by innings: every batting line (the name, how out, runs, balls, 4s, 6s), the extras, the total
line (runs, wickets or all out, overs or balls), every bowling line (overs or balls, maidens or dot balls, runs,
wickets) and the fall of wickets; then the result and the player of the match. The economy and the strike rate the card
prints are worked out by the game from those, so they're compared too, to their last printed figure."""

from __future__ import annotations

import re

from .parser import Match, balls_to_overs

ZERO = {"-": "0", "–": "0"}


def _words(line: str) -> list[str]:
    return [ZERO.get(w, w) for w in line.split()]


def _innings_lines(text: str) -> list[list[str]]:
    """The card's own lines, one list per innings (super overs left out), each the printed lines from the innings
    heading to its fall of wickets."""
    out: list[list[str]] = []
    cur: list[str] | None = None
    for raw in text.splitlines():
        line = raw.strip()
        # (a long team name leaves no gap before the first column: "… - 1st InningsR    B    4s  6s", as the reader knows)
        if re.search(r" - \d\w\w Innings(?:R)?\b", line):
            cur = [line]
            out.append(cur)
            continue
        if re.search(r" - Super over(?:R)?\b", line):
            cur = None
            continue
        if cur is not None and line and not set(line) <= set("-*"):
            cur.append(line)
    return out


def read_back(text: str, m: Match) -> list[str]:
    """The differences between the card as printed and the card written out again from what the site understood;
    empty when every line reads back the same."""
    diffs: list[str] = []
    printed = _innings_lines(text)
    # the site keeps innings in the order they were batted; the card lists them in team order (`listed`)
    mine = sorted(m.innings, key=lambda i: i.listed or i.number)
    if len(printed) != len(mine):
        return [f"{len(printed)} innings printed but {len(mine)} read"]
    for inn, lines in zip(mine, printed):
        where = f"{inn.team} innings {inn.team_innings}"
        body = lines[1:]
        # batting: each printed batting line, in order, against what was read (the lines before "Extras")
        stop = next((k for k, l in enumerate(body) if l.startswith("Extras")), len(body))
        bat_lines = body[:stop]
        if len(bat_lines) != len(inn.batting):
            diffs.append(f"{where}: {len(bat_lines)} batting lines printed but {len(inn.batting)} read")
        for line, b in zip(bat_lines, inn.batting):
            want = _words(line)
            got = _words(f"{b.player} {b.dismissal}" + (f" {b.runs} {b.balls} {b.fours} {b.sixes}" if b.did_bat else ""))
            if want != got and not _same_row(want, got, b):
                diffs.append(f"{where}: \"{line}\" read back as \"{' '.join(got)}\"")
        rest = body[stop:]
        ex = next((l for l in rest if l.startswith("Extras")), "")
        if ex and _num(ex.split()[-1]) != inn.extras:
            diffs.append(f"{where}: extras printed {ex.split()[-1]} but read {inn.extras}")
        tot = next((l for l in rest if l.startswith("TOTAL")), "")
        if tot:
            nums = re.findall(r"\d+(?:\.\d)?", tot)
            if not nums or _num(nums[-1]) != inn.total:
                diffs.append(f"{where}: total printed \"{tot}\" but read {inn.total}")
            wk = re.search(r"(\d+)\s*wkts?", tot)
            read_wk = 10 if "all out" in tot.lower() and inn.wickets == 10 else inn.wickets
            if wk and int(wk.group(1)) != read_wk:
                diffs.append(f"{where}: {wk.group(1)} wickets printed but {inn.wickets} read")
            length = re.search(r"([\d.]+)\s*(overs?|balls?)", tot)
            if length:
                shown = length.group(1)
                shown = shown[:-2] if shown.endswith(".0") else shown          # "20.0" overs is "20"
                mine_len = str(inn.balls) if length.group(2).startswith("ball") else balls_to_overs(inn.balls)
                mine_len = mine_len[:-2] if mine_len.endswith(".0") else mine_len
                if shown != mine_len:
                    diffs.append(f"{where}: {length.group(0)} printed but {mine_len} read")
        # bowling: each printed figure line after the column heading, in order, against what was read
        bowl_at = next((k for k, l in enumerate(rest) if re.match(r"(O|B|Balls)\s+", l)), None)
        if bowl_at is not None:
            fow_at = next((k for k, l in enumerate(rest) if l.startswith("Fall of Wickets")), len(rest))
            bowl_lines = [l for l in rest[bowl_at + 1:fow_at] if re.search(r"\d", l)]
            if len(bowl_lines) != len(inn.bowling):
                diffs.append(f"{where}: {len(bowl_lines)} bowling lines printed but {len(inn.bowling)} read")
            for line, w in zip(bowl_lines, inn.bowling):
                want = _words(line)
                length = str(w.balls) if inn.counted_in_balls else balls_to_overs(w.balls)
                middle = w.maidens if w.maidens is not None else w.dots if w.dots is not None else 0
                got = _words(f"{w.player} {length} {middle} {w.runs} {w.wickets}")
                if want[:len(got)] != got and not _same_overs(want, got):
                    diffs.append(f"{where}: \"{line}\" read back as \"{' '.join(got)}\"")
            fow = " ".join(rest[fow_at + 1:]) if fow_at < len(rest) else ""
            pairs = [(int(a), int(b)) for a, b in re.findall(r"(\d+)-(\d+)", fow)]
            if pairs and pairs != list(inn.fow):
                diffs.append(f"{where}: fall of wickets printed {fow.strip()} but read {inn.fow}")
    res = next((l.strip() for l in text.splitlines() if l.strip() == m.result), None) if m.result else ""
    if m.result and res is None:
        diffs.append(f"the result \"{m.result}\" isn't a line of the card")
    if m.player_of_match and not re.search(rf"Man of the match:\s*{re.escape(m.player_of_match)}\s*$", text, re.M | re.I):
        diffs.append(f"the player of the match \"{m.player_of_match}\" isn't the card's")
    return diffs


def _num(t: str) -> int:
    try:
        return int(t)
    except ValueError:
        return -1


def _same_row(want: list[str], got: list[str], b) -> bool:
    """A batter who didn't bat prints only a name; a not out batter's runs may carry a "*" in some cards."""
    return [w.rstrip("*") for w in want] == [g.rstrip("*") for g in got]


def _same_overs(want: list[str], got: list[str]) -> bool:
    """"4" overs and "4.0" are the same."""
    norm = lambda xs: [x[:-2] if x.endswith(".0") else x for x in xs]   # noqa: E731
    return norm(want[:len(got)]) == norm(got)
