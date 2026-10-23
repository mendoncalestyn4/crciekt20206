# Fresh-look mock-ups

The five page styles and five chart styles shown as screenshots before the new site is built
(see `NEW_SITE_PLAN.md`). They are design references, not part of the program.

| File | What it is |
|---|---|
| `a_broadcast.html` | Page style 1 · Broadcast (TV sports graphics) |
| `b_bento.html` | Page style 2 · Bento (app dashboard) |
| `c_almanack.html` | Page style 3 · Almanack (cricket magazine) |
| `d_scoreboard.html` | Page style 4 · Scoreboard (stadium LED board) |
| `e_game.html` | Page style 5 · Game menu (player cards) |
| `charts.html?idea=1…5` | Chart styles 1–5: Circles, Scouting report, Pictograms, Flows and timelines, Grids |
| `lib.js` | Shared helpers (formatting, partnerships from the fall of wickets, donuts) |
| `extract_data.py` | Pulls the real numbers from a folder of scorecards into `data.json` |
| `shoot_pages.py`, `shoot_charts.py` | Screenshot every page / chart with Playwright |
| `mix.html?idea=1…3` | The mixed style you asked for: Bento as the base, with Broadcast's player page, series tables and leaderboards, Almanack's player-of-the-match summary and Scoreboard's name font. Numbers in Bento's font. Idea 1 = Bento + Broadcast, 2 = Bento + Scoreboard, 3 = clean Bento, 4 = idea 2 exactly with idea 1's charts (solid innings bars, percentile bars, a plain form line, solid list bars) and its latest-results strip |
| `extract_mix.py` | Adds what the mixed style needs (player-of-the-match headlines, the series story, more leaderboards, a Test scorecard) |
| `check_fit.py` | Checks that nothing goes outside its tile, chart or the page: text past an edge, text cut short, two pieces of text on top of each other, a page wider than the window. `python3 check_fit.py 4` checks every idea 4 page |
| `shoot_mix.py` | Screenshots of the mixed style, e.g. `python3 shoot_mix.py 1 2 3 --pages=home,match,match:2,match+test` |

Each page style has six pages: `?page=home`, `player`, `match`, `series`, `leaders`, `rankings`; the mixed style adds `squad` and `results`,
and the match page takes `&inn=2` (the second innings) and `&match=test` (a four-innings Test).

To run them again: `python3 extract_data.py <Scorecards folder>`, write `data.js` as
`window.D = <data.json>;`, put `echarts.min.js` (ECharts 5.5.1) and a `fonts.css` with the fonts below
next to the HTML files, then open them in a browser or run the screenshot scripts.
Fonts: Bebas Neue, Barlow Condensed, Inter, Fraunces, Source Serif 4, Doto, Teko, Space Grotesk, Rajdhani.

Not saved here: your scorecards and the data made from them, the game's logo pictures, the fonts and the chart library.
