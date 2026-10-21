// Shared helpers for the fresh-look mock-ups: real numbers from the career (window.D), formatting, small builders.
const TEAM = "India";
const Q = new URLSearchParams(location.search);
const PAGE = Q.get("page") || "home";
const f0 = v => (v == null || isNaN(v)) ? "–" : Math.round(v).toLocaleString("en-GB");
const f1 = v => (v == null || isNaN(v)) ? "–" : (+v).toFixed(1);
const f2 = v => (v == null || isNaN(v)) ? "–" : (+v).toFixed(2);
const pct = v => (v == null || isNaN(v)) ? "–" : Math.round(v) + "%";
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const day = d => { const [y, m, dd] = d.split("-"); return `${+dd} ${MONTHS[+m - 1]}`; };
const dayY = d => { const [y, m, dd] = d.split("-"); return `${+dd} ${MONTHS[+m - 1]} ${y}`; };
const ABBR = {"India": "IND", "West Indies": "WI", "England": "ENG", "Ireland": "IRE", "Afghanistan": "AFG",
  "Australia": "AUS", "New Zealand": "NZ", "Pakistan": "PAK", "South Africa": "SA", "Sri Lanka": "SL",
  "Bangladesh": "BAN", "Zimbabwe": "ZIM", "Netherlands": "NED", "Scotland": "SCO", "Nepal": "NEP", "UAE": "UAE"};
const ab = t => ABBR[t] || t.slice(0, 3).toUpperCase();
const logo = (t, dark = true) => (D.logos[t] ? D.logos[t][dark ? "dark" : "plain"] : "");
const img = (t, px, dark = true, cls = "lg") => logo(t, dark) ? `<img class="${cls}" src="${logo(t, dark)}" style="width:${px}px;height:${px}px" alt="">` : "";
const ord = n => n + (["th", "st", "nd", "rd"][(n % 100 - 20) % 10] || ["th", "st", "nd", "rd"][n % 100] || "th");
const FORMAT = {"T20Is": "T20I", "ODIs": "ODI", "Tests": "Test"};

// the season in numbers
const R = D.results;                       // newest first
const won = R.filter(r => r.outcome === "W").length, lost = R.filter(r => r.outcome === "L").length;
const banner = Object.fromEntries(D.banner.map(b => [b.section, b]));
function series() {                       // India's series, newest first: [{opp, section, games, w, l, month}]
  const out = [];
  for (const r of [...R].reverse()) {
    const last = out[out.length - 1];
    if (last && last.opp === r.opp && last.section === r.section && r.no && r.no > 1) { last.games.push(r); }
    else out.push({opp: r.opp, section: r.section, games: [r]});
  }
  out.forEach(s => { s.w = s.games.filter(g => g.outcome === "W").length; s.l = s.games.filter(g => g.outcome === "L").length;
    s.when = dayY(s.games[0].date).split(" ").slice(1).join(" "); s.of = s.games[0].of; });
  return out.reverse();
}
const SERIES = series();
const seriesText = s => s.w > s.l ? `won ${s.w}–${s.l}` : s.w < s.l ? `lost ${s.w}–${s.l}` : `drew ${s.w}–${s.l}`;
const STAR = D.star_runs.player, SP = D.profile;
const scoreOf = (card) => `${card.runs}${card.all_out ? "" : "/" + card.wickets}`;

// a wicket ladder from a scorecard's fall of wickets: partnerships per wicket
function stands(card) {
  let prev = 0; const out = [];
  card.fow.forEach(w => { out.push({wicket: w.wicket, runs: w.score - prev, end: w.score}); prev = w.score; });
  if (prev < card.runs) out.push({wicket: card.fow.length + 1, runs: card.runs - prev, end: card.runs, unbroken: true});
  return out;
}
function chart(el, option) { const c = echarts.init(document.getElementById(el), null, {renderer: "svg"}); c.setOption(option); return c; }
// Elo rank of every ODI team after each date (from the site's Elo), for race / bump charts
const ELO = D.elo_odis;
const howOut = x => x.out ? (x.dismissal || x.how_out) : "not out";
// how a side's wickets fell: {caught: 6, bowled: 2, ...}
function wicketKinds(card) { const k = {}; card.bat.filter(x => x.out).forEach(x => { k[x.how_out] = (k[x.how_out] || 0) + 1; }); return k; }
const cap = s => s.charAt(0).toUpperCase() + s.slice(1);
// a donut (pie with a hole): items [[name, value, colour]], a big number and a word in the middle
function donut(el, items, centre, sub, opt = {}) {
  const cf = opt.centreFont || "700 30px Inter", sf = opt.subFont || "600 12px Inter";
  const parse = f => { const m = f.match(/^(?:(\d+)\s+)?(\d+)px\s+(.+)$/); return {fontWeight: m[1] || 400, fontSize: +m[2], fontFamily: m[3]}; };
  return chart(el, {
    title: centre ? {text: centre, subtext: sub || "", left: "center", top: "center", itemGap: 2,
      textStyle: {color: opt.centreInk || opt.ink || "#fff", ...parse(cf)}, subtextStyle: {color: opt.subInk || "#a9b6d3", ...parse(sf)}} : undefined,
    series: [{type: "pie", radius: opt.radius || ["44%", "66%"], center: ["50%", "50%"], avoidLabelOverlap: true, padAngle: opt.pad ?? 2, labelLayout: {hideOverlap: false},
    itemStyle: {borderRadius: opt.round ?? 4, borderColor: opt.gap || "transparent", borderWidth: opt.gap ? 3 : 0},
    label: {show: opt.labels ?? true, overflow: "none", formatter: opt.fmt || "{b}\n{c}", color: opt.ink || "#fff", fontFamily: opt.font || "Inter", fontSize: opt.size || 13, lineHeight: 17},
    labelLine: {length: 8, length2: 8, lineStyle: {color: opt.lineCol || "#8899bb"}},
    data: items.map(([n, v, c]) => ({name: n, value: v, itemStyle: {color: c}}))}]});
}
