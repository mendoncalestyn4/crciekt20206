"""More real numbers for the mixed-style mock-ups (Bento base + Broadcast + Almanack summary + Scoreboard fonts).
Run after extract_data.py; adds to its data.json and rewrites site/data.js:  python3 extract_mix.py <folder of scorecards> [<game folder>]

* pom: for every India match, the player of the match's figures and a headline about them (Almanack style),
  plus the engine's own one-line story and match report;
* series_story: the West Indies T20I series as a headline and summary, with the player of the series;
* lead_more: more T20I leaderboards (sixes, average, strike rate, economy)."""
import json
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))  # the repository
import pandas as pd

from ccstats import players as PL
from ccstats.loader import Career
from ccstats.preview import story
from ccstats.stats import Scope, player_tables, poss
from ccstats.winprob import match_report

HERE = pathlib.Path(__file__).parent
TEAM = "India"
files = [(f.name, f.read_bytes()) for f in sorted(pathlib.Path(sys.argv[1]).glob("*.txt"))]
c = Career.build("Real career", files)
m = c.matches
D = json.loads((HERE / "data.json").read_text())
QUOTA = {"T20Is": 120, "ODIs": 300}  # balls in a full innings
WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}


def num(v):
    if v is None or (isinstance(v, float) and not math.isfinite(v)):
        return None
    return int(v) if float(v).is_integer() else round(float(v), 2)


def team_of(mid, p):
    x = c.batting[(c.batting.match_id == mid) & (c.batting.player == p)]
    if len(x):
        return x.team.iloc[0]
    y = c.bowling[(c.bowling.match_id == mid) & (c.bowling.player == p)]
    return y.team.iloc[0] if len(y) else ""


def figures(mid, p):
    """What the player did in the match: batting and bowling."""
    b = c.batting[(c.batting.match_id == mid) & (c.batting.player == p) & c.batting.did_bat].sort_values("innings_no")
    w = c.bowling[(c.bowling.match_id == mid) & (c.bowling.player == p)]
    bat = None
    if len(b):
        bat = dict(runs=int(b.runs.sum()), balls=int(b.balls.sum()), fours=int(b.fours.sum()), sixes=int(b.sixes.sum()),
                   notout=bool(len(b) == 1 and not b.out.iloc[0]),
                   text=" & ".join(f"{int(x.runs)}{'' if x.out else '*'}" for x in b.itertuples()))
    bowl = None
    if len(w) and int(w.balls.sum()) > 0:
        bowl = dict(wickets=int(w.wickets.sum()), runs=int(w.runs.sum()), balls=int(w.balls.sum()),
                    text=f"{int(w.wickets.sum())}/{int(w.runs.sum())}")
    return bat, bowl


def margin_words(r):
    if pd.notna(r.margin_wickets):
        n = int(r.margin_wickets)
        return f"{n}-wicket"
    if pd.notna(r.margin_runs):
        n = int(r.margin_runs)
        return "an innings" if r.innings_win else f"{n}-run"
    return ""


def headline(mid):
    """A headline about the player of the match: what they did and what it meant."""
    r = m.set_index("match_id").loc[mid]
    p = r.player_of_match
    if not p:
        return ""
    t = team_of(mid, p)
    bat, bowl = figures(mid, p)
    inn = c.innings[c.innings.match_id == mid].sort_values("innings_no")
    rpw = inn.runs.sum() / max(inn.wickets.sum(), 1)
    bat_pts = bat["runs"] if bat else 0
    bowl_pts = bowl["wickets"] * rpw if bowl else 0
    by_bat = bat_pts >= bowl_pts
    allround = bat and bowl and bat["runs"] >= 30 and bowl["wickets"] >= 2
    if allround:
        who = f"{p} does it all: {bat['text']} and {bowl['wickets']} for {bowl['runs']}"
    elif by_bat and " & " in bat["text"]:  # batted twice (a Test): name both innings, never their sum
        who = f"{poss(p)} {bat['text'].replace(' & ', ' and ')}"
    elif by_bat:
        who = f"{poss(p)} {'unbeaten ' if bat['notout'] else ''}{bat['runs']}"
    else:
        who = f"{poss(p)} {bowl['wickets']} for {bowl['runs']}"
    won = r.winner == t
    mw = margin_words(r)
    if won and pd.notna(r.margin_wickets):
        chase = inn[inn.team == t].iloc[-1]
        spare = QUOTA.get(r.section, 0) - int(chase.balls)
        if r.section in QUOTA and not r.rain and spare >= 6:
            tail = f"with {spare // 6} overs to spare"
        elif r.section in QUOTA and not r.rain and spare > 0:
            tail = f"with {spare} ball{'s' if spare != 1 else ''} to spare"
        else:
            tail = f"by {int(r.margin_wickets)} wickets"
        what = (f"as {t} get home {tail}" if allround else f"takes {t} home {tail}" if by_bat
                else f"sets up {poss(t)} {mw} win")
    elif won:
        by = mw.replace("-run", " runs").replace("-wicket", " wickets")
        what = (f"as {t} win by {by}" if allround else f"sets up {poss(t)} {mw} win" if by_bat
                else f"bowls {t} to {('a ' if mw[0].isdigit() else '') + mw} win")
    elif r.winner:
        what = f"but {r.winner} win" if allround else f"not enough for {t}"
    else:
        word = {"draw": "a draw", "tie": "a tie", "no result": "no result"}.get(r.result_type, "the match")
        what = f"the story of {word}"
    return f"{who} {what}"


pom = {}
for res in D["results"]:
    mid = res["id"]
    r = m.set_index("match_id").loc[mid]
    p = r.player_of_match
    bat, bowl = figures(mid, p) if p else (None, None)
    pom[mid] = dict(player=p, team=team_of(mid, p) if p else "", headline=headline(mid), bat=bat, bowl=bowl,
                    story=story(c, next(m[m.match_id == mid].itertuples())), report=match_report(c, mid))
D["pom"] = pom
print("featured match:", D["match"]["id"], pom.get(D["match"]["id"], {}).get("headline"))
for k in list(pom)[:6]:
    print(" ", k, pom[k]["headline"], "|", pom[k]["story"])

# ---- the West Indies T20I series as a story
sids = [x["id"] for x in D["series"]["matches"]]
ps = PL.player_of_series(c, sids)
best = ps.iloc[0].to_dict() if len(ps) else {}
seq = [x["outcome"] for x in D["series"]["matches"]]
nw, nl = seq.count("W"), seq.count("L")
opp = D["series"]["matches"][0]["opp"]
groups = []
for o in seq:
    if groups and groups[-1][0] == o:
        groups[-1][1] += 1
    else:
        groups.append([o, 1])
parts = []
for i, (o, n) in enumerate(groups):
    verb = {"W": "won", "L": "lost"}.get(o, "drew")
    if i == len(groups) - 1 and n == 1 and len(seq) % 2 == 1 and seq[:-1].count("W") == seq[:-1].count("L") and i:
        parts.append(f"{verb} the decider")
    elif i == 0:
        parts.append(f"{verb} the first {WORDS.get(n, n)}" if n > 1 else f"{verb} the first")
    elif i == len(groups) - 1:
        parts.append(f"{verb} the last {WORDS.get(n, n)}" if n > 1 else f"{verb} the last")
    else:
        parts.append(f"{verb} the next {WORDS.get(n, n)}" if n > 1 else f"{verb} the next")
flow = (", ".join(parts[:-1]) + " and " + parts[-1]) if len(parts) > 1 else parts[0]
level_before = seq[:-1].count("W") == seq[:-1].count("L")
if nw > nl:
    head = (f"{TEAM} win the decider to take the series {nw}–{nl}" if level_before and len(seq) > 1
            else f"{TEAM} sweep {opp} {nw}–0" if nl == 0 else f"{TEAM} beat {opp} {nw}–{nl}")
elif nl > nw:
    head = f"{opp} take the series {nl}–{nw}"
else:
    head = f"Honours even: {TEAM} and {opp} share the series {nw}–{nl}"
last = D["series"]["matches"][-1]
lp = pom.get(last["id"], {})
sb, sw = D["series"]["bat"][0], D["series"]["bowl"][0]
deck = (f"{TEAM} {flow}." + (f" {poss(lp['player'])} {lp['bat']['text'] if lp.get('bat') and (not lp.get('bowl') or lp['bat']['runs'] >= 20) else lp['bowl']['text']} "
                             f"won the {'decider' if level_before else 'last match'}." if lp.get("player") else "")
        + f" {sb['player']} made the most runs ({sb['runs']}), {sw['player']} took the most wickets ({sw['wickets']}).")
D["series_story"] = dict(headline=head, deck=deck, flow=flow, w=nw, l=nl, opp=opp,
                         pos=dict(player=best.get("player", ""), team=best.get("team", ""), runs=num(best.get("runs")),
                                  wickets=num(best.get("wickets")), matches=num(best.get("matches"))))
print("series:", head, "|", deck, "| POS", D["series_story"]["pos"])

# ---- more T20I leaderboards
bt, bw, fl, bs = player_tables(c, Scope(sections=["T20Is"]), by_team=True)
keep_b = ["player", "team", "innings", "runs", "balls", "average", "strike_rate", "sixes", "fours", "high_score_text"]
keep_w = ["player", "team", "innings", "balls", "wickets", "runs", "economy", "average", "best"]
def rows(df, cols):
    return [{k: (num(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v) for k, v in zip(cols, r)}
            for r in df[cols].itertuples(index=False)]



D["lead_more"] = dict(
    sixes=rows(bt.sort_values(["sixes", "runs"], ascending=False).head(10), keep_b),
    average=rows(bt[bt.innings >= 4].sort_values("average", ascending=False).head(10), keep_b),
    strike_rate=rows(bt[bt.balls >= 60].sort_values("strike_rate", ascending=False).head(10), keep_b),
    economy=rows(bw[bw.balls >= 60].sort_values("economy").head(10), keep_w))
print("sixes:", [(x["player"], x["sixes"]) for x in D["lead_more"]["sixes"][:3]])
print("economy:", [(x["player"], x["economy"]) for x in D["lead_more"]["economy"][:3]])

# ---- a Test scorecard too (four innings), for the match summary
def overs(balls):
    balls = int(balls)
    return f"{balls // 6}" + (f".{balls % 6}" if balls % 6 else "")


def tidy(df, cols):
    """Rows as plain dicts: numbers as int or float, missing as None."""
    return [{k: (num(v) if isinstance(v, float) else (int(v) if hasattr(v, "item") and not isinstance(v, bool) and str(v).lstrip("-").isdigit() else v))
             for k, v in zip(cols, r)} for r in df[cols].itertuples(index=False)]


def scorecard(mid):
    mm = m[m.match_id == mid].iloc[0]
    inn = c.innings[c.innings.match_id == mid].sort_values("innings_no")
    cards = []
    for i in inn.itertuples():
        bt = c.batting[(c.batting.match_id == mid) & (c.batting.innings_no == i.innings_no)].sort_values("position")
        bw = c.bowling[(c.bowling.match_id == mid) & (c.bowling.innings_no == i.innings_no)]
        fw = c.fow[(c.fow.match_id == mid) & (c.fow.innings_no == i.innings_no)].sort_values("wicket")
        cards.append(dict(team=i.team, runs=int(i.runs), wickets=int(i.wickets), overs=overs(i.balls), all_out=bool(i.all_out),
                          declared=bool(i.declared), extras=int(i.extras),
                          bat=[{**x, "did_bat": bool(x["did_bat"]), "out": bool(x["out"])} for x in tidy(bt, ["player", "position", "did_bat", "how_out", "dismissal", "runs", "balls", "fours", "sixes", "out"])],
                          bowl=tidy(bw, ["player", "balls", "maidens", "runs", "wickets", "dots"]), fow=tidy(fw, ["wicket", "score"])))
    return dict(id=mid, date=mm.date.strftime("%Y-%m-%d"), home=mm.home, away=mm.away, result=mm.result, pom=mm.player_of_match,
                section=mm.section, no=num(mm.series_match_no), of=num(mm.series_length), event=mm.event, cards=cards)


test_id = next(r["id"] for r in D["results"] if r["section"] == "Tests")
D["match_test"] = scorecard(test_id)
print("test:", [(k["team"], k["runs"], k["wickets"], k["overs"]) for k in D["match_test"]["cards"]], D["match_test"]["result"])

# ---- logos drawn in the looks the engine picks today (England: a light tint of its own colours)
from ccstats import logos as LG  # noqa: E402
GAME = sys.argv[2] if len(sys.argv) > 2 else ""   # the game's folder (with editor/emblems), optional
if GAME:
    book = LG.LogoBook(LG.find([pathlib.Path(GAME)]))
    for t in D.get("logos", {}):
        lp = book.team(t) or book.comp(t)
        if lp is not None:
            D["logos"][t] = {"plain": LG.badge(lp, 160, "plain"), "dark": LG.badge(lp, 160, book.style(lp))}
    print("logos redrawn; England's look:", book.style(book.team("England")))

(HERE / "data.json").write_text(json.dumps(D, indent=1, default=str))
(HERE / "site" / "data.js").write_text("window.D = " + json.dumps(D, default=str) + ";\n")
print("written")
