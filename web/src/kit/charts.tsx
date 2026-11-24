// The chart pieces, exactly as on the approved mock-up (idea 4: idea 1's charts in idea 2's look), drawn from the
// engine's numbers. Heights are the mock-up's with the approved 20% extra room for the bigger words.
import { useEffect, useMemo, useRef, useState, type RefObject } from "react";
import type { Banner, Bar, Elo, Form, Result, Stand, Strength } from "../api";
import { ab, day, dayer, fmtOf, ord, rnd } from "../format";
import { useTheme } from "../theme";
import { EChart, type Option } from "./EChart";
import { look, NUMF, sc, ts } from "./look";

export const alpha = (hex: string, a: number) => {
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
      series: [{ type: "bar", barWidth: "60%", data: innings.map((i) => ({ value: i.runs, itemStyle: { color: col(i.runs), borderRadius: 0 },
          ...(innings.length > 16 ? { label: { show: i.runs >= 50 } } : {}) })),
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

/** Where the team ranks in each section: a track for every team, the team's place on it. */
export function RankTrack({ banner, height = 276 }: { banner: Banner[]; height?: number }) {
  const t = useTheme();
  const option = useMemo<Option>(() => {
    const L = look(t), rows = banner.filter((b) => b.rank != null);
    return {
      grid: { left: 70, right: 30, top: 10, bottom: 30 },
      // every place up to 12 teams; with more, every 2nd (or 3rd...) place, so the labels never touch
      xAxis: { type: "value", min: 1, interval: Math.max(1, Math.ceil(Math.max(...rows.map((b) => b.teams), 1) / 12)), inverse: true, ...L.AX,
        axisLabel: { ...L.AX.axisLabel, formatter: (v: number) => ord(v) } },
      yAxis: { type: "category", data: rows.map((b) => (b.section.length > 12 ? fmtOf(b.section) : b.section)), axisLine: { show: false }, axisTick: { show: false },
        axisLabel: { color: t.ink, fontFamily: "Bebas Neue", fontSize: ts(22) } },
      series: [
        { type: "bar", barWidth: 10, data: rows.map((b) => b.teams), itemStyle: { color: t.track, borderRadius: 5 }, barGap: "-100%", silent: true },
        { type: "scatter", symbolSize: 36, data: rows.map((b) => b.rank), itemStyle: { color: L.MINE, borderColor: t.dark ? "#fff" : t.ink, borderWidth: 2 },
          label: { show: true, ...L.VAL(17), color: t.led_ink, formatter: (p: { value: number }) => p.value } }],
    };
  }, [t, banner]);
  return <EChart option={option} height={height} label="Where the team ranks" />;
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
      grid: { left: 40, right: 60, top: 10, bottom: 30 },   // the first date is centred on the first match day
      xAxis: { type: "category", data: elo.snaps.map((s) => when(s.date)), ...L.AX, splitLine: { show: false } },
      yAxis: { inverse: true, min: 1, max: Math.max(elo.teams.length, 2), interval: 1, splitLine: { show: false }, axisLabel: { show: false } },
      series: elo.teams.map((x) => ({ type: "line", name: x, smooth: 0.3, symbolSize: x === team ? 8 : 0, data: elo.snaps.map((s) => s.rank[x]),
        lineStyle: { width: x === team ? 5 : 1.5, color: x === team ? L.MINE : t.other }, itemStyle: { color: x === team ? L.MINE : t.other },
        z: x === team ? 5 : 1,
        endLabel: { show: elo.teams.length <= 12 || x === team || x === elo.table[0]?.team || x === elo.table[elo.table.length - 1]?.team,
          color: x === team ? t.ink : t.dim, fontFamily: "Bebas Neue", fontSize: x === team ? 18 : ts(14), formatter: () => ab(x) } })),
    };
  }, [t, elo, team]);
  return <EChart option={option} height={height} label="Every team's rank after each match day" />;
}

/** The width of a chart's box, kept up to date (for pieces that place their own labels). */
function useWidth(): [RefObject<HTMLDivElement | null>, number] {
  const box = useRef<HTMLDivElement>(null);
  const [w, setW] = useState(0);
  useEffect(() => {
    if (!box.current) return;
    const ro = new ResizeObserver(() => setW(Math.round(box.current?.getBoundingClientRect().width ?? 0)));
    ro.observe(box.current);
    return () => ro.disconnect();
  }, []);
  return [box, w];
}

/** A ring with its list beside it (no words on the ring): each part with its number, its share and a bar. In a
 *  narrow tile the list goes under the ring. */
export function RingList({ items, centre, sub }: { items: [string, number, string][]; centre: string; sub: string }) {
  const t = useTheme();
  const shown = items.filter(([, v]) => v > 0), tot = shown.reduce((a, [, v]) => a + v, 0);
  const option = useMemo<Option>(() => ({
    title: { text: centre, subtext: sub, left: "center", top: "center", itemGap: 0,
      textStyle: { color: t.led, fontFamily: NUMF, fontWeight: 700, fontSize: 32 }, subtextStyle: { color: t.dim, fontFamily: "Bebas Neue", fontSize: 16 } },
    tooltip: { ...look(t).TT, formatter: "{b}: {c} ({d}%)" },
    series: [{ type: "pie", radius: ["62%", "92%"], padAngle: 3, label: { show: false }, labelLine: { show: false },
      itemStyle: { borderRadius: 0, borderColor: "transparent", borderWidth: 0 },
      data: items.filter(([, v]) => v > 0).map(([n, v, c]) => ({ name: n, value: v, itemStyle: { color: c } })) }],
  }), [t, items, centre, sub]);
  return (
    <div className="dlw" data-chart><div className="dl"><div className="dl-ring"><EChart option={option} height={180} label={`${centre} ${sub}`} /></div>
      <div className="dl-list">{shown.map(([n, v, c]) => (
        <div className="dl-row" key={n}><i style={{ background: c }} /><span className="pn" style={{ fontSize: ts(15) }}>{n}</span>
          <span className="v"><b>{v}</b><small>{rnd((v / tot) * 100)}%</small></span>
          <div className="dl-bar"><span style={{ width: `${(v / tot) * 100}%`, background: c }} /></div></div>))}</div></div></div>
  );
}

/** The form line: the share of the last five matches won (the server's numbers), on its own scale, with every result
 *  as a lamp under it and each series marked over its matches. The first five are dashed until there are five to
 *  count; hot (60%+) and cold (under 40%) zones; dots for now, the best and the worst. `big`: the full chart with its
 *  dates, labels and legend; otherwise the small one for a tile. */
export function FormLine({ results, form, big = false, height }: { results: Result[]; form: Form; big?: boolean; height?: number }) {
  const t = useTheme();
  const [box, width] = useWidth();
  const option = useMemo<Option>(() => {
    const L = look(t), N = form.n, w = form.pct, n = results.length, now = n - 1, ready = (i: number) => i >= N - 1;
    const early = w.map((v, i) => (i <= N - 1 ? v : null)), solid = w.map((v, i) => (ready(i) ? v : null));
    const mk = (i: number, word: string) => ({ coord: [i, w[i]], symbol: "circle", symbolSize: big ? 12 : 7,
      itemStyle: { color: t.ink, borderColor: t.led, borderWidth: big ? 3 : 2 },
      label: { show: big, position: i === now ? "right" : "top", formatter: `${word} ${w[i]}%`, color: t.ink, fontFamily: "Inter", fontWeight: 600, fontSize: 13, distance: 8 } });
    const marks = [];
    if (ready(now) && w[now] != null) marks.push(mk(now, "now"));
    if (form.best != null && form.best !== now) marks.push(mk(form.best, "best"));
    if (form.worst != null && form.worst !== now && form.worst !== form.best) marks.push(mk(form.worst, "worst"));
    const cats = results.map((r) => `${ab(r.opp)}\n${day(r.date)}`), side = big ? { left: 60, right: 128 } : { left: 6, right: 6 };
    const lamp = (o: string) => (o === "W" ? t.win : o === "L" ? t.loss : t.grey);
    const word = (g: Form["groups"][number]) => `v ${ab(g.opp)} · ${g.won > g.lost ? "won" : g.won < g.lost ? "lost" : "drew"} ${g.won}–${g.lost}`;
    // a series' name only where it has room: left to right, one that would touch the name before it is left off
    // (its bar stays; many one-match series in a season would otherwise run into each other)
    const slot = (Math.max(width, 300) - side.left - side.right) / Math.max(n, 1);
    let edge = -Infinity;
    const named = form.groups.map((g) => {
      const mid = ((g.start + g.end + 1) / 2) * slot, half = (word(g).length * 17 * 0.5) / 2;
      if (mid - half < edge + 10 || mid - half < -side.left || mid + half > slot * n + side.right) return false;
      edge = mid + half;
      return true;
    });
    return {
      grid: [{ ...side, top: big ? 30 : 6, height: big ? 250 : 54 }, { ...side, top: big ? 336 : 66, height: big ? 70 : 16 }],
      tooltip: { ...L.TT, trigger: "item", formatter: (p: { dataIndex: number; seriesType: string }) => {
        const r = results[p.dataIndex];
        return r ? `${day(r.date)} v ${r.opp}: ${r.result}${w[p.dataIndex] != null ? ` · last five ${w[p.dataIndex]}% won` : ""}` : ""; } },
      xAxis: [{ type: "category", data: cats, gridIndex: 0, show: false },
        { type: "category", data: cats, gridIndex: 1, show: big, ...L.AX, axisLine: { show: false }, splitLine: { show: false },
          axisLabel: { ...L.AX.axisLabel, fontSize: 12, margin: 8, ...(n <= 16 ? { interval: 0 } : { hideOverlap: true }) } },
        { type: "value", min: -0.5, max: n - 0.5, gridIndex: 1, show: false }],
      yAxis: [{ type: "value", min: 0, max: 100, interval: 20, gridIndex: 0, show: big, ...L.AX, axisLabel: { ...L.AX.axisLabel, formatter: (v: number) => `${v}%` } },
        { type: "value", min: 0, max: 1, gridIndex: 1, show: false }],
      series: [
        { type: "line", xAxisIndex: 0, yAxisIndex: 0, data: early, smooth: 0.3, symbol: "none", z: 2, silent: true,
          lineStyle: { color: t.dim, width: big ? 3 : 2, type: "dashed" },
          markArea: big ? { silent: true, itemStyle: { color: alpha(t.ink, 0.04) }, label: { show: true, position: "insideTop", formatter: "THE FIRST FIVE: BUILDING UP",
            color: t.dim, fontFamily: "Bebas Neue", fontSize: 16, distance: 6 }, data: [[{ xAxis: 0 }, { xAxis: Math.min(N - 1, n - 1) }]] } : undefined },
        { type: "line", xAxisIndex: 0, yAxisIndex: 0, data: solid, smooth: 0.3, symbol: "none", z: 3, silent: true, lineStyle: { color: t.led, width: big ? 4 : 3 },
          markArea: { silent: true, data: [
            [{ yAxis: 60, itemStyle: { color: alpha(t.win, 0.1) }, label: { show: big, position: "insideTopRight", formatter: "HOT · 60%+", color: t.win, fontFamily: "Bebas Neue", fontSize: 18 } }, { yAxis: 100 }],
            [{ yAxis: 0, itemStyle: { color: alpha(t.loss, 0.1) }, label: { show: big, position: "insideBottomRight", formatter: "COLD · UNDER 40%", color: t.loss, fontFamily: "Bebas Neue", fontSize: 18 } }, { yAxis: 40 }]] },
          markPoint: { silent: true, data: marks } },
        { type: "scatter", xAxisIndex: 2, yAxisIndex: 1, symbolSize: big ? 28 : 10, z: 4,
          data: results.map((r, i) => ({ value: [i, big ? 0.32 : 0.5], itemStyle: { color: lamp(r.outcome) } })),
          label: { show: big, formatter: (p: { dataIndex: number }) => results[p.dataIndex]?.outcome ?? "", color: "#0b1b3d", fontFamily: "Inter", fontWeight: 700, fontSize: 12 },
          markArea: big ? { silent: true, data: form.groups.map((g, k) => { const col = g.won > g.lost ? t.win : g.won < g.lost ? t.loss : t.grey;
            return [{ coord: [g.start - 0.42, 0.86], itemStyle: { color: col }, label: { show: named[k], position: "top", formatter: word(g), color: col, fontFamily: "Bebas Neue", fontSize: 17, distance: 3 } },
              { coord: [g.end + 0.42, 0.93] }]; }) } : undefined },
      ],
    };
  }, [t, results, form, big, width]);
  return <div ref={box}><EChart option={option} height={height ?? (big ? 470 : 90)} label="Form line" /></div>;
}

/** The series as a tug of war: above the line the team leads, below it the other side does; the score after every
 *  match. */
export function TugOfWar({ matches, progress, team, opp, height = 380 }: {
  matches: Result[]; progress: { won: number; lost: number }[]; team: string; opp: string; height?: number;
}) {
  const t = useTheme();
  const option = useMemo<Option>(() => {
    const L = look(t);
    const pts = [{ x: "Start", v: 0, s: "0–0" }].concat(matches.map((r, i) => {
      const p = progress[i] ?? { won: 0, lost: 0 };
      return { x: `${fmtOf(r.section)} ${r.no ?? i + 1}`, v: p.won - p.lost, s: `${p.won}–${p.lost}` };
    }));
    const top = Math.max(2, ...pts.map((p) => Math.abs(p.v)));
    const side = (sign: number) => pts.map((p, i) => (p.v * sign > 0 || (p.v === 0 && ((pts[i - 1]?.v ?? 0) * sign > 0 || (pts[i + 1]?.v ?? 0) * sign > 0)) ? p.v : null));
    return {
      grid: { left: 10, right: 40, top: 58, bottom: 30 },   // the axis labels are kept inside by the fit rules (EChart)
      xAxis: { type: "category", data: pts.map((p) => p.x), boundaryGap: false, ...L.AX, splitLine: { show: true, lineStyle: { color: t.split } } },
      yAxis: { type: "value", min: -top, max: top, interval: 1, ...L.AX, axisLabel: { ...L.AX.axisLabel, fontFamily: "Bebas Neue", fontSize: ts(14), margin: 22,
        formatter: (v: number) => (v > 0 ? `${ab(team)} +${v}` : v < 0 ? `${ab(opp)} +${-v}` : "LEVEL") }, splitLine: { lineStyle: { color: t.split } } },
      series: [
        { type: "line", data: side(1), symbol: "none", silent: true, lineStyle: { width: 4, color: t.led }, areaStyle: { color: alpha(t.led, 0.22), origin: 0 }, z: 2 },
        { type: "line", data: side(-1), symbol: "none", silent: true, lineStyle: { width: 4, color: t.blue }, areaStyle: { color: alpha(t.blue, 0.22), origin: 0 }, z: 2,
          markLine: { silent: true, symbol: "none", lineStyle: { color: t.ink, width: 2 }, data: [{ yAxis: 0 }], label: { show: false } } },
        { type: "line", lineStyle: { opacity: 0 }, symbolSize: 14, z: 3,
          data: pts.map((p) => ({ value: p.v, itemStyle: { color: t.ink, borderWidth: 3, borderColor: p.v > 0 ? t.led : p.v < 0 ? t.blue : t.dim },
            label: { color: p.v > 0 ? t.led : p.v < 0 ? t.blue : t.ink } })),
          label: { show: true, position: "top", distance: 10, ...L.VAL(19), formatter: (p: { dataIndex: number }) => pts[p.dataIndex]?.s ?? "" } },
      ],
    };
  }, [t, matches, progress, team, opp]);
  return <EChart option={option} height={height} label="The series score after each match" />;
}

/** Every match placed by how the two sides were rated just before it (theirs minus ours), one row per format; dots
 *  that would touch move up or down within their row, so every match can be seen. */
export function StrengthDots({ rows, lanes, height = 360, who }: { rows: Strength[]; lanes: string[]; height?: number; who?: string }) {
  const t = useTheme();
  const [box, w] = useWidth();
  const option = useMemo<Option>(() => {
    const L = look(t), G = { left: 70, right: 30, top: 14, bottom: 56 };
    const widest = Math.max(...rows.map((x) => Math.abs(x.gap)), 10);
    const step = [20, 25, 50, 100, 200, 250, 500].find((k) => (2 * Math.ceil(widest / k) * k) / k <= 10) ?? 1000;
    const gapMax = Math.ceil(widest / step) * step;
    const xs = (Math.max(w, 300) - G.left - G.right) / (2 * gapMax), ys = (height - G.top - G.bottom) / Math.max(lanes.length, 1);
    const placed: { x: number; y: number }[] = [], spots = [0, 0.21, -0.21, 0.42, -0.42];
    const dist = (a: { x: number; y: number }, b: { x: number; y: number }) => Math.hypot((a.x - b.x) * xs, (a.y - b.y) * ys);
    const pts = [...rows].sort((a, b) => a.gap - b.gap).map((x) => {
      const y0 = lanes.indexOf(x.section), tries = spots.map((o) => ({ x: x.gap, y: y0 + o }));
      const room = (p: { x: number; y: number }) => Math.min(Infinity, ...placed.map((q) => dist(q, p)));
      const at = tries.find((p) => room(p) >= 20) ?? tries.reduce((a, b) => (room(b) > room(a) ? b : a));   // 18px dots, 2px apart
      placed.push(at);
      return { value: [at.x, at.y], name: `${day(x.date)} v ${x.opp}`, gap: x.gap, match: x.id,
        itemStyle: { color: x.outcome === "W" ? t.win : x.outcome === "L" ? t.loss : t.grey, borderColor: t.tile, borderWidth: 2 } };
    });
    return {
      grid: G,
      tooltip: { ...L.TT, formatter: (p: { data: { name: string; gap: number } }) => `${p.data.name}: rated ${p.data.gap > 0 ? `${p.data.gap} above ${who ?? "you"}` : p.data.gap < 0 ? `${-p.data.gap} below ${who ?? "you"}` : "level"}` },
      xAxis: { type: "value", ...L.AX, min: -gapMax, max: gapMax, interval: step, name: who ? `← rated below ${who}   ·   their rating minus ${who}'s   ·   above ${who} →` : "← rated below you   ·   their rating minus yours   ·   above you →",
        nameLocation: "middle", nameGap: 34, nameTextStyle: { color: t.dim, fontFamily: "Inter", fontSize: 13 }, splitLine: { lineStyle: { color: t.split } } },
      // the dots sit on a value axis; the format names come from a category axis whose rows line up with it
      yAxis: [{ type: "value", min: -0.5, max: lanes.length - 0.5, show: false },
        { type: "category", data: lanes.map(fmtOf), position: "left", ...L.AX, splitLine: { show: false }, axisLabel: { color: t.ink, fontFamily: "Bebas Neue", fontSize: ts(15) } }],
      series: [{ type: "scatter", symbolSize: 18, data: pts,
        markLine: { silent: true, symbol: "none", lineStyle: { color: t.ink, width: 2 }, data: [{ xAxis: 0 }], label: { show: false } } }],
    };
  }, [t, rows, lanes, height, w, who]);
  return <div ref={box}><EChart option={option} height={height} label="Against stronger and weaker sides" /></div>;
}

/** A share of a whole as a donut with its list (RingList), each slice in the site's share colours: `count` is what
 *  each slice is made of (runs, dismissals), `centre` the whole. */
export function ShareRing({ rows, count, centre, sub }: { rows: Bar[]; count: (r: Bar) => number; centre: string; sub: string }) {
  const t = useTheme(), pal = [t.led, t.warm, t.cream, t.win, t.blue, t.grey];
  return <RingList items={rows.map((r, i) => [r.label, count(r), pal[i % pal.length]!] as [string, number, string])} centre={centre} sub={sub} />;
}
