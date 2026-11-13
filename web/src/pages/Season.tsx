// Seasons · Season (stage 2): a whole season (April to March) on one calendar, every result and your fixtures still to
// come; every bilateral series and how it stands; how far each competition has got.
import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate, useSearchParams } from "react-router";
import { get, type SeasonPage } from "../api";
import { Explain, Missing, Num, Tile } from "../kit/base";
import { f0, ord } from "../format";
import { MonthGrid } from "../kit/calendar";
import { TugOfWar } from "../kit/charts";
import { Grid } from "../kit/teams";
import { useReady } from "../ready";
import { Head, useShell } from "../shell/Shell";
import { T } from "../shell/names";
import { SEASON_PAGES } from "./Competitions";

export function Season() {
  const { career, noCareer, nation } = useShell();
  const [params] = useSearchParams();
  const go = useNavigate();
  const keep = nation ? `?nation=${encodeURIComponent(nation)}` : "";
  const want = { team: params.get("team") ?? "", tab: params.get("tab") ?? "", view: params.get("view") ?? "",
    season: params.get("season") ?? "", month: params.get("month") ?? "" };
  const qs = Object.entries(want).map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join("&");
  const q = useQuery({ queryKey: ["season", qs, career?.name], enabled: Boolean(career), retry: false,
    queryFn: () => get<SeasonPage>(`/api/season?${qs}`) });
  useReady(Boolean(q.data || q.error || noCareer), qs);
  const set = (changes: Record<string, string>) => {
    const next: Record<string, string> = { ...want, ...changes };
    if ("team" in changes) Object.assign(next, { season: "", month: "" });
    if (nation) next.nation = nation;
    go(`/seasons/season?${new URLSearchParams(Object.entries(next).filter(([, v]) => v)).toString()}`);
  };
  const on = SEASON_PAGES.findIndex((p) => p.to === "/seasons/season");
  const head = <Head title="Seasons" crumb="Season · calendar and series" chips={SEASON_PAGES.map((p) => p.label)} on={on}
    onChip={(i) => go(`${SEASON_PAGES[i]!.to}${keep}`)} />;
  if (noCareer) return <>{head}<div className="grid"><Tile span={12} title="No career yet"><div className="plain">Add a career on the current site for now.</div></Tile></div></>;
  if (q.error) return <>{head}<div className="grid"><Tile span={12}><Missing why={String(q.error)} /></Tile></div></>;
  if (!q.data) return <>{head}<div className="empty">Laying out the season…</div></>;
  const d = q.data, cal = d.calendar, sr = d.series, pr = d.progress;
  return (
    <>
      {head}
      <div className="grid">
        <Tile span={12} title="Pick a team">
          <div className="plain">A whole season (April to March) on one calendar: every result, and your fixtures still to come; every
            bilateral series and how it stands, and how far each competition has got this season.</div>
          <div className="field"><label htmlFor="se-team">Team</label>
            <select id="se-team" className="pick" value={d.team} onChange={(e) => set({ team: e.target.value })}>
              {d.teams.map((t) => <option key={t}>{t}</option>)}</select></div>
        </Tile>
        {d.none ? <Tile span={12}><Missing why={d.none} /></Tile> : <>
          {d.ranks && d.ranks.rows.length > 0 && <Tile span={12} title={`Where ${d.team} rank`} right={`this season · ${d.ranks.season}`}>
            <div className="ranks">{d.ranks.rows.map((r) => (
              <div key={r.section} className="bf-side"><div className="k">{r.section}</div>
                <div className="rk"><span><Num v={ord(r.runs_rank)} px={40} /><small>of {r.teams} teams by runs ({f0(r.runs)})</small>
                    {r.runs_rank > 1 && <small>most: {r.runs_top}</small>}</span>
                  <span><Num v={ord(r.wickets_rank)} px={40} /><small>of {r.teams} by wickets ({r.wickets})</small>
                    {r.wickets_rank > 1 && <small>most: {r.wickets_top}</small>}</span></div>
                <div className="note" style={{ marginTop: 4 }}>{r.matches} matches</div></div>))}</div>
            {d.ranks.note && <div className="note">{d.ranks.note}</div>}</Tile>}
          <div className="itabs">{d.tabs.map((x, i) => (
            <button key={x} className={x === d.tab ? "on" : ""} onClick={() => set({ tab: i === 0 ? "" : x })}>{x}</button>))}</div>
          {cal && (cal.none ? <Tile span={12}><Missing why={cal.none} /></Tile> : <Tile span={12} title={cal.view === "season" ? "The season" : "One month"}
            right={<div className="itabs" style={{ margin: 0 }}>{([["season", "Whole season"], ["month", "One month"]] as const).map(([v, l]) => (
              <button key={v} className={cal.view === v ? "on" : ""} onClick={() => set({ view: v === "season" ? "" : v })}>{l}</button>))}</div>}>
            <div className="field">
              {cal.view === "season" ? <><label htmlFor="se-season">Season</label>
                <select id="se-season" className="pick" value={cal.season} onChange={(e) => set({ season: e.target.value })}>
                  {cal.seasons.map((s) => <option key={s.key} value={s.key}>{s.label}</option>)}</select></>
                : <><label htmlFor="se-month">Month</label>
                  <select id="se-month" className="pick" value={cal.month} onChange={(e) => set({ month: e.target.value })}>
                    {cal.months.map((s) => <option key={s.key} value={s.key}>{s.label}</option>)}</select></>}
            </div>
            {cal.view === "season" ? <div className="cms" data-chart>{cal.grid.map((mo) => <MonthGrid key={mo.key} mo={mo} keep={keep} today={cal.today} />)}</div>
              : cal.grid[0] && <div data-chart><MonthGrid mo={cal.grid[0]} big keep={keep} today={cal.today} /></div>}
            {cal.caption && <div className="note">{cal.caption}</div>}
            {cal.shows && <Explain shows={cal.shows} for_={cal.for_} />}
          </Tile>)}
          {sr && (sr.none ? <Tile span={12}><Missing why={sr.none} /></Tile> : <>
            {sr.live && <Tile span={12} title="Still going · each side's chance of winning the series"><Grid t={sr.live} />
              {sr.live.note && <div className="note">{sr.live.note}</div>}</Tile>}
            {(sr.tugs ?? []).map((tg) => <Tile key={tg.id} span={6} title={`${tg.section} · ${tg.team} v ${tg.opp}`}
              right={tg.story.complete ? "finished" : "under way"}>
              <TugOfWar matches={tg.matches} progress={tg.progress} team={tg.team ?? ""} opp={tg.opp} height={280} />
              <div className="note">Above the line {tg.team} lead, below it {tg.opp} do. <T>{tg.title}</T></div>
              {tg.shows && <Explain shows={tg.shows} for_={tg.for_} />}</Tile>)}
            <Tile span={12} title="Finished series · newest first">
              {sr.done ? <Grid t={sr.done} /> : <div className="plain">None finished yet.</div>}
              {sr.note && <div className="note">{sr.note}</div>}</Tile>
          </>)}
          {pr && (pr.none ? <Tile span={12}><Missing why={pr.none} /></Tile> : <Tile span={12} title="How far each competition has got">
            <div className="scrollx"><table className="c"><thead><tr><th>Competition</th><th>Played</th><th>Progress</th><th>Stage</th><th>Top of the table</th></tr></thead>
              <tbody>{pr.rows.map((r) => (
                <tr key={r.name}><td><Link className="lk" to={`/seasons?event=${encodeURIComponent(r.event)}&season=${encodeURIComponent(r.season)}${nation ? `&nation=${encodeURIComponent(nation)}` : ""}`}>{r.name}</Link></td>
                  <td><span className="why">{r.played}</span></td>
                  <td>{r.pct != null && <div className="prog" title={`${Math.round(r.pct)}%`}><i style={{ width: `${r.pct}%` }} /></div>}</td>
                  <td><span className="why">{r.stage}</span></td><td><span className="why">{r.leader}</span></td></tr>))}</tbody></table></div>
            {pr.note && <div className="note">{pr.note}</div>}
          </Tile>)}
        </>}
      </div>
    </>
  );
}
