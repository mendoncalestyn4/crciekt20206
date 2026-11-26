"""Data check (stage 4): the current site's Data check page (views/data_check.py) in six tabs (your answer 15 of 26
November): Shared names, Player with two names, Games left out, Scorecards, Copies, Your changes. Team catches is gone
(no fielding). A change is shown first as a preview of what it does to the numbers (your pick), made only by your
click, with a backup of the career made before it; while every number is worked out again the site stays usable. The
sums are in the engine (ccstats/datacheck.py, checks.py); this only turns them into what the page shows."""

from __future__ import annotations

import pandas as pd

from ccstats import checks
from ccstats import datacheck as DC

from .cache import kept

TABS = ["Shared names", "Player with two names", "Games left out", "Scorecards", "Copies", "Your changes"]
INTRO = ("The scorecards leave a few things unclear. Each one is explained below, with a one-click fix where there's a "
         "safe answer. Nothing changes until you click, you see what a change does to the numbers first, and every change "
         "can be undone under Your changes.")


def page(career, q: dict, state: dict) -> dict:
    tab = q.get("tab", "") if q.get("tab", "") in TABS else TABS[0]
    sm = kept(career, ("dc-summary",), lambda: DC.summary(career))
    out = dict(tabs=TABS, tab=tab, intro=INTRO, summary=sm, state=dict(state))
    out["body"] = kept(career, ("dc-tab", tab), lambda: _body(career, tab))
    return out


def _body(career, tab: str) -> dict:
    if tab == "Shared names":
        auto = career.auto_splits
        by = []
        for p, g in auto.groupby("player", sort=True):
            by.append(dict(player=p, keep=g.keep.iloc[0],
                           others=[dict(team=r.team, new_name=r.new_name, games=int(r.games), where=r.where) for r in g.itertuples()]))
        shared = checks.shared_names(career)
        still = [dict(player=r.player, keep=r.keep, separate=list(r.separate),
                      played=" and ".join(f"{t} ({r.games[t]} game{'s' if r.games[t] != 1 else ''})" for t in r.teams),
                      where=", ".join(r.where)) for r in shared.itertuples()]
        return dict(
            explain=("**Two different players with the same name.** The game prints only an initial and surname, so two "
                     "players can end up with the same name, like R Patel at Leicestershire and R Patel at Surrey. A "
                     "player can't play for two teams in the same season of a competition, so the site keeps each such "
                     "name apart by itself: the name stays with the team it played most games for, and the player at the "
                     "other team gets the team added to their name. A name that only changed team between seasons (a "
                     "transfer) stays one player."),
            auto=by, still=still, kept_together=list(career.fixes.keep_together),
            none="" if by or still else "No name is used by two players.",
            players=DC.players(career))
    if tab == "Player with two names":
        mg = checks.merge_suggestions(career)
        return dict(
            explain=("**One player under two names.** Sometimes the same player shows up under two slightly different "
                     "names. The site looks for names that may be one player: the same initial and surname, a missing or "
                     "extra initial, a surname spelt nearly the same on the same team, or a move between teams with the "
                     "very same surname, and never two names that played in the same match. Pairs that are beyond doubt "
                     "are joined by themselves (the same team, one name straight after the other, no other candidate); "
                     "each is listed here with an Undo. The rest wait for your click."),
            pairs=[dict(keep=r.keep, other=r.other, keep_matches=int(r.keep_matches), other_matches=int(r.other_matches),
                        teams=r.teams, why=r.why) for r in mg.itertuples()],
            joined=[dict(other=r.other, keep=r.keep, team=r.team, why=r.why, other_matches=int(r.other_matches),
                         keep_matches=int(r.keep_matches)) for r in career.auto_joins.itertuples()],
            none="" if len(mg) or len(career.auto_joins) else "No player appears under two names.",
            players=DC.players(career))
    if tab == "Games left out":
        left = career.leftovers
        conf = checks.replay_conflicts(career)
        mm = career.matches.sort_values("date", ascending=False)
        return dict(
            explain=("**Games from an earlier playthrough.** When you reload a save and play part of a season again, the "
                     "game saves each replayed match over its old file. But a match with different teams gets a new file, "
                     "so the old game stays in your Scorecards folder. The site spots these from when each file was saved "
                     "and leaves them out of every stat. Nothing to do, unless one of them should count."),
            left=[dict(match_id=r.match_id, text=f"{pd.Timestamp(r.date):%d %b %Y} · {r.competition}{' · ' + r.stage if r.stage else ''} · "
                       f"{r.home} v {r.away}", result=r.result, reason=r.reason) for r in left.itertuples()],
            none="" if len(left) else "Every match counts: none are from an earlier playthrough.",
            conflicts=[dict(match_id=r.match_id, text=f"{r.group} · {pd.Timestamp(r.date):%d %b %Y} · {r.stage} · {r.home} v {r.away} · {r.result}")
                       for r in conf.itertuples()],
            conflict_warn=("These knockout games can't all be from one playthrough (two finals, or a team in two knockouts "
                           "on the same day), and their files came without the save times that tell which is older. Leave "
                           "out the ones from the earlier playthrough.") if len(conf) else "",
            matches=[dict(v=r.match_id, label=f"{r.date:%d %b %Y} · {r.home} v {r.away} · {r.event} · {r.result}") for r in mm.itertuples()])
    if tab == "Scorecards":
        failed = [dict(file=r.source, why=r.message) for r in getattr(career, "report", []) if r.status == "failed"]
        return dict(
            explain=("**Every scorecard is checked when it's read:** the batters' runs plus extras make the total, the "
                     "bowlers' runs, overs and wickets match the innings, and the dismissals match the fall of wickets. "
                     "A mistake the game makes in its own scorecards is put right by the site (when the card proves the "
                     "answer, or else by the closest fair guess, so every total adds up), with a note on that match's "
                     "own page. Only a file that isn't a scorecard at all is listed here."),
            failed=failed, failed_line=(f"{len(failed)} file(s) couldn't be read as a scorecard (empty or broken), so "
                                        "they aren't in any stat." if failed else ""),
            ok="" if failed else f"✓ All {len(career.matches):,} scorecards add up. Nothing needs you here.")
    if tab == "Copies":
        cp = DC.copies(career)
        return dict(explain=("**A match saved twice.** The same match (same teams, date and scores) saved under two file "
                             "names is counted once; the copy is listed here."),
                    copies=cp, none="" if cp else "No match is saved twice.")
    return dict(changes=DC.your_changes(career), none="" if DC.your_changes(career) else "You haven't changed anything yet.")
