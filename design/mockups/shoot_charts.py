"""Screenshot the chart ideas: the whole gallery and each chart on its own."""
import sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright
HERE = Path(__file__).parent
OUT = HERE / "shots"
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
ideas = [int(x) for x in sys.argv[1:]] or [1, 2, 3, 4, 5]
problems = {}
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CHROME)
    for n in ideas:
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        pg.goto(f"file://{HERE / 'site' / 'charts.html'}?idea={n}", wait_until="networkidle")
        pg.evaluate("document.fonts.ready"); time.sleep(1.5)
        pg.screenshot(path=str(OUT / f"chart{n}_0_all.png"), full_page=True)
        for i in range(1, 7):
            el = pg.query_selector(f"#p{i}")
            if el:
                el.screenshot(path=str(OUT / f"chart{n}_{i}.png"))
        if errs:
            problems[n] = errs[:4]
        pg.close()
    b.close()
print(problems or "no errors")
