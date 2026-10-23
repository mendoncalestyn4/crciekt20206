"""Everything you can search for: players, teams, sections and matches, in the order the list shows them. Shared by
the current site's search box (ui/search.py) and the new site's (Ctrl K)."""

from __future__ import annotations


def items(career) -> list[dict]:
    """[{kind, value, label, sub}]: every player (by name), every team, every section, then every match, newest
    first ('12 Mar 2026 · Australia v India · Final')."""
    out = [dict(kind="player", value=p, label=p, sub="player")
           for p in sorted(set(career.batting.player) | set(career.bowling.player))]
    m = career.matches
    out += [dict(kind="team", value=t, label=t, sub="team") for t in sorted(set(m.home) | set(m.away))]
    out += [dict(kind="section", value=s, label=s, sub="competition") for s in sorted(m.section.unique())]
    for r in m.sort_values(["date", "match_id"], ascending=False).itertuples():
        stage = f" · {r.stage}" if r.stage else ""
        out.append(dict(kind="match", value=r.match_id, label=f"{r.date:%d %b %Y} · {r.home} v {r.away}{stage}",
                        sub=r.section))
    return out
