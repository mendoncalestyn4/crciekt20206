# Cricket Captain 2026 Stats Pack

Your own stats site for Cricket Captain 2026. It reads the scorecards the game saves, keeps every competition
separate (IPL, Tests, bilateral ODIs, World Cups, each County Championship division, Ranji Trophy, …) and turns
them into leaderboards, player and team pages, head-to-heads, records, rankings and more. New matches appear by
themselves while you play.

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

| Page | What it's for |
|---|---|
| **Home** | Latest result, totals, every section, latest records, backups |
| **Stat by stat** | Pick a section and one stat (runs, average, strike rate, economy, …). Left: the best (or worst) ranked. Right: every player as a dot against the section average. Filter by season, team, batting position, or pick exact players. Download the table as CSV. |
| **Players** | Everything about one player: batting and bowling tables for every section, form, how they get out, splits (chasing, home/away, strong/weak opponents), nemesis and bunnies, batting position, role |
| **Compare players** | Up to four players side by side, one chart per stat |
| **Teams** | A team's record against the average team, streaks, top players, partnerships, collapses, results, the section table |
| **Team vs team** | Two teams head to head, overall / home / away / only against each other |
| **Matches** | Search any match: scoreboard, wicket timeline, full scorecard |
| **Competitions** | League tables (points, NRR), knockout brackets, bilateral series |
| **Insights** | Is this total enough? Home advantage, how scoring changes season to season, breakout players |
| **Rankings** | Player ratings (recent form counts most) and team Elo |
| **Records** | The record books for every competition; 🆕 marks records from your latest matches |
| **Data check** | Fix what the scorecards leave unclear: who took "c Patel" when there are four Patels, two players with one name, one player with two names. Nothing changes unless you say so, and every fix can be undone. |

**Hover** over any bar or dot to see the player's full figures and rank. Hover a chart and click the
**camera** in its top-right corner to save it as a picture.

**Night or day look:** the site follows your Windows setting. Change it in the **⋮** menu (top right) →
**Settings → Theme**.

---

## Your data is safe

- Careers are saved in **`Documents\Cricket Captain Stats Pack`**, not in the program folder, so updating the
  program never touches them.
- A **backup** of every career is made automatically once a week (the newest 8 are kept). On Home, open
  **Backups** to restore one. Restoring backs up your current state first, so you can always undo it.
- Deleting old scorecards from the game's folder never removes matches from your career.
- **Download career file** (on Home) gives you one small file with every match and your fixes, e.g. to move to
  another PC (open it there with *Upload files instead, or open a career file*).

## Updating to a new version

Download the new zip, extract it over the old program folder (or to a new folder) and double-click
`Start Stats Pack.bat`. Your careers and backups stay where they are.

## If something goes wrong

| Problem | Fix |
|---|---|
| The black window closes straight away | Open the program folder, click the address bar at the top, type `cmd` and press Enter. In the window that opens, type `"Start Stats Pack.bat"` and press Enter: the message stays on screen so you can read it. |
| "Python isn't installed" but you installed it | Re-run the Python installer → **Modify** → make sure **Add Python to environment variables** is ticked. |
| First start fails | Check your internet connection, delete the `.venv` folder in the program folder, and start again. |
| New matches don't appear | Check **Autosave scorecards** is on in the game, and that Home says *New matches from your Scorecards folder are added automatically*. |
| A catch is credited to nobody | The scorecard only printed a surname shared by two players. Credit it on **Data check**. |
| The browser didn't open | Open **http://localhost:8501** yourself (or the address shown in the black window). |

---

For developers: `pip install -r requirements.txt`, then `streamlit run app.py`; tests with `python -m pytest`.
