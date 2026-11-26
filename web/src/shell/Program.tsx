// The program's own pieces (stage 5, your answers of 26 November): the update offered with a button when the program
// opens, "What's new" in Settings (a small "Updated" mark in the menu leads to it), and the tour of every section on
// the first start ("Show me around again" in Settings). Running from the code (not as the program) none of this shows.
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useLayoutEffect, useState } from "react";
import { useLocation } from "react-router";
import { get, post } from "../api";
import { Tile } from "../kit/base";

export type ProgramInfo = {
  program: boolean; version?: string; date?: string;
  update?: { version: string; date: string; notes: string[] } | null;
  state?: { busy: boolean; error: string; said: string };
  whats_new?: { version: string; date: string; notes: string[] }[];
  updated?: boolean;
  tour: { key: string; title: string; text: string }[] | null;
};

export function useProgram() {
  return useQuery({ queryKey: ["program"], queryFn: () => get<ProgramInfo>("/api/program"), retry: false, staleTime: 30_000,
    refetchInterval: (q) => (q.state.data?.state?.busy ? 1500 : false) });
}

/** "Update ready" at the top of every page while an update is on offer. */
export function UpdateBar() {
  const p = useProgram().data;
  const loc = useLocation();
  const qc = useQueryClient();
  const [asked, setAsked] = useState(false);
  if (!p?.program || !p.update) return null;
  const st = p.state;
  const go = async () => {
    setAsked(true);
    try { await post("/api/program", { action: "update", page: loc.pathname + loc.search }); } finally { void qc.invalidateQueries({ queryKey: ["program"] }); }
  };
  return (
    <div className={`updatebar${st?.error ? " bad" : ""}`}>
      {st?.error ? <span>{st.error}</span>
        : st?.busy || asked ? <span>{st?.said || "Backing up your careers, then updating… the Stats Pack closes and opens again on this page."}</span>
          : <span><b>Update ready</b> · version {p.update.version}{p.update.date ? ` (${p.update.date})` : ""}: {p.update.notes[0] ?? "improvements and fixes"}
            {p.update.notes.length > 1 ? ` and ${p.update.notes.length - 1} more (Settings → What's new)` : ""}</span>}
      {!st?.busy && !asked && !st?.error && <button className="btn sm" onClick={go}>Update</button>}
    </div>
  );
}

/** Settings → What's new: every version's notes in plain words, the newest first. */
export function WhatsNew({ p }: { p: ProgramInfo }) {
  const qc = useQueryClient();
  useEffect(() => {
    if (p.updated) void post("/api/program", { action: "seen" }).then(() => qc.invalidateQueries({ queryKey: ["program"] }));
  }, [p.updated, qc]);
  const again = async () => { await post("/api/program", { action: "tour_again" }); void qc.invalidateQueries({ queryKey: ["program"] }); };
  return (
    <Tile span={12} title="What's new" right={<span className="tag">You have version {p.version}</span>}>
      {p.update && <div className="saidok">Version {p.update.version} is ready: the Update button is at the top of the page.</div>}
      {(p.whats_new ?? []).length === 0 && <div className="note">Nothing yet: each update's changes will be listed here in plain words.</div>}
      {(p.whats_new ?? []).map((v) => (
        <div key={v.version} className="fxitem"><div className="plain"><b>Version {v.version}</b>{v.date ? ` · ${v.date}` : ""}</div>
          <ul className="notes">{v.notes.map((n, i) => <li key={i}>{n}</li>)}</ul></div>))}
      <div className="field" style={{ marginTop: 12 }}><button className="btn quiet sm" onClick={again}>Show me around again</button></div>
    </Tile>
  );
}

/** The tour of every section on the first start: a tip beside each part of the menu in turn, Next and Skip. */
export function Tour() {
  const p = useProgram().data;
  const qc = useQueryClient();
  const [i, setI] = useState(0);
  const [at, setAt] = useState<{ top: number; left: number; h: number } | null>(null);
  const steps = p?.program ? p.tour : null;
  const step = steps?.[i];
  useLayoutEffect(() => {
    if (!step) return;
    const el = document.querySelector(`[data-tour="${step.key}"]`);
    const r = el?.getBoundingClientRect();
    setAt(r ? { top: r.top, left: r.right + 14, h: r.height } : null);
  }, [step]);
  if (!steps || !step) return null;
  const done = async () => { await post("/api/program", { action: "tour_done" }); void qc.invalidateQueries({ queryKey: ["program"] }); setI(0); };
  const style = at ? { top: Math.max(10, Math.min(at.top + at.h / 2 - 60, innerHeight - 190)), left: Math.min(at.left, innerWidth - 360) }
    : { top: 90, left: Math.max(10, innerWidth / 2 - 170) };
  return (
    <div className="tour" role="dialog" aria-label="A quick tour">
      <div className="tourtip" style={style}>
        <div className="tourstep">{i + 1} of {steps.length}</div>
        <b>{step.title}</b>
        <div>{step.text}</div>
        <div className="field">
          {i + 1 < steps.length ? <button className="btn sm" onClick={() => setI(i + 1)}>Next</button>
            : <button className="btn sm" onClick={done}>Done</button>}
          <button className="btn quiet sm" onClick={done}>Skip the tour</button>
        </div>
      </div>
    </div>
  );
}
