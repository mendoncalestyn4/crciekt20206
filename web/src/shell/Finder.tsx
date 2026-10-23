// The search box (Ctrl K): players, teams, competitions and matches, the same list as the current site's.
import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router";
import { get, type SearchItem } from "../api";

const KIND = { player: "Player", team: "Team", section: "Competition", match: "Match" };
const PAGE = { player: "/players/", team: "/teams/", section: "/leaders/", match: "/matches/" };

export function Finder({ close, keep }: { close: () => void; keep: string }) {
  const items = useQuery({ queryKey: ["search"], queryFn: () => get<{ items: SearchItem[] }>("/api/search") });
  const [q, setQ] = useState("");
  const [on, setOn] = useState(0);
  const go = useNavigate();
  const box = useRef<HTMLInputElement>(null);
  useEffect(() => box.current?.focus(), []);
  const found = useMemo(() => {
    const words = q.toLowerCase().split(/\s+/).filter(Boolean);
    const all = items.data?.items ?? [];
    return (words.length ? all.filter((i) => words.every((w) => `${i.label} ${i.sub}`.toLowerCase().includes(w))) : all).slice(0, 40);
  }, [q, items.data]);
  const pick = (i: SearchItem | undefined) => {
    if (!i) return;
    close();
    go(`${PAGE[i.kind]}${encodeURIComponent(i.value)}${keep}`);
  };
  return (
    <div className="veil" onMouseDown={(e) => { if (e.target === e.currentTarget) close(); }}>
      <div className="finder" role="dialog" aria-label="Search">
        <input ref={box} value={q} placeholder="Player, team, competition or match" aria-label="Search"
          onChange={(e) => { setQ(e.target.value); setOn(0); }}
          onKeyDown={(e) => {
            if (e.key === "Escape") close();
            else if (e.key === "ArrowDown") { e.preventDefault(); setOn((n) => Math.min(n + 1, found.length - 1)); }
            else if (e.key === "ArrowUp") { e.preventDefault(); setOn((n) => Math.max(n - 1, 0)); }
            else if (e.key === "Enter") pick(found[on]);
          }} />
        {items.isLoading && <div className="none">Loading…</div>}
        {items.error && <div className="none">Search needs a career: open one in Settings.</div>}
        {items.data && !found.length && <div className="none">Nothing matches “{q}”.</div>}
        <ul>{found.map((i, k) => (
          <li key={i.kind + i.value} className={k === on ? "on" : ""} onMouseEnter={() => setOn(k)} onClick={() => pick(i)}>
            <span className="kind">{KIND[i.kind]}</span><span className="what">{i.label}</span>
            <span className="where">{i.kind === "match" ? i.sub : ""}</span></li>))}</ul>
      </div>
    </div>
  );
}
