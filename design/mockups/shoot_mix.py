"""Screenshot the mixed-style mock-ups: python3 shoot_mix.py [idea ...] [--pages home,player]"""
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent
SITE, OUT = HERE / "site", HERE / "shots" / "mix"
OUT.mkdir(parents=True, exist_ok=True)
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
ALL = ["home", "player", "match", "series", "leaders", "rankings", "squad", "results"]
args = [a for a in sys.argv[1:] if not a.startswith("--")]
ideas = args or ["1", "2", "3"]
pages = next((a.split("=", 1)[1].split(",") for a in sys.argv[1:] if a.startswith("--pages=")), ALL)
problems = {}
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CHROME)
    for idea in ideas:
        for page in pages:
            pg = b.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
            test = page.endswith("+test")
            page = page.removesuffix("+test")
            url = f"file://{SITE / 'mix.html'}?idea={idea}&page={page.split(':')[0]}" + (f"&inn={page.split(':')[1]}" if ":" in page else "") + ("&match=test" if test else "")
            pg.goto(url, wait_until="networkidle")
            try:
                pg.wait_for_selector("body[data-ready='1']", timeout=15000)
            except Exception as e:  # noqa: BLE001
                errs.append(f"never ready: {e}")
            pg.evaluate("document.fonts.ready")
            time.sleep(1.2)
            # anything wider than the page, or text cut off inside a tile
            wide = pg.evaluate("document.documentElement.scrollWidth")
            if wide > 1440:
                errs.append(f"page is {wide}px wide")
            base = page.split(":")[0]
            pg.screenshot(path=str(OUT / f"{idea}_{ALL.index(base) + 1}_{base}{'_inn' + page.split(':')[1] if ':' in page else ''}{'_test' if test else ''}.png"), full_page=True)
            if errs:
                problems[f"{idea}/{page}"] = errs[:3]
            pg.close()
    b.close()
print(problems or "no errors")
