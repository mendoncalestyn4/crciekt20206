// Every player's name in the career (from /api/names), so a name inside a sentence or a chart opens the player menu
// like a name in a list does. Sentences are read word by word: two to four words in a row that make a player's name
// ("S Gill", "Q de Kock", "N Kumar Reddy"), with a trailing 's ("Y Jaiswal's 47") left outside the name.
import { useQuery } from "@tanstack/react-query";
import { createContext, useContext, useMemo, type ReactNode } from "react";
import { get } from "../api";

type Names = { set: Set<string>; longest: number };
const NamesContext = createContext<Names>({ set: new Set(), longest: 0 });
export const useNames = () => useContext(NamesContext);

export function NamesProvider({ on, children }: { on: boolean; children: ReactNode }) {
  const q = useQuery({ queryKey: ["names"], queryFn: () => get<{ names: string[] }>("/api/names"), enabled: on, retry: false, staleTime: Infinity });
  const value = useMemo<Names>(() => {
    const names = q.data?.names ?? [];
    return { set: new Set(names), longest: Math.max(0, ...names.map((n) => n.split(" ").length)) };
  }, [q.data]);
  return <NamesContext.Provider value={value}>{children}</NamesContext.Provider>;
}

const WORD = /[\p{L}\p{N}'’.-]+/gu;

/** The player names in `text`, as [start, end, name], left to right; the longest name wins where two overlap. */
export function findNames(text: string, names: Names): [number, number, string][] {
  if (!names.set.size) return [];
  const words = [...text.matchAll(WORD)].map((m) => [m.index ?? 0, (m.index ?? 0) + m[0].length] as const);
  const out: [number, number, string][] = [];
  for (let i = 0; i < words.length; i++) {
    for (let len = Math.min(names.longest, words.length - i); len >= 2; len--) {
      const start = words[i]![0];
      let end = words[i + len - 1]![1];
      let s = text.slice(start, end);
      if (/ {2,}|[^\p{L}\p{N}'’. -]/u.test(s)) continue;   // the words must sit side by side, one space apart
      if (/['’]s$/.test(s) && !names.set.has(s)) { s = s.slice(0, -2); end -= 2; }
      if (s.endsWith(".") && !names.set.has(s)) { s = s.slice(0, -1); end -= 1; }
      if (names.set.has(s)) { out.push([start, end, s]); i += len - 1; break; }
    }
  }
  return out;
}

/** A sentence in which every player's name opens the player menu. Anything that isn't plain text is left as it is. */
export function T({ children }: { children: ReactNode }) {
  const names = useNames();
  if (typeof children !== "string") return <>{children}</>;
  const found = findNames(children, names);
  if (!found.length) return <>{children}</>;
  const out: ReactNode[] = [];
  let last = 0;
  for (const [a, b, name] of found) {
    if (a > last) out.push(children.slice(last, a));
    out.push(<span key={a} className="pmenu pin" data-player={name} role="button" tabIndex={0} title={`${name}: player page, batting, bowling, story`}>
      {children.slice(a, b)}</span>);
    last = b;
  }
  out.push(children.slice(last));
  return <>{out}</>;
}
