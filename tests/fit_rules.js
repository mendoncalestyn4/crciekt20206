// Does everything stay inside the page? (the approved rule, as design/mockups/check_fit.py checks the mock-ups)
//   edge     - text (or a chart label) reaching past the tile, chart or page it sits in
//   cut      - text cut short inside its own box
//   overlap  - two pieces of text drawn on top of each other
//   wide     - the page wider than the window
() => {
  const out = [], T = 1.5;                                   // allow 1.5px for rounding
  const label = el => (el.textContent || "").trim().replace(/\s+/g, " ").slice(0, 60);
  const tileOf = el => el.closest(".t, .hero, .ticker, .itabs, .head, .rail");
  const titleOf = t => t ? ((t.querySelector(".tl") || {}).textContent || t.className.split(" ")[0]).trim().slice(0, 40) : "page";
  // the text pieces: html elements holding their own text, and every chart label
  const pieces = [];
  for (const el of document.querySelectorAll("body *")) {
    if (el.closest("svg") || ["SCRIPT", "STYLE"].includes(el.tagName)) continue;
    const own = [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
    if (!own) continue;
    const st = getComputedStyle(el);
    if (st.visibility === "hidden" || st.display === "none" || +st.opacity === 0) continue;
    const range = document.createRange(); range.selectNodeContents(el);
    const r = range.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) continue;
    const sh = r.height * .18;   // the letters sit inside the font's box: trim its empty top and bottom
    pieces.push({el, r: {left: r.left, right: r.right, top: r.top + sh, bottom: r.bottom - sh, width: r.width, height: r.height - 2 * sh}, kind: "text"});
    // cut: wider than its own box while the box hides what spills
    if ((st.overflow === "hidden" || st.textOverflow === "ellipsis") && el.scrollWidth > el.clientWidth + T)
      out.push({type: "cut", where: titleOf(tileOf(el)), what: label(el)});
  }
  for (const svg of document.querySelectorAll(".t svg, .hero svg")) {
    const box = svg.getBoundingClientRect();
    for (const tx of svg.querySelectorAll("text")) {
      const r = tx.getBoundingClientRect();
      if (r.width < 1 || !tx.textContent.trim()) continue;
      const sh = r.height * .12;
      pieces.push({el: tx, r: {left: r.left, right: r.right, top: r.top + sh, bottom: r.bottom - sh, width: r.width, height: r.height - 2 * sh}, kind: "chart"});
      if (r.left < box.left - T || r.right > box.right + T || r.top < box.top - T || r.bottom > box.bottom + T)
        out.push({type: "edge", where: titleOf(tileOf(svg)), what: "chart label '" + tx.textContent.trim().slice(0, 40) + "'"});
    }
  }
  // edge: any text past its tile (tiles hide what spills over) or past the window
  for (const p of pieces) {
    const t = tileOf(p.el), b = t ? t.getBoundingClientRect() : {left: 0, right: innerWidth, top: -1e9, bottom: 1e9};
    if (p.r.left < b.left - T || p.r.right > b.right + T || p.r.top < b.top - T || p.r.bottom > b.bottom + T)
      out.push({type: "edge", where: titleOf(t), what: (p.kind === "chart" ? "chart label '" : "'") + label(p.el) + "'"});
  }
  // overlap: two text pieces in the same tile drawn on top of each other (more than a sliver)
  const byTile = new Map();
  for (const p of pieces) { const t = tileOf(p.el); if (!byTile.has(t)) byTile.set(t, []); byTile.get(t).push(p); }
  for (const [t, ps] of byTile) for (let i = 0; i < ps.length; i++) for (let j = i + 1; j < ps.length; j++) {
    const a = ps[i].r, b = ps[j].r;
    if (ps[i].el.contains(ps[j].el) || ps[j].el.contains(ps[i].el)) continue;
    const w = Math.min(a.right, b.right) - Math.max(a.left, b.left), h = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
    if (w > 3 && h > 3 && w * h > 0.12 * Math.min(a.width * a.height, b.width * b.height))
      out.push({type: "overlap", where: titleOf(t), what: "'" + label(ps[i].el) + "' and '" + label(ps[j].el) + "'"});
  }
  if (document.documentElement.scrollWidth > innerWidth) out.push({type: "wide", where: "page", what: document.documentElement.scrollWidth + "px"});
  return out;
}
