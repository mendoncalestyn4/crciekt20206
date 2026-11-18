"""A second, separate counter (your pick of 14 November): a small reader of its own, written apart from the site's,
reads every test scorecard straight from the text and counts every batter's runs, balls, fours, sixes and whether they
were out, and every bowler's balls, runs and wickets. The site's numbers must be the same, line for line; and every
player's average, strike rate and economy, worked out from this counter, must be the site's too."""

import re
from collections import defaultdict
from pathlib import Path

import pytest

from ccstats.loader import Career
from ccstats.stats import player_tables

HERE = Path(__file__).parent
# each scorecard once (the same rain game with a super over is in two of the test folders)
FILES = list({f.name: f for d in ("fixtures", "fixtures_declare", "fixtures_rain", "fixtures_super")
              for f in sorted((HERE / d).glob("*.txt"))}.values())
NOT_OUT = ("not out", "retired hurt", "retired ill", "absent")


def num(t: str) -> int:
    return 0 if t in ("-", "") else int(t)


def overs_balls(t: str, per_over: int = 6) -> int:
    o, _, b = t.partition(".")
    return int(o) * per_over + (int(b) if b else 0)


def count(text: str) -> dict:
    """My own reading of one card: the innings in the order printed, each with its batting rows (runs, balls, 4s, 6s,
    out) and bowling rows (balls, runs, wickets), the super over left out."""
    inns, cur, part = [], None, None
    for raw in text.splitlines():
        line = raw.rstrip()
        if re.search(r" - (\d)\w\w Innings", line):
            cur = dict(team=line.split(" - ")[0].strip(), bat=[], bowl=[], balls_count="balls" in line)
            inns.append(cur)
            part = "bat"
            continue
        if re.search(r" - Super over", line):
            cur, part = None, None
            continue
        if cur is None or not line.strip() or set(line.strip()) <= set("-*"):
            continue
        if line.startswith(("Extras", "TOTAL")):
            if line.startswith("TOTAL") and "balls" in line:
                cur["balls_count"] = True
            part = "after"
            continue
        if re.match(r"\s+(O|B|Balls)\s+", line):
            part = "bowl"
            continue
        if line.startswith("Fall of Wickets"):
            part = None
            continue
        toks = line.split()
        if part == "bat":
            nums = toks[-4:] if len(toks) >= 4 and all(re.fullmatch(r"\d+|-", x) for x in toks[-4:]) else None
            if nums is None:
                continue   # did not bat
            words = " ".join(toks[:-4]).lower()
            hurt = re.search(r"\b(retired|rtrd|retd|ret'd)\b.*\b(hurt|ht|ill)\b", words)
            out = not (hurt or any(k in words for k in NOT_OUT))
            cur["bat"].append((num(nums[0]), num(nums[1]), num(nums[2]), num(nums[3]), out))
        elif part == "bowl" and len(toks) >= 5 and re.fullmatch(r"[\d.]+", toks[-5]):
            o, _, r, w = toks[-5], toks[-4], toks[-3], toks[-2]
            balls = int(o) if cur["balls_count"] else overs_balls(o)
            cur["bowl"].append((balls, int(r), int(w)))
    return dict(innings=inns)


def corrected(career, mid: str, player: str) -> bool:
    """A batter the site counts out though the card prints him retired hurt: a correction the card itself proves
    (listed on the match and on the data check page), the one place the site and a literal reading of the card may
    differ, and only on whether he was out."""
    cs = career.corrections
    printed = re.sub(r" \([^)]*\)$", "", player)   # a shared name split by team, "S Singh (Jharkhand)", is printed "S Singh"
    return bool(len(cs)) and any(f"{printed} is printed" in x for x in cs[cs.match_id == mid].correction)


@pytest.fixture(scope="module")
def career():
    c = Career.build("Second counter", [(f.name, f.read_bytes()) for f in FILES])
    c.count_fielding = False
    return c


def test_every_line_counted_the_same(career):
    checked = 0
    for f in FILES:
        mine = count(f.read_text(errors="replace"))
        m = career.matches[career.matches.source == f.name]
        if m.empty:
            continue   # a copy of a match counted once
        mid = m.match_id.iloc[0]
        inns = career.innings[career.innings.match_id == mid]
        # the site keeps innings in batting order (a follow-on moved); match mine to it by team and that team's turn
        turn: dict = defaultdict(int)
        for k, x in enumerate(mine["innings"]):
            turn[x["team"]] += 1
            row = inns[(inns.team == x["team"]) & (inns.team_innings == turn[x["team"]])]
            assert len(row) == 1, (f.name, x["team"])
            no = int(row.innings_no.iloc[0])
            bat = career.batting[(career.batting.match_id == mid) & (career.batting.innings_no == no) & career.batting.did_bat]
            rows = list(bat.sort_values("position").itertuples())
            site_bat = [(int(r.runs), int(r.balls), int(r.fours), int(r.sixes), bool(r.out)) for r in rows]
            mine_bat = [(a, b_, c4, c6, (r.out if corrected(career, mid, r.player) else out))
                        for (a, b_, c4, c6, out), r in zip(x["bat"], rows)]
            assert len(rows) == len(x["bat"]) and site_bat == mine_bat, (f.name, x["team"], turn[x["team"]])
            bowl = career.bowling[(career.bowling.match_id == mid) & (career.bowling.innings_no == no)]
            site_bowl = sorted((int(r.balls), int(r.runs), int(r.wickets)) for r in bowl.itertuples())
            assert site_bowl == sorted(x["bowl"]), (f.name, x["team"], turn[x["team"]])
            checked += 1
    assert checked >= 100


def test_averages_strike_rates_and_economy_from_my_own_counts(career):
    """Every player's batting average and strike rate, and every bowler's economy and average, in every competition,
    worked out from the second counter's own numbers."""
    bat_tot: dict = defaultdict(lambda: [0, 0, 0])     # (section, player) -> runs, balls, outs
    bowl_tot: dict = defaultdict(lambda: [0, 0, 0])    # (section, player) -> balls, runs, wickets
    sec = career.matches.set_index("source").section
    for f in FILES:
        if f.name not in sec.index:
            continue
        mid = career.matches[career.matches.source == f.name].match_id.iloc[0]
        w = career.bowling[career.bowling.match_id == mid]
        mine = count(f.read_text(errors="replace"))
        inns = career.innings[career.innings.match_id == mid]
        turn: dict = defaultdict(int)
        for x in mine["innings"]:   # each printed innings matched to the site's by team and that team's turn
            turn[x["team"]] += 1
            no = int(inns[(inns.team == x["team"]) & (inns.team_innings == turn[x["team"]])].innings_no.iloc[0])
            b = career.batting[(career.batting.match_id == mid) & (career.batting.innings_no == no)
                               & career.batting.did_bat].sort_values("position")
            # names come from the site's rows (the counter checks the numbers; the names are the site's own)
            for (r, bl, _, _, out), p, site_out in zip(x["bat"], b.player, b.out):
                t = bat_tot[(sec[f.name], p)]
                t[0] += r; t[1] += bl; t[2] += bool(site_out) if corrected(career, mid, p) else out
        for p, balls, runs, wk in zip(w.player, w.balls, w.runs, w.wickets):
            t = bowl_tot[(sec[f.name], p)]
            t[0] += int(balls); t[1] += int(runs); t[2] += int(wk)
    checked = 0
    for s in career.matches.section.unique():
        from ccstats.stats import Scope
        bt, wt, _, _ = player_tables(career, Scope(sections=[s]))
        for r in bt.itertuples():
            runs, balls, outs = bat_tot[(s, r.player)]
            assert (int(r.runs), int(r.balls), int(r.outs)) == (runs, balls, outs), (s, r.player)
            if outs:
                assert r.average == pytest.approx(runs / outs), (s, r.player)
            if balls:
                assert r.strike_rate == pytest.approx(runs / balls * 100), (s, r.player)
            checked += 1
        for r in wt.itertuples():
            balls, runs, wk = bowl_tot[(s, r.player)]
            assert (int(r.balls), int(r.runs), int(r.wickets)) == (balls, runs, wk), (s, r.player)
            assert r.economy == pytest.approx(runs / balls * 6), (s, r.player)
            if wk:
                assert r.average == pytest.approx(runs / wk), (s, r.player)
            checked += 1
    assert checked >= 500
