// The Season page's calendar: a month as a grid of days, each day its games (a result opening its scorecard, a game
// still to come dashed, or for every team a count), and the month's notes; twelve small ones make a season, one big
// one a month.
import { Link } from "react-router";
import type { CalMonth } from "../api";

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export function MonthGrid({ mo, big, keep, today }: { mo: CalMonth; big?: boolean; keep: string; today?: string }) {
  return (
    <div className={`cm${big ? " big" : ""}${mo.played ? "" : " quiet"}`}>
      <div className="cm-h"><b>{mo.name} {mo.year}</b>{mo.played > 0 && <span>{mo.won || mo.lost ? `${mo.won}–${mo.lost} · ` : ""}{mo.played} played</span>}</div>
      {mo.notes.length > 0 && <div className="cm-n">{mo.notes.map((n, i) => <div key={i} className={n.kind}>{n.text}</div>)}</div>}
      <div className="cm-g">{DAYS.map((d) => <span key={d} className="dn">{big ? d : d[0]}</span>)}
        {Array.from({ length: mo.first }, (_, k) => <span key={`e${k}`} />)}
        {Array.from({ length: mo.days_in }, (_, k) => {
          const d = k + 1, chips = mo.days[String(d)] ?? [];
          const iso = `${mo.key}-${String(d).padStart(2, "0")}`;
          return (
            <div key={d} className={`cd${iso === today ? " today" : ""}`}>
              <span className="dd">{d}</span>
              {chips.map((c, i) => {
                const text = big ? (c.long ?? c.text) : c.text;
                const inner = <span className={`chip ${c.kind}`} title={c.tip}>{text}</span>;
                if (big && c.games) return <div key={i} className="cd-games">{c.games.map((g) => (
                  <Link key={g.id} to={`/matches/${g.id}${keep}`} className="chip N" title={g.result}>{g.text}</Link>))}</div>;
                return c.id ? <Link key={i} to={`/matches/${c.id}${keep}`} className="cl">{inner}</Link> : <span key={i}>{inner}</span>;
              })}
            </div>);
        })}</div>
    </div>
  );
}
