// Nothing may spill out of its tile (the approved rule; design/mockups/check_fit.py checks it). After a page is
// drawn, and again when the window changes size:
//   * the latest-results strip shows only the results that fit;
//   * a table wider than its tile is scaled down to fit;
//   * a number or name reaching past its tile's edge, or text wider than its own box, shrinks just enough.
// Every change is undone first, so a wider window gets the full sizes back. Charts keep their own labels inside.

const shrunk = new Set<HTMLElement>();

function undo(): void {
  for (const el of shrunk) {
    el.style.fontSize = el.dataset.fitFs ?? "";
    el.style.zoom = el.dataset.fitZoom ?? "";
    delete el.dataset.fitFs;
    delete el.dataset.fitZoom;
  }
  shrunk.clear();
  document.querySelectorAll<HTMLElement>(".tk[data-fit-hidden]").forEach((k) => {
    k.style.display = "";
    delete k.dataset.fitHidden;
  });
}

function room(t: Element): [number, number] {
  const cs = getComputedStyle(t), r = t.getBoundingClientRect();
  return [r.left + parseFloat(cs.paddingLeft), r.right - parseFloat(cs.paddingRight)];
}

function shrink(el: HTMLElement, avail: number): void {
  for (let i = 0; i < 4; i++) {
    const w = el.getBoundingClientRect().width;
    if (w <= avail + 0.5) break;
    if (!shrunk.has(el)) {
      el.dataset.fitFs = el.style.fontSize;
      shrunk.add(el);
    }
    el.style.fontSize = `${parseFloat(getComputedStyle(el).fontSize) * Math.max(0.4, avail / w) * 0.98}px`;
  }
}

export function keepInside(root: ParentNode = document): void {
  root.querySelectorAll(".ticker").forEach((t) => {
    const edge = t.getBoundingClientRect().right - 18;
    t.querySelectorAll<HTMLElement>(".tk").forEach((k) => {
      if (k.getBoundingClientRect().right > edge) {
        k.style.display = "none";
        k.dataset.fitHidden = "1";
      }
    });
  });
  root.querySelectorAll<HTMLElement>(".t table").forEach((tb) => {
    const tile = tb.closest(".t");
    if (!tile) return;
    const [l, r] = room(tile), w = tb.getBoundingClientRect().width;
    if (w > r - l + 0.5) {
      if (!shrunk.has(tb)) {
        tb.dataset.fitZoom = tb.style.zoom;
        shrunk.add(tb);
      }
      tb.style.zoom = ((r - l) / w).toFixed(3);
    }
  });
  root.querySelectorAll<HTMLElement>(".t .nm, .t .pn, .hero h2, .hero .side b").forEach((el) => {
    const box = el.closest(".t, .hero");
    if (!box || el.closest("table")) return;
    shrink(el, room(box)[1] - el.getBoundingClientRect().left);
  });
  root.querySelectorAll<HTMLElement>(".t *, .hero *").forEach((el) => {
    if (el.closest("svg") || el.closest("table")) return;
    const own = [...el.childNodes].some((n) => n.nodeType === 3 && (n.textContent ?? "").trim());
    if (own && getComputedStyle(el).display !== "inline" && el.scrollWidth > el.clientWidth + 1 && el.clientWidth > 0)
      shrink(el, el.clientWidth);
  });
}

/** Run the fit after each frame until the layout stops moving (a shrink can move what follows it). */
export function settle(done: () => void = () => {}, left = 3): void {
  keepInside();
  requestAnimationFrame(() => (left > 1 ? settle(done, left - 1) : done()));
}

/** From scratch: every size back to the design's, then fitted again (a resize, new data). */
export function refit(done?: () => void): void {
  undo();
  settle(done);
}
