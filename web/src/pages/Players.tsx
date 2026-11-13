// Players: your squads and a search over everyone, then one player in full (the current site's Players page in the
// approved style): the career card, the tables for every competition, every format side by side, the player's share
// of the team, the matches they won, their marks out of 10, the career journey; then batting, bowling, fielding and
// their story for one competition and season.
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState, type ReactNode } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router";
import { get, type ByInnings, type InningsCol, type InningsMarks, type PlayerPage, type PlayersLanding, type Split, remember } from "../api";
import { Explain, Hero, Logo, Missing, Name, Num, PName, Sub, Tile } from "../kit/base";
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
      <Head title="Players" crumb="Pick a player" />
      <div className="grid">
        <Tile span={12} title="Find a player" right={`${d.players.length.toLocaleString("en-GB")} who have batted or bowled`}>
          <div className="field"><input className="typed" autoFocus value={typed} onChange={(e) => setTyped(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && hits[0]) go(`/players/${encodeURIComponent(hits[0].player)}${keep}`); }}
            placeholder="Type a name or a team, e.g. S Gill" aria-label="Find a player" /></div>
          {typed && <div className="plist">{hits.slice(0, SHOWN).map((p) => (
            <Link key={p.player} className="pli" to={`/players/${encodeURIComponent(p.player)}${keep}`}>
              <Logo team={p.team} size={30} /><Name p={p.player} px={22} />
              <span className="how">{p.teams.join(" · ")}</span><span className="how">{plural(p.matches, "match", "matches")} · {p.sections.slice(0, 3).map(fmtOf).join(", ")}</span></Link>))}
            {!hits.length && <div className="empty">Nobody fits "{typed}".</div>}
            {hits.length > SHOWN && <div className="note">and {hits.length - SHOWN} more: type more of the name.</div>}</div>}
          {!typed && <div className="note">Every player who has batted or bowled in this career is here; your squads are below.</div>}
        </Tile>
        {d.squads.map((s) => (
          <Tile key={s.team + s.section} span={6} title={`${s.team} · ${s.section} ${s.season}`} right={`${s.players.length} played`}>
            <table className="c"><thead><tr><th>Player</th><th className="r">Games</th><th className="r">Runs</th><th className="r">Avg</th><th className="r">Wkts</th><th className="r">Econ</th></tr></thead>
              <tbody>{s.players.slice(0, 14).map((p) => (
                <tr key={p.player}><td><PName p={p.player} px={21} /></td>
                  <td className="r"><span className="tn dimn">{p.games}</span></td><td className="r"><span className="tn">{p.runs}</span></td>
                  <td className="r"><span className="tn dimn">{f1(p.average)}</span></td><td className="r"><span className="tn">{p.wickets || "–"}</span></td>
                  <td className="r"><span className="tn dimn">{f2(p.economy)}</span></td></tr>))}</tbody></table>
            {s.players.length > 14 && <div className="note">The 14 who played most this season; {s.players.length - 14} more in the search.</div>}
          </Tile>))}
      </div>
    </>
  );
}

const Box = ({ title, right, span = 6, children }: { title: string; right?: string; span?: number; children: ReactNode }) =>
  <Tile span={span} title={title} right={right}>{children}</Tile>;
const Sp = ({ s, overall, dec = 1, unit, low }: { s: Split; overall?: number | null; dec?: number; unit?: string; low?: boolean }) =>
  <><SplitBars rows={s.rows} reference={overall} dec={dec} unit={unit} lowBetter={low} /><Explain shows={s.shows} for_={s.for_} /></>;
const KP = ({ items }: { items: [string, ReactNode][] }) => (
  <Sub cols={items.length}>{items.map(([k, v]) => <Tile span={1} key={k} title={k}><Num v={v} px={56} /></Tile>)}</Sub>);

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
  const tab = d.tabs.includes(cap(view)) ? cap(view) : d.tabs[0]!;
  const scope = `${d.section}${d.season === "All seasons" ? "" : ` ${d.season}`}`;
  const pal = [t.led, t.warm, t.cream, t.win, t.blue, t.grey];
  // the latest three teams, newest first (every one is in the career journey below)
  const teamsLine = d.teams.slice(-3).reverse().join(" · ") + (d.teams.length > 3 ? ` · and ${d.teams.length - 3} more` : "");
  return (
    <>
      <Head title="Players" crumb={`${teamsLine}${d.keeper ? " · wicketkeeper" : ""}`} chips={d.tabs} on={d.tabs.indexOf(tab)}
        onChip={(i) => set("view", i === 0 ? "" : d.tabs[i]!.toLowerCase())} />
      <div className="back"><Link to={`/players${keep}`}>← Find another player</Link></div>
      <div className="grid">
        <Hero logo={d.teams[d.teams.length - 1]} px={170} kicker={`${teamsLine}${d.role ? ` · ${d.role.role.toLowerCase()}` : ""}`} title={d.player} size={104}
          side={["Matches", String(d.matches), `in ${plural(c?.sections ?? 0, "competition")}`]} />
        {c && <Sub cols={6}>{([["Matches", c.matches], ["Runs", c.runs.toLocaleString("en-GB")], ["Best score", c.best_score], ["Wickets", c.wickets],
          ["Best bowling", c.best_bowling], ["Badges", c.badges]] as [string, ReactNode][]).map(([k, v]) => <Tile span={1} key={k} title={k}><Num v={v} px={50} /></Tile>)}</Sub>}
        {c && (c.last10.length > 1 || c.badge_list.length > 0) && <Tile span={12} title={`Last ${c.last10.length} innings`}>
          <div className="row2" style={{ flexWrap: "wrap", gap: 10 }}><span className="l5" style={{ height: 40 }}>{c.last10.map((r, i) => (
            <i key={i} className={r >= 50 ? "g" : ""} style={{ height: Math.max(3, Math.min(40, (r / Math.max(...c.last10, 1)) * 40)) }} title={String(r)} />))}</span>
            <span className="l5t">{c.last10.join(" ")}</span>
            {c.badge_list.map((x) => <span key={x.badge} className="tag" title={x.detail}>🏅 {x.badge}{x.times > 1 ? ` ×${x.times}` : ""}</span>)}</div></Tile>}
        <Tile span={12} title="Batting and fielding · every competition">
          {d.bat_table ? <RecordTable t={d.bat_table} /> : <Missing why={d.missing.bat_table} />}
          {d.bowl_table ? <><div className="k3" style={{ marginTop: 16 }}>Bowling · every competition</div><RecordTable t={d.bowl_table} /></> : <div className="note">Hasn't bowled.</div>}
          <div className="note">Same columns in every competition. Hover a column name for what it means. Maidens are only printed on longer-format
            scorecards and dot balls only on T20 and Hundred scorecards, so one of them is blank.</div>
        </Tile>
        {d.formats && <Tile span={12} title="Every format side by side" right="each against the average player there">
          <table className="c"><thead><tr><th>Format</th><th className="r">Mat</th><th className="r">Runs</th><th className="r">Avg</th><th className="r">v average</th>
            <th className="r">SR</th><th className="r">v average</th><th className="r">Wkts</th><th className="r">Bowl avg</th><th className="r">v average</th></tr></thead>
            <tbody>{d.formats.rows.map((r) => (
              <tr key={r.section} className={r.best ? "me" : ""}><td><Name p={`${r.best ? "⭐ " : ""}${r.section}`} px={20} /></td>
                <td className="r"><span className="tn dimn">{r.matches}</span></td><td className="r"><span className="tn">{r.runs}</span></td>
                <td className="r"><span className="tn dimn">{f1(r.average)}</span></td><td className="r"><span className="tn">{pc(r.bat_vs)}</span></td>
                <td className="r"><span className="tn dimn">{f1(r.strike_rate)}</span></td><td className="r"><span className="tn">{pc(r.sr_vs)}</span></td>
                <td className="r"><span className="tn">{r.wickets}</span></td><td className="r"><span className="tn dimn">{f1(r.bowl_average)}</span></td>
                <td className="r"><span className="tn">{pc(r.bowl_vs)}</span></td></tr>))}</tbody></table>
          <Explain shows={d.formats.shows} for_={d.formats.for_} /></Tile>}
        {d.share && d.share.length > 0 && <Tile span={7} title="Share of the team" right="each competition and season">
          <table className="c"><thead><tr><th>Season</th><th>Competition</th><th className="r">Matches</th><th className="r">Runs</th><th>of the team's</th><th className="r">Wkts</th><th>of the team's</th></tr></thead>
            <tbody>{d.share.slice(0, 12).map((r) => (
              <tr key={r.section + r.season + r.team}><td><span className="tn dimn">{r.season}</span></td><td><Name p={fmtOf(r.section)} px={19} /><div className="how">{r.team}</div></td>
                <td className="r"><span className="tn dimn">{r.matches}/{r.team_matches}</span></td>
                <td className="r"><span className="tn">{r.runs}</span></td><td><ShareBar v={r.run_share} of={r.team_runs} /></td>
                <td className="r"><span className="tn">{r.wickets}</span></td><td><ShareBar v={r.wicket_share} of={r.team_wickets} /></td></tr>))}</tbody></table>
          <div className="note">Their runs out of all the runs the team's batters made that season there (off the bat: extras are no one's), and their
            wickets out of all the wickets the team took; matches: theirs of the team's.</div></Tile>}
        {d.winners ? <Tile span={12} title="Match-winners" right="player of the match in a win, and what they did">
          {d.winners.players.length ? <MatchWinners w={d.winners} /> : null}<div className="note">{d.winners.line}</div></Tile>
          : d.missing.winners ? <Tile span={12} title="Match-winners"><Missing why={d.missing.winners} /></Tile> : null}
        <Tile span={7} title={`🏟️ ${d.countries?.nation === false ? "Ground by ground" : "Country by country"}`} right={`${fmtOf(d.section)} · every season · neutral grounds on their own`}>
          {d.countries ? <Grid t={d.countries} /> : d.missing.countries ? <Missing why={d.missing.countries} /> : <div className="plain">No games here yet.</div>}</Tile>
        <Tile span={5} title="🔥 Big-match player" right="knockouts and series deciders">
          {d.big ? (d.big.none ? <div className="plain">{d.big.none}</div> : d.big.rows!.map((r) => (
            <div key={r.team}><table className="c"><thead><tr><th></th><th className="r">Big games ({r.big})</th><th className="r">Otherwise ({r.ordinary})</th></tr></thead>
              <tbody><tr><td>Batting</td><td className="r">{r.big_bat}</td><td className="r">{r.ord_bat}</td></tr>
                <tr><td>Strike rate</td><td className="r">{r.big_sr}</td><td className="r">{r.ord_sr}</td></tr>
                <tr><td>Bowling</td><td className="r">{r.big_bowl}</td><td className="r">{r.ord_bowl}</td></tr>
                <tr><td>Economy</td><td className="r">{r.big_econ}</td><td className="r">{r.ord_econ}</td></tr></tbody></table>
              {d.big!.rows!.length > 1 && <div className="note">For {r.team}.</div>}</div>))) : <Missing why={d.missing.big} />}
          <div className="note">Big games: finals, semi-finals, qualifiers, eliminators and other knockouts, and series deciders (level with one to play). Shown from 3.</div></Tile>
        <Tile span={12} title="↩️ Bounce-back" right="the game after a poor one">
          {d.bounce ? ((d.bounce.bat || d.bounce.bowl) ? <ul className="dots">{[d.bounce.bat, d.bounce.bowl].filter(Boolean).map((x) => <li key={x!.line}>{x!.line}</li>)}</ul>
            : <div className="plain">No poor games here yet: never out for under 10, and never wicketless for 30 or more.</div>) : <Missing why={d.missing.bounce} />}
          <div className="note">A poor game: out for a duck or under 10 with the bat, or no wicket for 30 runs or more with the ball. The game after it is their next match here; shown from 3.</div></Tile>
        {d.marks && d.marks.length > 0 && <Tile span={12} title="Marks out of 10 · every series" right="newest first">
          <table className="c marks"><thead><tr><th>Series</th><th className="r">Mark</th><th className="r">Rank</th><th>In the series</th><th>Best match</th></tr></thead>
            <tbody>{d.marks.slice(0, 10).map((m) => (
              <tr key={m.series + m.team}><td><Name p={m.label} px={19} /><div className="how">{m.team}</div></td><td className="r"><Mark v={m.mark} /></td>
                <td className="r"><span className="tn dimn">{m.rank} of {m.of}</span></td><td><span className="why">{m.line}</span></td>
                <td><Link to={`/matches/${m.best_match}${keep}`} className="why lk">{m.best}</Link></td></tr>))}</tbody></table>
          <div className="note">Where each series ranks among every player's series in that format in this career (see My team); batters against batters, bowlers against bowlers.
            {d.marks.length > 10 ? ` The latest 10 of ${d.marks.length}.` : ""}</div></Tile>}
        {d.journey && d.journey.length > 0 && <Tile span={12} title="Career journey" right="every team and competition, in order">
          <table className="c"><thead><tr><th>From</th><th>To</th><th>Team</th><th>Competition</th><th>Season</th><th className="r">Matches</th><th className="r">Runs</th><th className="r">Wickets</th></tr></thead>
            <tbody>{d.journey.map((j, i) => (
              <tr key={i}><td><span className="tn dimn">{dayY(j.first)}</span></td><td><span className="tn dimn">{dayY(j.last)}</span></td><td><Name p={j.team} px={19} /></td>
                <td><span className="why">{j.section}</span></td><td><span className="tn dimn">{j.season}</span></td><td className="r"><span className="tn dimn">{j.matches}</span></td>
                <td className="r"><span className="tn">{j.runs}</span></td><td className="r"><span className="tn">{j.wickets}</span></td></tr>))}</tbody></table></Tile>}

        <div className="part"><span className="tl2">{scope}</span>
          <div className="field" style={{ marginTop: 0 }}>
            <select className="pick" value={d.section} onChange={(e) => set("section", e.target.value)} aria-label="Competition">{d.sections.map((s) => <option key={s}>{s}</option>)}</select>
            <select className="pick" value={d.season} onChange={(e) => set("season", e.target.value === "All seasons" ? "" : e.target.value)} aria-label="Season">{d.seasons.map((s) => <option key={s}>{s}</option>)}</select></div>
          {d.role && <span className="row2" style={{ gap: 8 }}>{[d.role.role, ...d.role.tags].map((x) => <span className="tag" key={x}>{x}</span>)}
            <span className="note" style={{ margin: 0 }}>from where they bat (usually no. {f0(d.role.usual_position)}) and how much they bowl</span></span>}
          <div className="itabs" style={{ gridColumn: "auto", margin: 0 }}>{d.tabs.map((x) => (
            <button key={x} className={x === tab ? "on" : ""} onClick={() => set("view", x === d.tabs[0] ? "" : x.toLowerCase())}>{x}</button>))}</div>
          <span className="note" style={{ margin: 0 }}>Everything below is for {scope} only; pick another competition or season above.</span>
        </div>

        {d.profile && <Tile span={7} title={`Attributes in ${d.section}`} right="out of 20 · against everyone there">
          <AttrGrid a={d.profile.attributes} show={d.profile.show} other={d.profile.other} section={d.section} /></Tile>}
        {d.profile && <Tile span={5} title="Scout report" right={d.profile.report.role ?? ""}><ScoutText r={d.profile.report} />
          {d.season !== "All seasons" && <div className="note">Over every season of {d.section}, not just {d.season}.</div>}</Tile>}

        {tab === "Batting" && b && <>
          <KP items={[["Innings", b.kpis.innings], ["Runs", b.kpis.runs.toLocaleString("en-GB")], ["Average", f2(b.kpis.average)], ["Strike rate", f1(b.kpis.strike_rate)],
            ["High score", b.kpis.high_score], ["100s / 50s", `${b.kpis.hundreds} / ${b.kpis.fifties}`]]} />
          <Box span={12} title="Form · every innings" right="oldest first">
            <FormBars f={b.form} unit="runs" />
            <div className="legend"><span><i style={{ background: t.led }} />each innings (green: 50 or more)</span><span><i className="ln" style={{ background: t.led }} />average over the last {b.form.window} innings</span>
              <span><i className="ln" style={{ background: t.ink, opacity: 0.6 }} />their average over every innings shown</span></div>
            <Explain shows={b.form.shows} for_={b.form.for_} /></Box>
          {b.compare && <Box span={7} title={`How they compare · v ${b.compare.pool} batters here`}><PercentileBars values={b.compare.values} />
            <div className="note">Percentiles among the batters here with 3+ innings: 100 = the best, 50 = the middle of the pack.</div></Box>}
          <Box span={b.compare ? 5 : 6} title="Where the runs come from"><RingList items={[["Fours", b.runs_from.fours, pal[0]!], ["Sixes", b.runs_from.sixes, pal[1]!], ["Running", b.runs_from.running, pal[2]!]]}
            centre={String(b.kpis.runs)} sub="runs" /><div className="note">{plural(b.runs_from.n4, "four")} and {plural(b.runs_from.n6, "six", "sixes")}.</div></Box>
          <Box title="Season by season · runs"><Sp s={b.seasons} dec={0} /></Box>
          <Box title="How they get out">{b.how_out ? <><RingList items={b.how_out.rows.map((r, i) => [r.label, r.value ?? 0, pal[i % pal.length]!])} centre={String(b.how_out.rows.reduce((a, r) => a + (r.value ?? 0), 0))} sub="dismissals" />
            <Explain shows={b.how_out.shows} for_={b.how_out.for_} /></> : <div className="note">Never dismissed.</div>}</Box>
          <Box title="Danger zones" right="when they get out">{b.danger ? <>{b.danger.key && <div className="keyz">⭐ {b.danger.key}</div>}
            <PairedBars rows={b.danger.rows} me={d.player} unit="%" dec={0} /><Explain shows={b.danger.shows} for_={b.danger.for_} /></> : <div className="note">Never dismissed here.</div>}</Box>
          <Box title="Conversion" right="% of innings reaching each score">{b.funnel ? <><Funnel rows={b.funnel.rows} />{b.funnel.extra && <div className="plain">{b.funnel.extra}</div>}
            <Explain shows={b.funnel.shows} for_={b.funnel.for_} /></> : <div className="note">No innings yet.</div>}</Box>
          <Box span={12} title={`Every season in ${d.section}`} right="the same columns as the table at the top"><RecordTable t={b.season_table} /></Box>
          {d.bat_innings && <InningsTile x={d.bat_innings} />}
          <div className="part"><span className="tl2" style={{ fontSize: 32 }}>Average in different situations</span>
            <span className="note" style={{ margin: 0 }}>Each chart splits the same innings one way. The dashed line is their overall average ({f1(b.splits.overall)}).</span></div>
          {b.splits.rows.map((s) => <Box key={s.title} title={s.title!}><Sp s={s} overall={b.splits.overall} /></Box>)}
          <Tile span={12}><div className="plain">Stronger and weaker teams: teams ranked by their win % here (each counted as if it had already won 2 and lost 2,
            so one win in one game doesn't make a side strong); the top half are the stronger teams. Stronger half: <b>{b.splits.stronger}</b>.</div></Tile>
          {b.positions && <Box span={12} title="At each batting position" right={b.positions.best ? `best at no. ${b.positions.best}` : "against the average batter there"}>
            <PairedBars rows={b.positions.rows} me={d.player} others="Average batter there" />
            <table className="c" style={{ marginTop: 10 }}><thead><tr><th>Position</th><th className="r">Inns</th><th className="r">Runs</th><th className="r">NO</th>
              <th className="r">HS</th><th className="r">Avg</th><th className="r">SR</th><th className="r">50s</th><th className="r">100s</th><th className="r">Average batter there</th><th className="r" title="Settled: a few innings at the usual level for that position added before comparing">They are (settled)</th></tr></thead>
              <tbody>{b.positions.table.map((r) => (
                <tr key={r.position} className={r.best ? "me" : ""}><td><Name p={`${r.best ? "★ " : ""}No. ${r.position}`} px={19} />{r.small && <div className="how">only {r.innings} innings</div>}</td>
                  <td className="r"><span className="tn dimn">{r.innings}</span></td><td className="r"><span className="tn">{r.runs}</span></td>
                  <td className="r"><span className="tn dimn">{r.not_outs}</span></td><td className="r"><span className="tn dimn">{r.high}</span></td>
                  <td className="r"><span className="tn">{f1(r.average)}</span></td><td className="r"><span className="tn dimn">{f1(r.strike_rate)}</span></td>
                  <td className="r"><span className="tn dimn">{r.fifties}</span></td><td className="r"><span className="tn dimn">{r.hundreds}</span></td>
                  <td className="r"><span className="tn dimn">{f1(r.all_average)}</span></td>
                  <td className="r"><span className="tn">{r.edge == null ? "–" : `${r.edge >= 0 ? "+" : ""}${rnd(r.edge)}%`}</span></td></tr>))}</tbody></table>
            <Explain shows={b.positions.shows} for_={b.positions.for_} /></Box>}
          <Box title="Average by the situation they walked into"><Sp s={b.came_in} overall={b.splits.overall} /></Box>
          <Box title="Best rescue innings" right={`came in 3+ down for ${b.came_in.press} or fewer`}>{b.came_in.rescue.length ? <table className="c"><thead><tr><th>Came in at</th><th className="r">Score</th><th className="r">Balls</th><th>Against</th><th>Date</th></tr></thead>
            <tbody>{b.came_in.rescue.map((r, i) => <tr key={i}><td><span className="tn">{r.at}</span></td><td className="r"><span className="tn">{r.score}</span></td><td className="r"><span className="tn dimn">{r.balls}</span></td>
              <td><Name p={r.against} px={19} /></td><td><span className="tn dimn">{dayY(r.date)}</span></td></tr>)}</tbody></table> : <div className="note">No innings started in that kind of trouble yet.</div>}</Box>
          <Box title="Consistency"><Sub cols={2}>{([[`${b.consistency.bar}+ scores`, `${f0(b.consistency.past_bar_pct)}%`], ["Single figures", `${f0(b.consistency.single_figures_pct)}%`],
            ["Golden ducks", b.consistency.golden_ducks], ["50s → 100s", b.consistency.conversion_pct == null ? "–" : `${f0(b.consistency.conversion_pct)}%`]] as [string, ReactNode][]).map(([k, v]) =>
              <div className="bf-side" key={k}><div className="k">{k}</div><Num v={v} px={40} /></div>)}</Sub>
            <div className="note">'{b.consistency.bar}+ scores' is how often they pass {b.consistency.bar}, a decent score in this format. 'Single figures' is how often they're out for under 10.
              A golden duck is out first ball. '50s → 100s' is how often a fifty is turned into a hundred.</div></Box>
          <Box title="Nemesis" right="bowlers who have got them out most">{b.nemesis ? <Sp s={b.nemesis} dec={0} /> : <div className="note">No bowler has dismissed them yet.</div>}</Box>
          <Box title="Streaks" right="innings in a row"><StreakTable rows={b.streaks} /><div className="note">Current = the run they're on now, counting back from their latest innings here.</div></Box>
          <Box title="When chasing" right="batting in the last innings">{b.chasing ? <><Sub cols={2}>{([["Chases won", b.chasing.won_innings], ["Average in wins", f1(b.chasing.won_average)],
            ["Chases lost", b.chasing.lost_innings], ["Average in defeats", f1(b.chasing.lost_average)]] as [string, ReactNode][]).map(([k, v]) =>
              <div className="bf-side" key={k}><div className="k">{k}</div><Num v={v} px={40} /></div>)}</Sub>
            <div className="note">Not out at the end of {plural(b.chasing.not_out_in_wins, "winning chase")}: still there when the runs were knocked off.</div></> : <div className="note">Hasn't batted in a chase here yet.</div>}</Box>
          <Box span={12} title="Against each team" right="average"><Sp s={b.against} overall={b.splits.overall} /></Box>
        </>}

        {tab === "Bowling" && w && <>
          <KP items={[["Wickets", w.kpis.wickets], ["Average", f2(w.kpis.average)], ["Economy", f2(w.kpis.economy)], ["Strike rate", f1(w.kpis.strike_rate)], ["Best", w.kpis.best], ["4+ hauls", w.kpis.hauls]]} />
          <Box span={12} title="Form · wickets in every innings bowled" right="oldest first"><FormBars f={w.form} unit="wickets" />
            <div className="legend"><span><i style={{ background: t.led }} />wickets in each innings (green: 4 or more)</span><span><i className="ln" style={{ background: t.led }} />wickets an innings over the last {w.form.window}</span>
              <span><i className="ln" style={{ background: t.ink, opacity: 0.6 }} />over everything shown</span></div>
            <Explain shows={w.form.shows} for_={w.form.for_} /></Box>
          <Box title="Season by season · wickets"><Sp s={w.seasons} dec={0} /></Box>
          <Box title="How they take wickets">{w.how_wickets ? <><RingList items={w.how_wickets.rows.map((r, i) => [r.label, r.value ?? 0, pal[i % pal.length]!])} centre={String(w.kpis.wickets)} sub="wickets" />
            <Explain shows={w.how_wickets.shows} for_={w.how_wickets.for_} /></> : <div className="note">No wickets yet.</div>}</Box>
          {w.match_pattern && <Box title="Over a match" right="first bowling innings v the second">{w.match_pattern.none ? <div className="note">{w.match_pattern.none}</div> : <>
            <table className="c"><tbody>{([["First innings", w.match_pattern.first], ["Second innings", w.match_pattern.second], ["Wickets in both innings", w.match_pattern.both], ["Best match figures", w.match_pattern.best]] as [string, string][]).map(([k, v]) =>
              <tr key={k}><td><span className="why">{k}</span></td><td className="r"><span className="tn">{v}</span></td></tr>)}</tbody></table>
            {w.match_pattern.shows && <Explain shows={w.match_pattern.shows} for_={w.match_pattern.for_ ?? ""} />}</>}</Box>}
          <Box title="With and without wickets" right="their spells split">
            <table className="c"><thead><tr><th /><th className="r">Spells</th><th className="r">Wkts</th><th className="r">Econ</th><th className="r">Maidens per 10 overs</th></tr></thead>
              <tbody>{w.with_without.rows.map((r) => <tr key={r.label}><td><Name p={r.label} px={19} /></td><td className="r"><span className="tn dimn">{r.spells}</span></td>
                <td className="r"><span className="tn">{r.wickets}</span></td><td className="r"><span className="tn">{r.economy}</span></td><td className="r"><span className="tn dimn">{r.maidens}</span></td></tr>)}</tbody></table>
            {w.with_without.shows && <Explain shows={w.with_without.shows} for_={w.with_without.for_ ?? ""} />}</Box>
          <Box span={12} title={`Every season in ${d.section}`} right="the same columns as the table at the top"><RecordTable t={w.season_table} /></Box>
          {d.bowl_innings && <InningsTile x={d.bowl_innings} />}
          <Box title="Quality of wickets" right="where their victims bat">{w.quality ? <Sp s={w.quality} dec={0} /> : <div className="note">No wickets yet.</div>}</Box>
          <Box title="Bunnies" right="batters they have got out most">{w.bunnies ? <Sp s={w.bunnies} dec={0} /> : <div className="note">No wickets yet.</div>}</Box>
          <Box span={12} title="Streaks" right="innings bowled in a row"><StreakTable rows={w.streaks} /></Box>
          {w.splits.rows.map((s) => <Box key={s.title} title={`${s.title} · economy`}><Sp s={s} overall={w.splits.overall} dec={2} low /></Box>)}
        </>}

        {tab === "Fielding" && <Tile span={12} title="Fielding">
          {d.fielding ? <Sub cols={3}>{([["Matches", d.fielding.matches], ["Catches", d.fielding.catches], ["Stumpings", d.fielding.stumpings]] as [string, number][]).map(([k, v]) =>
            <div className="bf-side" key={k}><div className="k">{k}</div><Num v={v} px={56} /></div>)}</Sub> : <div className="note">No fielding record in this competition.</div>}
          <div className="note">Catches and stumpings are credited under the player's own name, so 'c de Kock' counts for Q de Kock. Run outs aren't credited to
            fielders because the scorecard doesn't name them.</div></Tile>}

        {tab === "Story" && st && <>
          <Box title={`Match impact · ${d.section}`} right="one number a match">{st.impact ? <><ImpactBars rows={st.impact.rows} /><Explain shows={st.impact.shows} for_={st.impact.for_} /></>
            : <div className="note">No matches yet.</div>}</Box>
          <Box title="Rank over time" right={`where they finished in ${fmtOf(d.section)}`}>{st.rank ? <><RankLines rows={st.rank.rows} /><Explain shows={st.rank.shows} for_={st.rank.for_} /></>
            : <div className="note">No seasons yet.</div>}</Box>
          <Box title="Milestones" right={`how many ${st.milestones.unit} it took`}>{st.milestones.rows.length ? <table className="c"><thead><tr><th>Milestone</th><th className="r">Took</th><th className="r">Fastest</th><th>Reached</th></tr></thead>
            <tbody>{st.milestones.rows.map((r) => <tr key={r.milestone}><td><Name p={r.milestone} px={19} /></td><td className="r"><span className="tn">{r.took}</span></td><td className="r"><span className="tn dimn">{r.fastest}</span></td><td><span className="tn dimn">{dayY(r.date)}</span></td></tr>)}</tbody></table>
            : <div className="note">No milestone reached here yet.</div>}<div className="note">The rank is among everyone here who got there.</div></Box>
          <Box title="Badges" right="special feats">{st.badges.length ? <table className="c"><tbody>{st.badges.map((x, i) => (
            <tr key={i}><td><Name p={`🏅 ${x.badge}`} px={19} /></td><td><span className="why">{x.detail}</span></td><td><Link to={`/matches/${x.id}${keep}`} className="why lk">{dayY(x.date)}</Link></td></tr>))}</tbody></table>
            : <div className="note">No badges yet: a T20 hundred, a five-for, a Test double hundred or ten in a match earns one.</div>}</Box>
          <Box title="Career firsts" right="every competition">{st.firsts.length ? <table className="c"><tbody>{st.firsts.map((x, i) => (
            <tr key={i}><td><span className="tn dimn">{dayY(x.date)}</span></td><td><span className="why" style={{ color: "var(--ink)" }}>{x.what}</span><div className="how">{x.detail}</div></td>
              <td><Link to={`/matches/${x.id}${keep}`} className="why lk">v {x.against}</Link></td></tr>))}</tbody></table> : <div className="note">Nothing yet.</div>}</Box>
          <Box title={`When ${d.player} fires`} right={`their team's win % in ${fmtOf(d.section)}${d.season === "All seasons" ? "" : ` ${d.season}`}`}>{st.fires.rows.length ? <table className="c"><thead><tr><th /><th className="r">Times</th><th className="r">Win % then</th><th className="r">Otherwise</th></tr></thead>
            <tbody>{st.fires.rows.map((r) => <tr key={r.label}><td><span className="why">{r.label}</span></td><td className="r"><span className="tn dimn">{r.times}</span></td><td className="r"><span className="tn">{r.when}</span></td><td className="r"><span className="tn dimn">{r.other}</span></td></tr>)}</tbody></table>
            : <div className="note">{st.fires.none}</div>}
            <div className="k3" style={{ marginTop: 16 }}>Odd ones</div>{st.quirks.length ? st.quirks.map((x) => <div className="plain" key={x}><T>{x}</T></div>) : <div className="note">Nothing unusual yet.</div>}</Box>
          <CompareSeasons c={st.compare} section={d.section} />
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

function InningsTile({ x }: { x: ByInnings }) {
  const [key, setKey] = useState("normal");
  const v = x.views.find((y) => y.key === key) ?? x.views[0]!;
  return (
    <Tile span={12} title={x.title} right={x.right}>
      <div className="itabs" style={{ gridColumn: "auto", margin: "0 0 10px" }}>{x.views.map((y) => (
        <button key={y.key} className={y.key === v.key ? "on" : ""} onClick={() => setKey(y.key)}>{y.label}</button>))}</div>
      <table className="c bi"><thead><tr><th />{v.cols.map((c) => <th key={c.k} className="r" title={c.help || undefined}>{c.label}</th>)}</tr></thead>
        <tbody>{v.rows.map((r) => <tr key={r.slot} className={r.best ? "me" : r.slot === "all" ? "tot" : ""}><Slot r={r} />
          {v.cols.map((c) => <Cell key={c.k} c={c} v={r[c.k]} />)}</tr>)}
          {v.total && <tr className="tot"><td><Name p="All" px={19} /></td>{v.cols.map((c) => <Cell key={c.k} c={c} v={v.total![c.k]} />)}</tr>}</tbody></table>
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
      <div className="field"><select className="pick" value={a} onChange={(e) => setA(e.target.value)} aria-label="Season">{c.seasons.map((s) => <option key={s}>{s}</option>)}</select>
        <span className="note" style={{ margin: 0 }}>against</span>
        <select className="pick" value={b} onChange={(e) => setB(e.target.value)} aria-label="Against">{others.map((s) => <option key={s}>{s}</option>)}</select></div>
      <table className="c" style={{ marginTop: 10 }}><thead><tr><th /><th className="r">{a}</th><th className="r">{b}</th></tr></thead>
        <tbody>{keys.map((k) => { const w = better(k, A[k]?.v ?? null, B[k]?.v ?? null); return (
          <tr key={k}><td><span className="why">{k}</span></td><td className="r"><span className="tn">{w === "a" ? "✓ " : ""}{A[k]?.text}</span></td>
            <td className="r"><span className="tn">{w === "b" ? "✓ " : ""}{B[k]?.text ?? "–"}</span></td></tr>); })}</tbody></table>
      <div className="note">✓ marks the better season on each (for bowling average, economy and strike rate, lower is better).</div>
    </Tile>
  );
}
