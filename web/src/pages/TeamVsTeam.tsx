// Team v team (stage 2): two teams in one competition and season, against each other (only their meetings) or each
// against anyone (each side's own games, to size up two sides that haven't met), at any ground or one side's home.
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import { get, type TvtPage, remember } from "../api";
import { Explain, Logo, Missing, Num, Tile } from "../kit/base";
import { BatFirstSides } from "../kit/season";
import { Grid, TapeBars, TeamBars, TwoScatter } from "../kit/teams";
import { dayY, NO_MATCHES } from "../format";
import { useReady } from "../ready";
import { Head, useShell } from "../shell/Shell";
import { T } from "../shell/names";
import { TEAM_PAGES } from "./Teams";

export function TeamVsTeam() {
  const { career, noCareer, nation } = useShell();
  const [params] = useSearchParams();
  const go = useNavigate();
  const [all, setAll] = useState(false);
  const keep = nation ? `?nation=${encodeURIComponent(nation)}` : "";
  const want = { section: params.get("section") ?? "", season: params.get("season") ?? "", a: params.get("a") ?? "",
    b: params.get("b") ?? "", which: params.get("which") ?? "", ground: params.get("ground") ?? "" };
  const qs = Object.entries(want).map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join("&");
  const q = useQuery({ queryKey: ["teamvteam", qs, career?.name], enabled: Boolean(career), retry: false,
    queryFn: () => get<TvtPage>(`/api/teamvteam?${qs}`) });
  useReady(Boolean(q.data || q.error || noCareer), qs);
  const set = (changes: Record<string, string>) => {
    remember(changes);
    const next: Record<string, string> = { ...want, ...changes };
    if ("section" in changes) Object.assign(next, { season: "", a: want.a, b: "", which: "", ground: "" });
    if ("a" in changes || "b" in changes || "season" in changes) Object.assign(next, { which: "", ground: "" });
    if ("which" in changes) next.ground = "";
    if (nation) next.nation = nation;
    go(`/teams/vs?${new URLSearchParams(Object.entries(next).filter(([, v]) => v)).toString()}`);
  };
  const head = <Head title="Teams" crumb="Team v team · head to head" chips={TEAM_PAGES.map((p) => p.label)} on={1}
    onChip={(i) => go(`${TEAM_PAGES[i]!.to}${keep}`)} />;
  if (noCareer) return <>{head}<div className="grid"><Tile span={12} title="No career yet"><div className="plain">Add a career on the current site for now.</div></Tile></div></>;
  if (q.error) return <>{head}<div className="grid"><Tile span={12}><Missing why={String(q.error)} /></Tile></div></>;
  if (!q.data) return <>{head}<div className="empty">Putting the two teams side by side…</div></>;
  const d = q.data, p = d.page;
  if (!p) return <>{head}<div className="grid"><Tile span={12}><Missing why={NO_MATCHES} /></Tile></div></>;
  const ch = d.choices.find((c) => c.section === p.section)!;
  const b = p.body, m = b?.missing ?? {};
  const mark = (t: string) => `${t}${p.todo.includes(t) ? " (0 games)" : ""}`;
  return (
    <>
      {head}
      <div className="grid">
        <Tile span={12} title="Pick a competition and two teams">
          <div className="plain">Against each other: only their meetings, at any ground or one side's home. Against anyone: each team's own games, to
            size up two sides that haven't met (home games next to away games, as for a game at one team's ground).</div>
          <div className="field">
            <label htmlFor="tv-sec">Competition</label>
            <select id="tv-sec" className="pick" value={p.section} onChange={(e) => set({ section: e.target.value })}>
              {d.choices.map((c) => <option key={c.section} value={c.section}>{c.section} · {c.matches} matches</option>)}</select>
            <label htmlFor="tv-season">Season</label>
            <select id="tv-season" className="pick" value={p.season} onChange={(e) => set({ season: e.target.value === "All seasons" ? "" : e.target.value })}>
              {["All seasons", ...ch.seasons].map((s) => <option key={s}>{s}</option>)}</select>
          </div>
          {p.teams.length >= 2 && <div className="field">
            <label htmlFor="tv-a">Team A</label>
            <select id="tv-a" className="pick" value={p.a} onChange={(e) => set({ a: e.target.value, b: "" })}>
              {p.teams.map((t) => <option key={t} value={t}>{mark(t)}</option>)}</select>
            <label htmlFor="tv-b">Team B</label>
            <select id="tv-b" className="pick" value={p.b} onChange={(e) => set({ b: e.target.value })}>
              {(p.others ?? []).map((t) => <option key={t} value={t}>{mark(t)}</option>)}</select>
          </div>}
          {p.grounds.length > 0 && <>
            <div className="field"><label>Matches</label><div className="itabs" style={{ gridColumn: "auto", margin: 0 }}>
              {[["each", "Against each other"], ["any", "Against anyone"]].map(([k, l]) => (
                <button key={k} className={k === p.which ? "on" : ""} onClick={() => set({ which: k! })}>{l}</button>))}</div></div>
            <div className="field"><label>Where</label><div className="itabs" style={{ gridColumn: "auto", margin: 0 }}>
              {p.grounds.map((g) => <button key={g.key} className={g.key === p.ground ? "on" : ""} onClick={() => set({ ground: g.key })}>{g.label}</button>)}</div></div>
            {p.where_help && <div className="note">{p.where_help}</div>}</>}
        </Tile>
        {p.none ? <Tile span={12} title={p.teams.length >= 2 ? `${p.a} v ${p.b}` : p.section}><div className="plain"><T>{p.none}</T></div></Tile> : !b ? null : <>
          {p.info && <Tile span={12} title="Whose games these are"><div className="plain"><T>{p.info}</T></div></Tile>}
          {b.tiles ? b.tiles.map((tl, i) => (
            <Tile key={tl.team} span={6} title={tl.team} className={i === 0 ? "tvA" : "tvB"}>
              <div className="row2" style={{ gap: 18, flexWrap: "wrap" }}><Logo team={tl.team} size={64} />
                <div className="kpis">{tl.figures.map((f) => <div key={f.k}><span>{f.k}</span><Num v={f.v} px={30} style={f.up ? { color: "var(--win)" } : undefined} /></div>)}</div></div>
              <div className="note">{tl.sub}</div>
            </Tile>)) : <Tile span={12}><Missing why={m.tiles} /></Tile>}
          <Tile span={7} title="Tale of the tape">
            {b.tape ? <><div className="plain"><b>{b.tape.verdict}</b></div><TapeBars rows={b.tape.rows} a={p.a} b={p.b} />
              <Explain shows={<T>{b.tape.shows}</T>} for_={b.tape.for_} /></> : <Missing why={m.tape} />}</Tile>
          <Tile span={5} title="Head to head">
            {!b.meetings ? <Missing why={m.meetings} /> : b.meetings.none ? <div className="plain"><T>{b.meetings.none}</T></div> : <>
              <div className="plain"><b><T>{b.meetings.line}</T></b></div>
              <div className="meets">{b.meetings.rows.slice(0, 8).map((r) => (
                <Link key={r.id} to={`/matches/${r.id}${keep}`} className="meet"><b>{dayY(r.date)}</b>{r.stage ? ` · ${r.stage}` : ""} · {r.match}
                  <span className="how">{r.result}</span></Link>))}</div>
              {b.meetings.rows.length > 8 && (all
                ? <div className="meets">{b.meetings.rows.slice(8).map((r) => (
                  <Link key={r.id} to={`/matches/${r.id}${keep}`} className="meet"><b>{dayY(r.date)}</b>{r.stage ? ` · ${r.stage}` : ""} · {r.match}
                    <span className="how">{r.result}</span></Link>))}</div>
                : <button className="btn quiet" style={{ marginTop: 10 }} onClick={() => setAll(true)}>All {b.meetings.rows.length} meetings</button>)}</>}
          </Tile>
          {b.bat_first ? b.bat_first.sides.map((x, i) => (
            <Tile key={x.team} span={6} title={`${x.team}: batting first or ${x.multi ? "batting second" : "chasing"}`} className={i === 0 ? "tvA" : "tvB"}>
              <BatFirstSides bf={x} who={x.team} />
              {i === 0 ? <div className="note">Games shortened by rain are left out of the totals.</div> : null}
              <Explain shows={<T>{b.bat_first!.shows}</T>} for_={b.bat_first!.for_} /></Tile>))
            : <Tile span={12} title="Batting first or chasing"><Missing why={m.bat_first} /></Tile>}
          <div className="part"><span className="tl2">Player by player</span></div>
          {([["bat_dots", "Batters: runs v balls faced"], ["bowl_dots", "Bowlers: wickets v balls bowled"]] as const).map(([k, title]) => {
            const s = b[k];
            return <Tile key={k} span={6} title={title}>
              {s ? <><TwoScatter points={s.points} a={p.a} slope={s.slope} x={s.x} y={s.y} />
                <Explain shows={<T>{s.shows}</T>} for_={s.for_} />
                <ul className="dots">{k === "bat_dots" && <li><b>Gold</b>: {p.a}. <b>Blue</b>: {p.b}.</li>}
                  {s.keys.map((x, i) => <li key={x}>{i === 0 ? `${x.replace(/\.$/, "")} (${s.line}).` : x}</li>)}</ul></>
                : <Missing why={m[k]} />}</Tile>;
          })}
          {([["above", "Every batter: runs above average"], ["saved", "Every bowler: runs saved"]] as const).map(([k, title]) => {
            const s = b[k];
            return <Tile key={k} span={6} title={title}>
              {s ? <><TeamBars rows={s.rows} a={p.a} /><Explain shows={<T>{s.shows}</T>} for_={s.for_} /></> : <Missing why={m[k]} />}</Tile>;
          })}
          <Tile span={12} title="Top performers side by side">{b.top ? <Grid t={b.top} keep={keep} /> : <Missing why={m.top} />}</Tile>
        </>}
      </div>
    </>
  );
}
