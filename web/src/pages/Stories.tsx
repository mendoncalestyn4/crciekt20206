// Player stories (stage 3): the current site's 15 tabs in the same order (your answer 3), one competition and season at
// a time; Batter v bowler adds competitions up with the tick boxes (answer 32). Every number comes from the server
// (server/storiespage.py); the page only shows it.
import { useQuery } from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router";
import { get, type NGrid, type StoriesPage, remember } from "../api";
import { Drop, Explain, Missing, Num, Pick, Tile, three } from "../kit/base";
import { Grid, SignedBars } from "../kit/teams";
import { T } from "../shell/names";
import { useReady } from "../ready";
import { Head, useShell } from "../shell/Shell";
import { useTheme } from "../theme";

export const PLAYER_PAGES = [{ label: "Find a player", to: "/players" }, { label: "Player stories", to: "/players/stories" },
  { label: "Compare players", to: "/players/compare" }];

/** The Players section's heading, with a chip for each of its pages. */
export function PlayersHead({ on, crumb }: { on: number; crumb: string }) {
  const go = useNavigate();
  const { nation } = useShell();
  const keep = nation ? `?nation=${encodeURIComponent(nation)}` : "";
  return <Head title="Players" crumb={crumb} chips={PLAYER_PAGES.map((p) => p.label)} on={on} onChip={(i) => go(`${PLAYER_PAGES[i]!.to}${keep}`)} />;
}

function Noted({ t }: { t: NGrid }) {
  return <><Grid t={t} />{t.note && <div className="note">{t.note}</div>}</>;
}

const KEYS = ["tab", "section", "season", "batter", "bowler"];

export function Stories() {
  const { career, noCareer, nation } = useShell();
  const t = useTheme();
  const [params] = useSearchParams();
  const go = useNavigate();
  const want = Object.fromEntries(KEYS.map((k) => [k, params.get(k) ?? ""]));
  const qs = KEYS.filter((k) => want[k]).map((k) => `${k}=${encodeURIComponent(want[k]!)}`).join("&");
  const q = useQuery({ queryKey: ["stories", qs, career?.name], enabled: Boolean(career), retry: false,
    queryFn: () => get<StoriesPage>(`/api/stories?${qs}`), placeholderData: (was) => was });
  useReady(Boolean(q.data || q.error || noCareer), qs);
  const set = (changes: Record<string, string>) => {
    if (changes.section) remember({ section: changes.section });
    if (changes.season) remember({ season: changes.season });
    const next: Record<string, string> = { ...want, ...changes };
    if ("section" in changes) Object.assign(next, { season: "" });
    if (nation) next.nation = nation;
    go(`/players/stories?${new URLSearchParams(Object.entries(next).filter(([, v]) => v)).toString()}`);
  };
  const head = <PlayersHead on={1} crumb="Player stories · the stories behind the numbers" />;
  if (noCareer) return <>{head}<div className="grid"><Tile span={12} title="No career yet"><div className="plain">Add a career in Settings first.</div></Tile></div></>;
  if (q.error) return <>{head}<div className="grid"><Tile span={12}><Missing why={String(q.error)} /></Tile></div></>;
  if (!q.data) return <>{head}<div className="empty">Finding the stories…</div></>;
  const d = q.data;
  if (!d.choices.length) return <>{head}<div className="grid"><Tile span={12}><Missing why={d.none} /></Tile></div></>;
  const tab = d.tab, T_ = d.tabs;
  const comps = d.choices.map((c) => c.section);
  const note = (x: string) => `${d.choices.find((c) => c.section === x)?.matches ?? ""} matches`;
  const none = (why?: string) => <div className="plain">{why ?? "Nothing yet."}</div>;
  const bvb = tab === T_[13];
  return (
    <>
      {head}
      <div className="grid">
        <div className="intro">Who's in form, who's closing in on a milestone or a record, who wins games, who stands up when the team loses, and the
          odd ones: nervous nineties, pairs and not-outs.</div>
        <div className="itabs">{T_.map((x, i) => (
          <button key={x} className={x === tab ? "on" : ""} onClick={() => set({ tab: i === 0 ? "" : x })}>{x}</button>))}</div>
        <Tile span={12} className="pickbar"><div className="drops">
          {bvb ? <Drop label="Competition" all={comps} on={d.ticked ?? []} set={(v) => set({ section: v.join("|") })} keepOne note={note} />
            : <Pick label="Competition" value={d.ticked?.[0] ?? ""} options={comps.map((c) => ({ v: c, label: c, note: note(c) }))} set={(v) => set({ section: v })} />}
          <Pick label="Season" value={d.season ?? ""} options={[{ v: "", label: "All seasons" }, ...(d.seasons ?? [])]} set={(v) => set({ season: v })} />
          {bvb && d.batters && <Pick label="Batter" value={d.batter ?? ""} options={[{ v: "", label: "Pick a batter" }, ...d.batters]} set={(v) => set({ batter: v })} />}
          {bvb && d.bowlers && <Pick label="Bowler" value={d.bowler ?? ""} options={[{ v: "", label: "Pick a bowler" }, ...d.bowlers]} set={(v) => set({ bowler: v })} />}
        </div>
        {bvb && <div className="note">Tick several competitions to add their meetings up (Tests and ODIs, say); each league stays on its own unless ticked.</div>}</Tile>

        {tab === T_[0] && <>
          <Tile span={12} title="Batters" right="last 5 innings (oldest first), against their own average">{d.bat ? <Grid t={d.bat} /> : none(d.bat_none)}</Tile>
          <Tile span={12} title="Bowlers" right="last 5 innings, wickets per innings against their own">{d.bowl ? <Grid t={d.bowl} /> : none(d.bowl_none)}</Tile>
          {d.note && <div className="note" style={{ gridColumn: "span 12" }}>{d.note}</div>}
        </>}

        {tab === T_[1] && <>
          <Tile span={6} title="Milestone watch" right="all seasons">{d.miles ? <Grid t={d.miles} /> : none(d.miles_none)}</Tile>
          <Tile span={6} title="Record watch" right="could fall">{d.records ? <Noted t={d.records} /> : none(d.records_none)}</Tile>
        </>}

        {tab === T_[2] && d.parts?.map((p) => <Tile key={p.title} span={12} title={p.title} right="their team's win % in those games and in the rest">
          {p.table ? <Grid t={p.table} /> : none(p.none)}</Tile>)}

        {tab === T_[3] && <>
          <Tile span={12} title="Best innings in a losing side">{d.bat ? <Grid t={d.bat} /> : none()}</Tile>
          <Tile span={12} title="Best bowling in a losing side">{d.bowl ? <Grid t={d.bowl} /> : none()}</Tile>
        </>}

        {tab === T_[4] && <>
          <Tile span={6} title="One-man shows" right="in one innings">{d.one ? <Grid t={d.one} /> : none()}</Tile>
          <Tile span={6} title="Who carries their team" right="5+ innings">
            {d.share ? <><SignedBars rows={d.share.rows} colour={t.blue} /><Explain {...three(d.share)} /></> : none(d.share_none)}</Tile>
        </>}

        {tab === T_[5] && <>
          <Tile span={4} title="Nervous nineties" right="out for 90-99">{d.nineties ? <Grid t={d.nineties} /> : none("Nobody yet.")}</Tile>
          <Tile span={4} title="Pairs" right="0 twice in a match">{d.pairs ? <Grid t={d.pairs} /> : none("Nobody yet (only possible in two-innings matches).")}</Tile>
          <Tile span={4} title="Not out" right="most unbeaten">{d.not_outs ? <Grid t={d.not_outs} /> : none("Nobody yet.")}</Tile>
        </>}

        {tab === T_[6] && <Tile span={12} title="The innings after a hundred" right="do they kick on or come back down?">{d.after ? <Grid t={d.after} /> : none(d.after_none)}</Tile>}

        {tab === T_[7] && <>
          <Tile span={12} title="Batting partners" right="stands together (2+)">{d.bat ? <Noted t={d.bat} /> : none("No pairs yet.")}</Tile>
          <Tile span={12} title="Bowling partners" right="both bowled in the same innings (3+)">{d.bowl ? <Grid t={d.bowl} /> : none("No pairs yet.")}</Tile>
          <Tile span={12} title="Partnership chemistry" right="named pairs (3+ stands) against the average stand for the same wickets">{d.chem ? <Noted t={d.chem} /> : none(d.chem_none)}</Tile>
          <Tile span={12} title="Strike-rate pressure" right="how fast their partners score with them (top-7 batters)">{d.pressure ? <Noted t={d.pressure} /> : none(d.pressure_none)}</Tile>
        </>}

        {tab === T_[8] && <Tile span={12} title="Player of the Series" right="most impact over each bilateral series">{d.series ? <Noted t={d.series} /> : none(d.series_none)}</Tile>}

        {tab === T_[9] && <Tile span={12} title={`Biggest upsets in ${d.sec}`} right="wins the ratings gave the least chance (all seasons)">{d.upsets ? <Noted t={d.upsets} /> : none(d.upsets_none)}</Tile>}

        {tab === T_[10] && <>
          {d.fast_note && <div className="note" style={{ gridColumn: "span 12" }}>{d.fast_note}</div>}
          {d.fast ? d.fast.map((g) => <Tile key={g.title} span={6} title={g.title} right={g.right}><Grid t={g.table} /></Tile>) : <Tile span={12}>{none(d.fast_none)}</Tile>}
        </>}

        {tab === T_[11] && (d.top ? <>
          <Tile span={12} title="Biggest single-match impact"><Grid t={d.top} /></Tile>
          {d.per && <Tile span={12} title="Most impact per match" right="regulars only"><SignedBars rows={d.per.rows} colour={t.blue} /><Explain {...three(d.per)} /></Tile>}</>
          : <Tile span={12}>{none(d.impact_none)}</Tile>)}

        {tab === T_[12] && <>
          <Tile span={7} title={`Badges earned in ${d.sec}`} right="newest first">{d.badges ? <Grid t={d.badges} /> : none(d.badges_none)}</Tile>
          <Tile span={5} title="How common each badge is here">{d.common && <Grid t={d.common} />}
            <div className="note">{d.badge_note}</div>
            {d.team_badges?.map((x) => <div key={x} className="plain" style={{ marginTop: 8 }}><T>{x}</T></div>)}</Tile>
        </>}

        {bvb && <Tile span={12} title={d.batter && d.bowler ? `${d.batter} v ${d.bowler}` : d.one_title ?? "Batter v bowler"} right={d.where}>
          {d.pick && none(d.pick)}
          {d.one_none && none(d.one_none)}
          {d.one && <><div className="plain" style={{ marginBottom: 8 }}>Most dismissals first; pick one above for every innings between them.</div><Grid t={d.one} /></>}
          {d.both_none && none(d.both_none)}
          {d.kpis && <div className="kpis">{d.kpis.map((k) => <div key={k.k}><span>{k.k}</span><Num v={k.v} px={40} how={k.how || undefined} /></div>)}</div>}
          {d.verdict && <div className="verdict2" style={{ marginTop: 10 }}>{d.verdict}</div>}
          {d.meetings && <Noted t={d.meetings} />}
        </Tile>}

        {tab === T_[15] && <>
          {d.breakers_note && <div className="note" style={{ gridColumn: "span 12" }}>{d.breakers_note}</div>}
          <Tile span={12} title="Partnership breakers" right="bowlers who ended the most stands of 50 and more">
            {d.breakers ? <><Grid t={d.breakers} /><Explain {...three(d)} /></> : none(d.breakers_none)}</Tile>
          {d.biggest && <Tile span={12} title="The biggest stands broken" right="and who broke them"><Grid t={d.biggest} /></Tile>}
        </>}

        {tab === T_[14] && <>
          {d.clutch_note && <div className="note" style={{ gridColumn: "span 12" }}>{d.clutch_note}</div>}
          <Tile span={12} title="Batters in big games" right="average then against average otherwise (top-7 batters)">{d.bat ? <Grid t={d.bat} /> : none(d.bat_none)}</Tile>
          <Tile span={12} title="Bowlers in big games" right="wickets per innings then against otherwise">{d.bowl ? <Grid t={d.bowl} /> : none(d.bowl_none)}</Tile>
        </>}
      </div>
    </>
  );
}
