// Your season, wrapped (stage 2, Season review): one team's season as ten slides, each drawn on a canvas in the team's
// colours, so the slide on screen is exactly the picture you save. One slide at a time, or all of them on one picture.
import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router";
import { get, type Theme, type WrapSlide } from "../api";
import { useShell } from "../shell/Shell";
import { useTheme } from "../theme";

const W = 1600, H = 900;

const FONTS = ["400 120px 'Bebas Neue'", "500 200px 'Space Grotesk'", "600 40px Inter", "400 40px Inter"];

/** Each line cut to the width, at word breaks. */
function wrap(g: CanvasRenderingContext2D, text: string, width: number): string[] {
  const out: string[] = [];
  let line = "";
  for (const word of text.split(" ")) {
    const next = line ? `${line} ${word}` : word;
    if (g.measureText(next).width > width && line) { out.push(line); line = word; } else line = next;
  }
  if (line) out.push(line);
  return out;
}

/** The biggest size (down to `min`) at which `text` fits in `width`. */
function fit(g: CanvasRenderingContext2D, text: string, font: (px: number) => string, start: number, min: number, width: number) {
  let px = start;
  for (; px > min; px -= 4) { g.font = font(px); if (g.measureText(text).width <= width) break; }
  g.font = font(px);
  return px;
}

function draw(g: CanvasRenderingContext2D, s: WrapSlide, t: Theme, logo: HTMLImageElement | null, n: number, of: number, foot: string) {
  g.save();
  const bg = g.createLinearGradient(0, 0, W, H);
  bg.addColorStop(0, t.tile); bg.addColorStop(1, t.page);
  g.fillStyle = bg; g.fillRect(0, 0, W, H);
  g.fillStyle = t.blue; g.fillRect(0, 0, 18, H);
  // the slide's number, large and faint, behind everything
  g.globalAlpha = 0.06; g.fillStyle = t.ink; g.font = "400 560px 'Bebas Neue'"; g.textAlign = "right"; g.textBaseline = "alphabetic";
  g.fillText(String(n), W - 110, H - 120);   // clear of the "n / of" count under it g.globalAlpha = 1; g.textAlign = "left";
  const L = 110, R = W - 110, width = R - L;
  if (logo && logo.complete && logo.naturalWidth) g.drawImage(logo, R - 150, 70, 150, 150);
  g.fillStyle = t.gold; g.font = "600 34px Inter"; g.textBaseline = "top";
  g.fillText(s.kicker.toUpperCase(), L, 92);
  g.fillStyle = t.ink;
  const headW = width - (logo ? 190 : 0);
  const hp = fit(g, s.head, (px) => `400 ${px}px 'Bebas Neue'`, s.big ? 120 : 150, 56, headW);
  g.fillText(s.head, L, 146);
  let y = 146 + hp + 30;
  if (s.big) {
    g.fillStyle = t.blue;
    const bp = fit(g, s.big, (px) => `500 ${px}px 'Space Grotesk'`, 230, 120, width * 0.75);
    g.textBaseline = "alphabetic";
    g.fillText(s.big, L - 6, y + bp * 0.8);
    const bw = g.measureText(s.big).width;
    if (s.unit) { g.fillStyle = t.dim; g.font = "400 46px Inter"; g.fillText(s.unit, L + bw + 26, y + bp * 0.8); }
    g.textBaseline = "top";
    y += bp * 0.8 + 50;
  }
  g.font = `400 ${s.big ? 40 : 48}px Inter`;
  s.lines.forEach((line, i) => {
    g.fillStyle = i === 0 ? t.ink : t.dim;
    for (const part of wrap(g, line, width)) { if (y < H - 130) g.fillText(part, L, y); y += s.big ? 54 : 64; }
  });
  g.fillStyle = t.dim; g.font = "400 26px Inter"; g.textBaseline = "alphabetic";
  g.fillText(foot, L, H - 56);
  g.textAlign = "right"; g.fillText(`${n} / ${of}`, R, H - 56);
  g.restore();
}

function save(canvas: HTMLCanvasElement, name: string) {
  canvas.toBlob((b) => {
    if (!b) return;
    const a = document.createElement("a");
    a.href = URL.createObjectURL(b); a.download = name;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 2000);
  }, "image/png");
}

const slug = (s: string) => s.replace(/[^A-Za-z0-9]+/g, "-").replace(/^-|-$/g, "");

export function Wrapped({ slides, team, section, season, keep }: { slides: WrapSlide[]; team: string; section: string; season: string; keep: string }) {
  const site = useTheme();
  // the team's own colours where it has them (else the page's), in the page's light or dark
  const { logos } = useShell();
  const nations = useQuery({ queryKey: ["nations"], queryFn: () => get<{ nations: string[] }>("/api/nations") });
  const coloured = Boolean(nations.data?.nations.includes(team)), drawn = logos.teams.has(team);
  const tq = useQuery({ queryKey: ["theme", team], retry: false, staleTime: Infinity, enabled: coloured,
    queryFn: () => get<Theme>(`/api/theme?nation=${encodeURIComponent(team)}`) });
  const t = tq.data && tq.data.dark === site.dark ? tq.data : site;
  const [i, setI] = useState(0);
  const [ready, setReady] = useState(false);
  const [logo, setLogo] = useState<HTMLImageElement | null>(null);
  const ref = useRef<HTMLCanvasElement>(null);
  const n = slides.length, k = Math.min(i, n - 1), foot = `Stats Pack · ${team} · ${section} ${season}`;
  useEffect(() => { setI(0); }, [team, section, season]);
  useEffect(() => {
    let live = true;
    Promise.all(FONTS.map((f) => document.fonts.load(f))).catch(() => null).then(() => { if (live) setReady(true); });
    return () => { live = false; };
  }, []);
  useEffect(() => {
    setLogo(null);
    if (!drawn) return;   // only the teams with a picture, as everywhere on the site
    const img = new Image();
    img.onload = () => setLogo(img);
    img.onerror = () => setLogo(null);
    img.src = `/api/logo/team/${encodeURIComponent(team)}.png?size=240&page=${site.dark ? "dark" : "light"}`;
    return () => { img.onload = null; img.onerror = null; };
  }, [team, site.dark, drawn]);
  useEffect(() => {
    const c = ref.current, g = c?.getContext("2d");
    if (!c || !g || !ready || !slides[k]) return;
    draw(g, slides[k]!, t, logo, k + 1, n, foot);
  }, [slides, k, t, logo, ready, n, foot]);
  const all = () => {
    const c = document.createElement("canvas"), cols = 2, rows = Math.ceil(n / cols), sc = 0.5, gap = 24;
    c.width = cols * W * sc + (cols + 1) * gap; c.height = rows * H * sc + (rows + 1) * gap;
    const g = c.getContext("2d")!;
    g.fillStyle = t.page; g.fillRect(0, 0, c.width, c.height);
    slides.forEach((s, j) => {
      g.save(); g.translate(gap + (j % cols) * (W * sc + gap), gap + Math.floor(j / cols) * (H * sc + gap)); g.scale(sc, sc);
      draw(g, s, t, logo, j + 1, n, foot); g.restore();
    });
    save(c, `${slug(team)}-${slug(section)}-${season}-wrapped.png`);
  };
  if (!n) return null;
  const s = slides[k]!;
  return (
    <div className="wrapped">
      <canvas ref={ref} width={W} height={H} role="img" aria-label={`${s.kicker}: ${s.head} ${s.big} ${s.unit}. ${s.lines.join(". ")}`} />
      <div className="wbar">
        <button className="btn quiet sm" disabled={k === 0} onClick={() => setI(k - 1)} aria-label="Previous slide">‹ Back</button>
        <div className="wdots">{slides.map((x, j) => <button key={x.key} className={j === k ? "on" : ""} title={x.kicker} aria-label={x.kicker} onClick={() => setI(j)} />)}</div>
        <button className="btn quiet sm" disabled={k === n - 1} onClick={() => setI(k + 1)} aria-label="Next slide">Next ›</button>
        <span className="wsp" />
        {s.id && <Link className="lk" to={`/matches/${s.id}${keep}`}>Open the match</Link>}
        <button className="btn sm" onClick={() => ref.current && save(ref.current, `${slug(team)}-${slug(section)}-${season}-${k + 1}-${s.key}.png`)}>Save this slide</button>
        <button className="btn sm" onClick={all}>Save all on one picture</button>
      </div>
    </div>
  );
}
