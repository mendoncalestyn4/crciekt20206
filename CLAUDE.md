# Working on Stats Pack: the owner's standing rules

Read these at the start of every session. They come from the owner and hold until they say otherwise.

## Ask first
- **Before any extra work that wasn't asked for, ask.** That includes checks to "be sure", setting up another
  environment, a different approach, or anything meant to make the work easier. Say what you'd do, why, and roughly
  how long it takes, give the choices, and wait for the answer.
- When the owner says "stop", "no wait" or "don't make anything", stop.
- **No need to ask (approved 31 October; say afterwards what was done):** fixing bugs found by checks (wrong numbers,
  crashes, errors on the new site; crashes on the old one), updating tests that an approved change made outdated,
  fixing layout problems found by the fit check, and running the owner's saves through every page to find bugs.
- New features always need a yes.
- **4 November: full authority.** The owner gave all authority to decide and say yes to anything without waiting for
  approval ("I give you ALL AUTHORITY to say yes to anything u want"). Still report afterwards what was done and why.
  Stage 1 was finished and stress-tested on 6 November. **12 November: the owner gave the word for stage 2** ("move
  on to stage 2"). Fixes are always at the root cause, never temporary; every stage gets its own stress test.
- **No player art** (12 November): no pictures of players behind the pages.

## How the owner likes the work done
- Do it well rather than fast: zero errors, deep checks, and screenshots of what changed.
- **Ask every clarifying question before building** (13 November: "Remember to ask me all these clarification while
  building the next stages I want it perfect"): before each stage, page or feature, go through it deeply and ask
  about everything that is the owner's choice (what it shows, edge cases, defaults, names, where it lives), say which
  smaller things you'll decide yourself and how, and wait for the answers and a "go".
- **Read the plan before building, and check against it before calling anything finished** (13 November, after
  stage 2 was found to differ from it): before each stage, page or feature, read `NEW_SITE_PLAN.md` in full for it
  (its row in section 8, the recipe in section 9, the checks in section 10, everything section 14 says about it, and
  what section 5 asks of every page), and `design/INVENTORY.md` for its pages. Build exactly what was agreed. Before
  saying a page or stage is finished, go through those sections again point by point and tick its checklist lines;
  anything that differs is either put right or brought to the owner.
- **Safeguards so nothing agreed is missed** (13 November, the owner: "save 4-6 in your memory always"):
  1. **A written checklist for each stage, made before building starts:** every promise the plan makes for the stage
     (each feature and chart and the page it goes on, each logo, every nothing-lost line, the parity tests, the test
     data the plan names, the screenshots). Show it to the owner before starting; at the end tick every item with
     where it is on the site, and show it again with the screenshots.
  2. **Checks that block calling a page finished:** a page isn't finished while any of its nothing-lost lines is
     unticked, while a chart or piece the plan puts on it is missing, or without its parity test (its numbers equal
     to the old site's). The owner said not to build the automatic tests for this yet (13 November): until told, do
     these three checks by hand, every time, before saying a page or stage is finished.
  3. **Each stage's "what was built" section in the plan has a line for every promise:** built, where, and how it was
     checked.
- Explain in plain words, not code words.
- Commit and push after every finished piece (on the branch you were told to use), so a machine reset loses nothing.
  No pull request unless asked.

## The site
- New site: `server/` (Starlette) + `web/` (React, built into `web/dist`, which is committed: run `npm run build` in
  `web/`). Engine: `ccstats/`. The old Streamlit site (`app.py`, `views/`, `ui/`) gets no new work, but must keep
  working until the switch-over (stage 5). At the switch-over it is deleted completely, with no backup launcher (chosen
  31 October).
- Desktop only. Every feature must work for every team and competition: national, franchise and domestic.
- Formats are never mixed: Tests, ODIs and T20Is apart; each domestic competition on its own.
- Competition order everywhere (14 November, "always"): Tests, ODIs, T20Is first, then franchise leagues, then
  domestic competitions; most matches first within each group.
- The plan, stages and approvals: `NEW_SITE_PLAN.md`.
- Tests: `python3 -m pytest -q` (the browser tests are `tests/test_web.py`). The owner's PC has Python 3.14;
  `requirements.txt` pins pandas 3.1 (chosen 31 October, every test passing on Python 3.14); the code also works on
  pandas 2.3. Changing the packages the site installs always needs a yes.

## The owner's data
- Uploaded scorecards and saves are the owner's: use them only for checks and screenshots, keep them out of the
  repository, and read them with `python -I` from a new empty folder.
