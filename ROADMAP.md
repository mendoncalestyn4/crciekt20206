# Cricket Captain 2026 Stats Pack: plan

What the site does, the decisions behind it, and what is built so far.
✅ built · 🔨 in progress · ⬜ to do

## Decisions

- **Cricket Captain 2026 only.** Titles in CC2026 use the real competition names (Ranji Trophy, IPL, County Championship, …).
- **Runs on your own PC (Windows).** The site watches your Scorecards folder
  (`%AppData%\Childish Things\Cricket Captain 2026\Scorecards`) and new matches appear automatically.
  Turn on **Autosave scorecards** in the game's options.
- **Separate careers, one per save.** You play more than one save, so the left menu has a **Playing now** switch:
  new scorecards go to whichever save is set as Playing now. Nothing else is automatic.
- **Every competition is its own section, nothing merged.** Bilateral Tests / ODIs / T20Is, ODI World Cup,
  T20 World Cup, WTC final, Champions Trophy, IPL, The Hundred, T20 Blast, County Championship Division 1 and
  Division 2, Ranji Trophy, … are all separate.
- **Players are linked by name** across teams and competitions. Two same-named players in one XI are kept apart
  ("J Denly (2)"). Anything else that looks wrong is listed on the Data check page and **you** decide (manual only).
- **First-named team is the home team**; ICC events count as neutral.
- **General stats browser** (not built around one team).
- **One stat per chart**, with Top-N limits and a minimum to qualify.

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
- ✅ Playing now switch in the left menu; live check every ~20 seconds with a "new matches added" message
- ✅ Browse… button (normal Windows folder picker)
- 🔨 `Start Stats Pack.bat`: first run installs everything, then opens the site in your browser
- ⬜ Download any chart as an image (14)

## Pages

- ✅ **Home**: career summary, sections, latest results, load folder / files / career file
- ✅ **Stat by stat**: pick a section, season, stat; ranked bars + dot chart with every region explained; full table + download
- ⬜ **Search** box on every page (20)
- ⬜ **Player page**
  - career by section, season by season (9), form
  - nemesis and bunnies (1), batting first vs chasing (2), wins vs losses and share of team runs/wickets (3)
  - consistency (4), how they get out / how they take wickets (8), quality of wickets (new 1)
  - player vs each team (21), golden ducks
- ⬜ **Compare players** side by side (new 5)
- ⬜ **Teams**: record overall/home/away, streaks and form (14), batting depth (15), opening partnerships (11),
  partnership averages by wicket (new 9), collapses (12)
- ⬜ **Team vs team**: overall / home / away / only against each other, tale of the tape, head to head,
  player-by-player dot charts, runs above average / runs saved for every player
- ⬜ **Best batting position** rankings (6), **role labels** (7)
- ⬜ **Competitions**: points tables (NRR, Ranji points, county points), knockout brackets, series results
- ⬜ **Is this total enough?** win % by first-innings score (new 6), **home advantage** by section (new 8)
- ⬜ **How the game changes over seasons** (new 11), **breakout players** (new 3)
- ⬜ **Records** and **"New record!" alerts** when a new match breaks one (new 13)
- ⬜ **Scorecards** with the **wicket timeline** (new 7)
- ⬜ **Data check** (22): upload report, dismissals that couldn't be credited, same-name players to merge or split (manual)
