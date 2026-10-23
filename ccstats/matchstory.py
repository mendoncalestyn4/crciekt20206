"""A match and a series told in a line, from the scorecards.

* figures / pom_headline: what the player of the match did, and a headline about it ("D Jurel's unbeaten 97 takes
  India home with 7 overs to spare");
* series_story: how a series went for your team ("India win the decider to take the series 3–2"), with a summary and
  the player of the series.

The new site's match summary and series pages show these; the match report under a headline is winprob.match_report."""

from __future__ import annotations

import pandas as pd

from .stats import poss

BALLS = {"T20": 120, "T20I": 120, "ODI": 300, "List A": 300, "The Hundred": 100}   # a full innings, by format
WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven"}


def overs_text(balls: int) -> str:
    """Balls as overs: 51 -> '8.3'."""
    return f"{balls // 6}" + (f".{balls % 6}" if balls % 6 else "")


def team_of(career, match_id: str, player: str) -> str:
    """The team a player played for in a match ('' if the scorecards don't have them)."""
    for df in (career.batting, career.bowling):
        x = df[(df.match_id == match_id) & (df.player == player)]
        if len(x):
            return str(x.team.iloc[0])
    return ""


def figures(career, match_id: str, player: str) -> dict:
    """What a player did in a match: {'bat': {...} or None, 'bowl': {...} or None}. A Test's two innings are kept
    apart in the text ('56 & 143'), never added up."""
    b = career.batting[(career.batting.match_id == match_id) & (career.batting.player == player)
                       & career.batting.did_bat].sort_values("innings_no")
    w = career.bowling[(career.bowling.match_id == match_id) & (career.bowling.player == player)]
    bat = None
    if len(b):
        bat = dict(runs=int(b.runs.sum()), balls=int(b.balls.sum()), fours=int(b.fours.sum()), sixes=int(b.sixes.sum()),
                   innings=len(b), notout=bool(len(b) == 1 and not b.out.iloc[0]),
                   text=" & ".join(f"{int(x.runs)}{'' if x.out else '*'}" for x in b.itertuples()))
    bowl = None
    if len(w) and int(w.balls.sum()) > 0:
        bowl = dict(wickets=int(w.wickets.sum()), runs=int(w.runs.sum()), balls=int(w.balls.sum()),
                    text=f"{int(w.wickets.sum())}/{int(w.runs.sum())}")
    return dict(bat=bat, bowl=bowl)


def _a(phrase: str) -> str:
    """'a 34-run' or 'an 80-run' (an 8, 11 or 18 is said with a vowel); 'an innings' stays as it is."""
    if phrase.startswith("an "):
        return phrase
    lead = phrase.split("-")[0]
    return ("an " if lead.startswith("8") or lead in ("11", "18") else "a ") + phrase


def _margin(r) -> tuple[str, str]:
    """('6-wicket', '6 wickets') or ('18-run', '18 runs') or ('an innings', 'an innings')."""
    if pd.notna(r.margin_wickets):
        n = int(r.margin_wickets)
        return f"{n}-wicket", f"{n} wicket{'s' if n != 1 else ''}"
    if pd.notna(r.margin_runs):
        if r.innings_win:
            return "an innings", "an innings"
        n = int(r.margin_runs)
        return f"{n}-run", f"{n} run{'s' if n != 1 else ''}"
    return "", ""


def pom_headline(career, match_id: str) -> str:
    """A headline about the player of the match: what they did and what it meant. '' when there's no player of the
    match."""
    r = career.matches.set_index("match_id").loc[match_id]
    p = r.player_of_match
    if not p:
        return ""
    t = team_of(career, match_id, p)
    f = figures(career, match_id, p)
    bat, bowl = f["bat"], f["bowl"]
    if not t or (bat is None and bowl is None):            # the scorecards can't place them: say just that much
        return f"{p} is player of the match" + (f" as {r.winner} win" if r.winner else "")
    inn = career.innings[career.innings.match_id == match_id].sort_values("innings_no")
    per_wicket = inn.runs.sum() / max(inn.wickets.sum(), 1)  # a wicket is worth this many runs in this match
    by_bat = (bat["runs"] if bat else 0) >= (bowl["wickets"] * per_wicket if bowl else 0)
    allround = bool(bat and bowl and bat["runs"] >= 30 and bowl["wickets"] >= 2)
    twice = bool(bat and bat["innings"] > 1)
    if allround and twice:
        who = f"{p} does it all: {bat['text'].replace(' & ', ' and ')} with the bat, {bowl['wickets']} for {bowl['runs']} with the ball,"
    elif allround:
        who = f"{p} does it all: {bat['text']} and {bowl['wickets']} for {bowl['runs']}"
    elif by_bat and twice:                                 # batted twice (a Test): both innings, never their sum
        who = f"{poss(p)} {bat['text'].replace(' & ', ' and ')}"
    elif by_bat:
        who = f"{poss(p)} {'unbeaten ' if bat['notout'] else ''}{bat['runs']}"
    else:
        who = f"{poss(p)} {bowl['wickets']} for {bowl['runs']}"
    adj, words = _margin(r)
    take, set_up = ("take", "set up") if by_bat and twice and not allround else ("takes", "sets up")   # 91 and 60 take
    if r.winner == t and pd.notna(r.margin_wickets):        # won chasing
        quota = BALLS.get(r.format)
        chase = inn[inn.team == t]
        spare = quota - int(chase.balls.iloc[-1]) if quota and len(chase) else 0
        o, b = divmod(spare, 6)
        if not quota or r.rain or spare <= 0:               # a rain-cut chase or one won off the last ball
            tail = f"by {words}"
        elif r.format == "The Hundred" or (b and spare < 60):   # the Hundred counts balls, not overs
            tail = f"with {spare} ball{'s' if spare != 1 else ''} to spare"
        elif b:                                             # 12.1 overs left: never round it down to 12
            tail = f"with more than {o} overs to spare"
        else:
            tail = f"with {o} over{'s' if o != 1 else ''} to spare"
        what = (f"as {t} get home {tail}" if allround else f"{take} {t} home {tail}" if by_bat
                else f"{set_up} {poss(t)} {adj} win")
    elif r.winner == t:                                     # won batting first, or by an innings
        what = (f"as {t} win by {words}" if allround else f"{set_up} {poss(t)} {adj} win" if by_bat and adj
                else f"bowls {t} to {_a(adj)} win" if adj else f"wins it for {t}")
    elif r.winner:
        what = f"but {r.winner} win" if allround else f"not enough for {t}"
    else:
        what = {"draw": "in a drawn match", "tie": "in a tied match", "no result": "in a match with no result"}.get(
            r.result_type, "")
        if r.result_type == "tie" and r.tiebreak_winner:
            what += f", won by {r.tiebreak_winner} in the super over"
    return f"{who} {what}".strip()


def _names(totals: pd.Series) -> str:
    """Who is on top ('K Rabada and W Mulder' when two share it, '4 players' past three)."""
    top = sorted(totals[totals == totals.max()].index)
    return (top[0] if len(top) == 1 else " and ".join([", ".join(top[:-1]), top[-1]]) if len(top) <= 3
            else f"{len(top)} players")


def series_story(career, ids, team: str) -> dict:
    """How a series went for your team: a headline, a short summary, the run of results, the player of the series.
    ids are the series' matches; a series still going says who leads it."""
    from .players import player_of_series
    m = career.matches[career.matches.match_id.isin(ids)].sort_values(["date", "match_id"])
    if m.empty or not ((m.home == team) | (m.away == team)).all():
        raise ValueError(f"{team} didn't play every match given")
    others = (set(m.home) | set(m.away)) - {team}
    if len(others) != 1 or m.series_id.nunique() != 1:
        raise ValueError("give the matches of one series between two teams")
    opp = others.pop()
    seq = ["W" if w == team else "L" if w == opp else "D" for w in m.winner]
    nw, nl = seq.count("W"), seq.count("L")
    length = m.series_length.dropna()
    complete = not len(length) or len(m) >= int(length.max())
    level_before = seq[:-1].count("W") == seq[:-1].count("L")
    decider = complete and len(seq) > 1 and level_before and seq[-1] != "D"
    groups: list[list] = []
    for o in seq:
        if groups and groups[-1][0] == o:
            groups[-1][1] += 1
        else:
            groups.append([o, 1])
    parts = []
    for i, (o, n) in enumerate(groups):
        verb = {"W": "won", "L": "lost"}.get(o, "drew")
        count = f" {WORDS.get(n, n)}" if n > 1 else ""
        if i == len(groups) - 1 and n == 1 and decider and i:
            parts.append(f"{verb} the decider")
        elif len(groups) == 1 and complete and n > 1:      # the same every time: 'lost all three'
            parts.append(f"{verb} {'both' if n == 2 else 'all ' + WORDS.get(n, str(n))}")
        elif i == 0:
            parts.append(f"{verb} the first{count}")
        elif i == len(groups) - 1:
            parts.append(f"{verb} the last{count}" if complete else f"{verb} the latest{count}")
        else:
            parts.append(f"{verb} the next{count}")
    flow = (", ".join(parts[:-1]) + " and " + parts[-1]) if len(parts) > 1 else parts[0]
    if not complete:
        head = (f"{team} lead {opp} {nw}–{nl}" if nw > nl else f"{opp} lead {team} {nl}–{nw}" if nl > nw
                else f"{team} and {opp} level at {nw}–{nl}")
    elif nw > nl:
        head = (f"{team} win the decider to take the series {nw}–{nl}" if decider
                else f"{team} sweep {opp} {nw}–0" if nl == 0 and nw > 1 else f"{team} beat {opp} {nw}–{nl}")
    elif nl > nw:
        head = f"{opp} take the series {nl}–{nw}"
    else:
        head = f"{team} and {opp} share the series {nw}–{nl}"
    deck = [f"{team} {flow}."]
    last = m.iloc[-1]
    if last.player_of_match and decider:
        f = figures(career, last.match_id, last.player_of_match)
        did = (f["bat"]["text"] if f["bat"] and (not f["bowl"] or f["bat"]["runs"] >= 20)
               else f["bowl"]["text"] if f["bowl"] else "")
        if did:
            deck.append(f"{poss(last.player_of_match)} {did} won the decider.")
    bat = career.batting[career.batting.match_id.isin(ids) & career.batting.did_bat].groupby("player").runs.sum()
    wk = career.bowling[career.bowling.match_id.isin(ids)].groupby("player").wickets.sum()
    most = [f"{_names(t)} {verb} ({int(t.max())})" for t, verb in ((bat, "made the most runs"), (wk, "took the most wickets"))
            if len(t) and t.max() > 0]
    if most:
        deck.append(", ".join(most) + ".")
    ps = player_of_series(career, list(m.match_id))
    best = ps.iloc[0] if len(ps) else None
    return dict(headline=head, deck=" ".join(deck), flow=flow, won=nw, lost=nl, opponent=opp, complete=complete,
                results=seq, player_of_series=None if best is None else dict(
                    player=str(best.player), team=str(best.team), runs=int(best.runs), wickets=int(best.wickets),
                    matches=int(best.matches)))
