// The Competitions page's own pieces: the title race (each side's chance after every match day) and the knockout
// bracket (a column a round, a card a match, the side that went through lit).
import { useMemo } from "react";
import { Link } from "react-router";
import type { KoCard, OddsLine } from "../api";
import { ab } from "../format";
import { useTheme } from "../theme";
import { alpha } from "./charts";
import { EChart, type Option } from "./EChart";
import { look, ts } from "./look";

export function OddsRace({ lines, team, what, height = 380 }: { lines: OddsLine[]; team: string; what: string; height?: number }) {
  const t = useTheme();
  const option = useMemo<Option>(() => {
    const L = look(t), mine = lines.find((l) => l.team === team);
    // the names at the end of the lines: the picked side, then the leaders, each only where it has room (once a season is
    // decided every other side ends on 0%, and their names would sit on top of each other); the rest show on hover
    const end = (l: (typeof lines)[number]) => l.points[l.points.length - 1]?.chance ?? 0;
    const named: number[] = mine ? [end(mine)] : [];
    const label = new Set<string>(mine ? [team] : []);
    for (const l of [...lines].sort((a, b) => end(b) - end(a))) {
      if (label.has(l.team) || label.size >= 5) continue;
      if (named.every((y) => Math.abs(y - end(l)) >= 8)) { label.add(l.team); named.push(end(l)); }
    }
    const order = [...lines.filter((l) => l.team !== team), ...(mine ? [mine] : [])];
    return {
      grid: { left: 64, right: 120, top: 16, bottom: 40 },
      tooltip: { ...L.TT, trigger: "item", formatter: (p: { seriesName: string; data: [string, number] }) =>
        `${p.seriesName}: ${p.data[1]}% for ${what} after ${p.data[0]}` },
      xAxis: { type: "time", ...L.AX, splitLine: { show: false } },
      yAxis: { type: "value", min: 0, max: 100, interval: 25, name: "Chance %", nameLocation: "middle", nameRotate: 90, nameGap: 40, ...L.AX,
        nameTextStyle: { color: t.dim, fontFamily: "Inter", fontSize: ts(11) } },
      series: order.map((l) => {
        const me = l.team === team;
        return { name: l.team, type: "line", z: me ? 5 : 2, symbolSize: me ? 8 : 4, smooth: false,
          lineStyle: { width: me ? 4 : 2, color: me ? L.MINE : alpha(t.dim, 0.5), ...(me ? L.glow(alpha(t.led, 0.6)) : {}) },
          itemStyle: { color: me ? L.MINE : alpha(t.dim, 0.7) },
          data: l.points.map((p) => [p.date, p.chance]),
          endLabel: { show: label.has(l.team), formatter: ab(l.team), color: me ? t.led : t.dim, fontFamily: "Bebas Neue", fontSize: ts(me ? 15 : 12) } };
      }),
    };
  }, [t, lines, team, what]);
  if (!lines.length) return null;
  return <EChart option={option} height={height} label="Title race" />;
}

export function Bracket({ rounds, keep }: { rounds: { round: string; cards: KoCard[] }[]; keep: string }) {
  return (
    <div className="ko">{rounds.map((r) => (
      <div key={r.round} className="ko-col"><div className="ko-round">{r.round}</div>
        <div className="ko-cards">{r.cards.map((c) => (
          <Link key={c.id} className="ko-card" to={`/matches/${c.id}${keep}`}>
            <div className="ko-date">{c.date}</div>
            {c.teams.map((x) => <div key={x.team} className={`ko-team${x.won ? " win" : ""}`}><span>{x.team}</span><b>{x.score}</b></div>)}
            <div className="ko-res">{c.result}</div>
          </Link>))}</div>
      </div>))}</div>
  );
}
