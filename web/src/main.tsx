// The new Stats Pack website: your careers' numbers from the stats server, in the look you chose.
import "./fonts.css";
import "./styles.css";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router";
import { Inbox } from "./pages/Inbox";
import { Teams } from "./pages/Teams";
import { TeamVsTeam } from "./pages/TeamVsTeam";
import { Preview } from "./pages/Preview";
import { Planner } from "./pages/Planner";
import { Rivalries } from "./pages/Rivalries";
import { Competitions } from "./pages/Competitions";
import { Season } from "./pages/Season";
import { Review } from "./pages/Review";
import { Honours } from "./pages/Honours";
import { HallOfFame, Rankings, Records, StatByStat } from "./pages/Leaders";
import { MyTeam } from "./pages/MyTeam";
import { PlayersHome, PlayerView } from "./pages/Players";
import { MatchesHome, MatchView } from "./pages/Matches";
import { Analytics, Insights } from "./pages/Insights";
import { Stories } from "./pages/Stories";
import { Compare } from "./pages/Compare";
import { NotFound, PLANS, Section } from "./pages/Sections";
import { Settings } from "./pages/Settings";
import { StyleGuide } from "./pages/StyleGuide";
import { Shell } from "./shell/Shell";
import { watchForProblems } from "./problems";

// Double- or triple-clicking anywhere never selects text (your request of 14 November: no blue highlight); dragging
// across text still selects it, so a name or a number can still be copied, and typing boxes work as usual.
document.addEventListener("mousedown", (e) => {
  const el = e.target as HTMLElement | null;
  if (e.detail > 1 && !el?.closest("input, textarea, select, [contenteditable]")) e.preventDefault();
}, true);

const queries = new QueryClient({ defaultOptions: { queries: { staleTime: 60_000, refetchOnWindowFocus: false } } });
watchForProblems(queries);

// Charts measure their words before drawing them: the fonts are loaded first, or the measures would be the stand-in
// font's and labels would touch (as the mock-ups did it).
const FONTS = ["400 20px 'Bebas Neue'", "500 20px 'Space Grotesk'", "600 20px 'Space Grotesk'", "700 20px 'Space Grotesk'",
  "400 16px Inter", "500 16px Inter", "600 16px Inter", "700 16px Inter"];
await Promise.all(FONTS.map((f) => document.fonts.load(f))).catch(() => undefined);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queries}>
      <BrowserRouter>
        <Shell>
          <Routes>
            <Route path="/" element={<MyTeam />} />
            {Object.keys(PLANS).map((p) => [
              <Route key={p} path={p} element={<Section path={p} />} />,
              <Route key={`${p}/pick`} path={`${p}/:pick`} element={<Section path={p} />} />,
            ])}
            <Route path="/leaders" element={<StatByStat />} />
            <Route path="/leaders/records" element={<Records />} />
            <Route path="/leaders/hall" element={<HallOfFame />} />
            <Route path="/leaders/rankings" element={<Rankings />} />
            <Route path="/leaders/:pick" element={<StatByStat />} />
            <Route path="/insights" element={<Insights />} />
            <Route path="/insights/analytics" element={<Analytics />} />
            <Route path="/teams" element={<Teams />} />
            <Route path="/teams/vs" element={<TeamVsTeam />} />
            <Route path="/teams/preview" element={<Preview />} />
            <Route path="/teams/planner" element={<Planner />} />
            <Route path="/teams/rivalries" element={<Rivalries />} />
            <Route path="/teams/:pick" element={<Teams />} />
            <Route path="/seasons" element={<Competitions />} />
            <Route path="/seasons/season" element={<Season />} />
            <Route path="/seasons/review" element={<Review />} />
            <Route path="/seasons/honours" element={<Honours />} />
            <Route path="/inbox" element={<Inbox />} />
            <Route path="/players" element={<PlayersHome />} />
            <Route path="/players/stories" element={<Stories />} />
            <Route path="/players/compare" element={<Compare />} />
            <Route path="/players/:pick" element={<PlayerView />} />
            <Route path="/matches" element={<MatchesHome />} />
            <Route path="/matches/:pick" element={<MatchView />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/style-guide" element={<StyleGuide />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </Shell>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
