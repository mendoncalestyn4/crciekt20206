// Settings (stage 4): the tabs Careers, Your teams, Backups, Logos, Colours and Problems (your answer of 26 November),
// the first start with no careers yet, and the "Which teams do you play as?" question. Every change is made by the
// server in the same files the current site reads (server/settingspage.py).
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import { get, post, type Problem, type ProblemsPage } from "../api";
import { Pick, Tile } from "../kit/base";
import { Md } from "../kit/teams";
import { useReady } from "../ready";
import { Head, useShell } from "../shell/Shell";

type CareerRow = { name: string; folder: string; updated: string; size: string; current: boolean; backups: number; last_backup: string };
export type SettingsPage = { tabs: string[]; first: boolean; current: string; scorecards_help: string; detected: string; browse: boolean;
  careers: CareerRow[]; career?: { name: string; matches: number; span: string; empty: string };
  teams?: { picked: string[]; choices: string[]; asked: boolean; ask: boolean; last: string[] };
  backups?: { items: { file: string; when: string; before_restore: boolean; note: string }[]; kept: number; where: string; total: number;
    room: boolean; free: string; need: string };
  logos: { teams: number; comps: number; where: string; chosen: string } };
type Report = { name?: string; line?: string; failed?: { file: string; reason: string }[]; message?: string };

function useSettings() {
  return useQuery({ queryKey: ["settings"], queryFn: () => get<SettingsPage>("/api/settings"), retry: false });
}

function useAct(onDone?: (r: Report) => void) {
  const qc = useQueryClient();
  const [said, setSaid] = useState<{ ok: boolean; text: string } | null>(null);
  const m = useMutation({
    mutationFn: (b: Record<string, unknown>) => post<Report>("/api/settings", b),
    onSuccess: (r) => { setSaid(r.message ? { ok: true, text: r.message } : null); onDone?.(r); void qc.invalidateQueries(); },
    onError: (e) => setSaid({ ok: false, text: e instanceof Error ? e.message : String(e) }),
  });
  return { run: (b: Record<string, unknown>) => m.mutateAsync(b).catch(() => undefined), busy: m.isPending, said, setSaid };
}

function Said({ s }: { s: { ok: boolean; text: string } | null }) {
  if (!s) return null;
  return <div className={s.ok ? "saidok" : "saidbad"} role="status">{s.ok ? "✓ " : "⚠️ "}<Md s={s.text} /></div>;
}

export function Settings() {
  const go = useNavigate();
  const [params] = useSearchParams();
  const { nation } = useShell();
  const q = useSettings();
  const problems = useQuery({ queryKey: ["problems"], queryFn: () => get<ProblemsPage>("/api/problems"), retry: false });
  const nations = useQuery({ queryKey: ["nations"], queryFn: () => get<{ nations: string[] }>("/api/nations") });
  const tab = params.get("tab") ?? "";
  useReady(Boolean((q.data || q.error) && nations.data && (problems.data || problems.error)), tab);
  const head = <Head title="Settings" crumb="Careers, your teams, backups, logos, colours and problems" />;
  if (q.error) return <>{head}<div className="grid"><Tile span={12}><div className="saidbad">{String(q.error)}</div></Tile></div></>;
  const d = q.data;
  if (!d) return <>{head}<div className="empty">Reading your settings…</div></>;
  if (d.first) return <>{head}<div className="grid"><FirstStart d={d} /></div></>;
  const on = d.tabs.includes(tab) ? tab : (problems.data?.count ?? 0) > 0 && !tab ? "Problems" : d.tabs[0]!;
  const set = (t: string) => go(`/settings?${new URLSearchParams({ ...(t !== d.tabs[0] ? { tab: t } : {}), ...(nation ? { nation } : {}) }).toString()}`);
  return (
    <>
      {head}
      <div className="grid">
        <div className="itabs">{d.tabs.map((x) => (
          <button key={x} className={x === on ? "on" : ""} onClick={() => set(x)}>{x}
            {x === "Problems" && (problems.data?.count ?? 0) > 0 && <b className="cnt">{problems.data!.count}</b>}</button>))}
          <Link className="itablink" to={`/settings/data-check${nation ? `?nation=${encodeURIComponent(nation)}` : ""}`}>Data check →</Link></div>
        {on === "Careers" && <CareersTab d={d} />}
        {on === "Your teams" && <TeamsTab d={d} />}
        {on === "Backups" && <BackupsTab d={d} />}
        {on === "Logos" && <LogosTab d={d} />}
        {on === "Colours" && <Tile span={12} title="Colours">
          <div className="plain">The site wears your first national side's colours (the night look when you play as none). Preview another
            side's colours here: nothing is saved.</div>
          <div className="drops one"><Pick label="Preview" value={nation}
            options={[{ v: "", label: "Your colours" }, { v: "none", label: "No national side (night)" }, ...(nations.data?.nations ?? [])]}
            set={(v) => go(`/settings?tab=Colours${v ? `&nation=${encodeURIComponent(v)}` : ""}`)} /></div>
          <div className="plain" style={{ marginTop: 14 }}><Link to={`/style-guide${nation ? `?nation=${encodeURIComponent(nation)}` : ""}`}>The style guide</Link> shows every piece in these colours.</div>
        </Tile>}
        {on === "Problems" && problems.data && <Problems data={problems.data} />}
      </div>
    </>
  );
}

// ------------------------------------------------------------------ adding a career (the first start and the Careers tab)
function FolderForm({ d, first }: { d: SettingsPage; first: boolean }) {
  const [folder, setFolder] = useState(d.detected);
  const [name, setName] = useState(first ? "My career" : "");
  const [rep, setRep] = useState<Report | null>(null);
  const { run, busy, said, setSaid } = useAct((r) => setRep(r));
  const browse = useAct((r) => { const f = (r as { folder?: string; unavailable?: string }); if (f.folder) setFolder(f.folder); else if (f.unavailable) setSaid({ ok: false, text: f.unavailable }); });
  return (
    <div>
      <div className="plain"><b>1 · Your Scorecards folder</b></div>
      <div className="note" style={{ marginTop: 2 }}><Md s={d.scorecards_help} /></div>
      <div className="field"><input className="typed wide" value={folder} placeholder="Paste the folder path here" aria-label="Folder" onChange={(e) => { setFolder(e.target.value); setSaid(null); }} />
        <button className="btn quiet" disabled={browse.busy} onClick={() => void browse.run({ action: "browse", start: folder })}>Browse…</button></div>
      <div className="plain" style={{ marginTop: 12 }}><b>2 · Name this career</b></div>
      <div className="field"><input className="typed wide" value={name} placeholder="e.g. India save" aria-label="Career name" onChange={(e) => { setName(e.target.value); setSaid(null); }} />
        <button className="btn" disabled={busy || !folder.trim() || !name.trim()} onClick={() => void run({ action: "add_folder", folder, name })}>{busy ? "Reading scorecards…" : "Start watching"}</button></div>
      <Said s={said} /><ReportBox r={rep} />
    </div>
  );
}

function ReportBox({ r }: { r: Report | null }) {
  if (!r?.line) return null;
  return <div className="report"><div className="saidok">{r.line}</div>
    {r.failed && r.failed.length > 0 && <details><summary>{r.failed.length} file(s) could not be read</summary>
      <table className="c"><thead><tr><th>File</th><th>Reason</th></tr></thead><tbody>{r.failed.map((f) => <tr key={f.file}><td>{f.file}</td><td>{f.reason}</td></tr>)}</tbody></table></details>}</div>;
}

function readAll(files: File[]): Promise<{ name: string; data: string }[]> {
  return Promise.all(files.map((f) => new Promise<{ name: string; data: string }>((ok, bad) => {
    const r = new FileReader();
    r.onload = () => ok({ name: f.name, data: String(r.result).split(",", 2)[1] ?? "" });
    r.onerror = () => bad(new Error(`${f.name} couldn't be read`));
    r.readAsDataURL(f);
  })));
}

function UploadForm({ d, first }: { d: SettingsPage; first: boolean }) {
  const qc = useQueryClient();
  const [kind, setKind] = useState("files");
  const [picked, setPicked] = useState<File[]>([]);
  const [name, setName] = useState(first ? "My career" : "");
  const [mode, setMode] = useState(first || !d.current ? "new" : "new");
  const [busy, setBusy] = useState("");
  const [said, setSaid] = useState<{ ok: boolean; text: string } | null>(null);
  const [rep, setRep] = useState<Report | null>(null);
  const send = async () => {
    setSaid(null); setRep(null);
    try {
      let token = "";
      for (let i = 0; i < picked.length; i += 200) {
        setBusy(`Sending ${Math.min(i + 200, picked.length)} of ${picked.length}…`);
        const part = await readAll(picked.slice(i, i + 200));
        const last = i + 200 >= picked.length;
        const r = await post<{ token: string } & Report>("/api/upload", { token, files: part, ...(last ? { finish: kind === "pack" ? "new" : mode, name } : {}) });
        token = r.token ?? token;
        if (last) { setRep(r); setSaid({ ok: true, text: r.message ?? "Loaded" }); }
      }
      void qc.invalidateQueries();
    } catch (e) { setSaid({ ok: false, text: e instanceof Error ? e.message : String(e) }); }
    setBusy("");
  };
  const accept = kind === "pack" ? ".zip" : kind === "folder" ? ".txt" : ".txt,.zip";
  return (
    <div>
      <div className="drops">
        <Pick label="What" value={kind} options={[{ v: "folder", label: "Upload a folder" }, { v: "files", label: "Upload files or a zip" }, { v: "pack", label: "Open a career file" }]}
          set={(v) => { setKind(v); setPicked([]); }} />
        {kind !== "pack" && d.current && !first && <Pick label="Into" value={mode} options={[{ v: "new", label: "A new career" }, { v: "add", label: `Add to ${d.current}` }]} set={setMode} />}
      </div>
      <div className="field">
        <label className="btn quiet filebtn">{kind === "folder" ? "Choose a Scorecards folder" : kind === "pack" ? "Choose a career file (.zip saved from this site)" : "Choose scorecard .txt files or a .zip"}
          <input type="file" hidden multiple={kind !== "pack"} accept={accept}
            {...(kind === "folder" ? { webkitdirectory: "", directory: "" } as Record<string, string> : {})}
            onChange={(e) => setPicked(Array.from(e.target.files ?? []).filter((f) => kind !== "folder" || f.name.toLowerCase().endsWith(".txt")))} /></label>
        {picked.length > 0 && <span className="note" style={{ marginTop: 0 }}>{picked.length} file{picked.length !== 1 ? "s" : ""} picked</span>}
      </div>
      {(mode === "new" || kind === "pack") && <div className="field"><label>Career name</label>
        <input className="typed wide" value={name} placeholder="e.g. India save" onChange={(e) => setName(e.target.value)} /></div>}
      <div className="field"><button className="btn" disabled={Boolean(busy) || !picked.length || ((mode === "new" || kind === "pack") && !name.trim())} onClick={() => void send()}>{busy || "Load"}</button></div>
      <Said s={said} /><ReportBox r={rep} />
    </div>
  );
}

export function FirstStart({ d }: { d: SettingsPage }) {
  const demo = useAct();
  return <>
    <Tile span={12} title="Cricket Captain 2026 · your stats pack">
      <div className="plain">Point the site at your Scorecards folder and every page fills in: leaderboards for every stat, player and team pages,
        team-vs-team comparisons and records. New matches appear by themselves while you play.</div>
    </Tile>
    <Tile span={12} title="Start a career"><FolderForm d={d} first /></Tile>
    <Tile span={12} title="Other ways to load: upload files, open a career file, or try the demo league">
      <UploadForm d={d} first />
      <div className="field"><button className="btn quiet" disabled={demo.busy} onClick={() => void demo.run({ action: "demo" })}>Try the demo league</button></div>
      <Said s={demo.said} />
    </Tile>
  </>;
}

// ------------------------------------------------------------------ the tabs
function CareersTab({ d }: { d: SettingsPage }) {
  const { run, busy, said } = useAct();
  const [renaming, setRenaming] = useState("");
  const [newName, setNewName] = useState("");
  const [removing, setRemoving] = useState("");
  const [sure, setSure] = useState(false);
  const [reset1, setReset1] = useState(false);
  const [typed, setTyped] = useState("");
  const open = useMutation({ mutationFn: (name: string) => post("/api/careers/current", { name }) });
  const qc = useQueryClient();
  return <>
    <Tile span={12} title="Careers on this PC" right={`${d.careers.length}`}>
      <Said s={said} />
      <table className="c"><tbody>{d.careers.map((c) => (
        <tr key={c.name} className={c.current ? "me" : ""}>
          <td><span className="pn" style={{ fontSize: 32 }}>{c.name}</span>
            <div className="note" style={{ marginTop: 2 }}>{c.folder ? `Watching ${c.folder}` : "Not watching a folder (made from uploaded files)"}
              {c.size ? ` · ${c.size}` : ""}{c.last_backup ? ` · last backup ${c.last_backup}` : " · no backup yet"}</div>
            {renaming === c.name && <div className="field"><input className="typed" value={newName} aria-label="New name" onChange={(e) => setNewName(e.target.value)} />
              <button className="btn sm" disabled={busy || !newName.trim()} onClick={() => void run({ action: "rename", name: c.name, new: newName }).then(() => setRenaming(""))}>Save</button>
              <button className="btn quiet sm" onClick={() => setRenaming("")}>Cancel</button></div>}
            {removing === c.name && <div className="confirm"><span>Remove <b>{c.name}</b> from this PC? A backup is made first (kept in the backups folder);
              your game's Scorecards folder isn't touched.</span>
              <label className={`tick ${sure ? "on" : ""}`}><input type="checkbox" checked={sure} onChange={(e) => setSure(e.target.checked)} /> Yes, remove it</label>
              <button className="btn sm" disabled={!sure || busy} onClick={() => void run({ action: "remove", name: c.name, sure: true }).then(() => { setRemoving(""); setSure(false); })}>Remove</button>
              <button className="btn quiet sm" onClick={() => { setRemoving(""); setSure(false); }}>Cancel</button></div>}
          </td>
          <td className="r nowrap">{c.current ? <span className="tag">On screen</span>
            : <button className="btn quiet sm" disabled={open.isPending} onClick={() => open.mutate(c.name, { onSuccess: () => void qc.invalidateQueries() })}>Open</button>}
            <button className="btn quiet sm" onClick={() => { setRenaming(c.name); setNewName(c.name); setRemoving(""); }}>Rename</button>
            <a className="btn quiet sm" href={`/api/careers/${encodeURIComponent(c.name)}/file`} download>Download career file</a>
            <button className="btn quiet sm" onClick={() => { setRemoving(c.name); setRenaming(""); }}>Remove</button></td></tr>))}</tbody></table>
      {d.career && <div className="note">On screen: {d.career.name} · {d.career.matches.toLocaleString("en-GB")} match{d.career.matches !== 1 ? "es" : ""}{d.career.span ? ` · ${d.career.span}` : ""}.
        {d.careers.find((c) => c.current)?.folder ? " New matches from your Scorecards folder are added automatically." : ""}</div>}
      {d.career?.empty && <div className="plain" style={{ marginTop: 8 }}><Md s={d.career.empty} /></div>}
    </Tile>
    <Tile span={12} title="Add another career (a different Scorecards folder)"><FolderForm d={d} first={false} /></Tile>
    <Tile span={12} title="Upload files instead, or open a career file"><UploadForm d={d} first={false} /></Tile>
    <Tile span={12} title="Delete everything">
      <div className="plain">Deletes every career and every backup on this PC, and the answers kept for them. Your game's Scorecards folders
        are never touched, so a career can be made again from them.</div>
      {!reset1 ? <div className="field"><button className="btn quiet" onClick={() => setReset1(true)}>Delete all careers and backups…</button></div> :
        <div className="confirm"><span>Are you sure? This can't be undone. Type <b>DELETE EVERYTHING</b> to confirm.</span>
          <input className="typed" value={typed} aria-label="Type DELETE EVERYTHING" onChange={(e) => setTyped(e.target.value)} />
          <button className="btn sm" disabled={typed !== "DELETE EVERYTHING" || busy} onClick={() => void run({ action: "reset", sure: typed }).then(() => { setReset1(false); setTyped(""); })}>Delete everything</button>
          <button className="btn quiet sm" onClick={() => { setReset1(false); setTyped(""); }}>Cancel</button></div>}
    </Tile>
  </>;
}

function TeamsTab({ d }: { d: SettingsPage }) {
  const t = d.teams;
  if (!t) return <Tile span={12}><div className="plain">Open a career first.</div></Tile>;
  return <Tile span={12} title="Your teams"><TeamPicker t={t} career={d.career?.name ?? ""} /></Tile>;
}

export function TeamPicker({ t, career, onDone, asking }: { t: NonNullable<SettingsPage["teams"]>; career: string; onDone?: () => void; asking?: boolean }) {
  const start = t.picked.length ? t.picked : asking ? t.last : [];
  const [mine, setMine] = useState<string[]>(start);
  const [find, setFind] = useState("");
  const { run, busy, said } = useAct(() => onDone?.());
  const shown = find.trim() ? t.choices.filter((x) => x.toLowerCase().includes(find.trim().toLowerCase())).slice(0, 40) : [];
  return (
    <div>
      <div className="plain">Pick the country, franchise or county you control in <b>{career}</b> (more than one if you manage a franchise and a
        country). Home then opens on your team, and the planner, previews, fixtures and every page start from it.</div>
      <div className="chipsel">{mine.map((x) => <span key={x} className="pickedchip">{x}<button aria-label={`Take off ${x}`} onClick={() => setMine(mine.filter((y) => y !== x))}>✕</button></span>)}
        {!mine.length && <span className="note" style={{ marginTop: 0 }}>No teams picked yet.</span>}</div>
      <div className="field"><input className="typed wide" value={find} placeholder="Type a team's name" aria-label="Your teams" onChange={(e) => setFind(e.target.value)} /></div>
      {shown.length > 0 && <div className="found">{shown.map((x) => <button key={x} className={mine.includes(x) ? "on" : ""}
        onClick={() => { setMine(mine.includes(x) ? mine.filter((y) => y !== x) : [...mine, x]); setFind(""); }}>{x}</button>)}</div>}
      {asking && t.last.length > 0 && !t.picked.length && <div className="note">Ticked: the teams you picked last time.</div>}
      <div className="field"><button className="btn" disabled={busy} onClick={() => void run({ action: "teams", teams: mine })}>Save</button>
        {asking && <><button className="btn quiet" onClick={() => onDone?.()}>Not now</button>
          <button className="btn quiet" title="Don't ask again for this career. You can still pick them in Settings → Your teams." disabled={busy}
            onClick={() => void run({ action: "teams_never" })}>I don't play as one team</button></>}</div>
      <div className="note">Saved with this career on this PC, so you're only asked once. Change it any time in Settings → Your teams.</div>
      <Said s={said} />
    </div>
  );
}

/** "Which teams do you play as?" (the first-start question): asked once per career with no teams picked. */
export function TeamsAsk() {
  const { career } = useShell();
  const [gone, setGone] = useState(() => { try { return sessionStorage.getItem(`teams_not_now::${career?.name}`) === "1"; } catch { return false; } });
  const need = Boolean(career && !career.my_teams_picked.length && career.teams_asked === false && !gone);
  const q = useQuery({ queryKey: ["settings"], queryFn: () => get<SettingsPage>("/api/settings"), enabled: need, retry: false });
  if (!need || !q.data?.teams) return null;
  const close = () => { try { sessionStorage.setItem(`teams_not_now::${career?.name}`, "1"); } catch { /* fine */ } setGone(true); };
  return (
    <div className="modal" role="dialog" aria-label="Which teams do you play as?"><div className="modalbox">
      <div className="tt">Which teams do you play as?</div>
      <TeamPicker t={q.data.teams} career={career?.name ?? ""} onDone={close} asking />
    </div></div>
  );
}

function BackupsTab({ d }: { d: SettingsPage }) {
  const { run, busy, said } = useAct();
  const [confirm, setConfirm] = useState("");
  const b = d.backups;
  if (!b) return <Tile span={12}><div className="plain">Open a career first.</div></Tile>;
  return (
    <Tile span={12} title={`Backups (${b.items.length})`} right={`${b.total} on this PC`}>
      <div className="plain">A copy of every career is saved automatically once a week, and before every Data check change and every update;
        the newest {b.kept} of each are kept, in <code>{b.where}</code>. Each backup is read back to check it. Restoring puts that copy back;
        your current state is backed up first, so you can always undo it.</div>
      {!b.room && <div className="saidbad">Not enough room on the disk for a backup: {b.free} free, {b.need} needed. Free some space and backups carry on.</div>}
      <div className="field"><button className="btn" disabled={busy} onClick={() => void run({ action: "backup_now" })}>Back up now</button></div>
      <Said s={said} />
      {b.items.map((x) => (
        <div key={x.file} className="hist"><span><b>{x.when}</b>{x.note && <small> · {x.note}</small>}</span>
          {confirm === x.file ? <span><button className="btn sm" disabled={busy} onClick={() => void run({ action: "restore", file: x.file }).then(() => setConfirm(""))}>Yes, restore</button>
            <button className="btn quiet sm" onClick={() => setConfirm("")}>Cancel</button></span>
            : <button className="btn quiet sm" onClick={() => setConfirm(x.file)}>Restore</button>}</div>))}
      {!b.items.length && <div className="note">No backups of this career yet: the first is made within a few seconds of the site starting.</div>}
    </Tile>
  );
}

function LogosTab({ d }: { d: SettingsPage }) {
  const l = d.logos;
  const [folder, setFolder] = useState(l.chosen);
  const { run, busy, said } = useAct();
  return (
    <Tile span={12} title="🎨 Logos" right={l.teams ? `${l.teams} teams` : undefined}>
      {l.teams || l.comps ? <div className="plain">{l.teams} team emblems and {l.comps} competition logos, from your Cricket Captain editor files in {l.where}.</div>
        : <div className="plain">No logos found yet. They come from your Cricket Captain editor files: the emblems and complogos folders (with
          editemblems.txt and editcomplogos.txt). Put the folder that has them below.</div>}
      <div className="field"><label>Folder with your editor files</label>
        <input className="typed wide" value={folder} placeholder={"e.g. C:\\...\\Cricket Captain 2026\\editor"} onChange={(e) => setFolder(e.target.value)}
          title="The folder holding 'emblems' and 'complogos' (or the game's folder above it). Leave empty to look next to your Scorecards folder and in the Steam folder." />
        <button className="btn" disabled={busy || folder.trim() === l.chosen} onClick={() => void run({ action: "logos_folder", folder })}>Use this folder</button></div>
      <div className="note">The folder holding 'emblems' and 'complogos' (or the game's folder above it). Leave empty to look next to your Scorecards folder and in the Steam folder.</div>
      <Said s={said} />
    </Tile>
  );
}

/** The daily summary (your pick, 26 November): the first time you open the site each day, what happened since. */
export function Daily() {
  const { career } = useShell();
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["daily", career?.name], enabled: Boolean(career), retry: false, staleTime: Infinity,
    queryFn: () => get<{ show: boolean; since?: string; matches?: number; groups?: { title: string; items: string[]; more: number }[] }>("/api/daily") });
  const seen = useMutation({ mutationFn: () => post("/api/daily", {}), onSuccess: () => qc.setQueryData(["daily", career?.name], { show: false }) });
  const d = q.data;
  if (!d?.show) return null;
  return (
    <div className="modal" role="dialog" aria-label="Since you last looked"><div className="modalbox">
      <div className="tt">Since you last looked</div>
      <div className="plain">Since {d.since}: {d.matches ? <b>{d.matches} new match{d.matches !== 1 ? "es" : ""}</b> : "no new matches"}.</div>
      {(d.groups ?? []).map((g) => <div key={g.title} style={{ marginTop: 10 }}><div className="plain"><b>{g.title}</b></div>
        <ul className="dots">{g.items.map((x, i) => <li key={i}>{x}</li>)}{g.more > 0 && <li>and {g.more} more</li>}</ul></div>)}
      <div className="field"><button className="btn" onClick={() => seen.mutate()}>Got it</button></div>
    </div></div>
  );
}

/** My team with no career yet: the first-start screen. */
export function FirstStartPage() {
  const q = useSettings();
  if (!q.data) return <div className="empty">Getting ready…</div>;
  return <div className="grid">{q.data.first ? <FirstStart d={q.data} /> :
    <Tile span={12} title="No career open"><div className="plain">Open a career in <Link to="/settings">Settings</Link>.</div></Tile>}</div>;
}

const KIND: Record<Problem["kind"], string> = { part: "Part of a page", server: "Server", page: "Page broke", scorecard: "Scorecard" };

// copied the modern way, or the old way where the browser won't allow that
async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.cssText = "position:fixed;top:0;left:0;opacity:0";
    document.body.appendChild(ta);
    ta.select();
    let ok = false;
    try { ok = document.execCommand("copy"); } catch { ok = false; }
    ta.remove();
    return ok;
  }
}

function Problems({ data }: { data: ProblemsPage }) {
  const qc = useQueryClient();
  const [note, setNote] = useState("");
  const [shown, setShown] = useState<Set<string>>(new Set());
  const [report, setReport] = useState(false);
  const clear = useMutation({ mutationFn: (ids: true | string[]) => post<ProblemsPage>("/api/problems", { clear: ids }),
    onSuccess: (d) => qc.setQueryData(["problems"], d) });
  const copy = async () => {
    const ok = await copyText(data.report);
    setNote(ok ? "Copied. Paste it into your chat with Claude to have these fixed." : "This browser wouldn't copy: the report is below to copy by hand.");
    if (!ok) setReport(true);
  };
  const flip = (id: string) => setShown((s) => { const n = new Set(s); if (n.has(id)) n.delete(id); else n.add(id); return n; });
  if (!data.count) return (
    <Tile span={12} title="Problems" right={<span className="tag">None</span>}>
      <div className="plain">Nothing so far. If a part of a page can't be worked out, a page breaks or a scorecard can't be read, it's
        listed here, with a report you can copy and send to Claude to be fixed. A red count on Settings in the menu says when there's one.</div>
    </Tile>
  );
  return (
    <Tile span={12} title="Problems" right={<span className="tag bad">{data.count} noticed</span>}>
      <div className="plain">The site noticed {data.count === 1 ? "this" : "these"} while you used it. Copy the report and paste it to
        Claude to have {data.count === 1 ? "it" : "them"} fixed; clear {data.count === 1 ? "it" : "them"} once fixed.</div>
      <div className="probbar">
        <button className="btn" onClick={() => void copy()}>Copy for Claude</button>
        <button className="btn quiet" onClick={() => setReport((r) => !r)}>{report ? "Hide the report" : "Show the report"}</button>
        <button className="btn quiet" onClick={() => clear.mutate(true)} disabled={clear.isPending}>Clear all</button>
        {note && <span className="note" role="status">{note}</span>}
      </div>
      {report && <pre className="probtext">{data.report}</pre>}
      <table className="probs"><colgroup><col style={{ width: 170 }} /><col /><col style={{ width: 210 }} /><col style={{ width: 150 }} /></colgroup>
        <tbody>{data.problems.map((p) => (
          <tr key={p.id}>
            <td><span className="tag">{KIND[p.kind] ?? p.kind}</span></td>
            <td><div className="what">{p.what}</div>
              <div className="where">{p.kind === "scorecard" ? "File" : "Page"}: {p.where || "–"}{p.career ? ` · ${p.career}` : ""}</div>
              {shown.has(p.id) && p.detail && <pre className="probtext">{p.detail}</pre>}</td>
            <td className="seen">{p.count === 1 ? "Once" : `${p.count} times`}<br />last {p.last}</td>
            <td className="r">{p.detail && <button className="btn quiet sm" onClick={() => flip(p.id)}>{shown.has(p.id) ? "Less" : "Details"}</button>}
              <button className="btn quiet sm" onClick={() => clear.mutate([p.id])} disabled={clear.isPending} aria-label="Clear this one" title="Clear this one">✕</button></td>
          </tr>))}</tbody></table>
    </Tile>
  );
}
