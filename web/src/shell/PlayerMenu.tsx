// The player menu: tap any player's name anywhere on the site (a name drawn with PName, or any element with
// data-player) and a small menu opens beside it: their page, batting, bowling, their story. One menu for the whole
// site, opened from a click anywhere, so every name works the same way. A chart opens it with a "player-menu" event (a
// name drawn in the chart has no element of its own), at the point clicked.
import { useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router";

type Open = { player: string; x: number; y: number };
const WIDTH = 230;

export function PlayerMenu({ keep }: { keep: string }) {
  const [open, setOpen] = useState<Open | null>(null);
  const box = useRef<HTMLDivElement>(null);
  const loc = useLocation();
  useEffect(() => setOpen(null), [loc.pathname, loc.search]);   // a link was followed
  useEffect(() => {
    const at = (el: Element) => {
      const r = el.getBoundingClientRect();
      setOpen({ player: el.getAttribute("data-player") ?? "", x: Math.max(8, Math.min(r.left, innerWidth - WIDTH - 8)),
        y: r.bottom + 6 + 200 > innerHeight ? Math.max(8, r.top - 6 - 200) : r.bottom + 6 });
    };
    const click = (e: MouseEvent) => {
      const t = e.target as Element | null;
      if (box.current && t && box.current.contains(t)) return;      // inside the menu: its links do the work
      const el = t?.closest("[data-player]");
      if (el && el.getAttribute("data-player")) {
        e.preventDefault();
        e.stopPropagation();
        at(el);
      } else setOpen(null);
    };
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(null);
      const el = (e.target as Element | null)?.closest?.("[data-player]");
      if ((e.key === "Enter" || e.key === " ") && el) { e.preventDefault(); at(el); }
    };
    const away = () => setOpen(null);
    const fromChart = (e: Event) => {
      const d = (e as CustomEvent<{ player: string; x: number; y: number }>).detail;
      setOpen({ player: d.player, x: Math.max(8, Math.min(d.x, innerWidth - WIDTH - 8)),
        y: d.y + 14 + 200 > innerHeight ? Math.max(8, d.y - 14 - 200) : d.y + 14 });
    };
    window.addEventListener("player-menu", fromChart);
    document.addEventListener("click", click, true);
    document.addEventListener("keydown", key);
    window.addEventListener("scroll", away, true);
    window.addEventListener("resize", away);
    return () => {
      document.removeEventListener("click", click, true);
      document.removeEventListener("keydown", key);
      window.removeEventListener("scroll", away, true);
      window.removeEventListener("resize", away);
      window.removeEventListener("player-menu", fromChart);
    };
  }, []);
  if (!open) return null;
  const base = `/players/${encodeURIComponent(open.player)}`;
  const view = (v: string) => { const q = new URLSearchParams(keep.slice(1)); q.set("view", v); return `${base}?${q}`; };
  return (
    <div className="pm-pop" ref={box} style={{ left: open.x, top: open.y, width: WIDTH }} role="menu" aria-label={`${open.player}: where to go`}>
      <div className="pm-t">{open.player}</div>
      <Link role="menuitem" to={`${base}${keep}`}>Player page</Link>
      <Link role="menuitem" to={view("batting")}>Batting</Link>
      <Link role="menuitem" to={view("bowling")}>Bowling</Link>
      <Link role="menuitem" to={view("story")}>Their story</Link>
    </div>
  );
}
