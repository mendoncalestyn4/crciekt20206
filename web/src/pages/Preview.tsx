// Opponent preview (stage 2): know your opponent. Your team and the team you're about to play: their record and form,
// the predicted result, a game plan, then head to head (with who gets whom out), about them, side by side, and your
// best XI against them. It opens on your next match; pick any two sides in a competition.
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import { type Explained, get, type GridT, type HowTheyPlay as HowTheyPlayT, type NGrid, type Outcome, type PreviewPage, remember } from "../api";
import { Explain, Lamps, Logo, Missing, Num, Tile } from "../kit/base";
import { LeaderBars, ShareRing } from "../kit/charts";
import { BatFirstSides, VenueRecord } from "../kit/season";
import { Grid, Md, SignedBars } from "../kit/teams";
import { ab, dayY } from "../format";
import { useReady } from "../ready";
import { Head, useShell } from "../shell/Shell";
import { T } from "../shell/names";
import { TEAM_PAGES } from "./Teams";

const WHERE = ["Home", "Away", "Neutral"];

export function Preview() {
  const { career, noCareer, nation } = useShell();
  const [params] = useSearchParams();
  const go = useNavigate();
  const keep = nation ? `?nation=${encodeURIComponent(nation)}` : "";
  const want = { section: params.get("section") ?? "", format: params.get("format") ?? "", mine: params.get("mine") ?? "",
    opp: params.get("opp") ?? "", tab: params.get("tab") ?? "", mu: params.get("mu") ?? "", cur: params.get("cur") ?? "",
    htp: params.get("htp") ?? "" };
  const qs = Object.entries(want).map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join("&");
  const q = useQuery({ queryKey: ["preview", qs, career?.name], enabled: Boolean(career), retry: false, queryFn: () => get<PreviewPage>(`/api/preview?${qs}`) });
  const [where, setWhere] = useState(""), [you, setYou] = useState("Home");
  useReady(Boolean(q.data || q.error || noCareer), qs);
  const d = q.data;
  // once a page is open, keep its picks in the address so a change of one keeps the others
  const set = (changes: Record<string, string>) => {
    remember({ ...(changes.section && changes.section !== "International cricket" ? { section: changes.section } : {}),
      ...(changes.format && changes.format !== "All" ? { format: changes.format } : {}) }, { format: "section" });
    const base = d ? { section: d.section, format: d.format, mine: d.mine, opp: d.opp, tab: d.tab === d.tabs[0] ? "" : d.tab,
      mu: d.mu ? "every" : "", cur: d.cur ? "1" : "", htp: d.htp ?? "" } : want;
    const next: Record<string, string> = { ...base, ...changes };
    if ("section" in changes) Object.assign(next, { format: "", opp: "" });
    if ("format" in changes || "mine" in changes) next.opp = "";
    if (!("htp" in changes) && ("section" in changes || "format" in changes || "opp" in changes)) next.htp = "";   // a new opponent: this season again
    if (nation) next.nation = nation;
    go(`/teams/preview?${new URLSearchParams(Object.entries(next).filter(([, v]) => Boolean(v))).toString()}`);
  };
  const head = <Head title="Teams" crumb="Opponent preview · know your opponent" chips={TEAM_PAGES.map((p) => p.label)} on={2}
    onChip={(i) => go(`${TEAM_PAGES[i]!.to}${keep}`)} />;
  if (noCareer) return <>{head}<div className="grid"><Tile span={12} title="No career yet"><div className="plain">Add a career on the current site for now.</div></Tile></div></>;
  if (q.error) return <>{head}<div className="grid"><Tile span={12}><Missing why={String(q.error)} /></Tile></div></>;
  if (!d) return <>{head}<div className="empty">Sizing up the opposition…</div></>;
  const h = d.head, b = d.body, m = b?.missing ?? {}, me = d.mine === "—" ? "" : d.mine;
  const w = where || h?.where_default || "Neutral";
  const pr = h?.predicted?.[w];
  return (
    <>
      {head}
      <div className="grid">
        <Tile span={12} title="Pick your team and the team you're about to play">
          <div className="plain">Your history against them, who gets whom out, their form, their key players and weak spots, and a plan to beat them.</div>
          <div className="field">
            <label htmlFor="op-sec">Competition</label>
            <select id="op-sec" className="pick" value={d.section} onChange={(e) => set({ section: e.target.value })}>
              {d.choices.map((c) => <option key={c.section} value={c.section}>{c.section} · {c.matches} matches</option>)}</select>
            {d.formats.length > 0 && <div className="itabs" style={{ gridColumn: "auto", margin: 0 }}>{d.formats.map((f) => (
              <button key={f} className={f === d.format ? "on" : ""} onClick={() => set({ format: f })}>{f}</button>))}</div>}
          </div>
          <div className="field">
            <label htmlFor="op-mine">Your team</label>
            <select id="op-mine" className="pick" value={d.mine} onChange={(e) => set({ mine: e.target.value })}>
              {d.mine_opts.map((t) => <option key={t} value={t}>{t}</option>)}</select>
            <label htmlFor="op-opp">Opponent</label>
            <select id="op-opp" className="pick" value={d.opp} onChange={(e) => set({ opp: e.target.value })}>
              {d.opp_opts.map((o) => <option key={o.team} value={o.team}>{o.label}</option>)}</select>
          </div>
          <div className="note">Your team: any side here, yours first; your history against them, side by side and your best XI need your team.
            Opponent: every side here, and the teams still to come in your schedule.</div>
        </Tile>
        {d.none ? <Tile span={12} title={d.opp || d.section}><div className="plain"><T>{d.none}</T></div>
          {d.elsewhere.length > 0 && <div className="field">{d.elsewhere.map((s) => (
            <button key={s} className="btn quiet" onClick={() => set({ format: s, opp: d.opp })}>Show {s}</button>))}</div>}</Tile> : h && <>
          {d.mine_note && <Tile span={12} title={me}><div className="plain">ℹ️ <T>{d.mine_note}</T></div></Tile>}
          <Tile span={12} title={d.where_note ?? ""}>
            <div className="row2" style={{ gap: 26, flexWrap: "wrap" }}>
              <Logo team={d.opp} size={96} /><div className="hl" style={{ fontSize: 44 }}>{d.opp}</div>
              <div className="kpis">{h.kpis.map((k) => <div key={k.k}><span>{k.k}</span><Num v={k.v} px={34} /></div>)}
                <div><span>Last 5</span>{h.last5.length ? <Lamps seq={h.last5 as Outcome[]} /> : <Num v="–" px={34} />}</div></div>
            </div>
            <div className="note">{h.caption}</div>
          </Tile>
          {me && <Tile span={7} title="🔮 Predicted result">
            {pr ? <><div className="field" style={{ marginTop: 0 }}><span className="plain" style={{ flex: 1 }}><b>{pr.line}</b></span>
              <div className="itabs" style={{ gridColumn: "auto", margin: 0 }}>{WHERE.map((x) => (
                <button key={x} className={x === w ? "on" : ""} onClick={() => setWhere(x)}>{x}</button>))}</div></div>
              <Grid t={pr.steps} /><div className="note">{pr.note}</div></> : <Missing why={h.missing.predicted} />}</Tile>}
          {me && <Tile span={5} title={`📋 Game plan for ${me} v ${d.opp}`}>
            {h.plan ? (h.plan.length ? <ul className="dots plan">{h.plan.map((x) => <li key={x}><Md s={x} /></li>)}</ul>
              : <div className="plain">Nothing stands out yet: not enough games for a clear pattern. Play a few more and it fills in.</div>) : <Missing why={h.missing.plan} />}</Tile>}
          {me && <Tile span={12} title={h.aim?.kind === "multi" ? "🎯 First-innings totals that won, drew and lost" : "🎯 The score to aim for batting first"}>
            {h.aim ? (h.aim.none ? <div className="plain">{h.aim.none}</div> : (() => {
              const a = h.aim.venues[w];
              const where = <div className="itabs" style={{ gridColumn: "auto", margin: 0 }}>{WHERE.map((x) => (
                <button key={x} className={x === w ? "on" : ""} onClick={() => setWhere(x)}>{x}</button>))}</div>;
              if (!a) return null;
              if (h.aim.kind === "multi") return <><div className="field" style={{ marginTop: 0 }}><span className="plain" style={{ flex: 1 }}>
                  {a.line ? <b><T>{a.line}</T></b> : <T>{a.none || ""}</T>}</span>{where}</div>
                {a.games && <><div className="glabel">Every game against them here · newest first</div><Grid t={a.games} keep={keep} /></>}
                <div className="note">{h.aim.note}</div></>;
              return <><div className="field" style={{ marginTop: 0 }}><span className="plain" style={{ flex: 1 }}><b>{a.line}</b></span>{where}</div>
                {a.warn && <div className="plain">⚠️ {a.warn}</div>}
                {h.aim.few && <div className="plain">⚠️ {h.aim.few}</div>}
                <div className="plain"><T>{a.they || ""}</T></div>
                <div className="glabel">How sure it is</div>
                <div className="plain"><T>{h.aim.rests || ""}</T> {h.aim.sure}</div>
                {a.meetings ? <><div className="glabel">Your games against them here · newest first</div><Grid t={a.meetings} keep={keep} /></>
                  : <div className="plain">You haven't played them here yet.</div>}
                <div className="note">{h.aim.note}</div></>;
            })()) : <Missing why={h.missing.aim} />}</Tile>}
          <div className="itabs">{d.tabs.map((x, i) => (
            <button key={x} className={x === d.tab ? "on" : ""} onClick={() => set({ tab: i === 0 ? "" : x })}>{x === "About them" ? `About ${d.opp}` : x}</button>))}</div>
          {!b ? null : b.none ? <Tile span={12}><div className="plain">{b.none}</div></Tile> : <>
            {d.tab === "Head to head" && <>
              {b.h2h === null ? <Tile span={12}><Missing why={m.h2h} /></Tile> : b.h2h && (b.h2h.never ? <Tile span={12} title="Head to head">
                <div className="plain"><b><T>{b.h2h.never}</T></b></div>{b.h2h.other && <div className="note">{b.h2h.other}</div>}</Tile> : null)}
              {b.h2h === null || !b.h2h || b.h2h.never ? <TheirRecord b={b} opp={d.opp} /> : null}
              {b.h2h && !b.h2h.never && <>
                <Tile span={12} title={<span className="row2" style={{ gap: 10 }}><Logo team={me} size={40} />{me} v <Logo team={d.opp} size={40} />{d.opp}</span>}>
                  <div className="kpis">{b.h2h.kpis!.map((k) => <div key={k.k}><span>{k.k}</span><Num v={k.v} px={30} /></div>)}
                    <div><span>Last 5</span><Lamps seq={b.h2h.last5 as Outcome[]} /></div></div>
                  <div className="plain" style={{ marginTop: 8 }}><T>{b.h2h.how!}</T></div><div className="plain"><T>{b.h2h.typical!}</T></div>
                </Tile>
                <TheirRecord b={b} opp={d.opp} />
                {b.h2h.keys!.map((k, i) => <Tile key={k.title} span={6} title={<Titled team={i === 0 ? me : d.opp} text={k.title} />}>
                  {k.rows.length ? <Grid t={{ cols: ["Player", "", ""], rows: k.rows, num: [], hi: [], links: [], dim: k.dim }} /> : <div className="plain">No figures yet.</div>}
                  <div className="note">Greyed out: not in that team's last 3 games, so maybe not playing now.</div></Tile>)}
                <Tile span={12} title="Every meeting" right="newest first">
                  <div className="mcards">{b.h2h.cards!.map((c) => (
                    <div className="mcard" key={c.id}><div className="top"><span>{dayY(c.date)} · {c.event}</span><Link className="lk" to={`/matches/${c.id}${keep}`}>Scorecard →</Link></div>
                      {c.sides.map((s) => <div key={s.team}><div className="side"><span>{s.team}</span><b>{s.score}</b></div>
                        <div className="who"><T>{`🏏 ${s.top_bat} · 🎯 ${s.top_bowl}`}</T></div></div>)}
                      {c.potm && <div className="who"><T>{`⭐ Player of the Match: ${c.potm}`}</T></div>}
                      <div className="story"><T>{c.story}</T></div></div>))}</div>
                </Tile></>}
              {me && <Tile span={12} title="Who gets whom out" right="dismissals by each bowler of each batter (run-outs left out)">
                <div className="field" style={{ marginTop: 0 }}><label>Count</label><div className="itabs" style={{ gridColumn: "auto", margin: 0 }}>
                  {[["", "Only our meetings"], ["every", "Every match these players faced each other"]].map(([k, l]) => (
                    <button key={l} className={(d.mu ? "every" : "") === k ? "on" : ""} onClick={() => set({ mu: k! })}>{l}</button>))}
                  <button className={d.cur ? "on" : ""} onClick={() => set({ cur: d.cur ? "" : "1" })} title="Only players in each team's last 5 games here.">
                    {d.cur ? "✓ " : ""}Current players only</button></div></div>
                {b.matchups ? <div>{b.matchups.map((s) => (
                  <div key={s.title} style={{ marginTop: 12 }}><div className="k3">{s.title}</div>
                    {"cols" in s ? <><Grid t={s as NGrid} /><div className="note"><T>{(s as NGrid).note ?? ""}</T></div></> : <div className="plain">{s.none}</div>}</div>))}</div>
                  : <Missing why={m.matchups} />}
                <div className="note">Innings met: innings where the batter batted and the bowler bowled at them. The scorecards don't say which bowler each run came
                  off, so the runs are the batter's whole score in the innings that bowler got them out.</div>
              </Tile>}</>}
            {d.tab === "About them" && <>
              <Tile span={12} title={<Titled team={d.opp} text={`How ${d.opp} play`} />} right={b.how?.season ? `${b.how.showing_last ? "last season" : "this season"} · ${b.how.season} · ${b.how.matches} matches` : ""}>
                {b.how ? <HowTheyPlay h={b.how} toggle={(last) => set({ htp: last ? "last" : "" })} /> : <Missing why={m.how} />}</Tile>
              <Tile span={12} title={<Titled team={d.opp} text={`${poss(d.opp)} danger men right now`} />} right={b.danger?.season ? `most impact points · ${b.danger.season}` : ""}>
                {b.danger ? (b.danger.none ? <div className="plain">{b.danger.none}</div> : <>
                  {b.danger.note && <div className="note" style={{ marginTop: 0 }}>{b.danger.note}</div>}
                  <div className="danger">{b.danger.men.map((x) => <div key={x.player} className="bf-side">
                    <div className="k"><T>{x.player}</T></div><div className="note" style={{ marginTop: 2 }}>{x.line}</div>
                    {x.role !== "bowl" && x.innings.length > 0 && <><div className="glabel">Last five innings</div>
                      <div className="last5">{x.innings.map((i) => <Link key={i.id + i.text} className="lk" to={`/matches/${i.id}${keep}`} title={`v ${i.opp} · ${i.date}`}><b>{i.text}</b><small>{ab(i.opp)}</small></Link>)}</div></>}
                    {x.role !== "bat" && x.spells.length > 0 && <><div className="glabel">Last five spells</div>
                      <div className="last5">{x.spells.map((w) => <Link key={w.id + w.text} className="lk" to={`/matches/${w.id}${keep}`} title={`v ${w.opp} · ${w.date}`}><b>{w.text}</b><small>{ab(w.opp)}</small></Link>)}</div></>}
                  </div>)}</div>
                  {b.danger.shows && <Explain shows={<T>{b.danger.shows}</T>} for_={b.danger.for_ ?? ""} />}</>) : <Missing why={m.danger} />}</Tile>
              {(["batters", "bowlers"] as const).map((k) => {
                const s = b[k];
                return <Tile key={k} span={6} title={k === "batters" ? "Batters in form" : "Bowlers in form"} right={k === "batters" ? "runs, last 10 matches" : "wickets, last 10 matches"}>
                  {s === null && m[k] ? <Missing why={m[k]} /> : s ? <><LeaderBars rows={s.rows} value={k === "batters" ? "runs" : "wickets"} mine={d.opp} height={44 * s.rows.length + 16}
                    noTeam label={k === "batters" ? "Batters in form" : "Bowlers in form"} />
                    <Explain shows={<T>{s.shows}</T>} for_={s.for_} /></> : <div className="plain">{k === "batters" ? "No innings yet." : "No bowling yet."}</div>}</Tile>;
              })}
              <Tile span={6} title="🔑 Key wicket"><div className="how" style={{ marginTop: -4, marginBottom: 6 }}>The batter whose score decides their results</div>
                {b.key_wicket ? <Grid t={b.key_wicket} /> : m.key_wicket ? <Missing why={m.key_wicket} /> : <div className="plain">Not enough games yet.</div>}</Tile>
              <Tile span={6} title="🩹 Weak spot"><div className="how" style={{ marginTop: -4, marginBottom: 6 }}>Their average stand for each wicket v every team here</div>
                {b.weak_spot ? <><SignedBars rows={b.weak_spot.rows} /><Explain shows={<T>{b.weak_spot.shows}</T>} for_={b.weak_spot.for_} /></>
                  : m.weak_spot ? <Missing why={m.weak_spot} /> : <div className="plain">Not enough innings yet.</div>}</Tile>
              <Tile span={6} title="🎯 Attack to target"><div className="how" style={{ marginTop: -4, marginBottom: 6 }}>Their regular bowlers, most expensive first</div>
                {b.attack ? <><Grid t={b.attack} /><div className="note">{b.attack.note}</div></> : m.attack ? <Missing why={m.attack} /> : <div className="plain">No regular bowlers yet.</div>}</Tile>
              <Tile span={6} title="🏏 How their batters play"><div className="how" style={{ marginTop: -4, marginBottom: 6 }}>Average and strike rate against the average batter</div>
                {b.styles ? <Grid t={b.styles} /> : m.styles ? <Missing why={m.styles} /> : <div className="plain">No innings yet.</div>}</Tile>
              <Tile span={6} title={b.chase?.title ?? "Batting first or chasing"}>
                {b.chase ? <><Grid t={b.chase} />{b.chase.extremes.map((x) => (
                  <div key={x.id} className="plain" style={{ marginTop: 6 }}>{x.label}: <Link className="lk" to={`/matches/${x.id}${keep}`}>{x.text}</Link></div>))}</> : <Missing why={m.chase} />}</Tile>
              <Tile span={6} title="Home and away">
                {b.venues ? <><div className="field" style={{ marginTop: 0 }}><label>You are</label><div className="itabs" style={{ gridColumn: "auto", margin: 0 }}>{WHERE.map((x) => (
                  <button key={x} className={x === you ? "on" : ""} onClick={() => setYou(x)}>{x}</button>))}</div></div>
                  <Grid t={b.venues[you]!} /><div className="note">{b.venues[you]!.note}</div></> : <Missing why={m.venues} />}</Tile>
              <Tile span={12} title="🏟️ Their players where your match is" right="current players · their record there">
                {b.by_country ? (b.by_country.none ? <div className="plain">{b.by_country.none}</div> : (() => {
                  const keys = Object.keys(b.by_country.venues), k = keys.includes(you) ? you : keys[0]!, v = b.by_country.venues[k]!;
                  return <><div className="field" style={{ marginTop: 0 }}><label>You are</label><div className="itabs" style={{ gridColumn: "auto", margin: 0 }}>{keys.map((x) => (
                    <button key={x} className={x === k ? "on" : ""} onClick={() => setYou(x)}>{x}</button>))}</div><span className="plain">their players {v.place}</span></div>
                    {v.none ? <div className="plain"><T>{v.none}</T></div> : <Grid t={v as GridT} />}
                    {b.by_country.shows && <Explain shows={<T>{b.by_country.shows}</T>} for_={b.by_country.for_ ?? ""} />}</>;
                })()) : <Missing why={m.by_country} />}</Tile>
              <Tile span={12} title="🔥 Their big-match players" right="knockouts and series deciders against every other game">
                {b.big_players ? (b.big_players.none ? <div className="plain"><T>{b.big_players.none}</T></div> : <><Grid t={b.big_players as GridT} />
                  <Explain shows={<T>{(b.big_players as GridT & Explained).shows}</T>} for_={(b.big_players as GridT & Explained).for_} /></>) : <Missing why={m.big_players} />}</Tile>
              <Tile span={6} title="🏆 Big-match record">{b.big ? <Grid t={b.big} /> : m.big ? <Missing why={m.big} /> : <div className="plain">No knockouts, finals or series deciders yet.</div>}</Tile>
              <Tile span={6} title="📈 Trend">{b.trend ? <><div className="field" style={{ marginTop: 0 }}><span className="k3" style={{ margin: 0 }}>Last 5</span>
                <Lamps seq={b.trend.last as Outcome[]} /></div><div className="plain">{b.trend.line}</div></> : <Missing why={m.trend} />}</Tile>
              <Tile span={6} title="How their batters get out" right="share of dismissals">
                {b.how_out ? <><ShareRing rows={b.how_out.rows} count={(r) => r.n ?? 0} centre={String(b.how_out.outs ?? "")} sub="dismissals" /><Explain shows={b.how_out.shows} for_={b.how_out.for_} /></>
                  : m.how_out ? <Missing why={m.how_out} /> : <div className="plain">Not dismissed yet.</div>}</Tile>
              <Tile span={6} title="Where their runs come from">
                {b.depth ? <><ShareRing rows={b.depth.rows} count={(r) => r.runs ?? 0} centre={String(b.depth.rows.reduce((a, r) => a + (r.runs ?? 0), 0))} sub="runs" />{b.depth.shows && <Explain shows={b.depth.shows} for_={b.depth.for_} />}</> : m.depth ? <Missing why={m.depth} /> : <div className="plain">No runs yet.</div>}</Tile>
            </>}
            {d.tab === "Side by side" && <Tile span={12} title={b.sbs?.title ?? "Side by side"}>
              {b.sbs ? <><div className="how" style={{ marginTop: -4, marginBottom: 6 }}>{b.sbs.right}</div><Grid t={b.sbs} /><div className="note">{b.sbs.note}</div></> : <Missing why={m.sbs} />}</Tile>}
            {d.tab === "Your best XI v them" && <Tile span={12} title={b.xi?.title ?? "Your squad against them"}>
              {!b.xi ? <Missing why={m.xi} /> : b.xi.none ? <div className="plain"><T>{b.xi.none}</T></div> : <>
                <div className="how" style={{ marginTop: -4, marginBottom: 6 }}>{b.xi.right[0]!.toUpperCase() + b.xi.right.slice(1)}</div>
                <div className="k3">Batting</div>{b.xi.bat && <Grid t={b.xi.bat} />}
                <div className="k3" style={{ marginTop: 14 }}>Bowling</div>{b.xi.bowl && <Grid t={b.xi.bowl} />}
                {b.xi.lines.map((l) => <div key={l} className="plain"><T>{l}</T></div>)}
                <div className="note">{b.xi.note}</div></>}</Tile>}
          </>}
        </>}
      </div>
    </>
  );
}

/** A tile's title with the team's badge in front (only teams that have one). */
function Titled({ team, text }: { team: string; text: string }) {
  return <span className="row2" style={{ gap: 10 }}><Logo team={team} size={40} />{text}</span>;
}

/** "India's", "West Indies'" */
const poss = (t: string) => (t.endsWith("s") ? `${t}'` : `${t}'s`);

/** The opponent's own record batting first or chasing, and home, away and neutral then country by country, against
 *  every side: under the head-to-head record. */
function TheirRecord({ b, opp }: { b: NonNullable<PreviewPage["body"]>; opp: string }) {
  const m = b.missing, bf = b.bat_first, wh = b.where;
  return <>
    <Tile span={6} title={<Titled team={opp} text={`${opp}: batting first or chasing`} />}>
      {bf ? (bf.none !== undefined ? <div className="plain">{bf.none}</div> : <><BatFirstSides bf={bf} who={opp} />
        <div className="note">Games shortened by rain are left out of the totals.</div><Explain shows={<T>{bf.shows}</T>} for_={bf.for_} /></>)
        : <Missing why={m.bat_first} />}</Tile>
    <Tile span={6} title={<Titled team={opp} text={`${opp}: home, away and neutral`} />}>
      {wh ? (wh.none !== undefined ? <div className="plain">{wh.none}</div> : <><VenueRecord v={wh} team={opp} who />
        <div className="note">The scorecards don't name the ground, so it goes by the home side{wh.nation ? "'s country" : ""}.</div>
        <Explain shows={<T>{wh.shows}</T>} for_={wh.for_} /></>) : <Missing why={m.where} />}</Tile>
  </>;
}

/** How they play: a short summary, then their bowling and batting in plain words and how fast each part of the order
 *  goes; this season, with last season a click away when this one has too few matches. */
function HowTheyPlay({ h, toggle }: { h: HowTheyPlayT; toggle: (last: boolean) => void }) {
  const button = h.showing_last ? <button className="btn quiet" onClick={() => toggle(false)}>Back to this season ({h.this})</button>
    : h.last ? <button className="btn quiet" onClick={() => toggle(true)}>See last season ({h.last})</button> : null;
  if (h.none) return <><div className="plain">{h.none}</div>{h.note && <div className="note">{h.note}</div>}{button}</>;
  return <>
    {h.note && !h.showing_last && <div className="field" style={{ marginTop: 0 }}><span className="plain" style={{ flex: 1 }}>⚠️ {h.note}</span>{button}</div>}
    {h.showing_last && <div className="field" style={{ marginTop: 0 }}><span className="plain" style={{ flex: 1 }}>Showing last season ({h.season}).</span>{button}</div>}
    {h.summary && <div className="plain"><b><T>{h.summary}</T></b></div>}
    <div className="htp">
      <div><div className="k3">🎯 Bowling</div><ul className="dots">{(h.bowling ?? []).map((x) => <li key={x}><T>{x}</T></li>)}</ul></div>
      <div><div className="k3">🏏 Batting</div><ul className="dots">{(h.batting ?? []).map((x) => <li key={x}><T>{x}</T></li>)}</ul></div>
    </div>
    {h.parts && <><div className="glabel">Each part of the order</div><Grid t={h.parts} /></>}
    {h.rules && <div className="note">{h.rules}</div>}
  </>;
}
