"""Screenshot the mock-up pages: python3 shoot.py a_broadcast [pages...]"""
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent
SITE, OUT = HERE / "site", HERE / "shots"
OUT.mkdir(exist_ok=True)
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
name = sys.argv[1]
ALL = ["home", "player", "match", "series", "leaders", "rankings"]
pages = sys.argv[2:] or ALL
problems = {}
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CHROME)
    for page in pages:
        i = ALL.index(page) + 1 if page in ALL else 0
        pg = b.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        pg.goto(f"file://{SITE / (name + '.html')}?page={page}", wait_until="networkidle")
        pg.evaluate("document.fonts.ready")
        time.sleep(1.2)
        pg.screenshot(path=str(OUT / f"{name}_{i}_{page}.png"), full_page=True)
        if errs:
            problems[page] = errs[:3]
        pg.close()
    b.close()
print(problems or "no errors")
