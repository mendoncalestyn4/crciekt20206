// When a page has its numbers and every chart has finished drawing, it is fitted (nothing spills out of its tile) and
// marked ready: <body data-ready="1">. The browser tests wait for that.
import { useEffect } from "react";
import { refit } from "./fit";

export function useReady(ok: boolean, key: unknown = null): void {
  useEffect(() => {
    delete document.body.dataset.ready;
    if (!ok) return;
    let stop = false, rounds = 0;
    const idle = () => (window.chartsDrawing ?? 0) === 0;
    const wait = () => {
      if (stop) return;
      if (!idle()) { window.setTimeout(wait, 50); return; }
      // fitting can move tiles and so resize a chart, which redraws it: ready only when the charts are still idle after
      refit(() => window.setTimeout(() => {
        if (stop) return;
        if (idle() || ++rounds > 5) document.body.dataset.ready = "1";
        else wait();
      }, 120));
    };
    void document.fonts.ready.then(() => requestAnimationFrame(wait));
    return () => { stop = true; };
  }, [ok, key]);
}
