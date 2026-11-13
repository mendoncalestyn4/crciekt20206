// How numbers, dates and names are written on the site (as on the current site: en-GB, '–' for nothing).

export const f0 = (v: number | null | undefined) => (v == null || Number.isNaN(v) ? "–" : Math.round(v).toLocaleString("en-GB"));
export const f1 = (v: number | null | undefined) => (v == null || Number.isNaN(v) ? "–" : (+v).toFixed(1));
export const f2 = (v: number | null | undefined) => (v == null || Number.isNaN(v) ? "–" : (+v).toFixed(2));
export const pct = (v: number | null | undefined) => (v == null || Number.isNaN(v) ? "–" : `${Math.round(v)}%`);

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
/** '12 Mar' */
export const day = (d: string) => { const [, m, dd] = d.split("-"); return `${+(dd ?? 0)} ${MONTHS[+(m ?? 1) - 1]}`; };
/** Dates on a chart's axis: '12 Mar', or "12 Mar '26" when the chart runs over more than one year. */
export const dayer = (dates: string[]) => {
  const years = new Set(dates.map((d) => d.slice(0, 4)));
  return years.size > 1 ? (d: string) => `${day(d)} ’${d.slice(2, 4)}` : day;
};
/** '12 Mar 2026' */
export const dayY = (d: string) => `${day(d)} ${d.slice(0, 4)}`;
/** 1st, 2nd, 3rd, 11th, 22nd */
export const ord = (n: number) => {
  const s = ["th", "st", "nd", "rd"], v = n % 100;
  return n + (s[(v - 20) % 10] ?? s[v] ?? "th");
};
/** balls as overs: 51 -> '8.3' */
export const overs = (b: number) => `${Math.floor(b / 6)}${b % 6 ? "." + (b % 6) : ""}`;
export const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
/** '1 hundred', '3 hundreds', '1 six', '2 sixes' */
export const plural = (n: number, one: string, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;
export const initials = (p: string) => p.split(" ").map((x) => x[0] ?? "").join("").slice(0, 2);

// short names: a country's usual three letters, a franchise's initials ('Chennai Super Kings' -> CSK)
const ABBR: Record<string, string> = {
  India: "IND", England: "ENG", Australia: "AUS", Pakistan: "PAK", Bangladesh: "BAN", Ireland: "IRE", Afghanistan: "AFG",
  Zimbabwe: "ZIM", Netherlands: "NED", Scotland: "SCO", Nepal: "NEP", "Sunrisers Hyderabad": "SRH", "Punjab Kings": "PBKS",
  "South Africa": "SA",
};
export const ab = (t: string) => {
  if (ABBR[t]) return ABBR[t];
  const words = t.split(/\s+/).filter((w) => /^[A-Za-z]/.test(w));
  return words.length > 1 ? words.map((w) => w[0]).join("").toUpperCase() : t.slice(0, 3).toUpperCase();
};
/** '245/6', or '180' when all out */
export const score = (runs: number, wickets: number, allOut: boolean, declared = false) =>
  `${runs}${allOut ? "" : "/" + wickets}${declared ? "d" : ""}`;
/** the format word for a section: 'ODIs' -> 'ODI' */
export const FORMAT: Record<string, string> = { T20Is: "T20I", ODIs: "ODI", Tests: "Test" };
// a competition's short name, for labels in a small space (the full name stays in titles)
const SHORT: Record<string, string> = {
  "Indian Premier League": "IPL", "Big Bash League": "BBL", "The Hundred": "Hundred", "T20 Blast": "Blast",
  "One-Day Cup": "ODC", "Marsh One-Day Cup": "Marsh", "Sheffield Shield": "Shield", "Ranji Trophy": "Ranji",
  "Vijay Hazare Trophy": "VHT", "Syed Mushtaq Ali Trophy": "SMAT", "Super Smash": "Smash", "Plunket Shield": "Plunket",
  "Ford Trophy": "Ford", "First-class": "FC",
};
/** the format word for a section ('ODIs' -> 'ODI'), or a competition's short name ('County Championship · Division 1'
 *  -> 'CC D1', 'Pakistan Super League' -> 'PSL') */
export const fmtOf = (section: string) => {
  if (FORMAT[section]) return FORMAT[section];
  if (SHORT[section]) return SHORT[section];
  const div = /^County Championship · Division (\d)$/.exec(section);
  if (div) return `CC D${div[1]}`;
  if (section.length <= 7) return section;
  const words = section.split(/\s+/).filter((w) => /^[A-Z0-9]/.test(w) && w !== "The");
  return words.length > 1 ? words.map((w) => w[0]).join("") : section;
};

/** What every page says on a career with no matches yet (the same words the server uses, server/styleguide.py). */
export const NO_MATCHES = "No matches in this career yet. Play a match in Cricket Captain (with Autosave scorecards on in Options) and this page fills in within about 20 seconds.";
