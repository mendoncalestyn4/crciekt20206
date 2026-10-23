// The page's building blocks: tiles, the hero panel, numbers and names in their fonts, won / lost lamps, logos.
import { useState, type CSSProperties, type ReactNode } from "react";
import type { Outcome } from "../api";
import { useShell } from "../shell/Shell";
import { useTheme } from "../theme";
import { sc, ts } from "./look";

/** A number in Space Grotesk, gold: px is the mock-up's size (the approved scale is applied). */
export function Num({ v, px, style }: { v: ReactNode; px: number; style?: CSSProperties }) {
  return <span className="nm" style={{ fontSize: sc(px), ...style }}>{v}</span>;
}

/** A player or team name in Bebas Neue. */
export function Name({ p, px, style }: { p: string; px: number; style?: CSSProperties }) {
  return <span className="pn" style={{ fontSize: ts(px), ...style }}>{p}</span>;
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
  return (
    <div className={`t ${className ?? ""}`} style={{ gridColumn: `span ${span}`, ...(rows ? { gridRow: `span ${rows}` } : {}), ...style }}>
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
      <div style={{ position: "relative", zIndex: 2 }}>
        <div className="k">{kicker}</div>
        <h2 style={size ? { fontSize: size } : undefined}>{title}</h2>
      </div>
      {side && <div className="side">{side[0]}<b className={sideName ? "isname" : ""}>{side[1]}</b>{side[2]}</div>}
    </section>
  );
}

/** A team's emblem or a competition's logo, from your Cricket Captain files, in the look for this page. Nothing at
 *  all when there's no picture (never another team's). */
export function Logo({ team, comp, size }: { team?: string; comp?: string; size: number }) {
  const t = useTheme();
  const { logos } = useShell();
  const [gone, setGone] = useState(false);
  const name = team ?? comp ?? "";
  if (!name || gone || !(team ? logos.teams : logos.comps).has(name)) return null;   // only the ones with a picture
  const src = `/api/logo/${team ? "team" : "comp"}/${encodeURIComponent(name)}.png?size=${size}&page=${t.dark ? "dark" : "light"}`;
  return <img className="lg" src={src} width={size} height={size} alt="" title={name} onError={() => setGone(true)} />;
}

/** What a piece says when the career doesn't have enough for it yet. */
export function Missing({ why }: { why?: string }) {
  return <div className="empty">{why ?? "Not enough matches for this yet."}</div>;
}
