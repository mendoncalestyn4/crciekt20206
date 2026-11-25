// One chart: Apache ECharts drawn as SVG, resized with its tile, with the approved fit rules for the bigger words
// (the mock-up's chart wrapper): axis labels kept inside the chart, room on the right for line-end labels and on top
// for a legend, every label of a short category axis shown, two-line pie labels that don't overlap, and the number
// in a donut's hole shrunk with the hole.
import { BarChart, LineChart, PieChart, ScatterChart } from "echarts/charts";
import { GraphicComponent, GridComponent, LegendComponent, MarkAreaComponent, MarkLineComponent, MarkPointComponent, TitleComponent, TooltipComponent } from "echarts/components";
import * as echarts from "echarts/core";
import { LabelLayout } from "echarts/features";
import { SVGRenderer } from "echarts/renderers";
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router";
import { useNames } from "../shell/names";
import { useShell } from "../shell/Shell";
import { ts } from "./look";

echarts.use([BarChart, LineChart, PieChart, ScatterChart, GridComponent, TooltipComponent, LegendComponent, TitleComponent,
  MarkAreaComponent, MarkLineComponent, MarkPointComponent, GraphicComponent, LabelLayout, SVGRenderer]);

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type Option = Record<string, any>;

// how many charts are still drawing (the browser tests wait for none)
declare global { interface Window { chartsDrawing?: number } }
const drawing = (d: number) => { window.chartsDrawing = Math.max(0, (window.chartsDrawing ?? 0) + d); };

const wide = (v: unknown) => (typeof v === "string" ? v.replace(/ /g, " ") : v);   // a wider gap in a name

/** The approved fit rules for one chart, `width` x `height` pixels (width 0 before it's measured). */
export function adapt(input: Option, width = 0, height = 0): Option {
  const opt: Option = { ...input };
  const series = ([] as Option[]).concat(opt.series ?? []).filter(Boolean);
  const g = opt.grid;
  if (g && !Array.isArray(g) && !g.containLabel)
    opt.grid = { ...g, containLabel: true, right: ts(g.right ?? 10),
      top: opt.legend || series.some((s) => s.endLabel) ? ts(g.top ?? 30) + 8 : g.top };
  let slot = 0;   // the room each category has across a horizontal chart, once its width is known
  for (const key of ["xAxis", "yAxis"]) {
    if (!opt[key]) continue;
    const axes = ([] as Option[]).concat(opt[key]).map((a) => {
      const ax = { ...a };
      if (ax.axisLabel && ax.axisLabel.fontFamily === "Bebas Neue" && !ax.axisLabel.formatter) ax.axisLabel = { ...ax.axisLabel, formatter: wide };
      const n = (ax.data ?? []).length;
      if (key === "xAxis" && ax.type === "category" && ax.show !== false && width && n) slot = (width * 0.86) / n;   // each bar's room
      if (ax.type === "category" && ax.show !== false && n <= 12 && ax.axisLabel) {
        let fs: number = ax.axisLabel.fontSize ?? 12, every = true;
        if (key === "xAxis" && width && n) {   // every label shown, shrunk to fit its slot; if it still can't, ECharts skips some
          const longest = Math.max(...(ax.data as unknown[]).map((d) => Math.max(...String(d).split("\n").map((l) => l.length))), 1);
          if (longest * fs * 0.6 > slot - 4) fs = Math.max(10, Math.floor((slot - 4) / (longest * 0.6)));
          every = longest * fs * 0.6 <= slot - 2;
        }
        ax.axisLabel = { ...ax.axisLabel, fontSize: fs, ...(every ? { interval: 0, hideOverlap: false } : { hideOverlap: true }) };
      }
      if (ax.type === "category") ax.triggerEvent = true;   // a player's name on the axis can be clicked (the player menu)
      return ax;
    });
    opt[key] = Array.isArray(opt[key]) ? axes : axes[0];
  }
  opt.series = series.map((sr) => {
    if (sr.type === "bar" && slot && sr.label?.show && sr.label.position === "top") {   // a number on each bar: no wider than its bar's slot
      const chars = Math.max(...(sr.data ?? []).map((d: unknown) => String((d as Option)?.value ?? d).length), 1) + 1;
      const fs = Math.min(sr.label.fontSize ?? 12, Math.floor((slot - 2) / (chars * 0.62)));
      return { ...sr, label: fs >= 10 ? { ...sr.label, fontSize: fs } : { ...sr.label, show: false } };
    }
    if (sr.type !== "pie" || !sr.label || sr.label.show === false) return sr;
    const fs = Math.round((sr.label.fontSize ?? 13) * 0.9);
    const out: Option = { ...sr, label: { ...sr.label, fontSize: fs, lineHeight: Math.round(fs * 1.25) } };
    if (Array.isArray(sr.radius)) out.radius = sr.radius.map((x: unknown) => (typeof x === "string" && x.endsWith("%") ? `${parseFloat(x) * 0.8}%` : x));
    if (width && height && Array.isArray(out.radius) && out.radius.every((x: unknown) => typeof x === "string")) {
      // the labels sit beside the ring: in a narrow tile the ring gets smaller so they stay inside the chart
      const half = Math.min(width, height) / 2, outer = (parseFloat(String(out.radius[1])) / 100) * half;
      const names = (sr.data ?? []).map((d: Option) => String(d.name ?? "") + " ");
      const need = Math.max(...names.map((n: string) => n.length), 1) * fs * 0.62 + 26;   // the label, its line and a margin
      const room = width / 2 - outer;
      if (need > room) {
        const k = Math.max(0.45, (width / 2 - need) / outer);
        out.radius = out.radius.map((x: string) => `${parseFloat(x) * k}%`);
      }
    }
    if (opt.title && opt.title.textStyle)
      opt.title = { ...opt.title, itemGap: 0, textStyle: { ...opt.title.textStyle, fontSize: Math.round(opt.title.textStyle.fontSize * 0.78) },
        subtextStyle: { ...opt.title.subtextStyle, fontSize: Math.round((opt.title.subtextStyle?.fontSize ?? 14) * 0.8) } };
    return out;
  });
  return { animationDuration: 600, ...opt };
}

export function EChart({ option, height, width, label }: { option: Option; height: number; width?: number; label?: string }) {
  const el = useRef<HTMLDivElement>(null);
  const chart = useRef<echarts.ECharts | null>(null);
  const [w, setW] = useState(0);
  const drawn = useRef(false);   // only the first drawing is animated: a resize redraws at once
  const names = useNames();
  const known = useRef(names.set);
  known.current = names.set;
  const navigate = useNavigate();
  const { nation } = useShell();
  const go = useRef((id: string) => navigate(`/matches/${encodeURIComponent(id)}${nation ? `?nation=${encodeURIComponent(nation)}` : ""}`));
  go.current = (id: string) => navigate(`/matches/${encodeURIComponent(id)}${nation ? `?nation=${encodeURIComponent(nation)}` : ""}`);
  useEffect(() => {
    if (!el.current) return;
    const c = echarts.init(el.current, null, { renderer: "svg" });
    chart.current = c;
    // a click on a player's name (an axis label, or a bar or point named after them) opens the player menu there; a
    // bar or point that is one match (its data item says which: `match`) opens that match (every match clickable)
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    c.on("click", (p: any) => {
      const match = p.data && typeof p.data === "object" ? p.data.match : undefined;
      if (typeof match === "string" && match) { go.current(match); return; }
      const player = [p.value, p.name, p.seriesName].find((v) => typeof v === "string" && known.current.has(v));
      const ev = p.event?.event as MouseEvent | undefined;
      if (player && ev) window.dispatchEvent(new CustomEvent("player-menu", { detail: { player, x: ev.clientX, y: ev.clientY } }));
    });
    const ro = new ResizeObserver(() => {
      c.resize();
      const now = Math.round(el.current?.getBoundingClientRect().width ?? 0);
      setW((was) => (Math.abs(now - was) > 8 ? now : was));   // the labels are fitted again when the width really changes
    });
    ro.observe(el.current);
    return () => { ro.disconnect(); c.dispose(); chart.current = null; };
  }, []);
  useEffect(() => {
    const c = chart.current;
    if (!c || !w) return;
    drawing(+1);
    let done = false;
    const finish = () => { if (!done) { done = true; drawing(-1); } };
    c.on("finished", finish);
    c.setOption({ ...adapt(option, w, height), ...(drawn.current ? { animation: false } : {}) }, true);
    drawn.current = true;
    const t = window.setTimeout(finish, 3000);   // never wait for ever
    return () => { c.off("finished", finish); window.clearTimeout(t); finish(); };
  }, [option, w, height]);
  return <div ref={el} data-chart role="img" aria-label={label} style={{ height, width: width ?? "100%" }} />;
}
