// The pieces that aren't charts: percentile bars, the last five innings, Broadcast's TV table, the latest-results
// strip, top-player lists, the player of the match's card and story, the TV-style match summary, the scorecard.
import { Fragment, useState, type ReactNode } from "react";
import type { Card, Match, Parts, Pom, Result, SquadRow } from "../api";
import { ab, cap, day, dayY, f0, f1, f2, fmtOf, initials, ord, overs, score } from "../format";
import { useTheme } from "../theme";
import { Lamp, Logo, MatchLink, Missing, Name, Num, PName, Tile } from "./base";
import { PartnershipBars, RingList } from "./charts";
import { ts } from "./look";
import { T } from "../shell/names";

/** Scores like 2–1 never break across lines. */
export function KeepScores({ text }: { text: string }) {
  const parts = text.split(/(\d+[–-]\d+)/);
  return <>{parts.map((p, i) => (i % 2 ? <span key={i} style={{ whiteSpace: "nowrap" }}>{p}</span> : <Fragment key={i}>{p}</Fragment>))}</>;
}

/** How a player compares: one bar for each stat, 99 = the best in the pool. */
export function PercentileBars({ values }: { values: Record<string, number> }) {
  return <>{Object.entries(values).map(([k, v]) => (
    <div className="pbar" key={k}><span className="k2">{k}</span><div className="tr2"><div className="fill" style={{ width: `${v}%` }} /></div>
      <span className="v"><Num v={f0(v)} px={30} /></span></div>))}</>;
}

/** The last five innings as tiny bars, with the scores ('12 45* 3'). */
export function LastFive({ s }: { s: string }) {
  const v = s.split(" ").filter(Boolean), runs = v.map((x) => parseInt(x, 10));
  return <span style={{ whiteSpace: "nowrap" }}><span className="l5">{runs.map((x, i) => (
    <i key={i} className={x >= 50 ? "g" : ""} style={{ height: Math.max(2, Math.min(30, (x / 100) * 30)) }} />))}</span>
    <span className="l5t">{v.join(" ")}</span></span>;
}

/** Broadcast's TV table: a player with their team's badge, then numbers (the first one gold). */
export function TvTable<R extends { player: string; team: string }>({ rows, cols, mine, parts }: {
  rows: R[]; cols: [string, (r: R) => ReactNode][]; mine: string | null;
  /** what a row's average, strike rate or economy is made from, when its columns don't show it (howto.ts) */
  parts?: (r: R) => Parts;
}) {
  return (
    <table className="tv"><thead><tr><th>Player</th>{cols.map(([h]) => <th key={h} className="r">{h}</th>)}</tr></thead>
      <tbody>{rows.map((x) => (
        <tr key={x.player + x.team} className={x.team === mine ? "me" : ""} data-parts={parts ? JSON.stringify(parts(x)) : undefined}>
          <td><span className="cell"><Logo team={x.team} size={40} /><PName p={x.player} px={23} /></span></td>
          {cols.map(([h, f], i) => <td key={h} className="r"><span className={`tn ${i ? "dimn" : ""}`}>{f(x)}</span></td>)}
        </tr>))}</tbody>
    </table>
  );
}

/** The latest results as a strip: as many as fit. */
export function Ticker({ results, team }: { results: Result[]; team: string }) {
  return (
    <div className="ticker"><span className="lab">LATEST</span>{results.slice(0, 10).map((r) => (
      <MatchLink key={r.id} id={r.id} className="tk"><Lamp o={r.outcome} /><b>{ab(team)} <span>{r.us}</span></b><i>v</i>
        <b>{ab(r.opp)} <span>{r.them}</span></b><i>{fmtOf(r.section)} · {day(r.date)}</i></MatchLink>))}</div>
  );
}

/** A top-five list: initials, name, a bar against the leader, the number. */
export function TopList({ rows, value, gold }: { rows: ({ player: string } & Record<string, unknown>)[]; value: string; gold?: boolean }) {
  const top = Math.max(...rows.map((r) => Number(r[value] ?? 0)), 1);
  return (
    <div className="list" data-chart>{rows.map((p) => (
      <div className="li" key={String(p.player)}><span className="av">{initials(String(p.player))}</span>
        <div><PName p={String(p.player)} px={22} /><div className="bar"><i style={{ width: `${(Number(p[value] ?? 0) / top) * 100}%`,
          ...(gold ? { background: "var(--gold)" } : {}) }} /></div></div>
        <Num v={Number(p[value] ?? 0)} px={26} /></div>))}</div>
  );
}

/** What the player of the match did: their badge and name, then the batting and the bowling. */
export function PomCard({ pom }: { pom: Pom }) {
  const b = pom.bat, w = pom.bowl;
  return (
    <>
      <div className="row2" style={{ gap: 16 }}><Logo team={pom.team} size={82} />
        <div><PName p={pom.player} px={46} /><div className="s" style={{ marginTop: 2 }}>{pom.team}</div></div></div>
      {b && <><div className="rule" /><div className="fig"><Num v={b.text} px={64} />
        <span className="s">runs off <b>{b.balls}</b> balls<br /><b>{b.fours}</b> {b.fours === 1 ? "four" : "fours"} · <b>{b.sixes}</b> {b.sixes === 1 ? "six" : "sixes"} · SR <b>{f0((b.runs / Math.max(b.balls, 1)) * 100)}</b></span></div></>}
      {w && <><div className="rule" /><div className="fig"><Num v={w.text} px={64} />
        <span className="s">in <b>{overs(w.balls)}</b> {w.balls === 6 ? "over" : "overs"}<br />economy <b>{f2((w.runs / Math.max(w.balls, 1)) * 6)}</b></span></div></>}
    </>
  );
}

/** Almanack's summary: a kicker, the headline worked out from the scorecard, the scores, the engine's report. */
export function Story({ kicker, headline, report, size = 46, scores, comp }: {
  kicker: ReactNode; headline: string; report: string; size?: number; scores?: { team: string; opp: string; r: Result }; comp?: string;
}) {
  const t = useTheme();
  return (
    <>
      <div className="kick row2" style={{ gap: 10 }}>{comp && <Logo comp={comp} size={44} />}{kicker}</div>
      <div className="hl" style={{ fontSize: size }}><KeepScores text={headline} /></div>
      {scores && (
        <div className="row2" style={{ gap: 26, marginBottom: 12, flexWrap: "wrap" }}>
          {([[scores.team, scores.r.us], [scores.opp, scores.r.them]] as const).map(([tm, s]) => (
            <span className="row2" style={{ gap: 12 }} key={tm}><Logo team={tm} size={52} /><Name p={tm} px={28} /><Num v={s} px={32} /></span>))}
          <span className="tag" style={{ background: `color-mix(in srgb, ${scores.r.outcome === "W" ? t.win : t.loss} 16%, transparent)`,
            color: scores.r.outcome === "W" ? t.win : t.loss }}>● {scores.r.result}</span>
        </div>)}
      <div className="deck"><T>{report}</T></div>
    </>
  );
}

const ORD = ["1st", "2nd", "3rd", "4th"];
const sc_ = (c: Card) => score(c.runs, c.wickets, c.all_out, c.declared);
const isTest = (m: Match) => m.cards.length > 2 || ["Tests", "First-class"].includes(m.section);

/** Which innings each card is: in a Test each team's 1st or 2nd (as on TV), in a one-day game the match's. */
function nth(m: Match): number[] {
  return m.cards.map((c, i) => (isTest(m) ? m.cards.slice(0, i + 1).filter((x) => x.team === c.team).length : i + 1));
}
const which = (m: Match) => {
  const f = fmtOf(m.section);
  return m.of ? `${f} ${m.no} of ${m.of}` : m.no ? `${ord(m.no)} ${f}` : f;
};

/** The TV match summary: a band for each innings with its top batters and bowlers (three each in a one-day game,
 *  one each in a Test), the result, and the player of the match's story beside it. */
export function MatchSummary({ m }: { m: Match }) {
  const top = isTest(m) ? 1 : 3, n = nth(m);
  const topBat = (c: Card) => c.bat.filter((x) => x.did_bat).sort((a, b) => b.runs - a.runs || a.balls - b.balls).slice(0, top);
  const topBowl = (c: Card) => [...c.bowl].sort((a, b) => b.wickets - a.wickets || a.runs - b.runs).slice(0, top);
  return (
    <div className="msum"><div className="ttl row2" style={{ justifyContent: "center", gap: 12 }}><Logo comp={m.event} size={52} />Match summary</div>
      <div className="sub2">{which(m)} · {m.home} v {m.away} · {dayY(m.date)}</div>
      <div className="msgrid"><div>
        {m.cards.map((c, i) => { const bt = topBat(c), bw = topBowl(c); return (
          <div className="inn" key={c.innings_no}>
            <div className="band"><span style={{ width: 52, height: 52, display: "grid", placeItems: "center" }}><Logo team={c.team} size={52} fallback /></span>
              <span className="tm">{c.team}</span>
              <span className="which">{ORD[(n[i] ?? 1) - 1]} innings</span><span className="tot">{sc_(c)}<small>{c.overs} ov</small></span></div>
            <div className="ppl">{Array.from({ length: top }, (_, k) => (
              <Fragment key={k}>
                <div className="p">{bt[k] && <><span className="nmx" data-player={bt[k].player}>{bt[k].player}</span><span className="v">{bt[k].runs}{bt[k].out ? "" : "*"}</span><span className="b">{bt[k].balls}</span></>}</div>
                <div className="p">{bw[k] && <><span className="nmx" data-player={bw[k].player}>{bw[k].player}</span><span className="v">{bw[k].wickets}-{bw[k].runs}</span><span className="b">{overs(bw[k].balls)}</span></>}</div>
              </Fragment>))}</div>
          </div>); })}
        <div className="resline">{m.result}</div>
        <div className="note" style={{ textAlign: "center", marginTop: 2 }}>{top === 1
          ? "The top batter (runs, balls) and bowler (wickets-runs, overs) in each innings"
          : "The top three batters (runs, balls) and bowlers (wickets-runs, overs) in each innings"}</div>
      </div>
      {m.pom ? (
        <div className="pomx"><div className="kick">Player of the match</div><div style={{ marginTop: 12 }}><PomCard pom={m.pom} /></div>
          <div className="rule" /><div className="hl" style={{ fontSize: 34, marginTop: 0 }}><KeepScores text={m.pom.headline} /></div>
          <div className="deck"><T>{m.pom.report}</T></div></div>
      ) : <div className="pomx"><div className="kick">Player of the match</div><Missing why="The scorecard names no player of the match." /></div>}
      </div></div>
  );
}

/** The innings' best batter and best bowler (your choice, 14 November: a ★ by each on every scorecard). Batting: the
 *  most runs, then the fewest balls; equal on both, both. Bowling: the most wickets, then the fewest runs, then the
 *  fewest balls; when nobody took a wicket, the cheapest bowler (runs a ball) who bowled at least a fifth of the
 *  innings' balls. */
export function starsOf(c: { bat: { player: string; did_bat: boolean; runs: number; balls: number }[];
  bowl: { player: string; balls: number; runs: number; wickets: number }[] }): Set<string> {
  const out = new Set<string>();
  const bat = c.bat.filter((x) => x.did_bat);
  if (bat.length) {
    const top = [...bat].sort((a, b) => b.runs - a.runs || a.balls - b.balls)[0]!;
    bat.filter((x) => x.runs === top.runs && x.balls === top.balls).forEach((x) => out.add(x.player));
  }
  const bowled = c.bowl.filter((x) => x.balls > 0);
  if (bowled.some((x) => x.wickets > 0)) {
    const top = [...bowled].sort((a, b) => b.wickets - a.wickets || a.runs - b.runs || a.balls - b.balls)[0]!;
    bowled.filter((x) => x.wickets === top.wickets && x.runs === top.runs && x.balls === top.balls).forEach((x) => out.add(x.player));
  } else if (bowled.length) {
    const all = bowled.reduce((s, x) => s + x.balls, 0);
    const enough = bowled.filter((x) => x.balls * 5 >= all);
    const rate = (x: { runs: number; balls: number }) => x.runs / x.balls;
    const top = [...enough].sort((a, b) => rate(a) - rate(b))[0];
    if (top) enough.filter((x) => rate(x) === rate(top)).forEach((x) => out.add(x.player));
  }
  return out;
}

/** The scorecard one innings at a time (batting on the left, bowling on the right: your request of 14 November), with
 *  buttons to switch innings, the partnerships and how the wickets fell. A ★ marks the innings' best batter and bowler;
 *  the player of the match has a 🏆 by his name, and only the rows he earned it with are shaded: his batting when he
 *  made runs, his bowling when he took wickets. */
export function Scorecard({ m }: { m: Match }) {
  const t = useTheme();
  const [i, setI] = useState(0);
  const n = nth(m), c = m.cards[i];
  if (!c) return <Missing why="This match has no innings." />;
  const opp = m.cards.find((x) => x.team !== c.team)?.team ?? "";
  const stars = starsOf(c);
  const pom = m.pom?.player ?? "";
  const mark = (p: string) => <>{stars.has(p) && <span className="star" title="The best in this innings">★</span>}
    {p === pom && <span className="pomk" title="Player of the match">🏆</span>}</>;
  const kinds: Record<string, number> = {};
  c.bat.filter((x) => x.out).forEach((x) => { kinds[x.how_out] = (kinds[x.how_out] ?? 0) + 1; });
  const KC: Record<string, string> = { caught: t.led, bowled: t.warm, lbw: t.cream, "run out": t.win, stumped: t.grey };
  const dots = c.bowl.every((x) => x.maidens == null) && c.bowl.some((x) => x.dots != null);
  const label = (k: number) => (isTest(m) ? `${m.cards[k]?.team} ${ORD[(n[k] ?? 1) - 1]} innings${m.cards[k]?.followed_on ? " (f/o)" : ""}` : `${ORD[(n[k] ?? 1) - 1]} innings · ${m.cards[k]?.team}`);
  const balls = Boolean(c.counted_in_balls);   // The Hundred counts balls, not overs
  const dnb = c.bat.filter((x) => !x.did_bat).map((x) => x.player);
  let prev = 0;
  const falls = c.fow.map((w) => { const s = `${w.wicket}-${w.score} (+${w.score - prev})`; prev = w.score; return s; });
  return (
    <>
      <div className="itabs"><span className="tl2 row2" style={{ gap: 10 }}><Logo comp={m.event} size={40} />Scorecard</span>{m.cards.map((x, k) => (
        <button key={x.innings_no} className={k === i ? "on" : ""} onClick={() => setI(k)}>{label(k)} {sc_(x)}</button>))}</div>
      <div className="grid" style={{ gridColumn: "span 12" }}>
        <Tile span={7} title={`Batting · ${c.team} · ${ORD[(n[i] ?? 1) - 1]} innings`}>
          <table className="c"><thead><tr><th>Batter</th><th className="r">R</th><th className="r">B</th><th className="r">4s</th><th className="r">6s</th><th className="r">SR</th></tr></thead>
            <tbody>{c.bat.filter((x) => x.did_bat).map((x) => (
              <tr key={x.player} className={x.player === pom && x.runs > 0 ? "me" : ""}>
                <td><PName p={x.player} px={21} />{mark(x.player)}<div className="how">{x.out ? x.dismissal || x.how_out : "not out"}</div></td>
                <td className="r"><span className="tn">{x.runs}{x.out ? "" : "*"}</span><span className="inl" style={{ width: x.runs / 1.6 }} /></td>
                <td className="r"><span className="tn dimn">{x.balls}</span></td><td className="r"><span className="tn dimn">{x.fours}</span></td>
                <td className="r"><span className="tn dimn">{x.sixes}</span></td><td className="r"><span className="tn dimn">{f0((x.runs / Math.max(x.balls, 1)) * 100)}</span></td></tr>))}
              <tr><td><span className="pn" style={{ fontSize: ts(21) }}>Total</span><div className="how">{c.length ?? `${c.overs} overs`} · {c.extras_text ?? `extras ${c.extras}`}</div></td>
                <td className="r" colSpan={5}><Num v={sc_(c)} px={34} /></td></tr></tbody></table>
          {dnb.length > 0 && <div className="note">Did not bat: {dnb.join(", ")}{dnb.includes(pom) ? " (🏆 the player of the match)" : ""}</div>}
          <div className="note">Fall of wickets (the stand in brackets): {falls.join(", ") || "none"}</div>
        </Tile>
        <Tile span={5} title={`Bowling · ${opp}`}>
          <table className="c"><thead><tr><th>Bowler</th><th className="r">{balls ? "B" : "O"}</th><th className="r" title={dots ? "Dot balls" : "Maidens"}>{dots ? "0s" : "M"}</th><th className="r">R</th><th className="r">W</th><th className="r">Econ</th></tr></thead>
            <tbody>{c.bowl.map((x) => (
              <tr key={x.player} className={x.player === pom && x.wickets > 0 ? "me" : ""}><td><span className="cell"><Logo team={opp} size={44} /><Name p={x.player} px={21} />{mark(x.player)}</span></td>
                <td className="r"><span className="tn dimn">{balls ? x.balls : overs(x.balls)}</span></td><td className="r"><span className="tn dimn">{(dots ? x.dots : x.maidens) ?? "–"}</span></td>
                <td className="r"><span className="tn dimn">{x.runs}</span></td><td className="r"><span className="tn">{x.wickets}</span></td>
                <td className="r"><span className="tn dimn">{x.balls ? f2((x.runs / x.balls) * 6) : "–"}</span></td></tr>))}</tbody></table>
          <div className="note">★ the best batter and the best bowler in this innings · 🏆 the player of the match (shaded where he earned it).{dots ? " 0s: dot balls (a T20 card has no maidens)." : ""}</div>
        </Tile>
        <Tile span={8} title="Partnerships · runs added for each wicket">
          <PartnershipBars stands={m.stands.filter((s) => s.innings_no === c.innings_no)} />
          <div className="note">* = still together at the end.</div>
        </Tile>
        <Tile span={4} title={`How ${c.team} fell`}>
          {Object.keys(kinds).length
            ? <RingList items={Object.entries(kinds).sort((a, b) => b[1] - a[1]).map(([k, v]) => [cap(k), v, KC[k] ?? t.dim])} centre={String(c.wickets)} sub="wickets" />
            : <div className="note" style={{ paddingTop: 100, textAlign: "center" }}>No wickets fell.</div>}
        </Tile>
      </div>
    </>
  );
}

/** Every player this season, with the last five innings and a form arrow. */
export function SquadTable({ rows, mark, dim }: { rows: SquadRow[]; mark?: string; dim?: Set<string> }) {
  const t = useTheme();
  return (
    <table className="tv"><thead><tr><th>Player</th><th className="r">Mat</th><th className="r">Runs</th><th className="r">Avg</th><th className="r">SR</th>
      <th className="r">Wkts</th><th className="r">Econ</th><th>Last 5 innings · runs, oldest first</th><th className="r">Form</th></tr></thead>
      <tbody>{rows.map((x) => (
        <tr key={x.player} className={x.player === mark ? "me" : dim?.has(x.player) ? "dim" : ""} data-parts={x.parts ? JSON.stringify(x.parts) : undefined}><td><PName p={x.player} px={23} /></td>
          <td className="r"><span className="tn dimn">{x.games}</span></td><td className="r"><span className="tn">{x.runs}</span></td>
          <td className="r"><span className="tn dimn">{f1(x.average)}</span></td><td className="r"><span className="tn dimn">{f0(x.strike_rate)}</span></td>
          <td className="r"><span className="tn">{x.wickets || (x.bowled ? 0 : "–")}</span></td><td className="r"><span className="tn dimn">{f2(x.economy)}</span></td>
          <td><LastFive s={x.last5} /></td>
          <td className="r" style={{ fontSize: 18, color: x.form === "▲" ? t.win : x.form === "▼" ? t.loss : t.dim }}>{x.form}</td></tr>))}</tbody></table>
  );
}

/** Match by match: date, lamp, the scores with both badges, the headline, the result; each row opens its match. */
export function MatchRows({ results, team, compact }: { results: Result[]; team: string; compact?: boolean }) {
  const t = useTheme();
  if (compact) return <>{results.map((r) => (   // a narrow tile: the scores without badges, the result under the headline
    <MatchLink key={r.id} id={r.id} className="mrow lkrow" style={{ gridTemplateColumns: "64px 30px 196px minmax(0, 1fr)" }}><span style={{ display: "contents" }}>
      <span className="when">{fmtOf(r.section)} {r.no ?? ""}<br />{day(r.date)}</span><Lamp o={r.outcome} />
      <span className="sc2"><Num v={r.us} px={23} /><span className="s" style={{ margin: 0 }}>v</span><Num v={r.them} px={23} style={{ opacity: 0.7 }} /></span>
      <span><Name p={r.headline || r.result} px={17} /><div className="how">{r.result}</div></span></span></MatchLink>))}</>;
  return <>{results.map((r) => (
    <MatchLink key={r.id} id={r.id} className="mrow lkrow"><span style={{ display: "contents" }}>
      <span className="when row2" style={{ gap: 6 }}><span className="cslot sm"><Logo comp={r.event} size={32} /></span><span>{fmtOf(r.section)} {r.no ?? ""}<br />{day(r.date)}</span></span><Lamp o={r.outcome} />
      <span className="sc2"><Logo team={team} size={40} /><Num v={r.us} px={26} /><span className="s" style={{ margin: "0 2px" }}>v</span>
        <Num v={r.them} px={26} style={{ opacity: 0.7 }} /><Logo team={r.opp} size={40} /></span>
      <span><Name p={r.headline || r.result} px={18} /></span>
      <span className="res" style={{ color: r.outcome === "W" ? t.win : r.outcome === "L" ? t.loss : t.dim }}>{r.result}</span></span></MatchLink>))}</>;
}

