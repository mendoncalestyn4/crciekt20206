"""Team emblems and competition logos, from your Cricket Captain editor files.

The game keeps its picture edits in two text files and two folders::

    editemblems.txt    Sydney Green              ; sydneygreenem        a team, and its PNG in editor\\emblems
    editcomplogos.txt  India : 20 Over League    ; india20overleaguecl  a competition, and its PNG in editor\\complogos

A line can also point at another team's (or competition's) name, to borrow its picture.  The site reads the same
files, looked for where the game keeps them (the game's folder above the Scorecards folder, the Scorecards folder,
the Steam install folder) or in a folder you choose, and matches each picture to the name the site shows: the
game's name or the real one ("Sydney Green" is shown as "Sydney Thunder").  Without the text files, a picture named
the game's way ("sydneygreenem.png", "india20overleaguecl.png") or after the team ("Sydney Thunder.png") is used.

On the dark pages the IPL, Hundred, Big Bash and international logos are drawn in a look picked for each against
the original (STYLES, below; see ccstats/logo_look.py); every other logo is shown as it is."""

from __future__ import annotations

import base64
import re
from functools import lru_cache
from pathlib import Path

from . import names as NM

EMBLEM_DIRS = ("editor/emblems", "emblems", "Editor/Emblems")
COMP_DIRS = ("editor/complogos", "complogos", "Editor/CompLogos")

# the game's international competitions -> the names the site uses for them
INTERNATIONAL = {
    "test match": ["Tests", "Tests (bilateral series)", "World Test Championship Final", "Test"],
    "one day international": ["ODIs", "ODIs (bilateral series)", "ODI"],
    "20 over international": ["T20Is", "T20Is (bilateral series)", "T20I"],
    "world cup": ["ODI World Cup"],
    "world cup 20 over": ["T20 World Cup"],
    "champions trophy": ["Champions Trophy"],
    "asia cup": ["Asia Cup"],
    "asia cup 20 over": ["Asia Cup (T20)"],
}


def key(name: str) -> str:
    """'Trinidad & Tobago CC' -> 'trinidadandtobagocc': how the game names its pictures."""
    return re.sub(r"[^a-z0-9]", "", str(name).lower().replace("&", "and"))


def parse(text: str) -> list[tuple[str, str]]:
    """(name, reference) for each line with a ' ; ' in an editemblems / editcomplogos file."""
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ";" not in line:
            continue
        name, ref = (x.strip() for x in line.split(";", 1))
        if name and ref:
            out.append((name, ref))
    return out


def _decode(raw: bytes) -> str:
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def places(chosen, scorecards_folders, home) -> list[Path]:
    """Where to look for the editor files, in order: the folder you chose, the game's folder above each Scorecards
    folder you watch (and the Scorecards folder), the Steam install folder, and a 'logos' folder in the Stats Pack's
    own folder (home)."""
    from .local import game_install_folders
    out: list[Path] = [Path(chosen)] if chosen else []
    for f in scorecards_folders:
        if f:
            out += [Path(f).parent, Path(f)]
    out += game_install_folders()
    out.append(Path(home) / "logos")
    return list(dict.fromkeys(out))


def stamp(found: dict) -> tuple:
    """What was found and when each file last changed: the logos are matched again whenever this changes."""
    out = []
    for k in sorted(found):
        try:
            out.append((k, str(found[k]), Path(found[k]).stat().st_mtime_ns))
        except OSError:
            out.append((k, str(found[k]), 0))
    return tuple(out)


def look_on(style: str, dark: bool) -> str:
    """How a logo with this look is drawn on a page: in its look on a dark page; on a light page as it is, apart from
    the white the game shows inside some ('inside', 'whole'). The looks that make dark parts show up on a dark page
    would only fade them on a light one."""
    return style if dark or style in ("inside", "whole") else "plain"


def find(places) -> dict:
    """The editor files in the first of these folders that has them: {"emblems": dir, "complogos": dir,
    "emblem_list": file, "comp_list": file} (each only when found)."""
    found: dict = {}
    for base in places:
        if not base:
            continue
        base = Path(base)
        try:
            if not base.is_dir():
                continue
            for k, subs in (("emblems", EMBLEM_DIRS), ("complogos", COMP_DIRS)):
                for sub in subs:
                    d = base / sub
                    if k not in found and d.is_dir():
                        found[k] = d
            for k, pat in (("emblem_list", "*emblem*.txt"), ("comp_list", "*complogo*.txt")):
                if k in found:
                    continue
                for d in (base, base / "editor", base / "Editor"):
                    hits = sorted(d.glob(pat)) if d.is_dir() else []
                    if hits:
                        found[k] = hits[0]
                        break
        except OSError:  # a folder that can't be looked in
            continue
    return found


class LogoBook:
    """Which picture goes with which team and competition name."""

    def __init__(self, found: dict):
        self.found = found
        self.teams: dict[str, Path] = {}
        self.comps: dict[str, Path] = {}
        self.styles: dict[str, str] = {}
        self._build()
        self._fix_swaps()
        for name, look in STYLES.items():
            p = self.team(name) or self.comp(name)
            if p is not None:
                self.styles.setdefault(str(p), look)

    # pictures in a folder, by their name the game's way ('sydneygreenem')
    @staticmethod
    def _pictures(d) -> dict[str, Path]:
        if not d:
            return {}
        try:
            return {key(p.stem): p for p in Path(d).iterdir() if p.suffix.lower() == ".png" and p.is_file()}
        except OSError:
            return {}

    def _build(self) -> None:
        pics = self._pictures(self.found.get("emblems"))
        real_of = {}
        for country, game, real in NM.TEAMS:
            real_of.setdefault(game, real)
        listed = []
        if self.found.get("emblem_list"):
            try:
                listed = parse(_decode(Path(self.found["emblem_list"]).read_bytes()))
            except OSError:
                listed = []
        ref_of = {game: ref for game, ref in listed}
        names = list(dict.fromkeys(list(ref_of) + [g for _, g, _ in NM.TEAMS]))
        game_keys = {key(g) for g in names}

        def picture(game: str, depth: int = 0):
            ref = ref_of.get(game)
            if ref:
                if key(ref) in pics:
                    return pics[key(ref)]
                if ref in ref_of and depth < 3 and ref != game:  # borrowing another team's emblem
                    return picture(ref, depth + 1)
            tries = [key(game) + "em", key(game)]
            real = key(real_of.get(game, ""))
            if real and (real == key(game) or real not in game_keys):  # pictures are named the game's way, so a
                tries += [real + "em", real]  # printed name that is another team's game name is that team's file
            for k in tries:
                if k in pics:
                    return pics[k]
            return None
        # The names the scorecards print, which the site shows, come first: a game's name can be another team's
        # printed name ('Delhi' is the game's name for the IPL side, printed 'Delhi Capitals', and the printed name
        # of the Ranji side, 'Delhi CC' in the game), and must always mean the team printed with it.
        printed = {key(r) for _, _, r in NM.TEAMS}
        found = {game: picture(game) for game in names}
        for game, p in found.items():
            if p is not None and key(game) not in printed:
                self.teams[key(game)] = p
        for game, p in found.items():
            if p is not None and real_of.get(game):
                self.teams[key(real_of[game])] = p
        # competitions: "Country : the game's name" -> the names the site shows
        cpics = self._pictures(self.found.get("complogos"))
        clisted = []
        if self.found.get("comp_list"):
            try:
                clisted = parse(_decode(Path(self.found["comp_list"]).read_bytes()))
            except OSError:
                clisted = []
        cref = {}
        for name, ref in clisted:
            if ":" in name:
                country, comp = (x.strip() for x in name.split(":", 1))
                cref[(country, comp)] = ref
        from .competitions import KNOWN, SHARED
        pairs = [(c, g, r) for c, g, r in NM.COMPETITIONS] + [("International", g, g) for g in
                                                              ("Test Match", "One Day International",
                                                               "20 Over International", "World Cup",
                                                               "World Cup 20 Over", "Champions Trophy", "Asia Cup",
                                                               "Asia Cup 20 Over")]
        for country, game, printed in pairs:
            ref = cref.get((country, game))
            p = cpics.get(key(ref)) if ref else None
            if p is None:
                p = cpics.get(key(country + game) + "cl") or cpics.get(key(country + game))
            if p is None:
                continue
            shown = set()
            if country == "International":
                shown.update(INTERNATIONAL.get(game.lower(), []))
            else:
                k = printed.lower()
                if k in KNOWN:
                    shown.add(KNOWN[k][0])
                if k in SHARED and country in SHARED[k]:
                    shown.add(SHARED[k][country][0])
                else:  # a name two countries print ('National T20 Cup') is shown with the country, never bare
                    shown.add(printed)
            for s in shown:
                self.comps.setdefault(key(s), p)

    def _fix_swaps(self) -> None:
        for one, two, real_one, real_two in SWAPPED:
            p1, p2 = self.team(one), self.team(two)
            if p1 and p2 and _md5(p1) == real_two and _md5(p2) == real_one:  # each has the other's picture
                for k in self._names_of(one):
                    if self.teams.get(k) == p1:
                        self.teams[k] = p2
                for k in self._names_of(two):
                    if self.teams.get(k) == p2:
                        self.teams[k] = p1

    @staticmethod
    def _names_of(name: str) -> set[str]:
        out = {key(name)}
        for _, game, real in NM.TEAMS:
            if real == name or game == name:
                out |= {key(game), key(real)}
        return out

    def style(self, path) -> str:
        """How the logo at this path is drawn (its look, picked for its team or competition), or 'plain'."""
        return self.styles.get(str(path), "plain") if path else "plain"

    def team(self, name: str):
        return self.teams.get(key(name))

    def comp(self, name: str):
        """A competition's logo by the name the site shows: an event ('Indian Premier League'), a section
        ('County Championship · Division 1') or a format section ('ODIs')."""
        n = str(name)
        for cand in (n, n.split(" · ")[0], re.sub(r"\s*\(.*\)$", "", n)):
            p = self.comps.get(key(cand))
            if p is not None:
                return p
        return None

    def counts(self) -> tuple[int, int]:
        """(teams with a picture, competitions with one), counting each picture once per name the game uses."""
        game_names = {key(g) for _, g, _ in NM.TEAMS}
        return len([k for k in self.teams if k in game_names]), len({str(p) for p in self.comps.values()})


# How each logo is drawn on the dark pages (see ccstats/logo_look.py), picked one by one against the original for the
# IPL, the Hundred, the Big Bash and internationals. Every other logo is shown as it is.
STYLES: dict[str, str] = {
    **dict.fromkeys(("Delhi Capitals", "Gujarat Titans", "Kolkata Knight Riders", "Lucknow Super Giants", "Punjab Kings",
                     "Sunrisers Hyderabad", "SunRisers Leeds", "Sydney Thunder", "Bangladesh", "Pakistan",
                     "South Africa"), "inside"),
    "Chennai Super Kings": "whole",
    "Mumbai Indians": "line",
    **dict.fromkeys(("London Spirit", "Southern Brave", "Melbourne Renegades", "Tests", "ODI World Cup", "T20 World Cup",
                     "Bermuda", "Canada", "Denmark", "Hong Kong", "Nepal", "Papua New Guinea", "Scotland", "UAE",
                     "Uganda", "England"), "C"),   # England's navy badge vanishes on the dark blue: a light tint of its own colours
    **dict.fromkeys(("Champions Trophy", "Asia Cup", "Asia Cup (T20)"), "D"),
}

# Pictures known to be saved under each other's names in the game's files: (team, team, MD5 of the picture that is
# really the first team's, MD5 of the one that is really the second's). When each team's picture is the other's,
# they are swapped back; once the files are put right, nothing changes.
SWAPPED = [("Pamir Legends", "Maiwand Champions", "7c1e859ec9d4fc139500b10c231db7a2", "44f1764c00dff695aad4bbd192e982fc")]


def _md5(path) -> str:
    import hashlib
    try:
        return hashlib.md5(Path(path).read_bytes()).hexdigest()
    except OSError:
        return ""


@lru_cache(maxsize=4096)
def _badge(path: str, mtime: int, size: int, style: str) -> tuple[str, int]:
    """(a PNG data URI, how big to show the picture in pixels): the logo size pixels across its longest side, drawn
    in its look, in a square frame that is the same for every logo of that size (so logos line up)."""
    from . import logo_look
    return logo_look.draw(path, mtime, size, style if style in logo_look.STYLES else "plain")


def badge(path, size: int = 28, style: str = "plain") -> str:
    """A data URI for the logo at this path (the logo size pixels across), or '' if it can't be read."""
    return picture(path, size, style)[0]


def png(path, size: int = 28, style: str = "plain") -> bytes:
    """The logo at this path as a PNG file (drawn exactly as badge draws it, twice the size for sharp edges), or b''
    if it can't be read. The new site's stats server sends these."""
    uri = badge(path, size, style)
    return base64.b64decode(uri.split(",", 1)[1]) if uri else b""


def picture(path, size: int = 28, style: str = "plain") -> tuple[str, int]:
    """(data URI, the pixels to show it at) for the logo at this path, or ('', 0)."""
    if not path:
        return "", 0
    try:
        p = Path(path)
        return _badge(str(p), p.stat().st_mtime_ns, int(size), str(style))
    except Exception:  # noqa: BLE001 - a picture that can't be read is simply not shown
        return "", 0
