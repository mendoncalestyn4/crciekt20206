// Settings: the careers on this PC (switch which one is on screen), and a preview of every nation's colours. The rest
// of the settings (adding careers, your teams, logos folder, backups, data check) come in stage 4.
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router";
import { get, post, type Careers } from "../api";
import { Tile } from "../kit/base";
import { useReady } from "../ready";
import { Head, useShell } from "../shell/Shell";

export function Settings() {
  const qc = useQueryClient();
  const go = useNavigate();
  const { nation } = useShell();
  const careers = useQuery({ queryKey: ["careers"], queryFn: () => get<Careers>("/api/careers") });
  const nations = useQuery({ queryKey: ["nations"], queryFn: () => get<{ nations: string[] }>("/api/nations") });
  const open = useMutation({ mutationFn: (name: string) => post("/api/careers/current", { name }), onSuccess: () => qc.invalidateQueries() });
  useReady(Boolean(careers.data && nations.data));
  return (
    <>
      <Head title="Settings" crumb="Careers and colours" />
      <div className="grid">
        <Tile span={7} title="Careers on this PC">
          {careers.data && !careers.data.careers.length && <div className="plain">No careers yet. Add one on the current site for now.</div>}
          <table className="c"><tbody>{careers.data?.careers.map((c) => (
            <tr key={c} className={c === careers.data?.current ? "me" : ""}><td><span className="pn" style={{ fontSize: 32 }}>{c}</span></td>
              <td className="r">{c === careers.data?.current ? <span className="tag">On screen</span>
                : <button className="btn quiet" onClick={() => open.mutate(c)} disabled={open.isPending}>Open</button>}</td></tr>))}</tbody></table>
          {careers.data?.folders.length ? <div className="note">Watching: {careers.data.folders.join(" · ")}</div> : null}
        </Tile>
        <Tile span={5} title="Colours">
          <div className="plain">The site wears your first national side's colours (the night look when you play as none). Preview another
            side's colours here: nothing is saved.</div>
          <div className="field"><label htmlFor="nation">Preview</label>
            <select id="nation" className="pick" value={nation} onChange={(e) => go(`/settings${e.target.value ? `?nation=${encodeURIComponent(e.target.value)}` : ""}`)}>
              <option value="">Your colours</option><option value="none">No national side (night)</option>
              {nations.data?.nations.map((n) => <option key={n} value={n}>{n}</option>)}</select></div>
          <div className="plain" style={{ marginTop: 14 }}><Link to={`/style-guide${nation ? `?nation=${encodeURIComponent(nation)}` : ""}`}>The style guide</Link> shows every piece in these colours.</div>
        </Tile>
        <Tile span={12} title="Coming in stage 4">
          <ul className="dots"><li>Add a career from a Scorecards folder, from .txt files or a .zip, or from a career file; download a career file</li>
            <li>Your teams (and the first-start question), the logos folder, weekly backups with restore, data check (merge, split, credit a catch)</li></ul>
        </Tile>
      </div>
    </>
  );
}
