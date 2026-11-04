# Parked work (4 November): kept here so a machine reset loses nothing

Not part of the site. Each piece goes back in when work resumes.

- **Stage 2, Team planner and Rivalries** (stage 2 is stopped until the owner says so): `plannerpage.py`,
  `rivalriespage.py` and `stage2_planner_rivalries.patch` (their addresses, data types and menu entries). Server side
  done and smoke-tested on the 2029 save (375 pages, 0 problems); the pages themselves are still to build.
- **Stress tools** (`stress_tools/`): what the stage 1 stress test ran. `stress1.py` (every player, match and team
  page, 40-at-once bursts, the inbox), `stress2.py` (every player in every competition and season, the finder,
  search, junk input), `weird_check.py` + `weird_paths.py` + `make_weird.py` (eight made-up odd careers through every
  page), `stage0_stress.py`, `logo_stress.py`, `deepcheck.py` (figures worked out a second way) and
  `browser_stress.js` (fast clicking). They expect the scratchpad layout of the session that wrote them.

**Stress test status when stopped:** done with 0 problems left: stage 0; the logo stress (1 bug fixed); the eight
made-up saves through every page (3 bugs fixed); the owner's new career, seasons 1 and 2, figure checks; the 2029 save's
every player and every match. Still to run: round one's teams/bursts/inbox and round two on the 2029 and 2032 saves,
every page of the new career's seasons 1–3, the browser check of five made-up saves, the browser click-through, then
the full test runs and the stage 1 screenshots.
