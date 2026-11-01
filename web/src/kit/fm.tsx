// The pieces you approved (Football Manager style): attributes out of 20, the scout report, squad
// depth rows and inbox messages. Used on the Player page, My team and the Inbox.
import { Link } from "react-router";
import type { Attr, Attributes, DepthPlayer, InboxMsg, ScoutReport } from "../api";
import { dayY } from "../format";
import { PName } from "./base";
import { Mark } from "./myteam";
import { T } from "../shell/names";

export const band = (v: number) => (v >= 16 ? "a4" : v >= 11 ? "a3" : v >= 6 ? "a2" : "a1");

export function AttrRow({ a }: { a: Attr }) {
  return <div className="attr" title={a.text}><span className="an">{a.name}</span>
    <span className={`av ${a.score == null ? "" : band(a.score)}`}>{a.score ?? "–"}</span><span className="how">{a.text}</span></div>;
}

/** The attributes for the jobs shown (`show`: a bowler's bowling, a batter's batting, an all-rounder's both), and the
 *  other job in one line. */
export function AttrGrid({ a, show, other, section }: { a: Attributes; show: ("bat" | "bowl")[]; other: string; section: string }) {
  const jobs = show.length ? show : (["bat", "bowl"] as const).filter((j) => a[j].length || a.short[j]);
  return (
    <>
      <div className={jobs.length > 1 ? "attrs" : "attrs one"}>{jobs.map((job) => (
        <div key={job}><div className="k3">{job === "bat" ? "Batting" : "Bowling"}{a[`${job}_overall`] != null ? ` · ${a[`${job}_overall`]}` : ""}</div>
          {a[job].length ? a[job].map((x) => <AttrRow key={x.name} a={x} />)
            : <div className="note">{a.short[job] ? `Not enough yet: ${a.short[job]}.` : job === "bowl" ? "Doesn't bowl here." : "Hasn't batted enough here."}</div>}</div>))}</div>
      {other && <div className="plain" style={{ marginTop: 10 }}>{other}</div>}
      <div className="note">20 is the best in {section}, 10 the middle: {a.pool.bat} batters and {a.pool.bowl} bowlers with enough cricket there. – means not enough of it yet to rate.</div>
    </>
  );
}

export function ScoutText({ r }: { r: ScoutReport }) {
  if (r.none) return <div className="note">{r.none}</div>;
  return (
    <>
      <div className="verdict2">{r.verdict}</div>
      {r.strengths.map((x) => <div className="sr plus" key={x}>{x}</div>)}
      {r.weaknesses.map((x) => <div className="sr minus" key={x}>{x}</div>)}
      {r.notes.map((x) => <div className="sr note2" key={x}>{x}</div>)}
      {!r.weaknesses.length && <div className="note">No weak spot at this level (nothing 6 or under).</div>}
    </>
  );
}

export function DepthRow({ p }: { p: DepthPlayer }) {
  return (
    <div className={`drow ${p.starts ? "st" : ""}`}>
      <span className={`av ${p.rating == null ? "" : band(Math.round(p.rating))}`} title={p.rating == null ? "Not enough cricket here yet for a rating" : `Rating ${p.rating} out of 20`}>
        {p.rating == null ? "–" : Math.round(p.rating)}</span>
      <PName p={p.player} px={19} />
      <span className="dm">{p.marks.map((m, i) => <Mark key={i} v={m} />)}</span>
    </div>);
}

const ICON: Record<InboxMsg["kind"], string> = { result: "🏏", struggling: "⚠️", knocking: "🚪", milestone: "🎯" };

/** One inbox message: new ones lit, read ones shaded; `onRemove` shows the ✕, `onOpen` marks it read. */
export function Msg({ m, keep, read, onOpen, onRemove }: { m: InboxMsg; keep: string; read?: boolean; onOpen?: () => void; onRemove?: () => void }) {
  return (
    <div className={`msg ${m.kind} ${read ? "read" : "fresh"}`} onClick={onOpen}>
      <span className="ic">{ICON[m.kind]}</span>
      <div><div className="msgt">{!read && <i className="dotnew" title="New" />}<T>{m.title}</T></div><div className="how"><T>{m.body}</T></div></div>
      <span className="md">{dayY(m.date)}<br />{m.match ? <Link className="lk" to={`/matches/${m.match}${keep}`}>scorecard</Link>
        : m.player ? <span className="lk" data-player={m.player}>{m.player}</span> : null}</span>
      {onRemove && <button className="msgx" title="Remove this message" aria-label="Remove this message"
        onClick={(e) => { e.stopPropagation(); onRemove(); }}>✕</button>}
    </div>);
}
