// Anything that breaks in the browser is noted in Settings → Problems, so it can be sent to be fixed: an error on a
// page, a promise nobody caught, a part of a page that couldn't be drawn (the ErrorBoundary in the shell). The
// server notes its own problems itself (parts it couldn't work out, questions it couldn't answer).
import type { QueryClient } from "@tanstack/react-query";
import { ApiError } from "./api";

const seen = new Set<string>();
let client: QueryClient | null = null;
const clip = (s: string, n: number) => (s.length <= n ? s : `${s.slice(0, n - 1)}…`);

// what isn't the site's own problem: the browser's own noise, a script from elsewhere, the server not answering (it
// can't be told then), and the server's plain answers (its real failures it notes itself)
function ignore(what: string, err: unknown): boolean {
  if (err instanceof ApiError) return true;
  if (err instanceof DOMException && err.name === "AbortError") return true;
  return /^(Script error\.?|ResizeObserver loop.*|.*Failed to fetch.*|.*NetworkError.*|.*Load failed.*)$/i.test(what.trim());
}

export function reportProblem(what: string, detail = "", err: unknown = null): void {
  const where = window.location.pathname + window.location.search;
  if (!what.trim() || ignore(what, err)) return;
  const key = `${what}|${where}`;
  if (seen.has(key) || seen.size >= 30) return;   // once each, and never a flood
  seen.add(key);
  void fetch("/api/problems", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ report: { where, what: clip(what, 1500), detail: clip(detail, 5000) } }) })
    .then((r) => { if (r.ok) void client?.invalidateQueries({ queryKey: ["problems"] }); })
    .catch(() => { /* the server isn't answering: nothing to tell */ });
}

export function watchForProblems(queries: QueryClient): void {
  client = queries;
  window.addEventListener("error", (e) => {
    const err: unknown = e.error;
    const what = err instanceof Error ? `${err.name}: ${err.message}` : e.message || "";
    reportProblem(what, err instanceof Error ? err.stack ?? "" : `${e.filename}:${e.lineno}:${e.colno}`, err);
  });
  window.addEventListener("unhandledrejection", (e) => {
    const err: unknown = e.reason;
    const what = err instanceof Error ? `${err.name}: ${err.message}` : String(err ?? "");
    reportProblem(what, err instanceof Error ? err.stack ?? "" : "", err);
  });
}
