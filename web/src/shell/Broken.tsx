// A page that breaks while it's being drawn shows a plain note instead of a blank screen, and the problem is noted in
// Settings → Problems. Going to another page (or this one again) starts afresh.
import { Component, type ErrorInfo, type ReactNode } from "react";
import { Link } from "react-router";
import { Tile } from "../kit/base";
import { reportProblem } from "../problems";
import { useReady } from "../ready";

function Fallback({ what }: { what: string }) {
  useReady(true);
  return (
    <div className="grid"><Tile span={12} title="This page couldn't be shown">
      <div className="plain">Something went wrong drawing it ({what}). It's noted in <Link to="/settings">Settings → Problems</Link>,
        where you can copy it to send. Other pages still work.</div>
    </Tile></div>
  );
}

export class Broken extends Component<{ at: string; children: ReactNode }, { what: string | null; at: string }> {
  state = { what: null as string | null, at: this.props.at };

  static getDerivedStateFromError(e: unknown) {
    return { what: e instanceof Error ? `${e.name}: ${e.message}` : String(e) };
  }

  static getDerivedStateFromProps(p: { at: string }, s: { what: string | null; at: string }) {
    return p.at !== s.at ? { what: null, at: p.at } : null;   // a new page: try again
  }

  componentDidCatch(e: unknown, info: ErrorInfo) {
    const what = e instanceof Error ? `${e.name}: ${e.message}` : String(e);
    reportProblem(what, `${e instanceof Error ? e.stack ?? "" : ""}\n${info.componentStack ?? ""}`.trim());
  }

  render() {
    return this.state.what !== null ? <Fallback what={this.state.what} /> : this.props.children;
  }
}
