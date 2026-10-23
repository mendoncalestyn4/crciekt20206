// My team: in stage 0, where the new site stands and what the style guide shows. The real home page comes in stage 1.
import { Link } from "react-router";
import { Hero, Tile } from "../kit/base";
import { useReady } from "../ready";
import { Head, useShell } from "../shell/Shell";

const STAGES: [string, string, string][] = [
  ["0", "Foundations", "The stats server, this shell, team colours, fonts, logos, the chart kit and its style guide."],
  ["1", "Core pages", "My team, Player profile, Match (summary and scorecard)."],
  ["2", "Teams and competitions", "Teams, Team v team, Opponent preview, Planner, Rivalries, Seasons."],
  ["3", "Leaders, records and insights", "Stat by stat, Records, Hall of fame, Rankings, Insights, Compare players."],
  ["4", "Fixtures and tools", "Fixtures, careers and uploads, backups, data check, the first-start question."],
  ["5", "Final checks and switch-over", "Every page checked, then this becomes Start Stats Pack.bat."],
];

export function Home() {
  const { career, noCareer, nation } = useShell();
  const team = career?.my_teams[0];
  useReady(Boolean(career) || noCareer);
  const keep = nation ? `?nation=${encodeURIComponent(nation)}` : "";
  return (
    <>
      <Head title="Good evening, captain" crumb={career ? `${team ?? "No team picked"} · ${career.name}` : "No career open yet"} />
      <div className="grid">
        <Hero logo={team} px={150} h={190} kicker="The new Stats Pack · a preview" title={team ?? "Stats Pack"} size={96}
          side={career ? ["This career", career.matches.toLocaleString("en-GB"), "matches"] : undefined} />
        {noCareer && <Tile span={12} title="No career yet">
          <div className="plain">Add a career on the current site for now (<b>Start Stats Pack.bat</b>): the new site sees it straight away.
            Adding careers here comes in stage 4.</div></Tile>}
        <Tile span={7} title="Stage 0 · foundations" right="you are here">
          <div className="plain">The look you chose (idea 4) is now a real website, in your team's colours, with the fonts and logos built in.
            The pages come next, stage by stage. Until then the current site keeps working, on the same careers.</div>
          <div style={{ marginTop: 18 }}><Link className="btn" to={`/style-guide${keep}`} style={{ textDecoration: "none", display: "inline-block" }}>Open the style guide</Link></div>
          <div className="note">Every chart and table piece, drawn from your own career.</div>
        </Tile>
        <Tile span={5} title="This career">
          {career ? <>
            <div className="plain"><b>{career.name}</b>: {career.matches.toLocaleString("en-GB")} matches, {career.sections.length} competitions.</div>
            <div className="plain">Your team{career.my_teams_picked.length === 1 ? "" : "s"}: <b>{career.my_teams_picked.join(", ") || "none picked yet"}</b></div>
            <div className="plain">{career.folder ? "New matches come in by themselves from your Scorecards folder:" : "No Scorecards folder is watched for this career."}</div>
            {career.folder && <div className="how" style={{ overflowWrap: "anywhere" }}>{career.folder}</div>}
          </> : <div className="plain">Open a career in Settings.</div>}
        </Tile>
        <Tile span={12} title="The stages">
          <table className="c"><tbody>{STAGES.map(([n, what, detail]) => (
            <tr key={n} className={n === "0" ? "me" : ""}><td style={{ width: 70 }}><span className="tn">{n}</span></td>
              <td style={{ width: 360 }}><span className="pn" style={{ fontSize: 30 }}>{what}</span></td><td><span className="plain">{detail}</span></td></tr>))}</tbody></table>
        </Tile>
      </div>
    </>
  );
}
