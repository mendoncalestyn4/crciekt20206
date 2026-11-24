// Insights (stage 3): home wins against away wins in every competition, and one measure of scoring season by season.
import { useMemo } from "react";
import type { HomeRow, SeasonChart } from "../api";
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
