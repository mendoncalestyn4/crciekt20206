// Players: your squads and a search over everyone, then one player in full (the current site's Players page in the
// approved style): the career card, the tables for every competition, every format side by side, the player's share
// of the team, the matches they won, their marks out of 10, the career journey; then batting, bowling, fielding and
// their story for one competition and season.
import { useQuery } from "@tanstack/react-query";
import { PlayersHead } from "./Stories";
import { Fragment, useMemo, useState, type ReactNode } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router";
import { get, type ByInnings, type Each, type InningsCol, type InningsMarks, type Lines, type PlayerPage, type PlayersLanding, type Split, remember } from "../api";
import { Explain, FormatTicks, Hero, howOf, Logo, Missing, Name, Num, Pick, PName, Sub, Tile } from "../kit/base";
import { PercentileBars } from "../kit/blocks";
import { RingList } from "../kit/charts";
import { MatchWinners } from "../kit/season";
import { Grid } from "../kit/teams";
import { Mark } from "../kit/myteam";
import { AttrGrid, ScoutText } from "../kit/fm";
import { FormBars, Funnel, ImpactBars, PairedBars, RankLines, RecordTable, SplitBars } from "../kit/player";
import { cap, dayY, f0, f1, f2, fmtOf, plural, NO_MATCHES, rnd, fx } from "../format";
import { useReady } from "../ready";
import { Head, useShell } from "../shell/Shell";
import { useTheme } from "../theme";
import { T } from "../shell/names";

const SHOWN = 40;

export function PlayersHome() {
  const { nation, career } = useShell();
  const keep = nation ? `?nation=${encodeURIComponent(nation)}` : "";
  const go = useNavigate();
  const q = useQuery({ queryKey: ["players"], queryFn: () => get<PlayersLanding>("/api/players") });
  const [typed, setTyped] = useState("");
  useReady(Boolean(q.data || q.error));
  const hits = useMemo(() => {
    const words = typed.toLowerCase().split(/\s+/).filter(Boolean);
    return (q.data?.players ?? []).filter((p) => words.every((w) => `${p.player} ${p.teams.join(" ")}`.toLowerCase().includes(w)))
      .sort((a, b) => b.matches - a.matches);
  }, [q.data, typed]);
  if (q.error) return <><Head title="Players" crumb="Pick a player" /><div className="grid"><Tile span={12}><Missing why={String(q.error)} /></Tile></div></>;
  if (!q.data) return <><Head title="Players" crumb="Pick a player" /><div className="empty">Finding your players…</div></>;
  const d = q.data;
  if (career && career.matches === 0) return <><Head title="Players" crumb="Pick a player" /><div className="grid"><Tile span={12}><Missing why={NO_MATCHES} /></Tile></div></>;
  return (
    <>
      <PlayersHead on={0} crumb="Pick a player" />
      <div className="grid">
        <Tile span={12} title="Find a player" right={`${d.players.length.toLocaleString("en-GB")} who have batted or bowled`}>
          <div className="field"><input className="typed" autoFocus value={typed} onChange={(e) => setTyped(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && hits[0]) go(`/players/${encodeURIComponent(hits[0].player)}${keep}`); }}
            placeholder="Type a name or a team, e.g. S Gill" aria-label="Find a player" /></div>
          {typed && <div className="plist">{hits.slice(0, SHOWN).map((p) => (
            <Link key={p.player} className="pli" to={`/players/${encodeURIComponent(p.player)}${keep}`}>
              <span className="cslot">{/* always there, so the name keeps its own column when a team has no logo */}<Logo team={p.team} size={40} /></span><Name p={p.player} px={22} />
              <span className="how">{p.teams.join(" · ")}</span><span className="how">{plural(p.matches, "match", "matches")} · {p.sections.slice(0, 3).map(fmtOf).join(", ")}</span></Link>))}
            {!hits.length && <div className="empty">Nobody fits "{typed}".</div>}
            {hits.length > SHOWN && <div className="note">and {hits.length - SHOWN} more: type more of the name.</div>}</div>}
          {!typed && <div className="note">Every player who has batted or bowled in this career is here; your squads are below.</div>}
        </Tile>
        {d.squads.map((s) => (
          <Tile key={s.team + s.section} span={6} title={`${s.team} · ${s.section} ${s.season}`} right={`${s.players.length} played`}>
            <table className="c"><thead><tr><th>Player</th><th className="r">Mat</th><th className="r">Runs</th><th className="r">Avg</th><th className="r">Wkts</th><th className="r">Econ</th></tr></thead>
              <tbody>{s.players.slice(0, 14).map((p) => (
                <tr key={p.player} data-parts={p.parts ? JSON.stringify(p.parts) : undefined}><td><PName p={p.player} px={21} /></td>
                  <td className="r"><span className="tn dimn">{p.games}</span></td><td className="r"><span className="tn">{p.runs}</span></td>
                  <td className="r"><span className="tn dimn">{f1(p.average)}</span></td><td className="r"><span className="tn">{p.wickets || (p.bowled ? 0 : "–")}</span></td>
                  <td className="r"><span className="tn dimn">{f2(p.economy)}</span></td></tr>))}</tbody></table>
            {s.players.length > 14 && <div className="note">The 14 who played most this season; {s.players.length - 14} more in the search.</div>}
          </Tile>))}
      </div>
    </>
  );
}

const Box = ({ title, right, span = 6, children }: { title: string; right?: string; span?: number; children: ReactNode }) =>
  <Tile span={span} title={title} right={right}>{children}</Tile>;
/** A chart's three lines (What it is, Who's best, What it's for: design/CHART_LINES.md), as the server wrote them. */
/** A part as one block, or one block per format when several are ticked together (your answer of 17 November: the
 *  parts that only mean one format), each block's title naming its format; `none`: what shows when there's nothing. */
function per<X>(list: Each<X>[] | undefined, one: X | null | undefined, draw: (x: X, sfx: string) => ReactNode, none: ReactNode = null): ReactNode {
  if (!list) return one != null ? draw(one, "") : none;
  return list.map((e) => e.data != null ? <Fragment key={e.section}>{draw(e.data, ` · ${fmtOf(e.section)}`)}</Fragment>
    : e.missing ? <Tile key={e.section} span={6} title={fmtOf(e.section)}><Missing why={e.missing} /></Tile> : null);
}

const lines = (x: Lines) => ({ is_: x.is_, best: x.best, best_label: x.best_label, shows: x.shows, for_: x.for_ ?? "" });
const Sp = ({ s, overall, dec = 1, unit, low }: { s: Split; overall?: number | null; dec?: number; unit?: string; low?: boolean }) =>
  <><SplitBars rows={s.rows} reference={overall} dec={dec} unit={unit} lowBetter={low} /><Explain {...lines(s)} /></>;
const KP = ({ items }: { items: ([string, ReactNode] | [string, ReactNode, string | undefined])[] }) => (
  <Sub cols={items.length}>{items.map(([k, v, how]) => <Tile span={1} key={k} title={k}><Num v={v} px={56} how={how} /></Tile>)}</Sub>);

export function PlayerView() {
  const { pick = "" } = useParams();
  const { nation } = useShell();
  const t = useTheme();
  const keep = nation ? `?nation=${encodeURIComponent(nation)}` : "";
  const [params, setParams] = useSearchParams();
  const section = params.get("section") ?? "", season = params.get("season") ?? "", view = params.get("view") ?? "";
  const q = useQuery({ queryKey: ["player", pick, section, season], retry: false,
    queryFn: () => get<PlayerPage>(`/api/player?name=${encodeURIComponent(pick)}&section=${encodeURIComponent(section)}&season=${encodeURIComponent(season)}`) });
  useReady(Boolean(q.data || q.error), `${pick}|${section}|${season}|${view}`);
  const set = (k: string, v: string) => { remember({ [k]: v }); const p = new URLSearchParams(params); if (v) p.set(k, v); else p.delete(k); if (k === "section") p.delete("season"); setParams(p); };
  if (q.error) return <><Head title="Players" crumb={pick} /><div className="grid"><Tile span={12}><Missing why={String(q.error)} />
    <Link className="btn quiet" to={`/players${keep}`}>Find a player</Link></Tile></div></>;
  if (!q.data) return <><Head title="Players" crumb={`${pick} · working out the numbers…`} /><div className="empty">Working out {pick}'s numbers…</div></>;
  const d = q.data, c = d.card, b = d.batting, w = d.bowling, st = d.story;
  const tab = d.tabs.includes(cap(view)) ? cap(view) : d.open;
  const scope = `${d.section}${d.season === "All seasons" ? "" : ` ${d.season}`}`;
  const pal = [t.led, t.warm, t.cream, t.win, t.blue, t.grey];
  // the latest three teams, newest first (every one is in the career journey below)
  const teamsLine = d.teams.slice(-3).reverse().join(" · ") + (d.teams.length > 3 ? ` · and ${d.teams.length - 3} more` : "");
  const toTab = (x: string) => set("view", x === d.open ? "" : x.toLowerCase());
  return (
    <>
      <Head title="Players" crumb={teamsLine} chips={d.tabs} on={d.tabs.indexOf(tab)} onChip={(i) => toTab(d.tabs[i]!)} />
      <div className="back"><Link to={`/players${keep}`}>← Find another player</Link></div>
      <div className="grid">
        <Hero logo={d.teams[d.teams.length - 1]} px={170} kicker={`${teamsLine}${d.role ? ` · ${d.role.role.toLowerCase()}` : ""}`} title={d.player} size={104}
          side={["Matches", String(d.matches), `in ${plural(c?.sections ?? 0, "competition")}`]} />
        <div className="part"><div className="itabs" style={{ gridColumn: "auto", margin: 0 }}>{d.tabs.map((x) => (
            <button key={x} className={x === tab ? "on" : ""} onClick={() => toTab(x)}>{x}</button>))}</div>
          <span className="tl2">{scope}</span>
          <div className="drops row">
            <FormatTicks all={d.sections} on={d.ticked} set={(v) => set("section", v.join("|"))} />
            <Pick label="Season" value={d.season || "All seasons"} options={d.seasons} set={(v) => set("season", v === "All seasons" ? "" : v)} /></div>
          {d.role && <span className="row2" style={{ gap: 8 }}>{[d.role.role, ...d.role.tags].map((x) => <span className="tag" key={x}>{x}</span>)}
            <span className="note" style={{ margin: 0 }}>from where they bat (usually no. {f0(d.role.usual_position)}) and how much they bowl</span></span>}
          <span className="note" style={{ margin: 0 }}>Tiles marked "every competition" cover the whole career; the rest are for {scope}: tick other formats (any ticked together are counted together) or pick a season above.</span>
        </div>

        {tab === "Overview" && <>
          {c && <Sub cols={6}>{([["Matches", c.matches], ["Runs", c.runs.toLocaleString("en-GB")], ["Best score", c.best_score], ["Wickets", c.wickets],
            ["Best bowling", c.best_bowling], ["Badges", c.badges]] as [string, ReactNode][]).map(([k, v]) => <Tile span={1} key={k} title={k}><Num v={v} px={50} /></Tile>)}</Sub>}
          {c && c.badge_list.length > 0 && <Tile span={12} title="Badges" right="every competition">
            <div className="row2" style={{ flexWrap: "wrap", gap: 10 }}>{c.badge_list.map((x) => <span key={x.badge} className="tag" title={x.detail}>🏅 {x.badge}{x.times > 1 ? ` ×${x.times}` : ""}</span>)}</div></Tile>}
          {d.winners ? <Tile span={12} title="Match-winners" right="player of the match in a win, and what they did">
            {d.winners.players.length ? <MatchWinners w={d.winners} /> : null}<Explain {...lines({ ...d.winners, shows: d.winners.line })} /></Tile>
            : d.missing.winners ? <Tile span={12} title="Match-winners"><Missing why={d.missing.winners} /></Tile> : null}
          {d.share && d.share.length > 0 && <Tile span={12} title="Share of the team" right="each competition and season">
            <table className="c"><thead><tr><th>Season</th><th>Competition</th><th className="r">Mat</th><th className="r">Runs</th><th>of the team's</th><th className="r">Wkts</th><th>of the team's</th></tr></thead>
              <tbody>{d.share.slice(0, 12).map((r) => (
                <tr key={r.section + r.season + r.team}><td><span className="tn dimn">{r.season}</span></td><td><Name p={fmtOf(r.section)} px={19} /><div className="how">{r.team}</div></td>
                  <td className="r"><span className="tn dimn">{r.matches}/{r.team_matches}</span></td>
                  <td className="r"><span className="tn">{r.runs}</span></td><td><ShareBar v={r.run_share} of={r.team_runs} /></td>
                  <td className="r"><span className="tn">{r.wickets}</span></td><td><ShareBar v={r.wicket_share} of={r.team_wickets} /></td></tr>))}</tbody></table>
            <div className="note">Their runs out of all the runs the team's batters made that season there (off the bat: extras are no one's), and their
              wickets out of all the wickets the team took; matches: theirs of the team's.</div></Tile>}
          {per(d.each?.profile, d.profile, (pf, sfx) => <>
            <Tile span={7} title={`Attributes in ${sfx ? sfx.slice(3) : d.section}`} right="out of 20 · against everyone there">
            <AttrGrid a={pf.attributes} show={pf.show} other={pf.other} section={sfx ? sfx.slice(3) : d.section} />
            {pf.best && <Explain {...lines(pf)} />}</Tile>
            <Tile span={5} title={`Scout report${sfx}`} right={pf.report.role ?? ""}><ScoutText r={pf.report} />
            {d.season !== "All seasons" && <div className="note">Over every season of {sfx ? sfx.slice(3) : d.section}, not just {d.season}.</div>}</Tile></>)}
          {d.marks && d.marks.length > 0 && <Tile span={12} title="Marks out of 10 · every series" right="newest first">
            <table className="c marks"><thead><tr><th>Series</th><th className="r">Mark</th><th className="r">Rank</th><th>In the series</th><th>Best match</th></tr></thead>
              <tbody>{d.marks.slice(0, 10).map((m) => (
                <tr key={m.series + m.team}><td><Name p={m.label} px={19} /><div className="how">{m.team}</div></td><td className="r"><Mark v={m.mark} /></td>
                  <td className="r"><span className="tn dimn">{m.rank} of {m.of}</span></td><td><span className="why">{m.line}</span></td>
                  <td><Link to={`/matches/${m.best_match}${keep}`} className="why lk">{m.best}</Link></td></tr>))}</tbody></table>
            <div className="note">Where each series ranks among every player's series in that format in this career (see My team); batters against batters, bowlers against bowlers.
              {d.marks.length > 10 ? ` The latest 10 of ${d.marks.length}.` : ""}</div></Tile>}
          {d.journey && d.journey.length > 0 && <Tile span={12} title="Career journey" right="every team and competition, in order">
            <table className="c"><thead><tr><th>From</th><th>To</th><th>Team</th><th>Competition</th><th>Season</th><th className="r">Mat</th><th className="r">Runs</th><th className="r">Wkts</th></tr></thead>
              <tbody>{d.journey.map((j, i) => (
                <tr key={i}><td><span className="tn dimn">{dayY(j.first)}</span></td><td><span className="tn dimn">{dayY(j.last)}</span></td><td><Name p={j.team} px={19} /></td>
                  <td><span className="why">{j.section}</span></td><td><span className="tn dimn">{j.season}</span></td><td className="r"><span className="tn dimn">{j.matches}</span></td>
                  <td className="r"><span className="tn">{j.runs}</span></td><td className="r"><span className="tn">{j.wickets}</span></td></tr>))}</tbody></table></Tile>}
        </>}

        {tab === "Batting" && <>
          {b ? <KP items={[["Innings", b.kpis.innings], ["Runs", b.kpis.runs.toLocaleString("en-GB")],
            ["Average", f2(b.kpis.average), b.kpis.average == null ? undefined : howOf(`${b.kpis.runs} runs ÷ ${b.kpis.outs} times out = ${f2(b.kpis.average)}`, b.kpis.innings)],
            ["Strike rate", f1(b.kpis.strike_rate), b.kpis.strike_rate == null ? undefined : howOf(`${b.kpis.runs} runs ÷ ${b.kpis.balls} balls × 100 = ${f1(b.kpis.strike_rate)}`, b.kpis.innings)],
            ["High score", b.kpis.high_score], ["100s / 50s", `${b.kpis.hundreds} / ${b.kpis.fifties}`]]} />
            : <Tile span={12}><div className="plain">No innings in {scope}: tick another format above. Their batting everywhere is below.</div></Tile>}
          {c && c.last10.length > 1 && <Tile span={12} title={`Last ${c.last10.length} innings`} right="every competition">
            <div className="row2" style={{ flexWrap: "wrap", gap: 10 }}><span className="l5" style={{ height: 40 }}>{c.last10.map((r, i) => (
              <i key={i} className={r >= 50 ? "g" : ""} style={{ height: Math.max(3, Math.min(40, (r / Math.max(...c.last10, 1)) * 40)) }} title={String(r)} />))}</span>
              <span className="l5t">{c.last10.join(" ")}</span></div>
            <Explain is_={c.last10_is} best={c.last10_best} best_label="Best of them" for_={c.last10_for ?? ""} /></Tile>}
          <Tile span={12} title="Batting · every competition">
            {d.bat_table ? <RecordTable t={d.bat_table} /> : <Missing why={d.missing.bat_table} />}
            <div className="note">Same columns in every competition. Hover a column name for what it means.</div></Tile>
          {d.formats && <FormatsTile f={d.formats} kind="bat" />}
          <CountriesTile key={d.ticked.join("|")} d={d} kind="bat" />
          <BigTile key={d.ticked.join("|")} d={d} kind="bat" />
          <BounceTile key={d.ticked.join("|")} d={d} kind="bat" />
        </>}
        {tab === "Bowling" && <>
          {w ? <KP items={[["Wickets", w.kpis.wickets],
            ["Average", f2(w.kpis.average), w.kpis.average == null ? undefined : howOf(`${w.kpis.runs} runs ÷ ${w.kpis.wickets} wickets = ${f2(w.kpis.average)}`, w.kpis.innings)],
            ["Economy", f2(w.kpis.economy), w.kpis.economy == null ? undefined : howOf(`${w.kpis.runs} runs ÷ ${w.kpis.balls} balls × 6 = ${f2(w.kpis.economy)} an over`, w.kpis.innings)],
            ["Strike rate", f1(w.kpis.strike_rate), w.kpis.strike_rate == null ? undefined : howOf(`${w.kpis.balls} balls ÷ ${w.kpis.wickets} wickets = ${f1(w.kpis.strike_rate)}`, w.kpis.innings)],
            ["Best", w.kpis.best], ["4+ hauls", w.kpis.hauls]]} />
            : <Tile span={12}><div className="plain">Hasn't bowled in {scope}: tick another format above. Their bowling everywhere is below.</div></Tile>}
          <Tile span={12} title="Bowling · every competition">
            {d.bowl_table ? <RecordTable t={d.bowl_table} /> : <Missing why={d.missing.bowl_table ?? "Hasn't bowled."} />}
            <div className="note">Same columns in every competition. Maidens are only printed on longer-format scorecards and dot balls only on T20 and
              Hundred scorecards, so one of them is blank.</div></Tile>
          {d.formats && <FormatsTile f={d.formats} kind="bowl" />}
          <CountriesTile key={d.ticked.join("|")} d={d} kind="bowl" />
          <BigTile key={d.ticked.join("|")} d={d} kind="bowl" />
          <BounceTile key={d.ticked.join("|")} d={d} kind="bowl" />
        </>}

        {tab === "Batting" && b && <>
          <Box span={12} title="Form · every innings" right="oldest first">
            <FormBars f={b.form} unit="runs" />
            <div className="legend"><span><i style={{ background: t.led }} />each innings (green: 50 or more)</span><span><i className="ln" style={{ background: t.led }} />average over the last {b.form.window} innings</span>
              <span><i className="ln" style={{ background: t.ink, opacity: 0.6 }} />their average over every innings shown</span></div>
            <Explain {...lines(b.form)} /></Box>
          {b.compare && <Box span={7} title={`How they compare · v ${b.compare.pool} batters here`}><PercentileBars values={b.compare.values} />
            {b.compare.best && <Explain {...lines(b.compare)} />}
            <div className="note">Percentiles among the batters here with 3+ innings: 100 = the best, 50 = the middle of the pack.</div></Box>}
          <Box span={b.compare ? 5 : 6} title="Where the runs come from"><RingList items={[["Fours", b.runs_from.fours, pal[0]!], ["Sixes", b.runs_from.sixes, pal[1]!], ["Running", b.runs_from.running, pal[2]!]]}
            centre={String(b.kpis.runs)} sub="runs" /><div className="note">{plural(b.runs_from.n4, "four")} and {plural(b.runs_from.n6, "six", "sixes")}.</div>
            {b.runs_from.empty ? <div className="note">No runs yet.</div> : <Explain {...lines(b.runs_from)} />}</Box>
          <Box title="Season by season · runs"><Sp s={b.seasons} dec={0} /></Box>
          <Box title="How they get out">{b.how_out ? <><RingList items={b.how_out.rows.map((r, i) => [r.label, r.value ?? 0, pal[i % pal.length]!])} centre={String(b.how_out.rows.reduce((a, r) => a + (r.value ?? 0), 0))} sub="dismissals" />
            <Explain {...lines(b.how_out)} /></> : <div className="note">Never dismissed.</div>}</Box>
          {per(b.each?.danger, b.danger, (x, sfx) => <Box title={`Danger zones${sfx}`} right="when they get out">{x.key && <div className="keyz">⭐ {x.key}</div>}
            <PairedBars rows={x.rows} me={d.player} unit="%" dec={0} /><Explain {...lines(x)} /></Box>,
            <Box title="Danger zones" right="when they get out"><div className="note">Never dismissed here.</div></Box>)}
          {per(b.each?.funnel, b.funnel, (x, sfx) => <Box title={`Conversion${sfx}`} right="% of innings reaching each score"><Funnel rows={x.rows} />{x.extra && <div className="plain">{x.extra}</div>}
            <Explain {...lines(x)} /></Box>, <Box title="Conversion" right="% of innings reaching each score"><div className="note">No innings yet.</div></Box>)}
          <Box span={12} title={`Every season in ${d.section}`} right="the same columns as the table at the top"><RecordTable t={b.season_table} /></Box>
          {per(d.each?.bat_innings, d.bat_innings, (x, sfx) => <InningsTile x={x} sfx={sfx} />)}
          <div className="part"><span className="tl2" style={{ fontSize: 32 }}>Average in different situations</span>
            <span className="note" style={{ margin: 0 }}>Each chart splits the same innings one way. The dashed line is their overall average ({f1(b.splits.overall)}).</span></div>
          {b.splits.rows.map((s) => <Box key={s.title} title={s.title!}><Sp s={s} overall={b.splits.overall} /></Box>)}
          <Tile span={12}><div className="plain">Stronger and weaker teams: teams ranked by their win % here (each counted as if it had already won 2 and lost 2,
            so one win in one game doesn't make a side strong); the top half are the stronger teams. Stronger half: <b>{b.splits.stronger}</b>.</div></Tile>
          {per(b.each?.positions, b.positions, (x, sfx) => <Box span={12} title={`At each batting position${sfx}`} right={x.best_position ? `best at no. ${x.best_position}` : "against the average batter there"}>
            <PairedBars rows={x.rows} me={d.player} others="Average batter there" />
            <table className="c" style={{ marginTop: 10 }}><thead><tr><th>Position</th><th className="r">Inns</th><th className="r">Runs</th><th className="r">NO</th>
              <th className="r">HS</th><th className="r">Avg</th><th className="r">SR</th><th className="r">50</th><th className="r">100</th><th className="r">Average batter there</th><th className="r" title="Settled: a few innings at the usual level for that position added before comparing">They are (settled)</th></tr></thead>
              <tbody>{x.table.map((r) => (
                <tr key={r.position} className={r.best ? "me" : ""} data-parts={r.parts ? JSON.stringify(r.parts) : undefined}><td><Name p={`${r.best ? "★ " : ""}No. ${r.position}`} px={19} />{r.small && <div className="how">only {r.innings} innings</div>}</td>
                  <td className="r"><span className="tn dimn">{r.innings}</span></td><td className="r"><span className="tn">{r.runs}</span></td>
                  <td className="r"><span className="tn dimn">{r.not_outs}</span></td><td className="r"><span className="tn dimn">{r.high}</span></td>
                  <td className="r"><span className="tn">{f1(r.average)}</span></td><td className="r"><span className="tn dimn">{f1(r.strike_rate)}</span></td>
                  <td className="r"><span className="tn dimn">{r.fifties}</span></td><td className="r"><span className="tn dimn">{r.hundreds}</span></td>
                  <td className="r"><span className="tn dimn">{f1(r.all_average)}</span></td>
                  <td className="r"><span className="tn">{r.edge == null ? "–" : `${r.edge >= 0 ? "+" : ""}${rnd(r.edge)}%`}</span></td></tr>))}</tbody></table>
            <Explain {...lines(x)} /></Box>)}
          {per(b.each?.came_in, b.came_in, (ci, sfx) => <>
          <Box title={`Average by the situation they walked into${sfx}`}><Sp s={ci} overall={ci.overall ?? b.splits.overall} /></Box>
          <Box title={`Best rescue innings${sfx}`} right={`came in 3+ down for ${ci.press} or fewer`}>{ci.rescue.length ? <table className="c"><thead><tr><th>Came in at</th><th className="r">Score</th><th className="r">BF</th><th>Against</th><th>Date</th></tr></thead>
            <tbody>{ci.rescue.map((r, i) => <tr key={i}><td><span className="tn">{r.at}</span></td><td className="r"><span className="tn">{r.score}</span></td><td className="r"><span className="tn dimn">{r.balls}</span></td>
              <td><Name p={r.against} px={19} /></td><td><span className="tn dimn">{dayY(r.date)}</span></td></tr>)}</tbody></table> : <div className="note">No innings started in that kind of trouble yet.</div>}</Box></>)}
          {per(b.each?.consistency, b.consistency, (cs, sfx) => <Box title={`Consistency${sfx}`}><Sub cols={2}>{([[`${cs.bar}+ scores`, `${f0(cs.past_bar_pct)}%`], ["Single figures", `${f0(cs.single_figures_pct)}%`],
            ["Golden ducks", cs.golden_ducks], ["50s → 100s", cs.conversion_pct == null ? "–" : `${f0(cs.conversion_pct)}%`]] as [string, ReactNode][]).map(([k, v]) =>
              <div className="bf-side" key={k}><div className="k">{k}</div><Num v={v} px={40} /></div>)}</Sub>
            <div className="note">'{cs.bar}+ scores' is how often they pass {cs.bar}, a decent score in this format. 'Single figures' is how often they're out for under 10.
              A golden duck is out first ball. '50s → 100s' is how often a fifty is turned into a hundred.</div></Box>)}
          <Box title="Nemesis" right="bowlers who have got them out most">{b.nemesis ? <Sp s={b.nemesis} dec={0} /> : <div className="note">No bowler has dismissed them yet.</div>}</Box>
          {per(b.each?.streaks, b.streaks, (x, sfx) => <Box title={`Streaks${sfx}`} right="innings in a row"><StreakTable rows={x} /><div className="note">Current = the run they're on now, counting back from their latest innings here.</div></Box>)}
          <Box title="When chasing" right="batting in the last innings">{b.chasing ? <><Sub cols={2}>{([["Chases won", b.chasing.won_innings], ["Average in wins", f1(b.chasing.won_average)],
            ["Chases lost", b.chasing.lost_innings], ["Average in defeats", f1(b.chasing.lost_average)]] as [string, ReactNode][]).map(([k, v]) =>
              <div className="bf-side" key={k}><div className="k">{k}</div><Num v={v} px={40} /></div>)}</Sub>
            <div className="note">Not out at the end of {plural(b.chasing.not_out_in_wins, "winning chase")}: still there when the runs were knocked off.</div></> : <div className="note">Hasn't batted in a chase here yet.</div>}</Box>
          <Box span={12} title="Against each team" right="average"><Sp s={b.against} overall={b.splits.overall} /></Box>
        </>}

        {tab === "Bowling" && w && <>
          <Box span={12} title="Form · wickets in every innings bowled" right="oldest first"><FormBars f={w.form} unit="wickets" />
            <div className="legend"><span><i style={{ background: t.led }} />wickets in each innings (green: 4 or more)</span><span><i className="ln" style={{ background: t.led }} />wickets an innings over the last {w.form.window}</span>
              <span><i className="ln" style={{ background: t.ink, opacity: 0.6 }} />over everything shown</span></div>
            <Explain {...lines(w.form)} /></Box>
          <Box title="Season by season · wickets"><Sp s={w.seasons} dec={0} /></Box>
          <Box title="How they take wickets">{w.how_wickets ? <><RingList items={w.how_wickets.rows.map((r, i) => [r.label, r.value ?? 0, pal[i % pal.length]!])} centre={String(w.kpis.wickets)} sub="wickets" />
            <Explain {...lines(w.how_wickets)} /></> : <div className="note">No wickets yet.</div>}</Box>
          {per(w.each?.match_pattern, w.match_pattern, (mp, sfx) => <Box title={`Over a match${sfx}`} right="first bowling innings v the second">{mp.none ? <div className="note">{mp.none}</div> : <>
            <table className="c"><tbody>{([["First innings", mp.first], ["Second innings", mp.second], ["Wickets in both innings", mp.both], ["Best match figures", mp.best]] as [string, string][]).map(([k, v]) =>
              <tr key={k}><td><span className="why">{k}</span></td><td className="r"><span className="tn">{v}</span></td></tr>)}</tbody></table>
            {mp.shows && <Explain shows={mp.shows} for_={mp.for_ ?? ""} />}</>}</Box>)}
          {per(w.each?.with_without, w.with_without, (ww, sfx) => <Box title={`With and without wickets${sfx}`} right="their spells split">
            <table className="c"><thead><tr><th /><th className="r">Spells</th><th className="r">Wkts</th><th className="r">Econ</th><th className="r">Maidens per 10 overs</th></tr></thead>
              <tbody>{ww.rows.map((r) => <tr key={r.label} data-parts={r.parts ? JSON.stringify(r.parts) : undefined}><td><Name p={r.label} px={19} /></td><td className="r"><span className="tn dimn">{r.spells}</span></td>
                <td className="r"><span className="tn">{r.wickets}</span></td><td className="r"><span className="tn">{r.economy}</span></td><td className="r"><span className="tn dimn">{r.maidens}</span></td></tr>)}</tbody></table>
            {ww.shows && <Explain shows={ww.shows} for_={ww.for_ ?? ""} />}</Box>)}
          <Box span={12} title={`Every season in ${d.section}`} right="the same columns as the table at the top"><RecordTable t={w.season_table} /></Box>
          {per(d.each?.bowl_innings, d.bowl_innings, (x, sfx) => <InningsTile x={x} sfx={sfx} />)}
          <Box title="Quality of wickets" right="where their victims bat">{w.quality ? <Sp s={w.quality} dec={0} /> : <div className="note">No wickets yet.</div>}</Box>
          {w.breakers && <Box title="Partnership breaker" right={`stands of 50+ ended`}><div className="plain">{w.breakers.text}</div><Explain shows="" for_={w.breakers.for_} /></Box>}
          <Box title="Bunnies" right="batters they have got out most">{w.bunnies ? <Sp s={w.bunnies} dec={0} /> : <div className="note">No wickets yet.</div>}</Box>
          {per(w.each?.streaks, w.streaks, (x, sfx) => <Box span={12} title={`Streaks${sfx}`} right="innings bowled in a row"><StreakTable rows={x} /></Box>)}
          {w.splits.rows.map((s) => <Box key={s.title} title={`${s.title} · economy`}><Sp s={s} overall={w.splits.overall} dec={2} low /></Box>)}
        </>}

        {tab === "Story" && st && <>
          <Box title={`Match impact · ${d.section}`} right="one number a match">{st.impact ? <><ImpactBars rows={st.impact.rows} /><Explain {...lines(st.impact)} /></>
            : <div className="note">No matches yet.</div>}</Box>
          {per(st.each?.rank, st.rank, (rk, sfx) => <Box title={`Rank over time${sfx}`} right={`where they finished in ${sfx ? sfx.slice(3) : fmtOf(d.section)}`}>{!rk.empty ? <><RankLines rows={rk.rows} /><Explain {...lines(rk)} /></>
            : <div className="note">No seasons yet.</div>}</Box>, <Box title="Rank over time" right={`where they finished in ${fmtOf(d.section)}`}><div className="note">No seasons yet.</div></Box>)}
          {d.arc && <Box title="Career arc" right="against the usual curve">{d.arc.lines.length ? d.arc.lines.map((x) => (
            <div className="plain" key={x.section + x.text}><span className={`arcv ${x.verdict}`}>{x.verdict === "on" ? "On the curve" : x.verdict === "ahead" ? "Ahead" : "Behind"}</span> · <T>{x.text}</T></div>))
            : <div className="note">{d.arc.none}</div>}<Explain shows="" for_={d.arc.for_} /></Box>}
          {per(st.each?.milestones, st.milestones, (ms, sfx) => <Box title={`Milestones${sfx}`} right={`how many ${ms.unit} it took`}>{ms.rows.length ? <table className="c"><thead><tr><th>Milestone</th><th className="r">Took</th><th className="r">Fastest</th><th>Reached</th></tr></thead>
            <tbody>{ms.rows.map((r) => <tr key={r.milestone}><td><Name p={r.milestone} px={19} /></td><td className="r"><span className="tn">{r.took}</span></td><td className="r"><span className="tn dimn">{r.fastest}</span></td><td><span className="tn dimn">{dayY(r.date)}</span></td></tr>)}</tbody></table>
            : <div className="note">No milestone reached here yet.</div>}<div className="note">The rank is among everyone here who got there.</div></Box>)}
          <Box title="Badges" right="special feats">{st.badges.length ? <table className="c"><tbody>{st.badges.map((x, i) => (
            <tr key={i}><td><Name p={`🏅 ${x.badge}`} px={19} /></td><td><span className="why">{x.detail}</span></td><td><Link to={`/matches/${x.id}${keep}`} className="why lk">{dayY(x.date)}</Link></td></tr>))}</tbody></table>
            : <div className="note">No badges yet: a T20 hundred, a five-for, a Test double hundred or ten in a match earns one.</div>}</Box>
          <Box title="Career firsts" right="every competition">{st.firsts.length ? <table className="c"><tbody>{st.firsts.map((x, i) => (
            <tr key={i}><td><span className="tn dimn">{dayY(x.date)}</span></td><td><span className="why" style={{ color: "var(--ink)" }}>{x.what}</span><div className="how">{x.detail}</div></td>
              <td><Link to={`/matches/${x.id}${keep}`} className="why lk">v {x.against}</Link></td></tr>))}</tbody></table> : <div className="note">Nothing yet.</div>}</Box>
          {per(st.each?.fires, st.fires, (fi, sfx) => <Box title={`When ${d.player} fires${sfx}`} right={`their team's win % in ${sfx ? sfx.slice(3) : fmtOf(d.section)}${d.season === "All seasons" ? "" : ` ${d.season}`}`}>{fi.rows.length ? <table className="c"><thead><tr><th /><th className="r">Times</th><th className="r">Win % then</th><th className="r">Otherwise</th></tr></thead>
            <tbody>{fi.rows.map((r) => <tr key={r.label}><td><span className="why">{r.label}</span></td><td className="r"><span className="tn dimn">{r.times}</span></td><td className="r"><span className="tn">{r.when}</span></td><td className="r"><span className="tn dimn">{r.other}</span></td></tr>)}</tbody></table>
            : <div className="note">{fi.none}</div>}
            {!sfx || sfx === ` · ${fmtOf(st.each!.fires![0]!.section)}` ? <><div className="k3" style={{ marginTop: 16 }}>Odd ones</div>{st.quirks.length ? st.quirks.map((x) => <div className="plain" key={x}><T>{x}</T></div>) : <div className="note">Nothing unusual yet.</div>}</> : null}</Box>)}
          {per(st.each?.compare, st.compare, (cm, sfx) => <CompareSeasons c={cm} section={sfx ? sfx.slice(3) : d.section} />,
            <CompareSeasons c={null} section={d.section} />)}
        </>}
      </div>
    </>
  );
}

const pc = (v: number | null) => (v == null ? "–" : `${v >= 0 ? "+" : ""}${rnd(v)}%`);

function ShareBar({ v, of }: { v: number | null; of: number }) {
  return v == null ? <span className="tn dimn">–</span> : (
    <span className="share"><span className="bar"><i style={{ width: `${Math.min(100, v * 2.5)}%` }} /></span><span className="tn">{Math.round(v)}%</span><span className="how"> of {of.toLocaleString("en-GB")}</span></span>);
}

// ------------------------------------------------------------------ innings by innings: Normal, then each comparison on its own
/** "4.9 better", "27% worse" or "same": + always means better (the server turns bowling figures round). */
function Diff({ v, dec = 1, unit = "" }: { v: number | null; dec?: number; unit?: string }) {
  if (v == null) return <span className="tn dimn dif">–</span>;
  const a = fx(Math.abs(v), dec);
  if (Number(a) === 0) return <span className="tn dimn dif">same</span>;
  return <span className={`tn dif ${v > 0 ? "up" : "down"}`}>{a}{unit} {v > 0 ? "better" : "worse"}</span>;
}

/** "4th innings" with "chasing" under it (and "only 3 innings" when there are few): ★ the best, ▼ the weakest. */
function Slot({ r }: { r: InningsMarks }) {
  const [main, kind] = r.label.split(", ");
  return <td><Name p={`${r.best ? "★ " : r.weakest ? "▼ " : ""}${main}`} px={19} />
    {(kind || r.small) && <div className="how">{kind && <span style={{ color: "var(--ink)" }}>{kind}</span>}{kind && r.small ? " · " : ""}
      {r.small && `only ${plural(r.innings, "innings", "innings")}`}</div>}</td>;
}

function Cell({ c, v }: { c: InningsCol; v: unknown }) {
  if (c.t === "d") return <td className="r"><Diff v={typeof v === "number" ? v : null} dec={c.dec} unit={c.unit} /></td>;
  const text = v == null ? "–" : typeof v === "number" ? `${fx(v, c.dec)}${c.unit}` : String(v);
  return <td className="r"><span className={`tn${c.t === "n" ? "" : " dimn"}`}>{text}</span></td>;
}

function InningsTile({ x, sfx = "" }: { x: ByInnings; sfx?: string }) {
  const [key, setKey] = useState("normal");
  const v = x.views.find((y) => y.key === key) ?? x.views[0]!;
  return (
    <Tile span={12} title={`${x.title}${sfx}`} right={x.right}>
      <div className="itabs" style={{ gridColumn: "auto", margin: "0 0 10px" }}>{x.views.map((y) => (
        <button key={y.key} className={y.key === v.key ? "on" : ""} onClick={() => setKey(y.key)}>{y.label}</button>))}</div>
      <table className="c bi"><thead><tr><th />{v.cols.map((c) => <th key={c.k} className="r" title={c.help || undefined}>{c.label}</th>)}</tr></thead>
        <tbody>{v.rows.map((r, i) => <tr key={r.slot} className={r.best ? "me" : r.slot === "all" ? "tot" : ""} data-parts={v.parts?.[i] ? JSON.stringify(v.parts[i]) : undefined}><Slot r={r} />
          {v.cols.map((c) => <Cell key={c.k} c={c} v={r[c.k]} />)}</tr>)}
          {v.total && <tr className="tot" data-parts={v.total_parts ? JSON.stringify(v.total_parts) : undefined}><td><Name p="All" px={19} /></td>{v.cols.map((c) => <Cell key={c.k} c={c} v={v.total![c.k]} />)}</tr>}</tbody></table>
      {x.note && v.key !== "normal" && <div className="note">{x.note}</div>}
      <Explain shows={v.shows} for_={v.for_} />
      {x.rule && <div className="note">{x.rule}</div>}
    </Tile>
  );
}

function StreakTable({ rows }: { rows: { streak: string; longest: number; current: number }[] }) {
  return <table className="c"><thead><tr><th>Streak</th><th className="r">Longest</th><th className="r">Current</th></tr></thead>
    <tbody>{rows.map((r) => <tr key={r.streak}><td><span className="why">{r.streak}</span></td><td className="r"><span className="tn">{r.longest}</span></td><td className="r"><span className="tn dimn">{r.current}</span></td></tr>)}</tbody></table>;
}

function CompareSeasons({ c, section }: { c: NonNullable<PlayerPage["story"]>["compare"]; section: string }) {
  const [a, setA] = useState(c?.seasons[0] ?? "");
  const [b0, setB] = useState(c?.seasons[1] ?? "");
  if (!c) return <Tile span={12} title={`Compare two seasons · ${section}`}><div className="note">Only one season in this competition so far.</div></Tile>;
  const others = c.seasons.filter((s) => s !== a);
  const b = others.includes(b0) ? b0 : others[0] ?? "";   // never a season against itself
  const A = c.per[a] ?? {}, B = c.per[b] ?? {};
  const keys = Object.keys(A);
  const better = (k: string, x: number | null, y: number | null) => {
    const how = A[k]?.better;
    return how && x != null && y != null && x !== y ? ((x > y) === (how === "high") ? "a" : "b") : "";
  };
  return (
    <Tile span={12} title={`Compare two seasons · ${section}`}>
      <div className="drops"><Pick label="Season" value={a} options={c.seasons} set={setA} /><Pick label="Against" value={b} options={others} set={setB} /></div>
      <table className="c" style={{ marginTop: 10 }}><thead><tr><th /><th className="r">{a}</th><th className="r">{b}</th></tr></thead>
        <tbody>{keys.map((k) => { const w = better(k, A[k]?.v ?? null, B[k]?.v ?? null); return (
          <tr key={k}><td><span className="why">{k}</span></td><td className="r"><span className="tn">{w === "a" ? "✓ " : ""}{A[k]?.text}</span></td>
            <td className="r"><span className="tn">{w === "b" ? "✓ " : ""}{B[k]?.text ?? "–"}</span></td></tr>); })}</tbody></table>
      <div className="note">✓ marks the better season on each (for bowling average, economy and strike rate, lower is better).</div>
    </Tile>
  );
}


type PartOf<K extends "countries" | "big" | "bounce"> = NonNullable<PlayerPage[K]>;

/** One tile's numbers for the formats ticked on it: the page's own when it's just the page's competition, otherwise
 *  asked of the server (kept, so ticking back is instant). */
function usePart<K extends "countries" | "big" | "bounce">(d: PlayerPage, which: K) {
  // opens on the formats ticked at the top of the page (its own numbers); ticking others here asks the server
  const [on, setOn] = useState<string[]>(d.ticked);
  const same = on.join("|") === d.ticked.join("|");
  const q = useQuery({ queryKey: ["player_part", d.player, which, on.join("|")], enabled: !same, retry: false,
    queryFn: () => get<{ data: PartOf<K> | null; label: string }>(`/api/player_part?name=${encodeURIComponent(d.player)}&part=${which}&sections=${encodeURIComponent(on.join("|"))}`) });
  const data = (same ? d[which] : q.data?.data) as PartOf<K> | null | undefined;
  const label = same ? d.section : q.data?.label ?? on.join(" + ");
  return { on, setOn, data, label, waiting: !same && !q.data && !q.error, error: q.error ? String(q.error) : "", missing: same ? d.missing[which] : "" };
}

const BAT_COLS = [0, 1, 2, 3, 4], BOWL_COLS = [0, 1, 5, 6, 7];

/** Country by country (or ground by ground), batting or bowling only, for the formats ticked. */
function CountriesTile({ d, kind }: { d: PlayerPage; kind: "bat" | "bowl" }) {
  const p = usePart(d, "countries");
  const t = p.data;
  const cols = kind === "bat" ? BAT_COLS : BOWL_COLS;
  const kept = t ? t.rows.map((_, i) => i).filter((i) => { const r = t.rows[i]!; return kind === "bat" ? Number(r[2] ?? 0) > 0 || r[3] !== "–" : Number(r[5] ?? 0) > 0 || r[7] !== "–"; }) : [];
  const grid = t ? { ...t, cols: cols.map((i) => t.cols[i]!), rows: kept.map((k) => cols.map((i) => t.rows[k]![i]!)),
    num: cols.slice(1).map((_, i) => i + 1), parts: kept.map((k) => t.parts?.[k] ?? null) } : null;
  return (
    <Tile span={12} title={`🏟️ ${kind === "bat" ? "Batting" : "Bowling"} ${t?.nation === false ? "ground by ground" : "country by country"}`} right={`${p.label} · every season`}>
      <FormatTicks all={d.sections} on={p.on} set={p.setOn} />
      {p.waiting ? <div className="empty">Working it out…</div> : p.error ? <Missing why={p.error} />
        : grid && grid.rows.length ? <Grid t={grid} /> : p.missing ? <Missing why={p.missing} />
        : <div className="plain">{kind === "bat" ? "No innings" : "No bowling"} in {p.label} yet.</div>}
      <div className="note">{t?.nation === false ? "By the home side's ground" : "By the home side's country"} (the scorecards don't name the ground); neutral
        grounds are a row of their own. Several formats ticked: their games counted together.</div></Tile>
  );
}

/** Big-match player, batting or bowling only, for the formats ticked. */
function BigTile({ d, kind }: { d: PlayerPage; kind: "bat" | "bowl" }) {
  const p = usePart(d, "big");
  const x = p.data;
  return (
    <Tile span={6} title={`🔥 Big-match ${kind === "bat" ? "batting" : "bowling"}`} right={p.label}>
      <FormatTicks all={d.sections} on={p.on} set={p.setOn} />
      {p.waiting ? <div className="empty">Working it out…</div> : p.error ? <Missing why={p.error} /> : !x ? <Missing why={p.missing || "Not enough games yet."} />
        : x.none ? <div className="plain">{x.none}</div> : x.rows!.map((r) => (
          <div key={r.team}><table className="c"><thead><tr><th></th><th className="r">Big games ({r.big})</th><th className="r">Otherwise ({r.ordinary})</th></tr></thead>
            <tbody>{kind === "bat" ? <><tr><td>Batting</td><td className="r">{r.big_bat}</td><td className="r">{r.ord_bat}</td></tr>
              <tr><td>Strike rate</td><td className="r">{r.big_sr}</td><td className="r">{r.ord_sr}</td></tr></>
              : <><tr><td>Bowling</td><td className="r">{r.big_bowl}</td><td className="r">{r.ord_bowl}</td></tr>
              <tr><td>Economy</td><td className="r">{r.big_econ}</td><td className="r">{r.ord_econ}</td></tr></>}</tbody></table>
            {x.rows!.length > 1 && <div className="note">For {r.team}.</div>}</div>))}
      <div className="note">Big games: finals, semi-finals, qualifiers, eliminators and other knockouts, and series deciders (level with one to play). Shown from 3.</div></Tile>
  );
}

/** Bounce-back, batting or bowling only, for the formats ticked. */
function BounceTile({ d, kind }: { d: PlayerPage; kind: "bat" | "bowl" }) {
  const p = usePart(d, "bounce");
  const x = p.data?.[kind];
  return (
    <Tile span={6} title={`↩️ Bounce-back ${kind === "bat" ? "batting" : "bowling"}`} right={p.label}>
      <FormatTicks all={d.sections} on={p.on} set={p.setOn} />
      {p.waiting ? <div className="empty">Working it out…</div> : p.error ? <Missing why={p.error} />
        : x ? <div className="plain">{x.line}</div>
        : <div className="plain">{kind === "bat" ? "No poor innings here yet: never out for under 10." : "No poor spells here yet: never wicketless for 30 or more."}</div>}
      <div className="note">{kind === "bat" ? "A poor innings: out for a duck or under 10." : "A poor spell: no wicket for 30 runs or more."} The game after it is their next match in the formats ticked; shown from 3.</div></Tile>
  );
}

/** Every format side by side, batting or bowling only: each against the average player there. */
function FormatsTile({ f, kind }: { f: NonNullable<PlayerPage["formats"]>; kind: "bat" | "bowl" }) {
  const rows = f.rows.filter((r) => kind === "bat" ? r.average != null || r.runs > 0 : r.wickets > 0 || r.bowl_average != null);
  if (!rows.length) return null;
  return (
    <Tile span={12} title={`Every format side by side · ${kind === "bat" ? "batting" : "bowling"}`} right="each against the average player there">
      <table className="c"><thead><tr><th>Format</th><th className="r">Mat</th>{kind === "bat"
        ? <><th className="r">Runs</th><th className="r">Avg</th><th className="r">v average</th><th className="r">SR</th><th className="r">v average</th></>
        : <><th className="r">Wkts</th><th className="r">Avg</th><th className="r">v average</th></>}</tr></thead>
        <tbody>{rows.map((r) => (
          <tr key={r.section} className={r.best ? "me" : ""} data-parts={r.parts ? JSON.stringify(r.parts) : undefined}><td><Name p={`${r.best ? "⭐ " : ""}${r.section}`} px={20} /></td>
            <td className="r"><span className="tn dimn">{r.matches}</span></td>{kind === "bat" ? <>
              <td className="r"><span className="tn">{r.runs}</span></td><td className="r"><span className="tn dimn">{f1(r.average)}</span></td>
              <td className="r"><span className="tn">{pc(r.bat_vs)}</span></td><td className="r"><span className="tn dimn">{f1(r.strike_rate)}</span></td>
              <td className="r"><span className="tn">{pc(r.sr_vs)}</span></td></> : <>
              <td className="r"><span className="tn">{r.wickets}</span></td><td className="r"><span className="tn dimn">{f1(r.bowl_average)}</span></td>
              <td className="r"><span className="tn">{pc(r.bowl_vs)}</span></td></>}</tr>))}</tbody></table>
      <Explain shows={f.shows} for_={f.for_} /></Tile>
  );
}
