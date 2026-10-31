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

## How the owner likes the work done
- Do it well rather than fast: zero errors, deep checks, and screenshots of what changed.
- Explain in plain words, not code words.
- Commit and push after every finished piece (on the branch you were told to use), so a machine reset loses nothing.
  No pull request unless asked.

## The site
- New site: `server/` (Starlette) + `web/` (React, built into `web/dist`, which is committed: run `npm run build` in
  `web/`). Engine: `ccstats/`. The old Streamlit site (`app.py`, `views/`, `ui/`) gets no new work, but must keep
  working until the switch-over.
- Desktop only. Every feature must work for every team and competition: national, franchise and domestic.
- Formats are never mixed: Tests, ODIs and T20Is apart; each domestic competition on its own.
- The plan, stages and approvals: `NEW_SITE_PLAN.md`.
- Tests: `python3 -m pytest -q` (the browser tests are `tests/test_web.py`). The owner's PC has Python 3.14;
  `requirements.txt` pins pandas 3.1 (chosen 31 October, every test passing on Python 3.14); the code also works on
  pandas 2.3. Changing the packages the site installs always needs a yes.

## The owner's data
- Uploaded scorecards and saves are the owner's: use them only for checks and screenshots, keep them out of the
  repository, and read them with `python -I` from a new empty folder.
