// The frame of every page: the rail with the nine sections, the live news of new matches, the search box (Ctrl K),
// and your team's colours.
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { Link, NavLink, useLocation, useSearchParams } from "react-router";
import { ApiError, get, type CareerInfo, type InboxPage, type Live, type ProblemsPage, type Theme } from "../api";
import { ab, dayY, STAT_WORDS } from "../format";
import { refit } from "../fit";
import { explainTables } from "../howto";
import { ThemeProvider } from "../theme";
import { Broken } from "./Broken";
import { Finder } from "./Finder";
import { NamesProvider } from "./names";
import { PlayerMenu } from "./PlayerMenu";

const I = (d: ReactNode) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">{d}</svg>;
export const SECTIONS: { to: string; label: string; icon: ReactNode }[] = [
  { to: "/", label: "My team", icon: I(<path d="M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z" />) },
  { to: "/inbox", label: "Inbox", icon: I(<><path d="M3 13l3-8h12l3 8v6a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z" /><path d="M3 13h5l1.5 3h5L16 13h5" /></>) },
  { to: "/players", label: "Players", icon: I(<><circle cx="12" cy="8" r="4" /><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6" /></>) },
  { to: "/matches", label: "Matches", icon: I(<><rect x="3" y="5" width="18" height="14" rx="3" /><path d="M12 5v14M3 12h18" /></>) },
  { to: "/teams", label: "Teams", icon: I(<><circle cx="9" cy="8" r="3.5" /><circle cx="17" cy="9" r="2.5" /><path d="M2 20c1-3.5 3.8-5.5 7-5.5s6 2 7 5.5M15 14.6c2.6-.3 5 1.2 6 4.4" /></>) },
  { to: "/seasons", label: "Seasons", icon: I(<path d="M4 19V9M10 19V5M16 19v-7M22 19H2" />) },
  { to: "/fixtures", label: "Fixtures", icon: I(<><rect x="3" y="5" width="18" height="16" rx="2" /><path d="M3 10h18M8 3v4M16 3v4" /></>) },
  { to: "/leaders", label: "Leaders", icon: I(<path d="M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0zM17 6h3a3 3 0 0 1-3 4M7 6H4a3 3 0 0 0 3 4" />) },
  { to: "/insights", label: "Insights", icon: I(<path d="M3 17l6-6 4 4 8-8M21 7v5M21 7h-5" />) },
  { to: "/settings", label: "Settings", icon: I(<><circle cx="12" cy="12" r="3.2" /><circle cx="12" cy="12" r="7" /><path d="M12 2.5v2.5M12 19v2.5M2.5 12H5M19 12h2.5M5.3 5.3l1.8 1.8M16.9 16.9l1.8 1.8M5.3 18.7l1.8-1.8M16.9 7.1l1.8-1.8" /></>) },
];

type Shared = { career: CareerInfo | null; noCareer: boolean; openFinder: () => void; nation: string;
  logos: { teams: Set<string>; comps: Set<string> } };
const ShellContext = createContext<Shared>({ career: null, noCareer: false, openFinder: () => {}, nation: "",
  logos: { teams: new Set(), comps: new Set() } });
export const useShell = () => useContext(ShellContext);

type Toast = { id: number; kind: "new" | "rec" | "bad"; title: string; text: string };

/** The top of a page: title and where you are, choices, the date in your career, the search box. */
export function Head({ title, crumb, chips, on = 0, onChip }: {
  title: ReactNode; crumb: ReactNode; chips?: string[]; on?: number; onChip?: (i: number) => void;
}) {
  const { career, openFinder } = useShell();
  const team = career?.my_teams[0];
  return (
    <div className="head">
      <div><h1>{title}</h1><div className="crumb">{crumb}</div></div>
      {chips && chips.length > 0 && <div className={`chips${chips.length > 3 ? " many" : ""}`}>{chips.map((c, i) => onChip
        ? <button key={c} className={i === on ? "on" : ""} onClick={() => onChip(i)}>{c}</button>
        : <span key={c} className={i === on ? "on" : ""}>{c}</span>)}</div>}
      {career?.latest && <span className="clock" title="The date of the latest match in this career">{team ? `${ab(team)} · ` : ""}{dayY(career.latest).toUpperCase()}</span>}
      <button className="pill" onClick={openFinder} title="Search for a player, team, competition or match">🔍 Search anything <kbd>Ctrl K</kbd></button>
    </div>
  );
}

export function Shell({ children }: { children: ReactNode }) {
  const [params] = useSearchParams();
  const nation = params.get("nation") ?? "";
  const qc = useQueryClient();
  const loc = useLocation();
  const theme = useQuery({ queryKey: ["theme", nation], queryFn: () => get<Theme>(`/api/theme${nation ? `?nation=${encodeURIComponent(nation)}` : ""}`) });
  const career = useQuery({ queryKey: ["career"], queryFn: () => get<CareerInfo>("/api/career"), retry: (n, e) => !(e instanceof ApiError && e.status === 404) && n < 2 });
  const logos = useQuery({ queryKey: ["logos"], queryFn: () => get<{ teams: string[]; comps: string[] }>("/api/logos") });
  // the unread count on the Inbox in the rail (asked again when new matches arrive, like every page's numbers)
  const inbox = useQuery({ queryKey: ["inbox"], queryFn: () => get<InboxPage>("/api/inbox"), enabled: Boolean(career.data), retry: false });
  // the red count on Settings: problems the site noticed (asked again every half minute, and as soon as a page reports one)
  // getting every page ready (the speed work): a small bar in the menu while it's going, checked every 2 seconds then
  const ready = useQuery({ queryKey: ["warmup"], queryFn: () => get<{ done: number; total: number; busy: boolean }>("/api/warmup"),
    retry: false, refetchInterval: (q) => (q.state.data?.busy === false ? 30_000 : 2_000) });
  const problems = useQuery({ queryKey: ["problems"], queryFn: () => get<ProblemsPage>("/api/problems"), retry: false, refetchInterval: 30_000 });
  const [finder, setFinder] = useState(false);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [watch, setWatch] = useState<{ at: number; folders: number } | null>(null);

  // on every page: every table heading that's a short stat name shows its meaning on hover (one list: STAT_WORDS),
  // and every average, strike rate and economy in a table the sum behind it (howto.ts); done again after each change
  useEffect(() => {
    const name = () => {
      document.querySelectorAll<HTMLTableCellElement>("th:not([title])").forEach((th) => {
        const w = STAT_WORDS[(th.textContent ?? "").replace(/[▾▴]/g, "").trim()];
        if (w) th.title = w;
      });
      explainTables();
    };
    name();
    let queued = 0;
    const watch = new MutationObserver(() => { if (!queued) queued = requestAnimationFrame(() => { queued = 0; name(); }); });
    watch.observe(document.body, { childList: true, subtree: true, characterData: true });
    return () => { watch.disconnect(); cancelAnimationFrame(queued); };
  }, []);

  // Ctrl K (or /) opens the search box from anywhere
  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if ((e.key === "k" && (e.ctrlKey || e.metaKey)) || (e.key === "/" && !(e.target instanceof HTMLInputElement))) {
        e.preventDefault();
        setFinder(true);
      }
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, []);

  // the news of new matches: the folder is checked every 20 seconds by the server
  useEffect(() => {
    const es = new EventSource("/api/events");
    let n = 0;
    const toast = (kind: Toast["kind"], title: string, text: string) => {
      const id = ++n + Date.now();
      setToasts((ts) => [...ts.slice(-4), { id, kind, title, text }]);
      window.setTimeout(() => setToasts((ts) => ts.filter((x) => x.id !== id)), 10000);
    };
    es.onmessage = (m) => {
      const e = JSON.parse(m.data) as Live;
      if (e.type === "checked") setWatch({ at: e.at, folders: e.folders });
      else if (e.type === "matches") {
        toast("new", "New matches", `${e.added} new match${e.added > 1 ? "es" : ""} added to ${e.career}`);
        e.records.forEach((r) => toast("rec", "New record!", r));
        void qc.invalidateQueries();
      } else if (e.type === "failed") {
        toast("bad", "Couldn't read", `${e.files.length} file${e.files.length > 1 ? "s" : ""} couldn't be read: ${e.files.map((f) => f.file).join(", ")}`);
      }
    };
    return () => es.close();
  }, [qc]);

  // nothing may spill out of its tile: fitted again when the window changes size
  useEffect(() => {
    let timer = 0;
    const again = () => { window.clearTimeout(timer); timer = window.setTimeout(() => refit(), 150); };
    window.addEventListener("resize", again);
    return () => window.removeEventListener("resize", again);
  }, []);

  if (!theme.data || !logos.data) return theme.error ? <div className="main"><div className="empty">The stats server isn't answering: {String(theme.error)}</div></div> : null;
  const keep = nation ? `?nation=${encodeURIComponent(nation)}` : "";
  const shared: Shared = { career: career.data ?? null, noCareer: career.error instanceof ApiError && career.error.status === 404,
    openFinder: () => setFinder(true), nation, logos: { teams: new Set(logos.data.teams), comps: new Set(logos.data.comps) } };
  return (
    <ThemeProvider theme={theme.data}>
      <ShellContext.Provider value={shared}><NamesProvider on={Boolean(career.data)}>
        <nav className="rail"><div className="rail-in">
          <Link className="mark" to={`/${keep}`} title="Stats Pack">SP</Link>
          {SECTIONS.map((s) => (
            <NavLink key={s.to} to={`${s.to}${keep}`} end={s.to === "/"}
              className={({ isActive }) => `nav ${isActive || (s.to === "/settings" && loc.pathname === "/style-guide") ? "on" : ""}`}>
              {s.icon}{s.label}{s.to === "/inbox" && (inbox.data?.unread ?? 0) > 0 && <b className="badge">{inbox.data!.unread > 99 ? "99+" : inbox.data!.unread}</b>}
              {s.to === "/settings" && (problems.data?.count ?? 0) > 0 && <b className="badge bad" title="Problems the site noticed: see Settings → Problems">{problems.data!.count > 99 ? "99+" : problems.data!.count}</b>}</NavLink>))}
          {ready.data?.busy && ready.data.total > 0 && <div className="ready" title="Getting every page ready, your team and players first: the site can be used meanwhile, and a page not ready yet works itself out when you open it">
            Getting ready<span className="bar"><i style={{ width: `${Math.round((ready.data.done / ready.data.total) * 100)}%` }} /></span>
            {Math.round((ready.data.done / ready.data.total) * 100)}%</div>}
          {watch && watch.folders > 0 && <div className="watch" title={`Watching ${watch.folders} Scorecards folder${watch.folders > 1 ? "s" : ""}; new matches are added by themselves`}>
            <i />Watching<br />{new Date(watch.at * 1000).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}</div>}
        </div></nav>
        <main className="main"><Broken at={loc.pathname + loc.search}>{children}</Broken></main>
        {finder && <Finder close={() => setFinder(false)} keep={keep} />}
        <PlayerMenu keep={keep} />
        {toasts.length > 0 && <div className="toasts">{toasts.map((x) => (
          <div key={x.id} className={`toast ${x.kind}`}><div><b>{x.title}</b>{x.text}</div>
            <button onClick={() => setToasts((ts) => ts.filter((y) => y.id !== x.id))} aria-label="Close">✕</button></div>))}</div>}
      </NamesProvider></ShellContext.Provider>
    </ThemeProvider>
  );
}
