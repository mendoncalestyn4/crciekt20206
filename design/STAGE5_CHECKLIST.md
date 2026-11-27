# Stage 5 checklist (made before building, 26 November)

Every promise the plan makes for stage 5 (`NEW_SITE_PLAN.md` section 8's row, sections 3, 5, 6, 10, 20 and 21). Each
line is ticked at the end with where it is and how it was checked. Nothing is built until stage 4 is signed off and
the owner says go. Questions for every new piece are asked in one sitting first (the speed-up of 26 November).

## A. The program (section 8, section 20)
- [x] "Cricket Captain Stats Pack.exe" in a folder with its parts (no Python, no install, no black window), built on
      GitHub's Windows machines — ✓ .github/workflows/program.yml (desktop/, tools/build_program.py); every build is
      started once there and must answer with its pages (`--check`); builds 1, 11 and 12 passed
- [x] The owner's icon (full design at big sizes, ball and bat alone at small ones), once approved — ✓ approved 26
      November; tools/make_icon.py makes the .ico (16–48 the small design, 64–256 the full one) and the site's favicon
- [ ] Its own app window (no address bar or tabs; closing it closes the program)
- [ ] Only one copy runs (opening it again brings the open window forward)
- [ ] Stops by itself a minute after the last Stats Pack window or tab closes
- [ ] A clear message window if it can't start (what happened, what to do)
- [x] Updates from GitHub — **changed 27 November:** the project itself went public (your "go public"), so the
      updates are its own releases (no second repository or key needed): the Windows build publishes a version when
      asked; desktop/updates.py reads the newest release. tests/test_program.py; the real update on Windows:
      tools/update_check.py (see the deep test)
- [x] "Update ready: what's new" with an Update button; one click backs up every career, updates, reopens on the same
      page — ✓ the bar on every page (web shell/Program.tsx), tests/test_web_program.py; the backup and reopen on
      Windows by tools/update_check.py
- [x] Safe updates: each download checked complete and unchanged before it's installed; else the version you have
      stays and it tries again later — ✓ size, fingerprint and a whole zip checked first (desktop/updates.py); a failed
      swap puts the old folder back; tests/test_program.py
- [x] "What's new" in plain words after each update: only in Settings, with a small "Updated" mark in the menu — ✓
      Settings · What's new (design/WHATS_NEW.json), the "new" mark until seen; tests/test_web_program.py
- [x] The guided tour on first start: every section (all ten menu items and the search bar), Next and Skip; "Show me around again" in Settings
      — ✓ 11 steps, each tip inside the window; tests/test_web_program.py
- [ ] Your data stays where it is (Documents\Cricket Captain Stats Pack); existing careers open with nothing to convert
- [ ] The site reopens where you left off (your choice of 14 November)
- [ ] Windows may warn "unknown publisher" once (not signed): said in the README

## B. New on the site (section 21)
- [x] 1. Opponent preview: your in-form players and the records your players could break in that match — ✓ Teams ·
      Opponent preview (the 3 most in-form a side, every record within reach); tests/test_stage5_pieces.py
- [x] 2. Who's fading: beside Breakout players, your players clearly dropping season on season, each with a suggested
      replacement from the scouting list — ✓ Insights · Breakout players; tests/test_stage5_pieces.py
- [x] 3. Then and now: your team now against itself 1, 3 or 5 seasons ago — ✓ Teams · Then and now (any team, each
      ticked competition); counted again by hand (tests/test_stage5_pieces.py) and against the team's results
      (tests/test_same_number.py); browser: tests/test_web_stage5.py
- [x] 4. Selection review (My team): dropped after a good score, kept through a poor run, how often the side changes —
      ✓ My team · Selection; made cases and hand counts (tests/test_stage5_pieces.py)
- [x] 5. Records within reach (My team): career and all-time team records your players could break soon — ✓ My team
      (and the opponent preview); hand check and same-number check
- [x] 6. Stat by stat: against one chosen opponent; by result (wins, defeats, chasing only) — ✓ Leaders · Stat by stat,
      "Against" (any number of opponents, tick boxes) and "Result"; counted again by hand
- [x] 8. Partnership breakers: bowlers who end stands of 50 and more, in Player stories and on Stat by stat, a line on each bowler's Player page
      — ✓ all three; every broken stand checked against the fall of wickets; the same number on all three pages
- [x] 9. Player form alerts: a hot streak or a slump, beside the team streak alerts — ✓ ccstats/alerts.py (each said
      once); real and made streaks checked
- [x] 10. Career arc: the usual development over a player's 1st, 2nd, 3rd seasons and on, each of your players against it
      — ✓ Insights · Career arc and a line on each Player page (Story); the curve worked by hand, each player recounted
- [x] 11. Your eras: the strongest stretches by the ratings, named, with their key players and results — ✓ Teams · Eras
      (any team) and the current era on My team; ranks from the ratings, results recounted
- [x] 12. On this day (My team) — ✓ only on a day with something (exact day and month, earlier years); tests on exact
      dates and the day either side; browser: shown for a team with a match that day, hidden for one without
- [x] 14. Data check · Scorecards: cards put right aren't listed (tab "Scorecards ✓"); a card the scorecard can't settle
      is put right by the closest fair guess by itself (uncharged no-balls or wides shared between the bowlers by overs
      bowled), with a quiet note on that match's page; only a file that isn't a scorecard is named — ✓ ccstats/parser.py
      fair_fix (runs, balls and wickets gaps; extras), the note on the match page, Data check; tests/test_stage5_pieces.py
      and tests/test_mistakes.py
- [ ] Every new piece works for every team and competition (national, franchise, domestic), follows the format tick
      boxes, has its "What it is / Who's best / What it's for" lines, no fielding anywhere, competition order kept

## C. Accuracy checks kept for good (section 21, item 16)
- [x] A frozen copy of every number on every page of the test careers — ✓ tests/test_frozen.py (114 page answers, 16
      seconds; tools/freeze.py; reasons in tests/frozen/CHANGES.md); it already found two lists ordered differently on
      Windows (fixed)
- [x] The second, separately written scorecard reader on every test scorecard — ✓ tests/test_second_counter.py (every
      test scorecard folder)
- [x] The same number on every page (new pages included) — ✓ tests/test_same_number.py: stands broken (three pages),
      records within reach, then and now and eras added
- [x] One match at a time equals all at once — ✓ tests/test_one_at_a_time.py (as played every run; reversed weekly)
- [x] Test scorecards with deliberate mistakes, every one caught — ✓ tests/test_mistakes.py: 9 kinds on every test
      scorecard, all caught
- [ ] The nothing-lost crawl, automatic
- [x] A weekly full run on GitHub even with no change — ✓ every Monday (tests.yml), with the heavy checks (WEEKLY=1)
- [ ] A normal test run takes no longer than before (timed before and after)
- [x] The 20-season made-up career (about 15,000 matches) in the checks (item 7) — ✓ tests/longcareer.py: 12,760
      matches of 14 competitions (every format), players debut, peak and retire; weekly: every card reads cleanly, the
      same number everywhere, every page answers in good time (tests/test_long_career.py). It found one thing: a
      batter who never bowled and a new wicket-taker with a near-same name were joined as one; fixed

## D. The switch-over (sections 3, 5, 8)
- [ ] The nothing-lost crawl on the new site: every line of `design/INVENTORY.md` found or marked with the owner's yes
- [ ] Every number against the old site on the owner's new save (deep test, check 3), before anything is deleted
- [ ] Engine checks inside the old site's tests moved to other test files first
- [ ] Deleted: `app.py`, `views/`, `ui/`, both `.bat` launchers, the preview launcher, the tests that only check the old
      site, `.streamlit/`
- [ ] Install list: Streamlit, Plotly and openpyxl off; Pillow listed by name
- [ ] README rewritten for the program (and ROADMAP updated)

## E. The stop for your new scorecards and the deep test (section 21, item 15)
- [ ] Work stops when building is finished; the owner is told
- [ ] Every page, tab, choice and chart for every team and competition in the new save; every new piece, Data check,
      Fixtures, the program (opening, updates, the tour)
- [ ] The 13 checks: second reader on 30 matches; same number everywhere; against the old site; one at a time equals
      all at once; a season replayed live; restart and restore; every Data check change undone; messy files; an update
      from today's version; a run of several hours; every layout at every width, dark and light, every team colour; a
      cricket-sense read-through; the program installed fresh on GitHub's Windows machine
- [ ] Every problem fixed at the root and tested again until none is left

## F. Final checks (section 10)
- [ ] All tests, here and on Windows
- [ ] The stress test; the three logo stress tests (366 team and 60 competition names; 288 pictures in every look and
      size; odd and missing names)
- [ ] The new-user test from the zip on a clean Windows machine: unzip, double-click, first-start question, add a
      folder, a new match arrives by itself
- [ ] Speed: every page and the first start timed on the biggest save, the seconds reported (the speed work stays in
      stage 6)
- [ ] Screenshots of every page and tab, sent with this checklist ticked
- [ ] Section "Stage 5: what was built" in the plan, a line for every promise
