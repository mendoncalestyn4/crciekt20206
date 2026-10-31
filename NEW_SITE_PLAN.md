# The new Stats Pack website: the plan

**Status:** stage 0 approved (27 October); stage 1 (core pages) under way.
**You said:** build it without waiting for answers; screenshots come at the end of each stage.
**27 October:** you've stopped using the current site, so it gets no more work (it stays as it is until the
switch-over). The zip comes once the whole new site is done. Screenshots of other teams' colours go in a set of their
own. In your three-season save you play as India and Mumbai Indians.
**27 October, stage 1 choices:** My team opens on whichever of your teams played last (a switch at the top changes
it). Adding and changing fixtures stays in stage 4; until then "Next up" reads the fixtures you've already entered.
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
- **Old site:** the current site keeps working, as it is (no more work on it), until the switch-over.
- **Parked ideas (31 October, to ask about again after stage 1 or 2):** EA FC style player cards with an overall
  rating per format; Team of the series and Team of the season; board confidence (results against what the ratings
  expected) and season awards.
- **To do list (31 October; planned, nothing started; each waits for your "build it"):**

  **A. Figures innings by innings, for batting and for bowling** (you liked all five parts). On the Player page, in its
  own tile: a batter's page shows the batting half, a bowler's page the bowling half, an all-rounder's both. The tile
  has two sections (your choice, 31 October): **Normal**, the player's own figures innings by innings and nothing else;
  and **Compare**, each figure against the usual (and against the player's own overall), with "better" or "worse" and
  by how much, and the summary line. *Open choice:* whether Compare can also put another player alongside.
  1. **Tests and first-class: the match's 1st, 2nd, 3rd and 4th innings apart.** Batting: innings, not-outs, runs,
     average, strike rate. Bowling (the innings the bowler bowled in): innings, overs, wickets, average, economy,
     strike rate (balls a wicket) and five-wicket hauls.
  2. **Against the usual** for that innings in the same competition: batting "30 (the usual: 22)"; bowling "average 21.4
     (the usual: 33.0)", with "better" or "worse" written out, since a lower bowling figure is the better one. The
     scorecards don't say who bowls spin or pace (checked 31 October: a stumping is the only sign, and only 13 of 295
     bowlers in the project's scorecards have one), so there is no spin and pace split; which other comparisons
     Compare shows is your choice (ideas given 31 October).
  3. **Few innings:** beside every figure, innings and not-outs (batting) or innings and overs (bowling), and a note when
     there are under 5 innings, so one big score or one big haul can't mislead.
  4. **The 4th innings split in two.** Batting: chasing to win, and batting to save the match. Bowling, the same innings
     seen from the other end: defending a total (the other side chasing), and bowling to win (the other side batting to
     save). Proposed rule, to be checked on your saves with examples shown to you before it's fixed: a target that
     needed more than about 4 an over in the time left counts as batting to save.
  5. **A summary line with the details:** the best and the weakest innings. Batting: "Best in the 4th innings, chasing:
     averages 38 (9 innings, 3 not out) against the usual 22 in Tests. Weakest in the 1st innings: 24 against the usual
     33." Bowling: "Best in the 4th innings, bowling to win: 23 wickets at 17.8 (7 innings, 2 five-wicket hauls),
     economy 2.4, against the usual 29.5 in Tests. Weakest in the 1st innings: 38.6 against the usual 31.2."
     An innings is only called the best with enough innings behind it (settled, like the best batting position).
     Bowlers are ranked on bowling average, except in T20 cricket, where economy decides (runs saved matter most there).
  6. **ODIs, T20Is and domestic one-day and T20:** batting first against chasing; bowling first against defending a
     total; the same usual, counts and summary line. Each format and each domestic competition stays on its own.

  Checks: hand-worked numbers locked into the tests, every player's page still whole, the fit check, and screenshots.
  About 1 to 1½ days.

  **B. Hand-worked matches locked into the tests** (idea 6, approved). About 5 tricky scorecards already in the project
  (rain and a tie with a super over, a T20I super over, a rain-hit Hundred game, a county declaration, a follow-on if
  there is one), every number worked out by hand and locked in. ½ to 1 day. *Waiting on:* if none of the 66 has a
  follow-on, make one up in the game's format, or skip that case.

  **C. "Does it add up" check** (idea 7, approved). Every innings: batters' runs + extras = total, bowlers' runs + byes +
  leg-byes = total, wickets = batters out, bowlers' wickets = their dismissals, overs, fall of wickets, the result and
  margin. At least everything the old Data check catches. Tried on all 66 scorecards and on your saves. ½ day.
  *Waiting on:* is a note on the match page, a list in Settings and an alert for a new match the right places?

  **D. Faster: only redo what a new match changed** (idea 1, approved). Each competition gets a fingerprint; a new match
  only redoes the competitions whose fingerprint changed (safe even when a new match moves an earlier final into another
  division); anything unlabelled is redone as today. Proved by comparing every kept number with a fresh rebuild, and
  timed before and after on your 2032 save. About 1 day.

  **E. Faster: remember the sums between starts** (idea 2, approved). Saved in the career's own folder, with a
  fingerprint of the scorecards, your fixes and the site's code: anything different, or a damaged file, and it's
  rebuilt as today, so old numbers can never show. ½ day. *Waiting on:* Python's built-in format (no new package; my
  pick) or the pyarrow package.

  Suggested order: B, C, D, E, then A (the tests guard the numbers before the speed changes).
- **Ask first:** before any extra work that wasn't asked for (checks to be sure, another set-up, anything to make the
  work easier), ask, with the choices; new features always need a yes. (31 October; also in `CLAUDE.md`.)

---

## 2. Decisions made

The style is **idea 4** from the mock-ups (`design/mockups/mix.html?idea=4`). It's the reference for every page.

1. **Base: Bento.** The sidebar rail and rounded tiles in a 12-column grid, in your team's colours (India: light-brown
   rail on dark blue).
2. **Look: Scoreboard (idea 2) exactly.**
   - Tile titles in Bebas Neue, spaced, with the two-tone line on top of each tile.
   - Gold numbers, glowing W/L lamps and the date chip in the header.
   - No slanted TV banners, gold tabs or Broadcast fonts.
3. **Charts: the ones on the pages you liked, no new chart types.**
   - Broadcast's: the player page, the "Most runs / Most wickets in the series" tables and the leaderboard bars.
   - From idea 1: solid innings bars, a bar for each percentile, a plain form line, solid bars in top-player lists, and
     the "Latest" results strip.
   - Donuts where something is a share of a whole.
4. **Fonts.**
   - Player and team names: Bebas Neue (Scoreboard).
   - Numbers: Space Grotesk (Bento).
   - Other text: Inter.
5. **Sizes.**
   - Words about 45% bigger than the first mock-ups, and numbers about 5% bigger.
   - A little extra room between words in names.
   - Nothing may go outside its tile, chart or the page. `design/mockups/check_fit.py` checks every page, and the
     site itself shrinks a number, name or table just enough when it wouldn't fit.
6. **Player of the match story.**
   - Almanack's summary: a headline worked out from the scorecard, then the engine's match report.
   - Shown on the site's own colours.
7. **Match page.** It follows your TV photo:
   - The match summary comes first: a band for each innings with the top batters and bowlers (three each in one-day
     games, one each in a Test), the result, and the player of the match story.
   - Then the scorecard, one innings at a time (bowling, then batting), with buttons to switch innings.
8. **England's badge:** look B, "a light tint of its own colours" (`STYLES` in `ccstats/logos.py`). Its navy no
   longer vanishes on dark blue.
9. **Name:** the site stays "Stats Pack".

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

While the new site is being built, `Start Stats Pack.bat` still starts the current site, and
`Start new Stats Pack (preview).bat` starts the new one. Both read the same careers, so you can open either. At the
switch-over (stage 5) the new site becomes `Start Stats Pack.bat` and the old site is deleted completely, with no
backup launcher (your choice, 31 October): `app.py`, `views/`, `ui/`, the tests that only check it, the preview
launcher, and Streamlit and Plotly from `requirements.txt`. Any engine checks inside those tests move to other test
files first, so nothing goes unchecked.

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
| **8. Insights** | Score chances, par by opponent (every team, home and away), chase calculator, runs above expected, fair averages, what wins games, expected wins, match-winners, style maps, boom or bust, form, bat or bowl first | Insights, Analytics |
| **9. Settings and tools** | Careers (switch, add a Scorecards folder, upload files or a zip or a career file, download a career file), your teams, logos folder, backups and restore, data check (merges, splits, catch credits) | Sidebar, Home set-up, Data check |

**On every page:**
- search for players, teams, matches and sections, with Ctrl K from anywhere;
- live "new matches added" and "New record!" alerts;
- your team's colours.

---

## 5. Nothing lost: the checklist

Every one of these must work on the new site before it replaces the old one.

**Every bit of information, line by line: `design/INVENTORY.md`.** Made by `tools/inventory.py`, it lists everything the
current site shows, in two ways:
- **From the code:** every heading, label, option, help text, explanation, table column, chart text and message written in
  `views/`, `ui/` and `app.py`, page by page and part by part. This includes what appears only for some choices, sections
  or teams.
- **From the live site:** every page opened on the test career, with what it actually shows: text, tiles, tables and
  their columns, charts with their titles, axes and series, choices with their options, tabs, expanders, buttons and
  downloads. The Player and Match pages are opened again with a player and a match picked, and Home with no team.
- **Saved on your PC:** every file in `Documents\Cricket Captain Stats Pack`, everything inside a career file (your
  scorecards and your data-check fixes), every setting saved with a career, and every preference.

Today that is **4,474 lines**: 3,036 from the code, 1,409 from 27 live page visits (all of them opened with 0 errors)
and 29 saved items. Run `python3 tools/inventory.py` to make it again.

It is a **hard gate**:
1. A page isn't finished until every line for it is ticked (shown on the new page in the new style) or marked with
   where it moved and why, for example "now in the hover text".
2. Nothing is dropped silently. Leaving anything out needs your yes, written next to the line.
3. At the switch-over, the same crawl runs on the new site and the two lists are compared. Any line missing on the new
   site stops the switch-over.

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

## 6. Logos: moved over exactly as you approved them

The logo work you approved moves over exactly as it is: the code that finds the pictures, matches names and draws the looks is reused, not rewritten.

**Where the pictures come from (unchanged)**
- Your Cricket Captain editor files: the `emblems` and `complogos` folders, with `editemblems.txt` and `editcomplogos.txt`.
- They're looked for in this order:
  1. the folder you chose;
  2. the game folder above each Scorecards folder you watch, and the Scorecards folder itself;
  3. the Steam install folder;
  4. a `logos` folder in the Stats Pack's own folder.
- Change a picture in the game and the site picks it up straight away.

**Which picture goes with which name (unchanged, `ccstats/logos.py`)**
- The name the scorecards print comes first, so "Delhi" (the game's IPL name) can never take "Delhi CC"'s picture.
- A real-name fallback never takes another team's picture.
- A competition two countries share is matched only with its country.
- A team with no picture shows no logo, never someone else's.
- Pamir Legends and Maiwand Champions, whose pictures your game files have swapped, are swapped back automatically.

**How each logo is drawn (unchanged, `ccstats/logo_look.py`)**
- Your look picked for every IPL, Hundred, Big Bash and international logo is reused as is (the `STYLES` list): plain, white inside the outline, the whole badge on white, a soft edge line, or dark parts made visible. Every other logo is shown as it is.
- On a light page every logo is shown as in the game.
- The pictures are drawn by the same code and served as images from your own PC. They're stored once, so pages stay fast.

**Where logos appear (all kept)**
- **My team:** your team's badge in the banner, and both teams plus the competition logo on the latest result.
- **Every scoreboard (Matches, Fixtures, My team):** both teams' badges. The World Test Championship logo appears on every Test; World Cup logos appear only on their own games.
- **Competitions:** the logo in the heading, and every team's badge in the tables.
- **Fixtures:** each opponent in the list, and the heading of the next match and of each series.
- **Teams, Team vs team and Opponent preview:** the team badges in the headings and tiles.
- **New places the chosen style adds:** leaders, rankings, series and player pages, as in the mock-ups.

**Sizes:** the same relative sizes as now (big in headings, medium on scoreboards, small in tables and lists), scaled to the new design. Every logo of a size keeps the same square frame, so logos line up.

**The logos settings:** the "Logos" box (which folder, how many team and competition logos were found, choose another folder) moves to Settings.

**Proof it's right**
- The logo tests move over unchanged.
- Three logo stress tests are run again on the new site:
  - all 366 team names and 60 competition names matched to the right picture;
  - all 288 pictures drawn in every look and size;
  - odd and missing names.
- A browser check opens every page with logos and fails on a missing or broken picture.
- You get logo screenshots in stage 0 and stage 1 to approve.

**Still missing:** Namibia and Herat show no logo, because `namibiaem.png` and `heratem.png` aren't in the game's emblems folder. Adding them to the game fixes it.

**Decided:** England's navy badge gets look B (a light tint of its own colours), chosen from ten options. It's in
`ccstats/logos.py` with a test, so the current site gets it too.

---

## 7. Everything that transfers: part by part

The rule is simple. **Anything that works out a number or makes a decision moves into the engine, with tests, before its page is rebuilt.** The new website only shows things.

| Part of today's site | How it moves to the new site |
|---|---|
| **The engine:** `ccstats/` (31 files: parser, loader, stats, players, teams, fixtures, odds, records, rankings, logos, logo looks…) | **Reused as is.** Every data fix lives here, so it comes along automatically. |
| **Your saved data:** careers, settings, notes, schedules, goals, forecasts, remembered choices, preferences (last teams, logos folder) and backups, in `Documents\Cricket Captain Stats Pack` (`ccstats/local.py`) | **Same files, same code.** The new site reads and writes exactly what the old one does. |
| **Folder watching** (`Watcher`) and the **Windows folder window** (`ui/pick_folder.py`) | **Reused** by the server. |
| **Team colours** (31 nations: sidebar, page, buttons, highlights, readable text) in `ui/theme.py` | **Moved** to `ccstats/colours.py` with their tests, then applied to the new style. |
| **Logo finding and display choice** (`ui/logos.py`: where to look, the light-page rule, the logos box) | **Moved** into the engine or server (see section 6). |
| **Site memory** (`ui/state.py`): current career, my teams, the first-start question (not now / don't ask again), home and away taken from your schedule, notes, remembered selections | **Moved** to the server with tests, so behaviour is identical. |
| **Search** (`ui/search.py`: players, teams, sections, matches) | **Moved** to the server, with the box in the new design (Ctrl K). |
| **Logic inside today's pages** (`views/*.py`, for example parts of Fixtures, Teams and the Player page) | **Moved into the engine page by page**, with a parity test, before the page is rebuilt. |
| **Chart explanations** ("What it shows" and "What it's for", with the numbers) | **Moved** to the server, so every new chart keeps its explanation. |
| **Charts** (`ui/charts.py`: Plotly) | **Rebuilt** in your chosen chart style (ECharts). The numbers come from the same engine. |
| **Page layouts** (`views/`, `ui/myteam_view.py`, `ui/calendar_view.py`, `ui/xi.py`) | **Rebuilt** in your chosen page style, following each page's checklist. |
| **Tests:** 1,021 today | **Engine and logo tests carry over unchanged.** Tests that drive the old pages become server and browser tests that check the same things. |
| **Test data:** generated scorecards, the 477-match test career, your 89 real scorecards, and the rain, super-over, declaration and name fixtures | **Carried over** and used for every stage. |
| **Launcher and zip** (`Start Stats Pack.bat`: first-start set-up and updates) | **Same steps.** It starts the new server instead of Streamlit, and `Start old Stats Pack.bat` stays until the switch-over. |
| **README and ROADMAP** | **Updated** for the new site at the switch-over. |

---

## 8. The stages

Each stage ends with the same steps:
1. All tests pass.
2. I send screenshots of every page in that stage.
3. You approve or ask for changes before the next stage starts.

| Stage | What gets built | About |
|---|---|---|
| **0. Foundations** | The server (careers, settings, folder watching); the website shell in your chosen style (menu, search bar, team colours, fonts); logos served exactly as approved, with the logo tests carried over; the chart kit (your chosen chart style as reusable pieces); the launcher and zip; the test set-up. **You see:** the shell, plus a "style guide" page with every chart piece drawn from your data. | 2–3 days |
| **1. Core pages** | My team home, Player profile, Match (scorecard and report). Your national side and franchise together. New: a player's share of the team's runs and wickets, wicket by wicket in every innings (section 14) | 4–5 days |
| **2. Teams and competitions** | Teams, Team vs team, Opponent preview, Team planner, Rivalries, Competitions, Season, Season review, Honours. New: who carries the team, your usual score at each wicket, collapses, the score to aim for against your next opponent, home or away, your season wrapped (section 14) | 5–6 days |
| **3. Leaders, records and insights** | Stat by stat, Records, Hall of fame, Rankings, Insights, Analytics, Player stories, Compare players. New: every team ranked by runs and wickets up to any date, best stand for each wicket, the score to aim for against every team, home and away, "plays like" on Compare players (section 14) | 4–5 days |
| **4. Fixtures and tools** | Fixtures (all 8 tabs, the biggest page), careers and uploads, backups, Data check, the first-start question, live alerts | 4–5 days |
| **5. Final checks and switch-over** | Full test runs, stress tests (including the three logo stress tests), a new-user install test from the zip, speed checks, and screenshots of every page and tab. Then the new site becomes `Start Stats Pack.bat`, the old site (Streamlit) is deleted completely with no backup launcher (your choice, 31 October), and the README is rewritten. | 3–4 days |

**Total:** about 4 weeks of work (3½ to 5), plus the time you take to approve each stage. After stage 1 you can already use the new Home, Player and Match pages next to the old site.

---

## 9. How every page gets built (the same recipe each time)

1. **List what the old page shows:** that page's part of `design/INVENTORY.md` (every number, table, chart, option, help text and explanation, from the code and from the live page). This is the checklist for that page.
2. **The server answers with exactly those numbers,** straight from the engine. The website never does its own cricket maths.
3. **A parity test proves the numbers match.** For the same career, the new server's numbers must equal the old site's numbers, so nothing can change by accident.
4. **Build the page** in your style, with charts from the chart kit. Pies and donuts are used where something is a share of a whole.
5. **A browser test** opens the page with every section, season, team and option, fails on any error, and takes screenshots.
6. **Your approval** from the screenshots.

---

## 10. Testing and checks (zero errors)

**Tests**
- **Engine tests:** the current 1,021 keep running unchanged.
- **Server tests:** every question the website can ask, for every section, season and team in the test careers.
- **Parity tests:** new numbers against the old site's for the same inputs. They must be identical.
- **Browser tests:** a real browser clicks through every page, tab and filter. Any error on the page, or hidden in the browser's console, is a failure. Each run also takes screenshots.

**Data it's tested on**
- the 940 generated scorecards;
- the 477-match test career;
- **your 89 real scorecards;**
- **your three-season save** (1,544 matches, 15 competitions), which is also the speed test for big careers.

**Before the switch-over**
- **Nothing-lost check:** `tools/inventory.py` crawls the new site the same way it crawled the old one. Every line in `design/INVENTORY.md` must be found on the new site or marked with your yes.
- **New-user test:** unzip on a clean machine, double-click, answer the first-start question, add a folder, and see a new match arrive by itself.
- **Speed targets:** changing page in under half a second on a 500-match career, and first start in under 5 seconds.
- **Big careers:** the slow sums (every match's excitement rating, the ratings, the records) are worked out once in
  the background when a career is opened or new matches arrive, and kept on disk, so a page on your 1,544-match save
  opens in under a second once that's done.

---

## 11. Risks, and what we do about each

| Risk | What we do |
|---|---|
| Losing one of the many small fixes | The engine is kept as it is, logic in today's pages moves into the engine first, numbers are checked by parity tests, and every page has its checklist (sections 5 and 7) |
| A logo going wrong in the move | The logo code is reused unchanged, the logo tests and stress tests are run again, and you approve logo screenshots in stages 0 and 1 (section 6) |
| It takes longer than planned | Each stage delivers finished pages, and the old site keeps working |
| Windows quirks (folder window, paths, antivirus, a port already in use) | Keep today's Windows folder window, run only on your own computer, try another port if one is busy, and do the new-user test |
| Fonts or charts missing without internet | Everything is inside the zip |
| A big career being slow | The server keeps each career ready in memory and only re-reads it when files change |
| England's navy logo hard to see on dark styles | Solved: look B, as you picked |

---

## 12. What I need from you

1. ~~Your pick of page style and chart style.~~ Done: idea 4.
2. A yes (or changes) at the end of each stage, from the screenshots.
3. Optional: your latest scorecards zip near the end, for the final real-data test.

---

## 13. Stage 0: what was built

**In the engine** (shared by both sites, with tests):
- `ccstats/colours.py`: the 31 national palettes and the night look (moved from `ui/theme.py`).
- `ccstats/matchstory.py`: the player-of-the-match headline and the series story. Every headline in the tests was read
  against its scorecard. A chase says exactly what was left ("13 balls", "more than 12 overs"), never rounded.
- `ccstats/search.py`: everything the search box lists (the current site's search uses it too, unchanged).
- `ccstats/logos.py`: where logos are looked for, and how one is drawn on a light or dark page (moved from `ui/logos.py`).

**The stats server** (`server/`, `python -m server`):
- careers kept in memory until their file changes, the one on screen, your teams;
- your colours (`server/theme.py`): India's are the approved mock-up's exactly; any other dark page gets the same steps
  from its own colour;
- logos as pictures in the look for the page;
- the style guide's numbers;
- search;
- the folder checked every 20 seconds, with new matches, records and unreadable files sent to every open page.

**The website** (`web/`, built into `web/dist`, about 1.4 MB with its fonts and chart library):
- **The shell:** the rail with the nine sections, the page head (title, where you are, choices, the date in your career,
  search), Ctrl K search, live news of new matches, your colours.
- **The chart kit**, every piece of the approved mock-up, in the designs picked on 26 October (section 14):
  - leaderboard bars, innings bars, percentile bars, rings with their list beside them, the season ring, the form
    line (the share of the last five won, with the results as lamps under it), the season calendar (twelve month
    tiles, April to March);
  - where the team ranks, the series score (the tug of war, and the ladder for the analysis), partnerships, ratings
    through the season, every team's rank;
  - the six new charts: our score v theirs, batting first or chasing, against stronger and weaker sides, home, away
    and neutral, runs of results, match-winners (the "every match by margin" chart is gone);
  - lamps, the last five innings, the TV table, the latest-results strip, top-five lists;
  - the player of the match's card and story, the TV match summary, the scorecard, the squad table, match-by-match rows.
  The style guide shows each one, and next to the six new charts the pages and stages each goes to.
- **The style guide** (Settings, or `/style-guide`): every piece drawn from your career.
- **The other sections:** what each will hold and in which stage, so every link works.
- **The fit rule:** checked on every page at 1280, 1366, 1440, 1600 and 1920 wide, in dark and light colours: 0 problems.

**Choices made while building it (all kept, 26 October):**
- **The rail's fifth section is "Seasons":** "Competitions" is too long for the rail at the approved size. The page
  itself is "Competitions and seasons".
- **Light pages:** 30 of the 31 national sides have a light page. On a light page the gold numbers become a deep gold,
  and the lamps and bars a shade darker, so they read on a light tile. Bright gold on white would be hard to read.
- **Chart labels shrink to their room:** a chart in a narrow tile, or with many bars, makes its labels smaller rather
  than letting them touch. A donut's ring gets smaller to keep its labels inside.
- **Dates across seasons:** when a chart runs over more than one year, its dates carry the year ("11 Jun ’27").
- **T20 scorecards:** the bowling table shows dot balls ("0s") where the game prints them instead of maidens.

---

## 14. Added since stage 0 (your requests)

**Your teams.** Every national side works next to a franchise or domestic side you also play as (for example India
and Mumbai Indians). Every page can switch between your teams; the colours always come from the national side.
**Every feature works for every team in every competition:** national sides, franchises and domestic sides alike
(27 October). Each stage is checked with every team that has matches in the test careers, not just your own.

**A player's share of the team** (stage 1, Player profile; again in stage 2 on the team page as "who carries the
team"). For each format and each year: how many of the team's runs the player made and how many of its wickets they
took, with the share ("A Sharma: 419 of India's 1,980 T20I runs in 2026, 21%").

**Teams ranked by runs and wickets** (stage 3, Leaders). Every team, most to least: runs scored and wickets taken,
counted from the start of the career up to any date you pick on the calendar, for each format. Seasons (stage 2) gets
a small "where your team ranks" tile from it.

**Wickets and scores.** Only what the scorecards record exactly: the score at each wicket, the partnerships and who
batted, the total overs. The game doesn't save the over in which a wicket fell, or the runs in each over, so there is
no over-by-over chart.
1. **Wicket by wicket** (stage 1, Match): every innings as a climbing bar per wicket, with the score at the fall, the
   partnership and who was in ("2-171: Gill & Iyer added 156").
2. **Your usual score at each wicket** (stage 2, Teams): across a format or a season, the team's typical score at the
   fall of each wicket ("in ODIs India are usually 48/1, 97/2, 152/3…"), against the opponents', with the best and
   the worst.
3. **Collapses and big stands:** innings where several wickets fell for few runs, with your team's worst collapses
   (stage 2, Teams), and the best stand for each wicket (stage 3, Records).

**The score to aim for, against each team, home and away.** How many to make batting first to win, against that
team, at home, away or on a neutral ground (going by the host country, as the scorecards don't name the ground), for
each format.
1. **Opponent preview** (stage 2): for your next match, the total that makes it 50/50 and the total that gives you a
   70% chance ("v England, away, T20I: 175 for an even game, 194 for 70%"). Then, for when you bowl first, the score
   they usually set against you there. Your real matches against them there, each total and result, sit underneath.
   The My team "next up" tile shows the same line.
2. **Insights** (stage 3): the full table, every team at home, away and neutral in each format. The current "is it
   enough against a good side?" (the stronger and weaker half) stays as a second view, so nothing is lost.
3. **How it's worked out:** your own games against one team are too few on their own (India have played England 5
   times in T20Is, all in England), so it learns from every team's games in the format:
   - the chance of winning against the total made batting first, from every finished game without rain, with how
     fast it rises shared by all formats of the same length (T20Is with the IPL, the Blast and the Hundred);
   - what playing at home is worth, in runs, from every team's home and away games; it starts near nothing and grows
     only as the games show it (in your career so far: about 1 run in T20Is, 5 in ODIs);
   - how well that team bats, and how well you bowl, in runs above or below the usual total, pulled towards usual
     until there are enough games (5 games count half).
4. **How sure it is:** every target says how many games it rests on, with a "few games, treat with care" note when
   they are few. The page also shows how often it would have called your past games right (each game predicted
   from all the others). Checked on 25 October on your career and the 477-match test career: it matched or beat
   "the total alone" in all four checks (T20Is and ODIs in each). A version that let home and away and the teams count
   for as much as the few games suggested did worse than it in all four, so it isn't used.
5. **Tests:** draws mean no single target makes sense, so Tests show the first-innings totals that won, drew and lost
   against that team, home and away, instead.

**Every team from the start (fixed on the current site, 25 October).** In a new save a team that hadn't played yet
was in no list. Now the game's own list of teams (all 235, with each team's country) says which competitions each
plays in. That covers the international formats (only the 12 Test sides in Tests), every franchise league (IPL, BBL,
SA20, CPL, PSL, BPL, LPL, the Hundred) and the domestic competitions every side of a country plays: the County
Championship, Blast and One-Day Cup; the Ranji, Vijay Hazare and Mushtaq Ali; the Shield and Marsh Cup; and the
Plunket, Ford Trophy and Super Smash. These pages offer those teams from the start, marked "no games yet":
- My team (any franchise or county can be picked before its first match, as a country could);
- Team vs team, Teams, Opponent preview and the home page's next opponent;
- Fixtures (a franchise's whole league, a county's fellow counties);
- search.

A page then says plainly that the team hasn't played there yet, and where it has. A County Championship division, a
tour side, Afghanistan's sides and competitions only some sides play show their teams once they've played, because
who is in them isn't certain. A team renamed in the game is listed by its new name, and its scorecards from before
the rename aren't counted as a second team. The new site uses the same list.

**The features above, checked (25 October).** For each one: is there a version on the current site already, does
its logic hold on your career and the 477-match test career, and what the new site does better.

| Feature | Already on the current site? | Logic check | New site |
|---|---|---|---|
| Your teams (national + franchise) | Yes, but only countries could be picked before their first match | Fixed: every team can (above) | Same list |
| A player's share of the team | Partly: Stories, "who carries their team" (runs only, over all seasons, the innings they batted) | Correct for what it says | Runs and wickets, each format and year, of the whole team total |
| Teams ranked by runs and wickets to a date | No (team tables rank by results) | – | New |
| Wicket by wicket | Yes: Match page, with a par line | Correct; the par for a late wicket comes only from innings where it fell, which the new page's note will say | Climbing bars with the stand and who was in |
| Usual score at each wicket | Yes: the Match page's par line | As above | Your team against the opponents, best and worst |
| Collapses | Yes: Teams (4 or more wickets for 30 or fewer) | Correct (checked by hand); one per innings, the longest | Also big stands |
| Best stand for each wicket | Records only as alerts, Teams as "best" | **Wrong on the Teams page**: stands still unbroken at the end weren't counted, so the best was wrong in 30 rows of your career and 91 of the test career (England's best 5th-wicket ODI stand showed 46; it was 91*). Fixed: unbroken stands count, the average is over the stands that were broken (as cricket counts them), and Opponent preview's weak spot counts the same way | Records by wicket |
| Score to aim for | Partly: Insights, "is it enough against a good side?" (stronger and weaker half) | **Weak**: the halves went by raw win %, so one win in one game made a side "strong" (Ireland were a stronger Test side after one Test). Fixed: each side counts as if it had already won 2 and lost 2 | Every team, home and away (above) |
| Our score v theirs, bat first or chase, stronger and weaker sides, home and away, streaks, match-winners | Tables of each on Teams, Insights and Opponent preview | Correct (bat first or chase, home and away, streaks, match-winners checked on both careers) | The six new charts, on the pages you pick |

**New features (suggested 25 October, each tried on your two careers first; decided 26 October).** All exact from
what the scorecards record (no overs for wickets, no grounds, no toss).
1. **Plays like** (stage 3, Compare players): the three players most like the one you pick: average (3 dismissals at
   least), strike rate, share of runs in fours and sixes and where they bat, in the same length of game, each with
   how alike they are, to start a comparison from. Checked: a player's three nearest bat within a place of him on
   average (0.3 to 0.8 places, against 3.3 for any three players). Your career: S Gill (ODIs) plays like P Nissanka
   98%, Y Jaiswal 92%, T Head 90%.
2. **Your season, wrapped** (stage 2, Seasons · season review): the season in nine slides you can save as a picture:
   record, top run-scorer and wicket-taker, highest score, best bowling, biggest stand, longest winning run, biggest
   win, player of the season. Your 2026: 22 matches, won 12, lost 10; S Gill 830 runs; A Singh 34 wickets; S Gill
   163; K Yadav 5/28; Gill and Jaiswal's 225 for the first wicket; won by 201 runs v Afghanistan.

On hold: the scouting shortlist (you have another plan for it; it waits in the README under "Ideas on hold").
Dropped: fantasy points, how hard your players have worked, the career quiz, "on this day", a team "nemesis" list.

**The season calendar's year (decided):** April to March, with every competition in the year its season belongs to.
The IPL starting on 29 March stays whole in that season's calendar (with a small "29 Mar" mark at the start), never
split from the rest of its tournament, so its record matches its points table.

**Chart changes picked:** donuts with their list beside them (no words on the ring); the season calendar as twelve
month tiles, April to March (every match on its day, each month's record, the best month lit up); the series score
as a tug of war on the main pages (above the line you lead, below it they do) and as the scoreboard ladder (the series
score after every match, the decider marked) in the analysis. The "every match by margin" chart is dropped (it only
repeats each result); six new charts take its place (below).

**The six new charts, and where each goes (picked 26 October):**

| Chart | Pages | Stages |
|---|---|---|
| 1. Our score v their score (both totals on one line, green won, red lost; a Test's innings each on its own line) | Matches, My team | 1 |
| 2. Batting first v chasing (record each way, the score you usually set, totals defended, lost with, chased down, failed to chase) | Opponent preview, Team vs team, Insights | 2, 3 |
| 3. Against stronger and weaker sides (by the ratings just before each match) | Teams, Leaders · rankings, Insights | 2, 3 |
| 4. Home, away and neutral (then country by country, by the host country) | My team, Teams, Opponent preview | 1, 2 |
| 5. Streaks (every match in order, the longest runs marked, the run you're on) | My team, Teams, Leaders · records | 1, 2, 3 |
| 6. Match-winners (who won your wins, and what they did each time) | My team, Players, Seasons · season review | 1, 2 |

**The form line (final, 26 October):** the line is the share of the last five matches won,
on its own 0 to 100% scale, and the results sit under it as lamps (the first version stood win and loss bars on the %
scale, so a win looked like "90%"). The first four matches are dashed until there are five to count (no more "high
100%" after one win; best and worst count only full fives); each series is marked over its matches with its score; "now"
says whether it's up, down or level on five matches before; a format with fewer than five matches shows its results
and says when the line starts.

**Match excitement (26 October).** The current site's 0–10 score is too flat: the tightest normal finish is worth
only 3 to 4 points (a 1-wicket win is exactly 3.0), balls left in a chase count for nothing (West Indies' 3-wicket win
off the last ball scored 1.7), and nothing in your career scores above 5.2. A fixed rating was tried on your matches:
the finish worth up to 6 points (balls left count, no cliffs), drama up to 2 (a comeback under 25%, the lead really
changing hands), stakes up to 1 (finals, semi-finals, series deciders) and big performances up to 1; with each match's
rank and clearer reasons. You found it still too low for the closest games (England's 1-wicket Test win after
trailing by 115 got 6.7), so it was reworked (27 October) and checked on your three-season save (1,544 matches):
- **The finish, up to 7:** a tie 7, a tie and a super over 8; a 1-run, 1-wicket or last-ball win 7; otherwise smoothly
  less. A draw with the last pair holding on, or the chasers just short, up to 7.
- **A comeback, up to 2, read from the scorecard:** in the last innings, the runs still needed against what the wickets
  left usually add (from the section's own partnerships); in a Test, a first-innings deficit turned round; or the
  win-chance model's comeback, only where it rests on 8 matches or more.
- **The stakes, up to 1:** a final or series decider 1; a semi-final, qualifier or eliminator 0.7; levelling a series 0.5.
- **Big moments, up to ½:** a hundred, a big haul, both sides scoring big, a big chase.
- England's 1-wicket Test is now 9.6, West Indies' last-ball T20I win 9.3; every 1-run and 1-wicket win is 7 or more;
  New Zealand's 231-run win stays at 0.2. In `ccstats/excitement.py`, with its tests; the pages use it from stage 1.
- **Where (picked):** Matches (the best games list and the score on each match page, stage 1), Seasons · season review
  (the season's best matches, and a "best game" slide in Season wrapped, stage 2), Leaders · records (the best games
  ever, stage 3). Not on My team.
- **The current site** keeps its score as it is; the new rating comes with those pages, stage by stage.

**The series score (confirmed 26 October):** the tug of war on the main pages, the scoreboard ladder in the analysis,
as decided above.

---

## Appendix: technical outline

**Kept**
- `ccstats/` (the engine, about 12,700 lines), with small additions only:
  - team colours move from `ui/theme.py` to `ccstats/colours.py`;
  - a few helpers that return plain data.
- `CareerStore`, `CareerSettings` and `Watcher` from `ccstats/local.py`, used as they are, with the same files on disk.

**New: the server (`server/`)**
- **Framework:** Starlette with Uvicorn, on 127.0.0.1 only. (FastAPI was the first idea; Starlette, which FastAPI is
  built on, is enough here and adds nothing new to install: Streamlit already brings both. They're listed in
  `requirements.txt` all the same, so the new site keeps working when Streamlit goes.)
- **Only your computer:** it answers only to the names 127.0.0.1 and localhost, and takes changes only as JSON, so a
  web page elsewhere can't reach it or change anything.
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

**Testing tools:** pytest for the engine and server (a real server on a free port, asked over HTTP), and Playwright
(Chromium) for whole-site browser tests and screenshots. TypeScript runs in strict mode. (Vitest comes in when the
website has logic of its own worth testing apart from the pages.)

**Launcher:** `Start new Stats Pack (preview).bat` (the same set-up steps) runs `python -m server`, which picks a free
port from 8601 and opens the browser. At the switch-over it becomes `Start Stats Pack.bat`, and `Start old Stats
Pack.bat` starts Streamlit.

**After the switch-over:** `app.py`, `views/` and `ui/` (the old site) and the Streamlit dependency are removed. Their tests become server and browser tests.
