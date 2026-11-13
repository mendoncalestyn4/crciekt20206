# Audit of stages 0, 1 and 2 against the plan (13 November)

Asked for on 13 November: "do one again very very deeply audit of the 3 stages done, find more things you didn't add,
make them into a new file; I'll tell you later to do it". Nothing here has been fixed yet. Each point says what the
plan (`NEW_SITE_PLAN.md`) agreed, what the site does now, and which stage it belongs to.

How it was checked:
- **The plan, section by section** (1 to 16), every promise for stages 0, 1 and 2 looked up in the site's code and on
  the running site.
- **The nothing-lost checklist** (`design/INVENTORY.md`): every open line for the stage 2 pages, stage 1's lines
  marked "stage 2", and the shared parts (charts, team of the XI, logos, search, colours, the menu, saved data). Each
  line was matched against everything the new site says: its code, plus a crawl of every stage 1 and 2 page, tab and
  option on the checklist's own test career (6,922 answers, 27,760 pieces of text, 466 table columns). The 198 lines
  that didn't match were read by hand.
- **Shown, not just worked out:** every piece of information the server sends for these pages (452) was checked to
  be read by the pages: none is left unshown.

---

## A. Built differently from the plan, or not built (to put right)

### Stage 2
1. **The score to aim for** (section 14) was built another way. Agreed: how fast the chance of winning rises with
   the total is learned from all cricket of the same length (T20Is with the IPL, the Blast and the Hundred), while
   each competition keeps its own totals; home is worth some runs, starting near nothing and growing only as games
   show it; how well that team bats and how well you bowl, in runs above or below the usual total, pulled towards
   usual until there are enough games (5 games count half); every target says how many games it rests on, with a
   "few games, treat with care" note, and the page shows how often it would have called your past games right;
   **Tests** show the first-innings totals that won, drew and lost against that team, home and away; and **My team's
   "next up" tile shows the same line**. Built: each competition on its own, with the two sides' ratings (Elo),
   needing 30 games, no "how sure", "not for multi-day cricket" for Tests, nothing on My team. (The plan also notes a
   version like the one built did worse in all four checks on 25 October.)
2. **The six new charts aren't on the pages picked for them** (section 14, "the six new charts, and where each goes").
   Each is built and on the style guide:
   - batting first v chasing: **Opponent preview, Team vs team**;
   - against stronger and weaker sides (by the ratings just before each match): **Teams**;
   - home, away and neutral, then country by country: **Teams, Opponent preview**;
   - streaks (every match in order, the longest runs marked, the run you're on): **Teams**;
   - match-winners (who won your wins, and what they did each time): **Season review**.
3. **The season calendar** (section 14, "chart changes picked"): agreed as twelve month tiles, April to March, every
   match on its day, **each month's record, the best month lit up**, and a small **"29 Mar" mark** when the IPL starts
   in March. Built: month grids without the month records, the best month or the mark (the agreed tiles are on the
   style guide, not on the page).
4. **The series score** (section 14): a **tug of war on the main pages** (above the line you lead, below it they do)
   and the **scoreboard ladder** (the score after every match, the decider marked) **in the analysis**. Built and on
   the style guide; on no page (the Season page's series tracker and Competitions' series show tables only).
5. **The new match excitement rating** (section 14, "where (picked)"): Season review's best matches and Season
   wrapped's "best game" slide use the current site's old score, not the new rating Matches uses (a 1-wicket win is 7
   or more on the new one; Season wrapped shows 6.1 for one).
6. **Logos in the tables** (section 6, "where logos appear"): Competitions should show **every team's badge in the
   tables**; the league tables, series tables and title race tables show names only. "Series pages" are also named
   among the new places for logos; Competitions' series show none.
7. **"Most runs / Most wickets in the series" tables** (section 2.3, Broadcast's pieces): built and on the style guide,
   on no page; Competitions' "one series, match by match" is where a series is shown.
8. **Donuts where something is a share of a whole** (sections 1, 2.3 and 9.4): none of the stage 2 pages uses one.
   Shares shown as bars or tables include batting depth (share of the runs by batting order), who carries the team,
   how their batters get out (share of dismissals) and the series' share of results.
9. **"Where your team ranks" tile on Seasons** (section 14, "teams ranked by runs and wickets"): the plan puts it in
   stage 2, from the stage 3 ranking. It was moved to stage 3 without a clear yes from you.

### Stage 1
10. **Our score v their score** chart (one line per match, a Test's innings each on its own line): agreed for
    **Matches** and My team; it's only on My team.
11. **Match-winners** chart: agreed for **Players** (stage 1); the Player page has a "Matches they won" table instead.
12. **The series score** (point 4) belongs on My team's "series this season" too (a main page).
13. **The competition logo on scoreboards** (section 6): "the World Test Championship logo appears on every Test;
    World Cup logos appear only on their own games", and **My team's latest result shows both teams plus the
    competition logo**. Match pages and My team show the team badges only; the only competition logo on the site is
    in Competitions' heading.

### Stages 0 to 2 (every page)
14. **Save any chart as a picture** (section 5, "Charts and tables", a hard-gate line): no chart has it. The current
    site lets every chart be saved.

---

## B. The plan's own way of building a page wasn't followed

15. **The nothing-lost checklist wasn't ticked for stage 2** (section 5 makes it a hard gate; section 9 step 1). Open
    lines: Teams 343, Opponent preview 262, Team vs team 115, Team planner 117, Season review 110, Competitions 106,
    Season 73, Rivalries 52, Honours 44, plus the 10 lines stage 1 left for stage 2 and the shared parts (charts 238,
    the menu 99, team of the XI 7, logos 14, search 4, colours 11, saved data 29). **What the audit found:** the old
    pages' content is on the new ones (often reworded); the lines that didn't match are the old site's internal
    names for its controls, chart settings, numbers that change with the career, and things for stage 4 (the logos
    folder box, the first-start question, your-teams picker, saved files). So the work is ticking each line with
    where it is now, not rebuilding, but it has to be done before stage 2 can be called finished.
16. **Parity tests** (section 9 step 3; section 10): "the new server's numbers must equal the old site's numbers".
    Stages 1 and 2 test the new pages against the engine, not against the old site's pages, and some old pages hold
    sums of their own (fixed on both sites in one case: the title race's favourite on an empty day).
17. **Sums kept in the engine** (section 7: "anything that works out a number or makes a decision moves into the
    engine, with tests"): some sit in the server's page files instead (the Player page's most, the Teams page's,
    Team vs team's, Competitions' and Season's a few each).
18. **The browser test of every option** (section 9 step 5; section 10): the server was asked for every section,
    season, team and option (the stress test), but the browser opened the main pages and a sample of options, not
    every one; its widths were 1280, 1366, 1440 and 1920, while stage 0's fit rule names 1280, 1366, 1440, 1600 and
    1920.
19. **The test data the plan names** (section 10): the 940 generated scorecards (the made-up IPL) and the 477-match
    test career weren't run through the stage 1 and 2 pages; the checks used your 2029 and 2032 saves, your new
    career's seasons, the odd saves and the project's test scorecards.
20. **Screenshots of every page in the stage** (section 8): stage 2's set has each page once, as it opens, not its
    tabs and options.

---

## C. Asked to bring back to you, and not yet done

21. **The parked ideas** (section 1, "to ask about again after stage 1 or 2"): player cards with an overall rating
    per format (EA FC style); Team of the series and Team of the season; board confidence (results against what the
    ratings expected) and season awards. Not asked yet.
22. **To-dos B to E** (section 1) wait for your "build it", each with a question: B, if no scorecard has a follow-on,
    make one up or skip that case; C, where the "does it add up" warnings go (a note on the match page, a list in
    Settings, an alert for a new match); D, none; E, Python's own file format (my pick) or the pyarrow package.

## D. Questions this audit raises (yours to decide)

23. **Season wrapped: one format, or the whole year?** The plan's example ("your 2026: 22 matches, won 12, lost 10; S
    Gill 830 runs; A Singh 34 wickets…") reads like all of a team's cricket in a year together, while your rule is that
    formats are never mixed. Built: one format at a time. **Your answer (13 November): the team's whole year**
    (all its cricket in the year together, as the plan's example), a chosen exception to "never mixed" for Season
    wrapped only.
24. **"Collapses: also big stands"** (section 14's table): on Teams next to the collapses, or only as "the best stand
    for each wicket" on Records (stage 3), as point 3 of "wickets and scores" says? **Your answer (13 November): do it:**
    a "Big stands" list on Team record next to Collapses (the team's biggest partnerships in that competition and
    season), as well as the best stand for each wicket on Records in stage 3.
25. **Usual score at each wicket:** the plan's example is a line ("in ODIs India are usually 48/1, 97/2, 152/3…");
    built as a table (wicket, usual, opponents', difference, highest, lowest, innings). Keep the table, add the line,
    or both? **Your answer (13 November): both.**

---

## E. Checked and as agreed (so you know what was covered)

- Stage 0: the server, careers and folder watching every 20 seconds; live news of new matches, unreadable files and
  "New record!" alerts; your colours for all 31 nations and the dark look; logos by the approved code, with the broken
  picture check in the browser test; the chart kit and style guide; search with Ctrl K; the preview launcher; only
  your own computer can reach the server.
- Stage 1: My team, Inbox, Players and Matches as listed in section 15; their checklist lines ticked; a player's share
  of the team for each competition and season; wicket by wicket with the par line and its note about late wickets;
  the new excitement rating on Matches; teams with no games yet offered on My team; the form line.
- Stage 2: every page in section 4's Teams and "Competitions and seasons" rows exists with the current pages' parts;
  "What it shows / What it's for" under every chart on the stage 2 pages; teams with no games yet marked "(0 games)"
  on Teams and Team vs team and offered on Opponent preview; who carries the team and the usual score at each wicket
  (numbers checked by hand in tests); collapses; the best stands counted with unbroken stands; Season wrapped's slides
  (plus the best game, as section 14 asks); the stage 2 stress test's fixes.

---

## F. Added on 13 November (your request), for the stage 2 fix round

26. **Opponent preview: "How they play", an overview of the opponent** (to be built in the stage 2 fix round, once
    you say go). The scorecards hold no overs (no over a wicket fell in, no runs per over), so it reads the game
    through the score at each wicket, the batting order, each batter's runs, balls, fours and sixes, and the order
    the bowlers came on:
    - **Bowling:** when they take wickets (the usual score at their 1st, 2nd and 3rd wicket against the usual
      here); how often they have a side 3 down cheaply and how often they bowl sides out; the new-ball bowlers'
      share of the wickets against those who come on later; the share of their wickets that are top-order batters;
      attack or squeeze (wicket-taking against runs given, and dot balls in T20 where the cards print them).
    - **Batting:** strike rate and boundary share for the openers, the top order, the middle order and the lower
      order against the usual ("blast from the start", or "build, then blast"); how much comes in fours and sixes,
      and from where; their usual score at each wicket against the usual here (fast start and fade, or slow start
      and strong finish).
    - A short summary in plain words at the top.
    Open questions (asked 13 November): where on the page (my pick: the top of the "About them" tab); against the
    usual for that competition or that format (my pick: competition); whole career or recent seasons (my pick: whole
    career with a "this season" switch); them only, or your team beside them (my pick: them only).
