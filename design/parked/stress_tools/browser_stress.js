// node browser_stress.js <port> <width> <dark|light>: the stage 1 pages clicked through fast, as an impatient player would: every page opened
// without waiting for the last to finish, then every tab, chip and switch on My team, Players and Matches pressed in
// quick succession, then the back and forward buttons. Any page error, console error or failed request is a problem;
// at the end each page must still settle with the right content.
const { chromium } = require('playwright');
const port = process.argv[2] || '8613', base = `http://127.0.0.1:${port}`, width = +(process.argv[3] || 1440), scheme = process.argv[4] || 'dark';
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
  const p = await b.newPage({ viewport: { width, height: 1000 }, colorScheme: scheme });
  const errs = [];
  p.on('pageerror', (e) => errs.push('pageerror ' + String(e).slice(0, 200)));
  p.on('console', (m) => { if (m.type() === 'error') errs.push('console ' + m.text().slice(0, 200)); });
  p.on('response', (r) => { if (r.url().includes('/api/') && r.status() >= 500) errs.push(`api ${r.status()} ${r.url().slice(22, 160)}`); });
  const ready = async () => p.waitForSelector('body[data-ready]', { timeout: 300000 });
  // 1. every page, one after another without waiting
  const pages = ['/', '/?view=scouting', '/?team=Mumbai%20Indians', '/inbox', '/players', '/players/S%20Gill', '/players/S%20Gill?view=bowling',
    '/players/J%20Bumrah?view=story', '/players/J%20Bumrah?view=fielding', '/matches', '/settings', '/players/S%20Gill?section=Tests',
    '/?view=scouting&team=Mumbai%20Indians', '/matches', '/'];
  for (const path of pages) { await p.goto(base + path, { waitUntil: 'commit' }).catch((e) => errs.push('goto ' + path + ' ' + String(e).slice(0, 80))); await p.waitForTimeout(250); }
  await ready();
  // 2. every switch on the page pressed fast, page by page
  for (const path of ['/', '/players/S%20Gill', '/players/J%20Bumrah', '/matches']) {
    await p.goto(base + path); await ready(); await p.waitForTimeout(500);
    const buttons = p.locator('main .itabs button, main .chips button, .head .chips button');
    const n = await buttons.count();
    for (let round = 0; round < 2; round++) for (let i = 0; i < n; i++) { await buttons.nth(i).click({ timeout: 5000 }).catch(() => {}); await p.waitForTimeout(120); }
    await p.waitForTimeout(800); await ready();
  }
  // 3. a match page: its tabs fast, then back and forward through history
  await p.goto(base + '/matches'); await ready();
  const first = p.locator('a.mli').first();
  if (await first.count()) { await first.click(); await ready();
    const tabs = p.locator('.head .chips button, main .itabs button'); const n = await tabs.count();
    for (let i = 0; i < n; i++) { await tabs.nth(i).click({ timeout: 5000 }).catch(() => {}); await p.waitForTimeout(100); } }
  for (let i = 0; i < 6; i++) { await p.goBack().catch(() => {}); await p.waitForTimeout(150); }
  for (let i = 0; i < 6; i++) { await p.goForward().catch(() => {}); await p.waitForTimeout(150); }
  await ready();
  // 4. search: Ctrl K, type, pick the first result; then junk typed in
  for (const typed of ['Gill', 'India', 'Tests', 'zzzz', '<b>x</b>', '名前']) {
    await p.goto(base + '/'); await ready();
    await p.keyboard.press('Control+K'); await p.waitForTimeout(300);
    await p.keyboard.type(typed, { delay: 20 }); await p.waitForTimeout(400);
    await p.keyboard.press('Enter'); await p.waitForTimeout(800);
    await ready().catch(() => errs.push('not ready after searching ' + typed));
    await p.keyboard.press('Escape').catch(() => {});
  }
  // 5. after all that, each page still settles with its content
  for (const [path, sel] of [['/', '.t'], ['/players/S%20Gill', 'main .hero'], ['/matches', 'a.mli'], ['/inbox', '.t']]) {
    await p.goto(base + path); await ready();
    if (!(await p.locator(sel).count())) errs.push('no content after the stress on ' + path);
  }
  console.log(errs.length ? errs.join('\n') : 'no problems');
  console.log('problems', errs.length);
  await b.close();
})();
