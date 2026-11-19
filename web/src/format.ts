// How numbers, dates and names are written on the site (as on the current site: en-GB, '–' for nothing).

/** Rounds the way the server does (Python: an exact half goes to the even whole number, so 62.5 is 62 and 63.5 is 64),
 *  so a number worked out on the page and the same number from the server always read the same. */
export const rnd = (v: number) => (v - Math.floor(v) === 0.5 ? (Math.floor(v) % 2 === 0 ? Math.floor(v) : Math.floor(v) + 1) : Math.round(v));
export const f0 = (v: number | null | undefined) => (v == null || Number.isNaN(v) ? "–" : rnd(v).toLocaleString("en-GB"));
/** `d` decimal places the way the server writes them (an exact half to the even last digit: 30.25 is 30.2, 30.35 is
 *  30.4), where the browser's own way would take every half up. */
export const fx = (v: number, d: number) => {
  const exact = Math.abs(v).toFixed(Math.min(100, d + 30));   // the number's own digits, far enough to see a tie
  const [whole, frac = ""] = exact.split(".");
  if (!/^50*$/.test(frac.slice(d))) { const t = (+v).toFixed(d); return Number(t) === 0 ? t.replace("-", "") : t; }
  const cut = d ? `${whole}.${frac.slice(0, d)}` : whole!;
  const odd = Number(cut.slice(-1)) % 2 === 1;
  const out = odd ? (Number(cut) + 10 ** -d).toFixed(d) : cut;
  return (v < 0 && Number(out) !== 0 ? "-" : "") + out;
};
export const f1 = (v: number | null | undefined) => (v == null || Number.isNaN(v) ? "–" : fx(+v, 1));
export const f2 = (v: number | null | undefined) => (v == null || Number.isNaN(v) ? "–" : fx(+v, 2));
export const pct = (v: number | null | undefined) => (v == null || Number.isNaN(v) ? "–" : `${rnd(v)}%`);

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
  // every competition in the game, shortened so it still reads (your request of 14 November: "COCD1" said nothing)
  "County Championship": "County", "One-Day Cup": "One-Day Cup", "T20 Blast": "Blast", "The Hundred": "Hundred",
  "Sheffield Shield": "Shield", "Marsh One-Day Cup": "Marsh Cup", "Big Bash League": "Big Bash",
  "Ranji Trophy": "Ranji", "Vijay Hazare Trophy": "Vijay Hazare", "Syed Mushtaq Ali Trophy": "Mushtaq Ali",
  "Indian Premier League": "IPL", "Plunket Shield": "Plunket", "Ford Trophy": "Ford Trophy", "Super Smash": "Super Smash",
  "CSA 4-Day Series": "CSA 4-Day", "CSA One-Day Cup": "CSA One-Day", "CSA T20 Challenge": "CSA T20",
  "CSA T20 Knock-Out": "CSA T20 KO", "SA20": "SA20", "West Indies Championship": "WI 4-Day", "Super50 Cup": "Super50",
  "Caribbean Premier League": "CPL", "Quaid-e-Azam Trophy": "Quaid-e-Azam", "President's Trophy": "President's",
  "Pakistan Cup": "Pakistan Cup", "National T20 Cup": "National T20", "Pakistan Super League": "PSL",
  "National Cricket League": "NCL", "Dhaka Premier Division Cricket League": "Dhaka Premier", "NCL T20": "NCL T20",
  "Bangladesh Premier League": "BPL", "Ahmad Shah Abdali First Class Tournament": "Ahmad Shah Abdali",
  "Ghazi Amanullah Khan Regional One Day To": "Ghazi Amanullah",   // (the game cuts names at 40 letters) "Shpageeza Cricket League": "Shpageeza",
  "Inter-Provincial Championship": "Inter-Pro 4-Day", "Inter-Provincial Cup": "Inter-Pro Cup",
  "Inter-Provincial Trophy": "Inter-Pro T20", "Major League Tournament": "Major League",
  "Major Clubs Limited Over Tournament": "Major Clubs 50", "Major Clubs T20 Tournament": "Major Clubs T20",
  "Lanka Premier League": "LPL", "Logan Cup": "Logan Cup", "Pro50 Championship": "Pro50",
  "Domestic T20 Competition": "Domestic T20", "First-class": "FC", "Tour matches": "Tour",
};
/** the format word for a section ('ODIs' -> 'ODI'), or a competition's short name that still reads
 *  ('County Championship · Division 1' -> 'County D1', 'CSA One-Day Cup · Division 1' -> 'CSA One-Day D1',
 *  'Pakistan Super League' -> 'PSL'); a name the game may have that isn't listed keeps its full name. */
export const fmtOf = (section: string): string => {
  if (FORMAT[section]) return FORMAT[section];
  if (SHORT[section]) return SHORT[section];
  const div = /^(.*) · Division (\d)$/.exec(section);
  if (div) return `${fmtOf(div[1]!)} D${div[2]}`;
  const part = /^(.*) · (.*)$/.exec(section);   // 'Tour matches · First-class' -> 'Tour FC'
  if (part && SHORT[part[1]!]) return `${SHORT[part[1]!]} ${SHORT[part[2]!] ?? part[2]}`;
  return section;
};

/** What every page says on a career with no matches yet (the same words the server uses, server/styleguide.py). */
export const NO_MATCHES = "No matches in this career yet. Play a match in Cricket Captain (with Autosave scorecards on in Options) and this page fills in within about 20 seconds.";

/** One name per stat (your pick of 14 November): every table heading uses the short name here, and the big number
 *  tiles and charts the full words; hovering a short heading anywhere on the site shows what it means. Where batting
 *  and bowling use the same short name for two figures, both meanings are given. tests/test_web.py checks every page's
 *  headings against this list. */
export const STAT_WORDS: Record<string, string> = {
  Mat: "Matches played", Inns: "Innings", NO: "Not outs", Runs: "Runs", HS: "Highest score (* = not out)",
  Avg: "Average: batting, runs per time out; bowling, runs per wicket", BF: "Balls faced",
  SR: "Strike rate: batting, runs per 100 balls; bowling, balls per wicket", "100": "Hundreds", "50": "Fifties (50-99)",
  "0": "Ducks (out for nought)", "4s": "Fours", "6s": "Sixes", Overs: "Overs (six balls; The Hundred's balls are turned into overs)",
  Mdns: "Maidens (printed on longer-format cards)", Dots: "Dot balls (printed on T20 and Hundred cards)",
  Wkts: "Wickets", BBI: "Best bowling in an innings", BBM: "Best bowling in a match", Econ: "Economy: runs per over",
  "4w": "Four wickets in an innings", "4w+": "Four or more wickets in an innings", "5w": "Five or more wickets in an innings",
  "10m": "Ten or more wickets in a match", P: "Played", W: "Won", L: "Lost", D: "Drawn", T: "Tied", NRR: "Net run rate",
  Pts: "Points", "Win %": "Wins out of games played", "Avg score": "Runs per innings (a team's total)", "Runs/wkt": "Runs scored per wicket lost",
  "Conceded/wkt": "Runs conceded per wicket taken", "Run rate": "Runs scored per over",
};
