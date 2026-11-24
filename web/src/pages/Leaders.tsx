// Leaders and records (stage 3): Stat by stat, Records, Hall of fame and Rankings, one section of the menu with a chip
// for each page (as Teams has). Every number comes from the server (server/leaderspage.py); the page only shows it.
import { useQuery } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router";
import { get, type RecordsPage, type StatByStat, remember } from "../api";
import { Drop, Explain, MatchLink, Missing, Pick, Tile } from "../kit/base";
import { DotSpread, PaceBars, RankBars, RecordSteps } from "../kit/leaders";
import { BestTable } from "../kit/match";
import { Streaks } from "../kit/season";
import { Grid } from "../kit/teams";
import { T } from "../shell/names";
import { useReady } from "../ready";
import { Head, useShell } from "../shell/Shell";

export const LEADER_PAGES = [{ label: "Stat by stat", to: "/leaders" }, { label: "Records", to: "/leaders/records" },
  { label: "Hall of fame", to: "/leaders/hall" }, { label: "Rankings", to: "/leaders/rankings" }];

/** A table's rows as a CSV file to save (the current site's "Download this table"). */
export function CsvButton({ cols, rows, name }: { cols: string[]; rows: (string | number | null)[][]; name: string }) {
  const save = () => {
    const cell = (v: string | number | null) => { const s = v == null ? "" : String(v); return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; };
    const text = [["#", ...cols], ...rows.map((r, i) => [i + 1, ...r])].map((r) => r.map(cell).join(",")).join("\n");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([text], { type: "text/csv" }));
    a.download = name;
    a.click();
    window.setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  };
  return <button className="btn quiet sm" onClick={save}>Download this table (CSV)</button>;
}

export function LeadersHead({ on, crumb }: { on: number; crumb: ReactNode }) {
  const go = useNavigate();
  const { nation } = useShell();
  const keep = nation ? `?nation=${encodeURIComponent(nation)}` : "";
  return <Head title="Leaders" crumb={crumb} chips={LEADER_PAGES.map((p) => p.label)} on={on} onChip={(i) => go(`${LEADER_PAGES[i]!.to}${keep}`)} />;
}

const KEYS = ["section", "seasons", "disc", "events", "teams", "venues", "pos", "single", "posn", "view", "top", "min", "find", "only", "stat", "measure"];

export function StatByStat() {
  const { career, noCareer, nation } = useShell();
  const [params] = useSearchParams();
  const go = useNavigate();
  const { pick } = useParams();   // a competition found by the search opens here
  const want = Object.fromEntries(KEYS.map((k) => [k, params.get(k) ?? (k === "section" && pick ? pick : "")]));
  const qs = KEYS.filter((k) => want[k]).map((k) => `${k}=${encodeURIComponent(want[k]!)}`).join("&");
  const q = useQuery({ queryKey: ["statbystat", qs, career?.name], enabled: Boolean(career), retry: false,
    queryFn: () => get<StatByStat>(`/api/statbystat?${qs}`), placeholderData: (was) => was });   // the page stays while the next answer comes
  useReady(Boolean(q.data || q.error || noCareer), qs);
  const set = (changes: Record<string, string>) => {
    if (changes.section) remember({ section: changes.section });
    const next: Record<string, string> = { ...want, ...changes };
    if ("section" in changes) Object.assign(next, { seasons: "", events: "", teams: "", min: "", find: "", only: "" });
    if ("disc" in changes) Object.assign(next, { stat: "", min: "", pos: "", posn: "", single: "", measure: "" });
    if (nation) next.nation = nation;
    go(`/leaders?${new URLSearchParams(Object.entries(next).filter(([, v]) => v)).toString()}`);
  };
  const head = <LeadersHead on={0} crumb="Stat by stat · who's best, who's worst" />;
  if (noCareer) return <>{head}<div className="grid"><Tile span={12} title="No career yet"><div className="plain">Add a career on the current site for now.</div></Tile></div></>;
  if (q.error) return <>{head}<div className="grid"><Tile span={12}><Missing why={String(q.error)} /></Tile></div></>;
  if (!q.data) return <>{head}<div className="empty">Ranking everyone…</div></>;
  const d = q.data;
  if (!d.choices.length) return <>{head}<div className="grid"><Tile span={12}><Missing why={d.none} /></Tile></div></>;
  const best = d.view === "Best";
  const join = (v: string[]) => v.join("|");
  return (
    <>
      {head}
      <div className="grid">
        <Tile span={12} className="pickbar">
          <div className="drops">
            <Drop label="Competition" all={d.choices.map((c) => c.section)} on={d.ticked} set={(v) => set({ section: join(v) })} keepOne
              note={(x) => `${d.choices.find((c) => c.section === x)?.matches ?? ""} matches`} />
            <Drop label="Discipline" all={d.discs} on={[d.disc]} set={(v) => set({ disc: v[0]! })} multi={false} keepOne />
            <Drop label="Seasons" all={d.seasons} on={d.picked_seasons} set={(v) => set({ seasons: join(v) })} none="All seasons" />
            {d.events.length > 1 && <Drop label="Competitions inside" all={d.events} on={d.picked_events} set={(v) => set({ events: join(v) })} none="All of them" />}
            <Drop label="Teams" all={d.teams} on={d.picked_teams} set={(v) => set({ teams: join(v) })} none="All teams" />
            <Drop label="Venue" all={d.venues} on={d.picked_venues} set={(v) => set({ venues: join(v) })} none="Anywhere" />
            {d.disc === "Batting" && <>
              <Drop label="Batting positions" all={[...d.groups, ...Array.from({ length: 11 }, (_, i) => `No. ${i + 1}`)]}
                on={d.single ? d.picked_single.map((n) => `No. ${n}`) : d.picked_groups} none="Every position"
                set={(v) => {
                  // a group (openers, 4 and 5...) or single positions (No. 1 to 11), never both: the kind just picked wins
                  const now = d.single ? d.picked_single.map((n) => `No. ${n}`) : d.picked_groups;
                  const added = v.find((x) => !now.includes(x)), single = added ? added.startsWith("No. ") : d.single;
                  const keep = v.filter((x) => x.startsWith("No. ") === single);
                  set(single ? { single: "1", posn: join(keep.map((x) => x.slice(4))), pos: "" } : { single: "", pos: join(keep), posn: "" });
                }} />
            </>}
          </div>
          {d.stats && <div className="drops">
            <Drop label="Stat" all={d.stats.map((s) => s.label)} on={[d.stats.find((s) => s.id === d.stat)?.label ?? ""]} multi={false} keepOne
              set={(v) => set({ stat: d.stats!.find((s) => s.label === v[0])?.id ?? "" })} />
            <Drop label="Ranking" all={["Best", "Worst"]} on={[d.view]} set={(v) => set({ view: v[0]! })} multi={false} keepOne />
            <Drop label="Show" all={d.tops} on={[d.top]} set={(v) => set({ top: v[0]! })} multi={false} keepOne say={(x) => (x === "all" ? "Everyone" : `Top ${x}`)} />
            {d.minimum && <Drop label="Minimum to qualify" all={d.minimum.options.map((o) => String(o.v))} on={[String(d.minimum.value)]} multi={false} keepOne
              say={(x) => d.minimum!.options.find((o) => String(o.v) === x)?.label ?? x} set={(v) => set({ min: v[0]! })} />}
            {d.measures && d.measures.length > 1 && <Drop label="Measure against" all={d.measures.map((m) => m.id)} on={[d.measure ?? "all"]} multi={false} keepOne
              say={(x) => d.measures!.find((m) => m.id === x)?.label ?? x} set={(v) => set({ measure: v[0]! })} />}
            {d.names && <Drop label="Find a player" all={d.names} on={d.find ? [d.find] : []} multi={false} none="Nobody" set={(v) => set({ find: v[0] ?? "" })} />}
            {d.names && <Drop label="Only these players" all={d.names} on={d.only ?? []} none="Everyone" set={(v) => set({ only: join(v) })} />}
          </div>}
          <div className="note">Several competitions picked are counted together, each against its own average. Teams: only the players' games for these
            teams count. Venue: from the player's own team. Batting positions: only those innings, against the average batter there.</div>
        </Tile>
        {d.statdef && <Tile span={12}>
          <div className="plain"><b>{d.statdef.label}</b>: {d.statdef.definition}</div>
          <div className="note">{d.statdef.note}</div>
          {d.found && <div className="plain" style={{ marginTop: 8 }}><T>{d.found}</T></div>}
        </Tile>}
        {d.none ? <Tile span={12}><Missing why={d.none} /></Tile> : <>
          {d.bars && <Tile span={6} title={d.bars.title}>
            <RankBars rows={d.bars.rows} reference={d.bars.reference} decimals={d.bars.decimals} best={best} />
            <Explain is_={d.bars.is_} best={d.bars.best} best_label={d.bars.best_label} for_={d.bars.for_} />
          </Tile>}
          {d.dots && <Tile span={6} title={d.dots.title}>
            <DotSpread d={d.dots} best={best} />
            <Explain is_={d.dots.is_} best={d.dots.best} best_label={d.dots.best_label} for_={d.dots.for_} />
            <ul className="keylist">{d.dots.explain.map(([k, s]) => <li key={s} className={k}><T>{s}</T></li>)}</ul>
          </Tile>}
          {d.table && <Tile span={12} title={d.table.title}>
            <Grid t={d.table} />
            <div className="note">{d.table.note}</div>
            {d.csv && <CsvButton cols={d.table.cols} rows={d.table.rows} name={d.csv} />}
          </Tile>}
        </>}
      </div>
    </>
  );
}

/** A page of this section still to be built (stage 3 goes page by page). */
export function LeadersToCome({ on, what }: { on: number; what: string }) {
  useReady(true, on);
  return (
    <>
      <LeadersHead on={on} crumb={LEADER_PAGES[on]!.label} />
      <div className="grid"><Tile span={12} title="Coming in stage 3"><div className="plain">{what}</div>
        <div className="plain">Until then the current site has it: start it with <b>Start Stats Pack.bat</b>.</div></Tile></div>
    </>
  );
}

const REC_KEYS = ["section", "season", "top", "team", "record"];

/** Records (stage 3): the record books for the competitions picked, the best stand for each wicket, the best games
 *  ever, one team's streaks and every team's longest runs, and the record timeline. */
export function Records() {
  const { career, noCareer, nation } = useShell();
  const [params] = useSearchParams();
  const go = useNavigate();
  const keep = nation ? `?nation=${encodeURIComponent(nation)}` : "";
  const want = Object.fromEntries(REC_KEYS.map((k) => [k, params.get(k) ?? ""]));
  const qs = REC_KEYS.filter((k) => want[k]).map((k) => `${k}=${encodeURIComponent(want[k]!)}`).join("&");
  const q = useQuery({ queryKey: ["records", qs, career?.name], enabled: Boolean(career), retry: false,
    queryFn: () => get<RecordsPage>(`/api/records?${qs}`), placeholderData: (was) => was });
  useReady(Boolean(q.data || q.error || noCareer), qs);
  const [open, setOpen] = useState<Set<number>>(new Set());
  const set = (changes: Record<string, string>) => {
    if (changes.section) remember({ section: changes.section });
    const next: Record<string, string> = { ...want, ...changes };
    if ("section" in changes) Object.assign(next, { season: "", team: "", record: "" });
    if (nation) next.nation = nation;
    go(`/leaders/records?${new URLSearchParams(Object.entries(next).filter(([, v]) => v)).toString()}`);
  };
  const head = <LeadersHead on={1} crumb="Records · the record books" />;
  if (noCareer) return <>{head}<div className="grid"><Tile span={12} title="No career yet"><div className="plain">Add a career on the current site for now.</div></Tile></div></>;
  if (q.error) return <>{head}<div className="grid"><Tile span={12}><Missing why={String(q.error)} /></Tile></div></>;
  if (!q.data) return <>{head}<div className="empty">Opening the record books…</div></>;
  const d = q.data;
  if (!d.choices.length) return <>{head}<div className="grid"><Tile span={12}><Missing why={d.none} /></Tile></div></>;
  const tl = d.timeline;
  return (
    <>
      {head}
      <div className="grid">
        <Tile span={12} className="pickbar">
          <div className="drops">
            <Drop label="Competition" all={d.choices.map((c) => c.section)} on={d.ticked} set={(v) => set({ section: v.join("|") })} keepOne
              note={(x) => `${d.choices.find((c) => c.section === x)?.matches ?? ""} matches`} />
            <Pick label="Season" value={d.season || "All seasons"} options={["All seasons", ...d.seasons]} set={(v) => set({ season: v === "All seasons" ? "" : v })} />
            <Pick label="Show" value={d.top} options={d.tops.map((x) => ({ v: x, label: `Top ${x}` }))} set={(v) => set({ top: v })} />
          </div>
          <div className="note">The best (and worst) ever in the competitions picked; several are counted together. Anything set in your 10 most recent
            matches is marked 🆕.</div>
        </Tile>
        {d.pace && <Tile span={12} title={d.pace.title}>
          <div className="sub" style={{ gridTemplateColumns: "1fr 1fr" }}>{d.pace.parts.map((p) => (
            <div key={p.what}>{p.none ? <div className="plain">{p.none}</div> : <>
              <div className="glabel">Projected season {p.what}</div>
              <PaceBars rows={p.rows ?? []} record={p.record ?? null} />
              <Explain is_={p.is_} best={p.best} best_label={p.best_label} for_={p.for_ ?? ""} /></>}</div>))}</div>
          <div className="note">{d.pace.note}</div>
        </Tile>}
        {(d.groups ?? []).map((g) => <RecordGroup key={g.group} g={g} keep={keep} />)}
        {d.stands && d.stands.length > 0 && <Tile span={12} title="The best stand for each wicket" right="click a wicket for its top 5">
          <div className="scrollx"><table className="c"><thead><tr><th>Wicket</th><th className="r">Stand</th><th>Batters</th><th>Team</th><th>Against</th><th>Date</th><th /></tr></thead>
            <tbody>{d.stands.flatMap((w) => w.rows.filter((_, i) => i === 0 || open.has(w.wicket)).map((r, i) => (
              <tr key={`${w.wicket}-${i}`} className={i ? "dimrow" : ""}>
                <td>{i === 0 ? <b>{w.wicket}{["st", "nd", "rd"][w.wicket - 1] ?? "th"}</b> : <span className="why">{r.place}.</span>}</td>
                <td className="r"><span className="tn">{r.runs}</span></td><td><span className="why"><T>{r.who}</T></span></td>
                <td><span className="why">{r.team}</span></td><td><span className="why">{r.against}</span></td>
                <td><MatchLink id={r.id} className="lk">{r.date}</MatchLink></td>
                <td>{i === 0 && w.rows.length > 1 && <button className="btn quiet sm" onClick={() => setOpen((o) => { const n = new Set(o); if (n.has(w.wicket)) n.delete(w.wicket); else n.add(w.wicket); return n; })}>
                  {open.has(w.wicket) ? "Hide" : "Show top 5"}</button>}</td></tr>)))}</tbody></table></div>
          <div className="note">From the fall of wickets; * means unbroken at the end of the innings. Equal stands share a place.</div>
        </Tile>}
        {d.games && <Tile span={12} title="The best games ever" right="by the excitement rating, out of 10">
          {d.games.length ? <BestTable rows={d.games} showSection={d.ticked.length > 1} keep={keep} /> : <Missing why="No rated games here yet." />}
          <div className="note">Each game is rated within its own competition: how close the finish was, any comeback, what was at stake and the big moments.</div>
        </Tile>}
        <Tile span={12} title={`Streaks · ${d.team}`}>
          <div className="drops"><Pick label="Team" value={d.team} options={d.teams} set={(v) => set({ team: v })} /></div>
          {d.streaks ? <><Streaks cal={d.streaks} /><Explain is_={d.streaks.is_} best={d.streaks.best} best_label={d.streaks.best_label} for_={d.streaks.for_} /></>
            : <Missing why="No matches here yet." />}
        </Tile>
        {d.runs && <Tile span={12} title="Every team's longest runs"><Grid t={d.runs} />{d.runs.note && <div className="note">{d.runs.note}</div>}</Tile>}
        {tl && <Tile span={12} title="Record timeline">
          {tl.none ? <Missing why={tl.none} /> : <>
            <div className="drops"><Pick label="Record" value={tl.pick ?? ""} options={tl.names} set={(v) => set({ record: v })} /></div>
            <RecordSteps points={tl.points ?? []} end={tl.end ?? ""} unit={tl.unit ?? "runs"} />
            <Explain is_={tl.is_} best={tl.best} best_label={tl.best_label} for_={tl.for_ ?? ""} />
            {tl.table && <Grid t={tl.table} keep={keep} />}</>}
        </Tile>}
        {d.caption && <Tile span={12}><div className="note" style={{ marginTop: 0 }}>{d.caption}</div></Tile>}
      </div>
    </>
  );
}

function RecordGroup({ g, keep }: { g: NonNullable<RecordsPage["groups"]>[number]; keep: string }) {
  return (
    <>
      <div className="itabs" style={{ marginTop: 6 }}><span className="tl2">{g.group}</span></div>
      {g.tables.map((t) => (
        <Tile key={t.title} span={t.short ? 6 : 12} title={t.title}>
          <Grid t={t} keep={keep} />
          {t.near && <div className="note"><T>{t.near}</T></div>}
        </Tile>))}
    </>
  );
}
