// Fixtures (stage 4): your schedule, in the current site's 8 tabs: Schedule, Add matches, Change or delete, Series,
// Calendar, WTC race, Milestones, Goals. Schedules are made only for your teams (your answer of 26 November); every
// change can be undone from the list of recent changes. Every number comes from the server (server/fixturespage.py).
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type ReactNode, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import { get, type GridT, type CalMonth, type Outcome, post } from "../api";
import { Explain, Lamps, Logo, MatchLink, Missing, Pick, three, Tile } from "../kit/base";
import { MonthGrid } from "../kit/calendar";
import { EChart } from "../kit/EChart";
import { look, ts } from "../kit/look";
import { Grid, Md } from "../kit/teams";
import { useReady } from "../ready";
import { Head, useShell } from "../shell/Shell";
import { T } from "../shell/names";
import { useTheme } from "../theme";

type Three = { is_?: string; best?: string; best_label?: string; for_?: string; shows?: string };
type Chance = { win: number; draw: number; lose: number; multi?: boolean; level?: string; icon?: string };
type Last = { id: string; date: string; outcome: string; result: string; text: string; players: string[] } | null;
type Row = { icon: string; status: string; series: string; auto: boolean; badge: string; venue_note: string; venue_real: string;
  no: string; opponent: string; when: string; result: string; id: string | null; chance?: Chance; form?: Outcome[];
  rivalry?: { kind: string; icon: string; tip: string } | null; last?: Last };
type PreviewLink = { section: string; mine: string; opp: string; where: string };
type PreviewAny = { options: string[]; scheduled: string[]; formats: string[]; defaults: Record<string, { format: string; venue: string }>;
  links: Record<string, Record<string, PreviewLink>> } | null;
type Schedule = { empty?: string; info?: string; kpis?: [string, string][]; check?: { text: string; series: string; kind: string; fix: string }[];
  check_ok?: boolean; next?: { title: string; venue: string; when: string; opponent: string; note: string; chance?: Chance; form?: Outcome[];
    rivalry?: string; streaks?: string[]; battles?: string[]; preview?: PreviewLink; last?: Last };
  preview_any?: PreviewAny; missing_warn?: string; rows?: Row[]; caption?: string;
  outlook?: (Three & { title: string; left: string; kpis: [string, string][]; tough?: string; bars: { label: string; value: number; level: string; tip: string; team: string }[];
    by_format?: GridT; caption: string }) | null };
type Item = { series: string; kind: string; icon: string; played: number; total: number; when: string; venue: string; venue_word: string;
  opponent: string; format: string; n: number; month: string; date: string; dates: string[]; games: number };
type TableRow = { id: string; series: string; opponent: string; format: string; no: number; venue: string; month: string; date: string; games: number };
type Change = { items: Item[]; none: string; table: TableRow[]; table_caption: string; table_opponents: string[]; table_formats: string[] };
type Odds = { A: number; B: number; level: number; show_level: boolean };
type Extras = { past_title: string; past?: string[]; past_line?: string; past_none?: string; records: string[]; conditions_title?: string;
  conditions?: GridT; toss?: string; conditions_none?: string; travel_title?: string; travel_good?: { player: string; text: string }[];
  travel_worse?: { player: string; text: string }[]; travel_none?: string; note: string; is_goal: boolean };
type Review = { use_more: { player: string; why: string }[]; drop: { player: string; why: string }[]; keep: string[]; table?: GridT; caption: string } | null;
type SeriesBody = { none: string;
  live: { series: string; opponent: string; lead: string; left: number; need: string; odds: Odds; scorelines: string; extras: Extras }[];
  tournaments: { name: string; record: string; next: string; path?: { lines: string[]; by_wins: [number, number][]; caption: string }; over?: string }[];
  coming: { series: string; opponent: string; format: string; odds: Odds; scorelines: string; form: Record<string, Outcome[]>; h2h: string;
    watch: { team: string; matches: number; bat: [string, number][]; bowl: [string, number][] }[]; battles: string[]; pick: string[]; think: string[];
    nobody: boolean; extras: Extras; preview: PreviewLink }[];
  forecasts?: string;
  done: { series: string; title: string; result: string; span: string; forecast?: string; pos?: { player: string; team: string; text: string };
    top_bat: [string, string, number][]; top_bowl: [string, string, number][]; bits: string; records: string[]; milestones: string[];
    matches: { id: string; date: string }[]; review: Review }[];
  predictions?: (Three & { table: GridT; summary: string; bars: { label: string; value: number; n: number }[] }) | null };
type Cal = { none?: string; seasons: { key: string; label: string }[]; season: string; today: string; grid: CalMonth[]; caption?: string } & Three;
type Wtc = { none?: string; title?: string; left?: string; table?: GridT; line?: string; caption?: string };
type Miles = { none?: string; title?: string; table?: GridT; caption?: string };
type Goal = Record<string, string | number>;
type Goals = { goals: { id: string; label: string; text: string; status: string; badge: string; done: number }[]; none: string;
  suggested: { goal: Goal; label: string }[]; kinds: { v: string; label: string; group: string }[]; series: string[]; wtc: boolean;
  choices: { sections: string[]; leagues: string[]; seasons: Record<string, string[]>; years: { v: string; label: string }[]; formats: string[];
    opponents: string[]; players: string[] }; formats: string[]; years: string[] };
type Page = { tabs: string[]; tab: string; teams: string[]; team: string; how_to: string; none: string; national?: boolean; scheduled_any?: boolean;
  formats?: string[]; competitions?: { name: string; format: string; opponents: string[] }[]; opponents?: string[]; years?: number[];
  year_now?: number; month_now?: number; tournaments?: string[]; tournament_format?: Record<string, string>;
  history?: { id: string; what: string; at: string }[];
  body?: (Schedule & Change & SeriesBody & Cal & Wtc & Miles & Goals & { missing?: string }) };

const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
const WHERE = [{ v: "home", label: "Home" }, { v: "away", label: "Away" }, { v: "neutral", label: "Neutral" }];
const mm = (y: number, m: number) => `${y}-${String(m).padStart(2, "0")}`;

export function Fixtures() {
  const { career, noCareer, nation } = useShell();
  const [params] = useSearchParams();
  const go = useNavigate();
  const qc = useQueryClient();
  const keep = nation ? `?nation=${encodeURIComponent(nation)}` : "";
  const want = { team: params.get("team") ?? "", tab: params.get("tab") ?? "", season: params.get("season") ?? "" };
  const qs = Object.entries(want).map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join("&");
  const q = useQuery({ queryKey: ["fixtures", qs, career?.name], enabled: Boolean(career), retry: false,
    queryFn: () => get<Page>(`/api/fixtures?${qs}`) });
  const [said, setSaid] = useState<{ ok: boolean; text: string } | null>(null);
  useReady(Boolean(q.data || q.error || noCareer), qs);
  const d = q.data;
  const set = (changes: Record<string, string>) => {
    const next: Record<string, string> = { team: d?.team ?? want.team, tab: d && d.tab !== d.tabs[0] ? d.tab : "", season: want.season, ...changes };
    if ("team" in changes || "tab" in changes) next.season = changes.season ?? "";
    if (nation) next.nation = nation;
    setSaid(null);
    go(`/fixtures?${new URLSearchParams(Object.entries(next).filter(([, v]) => Boolean(v))).toString()}`);
  };
  const act = useMutation({
    mutationFn: (b: Record<string, unknown>) => post<{ message: string } & Record<string, unknown>>("/api/fixtures", { team: d?.team, ...b }),
    onSuccess: (r) => { if (r.message) setSaid({ ok: true, text: r.message }); return qc.invalidateQueries(); },   // the buttons wait for the page as it now stands
    onError: (e) => setSaid({ ok: false, text: e instanceof Error ? e.message : String(e) }),
  });
  const run = (b: Record<string, unknown>) => act.mutateAsync(b).catch(() => undefined);
  const head = <Head title="Fixtures" crumb="Your schedule" />;
  if (noCareer) return <>{head}<div className="grid"><Tile span={12} title="No career yet"><div className="plain">Add a career in Settings first.</div></Tile></div></>;
  if (q.error) return <>{head}<div className="grid"><Tile span={12}><Missing why={String(q.error)} /></Tile></div></>;
  if (!d) return <>{head}<div className="empty">Reading your schedule…</div></>;
  const b = d.body;
  return (
    <>
      {head}
      <div className="grid">
        <Tile span={12} title="Your schedule">
          <div className="plain">Add your schedule once. Every match ticks itself off when the game saves its scorecard, and the series
            chances, WTC race, milestones and goals update with it.</div>
          {d.none ? <div className="plain" style={{ marginTop: 10 }}><Md s={d.none} /> <Link to={`/settings${keep}`}>Settings</Link></div> :
            <div className="drops"><Pick label="Schedule for" value={d.team} options={d.teams} set={(v) => set({ team: v, tab: d.tab === d.tabs[0] ? "" : d.tab })} /></div>}
          {!d.none && <div className="note">Your teams only: every other team's matches come from the scorecards by themselves.</div>}
        </Tile>
        {!d.none && <>
          <div className="itabs">{d.tabs.map((x, i) => (
            <button key={x} className={x === d.tab ? "on" : ""} onClick={() => set({ tab: i === 0 ? "" : x })}>{x}</button>))}</div>
          {said && <Tile span={12}><div className={said.ok ? "saidok" : "saidbad"}>{said.ok ? "✓ " : "⚠️ "}{said.text}</div></Tile>}
          {b?.missing ? <Tile span={12}><Missing why={b.missing} /></Tile> : b && <>
            {d.tab === "Schedule" && <ScheduleTab d={d} b={b} keep={keep} run={run} busy={act.isPending} go={(t) => set({ tab: t })} />}
            {d.tab === "Add matches" && <AddTab d={d} run={run} busy={act.isPending} />}
            {d.tab === "Change or delete" && <ChangeTab d={d} b={b} run={run} busy={act.isPending} />}
            {d.tab === "Series" && <SeriesTab d={d} b={b} keep={keep} run={run} busy={act.isPending} />}
            {d.tab === "Calendar" && <CalTab b={b} keep={keep} set={set} />}
            {d.tab === "WTC race" && <WtcTab b={b} />}
            {d.tab === "Milestones" && <MilesTab b={b} />}
            {d.tab === "Goals" && <GoalsTab d={d} b={b} run={run} busy={act.isPending} />}
          </>}
        </>}
      </div>
    </>
  );
}

type Run = (b: Record<string, unknown>) => Promise<unknown>;

function Kpis({ rows }: { rows: [string, string][] }) {
  return <div className="kpis">{rows.map(([k, v]) => <div key={k}><span>{k}</span><b className="kv">{v}</b></div>)}</div>;
}

function previewUrl(p: PreviewLink, keep: string) {
  const sp = new URLSearchParams({ section: p.section, mine: p.mine, opp: p.opp });
  return `/teams/preview?${sp.toString()}${keep ? "&" + keep.slice(1) : ""}`;
}

function ChanceText({ team, opp, c }: { team: string; opp: string; c: Chance }) {
  return <span>🔮 <b>{team} {c.win}%</b>{c.multi ? ` · draw ${c.draw}%` : ""} · <b>{opp} {c.lose}%</b></span>;
}

function LastLine({ l }: { l: Last }) {
  if (!l) return null;
  return <span className="note" style={{ display: "block", marginTop: 2 }}>Last time: <MatchLink id={l.id}>{l.date}</MatchLink> · <T>{l.text.slice(l.date.length + 2)}</T></span>;
}

function History({ d, run, busy, all }: { d: Page; run: Run; busy: boolean; all?: boolean }) {
  const h = d.history ?? [];
  if (!h.length) return null;
  const rows = all ? h : h.slice(0, 1);
  return (
    <Tile span={12} title={all ? "Recent changes · undo any of them" : "Your last change"} right={all ? `${h.length} kept` : undefined}>
      {rows.map((x) => (
        <div key={x.id} className="hist"><span><T>{x.what}</T>{x.at && <small> · {x.at}</small>}</span>
          <button className="btn quiet sm" disabled={busy} onClick={() => void run({ action: "undo", id: x.id })}>↩️ Undo</button></div>))}
      {all && <div className="note">Undoing one change puts back only what that change did; the changes after it stay.</div>}
    </Tile>
  );
}

// ------------------------------------------------------------------ Schedule
function ScheduleTab({ d, b, keep, run, busy, go }: { d: Page; b: Schedule; keep: string; run: Run; busy: boolean; go: (tab: string) => void }) {
  const team = d.team;
  if (b.empty) return <>
    <Tile span={12}><Missing why={b.empty} /></Tile>
    <PreviewAnyTile p={b.preview_any ?? null} keep={keep} />
    <Tile span={12} title="How to add your schedule"><div className="plain howto"><Md s={d.how_to.replace("**How to add your schedule**\n", "")} /></div>
      <div className="field"><button className="btn" onClick={() => go("Add matches")}>Add matches →</button></div></Tile>
  </>;
  return <>
    {b.info && <Tile span={12}><div className="plain"><Md s={b.info} /></div></Tile>}
    <Tile span={12} title={`${team} · this season's schedule`}>{b.kpis && <Kpis rows={b.kpis} />}</Tile>
    <History d={d} run={run} busy={busy} />
    {b.check && b.check.length > 0 ? <Tile span={12} title={`🔍 Schedule check · ${b.check.length} thing${b.check.length !== 1 ? "s" : ""} to look at`}>
      {b.check.map((x) => <div key={x.series + x.kind} className="hist"><span>⚠️ <T>{x.text}</T></span>
        {x.fix ? <button className="btn sm" disabled={busy} onClick={() => void run({ action: "fix", series: x.series, kind: x.kind })}>
          {x.fix === "delete" ? "🗑️ Delete it" : "✅ Fix it"}</button> : <small>Change it on the <b>Change or delete</b> tab</small>}</div>)}
    </Tile> : b.check_ok ? <Tile span={12}><div className="note" style={{ marginTop: 0 }}>🔍 Schedule check: nothing looks wrong.</div></Tile> : null}
    {b.next && <Tile span={7} title="⏭ Next match" right={b.next.opponent ? <Logo team={b.next.opponent} size={40} /> : undefined}>
      <div className="plain"><b><T>{b.next.title}</T></b>{b.next.venue ? ` · ${b.next.venue}` : ""} · {b.next.when}</div>
      {b.next.chance && <div className="plain"><ChanceText team={team} opp={b.next.opponent} c={b.next.chance} /></div>}
      {(b.next.form?.length || b.next.rivalry) ? <div className="plain">{b.next.form?.length ? <>Their last {b.next.form.length}: <Lamps seq={b.next.form} /></> : null}
        {b.next.rivalry ? <> · <Md s={b.next.rivalry} /></> : null}</div> : null}
      {(b.next.streaks ?? []).map((s) => <div key={s} className="plain"><T>{s}</T></div>)}
      {b.next.battles && b.next.battles.length > 0 && <div className="plain">⚔️ Key battles: <T>{b.next.battles.join("; ") + "."}</T></div>}
      {b.next.last && <div className="plain"><LastLine l={b.next.last} /></div>}
      {b.next.note && <div className="plain">📝 <b>Your note:</b> {b.next.note}</div>}
      {b.next.preview && <div className="field"><Link className="btn" to={previewUrl(b.next.preview, keep)}>Full preview of {b.next.opponent} →</Link></div>}
    </Tile>}
    <PreviewAnyTile p={b.preview_any ?? null} keep={keep} span={b.next ? 5 : 12} />
    {b.missing_warn && <Tile span={12}><div className="saidbad">{b.missing_warn}</div></Tile>}
    {b.rows && <Tile span={12} title="Every fixture" right="✅ played · ⏭ next · ⏳ to come · ⚠️ no scorecard found · 🆕 auto-added">
      <div className="tablewrap"><table className="c fxt"><thead><tr><th /><th>Series</th><th>Match</th><th>Opponent</th><th>When</th>
        <th>Your chance</th><th>Their form</th><th>Result</th></tr></thead>
        <tbody>{b.rows.map((r, i) => (
          <tr key={i} className={r.status === "next" ? "hi" : ""}>
            <td>{r.icon}</td>
            <td>{r.badge && <Logo team={r.badge} size={36} />} <T>{r.series}</T>{r.auto && <span title="auto-added: not in your schedule, so added from the scorecards"> 🆕</span>}
              {r.venue_note && <span title={r.venue_note}> 📍 {r.venue_real}</span>}</td>
            <td>{r.no}</td><td>{r.opponent}</td><td>{r.when}</td>
            <td>{r.chance && <span className={`lv ${r.chance.level}`} title={`win ${r.chance.win}%${r.chance.draw ? `, draw ${r.chance.draw}%` : ""}, lose ${r.chance.lose}%`}>
              {r.chance.icon} {r.chance.win}% · {r.chance.level}</span>}</td>
            <td>{r.form && r.form.length > 0 && <Lamps seq={r.form} />}{r.rivalry && <span title={r.rivalry.tip}> {r.rivalry.icon}</span>}
              {r.last && <LastLine l={r.last} />}</td>
            <td>{r.id ? <MatchLink id={r.id}>{r.result}</MatchLink> : r.result}</td>
          </tr>))}</tbody></table></div>
      {b.caption && <div className="note">{b.caption}</div>}
    </Tile>}
    {b.outlook && <Outlook o={b.outlook} />}
  </>;
}

function PreviewAnyTile({ p, keep, span = 12 }: { p: PreviewAny; keep: string; span?: number }) {
  const [opp, setOpp] = useState("");
  const [fmt, setFmt] = useState("");
  if (!p) return null;
  const o = p.options.includes(opp) ? opp : p.options[0]!;
  const f = p.formats.includes(fmt) && opp === o ? fmt : p.defaults[o]?.format ?? p.formats[0]!;
  const link = p.links[o]?.[f];
  return (
    <Tile span={span} title="🔎 Preview any opponent">
      <div className="plain">Your history against them, their form, key players and a plan.</div>
      <div className="drops">
        <Pick label="Team to preview" value={o} options={p.options.map((t) => ({ v: t, label: t, note: p.scheduled.includes(t) ? "in your schedule" : "" }))}
          set={(v) => { setOpp(v); setFmt(""); }} />
        <Pick label="Format" value={f} options={p.formats} set={(v) => { setOpp(o); setFmt(v); }} />
      </div>
      {link && <div className="field"><Link className="btn" to={previewUrl(link, keep)}>Preview →</Link></div>}
    </Tile>
  );
}

function Outlook({ o }: { o: NonNullable<Schedule["outlook"]> }) {
  const t = useTheme();
  const option = useMemo(() => {
    const L = look(t);
    const col: Record<string, string> = { easy: t.win, even: t.grey, hard: t.loss };
    return {
      grid: { left: 6, right: 60, top: 6, bottom: 24, containLabel: true },
      xAxis: { type: "value", max: 100, name: "Chance of winning (%)", nameLocation: "middle", nameGap: 26,
        nameTextStyle: { color: t.dim, fontSize: ts(15) }, axisLabel: { color: t.dim, fontSize: ts(14) }, splitLine: { lineStyle: { color: t.edge } } },
      yAxis: { type: "category", inverse: true, data: o.bars.map((x) => x.label), axisLabel: { color: t.ink, fontSize: ts(14) }, axisTick: { show: false } },
      tooltip: { ...L.TT, formatter: (p: { dataIndex: number }) => `${o.bars[p.dataIndex]?.label}<br>${o.bars[p.dataIndex]?.tip}` },
      series: [{ type: "bar", barWidth: "60%", data: o.bars.map((x) => ({ value: x.value, itemStyle: { color: col[x.level] } })),
        label: { show: true, position: "right", color: t.soft, fontSize: ts(14), formatter: (p: { value: number }) => `${Math.round(p.value)}%` } }],
    };
  }, [t, o.bars]);
  return (
    <Tile span={12} title={o.title} right={o.left}>
      <Kpis rows={o.kpis} />
      {o.tough && <div className="plain" style={{ marginTop: 10 }}><Md s={o.tough} /></div>}
      <div data-chart><EChart option={option} height={Math.max(220, 30 * o.bars.length + 70)} label={o.title} /></div>
      <Explain {...three(o)} />
      {o.by_format && <Grid t={o.by_format} />}
      <div className="note">{o.caption}</div>
    </Tile>
  );
}

// ------------------------------------------------------------------ Add matches
function SeriesForm({ d, run, busy, start, onDone, change }: { d: Page; run: Run; busy: boolean; start?: Item; onDone?: () => void; change?: string }) {
  const national = Boolean(d.national);
  const comps = d.competitions ?? [];
  const [comp, setComp] = useState(start ? (comps.find((c) => c.format === start.format)?.name ?? comps[0]?.name ?? "") : comps[0]?.name ?? "");
  const compRow = comps.find((c) => c.name === comp);
  const opps = national ? d.opponents ?? [] : compRow?.opponents ?? d.opponents ?? [];
  const [opp, setOpp] = useState(start?.opponent ?? opps[0] ?? "");
  const [fmt, setFmt] = useState(start?.format ?? (national ? "Test" : compRow?.format ?? d.formats?.[0] ?? ""));
  const [n, setN] = useState(String(start?.n ?? 3));
  const [venue, setVenue] = useState(start?.venue || "home");
  const y0 = start?.month ? Number(start.month.slice(0, 4)) : d.year_now ?? 2030;
  const [year, setYear] = useState(String(y0));
  const [month, setMonth] = useState(String(start?.month ? Number(start.month.slice(5, 7)) : d.month_now ?? 1));
  const [know, setKnow] = useState(Boolean(start?.dates?.some(Boolean)));
  const [dates, setDates] = useState<string[]>(start?.dates ?? []);
  const fmtNow = national ? fmt : compRow?.format ?? fmt;
  const oppNow = opps.includes(opp) ? opp : opps[0] ?? "";
  const body = { kind: "series", opponent: oppNow, format: fmtNow, n: Number(n), venue, month: mm(Number(year), Number(month)),
    dates: know ? dates.slice(0, Number(n)) : [], competition: national ? "" : comp };
  const pv = usePreview(d.team, body);
  const years = Array.from(new Set([...(d.years ?? []), y0])).sort();
  return (
    <div>
      <div className="drops">
        {!national && comps.length > 0 && <Pick label="Competition" value={comp} options={comps.map((c) => c.name)} set={(v) => setComp(v)} />}
        <Pick label="Opponent" value={oppNow} options={opps} set={setOpp} />
        {national && <Pick label="Format" value={fmt} options={d.formats ?? []} set={setFmt} />}
        {!national && !comps.length && <Pick label="Format" value={fmt} options={d.formats ?? []} set={setFmt} />}
        <Pick label="How many matches" value={n} options={["1", "2", "3", "4", "5", "6", "7"]} set={setN} />
        <Pick label="Where" value={venue} options={WHERE} set={setVenue} />
        {!(know && dates.some(Boolean)) && <Pick label="Month" value={month} options={MONTHS.map((m, i) => ({ v: String(i + 1), label: m }))} set={setMonth} />}
        {!(know && dates.some(Boolean)) && <Pick label="Year" value={year} options={years.map(String)} set={setYear} />}
      </div>
      <div className="field"><label className={`tick ${know ? "on" : ""}`}><input type="checkbox" checked={know} onChange={(e) => setKnow(e.target.checked)} /> I know the dates</label>
        <span className="note" style={{ marginTop: 0 }}>Type the date of each match from the game's fixture list. Leave any you don't know empty: it's worked out from the match before it.</span></div>
      {know && <div className="dates">{Array.from({ length: Number(n) }, (_, j) => (
        <label key={j}>{ordinal(j + 1)} {fmtNow}<input className="typed" type="date" value={dates[j] ?? ""}
          onChange={(e) => { const next = [...dates]; next[j] = e.target.value; setDates(next); }} /></label>))}</div>}
      {pv?.wrong ? <div className="saidbad">{pv.wrong}</div> : pv?.series && <div className="note">{change ? "Becomes" : "Adds"}: <b>{pv.series}</b>
        {pv.n > 1 ? ` (${pv.n} matches${pv.given ? `, ${pv.given} with a date` : ""})` : ""}.{pv.given && !change ? " The month comes from the first date you gave." : ""}</div>}
      <div className="field">
        <button className="btn" disabled={busy || Boolean(pv?.wrong)} onClick={() => void run(change ? { action: "change", series: change, ...body } : { action: "add_series", ...body }).then(() => onDone?.())}>
          {change ? "Save" : "Add series"}</button>
        {onDone && <button className="btn quiet" onClick={onDone}>Cancel</button>}
      </div>
    </div>
  );
}

function TournamentForm({ d, run, busy, start, onDone, change }: { d: Page; run: Run; busy: boolean; start?: Item; onDone?: () => void; change?: string }) {
  const names = d.tournaments ?? [];
  const startName = start ? start.series.split(" · ")[0]! : "";
  const [pick, setPick] = useState(start ? (names.includes(startName) ? startName : "Other…") : names[0] ?? "Other…");
  const [other, setOther] = useState(start && !names.includes(startName) ? startName : "");
  const name = pick === "Other…" ? other : pick;
  const formats = d.formats ?? [];
  const tfDefault = d.tournament_format?.[pick];
  const [fmt, setFmt] = useState(start?.format ?? (tfDefault && formats.includes(tfDefault) ? tfDefault : formats[0] ?? ""));
  const y0 = start?.month ? Number(start.month.slice(0, 4)) : d.year_now ?? 2030;
  const [year, setYear] = useState(String(y0));
  const [month, setMonth] = useState(String(start?.month ? Number(start.month.slice(5, 7)) : d.month_now ?? 1));
  const [games, setGames] = useState(String(start?.games ?? 0));
  const body = { kind: "tournament", name, format: fmt, month: mm(Number(year), Number(month)), games: Number(games) || 0 };
  const pv = usePreview(d.team, body);
  const years = Array.from(new Set([...(d.years ?? []), y0])).sort();
  return (
    <div>
      <div className="drops">
        <Pick label="Tournament" value={pick} options={[...names, "Other…"]} set={(v) => { setPick(v); const f = d.tournament_format?.[v]; if (f && formats.includes(f)) setFmt(f); }} />
        {pick === "Other…" && <label className="drop"><span className="droplab">Name</span><input className="typed" value={other} placeholder="e.g. Asia Cup" onChange={(e) => setOther(e.target.value)} /></label>}
        <Pick label="Format" value={fmt} options={formats} set={setFmt} />
        <Pick label="Month it starts" value={month} options={MONTHS.map((m, i) => ({ v: String(i + 1), label: m }))} set={setMonth} />
        <Pick label="Year" value={year} options={years.map(String)} set={setYear} />
        <label className="drop"><span className="droplab">Games you'll play (0 = don't know)</span>
          <input className="typed" type="number" min={0} max={15} value={games} onChange={(e) => setGames(e.target.value)} /></label>
      </div>
      {pv?.series && <div className="note">{change ? "Becomes" : "Adds"}: <b>{pv.series}</b></div>}
      <div className="field">
        <button className="btn" disabled={busy || !name} onClick={() => void run(change ? { action: "change", series: change, ...body } : { action: "add_tournament", ...body }).then(() => onDone?.())}>
          {change ? "Save" : "Add tournament"}</button>
        {onDone && <button className="btn quiet" onClick={onDone}>Cancel</button>}
      </div>
      {!change && <div className="note">Every match you play in it is ticked off as its scorecard arrives, whoever you play.</div>}
    </div>
  );
}

function usePreview(team: string, body: Record<string, unknown>) {
  const key = JSON.stringify(body);
  const [pv, setPv] = useState<{ series: string; n: number; given: number; wrong: string } | null>(null);
  useEffect(() => {
    let live = true;
    const t = setTimeout(() => {
      void post<{ series: string; n: number; given: number; wrong: string }>("/api/fixtures", { team, action: "preview", ...body })
        .then((r) => { if (live) setPv(r); }).catch(() => undefined);
    }, 150);
    return () => { live = false; clearTimeout(t); };
  }, [team, key]);   // eslint-disable-line react-hooks/exhaustive-deps
  return pv;
}

function AddTab({ d, run, busy }: { d: Page; run: Run; busy: boolean }) {
  const [kind, setKind] = useState("series");
  const [text, setText] = useState("");
  const [read, setRead] = useState<{ will: string[]; skipped: string[] } | null>(null);
  return <>
    <Tile span={12} title="How to add your schedule"><div className="plain howto"><Md s={d.how_to.replace("**How to add your schedule**\n", "")} /></div></Tile>
    <Tile span={12} title="Add matches">
      <div className="drops one"><Pick label="What are you adding?" value={kind} options={[{ v: "series", label: "Series or match" }, { v: "tournament", label: "Tournament" }]} set={setKind} /></div>
      {kind === "series" ? <SeriesForm key={d.team} d={d} run={run} busy={busy} /> : <TournamentForm key={d.team} d={d} run={run} busy={busy} />}
    </Tile>
    <Tile span={12} title="⌨️ Faster: type your whole year, one series per line">
      <div className="plain">Examples you can copy and change:</div>
      <pre className="ex">{"England 3 Tests away Jan 2027\nAustralia 5 ODIs home Mar 2027\nNZ 3 T20Is away Apr 2027\nT20 World Cup Jun 2027\n12 Feb 2027 ODI v Sri Lanka home"}</pre>
      <div className="plain">Opponent (full name or short like NZ, SA, WI), how many and which format, home / away / neutral, and the month. Dates are optional.</div>
      <textarea className="typed" rows={6} value={text} placeholder="England 3 Tests away Jan 2027" aria-label="Your schedule"
        onChange={(e) => { setText(e.target.value); setRead(null); }} />
      <div className="field"><button className="btn quiet" disabled={busy} onClick={() => void run({ action: "read_lines", text }).then((r) => setRead((r as { will: string[]; skipped: string[] }) ?? null))}>Read these lines</button></div>
      {read && <>
        {read.skipped.map((e) => <div key={e} className="saidbad">Skipped: {e}</div>)}
        {read.will.length > 0 && <><div className="plain"><b>Will add:</b></div><ul className="dots">{read.will.map((x) => <li key={x}>{x}</li>)}</ul>
          <div className="field"><button className="btn" disabled={busy} onClick={() => void run({ action: "add_lines", text }).then(() => { setText(""); setRead(null); })}>Add these {read.will.length}</button></div></>}
      </>}
    </Tile>
  </>;
}

// ------------------------------------------------------------------ Change or delete
function ChangeTab({ d, b, run, busy }: { d: Page; b: Change; run: Run; busy: boolean }) {
  const [editing, setEditing] = useState("");
  const [confirm, setConfirm] = useState("");
  const [sure, setSure] = useState(false);
  return <>
    <History d={d} run={run} busy={busy} all />
    <Tile span={12} title={`What you added for ${d.team}`}>
      {b.none ? <div className="plain"><Md s={b.none} /></div> : <>
        <div className="plain">Press ✏️ to change a series (opponent, format, how many, home or away, month or date) or 🗑️ to delete it.</div>
        <div className="note">Matches already played keep their results: they're matched to their scorecards again after a change. Series marked 🆕 auto-added
          on the Schedule tab come from the scorecards, so they aren't listed here.</div>
        {b.items.map((it) => (
          <div key={it.series} className="fxitem">
            <div className="hist"><span>{it.icon} <b>{it.series}</b><small> · {it.played} of {it.total} played · {it.when}{it.venue_word ? ` · ${it.venue_word}` : ""}</small></span>
              <span><button className="btn quiet sm" onClick={() => { setEditing(editing === it.series ? "" : it.series); setConfirm(""); }}>✏️ Change</button>
                <button className="btn quiet sm" onClick={() => { setConfirm(it.series); setEditing(""); }}>🗑️ Delete</button></span></div>
            {confirm === it.series && <div className="confirm"><span>Delete <b>{it.series}</b> ({it.n} match{it.n !== 1 ? "es" : ""}) from your schedule? Results already played stay in your career.</span>
              <button className="btn sm" disabled={busy} onClick={() => void run({ action: "delete", series: it.series }).then(() => setConfirm(""))}>Yes, delete it</button>
              <button className="btn quiet sm" onClick={() => setConfirm("")}>Cancel</button></div>}
            {editing === it.series && <div className="editbox"><div className="plain"><b>Change {it.series}</b></div>
              {it.kind === "tournament" ? <TournamentForm d={d} run={run} busy={busy} start={it} change={it.series} onDone={() => setEditing("")} />
                : <SeriesForm d={d} run={run} busy={busy} start={it} change={it.series} onDone={() => setEditing("")} />}</div>}
          </div>))}
        <div className="editbox"><div className="plain"><b>Delete {d.team}'s whole schedule</b></div>
          <div className="note">Takes every series and tournament you added for {d.team} out of the schedule (results already played stay in your career). You can put it back straight after with Undo.</div>
          <div className="field"><label className={`tick ${sure ? "on" : ""}`}><input type="checkbox" checked={sure} onChange={(e) => setSure(e.target.checked)} /> Yes, delete all {b.items.length} of them</label>
            <button className="btn sm" disabled={!sure || busy} onClick={() => void run({ action: "delete_all" }).then(() => setSure(false))}>Delete the whole schedule</button></div></div>
      </>}
    </Tile>
    <TableEditor key={d.team + JSON.stringify(b.table)} b={b} run={run} busy={busy} />
  </>;
}

function TableEditor({ b, run, busy }: { b: Change; run: Run; busy: boolean }) {
  const [open, setOpen] = useState(false);
  const [rows, setRows] = useState<TableRow[]>(b.table);
  const [gone, setGone] = useState<Set<number>>(new Set());
  const edit = (i: number, k: keyof TableRow, v: string) => setRows(rows.map((r, j) => (j === i ? { ...r, [k]: k === "no" || k === "games" ? Number(v) || 0 : v } : r)));
  return (
    <Tile span={12} title="Match by match (advanced)" right={<button className="btn quiet sm" onClick={() => setOpen(!open)}>{open ? "Hide" : "Show"}</button>}>
      <div className="note" style={{ marginTop: 0 }}>Change any cell, add or delete rows.</div>
      {open && <>
        <div className="note">{b.table_caption.replace("select rows and press delete (the bin icon)", "press ✕ on a row")}</div>
        <div className="tablewrap"><table className="c fxedit"><thead><tr><th>Series</th><th>Opponent</th><th>Format</th><th>Match</th><th>Home/away</th>
          <th>Month</th><th>Date</th><th>Games (tournament)</th><th /></tr></thead>
          <tbody>{rows.map((r, i) => gone.has(i) ? null : (
            <tr key={i}>
              <td><input className="typed" value={r.series} title="Matches with the same series name are one series" onChange={(e) => edit(i, "series", e.target.value)} /></td>
              <td><select className="typed" value={r.opponent} title="Leave empty for a tournament" onChange={(e) => edit(i, "opponent", e.target.value)}>
                {Array.from(new Set([r.opponent, ...b.table_opponents])).map((o) => <option key={o} value={o}>{o}</option>)}</select></td>
              <td><select className="typed" value={r.format} onChange={(e) => edit(i, "format", e.target.value)}>{b.table_formats.map((o) => <option key={o}>{o}</option>)}</select></td>
              <td><input className="typed num" type="number" min={0} max={20} value={r.no} title="1 for the 1st Test, 2 for the 2nd …" onChange={(e) => edit(i, "no", e.target.value)} /></td>
              <td><select className="typed" value={r.venue} onChange={(e) => edit(i, "venue", e.target.value)}>{["home", "away", "neutral", ""].map((o) => <option key={o} value={o}>{o}</option>)}</select></td>
              <td><input className="typed" value={r.month} placeholder="e.g. Jan 2027" onChange={(e) => edit(i, "month", e.target.value)} /></td>
              <td><input className="typed" type="date" value={r.date} title="Only if you know it" onChange={(e) => edit(i, "date", e.target.value)} /></td>
              <td><input className="typed num" type="number" min={0} max={20} value={r.games} onChange={(e) => edit(i, "games", e.target.value)} /></td>
              <td><button className="btn quiet sm" aria-label="Delete this row" onClick={() => setGone(new Set([...gone, i]))}>✕</button></td>
            </tr>))}</tbody></table></div>
        <div className="field"><button className="btn quiet sm" onClick={() => setRows([...rows, { id: "", series: "", opponent: "", format: b.table_formats[0]!, no: 1, venue: "home", month: "", date: "", games: 0 }])}>+ Add a row</button>
          <button className="btn" disabled={busy} onClick={() => void run({ action: "save_table", rows: rows.filter((_, i) => !gone.has(i)) })}>Save changes</button></div>
      </>}
    </Tile>
  );
}

// ------------------------------------------------------------------ Series
function OddsLine({ team, opp, o, before }: { team: string; opp: string; o: Odds; before?: boolean }) {
  return before
    ? <div className="plain"><b>Before ball one:</b> {team} win the series <b>{o.A}%</b>{o.show_level ? ` · drawn ${o.level}%` : ""} · {opp} win it <b>{o.B}%</b></div>
    : <span>Chances from here: <b>{team} {o.A}%</b>{o.show_level ? ` · level ${o.level}%` : ""} · <b>{opp} {o.B}%</b></span>;
}

function ExtrasBox({ d, s, x, run, busy }: { d: Page; s: { series: string }; x: Extras; run: Run; busy: boolean }) {
  const [note, setNote] = useState(x.note);
  return (
    <div className="extras">
      <div className="two">
        <div>
          <div className="plain"><b><T>{x.past_title}</T></b></div>
          {x.past ? <>{x.past.map((p) => <div key={p} className="plain"><Md s={p} /></div>)}<div className="note">{x.past_line}</div></>
            : <div className="note">{x.past_none}</div>}
          {x.records.length > 0 && <><div className="plain" style={{ marginTop: 10 }}><b>🏆 Records in reach</b></div>{x.records.map((r) => <div key={r} className="plain"><T>{r}</T></div>)}</>}
        </div>
        <div>
          {x.conditions && <><div className="plain"><b>{x.conditions_title}</b></div><Grid t={x.conditions} />{x.toss && <div className="note">{x.toss}</div>}</>}
          {x.conditions_none && <div className="note">{x.conditions_none}</div>}
          {x.travel_title && <><div className="plain" style={{ marginTop: 10 }}><b><T>{x.travel_title}</T></b></div>
            {(x.travel_good ?? []).map((g) => <div key={g.player + g.text} className="plain"><T>{`${g.player} ${g.text}`}</T></div>)}
            {(x.travel_worse ?? []).length > 0 && <div className="plain">Struggle away: <T>{(x.travel_worse ?? []).map((g) => `${g.player} ${g.text}`).join(", ")}</T></div>}
            {x.travel_none && <div className="note">{x.travel_none}</div>}</>}
        </div>
      </div>
      <div className="field"><label>📝 Your note on this series</label>
        <input className="typed wide" maxLength={300} value={note} placeholder="e.g. rest the strike bowler for the 3rd; try the new opener" onChange={(e) => setNote(e.target.value)} />
        <button className="btn sm" disabled={busy || note.trim() === x.note} onClick={() => void run({ action: "note", series: s.series, text: note })}>Save note</button></div>
      {!x.is_goal && <div className="field"><button className="btn quiet sm" disabled={busy}
        onClick={() => void run({ action: "goal_add", goal: { kind: "series", series: s.series } })}>🎯 Make winning this series a goal</button></div>}
      {x.is_goal && <div className="note">🎯 Winning this series is one of your goals (see the Goals tab).</div>}
      <span hidden>{d.team}</span>
    </div>
  );
}

function Open({ title, start = false, children }: { title: ReactNode; start?: boolean; children: ReactNode }) {
  const [open, setOpen] = useState(start);
  return <div className="openbox"><button className="openhead" onClick={() => setOpen(!open)}><span>{title}</span><i>{open ? "▴" : "▾"}</i></button>
    {open && <div className="openbody">{children}</div>}</div>;
}

function SeriesTab({ d, b, keep, run, busy }: { d: Page; b: SeriesBody; keep: string; run: Run; busy: boolean }) {
  const team = d.team;
  return <>
    {b.none && <Tile span={12}><div className="plain">{b.none}</div></Tile>}
    {b.live.map((s) => (
      <Tile key={s.series} span={12} title={`🔴 Under way: ${s.series}`} right={<Logo team={s.opponent} size={40} />}>
        <div className="plain">{s.lead} · {s.left} to play</div>
        <div className="plain"><b>{s.need}.</b> <OddsLine team={team} opp={s.opponent} o={s.odds} /></div>
        <div className="note">Likeliest final scores: {s.scorelines}. Each game is worked out from the Elo ratings, form, head to head and venue (see Opponent preview); every combination of the games left is counted.</div>
        <Open title="More: past series, conditions, who travels well, records in reach, your note"><ExtrasBox d={d} s={s} x={s.extras} run={run} busy={busy} /></Open>
      </Tile>))}
    {b.tournaments.map((tu) => (
      <Tile key={tu.name} span={12} title={`🏆 Under way: ${tu.name}`} right={tu.next || undefined}>
        <div className="plain">{tu.record}</div>
        {tu.path && <>
          <div className="plain" style={{ marginTop: 6 }}><b>The tournament path</b></div>
          {tu.path.lines.map((l) => <div key={l} className="plain"><Md s={l} /></div>)}
          {tu.path.by_wins.length > 1 && <div className="wins">{tu.path.by_wins.map(([w, c]) => (
            <div key={w} className="winb"><span>{w} win{w !== 1 ? "s" : ""}</span><div className="bar"><i style={{ width: `${c}%` }} /></div><b>{c}%</b></div>))}</div>}
          <div className="note">{tu.path.caption}</div></>}
        {tu.over && <div className="note">{tu.over}</div>}
      </Tile>))}
    {b.coming.map((s, i) => (
      <Tile key={s.series} span={12} title={`🔮 Preview: ${s.series}`} right={<Logo team={s.opponent} size={40} />}>
        <Open title="Open the preview" start={i === 0}>
          <OddsLine team={team} opp={s.opponent} o={s.odds} before />
          <div className="note">Likeliest scores: {s.scorelines}</div>
          <div className="plain">Form in {s.format}s · {team} <Lamps seq={s.form[team] ?? []} /> · {s.opponent} <Lamps seq={s.form[s.opponent] ?? []} /> · {s.h2h}</div>
          <div className="two">{s.watch.map((w) => (
            <div key={w.team} className="plain"><b>{w.team} to watch</b> (last {w.matches} {s.format}s): <T>{[...w.bat.map(([p, v]) => `${p} ${v} runs`),
              ...w.bowl.map(([p, v]) => `${p} ${v} wkts`)].join(", ") || "–"}</T></div>))}</div>
          {s.battles.length > 0 && <div className="plain">⚔️ <T>{s.battles.join("; ") + "."}</T></div>}
          {(s.pick.length > 0 || s.think.length > 0) && <div className="plain">{s.pick.length > 0 && <><b>Pick:</b> <T>{s.pick.join(", ") + "."}</T> </>}
            {s.think.length > 0 && <><b>Think again:</b> <T>{s.think.join(", ") + "."}</T></>}</div>}
          {s.nobody && <div className="note">Nobody in your squad stands out against them either way yet.</div>}
          <ExtrasBox d={d} s={s} x={s.extras} run={run} busy={busy} />
          <div className="field"><Link className="btn" to={previewUrl(s.preview, keep)}>Full preview of {s.opponent} →</Link></div>
        </Open>
      </Tile>))}
    {b.done.length > 0 && <Tile span={12} title="Series reports">
      {b.forecasts && <div className="plain"><Md s={b.forecasts} /></div>}
      {b.done.map((s) => (
        <Open key={s.series} title={`📋 ${s.title}`}>
          <div className="plain"><b>{s.result}</b> · {s.span}</div>
          {s.forecast && <div className="plain">{s.forecast}</div>}
          {s.pos && <div className="plain">🏅 <b>Player of the Series: <T>{s.pos.player}</T></b> ({s.pos.team}) · {s.pos.text}</div>}
          <div className="two">
            <div className="plain"><b>Most runs</b>{s.top_bat.map(([p, t, v]) => <div key={p}><T>{`${p} (${t}) ${v}`}</T></div>)}</div>
            <div className="plain"><b>Most wickets</b>{s.top_bowl.map(([p, t, v]) => <div key={p}><T>{`${p} (${t}) ${v}`}</T></div>)}</div>
          </div>
          {s.bits && <div className="plain"><T>{s.bits}</T></div>}
          {s.records.map((r) => <div key={r} className="plain">🏆 <T>{r}</T></div>)}
          {s.milestones.map((r) => <div key={r} className="plain">🎯 <T>{r}</T></div>)}
          <div className="plain">Matches: {s.matches.map((m, i) => <span key={m.id}>{i ? " · " : ""}<MatchLink id={m.id}>{m.date}</MatchLink></span>)}</div>
          {s.review && <div className="review"><div className="plain"><b>🧑‍🏫 Series review: {team}</b></div>
            {s.review.use_more.length > 0 && <div className="plain"><b>📈 Use more:</b> <T>{s.review.use_more.map((r) => `${r.player} (${r.why})`).join("; ")}</T></div>}
            {s.review.drop.length > 0 && <div className="plain"><b>📉 Think about dropping:</b> <T>{s.review.drop.map((r) => `${r.player} (${r.why})`).join("; ")}</T></div>}
            {s.review.keep.length > 0 && <div className="plain"><b>✅ Keep:</b> <T>{s.review.keep.join(", ")}</T></div>}
            {s.review.table && <Grid t={s.review.table} />}
            <div className="note">{s.review.caption}</div></div>}
        </Open>))}
    </Tile>}
    {b.predictions && <Predictions p={b.predictions} />}
  </>;
}

function Predictions({ p }: { p: NonNullable<SeriesBody["predictions"]> }) {
  const t = useTheme();
  const option = useMemo(() => {
    const L = look(t);
    return {
      grid: { left: 6, right: 70, top: 6, bottom: 6, containLabel: true },
      xAxis: { type: "value", max: 100, show: false },
      yAxis: { type: "category", inverse: true, data: p.bars.map((x) => x.label), axisLabel: { color: t.ink, fontFamily: "Bebas Neue", fontSize: ts(22) },
        axisTick: { show: false }, axisLine: { show: false } },
      tooltip: { ...L.TT, formatter: (q: { dataIndex: number }) => `${p.bars[q.dataIndex]?.label}: right ${Math.round(p.bars[q.dataIndex]?.value ?? 0)}% of ${p.bars[q.dataIndex]?.n} games` },
      series: [{ type: "bar", barWidth: "58%", data: p.bars.map((x) => ({ value: x.value, itemStyle: { color: L.MINE } })),
        label: { show: true, position: "right", ...L.VAL(24), formatter: (q: { value: number }) => `${Math.round(q.value)}%` } }],
    };
  }, [t, p.bars]);
  return (
    <Tile span={12} title="How good are the predictions" right="each match's chance as it stood before the match">
      <div className="plain">{p.summary}</div>
      <div data-chart><EChart option={option} height={Math.max(150, 56 * p.bars.length + 20)} label="How good are the predictions" /></div>
      <Explain {...three(p)} />
      <Grid t={p.table} />
    </Tile>
  );
}

// ------------------------------------------------------------------ Calendar, WTC race, Milestones
function CalTab({ b, keep, set }: { b: Cal; keep: string; set: (c: Record<string, string>) => void }) {
  if (b.none) return <Tile span={12}><Missing why={b.none} /></Tile>;
  return (
    <Tile span={12} title="The season">
      <div className="drops one"><Pick label="Season" value={b.season} options={b.seasons.map((s) => ({ v: s.key, label: s.label }))} set={(v) => set({ season: v })} /></div>
      <div className="cms" data-chart>{b.grid.map((mo) => <MonthGrid key={mo.key} mo={mo} keep={keep} today={b.today} />)}</div>
      {b.caption && <div className="note">{b.caption}</div>}
      {b.best && <Explain {...three(b)} />}
    </Tile>
  );
}

function WtcTab({ b }: { b: Wtc }) {
  if (b.none) return <Tile span={12}><Missing why={b.none} /></Tile>;
  return (
    <Tile span={12} title={b.title ?? ""} right={b.left}>
      {b.table && <Grid t={b.table} />}
      {b.line && <div className="plain" style={{ marginTop: 10 }}><Md s={b.line} /></div>}
      {b.caption && <div className="note">{b.caption}</div>}
    </Tile>
  );
}

function MilesTab({ b }: { b: Miles }) {
  if (b.none) return <Tile span={12}><Missing why={b.none} /></Tile>;
  return <Tile span={12} title={b.title ?? ""}>{b.table && <Grid t={b.table} />}{b.caption && <div className="note">{b.caption}</div>}</Tile>;
}

// ------------------------------------------------------------------ Goals
function GoalsTab({ d, b, run, busy }: { d: Page; b: Goals; run: Run; busy: boolean }) {
  return <>
    <Tile span={12} title={`${d.team}'s goals`} right={b.goals.length ? `${b.goals.length}` : undefined}>
      {b.none ? <div className="plain">{b.none}</div> : b.goals.map((g) => (
        <div key={g.id} className="goal">
          <div className="hist"><span>{g.badge} <b><T>{g.label}</T></b></span>
            <button className="btn quiet sm" disabled={busy} onClick={() => void run({ action: "goal_remove", id: g.id })}>Remove</button></div>
          <div className="plain"><T>{g.text}</T></div>
          <div className="bar"><i style={{ width: `${Math.round(g.done * 100)}%` }} /></div>
        </div>))}
    </Tile>
    {b.suggested.length > 0 && <Tile span={12} title="💡 Suggested goals" right="from your schedule and this season, one click to add">
      {b.suggested.map((s) => (
        <div key={s.label} className="hist"><span><T>{s.label}</T></span>
          <button className="btn quiet sm" disabled={busy} onClick={() => void run({ action: "goal_add", goal: s.goal })}>Add</button></div>))}
      {b.suggested.length > 1 && <div className="field"><button className="btn sm" disabled={busy} onClick={() => void run({ action: "goals_add", goals: b.suggested.map((s) => s.goal) })}>
        Add all {b.suggested.length}</button></div>}
    </Tile>}
    <GoalForm key={d.team} d={d} b={b} run={run} busy={busy} />
  </>;
}

function GoalForm({ d, b, run, busy }: { d: Page; b: Goals; run: Run; busy: boolean }) {
  const [kind, setKind] = useState(b.kinds[0]?.v ?? "series");
  const ch = b.choices;
  const [v, setV] = useState<Record<string, string>>({});
  const val = (k: string, dflt: string) => v[k] ?? dflt;
  const put = (k: string) => (x: string) => setV({ ...v, [k]: x });
  const sec = val("section", (kind === "title" || kind === "top" ? ch.leagues : ch.sections)[0] ?? "");
  const seasons = ch.seasons[sec] ?? [];
  const years = ch.years.map((y) => ({ v: y.v, label: y.label }));
  const fmt = val("format", ch.formats[0] ?? d.formats?.[0] ?? "");
  const player = val("player", ch.players[0] ?? "");
  const goal: Goal = { kind };
  let ok = true, why = "";
  const boxes: ReactNode[] = [];
  const pickSec = (list: string[]) => boxes.push(<Pick key="sec" label="Competition" value={sec} options={list} set={(x) => setV({ ...v, section: x, season: "" })} />);
  const pickSeason = () => boxes.push(<Pick key="sea" label="Season" value={val("season", seasons[0] ?? "")} options={seasons} set={put("season")} />);
  const pickYear = () => boxes.push(<Pick key="yr" label="Season" value={val("year", years[0]?.v ?? "")} options={years} set={put("year")} />);
  const pickFmt = () => boxes.push(<Pick key="fmt" label="Format" value={fmt} options={ch.formats.length ? ch.formats : d.formats ?? []} set={put("format")} />);
  const pickPlayer = () => boxes.push(<Pick key="pl" label="Player" value={player} options={ch.players} set={put("player")} />);
  const num = (k: string, label: string, dflt: string, step = "1") => boxes.push(<label key={k} className="drop"><span className="droplab">{label}</span>
    <input className="typed" type="number" min={0} step={step} value={val(k, dflt)} onChange={(e) => put(k)(e.target.value)} /></label>);
  if (kind === "series") {
    if (b.series.length) { boxes.push(<Pick key="s" label="Series" value={val("series", b.series[0]!)} options={b.series} set={put("series")} />); goal.series = val("series", b.series[0]!); }
    else { ok = false; why = "Add a series on the Add matches tab first."; }
  } else if (kind === "wtc") {
    if (!b.wtc) { ok = false; why = `${d.team} aren't a World Test Championship side.`; }
  } else if (kind === "player") {
    pickPlayer(); pickFmt();
    boxes.push(<Pick key="what" label="Of" value={val("what", "runs")} options={["runs", "wickets"]} set={put("what")} />);
    num("target", "Target", "1000");
    boxes.push(<Pick key="cy" label="Counting" value={val("cyear", "")} options={[{ v: "", label: "Their whole career" }, ...b.years.map((y) => ({ v: y, label: y }))]} set={put("cyear")} />);
    Object.assign(goal, { player, format: fmt, what: val("what", "runs"), target: val("target", "1000"), year: val("cyear", "") });
    ok = Boolean(player);
  } else if (kind === "wins") {
    pickFmt(); num("target", "Wins", "10");
    boxes.push(<Pick key="wy" label="In" value={val("wyear", b.years[1] ?? b.years[0] ?? "")} options={b.years} set={put("wyear")} />);
    Object.assign(goal, { format: fmt, target: val("target", "10"), year: val("wyear", b.years[1] ?? b.years[0] ?? "") });
  } else if (kind === "title" || kind === "top") {
    if (!ch.leagues.length) { ok = false; why = `${d.team} haven't played in a league or tournament yet.`; }
    else {
      pickSec(ch.leagues); pickSeason();
      Object.assign(goal, { section: sec, season: val("season", seasons[0] ?? "") });
      if (kind === "top") {
        boxes.push(<Pick key="n" label="Aim" value={val("n", "0")} options={[{ v: "0", label: "Reach the knockouts" }, ...["1", "2", "3", "4", "6", "8"].map((n) => ({ v: n, label: `Finish in the top ${n}` }))]} set={put("n")} />);
        goal.n = val("n", "0");
      }
    }
  } else if (kind === "home" || kind === "away") {
    pickFmt(); pickYear();
    Object.assign(goal, { format: fmt, season: val("year", years[0]?.v ?? "") });
  } else if (kind === "no1") {
    pickSec(ch.sections); goal.section = sec;
  } else if (kind === "rival") {
    boxes.push(<Pick key="o" label="Opponent" value={val("opponent", ch.opponents[0] ?? "")} options={ch.opponents} set={put("opponent")} />);
    pickFmt(); pickYear();
    Object.assign(goal, { opponent: val("opponent", ch.opponents[0] ?? ""), format: fmt, season: val("year", years[0]?.v ?? "") });
  } else if (kind === "streak") {
    pickFmt(); pickYear(); num("target", "In a row", "5");
    Object.assign(goal, { format: fmt, season: val("year", years[0]?.v ?? ""), target: val("target", "5") });
  } else if (kind === "topscorer") {
    pickPlayer(); pickSec(ch.sections); pickSeason();
    boxes.push(<Pick key="what" label="Top" value={val("what", "runs")} options={[{ v: "runs", label: "run-scorer" }, { v: "wickets", label: "wicket-taker" }]} set={put("what")} />);
    Object.assign(goal, { player, section: sec, season: val("season", seasons[0] ?? ""), what: val("what", "runs") });
  } else if (kind === "average") {
    pickPlayer(); pickFmt(); pickYear();
    boxes.push(<Pick key="what" label="Average" value={val("what", "batting")} options={[{ v: "batting", label: "Batting (or more)" }, { v: "bowling", label: "Bowling (or less)" }]} set={put("what")} />);
    num("target", "Target", val("what", "batting") === "batting" ? "40" : "25", "0.5");
    Object.assign(goal, { player, format: fmt, season: val("year", years[0]?.v ?? ""), what: val("what", "batting"), target: val("target", val("what", "batting") === "batting" ? "40" : "25") });
  } else if (kind === "hauls") {
    pickPlayer(); pickFmt(); pickYear();
    boxes.push(<Pick key="what" label="Of" value={val("what", "hundreds")} options={[{ v: "hundreds", label: "Hundreds" }, { v: "fivefors", label: "Five-fors" }]} set={put("what")} />);
    num("target", "How many", "2");
    Object.assign(goal, { player, format: fmt, season: val("year", years[0]?.v ?? ""), what: val("what", "hundreds"), target: val("target", "2") });
  }
  return (
    <Tile span={12} title="Add a goal">
      <div className="drops">
        <Pick label="Goal" value={kind} options={b.kinds.map((k) => ({ v: k.v, label: k.label, note: k.group }))} set={(x) => { setKind(x); setV({}); }} />
        {boxes}
      </div>
      {why && <div className="note">{why}</div>}
      {kind === "average" && <div className="note">A season average counts once the player has 5 innings (batting) or 5 matches bowled in (bowling).</div>}
      {(kind === "home" || kind === "away" || kind === "rival" || kind === "streak" || kind === "average" || kind === "hauls") &&
        <div className="note">The season runs April to March, as on My team.</div>}
      <div className="field"><button className="btn" disabled={!ok || busy} onClick={() => void run({ action: "goal_add", goal })}>Add goal</button></div>
    </Tile>
  );
}

function ordinal(n: number) {
  const s = ["th", "st", "nd", "rd"], v = n % 100;
  return n + (s[(v - 20) % 10] ?? s[v] ?? s[0]!);
}
