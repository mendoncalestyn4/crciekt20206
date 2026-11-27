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

## Left, in order
1. **The real update test must pass.** Program build 34 (publish, with the "ends itself" fix) was running at the
   stop. When it has published: run program.yml with publish=true and update_test=true; read the printed program.log
   ("ending ... still running: ..."). Fix any cause at the root and repeat until the old version closes by itself.
2. **Windows runs green on the newest commit:** the push run, and a heavy run (dispatch Tests on Windows).
3. **Competition rules (deep check item t):** knockouts and who goes through still to read by hand.
4. **On the owner's new save only (the owner, 27 November: no checks on the old career):** the whole deep test in
   NEW_SITE_PLAN.md item 15 and its additions (a) to (y), except (p), here and on Windows, with problems fixed as soon
   as found and everything run again at the end. The save goes to Windows through the project (the owner's yes).
5. Then the switch-over, the final checks and screenshots, the plan's "Stage 5: what was built", and stage 6.

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
