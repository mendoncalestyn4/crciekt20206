// Seasons · Competitions (stage 2): one competition as it's run in one season: the league table, the title race, the
// knockouts, every series and the World Test Championship, as the current site's Competitions page shows them.
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { get, type CompPage, remember } from "../api";
import { Explain, Logo, Missing, Pick, three, Tile } from "../kit/base";
import { Bracket, OddsRace } from "../kit/comp";
import { TvTable } from "../kit/blocks";
import { Ladder } from "../kit/season";
import { Grid } from "../kit/teams";
import { f1, f2, overs } from "../format";
import { useReady } from "../ready";
import { Head, useShell } from "../shell/Shell";
import { T } from "../shell/names";

/** The Seasons section's pages, switched from the top of each. */
export const SEASON_PAGES = [{ label: "Competitions", to: "/seasons" }, { label: "Season", to: "/seasons/season" },
  { label: "Season review", to: "/seasons/review" }, { label: "Honours", to: "/seasons/honours" }];

export function Competitions() {
  const { career, noCareer, nation } = useShell();
  const [params] = useSearchParams();
  const go = useNavigate();
  const [cycle, setCycle] = useState("");
  const keep = nation ? `?nation=${encodeURIComponent(nation)}` : "";
  const want = { event: params.get("event") ?? "", season: params.get("season") ?? "", games: params.get("games") ?? "",
    places: params.get("places") ?? "", extra: params.get("extra") ?? "", pick: params.get("pick") ?? "", series: params.get("series") ?? "" };
  const qs = Object.entries(want).map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join("&");
  const q = useQuery({ queryKey: ["competition", qs, career?.name], enabled: Boolean(career), retry: false,
    queryFn: () => get<CompPage>(`/api/competition?${qs}`) });
  useReady(Boolean(q.data || q.error || noCareer), `${qs}|${cycle}`);
  const set = (changes: Record<string, string>) => {
    remember(changes);
    const next: Record<string, string> = { ...want, ...changes };
    if ("event" in changes) Object.assign(next, { season: "", games: "", places: "", extra: "", pick: "", series: "" });
    if ("season" in changes) Object.assign(next, { games: "", places: "", extra: "", series: "" });
    if (nation) next.nation = nation;
    go(`/seasons?${new URLSearchParams(Object.entries(next).filter(([, v]) => v)).toString()}`);
  };
  const head = <Head title="Seasons" crumb="Competitions · tables, brackets and series" chips={SEASON_PAGES.map((p) => p.label)} on={0}
    onChip={(i) => go(`${SEASON_PAGES[i]!.to}${keep}`)} />;
  if (noCareer) return <>{head}<div className="grid"><Tile span={12} title="No career yet"><div className="plain">Add a career in Settings first.</div></Tile></div></>;
  if (q.error) return <>{head}<div className="grid"><Tile span={12}><Missing why={String(q.error)} /></Tile></div></>;
  if (!q.data) return <>{head}<div className="empty">Working out the tables…</div></>;
  const d = q.data, m = d.missing ?? {}, ch = d.choices.find((c) => c.event === d.event);
  const r = d.race?.race, rm = d.race?.missing ?? {};
  const shown = Boolean(d.league || d.knockouts || d.series || d.wtc);
  const cyc = d.wtc ? (cycle && d.wtc.tables[cycle] ? cycle : d.wtc.cycle) : "";
  return (
    <>
      {head}
      <div className="grid">
        <Tile span={12} title="Pick a competition and a season">
          <div className="plain">A competition as it's run: the ODI World Cup on its own, every bilateral ODI series together, each
            County Championship division apart.</div>
          {d.choices.length > 0 && <div className="drops">
            <Pick label="Competition" value={d.event} options={d.choices.map((c) => ({ v: c.event, label: c.event, note: `${c.matches} matches` }))} set={(v) => set({ event: v })} />
            <Pick label="Season" value={d.season} options={ch?.seasons ?? []} set={(v) => set({ season: v })} />
            {d.event && <div className="drop"><Logo comp={d.event} size={44} /></div>}
          </div>}
        </Tile>
        {d.none ? <Tile span={12}><Missing why={d.none} /></Tile> : <>
          {m.league ? <Tile span={12} title="League table"><Missing why={m.league} /></Tile> : d.league && <Tile span={12} title={d.league.title}>
            {d.league.groups.map((g, i) => <div key={i}>{g.label && <div className="glabel">{g.label}</div>}<Grid t={g} keep={keep} />
              {g.note && <div className="note"><T>{g.note}</T></div>}</div>)}
            {d.league.note && <div className="note">{d.league.note}</div>}
          </Tile>}
          {d.race_on && (rm.race ? <Tile span={12} title="Title race"><Missing why={rm.race} /></Tile> : r && <Tile span={12} title="Title race">
            <div className="drops">
              <div className="drop"><label className="droplab" htmlFor="cp-games">League games per team</label>
                <input id="cp-games" className="typed num" type="number" min={1} max={60} value={r.games} onChange={(e) => set({ games: e.target.value })} /></div>
              <div className="drop"><label className="droplab" htmlFor="cp-places">Places that go through{r.many ? " (per group)" : ""}</label>
                <input id="cp-places" className="typed num" type="number" min={1} max={16} value={r.places} disabled={!r.knockouts}
                  onChange={(e) => set({ places: e.target.value })} /></div>
              {r.many && <div className="drop"><label className="droplab" htmlFor="cp-extra" title="The Blast also takes the two best third-placed sides.">…and the best next-placed sides</label>
                <input id="cp-extra" className="typed num" type="number" min={0} max={8} value={r.extra} disabled={!r.knockouts}
                  onChange={(e) => set({ extra: e.target.value })} /></div>}
              {r.teams.length > 0 && <Pick label="Team in colour" value={r.pick} options={r.teams} set={(v) => set({ pick: v })} />}
            </div>
            {r.groups.map((g, i) => <div key={i}>{g.label && <div className="glabel">{g.label}</div>}<Grid t={g} /></div>)}
            {r.caption && <div className="note">{r.caption}</div>}
            {r.lines.length > 0 && <><OddsRace lines={r.lines} team={r.pick} what={r.what} />
              {r.best && <Explain {...three(r)} />}</>}
            <div className="note">{r.note}</div>
          </Tile>)}
          {m.knockouts ? <Tile span={12} title="Knockouts"><Missing why={m.knockouts} /></Tile> : d.knockouts && <Tile span={12} title="Knockouts">
            <Bracket rounds={d.knockouts.rounds} keep={keep} />
            {d.knockouts.champion && <div className="champ">{d.knockouts.champion}</div>}
            <div className="note">Click a match to open its scorecard. The side that went through is lit.</div>
          </Tile>}
          {m.series ? <Tile span={12} title="Series"><Missing why={m.series} /></Tile> : d.series && <>
            <Tile span={12} title="Series"><Grid t={d.series.table} />{d.series.table.note && <div className="note">{d.series.table.note}</div>}</Tile>
            <Tile span={12} title="One series, match by match">
              <div className="drops"><Pick label="Series" value={String(d.series_pick ?? 0)} options={d.series.each.map((s, i) => ({ v: String(i), label: s.label }))}
                set={(v) => set({ series: v })} /></div>
              {(() => { const e = d.series!.each[d.series_pick ?? 0], one = d.series_one, l = one?.ladder;
                if (!e) return null;
                return <>
                  {l ? <><div className="glabel">The series score after each match{l.decider ? " · the decider marked" : ""}</div><Ladder s={l} team={one!.team} />
                    {l.lines && <Explain {...l.lines} />}</>
                    : one?.missing.ladder ? <Missing why={one.missing.ladder} /> : null}
                  <div className="glabel" style={{ marginTop: 16 }}>Every match</div><Grid t={e.matches} keep={keep} />
                </>; })()}
            </Tile>
            {d.series_one?.ladder && (() => { const one = d.series_one!, l = one.ladder!;
              return <>
                <Tile span={6} title="Most runs in the series">
                  <TvTable rows={l.most_runs} mine={one.team} cols={[["Runs", (x) => x.runs], ["Inns", (x) => x.inns], ["HS", (x) => x.hs], ["SR", (x) => (x.balls ? f1((x.runs / x.balls) * 100) : "–")]]} parts={(x) => ({ runs: x.runs, bf: x.balls, inns: x.inns })} /></Tile>
                <Tile span={6} title="Most wickets in the series">
                  <TvTable rows={l.most_wickets} mine={one.team} cols={[["Wkts", (x) => x.wickets], ["Runs", (x) => x.runs], ["Overs", (x) => overs(x.balls)], ["Econ", (x) => f2(x.economy)]]} /></Tile>
              </>; })()}
            {d.series_one?.missing.xi ? <Tile span={12} title="Team of the series"><Missing why={d.series_one.missing.xi} /></Tile>
              : d.series_one?.xi && <Tile span={12} title={d.series_one.xi.title}>{d.series_one.xi.none ? <div className="plain">{d.series_one.xi.none}</div>
                : <><Grid t={d.series_one.xi} keep={keep} />{d.series_one.xi.note && <div className="note">{d.series_one.xi.note}</div>}</>}</Tile>}
          </>}
          {m.wtc ? <Tile span={12} title="World Test Championship"><Missing why={m.wtc} /></Tile> : d.wtc && <Tile span={12} title="World Test Championship">
            <div className="drops"><Pick label="Cycle" value={cyc} options={d.wtc.cycles.map((c) => ({ v: c.key, label: c.label }))} set={setCycle} /></div>
            {d.wtc.tables[cyc] && <><Grid t={d.wtc.tables[cyc]!} />
              {d.wtc.tables[cyc]!.heading && <div className="plain" style={{ marginTop: 12 }}><b>{d.wtc.tables[cyc]!.heading}</b></div>}</>}
            <div className="note">{d.wtc.note}</div>
          </Tile>}
          {!shown && <Tile span={12}><Missing why="No league, knockout or series matches in this competition and season yet." /></Tile>}
        </>}
        {d.every && d.every.rows.length > 0 && <Tile span={12} title="Every competition in this career">
          <Grid t={d.every} />{d.every.note && <div className="note">{d.every.note}</div>}</Tile>}
      </div>
    </>
  );
}
