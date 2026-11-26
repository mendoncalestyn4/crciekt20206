// Insights (stage 3): questions about a whole competition, one at a time (a T20 total means nothing next to a Test's):
// is this total enough, the score to aim for against every side (new, your answer 7), the chase calculator, home
// advantage, season by season, breakout players and innings by innings. Every number comes from the server
// (server/insightspage.py); the page only shows it.
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { get, type AnalyticsPage, type ArcTable, type InsightsPage, type NGrid, type Quad, remember } from "../api";
import { Explain, Missing, Num, Pick, Tile, three } from "../kit/base";
import { PName } from "../kit/base";
import { ArcLines, HomeBars, Quadrant, SeasonLine } from "../kit/insights";
import { BatFirstSides, MatchWinners, StrengthPanel } from "../kit/season";
import { Grid, SignedBars } from "../kit/teams";
import { T } from "../shell/names";
import { useReady } from "../ready";
import { Head, useShell } from "../shell/Shell";
import { useTheme } from "../theme";

export const INSIGHT_PAGES = [{ label: "Insights", to: "/insights" }, { label: "Analytics", to: "/insights/analytics" }];

export function InsightsHead({ on, crumb }: { on: number; crumb: string }) {
  const go = useNavigate();
  const { nation } = useShell();
  const keep = nation ? `?nation=${encodeURIComponent(nation)}` : "";
  return <Head title="Insights" crumb={crumb} chips={INSIGHT_PAGES.map((p) => p.label)} on={on} onChip={(i) => go(`${INSIGHT_PAGES[i]!.to}${keep}`)} />;
}

const KEYS = ["tab", "section", "season", "team", "score", "target", "now", "down", "min"];

/** A number typed into the page: sent once you stop typing (or press Enter), so a three-figure score isn't asked for
 *  three times on the way. */
function Typed({ id, label, value, min, max, set }: { id: string; label: string; value: number; min: number; max: number; set: (v: string) => void }) {
  const [text, setText] = useState(String(value));
  useEffect(() => setText(String(value)), [value]);
  useEffect(() => {
    if (text === String(value) || text.trim() === "" || !Number.isFinite(Number(text))) return;
    const wait = window.setTimeout(() => set(text), 450);
    return () => window.clearTimeout(wait);
  }, [text, value, set]);
  return (
    <div className="drop"><label className="droplab" htmlFor={id}>{label}</label>
      <input id={id} className="typed num" type="number" min={min} max={max} value={text} onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => { if (e.key === "Enter" && text.trim() !== "") set(text); }} /></div>
  );
}

export function Insights() {
  const { career, noCareer, nation } = useShell();
  const t = useTheme();
  const [params] = useSearchParams();
  const go = useNavigate();
  const want = Object.fromEntries(KEYS.map((k) => [k, params.get(k) ?? ""]));
  const qs = KEYS.filter((k) => want[k]).map((k) => `${k}=${encodeURIComponent(want[k]!)}`).join("&");
  const q = useQuery({ queryKey: ["insights", qs, career?.name], enabled: Boolean(career), retry: false,
    queryFn: () => get<InsightsPage>(`/api/insights?${qs}`), placeholderData: (was) => was });   // the page stays while the next answer comes
  useReady(Boolean(q.data || q.error || noCareer), qs);
  const set = (changes: Record<string, string>) => {
    if (changes.section) remember({ section: changes.section });
    const next: Record<string, string> = { ...want, ...changes };
    if ("section" in changes) Object.assign(next, { season: "", score: "", target: "", now: "" });
    if ("tab" in changes) Object.assign(next, { season: "", score: "", target: "", now: "", down: "", min: "" });
    if (nation) next.nation = nation;
    go(`/insights?${new URLSearchParams(Object.entries(next).filter(([, v]) => v)).toString()}`);
  };
  const head = <InsightsHead on={0} crumb="The bigger picture · what wins games here" />;
  if (noCareer) return <>{head}<div className="grid"><Tile span={12} title="No career yet"><div className="plain">Add a career in Settings first.</div></Tile></div></>;
  if (q.error) return <>{head}<div className="grid"><Tile span={12}><Missing why={String(q.error)} /></Tile></div></>;
  if (!q.data) return <>{head}<div className="empty">Working it out…</div></>;
  const d = q.data;
  if (!d.choices.length) return <>{head}<div className="grid"><Tile span={12}><Missing why={d.none} /></Tile></div></>;
  const tab = d.tab;
  const note = (x: string) => `${d.choices.find((c) => c.section === x)?.matches ?? ""} matches`;
  const comp = d.options && d.section ? <Pick label="Competition" value={d.section} options={d.options.map((c) => ({ v: c, label: c, note: note(c) }))}
    set={(v) => set({ section: v })} /> : null;
  return (
    <>
      {head}
      <div className="grid">
        <div className="intro">Questions about a whole competition: what total wins games, how much home matters, how scoring changes from season to
          season, and who has suddenly got better.</div>
        <div className="itabs">{d.tabs.map((x, i) => (
          <button key={x} className={x === tab ? "on" : ""} onClick={() => set({ tab: i === 0 ? "" : x })}>{x}</button>))}</div>

        {tab === d.tabs[0] && <>
          <Tile span={12} className="pickbar"><div className="drops">
            {comp}
            {d.seasons && <Pick label="Season" value={d.season ?? ""} options={[{ v: "", label: "All seasons" }, ...d.seasons]} set={(v) => set({ season: v })} />}
            {d.score != null && <Typed id="in-score" label={`Type a ${d.what}`} value={d.score} min={0} max={1500} set={(v) => set({ score: v })} />}
            {d.teams && <Pick label="Only this team's games" value={d.team ?? ""} options={d.teams} set={(v) => set({ team: v })} />}
          </div></Tile>
          {d.none ? <Tile span={12}><Missing why={d.none} /></Tile> : <>
            {d.board && <Tile span={12} title={d.board.label}>
              <div className="kpis"><div><span>Won with {d.score} or more</span><Num v={d.board.pct} px={56} /></div></div>
              <div className="plain" style={{ marginTop: 6 }}>{d.board.pct} {d.board.line}. {d.board.res}.</div></Tile>}
            {d.sides?.map((s) => (
              <Tile key={s.title} span={6} title={<T>{s.title}</T>}>
                {s.none ? <div className="plain">{s.none}</div> : <>
                  <div className="kpis"><div><span>{s.label}</span><Num v={s.value} px={44} />{s.small && <span className="why" style={{ marginLeft: 10 }}>{s.small}</span>}</div></div>
                  <div className="note">{s.note}</div></>}
              </Tile>))}
            {d.sides_note && <div className="note" style={{ gridColumn: "span 12" }}>{d.sides_note}</div>}
            {d.bands && <Tile span={12} title={`Win % batting first, by ${d.what}`} right={`bands of ${d.bands.size} runs`}>
              <SignedBars rows={d.bands.rows} colour={t.blue} /><Explain {...three(d.bands)} /></Tile>}
            {d.strong && <Tile span={12} title="Is it enough against a good side?" right="the stronger and the weaker half">
              <div className="plain" style={{ marginBottom: 8 }}>Win % batting first by {d.what}, against the stronger and the weaker half of the teams
                (ranked by win % here, each counted as if it had already won 2 and lost 2).</div>
              <Grid t={d.strong} />{d.strong.note && <div className="note">{d.strong.note}</div>}</Tile>}
          </>}
        </>}

        {tab === d.tabs[1] && <>
          <Tile span={12} className="pickbar"><div className="drops">
            {comp}
            {d.teams && <Pick label="Team" value={d.team ?? ""} options={d.teams} set={(v) => set({ team: v })} />}
          </div></Tile>
          <Tile span={12} title={d.kind === "multi" ? `🎯 ${d.team}: first-innings totals that won, drew and lost` : `🎯 ${d.team}: the score to aim for batting first`}>
            {d.aim_none ? <Missing why={d.aim_none} /> : d.aim && <><Grid t={d.aim} />{d.aim.note && <div className="note"><T>{d.aim.note}</T></div>}</>}
            {d.aim_lines && <Explain is_={d.aim_lines.is_} for_={d.aim_lines.for_} />}
          </Tile>
          {d.bat_first && <Tile span={6} title="Batting first v chasing"><BatFirstSides bf={d.bat_first} who={d.bat_first.who} /><Explain {...three(d.bat_first)} /></Tile>}
          {d.strength && <Tile span={d.bat_first ? 6 : 12} title="Against stronger and weaker sides"><StrengthPanel rows={d.strength.rows} lanes={d.strength.lanes} who={d.team} />
            <Explain {...three(d.strength)} /></Tile>}
        </>}

        {tab === d.tabs[2] && <>
          <Tile span={12} className="pickbar"><div className="drops">
            {comp}
            {d.target != null && <Typed id="in-target" label="Target" value={d.target} min={1} max={1000} set={(v) => set({ target: v })} />}
            {d.now != null && <Typed id="in-now" label="Score now" value={d.now} min={0} max={1000} set={(v) => set({ now: v })} />}
            {d.down != null && <Pick label="Wickets down" value={String(d.down)} options={Array.from({ length: 10 }, (_, i) => String(i))} set={(v) => set({ down: v })} />}
          </div></Tile>
          <Tile span={12} title="The chasing side's chance">
            {d.won ? <div className="plain">{d.won}</div> : d.chase_none ? <Missing why={d.chase_none} /> : <>
              <div className="kpis">{d.kpis?.map((k) => <div key={k.k}><span>{k.k}</span><Num v={k.v} px={48} /></div>)}</div>
              <div className="plain" style={{ marginTop: 8 }}>{d.line}</div>
              {d.table && <div style={{ marginTop: 10 }}><Grid t={d.table} />{d.table.note && <div className="note">{d.table.note}</div>}</div>}</>}
          </Tile>
        </>}

        {tab === d.tabs[3] && (d.none ? <Tile span={12}><Missing why={d.none} /></Tile> : d.home &&
          <Tile span={12} title="Home wins against away wins, in every competition" right="finished matches at home grounds">
            <HomeBars rows={d.home.rows} /><Explain {...three(d.home)} /></Tile>)}

        {tab === d.tabs[4] && <>
          <Tile span={12} className="pickbar"><div className="drops">{comp}</div></Tile>
          {d.one && <Tile span={12}><div className="plain">{d.one}</div></Tile>}
          {d.charts?.map((c) => <Tile key={c.id} span={6} title={c.label}><SeasonLine c={c} /><Explain {...three(c)} /></Tile>)}
        </>}

        {tab === d.tabs[5] && <>
          <Tile span={12} className="pickbar"><div className="drops">
            {comp}
            {d.seasons && <Pick label="Season" value={d.season ?? ""} options={d.seasons} set={(v) => set({ season: v })} />}
            {d.mins && d.earlier && <Pick label="Minimum innings in both" value={String(d.min)} options={d.mins.map(String)} set={(v) => set({ min: v })} />}
          </div>
          {d.earlier && <div className="note">Innings needed in this season and in the earlier ones.</div>}</Tile>
          {d.first ? <Tile span={12}><div className="plain">{d.first}</div></Tile> : <>
            {d.parts?.map((p) => (
              <Tile key={p.title} span={6} title={p.title} right={p.sub}>
                {p.none ? <div className="plain">{p.none}</div> : p.rows && <><SignedBars rows={p.rows} /><Explain {...three(p)} /></>}
              </Tile>))}
            {d.fading && <Tile span={12} title={d.fading.title} right={d.fading.sub}>
              {d.fading.none ? <div className="plain">{d.fading.none}</div> : <><table className="c"><thead><tr><th>Player</th><th>Team</th><th>Fading in</th>
                <th className="r">Drop</th><th>Suggested replacement</th></tr></thead><tbody>{d.fading.rows?.map((r) => (
                <tr key={r.player + r.what}><td><PName p={r.player} px={21} /><div className="how">{r.line}</div></td><td><span className="why">{r.team}</span></td>
                  <td><span className="why">{r.what}</span></td><td className="r"><span className="tn">{r.drop}</span></td><td><span className="why">{r.pick}</span></td></tr>))}</tbody></table>
                {d.fading.note && <div className="note">{d.fading.note}</div>}</>}</Tile>}
            {d.note && <div className="note" style={{ gridColumn: "span 12" }}>{d.note}</div>}
          </>}
        </>}

        {tab === d.tabs[6] && (d.none ? <Tile span={12}><Missing why={d.none} /></Tile> : <>
          <Tile span={12} className="pickbar"><div className="drops">{comp}</div></Tile>
          <Tile span={12} title="Each innings of the match" right="how much harder batting gets as the pitch wears">
            {d.innings_none ? <div className="plain">{d.innings_none}</div> : d.innings && <><SignedBars rows={d.innings.rows} colour={t.blue} /><Explain {...three(d.innings)} /></>}
          </Tile>
          <Tile span={6} title="First-innings lead" right="the side that led">
            {d.lead_none ? <div className="plain">{d.lead_none}</div> : d.lead && <><Grid t={d.lead} />{d.lead.note && <div className="note">{d.lead.note}</div>}</>}
          </Tile>
          <Tile span={6} title="Follow-on and declarations" right="how often each won">
            {d.follow_none ? <div className="plain">{d.follow_none}</div> : d.follow && <><Grid t={d.follow} />{d.follow.note && <div className="note">{d.follow.note}</div>}</>}
          </Tile>
        </>)}

        {tab === "Career arc" && <>
          <Tile span={12} className="pickbar"><div className="drops">{comp}</div></Tile>
          {d.arc_none ? <Tile span={12}><div className="plain">{d.arc_none}</div></Tile> : <>
            {d.arc_charts?.map((c) => <Tile key={c.id} span={6} title={c.title} right={c.sub}>
              {c.none ? <div className="plain">{c.none}</div> : <><ArcLines c={c} /><Explain {...three(c)} /></>}</Tile>)}
            {d.arc_mine && <ArcTiles t={d.arc_mine} />}
            {d.arc_top && <ArcTiles t={d.arc_top} />}
            {d.arc_note && <div className="note" style={{ gridColumn: "span 12" }}>{d.arc_note}</div>}
          </>}
        </>}
      </div>
    </>
  );
}

/** A table of players against the usual career curve: what they did, the usual change over the same seasons, and the
 *  verdict (ahead in the win colour, behind in the loss colour). */
function ArcTiles({ t }: { t: ArcTable }) {
  return (
    <Tile span={12} title={t.title} right={t.sub}>
      {t.none ? <div className="plain">{t.none}</div> : <table className="c"><thead><tr><th>Player</th><th>Team</th><th>In</th>
        <th className="r">Seasons</th><th className="r">Their change</th><th className="r">Usual</th><th>Against the curve</th></tr></thead>
        <tbody>{t.rows.map((r) => (
          <tr key={r.player + r.what}><td><PName p={r.player} px={21} /><div className="how">{r.line}</div></td><td><span className="why">{r.team}</span></td>
            <td><span className="why">{r.what}</span></td><td className="r"><span className="tn dimn">{r.seasons}</span></td>
            <td className="r"><span className="tn">{r.own}</span></td><td className="r"><span className="tn dimn">{r.usual}</span></td>
            <td><span className={`arcv ${r.verdict}`}>{r.verdict === "on" ? "on it" : r.verdict}</span></td></tr>))}</tbody></table>}
    </Tile>
  );
}

const AN_KEYS = ["tab", "section", "season", "team"];

/** A table with its note under it. */
function Noted({ t }: { t: NGrid }) {
  return <><Grid t={t} />{t.note && <div className="note">{t.note}</div>}</>;
}

/** Analytics (stage 3): the deeper numbers for one competition and season, kept as its own page (your answer 2), with
 *  the match-winners chart (your answer 14). Every number comes from the server (server/analyticspage.py). */
export function Analytics() {
  const { career, noCareer, nation } = useShell();
  const t = useTheme();
  const [params] = useSearchParams();
  const go = useNavigate();
  const want = Object.fromEntries(AN_KEYS.map((k) => [k, params.get(k) ?? ""]));
  const qs = AN_KEYS.filter((k) => want[k]).map((k) => `${k}=${encodeURIComponent(want[k]!)}`).join("&");
  const q = useQuery({ queryKey: ["analytics", qs, career?.name], enabled: Boolean(career), retry: false,
    queryFn: () => get<AnalyticsPage>(`/api/analytics?${qs}`), placeholderData: (was) => was });
  useReady(Boolean(q.data || q.error || noCareer), qs);
  const set = (changes: Record<string, string>) => {
    if (changes.section) remember({ section: changes.section });
    if ("season" in changes && changes.season) remember({ season: changes.season });
    const next: Record<string, string> = { ...want, ...changes };
    if ("section" in changes) Object.assign(next, { season: "", team: "" });
    if (nation) next.nation = nation;
    go(`/insights/analytics?${new URLSearchParams(Object.entries(next).filter(([, v]) => v)).toString()}`);
  };
  const head = <InsightsHead on={1} crumb="Under the bonnet · the deeper numbers" />;
  if (noCareer) return <>{head}<div className="grid"><Tile span={12} title="No career yet"><div className="plain">Add a career in Settings first.</div></Tile></div></>;
  if (q.error) return <>{head}<div className="grid"><Tile span={12}><Missing why={String(q.error)} /></Tile></div></>;
  if (!q.data) return <>{head}<div className="empty">Working it out…</div></>;
  const d = q.data;
  if (!d.choices.length) return <>{head}<div className="grid"><Tile span={12}><Missing why={d.none} /></Tile></div></>;
  const tab = d.tab, T_ = d.tabs;
  const note = (x: string) => `${d.choices.find((c) => c.section === x)?.matches ?? ""} matches`;
  const none = (why?: string) => <div className="plain">{why}</div>;
  return (
    <>
      {head}
      <div className="grid">
        <div className="intro">Deeper numbers for one competition: runs against what the situation called for, averages made fair, what really wins
          games, luck, match-winners, styles, consistency and whether a run of form is real.</div>
        <div className="itabs">{T_.map((x, i) => (
          <button key={x} className={x === tab ? "on" : ""} onClick={() => set({ tab: i === 0 ? "" : x })}>{x}</button>))}</div>
        <Tile span={12} className="pickbar"><div className="drops">
          <Pick label="Competition" value={d.section ?? ""} options={d.choices.map((c) => ({ v: c.section, label: c.section, note: note(c.section) }))} set={(v) => set({ section: v })} />
          <Pick label="Season" value={d.season ?? ""} options={[{ v: "", label: "All seasons" }, ...(d.seasons ?? [])]} set={(v) => set({ season: v })} />
          {tab === T_[4] && d.teams && <Pick label="Match-winners of" value={d.team ?? ""} options={d.teams} set={(v) => set({ team: v })} />}
        </div></Tile>

        {tab === T_[0] && <>
          <Tile span={12} title="Runs above expected" right="against the average batter in the same spot">
            {d.rae ? <><SignedBars rows={d.rae.rows} /><Explain {...three(d.rae)} /></> : none(d.rae_none)}</Tile>
          {d.rae_table && <Tile span={12} title="Everyone with 5+ innings"><Noted t={d.rae_table} /></Tile>}
        </>}

        {tab === T_[1] && <>
          <Tile span={6} title="Batting averages made fair">{d.bat ? <Noted t={d.bat as NGrid} /> : none(d.bat_none)}</Tile>
          <Tile span={6} title="Bowling averages made fair" right="lower is better">{d.bowl ? <Noted t={d.bowl as NGrid} /> : none(d.bowl_none)}</Tile>
          {d.note && <div className="note" style={{ gridColumn: "span 12" }}>{d.note}</div>}
        </>}

        {tab === T_[2] && <Tile span={12} title="What wins games" right="% of games won by the side that did more of each">
          {d.wins ? <><SignedBars rows={d.wins.rows} colour={t.blue} /><Explain {...three(d.wins)} /></> : none(d.wins_none)}</Tile>}

        {tab === T_[3] && <Tile span={12} title="Wins against expected wins" right="from the runs each team scored and gave away">
          {d.luck ? <><SignedBars rows={d.luck.rows} /><Explain {...three(d.luck)} /></> : none(d.luck_none)}</Tile>}

        {tab === T_[4] && <>
          {d.winners && <Tile span={12} title={`Who won ${d.winners.team}'s matches`} right="their players of the match in their wins">
            {d.winners.players.length ? <><MatchWinners w={d.winners} />{d.winners.lines && <Explain {...three(d.winners.lines)} />}</> : none(d.winners.shows)}</Tile>}
          <Tile span={6} title="Match-winners" right="the winners' biggest contributor in each win">{d.table ? <Noted t={d.table} /> : none(d.table_none)}</Tile>
          <Tile span={6} title="Who each team leans on" right={d.leans_head ?? ""}>{d.leans ? <Noted t={d.leans} /> : none(d.leans_none)}</Tile>
        </>}

        {tab === T_[5] && <>
          <Tile span={6} title="Batting styles" right={`${d.least ?? ""}+ balls faced`}>
            {d.bat ? <><Quadrant q={d.bat as Quad} /><Explain {...three(d.bat as Quad)} /></> : none(d.bat_none)}</Tile>
          <Tile span={6} title="Bowling styles" right={`${d.least ?? ""}+ balls bowled`}>
            {d.bowl ? <><Quadrant q={d.bowl as Quad} /><Explain {...three(d.bowl as Quad)} /></> : none(d.bowl_none)}</Tile>
          {d.note && <div className="note" style={{ gridColumn: "span 12" }}>{d.note}</div>}
        </>}

        {tab === T_[6] && (d.boom ? <>
          <Tile span={12} title="Boom or bust" right="how a batter's scores are spread (8+ innings)"><Quadrant q={d.boom} /><Explain {...three(d.boom)} /></Tile>
          {d.boom_table && <Tile span={12} title="Batter by batter"><Noted t={d.boom_table} /></Tile>}</>
          : <Tile span={12} title="Boom or bust">{none(d.boom_none)}</Tile>)}

        {tab === T_[7] && <Tile span={12} title="Is the form real?" right="last 8 innings against their earlier innings">
          {d.form ? <Noted t={d.form} /> : none(d.form_none)}</Tile>}

        {tab === T_[8] && <>
          <Tile span={12} title="Bat or bowl first?">
            {d.toss ? <><div className="verdict2">{d.toss.verdict}</div><div className="plain">{d.toss.line}</div></> : none(d.toss_none)}</Tile>
          {d.teams_table && <Tile span={12} title="Team by team" right="their own win % each way"><Noted t={d.teams_table} /></Tile>}
        </>}
      </div>
    </>
  );
}
