// The Teams page's own pieces: a plain table from the server (names in it open the player menu, a row can open its
// match), bars either side of the average team, and the league race (position after each match day).
import { useMemo } from "react";
import { Link } from "react-router";
import type { Dot, GridT, RaceLine, SignedBar, TapeRow, TeamBarRow } from "../api";
import { ab } from "../format";
import { T } from "../shell/names";
import { useTheme } from "../theme";
import { alpha } from "./charts";
import { EChart, type Option } from "./EChart";
import { look, ts } from "./look";

/** A table as the server sends it: numbers right-aligned, the picked team's rows lit, the first column opening the
 * match when the row is one. */
export function Grid({ t, keep = "" }: { t: GridT; keep?: string }) {
  const num = new Set(t.num);
  return (
    <div className="scrollx"><table className="c"><thead><tr>{t.cols.map((c, i) => <th key={i} className={num.has(i) ? "r" : ""}>{c}</th>)}</tr></thead>
      <tbody>{t.rows.map((r, i) => (
        <tr key={i} className={t.hi[i] ? "me" : t.dim?.[i] ? "dimrow" : ""}>{r.map((v, j) => {
          const text = v == null ? "–" : String(v);
          const link = j === 0 && t.links[i];
          return <td key={j} className={num.has(j) ? "r" : ""}>{num.has(j) ? <span className="tn">{text}</span>
            : link ? <Link className="lk" to={`/matches/${link}${keep}`}>{text}</Link> : <span className="why"><T>{text}</T></span>}</td>;
        })}</tr>))}</tbody></table></div>
  );
}

/** Bars either side of nought: better (blue) or worse (red) than the average team; or, with `colour`, more or less of
 * something that isn't better or worse. Each bar says its own figures. */
export function SignedBars({ rows, colour, height }: { rows: SignedBar[]; colour?: string; height?: number }) {
  const t = useTheme();
  const option = useMemo<Option>(() => {
    const L = look(t), vals = rows.map((r) => r.value);
    // room beyond each bar's end for its label ("+12% · 8.6 v 7.7"), on the side it grows towards
    const lo = Math.min(0, ...vals), hi = Math.max(0, ...vals), pad = Math.max(hi - lo, 10) * 1.35;
    return {
      grid: { left: 6, right: 12, top: 6, bottom: 6, containLabel: true },
      xAxis: { show: false, min: lo - (lo < 0 ? pad : 0), max: hi + pad },
      yAxis: { type: "category", inverse: true, data: rows.map((r) => r.label), axisLine: { show: false }, axisTick: { show: false },
        axisLabel: { color: t.ink, fontFamily: "Bebas Neue", fontSize: ts(14), margin: 10 } },
      tooltip: { ...L.TT, formatter: (p: { dataIndex: number }) => { const r = rows[p.dataIndex]; return r ? `${r.label}: ${r.text}${r.note ? `<br/><span style="opacity:.75">${r.note}</span>` : ""}` : ""; } },
      series: [{ type: "bar", barWidth: "58%",
        data: rows.map((r) => ({ value: r.value, itemStyle: { borderRadius: 0, color: colour ?? (r.value >= 0 ? t.blue : t.loss) },
          label: { position: r.value >= 0 ? "right" : "left" } })),
        label: { show: true, ...L.VAL(13), color: t.ink, formatter: (p: { dataIndex: number }) => rows[p.dataIndex]?.text ?? "" },
        markLine: { silent: true, symbol: "none", label: { show: false }, lineStyle: { color: t.dim, width: 1.5 }, data: [{ xAxis: 0 }] } }],
    };
  }, [t, rows, colour]);
  if (!rows.length) return <div className="empty">Not enough games yet.</div>;
  return <EChart option={option} height={height ?? Math.max(120, 30 + rows.length * 44)} label="Against the average team" />;
}

/** Each team's league position after every match day: the picked team in gold, the rest grey; hover for points. */
export function PositionRace({ lines, team, height = 380 }: { lines: RaceLine[]; team: string; height?: number }) {
  const t = useTheme();
  const option = useMemo<Option>(() => {
    const L = look(t), rounds = Math.max(1, ...lines.flatMap((l) => l.points.map((p) => p.round)));
    const teams = lines.length, mine = lines.find((l) => l.team === team);
    const order = [...lines.filter((l) => l.team !== team), ...(mine ? [mine] : [])];
    return {
      grid: { left: 64, right: 120, top: 16, bottom: 40 },
      tooltip: { ...L.TT, trigger: "item", formatter: (p: { seriesName: string; data: [number, number, number | null, number] }) =>
        `${p.seriesName}: ${p.data[1]} of ${teams} after match day ${p.data[0]}${p.data[2] != null ? ` · ${p.data[2]} points` : ""} · ${p.data[3]} played` },
      xAxis: { type: "value", min: 1, max: rounds, interval: 1, name: "Match day", nameLocation: "middle", nameGap: 26, ...L.AX,
        nameTextStyle: { color: t.dim, fontFamily: "Inter", fontSize: ts(11) }, splitLine: { show: false } },
      yAxis: { type: "value", inverse: true, min: 1, max: teams, interval: 1, name: "Position", nameLocation: "middle", nameRotate: 90, nameGap: 34, ...L.AX,
        nameTextStyle: { color: t.dim, fontFamily: "Inter", fontSize: ts(11) } },
      series: order.map((l) => {
        const me = l.team === team, last = l.points[l.points.length - 1];
        return { name: l.team, type: "line", z: me ? 5 : 2, symbolSize: me ? 9 : 5, smooth: false,
          lineStyle: { width: me ? 4 : 2, color: me ? L.MINE : alpha(t.dim, 0.55), ...(me ? L.glow(alpha(t.led, 0.6)) : {}) },
          itemStyle: { color: me ? L.MINE : alpha(t.dim, 0.7) },
          data: l.points.map((p) => [p.round, p.position, p.points, p.played]),
          endLabel: { show: Boolean(last), formatter: ab(l.team), color: me ? t.led : t.dim, fontFamily: "Bebas Neue", fontSize: ts(me ? 15 : 12) } };
      }),
    };
  }, [t, lines, team]);
  if (!lines.length) return <div className="empty">No table for this one.</div>;
  return <EChart option={option} height={height} label="League race" />;
}

/** The tale of the tape: each measure's two figures pulling apart from the middle, team A left, team B right, the
 * better one solid with a tick (lower is better for runs conceded and economy). */
export function TapeBars({ rows, a, b }: { rows: TapeRow[]; a: string; b: string }) {
  const t = useTheme();
  const option = useMemo<Option>(() => {
    const L = look(t);
    const side = (k: "a" | "b") => rows.map((r) => ({ value: k === "a" ? -Math.abs(r.a) : Math.abs(r.b),
      itemStyle: { borderRadius: 0, color: alpha(k === "a" ? t.led : t.blue, (k === "a" ? r.a_better : r.b_better) ? 1 : 0.4) },
      label: { formatter: k === "a" ? `${r.a_better ? "✓ " : ""}${r.at}` : `${r.bt}${r.b_better ? " ✓" : ""}` } }));
    return {
      legend: { top: 0, textStyle: { color: t.ink, fontFamily: "Inter", fontSize: ts(11) }, data: [a, b] },
      grid: { left: 6, right: 12, top: 34, bottom: 4, containLabel: true },
      xAxis: { show: false, min: -1.75, max: 1.75 },
      yAxis: { type: "category", inverse: true, data: rows.map((r) => r.label), axisLine: { show: false }, axisTick: { show: false },
        axisLabel: { color: t.ink, fontFamily: "Bebas Neue", fontSize: ts(13), margin: 10 } },
      tooltip: { ...L.TT, formatter: (p: { seriesName: string; dataIndex: number }) => { const r = rows[p.dataIndex]; return r ? `${r.label}<br/>${a}: ${r.at}<br/>${b}: ${r.bt}` : ""; } },
      series: (["a", "b"] as const).map((k) => ({ name: k === "a" ? a : b, type: "bar", stack: "tape", barWidth: "56%", itemStyle: { color: k === "a" ? t.led : t.blue },
        data: side(k), label: { show: true, position: k === "a" ? "left" : "right", ...L.VAL(14), color: t.ink } })),
    };
  }, [t, rows, a, b]);
  if (!rows.length) return <div className="empty">Not enough games yet.</div>;
  return <EChart option={option} height={60 + rows.length * 42} label="Tale of the tape" />;
}

/** Two teams' players as dots (team A gold, team B blue), with the competition's average rate as a dashed line and the
 * better side of it shaded; each side's top two named; hover a dot for the player's figures. */
export function TwoScatter({ points, a, slope, x, y }: { points: Dot[]; a: string; slope: number; x: string; y: string }) {
  const t = useTheme();
  const option = useMemo<Option>(() => {
    const L = look(t);
    const nice = (v: number) => { const step = 10 ** Math.floor(Math.log10(Math.max(v, 1))); return Math.ceil(v / step) * step; };
    const xmax = nice(Math.max(1, ...points.map((p) => p.x)) * 1.08), ymax = nice(Math.max(1, ...points.map((p) => p.y)) * 1.15);
    const teams = [...new Set(points.map((p) => p.team))].sort((p, q) => (p === a ? -1 : q === a ? 1 : 0));
    // each side's top two named in a column in the empty top left, highest first, each with a thin line to its dot, so
    // two dots close together never put their names on top of each other
    const named = teams.flatMap((tm) => points.filter((p) => p.team === tm).sort((p, q) => q.y - p.y).slice(0, 2)).sort((p, q) => q.y - p.y);
    const at = (k: number): [number, number] => [xmax * 0.4, ymax * (0.95 - k * 0.08)];
    const ax = (name: string, extra: object) => ({ type: "value", min: 0, name, nameLocation: "middle", ...L.AX,
      nameTextStyle: { color: t.dim, fontFamily: "Inter", fontSize: ts(11) }, ...extra });
    return {
      legend: { top: 0, textStyle: { color: t.ink, fontFamily: "Inter", fontSize: ts(11) }, data: teams },
      grid: { left: 70, right: 20, top: 40, bottom: 46 },
      xAxis: ax(x, { max: xmax, nameGap: 28 }),
      yAxis: ax(y, { max: ymax, nameGap: 54, nameRotate: 90 }),
      tooltip: { ...L.TT, trigger: "item", formatter: (p: { data: { d?: Dot } }) => { const d = p.data?.d; return d ? `<b>${d.player}</b> · ${d.team}<br/>${d.note.join("<br/>")}` : ""; } },
      series: [
        { name: "average", type: "line", silent: true, symbol: "none", data: [[0, 0], [xmax, slope * xmax]],
          lineStyle: { color: t.dim, type: "dashed", width: 1.5 }, areaStyle: { color: alpha(t.win, 0.08), origin: "end" } },
        ...named.map((p, k) => ({ type: "line", silent: true, symbol: "none", z: 1, data: [at(k), [p.x, p.y]],
          lineStyle: { color: p.team === a ? t.led : t.blue, width: 1, opacity: 0.6 } })),
        { type: "scatter", silent: true, symbolSize: 0, z: 5, data: named.map((p, k) => ({ value: at(k),
          label: { show: true, position: "left", formatter: `${p.player} · ${ab(p.team)}`, color: p.team === a ? t.led : t.blue, fontFamily: "Bebas Neue", fontSize: ts(13) } })) },
        ...teams.map((tm) => ({ name: tm, type: "scatter", symbolSize: 13, z: tm === a ? 4 : 3,
          itemStyle: { color: tm === a ? t.led : t.blue, borderColor: t.tile, borderWidth: 2 },
          data: points.filter((p) => p.team === tm).map((p) => ({ value: [p.x, p.y], d: p })) })),
      ],
    };
  }, [t, points, a, slope, x, y]);
  if (!points.length) return <div className="empty">Nothing to show yet.</div>;
  return <EChart option={option} height={440} label={`${y} against ${x.toLowerCase()}`} />;
}

/** Every player of both sides as a bar either side of nought, coloured by team (A gold, B blue). */
export function TeamBars({ rows, a }: { rows: TeamBarRow[]; a: string }) {
  const t = useTheme();
  const option = useMemo<Option>(() => {
    const L = look(t), vals = rows.map((r) => r.value), lo = Math.min(0, ...vals), hi = Math.max(0, ...vals), pad = (hi - lo) * 0.22 || 1;
    return {
      grid: { left: 16, right: 12, top: 4, bottom: 4, containLabel: true },
      xAxis: { show: false, min: lo - (lo < 0 ? pad : 0), max: hi + pad },
      yAxis: { type: "category", inverse: true, data: rows.map((r) => `${r.player} · ${ab(r.team)}`), axisLine: { show: false }, axisTick: { show: false },
        axisLabel: { color: t.ink, fontFamily: "Bebas Neue", fontSize: ts(12), margin: 8 } },
      tooltip: { ...L.TT, formatter: (p: { dataIndex: number }) => { const r = rows[p.dataIndex]; return r ? `<b>${r.player}</b> · ${r.team}<br/>${r.note.join("<br/>")}` : ""; } },
      series: [{ type: "bar", barWidth: "62%",
        data: rows.map((r) => ({ value: r.value, itemStyle: { borderRadius: 0, color: r.team === a ? t.led : t.blue }, label: { position: r.value >= 0 ? "right" : "left" } })),
        label: { show: true, ...L.VAL(12), color: t.ink, formatter: (p: { value: number }) => `${p.value > 0 ? "+" : ""}${(+p.value).toFixed(1)}` },
        markLine: { silent: true, symbol: "none", label: { show: false }, lineStyle: { color: t.dim, width: 1.5 }, data: [{ xAxis: 0 }] } }],
    };
  }, [t, rows, a]);
  if (!rows.length) return <div className="empty">Nothing to show yet.</div>;
  return <EChart option={option} height={Math.max(300, 26 * rows.length + 20)} label="Every player" />;
}

/** A line from the engine with **bold** parts (the current site wrote them as Markdown): bold shown as bold, names
 * opening the player menu. */
export function Md({ s }: { s: string }) {
  return <>{s.split("**").map((part, i) => (i % 2 ? <b key={i}><T>{part}</T></b> : <T key={i}>{part}</T>))}</>;
}
