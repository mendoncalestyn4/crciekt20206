// Questions to the stats server (server/app.py). Every number on the site comes from there: the website never does
// its own cricket maths.

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export async function get<T>(path: string): Promise<T> {
  const r = await fetch(path, { headers: { Accept: "application/json" } });
  if (!r.ok) {
    let message = `The server said ${r.status}.`;
    try {
      message = ((await r.json()) as { error?: string }).error ?? message;
    } catch {
      /* not JSON: keep the plain message */
    }
    throw new ApiError(r.status, message);
  }
  return (await r.json()) as T;
}

export async function post<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!r.ok) throw new ApiError(r.status, ((await r.json().catch(() => ({}))) as { error?: string }).error ?? `The server said ${r.status}.`);
  return (await r.json()) as T;
}

export type Theme = {
  nation: string | null; dark: boolean; glow: boolean;
  page: string; rail: string; rail_ink: string; rail_on: string; rail_on_ink: string; main: string; line: [string, string];
  tile: string; tile2: string; edge: string; deep: string; track: string; meter: string; ppl: string; ppl_edge: string;
  split: string; other: string; ink: string; dim: string; soft: string; blue: string; gold: string; dimn: string;
  win: string; loss: string; orange: string; led: string; led_ink: string; warm: string; cream: string; grey: string;
};

export type Careers = { careers: string[]; current: string | null; folders: string[] };
export type CareerInfo = {
  name: string; matches: number; sections: string[]; seasons: string[]; my_teams: string[]; my_teams_picked: string[];
  folder: string; checked_at: number | null; latest: string | null;
};
export type SearchItem = { kind: "player" | "team" | "section" | "match"; value: string; label: string; sub: string };

export type Outcome = "W" | "L" | "D" | "T" | "NR";
export type Innings = { runs: number; wkts: number; all_out: boolean; declared: boolean };
export type Result = {
  id: string; date: string; section: string; event: string; opp: string; outcome: Outcome; result: string; us: string;
  them: string; no: number | null; of: number | null; series: string; headline: string;
  margin_runs: number | null; margin_wickets: number | null; innings_win: boolean; rain: boolean; batted_first: boolean;
  venue: "home" | "away" | "neutral"; host: string; ours: Innings[]; theirs: Innings[]; pom: string; pom_team: string;
};
export type Record_ = { played: number; won: number; lost: number; drawn: number; other: number };
/** The form line (server/styleguide.py form()): the share of the last n won after each match, and so on. */
export type Form = { n: number; pct: (number | null)[]; best: number | null; worst: number | null;
  trend: { now: number | null; prev: number | null; word: "" | "up" | "down" | "level" } | null;
  groups: { series: string; opp: string; start: number; end: number; won: number; lost: number }[] };
export type Run = { o: Outcome; start: number; end: number };
export type Calendar = { year: number; start: string; end: string; results: Result[]; best: number | null;
  months: (Record_ & { year: number; month: number; names: string[]; extra: Result[] })[];
  formats: { section: string; kind: "multi" | "one" | "t20" }[]; streaks: Run[] };
export type Venues = { home: Record_; away: Record_; neutral: Record_; nation: boolean;
  hosts: (Record_ & { host: string; venue: "home" | "away" | "neutral"; outcomes: Outcome[] })[] };
export type Strength = { id: string; date: string; section: string; opp: string; outcome: Outcome; me: number; them: number; gap: number };
export type Brief = { score: number; opp: string; date: string; result: string } | null;
export type BatFirst = { first: { played: number; won: number; lost: number }; chase: { played: number; won: number; lost: number };
  multi: boolean; avg_set?: number | null; lowest_defended?: Brief; highest_lost?: Brief; highest_chased?: Brief; lowest_missed?: Brief };
export type Scores = Record_ & { avg_made: number | null; avg_conceded: number | null };
export type Winners = { players: { player: string; matches: { id: string; date: string; section: string; opp: string; headline: string }[] }[];
  wins: number; others: number };
export type BatRow = { player: string; position: number; did_bat: boolean; how_out: string; dismissal: string; runs: number;
  balls: number; fours: number; sixes: number; out: boolean };
export type BowlRow = { player: string; balls: number; maidens: number | null; runs: number; wickets: number; dots: number | null };
export type Card = { innings_no: number; team: string; runs: number; wickets: number; balls: number; overs: string;
  all_out: boolean; declared: boolean; extras: number; bat: BatRow[]; bowl: BowlRow[]; fow: { wicket: number; score: number }[];
  // on the Matches page: as the scorecard prints it
  team_innings?: number; length?: string; total_text?: string; extras_text?: string; followed_on?: boolean;
  counted_in_balls?: boolean; how_fell?: Record<string, number> };
export type Figures = {
  bat: { runs: number; balls: number; fours: number; sixes: number; innings: number; notout: boolean; text: string } | null;
  bowl: { wickets: number; runs: number; balls: number; text: string } | null;
};
export type Pom = Figures & { player: string; team: string; headline: string; report: string };
export type Stand = { innings_no: number; team: string; wicket: number; runs: number; unbroken: boolean; batter1: string; batter2: string };
export type Match = { id: string; date: string; section: string; event: string; home: string; away: string; result: string;
  no: number | null; of: number | null; cards: Card[]; pom: Pom | null; stands: Stand[] };
export type Leader = { player: string; team: string; innings: number; runs?: number; balls: number; average: number | null;
  strike_rate?: number | null; sixes?: number; fours?: number; high_score_text?: string; wickets?: number; economy?: number | null;
  best?: string };
export type Star = {
  player: string; team: string; section: string; season: string; innings: { date: string; opp: string; runs: number; balls: number; out: boolean }[];
  percentiles: Record<string, number>; pool: number; among: string; runs: number; fours: number; sixes: number; from4: number;
  from6: number; running: number; outs: number; how_out: Record<string, number>;
  formats: { section: string; innings: number; runs: number; average: number | null; strike_rate: number | null;
    high_score_text: string; fours: number; sixes: number; hundreds: number; fifties: number }[];
  rating: { value: number; rank: number } | null;
};
export type Banner = { section: string; season: string; elo: number | null; moved: number | null; rank: number | null;
  teams: number; record: { played: number; won: number; lost: number; drawn: number; tied: number; no_result: number } };
export type Series = {
  id: string; section: string; opp: string;
  story: { headline: string; deck: string; flow: string; won: number; lost: number; opponent: string; complete: boolean;
    results: Outcome[]; player_of_series: { player: string; team: string; runs: number; wickets: number; matches: number } | null };
  matches: Result[]; progress: { won: number; lost: number }[]; decider: boolean;
  most_runs: { player: string; team: string; runs: number; balls: number; inns: number; outs: number; hs: number }[];
  most_wickets: { player: string; team: string; wickets: number; runs: number; balls: number; economy: number }[];
};
export type Elo = { table: { rank: number; team: string; elo: number; played: number; peak: number }[]; teams: string[];
  snaps: { date: string; elo: Record<string, number>; rank: Record<string, number> }[] };
export type SquadRow = { player: string; games: number; runs: number; average: number | null; strike_rate: number | null;
  wickets: number; economy: number | null; last5: string; form: string };
export type StyleGuide = {
  career: string; matches: number; team: string | null; mine: boolean; section?: string; season?: string; format?: string;
  missing: Record<string, string>;
  banner?: Banner[] | null; results?: Result[] | null; this_season?: Result[] | null;
  form?: Form | null; scores?: Scores | null; bat_first?: BatFirst | null; calendar?: Calendar | null; venues?: Venues | null;
  strength?: Strength[] | null; winners?: Winners | null;
  leaders?: { runs: Leader[]; wickets: Leader[]; sixes: Leader[]; average: Leader[]; strike_rate: Leader[]; economy: Leader[] } | null;
  star?: Star | null; match?: Match | null; match_test?: Match | null; series?: Series | null; elo?: Elo | null;
  ratings?: { bat: { player: string; team: string; batting: number }[]; bowl: { player: string; team: string; bowling: number }[] } | null;
  squad?: SquadRow[] | null;
};

export type Live = { type: "matches"; career: string; added: number; records: string[] }
  | { type: "failed"; career: string; files: { file: string; reason: string }[] }
  | { type: "checked"; at: number; folders: number };

// ------------------------------------------------------------------ Matches (server/matchpage.py)
export type FinderItem = { id: string; label: string; date: string; home: string; away: string; section: string; name: string; result: string };
export type Finder = { section: string; team: string; sections: string[]; teams: string[]; matches: FinderItem[] };
export type BestGame = { id: string; rating: number; rank: number; of: number; home: string; away: string; date: string;
  section: string; name: string; result: string; why: string; finish: number; comeback: number; stakes: number; show: number };
export type BestGames = { section: string; team: string; rows: BestGame[] };
export type Excitement = { rating: number; rank: number; of: number; why: string; finish: number; comeback: number; stakes: number; show: number };
export type WinPoint = { label: string; W: number | null; D: number | null; L: number | null; note: string };
export type WinChance = { none?: string; team1: string; team2: string; multi: boolean; starts: number[]; points: WinPoint[]; shows: string; for_: string };
export type WicketStep = { wicket: number; score: number; start: number; stand: number; unbroken: boolean; batters: string[] };
export type Wickets = { innings: { innings_no: number; team: string; total: string; all_out: boolean; label: string; steps: WicketStep[] }[];
  par: { wicket: number; par: number; innings: number }[] | null; section: string; shows: string; for_: string };
export type MatchPage = {
  id: string; kicker: string; name: string; series: string; date: string; section: string; event: string; stage: string;
  home: string; away: string; home_score: string; away_score: string; result: string; player_of_match: string; rain: string;
  source: string; note: string; match: Match; report: string; excitement: Excitement | null; win: WinChance | null; wickets: Wickets;
  sides: { team: string; best: { player: string; figures: string }[]; worst: { player: string; figures: string }[] }[];
  top_scores: { player: string; team: string; score: string; balls: number }[];
  best_bowling: { player: string; team: string; figures: string; overs: string }[];
};

// ------------------------------------------------------------------ My team (server/myteam.py)
export type MarkRow = { player: string; mark: number; rank: number; of: number; games: number; line: string; best: string; best_match: string };
export type Pick = { player: string; role: string; gain: number; clears: boolean; keeper: boolean; spinner: boolean; country: string;
  capped: boolean; unsure: boolean; bat: string; bowl: string; raw_bat: string; raw_bowl: string };
export type Advice = { player: string; role: string; why: string; verdict: string; own: { bat: string; bowl: string; raw_bat: string; raw_bowl: string }; picks: Pick[] };
export type ReportCard = { series: string; label: string; format: string; section: string; start: string; end: string; players: MarkRow[];
  earlier: { label: string; series: string; format: string; top: { player: string; mark: number }[] }[]; advice: Advice[] };
export type BannerTile = Banner & { position: [string, string, number, number] | null };
export type SeriesItem = { key: string; opp: string; event: string; section: string; start: string; end: string; won: number; lost: number;
  other: number; played: number; tournament: boolean };
export type SectionBlock = {
  section: string; season: string; missing: Record<string, string>;
  so_far: { last5: Outcome[]; line: string; card: { subject: string; grade: string; why: string }[] } | null;
  squad: (SquadRow & { recent: boolean })[] | null;
  stars: { bat: { player: string; runs: number; average: number | null; form: string }[]; bowl: { player: string; wickets: number; economy: number | null }[] } | null;
  alerts: string[] | null; headlines: string[] | null; milestones: { player: string; chasing: string; needs: string }[] | null;
  how_you_win: { first: { pct: string; won: number; decided: number }; second: { word: string; pct: string; won: number; decided: number }; extra: string } | null;
  rivals: { rows: { opponent: string; played: number; record: string; win_pct: string; favourite: boolean; bogey: boolean }[];
    next: { team: string; note: string }[] } | null;
  trophies: { section: string; season: string; how: string; runners_up: string }[] | null;
  records: { what: string; detail: string }[] | null;
};
export type MyTeam = {
  teams: string[]; team: string; mine: boolean; missing: Record<string, string>; sections?: string[]; section?: string;
  banner?: { tiles: BannerTile[]; caption: string } | null; ticker?: Result[] | null;
  latest?: { result: Result; kicker: string; name: string; report: string } | null;
  after?: { opponent: string; date: string; lines: { k: string; text: string; up: boolean | null }[]; news: string[];
    form: { player: string; arrow: string; text: string }[]; match_id: string } | null;
  next_up?: { played: number; total: number; next: { what: string; venue: string; when: string; opponent: string;
    chance: { win: number; draw: number | null; lose: number } | null } | null; under_way: string[] } | null;
  report?: ReportCard | null; season?: Calendar | null; forms?: { section: string; results: Result[]; form: Form }[] | null;
  series?: SeriesItem[] | null; venues?: Venues | null; winners?: Winners | null; scores?: Scores | null;
  history?: { season: string; section: string; played: number; won: number; lost: number; drawn: number; tied: number;
    no_result: number; win_pct: number | null; finish: string }[] | null;
  notes?: { id: string; date: string; home: string; away: string; note: string }[] | null;
  block?: SectionBlock | null;
};
