// A demo of ideas 2, 3, 5 and 7 (attributes out of 20, the scout report, squad depth, the inbox) beside the marks and
// the replacement advice, with your own numbers: not linked from the rail until you approve them.
import { useQuery } from "@tanstack/react-query";
import { Fragment } from "react";
import { Link, useSearchParams } from "react-router";
import { get, type Attr, type DemoPage, type DepthPlayer, type InboxMsg } from "../api";
import { Missing, Name, Tile } from "../kit/base";
import { AdviceList, Mark, MarksTable } from "../kit/myteam";
import { dayY, fmtOf } from "../format";
import { useReady } from "../ready";
import { Head, useShell } from "../shell/Shell";

const ICON: Record<InboxMsg["kind"], string> = { result: "🏏", struggling: "⚠️", knocking: "🚪", milestone: "🎯" };

export function Demo() {
  const { nation } = useShell();
  const keep = nation ? `?nation=${encodeURIComponent(nation)}` : "";
  const [params, setParams] = useSearchParams();
  const team = params.get("team") ?? "India", section = params.get("section") ?? "", players = params.get("players") ?? "";
  const q = useQuery({ queryKey: ["demo", team, section, players], retry: false,
    queryFn: () => get<DemoPage>(`/api/demo?team=${encodeURIComponent(team)}&section=${encodeURIComponent(section)}&players=${encodeURIComponent(players)}`) });
  useReady(Boolean(q.data || q.error), `${team}|${section}|${players}`);
  if (q.error) return <><Head title="Demo" crumb={team} /><div className="grid"><Tile span={12}><Missing why={String(q.error)} /></Tile></div></>;
  if (!q.data) return <><Head title="Demo" crumb="Working it out…" /><div className="empty">Working out {team}'s numbers…</div></>;
  const d = q.data, newest = d.inbox?.[0]?.date ?? "";
  const unread = (d.inbox ?? []).filter((m) => m.date === newest);
  return (
    <>
      <Head title="Demo" crumb={`Ideas 2, 3, 5 and 7 with your numbers: ${d.team} · not on the site until you approve them`}
        chips={d.sections.map(fmtOf)} on={d.sections.indexOf(d.section)}
        onChip={(i) => { const p = new URLSearchParams(params); p.set("section", d.sections[i]!); setParams(p); }} />
      <div className="grid">
        <div className="part"><span className="tl2">On My team</span><span className="note" style={{ margin: 0 }}>the inbox's newest messages at the top, then the marks, who to bring in and the squad depth</span></div>
        {d.inbox && <Tile span={12} title={`Inbox · ${unread.length} new`} right={`after ${unread[0]?.series ?? ""}`}>
          <div className="inbox">{unread.slice(0, 4).map((m, i) => <Msg key={i} m={m} keep={keep} />)}</div></Tile>}
        {d.report && <Tile span={7} title="After the series · marks out of 10" right={d.report.label}><MarksTable r={d.report} keep={keep} /></Tile>}
        {d.report && <Tile span={5} title="Who to bring in" right={d.report.advice.length ? `${d.report.advice.length} to look at` : "nobody struggling"}>
          {d.report.advice.length ? <AdviceList items={d.report.advice} keep={keep} /> : <div className="plain">Nobody is struggling.</div>}</Tile>}
        {d.depth ? <Tile span={12} title={`Squad depth · ${d.depth.section}`} right="who starts, who's next, who's waiting in domestic cricket">
          <div className="depth">{d.depth.roles.map((r) => (
            <div className="drole" key={r.role}><div className="k3">{r.role}</div>
              {r.starters.map((p) => <DepthRow key={p.player} p={p} keep={keep} />)}
              {r.backups.length > 0 && <div className="dsub">Backups</div>}
              {r.backups.map((p) => <DepthRow key={p.player} p={p} keep={keep} />)}
              {r.waiting.length > 0 && <div className="dsub">Waiting in domestic cricket</div>}
              {r.waiting.map((w) => (
                <div className={`dwait ${w.clears ? "ok" : ""}`} key={w.player}><Link className="plink" to={`/players/${encodeURIComponent(w.player)}${keep}`}><Name p={w.player} px={19} /></Link>
                  <span className="gain">{w.gain == null ? "" : `${w.gain >= 0 ? "+" : ""}${Math.round(w.gain * 100)}%`}</span>
                  <div className="how">{w.side} · {w.raw_bat || w.raw_bowl}</div></div>))}
              {!r.starters.length && !r.backups.length && !r.waiting.length && <div className="note">Nobody in this role yet.</div>}
            </div>))}</div>
          <div className="note">Starters: who played in {d.depth.series ? "the latest series" : "the latest games"}. The number is their rating out of 20 here (the average of their
            attributes; – means not enough cricket here yet); the small marks are their last three series, newest first. Waiting: the best eligible domestic players, and how much better than your
            weakest in the role they are after the conversion (green: 10% or more).</div></Tile> : <Tile span={12} title="Squad depth"><Missing why={d.missing.depth} /></Tile>}

        <div className="part"><span className="tl2">On the Player page</span><span className="note" style={{ margin: 0 }}>at the top, next to the career card · {d.section} only, never mixed with other formats</span></div>
        {(d.players ?? []).map((p) => (
          <Fragment key={p.player}>
            <Tile span={7} title={`${p.player} · attributes in ${d.section}`} right="out of 20 · against everyone there">
              <div className="attrs">{(["bat", "bowl"] as const).map((job) => (
                <div key={job}><div className="k3">{job === "bat" ? "Batting" : "Bowling"}{p.attributes[`${job}_overall`] != null ? ` · ${p.attributes[`${job}_overall`]}` : ""}</div>
                  {p.attributes[job].length ? p.attributes[job].map((a) => <AttrRow key={a.name} a={a} />)
                    : <div className="note">{p.attributes.short[job] ? `Not enough yet: ${p.attributes.short[job]}.` : job === "bowl" ? "Doesn't bowl here." : "Hasn't batted enough here."}</div>}</div>))}</div>
              <div className="note">20 is the best in {d.section}, 10 the middle: {p.attributes.pool.bat} batters and {p.attributes.pool.bowl} bowlers with enough cricket there. – means not enough of it yet to rate.</div>
            </Tile>
            <Tile span={5} title="Scout report" right={p.report.role ?? ""}>
              {p.report.none ? <div className="note">{p.report.none}</div> : <>
                <div className="verdict2">{p.report.verdict}</div>
                {p.report.strengths.map((x) => <div className="sr plus" key={x}>{x}</div>)}
                {p.report.weaknesses.map((x) => <div className="sr minus" key={x}>{x}</div>)}
                {p.report.notes.map((x) => <div className="sr note2" key={x}>{x}</div>)}
                {!p.report.weaknesses.length && <div className="note">No weak spot at this level (nothing 6 or under).</div>}</>}
            </Tile>
          </Fragment>))}

        <div className="part"><span className="tl2">Inbox</span><span className="note" style={{ margin: 0 }}>a new item in the rail with the number of new messages</span></div>
        {d.inbox && <Tile span={12} title={`Every message · ${d.inbox.length}`} right="newest first">
          <div className="inbox">{d.inbox.map((m, i) => <Msg key={i} m={m} keep={keep} fresh={m.date === newest} />)}</div></Tile>}
      </div>
    </>
  );
}

function band(v: number) { return v >= 16 ? "a4" : v >= 11 ? "a3" : v >= 6 ? "a2" : "a1"; }

function AttrRow({ a }: { a: Attr }) {
  return <div className="attr" title={a.text}><span className="an">{a.name}</span>
    <span className={`av ${a.score == null ? "" : band(a.score)}`}>{a.score ?? "–"}</span><span className="how">{a.text}</span></div>;
}

function DepthRow({ p, keep }: { p: DepthPlayer; keep: string }) {
  return (
    <div className={`drow ${p.starts ? "st" : ""}`}>
      <span className={`av ${p.rating == null ? "" : band(Math.round(p.rating))}`} title={p.rating == null ? "Not enough cricket here yet for a rating" : `Rating ${p.rating} out of 20`}>
        {p.rating == null ? "–" : Math.round(p.rating)}</span>
      <Link className="plink" to={`/players/${encodeURIComponent(p.player)}${keep}`}><Name p={p.player} px={19} /></Link>
      <span className="dm">{p.marks.map((m, i) => <Mark key={i} v={m} />)}</span>
    </div>);
}

function Msg({ m, keep, fresh }: { m: InboxMsg; keep: string; fresh?: boolean }) {
  return (
    <div className={`msg ${m.kind} ${fresh ? "fresh" : ""}`}>
      <span className="ic">{ICON[m.kind]}</span>
      <div><div className="msgt">{m.title}</div><div className="how">{m.body}</div></div>
      <span className="md">{dayY(m.date)}<br />{m.match ? <Link className="lk" to={`/matches/${m.match}${keep}`}>scorecard</Link>
        : m.player ? <Link className="lk" to={`/players/${encodeURIComponent(m.player)}${keep}`}>player</Link> : null}</span>
    </div>);
}
