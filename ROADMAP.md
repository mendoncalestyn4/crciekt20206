# Cricket Captain 2026 Stats Pack: plan

What the site does, the decisions behind it, and what is built so far.
✅ built · 🔨 in progress · ⬜ to do

## Decisions

- **Cricket Captain 2026 only.** Titles in CC2026 use the real competition names (Ranji Trophy, IPL, County Championship, …).
- **Runs on your own PC (Windows).** The site watches your Scorecards folder
  (`%AppData%\Childish Things\Cricket Captain 2026\Scorecards`) and new matches appear automatically.
  Turn on **Autosave scorecards** in the game's options.
- **One Scorecards folder = one career.** If you play more than one save into the same folder, their matches
  go into that one career together (your choice). A separate career needs a separate folder or an upload.
- **Every competition is its own section, nothing merged.** Bilateral Tests / ODIs / T20Is, ODI World Cup,
  T20 World Cup, WTC final, Champions Trophy, IPL, The Hundred, T20 Blast, County Championship Division 1 and
  Division 2, Ranji Trophy, … are all separate.
- **Players are linked by name** across teams and competitions. Two same-named players in one XI are kept apart
  ("J Denly (2)"). Anything else that looks wrong is listed on the Data check page and **you** decide (manual only).
- **First-named team is the home team**; ICC events count as neutral.
- **General stats browser** (not built around one team).
- **One stat per chart**, with Top-N limits and a minimum to qualify.
- **Look:** "night match under floodlights" (dark) and "day match" (light), scoreboard-style headings and tiles.
- **Wrong margins in the game's files** are silently corrected from the scores.

## Data you can trust

- ✅ Parser for the CC2026 layout (did-not-bat rows, dot balls in T20, balls in The Hundred, `rtrd ht`, shortened names like `K'r Reddy`)
- ✅ Every scorecard self-checked (runs, extras, bowling, wickets, fall of wickets, 4s/6s must all agree)
- ✅ 4s/6s cross-checked by fixed column position; stats engine checked against an independent count from the raw text
- ✅ Catches and stumpings credited to the fielder's full name (`st de Kock`, `c DKock`, `c van Beek`)
- ✅ Competition, stage, division, season (incl. 2026/27 seasons), series and home/away for every match
- ✅ IPL Eliminator recovered from the bracket (the game labels it "Qualifier 1")

## Running on your PC

- ✅ Careers saved in `Documents\Cricket Captain Stats Pack` (safe when you update the program)
- ✅ Folder watching: only new or changed scorecards are read; deleting old files never loses matches
- ✅ Live check every ~20 seconds with a "new matches added" message
- ✅ Browse… button (normal Windows folder picker)
- ✅ `Start Stats Pack.bat`: first run installs everything, then opens the site in your browser (see README)
- ✅ Download any chart as an image: camera button on every chart
- ✅ Automatic weekly backup of every career, restore from Home

## Pages

- ✅ **Home**: career summary, sections, latest results, load folder / files / career file
- ✅ **Stat by stat**: pick a section, season, stat; ranked bars + dot chart with every region explained; full table + download
- ✅ **Search** box in the sidebar: players, teams, competitions, matches (20)
- ✅ **Player page**
  - batting and bowling tables with the same columns in every section, and season by season
  - form, nemesis and bunnies (1), batting first vs chasing (2), wins vs losses (3)
  - consistency (4), how they get out / how they take wickets (8), quality of wickets (new 1)
  - player vs each team (21), golden ducks, average at each batting position, role labels
  - "came in at": score when they walked in, batting under pressure, best rescue innings
  - record against strong vs weak teams; wicketkeeper flag
- ✅ **Compare players** side by side (new 5)
- ✅ **Teams**: record overall/home/away against the average team, streaks and form (14), batting depth (15),
  opening partnerships (11), partnership averages by wicket (new 9), collapses (12), wicketkeepers
- ✅ **Team vs team**: overall / home / away / only against each other, tale of the tape, head to head,
  player-by-player dot charts, runs above average / runs saved for every player
- ✅ **Best batting position** rankings (6), **role labels** (7)
- ✅ **Competitions**: league tables (NRR, Ranji points, county points from results), knockout brackets, series results
- ✅ **Is this total enough?** win % by first-innings score (new 6), **home advantage** by section (new 8)
- ✅ **How the game changes over seasons** (new 11), **breakout players** (new 3)
- ✅ **Rankings**: player ratings per section and team Elo over time
- ✅ **Records** and **"New record!" alerts** when a new match breaks one (new 13)
- ✅ **Matches**: search, scorecards and the **wicket timeline** (new 7)
- ✅ **Data check** (22): scorecard report, unclear catches to credit, same-name players to merge or split (manual, undoable)

## Done in the latest round

- ✅ Rain-affected results keep the game's official margin (the rain rule, DLS) and show "(DLS)"
- ✅ Chart names always joined to their own dot by a thin line; only the top 4 named, the rest on hover
- ✅ The site is always dark (the night-match look)
- ✅ Rain games everywhere: marked on the Matches page, left out of par scores, "Is this total enough?", lowest total
  defended and other games' win chances; net run rate by the ICC's rules
- ✅ Declarations: an innings ended by a retired-hurt batter with nobody left is all out, not declared
- ✅ **Title race** (idea 3) on Competitions, and playoff / title chances on Home
- ✅ **Most valuable players** (idea 4) on Season review: impact points, or the IPL's MVP points in T20

Ideas to decide on later:

- "Since you last looked" panel on Home: new matches, records, milestones, table moves, form changes
- Download the whole career to Excel (matches, batting, bowling, fielding, records)
- Faster opening for very big careers (save the built tables between runs)
- Bowler workload: overs each bowler has bowled in the last 7 and 14 days, flagging tired bowlers before the next
  match
- One-page season report as a picture or PDF, ready to share
- Quick question box: type "most sixes IPL 2027" and get the answer and the list

Decided against: team logos.
