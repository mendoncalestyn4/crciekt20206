"""Real numbers from the test career for the fresh-look mock-ups (India's view). Writes data.json next to this file."""
import json
import math
import pathlib
import sys

sys.path.insert(0, "/home/user/crciekt20206")
import numpy as np
import pandas as pd

from ccstats import myteam as MT
from ccstats import partnerships as PT
from ccstats import playerdeep as PD
from ccstats.local import CareerStore
from ccstats.rankings import team_elo
from ccstats.stats import Scope, player_tables

HERE = pathlib.Path(__file__).parent
HOME = pathlib.Path("/tmp/claude-0/-home-user-crciekt20206/db8ebe3d-6d6c-58e2-9ecc-4739d2cc52d6/scratchpad/bg/homes/India")
TEAM = "India"
if len(sys.argv) > 1:  # a folder of scorecards (the user's own career)
    from ccstats.loader import Career
    files = [(f.name, f.read_bytes()) for f in sorted(pathlib.Path(sys.argv[1]).glob("*.txt"))]
    c = Career.build("Real career", files)
else:
    c, s = CareerStore(HOME).load("My career")
m = c.matches


def clean(v):
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating, float)):
        return None if not math.isfinite(float(v)) else round(float(v), 2)
    if isinstance(v, (pd.Timestamp,)):
        return v.strftime("%Y-%m-%d")
    return v


def rows(df, cols):
    return [{k: clean(r[k]) for k in cols} for _, r in df.iterrows()]


out = {}
# ---- the banner: record, Elo, rank per format
ban = []
for b in MT.banner(c, TEAM):
    rec = b["record"]
    ban.append(dict(section=b["section"], season=b["season"], elo=clean(b["elo"]), moved=clean(b["moved"]),
                    rank=b["rank"], teams=b["teams"], record={k: clean(v) for k, v in dict(rec).items()}))
out["banner"] = ban

# ---- recent results (newest first)
mine = m[(m.home == TEAM) | (m.away == TEAM)].sort_values(["date", "match_id"])
res = []
for r in mine.itertuples():
    opp = r.away if r.home == TEAM else r.home
    inn = c.innings[c.innings.match_id == r.match_id]
    def score(t):
        x = inn[inn.team == t]
        return " & ".join(f"{int(i.runs)}" + ("" if i.all_out else f"/{int(i.wickets)}") + ("d" if i.declared else "")
                          for i in x.itertuples())
    outcome = "W" if r.winner == TEAM else "L" if r.winner == opp else ("NR" if r.result_type == "no result" else "D")
    res.append(dict(id=r.match_id, date=clean(r.date), section=r.section, opp=opp, home=r.home == TEAM, outcome=outcome,
                    result=r.result, us=score(TEAM), them=score(opp), pom=r.player_of_match,
                    no=clean(r.series_match_no), of=clean(r.series_length)))
out["results"] = res[::-1]

# ---- squads per format (this season)
sq = {}
for sec in ("ODIs", "T20Is", "Tests"):
    season = MT.latest_season(c, TEAM, sec)
    d = MT.squad(c, TEAM, sec, season)
    sq[sec] = rows(d.head(14), ["player", "games", "runs", "average", "strike_rate", "wickets", "economy", "last5", "form"])
out["squad"] = sq

# ---- Elo history for the ODI teams (bump / race charts)
table, hist = team_elo(c, "ODIs")
hist = hist.sort_values(["date", "match_id"])
teams = list(table.team)
# rank of every team after each date
dates = sorted(hist.date.unique())
rating = {t: 1500.0 for t in teams}
seen = set()
snaps = []
for d in dates:
    for r in hist[hist.date == d].itertuples():
        rating[r.team] = r.after
        seen.add(r.team)
    order = sorted(teams, key=lambda t: -rating[t])
    snaps.append(dict(date=clean(pd.Timestamp(d)), elo={t: round(rating[t], 1) for t in teams},
                      rank={t: order.index(t) + 1 for t in teams}))
out["elo_odis"] = dict(teams=teams, table=rows(table, ["team", "elo", "played", "peak"]), snaps=snaps)

# ---- players: ODIs section tables, percentiles for India's batters
scope = Scope(sections=["ODIs"])
bat, bowl, fld, base = player_tables(c, scope)
out["bat_cols"] = list(bat.columns)
q = bat[bat.innings >= 5].copy() if "innings" in bat else bat.copy()
q = q.assign(fifty_rate=q.fifty_plus / q.innings, six_rate=q.sixes / q.balls.clip(lower=1) * 100,
             safe=1 - q.ducks / q.innings)
stats = {"Runs": "runs", "Average": "average", "Strike rate": "strike_rate", "Boundary %": "boundary_pct",
         "50+ scores": "fifty_rate", "Six hitting": "six_rate", "Runs above average": "runs_above_average"}
have = {k: v for k, v in stats.items() if v in q.columns}
out["radar_stats"] = list(have)
pct = {}
out["radar_pool"] = int(len(q))
for p in q.player:
    r = q[q.player == p].iloc[0]
    pct[p] = {k: round(float((q[v] <= r[v]).mean() * 100), 0) for k, v in have.items()}
ind = bat[bat.player.isin(set(c.batting[(c.batting.team == TEAM)].player))]
out["india_bat_odis"] = rows(ind.sort_values("runs", ascending=False).head(10), [x for x in ["player", "innings", "runs", "average", "strike_rate", "boundary_share", "fifty_rate", "six_rate", "hundreds", "fifties"] if x in ind.columns])
out["radar"] = {p: pct[p] for p in list(ind.sort_values("runs", ascending=False).player.head(6)) if p in pct}
out["base_odis"] = {k: clean(v) for k, v in vars(base).items()}

# ---- match impact per match for India's top batter (form calendar)
ids_all = list(m.match_id)
imp = PD.match_impact(c, list(mine.match_id))
star = out["india_bat_odis"][0]["player"]
me = imp[(imp.player == star) & (imp.team == TEAM)].merge(m[["match_id", "section"]], on="match_id")
out["impact_star"] = dict(player=star, games=rows(me, ["match_id", "date", "section", "opponent", "impact", "runs", "wickets", "won"]))
team_imp = imp[imp.team == TEAM].merge(m[["match_id", "section"]], on="match_id")
out["impact_team"] = rows(team_imp, ["match_id", "date", "section", "player", "impact", "runs", "wickets", "won"])

# ---- how the star scores and gets out (ODIs)
b = c.batting[(c.batting.player == star) & c.batting.did_bat & c.batting.match_id.isin(m[m.section == "ODIs"].match_id)]
fours, sixes, runs = int(b.fours.sum()), int(b.sixes.sum()), int(b.runs.sum())
out["star_runs"] = dict(player=star, runs=runs, fours=fours, sixes=sixes, from4=fours * 4, from6=sixes * 6,
                        running=runs - fours * 4 - sixes * 6, balls=int(b.balls.sum()), innings=len(b),
                        outs=int(b.out.sum()), how=b[b.out].how_out.value_counts().to_dict(),
                        scores=[int(x) for x in b.runs], notout=[not bool(x) for x in b.out])

# ---- partnerships in India's latest ODI
last_odi = mine[mine.section == "ODIs"].iloc[-1]
st = PT.stands(c, [last_odi.match_id])
out["stands"] = dict(match=dict(id=last_odi.match_id, date=clean(last_odi.date), home=last_odi.home, away=last_odi.away,
                                result=last_odi.result),
                     rows=rows(st, [x for x in st.columns if x in ("innings_no", "team", "wicket", "runs", "start", "end",
                                                                     "unbroken", "batter1", "batter2", "a", "b", "known")]),
                     cols=list(st.columns))
fw = c.fow[c.fow.match_id == last_odi.match_id]
out["fow"] = rows(fw, ["innings_no", "team", "wicket", "score"])
out["latest_inns"] = rows(c.innings[c.innings.match_id == last_odi.match_id], ["innings_no", "team", "runs", "wickets", "balls", "all_out"])

(HERE / "data.json").write_text(json.dumps(out, indent=1, default=str))
print("star", star, "| banner", [(b["section"], b["record"]) for b in ban])
print("radar players", list(out["radar"]))
print("stands cols", out["stands"]["cols"])
print("bat cols", out["bat_cols"])

# ---- more for the mock-ups: bowling leaders, the star's innings, logos
for sec in ("ODIs", "T20Is"):
    bt, bw, fl, bs = player_tables(c, Scope(sections=[sec]))
    mine_p = set(c.bowling[c.bowling.team == TEAM].player)
    w = bw[bw.player.isin(mine_p)].sort_values("wickets", ascending=False).head(6)
    out.setdefault("bowl", {})[sec] = rows(w, [x for x in ("player", "innings", "wickets", "average", "economy", "strike_rate", "best") if x in w.columns])
    bb = bt[bt.player.isin(set(c.batting[c.batting.team == TEAM].player))].sort_values("runs", ascending=False).head(6)
    out.setdefault("bat", {})[sec] = rows(bb, ["player", "innings", "runs", "average", "strike_rate", "hundreds", "fifties", "high_score_text"])
    out.setdefault("bowl_cols", list(bw.columns))
inns = c.batting[(c.batting.player == star) & c.batting.did_bat].merge(m[["match_id", "date", "section", "home", "away"]], on="match_id")
inns["opp"] = np.where(inns.home == TEAM, inns.away, inns.home)
out["star_innings"] = rows(inns.sort_values(["date", "innings_no"]), ["date", "section", "opp", "runs", "balls", "fours", "sixes", "out", "how_out"])
from ccstats import logos as LG
book = LG.LogoBook(LG.find([pathlib.Path("/tmp/claude-0/-home-user-crciekt20206/db8ebe3d-6d6c-58e2-9ecc-4739d2cc52d6/scratchpad/gamefold")]))
logos = {}
for t in set([TEAM] + [r["opp"] for r in out["results"]] + out["elo_odis"]["teams"]):
    p = book.team(t)
    if p is not None:
        logos[t] = {"plain": LG.badge(p, 160, "plain"), "dark": LG.badge(p, 160, book.style(p))}
for comp in ("Tests", "T20 World Cup", "ODI World Cup"):
    p = book.comp(comp)
    if p is not None:
        logos[comp] = {"plain": LG.badge(p, 160, "plain"), "dark": LG.badge(p, 160, book.style(p))}
out["logos"] = logos
(HERE / "data.json").write_text(json.dumps(out, indent=1, default=str))
print("logos", sorted(logos), "bowl", out["bowl"]["ODIs"][:2], out["bowl_cols"])

# ---- player ratings (the site's Rankings page) for India's players
from ccstats.rankings import player_ratings
rt = {}
for sec in ("ODIs", "T20Is"):
    r = player_ratings(c, sec)
    r = r[r.team == TEAM]
    rt[sec] = rows(r, ["player", "batting", "bowling", "all_round", "batting_innings", "bowling_innings"])
out["ratings"] = rt
(HERE / "data.json").write_text(json.dumps(out, indent=1, default=str))
print({k: sorted(v, key=lambda x: -(x["batting"] or 0))[:5] for k, v in rt.items()})

# ---- pages: a match scorecard, a series, section leaders, rankings, the star's profile
def overs(balls):
    balls = int(balls)
    return f"{balls // 6}" + (f".{balls % 6}" if balls % 6 else "")

def scorecard(mid):
    mm = m[m.match_id == mid].iloc[0]
    inn = c.innings[c.innings.match_id == mid].sort_values("innings_no")
    cards = []
    for i in inn.itertuples():
        bt = c.batting[(c.batting.match_id == mid) & (c.batting.innings_no == i.innings_no)].sort_values("position")
        bw = c.bowling[(c.bowling.match_id == mid) & (c.bowling.innings_no == i.innings_no)]
        fw = c.fow[(c.fow.match_id == mid) & (c.fow.innings_no == i.innings_no)].sort_values("wicket")
        cards.append(dict(team=i.team, runs=int(i.runs), wickets=int(i.wickets), overs=overs(i.balls), all_out=bool(i.all_out),
                          extras=int(i.extras),
                          bat=rows(bt, ["player", "position", "did_bat", "how_out", "dismissal", "runs", "balls", "fours", "sixes", "out"]),
                          bowl=rows(bw, ["player", "balls", "maidens", "runs", "wickets", "dots"]),
                          fow=rows(fw, ["wicket", "score"])))
    return dict(id=mid, date=clean(mm.date), home=mm.home, away=mm.away, result=mm.result, pom=mm.player_of_match,
                section=mm.section, no=clean(mm.series_match_no), of=clean(mm.series_length), event=mm.event, cards=cards)

out["match"] = scorecard(last_odi.match_id)
ser = mine[(mine.section == "T20Is") & (mine.date >= "2026-10-01")]
sids = list(ser.match_id)
sb = c.batting[c.batting.match_id.isin(sids) & c.batting.did_bat].groupby(["player", "team"]).agg(
    runs=("runs", "sum"), balls=("balls", "sum"), inns=("runs", "size"), outs=("out", "sum"), hs=("runs", "max"),
    sixes=("sixes", "sum")).reset_index().sort_values("runs", ascending=False)
sw = c.bowling[c.bowling.match_id.isin(sids) & (c.bowling.balls > 0)].groupby(["player", "team"]).agg(
    wickets=("wickets", "sum"), runs=("runs", "sum"), balls=("balls", "sum")).reset_index().sort_values(["wickets", "runs"], ascending=[False, True])
sw["economy"] = sw.runs / sw.balls * 6
out["series"] = dict(name="India v West Indies · T20I series · Oct 2026", matches=[r for r in out["results"] if r["id"] in sids][::-1],
                     bat=rows(sb.head(8), ["player", "team", "runs", "balls", "inns", "outs", "hs", "sixes"]),
                     bowl=rows(sw.head(8), ["player", "team", "wickets", "runs", "balls", "economy"]),
                     cards={mid: scorecard(mid) for mid in sids})
lead = {}
for sec in ("T20Is", "ODIs"):
    bt, bw, fl, bs = player_tables(c, Scope(sections=[sec]), by_team=True)
    lead[sec] = dict(bat=rows(bt.sort_values("runs", ascending=False).head(12), ["player", "team", "innings", "runs", "average", "strike_rate", "high_score_text", "fifties", "hundreds", "sixes"]),
                     bowl=rows(bw.sort_values(["wickets", "average"], ascending=[False, True]).head(12), ["player", "team", "innings", "wickets", "average", "economy", "strike_rate", "best"]),
                     base={k: clean(v) for k, v in vars(bs).items()})
out["leaders"] = lead
rk = {}
for sec in ("ODIs", "T20Is", "Tests"):
    t, h = team_elo(c, sec)
    pr = player_ratings(c, sec)
    rk[sec] = dict(teams=rows(t.reset_index().rename(columns={"index": "rank"}), ["rank", "team", "elo", "played", "peak"]),
                   bat=rows(pr.sort_values("batting", ascending=False).head(10), ["player", "team", "batting", "batting_innings"]),
                   bowl=rows(pr.dropna(subset=["bowling"]).sort_values("bowling", ascending=False).head(10), ["player", "team", "bowling", "bowling_innings"]))
out["rankings"] = rk
prof = {}
for sec in ("Tests", "ODIs", "T20Is"):
    bt, bw, fl, bs = player_tables(c, Scope(sections=[sec]))
    r = bt[bt.player == star]
    if len(r):
        prof[sec] = rows(r, ["innings", "runs", "balls", "outs", "not_outs", "average", "strike_rate", "high_score_text", "fifties", "hundreds", "ducks", "fours", "sixes", "boundary_pct"])[0]
out["profile"] = prof
(HERE / "data.json").write_text(json.dumps(out, indent=1, default=str))
print("match", out["match"]["home"], out["match"]["away"], [ (k["team"], k["runs"], k["wickets"], k["overs"]) for k in out["match"]["cards"]])
print("series bat", out["series"]["bat"][:3]); print("lead T20Is", out["leaders"]["T20Is"]["bat"][:3]); print("rank ODIs", out["rankings"]["ODIs"]["teams"][:3], out["rankings"]["ODIs"]["bowl"][:2]); print("profile", out["profile"])

# ---- for the chart ideas: T20I runs race (match by match) and every T20I batter's runs
t20 = m[m.section == "T20Is"].sort_values(["date", "match_id"])
tb = c.batting[c.batting.match_id.isin(t20.match_id) & c.batting.did_bat].merge(t20[["match_id", "date"]], on="match_id")
top = list(tb.groupby("player").runs.sum().sort_values(ascending=False).head(8).index)
dates = sorted(t20.date.unique())
cum = {p: [] for p in top}
for d in dates:
    upto = tb[tb.date <= d]
    tot = upto.groupby("player").runs.sum()
    for p in top:
        cum[p].append(int(tot.get(p, 0)))
team_of = tb.groupby("player").team.agg(lambda x: x.iloc[-1]).to_dict()
out["t20_race"] = dict(dates=[clean(pd.Timestamp(d)) for d in dates], players=top, teams={p: team_of[p] for p in top}, cum=cum)
allr = tb.groupby(["team", "player"]).runs.sum().reset_index()
out["t20_runs"] = rows(allr[allr.runs >= 60].sort_values("runs", ascending=False), ["team", "player", "runs"])
(HERE / "data.json").write_text(json.dumps(out, indent=1, default=str))
print("race", top, len(dates)); print("t20 runs rows", len(out["t20_runs"]))
