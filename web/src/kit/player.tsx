// The Player page's pieces: bars for one stat split one way (with the player's own overall as a dashed line), the
// player against everyone (paired bars), every innings with the form line, the conversion funnel, match impact, rank
// over time, and the standard batting and bowling tables (the same columns in every competition).
import { useMemo } from "react";
import type { Bar, FormT, Pair, RecordTableT } from "../api";
import { f1, ord } from "../format";
import { useTheme } from "../theme";
import { Name } from "./base";
import { alpha } from "./charts";
import { EChart, type Option } from "./EChart";
import { look, ts } from "./look";

/** One stat split one way, as horizontal bars: the label on the left, the number at the end, the player's overall as a
 *  dashed line. `lowBetter`: economy (the shortest bar is the best). */
export function SplitBars({ rows, reference, dec = 1, height, unit = "", lowBetter = false }: {
  rows: Bar[]; reference?: number | null; dec?: number; height?: number; unit?: string; lowBetter?: boolean;
}) {
  const t = useTheme();
  const shown = useMemo(() => rows.filter((r) => r.value != null), [rows]);
  const option = useMemo<Option>(() => {
    const L = look(t), vals = shown.map((r) => r.value ?? 0);
    const best = lowBetter ? Math.min(...vals) : Math.max(...vals);
    return {
      grid: { left: 6, right: 70, top: 8, bottom: 8, containLabel: true },
      xAxis: { show: false, max: Math.max(...vals, reference ?? 0, 1) * 1.05 },
      yAxis: { type: "category", inverse: true, data: shown.map((r) => r.label), axisLine: { show: false }, axisTick: { show: false },
        axisLabel: { color: t.ink, fontFamily: "Bebas Neue", fontSize: ts(15), margin: 10 } },
      tooltip: { ...L.TT, formatter: (p: { dataIndex: number }) => { const r = shown[p.dataIndex]; return r ? `${r.label}: ${r.value == null ? "–" : (+r.value).toFixed(dec)}${unit}${r.note ? `<br/><span style="opacity:.75">${r.note}</span>` : ""}` : ""; } },
      series: [{ type: "bar", barWidth: "58%",
        data: shown.map((r) => ({ value: r.value, itemStyle: { color: r.value === best && shown.length > 1 ? t.led : alpha(t.led, 0.55), borderRadius: 0 } })),
        label: { show: true, position: "right", ...L.VAL(17), formatter: (p: { value: number }) => (+p.value).toFixed(dec) + unit },
        ...(reference != null ? { markLine: { silent: true, symbol: "none", label: { show: false }, lineStyle: { color: t.ink, type: "dashed", width: 1.5, opacity: 0.6 },
          data: [{ xAxis: reference }] } } : {}) }],
    };
  }, [t, shown, reference, dec, unit, lowBetter]);
  if (!shown.length) return <div className="empty">Nothing to show yet.</div>;
  return <EChart option={option} height={height ?? Math.max(110, 34 + shown.length * 40)} label="Split" />;
}

/** The player (gold) against everyone here (grey), side by side for each band or position. */
export function PairedBars({ rows, me, unit = "", dec = 1, others = "Everyone here" }: { rows: Pair[]; me: string; unit?: string; dec?: number; others?: string }) {
  const t = useTheme();
  const option = useMemo<Option>(() => {
    const L = look(t);
    return {
      legend: { top: 0, left: 0, textStyle: { color: t.ink, fontFamily: "Bebas Neue", fontSize: ts(14) }, itemWidth: 16, itemHeight: 12 },
      grid: { left: 6, right: 60, top: 34, bottom: 6, containLabel: true },
      xAxis: { show: false },
      yAxis: { type: "category", inverse: true, data: rows.map((r) => (r.key ? `★ ${r.label}` : r.label)), axisLine: { show: false }, axisTick: { show: false },
        axisLabel: { color: t.ink, fontFamily: "Bebas Neue", fontSize: ts(15), margin: 10 } },
      tooltip: { ...L.TT, trigger: "axis", axisPointer: { type: "shadow" }, formatter: (ps: { dataIndex: number }[]) => {
        const r = rows[ps[0]?.dataIndex ?? 0];
        return r ? `${r.label}<br/>${me}: <b>${r.me == null ? "–" : (+r.me).toFixed(dec)}${unit}</b><br/>${others}: ${r.all == null ? "–" : (+r.all).toFixed(dec)}${unit}${r.note ? `<br/><span style="opacity:.75">${r.note}</span>` : ""}` : ""; } },
      series: [
        { type: "bar", name: me, data: rows.map((r) => r.me), barGap: "15%", itemStyle: { color: t.led, borderRadius: 0 },
          label: { show: true, position: "right", ...L.VAL(15), formatter: (p: { value: number | null }) => (p.value == null ? "" : `${(+p.value).toFixed(dec)}${unit}`) } },
        { type: "bar", name: others, data: rows.map((r) => r.all), itemStyle: { color: t.grey, borderRadius: 0 },
          label: { show: true, position: "right", color: t.dim, fontFamily: "Inter", fontSize: 12, formatter: (p: { value: number | null }) => (p.value == null ? "" : `${(+p.value).toFixed(dec)}${unit}`) } },
      ],
    };
  }, [t, rows, me, unit, dec, others]);
  return <EChart option={option} height={Math.max(150, 50 + rows.length * 56)} label={`Against ${others.toLowerCase()}`} />;
}

/** Every innings (or innings bowled) as a bar, oldest first; the average over the last few as a line; the average
 *  over all of them dashed. */
export function FormBars({ f, unit }: { f: FormT; unit: "runs" | "wickets" }) {
  const t = useTheme();
  const option = useMemo<Option>(() => {
    const L = look(t), n = f.values.length;
    const col = (v: number) => (unit === "runs" ? (v >= 100 ? t.win : v >= 50 ? alpha(t.win, 0.75) : alpha(t.led, 0.6)) : v >= 4 ? t.win : alpha(t.led, 0.6));
    return {
      grid: { left: 36, right: 14, top: 18, bottom: 22 },
      tooltip: { ...L.TT, trigger: "axis", axisPointer: { type: "shadow" }, formatter: (ps: { dataIndex: number }[]) => {
        const i = ps[0]?.dataIndex ?? 0, r = f.rolling[i];
        return `${f.labels[i] ?? ""}${r != null ? `<br/><span style="opacity:.75">${unit === "runs" ? "average" : "wickets an innings"} over the last ${f.window}: ${unit === "runs" ? f1(r) : r.toFixed(2)}</span>` : ""}`; } },
      xAxis: { type: "category", data: f.values.map((_, i) => String(i + 1)), ...L.AX, splitLine: { show: false },
        axisLabel: { ...L.AX.axisLabel, interval: n > 40 ? Math.ceil(n / 20) - 1 : n > 20 ? 1 : 0 } },
      yAxis: { ...L.AX, axisLine: { show: false }, minInterval: 1 },
      series: [
        { type: "bar", barWidth: n > 60 ? "70%" : "58%", data: f.values.map((v) => ({ value: v, itemStyle: { color: col(v), borderRadius: 0 } })) },
        { type: "line", data: f.rolling, symbol: "none", smooth: 0.2, lineStyle: { color: t.led, width: 3 }, connectNulls: false, z: 5,
          ...(f.overall != null ? { markLine: { silent: true, symbol: "none", label: { show: false }, lineStyle: { color: t.ink, type: "dashed", width: 1.5, opacity: 0.55 },
            data: [{ yAxis: f.overall }] } } : {}) },
      ],
    };
  }, [t, f, unit]);
  return <EChart option={option} height={300} label="Form" />;
}

/** Conversion: the share of innings reaching each score (the player's line, everyone here as grey dots), the key marks
 *  for the format lit up. */
export function Funnel({ rows }: { rows: { mark: number; pct: number | null; all_pct: number | null; highlight: boolean }[] }) {
  const t = useTheme();
  const option = useMemo<Option>(() => {
    const L = look(t);
    return {
      grid: { left: 44, right: 16, top: 30, bottom: 26 },
      legend: { top: 0, right: 0, textStyle: { color: t.ink, fontFamily: "Bebas Neue", fontSize: ts(14) }, itemWidth: 16, itemHeight: 10 },
      tooltip: { ...L.TT, trigger: "axis", formatter: (ps: { dataIndex: number }[]) => { const r = rows[ps[0]?.dataIndex ?? 0];
        return r ? `${r.mark}+: <b>${r.pct == null ? "–" : Math.round(r.pct)}%</b> of their innings<br/>everyone here: ${r.all_pct == null ? "–" : Math.round(r.all_pct)}%` : ""; } },
      xAxis: { type: "category", data: rows.map((r) => `${r.mark}+`), ...L.AX, splitLine: { show: false } },
      yAxis: { type: "value", min: 0, max: 100, ...L.AX, axisLine: { show: false }, axisLabel: { ...L.AX.axisLabel, formatter: (v: number) => `${v}%` } },
      series: [
        { type: "line", name: "This player", data: rows.map((r) => ({ value: r.pct, symbolSize: r.highlight ? 13 : 7 })), symbol: "circle",
          lineStyle: { color: t.led, width: 3 }, itemStyle: { color: t.led },
          label: { show: true, position: "top", ...L.VAL(14), formatter: (p: { value: number | null; dataIndex: number }) => (rows[p.dataIndex]?.highlight && p.value != null ? `${Math.round(p.value)}%` : "") } },
        { type: "scatter", name: "Every batter here", data: rows.map((r) => r.all_pct), symbolSize: 10, itemStyle: { color: t.grey } },
      ],
    };
  }, [t, rows]);
  return <EChart option={option} height={300} label="Conversion" />;
}

/** One number a match: green for a win. */
export function ImpactBars({ rows }: { rows: { label: string; value: number; won: boolean; note: string }[] }) {
  const t = useTheme();
  const option = useMemo<Option>(() => {
    const L = look(t), n = rows.length;
    return {
      grid: { left: 40, right: 12, top: 14, bottom: 22 },
      tooltip: { ...L.TT, formatter: (p: { dataIndex: number }) => { const r = rows[p.dataIndex]; return r ? `${r.label}: <b>${r.value}</b> (${r.note})${r.won ? " · won" : ""}` : ""; } },
      xAxis: { type: "category", data: rows.map((_, i) => String(i + 1)), ...L.AX, splitLine: { show: false },
        axisLabel: { ...L.AX.axisLabel, interval: n > 40 ? Math.ceil(n / 20) - 1 : n > 20 ? 1 : 0 } },
      yAxis: { ...L.AX, axisLine: { show: false } },
      series: [{ type: "bar", barWidth: "60%", data: rows.map((r) => ({ value: r.value, itemStyle: { color: r.won ? t.win : alpha(t.led, 0.6), borderRadius: 0 } })) }],
    };
  }, [t, rows]);
  return <EChart option={option} height={280} label="Match impact" />;
}

/** Where they finished each season for runs and wickets (1 at the top). */
export function RankLines({ rows }: { rows: { season: string; runs_rank: number | null; runs_of: number | null; wickets_rank: number | null; wickets_of: number | null }[] }) {
  const t = useTheme();
  const option = useMemo<Option>(() => {
    const L = look(t), most = Math.max(...rows.map((r) => Math.max(r.runs_of ?? 0, r.wickets_of ?? 0)), 2);
    const pad = Math.max(0.6, (most - 1) * 0.15);   // room for a label above the best rank and below the worst
    // each season's two labels move apart: the higher point's above it, the lower point's below (in a big competition a
    // 6th and a 71st can sit close together)
    const other = (key: "runs_rank" | "wickets_rank") => (key === "runs_rank" ? "wickets_rank" : "runs_rank");
    const at = (r: (typeof rows)[number], key: "runs_rank" | "wickets_rank", dflt: "top" | "bottom") => {
      const mine = r[key], theirs = r[other(key)];
      return mine == null || theirs == null ? dflt : mine <= theirs ? "top" : "bottom";
    };
    const line = (name: string, key: "runs_rank" | "wickets_rank", c: string, dflt: "top" | "bottom") => ({ type: "line", name,
      data: rows.map((r) => ({ value: r[key], label: { position: at(r, key, dflt) } })), symbol: "circle", symbolSize: 10,
      lineStyle: { color: c, width: 3 }, itemStyle: { color: c }, connectNulls: true,
      label: { show: true, ...L.VAL(14), color: c, formatter: (p: { value: number | null }) => (p.value == null ? "" : ord(p.value)) } });
    return {
      legend: { top: 0, left: 0, textStyle: { color: t.ink, fontFamily: "Bebas Neue", fontSize: ts(14) }, itemWidth: 16, itemHeight: 10 },
      grid: { left: 44, right: 20, top: 40, bottom: 34 },
      tooltip: { ...L.TT, trigger: "axis" },
      xAxis: { type: "category", data: rows.map((r) => String(r.season)), ...L.AX, splitLine: { show: false } },
      yAxis: { type: "value", inverse: true, min: 1 - pad, max: most + pad, ...L.AX, axisLine: { show: false },
        axisLabel: { ...L.AX.axisLabel, formatter: (v: number) => (Number.isInteger(v) && v >= 1 && v <= most ? ord(v) : "") } },
      series: [...(rows.some((r) => r.runs_rank != null) ? [line("Rank by runs", "runs_rank", t.led, "top")] : []),
        ...(rows.some((r) => r.wickets_rank != null) ? [line("Rank by wickets", "wickets_rank", t.blue, "bottom")] : [])],
    };
  }, [t, rows]);
  return <EChart option={option} height={280} label="Rank over time" />;
}

/** The standard batting or bowling table: hover a column name for what it means. */
export function RecordTable({ t }: { t: RecordTableT }) {
  return (
    <div className="scrollx"><table className="c rec"><thead><tr>{t.cols.map((c) => (
      <th key={c} className={c === t.first ? "" : "r"} title={t.help[c] || undefined}>{c === t.first ? (c === "section" ? "Competition" : "Season") : c}</th>))}</tr></thead>
      <tbody>{t.rows.map((r, i) => (
        <tr key={i}>{t.cols.map((c) => (
          <td key={c} className={c === t.first ? "" : "r"}>{c === t.first ? <Name p={String(r[c] ?? "")} px={19} />
            : <span className={`tn ${["Runs", "Wkts"].includes(c) ? "" : "dimn"}`}>{r[c] ?? "–"}</span>}</td>))}</tr>))}</tbody></table></div>
  );
}
