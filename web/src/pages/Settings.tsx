// Settings: the careers on this PC (switch which one is on screen), a preview of every nation's colours, and the
// problems the site noticed while you used it (with a report to copy and send to be fixed). The rest of the settings
// (adding careers, your teams, logos folder, backups, data check) come in stage 4.
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { get, post, type Careers, type Problem, type ProblemsPage } from "../api";
import { Tile } from "../kit/base";
import { useReady } from "../ready";
import { Head, useShell } from "../shell/Shell";

export function Settings() {
  const qc = useQueryClient();
  const go = useNavigate();
  const { nation } = useShell();
  const careers = useQuery({ queryKey: ["careers"], queryFn: () => get<Careers>("/api/careers") });
  const nations = useQuery({ queryKey: ["nations"], queryFn: () => get<{ nations: string[] }>("/api/nations") });
  const open = useMutation({ mutationFn: (name: string) => post("/api/careers/current", { name }), onSuccess: () => qc.invalidateQueries() });
  const problems = useQuery({ queryKey: ["problems"], queryFn: () => get<ProblemsPage>("/api/problems"), retry: false });
  useReady(Boolean(careers.data && nations.data && (problems.data || problems.error)));
  const some = (problems.data?.count ?? 0) > 0;
  const list = problems.data ? <Problems data={problems.data} /> : null;
  return (
    <>
      <Head title="Settings" crumb="Careers, colours and problems" />
      <div className="grid">
        {some && list}
        <Tile span={7} title="Careers on this PC">
          {careers.data && !careers.data.careers.length && <div className="plain">No careers yet. Add one on the current site for now.</div>}
          <table className="c"><tbody>{careers.data?.careers.map((c) => (
            <tr key={c} className={c === careers.data?.current ? "me" : ""}><td><span className="pn" style={{ fontSize: 32 }}>{c}</span></td>
              <td className="r">{c === careers.data?.current ? <span className="tag">On screen</span>
                : <button className="btn quiet" onClick={() => open.mutate(c)} disabled={open.isPending}>Open</button>}</td></tr>))}</tbody></table>
          {careers.data?.folders.length ? <div className="note">Watching: {careers.data.folders.join(" · ")}</div> : null}
        </Tile>
        <Tile span={5} title="Colours">
          <div className="plain">The site wears your first national side's colours (the night look when you play as none). Preview another
            side's colours here: nothing is saved.</div>
          <div className="field"><label htmlFor="nation">Preview</label>
            <select id="nation" className="pick" value={nation} onChange={(e) => go(`/settings${e.target.value ? `?nation=${encodeURIComponent(e.target.value)}` : ""}`)}>
              <option value="">Your colours</option><option value="none">No national side (night)</option>
              {nations.data?.nations.map((n) => <option key={n} value={n}>{n}</option>)}</select></div>
          <div className="plain" style={{ marginTop: 14 }}><Link to={`/style-guide${nation ? `?nation=${encodeURIComponent(nation)}` : ""}`}>The style guide</Link> shows every piece in these colours.</div>
        </Tile>
        {!some && list}
        <Tile span={12} title="Coming in stage 4">
          <ul className="dots"><li>Add a career from a Scorecards folder, from .txt files or a .zip, or from a career file; download a career file</li>
            <li>Your teams (and the first-start question), the logos folder, weekly backups with restore, data check (merge, split, credit a catch)</li></ul>
        </Tile>
      </div>
    </>
  );
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
