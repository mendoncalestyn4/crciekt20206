// Matches: find a match (by competition, team, or typing), the best games, and one match in full: the summary with
// the player of the match, the report and its excitement rating, the win chance through the match, your side's best
// and worst, your notes, the scorecard one innings at a time, and every innings wicket by wicket.
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router";
import { get, type BestGames, type Finder, type MatchPage, remember } from "../api";
import { Drop, Explain, Logo, Missing, Name, Pick, PName, Tile } from "../kit/base";
import { MatchSummary, Scorecard } from "../kit/blocks";
import { ScoreRows } from "../kit/season";
import { BestTable, ExcitementPanel, NoteBox, WicketClimb, WinChanceChart } from "../kit/match";
import { fmtOf, NO_MATCHES } from "../format";
import { useReady } from "../ready";
import { Head, useShell } from "../shell/Shell";
import { T } from "../shell/names";

const PAGE = 15;   // matches listed at first, and how many more each "Show more" adds

export function MatchesHome() {
  const { nation, career } = useShell();
  const keep = nation ? `?nation=${encodeURIComponent(nation)}` : "";
  const [params, setParams] = useSearchParams();
  const section = params.get("section") ?? "", team = params.get("team") ?? "";
  const [typed, setTyped] = useState("");
  const [shown, setShown] = useState(PAGE);
  const f = useQuery({ queryKey: ["finder", section, team], queryFn: () =>
    get<Finder>(`/api/matches?section=${encodeURIComponent(section)}&team=${encodeURIComponent(team)}`) });
  const sec = f.data?.section ?? "";
  const best = useQuery({ queryKey: ["best", sec, team], enabled: Boolean(sec), queryFn: () =>
    get<BestGames>(`/api/matches/best?section=${encodeURIComponent(sec)}&team=${encodeURIComponent(team)}`) });
  useReady(Boolean((f.data && best.data) || f.error || best.error), `${sec}|${team}`);
  const set = (k: string, v: string) => {
    remember({ [k]: v });
    const p = new URLSearchParams(params);
    if (v) p.set(k, v); else p.delete(k);
    if (k === "section") p.delete("team");
    setParams(p);
  };
  const words = typed.toLowerCase().split(/\s+/).filter(Boolean);
  const hits = useMemo(() => (f.data?.matches ?? []).filter((m) => words.every((w) => m.label.toLowerCase().includes(w))),
    [f.data, typed]);   // eslint-disable-line react-hooks/exhaustive-deps
  if (f.error) return <><Head title="Matches" crumb="Find a match" /><div className="grid"><Tile span={12}><Missing why={String(f.error)} /></Tile></div></>;
  if (!f.data) return <><Head title="Matches" crumb="Find a match" /><div className="empty">Finding your matches…</div></>;
  if (career && career.matches === 0) return <><Head title="Matches" crumb="Find a match" /><div className="grid"><Tile span={12}><Missing why={NO_MATCHES} /></Tile></div></>;
  const d = f.data, all = d.section === "All sections", several = d.ticked.length > 1, every = d.sections.slice(1);
  return (
    <>
      <Head title="Matches" crumb="Find a match" />
      <div className="grid">
        <Tile span={12} title="Find a match" right={`${d.matches.length.toLocaleString("en-GB")} to choose from, newest first`}>
          <div className="plain">Narrow the list by competition or team, then type to search: a team, a date, a stage like "Final", or a result.</div>
          <div className="note">International matches are grouped by format (all Tests, all ODIs, all T20Is, World Cups included); everything else, like the
            IPL, the T20 Blast and each County Championship division, is its own competition.</div>
          <div className="drops">
            {every.length > 1 && <Drop label="Competition" all={every} on={all ? [] : d.ticked} none="Every competition" say={fmtOf}
              set={(v) => set("section", !v.length || v.length === every.length ? "All sections" : v.join("|"))} />}
            <Pick label="Team" value={d.team || "All teams"} options={d.teams} set={(v) => set("team", v === "All teams" ? "" : v)} />
            <div className="drop wide"><span className="droplab">Search</span>
              <input className="typed" value={typed} onChange={(e) => { setTyped(e.target.value); setShown(PAGE); }} placeholder="Type to search, e.g. 'Final' or 'Kent'" aria-label="Search the matches" /></div>
          </div>
          <div className="mlist">{hits.slice(0, shown).map((m) => (
            <Link key={m.id} to={`/matches/${m.id}${keep}`} className="mli">
              <span className="when">{m.label.split(" · ")[0]}</span>
              <span className="cell"><Logo team={m.home} size={40} /><Name p={`${m.home} v ${m.away}`} px={21} /><Logo team={m.away} size={40} /></span>
              <span className="how row2" style={{ gap: 8 }}><span className="cslot"><Logo comp={m.event} size={40} /></span>{m.name}</span><span className="res">{m.result}{m.checked === false ? <span className="chk bad" title="A sum on this scorecard didn't add up: open it to see which"> ⚠</span>
                : <span className="chk" title="Every sum on this scorecard checked against the others"> ✓</span>}</span></Link>))}
            {!hits.length && <div className="empty">No match fits "{typed}".</div>}</div>
          {hits.length > shown && <div className="field"><button className="btn quiet" onClick={() => setShown(shown + 30)}>Show 30 more</button>
            <span className="note" style={{ marginTop: 0 }}>Showing the newest {shown} of {hits.length.toLocaleString("en-GB")}; type to narrow the list.</span></div>}
        </Tile>
        <Tile span={12} title={`Our score v theirs${d.scores ? ` · ${d.scores.team} · ${d.name}` : ""}`} right={d.scores ? `the latest ${d.scores.results.length}, newest at the bottom` : undefined}>
          {d.scores ? <><ScoreRows results={d.scores.results} scores={d.scores.summary} />
            <div className="note">Both totals on one line for each match: {d.scores.team}'s in gold, the other side's in blue, joined in green when they won and
              red when they lost; a Test's innings each on its own line. Games shortened by rain are left out of the averages.</div>
            {d.scores.summary.lines && <Explain {...d.scores.summary.lines} />}</>
            : <div className="plain">"Pick a team to see its totals against the other side's, match by match (each competition's averages kept apart)."</div>}
        </Tile>
        <Tile span={12} title={`Best games · ${d.name}${d.team !== "All teams" ? ` · ${d.team}` : ""}`} right="rated 0–10 for excitement">
          {best.data ? (best.data.rows.length ? <BestTable rows={best.data.rows} showSection={all || several} keep={keep} /> : <Missing why="No matches here yet." />)
            : <div className="empty">Rating every match…</div>}
          <div className="note">Out of 10: the finish up to 7 (a tie, a 1-run, 1-wicket or last-ball win is 7, a super over 8, and a draw
            with the last pair holding on up to 7), a comeback up to 2 (read from the scorecard: the runs still needed against what the
            wickets left usually add), the stakes up to 1 (a final or series decider; a semi-final 0.7; levelling a series 0.5), and big
            moments up to ½ (a hundred, a big haul, both sides scoring big, a big chase). Ranked within each competition.</div>
        </Tile>
      </div>
    </>
  );
}

const TABS = ["Summary", "Scorecard", "Wicket by wicket"];
const VIEWS = ["summary", "scorecard", "wickets"];

export function MatchView() {
  const { pick = "" } = useParams();
  const { nation, career } = useShell();
  const keep = nation ? `?nation=${encodeURIComponent(nation)}` : "";
  const [params, setParams] = useSearchParams();   // the view is in the address, so a link or a refresh keeps it
  const tab = Math.max(0, VIEWS.indexOf(params.get("view") ?? "summary"));
  const setTab = (i: number) => { const p = new URLSearchParams(params); if (i) p.set("view", VIEWS[i]!); else p.delete("view"); setParams(p); };
  const q = useQuery({ queryKey: ["match", pick], queryFn: () => get<MatchPage>(`/api/match/${encodeURIComponent(pick)}`), retry: false });
  useReady(Boolean(q.data || q.error), `${pick}|${tab}`);
  if (q.error) return <><Head title="Matches" crumb="No such match" /><div className="grid"><Tile span={12}><Missing why={String(q.error)} />
    <Link className="btn quiet" to={`/matches${keep}`}>Find a match</Link></Tile></div></>;
  if (!q.data) return <><Head title="Matches" crumb="Opening the match…" /><div className="empty">Working out the match…</div></>;
  const d = q.data;
  const m = { ...d.match, pom: d.match.pom ? { ...d.match.pom, report: d.report } : null };
  return (
    <>
      <Head title="Matches" crumb={d.kicker} chips={TABS} on={tab} onChip={setTab} />
      <div className="back"><Link to={`/matches?section=${encodeURIComponent(d.section)}${nation ? `&nation=${encodeURIComponent(nation)}` : ""}`}>← Every {d.section} match</Link></div>
      <div className="grid">
        {tab === 0 && <>
          <Tile span={12}><MatchSummary m={m} />
            {d.checked && (d.checked.ok
              ? <div className="note" title={`Checked: ${d.checked.checks.join("; ")}.`}><span className="chk">✓</span> Checked: every sum on this scorecard adds up
                (the totals, extras, overs, wickets, fall of wickets and the result).</div>
              : <div className="plain"><span className="chk bad">⚠</span> {d.checked.problems.length === 1 ? "One sum" : `${d.checked.problems.length} sums`} on
                this scorecard didn't add up, so treat its numbers with care: {d.checked.problems.join("; ")}.</div>)}
            {d.checked?.unclear?.length ? <div className="note">Bowlers who share a name: {d.checked.unclear.join("; ")}.</div> : null}</Tile>
          {d.rain && <Tile span={12} title="🌧️ Rain"><div className="plain">{d.rain}</div></Tile>}
          {d.corrected?.length ? <Tile span={12} title="✎ Scorecard put right">
            <div className="plain">The game's scorecard didn't add up; the card itself shows what happened, so it's counted this way:</div>
            {d.corrected.map((x) => <div className="how" key={x}>{x}.</div>)}</Tile> : null}
          <Tile span={7} title="Excitement rating · out of 10">
            {d.excitement ? <><ExcitementPanel ex={d.excitement} section={d.section} />{d.excitement.lines && <Explain {...d.excitement.lines} />}</>
              : <Missing why="Too few matches in this competition to rate yet." />}
            {!d.match.pom && <div className="deck" style={{ marginTop: 12 }}><T>{d.report}</T></div>}
          </Tile>
          <Tile span={5} title="📝 Your notes on this match"><NoteBox mid={d.id} note={d.note} /></Tile>
          {d.win && <Tile span={12} title="Win chance through the match" right={d.win.none ? undefined : `${d.win.multi ? "won / drawn / lost" : "chance"} for ${d.win.team1}`}>
            {d.win.none ? <Missing why={d.win.none} /> : <>
              <WinChanceChart win={d.win} mine={career?.my_teams ?? []} />
              <div className="note">At the start of each innings and after every wicket ({d.win.team1} batted first); dotted lines: a new innings. The last point is the result.</div>
              <Explain is_={d.win.is_} best={d.win.best} best_label={d.win.best_label} for_={d.win.for_} /></>}
          </Tile>}
          <Tile span={6} title="Top scores">
            <table className="c"><thead><tr><th>Batter</th><th className="r">Score</th><th className="r">BF</th></tr></thead>
              <tbody>{d.top_scores.map((r) => (
                <tr key={r.player + r.team}><td><span className="cell"><Logo team={r.team} size={40} /><PName p={r.player} px={21} /></span></td>
                  <td className="r"><span className="tn">{r.score}</span></td><td className="r"><span className="tn dimn">{r.balls}</span></td></tr>))}</tbody></table>
          </Tile>
          <Tile span={6} title="Best bowling">
            <table className="c"><thead><tr><th>Bowler</th><th className="r">Figures</th><th className="r">Overs</th></tr></thead>
              <tbody>{d.best_bowling.map((r) => (
                <tr key={r.player + r.team}><td><span className="cell"><Logo team={r.team} size={40} /><PName p={r.player} px={21} /></span></td>
                  <td className="r"><span className="tn">{r.figures}</span></td><td className="r"><span className="tn dimn">{r.overs}</span></td></tr>))}</tbody></table>
          </Tile>
          {d.sides.map((s) => (
            <Tile span={d.sides.length === 1 ? 12 : 6} key={s.team} title={`⭐ ${s.team}: best and worst in this match`}>
              <div className="bw"><div><div className="k3">Best</div>{s.best.map((b, i) => (
                <div className="bwr" key={b.player}><span>{["🥇", "🥈", "🥉"][i]}</span><PName p={b.player} px={22} /><span className="how">{b.figures}</span></div>))}</div>
                <div><div className="k3">Did least</div>{s.worst.length ? s.worst.map((b) => (
                  <div className="bwr" key={b.player}><span>🔻</span><PName p={b.player} px={22} /><span className="how">{b.figures}</span></div>))
                  : <div className="note">Everyone who batted or bowled chipped in.</div>}</div></div>
              <div className="note">By match impact (as on the player pages): runs, with a strike-rate part in white-ball cricket; wickets worth the
                competition's runs per wicket, with an economy part (no fielding is counted). Did least: of those who batted in the top seven or bowled.</div>
            </Tile>))}
        </>}
        {tab === 1 && <Scorecard m={m} />}
        {tab === 2 && <>
          {d.wickets.innings.map((inn) => (
            <Tile span={6} key={inn.innings_no} title={`${inn.label} · wicket by wicket`}>
              {inn.steps.length ? <WicketClimb inn={inn} par={d.wickets.par} /> : <Missing why="No wickets fell and no stand to show." />}
            </Tile>))}
          <Tile span={12} title="How to read it">
            <div className="plain">Each bar is one wicket: it climbs from the score when that stand began to the score when the wicket fell, so its
              height is the stand. A row of short bars is a collapse; one tall bar is a big stand that rebuilt the innings. Gold: still together
              at the end. Green: a stand of 50 or more.</div>
            {d.wickets.par ? <div className="plain">Grey dashed line: par, the usual score when each wicket falls in {d.wickets.section}. Above it is
              ahead of the game, below it behind. A late wicket's par comes only from the innings that got that far, so it stops where too
              few do.</div> : <div className="plain">No par line yet: too few {d.wickets.section} matches to say what's usual.</div>}
            <div className="plain">The scorecard gives the score at each wicket but not the over, so this shows wickets, not overs.</div>
            {d.wickets.innings.some((i) => i.steps.length) && <Explain is_={d.wickets.is_} best={d.wickets.best} best_label={d.wickets.best_label} for_={d.wickets.for_} />}
          </Tile>
        </>}
      </div>
    </>
  );
}
