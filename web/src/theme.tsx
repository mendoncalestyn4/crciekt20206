// Your team's colours on every page: the server's colour tokens (server/theme.py) as CSS variables, and the same
// tokens for the charts.
import { createContext, useContext, useLayoutEffect, type ReactNode } from "react";
import type { Theme } from "./api";

const ThemeContext = createContext<Theme | null>(null);

export function useTheme(): Theme {
  const t = useContext(ThemeContext);
  if (!t) throw new Error("useTheme outside ThemeProvider");
  return t;
}

export function ThemeProvider({ theme, children }: { theme: Theme; children: ReactNode }) {
  useLayoutEffect(() => {
    const s = document.documentElement.style;
    for (const [k, v] of Object.entries(theme)) if (typeof v === "string") s.setProperty(`--${k.replace(/_/g, "-")}`, v);
    s.setProperty("--line1", theme.line[0]);
    s.setProperty("--line2", theme.line[1]);
    document.body.classList.toggle("glow", theme.glow);
    document.body.classList.toggle("light", !theme.dark);
  }, [theme]);
  return <ThemeContext.Provider value={theme}>{children}</ThemeContext.Provider>;
}
