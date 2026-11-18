"""Problems the site noticed while you used it, kept on this PC so you can send them to be fixed: a part of a page that
couldn't be worked out, a request the server couldn't answer, a page that crashed in the browser. Each is kept once
(with how many times it happened, and when first and last), newest first, up to LIMIT; Settings shows them, with a
plain report to copy. Scorecards the folder check couldn't read are noted here too (a career keeps only the
matches it could read, so they'd be lost otherwise)."""

from __future__ import annotations

import contextvars
import json
import os
import sys
import threading
import time
import traceback
from pathlib import Path

LIMIT = 300          # the most kept; the oldest go first
LOG_MAX = 1_000_000  # the server log's size before it's moved to server.log.1 (so it never fills the disk)
TEXT = 2000          # the longest any one piece of text is kept
FAILED = "Couldn't be worked out"

# the page being answered and the list to note problems on, set for each request (see Watch in app.py)
REQUEST: contextvars.ContextVar = contextvars.ContextVar("request", default=None)


def clip(v, n: int = TEXT) -> str:
    s = v if isinstance(v, str) else str(v)
    return s if len(s) <= n else s[: n - 1] + "…"


class Problems:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.log_path = self.path.with_name("server.log")   # the server's error log, beside the careers
        self._lock = threading.Lock()
        self._items = self._read()

    def _read(self) -> list[dict]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return [x for x in data if isinstance(x, dict) and "id" in x] if isinstance(data, list) else []
        except (OSError, ValueError):
            return []

    def _write(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self._items, ensure_ascii=False, indent=1), encoding="utf-8")
            os.replace(tmp, self.path)
        except OSError:
            pass   # the list still works for this session; it just isn't saved

    def add(self, kind: str, where: str, what: str, detail: str = "", career: str = "") -> dict:
        """Note a problem; the same one again (same kind, page and message) counts up instead of being listed twice."""
        kind, where, what, detail, career = clip(kind, 20), clip(where, 500), clip(what), clip(detail, 6000), clip(career, 200)
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        with self._lock:
            for x in self._items:
                if (x["kind"], x["where"], x["what"]) == (kind, where, what):
                    x.update(count=x["count"] + 1, last=now, detail=detail or x["detail"], career=career or x["career"])
                    self._items.remove(x)
                    self._items.insert(0, x)
                    break
            else:
                x = dict(id=f"{time.time_ns():x}", kind=kind, where=where, what=what, detail=detail, career=career,
                         first=now, last=now, count=1)
                self._items.insert(0, x)
                del self._items[LIMIT:]
            self._write()
            self._log(now, kind, where, what, detail, career)
            return dict(x)

    def _log(self, now: str, kind: str, where: str, what: str, detail: str, career: str) -> None:
        """Every problem also goes to the server's log as it happens (the console and server.log beside the careers),
        so a check after a run can read it (the fix round: "the server writes its errors to its log")."""
        line = f"{now} ERROR {kind} | {where} | {what}" + (f" | career: {career}" if career else "")
        text = line + ("\n    " + detail.replace("\n", "\n    ") if detail else "") + "\n"
        try:
            print(line, file=sys.stderr, flush=True)
        except (OSError, ValueError):
            pass
        try:
            if self.log_path.exists() and self.log_path.stat().st_size > LOG_MAX:
                os.replace(self.log_path, self.log_path.with_name("server.log.1"))
            with self.log_path.open("a", encoding="utf-8") as fh:
                fh.write(text)
        except OSError:
            pass   # the problems list still has it

    def items(self) -> list[dict]:
        with self._lock:
            return [dict(x) for x in self._items]

    def clear(self, ids: list[str] | None = None) -> None:
        with self._lock:
            self._items = [x for x in self._items if ids is not None and x["id"] not in set(ids)]
            self._write()

    def note_failed_parts(self, data, where: str, career: str = "") -> None:
        """Every part of an answer that couldn't be worked out ('missing' parts saying so), noted against the page."""
        for part, why in failed_parts(data):
            self.add("part", where, f"{part}: {why}", career=career)

    def note_crash(self, where: str, exc: BaseException, career: str = "") -> None:
        parts = traceback.format_exception(type(exc), exc, exc.__traceback__)
        tb = "".join(parts if len(parts) <= 13 else parts[:1] + parts[-12:])   # the heading and the last steps
        self.add("server", where, f"{type(exc).__name__}: {exc}", detail=tb, career=career)


def failed_parts(v, where: str = "") -> list[tuple[str, str]]:
    """(part, why) for each part of an answer that says it couldn't be worked out."""
    out = []
    if isinstance(v, dict):
        for k, x in v.items():
            if k == "missing" and isinstance(x, dict):
                out += [((f"{where}." if where else "") + str(a), str(b)) for a, b in x.items() if FAILED in str(b)]
            else:
                out += failed_parts(x, f"{where}.{k}" if where else str(k))
    elif isinstance(v, list):
        for i, x in enumerate(v):
            out += failed_parts(x, f"{where}[{i}]")
    elif isinstance(v, str) and v.startswith(FAILED):
        out.append((where or "page", v))
    return out


def report(items: list[dict], version: str = "") -> str:
    """The plain report to copy and send: every problem with its page (or scorecard), when, how often, and the
    details."""
    lines = [f"Stats Pack: problems the site noticed ({len(items)})" + (f", site version {version}" if version else ""), ""]
    for x in items:
        lines.append(f"- [{x['kind']}] {x['what']}")
        lines.append(f"  {'file' if x['kind'] == 'scorecard' else 'page'}: {x['where']}"
                     + (f" · career: {x['career']}" if x.get("career") else ""))
        lines.append(f"  seen {x['count']} time{'s' if x['count'] != 1 else ''}, first {x['first']}, last {x['last']}")
        if x.get("detail"):
            lines += ["  details:"] + [f"    {d}" for d in x["detail"].strip().splitlines()[-14:]]
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
