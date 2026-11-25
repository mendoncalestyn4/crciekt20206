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

**Stage 1 stress test: finished 6 November** (results in NEW_SITE_PLAN.md, end of section 15). The tools above are what it ran.

- **Stage 6, first open faster** (parked 25 November, the owner: do it with stage 6): `stage6_speed_first_open.patch`. Saved sums stamped with only the code they use (`ccstats/keep.py` version_of, on_disk, engine files per career), used for honours, marks, rankings, Hall of Fame and match ratings; the read-in career keyed by the loader's code only; tests at the end of `tests/test_speed.py`. Not yet passing: the memo lock fix (version_of's own lock) is in the patch but untested. Plan: NEW_SITE_PLAN.md section 8, stage 6 row.
