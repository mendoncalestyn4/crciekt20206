"""A demo page (not linked from the rail): ideas 2, 3, 5 and 7 (attributes out of 20, the scout report, squad
depth, the inbox) next to the marks and the replacement advice, with the career's own numbers, to approve before
they're built into My team and the Player page."""

from __future__ import annotations

from ccstats import attributes as AT
from ccstats import depth as DP

from . import myteam
from . import styleguide as SG
from .cache import kept


def page(career, team: str, section: str, players: list[str], mine: list[str]) -> dict:
    played = set(career.matches.home) | set(career.matches.away)
    if team not in played:
        raise KeyError(team)
    rep = kept(career, ("demo-report", team), lambda: myteam.report_card(career, team))
    secs = list(dict.fromkeys(career.matches[(career.matches.home == team) | (career.matches.away == team)].section))
    section = section if section in secs else (rep["section"] if rep else secs[0])
    out: dict = dict(team=team, mine=team in mine, section=section, sections=secs, report=rep, missing={})

    def piece(name, fn):
        try:
            out[name] = SG.clean(fn())
        except Exception as e:  # noqa: BLE001 - one part that can't be worked out never stops the others
            out[name] = None
            out["missing"][name] = f"Couldn't be worked out ({type(e).__name__}: {e})"

    piece("depth", lambda: kept(career, ("demo-depth", team, section), lambda: DP.squad_depth(career, team, section)))
    piece("inbox", lambda: kept(career, ("demo-inbox", team), lambda: DP.inbox(career, team)))
    piece("players", lambda: [dict(player=p, attributes=AT.player(career, section, p), report=AT.scout_report(career, section, p))
                              for p in players])
    return out
