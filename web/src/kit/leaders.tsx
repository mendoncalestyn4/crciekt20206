// Leaders and records (stage 3): the ranking bars (every qualifying player on one stat, the average marked) and
// "where everyone sits" (every qualifying player against the average player's line, the better side shaded).
import { useMemo } from "react";
import type { SbsBar, SbsDot } from "../api";
import { ab, fx } from "../format";
import { useTheme } from "../theme";
import { alpha } from "./charts";
import { EChart, type Option } from "./EChart";
import { look, ts } from "./look";

const show = (v: number, d: number) => (d ? fx(v, d) : Math.round(v).toLocaleString("en-GB"));

/** One bar per player, best (or worst) first; the player you looked for lit in gold; the average as a dashed line. */
export function RankBars({ rows, reference, decimals, best }: { rows: SbsBar[]; reference: number | null; decimals: number; best: boolean }) {
  const t = useTheme();
  const option = useMemo<Option>(() => {
    const L = look(t), col = best ? t.blue : t.loss;
    // room on the right for the longest figure and what follows it, so nothing is cut off
    const room = Math.max(...rows.map((r) => r.text.length * 11 + (r.sub ?? ab(r.team)).length * 9), 40) + 24;
    return {
      grid: { left: 6, right: room, top: 6, bottom: 6, containLabel: true },
      xAxis: { type: "value", show: false, scale: false },
      yAxis: { type: "category", inverse: true, data: rows.map((r) => r.player), triggerEvent: true, axisLine: { show: false }, axisTick: { show: false },
        axisLabel: { color: t.ink, fontFamily: "Bebas Neue", fontSize: ts(17), margin: 10 } },
      tooltip: { ...L.TT, formatter: (p: { dataIndex: number }) => { const r = rows[p.dataIndex]; return r ? `${r.player} (${r.team}): ${r.text}` : ""; } },
      series: [{ type: "bar", barWidth: "60%",
        data: rows.map((r) => ({ value: r.value, name: r.player, itemStyle: { color: r.hi ? t.led : col, borderRadius: 0, ...(r.hi ? L.glow(alpha(t.led, 0.5)) : {}) } })),
        label: { show: true, position: "right", formatter: (p: { dataIndex: number }) => { const r = rows[p.dataIndex]; return r ? `{v|${r.text}}{t|${r.sub ?? ab(r.team)}}` : ""; },
          rich: { v: { ...L.VAL(17) }, t: { fontFamily: "Bebas Neue", fontSize: ts(14), color: t.dim, padding: [0, 0, 0, 8] } } },
        ...(reference != null ? { markLine: { silent: true, symbol: "none", lineStyle: { color: t.dim, type: "dashed", width: 1.5 },
          label: { formatter: `average ${show(reference, Math.max(decimals, 1))}`, color: t.dim, fontFamily: "Inter", fontSize: ts(10), position: "end" },
          data: [{ xAxis: reference }] } } : {}) }],
    };
  }, [t, rows, reference, decimals, best]);
  return <EChart option={option} height={Math.max(160, rows.length * 34 + 30)} label="Each player's figure, ranked" />;
}

/** Every qualifying player as a dot: the average player's line (through nought, or flat), the better side shaded,
 *  the ranked players coloured (the top four named), everyone else grey, the player you looked for in gold. */
export function DotSpread({ d, best }: { d: SbsDot; best: boolean }) {
  const t = useTheme();
  const option = useMemo<Option>(() => {
    const L = look(t), col = best ? t.blue : t.loss;
    const xs = d.points.map((p) => p.x), ys = d.points.map((p) => p.y);
    const xmax = Math.max(1, ...xs) * 1.05, ymin = Math.min(0, ...ys), ymax = Math.max(1, ...ys) * 1.08;
    const at = (x: number) => (d.line === "slope" ? (d.value ?? 0) * x : (d.value ?? 0));
    const line = d.value == null ? [] : [[0, at(0)], [xmax, at(xmax)]];
    // the better side: above the line (or below it, where lower is better), shaded
    const shade = d.value == null ? [] : [{ type: "line", silent: true, symbol: "none", data: line, lineStyle: { opacity: 0 },
      areaStyle: { color: alpha(t.win, 0.08), origin: d.better_below ? "start" : "end" }, z: 0 }];
    const ax = (name: string, extra: object) => ({ type: "value", name, nameLocation: "middle", ...L.AX,
      nameTextStyle: { color: t.dim, fontFamily: "Inter", fontSize: ts(11) }, ...extra });
    const dot = (p: SbsDot["points"][number]) => ({ value: [p.x, p.y], name: p.player, d: p });
    const named = d.points.filter((p) => p.named || p.hi).sort((a, b) => b.y - a.y);
    const yspan = Math.ceil(ymax) - Math.floor(ymin);
    const slot = (k: number): [number, number] => [xmax * 0.02, Math.floor(ymin) + yspan * (0.95 - k * 0.075)];
    const tip = (p: { data: { d?: SbsDot["points"][number] } }) => { const x = p.data?.d;
      return x ? `<b>${x.player}</b> · ${x.team}<br/>${d.x_label}: ${show(x.x, 0)} · ${d.y_label}: ${show(x.y, d.y_label === "Runs above average" || d.y_label === "Runs saved" ? 1 : 0)}` : ""; };
    return {
      grid: { left: 70, right: 24, top: 18, bottom: 48 },
      xAxis: ax(d.x_label, { min: 0, max: Math.ceil(xmax), nameGap: 28 }),
      yAxis: ax(d.y_label, { min: Math.floor(ymin), max: Math.ceil(ymax), nameGap: 52, nameRotate: 90 }),
      tooltip: { ...L.TT, trigger: "item", formatter: tip },
      series: [
        ...shade,
        ...(line.length ? [{ type: "line", silent: true, symbol: "none", data: line, lineStyle: { color: t.dim, type: "dashed", width: 1.5 }, z: 1 }] : []),
        { type: "scatter", symbolSize: 9, z: 2, itemStyle: { color: t.grey, opacity: 0.55 }, data: d.points.filter((p) => !p.ranked && !p.hi).map(dot) },
        { type: "scatter", symbolSize: 13, z: 3, itemStyle: { color: col, borderColor: t.tile, borderWidth: 2 },
          data: d.points.filter((p) => p.ranked && !p.hi).map(dot) },
        { type: "scatter", symbolSize: 17, z: 4, itemStyle: { color: t.led, borderColor: t.tile, borderWidth: 2, ...L.glow(alpha(t.led, 0.6)) },
          data: d.points.filter((p) => p.hi).map(dot) },
        // the names in a column at the top left, highest first, each with a thin line to its dot, so two dots close
        // together never put their names on top of each other
        ...named.map((p, k) => ({ type: "line", silent: true, symbol: "none", z: 1, data: [slot(k), [p.x, p.y]],
          lineStyle: { color: p.hi ? t.led : col, width: 1, opacity: 0.6 } })),
        { type: "scatter", silent: true, symbolSize: 0, z: 5, data: named.map((p, k) => ({ value: slot(k),
          label: { show: true, position: "right", formatter: p.player, color: p.hi ? t.led : t.ink, fontFamily: "Bebas Neue", fontSize: ts(13) } })) },
      ],
    };
  }, [t, d, best]);
  if (!d.points.length) return <div className="empty">Nothing to show yet.</div>;
  return <EChart option={option} height={420} label={`${d.y_label} against ${d.x_label.toLowerCase()}`} />;
}

/** Projected season totals, the season record as a dashed line; a player on course to beat it lit (🔥). */
export function PaceBars({ rows, record }: { rows: { player: string; team: string; value: number; now: number; matches: number; beats: boolean }[]; record: number | null }) {
  const t = useTheme();
  const option = useMemo<Option>(() => {
    const L = look(t), max = Math.max(...rows.map((r) => r.value), record ?? 0) * 1.25;
    return {
      grid: { left: 6, right: 40, top: 6, bottom: 6, containLabel: true },
      xAxis: { type: "value", show: false, max },
      yAxis: { type: "category", inverse: true, data: rows.map((r) => r.player), triggerEvent: true, axisLine: { show: false }, axisTick: { show: false },
        axisLabel: { color: t.ink, fontFamily: "Bebas Neue", fontSize: ts(17), margin: 10, formatter: (v: string) => `${v}${rows.find((r) => r.player === v)?.beats ? " 🔥" : ""}` } },
      tooltip: { ...L.TT, formatter: (p: { dataIndex: number }) => { const r = rows[p.dataIndex]; return r ? `${r.player} (${r.team}): on course for ${r.value}, now ${r.now} in ${r.matches} matches` : ""; } },
      series: [{ type: "bar", barWidth: "60%", data: rows.map((r) => ({ value: r.value, name: r.player, itemStyle: { color: r.beats ? t.led : t.blue, borderRadius: 0 } })),
        label: { show: true, position: "right", formatter: (p: { dataIndex: number }) => `{v|${rows[p.dataIndex]?.value ?? ""}}{t|now ${rows[p.dataIndex]?.now ?? ""}}`,
          rich: { v: { ...L.VAL(17) }, t: { fontFamily: "Inter", fontSize: ts(10), color: t.dim, padding: [0, 0, 0, 8] } } },
        ...(record ? { markLine: { silent: true, symbol: "none", lineStyle: { color: t.dim, type: "dashed", width: 1.5 },
          label: { formatter: `season record ${record}`, color: t.dim, fontFamily: "Inter", fontSize: ts(10), position: "end" }, data: [{ xAxis: record }] } } : {}) }],
    };
  }, [t, rows, record]);
  return <EChart option={option} height={Math.max(160, rows.length * 34 + 30)} label="Projected season totals" />;
}

/** A record's history: each dot a new record (the match opens on a click), the line flat while it stood. */
export function RecordSteps({ points, end, unit }: { points: { date: string; y: number; label: string; holder: string; id: string }[]; end: string; unit: string }) {
  const t = useTheme();
  const option = useMemo<Option>(() => {
    const L = look(t), last = points[points.length - 1];
    const line = [...points.map((p) => [p.date, p.y]), ...(last && end > last.date ? [[end, last.y]] : [])];
    return {
      grid: { left: 70, right: 40, top: 40, bottom: 36 },
      xAxis: { type: "time", ...L.AX },
      yAxis: { type: "value", name: unit, nameLocation: "middle", nameRotate: 90, nameGap: 50, boundaryGap: ["8%", "18%"],
        nameTextStyle: { color: t.dim, fontFamily: "Inter", fontSize: ts(11) }, ...L.AX, scale: true },
      tooltip: { ...L.TT, trigger: "item", formatter: (p: { data: { d?: (typeof points)[number] } }) => { const d = p.data?.d; return d ? `<b>${d.label}</b> by ${d.holder}<br/>${d.date}` : ""; } },
      series: [
        { type: "line", step: "end", silent: true, symbol: "none", data: line, lineStyle: { color: t.blue, width: 3 } },
        { type: "scatter", symbolSize: 14, z: 3, itemStyle: { color: t.led, borderColor: t.tile, borderWidth: 2 },
          // the record as it stands is named; every earlier one says its figures when you point at it
          data: points.map((p, i) => ({ value: [p.date, p.y], d: p, match: p.id,
            label: { show: i === points.length - 1, position: "top", formatter: p.label, color: t.ink, fontFamily: "Inter", fontWeight: 700, fontSize: ts(11) } })) },
      ],
    };
  }, [t, points, end, unit]);
  return <EChart option={option} height={340} label="The record over time" />;
}

/** Lines over time: one per player (a rating) or team (Elo), each point a match day; `base` draws a dashed line
 *  (1500 for Elo). */
export function TimeLines({ series, y, base, dec = 2 }: { series: { name: string; points: { date: string; v: number; id?: string }[] }[]; y: string; base?: number; dec?: number }) {
  const t = useTheme();
  const option = useMemo<Option>(() => {
    const L = look(t), pal = [t.led, t.blue, t.win, t.violet, t.warm, t.teal, t.grey];
    return {
      legend: { top: 0, textStyle: { color: t.ink, fontFamily: "Inter", fontSize: ts(11) } },
      grid: { left: 56, right: 24, top: 40, bottom: 36 },
      xAxis: { type: "time", ...L.AX },
      yAxis: { type: "value", name: y, scale: true, nameTextStyle: { color: t.dim, fontFamily: "Inter", fontSize: ts(11) }, ...L.AX },
      tooltip: { ...L.TT, trigger: "axis", valueFormatter: (v: number) => (dec ? v.toFixed(dec) : String(Math.round(v))) },
      series: series.map((s, i) => ({ name: s.name, type: "line", step: "end", symbol: "circle", symbolSize: 5, showSymbol: s.points.length < 60,
        lineStyle: { width: 2.5, color: pal[i % pal.length] }, itemStyle: { color: pal[i % pal.length] },
        data: s.points.map((p) => ({ value: [p.date, p.v], ...(p.id ? { match: p.id } : {}) })),
        ...(i === 0 && base != null ? { markLine: { silent: true, symbol: "none", lineStyle: { color: t.dim, type: "dashed" }, label: { show: false }, data: [{ yAxis: base }] } } : {}) })),
    };
  }, [t, series, y, base, dec]);
  if (!series.length) return <div className="empty">Pick someone to draw.</div>;
  return <EChart option={option} height={380} label={`${y} over time`} />;
}
