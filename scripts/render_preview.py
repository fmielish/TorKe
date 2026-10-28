"""Render TorKe's cards to PNG for the README (needs: pip install playwright pillow; playwright install chromium).

Usage, from the repo root:  python scripts/render_preview.py [output_dir]
Everything runs offline: the "photo" is a drawing made here, and no network calls are made.
"""

import asyncio
import base64
import io
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import torke  # noqa: E402


def stand_in_photo() -> str:
    """A simple original drawing of a dishwasher, standing in for a user's photo."""
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (600, 600), (232, 236, 240))
    d = ImageDraw.Draw(img)
    for y in range(600):  # soft studio backdrop
        c = 238 - y // 20
        d.line([(0, y), (600, y)], fill=(c, c + 2, c + 5))
    d.rectangle([120, 70, 480, 560], fill=(206, 211, 216), outline=(150, 156, 162), width=4)
    d.rectangle([120, 70, 480, 140], fill=(60, 64, 70))
    for i, x in enumerate(range(150, 330, 36)):
        d.ellipse([x, 96, x + 16, 112], fill=(120, 220, 160) if i == 0 else (140, 146, 152))
    d.rectangle([360, 98, 450, 112], fill=(30, 140, 200))
    d.rounded_rectangle([170, 160, 430, 182], radius=10, fill=(170, 176, 182), outline=(120, 126, 132), width=2)
    for x in range(140, 470, 14):
        d.line([(x, 200), (x, 540)], fill=(198, 203, 208), width=1)
    d.rectangle([120, 545, 480, 560], fill=(80, 84, 90))
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


async def build_cards(tmp: Path) -> dict:
    import os

    os.environ["DATA_DIR"] = str(tmp)
    t = torke.Tools()
    t.valves.site_ifixit = True
    t.valves.site_manualslib = True
    t.valves.repair_log = True
    user = {"id": "preview", "valves": torke.Tools.UserValves()}
    await t.log_repair("Bosch dishwasher SHE3AR75UC", "Cleaned the filter", "Standing water, filter clogged.",
                       "2026-03-14", __user__=user)
    msgs = [{"role": "user", "content": [{"type": "image_url", "image_url": {"url": stand_in_photo()}}]}]
    photo, _ = await t.open_project("Bosch dishwasher SHE3AR75UC", "Won't drain, error E24", "appliance",
                                    "Bosch", "SHE3AR75UC", __user__=user, __messages__=msgs)
    t.valves.repair_log = False
    car, _ = await t.open_project("2012 Honda Civic", "Front brake pads and rotors", "vehicle", "Honda",
                                  "Civic", "2012", __user__=user)
    owner = {"id": "preview", "valves": torke.Tools.UserValves(my_tools="3/8 in drive torque wrench")}
    await t.save_needed_tools(["jack stands"], "Front brake pads and rotors", "2012 Honda Civic", __user__=owner)
    tools, _ = await t.check_tools(["torque wrench", "14 mm socket", "17 mm socket", "C-clamp or caliper piston tool",
                                    "jack stands", "floor jack", "wire brush"], "Front brake pads and rotors",
                                   "2012 Honda Civic", __user__=owner)
    return {"card-photo": photo.body.decode(), "card-vehicle": car.body.decode(), "card-tools": tools.body.decode()}


async def main(out: Path):
    from playwright.async_api import async_playwright

    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        cards = await build_cards(Path(tmp))
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        for name, html_text in cards.items():
            for width, suffix in ((760, ""), (390, "-phone")):
                page = await browser.new_page(viewport={"width": width, "height": 400}, device_scale_factor=2)
                await page.set_content(html_text)
                await page.wait_for_timeout(1500)  # let the ring finish drawing
                await page.locator("section.hud").screenshot(path=str(out / f"{name}{suffix}.png"))
                await page.close()
        await browser.close()
    print("wrote", ", ".join(sorted(f.name for f in out.glob("card-*.png"))))


if __name__ == "__main__":
    asyncio.run(main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "docs"))
