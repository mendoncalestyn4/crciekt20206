# Cricket Captain 2026 Stats Pack

Your own stats site for Cricket Captain 2026. It reads the scorecards the game saves and turns them into
leaderboards, player and team pages, head-to-heads, records, rankings and more. New matches appear by themselves
while you play.

International matches are grouped by format, like real career records: every Test (series and the World Test
Championship Final) is in **Tests**, every ODI (series, World Cup, Champions Trophy, Asia Cup) in **ODIs**, and
every T20I in **T20Is**. Everything else stays separate: IPL, T20 Blast, The Hundred, Ranji Trophy, each County
Championship division and so on never mix. The Competitions page still shows each World Cup's own table and
bracket, and each series on its own.

Everything runs on your own PC. Nothing is uploaded anywhere.

---

## Install (once, about 5 minutes)

### 1 · Install Python
1. Go to **https://www.python.org/downloads/windows/** and download the latest **Python 3** (3.12 or newer).
2. Run it. On the first screen **tick "Add python.exe to PATH"**, then click **Install Now**.

(If you skip this, the Stats Pack opens the download page for you and explains what to do.)

### 2 · Get the Stats Pack
1. Download **Cricket-Captain-Stats-Pack.zip**.
2. Right-click it → **Extract All…** → pick a folder, e.g. `Documents\Stats Pack program`.

### 3 · Turn on scorecards in the game
In Cricket Captain 2026: **Options → Autosave scorecards → On**. The game then saves every match you play to
`C:\Users\<you>\AppData\Roaming\Childish Things\Cricket Captain 2026\Scorecards`.

### 4 · Start it
Double-click **`Start Stats Pack.bat`** in the folder you extracted.

- The **first time** it sets itself up (a few minutes, needs internet). After that it starts in seconds.
- If Windows says **"Windows protected your PC"**, click **More info → Run anyway** (this happens for any
  downloaded .bat file).
- Your browser opens the site. **Keep the black window open** while you use it; close it to stop.

Tip: right-click `Start Stats Pack.bat` → **Send to → Desktop (create shortcut)** to start it from your desktop.

### The new site (a preview)
A completely new site, in the look you chose, is being built page by page (see `NEW_SITE_PLAN.md`). To have a look,
double-click **`Start new Stats Pack (preview).bat`**: it opens on the same careers as the current site (add a
career on the current site first). For now it has the new menu, search (Ctrl K), your team's colours, live news of
new matches and a **style guide** with every chart drawn from your own career; the pages arrive stage by stage. The
current site stays exactly as it is until the new one has everything.

### 5 · Connect your career
On the **Home** page:
1. Your Scorecards folder is usually found for you. If not, click **Browse…** and pick it.
2. Give the career a name (e.g. "India save") and click **Start watching**.

All the matches already in the folder are read, and from then on every new match appears within about
20 seconds, with a message in the corner.

---

## Using it

Use the **menu on the left** to move between pages, and the **search box** under it to jump straight to any
player, team, competition or match.

**Your team, asked once:** the first time you open a career, the site asks **which teams you play as** (a country,
a franchise, a county, or several). Pick them and press **Save**: it's saved with the career, so you're never asked
again, and a new career starts with the same teams ticked. *Not now* asks again next time; *I don't play as one team*
never asks for that career. Change it any time under **My team** in the sidebar (a country can be picked before its
first match). Home then opens on your team, and every page (Stat by stat, Teams, Team vs team, Opponent preview,
Competitions, the planner…) starts on your team's latest competition until you pick something else.

**T20 is judged on fifties:** on the Players page in T20, the conversion chart runs to 50 (hundreds are counted on
their own underneath), the season table puts 50s before 100s, **danger zones** highlight the 20–49 band (got in, out
before 50), and the match impact score gives a fifty a bonus and a hundred a smaller extra on top.

**Catches the scorecard can't name** (*c Mendis* when a side has two Mendises) simply count for the team, not for
either player: nothing to sort out. You can still credit one under Data check → Team catches if you want.

**Your choices follow you:** pick a section, season or team on one page (say IPL 2027) and every other page opens on
it too, until you change it. That's saved with your career as well.

The pages are grouped in the menu:

| Page | What it's for |
|---|---|
| **Home** | One tab per team you play as: record and rating in each competition, latest result, **what changed after the latest game** (Elo, table position, series score, first-innings lead, records, milestones, who rose or dipped), this season against the same point last season, report cards (A to E), your stars with form arrows, squad, alerts, headlines, milestones and records in sight, how you win, rivals, a *Next opponent → Preview* button, trophies, team records, season by season and **your match notes**. The **Everything** tab has the latest result, headlines and every section. |
| **Stat by stat** | Pick a section and one stat. Left: the best (or worst) ranked. Right: every player as a dot against the section average. Pick several seasons, competitions, teams, venues, ways out and batting positions at once (groups like openers + no. 3, or single positions 1 to 11), or combine sections. Each player's **rank %** (top 5% …), the **change since last season** (when one season is picked), and **Measure against** their own section's or season's average, so figures from different competitions are fair to add up. Download as CSV. |
| **Players** | Everything about one player: a career card and **every format side by side** (best one highlighted), batting and bowling tables for every section, **danger zones** (the scores they tend to get out on), the **conversion funnel** (20 → 50 in T20; 30 → 50 → 80 → 100 in ODIs; 50 → 80 → 100 in Tests), bowling with and without wickets, Test bowlers' match pattern, career journey, form, streaks, chasing, splits, nemesis and bunnies, batting position, role. **Story** tab: match impact game by game, rank in the section season by season, fastest to milestones, badges, career firsts, team win % when they fire, nervous nineties, pairs, not-outs, after a hundred, compare two seasons. |
| **Compare players** | Up to four players side by side, one chart per stat |
| **Teams** | **Overall / Home / Away** applies to the whole page (results, players, how they win, opponents, series). Tabs: **Overview** (against the average team, top players, partnerships, collapses, style, discipline), **How they win** (batting first or chasing, close games, chasing and defending by target size, the openers' start), **Opponents and stages** (league v knockouts, favourite and bogey teams, home fortress, bouncing back after a defeat, revenge games), **Season** (the league race after each match day, early v late season), **Series and Tests** (first blood, deciders, dead rubbers, follow-on and declarations, second-innings collapses and 4th-innings chases), **Squad** (the all-time or season XI, who came in and who left), **Results**. Also: batting and bowling ratings, how dominant the wins are (thrashings, comfortable, scrapes by the format's margins) and comebacks from a low win chance |
| **Team vs team** | Two teams head to head (Team A starts on your team). **Where**: all venues, *at A's home* (A's home games against B's away games) or *at B's home*, or neutral grounds; and all their matches or only the games against each other |
| **Opponent preview** | Opens on your next match (from your schedule, or the next game of a series under way). Pick your team and theirs (Tests / ODIs / T20Is / all for internationals; every side is listed, and your scheduled opponents are tagged, even before they've played here): a **predicted result** (built in steps you can see), **your best XI against them** (your squad's record v them, with picks and players to think again about), a game plan, every past meeting with key players and a card per game, who gets whom out, their form, key wicket, weak spot, the bowler to attack, batting styles, batting first or chasing, home and away, big matches, trend, and the two sides side by side |
| **Team planner** | Qualification scenarios, a suggested batting order, a bowling plan, fringe players knocking on the door, batting and bowling partnerships |
| **Player stories** | Form guide, milestone and record watch, team win % when a player fires, heroes in defeat, one-man shows, nervous nineties, pairs, after a hundred, partnerships (with chemistry and strike-rate pressure), Player of the Series, biggest upsets, fastest to milestones, match impact, badges, batter v bowler, clutch players |
| **Matches** | Search any match: scoreboard, **your side's best and worst** in it (by match impact), **your notes** (saved with the career), a written match report with an excitement rating, **win chance** after every wicket (ending at the result), wicket timeline with the par line, full scorecard. With no match picked: the best games you've played |
| **Fixtures** | Your schedule: add a series with pickers (opponent, format, how many, home or away, month, and if you know them the date of every match) or type your whole year one line per series. A match without a date is placed from the match before it (*about 12 Jun*), and a series under way always finishes before the next one starts, so **Next match** is right. Made a mistake? **Change or delete** any series or tournament (with Undo), and the **schedule check** spots the likely ones (a series added twice, two on the same days, the wrong month or venue) with a one-click fix. Every game still to come shows **your chance** (🟢 easy · ⚪ even · 🔴 hard) and the opponent's form (👻 bogey team, 😊 favourite opponent); **the season ahead** gives the record you're heading for and your toughest run. Series previews add **conditions** in that country, **who travels well**, your past series with them, records in reach and **your own note**; a **forecast** is kept before each series and checked after it, and every finished series gets a **series review** (use more · keep · think about dropping, against each player's usual level, and the series against your previous ones). Tournaments under way show your chance of the knockouts, and **suggested goals** come from your schedule. Each match ticks itself off when the game saves its scorecard. **Forgot something?** Any match your team plays that isn't in the schedule is added by itself (🆕), with the rest of its series, and in a tournament the next knockout game (quarter-final, semi-final, Qualifier 2, final) appears once you're through, against the other tie's winner when that's known. Also: the next match with a prediction, series previews and live series chances, series reports, a season calendar (April to March), the World Test Championship race, milestone countdowns and season goals, and **Preview any opponent**. Home and away come from the scorecards (the side named first is at home): a series added at the wrong venue is put right and marked 📍; mark a series neutral if it was at a neutral ground |
| **Season** | A **season calendar, April to March**: every result on its day, and your fixtures still to come (on their day when you gave a date, otherwise in a yellow box at the top of their month), with who you played each month; or one month at a time (results and fixtures to come). Also a tracker for every bilateral series (with the chances of each series result while it's still going), and how far each competition has got |
| **Competitions** | Pick a competition (a World Cup, the bilateral ODI series, a league): league tables (points, NRR, wins batting first and chasing, last 5, home and away, points per game, run rates, places moved since the last match day), knockout brackets, the **title race** (each side's chance of the playoffs and the title, from the rest of the season played out 4,000 times, with how it changed after every match day), every series with its Player of the Series, and for Tests the **World Test Championship** table (12 a win, 6 a tie, 4 a draw, by % of points) |
| **Season review** | Each competition's season in one place: champions and the final, Team of the Season, leading players, breakout players, best matches, biggest upset, records broken, your report card, and the **most valuable players** (impact points in every format, or the IPL's own MVP points in T20 and The Hundred). International cricket gets a calendar-year review: Player of the Year and Team of the Year in Tests, ODIs and T20Is, and the Cricketer of the Year |
| **Honours board** | Champions of every competition and season, top scorers, trophy cabinets |
| **Rivalries** | Every pair of teams that have met, and who does best in those games |
| **Records** | The record books (partnerships with both batters named where the scorecard allows) with the **near miss** under each (the closest anyone has come), the **record timeline** (who held each record and when it fell), plus "On pace for" projections while a season is under way |
| **Hall of fame** | Player of the Match leaderboard, deadly catcher-and-bowler duos, best all-round match performances |
| **Rankings** | Player ratings (recent form counts most), **rankings history** (each player's peak and when, matches at No. 1, every No. 1 reign), team Elo with batting and bowling ratings, and a **combined international rating** across Tests, ODIs and T20Is |
| **Insights** | Is this total enough? (and what a score is worth batting first and chasing, and against a good side), a **chase calculator**, home advantage, how scoring changes season to season, breakout players, Test innings by innings |
| **Analytics** | Runs above expected, fair averages (against the attacks faced, and settled for short careers), what wins games, luck (expected wins), match-winners and who each team leans on, style maps, boom or bust, is the form real?, bat or bowl first? |
| **Data check** | Starts with a short list of what needs you. **Name shared by 2 players**: e.g. *R Patel* at Leicestershire and at Surrey, kept apart in one click. **Player with 2 names**. **Games left out**: knockouts from an earlier playthrough of a season (see below). **Team catches**: catches the scorecard can't give to one player count for the team (nothing to do; credit a player if you like). Nothing changes unless you click, and every change can be undone under *Your changes*. |

Under every chart, **What it shows** reads the chart for you with its numbers, and **What it's for** says what to
use it for.

**Format rules:** every figure uses the bar that fits the format. A big score is 50 in T20 and ODIs and 100 in Tests;
a haul is 3 wickets in T20, 4 in ODIs and 5 in Tests; close games, thrashings and good starts are measured the same
way.

**Latest** always means the match you played last (from when the game saved the scorecard), not the date printed on
it: the game saves some scorecards dated months ahead.

**What the scorecards can't tell us:** there's no ball-by-ball detail, toss, captains, ages or fixtures (add yours on the Fixtures page), so there's
nothing on who scored off which bowler, the toss, or games still to come. Partnerships name both batters only where
the scorecard leaves no doubt (about two thirds of them, nearly all the big ones).

**Hover** over any bar or dot to see the player's full figures and rank. Hover a chart and click the
**camera** in its top-right corner to save it as a picture.

**Your team's colours:** pick a national side under **My team** and every page takes its colours: the sidebar and
a page matched to its shirt (India: a light-brown sidebar on a dark blue page; England: navy on light blue;
Australia: dark green on yellow; New Zealand: black on light grey), with buttons, headings and tables to match.
All 31 national sides have colours. Play as no national side and the site has its dark night-match look, whatever
Windows is set to. Chart colours stay the same blue and orange in every look, so colour-blind players can read them.

---

## Competition and team names

The Stats Pack knows every competition and team in Cricket Captain 2026 by the game's own names ("20 Over Trophy",
"FC League") and by the real names from the name files ("T20 Blast", "Ranji Trophy"). A competition is one section
whichever name its scorecards print. Where two countries' competitions have the same name (Pakistan and
Afghanistan both have a "National T20 Cup"), each country's is kept separate.

**Internationals** include every national side in the game, associates too (Denmark, Bermuda, Italy, UAE …).
**World XI** games and **tour games** (a country against a side that isn't one, like the Prime Minister's XI or a
county) have sections of their own, one per format ("World XI · T20", "Tour matches · First-class"). They never
count in anyone's Test, ODI, T20I or domestic record, and they have no league table or champion.

**Renamed something yourself?** Keep your copies of the game's name files (`editcompnames.txt` and
`editteamnames.txt`) in the *Cricket Captain 2026* folder that holds your Scorecards folder (or in the Scorecards
folder itself). The Stats Pack reads them when it opens your career, and again whenever they change. A competition
you rename stays the same competition, under the name the site already uses for it, so its records carry on.

## Team and competition logos

The site shows each team's emblem and each competition's logo, from your game's editor files: `editemblems.txt`
with the `editor\emblems` pictures, and `editcomplogos.txt` with the `editor\complogos` pictures. It finds them in
the *Cricket Captain 2026* folder that holds your Scorecards folder (or the Scorecards folder itself, or the Steam
install folder). If yours are somewhere else, open **🎨 Logos** in the sidebar, type the folder that holds them and
press **Use this folder**.

Each picture goes with the name the site shows for the team or competition, the way the files say: a line can
point at its own picture or borrow another team's. A team with no picture shows no logo, never someone else's.
Logos appear on Home (your team, the latest result), Matches, Team vs team, Opponent preview, Fixtures (the next
match, the fixture list, each series), Competitions (the heading and every team in the league tables) and Teams.
The IPL, Hundred, Big Bash and international logos are each drawn in a look picked against the original so they
read on the dark pages (a see-through part shown white as in the game, dark writing made light, or a soft edge line);
every other logo is shown exactly as it is. On a light team page every logo is shown as in the game. A competition's logo also stands on the scoreboard of each of its matches
(every Test shows the World Test Championship's; a World Cup's only its own games). Add or change a picture in the
game and the site picks it up on its next page.

## Rain and declarations

The scorecards never say "rain", but a shortened game gives itself away: an innings stopped short of its overs
without being bowled out, a margin the scores don't give (the rain rule, shown as "(DLS)"), a chase won below the
other side's total, or an abandoned game. Such games are marked on the Matches page. They count as normal for the
players' runs and wickets, but they're left out of par scores, "Is this total enough?", lowest total defended and the
win chances of other games. Net run rate follows the ICC's rules: abandoned games don't count, a side bowled out is
charged its overs, and in a rain-rule result the side batting first is credited with the par score.

The scorecards don't say "declared" either. An innings that ended with two batters not out, before the last innings,
was declared; one that ended because a batter retired hurt and nobody was left to bat counts as all out.

## Replayed a season?

If you reload a save and play part of a season again, the game saves each replayed match over its old file, but a
knockout with different teams gets a new file, so the old one stays in your Scorecards folder (that's how one IPL
season can end up with three finals). The Stats Pack spots these from when each file was saved and leaves them out
of every stat. They're listed on **Data check → Games left out**, where you can count any of them again.

## Your data is safe

- Careers are saved in **`Documents\Cricket Captain Stats Pack`**, not in the program folder, so updating the
  program never touches them.
- A **backup** of every career is made automatically once a week (the newest 8 are kept). On Home, open
  **Backups** to restore one. Restoring backs up your current state first, so you can always undo it.
- Deleting old scorecards from the game's folder never removes matches from your career.
- **Download career file** (on Home) gives you one small file with every match and your fixes, e.g. to move to
  another PC (open it there with *Upload files instead, or open a career file*).

## Updating to a new version

Close the black window first. Then download the new zip, extract it over the old program folder (choose
**Replace the files in the destination**) and double-click `Start Stats Pack.bat`. Your careers, fixes and backups
stay where they are, and every scorecard is read again with the new version, so fixes to how scorecards are read
(like super overs) apply to matches you already have.

## If something goes wrong

| Problem | Fix |
|---|---|
| The black window closes straight away | Open the program folder, click the address bar at the top, type `cmd` and press Enter. In the window that opens, type `"Start Stats Pack.bat"` and press Enter: the message stays on screen so you can read it. |
| "Python isn't installed" but you installed it | Re-run the Python installer → **Modify** → make sure **Add Python to environment variables** is ticked. |
| First start fails | Check your internet connection, delete the `.venv` folder in the program folder, and start again. |
| New matches don't appear | Check **Autosave scorecards** is on in the game, and that Home says *New matches from your Scorecards folder are added automatically*. |
| A catch is credited to no player | The scorecard only printed a surname shared by two players, so it counts for the team. That's all it needs; if you want a player to have it, pick them on **Data check → Team catches**. |
| A box says "couldn't be shown" or "Something went wrong" | The rest of the site still works. Open **Details** in that box and send the text so it can be fixed. |
| The browser didn't open | Open **http://localhost:8501** yourself (or the address shown in the black window). |

## Ideas on hold

- **Scouting shortlist** (suggested 25 October 2026, on hold: you have another plan for it). The best players in
  your competition who don't play for you, by role (top order, middle order, finisher, all-rounder, bowler), ranked by
  match impact a game over the last two seasons (5 games at least): for an auction or a call-up. Tried on the
  477-match test career (IPL, for Mumbai Indians): H Singh and P Shaw at the top of the order, D Jurel in the middle,
  N Sindhu as an all-rounder.

---

For developers: `pip install -r requirements.txt`, then `streamlit run app.py`; tests with `python -m pytest`.
