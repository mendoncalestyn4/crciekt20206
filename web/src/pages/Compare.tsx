// Compare players (stage 3): up to four side by side (your answer 22: the competition dropdown with tick boxes), every
// stat as its own chart, how each career has built up, and "plays like" (answers 12, 15, 16). Every number comes from
// the server (server/comparepage.py); the page only shows it.
import { useQuery } from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router";
import { get, type ComparePage, remember } from "../api";
import { Drop, Explain, Missing, Pick, Tile, three } from "../kit/base";
import { CareerCurves, CompareBars, pickColours } from "../kit/insights";
import { Grid } from "../kit/teams";
import { T } from "../shell/names";
import { useReady } from "../ready";
import { useShell } from "../shell/Shell";
import { useTheme } from "../theme";
import { PlayersHead } from "./Stories";

const KEYS = ["section", "season", "disc", "players", "like"];

export function Compare() {
  const { career, noCareer, nation } = useShell();
  const t = useTheme();
  const [params] = useSearchParams();
  const go = useNavigate();
  const want = Object.fromEntries(KEYS.map((k) => [k, params.get(k) ?? ""]));
  const qs = KEYS.filter((k) => want[k]).map((k) => `${k}=${encodeURIComponent(want[k]!)}`).join("&");
  const q = useQuery({ queryKey: ["compare", qs, career?.name], enabled: Boolean(career), retry: false,
    queryFn: () => get<ComparePage>(`/api/compare?${qs}`), placeholderData: (was) => was });
  useReady(Boolean(q.data || q.error || noCareer), qs);
  const set = (changes: Record<string, string>) => {
    if (changes.section) remember({ section: changes.section });
    if (changes.season) remember({ season: changes.season });
    const next: Record<string, string> = { ...want, ...changes };
    if ("section" in changes || "season" in changes || "disc" in changes) Object.assign(next, { like: "" });
    if (nation) next.nation = nation;
    go(`/players/compare?${new URLSearchParams(Object.entries(next).filter(([, v]) => v)).toString()}`);
  };
  const head = <PlayersHead on={2} crumb="Compare players · side by side" />;
  if (noCareer) return <>{head}<div className="grid"><Tile span={12} title="No career yet"><div className="plain">Add a career on the current site for now.</div></Tile></div></>;
  if (q.error) return <>{head}<div className="grid"><Tile span={12}><Missing why={String(q.error)} /></Tile></div></>;
  if (!q.data) return <>{head}<div className="empty">Lining them up…</div></>;
  const d = q.data;
  if (!d.choices.length) return <>{head}<div className="grid"><Tile span={12}><Missing why={d.none} /></Tile></div></>;
  const comps = d.choices.map((c) => c.section);
  const note = (x: string) => `${d.choices.find((c) => c.section === x)?.matches ?? ""} matches`;
  const order = d.players ?? [];
  const pal = pickColours(t);
  const add = (p: string) => set({ players: [...order, p].join("|") });
  return (
    <>
      {head}
      <div className="grid">
        <div className="intro">Pick a competition and up to four players. Each chart shows one stat, with the competition's average as a dashed line.</div>
        <Tile span={12} className="pickbar"><div className="drops">
          <Drop label="Competition" all={comps} on={d.ticked ?? []} set={(v) => set({ section: v.join("|"), players: "" })} keepOne note={note} />
          <Pick label="Season" value={d.season ?? ""} options={[{ v: "", label: "All seasons" }, ...(d.seasons ?? [])]} set={(v) => set({ season: v })} />
          <Pick label="Discipline" value={d.disc ?? "Batting"} options={d.discs ?? []} set={(v) => set({ disc: v, players: "" })} />
          {d.names && <Drop label="Players (up to 4)" all={d.names} on={order} set={(v) => set({ players: v.slice(0, 4).join("|") })} keepOne />}
        </div>
        {order.length > 0 && <div className="pickkey">{order.map((p, i) => <span key={p}><i style={{ background: pal[i] }} /><T>{p}</T></span>)}</div>}
        {d.combined && <div className="note">{d.combined}</div>}</Tile>
        {d.few && <Tile span={12}><div className="plain">{d.few}</div></Tile>}

        {d.like && <Tile span={12} title={`Plays like ${d.like.player}`} right={d.like.section}>
          {order.length > 1 && <div className="drops" style={{ marginBottom: 10 }}><Pick label="Find who plays like" value={d.like.player} options={order} set={(v) => set({ like: v })} /></div>}
          {d.like.none ? <div className="plain">{d.like.none}</div> : <>
            {d.like.own && <div className="plain" style={{ marginBottom: 8 }}><T>{d.like.player}</T>: {d.like.own}</div>}
            <div className="likes">{d.like.rows.map((r) => (
              <div key={r.player} className="like">
                <div className="alike">{r.alike}</div>
                <div><T>{r.player}</T> <span className="why">{r.team}</span><div className="note" style={{ marginTop: 2 }}>{r.figures}</div></div>
                {r.picked ? <span className="why">In the comparison</span>
                  : d.like!.full ? <span className="why">Remove one first (four is the most)</span>
                  : <button className="btn quiet sm" onClick={() => add(r.player)}>Add to the comparison</button>}
              </div>))}</div></>}
          <div className="note">{d.like.note}</div></Tile>}

        {d.summary && order.length > 0 && <Tile span={12} title={d.where}><Grid t={{ ...d.summary, dim: [], badges: [] }} /></Tile>}
        {d.charts && order.length > 1 && <div className="glabel" style={{ gridColumn: "span 12" }}>Stat by stat</div>}
        {order.length > 1 && d.charts?.map((c) => (
          <Tile key={c.id} span={6} title={c.label} right={c.better}><CompareBars c={c} order={order} /><Explain {...three(c)} /></Tile>))}
        {d.curves && order.length > 0 && <Tile span={12} title={`Career so far · total ${d.curves.what} after each innings`}>
          <CareerCurves series={d.curves.series} what={d.curves.what} order={order} /><Explain {...three(d.curves)} /></Tile>}
      </div>
    </>
  );
}
