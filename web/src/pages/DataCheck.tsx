// Data check (stage 4): what the scorecards leave unclear, in six tabs (your answer of 26 November): Shared names,
// Player with two names, Games left out, Scorecards, Copies, Your changes. A change shows first what it does to the
// numbers (the fix preview), is made only by your click, with a backup first, and every number is worked out again
// in the background while the site stays usable (server/datacheckpage.py, ccstats/datacheck.py).
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import { get, post } from "../api";
import { Missing, Pick, Tile } from "../kit/base";
import { Md } from "../kit/teams";
import { useReady } from "../ready";
import { Head, useShell } from "../shell/Shell";

type Tot = { name: string; matches: number; runs: number; wickets: number; innings: number };
type Preview = { before: Tot[]; after: Tot[]; together?: boolean };
type Body = { explain?: string; none?: string; players?: string[];
  auto?: { player: string; keep: string; others: { team: string; new_name: string; games: number; where: string }[] }[];
  still?: { player: string; keep: string; separate: string[]; played: string; where: string }[]; kept_together?: string[];
  pairs?: { keep: string; other: string; keep_matches: number; other_matches: number; teams: string; why: string }[];
  joined?: { keep: string; other: string; keep_matches: number; other_matches: number; team: string; why: string }[];
  left?: { match_id: string; text: string; result: string; reason: string }[]; conflicts?: { match_id: string; text: string }[];
  conflict_warn?: string; matches?: { v: string; label: string }[];
  failed?: { file: string; why: string }[]; failed_line?: string; ok?: string; problems?: { file: string; what: string }[];
  problems_line?: string; corrected?: { file: string; what: string }[]; corrected_line?: string;
  copies?: { file: string; same_as: string; match_id: string }[];
  changes?: { kind: string; key: unknown; text: string }[] };
type Page = { tabs: string[]; tab: string; intro: string;
  summary: { todo: string[]; fine: string[]; counts: Record<string, number>; needs_you: number };
  state: { busy: boolean; what: string; done: string; error: string }; body: Body };

export function DataCheck() {
  const { career, noCareer, nation } = useShell();
  const [params] = useSearchParams();
  const go = useNavigate();
  const qc = useQueryClient();
  const keep = nation ? `?nation=${encodeURIComponent(nation)}` : "";
  const tab = params.get("tab") ?? "";
  const q = useQuery({ queryKey: ["datacheck", tab, career?.name], enabled: Boolean(career), retry: false,
    queryFn: () => get<Page>(`/api/datacheck?tab=${encodeURIComponent(tab)}`),
    refetchInterval: (qq) => (qq.state.data?.state.busy ? 1500 : false) });
  const [said, setSaid] = useState<string>("");
  const busy = q.data?.state.busy ?? false;
  // when the change is made, every page's numbers are new: everything is asked again
  const [wasBusy, setWasBusy] = useState(false);
  useEffect(() => { if (wasBusy && !busy) void qc.invalidateQueries(); setWasBusy(busy); }, [busy]);   // eslint-disable-line react-hooks/exhaustive-deps
  const act = useMutation({ mutationFn: (b: Record<string, unknown>) => post<{ message: string }>("/api/datacheck", b),
    onSuccess: (r) => { setSaid(r.message); return qc.invalidateQueries({ queryKey: ["datacheck"] }); },
    onError: (e) => setSaid(`⚠️ ${e instanceof Error ? e.message : String(e)}`) });
  useReady(Boolean(q.data || q.error || noCareer), tab);
  const head = <Head title="Data check" crumb="Check and fix" />;
  if (noCareer) return <>{head}<div className="grid"><Tile span={12} title="No career yet"><div className="plain">Add a career in Settings first.</div></Tile></div></>;
  if (q.error) return <>{head}<div className="grid"><Tile span={12}><Missing why={String(q.error)} /></Tile></div></>;
  const d = q.data;
  if (!d) return <>{head}<div className="empty">Checking the scorecards…</div></>;
  const set = (t: string) => { setSaid(""); go(`/settings/data-check?${new URLSearchParams({ ...(t !== d.tabs[0] ? { tab: t } : {}), ...(nation ? { nation } : {}) }).toString()}`); };
  const run = (b: Record<string, unknown>) => act.mutate(b);
  const b = d.body, sm = d.summary;
  return (
    <>
      {head}
      <div className="grid">
        <Tile span={12} title={sm.todo.length ? "What needs you" : "Nothing needs you 🎉"} right={<Link to={`/settings${keep}`}>← Settings</Link>}>
          <div className="plain">{d.intro}</div>
          {sm.todo.map((t) => <div key={t} className="plain">👉 <Md s={t} /></div>)}
          <div className="note">{sm.fine.join(" · ")}</div>
        </Tile>
        {busy && <Tile span={12}><div className="saidok">⏳ Updating every number with your change… ({d.state.what})</div>
          <div className="note">The site can be used meanwhile; pages show the new numbers once it's done.</div></Tile>}
        {!busy && d.state.done && <Tile span={12}><div className="saidok">✓ {d.state.done} A backup of the career was made first.</div></Tile>}
        {!busy && d.state.error && <Tile span={12}><div className="saidbad">{d.state.error}</div></Tile>}
        {said && !busy && !d.state.done && <Tile span={12}><div className={said.startsWith("⚠️") ? "saidbad" : "saidok"}>{said}</div></Tile>}
        <div className="itabs">{d.tabs.map((x) => (
          <button key={x} className={x === d.tab ? "on" : ""} onClick={() => set(x)}>{x} · {sm.counts[x] ?? 0}</button>))}</div>
        <Tile span={12} title={d.tab}>
          {b.explain && <div className="plain"><Md s={b.explain} /></div>}
          {d.tab === "Shared names" && <Shared b={b} run={run} busy={busy || act.isPending} />}
          {d.tab === "Player with two names" && <Joins b={b} run={run} busy={busy || act.isPending} />}
          {d.tab === "Games left out" && <Left b={b} run={run} busy={busy || act.isPending} />}
          {d.tab === "Scorecards" && <Cards b={b} />}
          {d.tab === "Copies" && <>{b.none ? <div className="saidok">{b.none}</div> :
            <table className="c"><thead><tr><th>File</th><th>The same match as</th></tr></thead>
              <tbody>{(b.copies ?? []).map((c) => <tr key={c.file}><td>{c.file}</td><td>{c.same_as}</td></tr>)}</tbody></table>}</>}
          {d.tab === "Your changes" && <>{b.none ? <div className="note">{b.none}</div> : (b.changes ?? []).map((c, i) => (
            <div key={i} className="hist"><span><Md s={c.text} /></span>
              <button className="btn quiet sm" disabled={busy || act.isPending} onClick={() => run({ action: "undo", kind: c.kind, key: c.key })}>Undo</button></div>))}</>}
        </Tile>
      </div>
    </>
  );
}

type Run = (b: Record<string, unknown>) => void;

/** The fix preview: each player's numbers before and after the change, asked of the server before you click. */
function PreviewBox({ body, label, run, busy, onCancel }: { body: Record<string, unknown>; label: string; run: Run; busy: boolean; onCancel: () => void }) {
  const q = useQuery({ queryKey: ["dc-preview", JSON.stringify(body)], retry: false,
    queryFn: () => post<{ preview: Preview }>("/api/datacheck", { ...body, preview: true }) });
  const pv = q.data?.preview;
  const rows = (xs: Tot[]) => xs.map((x) => <tr key={x.name}><td><b>{x.name}</b></td><td className="r">{x.matches}</td><td className="r">{x.innings}</td>
    <td className="r">{x.runs.toLocaleString("en-GB")}</td><td className="r">{x.wickets}</td></tr>);
  return (
    <div className="editbox">
      <div className="plain"><b>What this does to the numbers</b></div>
      {!pv ? <div className="note">Counting…</div> : <div className="two">
        <div><div className="note" style={{ marginTop: 0 }}>Now</div><table className="c"><thead><tr><th>Player</th><th className="r">Matches</th><th className="r">Innings</th><th className="r">Runs</th><th className="r">Wkts</th></tr></thead><tbody>{rows(pv.before)}</tbody></table></div>
        <div><div className="note" style={{ marginTop: 0 }}>After</div><table className="c"><thead><tr><th>Player</th><th className="r">Matches</th><th className="r">Innings</th><th className="r">Runs</th><th className="r">Wkts</th></tr></thead><tbody>{rows(pv.after)}</tbody></table></div>
      </div>}
      {pv?.together && <div className="saidbad">These two played in the same match, so they can't be one player.</div>}
      <div className="field"><button className="btn sm" disabled={busy || !pv || pv.together} onClick={() => { run(body); onCancel(); }}>{label}</button>
        <button className="btn quiet sm" onClick={onCancel}>Cancel</button></div>
    </div>
  );
}

function Shared({ b, run, busy }: { b: Body; run: Run; busy: boolean }) {
  const [open, setOpen] = useState("");
  const [p, setP] = useState("");
  const [t, setT] = useState("");
  const [name, setName] = useState("");
  const players = b.players ?? [];
  return <>
    {b.none && <div className="saidok">{b.none}</div>}
    {(b.auto ?? []).length > 0 && <>
      <div className="plain" style={{ marginTop: 10 }}><b>Kept apart by themselves ({(b.auto ?? []).length})</b></div>
      <table className="c dct"><thead><tr><th>Name</th><th>Stays with</th><th>Kept apart as</th><th /></tr></thead>
        <tbody>{(b.auto ?? []).map((r) => [
          <tr key={r.player}><td><b>{r.player}</b></td><td>{r.keep}</td>
            <td>{r.others.map((o) => <div key={o.team}>{o.new_name} <small>· {o.games} game{o.games !== 1 ? "s" : ""} · {o.where}</small></div>)}</td>
            <td className="r"><button className="btn quiet sm" disabled={busy} onClick={() => setOpen(open === "u" + r.player ? "" : "u" + r.player)}>Count as one player</button></td></tr>,
          open === "u" + r.player ? <tr key={r.player + "-pv"}><td colSpan={4}><PreviewBox body={{ action: "undo_auto_split", player: r.player }} label="Yes, one player" run={run} busy={busy} onCancel={() => setOpen("")} /></td></tr> : null,
        ])}</tbody></table></>}
    {(b.kept_together ?? []).length > 0 && <div className="note">Kept as one player by your choice: {(b.kept_together ?? []).join(", ")} (undo under Your changes).</div>}
    {(b.still ?? []).length > 0 && <><div className="plain" style={{ marginTop: 12 }}><b>Still shared ({(b.still ?? []).length})</b></div>
      {(b.still ?? []).length > 1 && <div className="field"><button className="btn sm" disabled={busy} onClick={() => run({ action: "split_shared", all: true })}>Keep all {(b.still ?? []).length} apart</button></div>}
      {(b.still ?? []).map((r) => (
        <div key={r.player} className="fxitem">
          <div className="hist"><span><b>{r.player}</b> played for {r.played}, in {r.where}<small> · After: {r.player} at {r.keep}, and {r.separate.map((x) => `${r.player} (${x})`).join(", ")}</small></span>
            <button className="btn quiet sm" disabled={busy} onClick={() => setOpen(open === "s" + r.player ? "" : "s" + r.player)}>Keep apart</button></div>
          {open === "s" + r.player && <PreviewBox body={{ action: "split_shared", player: r.player }} label="Yes, keep them apart" run={run} busy={busy} onCancel={() => setOpen("")} />}
        </div>))}</>}
    <div className="editbox"><div className="plain"><b>Separate any other name yourself</b></div>
      <div className="note" style={{ marginTop: 2 }}>For a name the site didn't spot: pick the player, the team where it's really someone else, and the name to show for them.</div>
      <SplitPicker players={players} p={p} setP={(v) => { setP(v); setT(""); setName(""); }} t={t} setT={(v) => { setT(v); setName(`${p} (${v})`); }} name={name} setName={setName} />
      {p && t && name.trim() && name.trim() !== p && <PreviewBox key={p + t + name} body={{ action: "split", player: p, team: t, new_name: name.trim() }} label="Make them a separate player" run={run} busy={busy} onCancel={() => setP("")} />}
    </div>
  </>;
}

function SplitPicker({ players, p, setP, t, setT, name, setName }: { players: string[]; p: string; setP: (v: string) => void; t: string; setT: (v: string) => void; name: string; setName: (v: string) => void }) {
  const [find, setFind] = useState("");
  const tq = useQuery({ queryKey: ["dc-teams-of", p], enabled: Boolean(p), retry: false,
    queryFn: () => get<{ teams: string[] }>(`/api/datacheck/teams?player=${encodeURIComponent(p)}`) });
  const shown = find.trim() ? players.filter((x) => x.toLowerCase().includes(find.trim().toLowerCase())).slice(0, 30) : [];
  return <>
    <div className="field"><input className="typed wide" value={p || find} placeholder="Type to find a player" aria-label="Player"
      onChange={(e) => { setP(""); setFind(e.target.value); }} /></div>
    {!p && shown.length > 0 && <div className="found">{shown.map((x) => <button key={x} onClick={() => { setP(x); setFind(""); }}>{x}</button>)}</div>}
    {p && <div className="drops">
      <Pick label="The one playing for" value={t} options={tq.data?.teams ?? []} set={setT} />
      <label className="drop"><span className="droplab">Show them as</span><input className="typed" value={name} onChange={(e) => setName(e.target.value)} /></label>
    </div>}
  </>;
}

function Joins({ b, run, busy }: { b: Body; run: Run; busy: boolean }) {
  const [open, setOpen] = useState("");
  const [a, setA] = useState("");
  const [k, setK] = useState("");
  const players = b.players ?? [];
  return <>
    {b.none && <div className="saidok">{b.none}</div>}
    {(b.joined ?? []).length > 0 && <>
      <div className="plain" style={{ marginTop: 10 }}><b>Joined by themselves, sure to be one player ({(b.joined ?? []).length})</b></div>
      {(b.joined ?? []).map((r) => (
        <div key={r.other + r.keep} className="fxitem">
          <div className="hist"><div><div><b>{r.other}</b> ({r.other_matches} games) now counts as <b>{r.keep}</b> ({r.keep_matches} games) · {r.team}</div>
            <div className="note" style={{ marginTop: 2 }}>Why: {r.why}, never in the same match, one name straight after the other</div></div>
            <button className="btn quiet sm" disabled={busy} onClick={() => setOpen(open === "j" + r.other ? "" : "j" + r.other)}>Undo: two players</button></div>
          {open === "j" + r.other && <PreviewBox body={{ action: "keep_apart", other: r.other, keep: r.keep }} label="Yes, keep them apart" run={run} busy={busy} onCancel={() => setOpen("")} />}
        </div>))}
    </>}
    {(b.pairs ?? []).length > 0 && <div className="plain" style={{ marginTop: 10 }}><b>May be one player: your choice ({(b.pairs ?? []).length})</b></div>}
    {(b.pairs ?? []).map((r) => (
      <div key={r.other + r.keep} className="fxitem">
        <div className="hist"><div><div><b>{r.other}</b> ({r.other_matches} games) and <b>{r.keep}</b> ({r.keep_matches} games) · {r.teams}</div>
          <div className="note" style={{ marginTop: 2 }}>Why: {r.why} · After: all {r.other_matches + r.keep_matches} games count for {r.keep}</div></div>
          <button className="btn quiet sm" disabled={busy} onClick={() => setOpen(open === r.other ? "" : r.other)}>Same player</button></div>
        {open === r.other && <PreviewBox body={{ action: "join", name: r.other, keep: r.keep }} label="Yes, the same player" run={run} busy={busy} onCancel={() => setOpen("")} />}
      </div>))}
    <div className="editbox"><div className="plain"><b>Join any two names yourself</b></div>
      <div className="drops">
        <NameFind label="This name…" players={players} value={a} set={setA} />
        <NameFind label="…is the same player as" players={players.filter((x) => x !== a)} value={k} set={setK} />
      </div>
      {a && k && <PreviewBox key={a + k} body={{ action: "join", name: a, keep: k }} label="Count them as one player" run={run} busy={busy} onCancel={() => { setA(""); setK(""); }} />}
    </div>
  </>;
}

function NameFind({ label, players, value, set }: { label: string; players: string[]; value: string; set: (v: string) => void }) {
  const [find, setFind] = useState("");
  const shown = find.trim() ? players.filter((x) => x.toLowerCase().includes(find.trim().toLowerCase())).slice(0, 20) : [];
  return <label className="drop"><span className="droplab">{label}</span>
    <input className="typed" value={value || find} placeholder="Type to find a player" onChange={(e) => { set(""); setFind(e.target.value); }} />
    {!value && shown.length > 0 && <div className="found">{shown.map((x) => <button key={x} type="button" onClick={() => { set(x); setFind(""); }}>{x}</button>)}</div>}
  </label>;
}

function Left({ b, run, busy }: { b: Body; run: Run; busy: boolean }) {
  const [pick, setPick] = useState("");
  const [find, setFind] = useState("");
  const ms = b.matches ?? [];
  const shown = find.trim() ? ms.filter((x) => x.label.toLowerCase().includes(find.trim().toLowerCase())).slice(0, 30) : [];
  return <>
    {b.none && <div className="saidok">{b.none}</div>}
    {(b.left ?? []).map((r) => (
      <div key={r.match_id} className="hist"><span><b>{r.text}</b> · {r.result}<small> · {r.reason}</small></span>
        <button className="btn quiet sm" disabled={busy} onClick={() => run({ action: "count_it", match_id: r.match_id })}>Count it</button></div>))}
    {b.conflict_warn && <div className="saidbad">{b.conflict_warn}</div>}
    {(b.conflicts ?? []).map((r) => (
      <div key={r.match_id} className="hist"><span>{r.text}</span>
        <button className="btn quiet sm" disabled={busy} onClick={() => run({ action: "leave_out", match_id: r.match_id })}>Leave out</button></div>))}
    <div className="editbox"><div className="plain"><b>Leave out any other match</b></div>
      <div className="field"><input className="typed wide" value={pick ? ms.find((x) => x.v === pick)?.label ?? "" : find} placeholder="Type to search"
        onChange={(e) => { setPick(""); setFind(e.target.value); }} />
        <button className="btn sm" disabled={!pick || busy} onClick={() => { run({ action: "leave_out", match_id: pick }); setPick(""); }}>Leave it out</button></div>
      {!pick && shown.length > 0 && <div className="found">{shown.map((x) => <button key={x.v} onClick={() => { setPick(x.v); setFind(""); }}>{x.label}</button>)}</div>}
    </div>
  </>;
}

function Cards({ b }: { b: Body }) {
  return <>
    {b.failed_line && <div className="saidbad">{b.failed_line}</div>}
    {(b.failed ?? []).length > 0 && <table className="c"><thead><tr><th>File</th><th>Why</th></tr></thead><tbody>{(b.failed ?? []).map((f) => <tr key={f.file}><td>{f.file}</td><td>{f.why}</td></tr>)}</tbody></table>}
    {b.ok && <div className="saidok">{b.ok}</div>}
    {b.problems_line && <div className="saidbad">{b.problems_line}</div>}
    {(b.problems ?? []).length > 0 && <table className="c"><thead><tr><th>File</th><th>What doesn't add up</th></tr></thead><tbody>{(b.problems ?? []).map((f, i) => <tr key={i}><td>{f.file}</td><td>{f.what}</td></tr>)}</tbody></table>}
    {b.corrected_line && <div className="plain" style={{ marginTop: 10 }}>{b.corrected_line}</div>}
    {(b.corrected ?? []).length > 0 && <table className="c"><thead><tr><th>File</th><th>Put right</th></tr></thead><tbody>{(b.corrected ?? []).map((f, i) => <tr key={i}><td>{f.file}</td><td>{f.what}</td></tr>)}</tbody></table>}
  </>;
}
