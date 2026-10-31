"""Made-up careers for tests that need numbers worked out by hand: a few matches written straight into the engine's
tables (no scorecard files), with only what the code under test reads."""

from __future__ import annotations

from types import SimpleNamespace

import pandas as pd


class Book:
    def __init__(self):
        self.m, self.i, self.b, self.w, self.f = [], [], [], [], []

    def match(self, mid: str, date: str, home: str, away: str, *, section: str = "Tests", fmt: str = "Test",
              level: str = "International", country: str = "", competition: str = "", series: str = "",
              no: float | None = None, length: float | None = None, winner: str = "", result: str = "win",
              rain: bool = False, event: str = "", season: str = "", stage: str = "", neutral: bool = False):
        self.m.append(dict(match_id=mid, date=pd.Timestamp(date), season=season or date[:4],
                           competition=competition or section, section=section, event=event or section, format=fmt,
                           level=level, country=country, stage=stage, knockout=bool(stage), neutral=neutral,
                           series_id=series, series_match_no=no, series_length=length, home=home, away=away,
                           winner=winner, loser=(away if winner == home else home) if winner else "", result_type=result,
                           rain=rain, source=f"{mid}.txt"))
        return self

    def inns(self, mid: str, no: int, team: str, opp: str, bats, extras: int = 0, balls: int | None = None):
        """`bats`: (player, runs, balls, out) in batting order; the total is their runs plus `extras`."""
        runs = sum(r for _, r, _, _ in bats) + extras
        wkts = sum(1 for *_, o in bats if o)
        for pos, (p, r, bl, o) in enumerate(bats, start=1):
            self.b.append(dict(match_id=mid, innings_no=no, team=team, opposition=opp, player=p, position=pos,
                               did_bat=True, runs=r, balls=bl, fours=0, sixes=0, out=o,
                               how_out="caught" if o else "not out", dismissal="", bowler="", fielder="",
                               fielder_resolved=False))
        self.i.append(dict(match_id=mid, innings_no=no, team=team, opposition=opp, runs=runs, wickets=wkts,
                           balls=balls if balls is not None else sum(bl for _, _, bl, _ in bats)))
        return self

    def bowl(self, mid: str, no: int, team: str, opp: str, spells):
        """`spells`: (player, balls, runs, wickets[, dots]) for the side bowling in innings `no`, in the order they came on."""
        for p, bl, r, wk, *dots in spells:
            self.w.append(dict(match_id=mid, innings_no=no, team=team, opposition=opp, player=p, balls=bl, runs=r,
                               wickets=wk, maidens=0, dots=dots[0] if dots else 0))
        return self

    def catch(self, mid: str, no: int, team: str, player: str, kind: str = "caught"):
        self.f.append(dict(match_id=mid, innings_no=no, team=team, opposition="", player=player, printed=player,
                           kind=kind, batter="", bowler="", resolved=True, credit_key=""))
        return self

    def career(self, name: str = "Made up"):
        f_cols = ["match_id", "innings_no", "team", "opposition", "player", "printed", "kind", "batter", "bowler",
                  "resolved", "credit_key"]
        w_cols = ["match_id", "innings_no", "team", "opposition", "player", "balls", "runs", "wickets", "maidens", "dots"]
        return SimpleNamespace(name=name, matches=pd.DataFrame(self.m), innings=pd.DataFrame(self.i),
                               batting=pd.DataFrame(self.b), bowling=pd.DataFrame(self.w, columns=w_cols),
                               fielding=pd.DataFrame(self.f, columns=f_cols), times={})


def side(prefix: str, runs: list[int], outs: int = 10, balls_each: int = 30):
    """Eleven batters called prefix1..prefix11 with these runs (padded with 0s); the first `outs` are out."""
    runs = list(runs) + [0] * (11 - len(runs))
    return [(f"{prefix}{k + 1}", r, balls_each, k < outs) for k, r in enumerate(runs)]
