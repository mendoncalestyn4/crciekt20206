// "How it's worked out" on every average, strike rate and economy in every table (your pick of 14 November): hover the
// figure for the sum behind it ("845 runs ÷ 21 times out = 40.24"), with the few-games note when it rests on fewer
// than FEW innings. The numbers come from the figure's own row (its Runs, Inns, NO, BF, Overs, Wkts) or, where the row
// doesn't show them, from the parts the site sends with the row (`data-parts`, api.ts Parts). One place does it for
// every table on every page, so a table added later gets it too; a figure that already explains itself (the Player
// page's own tables) is left alone.
import type { Parts } from "./api";
import { howOf } from "./kit/base";

const num = (s: string | undefined): number | undefined => {
  if (s == null) return undefined;
  const t = s.replace(/,/g, "").replace(/\*$/, "").trim();
  return /^-?\d+(\.\d+)?$/.test(t) ? Number(t) : undefined;
};
// "12.3" overs is 12 overs and 3 balls
const ballsOf = (overs: string | undefined): number | undefined => {
  const m = /^(\d+)(?:\.(\d))?$/.exec((overs ?? "").trim());
  return m ? Number(m[1]) * 6 + Number(m[2] ?? 0) : undefined;
};
const n = (x: number) => x.toLocaleString("en-GB");

/** The sum behind one figure (`stat` "Avg", "SR" or "Econ", batting or bowling), or "" when the numbers it's made
 *  from aren't known. */
export function sumFor(stat: string, v: string, p: Parts, bowling: boolean): string {
  if (!bowling) {
    if (stat === "Avg" && p.runs != null && p.outs) return `${n(p.runs)} runs ÷ ${n(p.outs)} ${p.what === "stands" ? "broken stands" : "times out"} = ${v}`;
    if (stat === "SR" && p.runs != null && p.bf) return `${n(p.runs)} runs ÷ ${n(p.bf)} balls × 100 = ${v}`;
    return "";
  }
  if (stat === "Avg" && p.bruns != null && p.wkts) return `${n(p.bruns)} runs ÷ ${n(p.wkts)} wickets = ${v}`;
  if (stat === "Econ" && p.bruns != null && p.bballs) return `${n(p.bruns)} runs ÷ ${n(p.bballs)} balls × 6 = ${v} an over`;
  if (stat === "SR" && p.bballs && p.wkts) return `${n(p.bballs)} balls ÷ ${n(p.wkts)} wickets = ${v}`;
  return "";
}

/** Give every average, strike rate and economy in every table its sum on hover (run again whenever the page
 *  changes: a sum this wrote is written afresh, so it always matches the figures on screen). */
export function explainTables(root: ParentNode = document): void {
  for (const t of root.querySelectorAll<HTMLTableElement>("main table")) {
    const head = [...t.querySelectorAll("thead th")].map((h) => (h.textContent ?? "").replace(/[▾▴]/g, "").trim());
    if (!head.some((h) => h === "Avg" || h === "SR" || h === "Econ")) continue;
    // a bowling table (wickets and overs or balls: "Wkts" and "Overs", or a scorecard's "W" with "O" or "B"), or the
    // columns after "Wkts" in a table of both; a scorecard's batting says "R" and "B" for runs and balls
    const card = head.includes("R");
    const bowlingTable = (head.includes("Wkts") && head.includes("Overs")) || (card && head.includes("W") && (head.includes("O") || head.includes("B")));
    const wk = head.indexOf("Wkts");
    for (const r of t.querySelectorAll<HTMLTableRowElement>("tbody tr")) {
      const cells = [...r.querySelectorAll<HTMLTableCellElement>(":scope > td")];
      if (cells.length !== head.length) continue;
      const at = (h: string) => { const i = head.indexOf(h); return i >= 0 ? (cells[i]!.textContent ?? "").trim() : undefined; };
      const inns = num(at("Inns")), no = num(at("NO"));
      const seen: Parts = bowlingTable
        ? { bruns: num(at(card ? "R" : "Runs")), bballs: head.includes("B") && card ? num(at("B")) : ballsOf(at(card ? "O" : "Overs")),
            wkts: num(at(card ? "W" : "Wkts")), binns: inns }
        : { runs: num(at(card ? "R" : "Runs")), outs: inns != null && no != null ? inns - no : undefined, bf: num(at(card ? "B" : "BF")),
            inns, wkts: num(at("Wkts")) };
      let sent: Parts = {};
      try { sent = r.dataset.parts ? JSON.parse(r.dataset.parts) as Parts : {}; } catch { sent = {}; }
      const p: Parts = { ...seen, ...Object.fromEntries(Object.entries(sent).filter(([, x]) => x != null)) };
      head.forEach((h, i) => {
        if (h !== "Avg" && h !== "SR" && h !== "Econ") return;
        const el = cells[i]!.querySelector<HTMLElement>(".tn, .nm") ?? cells[i]!;
        if (el.title && !el.dataset.how) return;                  // explains itself already
        const v = (cells[i]!.textContent ?? "").trim();
        // a bowling figure: in a bowling table, an economy, after the wickets column, or a row whose parts are bowling's
        const bowling = bowlingTable || h === "Econ" || (wk >= 0 && i > wk) || (p.runs == null && p.bruns != null);
        const sum = v === "–" ? "" : sumFor(h, v, p, bowling);
        if (sum) {
          const say = howOf(sum, bowling ? p.binns : p.inns);
          if (el.title !== say) el.title = say;
          el.dataset.how = "1";
          el.classList.add("how-tip");
        } else if (el.dataset.how) {
          el.removeAttribute("title");
          delete el.dataset.how;
          el.classList.remove("how-tip");
        }
      });
    }
  }
}
