"""The stats server: answers the new website's questions from the engine, sends the logos, tells the browser when new
matches arrive, and serves the website itself (web/dist).

Only your own computer can reach it: it listens on 127.0.0.1, answers only to the names 127.0.0.1 and localhost (so
a web page elsewhere can't reach it by renaming itself), and changes are only accepted as JSON (which another site
can't send without asking first)."""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import time
from collections import deque
from pathlib import Path

import anyio
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, HTMLResponse, JSONResponse, Response, StreamingResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from ccstats import depth as DP
from ccstats import keep as KEEP
from ccstats import logos as LG
from ccstats import search as SR
from ccstats.colours import TEAM_COLOURS
from ccstats.local import CareerStore
from ccstats.competitions import ordered as in_order

from . import analyticspage, comppage, storiespage, insightspage, leaderspage, matchpage, myteam, plannerpage, playerpage, previewpage, reviewpage, rivalriespage, seasonpage, styleguide, teampage, tvtpage
from .cache import _stamp as cache_stamp, kept, put as cache_put, save as save_kept
from . import warmers
from .site import Site
from .problems import REQUEST, Problems, report as problems_report

WEB = Path(__file__).resolve().parent.parent / "web" / "dist"
HOSTS = ["127.0.0.1", "localhost"]
LOGO_SIZES = range(12, 241)   # pixels across; anything else is refused


class Hub:
    """What happened (new matches, files that couldn't be read, each check of the folders), for every open page. The
    last few are kept, so a page that lost its connection for a moment catches up when it's back."""

    def __init__(self, keep: int = 50):
        self.last_id = 0
        self.recent: deque[tuple[int, dict]] = deque(maxlen=keep)
        self._queues: set[asyncio.Queue] = set()

    def publish(self, event: dict) -> int:
        self.last_id += 1
        self.recent.append((self.last_id, event))
        for q in list(self._queues):
            q.put_nowait((self.last_id, event))
        return self.last_id

    def subscribe(self, after: int | None) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        if after is not None:
            for i, e in self.recent:
                if i > after:
                    q.put_nowait((i, e))
        self._queues.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._queues.discard(q)


def _json(data, status: int = 200) -> JSONResponse:
    req = REQUEST.get()
    if req is not None and status == 200:
        where, problems, site = req
        try:
            problems.note_failed_parts(data, where, site.current() or "")
        except Exception:  # noqa: BLE001 - noting a problem must never become one
            pass
    return JSONResponse(data, status_code=status, headers={"Cache-Control": "no-store"})


ASKING = [0]   # pages being answered for you, or new matches being taken in, right now (the warm-up waits meanwhile)
QUIET = {"/api/events", "/api/warmup", "/api/health", "/api/problems"}   # asked all the time: never a reason to wait


class Watch:
    """For each request: which page is being answered and where to note its problems (read by _json)."""

    def __init__(self, app, problems: Problems, site):
        self.app, self.problems, self.site = app, problems, site

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        qs = scope.get("query_string", b"").decode("latin-1")
        token = REQUEST.set((scope.get("path", "") + (f"?{qs}" if qs else ""), self.problems, self.site))
        mine = scope.get("path", "").startswith("/api/") and not scope.get("warm") and scope["path"] not in QUIET
        if mine:
            ASKING[0] += 1
        try:
            await self.app(scope, receive, send)
        finally:
            REQUEST.reset(token)
            if mine:
                ASKING[0] -= 1


class Squeeze:
    """Answers sent squeezed (gzip), so big pages arrive sooner; never the live news stream, which must flow at once."""

    def __init__(self, app):
        self.app, self.gz = app, GZipMiddleware(app, minimum_size=1024)

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope.get("path") != "/api/events":
            return await self.gz(scope, receive, send)
        return await self.app(scope, receive, send)


def _error(message: str, status: int) -> JSONResponse:
    return _json({"error": message}, status)


async def _body(request: Request) -> dict:
    if not request.headers.get("content-type", "").startswith("application/json"):
        raise ValueError("send JSON")
    data = await request.json()
    if not isinstance(data, dict):
        raise ValueError("send a JSON object")
    return data


def create_app(store: CareerStore | None = None, web: Path | None = None, watch_every: float = 2.0) -> Starlette:
    """The server. `watch_every` seconds between checks of the watched folders (0: never, for tests): every 2 seconds,
    so a new scorecard is on the site within a second or two of the game saving it (your decision, 14 November)."""
    site = Site(store)
    KEEP.DIR = site.store.root / "kept"     # sums and answers kept between starts (ccstats/keep.py, cache.py)
    hub = Hub()
    web = Path(web) if web else WEB
    problems = Problems(site.store.root / "problems.json")

    # ------------------------------------------------------------------ careers and colours
    async def health(request: Request):
        return _json({"ok": True, "site": "Stats Pack", "careers": len(site.names())})

    async def careers(request: Request):
        names = await anyio.to_thread.run_sync(site.names)
        return _json({"careers": names, "current": await anyio.to_thread.run_sync(site.current),
                      "folders": await anyio.to_thread.run_sync(site.folders)})

    async def choose_career(request: Request):
        try:
            name = str((await _body(request)).get("name", ""))
        except ValueError as e:
            return _error(str(e), 415)
        try:
            await anyio.to_thread.run_sync(site.select, name)
        except KeyError:
            return _error(f"There's no career called {name!r}.", 404)
        return _json({"current": name})

    def _career_info():
        c = site.career()
        if c is None:
            return None
        s = site.settings(c.name)
        m = c.matches
        order = m.sort_values(["date", "match_id"])
        return {"name": c.name, "matches": int(len(m)),
                "sections": in_order(m, m.section.unique()),   # the agreed order (Tests, ODIs, T20Is, ...)
                "seasons": sorted(map(str, m.season.unique()), reverse=True),
                "my_teams": site.my_teams(c), "my_teams_picked": site.my_teams(c, unplayed=True),
                "folder": s.folder if s else "", "checked_at": site.checked_at or None,
                "latest": order.date.iloc[-1].strftime("%Y-%m-%d") if len(order) else None}

    async def career(request: Request):
        info = await anyio.to_thread.run_sync(_career_info)
        if info is None:
            return _error("No career is open yet.", 404)
        return _json(info)

    async def theme_(request: Request):
        nation = request.query_params.get("nation", "")
        if nation and nation not in TEAM_COLOURS and nation != "none":
            return _error(f"No colours for {nation!r}.", 404)
        if nation == "none":
            from .theme import tokens
            return _json(tokens(None))
        return _json(await anyio.to_thread.run_sync(site.theme, nation))

    async def nations(request: Request):
        return _json({"nations": sorted(TEAM_COLOURS)})

    # ------------------------------------------------------------------ logos
    def _logo(kind: str, name: str, size: int, dark: bool) -> bytes:
        book = site.logos()
        path = book.team(name) if kind == "team" else book.comp(name)
        return LG.png(path, size, LG.look_on(book.style(path), dark)) if path is not None else b""

    async def logo(request: Request):
        kind, name = request.path_params["kind"], request.path_params["name"].removesuffix(".png")
        try:
            size = int(request.query_params.get("size", "48"))
        except ValueError:
            size = 0
        if kind not in ("team", "comp") or size not in LOGO_SIZES:
            return _error("Ask for a team or comp logo, 12 to 240 pixels.", 400)
        page = request.query_params.get("page", "")
        dark = (await anyio.to_thread.run_sync(site.theme))["dark"] if page not in ("dark", "light") else page == "dark"
        data = await anyio.to_thread.run_sync(_logo, kind, name, size, dark)
        if not data:
            return Response(status_code=404, headers={"Cache-Control": "no-store"})
        # a picture changed in the game shows at once: the browser asks again each time, but keeps the picture and
        # gets it again only when it changed (its fingerprint), so an unchanged logo costs a tiny answer, not a picture
        tag = '"' + hashlib.sha1(data).hexdigest()[:20] + '"'
        head = {"Cache-Control": "no-cache", "ETag": tag}
        if tag in request.headers.get("if-none-match", ""):
            return Response(status_code=304, headers=head)
        return Response(data, media_type="image/png", headers=head)

    def _logo_names():
        """Which names have a picture: every team in the career and every team in the game (a side can be picked and
        searched for before its first match), every competition in the career. The website shows a logo only for
        these, so it never asks for one that isn't there."""
        from ccstats import catalogue as CAT
        from ccstats import fixtures as FX
        c, book = site.career(), site.logos()
        teams = set(FX.NATIONS) | set(CAT.every_team())
        comps: set = set()
        if c is not None:
            m = c.matches
            teams |= set(m.home) | set(m.away)
            comps |= set(m.section) | set(m.event) | set(m.competition)
        return {"teams": sorted(t for t in teams if t and book.team(t) is not None),
                "comps": sorted(x for x in comps if x and book.comp(x) is not None)}

    async def logo_names(request: Request):
        return _json(await anyio.to_thread.run_sync(_logo_names))

    # ------------------------------------------------------------------ the style guide
    def _styleguide():
        c = site.career()
        if c is None:
            return None
        return styleguide.build(c, site.my_teams(c))

    async def styleguide_(request: Request):
        data = await anyio.to_thread.run_sync(_styleguide)
        if data is None:
            return _error("No career is open yet.", 404)
        return _json(data)

    # ------------------------------------------------------------------ Matches
    def _with_career(fn):
        """Run fn(career) in a worker thread; None (404) when no career is open."""
        async def run():
            def go():
                c = site.career()
                return None if c is None else fn(c)
            return await anyio.to_thread.run_sync(go)
        return run

    async def matches_(request: Request):
        q = request.query_params
        def make(c):
            r, m = site.remembered(c), c.matches
            remembered = "|".join(x for x in r.get("section", "").split("|") if x in set(m.section))
            section = q.get("section", "") or remembered
            pool = m if section in ("", "All sections") else m[m.section.isin(section.split("|"))]
            team = q.get("team", "") or (r["team"] if not q.get("section") and r.get("team") in set(pool.home) | set(pool.away) else "")
            return matchpage.finder(c, section, team, site.my_teams(c))
        data = await _with_career(make)()
        return _json(data) if data is not None else _error("No career is open yet.", 404)

    async def best_(request: Request):
        q = request.query_params
        data = await _with_career(lambda c: matchpage.best_games(c, q.get("section", "All sections"), q.get("team", "")))()
        return _json(data) if data is not None else _error("No career is open yet.", 404)

    async def match_(request: Request):
        mid = request.path_params["mid"]
        try:
            data = await _with_career(lambda c: matchpage.page(c, mid, site.my_teams(c), site.notes(c)))()
        except KeyError:
            return _error("There's no such match in this career.", 404)
        return _json(data) if data is not None else _error("No career is open yet.", 404)

    async def note_(request: Request):
        try:
            body = await _body(request)
        except ValueError as e:
            return _error(str(e), 415)
        mid, text = str(body.get("match", "")), str(body.get("text", ""))
        if len(text) > 5000:
            return _error("A note can be up to 5,000 characters.", 400)

        def go():
            c = site.career()
            if c is None:
                return None
            hit = c.matches[c.matches.match_id == mid]
            if hit.empty:
                raise KeyError(mid)
            return site.set_note(hit.source.iloc[0], text)
        try:
            saved = await anyio.to_thread.run_sync(go)
        except KeyError:
            return _error("There's no such match in this career.", 404)
        if saved is None:
            return _error("No career is open yet.", 404)
        return _json({"note": saved, "saved": bool(saved)})

    # ------------------------------------------------------------------ My team
    def _myteam(c, team: str, section: str):
        mine = site.my_teams(c)
        order = myteam.teams_by_latest(c, mine)
        asked = ""
        if team and team not in order and team not in set(c.matches.home) | set(c.matches.away):
            # an old link (another career's team, or one you've since changed): your own team instead, and said so
            asked, team = team, ""
        team = team or (order[0] if order else styleguide.pick_team(c, []) or "")
        if not team:
            return dict(teams=[], team="", mine=False, asked=asked, missing={"everything": styleguide.NO_MATCHES})
        # a competition the team hasn't played (a junk or old name in the address) is the normal page straight
        # away, kept as one page, not worked out again for every new name (myteam.page opens on the latest then)
        if section and section not in set(myteam.MT.sections_of(c, team)):
            section = ""
        s = site.settings(c.name)
        notes, sched = site.notes(c), list(s.fixtures) if s else []
        # the whole page is kept with the career (and your notes and schedule as they are): a second look, or the
        # warm-up's answer, comes at once
        sig = json.dumps([sorted(notes.items()), sched, mine], sort_keys=True, default=str)
        data = kept(c, ("myteam", team, section, sig), lambda: myteam.page(c, team, section, mine, notes, sched))
        return {**data, "mine": team in mine, "asked": asked}

    async def myteam_(request: Request):
        q = request.query_params
        data = await _with_career(lambda c: _myteam(c, q.get("team", ""), q.get("section", "")))()
        return _json(data) if data is not None else _error("No career is open yet.", 404)

    async def scouting_(request: Request):
        """My team's Scouting tab: struggling players and who could come in, in every competition the team plays."""
        q = request.query_params

        def make(c):
            order = myteam.teams_by_latest(c, site.my_teams(c))
            team = q.get("team", "") or (order[0] if order else styleguide.pick_team(c, []) or "")
            if team not in set(c.matches.home) | set(c.matches.away):
                raise KeyError(team)
            return kept(c, ("scouting", team), lambda: myteam.scouting(c, team))
        try:
            data = await _with_career(make)()
        except KeyError:
            return _error("That team hasn't played in this career.", 404)
        return _json(data) if data is not None else _error("No career is open yet.", 404)

    # ------------------------------------------------------------------ remembered picks
    def _with_memory(c, q, kinds) -> dict:
        """The page's own choices, with the section, season, team or competition you last picked on any page as the
        default for each one it wasn't asked for (the page then keeps it only if it's one of its choices)."""
        out = dict(q)
        r = site.remembered(c)
        for k in kinds:
            if not out.get(k) and r.get(k):
                out[k] = r[k]
        return out

    async def remember_(request: Request):
        try:
            body = await _body(request)
        except ValueError as e:
            return _error(str(e), 415)
        kind, value = str(body.get("kind", "")), str(body.get("value", ""))
        if kind not in site.REMEMBERED or not value or len(value) > 200:
            return _error("Send the kind (section, season, team or event) and the value picked.", 400)
        try:
            await anyio.to_thread.run_sync(site.remember, kind, value)
        except KeyError:
            return _error("No career is open yet.", 404)
        return _json({"ok": True})

    # ------------------------------------------------------------------ Teams
    def _team(c, q) -> dict:
        """The Teams page: every competition, season and team to pick from, and the picked team's record and one tab.
        With nothing picked: your team in its most played competition."""
        ch = teampage.choices(c)
        if not ch:
            return dict(choices=[], page=None)
        every = {t for s in ch for t in s["teams"]}
        order = [t for t in myteam.teams_by_latest(c, site.my_teams(c)) if t in every]
        r = site.remembered(c)
        team = q.get("team", "") or (r["team"] if r.get("team") in every else "") or (order[0] if order else ch[0]["teams"][0])
        if team not in every:
            raise KeyError(team)
        m = c.matches
        played = m[(m.home == team) | (m.away == team)].section.value_counts()
        order = [s["section"] for s in ch]   # the agreed order
        # the competitions ticked (several are counted together); ticks carried over from another page keep the ones
        # this team played
        remembered = [x for x in r.get("section", "").split("|") if x in played.index]
        asked = set(teampage.secs_of(q.get("section", ""))) or set(remembered)
        secs = [s for s in order if s in asked]
        if len(secs) > 1:
            secs = [s for s in secs if s in played.index]
        if not secs:
            secs = [played.index[0] if len(played) else next(s["section"] for s in ch if team in s["teams"])]
        section = "|".join(secs)
        seasons = teampage.seasons_of(c, section)
        season = q.get("season", "") or r.get("season", "")
        season = season if season in seasons else "All seasons"
        venue = {"home": "home", "away": "away"}.get(q.get("venue", "").lower(), "all")
        return dict(choices=ch, played=[s for s in order if s in played.index],
                    page=teampage.page(c, section, season, team, venue, q.get("tab", ""), q.get("race", "")))

    async def team_(request: Request):
        q = request.query_params
        try:
            data = await _with_career(lambda c: _team(c, q))()
        except KeyError:
            return _error("That team hasn't played in this career.", 404)
        return _json(data) if data is not None else _error("No career is open yet.", 404)

    async def teamvteam_(request: Request):
        """Team vs team: two teams' records side by side, against each other or each against anyone."""
        q = request.query_params

        def make(c):
            if c.matches.empty:
                return dict(choices=[], page=None)
            ch = teampage.choices(c)
            mine = myteam.teams_by_latest(c, site.my_teams(c))
            qq = _with_memory(c, q, ("section", "season"))
            a = q.get("a", "")
            section = qq.get("section", "")
            if not set(teampage.secs_of(section)) & {x["section"] for x in ch}:   # none of the ticked ones is here
                team = a or (mine[0] if mine else "")
                played = c.matches[(c.matches.home == team) | (c.matches.away == team)].section.value_counts()
                section = played.index[0] if len(played) else ch[0]["section"]
            return dict(choices=ch, page=tvtpage.page(c, section, qq.get("season", ""), a, q.get("b", ""), q.get("which", ""),
                                                      q.get("ground", ""), mine))
        data = await _with_career(make)()
        return _json(data) if data is not None else _error("No career is open yet.", 404)

    async def preview_(request: Request):
        """Opponent preview: your team and the team you're about to play (it opens on your next match)."""
        q = dict(request.query_params)

        def make(c):
            s = site.settings(c.name)
            sched = list(s.fixtures) if s else []
            order = myteam.teams_by_latest(c, site.my_teams(c))
            return previewpage.page(c, q, site.my_teams(c, unplayed=True), order, sched, site.remembered(c))
        data = await _with_career(make)()
        return _json(data) if data is not None else _error("No career is open yet.", 404)

    # ------------------------------------------------------------------ problems the site noticed
    async def problems_(request: Request):
        """GET: everything noticed (newest first: parts of pages, server answers, pages that broke in the browser,
        scorecards that couldn't be read) and a report to copy. POST {"clear": true | [ids]}: clear them (once fixed). POST {"report": {where, what, detail}}: a page that
        crashed in the browser."""
        if request.method == "POST":
            try:
                body = await _body(request)
            except ValueError as e:
                return _error(str(e), 415)
            if "clear" in body:
                ids = body["clear"]
                if ids is not True and not (isinstance(ids, list) and all(isinstance(i, str) for i in ids)):
                    return _error("Send clear: true, or a list of ids.", 400)
                problems.clear(None if ids is True else ids)
            elif isinstance(body.get("report"), dict):
                r = body["report"]
                if not isinstance(r.get("what"), str) or not r["what"].strip():
                    return _error("Say what went wrong.", 400)
                problems.add("page", str(r.get("where", "")), r["what"], str(r.get("detail", "")), site.current() or "")
            else:
                return _error("Send clear or report.", 400)
        items = await anyio.to_thread.run_sync(problems.items)
        return _json(dict(problems=items, count=len(items), report=problems_report(items)))

    async def crashed(request: Request, exc: Exception):
        """A request the server couldn't answer: noted, and a plain answer instead of a broken one."""
        try:
            problems.note_crash(str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""), exc,
                                site.current() or "")
        except Exception:  # noqa: BLE001
            pass
        return _error("Something went wrong working this out. It's noted in Settings → Problems.", 500)

    async def planner_(request: Request):
        """Team planner: qualification, batting order, bowling plan, knocking on the door, partnerships."""
        q = dict(request.query_params)
        data = await _with_career(lambda c: plannerpage.page(
            c, _with_memory(c, q, ("season",) if site.my_teams(c) else ("section", "season")),
            myteam.teams_by_latest(c, site.my_teams(c))))()
        return _json(data) if data is not None else _error("No career is open yet.", 404)

    async def competition_(request: Request):
        """Competitions: one competition as it's run in one season: league, title race, knockouts, series, WTC."""
        q = dict(request.query_params)
        data = await _with_career(lambda c: comppage.page(c, _with_memory(c, q, ("event", "season")),
                                                          myteam.teams_by_latest(c, site.my_teams(c))))()
        return _json(data) if data is not None else _error("No career is open yet.", 404)

    async def season_(request: Request):
        """Season: the calendar (results and your fixtures to come), the series tracker, how far each competition has got."""
        q = dict(request.query_params)

        def make(c):
            s = site.settings(c.name)
            return seasonpage.page(c, q, myteam.teams_by_latest(c, site.my_teams(c)), list(s.fixtures) if s else [])
        data = await _with_career(make)()
        return _json(data) if data is not None else _error("No career is open yet.", 404)

    async def review_(request: Request):
        """Season review: one competition's season (or an international year) in one place, with the MVPs."""
        q = dict(request.query_params)
        def make(c):
            r = site.remembered(c)
            qq = dict(q)
            if not qq.get("pick") and r.get("section") and r.get("season"):
                qq["pick"] = f"{r['section']}|{r['season']}"
            return reviewpage.review(c, qq, myteam.teams_by_latest(c, site.my_teams(c)))
        data = await _with_career(make)()
        return _json(data) if data is not None else _error("No career is open yet.", 404)

    async def honours_(request: Request):
        """Honours: every competition's winners season by season, and each team's trophy cabinet."""
        q = dict(request.query_params)
        data = await _with_career(lambda c: reviewpage.honours(c, q, site.my_teams(c)))()
        return _json(data) if data is not None else _error("No career is open yet.", 404)

    async def rivalries_(request: Request):
        """Rivalries: every pair of teams that have met in a competition, and one of them close up."""
        q = dict(request.query_params)
        data = await _with_career(lambda c: rivalriespage.page(
            c, _with_memory(c, q, ("section",)), myteam.teams_by_latest(c, site.my_teams(c))))()
        return _json(data) if data is not None else _error("No career is open yet.", 404)

    # ------------------------------------------------------------------ Leaders and records
    async def statbystat_(request: Request):
        """Stat by stat: every qualifying player ranked on one stat, where everyone sits, and the full figures."""
        q = dict(request.query_params)
        data = await _with_career(lambda c: leaderspage.stat_by_stat(
            c, _with_memory(c, q, ("section",)), myteam.teams_by_latest(c, site.my_teams(c))))()
        return _json(data) if data is not None else _error("No career is open yet.", 404)

    async def records_(request: Request):
        """Records: the record books, the best stand for each wicket, the best games ever, streaks, the record timeline."""
        q = dict(request.query_params)
        data = await _with_career(lambda c: leaderspage.records_page(
            c, _with_memory(c, q, ("section",)), myteam.teams_by_latest(c, site.my_teams(c))))()
        return _json(data) if data is not None else _error("No career is open yet.", 404)

    async def rankings_(request: Request):
        """Rankings: players on the marks out of 10, the rankings history, team ratings, teams by runs and wickets."""
        q = dict(request.query_params)
        data = await _with_career(lambda c: leaderspage.rankings_page(
            c, _with_memory(c, q, ("section",)), myteam.teams_by_latest(c, site.my_teams(c))))()
        return _json(data) if data is not None else _error("No career is open yet.", 404)

    async def hall_(request: Request):
        """Hall of fame: inductions, Player of the Match, batting duos, all-round matches and the firsts timeline."""
        q = dict(request.query_params)
        data = await _with_career(lambda c: leaderspage.hall_page(
            c, _with_memory(c, q, ("section",)), myteam.teams_by_latest(c, site.my_teams(c))))()
        return _json(data) if data is not None else _error("No career is open yet.", 404)

    async def insights_(request: Request):
        """Insights: is this total enough, the score to aim for, the chase calculator, home advantage, season by season,
        breakout players and innings by innings."""
        q = dict(request.query_params)
        data = await _with_career(lambda c: insightspage.insights_page(
            c, _with_memory(c, q, ("section",)), myteam.teams_by_latest(c, site.my_teams(c))))()
        return _json(data) if data is not None else _error("No career is open yet.", 404)

    async def analytics_(request: Request):
        """Analytics: runs above expected, fair averages, what wins games, luck, match-winners, style maps, boom or bust,
        whether form is real, and bat or bowl first."""
        q = dict(request.query_params)
        data = await _with_career(lambda c: analyticspage.analytics_page(
            c, _with_memory(c, q, ("section", "season")), myteam.teams_by_latest(c, site.my_teams(c))))()
        return _json(data) if data is not None else _error("No career is open yet.", 404)

    async def stories_(request: Request):
        """Player stories: the current site's 15 tabs, one competition and season at a time (Batter v bowler adds
        competitions up)."""
        q = dict(request.query_params)
        data = await _with_career(lambda c: storiespage.stories_page(
            c, _with_memory(c, q, ("section", "season")), myteam.teams_by_latest(c, site.my_teams(c))))()
        return _json(data) if data is not None else _error("No career is open yet.", 404)

    # ------------------------------------------------------------------ Players
    async def players_(request: Request):
        data = await _with_career(lambda c: kept(c, ("players-landing", tuple(site.my_teams(c))),
                                                 lambda: playerpage.landing(c, site.my_teams(c))))()
        return _json(data) if data is not None else _error("No career is open yet.", 404)

    async def names_(request: Request):
        """Every player who has batted or bowled, so the website can open the player menu from a name in a sentence or a
        chart."""
        data = await _with_career(lambda c: kept(c, ("names",), lambda: sorted({p["player"] for p in playerpage.everyone(c)})))()
        return _json(dict(names=data)) if data is not None else _error("No career is open yet.", 404)

    async def player_(request: Request):
        q = request.query_params
        name = q.get("name", "")

        def picks(c):
            # tidied first (a junk name in the address is the normal page straight away, kept once)
            qq = _with_memory(c, q, ("section", "season"))
            return playerpage.picks(c, name, qq.get("section", ""), qq.get("season", ""))
        try:
            data = await _with_career(lambda c: kept(c, ("player", name) + picks(c),
                                                     lambda: playerpage.page(c, name, *picks(c))))()
        except KeyError:
            return _error(f"{name or 'That player'} hasn't batted or bowled in this career.", 404)
        return _json(data) if data is not None else _error("No career is open yet.", 404)

    async def player_part_(request: Request):
        """One tile of the player page for the formats ticked on it (Country by country, Big-match, Bounce-back)."""
        q = request.query_params
        name, which = q.get("name", ""), q.get("part", "")
        sections = [s for s in q.get("sections", "").split("|") if s]
        try:
            data = await _with_career(lambda c: playerpage.part(c, name, which, sections))()
        except KeyError:
            return _error(f"{name or 'That player'} hasn't batted or bowled in this career.", 404)
        except ValueError as e:
            return _error(str(e), 400)
        return _json(data) if data is not None else _error("No career is open yet.", 404)

    # ------------------------------------------------------------------ Inbox
    def _inbox(c) -> dict:
        """Your teams' messages, newest first, without the ones you removed, each marked read or not."""
        teams = myteam.teams_by_latest(c, site.my_teams(c)) or [t for t in [styleguide.pick_team(c, [])] if t]
        state = site.inbox_state(c)
        msgs = []
        for t in teams:
            msgs += kept(c, ("inbox", t), lambda: DP.inbox(c, t))
        msgs = [dict(m, read=m["id"] in state["read"]) for m in msgs if m["id"] not in state["removed"]]
        msgs.sort(key=lambda m: m["date"], reverse=True)   # stable: within a day, each team's own order
        return dict(teams=teams, messages=styleguide.clean(msgs), unread=sum(not m["read"] for m in msgs))

    async def inbox_(request: Request):
        if request.method == "POST":
            try:
                body = await _body(request)
            except ValueError as e:
                return _error(str(e), 415)
            read, remove = body.get("read", []), body.get("remove", [])
            if not isinstance(read, list) or not isinstance(remove, list) or len(read) + len(remove) > 2000:
                return _error("Send the message ids to mark read or remove, as lists.", 400)
            try:
                await anyio.to_thread.run_sync(lambda: site.set_inbox([str(x) for x in read], [str(x) for x in remove]))
            except KeyError:
                return _error("No career is open yet.", 404)
        data = await _with_career(_inbox)()
        return _json(data) if data is not None else _error("No career is open yet.", 404)

    # ------------------------------------------------------------------ search (Ctrl K)
    def _search():
        c = site.career()
        return None if c is None else SR.items(c)

    async def search(request: Request):
        items = await anyio.to_thread.run_sync(_search)
        if items is None:
            return _error("No career is open yet.", 404)
        return _json({"items": items})

    # ------------------------------------------------------------------ live news of new matches
    async def events(request: Request):
        try:
            after = int(request.headers.get("last-event-id") or request.query_params.get("after") or "")
        except ValueError:
            after = None
        q = hub.subscribe(after)

        async def stream():
            try:
                yield "retry: 5000\n\n"
                while True:
                    try:
                        i, e = await asyncio.wait_for(q.get(), timeout=15)
                        yield f"id: {i}\ndata: {json.dumps(e)}\n\n"
                    except asyncio.TimeoutError:
                        yield ": still here\n\n"   # keeps the connection open
            finally:
                hub.unsubscribe(q)

        return StreamingResponse(stream(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})

    # ------------------------------------------------------------------ getting every page ready (the speed work)
    WARM = {"done": 0, "total": 0, "busy": False, "gen": 0, "career": ""}

    def _ask(path: str) -> None:
        """A page answered here in the server, exactly as the browser asks for it (its answer is then kept)."""
        p, _, qs = path.partition("?")
        scope = {"type": "http", "method": "GET", "path": p, "raw_path": p.encode(), "query_string": qs.encode(),
                 "headers": [(b"host", b"127.0.0.1")], "scheme": "http", "server": ("127.0.0.1", 80),
                 "client": ("127.0.0.1", 0), "root_path": "", "http_version": "1.1", "warm": True}

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            pass
        asyncio.run(app(scope, receive, send))

    def _plan(c) -> list:
        """Every page to get ready, in order: your team's home and your players first (your pages before anyone
        else's), then every page of the site as it first opens, then every other player's page, most matches first."""
        mine = myteam.teams_by_latest(c, site.my_teams(c))
        steps: list = [("myteam", t) for t in mine] + [("ask", "/api/players"), ("inbox", None)]
        squad: list = []
        for team in mine:
            m = c.matches[(c.matches.home == team) | (c.matches.away == team)]
            if m.empty:
                continue
            last = m.sort_values("date").iloc[-1]
            ids = m[(m.section == last.section) & (m.season == last.season)].match_id
            b = c.batting[c.batting.match_id.isin(ids) & (c.batting.team == team)]
            squad += [p for p in b.groupby("player").match_id.nunique().sort_values(ascending=False).index if p not in squad]
        steps += [("player", p) for p in squad]
        steps += [("ask", u) for u in ("/api/matches", "/api/team", "/api/team?tab=How%20they%20win",
                                       "/api/team?tab=Season", "/api/team?tab=Squad", "/api/teamvteam", "/api/preview",
                                       "/api/planner", "/api/competition", "/api/season", "/api/review", "/api/honours",
                                       "/api/rivalries", "/api/names", "/api/statbystat",
                                       "/api/statbystat?disc=Bowling", "/api/records",
                                       "/api/rankings", "/api/rankings?what=bowling", "/api/rankings?what=all-round",
                                       "/api/hall", "/api/hall?tab=Firsts", "/api/insights",
                                       "/api/insights?tab=Score%20to%20aim%20for", "/api/analytics",
                                       "/api/stories")]
        steps += [("ratings", sec) for sec in sorted(c.matches.section.unique())]
        # every competition, and each of its seasons: the parts every player's page there shares, worked out through
        # its top run-scorer's page there, so the first player you open in any competition or season is quick too
        m = c.matches
        for sec in in_order(m, m.section.unique()):
            here = m[m.section == sec]
            for season in [""] + sorted(here.season.astype(str).unique(), reverse=True):
                ids = here.match_id if not season else here[here.season.astype(str) == season].match_id
                b = c.batting[c.batting.match_id.isin(ids)]
                if not b.empty:
                    steps.append(("player_in", (b.groupby("player").runs.sum().idxmax(), sec, season)))
        steps += [("scouting", t) for t in mine]
        everyone = c.batting.groupby("player").match_id.nunique().sort_values(ascending=False, kind="stable").index
        steps += [("player", p) for p in everyone if p not in set(squad)]
        return steps

    def _do(c, kind, x) -> None:
        if kind == "myteam":
            _myteam(c, x, "")
        elif kind == "ask":
            _ask(x)
        elif kind == "inbox":
            _inbox(c)
        elif kind == "player":
            picks = playerpage.picks(c, x, "", "")
            kept(c, ("player", x) + picks, lambda: playerpage.page(c, x, *picks))
        elif kind == "player_in":
            p, sec, season = x
            picks = playerpage.picks(c, p, sec, season)
            kept(c, ("player", p) + picks, lambda: playerpage.page(c, p, *picks))
        elif kind == "ratings":
            matchpage.ratings(c, x)
        elif kind == "scouting":
            kept(c, ("scouting", x), lambda: myteam.scouting(c, x))

    def warm():
        """Get every page ready before anyone asks (your picks, 14 November): your team and players first, then every
        page, then everyone else. The site is usable meanwhile: whenever you open a page, this waits until it's
        answered. Everything worked out is kept on disk as it goes (cache.py), so it happens once; a new match starts
        it again, and only what the new match changed is worked out (the rest is read back)."""
        WARM["gen"] += 1
        gen = WARM["gen"]
        c = site.career()
        if c is None:
            WARM.update(done=0, total=0, busy=False, career="")
            return
        steps = _plan(c)
        WARM.update(done=0, total=len(steps), busy=True, career=c.name)
        # everyone else's player pages (the long tail) go to helpers on the other cores, if there are any
        n_help = warmers.helpers()
        tail: list = []
        if n_help:
            last = max(i for i, (k, _) in enumerate(steps) if k != "player")   # everyone else comes after it
            tail = [x for _, x in steps[last + 1:]]
            steps = steps[:last + 1]
        for i, (kind, x) in enumerate(steps):
            while ASKING[0] > 0 and WARM["gen"] == gen:
                time.sleep(0.05)
            if WARM["gen"] != gen or site.career() is not c:   # new matches or another career: started again
                return
            try:
                _do(c, kind, x)
            except Exception:  # noqa: BLE001 - getting ready is only a head start: the page works it out when asked
                pass
            WARM["done"] = i + 1
            if i % 25 == 24:
                try:
                    save_kept(c, every=60)
                except Exception:  # noqa: BLE001 - a full disk: kept in memory, worked out again next start
                    pass
        if tail:
            _helped(c, tail, n_help, gen)
        try:
            save_kept(c)
        except Exception:  # noqa: BLE001
            pass
        if WARM["gen"] == gen:
            WARM["busy"] = False

    def _helped(c, names: list, n_help: int, gen: int) -> None:
        """The long tail of player pages on the helpers (warmers.py), in small batches, each answer kept as it comes;
        stopped at once if new matches arrive or the site closes."""
        from concurrent.futures import ProcessPoolExecutor, as_completed
        import multiprocessing as mp
        stamp = cache_stamp(c)
        batches = [names[i:i + 8] for i in range(0, len(names), 8)]
        done0 = WARM["done"]
        try:
            with ProcessPoolExecutor(n_help, mp_context=mp.get_context("spawn"), initializer=warmers.start,
                                     initargs=(str(site.store.root), c.name)) as pool:
                futs = [pool.submit(warmers.players, b, stamp) for b in batches]
                got = 0
                for fu in as_completed(futs):
                    if WARM["gen"] != gen or site.career() is not c:
                        for x in futs:
                            x.cancel()
                        return
                    for key, value in fu.result():
                        cache_put(c, key, value)
                    got += 1
                    WARM["done"] = done0 + min(len(names), got * 8)
                    if got % 10 == 0:
                        save_kept(c, every=60)
        except Exception:  # noqa: BLE001 - no helpers (a locked-down PC): the rest is done here, one at a time
            for p in names:
                if WARM["gen"] != gen or site.career() is not c:
                    return
                while ASKING[0] > 0 and WARM["gen"] == gen:
                    time.sleep(0.05)
                try:
                    _do(c, "player", p)
                except Exception:  # noqa: BLE001
                    pass
                WARM["done"] += 1

    async def warmup_(request: Request):
        """How far getting every page ready has got (the progress bar)."""
        return _json(dict(done=WARM["done"], total=WARM["total"], busy=WARM["busy"]))

    async def watch_loop():
        first = True
        while True:
            try:
                ASKING[0] += 1          # the background preparation steps aside while new matches are taken in
                try:
                    found = await anyio.to_thread.run_sync(site.sync)
                finally:
                    ASKING[0] -= 1
                for e in found:
                    hub.publish(e)
                    if e.get("type") == "failed":   # kept in Settings → Problems: a career keeps only what it could read
                        for f in e["files"]:
                            # a match still being saved by the game is read again once it's finished: not a problem
                            if not f["reason"].startswith("incomplete scorecard"):
                                problems.add("scorecard", f["file"], f["reason"], career=e["career"])
                # a new start, new matches, or another career opened: get every page ready (again)
                if first or any(e.get("type") == "matches" for e in found) or (site.current() or "") != WARM["career"]:
                    first = False
                    WARM["career"] = site.current() or ""
                    asyncio.get_running_loop().run_in_executor(None, warm)
                elif not WARM["busy"]:
                    # pages worked out as you open them are kept on disk too (at most once a minute)
                    c = site.career()
                    if c is not None:
                        await anyio.to_thread.run_sync(lambda: save_kept(c, every=60))
                hub.publish({"type": "checked", "at": time.time(), "folders": len(site.folders())})
            except Exception:  # noqa: BLE001 - a check that fails is tried again next time
                pass
            await asyncio.sleep(watch_every)

    @contextlib.asynccontextmanager
    async def lifespan(app):
        task = asyncio.create_task(watch_loop()) if watch_every else None
        try:
            yield
        finally:
            if task:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
            WARM["gen"] += 1   # the warm-up stops
            with contextlib.suppress(Exception):   # what's been worked out is kept for the next start
                c = site.career()
                if c is not None:
                    await anyio.to_thread.run_sync(lambda: save_kept(c))

    # ------------------------------------------------------------------ the website
    def _page_missing() -> HTMLResponse:
        return HTMLResponse("<!doctype html><meta charset='utf-8'><title>Stats Pack</title><body style='font:16px "
                            "sans-serif;padding:40px'><h1>The new site isn't built yet</h1><p>The folder web/dist is "
                            "missing. Download the Stats Pack zip again, or build it with <code>npm run build</code> "
                            "in the web folder.</p>", status_code=503)

    async def page(request: Request):
        """Any address that isn't a file is a page of the site: the website works out which (index.html)."""
        rel = request.path_params.get("path", "")
        if rel.startswith("api/"):
            return _error("There's no such question.", 404)
        if rel:
            f = (web / rel).resolve()
            if f.is_file() and f.is_relative_to(web.resolve()):
                return FileResponse(f)
        index = web / "index.html"
        if not index.is_file():
            return _page_missing()
        return FileResponse(index, headers={"Cache-Control": "no-cache"})

    routes = [
        Route("/api/health", health),
        Route("/api/careers", careers),
        Route("/api/careers/current", choose_career, methods=["POST"]),
        Route("/api/career", career),
        Route("/api/theme", theme_),
        Route("/api/nations", nations),
        Route("/api/logos", logo_names),
        Route("/api/logo/{kind}/{name:path}", logo),
        Route("/api/styleguide", styleguide_),
        Route("/api/search", search),
        Route("/api/myteam", myteam_),
        Route("/api/matches", matches_),
        Route("/api/matches/best", best_),
        Route("/api/match/{mid}", match_),
        Route("/api/notes", note_, methods=["POST"]),
        Route("/api/inbox", inbox_, methods=["GET", "POST"]),
        Route("/api/players", players_),
        Route("/api/names", names_),
        Route("/api/scouting", scouting_),
        Route("/api/team", team_),
        Route("/api/teamvteam", teamvteam_),
        Route("/api/preview", preview_),
        Route("/api/planner", planner_),
        Route("/api/rivalries", rivalries_),
        Route("/api/statbystat", statbystat_),
        Route("/api/records", records_),
        Route("/api/rankings", rankings_),
        Route("/api/hall", hall_),
        Route("/api/insights", insights_),
        Route("/api/analytics", analytics_),
        Route("/api/stories", stories_),
        Route("/api/competition", competition_),
        Route("/api/season", season_),
        Route("/api/review", review_),
        Route("/api/honours", honours_),
        Route("/api/player", player_),
        Route("/api/player_part", player_part_),
        Route("/api/events", events),
        Route("/api/problems", problems_, methods=["GET", "POST"]),
        Route("/api/remember", remember_, methods=["POST"]),
        Route("/api/warmup", warmup_),
    ]
    if (web / "assets").is_dir():   # the website's files, named after their contents: kept by the browser for good
        routes.append(Mount("/assets", app=StaticFiles(directory=web / "assets")))
    routes += [Route("/", page), Route("/{path:path}", page)]
    app = Starlette(routes=routes, lifespan=lifespan, exception_handlers={Exception: crashed},
                    middleware=[Middleware(TrustedHostMiddleware, allowed_hosts=HOSTS), Middleware(Squeeze),
                                Middleware(Watch, problems=problems, site=site)])
    app.state.site, app.state.hub = site, hub
    return app
