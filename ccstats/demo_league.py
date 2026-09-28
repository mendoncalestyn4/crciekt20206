"""A made-up IPL, played ball by ball and written out as Cricket Captain 2026
scorecard files.

It gives the site something to show before a user uploads their own save,
and because it writes the exact text layout the game does, every generated
file goes through the real parser - so it doubles as an end-to-end test.
Results are invented; squads are the 2026 IPL teams.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, timedelta

# (name, bowls, keeps) in batting order.  Seven XIs are the ones in the
# user's CC2026 IPL scorecards; CSK, KKR and RR are filled in to complete
# the ten teams.
SQUADS: dict[str, list[tuple[str, bool, bool]]] = {
    "Chennai Super Kings": [
        ("R Gaikwad", 0, 0), ("S Samson", 0, 0), ("A Mhatre", 0, 0), ("D Brevis", 0, 0),
        ("S Dube", 1, 0), ("U Patel", 0, 0), ("M Dhoni", 0, 1), ("J Overton", 1, 0),
        ("N Ahmad", 1, 0), ("K Ahmed", 1, 0), ("A Kamboj", 1, 0)],
    "Delhi Capitals": [
        ("P Shaw", 0, 0), ("K Rahul", 0, 0), ("K Nair", 0, 0), ("T Stubbs", 0, 0),
        ("A Porel", 0, 1), ("N Rana", 1, 0), ("A Patel", 1, 0), ("A Mandal", 1, 0),
        ("A Nabi", 1, 0), ("K Yadav", 1, 0), ("L Ngidi", 1, 0)],
    "Gujarat Titans": [
        ("S Gill", 0, 0), ("S Sudharsan", 0, 0), ("C Esterhuizen", 0, 1), ("J Buttler", 0, 0),
        ("N Sindhu", 1, 0), ("R Tewatia", 1, 0), ("J Holder", 1, 0), ("M Suthar", 1, 0),
        ("R Khan", 1, 0), ("K Rabada", 1, 0), ("A Khan", 1, 0)],
    "Kolkata Knight Riders": [
        ("A Rahane", 0, 0), ("S Narine", 1, 0), ("A Raghuvanshi", 0, 0), ("C Green", 1, 0),
        ("R Singh", 0, 0), ("R Powell", 0, 0), ("R Gurbaz", 0, 1), ("H Rana", 1, 0),
        ("V C'avarthy", 1, 0), ("V Arora", 1, 0), ("M Pathirana", 1, 0)],
    "Lucknow Super Giants": [
        ("M Breetzke", 0, 0), ("A Markram", 1, 0), ("M Marsh", 0, 0), ("R Pant", 0, 1),
        ("A Badoni", 0, 0), ("A Kulkarni", 0, 0), ("S Ahmed", 1, 0), ("G Linde", 1, 0),
        ("M Khan", 1, 0), ("M Siddarth", 1, 0), ("M Yadav", 1, 0)],
    "Mumbai Indians": [
        ("W Jacks", 0, 0), ("R Sharma", 0, 0), ("T Varma", 0, 0), ("S Yadav", 0, 0),
        ("H Pandya", 1, 0), ("R Rickelton", 0, 1), ("C Bosch", 1, 0), ("D Chahar", 1, 0),
        ("S Raju", 1, 0), ("J Bumrah", 1, 0), ("A Ghazanfar", 1, 0)],
    "Punjab Kings": [
        ("H Singh", 0, 0), ("P Singh", 0, 1), ("S Iyer", 0, 0), ("P Arya", 0, 0),
        ("M Stoinis", 1, 0), ("A Omarzai", 1, 0), ("M Khan", 0, 0), ("M Jansen", 1, 0),
        ("H Brar", 1, 0), ("L Ferguson", 1, 0), ("Y Thakur", 1, 0)],
    "Rajasthan Royals": [
        ("Y Jaiswal", 0, 0), ("V Suryavanshi", 0, 0), ("R Parag", 1, 0), ("D Jurel", 0, 1),
        ("S Hetmyer", 0, 0), ("R Jadeja", 1, 0), ("S Curran", 1, 0), ("J Archer", 1, 0),
        ("S Sharma", 1, 0), ("T Deshpande", 1, 0), ("K Maphaka", 1, 0)],
    "Royal Challengers Bengaluru": [
        ("V Kohli", 0, 0), ("D Padikkal", 0, 0), ("J Cox", 0, 0), ("R Patidar", 0, 0),
        ("T David", 0, 0), ("J Sharma", 0, 1), ("K Pandya", 1, 0), ("B Kumar", 1, 0),
        ("R Salam", 1, 0), ("J Duffy", 1, 0), ("J Hazlewood", 1, 0)],
    "Sunrisers Hyderabad": [
        ("A Sharma", 1, 0), ("T Head", 0, 0), ("I Kishan", 0, 1), ("L Livingstone", 1, 0),
        ("S Arora", 0, 0), ("R Smaran", 0, 0), ("A Verma", 0, 0), ("P Cummins", 1, 0),
        ("H Patel", 1, 0), ("D Payne", 1, 0), ("J Unadkat", 1, 0)],
}
SHORT = {  # used in file names, like the game does
    "Chennai Super Kings": "chn", "Delhi Capitals": "del", "Gujarat Titans": "gjt",
    "Kolkata Knight Riders": "kol", "Lucknow Super Giants": "lkn", "Mumbai Indians": "mmb",
    "Punjab Kings": "pnj", "Rajasthan Royals": "raj", "Royal Challengers Bengaluru": "bgl",
    "Sunrisers Hyderabad": "hdr",
}
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


@dataclass
class Player:
    name: str
    bat: float
    bowl: float
    bowls: bool
    keeps: bool


@dataclass
class BatLine:
    player: Player
    runs: int = 0
    balls: int = 0
    fours: int = 0
    sixes: int = 0
    out: str = ""  # dismissal text, "" = not out
    batted: bool = False


@dataclass
class BowlLine:
    player: Player
    balls: int = 0
    dots: int = 0
    runs: int = 0
    wkts: int = 0


@dataclass
class InningsResult:
    team: str
    bat: list[BatLine]
    bowl: list[BowlLine]
    total: int = 0
    wkts: int = 0
    balls: int = 0
    wides: int = 0
    no_balls: int = 0
    fow: list[tuple[int, int]] = field(default_factory=list)


def _surname(name: str) -> str:
    return name.split(" ", 1)[1] if " " in name else name


def build_teams(rng: random.Random) -> dict[str, list[Player]]:
    teams = {}
    for team, squad in SQUADS.items():
        form = rng.gauss(0, 0.035)  # some sides are a bit better than others
        players = []
        for pos, (name, bowls, keeps) in enumerate(squad):
            if pos < 4:
                bat = rng.gauss(1.12, 0.08)
            elif pos < 7:
                bat = rng.gauss(1.0, 0.08)
            elif pos < 8:
                bat = rng.gauss(0.72, 0.1)
            else:
                bat = rng.gauss(0.42, 0.1)
            bowl = rng.gauss(1.0, 0.07) if bowls else 0.7
            players.append(Player(name, max(0.25, bat + form), max(0.6, bowl + form), bool(bowls), bool(keeps)))
        teams[team] = players
    return teams


def _pick_bowler(bowlers: list[BowlLine], last: BowlLine | None, rng: random.Random) -> BowlLine:
    options = [b for b in bowlers if b.balls < 24 and b is not last] or [b for b in bowlers if b.balls < 24]
    weights = [b.player.bowl ** 3 for b in options]
    return rng.choices(options, weights)[0]


def play_innings(team: str, batters: list[Player], fielders: list[Player], rng: random.Random,
                 target: int | None = None, home_edge: float = 1.0) -> InningsResult:
    bat = [BatLine(p) for p in batters]
    bowlers = [BowlLine(p) for p in fielders if p.bowls]
    inn = InningsResult(team, bat, bowlers)
    striker, non_striker, next_in = 0, 1, 2
    bat[0].batted = bat[1].batted = True
    keeper = next((p for p in fielders if p.keeps), fielders[0])
    last = None
    for over in range(20):
        bowler = _pick_bowler(bowlers, last, rng)
        last = bowler
        legal = 0
        while legal < 6:
            b = bat[striker]
            if rng.random() < 0.028:  # wide
                inn.wides += 1; inn.total += 1; bowler.runs += 1
                continue
            if rng.random() < 0.006:  # no ball
                inn.no_balls += 1; inn.total += 1; bowler.runs += 1
                continue
            legal += 1
            inn.balls += 1; bowler.balls += 1; b.balls += 1
            m = (b.player.bat * home_edge) / bowler.player.bowl
            death = 1.15 if over >= 16 else 1.0
            p_w = 0.056 / m ** 1.2 * (1.1 if over >= 16 else 1.0)
            p4, p6 = 0.14 * m * death, 0.078 * m ** 1.6 * death
            p2, p3 = 0.07, 0.004
            p0 = 0.35 / m ** 0.5
            p1 = max(0.05, 1 - p_w - p4 - p6 - p2 - p3 - p0)
            r = rng.choices(["W", 0, 1, 2, 3, 4, 6], [p_w, p0, p1, p2, p3, p4, p6])[0]
            if r == "W":
                kind = rng.choices(["c", "b", "lbw", "ro", "st"], [0.6, 0.16, 0.15, 0.05, 0.04])[0]
                bowler.dots += 1
                if kind == "ro":
                    b.out = "run out"
                else:
                    bowler.wkts += 1
                    bs = _surname(bowler.player.name)
                    if kind == "c":
                        f = rng.choices(fielders, [2.5 if p.keeps else (0.6 if p is bowler.player else 1) for p in fielders])[0]
                        b.out = f"c & b {bs}" if f is bowler.player else f"c {_surname(f.name)} b {bs}"
                    elif kind == "st":
                        b.out = f"st {_surname(keeper.name)} b {bs}"
                    else:
                        b.out = f"{'lbw ' if kind == 'lbw' else ''}b {bs}"
                inn.wkts += 1
                inn.fow.append((inn.wkts, inn.total))
                if inn.wkts == 10 or next_in > 10:
                    return inn
                bat[next_in].batted = True
                striker, next_in = next_in, next_in + 1
            else:
                b.runs += r; inn.total += r; bowler.runs += r
                if r == 0:
                    bowler.dots += 1
                b.fours += r == 4
                b.sixes += r == 6
                if r % 2:
                    striker, non_striker = non_striker, striker
            if target is not None and inn.total >= target:
                return inn
        striker, non_striker = non_striker, striker
    return inn


# ------------------------------------------------------------------ writing


def _overs(balls: int) -> str:
    return f"{balls // 6}" if balls % 6 == 0 else f"{balls // 6}.{balls % 6}"


def _cell(v: int) -> str:
    return str(v) if v else "-"


def write_innings(inn: InningsResult) -> list[str]:
    out = [f"{inn.team + ' - 1st Innings':<42}R    B    4s  6s", "-" * 60]
    for b in inn.bat:
        if b.batted:
            how = b.out or "not out"
            out.append(f"{b.player.name:<16}{how:<26}{b.runs:<5}{b.balls:<5}{_cell(b.fours):<4}{_cell(b.sixes)}")
        else:
            out.append(f"{b.player.name:<16}")
    out.append("-" * 60)
    parts = [f"nb{inn.no_balls}"] * bool(inn.no_balls) + [f"w{inn.wides}"] * bool(inn.wides)
    extras = inn.wides + inn.no_balls
    out.append(f"{'Extras: ' + ('(' + ','.join(parts) + ')' if parts else ''):<42}{extras}")
    wk = "all out" if inn.wkts == 10 else f"{inn.wkts} wkts"
    out.append(f"{f'TOTAL: ({wk}, {_overs(inn.balls)} overs)':<42}{inn.total}")
    out += ["", "*" * 60, "", "                O      D     R      W     Econ", "-" * 60]
    for bw in inn.bowl:
        if bw.balls:
            econ = bw.runs / bw.balls * 6
            out.append(f"{bw.player.name:<16}{_overs(bw.balls):<7}{bw.dots:<6}{bw.runs:<7}{bw.wkts:<6}{econ:.2f}")
    out += ["-" * 60, "Fall of Wickets:"]
    fow = [f"{w}-{s}  " for w, s in inn.fow]
    for i in range(0, len(fow), 5):
        out.append("".join(fow[i:i + 5]))
    out += ["", "", "*" * 60]
    return out


def play_match(home: str, away: str, teams: dict[str, list[Player]], when: date, title: str,
               rng: random.Random) -> tuple[str, str]:
    """Returns (winner, scorecard text)."""
    if rng.random() < 0.5:
        first, second = home, away
    else:
        first, second = away, home
    edge = {home: 1.025, away: 1.0}
    one = play_innings(first, teams[first], teams[second], rng, home_edge=edge[first])
    two = play_innings(second, teams[second], teams[first], rng, target=one.total + 1, home_edge=edge[second])
    if two.total > one.total:
        winner, result = second, f"{second} won by {10 - two.wkts} wicket{'s' * (10 - two.wkts != 1)}"
    elif one.total > two.total:
        margin = one.total - two.total
        winner, result = first, f"{first} won by {margin} run{'s' * (margin != 1)}"
    else:
        winner, result = "", "Match tied"

    pool = [(b.runs + 22 * next((w.wkts for w in inn2.bowl if w.player.name == b.player.name), 0), b.player.name)
            for inn, inn2 in ((one, two), (two, one)) for b in inn.bat]
    motm = max(pool)[1]
    lines = ["*" * 60, f"{home} v {away}", f"{title} - {when.day} {MONTHS[when.month - 1]} {when.year}", "*" * 60, ""]
    lines += write_innings(one) + ["*" * 60, ""] + write_innings(two)
    lines += [result, f"Man of the match: {motm}", "*" * 60, ""]
    return winner, "\n".join(lines)


def generate_season(year: int, teams: dict[str, list[Player]], rng: random.Random) -> list[tuple[str, str]]:
    """A double round robin plus playoffs.  Returns (file name, text) pairs."""
    names = list(teams)
    fixtures = [(a, b) for a in names for b in names if a != b]
    rng.shuffle(fixtures)
    start = date(year, 3, 22)
    files, table = [], {t: [0, 0] for t in names}
    for i, (a, b) in enumerate(fixtures):
        when = start + timedelta(days=i * 60 // len(fixtures))
        winner, text = play_match(a, b, teams, when, "Indian Premier League", rng)
        for t in (a, b):
            table[t][1] += 1
            table[t][0] += 2 if t == winner else (1 if not winner else 0)
        files.append((f"{when.day}_{MONTHS[when.month - 1].lower()}_{year}-{SHORT[a]}_v_{SHORT[b]}_ipl.txt", text))
    ranked = sorted(names, key=lambda t: (-table[t][0], rng.random()))
    last = start + timedelta(days=62)

    def playoff(a: str, b: str, stage: str, code: str, days: int) -> tuple[str, str]:
        when = last + timedelta(days=days)
        winner, text = play_match(a, b, teams, when, f"Indian Premier League - {stage}", rng)
        if not winner:  # a tied playoff goes to the higher seed
            winner = a
        files.append((f"{when.day}_{MONTHS[when.month - 1].lower()}_{year}-{SHORT[a]}_v_{SHORT[b]}_ipl_-_{code}.txt", text))
        return winner, (b if winner == a else a)

    q1w, q1l = playoff(ranked[0], ranked[1], "Qualifier 1", "q1", 1)
    # the game titles the Eliminator "Qualifier 1" as well
    elw, _ = playoff(ranked[2], ranked[3], "Qualifier 1", "q1", 2)
    q2w, _ = playoff(q1l, elw, "Qualifier 2", "q2", 4)
    playoff(q1w, q2w, "Final", "f", 6)
    return files


def generate(seasons: tuple[int, ...] = (2026, 2027), seed: int = 2026) -> list[tuple[str, str]]:
    rng = random.Random(seed)
    teams = build_teams(rng)
    files = []
    for year in seasons:
        files += generate_season(year, teams, rng)
    return files
