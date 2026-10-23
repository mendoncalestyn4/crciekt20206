// The chart kit's sizes and colours: the approved word and number scales, and the theme's colours for axes, values,
// my team's bars and everyone else's.
import type { Theme } from "../api";

export const TS = 1.45;   // words: about 45% bigger than the first mock-ups
export const SC = 1.05;   // numbers: about 5% bigger
export const ts = (px: number) => Math.round(px * TS);
export const sc = (px: number) => Math.round(px * SC);
export const NUMF = "Space Grotesk";

export function look(t: Theme) {
  return {
    AX: { axisLabel: { color: t.dim, fontFamily: "Inter", fontSize: ts(11) }, axisLine: { lineStyle: { color: t.edge } },
      axisTick: { show: false }, splitLine: { lineStyle: { color: t.split } } },
    VAL: (px: number) => ({ fontFamily: NUMF, fontWeight: 700, fontSize: sc(px), color: t.led }),
    TT: { backgroundColor: t.page, borderColor: t.edge, textStyle: { color: t.ink, fontFamily: "Inter" } },
    MINE: t.led,          // my team in every chart
    OTHER: t.other,       // everyone else
    glow: (colour: string) => (t.glow ? { shadowBlur: 10, shadowColor: colour } : {}),
  };
}
