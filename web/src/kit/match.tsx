// The Matches section's pieces: the win chance through a match, wicket by wicket, the excitement rating, the best
// games, and your notes on a match.
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link } from "react-router";
import { post, type BestGame, type Excitement, type WinChance, type Wickets } from "../api";
import { ab, dayY, f1, ord } from "../format";
import { useTheme } from "../theme";
import { Logo, Name, Num } from "./base";
import { alpha } from "./charts";
import { EChart, type Option } from "./EChart";
import { look, ts } from "./look";

/** The chance for the side batting first at the start of each innings and after every wicket, ending at the result:
 *  one line in one-day cricket (50% dashed), won / drawn / lost stacked in a game over several days. */
export function WinChanceChart({ win, mine, height = 330 }: { win: WinChance; mine: string[]; height?: number }) {
  const t = useTheme();
  const option = useMemo<Option>(() => {
    const L = look(t), pts = win.points, x = pts.map((_, i) => String(i));
    // your team in gold (the other side blue); with neither of yours playing, the side batting first in gold
    const first = !mine.includes(win.team2) || mine.includes(win.team1), c1 = first ? t.led : t.blue, c2 = first ? t.blue : t.led;
    const tip = (i: number, what: string, v: number | null) => {
      const p = pts[i];
      return p ? `${p.label}<br/><b>${v == null ? "–" : Math.round(v)}%</b> ${what} <span style="opacity:.7">(${p.note})</span>` : "";
    };
    const starts = { silent: true, symbol: "none", lineStyle: { color: t.dim, type: "dotted", width: 1.5 }, label: { show: false },
      data: win.starts.map((s) => ({ xAxis: String(s) })) };
    const common = { grid: { left: 52, right: 18, top: win.multi ? 44 : 20, bottom: 26 },
      xAxis: { type: "category", data: x, boundaryGap: false, axisLabel: { show: false }, axisLine: { lineStyle: { color: t.edge } }, axisTick: { show: false } },
      yAxis: { type: "value", min: 0, max: 100, interval: 25, ...L.AX, axisLine: { show: false },
        axisLabel: { ...L.AX.axisLabel, formatter: (v: number) => `${v}%` } } };
    if (!win.multi) return {
      ...common,
      tooltip: { ...L.TT, trigger: "axis", formatter: (ps: { dataIndex: number; value: number }[]) => tip(ps[0]?.dataIndex ?? 0, `for ${win.team1}`, ps[0]?.value ?? null) },
      series: [{ type: "line", data: pts.map((p) => p.W), symbol: "circle", symbolSize: 7, smooth: 0.15,
        lineStyle: { color: c1, width: 3.5 }, itemStyle: { color: c1 },
        areaStyle: { color: { type: "linear", x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: alpha(c1, 0.28) }, { offset: 1, color: alpha(c1, 0) }] } },
        markLine: { ...starts, data: [...starts.data, { yAxis: 50, lineStyle: { color: t.dim, type: "dashed", width: 1 } }] } }],
    };
    const band = (key: "W" | "D" | "L", name: string, colour: string) => ({ type: "line", name, stack: "all", data: pts.map((p) => p[key]),
      symbol: "none", smooth: 0.15, lineStyle: { width: 0 }, itemStyle: { color: colour }, areaStyle: { color: colour, opacity: 0.9 } });
    return {
      ...common,
      legend: { top: 0, left: 0, textStyle: { color: t.ink, fontFamily: "Bebas Neue", fontSize: ts(15) }, itemWidth: 18, itemHeight: 12 },
      tooltip: { ...L.TT, trigger: "axis", formatter: (ps: { dataIndex: number; seriesName: string; value: number }[]) => {
        const i = ps[0]?.dataIndex ?? 0, p = pts[i];
        return p ? `${p.label}<br/>${ps.map((s) => `${s.seriesName}: <b>${s.value == null ? "–" : Math.round(s.value)}%</b>`).join("<br/>")}<br/><span style="opacity:.7">${p.note}</span>` : ""; } },
      series: [{ ...band("W", `${win.team1} win`, c1), markLine: starts }, band("D", "Draw", t.grey), band("L", `${win.team2} win`, c2)],
    };
  }, [t, win, mine]);
  return <EChart option={option} height={height} label="Win chance through the match" />;
}

/** One innings wicket by wicket: a bar climbing from the score when each stand began to the score at the fall (its
 *  height is the stand), the stand still unbroken at the end in gold, and the par score at each wicket dashed. */
export function WicketClimb({ inn, par, height = 330 }: { inn: Wickets["innings"][number]; par: Wickets["par"]; height?: number }) {
  const t = useTheme();
  const option = useMemo<Option>(() => {
    const L = look(t), st = inn.steps, cats = st.map((s) => (s.unbroken ? "end" : `${s.wicket}`));
    const who = (s: (typeof st)[number]) => (s.batters.length ? `${s.batters[0]} & ${s.batters[1]}` : "the stand");
    const parAt = new Map((par ?? []).map((p) => [p.wicket, p.par]));
    const top = Math.max(...st.map((s) => s.score), ...(par ?? []).map((p) => p.par), 10);
    return {
      grid: { left: 40, right: 12, top: 34, bottom: 30 },
      tooltip: { ...L.TT, trigger: "axis", axisPointer: { type: "shadow" }, formatter: (ps: { dataIndex: number }[]) => {
        const s = st[ps[0]?.dataIndex ?? 0];
        if (!s) return "";
        const head = s.unbroken ? `${s.score}* at the end: ${who(s)} added ${s.stand}, unbroken` : `${s.wicket}-${s.score}: ${who(s)} added ${s.stand}`;
        const p = parAt.get(s.wicket);
        return head + (p != null && !s.unbroken ? `<br/><span style="opacity:.7">par at the ${ord(s.wicket)} wicket: ${Math.round(p)}</span>` : ""); } },
      xAxis: { type: "category", data: cats, ...L.AX, splitLine: { show: false }, axisLabel: { ...L.AX.axisLabel, fontSize: ts(11) } },
      yAxis: { type: "value", max: Math.ceil((top * 1.12) / 10) * 10, ...L.AX, axisLine: { show: false } },
      series: [
        { type: "bar", stack: "c", silent: true, itemStyle: { color: "transparent" }, data: st.map((s) => s.start), barWidth: "62%" },
        { type: "bar", stack: "c", data: st.map((s) => ({ value: s.stand, itemStyle: { color: s.unbroken ? t.gold : s.stand >= 50 ? t.win : t.led, borderRadius: 0 } })),
          label: { show: true, position: "top", ...L.VAL(16), formatter: (p: { dataIndex: number }) => { const s = st[p.dataIndex]; return s ? `${s.score}${s.unbroken ? "*" : ""}` : ""; } } },
        ...(par?.length ? [{ type: "line", name: "Par", data: st.map((s) => (s.unbroken ? null : parAt.get(s.wicket) ?? null)), symbol: "none", z: 5,
          lineStyle: { color: t.dim, type: "dashed", width: 2 }, connectNulls: false, silent: true }] : []),
      ],
    };
  }, [t, inn, par]);
  return <EChart option={option} height={height} label={`${inn.label} wicket by wicket`} />;
}

/** The excitement rating: the number out of 10, where it ranks, its four parts and the reasons. */
export function ExcitementPanel({ ex, section }: { ex: Excitement; section: string }) {
  const parts: [string, number, number][] = [["The finish", ex.finish, 7], ["A comeback", ex.comeback, 2], ["The stakes", ex.stakes, 1], ["Big moments", ex.show, 0.5]];
  return (
    <div className="exc">
      <div className="exc-n"><Num v={f1(ex.rating)} px={64} /><span className="of">/ 10</span>
        <div className="s"><b>{ord(ex.rank)}</b> of {ex.of} in {section}</div></div>
      <div className="exc-parts">{parts.map(([k, v, max]) => (
        <div className="pbar small" key={k}><span className="k2">{k}</span>
          <span className="tr2"><span className="fill" style={{ width: `${Math.min(100, (v / max) * 100)}%` }} /></span>
          <span className="v"><b>{f1(v)}</b><small> / {max}</small></span></div>))}</div>
      {ex.why && <div className="note" style={{ gridColumn: "1 / -1" }}>Why: {ex.why}.</div>}
    </div>
  );
}

/** The best games: the rating, the match with both badges, when, and why. */
export function BestTable({ rows, showSection, keep }: { rows: BestGame[]; showSection: boolean; keep: string }) {
  return (
    <table className="c best"><thead><tr><th className="r">Rating</th><th>Match</th><th>When</th><th>Why</th></tr></thead>
      <tbody>{rows.map((r) => (
        <tr key={r.id}>
          <td className="r"><Link to={`/matches/${r.id}${keep}`} className="rate">{f1(r.rating)}</Link>
            <div className="how">{ord(r.rank)} of {r.of}</div></td>
          <td><Link to={`/matches/${r.id}${keep}`} className="cell" style={{ textDecoration: "none" }}>
            <Logo team={r.home} size={34} /><Name p={`${ab(r.home)} v ${ab(r.away)}`} px={22} /><Logo team={r.away} size={34} /></Link>
            <div className="how">{r.result}</div></td>
          <td><span className="tn dimn">{dayY(r.date)}</span><div className="how">{showSection ? r.name : r.name === r.section ? "" : r.name}</div></td>
          <td><span className="why">{r.why}</span></td></tr>))}</tbody></table>
  );
}

/** Your note on a match: saved with the career on this PC (the current site shows the same notes). */
export function NoteBox({ mid, note }: { mid: string; note: string }) {
  const qc = useQueryClient();
  const [text, setText] = useState(note);
  const [said, setSaid] = useState("");
  const save = useMutation({
    mutationFn: () => post<{ note: string; saved: boolean }>("/api/notes", { match: mid, text }),
    onSuccess: (r) => { setSaid(r.saved ? "Note saved" : "Note removed"); void qc.invalidateQueries({ queryKey: ["match", mid] }); },
    onError: (e) => setSaid(`Not saved: ${String(e)}`),
  });
  return (
    <div className="notebox">
      <textarea value={text} onChange={(e) => { setText(e.target.value); setSaid(""); }} rows={4} maxLength={5000}
        placeholder="e.g. rested Bumrah, regretted it · went spin-heavy on a turner" aria-label="Your notes on this match" />
      <div className="field"><button className="btn" onClick={() => save.mutate()} disabled={save.isPending || text.trim() === note.trim()}>Save note</button>
        {said && <span className="saved">📝 {said}</span>}</div>
      <div className="note">Saved with this career on this PC. Your notes also show on My team.</div>
    </div>
  );
}
