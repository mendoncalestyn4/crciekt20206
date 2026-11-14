# The stage 0-2 fix round: the checklist (13 November)

Made before building, as your rule asks: every promise from the plan (`NEW_SITE_PLAN.md`) and every answer you gave
(`design/AUDIT_STAGES_0-2.md`, its point numbers in brackets) that this round must deliver, each with the page it goes
on. Each line gets ticked with where it is on the site and how it was checked. Nothing is built until you say go.
Not in this round: Team leaders and the rest of stage 3; to-dos B to E (after stage 3).

---

## 1. First: the nothing-lost checklist (the hard gate)

- [x] Every open line of `design/INVENTORY.md` for Teams, Opponent preview, Team vs team, Team planner, Season review,
      Competitions, Season, Rivalries and Honours ticked with where it is now, or marked with the stage it goes to (15)
      — ✓ 1,226 lines, 13 November (each placed from a crawl of every page, tab and option, the rest by hand)
- [x] The 10 lines stage 1 left for stage 2 (the table of every competition, Opponent preview) ticked (15) — ✓ 11
- [x] The shared parts ticked: the charts' texts, team of the XI, logos, search, colours, the menu, saved data (15)
      — ✓ 401 placed (stage 3 and 4 ones marked with their stage)
- [x] Anything found missing is built in this round, or brought to you for a yes before being left out — ✓ 7 found,
      all built (13 November): the table of every competition (Competitions, in the engine, with a parity test);
      "Preview →" from My team's Next up; Rivalries' opening line; Season review's note on its rules; the planner's
      pair tables saying who qualifies; the "no matches yet" message with how to get matches in (every page); and the
      remembered picks: every page opens on the section, season, team and competition you last picked

## 2. Opponent preview

- [x] **The score to aim for, rebuilt as agreed** (1; section 14): the chance of winning against the total made
      batting first, from every finished game without rain, how fast it rises shared by cricket of one length (T20Is
      with the IPL, the Blast and the Hundred; ODIs with the domestic one-day cups), each competition keeping its own
      totals; home worth some runs, from near nothing, growing only as the games show it; their batting and your
      bowling in runs above or below the usual total, pulled to the usual until there are enough games (5 count
      half); the totals for an even game and for 70%, home, away and neutral — ✓ Opponent preview, top tile
      (`ccstats/aim.py`); checked: the fit finds a made-up known answer, every strength counted again by hand, every
      target put back through the curve gives 50% and 70% (`tests/test_aim.py`); on your 2032 save T20Is fit 1,110
      games in 0.7 s
- [x] How sure it is: how many games each target rests on; "few games, treat with care" under 10; how often it would
      have called your past games right, next to "the total alone" (1) — ✓ the tile's "How sure it is" lines; each game
      judged from all the others, counted again by hand in the tests (2032 save: T20Is 79% against 77% for the total
      alone, ODIs 75% against 73%)
- [x] The score they usually set against you there, and your real games against them there (1) — ✓ the same tile,
      each ground; checked against the scorecards for every pair of teams in six competitions
- [x] **Tests:** the typical first-innings total that won, drew and lost against that team, home and away, with every
      game under it (1) — ✓ the tile in Tests and first-class ("First-innings totals that won, drew and lost"), neutral
      grounds too; counted again by hand for every pair in Tests, the Ranji Trophy and the County Championship
- [x] **My team's "next up" tile** shows the same line ("v England, away, T20I: 175 for an even game, 194 for 70%") (1)
      — ✓ My team · Next up, "🎯 Batting first v …"; in Tests the first-innings total that usually beat them there;
      the test checks it equals Opponent preview's
- [x] Batting first v chasing chart, the opponent's own record, in the main tab under the head-to-head record (2, 7)
      — ✓ Opponent preview · Head to head, under the record (shows with no team of yours picked too); counted again
      from the scorecards for 18 opponents in ODIs, Tests and the IPL
- [x] Home, away and neutral chart, then country by country, the opponent's own record, same place (2, 7) — ✓ next
      to it; counted again the same way
- [x] **How they play** at the top of "About them" (26): bowling (when they take wickets, sides 3 down cheaply and
      bowled out, the new-ball bowlers' share, the top-order share, attack or squeeze, dot balls in T20); batting
      (strike rate and boundary share by part of the order, fours and sixes and from where, their usual score at each
      wicket); a plain summary; their own figures only; this season, with a note and a button for last season when
      this season has fewer than 5 matches — ✓ Opponent preview · About them, at the top (`ccstats/howtheyplay.py`); every figure counted
      again for every team of every competition; the rules it reads by written on the page
- [x] **Their danger men right now** (30): three by impact points this season (last season when under 5 matches),
      each with their last five innings or spells — ✓ Opponent preview · About them (`ccstats/moments.py`); the top three checked against
      Season review's MVP points, the last five innings against the scorecards
- [x] **Big-match players** (29): their players in finals, semi-finals, qualifiers, eliminators and series deciders
      against ordinary games, shown after 3 such games — ✓ Opponent preview · About them (every knockout and series decider); counted again
      for every player
- [x] **Record by country** (31): their players in the country the match is in — ✓ Opponent preview · About them, with the You are: Home / Away / Neutral picker
- [x] Donut: how their batters get out; batting depth (8, 9) — ✓ Opponent preview · About them (each slice's count
      from the engine; a team without a run now has no share instead of 0%)
- [x] Team badges in the headings and tiles (section 6) — ✓ Opponent preview: the head, India v Australia, each key
      players tile, their records, How they play and danger men; country by country with each host's badge (names line
      up, the bars too); checked with test badges, 0 layout problems at 1280 and 1920

## 3. Team record (Teams)

- [x] Against stronger and weaker sides chart, on Overview (2) — ✓ Teams · Team record · Overview; both ratings
      checked against the rating list for 16 teams in four competitions
- [x] Home, away and neutral chart, then country by country, on Overview (2) — ✓ same tab; every host counted again
- [x] Streaks chart (every match in order, the longest runs marked, the run you're on), on Overview (2) — ✓ same tab
      ("Runs of results"); every match's result and every run checked
- [x] **Every player's contribution** (27): all the team's players, share of the runs (off the bat) and of the
      wickets, one table sorted by clicking a column, under "Who carries the team", with a donut of the runs share
      — ✓ Teams · Overview; every player and run checked against the scorecards, the shares the same as "Who carries
      the team" writes them
- [x] **Big stands** next to Collapses (24) — ✓ Teams · Overview (the ten biggest, * not out); checked against every
      stand counted again
- [x] **The usual-score line** ("usually 48/1, 97/2, 152/3…") with the table (25) — ✓ above the table, with their
      opponents'; the same numbers as the table
- [x] Donut: batting depth (8, 9) — ✓ Teams · Overview, with the average team's shares (now adding up to 100%: a
      team without a run used to count as 0%)
- [x] **Runs off the bat** for every share: "Who carries the team" switches (27); its order stays as it is — ✓ the
      engine's team share (`ccstats/aim.py`, `ccstats/players.py`); the shares now add up to 100%

## 4. Team vs team

- [x] Batting first v chasing chart, under the head-to-head record (2) — ✓ Teams · Team v team, both sides, under
      "Head to head" (their meetings, or each side against anyone); counted again for every competition

## 5. Competitions

- [x] Every team's badge in every table that lists teams: league tables, title race, series (6; section 6) — ✓
      Competitions: the league tables, title race, series list, WTC table, knockout bracket and Team of the series (any
      table can now mark its team columns; names line up whether or not a team has a badge)
- [x] "Most runs / Most wickets in the series" tables on each series (7) — ✓ Competitions · one series (the sums
      moved into the engine, `ccstats/tables.py`); checked against the scorecards for every series
- [x] The series scoreboard ladder (the score after every match, the decider marked) on "match by match" (4, 8) — ✓ Competitions · one series, from your side when you play
      in it, else the winner's; every score checked
- [x] **Team of the series** for every series of 2 or more matches (28) — ✓ Competitions · one series, picked as Team of
      the Season is; each series worked out only when picked (a season's 23 ODI series opened in 12 s before)

## 6. Season

- [x] The agreed twelve month tiles, April to March: every match on its day, each month's record, the best month lit
      up, the "29 Mar" mark for an IPL that starts in March; the "one month" big view kept (3) — ✓ Seasons · Season · calendar: each month's record,
      the best month lit up, the IPL's 29 March start kept whole in its season with a "29 Mar" mark at the top of April
      (its line and record counting it too), one month kept; every game of every season checked to appear once
- [x] The series tug of war on the series tracker (4, G) — ✓ Seasons · Season · Series tracker: every series still going and
      your team's latest finished one, from your side; every score checked
- [x] **"Where your team ranks"** at the top: your rank by runs scored and wickets taken in each format this season,
      from the ranking of every team up to any date (stage 3's sums built now) (9, 12) — ✓ Seasons · Season, at the top (`ccstats/rankings.py`
      team_totals: stage 3's ranking, to any date); counted again by hand for every team of every competition

## 7. Season review

- [x] The match-winners chart, under the MVPs (2) — ✓ Seasons · Season review: your team's (or the side with the most
      wins), each win checked
- [x] The new excitement rating in the best matches (5) — ✓ Season review's best matches and Season wrapped's best game on the
      match excitement rating, with each one's place in the competition; the old site keeps its score
- [x] **Season wrapped:** each format on its own, or the whole April-March season with all formats together (runs and
      wickets added up there); its "best game" on the new rating (5, 23) — ✓ Season review: "This competition" or "The whole season,
      every format" (`ccstats/wrapped.py` whole_season_wrapped: every format added up, impact points game by game);
      counted again by hand; found and fixed: every slide's text was faint and pushed off its left edge (since 12 Nov)

## 8. Rivalries

- [x] **Rivalry streaks:** the current run in each rivalry and the longest ever; draws and ties end a run, no-results
      skipped (32) — ✓ Rivalries: "Run now" and "Longest run" in the
      table, and a Streaks tile for the rivalry picked (`ccstats/extras.py`); the rules checked on made-up runs and every
      rivalry counted again by hand

## 9. Stage 1 pages

- [x] Matches: our score v their score chart on the front page, for the competition and team picked (10) — ✓ Matches, under
      the list: the team's latest 14 there (a Test's innings each on its own line); asks for one competition and a team
- [x] Matches and My team: the competition logo on every scoreboard (the World Test Championship's on every Test,
      World Cup logos only on their games); My team's latest result with both teams and the competition logo (13) — ✓ the match summary, the matches list, the best games, My team's
      results and its latest result (with both teams' badges): the competition's own logo, a Test the game's Test logo
- [x] My team: the series tug of war on "series this season" (12) — ✓ My team, beside "Series this season": the latest series
- [x] Player page: the match-winners chart in place of "Matches they won" (11) — ✓ Players · the player's page (the same wins as before, with what they did)
- [x] Player page: share of the team on runs off the bat (27) — ✓ Players · the player's page, the same sum as Teams
      (checked player by player for every competition and season)
- [x] Player page: **big-match players** (29), **record by country** with neutral games their own row (31),
      **bounce-back** (a duck or under 10, or no wickets for 30+, shown after 3) (33) — ✓ Players · the player's page: big-match record, country by country (neutral grounds
      their own row) and bounce-back, each for the competition picked, counted again in `tests/test_moments.py`

## 10. Every chart

- [x] "Save picture" on each chart, shown when you point at it (14) — ✓ every tile holding a chart (each chart marks
      itself `data-chart`: the drawn charts, the calendars, the ladder, the runs strip, the rings and bar lists): a small
      tab on the tile's top edge when you point at it, clear of the title and its hint; saves the tile as a PNG at twice
      its size, with the page's fonts, colours, badges and notes (`web/src/kit/savepic.ts`, `Tile` in
      `web/src/kit/base.tsx`); checked in `tests/test_web.py` (shown on chart tiles only, clear of the title row, a
      real PNG of the tile at twice its size) and by eye on five saved pictures of the 2032 save
- [x] "What it shows / What it's for" under every new chart (section 5) — ✓ every fix-round chart: the series tug of
      war (My team, Season's series tracker) and ladder (Competitions) in `series_of`, match-winners (My team, Players,
      Season review), our score v theirs (Matches, My team), the season calendar (Season, all three views), and
      Players' "Where the runs come from" (missing since stage 1); written by the server with the numbers, each checked
      another way in `tests/test_pages.py::test_the_new_charts_say_their_numbers_counted_another_way`; a browser scan
      of every page on the 2032 save finds no fix-round chart without them. Season wrapped's slides each say their own
      numbers. My team's stage 1 charts (form, runs of results, home and away, rank, top scorers, the mini calendar)
      have none, as approved in stage 1: brought to you
      - Found and fixed on the way: My team's "Our score v theirs" averaged T20I and ODI totals together (formats
        mixed); averages are now only worked out within one competition, and each competition's own are in the line

## 12. Added 14 November: your preview finds and decisions (details in NEW_SITE_PLAN.md)

Wrong numbers and data:
- [ ] Two playthroughs counted together: leftovers of every kind of match set aside from the game's file times
      (listed on Data check, can be counted back); a team double-booked by the game counts both matches
- [ ] My team's T20I, ODI and Test tiles on the Season tile's April-to-March season, so they add up to it
- [ ] The five scorecards that don't add up: retired hurt reprinted in the 2nd innings counted out to the bowler with
      the extra wicket ("out, how not printed"); SA20 no-balls recorded as not charged to any bowler
- [ ] Scouting fully safe for national sides: never a name capped by another country, never a franchise-only player,
      shared names on sure games only (the 8 unsafe suggestions found on your saves, including Head -> A Sharma)
- [ ] Names: a name playing for two teams in one competition and season split automatically (listed on Data check,
      can be undone); different printed names never merged
- [ ] No fielding anywhere: nothing shown (Fielding tab, catches and stumpings columns, records, Stat by stat,
      Hall of fame pairs, Data check catch list) and nothing counted (marks, impact, MVP points); keepers worked out
      quietly; scorecards and how-out charts kept as printed

Pages and looks:
- [ ] Player page: each tab shows only its own stats (Batting all batting, Bowling all bowling, country by country
      included); an Overview tab for the rest; opens on the player's main job
- [ ] Batting on the left, bowling on the right (the scorecard and everywhere they sit side by side)
- [ ] Competition order everywhere: Tests, ODIs, T20Is, then franchise, then domestic
- [ ] Inner boxes in the page's own colour on every team's light look (no muddy mixes)
- [ ] Team logos about a third bigger in matches and tables; the competition logo on every franchise and domestic
      match's scorecard and summary
- [ ] No blue highlight on double- or triple-click (dragging still selects)
- [ ] Every chart: What it is / Who's best / What it's for, always shown, charts only

Accuracy and keeping it right:
- [ ] The same number on every page; totals built from their parts
- [ ] Every scorecard checks itself (totals, overs, fall of wickets, result and margin), new matches too
- [ ] About ten hand-worked matches and an odd-cases library locked into tests
- [ ] Impossible-value guard; a match saved twice counted once; a "checked ✓" mark on each match
- [ ] Every change tested automatically on Windows with Python 3.14.7 and pandas 3.1

At the end:
- [ ] One clean package for your PC that opens on your new scorecards with one double-click, with what to try
- [ ] One screenshot of each new or reworked thing

Right after this round, the speed work (your words: "when I open it, all the site starts opening"):
- [ ] The moment the site opens it starts getting every page ready in the background (every team, competition,
      season and player), your team and players first, using the whole processor; usable meanwhile, a small progress
      bar, a page not ready yet fills in by itself
- [ ] Everything kept on disk, so it happens once; later starts instant; a new match redoes only what it changes
- [ ] The slow sums fixed at the root; pages appear at once with the last numbers, tiles fill in on their own; pages
      fetched before you click; only what's on screen worked out; logos made once; long lists row by row; pages sent
      squeezed; the browser opens at once on a "starting..." screen; heavy work in its own lane
- [ ] Every page under a second (a speed guard in the tests), every number exactly the same before and after
      (the five accuracy promises), a self-check on new matches, smooth (no jumping, reopens where you left off),
      safety copies before updates

Later stages: the program (.exe) that updates itself, with Streamlit and Plotly removed (stage 5); everything smaller
so more fits (stage 6).

## 11. How it's built and checked (sections 5, 7, 9, 10)

- [ ] The new sums in the engine (`ccstats/`) with tests, and the server page files' existing sums moved there (17)
- [ ] Parity tests: each page's numbers against the old site's page for the same career; any difference that is an
      old-site bug listed for you, not copied (16)
- [ ] Every number of every new piece checked against the scorecards counted another way
- [ ] Accuracy checks picked 14 November: the same number on every page, totals built from their parts; every
      scorecard checks itself (totals, overs, fall of wickets, result and margin), new matches too; about ten
      hand-worked matches locked into tests; the odd-cases library from the owner's scorecards
- [ ] The browser through every page, tab and option, at 1280, 1366, 1440, 1600 and 1920, dark and light (18)
- [ ] The test data (changed 14 November: your old saves, zips and odd saves were deleted from this machine at your
      request; the checks use the new set of scorecards you're sending instead), with the
      project's test scorecards and the generated IPL (19)
- [ ] The stress test, as for stage 2: every page and choice through all of them, fast clicking, every log and
      problems list read, full tests on this machine and on your PC's set-up
- [ ] The plan's "what was built" section: a line for every promise, built, where, and how checked
- [ ] Screenshots of every page and tab for you, then your approval before stage 3
