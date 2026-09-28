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
import zipfile
from dataclasses import dataclass, field
from typing import Iterable

import pandas as pd

from .competitions import FIRST_CLASS, TEST, assign_seasons, assign_series, classify, fix_playoff_stages
from .parser import Match, ScorecardError, parse_scorecard, validate_match

MULTI_DAY = {TEST, FIRST_CLASS}


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
    """

    merges: dict[str, str] = field(default_factory=dict)
    splits: list[dict] = field(default_factory=list)
    credits: dict[str, str] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps({"merges": self.merges, "splits": self.splits, "credits": self.credits}, indent=1)

    @classmethod
    def from_json(cls, text: str) -> "Fixes":
        d = json.loads(text or "{}")
        return cls(d.get("merges", {}), d.get("splits", []), d.get("credits", {}))

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


def expand(files: Iterable[tuple[str, bytes]]) -> Iterable[tuple[str, bytes]]:
    """Yield (name, bytes) for every file, looking inside zips (and zips in zips)."""
    for name, data in files:
        if name.lower().endswith(".zip") or data[:4] == b"PK\x03\x04":
            try:
                with zipfile.ZipFile(io.BytesIO(data)) as zf:
                    inner = [(f"{name}/{i.filename}", zf.read(i)) for i in zf.infolist() if not i.is_dir()]
            except zipfile.BadZipFile:
                yield name, data
                continue
            yield from expand(inner)
        else:
            yield name, data


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

    # ------------------------------------------------------------ building
    @classmethod
    def build(cls, name: str, files: Iterable[tuple[str, bytes]], fixes: Fixes | None = None,
              existing: dict[str, str] | None = None) -> "Career":
        """Read files (plain .txt or zips) into a career.  `existing` are texts
        already in the career, so adding a new batch keeps what was there."""
        fixes = fixes or Fixes()
        texts: dict[str, str] = dict(existing or {})
        report: list[FileReport] = []
        parsed: dict[str, Match] = {}
        seen_ids: dict[str, str] = {}
        seen_sigs: dict[tuple, str] = {}

        def admit(source: str, text: str, is_new: bool) -> None:
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
        for source, data in expand(files):
            if not source.lower().endswith(".txt"):
                report.append(FileReport(source, "skipped", "not a .txt scorecard"))
                continue
            admit(source, decode(data), is_new=True)
        texts = {s: t for s, t in texts.items() if s in parsed}
        tables = build_tables(list(parsed.values()), fixes)
        return cls(name, texts, fixes, report, **tables)

    def add_files(self, files: Iterable[tuple[str, bytes]]) -> "Career":
        return Career.build(self.name, files, self.fixes, existing=self.texts)

    def with_fixes(self, fixes: Fixes) -> "Career":
        c = Career.build(self.name, [], fixes, existing=self.texts)
        c.report = self.report
        return c

    # ------------------------------------------------------------ packs
    def to_pack(self) -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(PACK_INFO, json.dumps({"name": self.name, "version": 1}))
            zf.writestr(PACK_FIXES, self.fixes.to_json())
            used = set()
            for source, text in self.texts.items():
                leaf = re.sub(r"[^\w.\-]+", "_", source.split("/")[-1]) or "scorecard.txt"
                while leaf in used:
                    leaf = "_" + leaf
                used.add(leaf)
                zf.writestr(PACK_TEXTS + leaf, text)
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
            fixes = Fixes.from_json(zf.read(PACK_FIXES).decode()) if PACK_FIXES in zf.namelist() else Fixes()
            files = [(n[len(PACK_TEXTS):], zf.read(n)) for n in zf.namelist() if n.startswith(PACK_TEXTS)]
        c = cls.build(info.get("name", "My career"), files, fixes)
        return c


# --------------------------------------------------------------------------- #
# Tables
# --------------------------------------------------------------------------- #


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
            format=c.format, level=c.level, country=c.country, stage=stages[i], knockout=c.knockout,
            neutral=c.neutral, recognised=c.recognised, title=m.title, series_id=series[i],
            series_match_no=m.series_match_no, series_length=m.series_length,
            home=m.team1, away=m.team2, winner=winner,
            loser=(m.team2 if winner == m.team1 else m.team1) if winner else "",
            result_type=result_type, result=m.result, tiebreak_winner=tiebreak,
            margin_runs=m.margin_runs, margin_wickets=m.margin_wickets, innings_win=m.innings_win,
            player_of_match=fixes.rename(m.player_of_match, ""), batted_first=batted_first, source=m.source))
        for p in validate_match(m):
            P.append(dict(match_id=m.match_id, source=m.source, problem=p))
        last_no = len(m.innings)
        for inn in m.innings:
            declared = multi and not inn.all_out and inn.wickets < 10 and inn.number < last_no
            I.append(dict(
                match_id=m.match_id, innings_no=inn.number, team_innings=inn.team_innings, team=inn.team,
                opposition=inn.bowling_team, runs=inn.total, wickets=inn.wickets, balls=inn.balls,
                all_out=inn.all_out or inn.wickets >= 10, declared=declared or inn.declared,
                counted_in_balls=inn.counted_in_balls, extras=inn.extras, byes=inn.byes, leg_byes=inn.leg_byes,
                wides=inn.wides, no_balls=inn.no_balls,
                home=inn.team == m.team1 and not c.neutral, batting_first=inn.team == batted_first))
            for w, score in inn.fow:
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
                if b.how_out in ("caught", "stumped") and b.fielder:
                    F.append(dict(
                        match_id=m.match_id, innings_no=inn.number, team=inn.bowling_team,
                        opposition=inn.team, player=fielder if resolved else "", printed=b.fielder if not resolved else fielder,
                        kind=b.how_out, batter=player, bowler=bowler, resolved=resolved, credit_key=key))
            for w in inn.bowling:
                W.append(dict(
                    match_id=m.match_id, innings_no=inn.number, team=inn.bowling_team, opposition=inn.team,
                    player=fixes.rename(w.player, inn.bowling_team), balls=w.balls, runs=w.runs,
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
    return frames


MATCH_COLUMNS = [
    "match_id", "date", "season", "competition", "format", "level", "country", "stage", "knockout", "neutral",
    "recognised", "title", "series_id", "series_match_no", "series_length", "home", "away", "winner", "loser",
    "result_type", "result", "tiebreak_winner", "margin_runs", "margin_wickets", "innings_win", "player_of_match",
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
