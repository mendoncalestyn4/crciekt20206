// Team leaders (stage 3, under Teams; agreed 13 November, your answer 13): each team's two biggest contributors to its
// runs and to its wickets, one competition and season at a time. Every number comes from the server
// (server/leaderteams.py); the page only shows it.
import { useQuery } from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router";
import { get, type TLRow, type TeamLeadersPage, remember } from "../api";
import { Drop, Logo, Missing, Pick, Tile } from "../kit/base";
import { T } from "../shell/names";
import { useReady } from "../ready";
import { Head, useShell } from "../shell/Shell";
import { TEAM_PAGES } from "./Teams";

const KEYS = ["section", "season", "teams"];

function Rows({ rows, unit }: { rows: TLRow[]; unit: string }) {
  return (
    <table className="c tl"><thead><tr><th className="r">#</th><th>Player</th><th className="r">Share</th><th className="r">{unit}</th><th className="r">Mat</th></tr></thead>
      <tbody>{rows.map((r, i) => (
        <tr key={r.player} className={r.gone ? "gone" : ""} title={r.gone ? "No game for the team here in its last two seasons" : undefined}>
          <td className="r"><span className="tn">{i + 1}</span></td><td><span className="why"><T>{r.player}</T></span></td>
          <td className="r"><span className="tn">{r.share}</span></td><td className="r"><span className="tn">{r.value.toLocaleString("en-GB")}</span></td>
          <td className="r"><span className="tn">{r.matches}</span></td></tr>))}</tbody></table>
  );
}

export function TeamLeaders() {
  const { career, noCareer, nation } = useShell();
  const [params] = useSearchParams();
  const go = useNavigate();
  const want = Object.fromEntries(KEYS.map((k) => [k, params.get(k) ?? ""]));
  const qs = KEYS.filter((k) => want[k]).map((k) => `${k}=${encodeURIComponent(want[k]!)}`).join("&");
  const q = useQuery({ queryKey: ["teamleaders", qs, career?.name], enabled: Boolean(career), retry: false,
    queryFn: () => get<TeamLeadersPage>(`/api/teamleaders?${qs}`), placeholderData: (was) => was });
  useReady(Boolean(q.data || q.error || noCareer), qs);
  const keep = nation ? `?nation=${encodeURIComponent(nation)}` : "";
  const set = (changes: Record<string, string>) => {
    if (changes.section) remember({ section: changes.section });
    if (changes.season) remember({ season: changes.season });
    const next: Record<string, string> = { ...want, ...changes };
    if ("section" in changes) {   // switching format keeps the ticked teams that play it (the server drops the rest)
      Object.assign(next, { season: "" });
    }
    if (nation) next.nation = nation;
    go(`/teams/leaders?${new URLSearchParams(Object.entries(next).filter(([, v]) => v)).toString()}`);
  };
  const head = <Head title="Teams" crumb="Team leaders · who makes the runs and takes the wickets" chips={TEAM_PAGES.map((p) => p.label)} on={5}
    onChip={(i) => go(`${TEAM_PAGES[i]!.to}${keep}`)} />;
  if (noCareer) return <>{head}<div className="grid"><Tile span={12} title="No career yet"><div className="plain">Add a career on the current site for now.</div></Tile></div></>;
  if (q.error) return <>{head}<div className="grid"><Tile span={12}><Missing why={String(q.error)} /></Tile></div></>;
  if (!q.data) return <>{head}<div className="empty">Finding each team's leaders…</div></>;
  const d = q.data;
  if (!d.choices.length) return <>{head}<div className="grid"><Tile span={12}><Missing why={d.none} /></Tile></div></>;
  const note = (x: string) => `${d.choices.find((c) => c.section === x)?.matches ?? ""} matches`;
  return (
    <>
      {head}
      <div className="grid">
        <div className="intro">Each team's two biggest contributors to its runs and to its wickets, just to see, not to compare.</div>
        <Tile span={12} className="pickbar"><div className="drops">
          <Pick label="Competition" value={d.section ?? ""} options={d.choices.map((c) => ({ v: c.section, label: c.section, note: note(c.section) }))} set={(v) => set({ section: v })} />
          <Pick label="Season" value={d.season ?? ""} options={[{ v: "", label: "All time" }, ...(d.seasons ?? [])]} set={(v) => set({ season: v })} />
          {d.teams && <Drop label="Teams" all={d.teams} on={d.picked ?? []} none="All teams" set={(v) => set({ teams: v.length ? v.join("|") : "all" })} />}
        </div><div className="note">{d.note}</div></Tile>
        {d.blocks?.map((b) => (
          <Tile key={b.team} span={6} title={<span className="tlname"><Logo team={b.team} size={26} /> {b.team}</span>} right={`${b.matches} match${b.matches === 1 ? "" : "es"}`} className={b.yours ? "mine" : ""}>
            <div className="two">
              <div><div className="glabel" style={{ marginTop: 0 }}>Runs</div>{b.runs.length ? <Rows rows={b.runs} unit="Runs" /> : <div className="plain">No runs yet.</div>}</div>
              <div><div className="glabel" style={{ marginTop: 0 }}>Wickets</div>{b.no_wickets ? <div className="plain">{b.no_wickets}</div> : <Rows rows={b.wickets} unit="Wkts" />}</div>
            </div>
          </Tile>))}
      </div>
    </>
  );
}
