# Stage 5: where we stopped (27 November, 2:51 pm IST)

The owner paused for their usage limit and sends the new scorecards (the save played to about 2038) when we resume.

## Done today (all pushed)
- The program closes 61 s after its window shuts (was 186 s): helper processes are stopped at once on closing.
- Every sort keeps level rows in a fixed order, so every page is the same on every computer (level rows came out in
  another order on GitHub's Windows machines). The Preview's competitions follow the agreed order.
- Team v team test checks all 16 teams in two competitions (it picked one at random and added up the wrong thing).
- Ranji Trophy: the first-innings lead in a drawn match follows the real rule; one shared points rule for the table,
  the title race and the season's points; the points note says how level teams are split.
- World Test Championship: teams level on PCT split by more finished series won, then runs per wicket.
- The packaged program ends itself once the site has stopped and everything is kept (Python's own tidying-up hung
  on Windows after an update), with two safety nets and a note in program.log if anything was still running.
- Full test run here: 1,597 passed. Windows: the normal runs green; the heavy run 5 of 6 green at the stop.

## Left, in order (updated 27 November, 9:55 pm IST: the owner said "stop right now"; everything was stopped)
1. **Look into the one real finding so far** (step 5, `deep5a.py`): on the ODI World Cup 2035 points table,
   Australia's W column doesn't equal the wins in Australia's own record (tests/test_same_number.py,
   test_the_points_table_is_the_teams_own_record). Find the cause (a tie won in a super over counted as a win, a
   game set aside, or a real fault), fix it at the root with a test.
2. **Run again what was stopped part-way**, from an empty folder (`python3 -I tools/deeptest/<script>.py …`):
   - `deep4.py`: step 4's crawl had reached 9,200 answers (pages with every choice, two levels deep, done; every team
     under way), 0 real findings (its 174 flags were all sentences starting "None of your players", a false alarm of
     the checker: filter those out, or teach the checker to skip `.none` messages).
   - `deep4b.py`: the "your team" crawl (England, Gujarat Titans, Titans set as the owner's teams), barely begun.
   - `deep5b.py`: every check in the test suite that takes a whole career, on the save: 8 passed when stopped.
   - `pressure.py`: never started (it runs after both crawls).
   - `deep5a.py` finished: 8 same-number checks, 7 passed, 1 failed (item 1).
3. **The last update test** (Build the program run started after commit faeed07, publish + update test): read its end;
   it must say "OK: … intact". The update itself already passed on Windows (the old version installed the new one
   and reopened as it, careers intact, backed up first); only the report's arrow failed to print before that fix.
4. **Deep test step 5 must end clean**, then stop and report to the owner (the owner: "stop after 5th").
5. Then, only when the owner says go: steps 6 to 12 of the deep test (NEW_SITE_PLAN.md item 15 and (a) to (y), except
   (p)), the switch-over, the final checks and screenshots, and stage 6.

## How to resume
1. Read this note and the plan (NEW_SITE_PLAN.md item 15) first.
2. The owner's save: unpacked in the session scratchpad (`save2038/Scorecards`, 5,796 cards, file times kept) with the
   read-in career in `save2038/career.pickle`. If the scratchpad was cleared, unpack the owner's zip again (kept in
   the session's uploads as "…1_nov_2026-rjc_v_utk_ranji_-_group.zip"), keeping each file's modified time, into a new
   empty folder, and run `python3 -I tools/deeptest/load2040.py <folder>` from an empty folder; if the zip is gone too,
   ask the owner to send it again. Never put the save in the repository.
3. Read the logs if they're still there (`deep4.log`, `deep4b.log`, `deep5a.log`, `deep5b.log`, `pressure.log`); if
   not, run the same scripts again from an empty folder (`python3 -I tools/deeptest/<script>.py <save folder> …`).
4. Check the last update test on GitHub (Build the program, publish + update test) ended with "OK: … intact".
5. Fix, test, commit and push each finding; then report to the owner and wait for their go.

## Deep test on the owner's save (5,796 scorecards, 2026-2040), from 27 November evening
- Step 1 done: crash doubles (two crashes in Aug-Oct 2035). Fault fixed: a Test begun before a reload moved the
  reload point back and set aside 2 genuine games (the LPL 2035 Qualifier 1); 26 crashed-try cards set aside, none
  counted twice; permanent test.
- Step 2 done: 57 problems -> 0 (50 false alarms: long team names, "1st InningsR"; 6 guessed figures reported twice;
  1 card the game printed impossibly, now left out by itself, the owner's choice). 3 guesses checked by hand; 307
  automatic splits right.
- For step 6 (the owner's yes, 27 November): names that may be two players in different competitions (about 90, e.g.
  M Khan for Pakistan and a Bangladeshi domestic side) listed on Data check with the reason, for the owner's click;
  nothing changed by itself.
