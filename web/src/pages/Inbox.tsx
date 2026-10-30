// The Inbox: what happened lately for your teams, newest first, one message each (series results and the best by
// marks, who is struggling and who could replace them, who is knocking on the door from domestic cricket,
// milestones in sight). Unread ones are lit; tap one to mark it read; ✕ removes it. Saved with your career.
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { get, post, type InboxPage } from "../api";
import { Missing, Tile } from "../kit/base";
import { Msg } from "../kit/fm";
import { useReady } from "../ready";
import { Head, useShell } from "../shell/Shell";

const KINDS = [["all", "Everything"], ["result", "Results"], ["struggling", "Who to replace"], ["knocking", "Knocking on the door"],
  ["milestone", "Milestones"]] as const;

export function useInbox() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["inbox"], queryFn: () => get<InboxPage>("/api/inbox"), retry: false });
  const change = useMutation({
    mutationFn: (b: { read?: string[]; remove?: string[] }) => post<InboxPage>("/api/inbox", { read: b.read ?? [], remove: b.remove ?? [] }),
    onSuccess: (d) => qc.setQueryData(["inbox"], d),
  });
  return { q, read: (ids: string[]) => ids.length && change.mutate({ read: ids }), remove: (ids: string[]) => change.mutate({ remove: ids }) };
}

export function Inbox() {
  const { nation } = useShell();
  const keep = nation ? `?nation=${encodeURIComponent(nation)}` : "";
  const { q, read, remove } = useInbox();
  const [kind, setKind] = useState<string>("all");
  const [team, setTeam] = useState<string>("");
  useReady(Boolean(q.data || q.error), `${kind}|${team}`);
  if (q.error) return <><Head title="Inbox" crumb="Your news" /><div className="grid"><Tile span={12}><Missing why={String(q.error)} /></Tile></div></>;
  if (!q.data) return <><Head title="Inbox" crumb="Your news" /><div className="empty">Reading your news…</div></>;
  const d = q.data;
  const shown = d.messages.filter((m) => (kind === "all" || m.kind === kind) && (!team || m.team === team));
  const unread = shown.filter((m) => !m.read);
  return (
    <>
      <Head title="Inbox" crumb={`${d.unread} new · your teams' latest news`} />
      <div className="grid">
        <Tile span={12} title={`${shown.length} message${shown.length === 1 ? "" : "s"}`} right={d.teams.length > 1 ? undefined : d.teams[0]}>
          <div className="itabs" style={{ margin: "0 0 12px" }}>{KINDS.map(([k, l]) => (
            <button key={k} className={k === kind ? "on" : ""} onClick={() => setKind(k)}>{l}</button>))}</div>
          <div className="field" style={{ marginTop: 0 }}>
            {d.teams.length > 1 && <select className="pick" value={team} onChange={(e) => setTeam(e.target.value)} aria-label="Team">
              <option value="">All your teams</option>{d.teams.map((t) => <option key={t}>{t}</option>)}</select>}
            <button className="btn quiet" disabled={!unread.length} onClick={() => read(unread.map((m) => m.id))}>Mark all read</button>
            <span className="note" style={{ margin: 0 }}>Tap a message to mark it read; ✕ removes it. New ones have a gold dot; read ones are shaded.</span></div>
          {shown.length ? <div className="inbox" style={{ marginTop: 10 }}>{shown.map((m) => (
            <Msg key={m.id} m={m} keep={keep} read={m.read} onOpen={() => !m.read && read([m.id])} onRemove={() => remove([m.id])} />))}</div>
            : <div className="note">Nothing here{kind !== "all" ? " of this kind" : ""}. News arrives after every series.</div>}
        </Tile>
      </div>
    </>
  );
}
