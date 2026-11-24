// Team planner (stage 2): plan your next game, as the current site's Team planner shows it: what you need to qualify,
// a batting order from where each player does best, how to use your bowlers, who's knocking on the door and which
// partnerships work.
import { useQuery } from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router";
import { get, type GridT, type PlannerPage, remember } from "../api";
import { Missing, Pick, Tile } from "../kit/base";
import { Grid } from "../kit/teams";
import { useReady } from "../ready";
import { Head, useShell } from "../shell/Shell";
import { T } from "../shell/names";
import { TEAM_PAGES } from "./Teams";

type Maybe = (GridT & { note?: string }) | { none: string } | null | undefined;

function Part({ title, t, why, span = 12, sub }: { title: string; t: Maybe; why?: string; span?: number; sub?: string }) {
  return (
    <Tile span={span} title={title}>
      {sub && <div className="how" style={{ marginTop: -4, marginBottom: 6 }}>{sub[0]!.toUpperCase() + sub.slice(1)}</div>}
      {why ? <Missing why={why} /> : !t ? <Missing /> : "none" in t ? <div className="plain"><T>{t.none}</T></div>
        : <><Grid t={t} />{t.note && <div className="note"><T>{t.note}</T></div>}</>}
    </Tile>
  );
}

export function Planner() {
  const { career, noCareer, nation } = useShell();
  const [params] = useSearchParams();
  const go = useNavigate();
  const keep = nation ? `?nation=${encodeURIComponent(nation)}` : "";
  const want = { section: params.get("section") ?? "", season: params.get("season") ?? "", team: params.get("team") ?? "",
    tab: params.get("tab") ?? "", event: params.get("event") ?? "", games: params.get("games") ?? "",
    places: params.get("places") ?? "", recent: params.get("recent") ?? "" };
  const qs = Object.entries(want).map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join("&");
  const q = useQuery({ queryKey: ["planner", qs, career?.name], enabled: Boolean(career), retry: false,
    queryFn: () => get<PlannerPage>(`/api/planner?${qs}`) });
  useReady(Boolean(q.data || q.error || noCareer), qs);
  const set = (changes: Record<string, string>) => {
    remember(changes);
    const next: Record<string, string> = { ...want, ...changes };
    if ("section" in changes) Object.assign(next, { season: "", team: want.team, event: "", games: "", places: "" });
    if ("team" in changes || "season" in changes) Object.assign(next, { event: "", games: "", places: "" });
    if ("event" in changes) Object.assign(next, { games: "", places: "" });
    if (nation) next.nation = nation;
    go(`/teams/planner?${new URLSearchParams(Object.entries(next).filter(([, v]) => v)).toString()}`);
  };
  const head = <Head title="Teams" crumb="Team planner · your next game" chips={TEAM_PAGES.map((p) => p.label)} on={3}
    onChip={(i) => go(`${TEAM_PAGES[i]!.to}${keep}`)} />;
  if (noCareer) return <>{head}<div className="grid"><Tile span={12} title="No career yet"><div className="plain">Add a career on the current site for now.</div></Tile></div></>;
  if (q.error) return <>{head}<div className="grid"><Tile span={12}><Missing why={String(q.error)} /></Tile></div></>;
  if (!q.data) return <>{head}<div className="empty">Planning the next game…</div></>;
  const d = q.data, ch = d.choices.find((c) => c.section === d.section), b = d.body, m = b?.missing ?? {};
  return (
    <>
      {head}
      <div className="grid">
        <Tile span={12} title="Pick a competition and a team">
          <div className="plain">Everything here is for the next game: the numbers come from this competition only, and the season you pick.</div>
          <div className="drops">
            <Pick label="Competition" value={d.section} options={d.choices.map((c) => ({ v: c.section, label: c.section, note: `${c.matches} matches` }))}
              set={(v) => set({ section: v })} />
            <Pick label="Season" value={d.season || "All seasons"} options={["All seasons", ...(ch?.seasons ?? [])]}
              set={(v) => set({ season: v === "All seasons" ? "" : v })} />
            {d.teams.length > 0 && <Pick label="Team" value={d.team} options={d.teams} set={(v) => set({ team: v })} />}
          </div>
          {d.tip && <div className="note">{d.tip}</div>}
        </Tile>
        {d.none ? <Tile span={12}><Missing why={d.none} /></Tile> : <>
          <div className="itabs">{d.tabs.map((x, i) => (
            <button key={x} className={x === d.tab ? "on" : ""} onClick={() => set({ tab: i === 0 ? "" : x })}>{x}</button>))}</div>
          {d.tab === "Qualification" && b && (b.none ? <Tile span={12} title="Qualification"><div className="plain"><T>{b.none}</T></div></Tile>
            : m.qualification ? <Tile span={12} title="Qualification"><Missing why={m.qualification} /></Tile>
            : b.qualification && <Tile span={12} title={`Qualification · ${b.qualification.event}`}>
              <div className="drops">
                {b.qualification.events.length > 1 && <Pick label="Competition" value={b.qualification.event} options={b.qualification.events}
                  set={(v) => set({ event: v })} />}
                <div className="drop"><label className="droplab" htmlFor="pl-games">League games each</label>
                  <input id="pl-games" className="typed num" type="number" min={1} max={60} value={b.qualification.games}
                    onChange={(e) => set({ games: e.target.value })} /></div>
                <div className="drop"><label className="droplab" htmlFor="pl-places">Teams going through</label>
                  <input id="pl-places" className="typed num" type="number" min={1} max={16} value={b.qualification.places}
                    onChange={(e) => set({ places: e.target.value })} /></div>
              </div>
              {b.qualification.none ? <Missing why={b.qualification.none} /> : <>
                {b.qualification.line && <div className="plain" style={{ marginTop: 12 }}><b><T>{b.qualification.line}</T></b></div>}
                {b.qualification.table && <Grid t={b.qualification.table} />}</>}
              <div className="note">{b.qualification.note}</div>
            </Tile>)}
          {d.tab === "Batting order" && b && <>
            <Tile span={12} title="Batting order" right={
              <div className="itabs" style={{ margin: 0 }}>{[["1", "Recent XI"], ["0", "Everyone"]].map(([v, l]) => (
                <button key={v} className={(b.recent ? "1" : "0") === v ? "on" : ""} onClick={() => set({ recent: v === "1" ? "" : "0" })}>{l}</button>))}</div>}>
              {m.order ? <Missing why={m.order} /> : !b.order ? <Missing /> : b.order.none ? <div className="plain">{b.order.none}</div> : <>
                <div className="plain">The top seven picked from where each player does best against the competition's average at that position
                  {b.recent ? ", from the players in the last five games" : ", from everyone who has batted here"}.</div>
                {b.order.top7 && <Grid t={b.order.top7} />}</>}
            </Tile>
            {b.order?.every && <Tile span={12} title="Every player at every position">
              <div className="plain">Highlighted: the position each player does best from.</div><Grid t={b.order.every} /></Tile>}
          </>}
          {d.tab === "Bowling plan" && b && <Part title="Bowling plan" t={b.plan} why={m.plan} />}
          {d.tab === "Knocking on the door" && b && <Part title="Knocking on the door" t={b.knocking} why={m.knocking} />}
          {d.tab === "Partnerships" && b && <>
            <Part span={6} title="Batting pairs" sub="2+ stands together" t={b.batting} why={m.batting} />
            <Part span={6} title="Bowling pairs" sub="bowled in the same innings 3+ times" t={b.bowling} why={m.bowling} />
          </>}
        </>}
      </div>
    </>
  );
}
