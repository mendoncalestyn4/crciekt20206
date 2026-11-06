// My team, the home page: your side's season at a glance (as on the approved mock-up), the latest result and what it
// changed, what's next, the marks out of 10 after the latest series with who to bring in, form in every format, runs
// of results, our score v theirs, home and away, match-winners, where you rank, then one competition in detail. With a
// national side and a franchise, the chips at the top switch between them; it opens on whichever played last.
import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router";
import { get, type MyTeam as Data, type Result, type ScoutingPage } from "../api";
import { Lamps, Logo, Missing, Name, Num, PName, Tile } from "../kit/base";
import { SquadTable, Story, Ticker, TopList } from "../kit/blocks";
import { RankTrack, Ring } from "../kit/charts";
import { DepthRow, Msg } from "../kit/fm";
import { AdviceList, AfterLines, Grades, MarksTable, NextUp } from "../kit/myteam";
import { useInbox } from "./Inbox";
import { FormCard, MatchWinners, ScoreRows, Streaks, VenueRecord } from "../kit/season";
import { dayY, f0, f1, f2, fmtOf, ord } from "../format";
import { useReady } from "../ready";
import { Head, useShell } from "../shell/Shell";
import { T } from "../shell/names";

const greeting = () => { const h = new Date().getHours(); return h < 12 ? "Good morning, captain" : h < 18 ? "Good afternoon, captain" : "Good evening, captain"; };

export function MyTeam() {
  const { career, noCareer, nation } = useShell();
  const [params, setParams] = useSearchParams();
  const keep = nation ? `?nation=${encodeURIComponent(nation)}` : "";
  const team = params.get("team") ?? "", section = params.get("section") ?? "", scouting = params.get("view") === "scouting";
  const q = useQuery({ queryKey: ["myteam", team, section, career?.name], enabled: Boolean(career),
    queryFn: () => get<Data>(`/api/myteam?team=${encodeURIComponent(team)}&section=${encodeURIComponent(section)}`), retry: false });
  const box = useInbox();
  // Scouting asks for the team My team settled on (yours, or the one picked), and only once there is one: a career
  // with no matches yet has no team to scout
  const scTeam = q.data?.missing.everything ? "" : q.data?.team ?? "";
  const sc = useQuery({ queryKey: ["scouting", scTeam, career?.name], enabled: Boolean(career) && scouting && Boolean(scTeam), retry: false,
    queryFn: () => get<ScoutingPage>(`/api/scouting?team=${encodeURIComponent(scTeam)}`) });
  useReady(Boolean(q.data || q.error || noCareer) && (!scouting || !scTeam || Boolean(sc.data || sc.error)), `${team}|${section}|${scouting}`);
  const set = (k: string, v: string) => { const p = new URLSearchParams(params); if (v) p.set(k, v); else p.delete(k); if (k === "team") p.delete("section"); setParams(p); };
  if (noCareer) return <><Head title={greeting()} crumb="No career open yet" /><div className="grid"><Tile span={12} title="No career yet">
    <div className="plain">Add a career on the current site for now (<b>Start Stats Pack.bat</b>): the new site sees it straight away. Adding careers here comes in stage 4.</div></Tile></div></>;
  if (q.error) return <><Head title={greeting()} crumb="My team" /><div className="grid"><Tile span={12}><Missing why={String(q.error)} /></Tile></div></>;
  if (!q.data) return <><Head title={greeting()} crumb="Working out your season…" /><div className="empty">Working out your season…</div></>;
  const d = q.data, miss = d.missing;
  // the address named a team that hasn't played in this career (an old link, or another career's team): said so
  const asked = d.asked ? <Tile span={12} title="Not in this career"><div className="plain"><b>{d.asked}</b> hasn't played in this career (an old
    link, or a team from another career), so this is {d.team ? <><b>{d.team}</b>'s page</> : "the career as it is"}.</div></Tile> : null;
  if (miss.everything) return <><Head title={greeting()} crumb={d.team || "My team"} /><div className="grid">{asked}<Tile span={12}><Missing why={miss.everything} /></Tile></div></>;
  const cal = d.season, rs: Result[] = cal?.results ?? [];
  const news = (box.q.data?.messages ?? []).filter((m) => m.team === d.team && !m.read);
  const won = rs.filter((r) => r.outcome === "W").length, lost = rs.filter((r) => r.outcome === "L").length;
  const label = cal ? `${cal.year}–${String(cal.year + 1).slice(2)} season` : "";
  const b = d.block, tiles = d.banner?.tiles ?? [];
  const chips = d.teams.length > 1 ? d.teams : undefined;
  const sq = b?.squad ?? [];
  return (
    <>
      <Head title={greeting()} crumb={`${d.team} · ${d.mine ? "your team" : team && !d.asked ? "not one of your teams" : "the team with the most matches"}${label ? ` · ${label}` : ""}`}
        chips={chips} on={chips ? chips.indexOf(d.team) : 0} onChip={chips ? (i) => set("team", chips[i]!) : undefined} />
      <div className="grid">
        <div className="itabs">{["Season", "Scouting"].map((x) => (
          <button key={x} className={(x === "Scouting") === scouting ? "on" : ""} onClick={() => set("view", x === "Scouting" ? "scouting" : "")}>{x}</button>))}</div>
        {asked}
        {scouting ? <Scouting sc={sc.data} error={sc.error} team={d.team} keep={keep} /> : <>
        {!d.mine && <Tile span={12} title="Pick your team"><div className="plain">You haven't said which teams you play as, so this shows the team
          with the most matches. Pick yours on the current site (My team) for now; the question comes to the new site in stage 4.</div></Tile>}
        {d.ticker?.length ? <Ticker results={d.ticker} team={d.team} /> : null}

        <Tile span={4} rows={2} title="Season">
          <div className="row2"><Logo team={d.team} size={124} /><div><Num v={`${won}–${lost}`} px={48} />
            <div className="s"><b>{rs.length}</b> matches · won <b>{won + lost ? `${Math.round((won / (won + lost)) * 100)}%` : "–"}</b></div></div></div>
          {rs.length ? <Ring won={won} lost={lost} other={rs.length - won - lost} /> : <Missing why={miss.season} />}
          <div className="note">Every format, April to March{cal ? ` (Apr ${cal.year} – Mar ${cal.year + 1})` : ""}.</div>
        </Tile>
        <div className="sub" style={{ gridColumn: "span 8", gridTemplateColumns: `repeat(${Math.max(1, Math.min(3, tiles.length))}, minmax(0, 1fr))` }}>
          {tiles.slice(0, 3).map((t) => (
            <Tile span={1} key={t.section} title={fmtOf(t.section)}>
              <Num v={`${t.record.won}–${t.record.lost}`} px={46} />
              <div className="s">Elo <b>{f0(t.elo)}</b> <span className={(t.moved ?? 0) >= 0 ? "up" : "down"}>{(t.moved ?? 0) >= 0 ? "▲" : "▼"}{f0(Math.abs(t.moved ?? 0))}</span>
                {t.rank ? <> · <b>{ord(t.rank)}</b>/{t.teams}</> : null}</div>
              <div className="how">{t.season}{t.position ? ` · ${ord(t.position[2])} of ${t.position[3]} in the table` : ""}</div>
            </Tile>))}
        </div>
        <Tile span={8} title="Latest result · player of the match">
          {d.latest ? <Story kicker={`${d.latest.kicker} · player of the match`} headline={d.latest.result.headline || d.latest.result.result}
            report={d.latest.report} size={42} scores={{ team: d.team, opp: d.latest.result.opp, r: d.latest.result }} /> : <Missing why={miss.latest} />}
          {d.latest && <div className="note"><Link to={`/matches/${d.latest.result.id}${keep}`}>Open the match →</Link></div>}
        </Tile>
        {d.banner?.caption && <div className="note" style={{ gridColumn: "span 12", marginTop: -4 }}>{d.banner.caption}</div>}

        <Tile span={6} title="What changed after the latest game">{d.after ? <AfterLines a={d.after} keep={keep} /> : <Missing why={miss.after ?? "No match yet."} />}</Tile>
        <Tile span={6} title="Next up">{d.next_up ? <NextUp n={d.next_up} />
          : <div className="plain">No schedule for {d.team} yet. Your next match and series chances show here once there's one (Fixtures, stage 4; the current site has it now).</div>}</Tile>

        {news.length > 0 && <Tile span={12} title={`📬 Inbox · ${news.length} new for ${d.team}`} right={<Link className="lk" to={`/inbox${keep}`}>Open the inbox →</Link>}>
          <div className="inbox">{news.slice(0, 3).map((m) => <Msg key={m.id} m={m} keep={keep} onOpen={() => box.read([m.id])} onRemove={() => box.remove([m.id])} />)}</div>
          {news.length > 3 && <div className="note">and {news.length - 3} more in the inbox.</div>}</Tile>}

        {d.report ? <>
          <Tile span={8} title={`After the series · marks out of 10`} right={d.report.label}>
            <MarksTable r={d.report} keep={keep} />
            <div className="note">Each match is measured against the match itself: a batter's runs as a share of their side's runs and of the average side's,
              a bowler's wickets as a share of the wickets their side took, speed and economy in white-ball cricket, a quarter of a wicket a catch. A
              lone hundred counts for about twice one of three. The mark is where that series ranks among every player's series in {d.report.among} in
              this career: 5–6 usual, 8 the best one in seven, 10 the best one in forty. Batters are marked against batters, bowlers against bowlers.</div>
          </Tile>
          <Tile span={4} title="Who to bring in" right={d.report.advice.length ? undefined : "nobody struggling"}>
            {d.report.advice.length ? <AdviceList items={d.report.advice} keep={keep} />
              : <div className="plain">Nobody is struggling: no one has had two poor series running (4 or less in both) or three (4 or less on average). One bad series alone doesn't count.</div>}
            <div className="note">Candidates come from {d.team}'s own competitions of the same kind, their numbers converted to this level (never easier
              than 25% in first-class cricket, 15% in white-ball), and must beat your player by 10%. Settled: a few dismissals (or wickets) at the
              usual level are added to everyone's record, so seven good innings don't count for as much as thirty.</div>
          </Tile>
          {d.report.earlier.length > 0 && <Tile span={12} title="Earlier series · the top three">
            <div className="earlier">{d.report.earlier.map((e) => (
              <div key={e.series}><div className="k3">{e.label}</div>{e.top.map((p) => (
                <div className="how" key={p.player}><b className="mk">{p.mark}</b> {p.player}</div>))}</div>))}</div>
          </Tile>}
        </> : <Tile span={12} title="After the series · marks out of 10"><Missing why={miss.report ?? "No series yet."} /></Tile>}

        {d.forms?.map((f) => (
          <Tile key={f.section} span={d.forms!.length === 1 ? 12 : d.forms!.length === 2 ? 6 : 4} title={`Form · ${f.section}`}>
            <FormCard results={f.results} form={f.form} /></Tile>))}
        {rs.length > 0 && cal && <Tile span={12} title={`Runs of results · every format · ${label}`}><Streaks cal={cal} />
          <div className="note">Every match in order; the longest runs marked; the run you're on at the end.</div></Tile>}
        {rs.length > 0 && <Tile span={7} rows={2} title="Our score v theirs" right="this season">
          <ScoreRows results={rs.slice(-14)} scores={d.scores} />
          <div className="note">Both totals on one line for each match (the latest {Math.min(14, rs.length)}); green won, red lost; a Test's innings each on its own line.</div></Tile>}
        {d.venues && <Tile span={5} title="Home, away and neutral"><VenueRecord v={d.venues} team={d.team} /></Tile>}
        {d.series && <Tile span={5} title="Series this season">
          <div className="list">{d.series.slice(0, 6).map((s) => (
            <div className="li" key={s.key}><span>{s.opp ? <Logo team={s.opp} size={44} /> : null}</span>
              <div><Name p={s.opp || s.event} px={22} /><div className="how">{s.opp ? `${s.section} · ` : ""}{dayY(s.start).slice(-8)}</div></div>
              <span className="tag">{s.tournament ? `${s.won}–${s.lost}` : s.won > s.lost ? `won ${s.won}–${s.lost}` : s.won < s.lost ? `lost ${s.won}–${s.lost}` : `drew ${s.won}–${s.lost}`}</span></div>))}</div>
        </Tile>}
        {d.winners && <Tile span={12} title="Match-winners" right="your players of the match in your wins"><MatchWinners w={d.winners} /></Tile>}
        {tiles.some((t) => t.rank != null) && <Tile span={12} title={`Where ${d.team} rank · team rating (Elo)`}>
          <RankTrack banner={tiles} height={Math.max(150, 80 + tiles.length * 60)} /></Tile>}

        {b && <>
          <div className="part"><span className="tl2">{b.section} {b.season}</span>
            {d.sections && d.sections.length > 1 && <span className="itabs" style={{ display: "inline-flex", gridColumn: "auto", margin: 0 }}>{d.sections.map((s) => (
              <button key={s} className={s === b.section ? "on" : ""} onClick={() => set("section", s)}>{fmtOf(s)}</button>))}</span>}</div>
          <Tile span={6} title={`${b.section} ${b.season} so far`}>
            {b.so_far ? <><div className="row2" style={{ gap: 12, marginBottom: 10 }}><span className="k3" style={{ margin: 0 }}>Last 5</span><Lamps seq={b.so_far.last5} /></div>
              {b.so_far.line && <div className="plain">{b.so_far.line}</div>}
              {b.so_far.card.length > 0 && <><Grades card={b.so_far.card} />
                <div className="note">Grades against the average team in this competition this season: A well above, C about average, E well below.</div></>}</>
              : <Missing why={b.missing.so_far} />}
          </Tile>
          <Tile span={6} title="Your stars this season" right="▲▼ form over the last 3 innings">
            {b.stars && (b.stars.bat.length || b.stars.bowl.length) ? <table className="c"><tbody>
              {b.stars.bat.map((r) => <tr key={`b${r.player}`}><td><PName p={r.player} px={22} /></td><td className="r"><span className="tn">{r.runs}</span> runs</td>
                <td className="r"><span className="tn dimn">avg {f1(r.average)}</span></td><td className="r">{r.form}</td></tr>)}
              {b.stars.bowl.map((r) => <tr key={`w${r.player}`}><td><PName p={r.player} px={22} /></td><td className="r"><span className="tn">{r.wickets}</span> wkts</td>
                <td className="r"><span className="tn dimn">econ {f2(r.economy)}</span></td><td /></tr>)}</tbody></table> : <Missing why="No games yet." />}
            {b.alerts && b.alerts.length > 0 && <><div className="k3" style={{ marginTop: 14 }}>Worth a look</div>{b.alerts.map((a) => <div className="plain" key={a}><T>{a}</T></div>)}</>}
          </Tile>
          {sq.length > 0 && <>
            <Tile span={4} title="Top run-scorers"><TopList rows={[...sq].sort((x, y) => y.runs - x.runs).slice(0, 5)} value="runs" /></Tile>
            <Tile span={4} title="Top wicket-takers">{sq.some((x) => x.wickets > 0) ? <TopList rows={[...sq].filter((x) => x.wickets > 0).sort((x, y) => y.wickets - x.wickets).slice(0, 5)} value="wickets" gold /> : <Missing why="No wickets yet." />}</Tile>
            <Tile span={4} title="How you win">{b.how_you_win ? <>
              <div className="plain">Batting first <b>{b.how_you_win.first.pct}</b> ({b.how_you_win.first.won} of {b.how_you_win.first.decided}) · {b.how_you_win.second.word} <b>{b.how_you_win.second.pct}</b> ({b.how_you_win.second.won} of {b.how_you_win.second.decided}).</div>
              {b.how_you_win.extra && <div className="note">{b.how_you_win.extra}</div>}</> : <Missing why="No decided games here yet." />}</Tile>
            <Tile span={12} title={`Squad · everyone who has played for ${d.team} in ${b.section} ${b.season}`}>
              <SquadTable rows={sq} dim={new Set(sq.filter((x) => !x.recent).map((x) => x.player))} />
              <div className="note">Greyed out: not in the last 3 games.</div></Tile>
          </>}
          {d.depth && d.depth.section === b.section && <Tile span={12} title={`Squad depth · ${b.section}`} right="who starts, who's next, who's waiting in domestic cricket">
            <div className="depth">{d.depth.roles.filter((r) => r.starters.length || r.backups.length || r.waiting.length).map((r) => (
              <div className="drole" key={r.role}><div className="k3">{r.role}</div>
                {r.starters.map((p) => <DepthRow key={p.player} p={p} />)}
                {r.backups.length > 0 && <div className="dsub">Backups</div>}
                {r.backups.map((p) => <DepthRow key={p.player} p={p} />)}
                {r.waiting.length > 0 && <div className="dsub">Waiting in domestic cricket</div>}
                {r.waiting.map((w) => (
                  <div className={`dwait ${w.clears ? "ok" : ""}`} key={w.player}><PName p={w.player} px={19} />
                    <span className="gain">{w.gain == null ? "" : `${w.gain >= 0 ? "+" : ""}${Math.round(w.gain * 100)}%`}</span>
                    <div className="how">{w.side} · {w.raw_bat || w.raw_bowl}</div></div>))}
              </div>))}</div>
            <div className="note">Starters: who played in the latest series here. The number is their rating out of 20 here (the average of their attributes; – means
              not enough cricket here yet); the small marks are their last three series, newest first. Waiting: the best eligible domestic players, and how much
              better than your weakest in the role they are after the conversion (green: 10% or more).</div></Tile>}
          <Tile span={6} title={`📰 ${d.team} headlines`}>{b.headlines?.length ? <ul className="dots">{b.headlines.map((h) => <li key={h}><T>{h}</T></li>)}</ul>
            : <div className="note">Nothing big in your recent games.</div>}</Tile>
          <Tile span={6} title="Milestones and records in sight">{b.milestones?.length ? <table className="c"><tbody>{b.milestones.map((r) => (
            <tr key={r.player + r.chasing}><td><PName p={r.player} px={22} /></td><td><span className="why">{r.chasing}</span></td><td className="r"><span className="tn">{r.needs}</span></td></tr>))}</tbody></table>
            : <div className="note">Nobody close to a milestone or a record right now.</div>}</Tile>
          <Tile span={6} title="Rivals at a glance" right="most-played opponents here">
            {b.rivals?.rows.length ? <table className="c"><thead><tr><th>Opponent</th><th className="r">Played</th><th className="r">Record</th><th className="r">Win %</th></tr></thead>
              <tbody>{b.rivals.rows.map((r) => <tr key={r.opponent}><td><span className="cell"><Logo team={r.opponent} size={30} /><Name p={`${r.favourite ? "⭐ " : r.bogey ? "👻 " : ""}${r.opponent}`} px={21} /></span></td>
                <td className="r"><span className="tn dimn">{r.played}</span></td><td className="r"><span className="tn">{r.record}</span></td><td className="r"><span className="tn dimn">{r.win_pct}</span></td></tr>)}</tbody></table>
              : <Missing why="No opponents here yet." />}
            {b.rivals && b.rivals.next.length > 0 && <div className="field"><label htmlFor="mt-next">Next opponent</label>
              <select id="mt-next" className="pick" defaultValue={b.rivals.next[0]!.team}>{b.rivals.next.map((o) => (
                <option key={o.team} value={o.team}>{o.team}{o.note ? `  ·  ${o.note}` : ""}</option>))}</select>
              <span className="note" style={{ marginTop: 0 }}>Opponent preview: stage 2.</span></div>}
          </Tile>
          <Tile span={6} title="🏆 Trophy cabinet">
            {b.trophies?.length ? <table className="c"><thead><tr><th>Title</th><th>How</th><th>Runners-up</th></tr></thead><tbody>{b.trophies.map((r) => (
              <tr key={r.section + r.season}><td><Name p={`${r.section} ${r.season}`} px={21} /></td><td><span className="why">{r.how}</span></td><td><span className="why">{r.runners_up}</span></td></tr>))}</tbody></table>
              : <div className="note">No titles yet.</div>}
            {b.records && b.records.length > 0 && <><div className="k3" style={{ marginTop: 14 }}>{d.team} records in {b.section}</div>
              <table className="c"><tbody>{b.records.map((r) => <tr key={r.what}><td><span className="why">{r.what}</span></td><td><span className="why" style={{ color: "var(--ink)" }}>{r.detail}</span></td></tr>)}</tbody></table></>}
          </Tile>
        </>}
        {d.history && d.history.length > 0 && <Tile span={7} title="Season by season">
          <table className="c"><thead><tr><th>Season</th><th>Competition</th><th className="r">Record</th><th className="r">Win %</th><th>Finished</th></tr></thead>
            <tbody>{d.history.map((r) => (
              <tr key={r.season + r.section}><td><span className="tn dimn">{r.season}</span></td><td><Name p={r.section} px={20} /></td>
                <td className="r"><span className="tn">{r.won}–{r.lost}{r.drawn ? `–${r.drawn}` : ""}</span></td>
                <td className="r"><span className="tn dimn">{r.win_pct == null ? "–" : `${Math.round(r.win_pct)}%`}</span></td><td><span className="why">{r.finish || "–"}</span></td></tr>))}</tbody></table>
        </Tile>}
        <Tile span={d.history?.length ? 5 : 12} title="📝 Your match notes">
          {d.notes?.length ? <table className="c"><tbody>{d.notes.map((n) => (
            <tr key={n.id}><td><span className="tn dimn">{dayY(n.date)}</span><div><Link to={`/matches/${n.id}${keep}`} className="why lk">{n.home} v {n.away}</Link></div></td>
              <td><span className="why">{n.note}</span></td></tr>))}</tbody></table>
            : <div className="note">No notes yet. Open any match on Matches and write one under the summary.</div>}
          {d.latest && <div className="note">Latest scorecard: <Link to={`/matches/${d.latest.result.id}${keep}`}>{d.team} v {d.latest.result.opp}, {dayY(d.latest.result.date)}</Link></div>}
        </Tile>
        {d.career && <>
          <div className="part"><span className="tl2">Whole career</span>
            <span className="note" style={{ margin: 0 }}>every team and competition in {career?.name ?? "this career"}</span></div>
          <div className="sub" style={{ gridColumn: "span 12", gridTemplateColumns: "repeat(3, minmax(0, 1fr))" }}>
            {([["Matches", d.career.matches], ["Competitions", d.career.sections], ["Seasons", d.career.seasons], ["Players", d.career.players],
              ["Runs", d.career.runs], ["Wickets", d.career.wickets]] as [string, number][]).map(([k, v]) => (
              <Tile span={1} key={k} title={k}><Num v={v.toLocaleString("en-GB")} px={46} /></Tile>))}</div>
          <Tile span={12} title="📰 Headlines" right="hundreds, five-fors, collapses, titles and new records from the 10 latest matches">
            {d.career.headlines.length ? <ul className="dots">{d.career.headlines.map((h) => <li key={h}><T>{h}</T></li>)}</ul>
              : <div className="note">Nothing big in the last 10 matches. Hundreds, five-wicket hauls, collapses, titles and new records show up here.</div>}
            <div className="note">International matches are grouped by format (all Tests, all ODIs, all T20Is, World Cups included); everything else, like
              the IPL, the T20 Blast and each County Championship division, is its own competition. The latest results everywhere are on <Link to={`/matches${keep}`}>Matches</Link>.</div>
          </Tile>
        </>}
        </>}
      </div>
    </>
  );
}

/** The Scouting tab: in every competition the team plays, who is struggling after the latest series there, and who
 * could come in, with their numbers and the verdict (the same advice as "Who to bring in", for every competition). */
function Scouting({ sc, error, team, keep }: { sc?: ScoutingPage; error: unknown; team: string; keep: string }) {
  if (error) return <Tile span={12}><Missing why={String(error)} /></Tile>;
  if (!sc) return <div className="empty" style={{ gridColumn: "span 12" }}>Looking at {team}'s players in every competition…</div>;
  const struggling = sc.sections.reduce((n, s) => n + s.advice.length, 0);
  return <>
    <Tile span={12} title={`Scouting · ${sc.team}`} right={struggling ? `${struggling} struggling` : "nobody struggling"}>
      <div className="plain">Every competition {sc.team} plays, after its latest series or tournament: anyone who has had two poor series running
        (4 or less out of 10 in both), or three (4 or less on average), with the best players who could take their place. One bad series alone
        doesn't count.</div>
      <div className="note">Candidates come from {sc.team}'s own competitions of the same kind, their numbers converted to this level (never easier
        than 25% in first-class cricket, 15% in white-ball), and must beat your player by 10%. Settled: a few dismissals (or wickets) at the usual
        level are added to everyone's record, so seven good innings don't count for as much as thirty.</div>
    </Tile>
    {sc.sections.map((s) => (
      <Tile key={s.section} span={s.advice.length ? 12 : 6} title={`${fmtOf(s.section)}${s.series ? ` · after ${s.series}` : ""}`}
        right={s.advice.length ? `${s.advice.length} struggling` : undefined}>
        {s.advice.length ? <AdviceList items={s.advice} keep={keep} /> : <div className="plain">{s.none}</div>}
      </Tile>))}
  </>;
}
