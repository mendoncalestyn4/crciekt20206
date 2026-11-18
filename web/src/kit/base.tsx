// The page's building blocks: tiles, the hero panel, numbers and names in their fonts, won / lost lamps, logos.
import { useRef, useState, type CSSProperties, type ReactNode } from "react";
import { Link } from "react-router";
import type { Outcome } from "../api";
import { useShell } from "../shell/Shell";
import { savePicture, slugOf } from "./savepic";
import { useTheme } from "../theme";
import { sc, ts } from "./look";
import { T } from "../shell/names";
import { ab, fmtOf } from "../format";

/** A number in Space Grotesk, gold: px is the mock-up's size (the approved scale is applied). */
export function Num({ v, px, style }: { v: ReactNode; px: number; style?: CSSProperties }) {
  return <span className="nm" style={{ fontSize: sc(px), ...style }}>{v}</span>;
}

/** A player or team name in Bebas Neue. */
export function Name({ p, px, style }: { p: string; px: number; style?: CSSProperties }) {
  return <span className="pn" style={{ fontSize: ts(px), ...style }}>{p}</span>;
}

/** A player's name: tapping it opens the player menu (their page, batting, bowling, story; shell/PlayerMenu.tsx).
 *  `label`: what to show when it isn't just the name ("★ S Gill"). */
export function PName({ p, px, style, label }: { p: string; px: number; style?: CSSProperties; label?: string }) {
  return <span className="pn pmenu" data-player={p} role="button" tabIndex={0} title={`${p}: player page, batting, bowling, story`}
    style={{ fontSize: ts(px), ...style }}>{label ?? p}</span>;
}

/** A won / lost / drawn lamp. */
export function Lamp({ o }: { o: Outcome }) {
  return <span className={`wl ${o}`}>{o}</span>;
}

export function Lamps({ seq }: { seq: Outcome[] }) {
  return <div className="sq">{seq.map((o, i) => <Lamp key={i} o={o} />)}</div>;
}

/** A tile in the 12-column grid: span columns wide, an optional title (and a hint on the right). */
export function Tile({ span, rows, title, right, className, style, children }: {
  span: number; rows?: number; title?: ReactNode; right?: ReactNode; className?: string; style?: CSSProperties; children?: ReactNode;
}) {
  const box = useRef<HTMLDivElement>(null);
  const [saving, setSaving] = useState(false);
  // "save picture": on every tile that holds a chart (the styles show it only there, when you point at the tile)
  const save = () => {
    const el = box.current;
    if (!el || saving) return;
    setSaving(true);
    savePicture(el, slugOf(el.querySelector(".tl")?.textContent ?? "chart")).catch(() => null).finally(() => setSaving(false));
  };
  return (
    <div ref={box} className={`t ${className ?? ""}`} style={{ gridColumn: `span ${span}`, ...(rows ? { gridRow: `span ${rows}` } : {}), ...style }}>
      <button className="savepic" onClick={save} title="Save this tile as a picture" aria-label="Save picture">{saving ? "Saving…" : "⤓ Save picture"}</button>
      {title != null && <div className="tt"><span className="tl">{title}</span>{right != null && <span className="tr">{right}</span>}</div>}
      {children}
    </div>
  );
}

/** Tiles side by side inside the grid (equal columns). */
export function Sub({ cols, children }: { cols: number; children: ReactNode }) {
  return <div className="sub" style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}>{children}</div>;
}

/** The scoreboard panel at the top of a page. */
export function Hero({ logo, px = 180, kicker, title, size, side, sideName, h }: {
  logo?: string; px?: number; kicker: ReactNode; title: ReactNode; size?: number; side?: [ReactNode, ReactNode, ReactNode?];
  sideName?: boolean; h?: number;
}) {
  return (
    <section className="hero" style={h ? { minHeight: h } : undefined}>
      {logo && <Logo team={logo} size={px} />}
      <div className="hero-main" style={{ position: "relative", zIndex: 2 }}>
        <div className="k">{kicker}</div>
        <h2 style={size ? { fontSize: size } : undefined}>{title}</h2>
      </div>
      {side && <div className="side">{side[0]}<b className={sideName ? "isname" : ""}>{side[1]}</b>{side[2]}</div>}
    </section>
  );
}

/** A team's emblem or a competition's logo, from your Cricket Captain files, in the look for this page. Nothing at
 *  all when there's no picture (never another team's). */
export function Logo({ team, comp, size, fallback }: { team?: string; comp?: string; size: number; fallback?: boolean }) {
  const t = useTheme();
  const { logos } = useShell();
  const [gone, setGone] = useState(false);
  const name = team ?? comp ?? "";
  if (!name || gone || !(team ? logos.teams : logos.comps).has(name)) {   // only the ones with a picture
    // where a logo always belongs (a match summary: found by you, 14 November, empty gaps where they go), a team the
    // game has no picture for gets a round badge with its short name instead
    return fallback && team ? <span className="lgx" style={{ width: size, height: size, fontSize: Math.round(size * 0.3) }} title={team}>{ab(team)}</span> : null;
  }
  const src = `/api/logo/${team ? "team" : "comp"}/${encodeURIComponent(name)}.png?size=${size}&page=${t.dark ? "dark" : "light"}`;
  return <img className="lg" src={src} width={size} height={size} alt="" title={name} onError={() => setGone(true)} />;
}

/** A match named anywhere opens its match page when clicked (your request of 14 November: every match clickable),
 *  keeping the look you picked. */
export function MatchLink({ id, className, title, style, children }: { id: string | null | undefined; className?: string; title?: string;
  style?: CSSProperties; children: ReactNode }) {
  const { nation } = useShell();
  if (!id) return <>{children}</>;
  return <Link className={className ?? "mlk"} style={style} title={title ?? "Open the match"} to={`/matches/${encodeURIComponent(id)}${nation ? `?nation=${encodeURIComponent(nation)}` : ""}`}>{children}</Link>;
}

/** What a piece says when the career doesn't have enough for it yet. */
export function Missing({ why }: { why?: string }) {
  return <div className="empty">{why ?? "Not enough matches for this yet."}</div>;
}

/** Under every chart, three short lines (your choice of 14 November), small and dim like notes: What it is (what the
 *  chart draws), Who's best (the leader with their number; on a chart with no player or team at the top, the top
 *  thing, labelled for it: "Best month", "Most often"...) and What it's for. All three are written by the server. */
/** A part's three lines (design/CHART_LINES.md) when the server keeps them beside its other fields: pass to Explain. */
export const three = (x: { is_?: string; best?: string; best_label?: string; shows?: ReactNode; for_?: ReactNode }) =>
  ({ is_: x.is_, best: x.best, best_label: x.best_label, shows: x.shows, for_: x.for_ ?? "" });

export function Explain({ is_, best, best_label, shows, for_ }: { is_?: ReactNode; best?: ReactNode; best_label?: string;
  shows?: ReactNode; for_: ReactNode }) {
  const top = best ?? shows;
  return (
    <div className="explain">
      {is_ ? <div><b>What it is:</b> <T>{is_}</T></div> : null}
      {top ? <div><b>{best_label ?? (best != null ? "Who's best" : "What it shows")}:</b> <T>{top}</T></div> : null}
      <div><b>What it's for:</b> {for_}</div></div>
  );
}

/** Tick boxes for the formats a tile counts (your decision of 14 November: tick any formats; it opens on one, ticking
 *  more counts them together). The player's competitions in the agreed order; one always stays ticked. */
export function FormatTicks({ all, on, set }: { all: string[]; on: string[]; set: (v: string[]) => void }) {
  if (all.length < 2) return null;
  return (
    <div className="ticks" role="group" aria-label="Formats">{all.map((x) => {
      const ticked = on.includes(x);
      return (
        <label key={x} className={`tick ${ticked ? "on" : ""}`} title={ticked && on.length === 1 ? "At least one stays ticked" : undefined}>
          <input type="checkbox" checked={ticked} onChange={() => {
            const next = ticked ? on.filter((y) => y !== x) : [...on, x];
            if (next.length) set(all.filter((y) => next.includes(y)));
          }} />{fmtOf(x)}</label>);
    })}</div>
  );
}
