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

/** Keep the section, season, team or competition you just picked, so every page opens on it (the current site's
 * remembered picks). `as` renames a page's own key (e.g. Opponent preview's format is a section). */
const KINDS = new Set(["section", "season", "team", "event"]);
export function remember(changes: Record<string, string>, as: Record<string, string> = {}) {
  for (const [k, v] of Object.entries(changes)) {
    const kind = as[k] ?? k;
    if (KINDS.has(kind) && v) void post("/api/remember", { kind, value: v }).catch(() => undefined);
  }
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
  win: string; loss: string; orange: string; led: string; led_ink: string; warm: string; cream: string; grey: string; violet: string; teal: string;
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
  groups: { series: string; opp: string; start: number; end: number; won: number; lost: number }[]; lines?: Three };
/** A shared piece's three lines under its chart (design/CHART_LINES.md), kept under its own `lines` key. */
export type Three = { is_: string; best: string; best_label?: string; for_: string };
export type Run = { o: Outcome; start: number; end: number };
export type Calendar = { year: number; start: string; end: string; results: Result[]; best: number | null;
  months: (Record_ & { year: number; month: number; names: string[]; extra: Result[] })[];
  formats: { section: string; kind: "multi" | "one" | "t20" }[]; streaks: Run[]; lines?: Three; record_lines?: Three; runs_lines?: Three };
export type Venues = { home: Record_; away: Record_; neutral: Record_; nation: boolean;
  hosts: (Record_ & { host: string; venue: "home" | "away" | "neutral"; outcomes: Outcome[] })[]; lines?: Three };
export type Strength = { id: string; date: string; section: string; opp: string; outcome: Outcome; me: number; them: number; gap: number };
export type Brief = { score: number; opp: string; date: string; result: string } | null;
export type BatFirst = { first: { played: number; won: number; lost: number }; chase: { played: number; won: number; lost: number };
  multi: boolean; avg_set?: number | null; lowest_defended?: Brief; highest_lost?: Brief; highest_chased?: Brief; lowest_missed?: Brief };
export type Scores = Record_ & { avg_made: number | null; avg_conceded: number | null; shows?: string; for_?: string; lines?: Three };
export type Winners = { players: { player: string; matches: { id: string; date: string; section: string; opp: string; headline: string }[] }[];
  wins: number; others: number; shows?: string; for_?: string; line?: string; lines?: Three };
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
    high_score_text: string; fours: number; sixes: number; hundreds: number; fifties: number; parts?: Parts }[];
  rating: { value: number; rank: number } | null;
};
export type Banner = { section: string; season: string; elo: number | null; moved: number | null; rank: number | null;
  teams: number; record: { played: number; won: number; lost: number; drawn: number; tied: number; no_result: number } };
export type Series = {
  id: string; section: string; team?: string; opp: string;
  story: { headline: string; deck: string; flow: string; won: number; lost: number; opponent: string; complete: boolean;
    results: Outcome[]; player_of_series: { player: string; team: string; runs: number; wickets: number; matches: number } | null };
  matches: Result[]; progress: { won: number; lost: number }[]; decider: boolean; shows?: string; for_?: string; lines?: Three;
  most_runs: { player: string; team: string; runs: number; balls: number; inns: number; outs: number; hs: number }[];
  most_wickets: { player: string; team: string; wickets: number; runs: number; balls: number; economy: number }[];
};
export type Elo = { table: { rank: number; team: string; elo: number; played: number; peak: number }[]; teams: string[];
  snaps: { date: string; elo: Record<string, number>; rank: Record<string, number> }[] };
export type SquadRow = { player: string; games: number; runs: number; average: number | null; strike_rate: number | null;
  wickets: number; economy: number | null; last5: string; form: string; bowled?: boolean; parts?: Parts };
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
export type FinderItem = { id: string; label: string; date: string; home: string; away: string; section: string; event: string; name: string; result: string;
  checked?: boolean };
export type Finder = { section: string; ticked: string[]; name: string; team: string; sections: string[]; teams: string[]; matches: FinderItem[];
  scores?: { results: Result[]; summary: Scores; team: string } | null };
export type BestGame = { id: string; rating: number; rank: number; of: number; home: string; away: string; date: string;
  section: string; event: string; name: string; result: string; why: string; finish: number; comeback: number; stakes: number; show: number };
export type BestGames = { section: string; team: string; rows: BestGame[] };
export type Excitement = { rating: number; rank: number; of: number; why: string; finish: number; comeback: number; stakes: number; show: number; lines?: Three };
export type WinPoint = { label: string; W: number | null; D: number | null; L: number | null; note: string };
export type WinChance = { none?: string; team1: string; team2: string; multi: boolean; starts: number[]; points: WinPoint[]; shows: string; for_: string;
  is_?: string; best?: string; best_label?: string };
export type WicketStep = { wicket: number; score: number; start: number; stand: number; unbroken: boolean; batters: string[] };
export type Wickets = { innings: { innings_no: number; team: string; total: string; all_out: boolean; label: string; steps: WicketStep[] }[];
  par: { wicket: number; par: number; innings: number }[] | null; section: string; shows: string; for_: string;
  is_: string; best: string; best_label: string };
export type MatchPage = {
  id: string; kicker: string; name: string; series: string; date: string; section: string; event: string; stage: string;
  home: string; away: string; home_score: string; away_score: string; result: string; player_of_match: string; rain: string; corrected?: string[];
  /** the "checked ✓" mark: every sum on the scorecard checked against the others when it was read */
  checked?: { ok: boolean; problems: string[]; checks: string[]; unclear?: string[] };
  source: string; note: string; match: Match; report: string; excitement: Excitement | null; win: WinChance | null; wickets: Wickets;
  sides: { team: string; best: { player: string; figures: string }[]; worst: { player: string; figures: string }[] }[];
  top_scores: { player: string; team: string; score: string; balls: number }[];
  best_bowling: { player: string; team: string; figures: string; overs: string }[];
};

// ------------------------------------------------------------------ My team (server/myteam.py)
export type MarkRow = { player: string; mark: number; rank: number; of: number; games: number; line: string; best: string; best_match: string };
export type Pick = { player: string; role: string; gain: number; clears: boolean; keeper: boolean; spinner: boolean; country: string;
  capped: boolean; shared: boolean; how: string; side: string; where: string; bat: string; bowl: string; raw_bat: string; raw_bowl: string };
export type ScoutingPage = { team: string; sections: { section: string; series: string; advice: Advice[]; none: string }[] };
export type Advice = { player: string; role: string; why: string; verdict: string; elsewhere?: string; own: { bat: string; bowl: string; raw_bat: string; raw_bowl: string }; picks: Pick[] };
export type ReportCard = { series: string; label: string; format: string; among: string; section: string; start: string; end: string; players: MarkRow[];
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
  lines_runs?: Three | null; lines_wickets?: Three | null;
  how_you_win: { first: { pct: string; won: number; decided: number }; second: { word: string; pct: string; won: number; decided: number }; extra: string } | null;
  rivals: { rows: { opponent: string; played: number; record: string; win_pct: string; favourite: boolean; bogey: boolean }[];
    next: { team: string; note: string }[] } | null;
  trophies: { section: string; season: string; how: string; runners_up: string }[] | null;
  records: { what: string; detail: string }[] | null;
};
export type MyTeam = {
  teams: string[]; team: string; mine: boolean; asked?: string; missing: Record<string, string>; sections?: string[]; section?: string;
  banner?: { tiles: BannerTile[]; caption: string; lines?: Three } | null; ticker?: Result[] | null;
  latest?: { result: Result; kicker: string; name: string; report: string } | null;
  after?: { opponent: string; date: string; lines: { k: string; text: string; up: boolean | null }[]; news: string[];
    form: { player: string; arrow: string; text: string }[]; match_id: string } | null;
  next_up?: { played: number; total: number; next: { what: string; venue: string; when: string; opponent: string;
    chance: { win: number; draw: number | null; lose: number } | null; aim?: string } | null; under_way: string[] } | null;
  report?: ReportCard | null; season?: Calendar | null; forms?: { section: string; results: Result[]; form: Form }[] | null;
  series?: SeriesItem[] | null; tug?: Series | null; venues?: Venues | null; winners?: Winners | null; scores?: Scores | null;
  history?: { season: string; section: string; played: number; won: number; lost: number; drawn: number; tied: number;
    no_result: number; win_pct: number | null; finish: string }[] | null;
  notes?: { id: string; date: string; home: string; away: string; note: string }[] | null;
  block?: SectionBlock | null;
  depth?: Depth | null;
  career?: { matches: number; sections: number; seasons: number; players: number; runs: number; wickets: number; headlines: string[] } | null;
};

// ------------------------------------------------------------------ Players (server/playerpage.py)
/** One bar of a split (a season, home or away...), with what the tooltip adds. */
export type Bar = { label: string; value: number | null; note?: string; n?: number; runs?: number; ref?: number };
/** The player against everyone here, for one band or position; `key`: the band that matters most in this format. */
export type Pair = { label: string; me: number | null; all: number | null; note?: string; key?: boolean };
export type Split = { title?: string; rows: Bar[]; shows: string; for_: string };
/** The three lines under a chart (design/CHART_LINES.md), written by the server; `shows` is the older second line. */
export type Lines = { is_?: string; best?: string; best_label?: string; shows?: string; for_?: string };
export type FormT = { values: number[]; rolling: (number | null)[]; labels: string[]; ids?: string[]; window: number; overall: number | null; shows: string; for_: string };
/** The standard batting or bowling table: `first` is "section" or "season", every other column a number as printed. */
export type RecordTableT = { cols: string[]; first: string; help: Record<string, string>; rows: Record<string, string | number | null>[] };
export type PlayersLanding = {
  players: { player: string; team: string; teams: string[]; matches: number; sections: string[] }[];
  squads: { team: string; section: string; season: string;
    players: { player: string; games: number; runs: number; average: number | null; wickets: number; economy: number | null; bowled?: boolean; parts?: Parts }[] }[];
};
export type Batting = {
  kpis: { innings: number; runs: number; average: number | null; strike_rate: number | null; high_score: string; hundreds: number; fifties: number;
    outs: number; balls: number };
  form: FormT; compare: ({ pool: number; values: Record<string, number> } & Lines) | null;
  runs_from: { fours: number; sixes: number; running: number; n4: number; n6: number; shows?: string; for_?: string; empty?: boolean } & Lines;
  seasons: Split; how_out: Split | null;
  danger: { key: string; rows: Pair[]; shows: string; for_: string } | null;
  funnel: { rows: { mark: number; pct: number | null; all_pct: number | null; highlight: boolean }[]; extra: string; shows: string; for_: string } | null;
  season_table: RecordTableT;
  splits: { overall: number | null; stronger: string; rows: Split[] };
  positions: { rows: Pair[]; best_position: number | null; is_?: string; best?: string; best_label?: string; shows: string; for_: string;
    table: { position: number; innings: number; runs: number; not_outs: number; average: number | null; strike_rate: number | null;
      fifties: number; hundreds: number; high: string; all_average: number | null; edge: number | null; best: boolean; small: boolean; parts?: Parts }[] } | null;
  came_in: Split & { press: number; overall?: number | null; rescue: { at: string; score: string; balls: number; against: string; date: string }[] };
  consistency: { bar: number; past_bar_pct: number | null; single_figures_pct: number | null; golden_ducks: number; conversion_pct: number | null };
  nemesis: Split | null; streaks: { streak: string; longest: number; current: number }[];
  chasing: { won_innings: number; won_average: number | null; lost_innings: number; lost_average: number | null; not_out_in_wins: number } | null;
  against: Split;
  /** formats ticked together: the parts shown one block per format (server/playerpage.py _several) */
  each?: Partial<{ [K in "positions" | "danger" | "funnel" | "came_in" | "consistency" | "streaks"]: Each<NonNullable<Batting[K]>>[] }>;
};
/** One format's own block of a part, when several formats are ticked together. */
export type Each<X> = { section: string; data: X | null; missing?: string };
export type Bowling = {
  kpis: { wickets: number; average: number | null; economy: number | null; strike_rate: number | null; best: string; hauls: number;
    runs: number; balls: number; innings: number };
  form: FormT; seasons: Split; how_wickets: Split | null;
  match_pattern: { none?: string; first: string; second: string; both: string; best: string; shows?: string; for_?: string } | null;
  with_without: { rows: { label: string; spells: number; wickets: number; economy: string; maidens: string; parts?: Parts }[]; shows?: string; for_?: string };
  season_table: RecordTableT; quality: Split | null; bunnies: Split | null; streaks: { streak: string; longest: number; current: number }[];
  splits: { overall: number | null; rows: Split[] };
  each?: Partial<{ [K in "match_pattern" | "with_without" | "streaks"]: Each<NonNullable<Bowling[K]>>[] }>;
};
export type Story = {
  impact: { rows: { label: string; value: number; won: boolean; note: string; id?: string }[]; shows: string; for_: string } | null;
  rank: { rows: { season: string; runs_rank: number | null; runs_of: number | null; wickets_rank: number | null; wickets_of: number | null }[]; shows: string; for_: string; empty?: boolean } & Lines | null;
  milestones: { unit: string; rows: { milestone: string; took: string; fastest: string; date: string }[] };
  badges: { badge: string; detail: string; id: string; date: string }[];
  firsts: { date: string; what: string; detail: string; id: string; against: string }[];
  fires: { rows: { label: string; times: number; when: string; other: string }[]; none: string };
  quirks: string[];
  compare: { seasons: string[]; per: Record<string, Record<string, { v: number | null; text: string; better: "high" | "low" | null }>> } | null;
  each?: Partial<{ [K in "rank" | "compare" | "milestones" | "fires"]: Each<NonNullable<Story[K]>>[] }>;
};
export type Bounce = { shown: boolean; poor: number; followed: number; after: string; usual: string; after_avg: number | null;
  usual_avg: number | null; line: string };
export type PlayerPage = {
  player: string; teams: string[]; matches: number; missing: Record<string, string>;
  card: { matches: number; sections: number; runs: number; best_score: string; wickets: number; best_bowling: string; badges: number;
    last10: number[]; last10_is?: string; last10_best?: string; last10_for?: string; badge_list: { badge: string; detail: string; times: number }[] } | null;
  bat_table: RecordTableT | null; bowl_table: RecordTableT | null;
  formats: { rows: { section: string; matches: number; runs: number; average: number | null; bat_vs: number | null; strike_rate: number | null;
    sr_vs: number | null; wickets: number; bowl_average: number | null; bowl_vs: number | null; best: boolean; parts?: Parts }[]; shows: string; for_: string } | null;
  share: { section: string; season: string; team: string; matches: number; team_matches: number; runs: number; team_runs: number;
    run_share: number | null; wickets: number; team_wickets: number; wicket_share: number | null }[] | null;
  won: { id: string; section: string; opp: string; date: string; headline: string }[] | null;
  winners?: (Winners & { line: string }) | null;
  big?: { none: string; section?: string; rows?: { team: string; big: number; ordinary: number; big_bat: string; ord_bat: string;
    big_bowl: string; ord_bowl: string; big_sr: string; ord_sr: string; big_econ: string; ord_econ: string }[] } | null;
  countries?: (GridT & { nation: boolean }) | null;
  bounce?: { bat?: Bounce; bowl?: Bounce } | null;
  marks: { series: string; team: string; label: string; mark: number; rank: number; of: number; line: string; best: string; best_match: string }[] | null;
  journey: { first: string; last: string; team: string; section: string; season: string; matches: number; runs: number; wickets: number }[] | null;
  section: string; season: string; sections: string[]; seasons: string[];
  /** the formats ticked (one, or several counted together); one_length: they are all the same length of game */
  ticked: string[]; one_length?: boolean;
  each?: { bat_innings?: Each<ByInnings>[]; bowl_innings?: Each<ByInnings>[]; profile?: Each<NonNullable<PlayerPage["profile"]>>[] };
  role: { role: string; tags: string[]; usual_position: number } | null;
  tabs: string[]; open: string; batting: Batting | null; bowling: Bowling | null;
  bat_innings?: ByInnings | null; bowl_innings?: ByInnings | null;
  story: Story | null;
  profile?: ({ attributes: Attributes; report: ScoutReport; show: ("bat" | "bowl")[]; other: string } & Lines) | null;
};

// ------------------------------------------------------------------ Innings by innings (ccstats/byinnings.py): sections the tile switches
// between, each a table whose columns say how to show them (n a figure, m a dim figure, d a difference where + is better, x text)
export type InningsMarks = { slot: string; label: string; innings: number; small: boolean; best?: boolean; weakest?: boolean };
export type InningsCol = { k: string; label: string; t: "n" | "m" | "d" | "x"; dec: number; help: string; unit: string };
export type InningsRow = InningsMarks & Record<string, string | number | boolean | null>;
export type InningsView = { key: string; label: string; cols: InningsCol[]; rows: InningsRow[]; total?: Record<string, string | number | null>;
  shows: string; for_: string; parts?: Parts[]; total_parts?: Parts };
export type ByInnings = { kind: string; title: string; right: string; views: InningsView[]; rule: string; note: string };

// ------------------------------------------------------------------ Attributes, scout report, squad depth, inbox (ccstats/attributes.py, ccstats/depth.py)
export type Attr = { name: string; score: number | null; text: string };
export type Attributes = { section: string; kind: string; bat: Attr[]; bowl: Attr[]; bat_overall: number | null; bowl_overall: number | null;
  pool: { bat: number; bowl: number }; short: Record<string, string> };
export type ScoutReport = { verdict: string; role?: string; overall?: number; main?: string; strengths: string[]; weaknesses: string[]; notes: string[]; none: string };
export type DepthPlayer = { player: string; starts: boolean; rating: number | null; spinner: boolean; marks: number[]; games: number };
export type Depth = { section: string; series: string; roles: { role: string; usual: number; starters: DepthPlayer[]; backups: DepthPlayer[];
  waiting: { player: string; side: string; gain: number | null; clears: boolean; bat: string; bowl: string; raw_bat: string; raw_bowl: string }[] }[] };
export type InboxMsg = { date: string; kind: "result" | "struggling" | "knocking" | "milestone"; title: string; body: string; section: string;
  series: string; player: string; match: string };
export type InboxItem = InboxMsg & { id: string; team: string; read: boolean };
export type InboxPage = { teams: string[]; messages: InboxItem[]; unread: number };

// ------------------------------------------------------------------ Teams (stage 2)
export type GridT = { cols: string[]; rows: (string | number | null)[][]; num: number[]; hi: boolean[]; links: (string | null)[]; dim?: boolean[]; bold?: number;
  badges?: number[]; parts?: (Parts | null)[] };   // badges: the columns that name teams ("India", or "India v Australia"), each shown with its badge
/** The numbers a row's average, strike rate or economy is made from, when the row doesn't show them (web/src/howto.ts):
 *  batting runs, times out, balls faced and innings; bowling runs, balls, wickets and innings; `what` names what the average is
 *  over when it isn't times out ("stands"). */
export type Parts = { runs?: number; outs?: number; bf?: number; inns?: number; what?: string; bruns?: number; bballs?: number; wkts?: number; binns?: number };
export type Noted = { title?: string; right?: string; note?: string; none?: string };
export type NGrid = GridT & Noted;
export type SignedBar = { label: string; value: number; text: string; note?: string };
export type RaceLine = { team: string; points: { round: number; position: number; points: number | null; played: number }[] };
export type Explained = { shows: string; for_: string; is_?: string; best?: string; best_label?: string };
export type TeamChoice = { section: string; matches: number; seasons: string[]; teams: string[]; todo: string[]; neutral: boolean };
export type TeamHead = { none: string; elsewhere?: string[]; kpis?: { k: string; v: string; how?: string }[]; last5?: string[]; runs?: string;
  venue_note?: string; ratings?: string; limited?: boolean };
export type Contribution = { player: string; matches: number; runs: number; run_share: number; wickets: number; wicket_share: number };
export type TeamBody = {
  missing: Record<string, string>;
  vs_average?: ({ title: string; right: string; rows: SignedBar[] } & Explained) | null;
  strength?: ({ rows: Strength[]; lanes: string[] } & Explained) | null;
  venues?: (Venues & Explained) | null;
  streaks?: ({ results: Result[]; streaks: Run[] } & Explained) | null;
  top_bat?: ({ rows: { player: string; team: string; runs: number; note: string }[] } & Explained) | null;
  top_bowl?: ({ rows: { player: string; team: string; wickets: number; note: string }[] } & Explained) | null;
  depth?: ({ rows: Bar[] } & Explained) | null;
  stands?: ({ rows: Bar[] } & Explained) | null;
  openers?: GridT | null; collapses?: GridT | null; carry?: (GridT & Explained) | null; usual?: (GridT & Explained & { line?: string }) | null; big_stands?: GridT | null;
  contribution?: ({ rows: Contribution[]; team_runs: number; team_wickets: number } & Explained) | null;
  how_they_play?: ({ rows: SignedBar[]; every: boolean } & Explained) | null;
  discipline?: ({ rows: { player: string; team: string; extras: number; note: string }[]; every: boolean } & Explained) | null;
  every_team?: NGrid | null;
  bat_first?: NGrid | null; close?: (NGrid & { games: GridT | null }) | null; start?: NGrid | null; targets?: NGrid | null;
  dominance?: NGrid | null; comebacks?: NGrid | null;
  stages?: GridT | null; bounce?: GridT | null; opponents?: GridT | null; fortress?: NGrid | null; revenge?: GridT | null;
  race?: ({ options: string[]; picked?: string; none: string; lines: RaceLine[] } & Explained) | null; halves?: GridT | null;
  has_series?: boolean; multi?: boolean; first_blood?: GridT | null; deciders?: GridT | null; second_innings?: GridT | null;
  follow_on?: GridT | null;
  best_xi?: NGrid | null;
  changes?: { right: string; steps: { title: string; ins: GridT; outs: GridT }[]; none: string; note: string } | null;
  results?: GridT | null;
};
/** section: the competitions ticked ("Tests|ODIs", counted together); name: as the page says them ("Tests + ODIs");
 *  seasons: the competition's own, or April-to-March years when several are ticked; played: the team's competitions. */
export type TeamPage = { choices: TeamChoice[]; played?: string[]; page: { section: string; ticked: string[]; name: string; seasons: string[];
  season: string; team: string; venue: string; tab: string; tabs: string[]; head: TeamHead; body: TeamBody | null } | null };
export type TapeRow = { label: string; a: number; b: number; at: string; bt: string; a_better: boolean; b_better: boolean };
export type Dot = { player: string; team: string; x: number; y: number; note: string[] };
export type TeamBarRow = { player: string; team: string; value: number; note: string[] };
export type TvtBody = {
  missing: Record<string, string>;
  tiles?: { team: string; sub: string; figures: { k: string; v: string; up: boolean }[] }[] | null;
  tape?: ({ rows: TapeRow[]; verdict: string } & Explained) | null;
  meetings?: { none: string; line: string; rows: { id: string; date: string; stage: string; match: string; result: string }[] } | null;
  bat_first?: ({ sides: (BatFirst & { team: string })[] } & Explained) | null;
  bat_dots?: ({ points: Dot[]; slope: number; line: string; x: string; y: string; keys: string[] } & Explained) | null;
  bowl_dots?: ({ points: Dot[]; slope: number; line: string; x: string; y: string; keys: string[] } & Explained) | null;
  above?: ({ rows: TeamBarRow[] } & Explained) | null;
  saved?: ({ rows: TeamBarRow[] } & Explained) | null;
  top?: GridT | null;
};
export type TvtPage = { choices: TeamChoice[]; page: { section: string; ticked: string[]; name: string; seasons: string[]; season: string; teams: string[]; todo: string[]; a: string; b: string;
  others?: string[]; which: string; ground: string; grounds: { key: string; label: string }[]; where_help?: string; info: string; none: string;
  body?: TvtBody } | null };
export type Fig = { k: string; v: string };
export type DangerMan = { player: string; points: number; matches: number; role: "bat" | "bowl" | "both"; line: string;
  innings: { id: string; date: string; opp: string; text: string }[]; spells: { id: string; date: string; opp: string; text: string }[] };
export type HowTheyPlay = { none: string; season?: string; this?: string; last?: string; showing_last?: boolean; matches?: number;
  note?: string; summary?: string; bowling?: string[]; batting?: string[]; parts?: GridT; rules?: string };
export type PreviewBody = {
  missing: Record<string, string>; none?: string; how?: HowTheyPlay | null;
  danger?: ({ none: string; season?: string; note?: string; men: DangerMan[] } & Partial<Explained>) | null;
  big_players?: ((GridT & Explained & { none: "" }) | { none: string }) | null;
  by_country?: ({ none: string; venues: Record<string, (GridT & { none: ""; place: string }) | { none: string; place: string }> } & Partial<Explained>) | null;
  h2h?: { never: string; other?: string; kpis?: Fig[]; last5?: string[]; how?: string; typical?: string;
    keys?: { title: string; rows: string[][]; dim: boolean[] }[];
    cards?: { id: string; date: string; event: string; sides: { team: string; score: string; top_bat: string; top_bowl: string }[]; potm: string; story: string }[] } | null;
  matchups?: (NGrid | { title: string; none: string })[] | null;
  bat_first?: ((BatFirst & Explained & { who: string; none?: undefined }) | { none: string }) | null;
  where?: ((Venues & Explained & { who: string; none?: undefined }) | { none: string }) | null;
  batters?: ({ rows: { player: string; team: string; runs: number }[]; notes: string[] } & Explained) | null;
  bowlers?: ({ rows: { player: string; team: string; wickets: number }[]; notes: string[] } & Explained) | null;
  key_wicket?: GridT | null; weak_spot?: ({ rows: SignedBar[] } & Explained) | null; attack?: NGrid | null; styles?: GridT | null;
  chase?: (NGrid & { extremes: { label: string; text: string; id: string }[] }) | null;
  venues?: Record<string, NGrid> | null; big?: GridT | null; trend?: { last: string[]; line: string } | null;
  how_out?: ({ rows: Bar[]; outs?: number } & Explained) | null; depth?: ({ rows: Bar[] } & Explained) | null;
  sbs?: NGrid | null;
  xi?: { title: string; right: string; none: string; bat: GridT | null; bowl: GridT | null; lines: string[]; note?: string } | null;
};
export type PreviewPage = { choices: { section: string; matches: number }[]; section: string; formats: string[]; format: string;
  mine_opts: string[]; mine: string; opp: string; opp_opts: { team: string; label: string }[]; none: string; elsewhere: string[];
  tabs: string[]; tab: string; mine_note?: string; where_note?: string; mu?: boolean; cur?: boolean; htp?: string;
  head?: { missing: Record<string, string>; kpis: Fig[]; last5: string[]; caption: string; where_default: string;
    predicted?: Record<string, { line: string; steps: GridT; note: string }> | null; plan?: string[] | null;
    aim?: { none: string; kind: string; note?: string; rests?: string; few?: string; sure?: string;
      venues: Record<string, { line: string; warn?: string; they?: string; meetings?: GridT | null; none?: string; games?: GridT | null }> } | null };
  body?: PreviewBody };

// ------------------------------------------------------------------ Settings → Problems
export type Problem = { id: string; kind: "part" | "server" | "page" | "scorecard"; where: string; what: string; detail: string;
  career: string; first: string; last: string; count: number };
export type ProblemsPage = { problems: Problem[]; count: number; report: string };

type Noneable<X> = X | { none: string };
export type PlannerPage = { choices: TeamChoice[]; section: string; season: string; teams: string[]; team: string; tabs: string[]; tab: string;
  none: string; tip: string;
  body?: { missing: Record<string, string>; none?: string; recent?: boolean;
    qualification?: { events: string[]; event: string; games: number; places: number; default_games: number; default_places: number;
      line: string; table: GridT | null; note: string; none?: string } | null;
    order?: { none: string; top7?: GridT | null; every?: GridT } | null;
    plan?: Noneable<NGrid> | null; knocking?: Noneable<NGrid> | null; batting?: Noneable<GridT> | null; bowling?: Noneable<GridT> | null } };
export type LeaderRow = { player: string; team: string; note: string } & Record<string, string | number>;
export type RivalriesPage = { choices: TeamChoice[]; section: string; ticked: string[]; name: string; none: string; table?: NGrid; pairs: { key: string; label: string }[]; pick: string;
  close?: { missing: Record<string, string>; a: string; b: string; runs?: ({ rows: LeaderRow[] } & Explained) | null;
    wickets?: ({ rows: LeaderRow[] } & Explained) | null; meetings?: GridT | null; streak?: { now: string; longest: string; note: string } } };

// ------------------------------------------------------------------ Seasons · Competitions (stage 2)
export type CompGrid = GridT & { note?: string; label?: string; teams?: string[]; heading?: string };
export type OddsLine = { team: string; points: { date: string; chance: number }[] };
export type KoCard = { id: string; date: string; result: string; teams: { team: string; score: string; won: boolean }[] };
export type CompRace = { knockouts: boolean; many: boolean; games: number; places: number; extra: number; default_games: number;
  default_places: number; default_extra: number; state: string; what: string; teams: string[]; pick: string; groups: CompGrid[];
  lines: OddsLine[]; shows: string; for_?: string; note: string; caption?: string; is_?: string; best?: string; best_label?: string; };
export type CompPage = { choices: { event: string; matches: number; seasons: string[] }[]; event: string; season: string; none: string;
  every?: GridT & { note?: string };
  missing?: Record<string, string>; bilateral?: boolean; race_on?: boolean;
  league?: { title: string; groups: CompGrid[]; note: string } | null;
  knockouts?: { rounds: { round: string; cards: KoCard[] }[]; champion: string } | null;
  series?: { table: CompGrid; each: { label: string; team: string; id: string; teams: string; matches: GridT }[] } | null;
  series_pick?: number;
  series_one?: { missing: Record<string, string>; team: string; ladder?: Series | null; xi?: (NGrid & { title: string }) | null } | null;
  wtc?: { cycles: { key: string; label: string }[]; cycle: string; tables: Record<string, CompGrid>; note: string } | null;
  race?: { missing: Record<string, string>; race?: CompRace | null } };

// ------------------------------------------------------------------ Seasons · Season (stage 2)
export type CalChip = { kind: "W" | "L" | "D" | "T" | "NR" | "UP" | "N"; text: string; tip: string; id: string | null; opp?: string;
  long?: string; event?: string; games?: { id: string; text: string; result: string }[] };
export type CalMonth = { key: string; year: number; month: number; name: string; first: number; days_in: number;
  days: Record<string, CalChip[]>; notes: { kind: "played" | "tocome"; text: string }[]; won: number; lost: number; played: number;
  extra?: CalChip[]; mark?: string; best?: boolean };
export type SeasonPage = { teams: string[]; team: string; tabs: string[]; tab: string; none: string;
  ranks?: { season: string; note?: string; rows: { section: string; teams: number; matches: number; runs: number; wickets: number;
    runs_rank: number; wickets_rank: number; runs_top: string; wickets_top: string }[] };
  calendar?: { view: "season" | "month"; seasons: { key: string; label: string }[]; season: string; months: { key: string; label: string }[];
    month: string; today: string; grid: CalMonth[]; caption?: string; shows?: string; for_?: string; none?: string; is_?: string; best?: string; best_label?: string; };
  series?: { none: string; live: (GridT & { note?: string }) | null; done: GridT | null; note?: string; tugs?: (Series & { title: string })[] };
  progress?: { none: string; rows: { name: string; event: string; season: string; played: string; pct: number | null; stage: string; leader: string }[]; note?: string } };

// ------------------------------------------------------------------ Seasons · Season review and Honours (stage 2)
export type XiGrid = (GridT & { title: string; note?: string }) | { title: string; none: string };
export type ReviewPage = { choices: { key: string; section: string; season: string; label: string }[]; pick: string; section: string;
  season: string; none: string; wrapped?: { missing: Record<string, string>; wrapped?: Wrap | null };
  winners?: { missing: Record<string, string>; winners?: (Winners & { team: string; yours: boolean }) | null };
  year?: { missing: Record<string, string>; year?: { title: string; counts: { label: string; value: number }[]; cricketer: GridT | null;
    formats: { format: string; matches: number; player: GridT | null; most: string; xi: XiGrid }[]; note: string } | null };
  season_review?: { missing: Record<string, string>; review?: { title: string; complete: boolean; matches: number; champion: string;
    champions: { team: string; how: string; runners_up: string; section: string }[]; final: { id: string; teams: string; result: string; pom: string } | null;
    leaders: GridT | null; xi: XiGrid; best: GridT | null; upset: { id: string; text: string; why: string } | "";
    records: (GridT & { note?: string }) | null; records_none: string;
    report_cards: { team: string; card: { subject: string; grade: string; why: string }[] }[] } | null };
  mvp?: { missing: Record<string, string>; mvp?: { points: "impact" | "ipl"; choose: boolean; table: GridT | null; none?: string;
    bars: { player: string; team: string; value: number; note: string }[]; shows: string; for_: string; note: string; is_?: string; best?: string; best_label?: string; } | null } };
export type WrapSlide = { key: string; kicker: string; head: string; big: string; unit: string; lines: string[]; id: string | null };
export type Wrap = { none: string; formats: string[]; format: string; teams: string[]; team: string; section?: string; season?: string;
  slides?: WrapSlide[]; note?: string ; view?: string };
export type HonoursPage = { tabs: string[]; tab: string; none: string; boards?: (GridT & { title: string })[]; note?: string;
  cabinet?: GridT | null; cabinet_none?: string };

// ---------------------------------------------------------------- stage 3: Leaders and records
export type SbsBar = { player: string; team: string; value: number; text: string; hi: boolean; sub?: string; id?: string };
export type SbsDot = { title: string; x_label: string; y_label: string; line: "slope" | "flat"; value: number | null; better_below: boolean;
  decimals: number; points: { player: string; team: string; x: number; y: number; ranked: boolean; named: boolean; hi: boolean }[];
  explain: [string, string][] } & Explained;
export type StatByStat = {
  choices: { section: string; matches: number }[]; ticked: string[]; section: string; seasons: string[]; picked_seasons: string[];
  discs: string[]; disc: string; events: string[]; picked_events: string[]; teams: string[]; picked_teams: string[];
  venues: string[]; picked_venues: string[]; groups: string[]; picked_groups: string[];
  single: boolean; picked_single: number[]; view: "Best" | "Worst"; tops: string[]; top: string;
  stats?: { id: string; label: string }[]; stat?: string; measures?: { id: string; label: string }[]; measure?: string;
  minimum?: { options: { v: number; label: string }[]; value: number }; names?: string[]; find?: string; only?: string[];
  statdef?: { label: string; definition: string; note: string }; none?: string; found?: string;
  bars?: { title: string; rows: SbsBar[]; reference: number | null; decimals: number; lower: boolean } & Explained;
  dots?: SbsDot; table?: NGrid & { bold: number }; csv?: string;
};
export type RecTable = GridT & { title: string; near: string; short: boolean };
export type PacePart = { what: string; none?: string; record?: number | null;
  rows?: { player: string; team: string; value: number; now: number; matches: number; beats: boolean; note: string }[] } & Partial<Explained>;
export type RecordsPage = {
  choices: { section: string; matches: number }[]; ticked: string[]; section: string; seasons: string[]; season: string; tops: string[];
  top: string; teams: string[]; team: string; none?: string; where?: string; groups?: { group: string; tables: RecTable[] }[]; caption?: string;
  pace?: { title: string; parts: PacePart[]; note: string } | null;
  stands?: { wicket: number; rows: { place: number; runs: string; who: string; team: string; against: string; date: string; id: string }[] }[];
  games?: BestGame[]; runs?: NGrid; streaks?: ({ results: Result[]; streaks: Run[] } & Explained) | null;
  timeline?: { names: string[]; none?: string; pick?: string; unit?: string; end?: string;
    points?: { date: string; y: number; label: string; holder: string; id: string }[]; table?: GridT } & Partial<Explained>;
};
export type RankRow = { rank: number; player: string; team: string; rating: string; move: string; peak: string; peak_date: string;
  at_one: number; inns: number; series: number; how: string; mine: boolean };
export type RankingsPage = {
  choices: { section: string; matches: number }[]; ticked: string[]; section: string; tabs: string[]; tab: string;
  kinds: { id: string; label: string }[]; what: string; none?: string; rule?: string; combined?: boolean; latest?: string;
  rows?: RankRow[]; near?: { player: string; team: string; inns: number; rating: string; needs: string }[]; need?: number;
  table?: NGrid; bars?: { rows: SbsBar[] } & Explained;
  players?: string[]; picked?: string[]; lines?: { player: string; points: { date: string; rating: number; rank: number }[] }[] |
    ({ teams: { team: string; points: { date: string; elo: number; id: string }[] }[] } & Explained);
  peaks?: { rows: SbsBar[] } & Explained; reigns?: NGrid; is_?: string; best?: string; best_label?: string; for_?: string;
  teams?: string[]; elo?: { rows: SignedBar[] } & Explained; note?: string; units?: NGrid; team?: string;
  strength?: ({ rows: Strength[]; lanes: string[] } & Explained) | null;
  date?: string; first?: string; last?: string; ends?: { label: string; date: string }[];
};
export type Plaque = { player: string; team: string; date: string; id: string; route: string; also: string; figures: string;
  moments: { what: string; date: string; id: string }[]; mine: boolean };
export type HallPage = {
  choices: { section: string; matches: number }[]; ticked: string[]; section: string; tabs: string[]; tab: string; seasons: string[]; season: string;
  none?: string; rule?: string; plaques?: Plaque[]; next?: { player: string; team: string; share: number; needs: string }[];
  bars?: { rows: SbsBar[] } & Explained; big?: GridT | null; note?: string; table?: NGrid;
  teams?: string[]; team?: string; events?: { date: string; year: number; kind: string; what: string; who: string; id: string | null; section: string }[];
};
