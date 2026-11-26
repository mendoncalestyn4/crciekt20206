// Insights (stage 3): home wins against away wins in every competition, and one measure of scoring season by season.
import { useMemo } from "react";
import type { ArcChart, CompareChart, HomeRow, Quad, QuadPoint, SeasonChart } from "../api";
import { useTheme } from "../theme";
import { EChart, type Option } from "./EChart";
import { look, ts } from "./look";

/** Black or white, whichever reads better on a bar of this colour (so the % inside shows in every team's look). */
const inkOn = (hex: string) => {
  const h = hex.replace("#", ""), n = (i: number) => parseInt(h.slice(i, i + 2), 16) / 255;
  const lin = (c: number) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
  const lum = 0.2126 * lin(n(0)) + 0.7152 * lin(n(2)) + 0.0722 * lin(n(4));
  return lum > 0.2 ? "#111111" : "#ffffff";
};

/** Home side won, away side won, draw or tie: one stacked bar per competition (in the agreed order), each part its
 *  share of the finished matches at home grounds. */
export function HomeBars({ rows }: { rows: HomeRow[] }) {
  const t = useTheme();
  const option = useMemo<Option>(() => {
    const L = look(t);
    const part = (name: string, key: "home" | "away" | "other", text: "home_text" | "away_text" | "other_text", colour: string, inside: boolean) => ({
      name, type: "bar", stack: "all", barWidth: "58%", itemStyle: { color: colour },
      data: rows.map((r) => ({ value: r[key], tip: r[text] })),
      label: { show: inside, position: "inside", ...L.VAL(13), color: inkOn(colour),
        formatter: (p: { value: number }) => (p.value >= 9 ? `${Math.round(p.value)}%` : "") },
    });
    return {
      legend: { top: 0, left: 0, textStyle: { color: t.ink, fontFamily: "Inter", fontSize: ts(11) } },
      grid: { left: 6, right: 16, top: 34, bottom: 24, containLabel: true },
      xAxis: { type: "value", max: 100, name: "% of matches", nameLocation: "middle", nameGap: 26, ...L.AX,
        nameTextStyle: { color: t.dim, fontFamily: "Inter", fontSize: ts(11) } },
      yAxis: { type: "category", inverse: true, data: rows.map((r) => r.label), axisLine: { show: false }, axisTick: { show: false },
        axisLabel: { color: t.ink, fontFamily: "Bebas Neue", fontSize: ts(14), margin: 10 } },
      tooltip: { ...L.TT, trigger: "item", formatter: (p: { seriesName: string; name: string; value: number; data: { tip: string } }) =>
        `<b>${p.name}</b><br/>${p.seriesName}: ${p.data.tip} (${Math.round(p.value)}%)` },
      series: [part("Home side won", "home", "home_text", t.blue, true), part("Away side won", "away", "away_text", t.loss, true),
        part("Draw or tie", "other", "other_text", t.grey, false)],
    };
  }, [t, rows]);
  return <EChart option={option} height={Math.max(220, 44 * rows.length + 80)} label="Home wins against away wins" />;
}

/** One measure in each season: a line through the seasons, each point labelled; hover for how many matches. */
export function SeasonLine({ c }: { c: SeasonChart }) {
  const t = useTheme();
  const option = useMemo<Option>(() => {
    const L = look(t);
    return {
      grid: { left: 52, right: 20, top: 28, bottom: 40 },
      xAxis: { type: "category", data: c.points.map((p) => p.season), name: "Season", nameLocation: "middle", nameGap: 28, ...L.AX,
        nameTextStyle: { color: t.dim, fontFamily: "Inter", fontSize: ts(11) } },
      yAxis: { type: "value", min: 0, boundaryGap: [0, "22%"], ...L.AX },   // room above the highest point for its label
      tooltip: { ...L.TT, trigger: "item", formatter: (p: { dataIndex: number }) => { const x = c.points[p.dataIndex];
        return x ? `${x.season}: ${x.text}<br/>${x.matches} match${x.matches === 1 ? "" : "es"}` : ""; } },
      series: [{ type: "line", symbol: "circle", symbolSize: 9, lineStyle: { width: 2.5, color: t.blue }, itemStyle: { color: t.blue },
        data: c.points.map((p) => p.v),
        label: { show: true, position: "top", ...L.VAL(12), color: t.ink, formatter: (p: { dataIndex: number }) => c.points[p.dataIndex]?.text ?? "" } }],
    };
  }, [t, c]);
  if (!c.points.length) return <div className="empty">No figures yet.</div>;
  return <EChart option={option} height={250} label={c.label} />;
}

/** Every player as a dot, split into four by the average lines (dashed): the best corner's dots blue, the rest grey,
 *  each corner named in the key under it; the furthest-out players named on the chart, everyone on hover. */
export function Quadrant({ q }: { q: Quad }) {
  const t = useTheme();
  const option = useMemo<Option>(() => {
    const L = look(t);
    const xs = q.points.map((p) => p.x), ys = q.points.map((p) => p.y);
    const x0 = Math.min(q.x_ref, ...xs), x1 = Math.max(q.x_ref, ...xs), y0 = Math.min(q.y_ref, ...ys), y1 = Math.max(q.y_ref, ...ys);
    const px = (x1 - x0) * 0.1 || 1, py = (y1 - y0) * 0.12 || 1;
    const good = (p: QuadPoint) => (q.x_low ? p.x <= q.x_ref : p.x >= q.x_ref) && (q.y_low ? p.y <= q.y_ref : p.y >= q.y_ref);
    const far = (p: QuadPoint) => Math.abs(p.x - q.x_ref) / ((x1 - x0) || 1) + Math.abs(p.y - q.y_ref) / ((y1 - y0) || 1);
    const named = new Set([...q.points].sort((a, b) => far(b) - far(a)).slice(0, 5).map((p) => p.player));
    const ax = (name: string, min: number, max: number, gap: number) => ({ type: "value", name, nameLocation: "middle", nameGap: gap,
      min: Math.floor(min), max: Math.ceil(max), ...L.AX, axisLabel: { ...L.AX.axisLabel, showMinLabel: false, showMaxLabel: false },
      nameTextStyle: { color: t.dim, fontFamily: "Inter", fontSize: ts(11) }, splitLine: { show: false } });
    const G = { left: 72, right: 24, top: 20, bottom: 54, containLabel: false };
    return {
      grid: G,
      xAxis: ax(q.x_label, x0 - px, x1 + px, 30), yAxis: ax(q.y_label, y0 - py, y1 + py, 44),
      tooltip: { ...L.TT, trigger: "item", formatter: (p: { data: { p: QuadPoint } }) => { const d = p.data.p;
        return `<b>${d.player}</b> · ${d.team}<br/>${q.x_label}: ${d.x.toFixed(1)}<br/>${q.y_label}: ${d.y.toFixed(1)}<br/>${d.style}`; } },
      series: [{ type: "scatter", symbolSize: 10,
        data: q.points.map((p) => ({ value: [p.x, p.y], name: p.player, p, itemStyle: { color: good(p) ? t.blue : t.grey, opacity: good(p) ? 1 : 0.7 },
          label: { show: named.has(p.player), formatter: p.player, position: "right", color: t.ink, fontFamily: "Inter", fontSize: ts(11) } })),
        labelLayout: { hideOverlap: true },
        markLine: { silent: true, symbol: "none", label: { show: false }, lineStyle: { color: t.dim, type: "dashed", width: 1.2 },
          data: [{ xAxis: q.x_ref }, { yAxis: q.y_ref }] } }],
    };
  }, [t, q]);
  if (q.points.length < 3) return <div className="empty">Not enough players yet.</div>;
  return (<>
    <EChart option={option} height={420} label={`${q.y_label} against ${q.x_label}`} />
    <div className="quadkey">{(["↗", "↖", "↘", "↙"] as const).map((a, i) => <span key={a}><b>{a}</b> {q.corners[i]}</span>)}</div>
  </>);
}

/** The colours of the players compared, in the order picked (the first is always blue). */
export const pickColours = (t: ReturnType<typeof useTheme>) => [t.blue, t.led, t.win, t.violet];

/** One stat for the players compared: a bar each in their own colour, the competition's average dashed. */
export function CompareBars({ c, order }: { c: CompareChart; order: string[] }) {
  const t = useTheme();
  const option = useMemo<Option>(() => {
    const L = look(t), pal = pickColours(t);
    return {
      grid: { left: 6, right: 70, top: c.reference != null ? 22 : 6, bottom: 6, containLabel: true },
      xAxis: { type: "value", show: false, scale: false },
      yAxis: { type: "category", inverse: true, data: c.rows.map((r) => r.player), axisLine: { show: false }, axisTick: { show: false },
        axisLabel: { color: t.ink, fontFamily: "Bebas Neue", fontSize: ts(15), margin: 10 } },
      tooltip: { ...L.TT, formatter: (p: { dataIndex: number }) => { const r = c.rows[p.dataIndex]; return r ? `${r.player}: ${r.text}` : ""; } },
      series: [{ type: "bar", barWidth: "56%",
        data: c.rows.map((r) => ({ value: r.value, name: r.player, itemStyle: { color: pal[order.indexOf(r.player) % 4] ?? t.blue } })),
        label: { show: true, position: "right", ...L.VAL(14), color: t.ink, formatter: (p: { dataIndex: number }) => c.rows[p.dataIndex]?.text ?? "" },
        ...(c.reference != null ? { markLine: { silent: true, symbol: "none", lineStyle: { color: t.dim, type: "dashed", width: 1.4 },
          label: { formatter: `average ${c.reference.toFixed(Math.max(c.dec, 1))}`, color: t.dim, fontFamily: "Inter", fontSize: ts(10), position: "end" },
          data: [{ xAxis: c.reference }] } } : {}) }],
    };
  }, [t, c, order]);
  return <EChart option={option} height={60 + c.rows.length * 40} label={c.label} />;
}

/** Each player's running total after every innings, a line each in their colour, named at its end. */
export function CareerCurves({ series, what, order }: { series: { player: string; points: number[] }[]; what: string; order: string[] }) {
  const t = useTheme();
  const option = useMemo<Option>(() => {
    const L = look(t), pal = pickColours(t);
    const ax = (name: string, gap: number, extra: object) => ({ type: "value", name, nameLocation: "middle", nameGap: gap, ...L.AX,
      nameTextStyle: { color: t.dim, fontFamily: "Inter", fontSize: ts(11) }, ...extra });
    return {
      grid: { left: 14, right: 110, top: 34, bottom: 24, containLabel: true },
      // the totals' name above their axis (never against its numbers, however wide they get)
      xAxis: ax("Innings played", 30, { minInterval: 1 }),
      yAxis: { ...ax(`Total ${what}`, 12, { minInterval: 1 }), nameLocation: "end", nameTextStyle: { color: t.dim, fontFamily: "Inter", fontSize: ts(11), align: "left" } },
      tooltip: { ...L.TT, trigger: "item", formatter: (p: { seriesName: string; value: [number, number] }) => `<b>${p.seriesName}</b><br/>after innings ${p.value[0]}: ${p.value[1]} ${what}` },
      series: series.map((s) => { const col = pal[order.indexOf(s.player) % 4] ?? t.blue;
        return { name: s.player, type: "line", symbol: "circle", symbolSize: 5, showSymbol: s.points.length < 40,
          lineStyle: { width: 2.5, color: col }, itemStyle: { color: col }, data: s.points.map((v, i) => [i + 1, v]),
          endLabel: { show: true, formatter: s.player, color: col, fontFamily: "Inter", fontSize: ts(12) },
          labelLayout: { moveOverlap: "shiftY" } }; }),   // two lines ending together keep their names apart
    };
  }, [t, series, what, order]);
  if (!series.some((s) => s.points.length)) return <div className="empty">No innings yet.</div>;
  return <EChart option={option} height={380} label={`Total ${what} after each innings`} />;
}

/** Career arc (stage 5): the usual change since a player's 1st season here, one line for new players and one for those
 *  already playing when the career began; a dashed line at 0 (no change), each point labelled; hover for how many
 *  players stand behind that step. */
export function ArcLines({ c }: { c: ArcChart }) {
  const t = useTheme();
  const option = useMemo<Option>(() => {
    const L = look(t);
    const most = Math.max(...c.lines.map((l) => l.points.length));
    const labels = Array.from({ length: most }, (_, i) => c.lines.flatMap((l) => l.points).find((p) => p.n === i + 1)?.label ?? `${i + 1}`);
    const colours = [t.blue, t.grey];
    return {
      legend: { top: 0, left: 0, textStyle: { color: t.ink, fontFamily: "Inter", fontSize: ts(11) } },
      grid: { left: 52, right: 24, top: 40, bottom: 40 },
      xAxis: { type: "category", data: labels, name: "Season of their career here", nameLocation: "middle", nameGap: 28, ...L.AX,
        nameTextStyle: { color: t.dim, fontFamily: "Inter", fontSize: ts(11) } },
      yAxis: { type: "value", boundaryGap: ["18%", "18%"], ...L.AX },
      tooltip: { ...L.TT, trigger: "item", formatter: (p: { seriesIndex: number; dataIndex: number }) => {
        const ln = c.lines[p.seriesIndex], x = ln?.points[p.dataIndex];
        return x && ln ? `<b>${ln.name}</b><br/>${x.label}: ${x.text}<br/>${x.n === 1 ? `${x.players} players` : `${x.players} players' change from the season before`}` : ""; } },
      series: c.lines.map((ln, i) => ({
        name: ln.name, type: "line", symbol: "circle", symbolSize: 8, labelLayout: { hideOverlap: true }, lineStyle: { width: 2.5, color: colours[i % 2] }, itemStyle: { color: colours[i % 2] },
        data: ln.points.map((p) => p.v),
        label: { show: true, position: i ? "bottom" : "top", ...L.VAL(11), color: t.ink, formatter: (p: { dataIndex: number }) => ln.points[p.dataIndex]?.text ?? "" },
        ...(i === 0 ? { markLine: { silent: true, symbol: "none", label: { show: false }, lineStyle: { type: "dashed", color: t.dim, width: 1 }, data: [{ yAxis: 0 }] } } : {}),
      })),
    };
  }, [t, c]);
  return <EChart option={option} height={270} label={c.title} />;
}
