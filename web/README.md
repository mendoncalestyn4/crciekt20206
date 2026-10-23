# The new Stats Pack website

React and TypeScript (strict), built with Vite, charts by Apache ECharts 5.5.1 (the version the mock-ups were approved
with). The stats server (`python -m server`, see `server/`) serves the built site from `dist/` and answers every
question the pages ask: the website never does its own cricket maths.

`dist/` is committed, so the Stats Pack needs only Python on your PC. After changing anything in `src/`, build it again:

    npm install        # once
    npm run build      # type-checks, then writes dist/

While working on it, `npm run dev` serves the site with live reload on port 5173 and passes `/api` questions to a
stats server on port 8601 (`python -m server --no-browser`).

- `src/kit/`: the chart kit (every piece of the approved mock-up) and the page's building blocks.
- `src/shell/`: the rail, the page head, search (Ctrl K), live news of new matches.
- `src/pages/`: the pages (stage 0: My team, the style guide, Settings and the sections still to come).
- `src/fit.ts`: nothing may spill out of its tile (`tests/fit_rules.js` checks it in a real browser).
- `src/fonts.css`: Bebas Neue, Space Grotesk and Inter from the @fontsource packages, latin and latin-ext only.

The browser tests are `tests/test_web.py` (they use `dist/`, so build first).
