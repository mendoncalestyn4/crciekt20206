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

## Left, in order (updated 27 November, 9:50 pm IST; the owner said: finish what's running, then stop)
1. **Finish the checks that were running at the stop** and read their results (below, "Running at the stop").
   Fix every real finding at the root with a test; update this note.
2. **Deep test step 5 must end clean**, then stop and report to the owner (the owner: "stop after 5th").
3. Then, only when the owner says go: steps 6 to 12 of the deep test (NEW_SITE_PLAN.md item 15 and (a) to (y), except
   (p)), the switch-over, the final checks and screenshots, and stage 6.

## Running at the stop (scripts kept in tools/deeptest/, logs in the session's scratchpad)
- Step 4: `deep4.py` (every page with every choice it offers, two levels deep; every team; every competition and season;
  every match; every player; the server's error log) and `deep4b.py` (the "your team" pages, with England, Gujarat
  Titans and Titans set as the owner's teams). At 8,400 answers: 0 real findings (the only flags were sentences
  starting "None of your players", a false alarm of the checker).
- Step 5: `deep5a.py` (every same-number check on the save; the first passed) and `deep5b.py` (every check in the test
  suite that takes a whole career, run on the save).
- Pressure: `pressure.py` (about 2,000 questions answered calmly, then by 16 visitors at once, three rounds, all must
  be identical; a new match arriving while 16 visitors ask; the slowest answer). It starts by itself after the crawls.
- The update test with UTF-8 reports (program build run after commit faeed07). The update itself already passed on
  Windows (old version installed the new one and reopened as it, careers intact, backed up first).

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
