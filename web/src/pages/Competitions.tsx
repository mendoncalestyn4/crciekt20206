// Seasons · Competitions (stage 2): one competition as it's run in one season: the league table, the title race, the
// knockouts, every series and the World Test Championship, as the current site's Competitions page shows them.
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { get, type CompPage } from "../api";
import { Explain, Logo, Missing, Tile } from "../kit/base";
import { Bracket, OddsRace } from "../kit/comp";
import { Grid } from "../kit/teams";
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
  const [series, setSeries] = useState(0);
  const [cycle, setCycle] = useState("");
  const keep = nation ? `?nation=${encodeURIComponent(nation)}` : "";
  const want = { event: params.get("event") ?? "", season: params.get("season") ?? "", games: params.get("games") ?? "",
    places: params.get("places") ?? "", extra: params.get("extra") ?? "", pick: params.get("pick") ?? "" };
  const qs = Object.entries(want).map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join("&");
  const q = useQuery({ queryKey: ["competition", qs, career?.name], enabled: Boolean(career), retry: false,
    queryFn: () => get<CompPage>(`/api/competition?${qs}`) });
  useReady(Boolean(q.data || q.error || noCareer), `${qs}|${series}|${cycle}`);
  const set = (changes: Record<string, string>) => {
    const next: Record<string, string> = { ...want, ...changes };
    if ("event" in changes) Object.assign(next, { season: "", games: "", places: "", extra: "", pick: "" });
    if ("season" in changes) Object.assign(next, { games: "", places: "", extra: "" });
    if (nation) next.nation = nation;
    setSeries(0);
    go(`/seasons?${new URLSearchParams(Object.entries(next).filter(([, v]) => v)).toString()}`);
  };
  const head = <Head title="Seasons" crumb="Competitions · tables, brackets and series" chips={SEASON_PAGES.map((p) => p.label)} on={0}
    onChip={(i) => go(`${SEASON_PAGES[i]!.to}${keep}`)} />;
  if (noCareer) return <>{head}<div className="grid"><Tile span={12} title="No career yet"><div className="plain">Add a career on the current site for now.</div></Tile></div></>;
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
          {d.choices.length > 0 && <div className="field">
            <label htmlFor="cp-ev">Competition</label>
            <select id="cp-ev" className="pick" value={d.event} onChange={(e) => set({ event: e.target.value })}>
              {d.choices.map((c) => <option key={c.event} value={c.event}>{c.event} · {c.matches} matches</option>)}</select>
            <label htmlFor="cp-season">Season</label>
            <select id="cp-season" className="pick" value={d.season} onChange={(e) => set({ season: e.target.value })}>
              {(ch?.seasons ?? []).map((s) => <option key={s}>{s}</option>)}</select>
            {d.event && <Logo comp={d.event} size={44} />}
          </div>}
        </Tile>
        {d.none ? <Tile span={12}><Missing why={d.none} /></Tile> : <>
          {m.league ? <Tile span={12} title="League table"><Missing why={m.league} /></Tile> : d.league && <Tile span={12} title={d.league.title}>
            {d.league.groups.map((g, i) => <div key={i}>{g.label && <div className="glabel">{g.label}</div>}<Grid t={g} keep={keep} />
              {g.note && <div className="note"><T>{g.note}</T></div>}</div>)}
            {d.league.note && <div className="note">{d.league.note}</div>}
          </Tile>}
          {d.race_on && (rm.race ? <Tile span={12} title="Title race"><Missing why={rm.race} /></Tile> : r && <Tile span={12} title="Title race">
            <div className="field">
              <label htmlFor="cp-games">League games per team</label>
              <input id="cp-games" className="typed num" type="number" min={1} max={60} value={r.games} onChange={(e) => set({ games: e.target.value })} />
              <label htmlFor="cp-places">Places that go through{r.many ? " (per group)" : ""}</label>
              <input id="cp-places" className="typed num" type="number" min={1} max={16} value={r.places} disabled={!r.knockouts}
                onChange={(e) => set({ places: e.target.value })} />
              {r.many && <><label htmlFor="cp-extra" title="The Blast also takes the two best third-placed sides.">…and the best next-placed sides</label>
                <input id="cp-extra" className="typed num" type="number" min={0} max={8} value={r.extra} disabled={!r.knockouts}
                  onChange={(e) => set({ extra: e.target.value })} /></>}
              {r.teams.length > 0 && <><label htmlFor="cp-pick">Team in colour</label>
                <select id="cp-pick" className="pick" value={r.pick} onChange={(e) => set({ pick: e.target.value })}>
                  {r.teams.map((t) => <option key={t}>{t}</option>)}</select></>}
            </div>
            {r.groups.map((g, i) => <div key={i}>{g.label && <div className="glabel">{g.label}</div>}<Grid t={g} /></div>)}
            {r.caption && <div className="note">{r.caption}</div>}
            {r.lines.length > 0 && <><OddsRace lines={r.lines} team={r.pick} what={r.what} />
              {r.shows && <Explain shows={r.shows} for_={r.for_ ?? ""} />}</>}
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
              <div className="field"><label htmlFor="cp-series">Series</label>
                <select id="cp-series" className="pick" value={series} onChange={(e) => setSeries(Number(e.target.value))}>
                  {d.series.each.map((s, i) => <option key={i} value={i}>{s.label}</option>)}</select></div>
              {d.series.each[series] && <Grid t={d.series.each[series]!.matches} keep={keep} />}
            </Tile>
          </>}
          {m.wtc ? <Tile span={12} title="World Test Championship"><Missing why={m.wtc} /></Tile> : d.wtc && <Tile span={12} title="World Test Championship">
            <div className="field"><label htmlFor="cp-cycle">Cycle</label>
              <select id="cp-cycle" className="pick" value={cyc} onChange={(e) => setCycle(e.target.value)}>
                {d.wtc.cycles.map((c) => <option key={c.key} value={c.key}>{c.label}</option>)}</select></div>
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
