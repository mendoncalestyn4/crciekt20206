// node player_art_mock.js <port> <art folder> <out folder>: the picked player art (design/player_art.md) laid on the
// real pages in the browser only (the site unchanged). The art folder holds the recoloured pictures: india.jpg and
// australia.jpg (made with the recipe in design/player_art.md); the photos are the owner's and never in the repo.
const { chromium } = require('playwright');
const fs = require('fs');
const [port, art, out] = process.argv.slice(2);
const uri = (f) => `data:image/jpeg;base64,${fs.readFileSync(`${art}/${f}`).toString('base64')}`;
const rgba = (hex, a) => `rgba(${parseInt(hex.slice(1, 3), 16)},${parseInt(hex.slice(3, 5), 16)},${parseInt(hex.slice(5, 7), 16)},${a})`;
// page, tile and menu colours of each side's page; dark pages get the soft shadow on the words, light pages none
const LOOKS = [
  { name: 'india_my_team', path: '/', pic: 'india.jpg', at: 'right -40px top -60px / auto 118vh', dark: true, page: '#0f2557', tile: '#162f68', rail: '#dab16f' },
  { name: 'australia_my_team', path: '/?team=Australia&nation=Australia', pic: 'australia.jpg', at: '62% 0 / cover', dark: false, page: '#e7e245', tile: '#f5f3b5', rail: '#0d3b1e' },
  { name: 'australia_smith', path: '/players/S%20Smith?nation=Australia', pic: 'australia.jpg', at: '62% 0 / cover', dark: false, page: '#e7e245', tile: '#f5f3b5', rail: '#0d3b1e' },
];
const css = (l) => `
  html, body { background: linear-gradient(90deg, ${rgba(l.page, .70)} 0%, ${rgba(l.page, .25)} 45%, ${rgba(l.page, .05)} 100%),
               url(${uri(l.pic)}) ${l.at} no-repeat fixed, var(--page) !important; }
  .main { background: transparent !important; }
  .rail, .rail-in { background: ${rgba(l.rail, .42)} !important; backdrop-filter: blur(6px); }
  .t, .tile, .hero { background: ${rgba(l.tile, .26)} !important; backdrop-filter: blur(2px); border-color: rgba(255,255,255,.14) !important; }
  .itabs button:not(.on), .head .chips button:not(.on), .head .chips span:not(.on), .pill { background: ${rgba(l.page, .35)} !important; }
  ${l.dark ? 'body { text-shadow: 0 1px 3px rgba(0,0,0,.85), 0 0 14px rgba(0,0,0,.45); }' : 'body, body * { text-shadow: none !important; }'}`;
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
  for (const l of LOOKS) {
    if (!fs.existsSync(`${art}/${l.pic}`)) { console.log('no picture for', l.name); continue; }
    const p = await b.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 2, colorScheme: l.dark ? 'dark' : 'light' });
    await p.goto(`http://127.0.0.1:${port}${l.path}`); await p.waitForSelector('body[data-ready]', { timeout: 300000 });
    await p.addStyleTag({ content: css(l) }); await p.waitForTimeout(900);
    await p.screenshot({ path: `${out}/${l.name}.png` }); console.log(l.name); await p.close();
  }
  await b.close();
})();
