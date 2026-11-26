"""The program's icon file (desktop/icon/stats-pack.ico) and the site's window icon (web/public/favicon.svg), from the
two drawings in desktop/icon (small.svg for 16-48 pixels, full.svg for 64-256). Needs Playwright's Chromium.

    python3 tools/make_icon.py"""
import base64
import io
import pathlib
import shutil

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
ICON = ROOT / "desktop" / "icon"
SMALL, BIG = (16, 20, 24, 32, 40, 48), (64, 96, 128, 256)


def main() -> None:
    images = {}
    with sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception:  # noqa: BLE001
            b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        pg = b.new_page()
        for name, sizes in (("small", SMALL), ("full", BIG)):
            svg = (ICON / f"{name}.svg").read_text()
            for n in sizes:
                pg.set_viewport_size({"width": n, "height": n})
                src = "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()
                pg.set_content(f'<html><body style="margin:0;background:transparent">'
                               f'<img src="{src}" width="{n}" height="{n}" style="display:block"></body></html>')
                pg.wait_for_timeout(50)
                images[n] = Image.open(io.BytesIO(pg.screenshot(omit_background=True))).convert("RGBA")
        b.close()
    big = images[256]
    big.save(ICON / "stats-pack.ico", format="ICO", sizes=[(n, n) for n in sorted(images)],
             append_images=[images[n] for n in sorted(images) if n != 256])
    big.save(ICON / "stats-pack-256.png")
    shutil.copy(ICON / "small.svg", ROOT / "web" / "public" / "favicon.svg")
    print("ok", sorted(images))


if __name__ == "__main__":
    main()
