"""A made-up 20-season career (stage 5, item 7 of your list of 26 November): about 12,800 matches of every kind (20 seasons: 12,760),
written out exactly as Cricket Captain writes its scorecards, so every page can be shown right and quick as a career
grows to 20 seasons. Your own saves stay out of the project; this one can live in the checks.

Every season: Tests, ODIs and T20Is (each nation in two tours a year), the Indian Premier League, the Big Bash League,
the County Championship (two divisions), the T20 Blast, the One-Day Cup, the Ranji Trophy, the Vijay Hazare Trophy,
the Syed Mushtaq Ali Trophy, the Sheffield Shield and the Marsh One-Day Cup. Players debut, get better, peak and fade, and retire; new ones come through, so
careers, eras and records move the way a long career's do. Each competition has its own window of the year, so no
player is ever in two matches at once. Everything comes from one seed: the same files every time.

    files = generate(seasons=20)          # [(file name, text), ...]"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from datetime import date, timedelta

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
SURNAMES = {
    "England": ["Ashby", "Barlow", "Carver", "Dunne", "Ellery", "Fenwick", "Garner", "Hollis", "Ingram", "Jessop", "Kerrigan",
                "Lister", "Marsden", "Norris", "Oakley", "Pargeter", "Quill", "Radley", "Stanworth", "Thorley", "Underhill",
                "Vane", "Whitlock", "Yardley", "Ashworth", "Bramall", "Colley", "Dawlish", "Eastwood", "Farrant"],
    "India": ["Agarwal", "Bhatt", "Chandran", "Desai", "Gaikwad", "Hegde", "Iyengar", "Joshi", "Kulkarni", "Lokesh",
              "Menon", "Nair", "Oberoi", "Pillai", "Rao", "Saxena", "Thakur", "Upadhyay", "Varma", "Yadav", "Bhosale",
              "Chauhan", "Dalal", "Gupta", "Jadhav", "Khanna", "Mehra", "Naidu", "Pandit", "Shetty"],
    "Australia": ["Abbott", "Brennan", "Calder", "Doherty", "Eckert", "Fawcett", "Gilmour", "Halloran", "Inglis", "Jaques",
                  "Kilroy", "Lennox", "McTavish", "Nolan", "O'Shea", "Prentice", "Quinlan", "Rafferty", "Sutcliffe",
                  "Trengove", "Ulrich", "Vickery", "Walsh", "Yeoman", "Barwick", "Coulter", "Dempster", "Everett"],
    "South Africa": ["Abrahams", "Botha", "Coetzee", "Du Toit", "Erasmus", "Fourie", "Grobler", "Hendricks", "Jacobs",
                     "Kruger", "Lombard", "Mokoena", "Nel", "Olivier", "Pretorius", "Roux", "Steyn", "Theron", "Venter",
                     "Visagie", "Wessels", "Zulu"],
    "New Zealand": ["Aldridge", "Bracewell", "Cairncross", "Donnelly", "Elwood", "Fulton", "Gillespie", "Hadlow", "Irvine",
                    "Kerr", "Latimer", "Munro", "Neesham", "Ormond", "Parore", "Rennie", "Shrimpton", "Tuffey", "Vettori",
                    "Wagstaff", "Young", "Lund"],
    "Pakistan": ["Afridi", "Butt", "Chaudhry", "Durrani", "Farooq", "Gul", "Hafeez", "Iqbal", "Jamshed", "Khattak",
                 "Latif", "Malik", "Nawaz", "Qadir", "Rauf", "Sohail", "Tanvir", "Umar", "Wasim", "Yasir", "Zaman", "Mirza"],
    "Sri Lanka": ["Amarasinghe", "Bandara", "Chandimal", "Dissanayake", "Fernando", "Gunaratne", "Herath", "Jayasekara",
                  "Kumara", "Lakmal", "Mendis", "Nissanka", "Perera", "Rajapaksa", "Samarawickrama", "Thirimanne",
                  "Udana", "Vandersay", "Wickramasinghe", "Silva", "Karunaratne", "Pathirana"],
    "West Indies": ["Ambrose", "Brathwaite", "Chanderpaul", "Dowrich", "Edwards", "Forde", "Garrick", "Hinds", "Joseph",
                    "King", "Lambert", "Mayers", "Nurse", "Paul", "Roach", "Samuels", "Thomas", "Walcott", "Warrican",
                    "Blades", "Cottoy", "Phillip"],
}
# printed names fit the game's columns, as its own do: one-word surnames, and a long one shortened the game's way
# (Chakravarthy is printed C'avarthy), so "c Dissanayake b Jayasekara" never runs into the runs
SURNAMES = {n: sorted({x if len(x) <= 9 else f"{x[0]}'{x[-7:]}" for x in v if " " not in x}) for n, v in SURNAMES.items()}
NATIONS = list(SURNAMES)
COUNTIES = ["Ashdown", "Brackenshire", "Cliffmouth", "Dalesford", "Easterly", "Fernhurst", "Greystone", "Hollowmere",
            "Ironbridge", "Kestrel Vale", "Lowmoor", "Marshgate", "Northam", "Oakshire", "Pennway", "Riverstow"]
STATES = ["Arunapur", "Bhavnagar State", "Chandrapur", "Devgiri", "Eastgate", "Gomti", "Himgiri", "Indravati",
          "Jalpur", "Kaveri"]
SHIELD = ["Bayside", "Coralcoast", "Goldfields", "Harbourtown", "Redsands", "Snowyridge"]
IPL = ["Chennai Super Kings", "Delhi Capitals", "Gujarat Titans", "Kolkata Knight Riders", "Lucknow Super Giants",
       "Mumbai Indians", "Punjab Kings", "Rajasthan Royals", "Royal Challengers Bengaluru", "Sunrisers Hyderabad"]
BBL = ["Adelaide Strikers", "Brisbane Heat", "Hobart Hurricanes", "Melbourne Renegades", "Melbourne Stars",
       "Perth Scorchers", "Sydney Sixers", "Sydney Thunder"]
# how each kind of cricket is played: balls an innings (None: no limit), the most a bowler may bowl, the bowling
# column (dots in T20s, maidens otherwise) and the ball's odds
KINDS = {
    "t20": dict(balls=120, cap=24, col="D", w=0.056, p4=0.14, p6=0.078, p0=0.35),
    "one": dict(balls=300, cap=60, col="M", w=0.032, p4=0.085, p6=0.022, p0=0.46),
    "multi": dict(balls=None, cap=None, col="M", w=0.019, p4=0.062, p6=0.006, p0=0.60),
}


@dataclass(eq=False)
class Player:
    name: str
    nation: str
    bat: float
    bowl: float
    bowls: bool
    keeps: bool
    first: int            # the season they start
    length: int           # seasons they play
    home: str = ""        # their domestic side

    def active(self, y: int) -> bool:
        return self.first <= y < self.first + self.length

    def form(self, y: int) -> float:
        """Better in their middle seasons, a little less at the start and the end."""
        t = (y - self.first + 0.5) / self.length
        return 0.86 + 0.24 * math.sin(math.pi * t)


@dataclass
class Bat:
    p: Player
    runs: int = 0
    balls: int = 0
    fours: int = 0
    sixes: int = 0
    out: str = ""
    batted: bool = False


@dataclass
class Bowl:
    p: Player
    balls: int = 0
    dots: int = 0
    maidens: int = 0
    runs: int = 0
    wkts: int = 0


@dataclass
class Inn:
    team: str
    no: int
    bat: list[Bat]
    bowl: list[Bowl]
    total: int = 0
    wkts: int = 0
    balls: int = 0
    wides: int = 0
    no_balls: int = 0
    fow: list[tuple[int, int]] = field(default_factory=list)


class World:
    def __init__(self, start: int, seasons: int, rng: random.Random):
        self.rng, self.start, self.seasons = rng, start, seasons
        self.used: set[str] = set()
        self.pool: dict[str, list[Player]] = {n: [] for n in NATIONS}
        sizes = {"England": len(COUNTIES) * 15, "India": len(STATES) * 15, "Australia": len(SHIELD) * 15}
        for n in NATIONS:
            for _ in range(sizes.get(n, 34)):
                self.pool[n].append(self.new_player(n, start - rng.randint(0, 12)))
        self.homes()

    def new_player(self, nation: str, first: int) -> Player:
        r = self.rng
        for _ in range(500):
            name = f"{r.choice('ABCDEGHJKLMNPRSTW')} {r.choice(SURNAMES[nation])}"
            if name not in self.used:
                break
        else:
            name = f"{r.choice('ABCDEGHJKLMNPRSTW')}{r.choice('ABCDEGHJKLMNPRSTW')} {r.choice(SURNAMES[nation])}"
            while name in self.used:
                name = f"{r.choice('ABCDEGHJKLMNPRSTW')}{r.choice('ABCDEGHJKLMNPRSTW')} {r.choice(SURNAMES[nation])}"
        self.used.add(name)
        role = r.random()
        bat = r.gauss(1.05, 0.12) if role < 0.45 else r.gauss(0.85, 0.12) if role < 0.65 else r.gauss(0.5, 0.12)
        bowls = role >= 0.45
        bowl = r.gauss(1.0, 0.08) if role >= 0.65 else r.gauss(0.88, 0.08) if bowls else 0.7
        return Player(name, nation, max(0.25, bat), max(0.6, bowl), bowls, role < 0.45 and r.random() < 0.2, first,
                      r.randint(7, 15))

    def homes(self) -> None:
        for n, sides in (("England", COUNTIES), ("India", STATES), ("Australia", SHIELD)):
            for i, p in enumerate(self.pool[n]):
                p.home = p.home or sides[i % len(sides)]

    def season_begins(self, y: int) -> None:
        """Retired players are replaced by new ones (debuting this season), so each pool keeps its size."""
        for n in NATIONS:
            for i, p in enumerate(self.pool[n]):
                if not p.active(y):
                    q = self.new_player(n, y)
                    q.home = p.home
                    self.pool[n][i] = q

    def xi(self, players: list[Player], y: int) -> list[Player]:
        """The best XI of these players this season: 6 batters (a keeper among them), the best all-rounder, 4 bowlers;
        in batting order."""
        ps = [p for p in players if p.active(y)]
        by_bat = sorted(ps, key=lambda p: -p.bat * p.form(y))
        keeper = next((p for p in by_bat if p.keeps), by_bat[0])
        bowlers = sorted((p for p in ps if p.bowls and p is not keeper), key=lambda p: -p.bowl * p.form(y))[:5]
        rest = [p for p in by_bat if p is not keeper and p not in bowlers][:5]
        side = rest + [keeper] + sorted(bowlers, key=lambda p: -p.bat)
        side += [p for p in by_bat if p not in side][: 11 - len(side)]     # a thin squad: the best of the rest
        return sorted(side[:11], key=lambda p: (p in bowlers, -p.bat))


def _surname(name: str) -> str:
    return name.split(" ", 1)[1]


def _pick(bowlers: list[Bowl], last: Bowl | None, cap: int | None, y: int, rng: random.Random) -> Bowl:
    ok = [b for b in bowlers if (cap is None or b.balls < cap) and b is not last] or \
         [b for b in bowlers if cap is None or b.balls < cap] or bowlers
    return rng.choices(ok, [(b.p.bowl * b.p.form(y)) ** 3 for b in ok])[0]


def innings(team: str, no: int, batters: list[Player], fielders: list[Player], kind: str, y: int, rng: random.Random,
            target: int | None = None, budget: int | None = None, declare: int | None = None, home: float = 1.0) -> Inn:
    """One innings, ball by ball: ends all out, at the format's balls, at the target, at a declaration (multi-day) or
    when the match's time (`budget` balls) runs out."""
    k = KINDS[kind]
    bat = [Bat(p) for p in batters]
    bowlers = [Bowl(p) for p in fielders if p.bowls]
    keeper_ = next((p for p in fielders if p.keeps), None)
    spare = [p for p in sorted(fielders, key=lambda p: -p.bowl) if not p.bowls and p is not keeper_]
    while k["cap"] and len(bowlers) * k["cap"] < k["balls"] and spare:     # enough bowlers for the overs: part-timers
        bowlers.append(Bowl(spare.pop(0)))
    inn = Inn(team, no, bat, bowlers)
    s, ns, nxt = 0, 1, 2
    bat[0].batted = bat[1].batted = True
    keeper = next((p for p in fielders if p.keeps), fielders[0])
    last = None
    limit = k["balls"] if budget is None else (budget if k["balls"] is None else min(k["balls"], budget))
    while limit is None or inn.balls < limit:
        bw = _pick(bowlers, last, k["cap"], y, rng)
        last = bw
        legal, over_runs = 0, 0
        while legal < 6 and (limit is None or inn.balls < limit):
            b = bat[s]
            if rng.random() < (0.028 if kind == "t20" else 0.015):
                inn.wides += 1; inn.total += 1; bw.runs += 1; over_runs += 1
                continue
            if rng.random() < 0.006:
                inn.no_balls += 1; inn.total += 1; bw.runs += 1; over_runs += 1
                continue
            legal += 1
            inn.balls += 1; bw.balls += 1; b.balls += 1
            m = (b.p.bat * b.p.form(y) * home) / (bw.p.bowl * bw.p.form(y))
            p_w = k["w"] / m ** 1.2
            p4, p6 = k["p4"] * m, k["p6"] * m ** 1.6
            p2, p3 = 0.06, 0.006
            p0 = k["p0"] / m ** 0.5
            p1 = max(0.05, 1 - p_w - p4 - p6 - p2 - p3 - p0)
            r = rng.choices(["W", 0, 1, 2, 3, 4, 6], [p_w, p0, p1, p2, p3, p4, p6])[0]
            if r == "W":
                how = rng.choices(["c", "b", "lbw", "ro", "st"], [0.58, 0.18, 0.16, 0.05, 0.03])[0]
                bw.dots += 1
                if how == "ro":
                    b.out = "run out"
                else:
                    bw.wkts += 1
                    bs = _surname(bw.p.name)
                    if how == "c":
                        f = rng.choices(fielders, [2.5 if p.keeps else (0.6 if p is bw.p else 1) for p in fielders])[0]
                        b.out = f"c & b {bs}" if f is bw.p else f"c {_surname(f.name)} b {bs}"
                    elif how == "st":
                        b.out = f"st {_surname(keeper.name)} b {bs}"
                    else:
                        b.out = f"{'lbw ' if how == 'lbw' else ''}b {bs}"
                inn.wkts += 1
                inn.fow.append((inn.wkts, inn.total))
                if inn.wkts == 10 or nxt >= len(bat):
                    return _maiden(inn, bw, legal, over_runs)
                bat[nxt].batted = True
                s, nxt = nxt, nxt + 1
            else:
                b.runs += r; inn.total += r; bw.runs += r; over_runs += r
                bw.dots += r == 0
                b.fours += r == 4
                b.sixes += r == 6
                if r % 2:
                    s, ns = ns, s
            if (target is not None and inn.total >= target) or (declare is not None and inn.total >= declare):
                return _maiden(inn, bw, legal, over_runs)
        _maiden(inn, bw, legal, over_runs)
        s, ns = ns, s
    return inn


def _maiden(inn: Inn, bw: Bowl, legal: int, runs: int) -> Inn:
    if legal == 6 and runs == 0:
        bw.maidens += 1
    return inn


def _overs(balls: int) -> str:
    return f"{balls // 6}" if balls % 6 == 0 else f"{balls // 6}.{balls % 6}"


def _cell(v: int) -> str:
    return str(v) if v else "-"


def write(inn: Inn, kind: str) -> list[str]:
    nth = {1: "1st", 2: "2nd"}[inn.no]
    out = [f"{f'{inn.team} - {nth} Innings':<42}R    B    4s  6s", "-" * 60]
    for b in inn.bat:
        if b.batted:
            out.append(f"{b.p.name:<16}{(b.out or 'not out'):<26}{b.runs:<5}{b.balls:<5}{_cell(b.fours):<4}{_cell(b.sixes)}")
        else:
            out.append(f"{b.p.name:<16}")
    out.append("-" * 60)
    parts = [f"nb{inn.no_balls}"] * bool(inn.no_balls) + [f"w{inn.wides}"] * bool(inn.wides)
    out.append(f"{'Extras: ' + ('(' + ','.join(parts) + ')' if parts else ''):<42}{inn.wides + inn.no_balls}")
    wk = "all out" if inn.wkts == 10 else f"{inn.wkts} wkts"
    out.append(f"{f'TOTAL: ({wk}, {_overs(inn.balls)} overs)':<42}{inn.total}")
    col = KINDS[kind]["col"]
    out += ["", "*" * 60, "", f"                O      {col}     R      W     Econ", "-" * 60]
    for bw in inn.bowl:
        if bw.balls:
            econ = bw.runs / bw.balls * 6
            mid = bw.dots if col == "D" else bw.maidens
            out.append(f"{bw.p.name:<16}{_overs(bw.balls):<7}{mid:<6}{bw.runs:<7}{bw.wkts:<6}{econ:.2f}")
    out += ["-" * 60, "Fall of Wickets:"]
    fow = [f"{w}-{s}  " for w, s in inn.fow]
    for i in range(0, len(fow), 5):
        out.append("".join(fow[i:i + 5]))
    out += ["", "", "*" * 60]
    return out


def match(home: str, away: str, xi_h: list[Player], xi_a: list[Player], kind: str, title: str, when: date, y: int,
          rng: random.Random, days: int = 0) -> str:
    """One match written out as the game does: limited overs, or a multi-day game of `days` days (declarations, a
    chase, a draw when time runs out, an innings win)."""
    first, second = (home, away) if rng.random() < 0.5 else (away, home)
    xi = {home: xi_h, away: xi_a}
    edge = {home: 1.03, away: 1.0}
    inns: list[Inn] = []
    if kind != "multi":
        one = innings(first, 1, xi[first], xi[second], kind, y, rng, home=edge[first])
        two = innings(second, 1, xi[second], xi[first], kind, y, rng, target=one.total + 1, home=edge[second])
        inns = [one, two]
        if two.total > one.total:
            winner, result = second, f"{second} won by {10 - two.wkts} wicket{'s' * (10 - two.wkts != 1)}"
        elif one.total > two.total:
            mg = one.total - two.total
            winner, result = first, f"{first} won by {mg} run{'s' * (mg != 1)}"
        else:
            winner, result = "", "Match tied"
    else:
        left = days * 540
        a1 = innings(first, 1, xi[first], xi[second], kind, y, rng, budget=left, declare=rng.randint(430, 650),
                     home=edge[first])
        left -= a1.balls
        inns = [a1]
        winner, result = "", "Match drawn"
        if left > 0:
            b1 = innings(second, 1, xi[second], xi[first], kind, y, rng, budget=left, home=edge[second])
            left -= b1.balls
            inns.append(b1)
            if left > 0:
                lead_needed = b1.total - a1.total + rng.randint(220, 380)
                a2 = innings(first, 2, xi[first], xi[second], kind, y, rng, budget=left,
                             declare=max(lead_needed, 1) if lead_needed > 0 else None, home=edge[first])
                left -= a2.balls
                inns.append(a2)
                if a2.wkts == 10 and a1.total + a2.total < b1.total:
                    mg = b1.total - a1.total - a2.total
                    winner, result = second, f"{second} won by an innings and {mg} run{'s' * (mg != 1)}"
                elif left > 0:
                    target = a1.total + a2.total - b1.total + 1
                    b2 = innings(second, 2, xi[second], xi[first], kind, y, rng, target=target, budget=left,
                                 home=edge[second])
                    inns.append(b2)
                    if b2.total >= target:
                        winner, result = second, f"{second} won by {10 - b2.wkts} wicket{'s' * (10 - b2.wkts != 1)}"
                    elif b2.wkts == 10:
                        mg = target - 1 - b2.total
                        winner = first
                        result = f"{first} won by {mg} run{'s' * (mg != 1)}" if mg else "Match tied"
                        winner = winner if mg else ""
    pool = [(b.runs + 22 * sum(w.wkts for i2 in inns if i2.team != i.team for w in i2.bowl if w.p is b.p), b.p.name)
            for i in inns for b in i.bat]
    motm = max(pool)[1]
    lines = ["*" * 60, f"{home} v {away}", f"{title} - {when.day} {MONTHS[when.month - 1]} {when.year}", "*" * 60, ""]
    for i in inns:
        lines += write(i, kind) + ["*" * 60, ""] if i is not inns[-1] else write(i, kind)
    lines += [result, f"Man of the match: {motm}", "*" * 60, ""]
    return "\n".join(lines)


def _code(team: str) -> str:
    w = [x for x in team.replace("'", "").split() if x]
    return (w[0][:3] if len(w) == 1 else "".join(x[0] for x in w[:3])).lower()


ORD = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 5: "5th"}


def _league(name: str, teams: list[str], sides: dict[str, list[Player]], kind: str, start: date, gap: int, y: int,
            rng: random.Random, files: list, code: str, double: bool = True, days: int = 0, knockouts: bool = True,
            title_extra: str = "") -> None:
    """A round robin (twice when `double`), one round every `gap` days, then a semi-final and a final for the top 4."""
    pairs = [(a, b) for i, a in enumerate(teams) for b in teams[i + 1:]]
    games = pairs + ([(b, a) for a, b in pairs] if double else [])
    rng.shuffle(games)
    # rounds: no side twice in a round
    rounds: list[list[tuple[str, str]]] = []
    for g in games:
        for r in rounds:
            if all(g[0] not in x and g[1] not in x for x in r):
                r.append(g)
                break
        else:
            rounds.append([g])
    pts = {t: 0 for t in teams}
    when = start
    for r in rounds:
        for a, b in r:
            text = match(a, b, sides[a], sides[b], kind, f"{name}{title_extra}", when, y, rng, days)
            files.append((f"{when.day}_{MONTHS[when.month - 1].lower()}_{when.year}-{_code(a)}_v_{_code(b)}_{code}.txt", text))
            res = text.rsplit("\n", 4)[1]
            pts[a] += 2 if res.startswith(a + " won") else 1 if "drawn" in res or "tied" in res else 0
            pts[b] += 2 if res.startswith(b + " won") else 1 if "drawn" in res or "tied" in res else 0
        when += timedelta(days=gap)
    if not knockouts:
        return
    top = sorted(teams, key=lambda t: (-pts[t], rng.random()))[:4]
    finalists = []
    for a, b, tag in ((top[0], top[3], "Semi-Final"), (top[1], top[2], "Semi-Final")):
        text = match(a, b, sides[a], sides[b], kind, f"{name} - {tag}", when, y, rng, days)
        files.append((f"{when.day}_{MONTHS[when.month - 1].lower()}_{when.year}-{_code(a)}_v_{_code(b)}_{code}_-_sf.txt", text))
        res = text.rsplit("\n", 4)[1]
        finalists.append(b if res.startswith(b + " won") else a)
    when += timedelta(days=gap)
    a, b = finalists
    text = match(a, b, sides[a], sides[b], kind, f"{name} - Final", when, y, rng, days)
    files.append((f"{when.day}_{MONTHS[when.month - 1].lower()}_{when.year}-{_code(a)}_v_{_code(b)}_{code}_-_f.txt", text))


def _tours(world: World, y: int, start: date, rng: random.Random, files: list) -> None:
    """Four tours at once (every nation in one): 2 or 3 Tests, 3 ODIs, 3 T20Is."""
    order = NATIONS[:]
    rng.shuffle(order)
    for host, guest in zip(order[::2], order[1::2]):
        xi_h, xi_g = world.xi(world.pool[host], y), world.xi(world.pool[guest], y)
        when = start
        n_tests = rng.choice((2, 3))
        for i in range(1, n_tests + 1):
            text = match(host, guest, xi_h, xi_g, "multi", f"{ORD[i]} Test Match (of {n_tests})", when, y, rng, days=5)
            files.append((f"{when.day}_{MONTHS[when.month - 1].lower()}_{when.year}-{_code(host)}_v_{_code(guest)}_{ORD[i]}_tst.txt", text))
            when += timedelta(days=7)
        for kind, title, code in (("one", "One Day International", "odi"), ("t20", "20 Over International", "20_over_int")):
            for i in range(1, 4):
                text = match(host, guest, xi_h, xi_g, kind, f"{ORD[i]} {title} (of 3)", when, y, rng)
                files.append((f"{when.day}_{MONTHS[when.month - 1].lower()}_{when.year}-{_code(host)}_v_{_code(guest)}_{ORD[i]}_{code}.txt", text))
                when += timedelta(days=3)


def generate(seasons: int = 20, start: int = 2026, seed: int = 7) -> list[tuple[str, str]]:
    rng = random.Random(seed)
    world = World(start, seasons, rng)
    files: list[tuple[str, str]] = []
    for y in range(start, start + seasons):
        world.season_begins(y)

        def sides_of(nation: str, names: list[str]) -> dict[str, list[Player]]:
            return {t: world.xi([p for p in world.pool[nation] if p.home == t], y) for t in names}
        # franchise squads, picked again every season: the best of India (IPL) or Australia (BBL), with 4 from abroad
        abroad = [p for n in ("South Africa", "New Zealand", "Pakistan", "Sri Lanka", "West Indies") for p in world.pool[n]]
        for league, home_n, teams in (("ipl", "India", IPL), ("bbl", "Australia", BBL)):
            locals_ = sorted((p for p in world.pool[home_n] + (world.pool["Australia"] if league == "ipl" else [])
                              if p.active(y)), key=lambda p: -max(p.bat, p.bowl) * p.form(y))
            overseas = sorted((p for p in abroad if p.active(y)), key=lambda p: -max(p.bat, p.bowl) * p.form(y))
            squads: dict[str, list[Player]] = {t: [] for t in teams}
            for i, p in enumerate(locals_[: 10 * len(teams)] + overseas[: 4 * len(teams)]):
                squads[teams[i % len(teams)]].append(p)
            sides = {t: world.xi(squads[t], y) for t in teams}
            if league == "ipl":
                _league("Indian Premier League", teams, sides, "t20", date(y, 3, 22), 3, y, rng, files, "ipl")
            else:
                _league("Big Bash League", teams, sides, "t20", date(y, 12, 4), 2, y, rng, files, "bbl", double=False)
        _tours(world, y, date(y, 2, 1), rng, files)
        _tours(world, y, date(y, 6, 10), rng, files)
        half = len(COUNTIES) // 2
        d1, d2 = COUNTIES[:half], COUNTIES[half:]
        cs = sides_of("England", COUNTIES)
        _league("County Championship", d1, cs, "multi", date(y, 4, 8), 5, y, rng, files, "county_-_d1", days=4,
                knockouts=False, title_extra=" - D1")
        _league("County Championship", d2, cs, "multi", date(y, 4, 8), 5, y, rng, files, "county_-_d2", days=4,
                knockouts=False, title_extra=" - D2")
        _league("T20 Blast", COUNTIES[:10], cs, "t20", date(y, 9, 1), 2, y, rng, files, "blast", double=False)
        _league("One-Day Cup", COUNTIES[:8], cs, "one", date(y, 8, 1), 2, y, rng, files, "1_day_cup", double=False)
        ind = sides_of("India", STATES)
        _league("Ranji Trophy", STATES, ind, "multi", date(y, 10, 1), 5, y, rng, files, "ranji", days=4)
        _league("Vijay Hazare Trophy", STATES, ind, "one", date(y, 9, 1), 2, y, rng, files, "vht", double=False)
        _league("Syed Mushtaq Ali Trophy", STATES, ind, "t20", date(y + 1, 1, 8), 2, y, rng, files, "smat", double=False)
        aus = sides_of("Australia", SHIELD)
        _league("Sheffield Shield", SHIELD, aus, "multi", date(y, 10, 2), 5, y, rng, files, "shield", days=4)
        _league("Marsh One-Day Cup", SHIELD, aus, "one", date(y, 9, 1), 2, y, rng, files, "marsh_cup")
    return files
