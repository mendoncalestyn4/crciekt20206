// The style guide: every piece of the chart kit, drawn from your own career (your team's latest section and season),
// in your team's colours. Each piece says where it will be used. A piece the career can't fill yet says why.
import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { useNavigate } from "react-router";
import { get, type Result, type StyleGuide as Data } from "../api";
import { Hero, Lamps, Logo, Missing, Name, Num, Sub, Tile } from "../kit/base";
import { KeepScores, MatchRows, MatchSummary, PercentileBars, PomCard, Scorecard, SquadTable, Story, TopList, TvTable, Ticker } from "../kit/blocks";
import { EloLines, InningsBars, LeaderBars, RankRace, RankTrack, Ring, RingList, TugOfWar } from "../kit/charts";
import { BatFirstSides, FormBig, FormCard, Goes, Ladder, MatchWinners, MonthTiles, ScoreRows, StrengthPanel, Streaks, VenueRecord } from "../kit/season";
import { ab, cap, day, dayY, f0, f1, f2, fmtOf, ord, overs, plural, rnd } from "../format";
import { useReady } from "../ready";
import { Head, useShell } from "../shell/Shell";
import { useTheme } from "../theme";

const Part = ({ title, sub }: { title: string; sub: string }) => (
  <div style={{ gridColumn: "span 12", marginTop: 18 }}><div className="tl2">{title}</div><div className="note" style={{ marginTop: 2 }}>{sub}</div></div>
);
const Used = ({ on }: { on: string }) => <div className="note">Used on: {on}.</div>;
/** A piece the plan places on several pages: the piece (8 columns, as on its mock-up) and where it goes beside it. */
const Placed = ({ title, right, goes, children }: { title: string; right?: string; goes: [string, string][]; children: ReactNode }) => (
  <><Tile span={8} title={title} right={right}>{children}</Tile><Tile span={4} title="Where it goes" style={{ alignSelf: "start" }}><Goes items={goes} /></Tile></>
);

export function StyleGuide() {
  const t = useTheme();
  const go = useNavigate();
  const { nation } = useShell();
  const q = useQuery({ queryKey: ["styleguide"], queryFn: () => get<Data>("/api/styleguide"), retry: false });
  const nations = useQuery({ queryKey: ["nations"], queryFn: () => get<{ nations: string[] }>("/api/nations") });
  useReady(Boolean(q.data || q.error), `${nation}`);
  if (q.isLoading) return <><Head title="Style guide" crumb="Working out the numbers…" /><div className="empty">Working out every piece from your career…</div></>;
  if (q.error || !q.data) return <><Head title="Style guide" crumb="No career open" /><div className="grid"><Tile span={12} title="No career yet"><Missing why={String(q.error)} /></Tile></div></>;
  const d = q.data, team = d.team, miss = d.missing;
  if (!team) return <><Head title="Style guide" crumb={d.career} /><div className="grid"><Tile span={12}><Missing why={miss.everything} /></Tile></div></>;
  const season = d.this_season ?? [], seq = season.map((r) => r.outcome);
  const won = seq.filter((o) => o === "W").length, lost = seq.filter((o) => o === "L").length;
  const st = d.star, L = d.leaders, s = d.series, m = d.match, latest = d.results?.[0], cal = d.calendar;
  const lanes = cal ? [...cal.formats].reverse().map((f) => f.section).filter((x) => d.strength?.some((r) => r.section === x)) : [];
  const mineBat = (d.squad ?? []).filter((x) => x.runs > 0).sort((a, b) => b.runs - a.runs).slice(0, 5);
  const mineBowl = (d.squad ?? []).filter((x) => x.wickets > 0).sort((a, b) => b.wickets - a.wickets).slice(0, 5);
  const pal = [t.led, t.warm, t.cream, t.win];
  return (
    <>
      <Head title="Style guide" crumb={`${team} · ${d.section} ${d.season} · from ${d.career}`}
        chips={[fmtOf(d.section ?? ""), String(d.season ?? "")]} />
      <div className="grid">
        <Hero logo={team} px={160} h={200} kicker={`${team} · ${d.section} · ${d.season}`} title={team} size={96}
          side={["This season", `${won}–${lost}`, `${season.length} match${season.length === 1 ? "" : "es"}`]} />
        {d.results?.length ? <Ticker results={d.results} team={team} /> : null}

        <Part title="Page parts" sub="The panel at the top of a page, the latest-results strip, numbers in tiles, lamps, lists." />
        <Sub cols={Math.max(3, Math.min(5, d.banner?.length ?? 0))}>
          {(d.banner ?? []).slice(0, 5).map((b) => (
            <Tile span={1} key={b.section} title={fmtOf(b.section)}>
              <Num v={`${b.record.won}–${b.record.lost}`} px={46} />
              <div className="s">Elo <b>{f0(b.elo)}</b> <span className={(b.moved ?? 0) >= 0 ? "up" : "down"}>{(b.moved ?? 0) >= 0 ? "▲" : "▼"}{f0(Math.abs(b.moved ?? 0))}</span>
                {b.rank ? <> · <b>{ord(b.rank)}</b>/{b.teams}</> : null}</div>
            </Tile>))}
        </Sub>
        {!d.banner?.length && <Tile span={12} title="Season tiles"><Missing why={miss.banner} /></Tile>}
        <Tile span={4} title="Season" rows={2}>
          <div className="row2"><Logo team={team} size={124} /><div><Num v={`${won}–${lost}`} px={48} />
            <div className="s"><b>{season.length}</b> matches · won <b>{won + lost ? `${rnd((won / (won + lost)) * 100)}%` : "–"}</b></div></div></div>
          {season.length ? <Ring won={won} lost={lost} other={season.length - won - lost} /> : <Missing why={miss.this_season} />}
          <Used on="My team" />
        </Tile>
        <Tile span={4} title={`Form · the last ten of ${d.season}`}>
          <Lamps seq={seq.slice(-10)} />
          <div className="s" style={{ marginTop: 10 }}>Oldest → newest · <b>{seq.slice(-10).filter((o) => o === "W").length}</b> of the last {Math.min(10, seq.length)} won</div>
          <Used on="My team, Matches" />
        </Tile>
        <Tile span={4} title={`Form line · ${fmtOf(d.section ?? "")}`}>
          {season.length && d.form ? <FormCard results={season} form={d.form} /> : <Missing why={miss.form ?? miss.this_season} />}
          <Used on="My team (one for each format)" />
        </Tile>
        <Tile span={4} title={`Top run-scorers · ${team}`}>
          {mineBat.length ? <TopList rows={mineBat} value="runs" /> : <Missing why={miss.squad} />}
        </Tile>
        <Tile span={4} title={`Top wicket-takers · ${team}`}>
          {mineBowl.length ? <TopList rows={mineBowl} value="wickets" gold /> : <Missing why={miss.squad} />}
        </Tile>

        <Part title="The season" sub={`April to March, every format${cal ? ` (Apr ${cal.year} – Mar ${cal.year + 1})` : ""}: every match on its day, the form line, the runs of results.`} />
        {cal ? <Tile span={12} title="The season · month by month" right={`${cal.results.length} matches`}>
          <MonthTiles cal={cal} /><Used on="Seasons (the season calendar)" /></Tile>
          : <Tile span={12} title="The season calendar"><Missing why={miss.calendar} /></Tile>}
        {/* the big form line from five matches (before that, the card above says when it starts) */}
        {season.length && d.form?.trend ? <Tile span={12} title={`Form · ${d.section} ${d.season} · every match`}
          right={d.form.trend.now != null ? `now ${d.form.trend.now}%${d.form.trend.word && d.form.trend.prev != null ? ` · ${d.form.trend.word} from ${d.form.trend.prev}%` : ""}` : "last five: no result"}>
          <FormBig results={season} form={d.form} />
          <div className="note">The line is the share of the last five matches won, on its own scale; the results sit under it. The first five are dashed until there are five to count.</div>
          <Used on="My team (one for each format)" /></Tile> : null}
        {cal?.results.length ? <Tile span={12} title={`Runs of results · every format · ${cal.year}`}><Streaks cal={cal} />
          <Used on="My team (the run you're on), Teams (every team's runs), Leaders · records (the longest ever)" /></Tile> : null}

        <Part title="Leaderboards" sub="Broadcast's bars: names on the left, the number and team on the right, your team lit up." />
        <Tile span={6} title="Most runs" right="runs · team">
          {L?.runs.length ? <LeaderBars rows={L.runs} value="runs" mine={team} height={624} /> : <Missing why={miss.leaders} />}
        </Tile>
        <Tile span={6} title="Most wickets" right="wickets · team">
          {L?.wickets.length ? <LeaderBars rows={L.wickets} value="wickets" mine={team} height={624} /> : <Missing why={miss.leaders} />}
        </Tile>
        <Tile span={6} title="Most sixes">{L?.sixes.length ? <LeaderBars rows={L.sixes} value="sixes" mine={team} height={360} valSize={24} /> : <Missing />}</Tile>
        <Tile span={6} title="Best average · 4+ innings">{L?.average.length ? <LeaderBars rows={L.average} value="average" mine={team} height={360} valSize={24} fmt={f1} /> : <Missing why="Nobody has batted 4 times yet." />}</Tile>
        <Tile span={6} title="Best strike rate · 60+ balls" right="runs per 100 balls">{L?.strike_rate.length ? <LeaderBars rows={L.strike_rate} value="strike_rate" mine={team} height={360} valSize={24} fmt={f0} /> : <Missing why="Nobody has faced 60 balls yet." />}</Tile>
        <Tile span={6} title="Best economy · 10+ overs" right="lower is better">{L?.economy.length ? <LeaderBars rows={L.economy} value="economy" mine={team} height={360} valSize={24} fmt={f2} /> : <Missing why="Nobody has bowled 10 overs yet." />}</Tile>
        <div style={{ gridColumn: "span 12" }}><Used on="Leaders, Rankings, Squad, Seasons" /></div>

        <Part title="A player" sub={st ? `${team}'s top run-scorer in ${d.section} ${d.season}: ${st.player}` : "The team's top run-scorer this season"} />
        {st ? <>
          <Hero logo={team} px={186} kicker={`${team} · batter · ${d.section} ${d.season}`} title={st.player} size={120}
            side={st.rating ? ["Batting rating", f0(st.rating.value), `${ord(st.rating.rank)} for ${team}`] : ["Runs", f0(st.runs), `${st.innings.length} innings`]} />
          <Sub cols={5}>{([["Runs", st.runs, `${st.innings.length} innings · ${st.innings.filter((i) => !i.out).length} not out`],
            ["Average", f1(st.outs ? st.runs / st.outs : null), "runs per dismissal"],
            ["Strike rate", f1(st.innings.reduce((a, i) => a + i.balls, 0) ? (st.runs / st.innings.reduce((a, i) => a + i.balls, 0)) * 100 : null), "runs per 100 balls"],
            ["50s", st.innings.filter((i) => i.runs >= 50 && i.runs < 100).length, plural(st.innings.filter((i) => i.runs >= 100).length, "hundred")],
            ["Best", (() => { const b = [...st.innings].sort((a, c) => c.runs - a.runs)[0]; return b ? `${b.runs}${b.out ? "" : "*"}` : "–"; })(),
              (() => { const b = [...st.innings].sort((a, c) => c.runs - a.runs)[0]; return b ? `v ${b.opp} · ${day(b.date)}` : ""; })()]] as [string, string | number, string][])
            .map(([k, v, sub]) => <Tile span={1} key={k} title={k}><Num v={v} px={72} /><div className="s">{sub}</div></Tile>)}</Sub>
          <Tile span={7} title={`Every innings · ${d.section} ${d.season}`}>
            <InningsBars innings={st.innings} /><div className="note">Each bar is one innings, oldest first. Green = 50 or more; * = not out.</div>
          </Tile>
          <Tile span={5} title={`How they compare · v ${st.pool} batters`}>
            {Object.keys(st.percentiles).length ? <PercentileBars values={st.percentiles} /> : <Missing why="Too few batters to compare with yet." />}
            <div className="note">Percentiles among {st.among} (3+ innings): 100 = the best, 50 = the middle of the pack.</div>
          </Tile>
          <Tile span={4} title="Where the runs come from">
            <RingList items={[["Fours", st.from4, pal[0]!], ["Sixes", st.from6, pal[1]!], ["Running", st.running, pal[2]!]]} centre={String(st.runs)} sub={`${fmtOf(st.section)} runs`} />
          </Tile>
          <Tile span={4} title="How they get out">
            {st.outs ? <RingList items={Object.entries(st.how_out).sort((a, b) => b[1] - a[1]).map(([k, v], i) => [cap(k), v, pal[i % 4]!])} centre={String(st.outs)} sub="dismissals" />
              : <Missing why="Not out yet this season." />}
          </Tile>
          <Tile span={4} title="Every format">
            <table className="tv"><thead><tr><th>Format</th><th className="r">Inns</th><th className="r">Runs</th><th className="r">Avg</th><th className="r">SR</th><th className="r">HS</th></tr></thead>
              <tbody>{st.formats.map((v) => (
                <tr key={v.section} className={v.section === st.section ? "me" : ""} data-parts={v.parts ? JSON.stringify(v.parts) : undefined}><td><Name p={fmtOf(v.section)} px={22} /></td>
                  <td className="r"><span className="tn dimn">{v.innings}</span></td><td className="r"><span className="tn">{v.runs}</span></td>
                  <td className="r"><span className="tn dimn">{f1(v.average)}</span></td><td className="r"><span className="tn dimn">{f0(v.strike_rate)}</span></td>
                  <td className="r"><span className="tn dimn">{v.high_score_text || "–"}</span></td></tr>))}</tbody></table>
            <div className="note" style={{ marginTop: 14 }}>{st.formats.map((v) => `${fmtOf(v.section)}: ${v.fours} fours, ${v.sixes} sixes`).join(" · ")}</div>
          </Tile>
          <div style={{ gridColumn: "span 12" }}><Used on="Players (the profile), Compare players" /></div>
        </> : <Tile span={12} title="The player pieces"><Missing why={miss.star} /></Tile>}

        <Part title="The latest match" sub="Almanack's player-of-the-match story, then the TV match summary and the scorecard one innings at a time." />
        {m && latest ? <>
          <Tile span={8} title="Latest result · player of the match">
            {m.pom ? <Story kicker={`${fmtOf(m.section)}${m.of ? ` ${m.no} of ${m.of}` : ""} · ${dayY(m.date)} · player of the match`} headline={m.pom.headline}
              report={m.pom.report} size={42} scores={{ team, opp: latest.opp, r: latest }} /> : <Missing why="No player of the match on this scorecard." />}
          </Tile>
          <Tile span={4} title="Player of the match">{m.pom ? <PomCard pom={m.pom} /> : <Missing />}</Tile>
          <Tile span={12}><MatchSummary m={m} /></Tile>
          <Scorecard m={m} />
          <div style={{ gridColumn: "span 12" }}><Used on="Matches, My team (the latest result)" /></div>
        </> : <Tile span={12} title="The match pieces"><Missing why={miss.match} /></Tile>}
        {d.match_test && <>
          <Part title="A Test" sub="Four innings: one batter and one bowler in each, as on the TV graphic." />
          <Tile span={12}><MatchSummary m={d.match_test} /></Tile>
        </>}

        <Part title="A series" sub={s ? `${team}'s latest series: v ${s.opp}` : "The team's latest series"} />
        {s ? <>
          <Tile span={8} title="The series">
            <div className="kick">{fmtOf(s.section)} series · {team} v {s.opp} · {s.matches.length} match{s.matches.length === 1 ? "" : "es"}</div>
            <div className="hl" style={{ fontSize: 52 }}><KeepScores text={s.story.headline} /></div><div className="deck">{s.story.deck}</div>
            <div className="sq" style={{ marginTop: 18, gap: 18 }}>{s.matches.map((r: Result) => (
              <span className="row2" style={{ gap: 8 }} key={r.id}><Lamps seq={[r.outcome]} /><span className="s" style={{ margin: 0 }}>{fmtOf(r.section)} {r.no} · {day(r.date)}</span></span>))}</div>
          </Tile>
          <Tile span={4} title="Player of the series">
            {s.story.player_of_series ? <>
              <div className="row2" style={{ gap: 16 }}><Logo team={s.story.player_of_series.team} size={82} />
                <div><Name p={s.story.player_of_series.player} px={46} /><div className="s" style={{ marginTop: 2 }}>{s.story.player_of_series.team} · {s.story.player_of_series.matches} matches</div></div></div>
              <div className="rule" /><div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                <div><Num v={s.story.player_of_series.runs} px={64} /><div className="s">runs</div></div>
                <div><Num v={s.story.player_of_series.wickets} px={64} /><div className="s">wickets</div></div></div>
              {!s.story.complete && <div className="note">So far: the series isn't over yet.</div>}
            </> : <Missing />}
          </Tile>
          <Tile span={5} title="Series score · tug of war"><TugOfWar matches={s.matches} progress={s.progress} team={team} opp={s.opp} />
            <div className="note">Above the line {team} lead, below it {s.opp} do.</div><Used on="Seasons, My team (the main pages)" /></Tile>
          <Tile span={7} title="Match by match"><MatchRows results={s.matches} team={team} compact /></Tile>
          <Tile span={12} title="Series score · the ladder" right={s.decider ? "the decider marked" : undefined}><Ladder s={s} team={team} />
            <Used on="Seasons · the series analysis" /></Tile>
          <Tile span={6} title="Most runs in the series">
            <TvTable rows={s.most_runs} mine={team} cols={[["Runs", (x) => x.runs], ["Inns", (x) => x.inns], ["HS", (x) => x.hs], ["SR", (x) => (x.balls ? f0((x.runs / x.balls) * 100) : "–")]]} parts={(x) => ({ runs: x.runs, bf: x.balls, inns: x.inns })} />
          </Tile>
          <Tile span={6} title="Most wickets in the series">
            <TvTable rows={s.most_wickets} mine={team} cols={[["Wkts", (x) => x.wickets], ["Runs", (x) => x.runs], ["Overs", (x) => overs(x.balls)], ["Econ", (x) => f2(x.economy)]]} />
          </Tile>
          <div style={{ gridColumn: "span 12" }}><Used on="Seasons (series), My team" /></div>
        </> : <Tile span={12} title="The series pieces"><Missing why={miss.series} /></Tile>}

        <Part title="How the team wins" sub="Our score against theirs, batting first or chasing, against stronger and weaker sides, home and away, and who wins the matches." />
        {season.length ? <Placed title={`Our score v theirs · ${d.section} ${d.season}`} right="newest first"
          goes={[["Matches · stage 1", "Under the list of results: the season at a glance."], ["My team · stage 1", "A small one for your latest format."]]}>
          <ScoreRows results={[...season].reverse()} scores={d.scores} />
          <div className="note">Your total (gold) and theirs (blue), joined in green when you won and red when you lost. A Test shows each innings on its own line.</div></Placed> : null}
        {d.bat_first ? <Placed title={`Batting first or chasing · ${d.section} ${d.season}`}
          goes={[["Opponent preview · stage 2", "Before your next match: your record and theirs each way."], ["Team vs team · stage 2", "Both sides each way."], ["Insights · stage 3", "Bat or bowl first, for every team."]]}>
          <BatFirstSides bf={d.bat_first} /><div className="note">Games shortened by rain are left out of the totals.</div></Placed>
          : <Tile span={12} title="Batting first or chasing"><Missing why={miss.bat_first} /></Tile>}
        {d.strength?.length ? <Placed title={`Against stronger and weaker sides · ${cal?.year ?? d.season}`}
          goes={[["Teams · stage 2", "With the team's other analyses."], ["Leaders · rankings · stage 3", "Next to the team ratings it comes from."], ["Insights · stage 3", "Every team: who beats the strong and who only beats the weak."]]}>
          <StrengthPanel rows={d.strength} lanes={lanes} /><div className="note">Each match placed by how the two sides were rated (Elo) just before it, in its format.</div></Placed> : null}
        {d.venues && cal?.results.length ? <Placed title={`Home, away and neutral · ${cal.year}`}
          goes={[["My team · stage 1", "Home and away this season."], ["Teams · stage 2", "Beside the home record (\"fortress\")."], ["Opponent preview · stage 2", "Your record in the country of your next match."]]}>
          <VenueRecord v={d.venues} team={team} /><div className="note">The scorecards don't name the ground, so it goes by the home side{d.venues.nation ? "'s country" : ""}.</div></Placed> : null}
        {d.winners?.players.length ? <Placed title={`Match-winners · ${d.winners.wins} wins in ${cal?.year ?? d.season}`}
          goes={[["My team · stage 1", "With your stars: who wins you matches."], ["Players · stage 1", "On each player: the matches they won for you."], ["Seasons · season review · stage 2", "The season's match-winners, next to the MVPs."]]}>
          <MatchWinners w={d.winners} /></Placed> : null}

        <Part title="Rankings and results" sub="Team ratings (Elo) through the season and every team's rank." />
        {d.banner?.some((b) => b.rank) ? <Tile span={7} title={`Where ${team} rank · team rating (Elo)`}><RankTrack banner={d.banner} /></Tile> : null}
        {d.elo ? <>
          <Tile span={5} title="Team table" rows={d.banner?.some((b) => b.rank) ? 2 : undefined}>
            <table className="c"><thead><tr><th className="r">#</th><th>Team</th><th className="r">Elo</th><th className="r">Played</th></tr></thead>
              <tbody>{d.elo.table.map((x) => (
                <tr key={x.team} className={x.team === team ? "me" : ""}><td className="r"><span className="tn dimn">{x.rank}</span></td>
                  <td><span className="cell"><Logo team={x.team} size={38} /><Name p={x.team} px={21} /></span></td>
                  <td className="r"><span className="tn">{f0(x.elo)}</span></td><td className="r"><span className="tn dimn">{x.played}</span></td></tr>))}</tbody></table>
          </Tile>
          <Tile span={7} title={`Rating through the season · ${d.section}`}><EloLines elo={d.elo} team={team} /></Tile>
          <Tile span={12} title="Every team's rank after each match day"><RankRace elo={d.elo} team={team} /></Tile>
        </> : <Tile span={12} title="Ratings"><Missing why={miss.elo} /></Tile>}
        {d.ratings && (d.ratings.bat.length || d.ratings.bowl.length) ? <>
          <Tile span={6} title={`Best batters · ${fmtOf(d.section ?? "")} rating (out of 1000)`}>
            {d.ratings.bat.length ? <LeaderBars rows={d.ratings.bat} value="batting" mine={team} height={480} valSize={24} /> : <Missing />}</Tile>
          <Tile span={6} title={`Best bowlers · ${fmtOf(d.section ?? "")} rating (out of 1000)`}>
            {d.ratings.bowl.length ? <LeaderBars rows={d.ratings.bowl} value="bowling" mine={team} height={480} valSize={24} /> : <Missing />}</Tile>
        </> : null}
        <div style={{ gridColumn: "span 12" }}><Used on="Leaders (rankings), My team, Matches" /></div>

        <Part title="The squad" sub="Everyone who played this season: Broadcast's TV table with the last five innings." />
        <Tile span={12} title={`Every player · ${team} · ${d.section} ${d.season}`}>
          {d.squad?.length ? <><SquadTable rows={d.squad} mark={mineBat[0]?.player} />
            <div className="note">Form: ▲ scoring more in the last five than before, ▼ less, ▬ about the same. Highlighted: the top run-scorer.</div></>
            : <Missing why={miss.squad} />}
        </Tile>

        <Part title="Colours, fonts and logos" sub="Your national side's colours on every page; Bebas Neue for names, Space Grotesk for numbers, Inter for words." />
        <Tile span={6} title="Colours">
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>{([["Page", t.page], ["Rail", t.rail], ["Tile", t.tile], ["Edge", t.edge],
            ["Words", t.ink], ["Quiet words", t.dim], ["Numbers", t.led], ["Won", t.win], ["Lost", t.loss], ["Everyone else", t.other],
            ["Line on a tile (left)", t.line[0]], ["Line on a tile (right)", t.line[1]]] as [string, string][]).map(([k, v]) => (
            <div className="swatch" key={k}><i style={{ background: v }} /><span><b>{k}</b> {v}</span></div>))}</div>
          <div className="field"><label htmlFor="nation">Preview a side's colours</label>
            <select id="nation" className="pick" value={nation} onChange={(e) => go(`/style-guide${e.target.value ? `?nation=${encodeURIComponent(e.target.value)}` : ""}`)}>
              <option value="">Your colours</option><option value="none">No national side (night)</option>
              {nations.data?.nations.map((n) => <option key={n} value={n}>{n}</option>)}</select></div>
        </Tile>
        <Tile span={6} title="Fonts">
          <Name p={`${team} · ${st?.player ?? "Player names"}`} px={46} />
          <div className="note">Bebas Neue: player and team names, titles</div>
          <div style={{ marginTop: 14 }}><Num v="1,234 · 56.78 · 7/21" px={46} /></div>
          <div className="note">Space Grotesk: every number</div>
          <div className="deck" style={{ marginTop: 14 }}>Inter: everything you read, like this sentence.</div>
        </Tile>
        <Tile span={12} title="Logos · from your Cricket Captain files, in the look you chose for each">
          <div className="row2" style={{ flexWrap: "wrap", gap: 28, alignItems: "flex-end" }}>
            {[team, ...new Set((d.results ?? []).map((r) => r.opp))].slice(0, 6).map((x) => (
              <div key={x} style={{ textAlign: "center" }}><div className="row2" style={{ gap: 10, alignItems: "flex-end" }}>
                <Logo team={x} size={96} /><Logo team={x} size={48} /><Logo team={x} size={28} /></div><Name p={ab(x)} px={20} /></div>))}
          </div>
          <div className="note">Big in headings, medium on scoreboards, small in tables and lists. A team with no picture shows none, never another's.</div>
        </Tile>
      </div>
    </>
  );
}
