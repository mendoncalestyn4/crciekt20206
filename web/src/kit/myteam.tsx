// My team's own pieces: the marks out of 10 after a series, who to bring in, what changed after the latest game,
// what's next, the report card's grades.
import { Link } from "react-router";
import type { Advice, MyTeam, ReportCard } from "../api";
import { dayY, pct } from "../format";
import { useTheme } from "../theme";
import { Name, PName } from "./base";
import { T } from "../shell/names";

/** A mark out of 10 as a badge: green 8 and up, gold 5 to 7, red 4 and under. */
export function Mark({ v, big }: { v: number; big?: boolean }) {
  const t = useTheme();
  const c = v >= 8 ? t.win : v >= 5 ? t.led : t.loss;
  return <span className={`mark ${big ? "big" : ""}`} style={{ borderColor: c, color: c }}>{v}</span>;
}

/** Every player who played in the series, best first: the mark, what they did, and their best match. */
export function MarksTable({ r, keep }: { r: ReportCard; keep: string }) {
  return (
    <table className="c marks"><thead><tr><th className="r">#</th><th>Player</th><th className="r">Mark</th><th>In the series</th><th>Best match</th></tr></thead>
      <tbody>{r.players.map((p) => (
        <tr key={p.player}><td className="r"><span className="tn dimn">{p.rank}</span></td>
          <td><PName p={p.player} px={22} />
            <div className="how">{p.games} match{p.games === 1 ? "" : "es"}</div></td>
          <td className="r"><Mark v={p.mark} /></td>
          <td><span className="why">{p.line}</span></td>
          <td><Link to={`/matches/${p.best_match}${keep}`} className="why lk">{p.best}</Link></td></tr>))}</tbody></table>
  );
}

/** Struggling players and who to bring in: the verdict, why, and the best candidates with their numbers. */
export function AdviceList({ items }: { items: Advice[]; keep?: string }) {
  return <>{items.map((a) => (
    <div className="adv" key={a.player}>
      <div className="verdict2">{a.verdict}</div>
      <div className="how"><span data-player={a.player}>{a.player}</span> ({a.role.toLowerCase()}): {a.why}.</div>
      {a.elsewhere && <div className="how"><T>{a.elsewhere}</T></div>}
      {(a.own.bat || a.own.bowl) && <div className="how">Their numbers here, last two seasons (settled): {[a.own.bat, a.own.bowl].filter(Boolean).join(" · ")}.</div>}
      {a.picks.map((p, i) => (
        <div className={`pickx ${p.clears ? "ok" : ""}`} key={p.player}>
          <span className="n">{i + 1}</span>
          <div><PName p={p.player} px={22} />
            <span className="tagx">{p.role}{p.capped ? " · capped" : ""}{p.spinner ? " · spin" : ""}{p.unsure ? " · country a guess" : ""}</span>
            <div className="how">At this level: {[p.bat, p.bowl].filter(Boolean).join(" · ")}</div>
            <div className="how">Domestic, last two seasons, as it is{p.side ? ` (now at ${p.side})` : ""}: {[p.raw_bat, p.raw_bowl].filter(Boolean).join(" · ")}</div></div>
          <span className="gain">{p.gain >= 0 ? "+" : ""}{Math.round(p.gain * 100)}%</span></div>))}
    </div>))}</>;
}

export function AfterLines({ a, keep }: { a: NonNullable<MyTeam["after"]>; keep: string }) {
  const t = useTheme();
  return (
    <>
      <div className="facts">{a.lines.map((l) => (
        <div className="fact" key={l.k}><span>{l.k}</span><b style={l.up == null ? undefined : { color: l.up ? t.win : t.loss }}><T>{l.text}</T></b></div>))}</div>
      {a.form.map((f) => (
        <div className="frm" key={f.player}><span style={{ color: f.arrow === "▲" ? t.win : f.arrow === "▼" ? t.loss : t.dim }}>{f.arrow}</span>
          <PName p={f.player} px={21} /><span className="how"><T>{f.text}</T></span></div>))}
      {a.news.map((n) => <div className="how" key={n} style={{ marginTop: 6 }}>{n}</div>)}
      <div className="note">v {a.opponent}, {dayY(a.date)} · <Link to={`/matches/${a.match_id}${keep}`}>the scorecard</Link>. Rating: Elo before and after this game.
        Table: league position before and after. ▲ a big game for the player (well above their season average before it, or a haul); ▼ a low
        score after a run of good ones.</div>
    </>
  );
}

export function NextUp({ n }: { n: NonNullable<MyTeam["next_up"]> }) {
  const x = n.next;
  return (
    <>
      <div className="plain">📅 Your schedule: <b>{n.played}</b> of <b>{n.total}</b> played.</div>
      {x && <div className="plain">⏭ Next: <b>{x.what}</b>{x.venue ? ` · ${x.venue}` : ""} · {x.when}
        {x.chance && <> · 🔮 win <b>{pct(x.chance.win)}</b>{x.chance.draw != null ? `, draw ${pct(x.chance.draw)}` : ""}, {x.opponent} {pct(x.chance.lose)}</>}</div>}
      {n.under_way.map((u) => <div className="plain" key={u}>🔴 {u}</div>)}
      <div className="note">From your schedule (Fixtures); adding and changing fixtures arrives on the new site in stage 4.</div>
    </>
  );
}

/** The report card: each subject's grade against the average team here this season, and why. */
export function Grades({ card }: { card: { subject: string; grade: string; why: string }[] }) {
  return (
    <table className="c"><thead><tr><th>Report card</th><th className="r">Grade</th><th>Why</th></tr></thead>
      <tbody>{card.map((c) => (
        <tr key={c.subject}><td><Name p={c.subject} px={22} /></td><td className="r"><span className={`grade g${c.grade}`}>{c.grade}</span></td>
          <td><span className="why">{c.why}</span></td></tr>))}</tbody></table>
  );
}
