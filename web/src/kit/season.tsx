// The team's season and how it wins, as on the approved mock-ups: the month calendar (April to March), the form card,
// the series ladder, runs of results, our score against theirs, batting first or chasing, against stronger and weaker
// sides, home and away, and the match-winners. Every number comes from the server (server/styleguide.py).
import { useLayoutEffect, useRef, useState, type ReactNode } from "react";
import type { BatFirst, Brief, Calendar, Form, Innings, Outcome, Result, Run, Scores, Series, Strength, Venues, Winners } from "../api";
import { ab, day, dayer, fmtOf, ord, plural, rnd } from "../format";
import { useTheme } from "../theme";
import { useShell } from "../shell/Shell";
import { Lamp, Logo, MatchLink, Name, Num, PName } from "./base";
import { FormLine, StrengthDots } from "./charts";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const pct = (w: number, n: number) => (n ? `${rnd((w / n) * 100)}%` : "–");
const colourOf = (t: ReturnType<typeof useTheme>, o: Outcome) => (o === "W" ? t.win : o === "L" ? t.loss : t.dim);

/** The line under each match in the calendar: one colour per format (longest game first: cream, blue, gold, then
 *  purple, orange, teal for a second competition of the same length). */
function formatColours(t: ReturnType<typeof useTheme>, formats: Calendar["formats"]): Record<string, string> {
  // cream reads on a dark page; on a light one the longest game takes the page's ink instead
  const first: Record<string, string> = { multi: t.dark ? "#f1efe6" : t.ink, one: t.blue, t20: t.led }, extra = ["#c58bff", t.warm, "#5ee0d0", t.grey];
  const used = new Set<string>(), out: Record<string, string> = {};
  for (const f of formats) {
    if (!used.has(f.kind)) { out[f.section] = first[f.kind] ?? t.grey; used.add(f.kind); }
    else out[f.section] = extra.shift() ?? t.grey;
  }
  return out;
}

/** Twelve months, April to March: every match on its day (the opponent, green won, red lost, the line under it the
 *  format), each month's record, the best month lit up. */
export function MonthTiles({ cal }: { cal: Calendar }) {
  const t = useTheme(), col = formatColours(t, cal.formats);
  return (
    <>
      <div className="mts" data-chart>{cal.months.map((mo, i) => {
        const first = (new Date(Date.UTC(mo.year, mo.month - 1, 1)).getUTCDay() + 6) % 7, days = new Date(Date.UTC(mo.year, mo.month, 0)).getUTCDate();
        const prefix = `${mo.year}-${String(mo.month).padStart(2, "0")}-`;
        return (
          <div className={`mt ${i === cal.best ? "best" : ""} ${mo.played ? "" : "quiet"}`} key={prefix}>
            {i === cal.best && <span className="mt-tag">best month</span>}
            <div className="mt-h"><Name p={MONTHS[mo.month - 1] ?? ""} px={20} />
              <span className="r">{mo.played ? `${mo.won}–${mo.lost}` : ""}<small>{mo.played ? plural(mo.played, "match", "matches") : "no matches"}</small></span></div>
            {mo.extra.length > 0 && <div className="mt-x">{mo.extra.map((r) => (   // part of this season, played just before April or after March
              <span key={r.id} title={`${day(r.date)} v ${r.opp}: ${r.result}`}><Lamp o={r.outcome} />{day(r.date)} v {ab(r.opp)}</span>))}</div>}
            <div className="mt-d">{["M", "T", "W", "T", "F", "S", "S"].map((x, k) => <span className="dn" key={`d${k}`}>{x}</span>)}
              {Array.from({ length: first }, (_, k) => <span key={`e${k}`} />)}
              {Array.from({ length: days }, (_, d) => {
                const r = cal.results.find((x) => x.date === `${prefix}${String(d + 1).padStart(2, "0")}`);
                return r ? <span key={d} className={`m ${r.outcome} ${ab(r.opp).length > 3 ? "long" : ""}`} style={{ ["--fmt" as string]: col[r.section] }} title={`${day(r.date)} v ${r.opp}: ${r.result}`}>{ab(r.opp)}</span>
                  : <span key={d}>{d + 1}</span>;
              })}</div>
            <div className="mt-note">{mo.names.join(" · ")}</div>
          </div>);
      })}</div>
      <div className="legend"><span><i style={{ background: t.win }} />won</span><span><i style={{ background: t.loss }} />lost</span>
        <span><i style={{ background: t.grey }} />drawn or no result</span>
        {cal.formats.map((f) => <span key={f.section}><i className="ln" style={{ background: col[f.section] }} />{f.section}</span>)}</div>
    </>
  );
}

/** The form card for a tile: the record, the small form line and how it's going; before five matches, the results
 *  and when the line starts. */
export function FormCard({ results, form }: { results: Result[]; form: Form }) {
  const w = results.filter((r) => r.outcome === "W").length, l = results.filter((r) => r.outcome === "L").length, tr = form.trend;
  return (
    <>
      <div className="head2"><Num v={`${w}–${l}`} px={46} /><span className="oldnew">{plural(results.length, "match", "matches")}</span></div>
      {tr ? <>
        <div style={{ marginTop: 8 }}><FormLine results={results} form={form} /></div>
        <div className="trend">{tr.now == null ? "Last five: no wins or defeats (all drawn or no result)" : <>Last five: <b>{tr.now}%</b> won{tr.word && tr.prev != null ? ` · ${tr.word}${tr.word === "level" ? " with" : " from"} ${tr.prev}% five games before` : ""}</>}</div>
      </> : <>
        <div className="sq" style={{ margin: "16px 0 10px" }}>{results.map((r) => <Lamp key={r.id} o={r.outcome} />)}</div>
        <div className="trend">{plural(results.length, "match", "matches")}: the line starts after {form.n}.</div>
      </>}
    </>
  );
}

/** The big form line with its key. */
export function FormBig({ results, form }: { results: Result[]; form: Form }) {
  const t = useTheme();
  return (
    <>
      <FormLine results={results} form={form} big />
      <div className="legend"><span><i className="ln" style={{ background: t.led }} />won in the last five</span>
        <span><i className="ln" style={{ background: t.dim }} />the first five (not a full five yet)</span>
        <span><i className="dot" style={{ background: t.win }} />won</span><span><i className="dot" style={{ background: t.loss }} />lost</span>
        <span><i style={{ background: `color-mix(in srgb, ${t.win} 30%, transparent)` }} />hot (60%+)</span>
        <span><i style={{ background: `color-mix(in srgb, ${t.loss} 30%, transparent)` }} />cold (under 40%)</span>
        <span>bars over the results: each series and its score</span></div>
    </>
  );
}

const marginText = (r: Result) => {
  if (r.outcome === "D") return "drawn";
  if (r.outcome === "T") return "tied";
  if (r.outcome === "NR") return "no result";
  const by = r.innings_win ? `an innings and ${r.margin_runs} runs` : r.margin_runs != null ? plural(r.margin_runs, "run")
    : r.margin_wickets != null ? plural(r.margin_wickets, "wkt") : "";
  return `${r.outcome === "W" ? "won" : "lost"}${by ? ` by ${by}` : ""}`;
};

/** The series as a ladder: the score after every match in big numbers, each match's card under it, the decider
 *  marked. */
export function Ladder({ s, team }: { s: Series; team: string }) {
  const t = useTheme(), n = s.matches.length;
  return (
    <div className="lad" data-chart style={{ gridTemplateColumns: `repeat(${n}, minmax(0, 1fr))` }}>
      {s.matches.map((r, i) => { const p = s.progress[i] ?? { won: 0, lost: 0 };
        return <div key={`s${r.id}`}><div className="lad-score">{p.won}–{p.lost}<small>{p.won > p.lost ? `${ab(team)} lead` : p.won < p.lost ? `${ab(s.opp)} lead` : "level"}</small></div></div>; })}
      {s.matches.map((r) => <div className="lad-line" key={`l${r.id}`} />)}
      {s.matches.map((r, i) => { const dec = s.decider && i === n - 1;
        return (
          <div className={`lad-card ${dec ? "decider" : ""}`} key={`c${r.id}`}>{dec && <span className="dec">Decider</span>}
            <div className="when"><span>{fmtOf(r.section)} {r.no ?? i + 1} · {day(r.date)}</span><Lamp o={r.outcome} /></div>
            <div className="sc">{r.us}<i>v</i><span>{r.them}</span></div>
            <div className="res" style={{ color: colourOf(t, r.outcome) }}>{marginText(r)}</div>
          </div>); })}
    </div>
  );
}

const WORD: Record<Outcome, [string, string]> = { W: ["win", "wins"], L: ["defeat", "defeats"], D: ["draw", "draws"], T: ["tie", "ties"], NR: ["no result", "no results"] };
const lenOf = (r: Run) => r.end - r.start + 1;
const wordOf = (r: Run) => WORD[r.o][lenOf(r) > 1 ? 1 : 0];

/** Every match of the season in order, the longest winning and losing runs marked over their matches, and the run
 *  the team is on now. */
export function Streaks({ cal }: { cal: Pick<Calendar, "results" | "streaks"> }) {
  const t = useTheme(), rs = cal.results, runs = cal.streaks;
  const longest = (o: Outcome) => [...runs].filter((r) => r.o === o).sort((a, b) => lenOf(b) - lenOf(a))[0];
  const cur = runs[runs.length - 1], lw = longest("W"), ll = longest("L");
  const multi = new Set(rs.map((x) => x.date.slice(0, 4))).size > 1, dd = dayer(rs.map((x) => x.date));   // years shown when it runs over more than one
  const span = (r: Run) => (r.start === r.end ? dd(rs[r.start]!.date) : `${dd(rs[r.start]!.date)} – ${dd(rs[r.end]!.date)}`);
  const who = (r: Run) => [...new Set(rs.slice(r.start, r.end + 1).map((x) => ab(x.opp)))].join(", ");
  const card = (title: string, r: Run | undefined, none: string) => (
    <div className="bf-side"><div className="k">{title}</div>
      {r ? <><div className="big"><Num v={lenOf(r)} px={52} /><small>{wordOf(r)} in a row</small></div><div className="note" style={{ marginTop: 0 }}>{span(r)} · v {who(r)}</div></>
        : <div className="note">{none}</div>}</div>);
  const strip = useRef<HTMLDivElement>(null);
  const [w, setW] = useState(0);
  const [segs, setSegs] = useState<{ left: number; width: number; top: number; colour: string; text: string }[]>([]);
  useLayoutEffect(() => {
    const el = strip.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setW(el.clientWidth));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  const cols = Math.max(1, Math.min(rs.length, Math.floor((w + 6) / 52) || rs.length));   // a cell at least 46px wide
  useLayoutEffect(() => {   // each bracket spans exactly its matches' lamps, a piece on each line they're on
    const el = strip.current;
    if (!el || !w) return;
    const cells = [...el.querySelectorAll<HTMLElement>(".cellx")], out: typeof segs = [];
    for (const [r, colour] of [[lw, t.win], [ll, t.loss]] as const) {
      if (!r || lenOf(r) < 2) continue;
      const mine: typeof segs = [];
      for (let i = r.start; i <= r.end; i++) {
        const c = cells[i];
        if (!c) continue;
        const last = mine[mine.length - 1];
        if (last && last.top === c.offsetTop - 54) last.width = c.offsetLeft + c.offsetWidth - 2 - last.left;
        else mine.push({ left: c.offsetLeft + 2, width: c.offsetWidth - 4, top: c.offsetTop - 54, colour, text: "" });
      }
      const widest = mine.reduce((a, b) => (b.width > a.width ? b : a), mine[0]!);
      widest.text = `${lenOf(r)} ${wordOf(r)} in a row`;
      out.push(...mine);
    }
    setSegs(out);
  }, [w, cols, rs, lw, ll, t]);
  return (
    <>
      <div className="trio">{card("The run you're on", cur, "No matches yet.")}{card("Longest winning run", lw, "No wins yet.")}{card("Longest losing run", ll, "No defeats yet.")}</div>
      <div className="strip" data-chart ref={strip} style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}>
        {segs.map((s, i) => <div className="brk" key={i} style={{ left: s.left, width: s.width, top: s.top, borderColor: s.colour }}>
          {s.text && <span style={{ color: s.colour }}>{s.text}</span>}</div>)}
        {rs.map((r) => <MatchLink key={r.id} id={r.id} className="cellx lkrow"><Lamp o={r.outcome} /><small className="f">{fmtOf(r.section)}</small><small>{ab(r.opp)}</small><small>{day(r.date)}</small>{multi && <small>’{r.date.slice(2, 4)}</small>}</MatchLink>)}
      </div>
    </>
  );
}

const score = (i: Innings | undefined) => (i ? `${i.runs}${i.all_out ? "" : `/${i.wkts}`}${i.declared ? "d" : ""}` : "");

/** Our score and theirs, one row per match (a Test: one row per innings), joined by a green line when the team won
 *  and red when it lost; the summary over it. Newest first. */
export function ScoreRows({ results, scores, narrow }: { results: Result[]; scores?: Scores | null; narrow?: boolean }) {
  const t = useTheme();
  // the track's width, so the scale leaves room for the longest score beside the dots at both ends ("521/4d" on a
  // narrow tile used to run past it)
  const box = useRef<HTMLDivElement>(null);
  const [tw, setTw] = useState(0);
  useLayoutEffect(() => {   // measured again when the rows change (none on the first render while the page loads)
    const el = box.current?.querySelector(".db-trk");
    if (!el) return;
    setTw(el.clientWidth);
    const ro = new ResizeObserver(() => setTw(el.clientWidth));
    ro.observe(el);
    return () => ro.disconnect();
  }, [results]);
  const lines = results.flatMap((r) => Array.from({ length: Math.max(r.ours.length, r.theirs.length) }, (_, k) => ({ r, o: r.ours[k], th: r.theirs[k], k, n: Math.max(r.ours.length, r.theirs.length) })));
  const vals = lines.flatMap((l) => [l.o?.runs, l.th?.runs]).filter((v): v is number => v != null);
  if (!vals.length) return null;
  const longest = Math.max(...lines.flatMap((l) => [score(l.o).length, score(l.th).length]));
  const need = 18 + longest * 10.5;                      // px from a dot to the far end of its label (17px Space Grotesk)
  const track = tw || 300;
  const frac = Math.min(0.4, need / track);
  const mn = Math.min(...vals), mx = Math.max(...vals), span = Math.max(mx - mn, 1) / (1 - 2 * frac);
  // below 0 when a score near 0 needs the room (an abandoned game's 0/0); the axis doesn't print a negative number
  const lo = Math.floor((mn - frac * span) / 25) * 25, hi = Math.ceil((mx + frac * span) / 25) * 25;
  const x = (v: number) => ((v - lo) / (hi - lo)) * 100;
  const cols = narrow ? { gridTemplateColumns: "62px 92px minmax(0, 1fr)" } : undefined;
  const lab = (pos: number, other: number | null, ours: boolean, text: string, colour: string) => {
    const left = other == null || pos < other || (pos === other && ours);   // the lower score's label on its left
    return left
      ? <span className="v" style={{ right: `calc(${100 - pos}% + 14px)`, color: colour }}>{text}</span>
      : <span className="v" style={{ left: `calc(${pos}% + 14px)`, color: colour }}>{text}</span>;
  };
  return (
    <div ref={box} data-chart>
      {scores && <div className="db-sum">{scores.avg_made != null && <div>Average made<b style={{ color: t.led }}>{scores.avg_made}</b></div>}
        {scores.avg_conceded != null && <div>Average conceded<b style={{ color: t.blue }}>{scores.avg_conceded}</b></div>}
        <div>Won<b style={{ color: t.win }}>{scores.won}</b></div><div>Lost<b style={{ color: t.loss }}>{scores.lost}</b></div></div>}
      {lines.map(({ r, o, th, k, n }) => {
        const a = o ? x(o.runs) : null, b = th ? x(th.runs) : null;
        return (
          <div className="db-row" style={cols} key={`${r.id}-${k}`}>
            <MatchLink id={r.id} className="db-when lkrow"><b>{day(r.date)}</b>{n > 1 ? `${ord(k + 1)} inns` : `${fmtOf(r.section)}${r.no ? ` ${r.no}` : ""}`}</MatchLink>
            <span className="db-who"><Lamp o={r.outcome} />{!narrow && <Logo team={r.opp} size={36} />}<Name p={narrow ? ab(r.opp) : r.opp} px={16} /></span>
            <div className="db-trk">
              {a != null && b != null && <span className="ln" style={{ left: `${Math.min(a, b)}%`, width: `${Math.abs(a - b)}%`, background: colourOf(t, r.outcome) }} />}
              {a != null && <><span className="dot" style={{ left: `${a}%`, background: t.led }} />{lab(a, b, true, score(o), t.led)}</>}
              {b != null && <><span className="dot" style={{ left: `${b}%`, background: t.blue }} />{lab(b, a, false, score(th), t.blue)}</>}
              {r.rain && <span className="v rain">rain</span>}
            </div>
          </div>);
      })}
      <div className="db-axis" style={cols}><span /><span /><div><span>{lo < 0 ? "" : lo}</span><span>{(lo + hi) / 2 < 0 ? "" : Math.round((lo + hi) / 2)}</span><span>{hi}</span></div></div>
    </div>
  );
}

function Side({ title, rec, sub, children }: { title: string; rec: { played: number; won: number; lost: number }; sub?: ReactNode; children?: ReactNode }) {
  return (
    <div className="bf-side"><div className="k">{title}</div>
      <div className="big"><Num v={rec.played ? `${rec.won}–${rec.lost}` : "–"} px={52} /><small>{rec.played ? `${rec.played} played · won ${pct(rec.won, rec.played)}` : "none yet"}</small></div>
      {sub && <div className="note" style={{ marginTop: 0 }}>{sub}</div>}{children}</div>
  );
}

function Fact({ label, b }: { label: string; b: Brief | undefined }) {
  if (!b) return null;
  return <div className="fact"><span>{label}</span><b>{b.score}<small>v {ab(b.opp)} · {day(b.date)}</small></b></div>;
}

/** Batting first or chasing: the record each way, with the totals defended, lost with, chased down and not chased.
 *  `who` names the side when it isn't yours (Opponent preview: their own record). */
export function BatFirstSides({ bf, who }: { bf: BatFirst; who?: string }) {
  const a = bf.first, c = bf.chase, rate = (x: typeof a) => (x.played ? x.won / x.played : 0);
  const better = !a.played || !c.played || pct(a.won, a.played) === pct(c.won, c.played) ? "" : rate(a) > rate(c) ? "batting first" : bf.multi ? "batting second" : "chasing";
  const they = who ? "they" : "you";
  return (
    <>
      <div className="bf" data-chart><Side title="Batting first" rec={a}><Fact label="Lowest total defended" b={bf.lowest_defended} /><Fact label={`Highest total ${they} lost with`} b={bf.highest_lost} /></Side>
        <Side title={bf.multi ? "Batting second" : "Chasing"} rec={c}><Fact label="Highest total chased down" b={bf.highest_chased} /><Fact label={`Lowest total ${they} failed to chase`} b={bf.lowest_missed} /></Side></div>
      {bf.avg_set != null && <div className="fact" style={{ border: 0, marginTop: 8 }}><span>Average score batting first</span><b>{bf.avg_set}</b></div>}
      {better && <div className="verdict">{who ?? "You"} win more often <span>{better}</span>: {pct(c.won, c.played)} {bf.multi ? "batting second" : "chasing"}, {pct(a.won, a.played)} batting first.</div>}
    </>
  );
}

/** Against stronger and weaker sides: the record each way, every match placed by the rating gap, the best win and the
 *  worst defeat. */
export function StrengthPanel({ rows, lanes }: { rows: Strength[]; lanes: string[] }) {
  const rec = (x: Strength[]) => ({ played: x.length, won: x.filter((r) => r.outcome === "W").length, lost: x.filter((r) => r.outcome === "L").length });
  const above = rows.filter((r) => r.gap > 0), level = rows.filter((r) => r.gap === 0), below = rows.filter((r) => r.gap < 0);
  const best = rows.filter((r) => r.outcome === "W" && r.gap > 0).sort((a, b) => b.gap - a.gap)[0];
  const worst = rows.filter((r) => r.outcome === "L" && r.gap < 0).sort((a, b) => a.gap - b.gap)[0];
  return (
    <>
      <div className="trio" data-chart><Side title="V stronger sides" rec={rec(above)} sub="Rated above you before the match" />
        <Side title="Level" rec={rec(level)} sub="First meetings, both still at the starting rating" />
        <Side title="V weaker sides" rec={rec(below)} sub="Rated below you before the match" /></div>
      <div style={{ marginTop: 14 }}><StrengthDots rows={rows} lanes={lanes} /></div>
      {best && <div className="fact"><span>Best win · beat the side rated furthest above you</span><b>+{best.gap}<small>{best.opp} · {day(best.date)}</small></b></div>}
      {worst && <div className="fact"><span>Worst defeat · lost to the side rated furthest below you</span><b>{worst.gap}<small>{worst.opp} · {day(worst.date)}</small></b></div>}
    </>
  );
}

/** Home, away and neutral, then host by host (by country for a national side). */
export function VenueRecord({ v, team, who }: { v: Venues; team: string; who?: boolean }) {
  const t = useTheme(), top = Math.max(...v.hosts.map((h) => h.played), 1);
  const { logos } = useShell(), slot = v.hosts.some((h) => h.host && logos.teams.has(h.host));   // badges line up
  const name = (h: Venues["hosts"][number]) => (h.venue === "neutral" ? "Neutral grounds" : h.venue === "home" ? (v.nation ? `In ${team} (home)` : "At home") : `${v.nation ? "In" : "At"} ${h.host}`);
  return (
    <>
      <div className="trio"><Side title="Home" rec={v.home} sub={v.nation ? `In ${team}` : who ? "On their own ground" : "On your own ground"} />
        <Side title="Away" rec={v.away} sub={v.nation ? "In the other side's country" : "On the other side's ground"} />
        <Side title="Neutral" rec={v.neutral} sub="World Cups, finals and the like" /></div>
      <div className="ctys" data-chart style={{ marginTop: 16 }}>{v.hosts.map((h) => (
        <div className="cty" key={h.host || "neutral"}><span className="row2" style={{ gap: 10 }}>{slot && <span className="slot">{h.host && <Logo team={h.host} size={40} />}</span>}<Name p={name(h)} px={17} /></span>
          <div><div className="stack" style={{ width: `${(h.played / top) * 100}%` }}>{h.outcomes.map((o, i) => <i key={i} style={{ background: colourOf(t, o) === t.dim ? t.grey : colourOf(t, o) }} />)}</div></div>
          <span className="r">{h.won}–{h.lost}<small>{h.played}</small></span></div>))}</div>
    </>
  );
}

/** Who wins the team's matches: its players of the match in its wins, most first, with what they did each time. */
export function MatchWinners({ w }: { w: Winners }) {
  const most = w.players[0]?.matches.length ?? 1;
  return <>{w.players.map(({ player, matches }) => (
    <div className="mw" data-chart key={player}><span className="n">{matches.length}<small>{matches.length > 1 ? "wins" : "win"}</small></span>
      <div><PName p={player} px={22} /><div className="bar" style={{ marginTop: 8 }}><i style={{ width: `${(matches.length / most) * 100}%` }} /></div></div>
      <div className="hls">{matches.map((x) => <MatchLink key={x.id} id={x.id} className="lkrow"><b>{fmtOf(x.section)} v {ab(x.opp)} · {day(x.date)}</b>{x.headline}</MatchLink>)}</div></div>))}
    {w.others > 0 && <div className="note">{plural(w.others, "other win")}: the player of the match was on the other side, or none was named.</div>}</>;
}

/** Where a piece goes on the new site. */
export function Goes({ items }: { items: [string, string][] }) {
  return <div className="goes">{items.map(([k, v]) => <div key={k}><b>{k}</b><span>{v}</span></div>)}</div>;
}
