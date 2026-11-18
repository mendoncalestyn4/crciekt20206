// Teams (stage 2): one team's record in one competition and season, overall, home or away, with every part of the
// current site's Teams page in its seven tabs. The pickers sit at the top; the search opens a team at /teams/<name>.
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router";
import { get, type GridT, type NGrid, type Outcome, type TeamBody, type TeamPage, remember } from "../api";
import { Explain, FormatTicks, Lamps, Logo, Missing, Num, three, Tile } from "../kit/base";
import { LeaderBars, RingList, ShareRing } from "../kit/charts";
import { SplitBars } from "../kit/player";
import { StrengthPanel, Streaks, VenueRecord } from "../kit/season";
import { Grid, PositionRace, SignedBars } from "../kit/teams";
import { NO_MATCHES, rnd, fx } from "../format";
import { useReady } from "../ready";
import { Head, useShell } from "../shell/Shell";
import { T } from "../shell/names";
import { useTheme } from "../theme";

const VENUES: [string, string][] = [["Overall", "all"], ["Home", "home"], ["Away", "away"]];
/** The Teams section's pages, switched from the top of each. */
export const TEAM_PAGES = [{ label: "Team record", to: "/teams" }, { label: "Team v team", to: "/teams/vs" },
  { label: "Opponent preview", to: "/teams/preview" }, { label: "Planner", to: "/teams/planner" },
  { label: "Rivalries", to: "/teams/rivalries" }];

export function Teams() {
  const { career, noCareer, nation } = useShell();
  const { pick } = useParams();
  const [params] = useSearchParams();
  const go = useNavigate();
  const keep = nation ? `?nation=${encodeURIComponent(nation)}` : "";
  const want = { team: pick ?? params.get("team") ?? "", section: params.get("section") ?? "", season: params.get("season") ?? "",
    venue: params.get("venue") ?? "", tab: params.get("tab") ?? "", race: params.get("race") ?? "" };
  const qs = Object.entries(want).map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join("&");
  const q = useQuery({ queryKey: ["team", qs, career?.name], enabled: Boolean(career), retry: false,
    queryFn: () => get<TeamPage>(`/api/team?${qs}`) });
  useReady(Boolean(q.data || q.error || noCareer), qs);
  const set = (changes: Record<string, string>) => {
    remember(changes);
    const next = { ...want, ...changes };
    if ("team" in changes || "section" in changes) { next.race = ""; }
    if ("section" in changes) next.season = "";
    if (nation) Object.assign(next, { nation });
    const p = new URLSearchParams(Object.entries(next).filter(([, v]) => v));
    go(`/teams?${p.toString()}`);
  };
  if (noCareer) return <><Head title="Teams" crumb="No career open yet" /><div className="grid"><Tile span={12} title="No career yet">
    <div className="plain">Add a career on the current site for now (<b>Start Stats Pack.bat</b>): the new site sees it straight away.</div></Tile></div></>;
  if (q.error) return <><Head title="Teams" crumb="Team record" /><div className="grid"><Tile span={12}><Missing why={String(q.error)} /></Tile></div></>;
  if (!q.data) return <><Head title="Teams" crumb="Team record" /><div className="empty">Working out the team's record…</div></>;
  const d = q.data, p = d.page;
  if (!p) return <><Head title="Teams" crumb="Team record" /><div className="grid"><Tile span={12}><Missing why={NO_MATCHES} /></Tile></div></>;
  // the competitions ticked: their teams together (those still to play marked)
  const chs = d.choices.filter((c) => p.ticked.includes(c.section));
  const teams = [...new Set(chs.flatMap((c) => c.teams))].sort(), todo = new Set(chs.flatMap((c) => c.todo));
  const h = p.head, b = p.body, scope = `${p.name}${p.season === "All seasons" ? "" : ` · ${p.season}`}`;
  const vlabel = VENUES.find(([, v]) => v === p.venue)?.[0] ?? "Overall";
  return (
    <>
      <Head title="Teams" crumb={`Team record · ${p.team}`} chips={TEAM_PAGES.map((x) => x.label)} on={0}
        onChip={(i) => go(`${TEAM_PAGES[i]!.to}${keep}`)} />
      <div className="grid">
        <Tile span={12} title="Pick a competition and a team">
          <div className="plain">Every comparison is against the average of all the teams in that competition; with several ticked, they are
            counted together and each competition's own average is used, weighted by the team's games in it.</div>
          <FormatTicks all={d.played?.length ? d.played : d.choices.map((c) => c.section)} on={p.ticked} set={(v) => set({ section: v.join("|") })} />
          <div className="field">
            <label htmlFor="tm-season">Season</label>
            <select id="tm-season" className="pick" value={p.season} onChange={(e) => set({ season: e.target.value === "All seasons" ? "" : e.target.value })}>
              {["All seasons", ...p.seasons].map((s) => <option key={s}>{s}</option>)}</select>
            <label htmlFor="tm-team">Team</label>
            <select id="tm-team" className="pick" value={p.team} onChange={(e) => set({ team: e.target.value })}>
              {(teams.includes(p.team) ? teams : [p.team, ...teams]).map((t) => (
                <option key={t} value={t}>{t}{todo.has(t) ? " (0 games)" : ""}</option>))}</select>
            <div className="itabs" style={{ gridColumn: "auto", margin: 0 }}>{VENUES.map(([l, v]) => (
              <button key={v} className={v === p.venue ? "on" : ""} onClick={() => set({ venue: v === "all" ? "" : v })}>{l}</button>))}</div>
          </div>
        </Tile>
        {!h.none && <div className="itabs">{p.tabs.map((x, i) => (
          <button key={x} className={x === p.tab ? "on" : ""} onClick={() => set({ tab: i === 0 ? "" : x })}>{x}</button>))}</div>}
        {h.none ? <Tile span={12} title={p.team}>
          <div className="plain"><T>{h.none}</T></div>
          {(h.elsewhere ?? []).length > 0 && <div className="field">{h.elsewhere!.map((s) => (
            <button key={s} className="btn quiet" onClick={() => set({ section: s, venue: "" })}>Show {s}</button>))}</div>}
        </Tile> : <>
          <Tile span={12} title={scope} right={p.venue === "all" ? undefined : `${vlabel} games`}>
            <div className="row2" style={{ gap: 26, alignItems: "center", flexWrap: "wrap" }}>
              <Logo team={p.team} size={96} />
              <div className="hl" style={{ fontSize: 44 }}>{p.team}</div>
              <div className="kpis">{(h.kpis ?? []).map((k) => <div key={k.k}><span>{k.k}</span><Num v={k.v} px={34} /></div>)}
                <div><span>Last 5</span>{(h.last5 ?? []).length ? <Lamps seq={h.last5 as Outcome[]} /> : <Num v="–" px={34} />}</div></div>
            </div>
            <div className="note">{h.runs}</div>
            {h.ratings && <div className="plain">{h.ratings}</div>}
            {h.venue_note && <div className="note">📍 {h.venue_note}</div>}
          </Tile>
          {!b ? <div className="empty">Working out {p.tab.toLowerCase()}…</div> : <Body tab={p.tab} b={b} team={p.team} keep={keep}
            race={(r) => set({ race: r })} />}
        </>}
      </div>
    </>
  );
}

/** One table in its own tile, or the plain reason there's nothing. */
function GridTile({ g, title, span = 6, sub, none = "Nothing yet.", keep, missing }: {
  g?: NGrid | GridT | null; title: string; span?: number; sub?: string; none?: string; keep: string; missing?: string;
}) {
  const n = g as NGrid | null | undefined, line = n?.right ?? sub;
  return (
    <Tile span={span} title={n?.title ?? title}>
      {line && <div className="how" style={{ marginTop: -4, marginBottom: 6 }}><T>{line.charAt(0).toUpperCase() + line.slice(1)}</T></div>}
      {missing ? <Missing why={missing} /> : n && !n.none && n.cols ? <Grid t={n} keep={keep} /> : <div className="plain">{n?.none ?? none}</div>}
      {n?.note && <div className="note"><T>{n.note}</T></div>}
    </Tile>
  );
}

/** Every player of the team: matches, runs and wickets with their share of the team's, sorted by a click on a column
 *  (runs first), next to a donut of the runs: the top six run-scorers and everyone else. */
function Contributions({ c }: { c: NonNullable<TeamBody["contribution"]> }) {
  const t = useTheme();
  const [key, setKey] = useState<"runs" | "wickets" | "matches" | "player">("runs");
  const [all, setAll] = useState(false);
  const rows = [...c.rows].sort((a, b) => (key === "player" ? a.player.localeCompare(b.player)
    : b[key] - a[key] || (key === "runs" ? b.wickets - a.wickets : b.runs - a.runs) || a.player.localeCompare(b.player)));
  const shown = all ? rows : rows.slice(0, 15);
  const byRuns = [...c.rows].sort((a, b) => b.runs - a.runs), pal = [t.led, t.warm, t.cream, t.win, t.blue, t.orange];
  const rest = byRuns.slice(6).reduce((a, r) => a + r.runs, 0);
  const ring: [string, number, string][] = [...byRuns.slice(0, 6).map((r, i) => [r.player, r.runs, pal[i]!] as [string, number, string]),
    ...(rest ? [[`${byRuns.length - 6} others`, rest, t.grey] as [string, number, string]] : [])];
  const th = (k: typeof key, label: string, right = true) => (
    <th className={`${right ? "r " : ""}sortable${key === k ? " on" : ""}`} onClick={() => setKey(k)} title={`Sort by ${label.toLowerCase()}`}>{label}{key === k ? " ▾" : ""}</th>);
  const topR = Math.max(...c.rows.map((r) => r.run_share), 1), topW = Math.max(...c.rows.map((r) => r.wicket_share), 1);
  const bar = (v: number, top: number) => <span className="sharecell"><span className="bar"><i style={{ width: `${(v / top) * 100}%` }} /></span><span className="tn dimn">{fx(v, 1)}%</span></span>;
  return <>
    <div className="contrib" data-chart>
      <div><div className="k3" style={{ marginTop: 0 }}>The runs off the bat</div><RingList items={ring} centre={String(c.team_runs)} sub="runs" /></div>
      <div><table className="c"><thead><tr>{th("player", "Player", false)}{th("matches", "Matches")}{th("runs", "Runs")}<th>Of the runs</th>{th("wickets", "Wickets")}<th>Of the wickets</th></tr></thead>
        <tbody>{shown.map((r) => <tr key={r.player}><td><T>{r.player}</T></td><td className="r"><span className="tn dimn">{r.matches}</span></td>
          <td className="r"><span className="tn">{r.runs}</span></td><td>{bar(r.run_share, topR)}</td>
          <td className="r"><span className="tn">{r.wickets}</span></td><td>{bar(r.wicket_share, topW)}</td></tr>)}</tbody></table>
        {rows.length > 15 && !all && <button className="btn quiet" style={{ marginTop: 10 }} onClick={() => setAll(true)}>All {rows.length} players</button>}</div>
    </div>
    <Explain {...three(c)} />
  </>;
}

function Body({ tab, b, team, keep, race }: { tab: string; b: TeamBody; team: string; keep: string; race: (r: string) => void }) {
  const t = useTheme();
  const m = b.missing;
  if (tab === "Overview") return <>
    <Tile span={12} title={b.vs_average?.title ?? "Against the average team"}>
      {b.vs_average && <div className="how" style={{ marginTop: -4 }}>{b.vs_average.right}</div>}
      {b.vs_average ? <><SignedBars rows={b.vs_average.rows} /><Explain {...three(b.vs_average)} /></>
        : <Missing why={m.vs_average} />}</Tile>
    <Tile span={12} title="Runs of results" right="every match in order">
      {b.streaks ? <><Streaks cal={b.streaks} /><Explain {...three(b.streaks)} /></>
        : m.streaks ? <Missing why={m.streaks} /> : <div className="plain">No matches yet.</div>}</Tile>
    <Tile span={12} title="Against stronger and weaker sides" right="by the ratings (Elo) just before each match">
      {b.strength ? <><StrengthPanel rows={b.strength.rows} lanes={b.strength.lanes} /><Explain {...three(b.strength)} /></>
        : m.strength ? <Missing why={m.strength} /> : <div className="plain">No rated matches yet (a no-result isn't rated).</div>}</Tile>
    <Tile span={12} title="Home, away and neutral">
      {b.venues ? <><VenueRecord v={b.venues} team={team} />
        <div className="note">The scorecards don't name the ground, so it goes by the home side{b.venues.nation ? "'s country" : ""}.</div>
        <Explain {...three(b.venues)} /></>
        : m.venues ? <Missing why={m.venues} /> : <div className="plain">No matches yet.</div>}</Tile>
    <Tile span={6} title="Top run-scorers">
      {b.top_bat ? (b.top_bat.rows.length ? <><LeaderBars rows={b.top_bat.rows} value="runs" mine={team} height={44 * b.top_bat.rows.length + 16} noTeam label="Top run-scorers" />
        <Explain {...three(b.top_bat)} /></> : <div className="plain">No runs yet.</div>) : <Missing why={m.top_bat} />}</Tile>
    <Tile span={6} title="Top wicket-takers">
      {b.top_bowl ? (b.top_bowl.rows.length ? <><LeaderBars rows={b.top_bowl.rows} value="wickets" mine={team} height={44 * b.top_bowl.rows.length + 16} noTeam label="Top wicket-takers" />
        <Explain {...three(b.top_bowl)} /></> : <div className="plain">No wickets yet.</div>) : <Missing why={m.top_bowl} />}</Tile>
    <Tile span={6} title="Batting depth" right="share of the runs">
      {b.depth ? <><ShareRing rows={b.depth.rows} count={(r) => r.runs ?? 0} centre={String(b.depth.rows.reduce((a, r) => a + (r.runs ?? 0), 0))} sub="runs" />
        <div className="note">The average team here: {b.depth.rows.map((r) => `${r.label.toLowerCase()} ${rnd(r.ref ?? 0)}%`).join(", ")}.</div>
        {b.depth.best && <Explain {...three(b.depth)} />}</>
        : m.depth ? <Missing why={m.depth} /> : <div className="plain">No runs yet.</div>}</Tile>
    <Tile span={6} title="Average partnership for each wicket">
      {b.stands ? <><SplitBars rows={b.stands.rows} dec={1} />{b.stands.best && <Explain {...three(b.stands)} />}</>
        : <Missing why={m.stands} />}</Tile>
    <GridTile g={b.collapses} title="Collapses" sub="4 or more wickets lost for 30 runs or fewer" none="No collapses. Nice." keep={keep} missing={m.collapses} />
    <GridTile g={b.big_stands} title="Big stands" sub="the team's biggest partnerships here (* not out)" none="No stands yet." keep={keep} missing={m.big_stands} />
    <GridTile span={12} g={b.openers} title="Opening pairs" sub="the two players who opened, and their stands" none="No innings yet." keep={keep} missing={m.openers} />
    <Tile span={12} title="Who carries the team">
      <div className="how" style={{ marginTop: -4, marginBottom: 6 }}>Each player's share of the team's runs and wickets</div>
      {m.carry ? <Missing why={m.carry} /> : b.carry ? <><Grid t={b.carry} keep={keep} />{b.carry.shows && <Explain shows={<T>{b.carry.shows}</T>} for_={b.carry.for_} />}</>
        : <div className="plain">No runs or wickets yet.</div>}</Tile>
    <Tile span={12} title="Every player's contribution" right="share of the runs off the bat and of the wickets">
      {b.contribution ? <Contributions c={b.contribution} /> : m.contribution ? <Missing why={m.contribution} /> : <div className="plain">No runs or wickets yet.</div>}</Tile>
    <Tile span={12} title="The usual score at each wicket">
      <div className="how" style={{ marginTop: -4, marginBottom: 6 }}>The typical score when each wicket fell, against their opponents in the same games</div>
      {m.usual ? <Missing why={m.usual} /> : b.usual ? <>{b.usual.line && <div className="plain" style={{ marginBottom: 8 }}><b><T>{b.usual.line}</T></b></div>}<Grid t={b.usual} keep={keep} />{b.usual.shows && <Explain shows={<T>{b.usual.shows}</T>} for_={b.usual.for_} />}</>
        : <div className="plain">No wickets have fallen yet.</div>}</Tile>
    {b.how_they_play !== null && <Tile span={7} title={`How ${team} play`}>
      <div className="how" style={{ marginTop: -4 }}>More (right) or less (left) than the average team, not better or worse{b.how_they_play?.every ? " · every game here" : ""}</div>
      {b.how_they_play ? <><SignedBars rows={b.how_they_play.rows} colour={t.orange} /><Explain {...three(b.how_they_play)} /></>
        : <Missing why={m.how_they_play} />}</Tile>}
    {b.discipline !== null && <Tile span={5} title="Discipline">
      <div className="how" style={{ marginTop: -4 }}>Extras given away per match, fewest first{b.discipline?.every ? " · every game here" : ""}</div>
      {b.discipline ? <><LeaderBars rows={b.discipline.rows} value="extras" mine={team} height={34 * b.discipline.rows.length + 16} noTeam nameSize={17} valSize={20}
        fmt={(v) => fx(v, 1)} label="Discipline" />{b.discipline.best && <Explain {...three(b.discipline)} />}</>
        : <Missing why={m.discipline} />}</Tile>}
    <GridTile g={b.every_team} title="Every team" span={12} keep={keep} missing={m.every_team} />
  </>;
  if (tab === "How they win") return <>
    <GridTile g={b.bat_first} title="Batting first or chasing" span={12} keep={keep} missing={m.bat_first} />
    <Tile span={6} title="Close games">
      {b.close?.right && <div className="how" style={{ marginTop: -4, marginBottom: 6 }}>{b.close.right[0]!.toUpperCase() + b.close.right.slice(1)}</div>}
      {b.close ? <><Grid t={b.close} keep={keep} />{b.close.games && <Grid t={b.close.games} keep={keep} />}</> : <Missing why={m.close} />}</Tile>
    <GridTile g={b.start} title="The openers' start" sub="result when the first wicket fell…" keep={keep} missing={m.start} />
    <GridTile g={b.targets} title="Chasing and defending" span={12} keep={keep} missing={m.targets} />
    <GridTile g={b.dominance} title="How they win and lose" sub="thrashings, comfortable results and scrapes" keep={keep} missing={m.dominance} />
    <GridTile g={b.comebacks} title="Comebacks" none="No comeback wins yet." keep={keep} missing={m.comebacks} />
  </>;
  if (tab === "Opponents and stages") return <>
    <GridTile g={b.stages} title="League games and knockouts" keep={keep} missing={m.stages} />
    <GridTile g={b.bounce} title="Bouncing back" sub="their next game after…" none="Not enough games yet." keep={keep} missing={m.bounce} />
    <GridTile g={b.opponents} title="Every opponent" sub="⭐ favourite and 👻 bogey team (met at least twice)" span={12} keep={keep} missing={m.opponents} />
    <GridTile g={b.fortress} title="Home fortress" sub="home record against the average home side here" keep={keep} missing={m.fortress} />
    <GridTile g={b.revenge} title="Revenge games" sub="against a side that beat them the last time they met" keep={keep} missing={m.revenge} />
  </>;
  if (tab === "Season") return <>
    <Tile span={12} title="The league race" right="position after each match day">
      {b.race ? (b.race.options.length ? <>
        <div className="field" style={{ marginTop: 0 }}><label htmlFor="tm-race">Competition and season</label>
          <select id="tm-race" className="pick" value={b.race.picked} onChange={(e) => race(e.target.value)}>
            {b.race.options.map((o) => <option key={o}>{o}</option>)}</select></div>
        {b.race.none ? <div className="plain">{b.race.none}</div> : <><PositionRace lines={b.race.lines} team={team} />
          <Explain {...three(b.race)} /></>}</> : <div className="plain">{b.race.none}</div>) : <Missing why={m.race} />}
    </Tile>
    <GridTile g={b.halves} title="Early or late starters" sub="league games in the first and second half of each season" span={12}
      none="No league games yet." keep={keep} missing={m.halves} />
  </>;
  if (tab === "Series and Tests") return <>
    {!b.has_series && !b.multi && <Tile span={12} title="Series and Tests"><div className="plain">Bilateral series and multi-day games only: this competition has neither.</div></Tile>}
    {b.has_series && <>
      <GridTile g={b.first_blood} title="First blood" sub="how their series went after the first match" none="No finished series yet." keep={keep} missing={m.first_blood} />
      <Tile span={6} title="Deciders and dead rubbers">
        {m.deciders ? <Missing why={m.deciders} /> : b.deciders ? <Grid t={b.deciders} keep={keep} /> : <div className="plain">No series games yet.</div>}
        <div className="note">Decider: the last game with the series level. Dead rubber: the series was already won.</div></Tile></>}
    {b.multi && <>
      <Tile span={12} title="Second innings and fourth-innings chases">
        {b.second_innings ? <Grid t={b.second_innings} keep={keep} /> : <Missing why={m.second_innings} />}
        <div className="note">Second innings: each team's second time batting in a match (after a follow-on too). Chases: batting in the 4th innings, with how those games ended.</div></Tile>
      <GridTile g={b.follow_on} title="Follow-on and declarations" sub="what happened next" span={12} none="No follow-ons or declarations yet." keep={keep} missing={m.follow_on} /></>}
  </>;
  if (tab === "Squad") return <>
    <GridTile g={b.best_xi} title="Best XI" span={12} keep={keep} missing={m.best_xi} />
    <Tile span={12} title="Who came in and who went out" right={b.changes?.right}>
      {!b.changes ? <Missing why={m.changes} /> : b.changes.none ? <div className="plain">{b.changes.none}</div> : <>
        {b.changes.steps.map((s) => (
          <div key={s.title} className="step"><div className="k3">{s.title}</div>
            <div className="two"><div><div className="how">🟢 In ({s.ins.rows.length})</div>{s.ins.rows.length > 0 && <Grid t={s.ins} keep={keep} />}</div>
              <div><div className="how">🔴 Out ({s.outs.rows.length})</div>{s.outs.rows.length > 0 && <Grid t={s.outs} keep={keep} />}</div></div></div>))}
        <div className="note">{b.changes.note}</div></>}
    </Tile>
  </>;
  return <GridTile g={b.results} title="Results" span={12} none="No games yet." keep={keep} missing={m.results} />;
}
