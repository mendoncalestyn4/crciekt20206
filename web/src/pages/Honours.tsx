// Seasons · Honours (stage 2): every competition's winners season by season, with the top run-scorer and wicket-taker,
// and each team's trophy cabinet.
import { useQuery } from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router";
import { get, type HonoursPage } from "../api";
import { Missing, Tile } from "../kit/base";
import { Grid } from "../kit/teams";
import { useReady } from "../ready";
import { Head, useShell } from "../shell/Shell";
import { SEASON_PAGES } from "./Competitions";

export function Honours() {
  const { career, noCareer, nation } = useShell();
  const [params] = useSearchParams();
  const go = useNavigate();
  const keep = nation ? `?nation=${encodeURIComponent(nation)}` : "";
  const tab = params.get("tab") ?? "";
  const q = useQuery({ queryKey: ["honours", tab, career?.name], enabled: Boolean(career), retry: false,
    queryFn: () => get<HonoursPage>(`/api/honours?tab=${encodeURIComponent(tab)}`) });
  useReady(Boolean(q.data || q.error || noCareer), tab);
  const on = SEASON_PAGES.findIndex((p) => p.to === "/seasons/honours");
  const head = <Head title="Seasons" crumb="Honours · champions and trophy cabinets" chips={SEASON_PAGES.map((p) => p.label)} on={on}
    onChip={(i) => go(`${SEASON_PAGES[i]!.to}${keep}`)} />;
  if (noCareer) return <>{head}<div className="grid"><Tile span={12} title="No career yet"><div className="plain">Add a career in Settings first.</div></Tile></div></>;
  if (q.error) return <>{head}<div className="grid"><Tile span={12}><Missing why={String(q.error)} /></Tile></div></>;
  if (!q.data) return <>{head}<div className="empty">Polishing the trophies…</div></>;
  const d = q.data;
  const setTab = (i: number) => {
    const p = new URLSearchParams(); if (i) p.set("tab", d.tabs[i]!); if (nation) p.set("nation", nation);
    go(`/seasons/honours${p.toString() ? `?${p.toString()}` : ""}`);
  };
  return (
    <>
      {head}
      <div className="grid">
        {d.none ? <Tile span={12}><Missing why={d.none} /></Tile> : <>
          <div className="itabs">{d.tabs.map((x, i) => <button key={x} className={x === d.tab ? "on" : ""} onClick={() => setTab(i)}>{x}</button>)}</div>
          {d.boards?.map((b) => <Tile key={b.title} span={12} title={b.title}><Grid t={b} /></Tile>)}
          {d.note && <Tile span={12}><div className="note">{d.note}</div></Tile>}
          {d.tab === "Trophy cabinets" && <Tile span={12} title="Trophy cabinets">
            {d.cabinet ? <Grid t={d.cabinet} /> : <div className="plain">{d.cabinet_none ?? "No titles decided yet."}</div>}
            <div className="note">One row a team; a shared title counts for both sides.</div></Tile>}
        </>}
      </div>
    </>
  );
}
