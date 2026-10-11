"""Team emblems and competition logos, from your Cricket Captain editor files.

The game keeps its picture edits in two text files and two folders::

    editemblems.txt    Sydney Green              ; sydneygreenem        a team, and its PNG in editor\\emblems
    editcomplogos.txt  India : 20 Over League    ; india20overleaguecl  a competition, and its PNG in editor\\complogos

A line can also point at another team's (or competition's) name, to borrow its picture.  The site reads the same
files, looked for where the game keeps them (the game's folder above the Scorecards folder, the Scorecards folder,
the Steam install folder) or in a folder you choose, and matches each picture to the name the site shows: the
game's name or the real one ("Sydney Green" is shown as "Sydney Thunder").  Without the text files, a picture named
the game's way ("sydneygreenem.png", "india20overleaguecl.png") or after the team ("Sydney Thunder.png") is used.

Pictures are drawn small: a logo that is mostly dark sits on a light coin so it shows on the dark pages; a bright
one is shown as it is."""

from __future__ import annotations

import base64
import io
import re
from functools import lru_cache
from pathlib import Path

from . import names as NM

EMBLEM_DIRS = ("editor/emblems", "emblems", "Editor/Emblems")
COMP_DIRS = ("editor/complogos", "complogos", "Editor/CompLogos")
DARK = 95  # average brightness (0-255) of a logo's visible pixels below which it gets a light coin

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
        self._build()

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

        def picture(game: str, depth: int = 0):
            ref = ref_of.get(game)
            if ref:
                if key(ref) in pics:
                    return pics[key(ref)]
                if ref in ref_of and depth < 3 and ref != game:  # borrowing another team's emblem
                    return picture(ref, depth + 1)
            for k in (key(game) + "em", key(game), key(real_of.get(game, "")) + "em", key(real_of.get(game, ""))):
                if k and k in pics:
                    return pics[k]
            return None
        for game in names:
            p = picture(game)
            if p is not None:
                self.teams[key(game)] = p
                if real_of.get(game):
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
                shown.add(printed)
            for s in shown:
                self.comps.setdefault(key(s), p)

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


COIN = 1.42  # room a dark logo's coin may take, as a share of the logo's size (a square logo's corners need 1.42)
HOLE = 0.015  # a see-through area enclosed by the logo, at least this share of it, counts as a see-through middle


def has_holes(im) -> bool:
    """Whether the logo has a see-through middle: an area inside it (the middle of a shield, a ring, a flower) that
    the designer left see-through, so in the game it shows white. Such a logo goes on the light coin, so the middle
    shows white here too, without changing anything in the logo itself. Small gaps (inside an 'O') don't count."""
    import numpy as np
    from PIL import Image, ImageDraw
    w, h = im.size
    mask = im.getchannel("A").point(lambda v: 255 if v < 128 else 0)  # see-through pixels
    px = mask.load()
    for x in range(w):  # everything see-through that reaches the edge is outside the logo
        for y in (0, h - 1):
            if px[x, y] == 255:
                ImageDraw.floodfill(mask, (x, y), 128)
    for y in range(h):
        for x in (0, w - 1):
            if px[x, y] == 255:
                ImageDraw.floodfill(mask, (x, y), 128)
    arr = np.array(mask)
    if not (arr == 255).any():
        return False
    need = HOLE * max(int((np.array(im.getchannel("A")) >= 128).sum()), 1)
    for y, x in zip(*np.nonzero(arr == 255)):  # each enclosed area in turn
        if arr[y, x] != 255:
            continue
        ImageDraw.floodfill(mask, (int(x), int(y)), 64)
        arr = np.array(mask)
        if (arr == 64).sum() >= need:
            return True
        arr[arr == 64] = 0
        mask = Image.fromarray(arr)
    return False


@lru_cache(maxsize=2048)
def _badge(path: str, mtime: int, size: int, pad: bool) -> tuple[str, bool, int]:
    """(a PNG data URI, whether the logo sits on a light coin, how big to show the picture in pixels).

    The logo itself is always drawn size pixels across, with or without a coin: a dark logo keeps its size and the
    coin is drawn round it (just big enough for the logo's visible part), so its picture is a little bigger. With
    pad, every picture gets that bigger frame (bright logos on a see-through one), so a table's column shows all
    the logos the same size."""
    import numpy as np
    from PIL import Image, ImageDraw, ImageStat
    im = Image.open(path).convert("RGBA")
    box = im.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    if box:
        im = im.crop(box)
    a = im.getchannel("A").point(lambda v: 255 if v > 40 else 0)
    stat = ImageStat.Stat(im.convert("L"), mask=a)
    dark = (bool(stat.count[0]) and stat.mean[0] < DARK) or has_holes(im)  # on the light coin
    s2 = size * 2  # drawn at twice the size, so it stays sharp on a high-resolution screen
    k = s2 / max(im.width, im.height)  # fitted to the size, bigger or smaller
    im = im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.LANCZOS)
    full = int(round(s2 * COIN)) if (dark or pad) else s2
    canvas = Image.new("RGBA", (full, full), (0, 0, 0, 0))
    if dark:  # the smallest circle round the logo's visible pixels, with a little room
        ys, xs = np.nonzero(np.array(im.getchannel("A")) > 40)
        r = float(np.sqrt((xs + 0.5 - im.width / 2) ** 2 + (ys + 0.5 - im.height / 2) ** 2).max()) * 1.05 + 3 \
            if len(xs) else full / 2
        r = min(r, full / 2 - 1)
        c = full / 2
        ImageDraw.Draw(canvas).ellipse([c - r, c - r, c + r, c + r], fill=(233, 238, 247, 255))
    canvas.alpha_composite(im, ((full - im.width) // 2, (full - im.height) // 2))
    buf = io.BytesIO()
    canvas.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode(), dark, full // 2


def badge(path, size: int = 28, pad: bool = True) -> str:
    """A data URI for the logo at this path (the logo size pixels across), or '' if it can't be read."""
    return picture(path, size, pad)[0]


def picture(path, size: int = 28, pad: bool = False) -> tuple[str, int]:
    """(data URI, the pixels to show it at) for the logo at this path, or ('', 0)."""
    if not path:
        return "", 0
    try:
        p = Path(path)
        uri, _, px = _badge(str(p), p.stat().st_mtime_ns, int(size), bool(pad))
        return uri, px
    except Exception:  # noqa: BLE001 - a picture that can't be read is simply not shown
        return "", 0
