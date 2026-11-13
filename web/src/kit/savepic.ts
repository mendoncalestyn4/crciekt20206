// "Save picture": a tile (its title, chart and notes) saved as a PNG, as it looks on the page. The tile is copied with
// every style written onto it, its pictures (team badges, logos) and the site's fonts put inside the copy, drawn into
// an SVG and from there onto a canvas at twice the size, so the picture is sharp and matches the page.

let fonts: Promise<string> | null = null;

const toData = (url: string): Promise<string> =>
  fetch(url).then((r) => r.blob()).then((b) => new Promise<string>((ok, no) => {
    const fr = new FileReader();
    fr.onload = () => ok(String(fr.result));
    fr.onerror = () => no(fr.error);
    fr.readAsDataURL(b);
  }));

/** Every @font-face of the site's own style sheets, with the font files put inside (worked out once). */
function fontRules(): Promise<string> {
  if (fonts) return fonts;
  const jobs: Promise<string>[] = [];
  for (const sheet of Array.from(document.styleSheets)) {
    let rules: CSSRuleList;
    try { rules = sheet.cssRules; } catch { continue; }   // a sheet from elsewhere can't be read
    for (const rule of Array.from(rules)) {
      if (!(rule instanceof CSSFontFaceRule)) continue;
      const css = rule.cssText, m = css.match(/url\(["']?([^"')]+)["']?\)/);
      if (!m) continue;
      const url = new URL(m[1]!, sheet.href ?? location.href).href;
      jobs.push(toData(url).then((d) => css.replace(m[0], `url("${d}")`)).catch(() => ""));
    }
  }
  fonts = Promise.all(jobs).then((r) => r.join("\n"));
  return fonts;
}

/** A copy of `el` with every computed style written onto it (so it looks the same outside the page). */
function copyWithStyles(el: Element): Element {
  const out = el.cloneNode(false) as Element;
  if (el instanceof HTMLElement || el instanceof SVGElement) {
    const cs = getComputedStyle(el), st = (out as HTMLElement).style;
    for (let i = 0; i < cs.length; i++) {
      const p = cs[i]!;
      st.setProperty(p, cs.getPropertyValue(p), cs.getPropertyPriority(p));
    }
  }
  for (const c of Array.from(el.childNodes)) {
    if (c.nodeType === Node.ELEMENT_NODE) {
      if ((c as Element).classList?.contains("savepic")) continue;   // not the button itself
      out.appendChild(copyWithStyles(c as Element));
    } else out.appendChild(c.cloneNode(true));
  }
  if (el instanceof HTMLCanvasElement) {   // a canvas copies blank: its picture instead
    const img = document.createElement("img");
    img.src = el.toDataURL("image/png");
    img.setAttribute("style", (out as HTMLElement).getAttribute("style") ?? "");
    return img;
  }
  return out;
}

/** Saves the tile `el` as `name`.png. */
export async function savePicture(el: HTMLElement, name: string): Promise<void> {
  const r = el.getBoundingClientRect(), w = Math.ceil(r.width), h = Math.ceil(r.height);
  const copy = copyWithStyles(el) as HTMLElement;
  copy.style.margin = "0";
  // the pictures inside (badges, logos), put in the copy itself: an SVG drawn as a picture loads nothing from outside
  await Promise.all(Array.from(copy.querySelectorAll("img")).map(async (img) => {
    const src = img.getAttribute("src") ?? "";
    if (src && !src.startsWith("data:")) img.setAttribute("src", await toData(src).catch(() => ""));
  }));
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}"><style>${await fontRules()}</style>` +
    `<foreignObject width="100%" height="100%"><div xmlns="http://www.w3.org/1999/xhtml">${new XMLSerializer().serializeToString(copy)}</div></foreignObject></svg>`;
  const img = new Image();
  await new Promise<void>((ok, no) => { img.onload = () => ok(); img.onerror = () => no(new Error("The picture couldn't be drawn.")); img.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`; });
  const scale = 2, c = document.createElement("canvas");
  c.width = w * scale; c.height = h * scale;
  const g = c.getContext("2d")!;
  g.fillStyle = getComputedStyle(document.body).backgroundColor || "#0e1a3c";
  g.fillRect(0, 0, c.width, c.height);
  g.scale(scale, scale);
  g.drawImage(img, 0, 0, w, h);
  const a = document.createElement("a");
  a.download = `${name}.png`;
  a.href = c.toDataURL("image/png");
  a.click();
}

/** A file name from a tile's title: "Batting first or chasing · ODIs" -> "batting-first-or-chasing-odis". */
export const slugOf = (s: string) => s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 80) || "chart";
