"""The nothing-lost crawl, automatic (your yes of 26 November; stage 5, in the weekly run so a normal test run is no
slower): the new site is opened page by page (every page of the browser tests, and every tab on them) on the test
career, everything it shows is read, and every line of design/INVENTORY.md (what the old site showed) is looked for in
it. A line that is a label, a heading, a tab, a choice or a sentence (not a number of the old test career) must be found
in the same words, or all of its words on one page.

    python tools/nothing_lost.py            # crawl, write design/NOTHING_LOST_CRAWL.md, keep what was found as the
                                            # baseline (tests/frozen/nothing_lost.json)
    python tools/nothing_lost.py --check    # crawl and fail if any line found before is missing now (the weekly run)

Lines not found in the same words were each ticked by hand with where they moved (the stage checklists); the report
lists them so they can be read again. A line found once must stay found: that is what the weekly run checks."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "tests"), str(ROOT / "tools")]
INVENTORY = ROOT / "design" / "INVENTORY.md"
REPORT = ROOT / "design" / "NOTHING_LOST_CRAWL.md"
BASELINE = ROOT / "tests" / "frozen" / "nothing_lost.json"
LINE = re.compile(r"^- \[(?P<tick>[x ])\] \*(?P<kind>[^*]+)\* (?P<text>.*?)(?: — (?P<note>.*))?$")
LABELS = {"title", "header", "subheader", "tab", "tabs", "selectbox", "radio", "multiselect", "button", "checkbox", "toggle",
          "expander", "caption", "markdown", "info", "warning", "success", "error", "text_input", "number_input",
          "slider", "select_slider", "segmented_control", "pills", "page_header", "metric", "column", "columns"}
STOP = {"the", "a", "an", "of", "in", "on", "and", "or", "to", "for", "by", "with", "at", "is", "are", "it", "its", "this",
        "that", "be", "as", "from", "their", "your", "you", "they", "each", "every", "one", "all", "what", "who", "how"}


def norm(t: str) -> str:
    t = re.sub(r"\*\*|__|`", "", t).lower()
    t = t.replace("’", "'").replace("–", "-").replace("—", "-")
    t = re.sub(r"[^a-z0-9%'+\- ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def items() -> list[dict]:
    """The checkable lines of the inventory: words the old site wrote (not its test career's numbers)."""
    out, section = [], ""
    for raw in INVENTORY.read_text(encoding="utf-8").splitlines():
        if raw.startswith("## "):
            section = raw[3:].split(" · ")[0]
            continue
        m = LINE.match(raw)
        if not m:
            continue
        kind, text = m["kind"].strip(), m["text"].strip()
        if kind not in LABELS:
            continue
        text = re.sub(r"\s*\[\d+ options?:.*$", "", text)      # a choice: its label (the options are the career's)
        text = re.sub(r"^`([^`]*)`.*$", r"\1", text)
        n = norm(text)
        if len(n) < 3 or len(n) > 160 or sum(c.isdigit() for c in n) > 2 or not re.search(r"[a-z]{3}", n):
            continue                                            # numbers of the old test career, or too short to mean much
        out.append(dict(key=f"{section} · {kind} · {n}", section=section, kind=kind, text=text, n=n,
                        tick=m["tick"] == "x", note=(m["note"] or "").strip()))
    seen, uniq = set(), []
    for x in out:
        if x["key"] not in seen:
            seen.add(x["key"])
            uniq.append(x)
    return uniq


def crawl() -> dict[str, str]:
    """Every page of the browser tests, and every tab on each page, as text."""
    import freeze
    from playwright import sync_api
    from serverkit import chrome
    from test_web import PAGES
    live = freeze.site()
    pages: dict[str, str] = {}
    try:
        with sync_api.sync_playwright() as p:
            c = chrome()
            b = p.chromium.launch(**({"executable_path": c} if c else {}))
            for path in PAGES:
                pg = b.new_page(viewport={"width": 1440, "height": 900})
                try:
                    pg.goto(live.url(path), wait_until="networkidle")
                    pg.wait_for_selector("body[data-ready='1']", timeout=60000)
                    pages[path] = text_of(pg)
                    if "tab=" not in path:                       # every tab on the page, clicked one by one
                        for i in range(pg.locator(".itabs button").count()):
                            btn = pg.locator(".itabs button").nth(i)
                            name = (btn.text_content() or "").strip()
                            if not name or "on" in (btn.get_attribute("class") or ""):
                                continue
                            btn.click()
                            pg.wait_for_timeout(400)
                            pg.wait_for_selector("body[data-ready='1']", timeout=60000)
                            pages[f"{path} · {name}"] = text_of(pg)
                except Exception as e:  # noqa: BLE001 - a page that won't open is named in the report
                    pages[path] = pages.get(path, "") + f" [could not be read: {e}]"
                finally:
                    pg.close()
            b.close()
    finally:
        live.stop()
    return pages


def text_of(pg) -> str:
    """What the page shows, with the words people see only on hover (titles) and every choice's options."""
    return pg.evaluate("""() => {
        const bits = [document.body.innerText];
        document.querySelectorAll('[title]').forEach(e => bits.push(e.getAttribute('title')));
        document.querySelectorAll('option, [role=option]').forEach(e => bits.push(e.textContent));
        document.querySelectorAll('[aria-label]').forEach(e => bits.push(e.getAttribute('aria-label')));
        return bits.join('\\n');
    }""")


def found(item: dict, pages: dict[str, str]) -> str:
    """The page an inventory line is found on ("" when it isn't): the same words, or every one of its words on a page."""
    n = item["n"]
    words = {w for w in n.split() if w not in STOP and len(w) > 2}
    for path, t in pages.items():
        if n in t:
            return path
    for path, t in pages.items():
        if words and all(re.search(rf"\b{re.escape(w)}", t) for w in words):
            return path
    return ""


def main() -> None:
    check = "--check" in sys.argv
    lines = items()
    pages = {k: norm(v) for k, v in crawl().items()}
    where = {x["key"]: found(x, pages) for x in lines}
    if check:
        before = json.loads(BASELINE.read_text())
        lost = [k for k in before if not where.get(k)]
        print(f"{len(before) - len(lost)} of {len(before)} lines found before are still found")
        if lost:
            print("LOST:\n" + "\n".join(f"  {k}" for k in lost[:50]))
            sys.exit(1)
        return
    ok = sorted(k for k, v in where.items() if v)
    BASELINE.write_text(json.dumps(ok, indent=0) + "\n")
    missing = [x for x in lines if not where[x["key"]]]
    by: dict[str, list[dict]] = {}
    for x in missing:
        by.setdefault(x["section"], []).append(x)
    out = ["# The nothing-lost crawl: the new site against the old site's every line", "",
           f"Made by `tools/nothing_lost.py`: {len(pages)} pages and tabs of the new site opened on the test career, "
           f"{len(lines)} lines of design/INVENTORY.md that are words (not the old test career's numbers) looked for.", "",
           f"- **Found on the new site in the same words (or all their words on one page): {len(ok)}.** These are the "
           "baseline: the weekly run fails if any of them goes missing.",
           f"- **Not found word for word: {len(missing)}.** Each is listed below with its hand tick from the stage "
           "checklists (where it moved, or why it went with your yes); these are read again at the switch-over.", ""]
    for sec, xs in sorted(by.items()):
        out += [f"## {sec} ({len(xs)})", ""]
        out += [f"- *{x['kind']}* {x['text'][:140]}" + (f" — {x['note']}" if x["note"] else "") for x in xs]
        out.append("")
    REPORT.write_text("\n".join(out), encoding="utf-8")
    print(f"{len(ok)} of {len(lines)} lines found; report in {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
