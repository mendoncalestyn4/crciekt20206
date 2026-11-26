// The sections still being built: what each will hold and in which stage, so every link works from the start.
import { useParams } from "react-router";
import { Tile } from "../kit/base";
import { useReady } from "../ready";
import { Head, SECTIONS } from "../shell/Shell";

export const PLANS: Record<string, { stage: string; crumb: string; items: string[]; from: string; title?: string }> = {
};

const PICKED: Record<string, string> = {};

export function Section({ path }: { path: string }) {
  const plan = PLANS[path]!;
  const label = plan.title ?? SECTIONS.find((s) => s.to === path)?.label ?? "";
  const { pick } = useParams();
  useReady(true, path + (pick ?? ""));
  return (
    <>
      <Head title={label} crumb={plan.crumb} />
      <div className="grid">
        {pick && <Tile span={12} title={`The ${PICKED[path] ?? "page"} you picked`}>
          <div className="hl" style={{ fontSize: 46, margin: "4px 0 6px" }}>{pick}</div>
          <div className="plain">Its page arrives with this section: {plan.stage.toLowerCase()}. The search already finds it.</div>
        </Tile>}
        <Tile span={7} title="Coming here" right={plan.stage}>
          <ul className="dots">{plan.items.map((x) => <li key={x}>{x}</li>)}</ul>
        </Tile>
        <Tile span={5} title="Until then">
          <div className="plain">The current site still has all of it: <b>{plan.from}</b>.</div>
          <div className="plain">Start it with <b>Start Stats Pack.bat</b>. Both sites read the same careers.</div>
        </Tile>
      </div>
    </>
  );
}

export function NotFound() {
  useReady(true);
  return (
    <>
      <Head title="Not found" crumb="There's no page here" />
      <div className="grid"><Tile span={12} title="Try the rail on the left, or search (Ctrl K)"><div className="plain">The address may be old or mistyped.</div></Tile></div>
    </>
  );
}
