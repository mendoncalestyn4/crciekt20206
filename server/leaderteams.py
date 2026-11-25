"""Team leaders (stage 3, under Teams): each team's top two by share of its runs and of its wickets, one competition
and season at a time (ccstats/teamleaders.py has the sums)."""

from __future__ import annotations

from ccstats import teamleaders as TL

from . import styleguide as SG
from .cache import kept
from .teampage import choices, secs_of


def page(career, q: dict, mine: list[str]) -> dict:
    ch = choices(career)
    if not ch:
        return SG.clean(dict(choices=[], none=SG.NO_MATCHES))
    every = [c["section"] for c in ch]
    asked = [s for s in secs_of(q.get("section", "")) if s in set(every)]
    sec = asked[0] if asked else next((c["section"] for c in ch if set(mine) & set(c["teams"])), every[0])
    seasons = next(c["seasons"] for c in ch if c["section"] == sec)
    season = str(q.get("season", ""))
    season = season if season in seasons else ""
    m = career.matches[career.matches.section == sec]
    real = next((s for s in m.season.unique() if str(s) == season), None) if season else None
    here = m[m.season == real] if season else m
    teams = sorted(set(here.home) | set(here.away))
    # all teams: yours first, then A to Z (answer 13)
    teams = [t for t in mine if t in set(teams)] + [t for t in teams if t not in set(mine)]
    raw = q.get("teams")
    if raw == "all":
        picked = []
    else:
        picked = [t for t in str(raw or "").split("|") if t in set(teams)]
        if not picked:   # opens on your team here, or the first team
            picked = [next((t for t in mine if t in set(teams)), teams[0])] if teams else []
    show = picked or teams
    blocks = [dict(team=t, yours=t in set(mine), **kept(career, ("team_leaders", sec, season, t), lambda t=t: TL.leaders(career, sec, real, t)))
              for t in show]
    for b in blocks:
        b["runs"] = [dict(r, share=f"{r['share']:.1f}%") for r in b["runs"]]
        b["wickets"] = [dict(r, share=f"{r['share']:.1f}%") for r in b["wickets"]]
        if not b["team_wickets"]:
            b["no_wickets"] = f"{b['team']} have no wickets yet here."
    return SG.clean(dict(choices=[dict(section=c["section"], matches=c["matches"]) for c in ch], section=sec, seasons=seasons,
                         season=season, teams=teams, picked=picked, all=not picked, blocks=blocks,
                         note=("Share of the team's runs off the bat (extras are nobody's, so the batters' shares add up to "
                               "100%) and of the wickets its bowlers took, in this competition and season; matches played "
                               "for the team, batted or not. Crossed out: no game for the team here in its last two seasons. "
                               "Equal shares go to more matches, then A to Z.")))
