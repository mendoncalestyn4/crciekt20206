# Changelog: the fix round and the speed stage (14–20 November)

## Added
- **"Getting ready" bar** in the menu: every page is prepared in the background the moment the site opens (your team
  and players first, then every page, every competition and season, then every other player), using the processor's
  other cores; the site works meanwhile.
- **Everything kept on disk:** later starts are instant (career 8 s → 0.1 s; every page ready → about 0.02 s); a new
  match shows in about 6 seconds; the folder is checked every 2 seconds (was 20).
- **Format tick boxes** on the Player page, Teams, Team v team, Rivalries and Find a match: combine any formats (Tests +
  ODIs), each against its own average; "Tick every competition" on Find a match.
- **Player page tabs:** Overview, Batting, Bowling, Story; innings by innings for batting and bowling.
- **Three lines under every chart** on every page: What it is / Who's best / What it's for; save any chart as a picture.
- **One short name per stat** in every table (Mat, Inns, Avg, SR, Econ, Wkts, BF, 100, 50, 0...), its meaning on hover.
- **How it's worked out:** point at any average, strike rate or economy for its sum ("2,384 runs ÷ 54 times out =
  44.15"); a dotted one rests on few games.
- **Checked ✓ mark** on every match (every sum on its scorecard adds up) and on Find a match; a warning if not.
- **Accuracy checks:** every scorecard checks itself (totals, overs, fall of wickets, result and margin) and is read back
  line by line against the printed card; an impossible-value guard; an alarm for anything unfamiliar; a second,
  separate counter; eleven hand-worked matches and an odd-cases library locked into tests; the same number checked on
  every page; Windows tests on every change. Your 2,720 cards: 0 problems.
- **Bowlers who share a name:** when the card can't say which of two bowlers took a wicket, both are named and the match
  page says so (one line per pair of bowlers).
- **Names shared by different players split automatically** (listed on Data check, can be undone); different printed
  names never joined without you.
- **Server log:** every problem the site notices is written to server.log beside your careers.

## Changed
- **Australia's look:** the page is the pale yellow the tiles had, everywhere (the boxes inside tiles too, the match
  summary included); no bright yellow left.
- **Chart colours on light looks:** the charts' blue is a real blue for every side (it was the team's own colour: green
  for Australia while the words said blue, and red for sides in red, the same as "worse"); the pale cream slice, the
  season's extra lines, drawn games and the orange slice are now deep enough to see on a light tile.

## Fixed
- An innings win lost its margin ("an innings and null runs" on Competitions); its self-check never ran. 37 in your set.
- Innings wins were counted as wins by runs and as close wins in records.
- "L'-Cachet" didn't match Z Lion-Cachet; two bowlers printed with the same name lost wickets.
- An unknown dismissal was read as part of a batter's name; an unknown line as a batter who didn't bat.
- A bowler who bowled but took no wickets showed "–" (now 0); "–" only where nothing can be worked out.
- Several sums divided by 1 when there was nothing to divide by (team runs per wicket, planner average and strike
  rate, style guide strike rate): now "–".
- The openers' and batting pairs' average now divides by the stands that were broken, as the partnerships table does.
- A team's average second-innings score was headed "Avg" (now "Avg score").
- The Player page's tables showed "0 balls" in some sums.
- A junk competition name in an address made the Player page and My team work everything out again (6–58 s); now the
  normal page at once.
- Find a match hung on an empty career.
- The menu was too tall for a 900-pixel window with Windows fonts ("Watching" fell off the bottom).
- Safe scouting for national sides; second playthroughs of a season; My team tiles on the April–March season;
  corrected scorecards (retired hurt reprinted, uncharged no-balls); no fielding anywhere; competition order (Tests,
  ODIs, T20Is first) everywhere; every match clickable.
- Speed: the slow sums fixed at their root (every innings built once for the career, role labels once, scouting in one
  pass, the stands solver, shared-name lookups); every number checked identical before and after on 92 pages.
