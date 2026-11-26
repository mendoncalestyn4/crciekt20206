// Leaders and records (stage 3): Stat by stat, Records, Hall of fame and Rankings, one section of the menu with a chip
// for each page (as Teams has). Every number comes from the server (server/leaderspage.py); the page only shows it.
import { useQuery } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { dayY } from "../format";
import { useNavigate, useParams, useSearchParams } from "react-router";
import { get, type HallPage, type RankingsPage, type RecordsPage, type StatByStat, remember } from "../api";
import { Drop, Explain, MatchLink, Missing, Pick, Tile } from "../kit/base";
import { DotSpread, PaceBars, RankBars, RecordSteps, TimeLines } from "../kit/leaders";
import { BestTable } from "../kit/match";
import { StrengthPanel, Streaks } from "../kit/season";
import { SignedBars } from "../kit/teams";
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

const KEYS = ["section", "seasons", "disc", "events", "teams", "venues", "pos", "single", "posn", "view", "top", "min", "find", "only", "stat", "measure",
  "opps", "result"];

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
  if (noCareer) return <>{head}<div className="grid"><Tile span={12} title="No career yet"><div className="plain">Add a career in Settings first.</div></Tile></div></>;
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
        <div className="intro">Pick a competition and a stat. The left chart ranks players on that one stat; the right chart shows where every qualifying player sits.</div>
        <Tile span={12} className="pickbar">
          <div className="drops">
            <Drop label="Competition" all={d.choices.map((c) => c.section)} on={d.ticked} set={(v) => set({ section: join(v) })} keepOne
              note={(x) => `${d.choices.find((c) => c.section === x)?.matches ?? ""} matches`} />
            <Drop label="Discipline" all={d.discs} on={[d.disc]} set={(v) => set({ disc: v[0]! })} multi={false} keepOne />
            <Drop label="Seasons" all={d.seasons} on={d.picked_seasons} set={(v) => set({ seasons: join(v) })} none="All seasons" />
            {d.events.length > 1 && <Drop label="Competitions inside" all={d.events} on={d.picked_events} set={(v) => set({ events: join(v) })} none="All of them" />}
            <Drop label="Teams" all={d.teams} on={d.picked_teams} set={(v) => set({ teams: join(v) })} none="All teams" />
            <Drop label="Venue" all={d.venues} on={d.picked_venues} set={(v) => set({ venues: join(v) })} none="Anywhere" />
            <Drop label="Against" all={d.teams} on={d.picked_opps ?? []} set={(v) => set({ opps: join(v) })} none="Every opponent" />
            {d.results && <Drop label="Result" all={d.results.map((r) => r.id || "all")} on={[d.result || "all"]} multi={false} keepOne
              say={(x) => d.results!.find((r) => (r.id || "all") === x)?.label ?? x} set={(v) => set({ result: v[0] === "all" ? "" : v[0]! })} />}
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
  if (noCareer) return <>{head}<div className="grid"><Tile span={12} title="No career yet"><div className="plain">Add a career in Settings first.</div></Tile></div></>;
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

const RK_KEYS = ["tab", "section", "what", "players", "teams", "team", "date"];

/** Rankings (stage 3): batters, bowlers and all-rounders on the marks out of 10, the rankings history, team ratings
 *  and every team ranked by runs and wickets up to any date. */
export function Rankings() {
  const { career, noCareer, nation } = useShell();
  const [params] = useSearchParams();
  const go = useNavigate();
  const want = Object.fromEntries(RK_KEYS.map((k) => [k, params.get(k) ?? ""]));
  const qs = RK_KEYS.filter((k) => want[k]).map((k) => `${k}=${encodeURIComponent(want[k]!)}`).join("&");
  const q = useQuery({ queryKey: ["rankings", qs, career?.name], enabled: Boolean(career), retry: false,
    queryFn: () => get<RankingsPage>(`/api/rankings?${qs}`), placeholderData: (was) => was });
  useReady(Boolean(q.data || q.error || noCareer), qs);
  const set = (changes: Record<string, string>) => {
    if (changes.section) remember({ section: changes.section });
    const next: Record<string, string> = { ...want, ...changes };
    if ("section" in changes || "what" in changes) Object.assign(next, { players: "", teams: "", team: "" });
    if (nation) next.nation = nation;
    go(`/leaders/rankings?${new URLSearchParams(Object.entries(next).filter(([, v]) => v)).toString()}`);
  };
  const head = <LeadersHead on={3} crumb="Rankings · who's on top right now" />;
  if (noCareer) return <>{head}<div className="grid"><Tile span={12} title="No career yet"><div className="plain">Add a career in Settings first.</div></Tile></div></>;
  if (q.error) return <>{head}<div className="grid"><Tile span={12}><Missing why={String(q.error)} /></Tile></div></>;
  if (!q.data) return <>{head}<div className="empty">Ranking everyone…</div></>;
  const d = q.data;
  if (!d.choices.length) return <>{head}<div className="grid"><Tile span={12}><Missing why={d.none} /></Tile></div></>;
  const one = d.tab === d.tabs[1] || d.tab === d.tabs[2];
  const comps = d.choices.map((c) => c.section);
  const note = (x: string) => `${d.choices.find((c) => c.section === x)?.matches ?? ""} matches`;
  const join = (v: string[]) => v.join("|");
  return (
    <>
      {head}
      <div className="grid">
        <div className="intro">Batters, bowlers and all-rounders ranked on their marks out of 10, team ratings (Elo) and every team by runs and wickets. Recent series count most, so these move as you play.</div>
        <div className="itabs">{d.tabs.map((x, i) => (
          <button key={x} className={x === d.tab ? "on" : ""} onClick={() => set({ tab: i === 0 ? "" : x })}>{x}</button>))}</div>
        <Tile span={12} className="pickbar">
          <div className="drops">
            {one ? <Pick label="Competition" value={d.ticked[0]!} options={comps.map((c) => ({ v: c, label: c, note: note(c) }))} set={(v) => set({ section: v })} />
              : <Drop label="Competition" all={comps} on={d.ticked} set={(v) => set({ section: join(v) })} keepOne note={note} />}
            {d.tab !== d.tabs[2] && d.tab !== d.tabs[3] && <Pick label="Ranking" value={d.what} options={d.kinds.map((k) => ({ v: k.id, label: k.label }))} set={(v) => set({ what: v })} />}
            {d.tab === d.tabs[1] && d.players && <Drop label="Players to draw" all={d.players} on={d.picked ?? []} set={(v) => set({ players: join(v) })} none="The top five now" />}
            {d.tab === d.tabs[2] && d.teams && <Drop label="Teams to draw" all={d.teams} on={d.picked ?? []} set={(v) => set({ teams: join(v) })} none="The top four" />}
            {d.tab === d.tabs[3] && d.date && <div className="drop"><label className="droplab" htmlFor="rk-date">Up to</label>
              <input id="rk-date" className="typed" type="date" min={d.first} max={d.last} value={d.date} onChange={(e) => e.target.value && set({ date: e.target.value })} /></div>}
            {d.tab === d.tabs[3] && d.ends && d.ends.length > 0 && <Pick label="Jump to" value={d.ends.find((e) => e.date === d.date)?.date ?? ""}
              options={[...(d.ends.some((e) => e.date === d.date) ? [] : [{ v: "", label: "Pick a season's end" }]), ...d.ends.map((e) => ({ v: e.date, label: e.label }))]}
              set={(v) => v && set({ date: v })} />}
          </div>
          {d.tab === d.tabs[0] && d.rule && <div className="note">{d.rule}</div>}
        </Tile>
        {d.none ? <Tile span={12}><Missing why={d.none} /></Tile> : null}
        {d.tab === d.tabs[0] && <>
          {d.rows && <Tile span={12} title="The rankings" right="point at a rating for how it's worked out">
            <div className="scrollx"><table className="c"><thead><tr><th className="r">#</th><th>Player</th><th>Team</th><th className="r">Rating</th><th>Move</th>
              <th className="r">Peak</th><th>When</th><th className="r">At No. 1</th><th className="r">Inns</th><th className="r">Series</th></tr></thead>
              <tbody>{d.rows.map((r) => (
                <tr key={r.player} className={r.mine ? "me" : ""}><td className="r"><span className="tn">{r.rank}</span></td>
                  <td><span className="why"><T>{r.player}</T></span></td><td><span className="why">{r.team}</span></td>
                  <td className="r"><span className="tn how-tip" title={r.how}>{r.rating}</span></td>
                  <td><span className={`why ${r.move.startsWith("▲") ? "up" : r.move.startsWith("▼") ? "down" : ""}`}>{r.move}</span></td>
                  <td className="r"><span className="tn">{r.peak}</span></td><td><span className="why">{r.peak_date}</span></td>
                  <td className="r"><span className="tn">{r.at_one}</span></td><td className="r"><span className="tn">{r.inns}</span></td>
                  <td className="r"><span className="tn">{r.series}</span></td></tr>))}</tbody></table></div>
            <div className="note">Move: places up or down since before the competition's last match day. At No. 1: matches played in the competition while
              they were top. Peak: the best rating they reached, and when.</div></Tile>}
          {d.bars && <Tile span={6} title={`Top 10 · ${d.kinds.find((k) => k.id === d.what)?.label.toLowerCase()}`} right={d.latest}>
            <RankBars rows={d.bars.rows} reference={null} decimals={2} best />
            <Explain is_={d.bars.is_} best={d.bars.best} best_label={d.bars.best_label} for_={d.bars.for_} /></Tile>}
          {d.table && <Tile span={12} title="The rankings" right="each competition's rating, combined by innings"><Grid t={d.table} /></Tile>}
          {d.near && d.near.length > 0 && <Tile span={6} title="Not ranked yet" right={d.need ? `${d.need} innings needed` : undefined}>
            <table className="c"><thead><tr><th>Player</th><th>Team</th><th className="r">Inns</th><th className="r">Rating so far</th><th>Still needs</th></tr></thead>
              <tbody>{d.near.map((r) => <tr key={r.player}><td><span className="why"><T>{r.player}</T></span></td><td><span className="why">{r.team}</span></td>
                <td className="r"><span className="tn">{r.inns}</span></td><td className="r"><span className="tn">{r.rating}</span></td><td><span className="why">{r.needs}</span></td></tr>)}</tbody></table>
          </Tile>}
        </>}
        {d.tab === d.tabs[1] && !d.none && <>
          {d.lines && Array.isArray(d.lines) && <Tile span={12} title="Rating over time">
            <TimeLines series={d.lines.map((l) => ({ name: l.player, points: l.points.map((p) => ({ date: p.date, v: p.rating })) }))} y="Rating" />
            <Explain is_={d.is_} best={d.best} best_label={d.best_label} for_={d.for_ ?? ""} /></Tile>}
          {d.peaks && <Tile span={6} title="Highest ratings ever" right="the peak each player reached, and when">
            <RankBars rows={d.peaks.rows} reference={null} decimals={2} best />
            <Explain is_={d.peaks.is_} best={d.peaks.best} best_label={d.peaks.best_label} for_={d.peaks.for_} /></Tile>}
          {d.reigns && <Tile span={6} title="No. 1 reigns" right="newest first"><Grid t={d.reigns} />{d.reigns.note && <div className="note">{d.reigns.note}</div>}</Tile>}
        </>}
        {d.tab === d.tabs[2] && !d.none && <>
          {d.elo && <Tile span={5} title="Team ratings now" right="above or below 1500"><SignedBars rows={d.elo.rows} />
            <Explain is_={d.elo.is_} best={d.elo.best} best_label={d.elo.best_label} for_={d.elo.for_} /></Tile>}
          {d.lines && !Array.isArray(d.lines) && <Tile span={7} title="Ratings over time" right="every match moves both teams">
            <TimeLines series={d.lines.teams.map((x) => ({ name: x.team, points: x.points.map((p) => ({ date: p.date, v: p.elo, id: p.id })) }))} y="Elo rating" base={1500} dec={0} />
            <Explain is_={d.lines.is_} best={d.lines.best} best_label={d.lines.best_label} for_={d.lines.for_} />
            {d.note && <div className="note">{d.note}</div>}</Tile>}
          {d.units && <Tile span={12} title="Batting and bowling ratings" right="each half of every team, 1000 = average"><Grid t={d.units} />
            {d.units.note && <div className="note">{d.units.note}</div>}</Tile>}
          {d.teams && <Tile span={12} title={`Against stronger and weaker sides · ${d.team}`} right="by the ratings just before each match">
            <div className="drops"><Pick label="Team" value={d.team ?? ""} options={d.teams} set={(v) => set({ team: v })} /></div>
            {d.strength ? <><StrengthPanel rows={d.strength.rows} lanes={d.strength.lanes} who={d.team} />
              <Explain is_={d.strength.is_} best={d.strength.best} best_label={d.strength.best_label} for_={d.strength.for_} /></> : <Missing why="No rated matches yet." />}
          </Tile>}
        </>}
        {d.tab === d.tabs[3] && !d.none && <>
          {d.bars && <Tile span={5} title="Most runs" right={d.date ? dayY(d.date) : undefined}>
            <RankBars rows={d.bars.rows} reference={null} decimals={0} best />
            <Explain is_={d.bars.is_} best={d.bars.best} best_label={d.bars.best_label} for_={d.bars.for_} /></Tile>}
          {d.table && <Tile span={7} title="Every team by runs and wickets"><Grid t={d.table} />{d.table.note && <div className="note">{d.table.note}</div>}</Tile>}
        </>}
      </div>
    </>
  );
}

const HALL_KEYS = ["tab", "section", "season", "team"];

/** Hall of fame (stage 3): inductions with their plaques and who's next in, Player of the Match, the best batting
 *  duos, the best all-round matches and the firsts timeline. */
export function HallOfFame() {
  const { career, noCareer, nation } = useShell();
  const [params] = useSearchParams();
  const go = useNavigate();
  const want = Object.fromEntries(HALL_KEYS.map((k) => [k, params.get(k) ?? ""]));
  const qs = HALL_KEYS.filter((k) => want[k]).map((k) => `${k}=${encodeURIComponent(want[k]!)}`).join("&");
  const q = useQuery({ queryKey: ["hall", qs, career?.name], enabled: Boolean(career), retry: false,
    queryFn: () => get<HallPage>(`/api/hall?${qs}`), placeholderData: (was) => was });
  useReady(Boolean(q.data || q.error || noCareer), qs);
  const [kind, setKind] = useState("all");
  const set = (changes: Record<string, string>) => {
    if (changes.section) remember({ section: changes.section });
    const next: Record<string, string> = { ...want, ...changes };
    if ("section" in changes) next.season = "";
    if (nation) next.nation = nation;
    go(`/leaders/hall?${new URLSearchParams(Object.entries(next).filter(([, v]) => v)).toString()}`);
  };
  const head = <LeadersHead on={2} crumb="Hall of fame · the big performers" />;
  if (noCareer) return <>{head}<div className="grid"><Tile span={12} title="No career yet"><div className="plain">Add a career in Settings first.</div></Tile></div></>;
  if (q.error) return <>{head}<div className="grid"><Tile span={12}><Missing why={String(q.error)} /></Tile></div></>;
  if (!q.data) return <>{head}<div className="empty">Opening the Hall of fame…</div></>;
  const d = q.data;
  if (!d.choices.length) return <>{head}<div className="grid"><Tile span={12}><Missing why={d.none} /></Tile></div></>;
  const comps = d.choices.map((c) => c.section);
  const note = (x: string) => `${d.choices.find((c) => c.section === x)?.matches ?? ""} matches`;
  const firsts = d.tab === "Firsts", ind = d.tab === "Inductions";
  const events = (d.events ?? []).filter((e) => kind === "all" || e.kind === kind);
  const years = [...new Set(events.map((e) => e.year))];
  return (
    <>
      {head}
      <div className="grid">
        <div className="intro">Players inducted when they reach a milestone, the Player of the Match awards, the best batting pairs, the best all-round performances in a single match, and every first.</div>
        <div className="itabs">{d.tabs.map((x, i) => (
          <button key={x} className={x === d.tab ? "on" : ""} onClick={() => set({ tab: i === 0 ? "" : x })}>{x}</button>))}</div>
        <Tile span={12} className="pickbar">
          <div className="drops">
            {firsts ? <><Pick label="Team" value={d.team ?? ""} options={d.teams ?? []} set={(v) => set({ team: v })} />
              <Pick label="Show" value={kind} options={[{ v: "all", label: "Everything" }, { v: "team", label: "The team's firsts" }, { v: "player", label: "Its players' firsts" }]} set={setKind} /></>
              : ind ? <Pick label="Competition" value={d.ticked[0]!} options={comps.map((c) => ({ v: c, label: c, note: note(c) }))} set={(v) => set({ section: v })} />
              : <><Drop label="Competition" all={comps} on={d.ticked} set={(v) => set({ section: v.join("|") })} keepOne note={note} />
                <Pick label="Season" value={d.season || "All seasons"} options={["All seasons", ...d.seasons]} set={(v) => set({ season: v === "All seasons" ? "" : v })} /></>}
          </div>
          {ind && d.rule && <div className="note">{d.rule}</div>}
          {firsts && <div className="note">Every first in {d.team}'s career and its players': first match and win in each format, against each side, series and
            titles, big totals and chases; its players' first fifties, hundreds, five-fors, big stands, awards, No. 1 rankings and Hall of fame entries.</div>}
        </Tile>
        {d.none ? <Tile span={12}><Missing why={d.none} /></Tile> : null}
        {ind && <>
          {(d.plaques ?? []).map((p) => (
            <Tile key={p.player} span={4} title={p.player} right={p.team} className={`plaque${p.mine ? " mine" : ""}`}>
              <div className="plain"><b>Inducted {p.date}</b> · <MatchLink id={p.id} className="lk">the match</MatchLink></div>
              <div className="plain">{p.route}{p.also ? ` · also ${p.also}` : ""}</div>
              <div className="note">{p.figures}</div>
              {p.moments.length > 0 && <><div className="glabel" style={{ marginTop: 8 }}>Best moments</div>
                <ul className="dots">{p.moments.map((x) => <li key={x.id + x.what}><MatchLink id={x.id} className="lk">{x.what}</MatchLink> <span className="why">{x.date}</span></li>)}</ul></>}
            </Tile>))}
          {d.next && d.next.length > 0 && <Tile span={12} title="Next in" right="the closest, and what each still needs">
            <table className="c"><thead><tr><th>Player</th><th>Team</th><th className="r">How close</th><th>Still needs</th></tr></thead>
              <tbody>{d.next.map((r) => <tr key={r.player}><td><span className="why"><T>{r.player}</T></span></td><td><span className="why">{r.team}</span></td>
                <td className="r"><span className="tn">{r.share}%</span></td><td><span className="why">{r.needs}</span></td></tr>)}</tbody></table></Tile>}
        </>}
        {(d.tab === "Player of the Match" || d.tab === "Batting duos" || d.tab === "All-round matches") && d.bars && <Tile span={d.tab === "All-round matches" ? 12 : 7}
          title={d.tab === "Player of the Match" ? "Most Player of the Match awards" : d.tab === "Batting duos" ? "Most runs together" : "Best all-round matches"}>
          <RankBars rows={d.bars.rows} reference={null} decimals={0} best />
          <Explain is_={d.bars.is_} best={d.bars.best} best_label={d.bars.best_label} for_={d.bars.for_} />
          {d.note && <div className="note">{d.note}</div>}</Tile>}
        {d.tab === "Player of the Match" && <Tile span={5} title="Big-game players" right="awards in knockouts and finals">
          {d.big ? <Grid t={d.big} /> : <Missing why="No knockout matches here yet." />}</Tile>}
        {d.tab === "Batting duos" && d.table && <Tile span={12} title="The best batting duos"><Grid t={d.table} />{d.table.note && <div className="note">{d.table.note}</div>}</Tile>}
        {firsts && events.length > 0 && <Tile span={12} title={`Firsts · ${d.team}`} right={`${events.length} so far`}>
          <div className="timeline">{years.map((y) => (
            <div key={y} className="tyear"><div className="ty">{y}</div>
              {events.filter((e) => e.year === y).map((e, i) => (
                <div key={i} className={`tev ${e.kind}`}><span className="td">{e.date.slice(0, 6)}</span>
                  <span className="tw"><b>{e.what}</b> <T>{e.who}</T></span>
                  {e.id ? <MatchLink id={e.id} className="lk">match</MatchLink> : <span />}</div>))}</div>))}</div>
        </Tile>}
      </div>
    </>
  );
}
