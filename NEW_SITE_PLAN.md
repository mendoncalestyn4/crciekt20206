# The new Stats Pack website: the plan

**Status:** style chosen (section 2). Stage 0 (foundations) is built (section 13): screenshots sent for your approval.
**You said:** build it without waiting for answers; screenshots come at the end of each stage.
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
switch-over (stage 5) the new site becomes `Start Stats Pack.bat` and the current one becomes `Start old Stats Pack.bat`,
kept until you're happy with the new one.

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
| **1. Core pages** | My team home, Player profile, Match (scorecard and report). Your national side and franchise together. New: a player's share of the team's runs and wickets, wicket by wicket in every innings, "plays like", how hard your players have worked lately (section 14) | 4–5 days |
| **2. Teams and competitions** | Teams, Team vs team, Opponent preview, Team planner, Rivalries, Competitions, Season, Season review, Honours. New: who carries the team, your usual score at each wicket, collapses, the score to aim for against your next opponent, home or away, your season wrapped, the scouting shortlist, the replacement finder (section 14) | 5–6 days |
| **3. Leaders, records and insights** | Stat by stat, Records, Hall of fame, Rankings, Insights, Analytics, Player stories, Compare players. New: every team ranked by runs and wickets up to any date, best stand for each wicket, the score to aim for against every team, home and away, fantasy points with a team of the week and of the season, the career quiz (section 14) | 4–5 days |
| **4. Fixtures and tools** | Fixtures (all 8 tabs, the biggest page), careers and uploads, backups, Data check, the first-start question, live alerts | 4–5 days |
| **5. Final checks and switch-over** | Full test runs, stress tests (including the three logo stress tests), a new-user install test from the zip, speed checks, and screenshots of every page and tab. Then the new site becomes `Start Stats Pack.bat`, the old site stays as a backup launcher, and the README is rewritten. | 3–4 days |

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
- **your 89 real scorecards.**

**Before the switch-over**
- **Nothing-lost check:** `tools/inventory.py` crawls the new site the same way it crawled the old one. Every line in `design/INVENTORY.md` must be found on the new site or marked with your yes.
- **New-user test:** unzip on a clean machine, double-click, answer the first-start question, add a folder, and see a new match arrive by itself.
- **Speed targets:** changing page in under half a second on a 500-match career, and first start in under 5 seconds.

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
- **The chart kit**, every piece of the approved mock-up:
  - leaderboard bars, innings bars, percentile bars, donuts, the season ring, the form line, the calendar;
  - where the team ranks, the series score, partnerships, ratings through the season, every team's rank, margins;
  - lamps, the last five innings, the TV table, the latest-results strip, top-five lists;
  - the player of the match's card and story, the TV match summary, the scorecard, the squad table, match-by-match rows.
- **The style guide** (Settings, or `/style-guide`): every piece drawn from your career.
- **The other sections:** what each will hold and in which stage, so every link works.
- **The fit rule:** checked on every page at 1280, 1366, 1440, 1600 and 1920 wide, in dark and light colours: 0 problems.

**Choices made while building it (say if you want them changed):**
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
Checked for Australia, New Zealand, England and India, each with a franchise (stage 1).

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

**New features (suggested 25 October; each one tried on your two careers first).** All of them are exact from what
the scorecards record (no overs for wickets, no grounds, no toss).
1. **Fantasy points** (stage 3, Leaders; team of the week on My team). Every player gets points from every match:
   - batting: a point a run, +1 a four, +2 a six, +8 for a fifty or +16 for a hundred, −2 for a duck (top seven);
     a strike-rate bonus or penalty in T20s (10 balls or more) and one-dayers (20 or more);
   - bowling: 25 a wicket, +8 if bowled or lbw, a bonus for 3, 4 or 5 wickets, a point a dot ball in T20s (their
     cards print dots), +4 a maiden in one-dayers (theirs print maidens), an economy bonus or penalty;
   - fielding: 8 a catch (+4 for three), 12 a stumping, 6 a run out when the card names the fielder;
   - 4 for playing.

   Leaderboards per format and season, the best single matches, and the team of the week and of the season. Checked
   by hand against the printed scorecards (A Sharma's 100* and 3/32 v West Indies: 250 points; four bowlers' bowled
   and lbw bonuses taken from the printed dismissals). Two players with one name on opposite sides (C Green for New
   South Wales and for Western Australia, in the same game) are kept apart. In your career, every format of 2026
   together: A Singh 1,335, S Gill 1,260, A Sharma 1,173.
2. **How hard your players have worked** (stage 1, My team; stage 2, Team planner). Overs bowled and matches played
   in the last 14 and 30 days, for every player of all your teams together (India and Mumbai Indians share players),
   against each one's usual 30 days, with a "heavy" flag before your next match. In the test career, J Bumrah bowled
   66 overs in the 30 days to 6 June across the IPL and India's Tests, against his usual 26.
3. **Plays like** (stage 1, Player profile; stage 2, the replacement finder in Team planner). The three players most
   like one: average (3 dismissals at least), strike rate, share of runs in boundaries and where they bat, in the
   same length of game. Checked: a player's three nearest bat within a place of him on average (0.3 to 0.8 places,
   against 3.3 for any three players). Your career: H Brook (ODIs) plays like J Inglis, B Duckett and P Stirling.
4. **Your season, wrapped** (stage 2, Seasons): the season told in slides you can save as a picture: record, top
   run-scorer and wicket-taker, highest score, best bowling, biggest stand, longest winning run, biggest win, most
   sixes. Your 2026: 22 matches, won 12, lost 10; S Gill 830 runs; A Singh 34 wickets; S Gill 163; K Yadav 5/28; Gill
   and Jaiswal's 225 for the first wicket; won by 201 runs v Afghanistan.
5. **Scouting shortlist** (stage 2, Team planner): the best players in your competition who don't play for you, by
   role (top order, middle order, finisher, all-rounder, bowler), by match impact over the last two seasons, five
   games at least: for the auction or a call-up. Test career, IPL for Mumbai Indians: H Singh and P Shaw at the top of
   the order, D Jurel in the middle, N Sindhu as an all-rounder.
6. **Career quiz** (stage 3, Player stories): questions made from your own career, with three wrong answers from the
   same pool ("Who made 163 for India v West Indies on 3 Oct 2026?"). Your own team is never offered as the answer
   to "against whom?".

Tried and dropped: "on this day" (both careers cover about one game year, so it would be empty for a long time); a
team "nemesis" list (the player page's nemesis and the opponent's key players already cover it).

**The season calendar's year (decided):** April to March, with every competition in the year its season belongs to.
The IPL starting on 29 March stays whole in that season's calendar (with a small "29 Mar" mark at the start), never
split from the rest of its tournament, so its record matches its points table.

**Chart changes picked:** donuts with their list beside them (no words on the ring); the season calendar as twelve
month tiles, April to March (every match on its day, each month's record, the best month lit up); the series score
as a tug of war on the main pages (above the line you lead, below it they do) and as the scoreboard ladder (the series
score after every match, the decider marked) in the analysis. The "every match by margin" chart is dropped (it only
repeats each result); something more useful takes its place.

**Chart changes waiting for your pick** (from the mock-ups sent on 24 October): every match by margin (one row per
match, runs and wickets on their own tracks), the season calendar (April to March: timeline, month tiles, heatmap or
year clock), donuts with their list beside them, the series score (ladder, race to win, tug of war), the new form
line. Whatever you pick goes into the chart kit before stage 1's pages use it.

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
