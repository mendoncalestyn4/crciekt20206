# The new Stats Pack website: the plan

**Status:** plan only. Nothing is built yet.
**Waiting for:** your choice of page style and chart style (section 2).
**Branch:** `claude/cricket-captain-rebuild-c8v4dp`

---

## 1. What we're building, and why

A completely fresh website for the Stats Pack:

- one of the five page styles from the mock-ups;
- new charts in the chart style you pick, with pie and donut charts wherever something is a share of a whole;
- a cool look that is easy to understand.

**Everything the current site does carries over, and nothing is lost.**

### Why a new site instead of restyling the current one

The current site is built with Streamlit. Streamlit is quick to build with, but it holds the design back:

- one colour scheme for the whole program;
- the whole page reloads on every click;
- fixed menus and layout pieces;
- no custom shapes or animations.

The bold styles need full control, which only a website of our own gives. Those are Broadcast, Scoreboard and Game menu.

### Ground rules (yours, kept throughout)

- **Desktop only.**
- **Colours:** your national side's colours as approved (India: light-brown sidebar on dark blue; England: navy on light blue; Australia: dark green on yellow; New Zealand: black on light grey; all 31 nations covered). With no national side picked, the site uses the dark look.
- **Backgrounds:** clean and plain, with no stripes or patterns.
- **Logos:** exactly as you approved them, team by team.
- **Checks:** zero errors, with deep checks before anything is shown to you.
- **Approvals:** screenshots for your approval at the end of every stage. Nothing replaces the current site until you say so.
- **Old site:** the current site keeps working the whole time.

---

## 2. Decisions waiting for you

1. **Page style:**
   1. Broadcast
   2. Bento
   3. Almanack
   4. Scoreboard
   5. Game menu
2. **Chart style:**
   1. Circles
   2. Scouting report
   3. Pictograms
   4. Flows and timelines
   5. Grids

   You can mix them. For example, Circles for shares, Scouting sliders for player profiles and Flows for seasons.
3. **Changes from the mock-ups:** anything you want changed before we start.
4. **Name:** the site stays "Stats Pack" unless you want a new name.

---

## 3. How it will work

```
Your PC
 ┌──────────────────────────┐   ┌───────────────────────────┐   ┌──────────────────────────┐
 │ Cricket Captain          │   │ The engine (kept as is)   │   │ The stats server (new)   │
 │ Scorecards folder        │──▶│ reads every scorecard and │──▶│ answers the website's    │
 │ (autosaved by the game)  │   │ works out every number    │   │ questions, watches the   │
 └──────────────────────────┘   └───────────────────────────┘   │ folder for new matches   │
                                                                └────────────┬─────────────┘
                                                                             ▼
                                                                ┌──────────────────────────┐
                                                                │ The new website (in your │
                                                                │ browser): pages, charts, │
                                                                │ menus, team colours      │
                                                                └──────────────────────────┘
```

### Installing and running

- **Same install as now:** double-click `Start Stats Pack.bat`. It needs Python only. The website comes ready-built inside the zip, so there is nothing extra to install.
- **Works offline:** fonts, the chart library and logos are all inside the zip.
- **Only on your PC:** the server listens on your own computer and nothing else can reach it.

### Your saved data

- Careers, settings, notes, schedules, goals and backups stay in the same folder: `Documents\Cricket Captain Stats Pack`.
- The files stay the same too, so the new site opens your existing careers with nothing to convert.

### Old and new side by side

While the new site is being built, the zip also has `Start old Stats Pack.bat`, so you can always use the current site. The old one is removed only when you're happy with the new one.

---

## 4. The new site map

There are nine clear sections instead of 22 pages in a long list. Every current page has a place.

| New section | What's in it | From today's pages |
|---|---|---|
| **1. My team** (home) | Banner, after the match, next up, season so far, stars, alerts, squad, headlines, milestones, how you win, rivals, trophy cabinet, history, notes | Home (My team) |
| **2. Players** | Player profile (career card, all formats, batting, bowling, fielding, danger zones, conversion, match impact, rank over time, milestones, badges, firsts, quirks, compare seasons), Compare players, Player stories | Players, Compare players, Player stories |
| **3. Matches** | Find a match, scorecard, match report, best and worst, partnerships, how the wickets fell, match notes | Matches |
| **4. Teams** | Team record (all the team analyses: ratings, best XI, squad changes, chasing, close games, targets, comebacks, fortress, revenge, league race, deciders and more), Team vs team, Opponent preview, Team planner, Rivalries | Teams, Team vs team, Opponent preview, Team planner, Rivalries |
| **5. Competitions and seasons** | Points tables, title race and odds, knockout brackets, series, World Test Championship, season calendar, series tracker, season progress, season review and MVPs, honours board, trophy cabinets | Competitions, Season, Season review, Honours board |
| **6. Fixtures** | Schedule, add matches, change or delete, series, calendar, WTC race, milestones, goals | Fixtures |
| **7. Leaders and records** | Stat by stat leaders, records with timeline, hall of fame, rankings (player ratings, history, team Elo) | Stat by stat, Records, Hall of fame, Rankings |
| **8. Insights** | Score chances, par by opponent, chase calculator, runs above expected, fair averages, what wins games, expected wins, match-winners, style maps, boom or bust, form, bat or bowl first | Insights, Analytics |
| **9. Settings and tools** | Careers (switch, add a Scorecards folder, upload files or a zip or a career file, download a career file), your teams, logos folder, backups and restore, data check (merges, splits, catch credits) | Sidebar, Home set-up, Data check |

**On every page:**
- search for players, teams, matches and sections, with Ctrl K from anywhere;
- live "new matches added" and "New record!" alerts;
- your team's colours.

---

## 5. Nothing lost: the checklist

Every one of these must work on the new site before it replaces the old one.

**Matches coming in**
- [ ] Folder watching about every 20 seconds. Only new or changed scorecards are read, and deleting old files never loses matches.
- [ ] A "new matches added" message, and any files that couldn't be read are listed.
- [ ] "New record!" alerts when a record is broken.

**Getting started and careers**
- [ ] The "Which teams do you play as?" question on first start, saved with the career, and the My team picker.
- [ ] Add a career from a Scorecards folder (with the normal Windows Browse… window), from .txt files or a .zip, or from a saved career file.
- [ ] Download a career file.
- [ ] Weekly backups, with restore that can be undone.

**Your own fixes and notes**
- [ ] Data check: merge two names, split one name, credit a catch. Manual only: nothing changes until you confirm.
- [ ] Notes on matches and series, goals, and schedule edits with undo.

**Charts and tables**
- [ ] Under every chart: "What it shows" (with its numbers) and "What it's for".
- [ ] Save any chart as a picture, and download tables as CSV.
- [ ] One stat per chart, top-N limits and a minimum to qualify. Baselines always come from the section, and sections are never merged.

**Logos and colours**
- [ ] Logos: your looks picked team by team, the competition logo on scoreboards, the Pamir and Maiwand pictures swapped back, and the logos folder setting.
- [ ] Team colours for all 31 national sides, and the dark look when you play as no national side.

**Safety and data**
- [ ] A part that can't be shown never breaks the rest of the page.
- [ ] Every data fix already made stays, because it lives in the engine. That covers rain games, super overs, declarations, playoff stages and replayed seasons, real names, overwritten files, uncertain catches and wrong margins in the game's files.

---

## 6. The stages

Each stage ends with the same steps:
1. All tests pass.
2. I send screenshots of every page in that stage.
3. You approve or ask for changes before the next stage starts.

| Stage | What gets built | About |
|---|---|---|
| **0. Foundations** | The server (careers, settings, folder watching); the website shell in your chosen style (menu, search bar, team colours, logos, fonts); the chart kit (your chosen chart style as reusable pieces); the launcher and zip; the test set-up. **You see:** the shell, plus a "style guide" page with every chart piece drawn from your data. | 2–3 days |
| **1. Core pages** | My team home, Player profile, Match (scorecard and report) | 4–5 days |
| **2. Teams and competitions** | Teams, Team vs team, Opponent preview, Team planner, Rivalries, Competitions, Season, Season review, Honours | 5–6 days |
| **3. Leaders, records and insights** | Stat by stat, Records, Hall of fame, Rankings, Insights, Analytics, Player stories, Compare players | 4–5 days |
| **4. Fixtures and tools** | Fixtures (all 8 tabs, the biggest page), careers and uploads, backups, Data check, the first-start question, live alerts | 4–5 days |
| **5. Final checks and switch-over** | Full test runs, stress tests, a new-user install test from the zip, speed checks, and screenshots of every page and tab. Then the new site becomes `Start Stats Pack.bat`, the old site stays as a backup launcher, and the README is rewritten. | 3–4 days |

**Total:** about 4 weeks of work (3½ to 5), plus the time you take to approve each stage. After stage 1 you can already use the new Home, Player and Match pages next to the old site.

---

## 7. How every page gets built (the same recipe each time)

1. **List what the old page shows:** every number, table, chart and option, taken from the old page's code. This is the checklist for that page.
2. **The server answers with exactly those numbers,** straight from the engine. The website never does its own cricket maths.
3. **A parity test proves the numbers match.** For the same career, the new server's numbers must equal the old site's numbers, so nothing can change by accident.
4. **Build the page** in your style, with charts from the chart kit. Pies and donuts are used where something is a share of a whole.
5. **A browser test** opens the page with every section, season, team and option, fails on any error, and takes screenshots.
6. **Your approval** from the screenshots.

---

## 8. Testing and checks (zero errors)

**Tests**
- **Engine tests:** the current 1,021 keep running unchanged.
- **Server tests:** every question the website can ask, for every section, season and team in the test careers.
- **Parity tests:** new numbers against the old site's for the same inputs. They must be identical.
- **Browser tests:** a real browser clicks through every page, tab and filter. Any error on the page, or hidden in the browser's console, is a failure. Each run also takes screenshots.

**Data it's tested on**
- the 940 generated scorecards;
- the 477-match test career;
- **your 89 real scorecards.**

**Before the switch-over**
- **New-user test:** unzip on a clean machine, double-click, answer the first-start question, add a folder, and see a new match arrive by itself.
- **Speed targets:** changing page in under half a second on a 500-match career, and first start in under 5 seconds.

---

## 9. Risks, and what we do about each

| Risk | What we do |
|---|---|
| Losing one of the many small fixes | The engine is kept as it is, numbers are checked by parity tests, and every page has its checklist (section 5) |
| It takes longer than planned | Each stage delivers finished pages, and the old site keeps working |
| Windows quirks (folder window, paths, antivirus, a port already in use) | Keep today's Windows folder window, run only on your own computer, try another port if one is busy, and do the new-user test |
| Fonts or charts missing without internet | Everything is inside the zip |
| A big career being slow | The server keeps each career ready in memory and only re-reads it when files change |
| England's navy logo hard to see on dark styles | Solved in stage 0 for your chosen style, with your approval |

---

## 10. What I need from you

1. Your pick of page style and chart style, or a mix.
2. A yes (or changes) at the end of each stage, from the screenshots.
3. Optional: your latest scorecards zip near the end, for the final real-data test.

---

## Appendix: technical outline

**Kept**
- `ccstats/` (the engine, about 12,700 lines), with small additions only:
  - team colours move from `ui/theme.py` to `ccstats/colours.py`;
  - a few helpers that return plain data.
- `CareerStore`, `CareerSettings` and `Watcher` from `ccstats/local.py`, used as they are, with the same files on disk.

**New: the server (`server/`)**
- **Framework:** FastAPI with Uvicorn, on 127.0.0.1 only.
- **Careers in memory:** each career is cached, keyed by its files' modified times.
- **Watcher:** a background task runs the existing `Watcher` about every 20 seconds and pushes events (new matches, new records, unreadable files) to the browser over Server-Sent Events.
- **Logos:** served as PNG images from `ccstats/logos.py` and `ccstats/logo_look.py`, cached by path, size and look.
- **Questions the website can ask (draft):**
  - `/api/careers`, `/api/careers/{name}`, `/api/careers/{name}/sections`
  - `/home`, `/players/{player}`, `/compare`, `/stories`
  - `/matches`, `/matches/{id}`
  - `/teams/{team}`, `/h2h`, `/opponent`, `/planner`, `/rivalries`
  - `/competitions/{event}`, `/season`, `/review`, `/honours`
  - `/leaders`, `/records`, `/hall-of-fame`, `/rankings`, `/insights`, `/analytics`
  - `/fixtures` (get, add, change, delete), `/notes`, `/goals`
  - `/settings`, `/backups`, `/data-check`, `/search`
  - `/logo/team/{name}.png`, `/logo/comp/{name}.png`, `/events`

**New: the website (`web/`)**
- **Tools:** React with TypeScript, built with Vite; Apache ECharts for charts (radar, sunburst, Sankey, calendar, treemap, pictorial bars, gauges); React Router; TanStack Query for loading and caching data.
- **Styling:** CSS variables for team colours and the chosen style. Fonts are bundled.
- **Shipping:** the built files (`web/dist`) go into the zip, so your PC never needs Node.

**Testing tools:** pytest for the engine and server (FastAPI TestClient), Vitest for website pieces, and Playwright (Chromium) for whole-site browser tests and screenshots. TypeScript runs in strict mode.

**Launcher:** `Start Stats Pack.bat` starts the stats server, which opens the browser. During the transition, `Start old Stats Pack.bat` starts Streamlit.

**After the switch-over:** `app.py`, `views/` and `ui/` (the old site) and the Streamlit dependency are removed. Their tests become server and browser tests.
