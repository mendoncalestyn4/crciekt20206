// Rivalries (stage 2): every pair of teams that have met in a competition, the record between them, and who has done
// best in those games, as the current site's Rivalries page shows it.
import { useQuery } from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router";
import { get, type LeaderRow, type RivalriesPage, remember } from "../api";
import { Explain, FormatTicks, Missing, Pick, PName, Tile } from "../kit/base";
import { Grid } from "../kit/teams";
import { T } from "../shell/names";
import { useReady } from "../ready";
import { Head, useShell } from "../shell/Shell";

import { TEAM_PAGES } from "./Teams";

function Leaders({ rows, value, unit }: { rows: LeaderRow[]; value: string; unit: string }) {
  return (
    <div className="scrollx"><table className="c"><thead><tr><th>Player</th><th>Team</th><th className="r">{unit}</th><th></th></tr></thead>
      <tbody>{rows.map((r) => (
        <tr key={`${r.player}|${r.team}`}><td><PName p={r.player} px={20} /></td><td><span className="why">{r.team}</span></td>
          <td className="r"><span className="tn">{String(r[value])}</span></td><td><span className="why">{r.note}</span></td></tr>))}</tbody></table></div>
  );
}

export function Rivalries() {
  const { career, noCareer, nation } = useShell();
  const [params] = useSearchParams();
  const go = useNavigate();
  const keep = nation ? `?nation=${encodeURIComponent(nation)}` : "";
  const want = { section: params.get("section") ?? "", pick: params.get("pick") ?? "" };
  const qs = Object.entries(want).map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join("&");
  const q = useQuery({ queryKey: ["rivalries", qs, career?.name], enabled: Boolean(career), retry: false,
    queryFn: () => get<RivalriesPage>(`/api/rivalries?${qs}`) });
  useReady(Boolean(q.data || q.error || noCareer), qs);
  const set = (changes: Record<string, string>) => {
    remember(changes);
    const next: Record<string, string> = { ...want, ...changes };
    if ("section" in changes) next.pick = "";
    if (nation) next.nation = nation;
    go(`/teams/rivalries?${new URLSearchParams(Object.entries(next).filter(([, v]) => v)).toString()}`);
  };
  const head = <Head title="Teams" crumb="Rivalries · who has the upper hand" chips={TEAM_PAGES.map((p) => p.label)} on={4}
    onChip={(i) => go(`${TEAM_PAGES[i]!.to}${keep}`)} />;
  if (noCareer) return <>{head}<div className="grid"><Tile span={12} title="No career yet"><div className="plain">Add a career in Settings first.</div></Tile></div></>;
  if (q.error) return <>{head}<div className="grid"><Tile span={12}><Missing why={String(q.error)} /></Tile></div></>;
  if (!q.data) return <>{head}<div className="empty">Finding every rivalry…</div></>;
  const d = q.data, c = d.close, m = c?.missing ?? {};
  return (
    <>
      {head}
      <div className="grid">
        <Tile span={12} title="Pick a competition">
          <div className="plain">Every pair of teams that have met, the record between them, and who has done best in those games. Several
            competitions ticked are counted together.</div>
          <FormatTicks all={d.choices.map((x) => x.section)} on={d.ticked} set={(v) => set({ section: v.join("|") })} />
        </Tile>
        {d.none ? <Tile span={12}><Missing why={d.none} /></Tile> : <>
          {d.table && <Tile span={12} title="The most played rivalries">
            <Grid t={d.table} keep={keep} />{d.table.note && <div className="note">{d.table.note}</div>}</Tile>}
          <Tile span={12} title="One rivalry close up">
            <div className="drops"><Pick label="Rivalry" value={d.pick} options={d.pairs.map((p) => ({ v: p.key, label: p.label }))} set={(v) => set({ pick: v })} /></div>
          </Tile>
          {c && <>
            {c.streak && <Tile span={12} title={`🔥 Streaks · ${c.a} v ${c.b}`}>
              <div className="plain"><b><T>{c.streak.now}</T></b></div><div className="plain"><T>{c.streak.longest}</T></div>
              <div className="note">{c.streak.note}</div></Tile>}
            <Tile span={6} title={`Most runs · ${c.a} v ${c.b}`}>
              {m.runs ? <Missing why={m.runs} /> : c.runs ? <><Leaders rows={c.runs.rows} value="runs" unit="Runs" />
                <Explain shows={c.runs.shows} for_={c.runs.for_} /></> : <Missing why="No runs in these games yet." />}
            </Tile>
            <Tile span={6} title={`Most wickets · ${c.a} v ${c.b}`}>
              {m.wickets ? <Missing why={m.wickets} /> : c.wickets ? <><Leaders rows={c.wickets.rows} value="wickets" unit="Wkts" />
                <Explain shows={c.wickets.shows} for_={c.wickets.for_} /></> : <Missing why="No wickets in these games yet." />}
            </Tile>
            <Tile span={12} title="Every meeting">
              {m.meetings ? <Missing why={m.meetings} /> : c.meetings ? <Grid t={c.meetings} keep={keep} /> : <Missing />}
            </Tile>
          </>}
        </>}
      </div>
    </>
  );
}
