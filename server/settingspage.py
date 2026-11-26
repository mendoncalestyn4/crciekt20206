"""Settings (stage 4): the tabs Careers, Your teams, Backups, Logos, Colours and Problems (your answer 8 of 26 November),
and the first start with no careers yet. The same files and the same engine code as the current site
(ccstats/local.py), so the two sites can run side by side.

Your answers: a career added four ways (a Scorecards folder by path or the Windows folder window, an uploaded folder,
.txt files or a .zip, a career file) and downloaded as a file; rename and remove a career, a backup made first; one
button that deletes every career and every backup on this PC, asked twice (the game's Scorecards folders are never
touched); "Which teams do you play as?" with all 235 of the game's teams; a weekly backup of every career, newest 8
kept, a copy before every Data check change and every update, each backup checked by reading it back, and a warning
instead of a backup when the disk is nearly full; the logos folder."""

from __future__ import annotations

import base64
import time
from pathlib import Path

from ccstats import catalogue as CAT
from ccstats import fixtures as FX
from ccstats.loader import Career
from ccstats.local import CareerSettings, default_scorecards_folder

DEMO_NAME = "Demo IPL (made-up results)"
TABS = ["Careers", "Your teams", "Backups", "Logos", "Colours", "Problems"]
SCORECARDS_HELP = ("In Cricket Captain 2026, turn on **Autosave scorecards** in Options. The folder is normally "
                   "`AppData\\Roaming\\Childish Things\\Cricket Captain 2026\\Scorecards`")


class Refused(ValueError):
    """A change that can't be made, with the reason in plain words."""


def _when(t: float) -> str:
    return time.strftime("%a %d %b %Y, %H:%M", time.localtime(t)) if t else ""


# --------------------------------------------------------------------------- the page
def page(site) -> dict:
    store = site.store
    names = site.names()
    current = site.current()
    detected = default_scorecards_folder()
    out: dict = dict(tabs=TABS, first=not names, current=current or "",
                     scorecards_help=SCORECARDS_HELP + (" and it was found on this PC." if detected else "."),
                     detected="" if detected is None or site.watcher.owner(str(detected)) else str(detected),
                     browse=_can_browse())
    rows = []
    for n in names:
        s = site.settings(n)
        f = store._dir(n) / "career.stats-pack.zip"
        b = store.backups(n)
        rows.append(dict(name=n, folder=s.folder if s else "", updated=_when(s.updated) if s else "",
                         size=f"{f.stat().st_size / 1e6:,.1f} MB" if f.is_file() else "", current=n == current,
                         backups=len(b), last_backup=_when(b[0][1]) if b else ""))
    out["careers"] = rows
    c = site.career() if current else None
    if c is not None:
        m = c.matches
        out["career"] = dict(name=c.name, matches=int(len(m)),
                             span=(f"{m.date.min():%d %b %Y} to {m.date.max():%d %b %Y}" if len(m) else ""),
                             empty="" if len(m) else ("**No matches in this career yet.** Play a match in Cricket Captain (with "
                                                      "*Autosave scorecards* on in Options) and this page fills in within "
                                                      "a second or two. Meanwhile you can add your schedule on the **Fixtures** page."))
        s = site.settings(c.name)
        picked = list(s.my_teams) if s else []
        out["teams"] = dict(picked=picked, choices=team_choices(c), asked=bool(s.teams_asked) if s else True,
                            ask=bool(s is not None and not s.my_teams and not s.teams_asked),
                            last=[t for t in store.preferences().get("last_teams", []) if t in set(team_choices(c))])
        ok, free, need = store.room_for_backup(c.name)
        out["backups"] = dict(
            items=[dict(file=p.name, when=_when(made), before_restore="before-restore" in p.name,
                        note=("made just before a restore" if "before-restore" in p.name else
                              "made before a Data check change" if "before-data-check" in p.name else
                              "made before an update" if "before-update" in p.name else
                              "made before removing" if "before-remove" in p.name else ""))
                   for p, made in store.backups(c.name)],
            kept=store.BACKUPS_KEPT, where=str(store.root / "backups"), total=store.all_backups(),
            room=ok, free=f"{free / 1e6:,.0f} MB" if free >= 0 else "", need=f"{need / 1e6:,.0f} MB")
    b = site.logos()
    n_teams, n_comps = b.counts()
    where = b.found.get("emblems") or b.found.get("complogos")
    out["logos"] = dict(teams=n_teams, comps=n_comps, where=str(where.parent) if where else "",
                        chosen=str(store.preferences().get("logos_folder") or ""))
    return out


def team_choices(career) -> list[str]:
    """Every team you could play as: the 31 national sides first, then every other team in the game (all 235, with
    those that have played in this career), A to Z."""
    played = set(career.matches.home) | set(career.matches.away) if career is not None else set()
    every = set(CAT.every_team()) | played
    nations = sorted(t for t in every if t in FX.NATIONS)
    return nations + sorted(t for t in every if t not in FX.NATIONS)


def _can_browse() -> bool:
    import sys
    return sys.platform.startswith("win")


def choose_folder(start: str = "") -> str | None:
    """The normal Windows 'choose folder' window, on this PC (the site and the browser are on the same computer)."""
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception:  # noqa: BLE001
        return None
    try:
        root = tk.Tk()
        root.withdraw()
        root.wm_attributes("-topmost", 1)
        path = filedialog.askdirectory(initialdir=start or None, title="Choose your Cricket Captain Scorecards folder")
        root.destroy()
    except Exception:  # noqa: BLE001
        return None
    return path or None


# --------------------------------------------------------------------------- changes
def report(career) -> dict:
    """What reading the scorecards did (the current site's "Finished:" line, and the files that couldn't be read)."""
    words = {"loaded": "loaded", "duplicate": "duplicates skipped", "failed": "could not be read", "skipped": "not scorecards"}
    counts: dict = {}
    for r in career.report:
        counts[r.status] = counts.get(r.status, 0) + 1
    return dict(line="Finished: " + ", ".join(f"{v} {words.get(k, k)}" for k, v in counts.items()) + "." if counts else "",
                failed=[dict(file=r.source, reason=r.message) for r in career.report if r.status == "failed"])


def add_folder(site, name: str, folder: str) -> dict:
    name, folder = name.strip(), folder.strip()
    if not folder:
        raise Refused("Paste the folder path, or use Browse….")
    if not Path(folder).is_dir():
        raise Refused("That folder doesn't exist on this PC. Check the path or use Browse….")
    owner = site.watcher.owner(folder)
    if owner:
        raise Refused(f"This folder is already used by **{owner}**. One Scorecards folder is one career, so both saves' "
                      "matches go there. Pick a different folder for a separate career.")
    if not name:
        raise Refused("Give the career a name.")
    if name in site.names():
        raise Refused("A career with that name already exists. Pick another name.")
    res = site.watcher.create(name, Path(folder))
    site.select(name)
    return dict(name=name, **report(res.career))


def save_new(site, career: Career, name: str) -> dict:
    """A career made from uploaded files, a career file or the demo league, saved on this PC under its name."""
    name = name.strip()
    if not name:
        raise Refused("Give the career a name.")
    if name in site.names():
        raise Refused("A career with that name already exists. Pick another name.")
    career.name = name
    site.store.save(career, CareerSettings(name=name))
    site.select(name)
    return dict(name=name, **report(career))


def demo(site) -> dict:
    from ccstats.demo_league import generate
    if DEMO_NAME in site.names():
        site.select(DEMO_NAME)
        return dict(name=DEMO_NAME, line="", failed=[])
    c = Career.build(DEMO_NAME, [(n, t.encode() if isinstance(t, str) else t) for n, t in generate()])
    return save_new(site, c, DEMO_NAME)


def from_upload(site, files: list[tuple[str, bytes]], mode: str, name: str) -> dict:
    """Uploaded scorecards (.txt files, a .zip of them, a whole folder) or a career file: a new career, or added to
    the career on screen (mode "add")."""
    if not files:
        raise Refused("Pick some files first.")
    packs = [d for n, d in files if n.lower().endswith(".zip") and Career.is_pack(d)]
    if packs:
        if len(files) > 1:
            raise Refused("Open one career file at a time.")
        return save_new(site, Career.from_pack(packs[0]), name)
    if mode == "add":
        cur = site.current()
        if not cur:
            raise Refused("No career is open to add them to.")
        career, settings = site.store.load(cur)
        career = career.add_files(files)
        site.store.save(career, settings)
        site.forget(cur)
        return dict(name=cur, **report(career))
    return save_new(site, Career.build(name.strip() or "Uploaded career", files), name)


def decode(files: list[dict]) -> list[tuple[str, bytes]]:
    out = []
    for f in files:
        try:
            out.append((Path(str(f.get("name", ""))).name, base64.b64decode(str(f.get("data", "")), validate=True)))
        except Exception:  # noqa: BLE001 - a file that didn't come through is said so, not guessed at
            raise Refused(f"{f.get('name', 'A file')} didn't upload properly: try again.") from None
    return out
