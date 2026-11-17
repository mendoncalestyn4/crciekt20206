// Seasons · Season review (stage 2): each competition's season in one place: the champions, Team of the Season, the
// leading players, the best matches, the biggest upset, the records broken, your teams' report cards and the most
// valuable players; international cricket gets a calendar-year review, awards style.
import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate, useSearchParams } from "react-router";
import { get, type ReviewPage, type XiGrid } from "../api";
import { Explain, Missing, Num, three, Tile } from "../kit/base";
import { LeaderBars } from "../kit/charts";
import { Grades } from "../kit/myteam";
import { MatchWinners } from "../kit/season";
import { Grid } from "../kit/teams";
import { Wrapped } from "../kit/wrapped";
import { useReady } from "../ready";
import { Head, useShell } from "../shell/Shell";
import { T } from "../shell/names";
import { SEASON_PAGES } from "./Competitions";

function Xi({ xi, span = 12 }: { xi: XiGrid; span?: number }) {
  return <Tile span={span} title={xi.title}>{"none" in xi ? <Missing why={xi.none} /> : <><Grid t={xi} />{xi.note && <div className="note">{xi.note}</div>}</>}</Tile>;
}

export function Review() {
  const { career, noCareer, nation } = useShell();
  const [params] = useSearchParams();
  const go = useNavigate();
  const keep = nation ? `?nation=${encodeURIComponent(nation)}` : "";
  const want = { pick: params.get("pick") ?? "", points: params.get("points") ?? "", wteam: params.get("wteam") ?? "", wfmt: params.get("wfmt") ?? "",
    wview: params.get("wview") ?? "" };
  const qs = Object.entries(want).map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join("&");
  const q = useQuery({ queryKey: ["review", qs, career?.name], enabled: Boolean(career), retry: false,
    queryFn: () => get<ReviewPage>(`/api/review?${qs}`) });
  useReady(Boolean(q.data || q.error || noCareer), qs);
  const set = (changes: Record<string, string>) => {
    const next: Record<string, string> = { ...want, ...changes };
    if ("pick" in changes) Object.assign(next, { wteam: "", wfmt: "" });
    if (nation) next.nation = nation;
    go(`/seasons/review?${new URLSearchParams(Object.entries(next).filter(([, v]) => v)).toString()}`);
  };
  const on = SEASON_PAGES.findIndex((p) => p.to === "/seasons/review");
  const head = <Head title="Seasons" crumb="Season review · the end of the season" chips={SEASON_PAGES.map((p) => p.label)} on={on}
    onChip={(i) => go(`${SEASON_PAGES[i]!.to}${keep}`)} />;
  if (noCareer) return <>{head}<div className="grid"><Tile span={12} title="No career yet"><div className="plain">Add a career on the current site for now.</div></Tile></div></>;
  if (q.error) return <>{head}<div className="grid"><Tile span={12}><Missing why={String(q.error)} /></Tile></div></>;
  if (!q.data) return <>{head}<div className="empty">Reviewing the season…</div></>;
  const d = q.data, yr = d.year?.year, rv = d.season_review?.review, mv = d.mvp?.mvp, wr = d.wrapped?.wrapped;
  const miss = { ...(d.year?.missing ?? {}), ...(d.season_review?.missing ?? {}), ...(d.mvp?.missing ?? {}), ...(d.wrapped?.missing ?? {}) };
  const mine = career?.my_teams[0] ?? null;
  return (
    <>
      {head}
      <div className="grid">
        <Tile span={12} title="Pick a season">
          <div className="plain">Each competition's season in one place. International cricket gets a calendar-year review, awards style.</div>
          {d.choices.length > 0 && <div className="field"><label htmlFor="rv-pick">Season</label>
            <select id="rv-pick" className="pick" value={d.pick} onChange={(e) => set({ pick: e.target.value })}>
              {d.choices.map((c) => <option key={c.key} value={c.key}>{c.label}</option>)}</select></div>}
        </Tile>
        {d.none ? <Tile span={12}><Missing why={d.none} /></Tile> : <>
          {Object.entries(miss).map(([k, v]) => <Tile key={k} span={12} title={k}><Missing why={v} /></Tile>)}
          {wr && <Tile span={12} title="🎁 Your season, wrapped">
            <div className="field" style={{ marginTop: 0 }}>
              <label htmlFor="rv-wteam">Team</label>
              <select id="rv-wteam" className="pick" value={wr.team} onChange={(e) => set({ wteam: e.target.value })}>
                {wr.teams.map((t) => <option key={t}>{t}</option>)}</select>
              <div className="itabs" style={{ gridColumn: "auto", margin: 0 }}>{([["", "This competition"], ["whole", "The whole season, every format"]] as const).map(([v, l]) => (
                <button key={l} className={(wr.view ?? "") === v ? "on" : ""} onClick={() => set({ wview: v })}
                  title={v ? "April to March, everything this team played, added up" : "This competition's season only"}>{l}</button>))}</div>
              {wr.formats.length > 0 && !wr.view && <div className="itabs" style={{ gridColumn: "auto", margin: 0 }}>{wr.formats.map((f) => (
                <button key={f} className={f === wr.format ? "on" : ""} onClick={() => set({ wfmt: f })}>{f}s</button>))}</div>}
            </div>
            {wr.none ? <Missing why={wr.none} /> : <><Wrapped slides={wr.slides ?? []} team={wr.team} section={wr.section ?? ""} season={wr.season ?? ""} keep={keep} />
              {wr.note && <div className="note">{wr.note}</div>}</>}
          </Tile>}
          {yr && <>
            <Tile span={12} title={yr.title}><div className="kpis">{yr.counts.map((c) => (
              <div key={c.label}><span>{c.label}</span><Num v={c.value} px={44} /></div>))}</div></Tile>
            {yr.cricketer && <Tile span={12} title="🏅 Cricketer of the Year · the most match impact across Tests, ODIs and T20Is"><Grid t={yr.cricketer} /></Tile>}
            {yr.formats.map((f) => <div key={f.format} style={{ display: "contents" }}>
              <Tile span={12} title={`${f.format} Player of the Year · ${f.matches} match${f.matches !== 1 ? "es" : ""}`}>
                {f.player ? <Grid t={f.player} /> : <Missing why="Not enough cricket yet." />}
                {f.most && <div className="plain" style={{ marginTop: 10 }}><T>{f.most}</T></div>}</Tile>
              <Xi xi={f.xi} /></div>)}
            <Tile span={12}><div className="note">{yr.note}</div></Tile>
          </>}
          {rv && <>
            <Tile span={12} title={rv.title}>
              {!rv.complete && <div className="plain">This season isn't finished yet, so this is the review so far. It completes itself once the
                final (or the last game) is in.</div>}
              <div className="kpis"><div><span>Matches</span><Num v={rv.matches} px={44} /></div>
                <div><span>Champions</span><div className="pn" style={{ fontSize: 34, overflowWrap: "anywhere" }}>{rv.champion}</div></div></div>
            </Tile>
            <Tile span={5} title="🏆 Champions">
              {rv.champions.length ? rv.champions.map((c) => <div key={c.team + c.section} className="plain"><b>{c.team}</b> · {c.how}
                {c.runners_up && ` · runners-up ${c.runners_up}`}{c.section && ` · ${c.section}`}</div>) : <div className="plain">Not decided yet.</div>}
              {rv.final && <div className="plain" style={{ marginTop: 10 }}>The final: <Link className="lk" to={`/matches/${rv.final.id}${keep}`}>{rv.final.teams}</Link>
                {" · "}{rv.final.result}{rv.final.pom && <> · Player of the Match <T>{rv.final.pom}</T></>}</div>}
            </Tile>
            <Tile span={7} title="Leading players">{rv.leaders ? <Grid t={rv.leaders} /> : <Missing />}</Tile>
            <Xi xi={rv.xi} />
            <Tile span={6} title="⭐ Best matches · rated 0–10 for excitement">
              {rv.best ? <Grid t={rv.best} keep={keep} /> : <div className="plain">No matches rated yet.</div>}
              {rv.upset && <div className="plain" style={{ marginTop: 12 }}><b>😱 Biggest upset</b>
                <div><Link className="lk" to={`/matches/${rv.upset.id}${keep}`}>{rv.upset.text}</Link>, {rv.upset.why}</div></div>}
            </Tile>
            <Tile span={6} title="📜 Records broken this season">
              {rv.records ? <><Grid t={rv.records} />{rv.records.note && <div className="note">{rv.records.note}</div>}</> : <div className="plain">{rv.records_none}</div>}
            </Tile>
            {rv.report_cards.map((r) => <Tile key={r.team} span={12} title={`📋 ${r.team} report card`}>
              <Grades card={r.card} /><div className="note">Grades against the average team this season: A well above, C about average, E well below.</div></Tile>)}
            <Tile span={12}><div className="note">Team of the Season, best matches and upsets use the same rules as the Teams, Matches and Player stories pages.</div></Tile>
          </>}
          {mv && <Tile span={12} title={`🏅 Most valuable players${rv && !rv.complete ? " · so far" : ""}`}
            right={mv.choose ? <div className="itabs" style={{ margin: 0 }}>{([["impact", "Impact points"], ["ipl", "IPL MVP points"]] as const).map(([v, l]) => (
              <button key={v} className={mv.points === v ? "on" : ""} onClick={() => set({ points: v === "impact" ? "" : v })}>{l}</button>))}</div> : undefined}>
            {mv.none ? <Missing why={mv.none} /> : <>
              {mv.table && <Grid t={mv.table} />}
              {mv.bars.length > 0 && <LeaderBars rows={mv.bars} value="value" mine={mine} height={Math.max(220, mv.bars.length * 40)} label="Most valuable players" />}
              {mv.best && <Explain {...three(mv)} />}
              <div className="note">{mv.note}</div></>}
          </Tile>}
          {d.winners?.winners && d.winners.winners.players.length > 0 && <Tile span={12} title={`Match-winners · ${d.winners.winners.team}`}
            right={`${d.winners.winners.wins} wins · the player of the match in each`}>
            <MatchWinners w={d.winners.winners} />
            {d.winners.winners.lines && <Explain {...d.winners.winners.lines} />}
            {!d.winners.winners.yours && <div className="note">Your team didn't play here, so it's the side with the most wins.</div>}</Tile>}
          {d.winners?.missing.winners && <Tile span={12} title="Match-winners"><Missing why={d.winners.missing.winners} /></Tile>}
        </>}
      </div>
    </>
  );
}
