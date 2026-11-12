"""Turn a pile of scorecard files into one career's tables.

A *career* is one Cricket Captain save.  Its data is the set of scorecard
texts plus the manual fixes the user made on the data check page.  Loading
re-parses the texts every time, so parser improvements reach old careers
automatically, and a career can be saved as one small "career pack" zip.
"""

from __future__ import annotations

import io
import json
import re
import time
import zipfile
from dataclasses import dataclass, field
import datetime
from datetime import timedelta
from typing import Iterable

import pandas as pd

from .competitions import (EXHIBITION, FIRST_CLASS, INTERNATIONAL, INTERNATIONAL_SECTION, TEST, TOUR, assign_seasons,
                           assign_series, classify, event_of, fix_playoff_stages, section_of)
from .parser import Match, ScorecardError, parse_scorecard, validate_match

MULTI_DAY = {TEST, FIRST_CLASS}
SUB_RE = re.compile(r"^(sub|substitute)\b", re.I)  # "c Sub b Cook": taken by a substitute fielder


# --------------------------------------------------------------------------- #
# Manual fixes (data check page)
# --------------------------------------------------------------------------- #


@dataclass
class Fixes:
    """Corrections the user confirmed by hand.  Nothing here is automatic.

    merges:  {"Q de Kock ": "Q de Kock"} - treat the first name as the second.
    splits:  [{"player": "A Sharma", "team": "Northamptonshire", "new_name": "A Sharma (Northants)"}]
             - rows for that player *while playing for that team* get the new name.
    credits: {"<match_id>|<innings_no>|<batting position>": "S Khan"} - who took a catch or
             stumping the scorecard left ambiguous ("c Khan" with two Khans in the XI).
    suggested: the credit keys that came from "Accept all suggestions" rather than
             being picked one by one, so they can be told apart and undone together.
    """

    merges: dict[str, str] = field(default_factory=dict)
    splits: list[dict] = field(default_factory=list)
    credits: dict[str, str] = field(default_factory=dict)
    suggested: list[str] = field(default_factory=list)
    include: list[str] = field(default_factory=list)  # match ids: count these even though they look like leftovers
    exclude: list[str] = field(default_factory=list)  # match ids: leave these out of every figure

    def to_json(self) -> str:
        return json.dumps({"merges": self.merges, "splits": self.splits, "credits": self.credits,
                           "suggested": self.suggested, "include": self.include, "exclude": self.exclude}, indent=1)

    @classmethod
    def from_json(cls, text: str) -> "Fixes":
        d = json.loads(text or "{}")
        return cls(d.get("merges", {}), d.get("splits", []), d.get("credits", {}), d.get("suggested", []),
                   d.get("include", []), d.get("exclude", []))

    def rename(self, name: str, team: str) -> str:
        for s in self.splits:
            if s["player"] == name and s["team"] == team:
                name = s["new_name"]
                break
        seen = set()
        while name in self.merges and name not in seen:  # follow chains, avoid loops
            seen.add(name)
            name = self.merges[name]
        return name


# --------------------------------------------------------------------------- #
# Reading files
# --------------------------------------------------------------------------- #


@dataclass
class FileReport:
    source: str
    status: str  # "loaded", "duplicate", "failed", "skipped"
    message: str = ""
    match_id: str = ""


def decode(data: bytes) -> str:
    for enc in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            text = data.decode(enc)
        except UnicodeDecodeError:
            continue
        if enc == "utf-16" and not data.startswith((b"\xff\xfe", b"\xfe\xff")):
            continue
        return text
    return data.decode("latin-1")


def _zip_time(info: zipfile.ZipInfo) -> float | None:
    try:
        return time.mktime(info.date_time + (0, 0, -1))
    except (OverflowError, ValueError):
        return None


def expand(files: Iterable[tuple]) -> Iterable[tuple[str, bytes, float | None]]:
    """Yield (name, bytes, modified time or None) for every file, looking inside zips
    (and zips in zips).  Items are (name, bytes) or (name, bytes, modified time)."""
    for item in files:
        name, data = item[0], item[1]
        mtime = item[2] if len(item) > 2 else None
        if name.lower().endswith(".zip") or data[:4] == b"PK\x03\x04":
            try:
                with zipfile.ZipFile(io.BytesIO(data)) as zf:
                    inner = [(f"{name}/{i.filename}", zf.read(i), _zip_time(i)) for i in zf.infolist() if not i.is_dir()]
            except zipfile.BadZipFile:
                yield name, data, mtime
                continue
            yield from expand(inner)
        else:
            yield name, data, mtime


def _leaf(source: str) -> str:
    """The file name a career file stores a scorecard under ("24 may 2026-mid v sry.txt" ->
    "24_may_2026-mid_v_sry.txt").  Careers saved before names were kept only have this."""
    return re.sub(r"[^\w.\-]+", "_", source.split("/")[-1]) or "scorecard.txt"


def _signature(m: Match) -> tuple:
    """Two saves of the same match (autosave + manual save) have the same
    teams, date and scores even if the whitespace differs."""
    return (m.date, m.team1, m.team2, m.title, tuple((i.team, i.total, i.wickets, i.balls) for i in m.innings))


# --------------------------------------------------------------------------- #
# Career
# --------------------------------------------------------------------------- #

PACK_TEXTS = "scorecards/"
PACK_FIXES = "fixes.json"
PACK_INFO = "career.json"
PACK_SOURCES = "sources.json"  # stored file name -> the scorecard's own file name
PACK_TIMES = "times.json"  # stored file name -> when the game saved it
LEFTOVER_COLUMNS = ["match_id", "source", "date", "competition", "stage", "home", "away", "result", "saved", "reason", "auto"]


@dataclass
class Career:
    name: str
    texts: dict[str, str]  # source -> scorecard text, one per distinct match
    fixes: Fixes
    report: list[FileReport]
    matches: pd.DataFrame
    innings: pd.DataFrame
    batting: pd.DataFrame
    bowling: pd.DataFrame
    fielding: pd.DataFrame
    fow: pd.DataFrame
    problems: pd.DataFrame  # self-check failures, per match
    times: dict[str, float] = field(default_factory=dict)  # source -> when the game saved the file
    # matches kept in the career but left out of every figure: games from an earlier
    # playthrough of a season, and any the user left out on the data check page
    leftovers: pd.DataFrame = field(default_factory=lambda: pd.DataFrame(columns=LEFTOVER_COLUMNS))

    # ------------------------------------------------------------ building
    @classmethod
    def build(cls, name: str, files: Iterable[tuple], fixes: Fixes | None = None,
              existing: dict[str, str] | None = None, times: dict[str, float] | None = None) -> "Career":
        """Read files (plain .txt or zips) into a career.  `existing` are texts
        already in the career, so adding a new batch keeps what was there; `times`
        are when the game saved each file (from the Scorecards folder), used to
        spot games left over from an earlier playthrough of a season."""
        fixes = fixes or Fixes()
        texts: dict[str, str] = dict(existing or {})
        saved: dict[str, float] = dict(times or {})
        report: list[FileReport] = []
        parsed: dict[str, Match] = {}
        seen_ids: dict[str, str] = {}
        seen_sigs: dict[tuple, str] = {}

        def forget(source: str) -> None:
            parsed.pop(source)
            texts.pop(source, None)
            for d in (seen_ids, seen_sigs):
                for k in [k for k, v in d.items() if v == source]:
                    del d[k]

        def admit(source: str, text: str, is_new: bool, mtime: float | None = None) -> None:
            try:
                m = parse_scorecard(text, source)
            except ScorecardError as e:
                report.append(FileReport(source, "failed", str(e)))
                return
            except Exception as e:  # a file the parser could not cope with at all
                report.append(FileReport(source, "failed", f"could not read: {e}"))
                return
            if m.date is None:
                report.append(FileReport(source, "failed", "no match date found"))
                return
            if not m.result:
                # no result line at all: the file was cut short (the game may still have been saving it). Counting it would
                # add half a match to every stat; when the file is finished it changes, and it's read again then.
                if is_new:
                    report.append(FileReport(source, "failed", "incomplete scorecard (no result yet): it's read again "
                                                               "once the game has finished saving it"))
                return
            if mtime is not None:
                saved[source] = mtime
            if is_new:
                # The game saved this file again (a replayed match): the new version
                # replaces the old one.  Careers saved by older versions stored the
                # file under a tidied name, so that counts as the same file too.
                old = source if source in parsed else _leaf(source) if _leaf(source) in parsed else None
                if old is not None:
                    if parsed[old].match_id == m.match_id:  # saved again unchanged
                        report.append(FileReport(source, "duplicate", f"same match as {old}", m.match_id))
                        return
                    forget(old)
            dup = seen_ids.get(m.match_id) or seen_sigs.get(_signature(m))
            if dup:
                if is_new:
                    report.append(FileReport(source, "duplicate", f"same match as {dup}", m.match_id))
                return
            seen_ids[m.match_id] = source
            seen_sigs[_signature(m)] = source
            parsed[source] = m
            texts[source] = text
            if is_new:
                report.append(FileReport(source, "loaded", "", m.match_id))

        for source, text in (existing or {}).items():
            admit(source, text, is_new=False)
        for source, data, mtime in expand(files):
            if not source.lower().endswith(".txt"):
                report.append(FileReport(source, "skipped", "not a .txt scorecard"))
                continue
            admit(source, decode(data), is_new=True, mtime=mtime)
        texts = {s: t for s, t in texts.items() if s in parsed}
        by_leaf = {_leaf(s): t for s, t in saved.items()}
        saved = {s: saved.get(s, by_leaf.get(_leaf(s))) for s in parsed}
        saved = {s: t for s, t in saved.items() if t is not None}
        left = find_leftovers(parsed, saved, fixes)
        tables = build_tables([m for s, m in parsed.items() if s not in left], fixes)
        rows = []
        for s, (reason, auto) in left.items():
            m = parsed[s]
            c = classify(m)
            rows.append(dict(match_id=m.match_id, source=s, date=pd.Timestamp(m.date), competition=c.competition,
                             stage=c.stage, home=m.team1, away=m.team2, result=m.result,
                             saved=pd.Timestamp(saved[s], unit="s") if s in saved else pd.NaT, reason=reason, auto=auto))
        leftovers = pd.DataFrame(rows, columns=LEFTOVER_COLUMNS).sort_values("date").reset_index(drop=True)
        return cls(name, texts, fixes, report, **tables, times=saved, leftovers=leftovers)

    def add_files(self, files: Iterable[tuple], times: dict[str, float] | None = None) -> "Career":
        return Career.build(self.name, files, self.fixes, existing=self.texts, times={**self.times, **(times or {})})

    def with_fixes(self, fixes: Fixes) -> "Career":
        c = Career.build(self.name, [], fixes, existing=self.texts, times=self.times)
        c.report = self.report
        return c

    # ------------------------------------------------------------ packs
    def to_pack(self) -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(PACK_INFO, json.dumps({"name": self.name, "version": 1}))
            zf.writestr(PACK_FIXES, self.fixes.to_json())
            used, sources, times = set(), {}, {}
            for source, text in self.texts.items():
                leaf = _leaf(source)
                while leaf in used:
                    leaf = "_" + leaf
                used.add(leaf)
                zf.writestr(PACK_TEXTS + leaf, text)
                sources[leaf] = source
                if source in self.times:
                    times[leaf] = self.times[source]
            zf.writestr(PACK_SOURCES, json.dumps(sources, indent=0))
            zf.writestr(PACK_TIMES, json.dumps(times, indent=0))
        return buf.getvalue()

    @staticmethod
    def is_pack(data: bytes) -> bool:
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                return PACK_INFO in zf.namelist()
        except zipfile.BadZipFile:
            return False

    @classmethod
    def from_pack(cls, data: bytes) -> "Career":
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            info = json.loads(zf.read(PACK_INFO))
            names = zf.namelist()
            fixes = Fixes.from_json(zf.read(PACK_FIXES).decode()) if PACK_FIXES in names else Fixes()
            sources = json.loads(zf.read(PACK_SOURCES)) if PACK_SOURCES in names else {}
            times = json.loads(zf.read(PACK_TIMES)) if PACK_TIMES in names else {}
            files = []
            for n in names:
                if n.startswith(PACK_TEXTS):
                    leaf = n[len(PACK_TEXTS):]
                    files.append((sources.get(leaf, leaf), zf.read(n), times.get(leaf)))
        c = cls.build(info.get("name", "My career"), files, fixes)
        return c


# --------------------------------------------------------------------------- #
# Games left over from an earlier playthrough of a season
# --------------------------------------------------------------------------- #

SAVE_SLACK = 5  # seconds: files saved together can carry slightly different times


def find_leftovers(parsed: dict[str, Match], saved: dict[str, float], fixes: Fixes) -> dict[str, tuple[str, bool]]:
    """{source: (reason, found automatically)} for matches left out of every figure.

    When a save is reloaded and part of a season played again, the game writes each
    replayed match over its old file, but a knockout game with different teams gets
    a new file name, so the old one stays in the folder (e.g. three IPL finals).
    Such a game gives itself away by the file times: another match of the same
    competition and season, played *before* it, was saved *after* it (the season
    was rewound past it), or a knockout on the same day with one of the same teams
    was saved after it.  Only knockout games are judged, and only with file times.
    The user can count any of them again, or leave out any other match, on the
    data check page."""
    out: dict[str, tuple[str, bool]] = {}
    items = list(parsed.items())
    cls = [classify(m) for _, m in items]
    seasons = assign_seasons([(c.competition, m.date) for c, (_, m) in zip(cls, items)])
    groups: dict[tuple, list[int]] = {}
    for i, (c, season) in enumerate(zip(cls, seasons)):
        groups.setdefault((c.competition, season), []).append(i)

    def when(t: float) -> str:
        return time.strftime("%d %b %Y", time.localtime(t)).lstrip("0")

    for idxs in groups.values():
        for i in idxs:
            src, m = items[i]
            if not cls[i].knockout or src not in saved:
                continue
            span = timedelta(days=5) if cls[i].format in MULTI_DAY else timedelta(0)  # a multi-day game can end later
            for j in idxs:
                other, o = items[j]
                if j == i or other not in saved or saved[other] <= saved[src] + SAVE_SLACK:
                    continue
                rewound = o.date + span < m.date
                clash = cls[j].knockout and o.date == m.date and {o.team1, o.team2} & {m.team1, m.team2}
                if rewound or clash:
                    later = "played again" if rewound else "replayed from this round"
                    out[src] = (f"From an earlier playthrough: saved {when(saved[src])}, before this season was "
                                f"{later} on {when(saved[other])}.", True)
                    break
    for src, m in parsed.items():
        if m.match_id in fixes.include:
            out.pop(src, None)
        elif m.match_id in fixes.exclude:
            out[src] = ("Left out by you on the data check page.", False)
    return out


# --------------------------------------------------------------------------- #
# Tables
# --------------------------------------------------------------------------- #


def divisions_of(games: list[tuple]) -> list[str]:
    """The division of each game, from (competition, season, stage, team1, team2): its stage when that's a division
    ("Division 1"); for any other game of a league with divisions (a final, a play-off: the scorecard says "f" or
    "p.o."), the division both teams played in that season, so a division's final is in that division's table and
    records. '' when there's none, or the two teams played in different divisions."""
    member: dict[tuple, set] = {}
    for comp, season, stage, t1, t2 in games:
        if stage.startswith("Division"):
            for t in (t1, t2):
                member.setdefault((comp, season, t), set()).add(stage)
    out = []
    for comp, season, stage, t1, t2 in games:
        if stage.startswith("Division"):
            out.append(stage)
            continue
        a, b = member.get((comp, season, t1), set()), member.get((comp, season, t2), set())
        out.append(next(iter(a)) if len(a) == 1 and a == b else "")
    return out


def build_tables(parsed: list[Match], fixes: Fixes) -> dict[str, pd.DataFrame]:
    parsed = sorted(parsed, key=lambda m: (m.date, m.source))
    cls = [classify(m) for m in parsed]
    seasons = assign_seasons([(c.competition, m.date) for c, m in zip(cls, parsed)])
    series = assign_series([
        (c.format, m.team1, m.team2, m.series_match_no, m.series_length, m.date)
        if c.competition in ("Test", "ODI", "T20I") else (c.format, m.team1, m.team2, None, None, m.date)
        for c, m in zip(cls, parsed)])
    stages = [c.stage for c in cls]
    brackets: dict[tuple, list[dict]] = {}
    for i, (c, m) in enumerate(zip(cls, parsed)):
        if c.knockout:
            loser = m.team2 if m.winner == m.team1 else m.team1 if m.winner else ""
            brackets.setdefault((c.competition, seasons[i]), []).append(
                dict(i=i, stage=c.stage, teams={m.team1, m.team2}, loser=loser, date=m.date))
    for games in brackets.values():
        fix_playoff_stages(games)
        for g in games:
            stages[g["i"]] = g["stage"]
    # International cricket is played all year round, so its seasons are calendar
    # years ("ODIs in 2026"), the same for a bilateral series and a World Cup; so
    # are tour games and World XI games, which come with the tours.
    seasons = [str(m.date.year) if (c.level == INTERNATIONAL and c.format in INTERNATIONAL_SECTION)
               or c.level in (EXHIBITION, TOUR) else s for s, c, m in zip(seasons, cls, parsed)]
    divisions = divisions_of([(c.competition, seasons[i], stages[i], m.team1, m.team2)
                              for i, (c, m) in enumerate(zip(cls, parsed))])

    M, I, B, W, F, FOW, P = [], [], [], [], [], [], []
    for i, (m, c) in enumerate(zip(parsed, cls)):
        multi = c.format in MULTI_DAY
        batted_first = m.innings[0].team if m.innings else ""
        result_type, tiebreak = m.result_type or "unknown", ""
        if result_type == "win" and re.search(r"\bwon on\b", m.result, re.I):
            # "Karnataka won on more wickets left": a drawn knockout settled by a
            # tiebreak. It counts as a draw in records; the bracket still uses it.
            result_type, tiebreak = "draw", m.winner
        elif result_type == "tie" and m.winner:
            tiebreak = m.winner  # super over
        winner = m.winner if result_type == "win" else ""
        M.append(dict(
            match_id=m.match_id, date=pd.Timestamp(m.date), season=seasons[i], competition=c.competition,
            section=section_of(c.competition, divisions[i] or stages[i], c.format, c.level),
            event=event_of(c.competition, divisions[i] or stages[i]),
            format=c.format, level=c.level, country=c.country, stage=stages[i], knockout=c.knockout,
            neutral=c.neutral, recognised=c.recognised, title=m.title, series_id=series[i],
            series_match_no=m.series_match_no, series_length=m.series_length,
            home=m.team1, away=m.team2, winner=winner,
            loser=(m.team2 if winner == m.team1 else m.team1) if winner else "",
            result_type=result_type, result=_corrected_result(m), tiebreak_winner=tiebreak,
            margin_runs=m.margin_runs, margin_wickets=m.margin_wickets, innings_win=m.innings_win,
            margin_note=m.margin_note, super_over=_super_over_text(m), rain=_rain(m, c.format, result_type),
            player_of_match=fixes.rename(m.player_of_match, ""), batted_first=batted_first, source=m.source))
        for p in validate_match(m):
            P.append(dict(match_id=m.match_id, source=m.source, problem=p))
        last_no = len(m.innings)
        for inn in m.innings:
            all_out = _all_out(inn)
            declared = multi and not all_out and inn.number < last_no
            I.append(dict(
                match_id=m.match_id, innings_no=inn.number, team_innings=inn.team_innings, team=inn.team,
                opposition=inn.bowling_team, runs=inn.total, wickets=inn.wickets, balls=inn.balls,
                all_out=all_out, declared=declared or inn.declared,
                counted_in_balls=inn.counted_in_balls, extras=inn.extras, byes=inn.byes, leg_byes=inn.leg_byes,
                wides=inn.wides, no_balls=inn.no_balls,
                home=inn.team == m.team1 and not c.neutral, batting_first=inn.team == batted_first))
            fell = set()
            for w, score in inn.fow:
                if w in fell:
                    continue  # a wicket listed twice: keep the first (a later list belongs to something else)
                fell.add(w)
                FOW.append(dict(match_id=m.match_id, innings_no=inn.number, team=inn.team, wicket=w, score=score))
            seen: dict[str, int] = {}
            for b in inn.batting:
                seen[b.player] = seen.get(b.player, 0) + 1
                raw = b.player if seen[b.player] == 1 else f"{b.player} ({seen[b.player]})"
                player = fixes.rename(raw, inn.team)
                bowler = fixes.rename(b.bowler, inn.bowling_team) if b.bowler else ""
                key = f"{m.match_id}|{inn.number}|{b.position}"
                fielder, resolved = b.fielder, b.fielder_resolved
                if key in fixes.credits:
                    fielder, resolved = fixes.credits[key], True
                if fielder and resolved:
                    fielder = fixes.rename(fielder, inn.bowling_team)
                B.append(dict(
                    match_id=m.match_id, innings_no=inn.number, team=inn.team, opposition=inn.bowling_team,
                    player=player, position=b.position, did_bat=b.did_bat, runs=b.runs, balls=b.balls,
                    fours=b.fours, sixes=b.sixes, out=b.did_bat and not b.not_out, how_out=b.how_out,
                    dismissal=b.dismissal, bowler=bowler, fielder=fielder if b.fielder else "",
                    fielder_resolved=resolved if b.fielder else False))
                if b.how_out in ("caught", "stumped") and b.fielder and not SUB_RE.match(b.fielder):
                    # (a catch by a substitute fielder, "c Sub", belongs to no one in the XI)
                    F.append(dict(
                        match_id=m.match_id, innings_no=inn.number, team=inn.bowling_team,
                        opposition=inn.team, player=fielder if resolved else "", printed=b.fielder if not resolved else fielder,
                        kind=b.how_out, batter=player, bowler=bowler, resolved=resolved, credit_key=key))
            # Two players the game prints the same way ("K Mendis" for Kusal and Kamindu) can
            # both bowl in one innings.  Like the batting list, where the one lower in the
            # order is "K Mendis (2)", they are kept apart.  The scorecard can't say which
            # bowling line is whose, so the one who bowled more is taken to be the one who
            # bats lower (specialist bowlers bat lower down).
            suffix: dict[int, str] = {}
            by_name: dict[str, list[int]] = {}
            for j, w in enumerate(inn.bowling):
                by_name.setdefault(w.player, []).append(j)
            for name, idx in by_name.items():
                for n, j in enumerate(sorted(idx, key=lambda j: inn.bowling[j].balls), start=1):
                    suffix[j] = name if n == 1 else f"{name} ({n})"
            for j, w in enumerate(inn.bowling):
                raw = suffix[j]
                W.append(dict(
                    match_id=m.match_id, innings_no=inn.number, team=inn.bowling_team, opposition=inn.team,
                    player=fixes.rename(raw, inn.bowling_team), balls=w.balls, runs=w.runs,
                    wickets=w.wickets, maidens=w.maidens, dots=w.dots, counted_in_balls=inn.counted_in_balls))

    frames = dict(
        matches=pd.DataFrame(M, columns=MATCH_COLUMNS),
        innings=pd.DataFrame(I, columns=INNINGS_COLUMNS),
        batting=pd.DataFrame(B, columns=BATTING_COLUMNS),
        bowling=pd.DataFrame(W, columns=BOWLING_COLUMNS),
        fielding=pd.DataFrame(F, columns=FIELDING_COLUMNS),
        fow=pd.DataFrame(FOW, columns=["match_id", "innings_no", "team", "wicket", "score"]),
        problems=pd.DataFrame(P, columns=["match_id", "source", "problem"]),
    )
    for name, types in TYPES.items():   # a career with no matches yet gets the same column types as a full one
        if frames[name].empty:
            frames[name] = frames[name].astype(types)
    _one_row_per_key(frames)
    return frames


# The columns that aren't text, by type. With rows, pandas works these out itself; with no rows every column would be
# text, and a yes/no column used to pick rows (matches[matches.knockout]) would then pick columns instead.
_B, _I, _F = "bool", "int64", "float64"
# a match's date is a pd.Timestamp of the day; the column type that makes is pandas' own choice (pandas 2 keeps it to
# the nanosecond, pandas 3 to the second), so the empty career asks pandas rather than fixing one
_DATE = str(pd.DataFrame({"d": [pd.Timestamp(datetime.date(2026, 1, 1))]}).d.dtype)
TYPES = {
    "matches": dict(date=_DATE, knockout=_B, neutral=_B, recognised=_B, margin_runs=_F, margin_wickets=_F,
                    innings_win=_B, rain=_B),
    "innings": dict(innings_no=_I, team_innings=_I, runs=_I, wickets=_I, balls=_I, all_out=_B, declared=_B,
                    counted_in_balls=_B, extras=_I, byes=_I, leg_byes=_I, wides=_I, no_balls=_I, home=_B,
                    batting_first=_B),
    "batting": dict(innings_no=_I, position=_I, did_bat=_B, runs=_I, balls=_I, fours=_I, sixes=_I, out=_B,
                    fielder_resolved=_B),
    "bowling": dict(innings_no=_I, balls=_I, runs=_I, wickets=_I, maidens=_F, dots=_F, counted_in_balls=_B),
    "fielding": dict(innings_no=_I, resolved=_B),
    "fow": dict(innings_no=_I, wicket=_I, score=_I),
}


# Every page looks rows up by these keys, so each must name exactly one row.
UNIQUE_KEYS = {
    "matches": ["match_id"],
    "innings": ["match_id", "innings_no"],
    "batting": ["match_id", "innings_no", "position"],
    "bowling": ["match_id", "innings_no", "player"],
    "fow": ["match_id", "innings_no", "wicket"],
    "fielding": ["credit_key"],
}


def _one_row_per_key(frames: dict[str, pd.DataFrame]) -> None:
    """A scorecard the parser half-understood must never leave two rows with the
    same key (that is what once broke the player page).  A bowler listed twice in
    one innings has the two lines added up; any other repeat keeps the first row.
    Either way the match is listed on the data check page."""
    source = frames["matches"].drop_duplicates("match_id").set_index("match_id").source
    extra = []
    for name, keys in UNIQUE_KEYS.items():
        df = frames[name]
        dup = df.duplicated(keys, keep=False)
        if not dup.any():
            continue
        for mid in (df[dup].match_id.unique() if "match_id" in df else []):
            extra.append(dict(match_id=mid, source=source.get(mid, ""),
                              problem=f"a {name} line appears twice in this scorecard; it is counted once"))
        if name == "bowling":
            nums = ["balls", "runs", "wickets", "maidens", "dots"]
            first = df.drop_duplicates(keys).set_index(keys)
            summed = df.groupby(keys, sort=False)[nums].sum(min_count=1)
            first[nums] = summed[nums]
            frames[name] = first.reset_index()[df.columns]
        else:
            frames[name] = df.drop_duplicates(keys).reset_index(drop=True)
    if extra:
        frames["problems"] = pd.concat([frames["problems"], pd.DataFrame(extra)], ignore_index=True)


def _super_over_text(m: Match) -> str:
    """'Bangladesh 11/2 · New Zealand 21/0' for a tie settled by a super over."""
    return " · ".join(f"{i.team} {i.total}/{i.wickets}" for i in m.super_overs)


def _all_out(inn) -> bool:
    """Bowled out: ten wickets down, or nobody left to come in.  The game prints "(9 wkts, …)" when a batter retired
    hurt and couldn't come back, but with one batter not out and nobody else to bat the innings is over: that's all
    out, not a declaration (a side declaring at 9 down has two batters not out)."""
    if inn.all_out or inn.wickets >= 10:
        return True
    left = sum(1 for b in inn.batting if b.how_out in ("not out", "dnb"))  # still able to bat
    return bool(inn.batting) and left < 2


# balls each side is allowed in a full limited-overs game
QUOTA = {"T20": 120, "T20I": 120, "The Hundred": 100, "ODI": 300, "List A": 300}


def _rain(m: Match, fmt: str, result_type: str) -> bool:
    """A limited-overs game the weather shortened: abandoned, decided by the rain rule (a margin the scores don't
    give), an innings stopped short of its overs without being bowled out (other than a chase that got there), or
    a chase won below the other side's total (a revised target).  The scorecards never say "rain", but these
    can't happen otherwise."""
    quota = QUOTA.get(fmt)
    if not quota:
        return False
    if result_type == "no result" or m.margin_note.startswith("Rain-affected"):
        return True
    if not m.innings:
        return False
    last = m.innings[-1]
    for inn in m.innings:
        chased = inn is last and result_type == "win" and m.winner == inn.team
        overs_known = inn.balls > 0 or inn.total == 0
        if overs_known and not _all_out(inn) and inn.balls < quota and not chased:
            return True
    if result_type == "win" and m.margin_wickets is not None and len(m.innings) == 2:
        first, second = m.innings
        if second.team == m.winner and second.total <= first.total:
            return True
    return False


def _corrected_result(m: Match) -> str:
    """The result line as the game printed it, marked "(DLS)" when the margin is by the rain rule (see
    parser._check_margin).  A super-over finish ("New Zealand won  (super over)") reads as the tie it was."""
    if m.super_overs and m.result_type == "tie":
        return (f"Match tied · {m.winner} won the super over" if m.winner else "Match tied (super over)")
    if m.margin_note.startswith("Rain-affected"):
        return f"{m.result} (DLS)"
    return m.result


MATCH_COLUMNS = [
    "match_id", "date", "season", "competition", "section", "event", "format", "level", "country", "stage", "knockout", "neutral",
    "recognised", "title", "series_id", "series_match_no", "series_length", "home", "away", "winner", "loser",
    "result_type", "result", "tiebreak_winner", "margin_runs", "margin_wickets", "innings_win", "margin_note",
    "super_over", "rain",
    "player_of_match",
    "batted_first", "source"]
INNINGS_COLUMNS = [
    "match_id", "innings_no", "team_innings", "team", "opposition", "runs", "wickets", "balls", "all_out",
    "declared", "counted_in_balls", "extras", "byes", "leg_byes", "wides", "no_balls", "home", "batting_first"]
BATTING_COLUMNS = [
    "match_id", "innings_no", "team", "opposition", "player", "position", "did_bat", "runs", "balls", "fours",
    "sixes", "out", "how_out", "dismissal", "bowler", "fielder", "fielder_resolved"]
BOWLING_COLUMNS = [
    "match_id", "innings_no", "team", "opposition", "player", "balls", "runs", "wickets", "maidens", "dots",
    "counted_in_balls"]
FIELDING_COLUMNS = [
    "match_id", "innings_no", "team", "opposition", "player", "printed", "kind", "batter", "bowler", "resolved",
    "credit_key"]
