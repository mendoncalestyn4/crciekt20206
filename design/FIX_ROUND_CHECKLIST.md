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

**Changed 17 November (your rule): none of the four ways to go faster any more** ("keep what's there, from now
don't use any of those 4, do as you did earlier"): no helper copies (all work done by me, one piece after another;
the two helpers' copies are kept untouched, unused); every choice that is yours asked as before; the full test suite
after every piece, not only the pages it touched; the big checks one at a time. Everything already built stays.

Before 17 November, how this round was worked (your choice, 14 November): **fewer stops**: every decision is saved, so the list is worked
through with very few questions, stopping only for a real choice of yours; **faster checks**: every full check runs
side by side on separate test servers, each problem and each slow page written down the moment it's found;
**helper copies working side by side (your choice, 14 November: "limits I don't mind, but it's faster")**: pieces
that don't touch the same pages (e.g. the fielding removal, the chart descriptions, the logos and colours) are done
at the same time by helpers, each in its own copy of the project; I check every helper's work, run every check on it
(every page's numbers before and after, all tests, the full sweep, the Windows tests) and only then combine it;
pieces that share a page are done one after another; **quick checks per piece (the safest of the two, your
question)**: after each piece the pages it touches are checked, the full test suite runs on every change, and the full
every-page sweep runs after each big group of pieces and at the end. The agreed order stays (accuracy checks before
the speed work, so the new safety nets guard the speed changes). Nothing moved to other stages. Pushed after every finished
piece, wrong numbers first.

Wrong numbers and data:
- [x] Two playthroughs counted together: leftovers of every kind of match set aside from the game's file times
      (listed on Data check, can be counted back); a team double-booked by the game counts both matches — ✓ engine
      (`ccstats/loader.py` find_leftovers, play_runs): a rewind is a jump back of more than 10 days in the files'
      saved order (your new set showed the game saving some games up to 3 days ahead, so smaller steps prove
      nothing), backed by a real replay (at least 10 new files, outnumbering the old ones it sets aside); copied files
      in no order and a few older scorecards copied in later set nothing aside; knockouts keep their stricter checks;
      the same team in two matches at once is never a sign. Tests: a made-up two-playthrough folder (every kind of
      match), copied files, copied-in files, a double-booked team, a Test saved late (`tests/test_real_career_cases.py`);
      your new set: 0 set aside (correct: one playthrough)
- [x] My team's T20I, ODI and Test tiles on the Season tile's April-to-March season, so they add up to it — ✓
      `server/myteam.py` banner: each tile counts the calendar's season and says "Apr 2031 – Mar 2032", the
      competitions played this season first; test `test_my_team_format_tiles_add_up_to_the_season_tile`; all 137 teams
      of your new set add up (Australia: Tests 5–1, ODIs 4–2, T20Is 4–0 = the Season tile's 16)
- [x] The five scorecards that don't add up: retired hurt reprinted in the 2nd innings counted out to the bowler with
      the extra wicket ("out, how not printed"); SA20 no-balls recorded as not charged to any bowler — ✓ engine
      (`ccstats/parser.py` _correct; the career's corrections list for the data check page; the match page says
      "✎ Scorecard put right" with what was done); your new set: exactly the five (S Singh to V Manoj, K R'h Reddy to
      P Karia, T Ward to T da Silva, A Vaughan to M Cohen; 2 uncharged no-balls in the SA20), 0 problems left;
      tests on made-up cards of each kind, and that a real retired hurt or an unproven gap is left alone
- [x] Scouting fully safe for national sides: never a name capped by another country, never a franchise-only player,
      shared names on sure games only (the 8 unsafe suggestions found on your saves, including Head -> A Sharma) — ✓
      `ccstats/scouting.py` (national_ok, proving_sections; "shared name" mark on the pick); tests: the A Sharma case
      and each rule, and every player offered to every national side in the test scorecards; your new set: 3,345
      offered, 0 break a rule; gone: Australia T20Is "Replace Z Coates with J Iqbal" (Iqbal only ever played in the
      Big Bash)
- [x] Names: a name playing for two teams in one competition and season split automatically (listed on Data check,
      can be undone); different printed names never merged — ✓ engine (`ccstats/loader.py` auto_splits: the name
      stays with the team it played most for, the others get the team added; undone with "keep together", saved with
      the career; the Player of the Match follows his side); tests in `tests/test_names.py` (split, undo, a transfer
      stays one, no name ever joined); your new set: 63 names split into 163 players, none left shared
- [x] No fielding anywhere: nothing shown (Fielding tab, catches and stumpings columns, records, Stat by stat,
      Hall of fame pairs, Data check catch list) and nothing counted (marks, impact, MVP points); keepers worked out
      quietly; scorecards and how-out charts kept as printed — ✓ the new site's careers count no fielding
      (`ccstats/stats.py` counts_fielding / fielding_credits, used by marks, match impact, MVP and IPL points, the
      report card and the team of the season's lines; `server/site.py` marks every career it opens); shown nowhere:
      the Player page's Fielding tab, its catches and stumpings columns, the "wicketkeeper" label and tag, Teams'
      keepers tile, the fielding parts of MVPs, Season wrapped and danger men, every note that counted catches;
      keepers still found from stumpings for the best XI and scouting. Stat by stat, Hall of fame and the Data check
      page are built without fielding in stages 3 and 4. The old site is left as it is. Tests: every page and tab of
      the test career read for any fielding figure, and marks, impact and MVP checked player by player
      (`tests/test_pages.py`)

Pages and looks:
- [x] Player page: each tab shows only its own stats (Batting all batting, Bowling all bowling, country by country
      included); an Overview tab for the rest; opens on the player's main job — ✓ Overview, Batting, Bowling,
      Story (`server/playerpage.py` tabs and `open`; `web/src/pages/Players.tsx`): the name card on every tab;
      Batting: its totals, last 10 innings, every competition, every format, country by country, big games and
      bounce-back, then everything it had; Bowling the same; Overview: the totals of both, badges, match-winners, share
      of the team, attributes and scout report, marks, career journey; a batter opens on Batting, a bowler on Bowling,
      an all-rounder on the Overview; checked in `tests/test_web.py` (each tab's tiles, K Rabada opens on Bowling)
- [x] Batting on the left, bowling on the right (the scorecard and everywhere they sit side by side) — ✓ the scorecard (`web/src/kit/blocks.tsx`); checked in the browser test
- [x] Player of the match highlighted only where he earned it (found by you: M Beardman's 0 off 1 was shaded in the
      batting card though he won it with 9 wickets, 5/40 and 4/66): his bowling rows shaded when he took wickets, his
      batting row when he made runs, both for an all-rounder; his mark is a small 🏆 (your choice) — ✓ scorecard; browser test: every shaded row is his
- [x] A ★ by the best of every innings (your choice, 14 November): the innings' top run-scorer and its best bowler,
      on every scorecard; ties: more runs, then fewer balls (equal on both: both get one); bowling: most wickets, then
      fewest runs, then fewest balls; an innings where nobody took a wicket: the cheapest bowler who bowled at least a
      fifth of its overs — ✓ `starsOf` in `web/src/kit/blocks.tsx`
- [x] Competition order everywhere: Tests, ODIs, T20Is, then franchise, then domestic — ✓ one order in the
      engine (`ccstats/competitions.py` section_rank / ordered / event_rank) used by every list: the career, every
      picker, Matches, My team and its Scouting tab, every player's page, row and every-format table, search, Season
      review's picker, Season's ranks, Opponent preview's other meetings; test on every page that lists them
- [x] Inner boxes in the page's own colour on every team's light look (no muddy mixes) — ✓ `server/theme.py`
      (tile2 = the page colour, set apart by the thin edge); all 30 light looks checked: the edge still shows
- [x] Team logos about a third bigger in matches and tables; the competition logo on every franchise and domestic
      match's scorecard and summary — ✓ every size moved to the agreed one (tables 36, match lists 40, bracket
      26, summary and innings headers 44-52); the competition logo on the summary and now the scorecard; every
      franchise and domestic competition of your new set has its logo when the game has the picture (checked with a
      stand-in set of the game's files; "Asia Trophy" has none known)
- [x] No blue highlight on double- or triple-click (dragging still selects) — ✓ `web/src/main.tsx`; browser
      test: double and triple clicks select nothing, a single press is never blocked, typing boxes untouched
- [x] The match report gives each innings its own figures (found by you: Pakistan v South Africa, 11 Jun 2031, said
      "N Shah took 7/158" for South Africa's 1st innings, where he took 6/74; 7/158 is his match figure); match
      figures only when said as such ("7/158 in the match") — ✓ `ccstats/winprob.py` match_report: the best
      spell of the match, said after its innings, with the innings named and match figures "in the match"; your
      example now: "M Ismail took 7/71 for Pakistan in South Africa's 2nd innings (7/198 in the match)"; test checks
      every report's figures against the spells
- [x] The excitement rating (your choices, 14 November): the tile renamed "Excitement rating · out of 10"; each part
      shown out of 10 (the finish, a comeback, the stakes, big moments: for Pakistan v South Africa 11 Jun 2031,
      10, 1.5, 10 and 10), the overall unchanged (8.8), with one line saying the finish counts most; the same on
      every page that shows the parts — ✓ `web/src/kit/match.tsx` (the only place the parts show)
- [x] Players · Find a player (found by you, 14 November, searching "smith"): the names squeezed into a column a
      letter or two wide ("J / S / MI / TH"); the name gets its own column and never breaks inside a word; the
      browser fit check now types a search before checking (it missed this) — ✓ the cause: a team without a
      logo let the name slide into the logo's column; the logo now has a fixed slot, the name a column as wide as its
      longest word; browser test types a search at 1280 and 1920
- [x] The competitions listed on each player row in the agreed order (J Smith showed "ODI, Test, T20I") — ✓
- [x] Readable short competition names everywhere (C Smith showed "COCD1, C4SD1" for the CSA One-Day Cup Division 1
      and the CSA 4-Day Series Division 1): e.g. "CSA One-Day D1", "CSA 4-Day D1"; checked for every competition — ✓ `web/src/format.ts` fmtOf: a readable short name for every competition in the game, "· Division N" as
      " DN", anything unknown keeps its full name
- [ ] Every match mentioned anywhere opens its match page when clicked (found by you, 14 November: the Player page's
      Match-winners list, "Test v ENG · 31 Jul ..." wasn't clickable); checked on every page that names a match:
      lists, sentences, charts, inbox, records
- [x] Player page, Country by country (found by you, 14 November: showed only Tests): format buttons on the tile
      itself (Tests, ODIs, T20Is, then the franchise and domestic competitions he played, agreed order, only ones he
      played), opening on the page's competition; the same for Big-match player and Bounce-back; formats never mixed — ✓ tick boxes on each of the three tiles (your later decision: tick any formats, counted together), opening
      on the page's competition (`/api/player_part`); test
- [x] Combine formats with tick boxes (your decision, 14 November: "tick any formats", "in all buttons where these
      formats are mentioned"): every format choice becomes tick boxes (Tests, ODIs, T20Is, each league), opening on one
      format; ticking more combines them (e.g. Tests + ODIs); "v the average" uses each format's own average, combined
      fairly. Where it can: the Player page and its tiles, Leaders, Stat by stat, records, team records, Team vs team,
      Rivalries, the match finder, Compare players, Player stories, Hall of fame. One at a time where combining has no
      meaning: points tables, title race, brackets, WTC, team ratings (Elo), score to aim for, season calendar views
      Your answers (17 November), for stages 1-2:
      - Player page: everything combined for the ticked formats; "v the average" (where they rank among everyone,
        runs above average) uses each format's own average, weighted by their innings in each. Pieces that only mean
        one format (rank over time, rating, marks, attributes and scout report) show each ticked format on its own.
      - Parts that only make sense in one length of game (innings by innings, the 50+/30+ bar, came in under
        pressure, and the like), when formats of different lengths are ticked: one block per ticked format.
      - Tick boxes on Teams, Team v team, Rivalries and the match finder too; parts where combining means nothing
        (league race, team ratings, points tables) show one competition at a time, with a short note.
      - Every competition can be ticked (Tests, ODIs, T20Is, every league and domestic competition), in the agreed
        order.
      - Seasons with several formats ticked: April-to-March years, as on My team (a league or tournament counts whole in
        the season most of it is played in).
      - The ticks carry over: open another player or team and your ticks follow (where they played those formats).
      ✓ Built for stages 1-2 (18 November):
      - Player page (`server/playerpage.py` `_several`): tick boxes at the top; the totals, form, seasons (April-to-March
        years), how they get out, every split, nemesis, bunnies, quality of wickets, impact, badges, firsts and odd ones
        counted together. Where they rank among everyone: each format's own rank, weighted by their innings in it;
        runs above average: each format's against its own average, added. Danger zones and conversion: put together
        fairly when the formats are one length (their share from all their innings; everyone's share each format's own,
        weighted by their innings), one block per format when they differ. One block per format always: batting
        positions, innings by innings, attributes and the scout report, rank over time, compare two seasons; and when
        the lengths differ: came in under pressure, consistency, streaks, over a match, with and without wickets,
        milestones, when they fire. Country by country, Big-match and Bounce-back open on the page's ticks.
      - Teams (`server/teampage.py`): every tab counts the ticked competitions together; against the average team, how
        they play and batting depth use each competition's own average team, weighted by the team's games in it; the
        league race stays one competition at a time (its own picker).
      - Team v team (`server/tvtpage.py`): counted together; runs above average and runs saved each against its own
        competition's average, added; the dashed lines are each competition's own rate, weighted by the balls the two
        sides faced (or bowled) in it.
      - Rivalries and the match finder: counted together ("Tick every competition" on the finder); our score v theirs
        keeps each competition's averages and highest total apart; the best games keep each match's rank within its own
        competition.
      - Ticks carry over (the site remembers them, keeping only the formats the next player or team played); a tick for
        a format they never played is dropped.
      - Checked: on your new set (T Farley: Tests + ODIs = 85 + 71 innings, 4,880 + 2,534 runs; Australia: 65 + 86 = 151
        matches; every tab with no part failing, no page errors); tests/test_format_ticks.py (9 tests: totals add up,
        April-to-March seasons, ticks dropped, one block per format, the weighted ranks and danger bands counted again,
        Teams v the average counted again, Team v team runs above average added format by format, Rivalries, the finder
        and best games) and the browser test test_ticking_a_second_format_counts_both_on_the_player_page.
- [x] Both team logos on every match summary (found by you: Pakistan v South Africa, 11 Jun 2031, showed empty gaps
      where they go); checked on every summary — ✓ the gap was a team the game has no picture for: the summary
      now shows a round badge with its short name there
- [x] Every chart: What it is / Who's best / What it's for, always shown, charts only — ✓ written by the server for
      every chart: the Player page (tests/test_chart_lines_players.py); My team (season ring, form in each format, runs
      of results, our score v theirs, home and away, the series score, match-winners, where you rank, top run-scorers
      and wicket-takers); Matches (our score v theirs, excitement, win chance, wicket by wicket); Opponent preview
      (batters and bowlers in form, weak spot, how their batters get out, where their runs come from, batting first or
      chasing, home and away); Teams (against the average team, runs of results, stronger and weaker sides, home and
      away, top run-scorers and wicket-takers, batting depth, stands, every player's contribution, how they play,
      discipline, the league race); Team v team (tale of the tape, batting first, both dot charts, runs above average,
      runs saved); Competitions (title race, series ladder); Season (calendar, series score); Season review (most
      valuable players, match-winners). Rivalries, Honours and the Planner show tables only, which keep their notes.
      Checked on your new set (63 charts, none without its lines) and in tests/test_chart_lines_pages.py, with
      "Who's best" counted again from the scorecards (top run-scorers and wicket-takers, highest totals, the season's
      record, the biggest stand from the fall of wickets)

Accuracy and keeping it right:
- [x] The same number on every page; totals built from their parts: tests/test_same_number.py takes one figure from
      every page that shows it (a player's runs and wickets on the top numbers, the every-competition table and the
      season-by-season table; a team's top run-scorers and every player's contribution, which add up to the team's
      runs; a team's games and wins on its record, its results, Rivalries and the points table; a match's top scores
      and its scorecard)
- [x] Every scorecard checks itself (totals, overs, fall of wickets, result and margin), new matches too: every card is
      checked as it's read (ccstats/parser.py validate_match), so a new match is too; 0 problems on the 71 test cards
      and your 2,720 new ones. On the way, a real bug: an innings win ("won by an innings and 102 runs") lost its margin
      when read, so the innings-win check never ran and the Competitions page said "an innings and null runs"; fixed,
      the 37 innings wins in your set now read and check out, and innings wins are never listed as wins by runs
- [x] About ten hand-worked matches and an odd-cases library locked into tests: tests/test_hand_worked.py (11 cards,
      every number added up by hand) and tests/test_odd_cases.py
- [x] Impossible-value guard; a match saved twice counted once; a "checked ✓" mark on each match: below 0, more than 6
      a ball, more than 10 wickets, maidens or dots past the balls, a bowler past his overs (tests/test_self_checks.py);
      the same card twice counted once (tests/test_loader.py); ✓ or ⚠ on every match in Find a match and on its page
- [ ] Every change tested automatically on Windows with Python 3.14.7 and pandas 3.1: set up (GitHub Actions); ticked
      when its first run passes
- [x] Reliability (your picks, 14 November): a second, separate counter for every main figure (runs, wickets,
      averages, strike rates, economy, records), compared after every change; "how it's worked out" on every number
      (point at it: "845 runs ÷ 21 dismissals in 23 innings = 40.2"); the same "few games: treat with care" note on
      every figure resting on very few games. Second counter: tests/test_second_counter.py (0 differences on the test
      cards and on your 2,720). How it's worked out: the Player page's top numbers and tables, Teams' win %, and every
      average, strike rate and economy in every table on every page (made from the numbers in its own row, so it always
      matches the screen), each with the few-games note under 5 innings
- [x] Reading and showing (your picks, 14 November): every scorecard read back (written out again from what the site
      understood and compared line by line with the original; any difference flagged), with an alarm for any
      unfamiliar line or rare dismissal (hit wicket, obstructing, timed out, retired out, absent hurt, handled the
      ball, each tested); shortened names ("c K'r Singh") must match exactly one player in the match or are flagged;
      a browser test reads every number off every page and checks it against the site's own figures; one name and
      unit per stat everywhere, "–" for doesn't apply and 0 for zero, checked on every page.
      Read back: tests/test_read_back.py, 0 differences on your 2,720. Shortened names: "L'-Cachet" now matches
      Z Lion-Cachet; two bowlers printed with the same name share their wickets; when the card can't say which of two
      bowlers took a wicket (1,255 wickets in 253 of your matches, e.g. "b Jansen" with D and M Jansen both bowling),
      both are named and the match page says so, and a name matching no one is flagged. Screen = numbers:
      tests/test_web.py reads the Player page's top numbers and table, a team's record and a scorecard off the screen.
      One name per stat: every table heading uses one short name (Mat, Inns, NO, Runs, HS, Avg, BF, SR, 100, 50, Wkts,
      Econ...; a dozen headings that said Games, Matches, Average, Economy, Wickets, Innings, 100s, Bowl avg or Balls
      changed), the full words in the big tiles and charts, and hovering any short heading says what it means; a
      browser test opens every page and tab and fails on another name, a "NaN", "null" or "undefined", an average shown
      with no one out or a bowling average with no wickets (those are "–"), or a count that isn't a number where they
      batted

Zero errors (your approval, 14 November):
- [ ] Working faster never means checking less (your words, 14 November: "ensure this still does the work well and
      finds bugs and fixes them"): no check is skipped or cut short to save time, however slow; every helper's work is
      read line by line by me before it goes in; a piece isn't finished until its own checks pass, and the round isn't
      finished until the full sweep passes with nothing left over
- [ ] Every error found, by my checks or by you in the preview, fixed at its root (never patched over), each with a
      test that recreates it so it can't come back
- [ ] The full sweep at the end of this round and of every stage: every page and option on your scorecards (each
      problem and each page over 20 seconds written down the moment it's found, each server's error log read at the
      end), junk and load, the browser at every width in dark and light, every number checked another way; a round
      or stage isn't finished while anything fails
- [ ] Every change tested automatically on Windows with your Python and pandas; the self-checks on every new match keep
      running in the finished site

At the end:
- [ ] One clean package for your PC that opens on your new scorecards with one double-click, with what to try
- [ ] One screenshot of each new or reworked thing

Right after this round, the speed work (your words: "when I open it, all the site starts opening"). Done 19 November;
every number checked the same before and after (92 pages of your career, 0 differences, three times: after the root
fixes, after a restart, and on the final code):
- [x] The moment the site opens it starts getting every page ready in the background (every page as it first opens,
      every player), your team and players first, then every page, then everyone else; helpers on the processor's
      other cores (every core but one, at most three, at low priority); usable meanwhile (it waits whenever you open a
      page); a small "Getting ready" bar in the menu. Your 2,720 cards: every page ready in about 10 minutes from a
      cold start (server/app.py warm, server/warmers.py)
- [x] Everything kept on disk, so it happens once; later starts instant: the server is up in about a second, the first
      page about 1 s, then every page about 0.02 s (My team 18 s before). Each card's reading and each innings' stands
      are kept under their own inputs, so a new match reads only its own card; the career has a ready-to-read copy
      (start 8.2 s -> 0.08 s). Not built: finished seasons locked, so a new match still makes the pages' answers be
      worked out again in the background (about 10 minutes for every page, your team's first; a page you open meanwhile
      is worked out at once). A new match shows on the site in about 6 seconds (was 8.5-20)
- [x] The slow sums fixed at the root (every innings and spell built once for the career, not looked up row by row;
      role labels once for the same matches; scouting countries in one pass; the stands solver looking only at the
      batters at the crease; shared-name splits looked up, not scanned); pages sent squeezed; logos kept by the browser
      until they change. Not built: pages shown at once with the last numbers before the fresh answer, pages fetched
      before you click, long lists drawn row by row, a "starting..." screen (each page now answers in about 0.02 s
      once ready, so these would add little)
- [x] Every page under a second once ready (a speed guard in tests/test_speed.py); every number exactly the same:
      (1) before and after on your career, 0 differences; (2) everything kept is stamped with the exact scorecards,
      Data check choices, the matches as the site sees them and the site's version, and a test shows a changed card or
      choice is never given old answers; (3) matches added in batches give exactly what a full redo gives (a test);
      (4) not needed (no old view is shown); (5) the full test suite and the Windows run pass on the faster site.
      The self-checks still run on every new match; safety copies are the weekly backups as before
- [x] The folder is checked every 2 seconds (was 20)

Later stages: the program (.exe) that updates itself, with Streamlit and Plotly removed (stage 5); everything smaller
so more fits (stage 6).

## Checks on your new scorecards: finished 14 November (2,720 matches, playing as Australia)

**0 errors anywhere.** Every number recomputed another way: 0 problems. The browser at 1280 and 1920, dark and
light, 70 pages: no layout or error problems. Every stage 1 page: 19,101 (every player in every competition and two
seasons, all 2,720 match pages, the match finder, best games, My team and Scouting for all 137 teams): 0 problems.
Every stage 2 page and option: 11,946 (Teams 5,554, Team v team 1,748, Opponent preview 1,033, Planner 1,595,
Rivalries 710, Competitions 111, Season 464, Season review and Honours 731): 0 problems. Junk and load: 8,800 (7,603
player pages, the finder for 25 competitions and 476 lists, search for all 2,242 players, 137 teams and every
competition, 32 kinds of junk in 12 places): 0 problems.

**Slow pages (40 over 20 seconds, all the first time a page was worked out, under the load of three checks at once):**
player pages 25-74 s, the 2026 Syed Mushtaq Ali Trophy 56 s, the 2028 T20 World Cup 26 s, My team for India with a
junk competition name in the address 25-55 s. **On a quiet fresh server (the before-numbers for the speed work):**
start 2.9 s; My team 18.3 s first time, 0.13 s after; a player (S Smith) 13.5 s, then 0.01 s; a match 15.1 s, then
0.5 s; Players 3.5 s; Opponent preview 1.9 s; Teams 1.6 s; Season review 1.2 s; everything else under 1 s; My team
with a junk competition name 6.2 s once, 0.03 s after.

**Found, for the fix round:**
- [ ] A junk or unknown competition name in an address is treated as the normal page straight away (today each new
      junk name is worked out from scratch once: 6 s quiet, up to 55 s under load)
- [ ] The server writes its errors to its log, so later checks can read them (today the log holds only the start-up
      lines; the checks rely on the error answers, which were all clean)
- The first-time slowness above is the speed work's job (its before-numbers are these)

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
