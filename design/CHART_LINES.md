# The three lines under every chart (the owner's decision, 14 November)

Every chart on every page (bars, rings, lines, calendars, ladders, strips, dot charts; **charts only**: tables keep
their own notes) has three short lines under it, small and dim like notes, **always shown**:

1. **What it is**: one short sentence on what the chart draws ("Their runs in every innings here, oldest first.").
2. **Who's best**: the leader with their number. On a chart with no player or team at the top, the top thing,
   labelled for it ("Best month", "Most often", "On top", "Best season", "Their nemesis"...). The old "What it shows"
   line becomes this one.
3. **What it's for**: as now.

All three are written by the server, as fields on the chart's own part of the page: `is_`, `best` (and `best_label`
when it isn't "Who's best"), `for_`. The page passes them to `Explain` (`web/src/kit/base.tsx`):
`<Explain is_={x.is_} best={x.best} best_label={x.best_label} for_={x.for_} />`.

Rules (owner's answers and the decisions told to him):
- "Who's best" names **the top of all**; on a chart of your team against everyone, **the top of all, then where your
  team is** ("Australia, 1,412 · India 3rd, 1,288"). `server/styleguide.py` `best_line` does this.
- Lower-is-better charts (economy, bowling average) name the lowest.
- Ties name up to three, then "and N others".
- The chart's own minimum to qualify applies.
- A one-player chart names that player's top thing (their best season, their most common way out...), labelled.
- Names open the player menu (the page's `<T>` does this for every known name in a sentence).
- One short sentence a line, plain words, no code words.
- A saved picture includes the lines (they are inside the tile).
- An empty chart shows its "not enough yet" message instead of the lines.
- No fielding anywhere; competitions in the agreed order; formats never mixed in an average.
- Every number in "Who's best" is checked in a test against the data counted another way.

Where the lines live (how it was built, 17 November):
- The Player page and most page parts keep the three lines beside their other fields (`is_`, `best`, `best_label`,
  `for_`); the page passes them with `three(x)` (`web/src/kit/base.tsx`).
- The shared pieces in `server/styleguide.py` (form, the season calendar, home and away, our score v theirs,
  match-winners, the series score) keep theirs under their own `lines` key (`record_lines` and `runs_lines` for the
  season ring and the runs of results), because `best` already means something else there; the page passes
  `{...x.lines}`.
- Tests: `tests/test_chart_lines_players.py` and `tests/test_chart_lines_pages.py`.
