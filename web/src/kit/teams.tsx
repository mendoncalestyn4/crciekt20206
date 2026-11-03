// The Teams page's own pieces: a plain table from the server (names in it open the player menu, a row can open its
// match), bars either side of the average team, and the league race (position after each match day).
import { useMemo } from "react";
import { Link } from "react-router";
import type { GridT, RaceLine, SignedBar } from "../api";
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
        <tr key={i} className={t.hi[i] ? "me" : ""}>{r.map((v, j) => {
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
