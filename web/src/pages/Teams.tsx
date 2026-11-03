// Teams (stage 2): one team's record in one competition and season, overall, home or away, with every part of the
// current site's Teams page in its seven tabs. The pickers sit at the top; the search opens a team at /teams/<name>.
import { useQuery } from "@tanstack/react-query";
import { useNavigate, useParams, useSearchParams } from "react-router";
import { get, type GridT, type NGrid, type Outcome, type TeamBody, type TeamPage } from "../api";
import { Explain, Lamps, Logo, Missing, Num, Tile } from "../kit/base";
import { LeaderBars } from "../kit/charts";
import { SplitBars } from "../kit/player";
import { Grid, PositionRace, SignedBars } from "../kit/teams";
import { useReady } from "../ready";
import { Head, useShell } from "../shell/Shell";
import { T } from "../shell/names";
import { useTheme } from "../theme";

const VENUES: [string, string][] = [["Overall", "all"], ["Home", "home"], ["Away", "away"]];

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
  if (!p) return <><Head title="Teams" crumb="Team record" /><div className="grid"><Tile span={12}><Missing why="No matches in this career yet." /></Tile></div></>;
  const ch = d.choices.find((c) => c.section === p.section)!;
  const h = p.head, b = p.body, scope = `${p.section}${p.season === "All seasons" ? "" : ` · ${p.season}`}`;
  const vlabel = VENUES.find(([, v]) => v === p.venue)?.[0] ?? "Overall";
  return (
    <>
      <Head title="Teams" crumb={`Team record · ${p.team}`} />
      <div className="grid">
        <Tile span={12} title="Pick a competition and a team">
          <div className="plain">Every comparison is against the average of all the teams in that competition.</div>
          <div className="field">
            <label htmlFor="tm-sec">Competition</label>
            <select id="tm-sec" className="pick" value={p.section} onChange={(e) => set({ section: e.target.value })}>
              {d.choices.map((c) => <option key={c.section} value={c.section}>{c.section} · {c.matches} matches</option>)}</select>
            <label htmlFor="tm-season">Season</label>
            <select id="tm-season" className="pick" value={p.season} onChange={(e) => set({ season: e.target.value === "All seasons" ? "" : e.target.value })}>
              {["All seasons", ...ch.seasons].map((s) => <option key={s}>{s}</option>)}</select>
            <label htmlFor="tm-team">Team</label>
            <select id="tm-team" className="pick" value={p.team} onChange={(e) => set({ team: e.target.value })}>
              {(ch.teams.includes(p.team) ? ch.teams : [p.team, ...ch.teams]).map((t) => (
                <option key={t} value={t}>{t}{ch.todo.includes(t) ? " (0 games)" : ""}</option>))}</select>
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

function Body({ tab, b, team, keep, race }: { tab: string; b: TeamBody; team: string; keep: string; race: (r: string) => void }) {
  const t = useTheme();
  const m = b.missing;
  if (tab === "Overview") return <>
    {(b.keepers ?? []).length > 0 && <Tile span={12} title={`🧤 Wicketkeeper${b.keepers!.length > 1 ? "s" : ""}`}>
      <div className="plain"><T>{b.keepers!.map((k) => `${k.player} (${k.stumpings} stumping${k.stumpings !== 1 ? "s" : ""})`).join(", ")}</T></div>
      <div className="note">The scorecards don't mark the keeper, so anyone who has made a stumping for this team is flagged as one.</div></Tile>}
    <Tile span={12} title={b.vs_average?.title ?? "Against the average team"}>
      {b.vs_average && <div className="how" style={{ marginTop: -4 }}>{b.vs_average.right}</div>}
      {b.vs_average ? <><SignedBars rows={b.vs_average.rows} /><Explain shows={<T>{b.vs_average.shows}</T>} for_={b.vs_average.for_} /></>
        : <Missing why={m.vs_average} />}</Tile>
    <Tile span={6} title="Top run-scorers">
      {b.top_bat ? (b.top_bat.rows.length ? <><LeaderBars rows={b.top_bat.rows} value="runs" mine={team} height={44 * b.top_bat.rows.length + 16} noTeam label="Top run-scorers" />
        <Explain shows={<T>{b.top_bat.shows}</T>} for_={b.top_bat.for_} /></> : <div className="plain">No runs yet.</div>) : <Missing why={m.top_bat} />}</Tile>
    <Tile span={6} title="Top wicket-takers">
      {b.top_bowl ? (b.top_bowl.rows.length ? <><LeaderBars rows={b.top_bowl.rows} value="wickets" mine={team} height={44 * b.top_bowl.rows.length + 16} noTeam label="Top wicket-takers" />
        <Explain shows={<T>{b.top_bowl.shows}</T>} for_={b.top_bowl.for_} /></> : <div className="plain">No wickets yet.</div>) : <Missing why={m.top_bowl} />}</Tile>
    <Tile span={6} title="Batting depth" right="share of the runs">
      {b.depth ? <><SplitBars rows={b.depth.rows} dec={0} unit="%" />{b.depth.shows && <Explain shows={<T>{b.depth.shows}</T>} for_={b.depth.for_} />}</>
        : <Missing why={m.depth} />}</Tile>
    <Tile span={6} title="Average partnership for each wicket">
      {b.stands ? <><SplitBars rows={b.stands.rows} dec={1} />{b.stands.shows && <Explain shows={<T>{b.stands.shows}</T>} for_={b.stands.for_} />}</>
        : <Missing why={m.stands} />}</Tile>
    <GridTile g={b.openers} title="Opening pairs" sub="the two players who opened, and their stands" none="No innings yet." keep={keep} missing={m.openers} />
    <GridTile g={b.collapses} title="Collapses" sub="4 or more wickets lost for 30 runs or fewer" none="No collapses. Nice." keep={keep} missing={m.collapses} />
    {b.how_they_play !== null && <Tile span={7} title={`How ${team} play`}>
      <div className="how" style={{ marginTop: -4 }}>More (right) or less (left) than the average team, not better or worse{b.how_they_play?.every ? " · every game here" : ""}</div>
      {b.how_they_play ? <><SignedBars rows={b.how_they_play.rows} colour={t.orange} /><Explain shows={<T>{b.how_they_play.shows}</T>} for_={b.how_they_play.for_} /></>
        : <Missing why={m.how_they_play} />}</Tile>}
    {b.discipline !== null && <Tile span={5} title="Discipline">
      <div className="how" style={{ marginTop: -4 }}>Extras given away per match, fewest first{b.discipline?.every ? " · every game here" : ""}</div>
      {b.discipline ? <><LeaderBars rows={b.discipline.rows} value="extras" mine={team} height={34 * b.discipline.rows.length + 16} noTeam nameSize={17} valSize={20}
        fmt={(v) => v.toFixed(1)} label="Discipline" />{b.discipline.shows && <Explain shows={<T>{b.discipline.shows}</T>} for_={b.discipline.for_} />}</>
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
          <Explain shows={<T>{b.race.shows}</T>} for_={b.race.for_} /></>}</> : <div className="plain">{b.race.none}</div>) : <Missing why={m.race} />}
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
