"""What the stats server remembers: the careers saved on this PC (each kept ready in memory until its file changes),
the one on screen, the teams you play as, the logos, and the watched Scorecards folders.

The same files and the same engine code as the current site (ccstats/local.py: CareerStore, CareerSettings,
Watcher), so the two sites can run side by side on the same careers."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from ccstats import fixtures as FX
from ccstats import local as L
from ccstats import logos as LG
from ccstats.loader import Career
from ccstats.local import CareerSettings, CareerStore, Watcher

from . import theme


class Site:
    def __init__(self, store: CareerStore | None = None):
        self.store = store or CareerStore()
        self.watcher = Watcher(self.store)
        self._lock = threading.RLock()
        self._careers: dict[str, tuple[tuple, Career]] = {}   # name -> (file signature, career)
        self._venues: dict[str, tuple[tuple, Career]] = {}    # name -> (schedule, career with its home / away)
        self._logos: tuple[tuple, LG.LogoBook] | None = None
        self.current_name: str | None = self.store.last_used()
        self.checked_at: float = 0.0

    # ------------------------------------------------------------------ careers
    def names(self) -> list[str]:
        return self.store.names()

    def _sig(self, name: str) -> tuple:
        f = self.store._dir(name) / "career.stats-pack.zip"
        st = f.stat()
        return st.st_mtime_ns, st.st_size

    def career(self, name: str | None = None) -> Career | None:
        """A saved career (the one on screen when no name is given), read again only when its file changes, with
        home and away taken from your schedule as the current site does. None when there is no such career."""
        name = self.current() if name is None else name
        if not name or name not in self.names():
            return None
        with self._lock:
            try:
                sig = self._sig(name)
            except OSError:
                return None
            hit = self._careers.get(name)
            if hit is None or hit[0] != sig:
                c, _ = self.store.load(name)
                c.count_fielding = False   # no fielding anywhere on the new site (14 November; ccstats.stats)
                self._careers[name] = (sig, c)
                self._venues.pop(name, None)
            c = self._careers[name][1]
            s = self.settings(name)
            fx = s.fixtures if s is not None else []
            if not fx:
                return c
            key = (json.dumps(fx, sort_keys=True, default=str), id(c))
            v = self._venues.get(name)
            if v is None or v[0] != key:
                try:
                    adj = FX.with_venues(c, FX.track(c, fx))
                except Exception:  # noqa: BLE001 - a schedule that can't be read must never stop the site
                    adj = c
                adj.count_fielding = False
                self._venues[name] = (key, adj)
            return self._venues[name][1]

    def current(self) -> str | None:
        """The career on screen: the one chosen here, or (none yet, or it was deleted) the one opened last on this PC."""
        if not self.current_name or self.current_name not in self.names():
            self.current_name = self.store.last_used()
        return self.current_name

    def settings(self, name: str | None = None) -> CareerSettings | None:
        name = name or self.current()
        if not name:
            return None
        try:
            return self.store.load_settings(name)[1]
        except (OSError, ValueError, TypeError):
            return None

    def select(self, name: str) -> None:
        """Put a career on screen, and remember it for next time (the current site opens on it too)."""
        if name not in self.names():
            raise KeyError(name)
        self.current_name = name
        L.write_atomic(self.store.root / "last.json", json.dumps({"career": name}))

    def forget(self, name: str) -> None:
        """Drop a career from memory (its file changed under us, e.g. after a sync)."""
        with self._lock:
            self._careers.pop(name, None)
            self._venues.pop(name, None)

    # ------------------------------------------------------------------ your teams
    def my_teams(self, career: Career | None = None, unplayed: bool = False) -> list[str]:
        """The teams you play as in this career: those with a match in it, or with `unplayed`, also the ones picked
        before their first match (exactly as the current site, ui/state.my_teams)."""
        career = career if career is not None else self.career()
        if career is None:
            return []
        s = self.settings(career.name)
        picked = s.my_teams if s is not None else []
        teams = set(career.matches.home) | set(career.matches.away)
        return [t for t in picked if unplayed or t in teams]

    def notes(self, career: Career | None = None) -> dict:
        """Your notes on matches, by scorecard file name (saved with the career on this PC)."""
        career = career if career is not None else self.career()
        s = self.settings(career.name) if career is not None else None
        return dict(s.notes) if s is not None else {}

    def set_note(self, source: str, text: str) -> str:
        """Save (or, empty, remove) your note on a match; the current site reads the same file."""
        name = self.current()
        if not name:
            raise KeyError("no career")
        with self._lock:
            _, s = self.store.load_settings(name, fresh=True)
            text = text.strip()
            if text:
                s.notes[source] = text
            else:
                s.notes.pop(source, None)
            self.store.save_settings(s)
        return text

    # ------------------------------------------------------------------ remembered picks
    REMEMBERED = ("section", "season", "team", "event")

    def remembered(self, career: Career | None = None) -> dict:
        """The section, season, team and competition you last picked on any page (the current site's "remembered",
        ui/state.py): every page opens on them when they're among its choices."""
        career = career if career is not None else self.career()
        s = self.settings(career.name) if career is not None else None
        r = dict(s.remembered) if s is not None else {}
        return {k: str(v) for k, v in r.items() if k in self.REMEMBERED and v is not None}

    def remember(self, kind: str, value: str) -> dict:
        """Keep a pick for every page, saved with the career on this PC (the current site reads the same file)."""
        if kind not in self.REMEMBERED:
            raise ValueError(kind)
        name = self.current()
        if not name:
            raise KeyError("no career")
        with self._lock:
            _, s = self.store.load_settings(name, fresh=True)
            r = dict(s.remembered or {})
            r[kind] = value
            s.remembered = r
            self.store.save_settings(s)
        return r

    def update_settings(self, change):
        """Change the career's saved settings in one step (read fresh, `change(settings)`, saved), so two changes at
        once never lose one another. Returns what `change` returns. The current site reads the same file."""
        name = self.current()
        if not name:
            raise KeyError("no career")
        with self._lock:
            _, s = self.store.load_settings(name, fresh=True)
            out = change(s)
            self.store.save_settings(s)
        return out

    def inbox_state(self, career: Career | None = None) -> dict:
        """Which inbox messages you have read and removed: {"read": set, "removed": set}."""
        career = career if career is not None else self.career()
        s = self.settings(career.name) if career is not None else None
        box = dict(s.inbox) if s is not None else {}
        return {"read": set(box.get("read", [])), "removed": set(box.get("removed", []))}

    def set_inbox(self, read: list[str], removed: list[str]) -> dict:
        """Mark messages read and remove messages (added to what's there); saved with the career on this PC."""
        name = self.current()
        if not name:
            raise KeyError("no career")
        with self._lock:
            _, s = self.store.load_settings(name, fresh=True)
            box = dict(s.inbox or {})
            for key, ids in (("read", read), ("removed", removed)):
                box[key] = sorted(set(box.get(key, [])) | {str(i) for i in ids})[-5000:]
            s.inbox = box
            self.store.save_settings(s)
        return {"read": set(box["read"]), "removed": set(box["removed"])}

    def theme(self, nation: str | None = "") -> dict:
        """The colours: a nation's when one is asked for (a preview), else your first national side's."""
        if nation:
            return theme.tokens(nation)
        return theme.for_teams(self.my_teams(unplayed=True))

    # ------------------------------------------------------------------ logos
    def logo_places(self) -> list[Path]:
        chosen = str(self.store.preferences().get("logos_folder") or "")
        folders = [s.folder for n in self.names() if (s := self.settings(n)) and s.folder]
        return LG.places(chosen, folders, self.store.root)

    def logos(self) -> LG.LogoBook:
        """Which picture goes with which name, matched again when a file or folder changes."""
        found = LG.find(self.logo_places())
        stamp = LG.stamp(found)
        with self._lock:
            if self._logos is None or self._logos[0] != stamp:
                self._logos = (stamp, LG.LogoBook(found))
            return self._logos[1]

    # ------------------------------------------------------------------ watching
    def sync(self) -> list[dict]:
        """Check every watched Scorecards folder once (and make the weekly backups), as the current site does every
        20 seconds. Returns what happened, for the browser: new matches (with any records they broke), files that
        couldn't be read."""
        from ccstats.records import new_records
        self.checked_at = time.time()
        try:
            self.store.backup_all_due()
        except OSError:
            pass  # a full or read-only disk must never stop the site; the next check tries again
        folders = sorted({s.folder for n in self.names() if (s := self.settings(n)) and s.folder})
        events: list[dict] = []
        for folder in folders:
            try:
                res = self.watcher.sync(folder)
            except Exception:  # noqa: BLE001 - a half-written file or a busy disk: the next check tries again
                continue
            if res is None:
                continue
            if res.added or res.refreshed:
                self.forget(res.career.name)
            if res.added:
                try:
                    records = new_records(res.career, res.added)[:5]
                except Exception:  # noqa: BLE001 - the records must never stop the news of new matches
                    records = []
                events.append(dict(type="matches", career=res.career.name, added=len(res.added), records=records))
            if res.failed:
                events.append(dict(type="failed", career=res.career.name,
                                   files=[dict(file=f, reason=why) for f, why in res.failed]))
        return events

    def folders(self) -> list[str]:
        return sorted({s.folder for n in self.names() if (s := self.settings(n)) and s.folder})
