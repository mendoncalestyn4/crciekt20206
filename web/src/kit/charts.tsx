// The chart pieces, exactly as on the approved mock-up (idea 4: idea 1's charts in idea 2's look), drawn from the
// engine's numbers. Heights are the mock-up's with the approved 20% extra room for the bigger words.
import { useMemo } from "react";
import type { Banner, Elo, Outcome, Result, Stand } from "../api";
import { ab, day, dayer, ord } from "../format";
import { useTheme } from "../theme";
import { EChart, type Option } from "./EChart";
import { look, NUMF, sc, ts } from "./look";

const alpha = (hex: string, a: number) => {
  const h = hex.replace("#", "");
  return `rgba(${parseInt(h.slice(0, 2), 16)},${parseInt(h.slice(2, 4), 16)},${parseInt(h.slice(4, 6), 16)},${a})`;
};

type Row = { player: string; team: string } & Record<string, unknown>;

/** Broadcast's leaderboard bars: names on the left, the number and team on the right, my team lit up. */
export function LeaderBars({ rows, value, mine, colour, height, right = 96, nameSize = 22, valSize = 26, fmt, noTeam, label }: {
  rows: Row[]; value: string; mine: string | null; colour?: string; height: number; right?: number; nameSize?: number;
  valSize?: number; fmt?: (v: number) => string; noTeam?: boolean; label?: string;
}) {
  const t = useTheme();
  const option = useMemo<Option>(() => {
    const L = look(t), col = colour ?? L.MINE, vals = rows.map((r) => Number(r[value] ?? 0));
    return {
      grid: { left: 6, right: ts(right) + 24, top: 4, bottom: 4, containLabel: true },
      xAxis: { show: false, max: Math.max(...vals, 1) },
      yAxis: { type: "category", inverse: true, data: rows.map((r) => r.player), axisLine: { show: false }, axisTick: { show: false },
        axisLabel: { color: t.ink, fontFamily: "Bebas Neue", fontSize: ts(nameSize), margin: 12 } },
      tooltip: { ...L.TT, formatter: (p: { dataIndex: number; value: number }) => `${rows[p.dataIndex]?.player} (${rows[p.dataIndex]?.team}): ${fmt ? fmt(p.value) : p.value}` },
      series: [{ type: "bar", barWidth: "62%",
        data: rows.map((r, i) => ({ value: vals[i], itemStyle: { color: r.team === mine ? col : L.OTHER, borderRadius: 0,
          ...(r.team === mine ? L.glow(alpha(t.led, 0.5)) : {}) } })),
        label: { show: true, position: "right", ...L.VAL(valSize),
          formatter: (p: { value: number; dataIndex: number }) => `{v|${fmt ? fmt(p.value) : p.value}}` + (noTeam ? "" : `{t|${ab(rows[p.dataIndex]?.team ?? "")}}`),
          rich: { v: { ...L.VAL(valSize) }, t: { fontFamily: "Bebas Neue", fontSize: ts(19), color: t.dim, padding: [0, 0, 0, 10] } } } }],
    };
  }, [t, rows, value, mine, colour, right, nameSize, valSize, fmt, noTeam]);
  return <EChart option={option} height={height} label={label} />;
}

/** Every innings as a solid bar, oldest first: green for 50 or more, * not out. */
export function InningsBars({ innings, height = 360 }: { innings: { date: string; opp: string; runs: number; out: boolean }[]; height?: number }) {
  const t = useTheme();
  const option = useMemo<Option>(() => {
    const L = look(t), col = (r: number) => (r >= 50 ? t.win : t.led), when = dayer(innings.map((i) => i.date));
    const max = Math.ceil((Math.max(...innings.map((i) => i.runs), 10) * 1.15) / 10) * 10;
    return {
      grid: { left: 34, right: 10, top: 30, bottom: 44 },
      tooltip: { ...L.TT, formatter: (p: { dataIndex: number }) => { const i = innings[p.dataIndex]; return i ? `${i.runs}${i.out ? "" : "*"} v ${i.opp}, ${day(i.date)}` : ""; } },
      xAxis: { type: "category", data: innings.map((i) => `${ab(i.opp)}\n${when(i.date)}`), ...L.AX, splitLine: { show: false } },
      yAxis: { ...L.AX, axisLine: { show: false }, max },
      series: [{ type: "bar", barWidth: "60%", data: innings.map((i) => ({ value: i.runs, itemStyle: { color: col(i.runs), borderRadius: 0 } })),
        label: { show: true, position: "top", ...L.VAL(24), formatter: (p: { value: number; dataIndex: number }) => p.value + (innings[p.dataIndex]?.out ? "" : "*") } }],
    };
  }, [t, innings]);
  return <EChart option={option} height={height} label="Every innings" />;
}

/** A donut: a share of a whole, with the total and a word in the hole. */
export function Donut({ items, centre, sub, height, radius = ["48%", "68%"], centrePx = 44, labels = true, pad = 3 }: {
  items: [string, number, string][]; centre: string; sub: string; height: number; radius?: [string, string]; centrePx?: number;
  labels?: boolean; pad?: number;
}) {
  const t = useTheme();
  const option = useMemo<Option>(() => ({
    title: { text: centre, subtext: sub, left: "center", top: "center", itemGap: 2,
      textStyle: { color: t.led, fontFamily: NUMF, fontWeight: 700, fontSize: sc(centrePx) },
      subtextStyle: { color: t.dim, fontFamily: "Bebas Neue", fontWeight: 400, fontSize: ts(16) } },
    tooltip: { ...look(t).TT, formatter: "{b}: {c} ({d}%)" },
    series: [{ type: "pie", radius, center: ["50%", "50%"], avoidLabelOverlap: true, padAngle: pad, labelLayout: { hideOverlap: false },
      itemStyle: { borderRadius: 0, borderColor: "transparent", borderWidth: 0 },
      label: { show: labels, overflow: "none", formatter: "{b}\n{c}", color: t.ink, fontFamily: "Inter", fontSize: ts(13), lineHeight: 17 },
      labelLine: { length: 8, length2: 8, lineStyle: { color: t.dim } },
      data: items.filter(([, v]) => v > 0).map(([n, v, c]) => ({ name: n, value: v, itemStyle: { color: c } })) }],
  }), [t, items, centre, sub, radius, centrePx, labels, pad]);
  return <EChart option={option} height={height} label={`${centre} ${sub}`} />;
}

/** A ring: won and lost this season, the win share in the middle. */
export function Ring({ won, lost, other = 0, height = 240 }: { won: number; lost: number; other?: number; height?: number }) {
  const t = useTheme();
  const decided = won + lost;
  return <Donut items={[["Won", won, t.win], ["Lost", lost, t.loss], ["Drawn or no result", other, t.grey]]}
    centre={decided ? `${Math.round((won / decided) * 100)}%` : "–"} sub="won" height={height} radius={["70%", "92%"]}
    centrePx={54} labels={false} pad={4} />;
}

/** A plain form line: wins minus defeats, match by match. */
export function Sparkline({ seq, height = 55 }: { seq: Outcome[]; height?: number }) {
  const t = useTheme();
  const option = useMemo<Option>(() => {
    let c = 0;
    const data = seq.map((o) => (c += o === "W" ? 1 : o === "L" ? -1 : 0));
    return {
      grid: { left: 2, right: 2, top: 4, bottom: 4 },
      xAxis: { type: "category", show: false, data: seq.map((_, i) => i + 1) },
      yAxis: { show: false, scale: true },
      series: [{ type: "line", smooth: 0, symbol: "none", data, lineStyle: { width: 3, color: t.led },
        areaStyle: { color: { type: "linear", x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: alpha(t.led, 0.3) }, { offset: 1, color: "rgba(0,0,0,0)" }] } } }],
    };
  }, [t, seq]);
  return <EChart option={option} height={height} label="Form line" />;
}

/** Every match on a calendar: green won, red lost, grey drawn. The last few months that fit. */
export function CalendarHeat({ results, height = 180, months = 5 }: { results: Result[]; height?: number; months?: number }) {
  const t = useTheme();
  const option = useMemo<Option>(() => {
    const dates = results.map((r) => r.date).sort();
    const last = dates[dates.length - 1] ?? "2026-01-01";
    const end = new Date(`${last.slice(0, 7)}-01T00:00:00Z`);
    end.setUTCMonth(end.getUTCMonth() + 1);
    end.setUTCDate(0);
    const start = new Date(end);
    start.setUTCDate(1);
    start.setUTCMonth(start.getUTCMonth() - (months - 1));
    const first = dates.find((d) => d >= start.toISOString().slice(0, 10)) ?? last;
    const from = first.slice(0, 7) + "-01";
    return {
      visualMap: { show: false, type: "piecewise", pieces: [{ value: 1, color: t.win }, { value: -1, color: t.loss }, { value: 0, color: t.grey }] },
      calendar: { range: [from, end.toISOString().slice(0, 10)], cellSize: [16, 16], top: 20, left: 6, right: 6,
        itemStyle: { color: t.track, borderColor: t.tile, borderWidth: 3 }, splitLine: { show: false }, dayLabel: { show: false },
        monthLabel: { color: t.dim, fontFamily: "Inter", fontSize: ts(11) }, yearLabel: { show: false } },
      tooltip: { ...look(t).TT, formatter: (p: { dataIndex: number }) => { const r = results[p.dataIndex]; return r ? `${day(r.date)}: ${r.result}` : ""; } },
      series: [{ type: "heatmap", coordinateSystem: "calendar", data: results.map((r) => [r.date, r.outcome === "W" ? 1 : r.outcome === "L" ? -1 : 0]) }],
    };
  }, [t, results, months]);
  return <EChart option={option} height={height} label="Every match on a calendar" />;
}

/** Where the team ranks in each section: a track for every team, the team's place on it. */
export function RankTrack({ banner, height = 276 }: { banner: Banner[]; height?: number }) {
  const t = useTheme();
  const option = useMemo<Option>(() => {
    const L = look(t), rows = banner.filter((b) => b.rank != null);
    return {
      grid: { left: 70, right: 30, top: 10, bottom: 30 },
      xAxis: { type: "value", min: 1, interval: 1, inverse: true, ...L.AX, axisLabel: { ...L.AX.axisLabel, formatter: (v: number) => ord(v) } },
      yAxis: { type: "category", data: rows.map((b) => b.section), axisLine: { show: false }, axisTick: { show: false },
        axisLabel: { color: t.ink, fontFamily: "Bebas Neue", fontSize: ts(22) } },
      series: [
        { type: "bar", barWidth: 10, data: rows.map((b) => b.teams), itemStyle: { color: t.track, borderRadius: 5 }, barGap: "-100%", silent: true },
        { type: "scatter", symbolSize: 36, data: rows.map((b) => b.rank), itemStyle: { color: L.MINE, borderColor: t.dark ? "#fff" : t.ink, borderWidth: 2 },
          label: { show: true, ...L.VAL(17), color: t.led_ink, formatter: (p: { value: number }) => p.value } }],
    };
  }, [t, banner]);
  return <EChart option={option} height={height} label="Where the team ranks" />;
}

/** The series score after each match: a step line for each side. */
export function StepLine({ matches, team, opp, height = 300 }: { matches: Result[]; team: string; opp: string; height?: number }) {
  const t = useTheme();
  const option = useMemo<Option>(() => {
    const L = look(t);
    return {
      grid: { left: 30, right: 16, top: 50, bottom: 30 },
      legend: { top: 0, right: 0, textStyle: { color: t.soft, fontFamily: "Bebas Neue", fontSize: ts(18) } },
      xAxis: { type: "category", data: matches.map((r, i) => `${r.section === "Tests" ? "Test" : r.section === "ODIs" ? "ODI" : r.section === "T20Is" ? "T20I" : "Match"} ${r.no ?? i + 1}`),
        ...L.AX, splitLine: { show: false } },
      yAxis: { ...L.AX, minInterval: 1, axisLine: { show: false } },
      series: ([[team, L.MINE, "W", "top"], [opp, t.blue, "L", "bottom"]] as const).map(([name, col, o, at]) => {
        let c = 0;
        return { name, type: "line", step: "end", symbolSize: 10, data: matches.map((r) => (c += r.outcome === o ? 1 : 0)),
          lineStyle: { width: 3, color: col }, itemStyle: { color: col },
          label: { show: true, position: at, distance: 8, ...L.VAL(18), color: col, formatter: (p: { value: number }) => (p.value ? String(p.value) : "") } };
      }),
    };
  }, [t, matches, team, opp]);
  return <EChart option={option} height={height} label="Series score after each match" />;
}

/** Runs added for each wicket; gold = still together at the end. */
export function PartnershipBars({ stands, height = 300 }: { stands: Stand[]; height?: number }) {
  const t = useTheme();
  const option = useMemo<Option>(() => {
    const L = look(t);
    return {
      grid: { left: 34, right: 10, top: 30, bottom: 28 },
      tooltip: { ...L.TT, formatter: (p: { dataIndex: number }) => { const s = stands[p.dataIndex]; return s ? `${s.batter1} & ${s.batter2}: ${s.runs}${s.unbroken ? "*" : ""}` : ""; } },
      xAxis: { type: "category", data: stands.map((s) => ord(s.wicket)), ...L.AX, splitLine: { show: false } },
      yAxis: { ...L.AX, axisLine: { show: false } },
      series: [{ type: "bar", barWidth: "56%", data: stands.map((s) => ({ value: s.runs, itemStyle: { color: s.unbroken ? t.gold : t.led, borderRadius: 0 } })),
        label: { show: true, position: "top", ...L.VAL(18), formatter: (p: { value: number; dataIndex: number }) => p.value + (stands[p.dataIndex]?.unbroken ? "*" : "") } }],
    };
  }, [t, stands]);
  return <EChart option={option} height={height} label="Partnerships" />;
}

/** Every team's rating through the season, the team lit up and named at the end of its line. */
export function EloLines({ elo, team, height = 408 }: { elo: Elo; team: string | null; height?: number }) {
  const t = useTheme();
  const option = useMemo<Option>(() => {
    const L = look(t), top = elo.table[0]?.team, when = dayer(elo.snaps.map((s) => s.date));
    return {
      grid: { left: 44, right: 60, top: 10, bottom: 30 },
      tooltip: { trigger: "axis", ...L.TT },
      xAxis: { type: "category", data: elo.snaps.map((s) => when(s.date)), ...L.AX, splitLine: { show: false } },
      yAxis: { scale: true, ...L.AX, axisLine: { show: false } },
      series: elo.teams.map((x) => ({ type: "line", name: x, step: "end", symbol: "none", data: elo.snaps.map((s) => s.elo[x]), z: x === team ? 5 : 1,
        lineStyle: { width: x === team ? 4 : 1.5, color: x === team ? L.MINE : alpha(t.blue, 0.45), ...(x === team ? L.glow(t.led) : {}) },
        endLabel: { show: x === team || x === top, color: x === team ? t.ink : t.dim, fontFamily: "Bebas Neue", fontSize: ts(18), formatter: () => ab(x) } })),
    };
  }, [t, elo, team]);
  return <EChart option={option} height={height} label="Rating through the season" />;
}

/** Every team's rank after each match day. */
export function RankRace({ elo, team, height = 360 }: { elo: Elo; team: string | null; height?: number }) {
  const t = useTheme();
  const option = useMemo<Option>(() => {
    const L = look(t), when = dayer(elo.snaps.map((s) => s.date));
    return {
      grid: { left: 16, right: 60, top: 10, bottom: 30 },
      xAxis: { type: "category", data: elo.snaps.map((s) => when(s.date)), ...L.AX, splitLine: { show: false } },
      yAxis: { inverse: true, min: 1, max: Math.max(elo.teams.length, 2), interval: 1, splitLine: { show: false }, axisLabel: { show: false } },
      series: elo.teams.map((x) => ({ type: "line", name: x, smooth: 0.3, symbolSize: x === team ? 8 : 0, data: elo.snaps.map((s) => s.rank[x]),
        lineStyle: { width: x === team ? 5 : 1.5, color: x === team ? L.MINE : t.other }, itemStyle: { color: x === team ? L.MINE : t.other },
        z: x === team ? 5 : 1,
        endLabel: { show: true, color: x === team ? t.ink : t.dim, fontFamily: "Bebas Neue", fontSize: x === team ? 18 : ts(14), formatter: () => ab(x) } })),
    };
  }, [t, elo, team]);
  return <EChart option={option} height={height} label="Every team's rank after each match day" />;
}

/** Every match by its margin: wins above the line, defeats below (runs, or wickets x 10 for chases). */
export function MarginBars({ results, height = 276 }: { results: Result[]; height?: number }) {
  const t = useTheme();
  const option = useMemo<Option>(() => {
    const L = look(t), all = [...results].reverse();
    const margin = (r: Result) => {
      const m = /by (?:an innings and )?(\d+) (runs?|wickets?)/.exec(r.result);
      return m ? Number(m[1]) * (m[2]?.startsWith("wicket") ? 10 : 1) : 0;
    };
    return {
      grid: { left: 40, right: 8, top: 10, bottom: 30 },
      tooltip: { ...L.TT, formatter: (p: { dataIndex: number }) => { const r = all[p.dataIndex]; return r ? `${day(r.date)} v ${r.opp}: ${r.result}` : ""; } },
      xAxis: { type: "category", data: all.map((r) => ab(r.opp)), ...L.AX, splitLine: { show: false } },
      yAxis: { ...L.AX, axisLine: { show: false } },
      series: [{ type: "bar", barWidth: "64%", data: all.map((r) => ({ value: (r.outcome === "W" ? 1 : r.outcome === "L" ? -1 : 0) * Math.min(margin(r), 200),
        itemStyle: { color: r.outcome === "W" ? t.win : t.loss, borderRadius: 0 } })) }],
    };
  }, [t, results]);
  return <EChart option={option} height={height} label="Every match by margin" />;
}
