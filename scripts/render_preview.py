"""Render TorKe's cards to PNG for the README (needs: pip install playwright pillow; playwright install chromium).

Usage, from the repo root:  python scripts/render_preview.py [output_dir]
Everything runs offline: the "photo" is a drawing made here, Homebox is the test suite's in-memory
stand-in, and no network calls are made. Needs pytest installed (the tests module imports it).
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

    sys.path.insert(0, str(ROOT / "tests"))
    from test_torke import FakeHomebox  # the test suite's in-memory Homebox

    os.environ["DATA_DIR"] = str(tmp)
    hb = FakeHomebox(new=True)
    torke._json, torke._fetch_bytes = hb.json, hb.fetch
    hb.maint["e2"] = [{"name": "Cleaned the filter", "description": "Standing water, filter clogged.",
                       "completedDate": "2026-03-14"}]
    torke.REQUIRE_WARNING = False  # the preview shows the cards, not the warning
    t = torke.Tools()
    t.valves.site_ifixit = True
    t.valves.site_manualslib = True
    t.valves.homebox_lookup, t.valves.homebox_url, t.valves.homebox_write = True, "http://homebox:7745", True
    t.valves.homebox_tools_location = "Garage"
    user = {"id": "preview", "valves": torke.Tools.UserValves()}
    msgs = [{"role": "user", "content": [{"type": "image_url", "image_url": {"url": stand_in_photo()}}]}]
    photo, _ = await t.open_project("Bosch dishwasher SHE3AR75UC", "Won't drain, error E24", "appliance",
                                    "Bosch", "SHE3AR75UC", __user__=user, __messages__=msgs)
    car, _ = await t.open_project("2012 Honda Civic", "Front brake pads and rotors", "vehicle", "Honda",
                                  "Civic", "2012", __user__=user)
    job, civic = "Front brake pads and rotors", "2012 Honda Civic"
    await t.save_needed_tools(["jack stands"], job, civic, __user__=user)
    await t.save_needed_tools(["floor jack"], job, civic, rent=True, __user__=user)
    tools, _ = await t.check_tools(["torque wrench", "14 mm socket", "17 mm socket", "C-clamp or caliper piston tool",
                                    "jack stands", "floor jack", "wire brush"], job, civic, __user__=user)
    await t.save_needed_parts([
        {"name": "Front brake pads, ceramic", "part_number": "D1089", "link": "https://www.example.com/pads",
         "price": "$42.99", "store": "Parts store"},
        {"name": "Front rotors", "qty": 2, "price": "$38.50"},
        {"name": "Brake fluid, DOT 3"}], job, civic, __user__=user)
    await t.save_needed_parts(["Drain pump"], "Won't drain, error E24", "Bosch dishwasher SHE3AR75UC", __user__=user)
    shop, _ = await t.shopping_list(__user__=user)
    await t.parts_arrived(["front brake pads", "front rotors"], __user__=user)
    await t.rental_picked_up(["floor jack"], __user__=user)
    done, _ = await t.complete_job(civic, job, __user__=user)
    ifixit = {"results": [{"dataType": "guide", "title": "Honda Civic Brake Pad Replacement",
                           "url": "https://www.ifixit.com/Guide/Honda+Civic+Brake+Pad+Replacement/1"}]}
    torke._json = lambda url, **kw: ifixit if "ifixit.com" in url else hb.json(url, **kw)
    hb.maint["e3"] = [{"name": "Replaced front brake pads", "completedDate": "2026-03-14",
                       "description": "Mileage: 90,000"}, {"name": "Change oil", "scheduledDate": "2026-12-01"}]
    jobs, _ = await t.job_picker(civic, "vehicle", __user__=user)
    hub_steps = [
        {"title": "Lift and support the truck", "how": "Loosen the lug nuts a little with the wheels on the ground. Lift the front, set jack stands, then take the wheel off.",
         "check": "The truck is solid on stands and doesn't rock when you push it.", "warn": "Never work under a truck held only by a jack."},
        {"title": "Remove the caliper and rotor", "how": "Take out the two caliper bracket bolts. Support the caliper, then pull the rotor.",
         "check": "The caliper hangs from wire, not its brake hose.", "warn": "Don't let the caliper hang from its brake hose."},
        {"title": "Remove the four hub bolts", "how": "Remove the four hub-to-knuckle bolts. They're single use.", "check": "All four bolts are out."},
        {"title": "Fasten the hub", "how": "Install the four new hub bolts, then a new axle nut. Reconnect the ABS sensor.",
         "check": "Every fastener is torqued and the sensor is clipped away from moving parts.",
         "torque": [{"what": "Hub bolts (new)", "value": "129 ft-lb", "note": "2 sources agree"},
                    {"what": "Axle nut (new)", "value": "30 ft-lb", "note": "Disputed: 20 or 30"}]},
        {"title": "Reassemble and test", "how": "Reinstall the rotor, caliper and wheel. Check the brake pedal is firm before you move.",
         "check": "The pedal is firm and 4WD engages at walking speed."},
    ]
    hub_src = "Sample steps for a layout preview. A real card names the manual or guide each step came from."
    proc, _ = await t.show_procedure("2013 Ford F-150", "Replace front hub assembly (4WD)", hub_steps, hub_src, __user__=user)
    proc_list, _ = await t.show_procedure("2013 Ford F-150", "Replace front hub assembly (4WD)", hub_steps, hub_src, "list",
                                          __user__=user)
    return {"card-procedure": proc.body.decode(), "card-procedure-list": proc_list.body.decode(), "card-photo": photo.body.decode(), "card-vehicle": car.body.decode(), "card-tools": tools.body.decode(),
            "card-shopping": shop.body.decode(), "card-job-done": done.body.decode(),
            "card-jobs": jobs.body.decode()}


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
                if name == "card-procedure":
                    await page.evaluate("cur=3;show()")  # show a middle step, the one with torque values
                await page.locator("section.hud").screenshot(path=str(out / f"{name}{suffix}.png"))
                await page.close()
        await browser.close()
    print("wrote", ", ".join(sorted(f.name for f in out.glob("card-*.png"))))


if __name__ == "__main__":
    asyncio.run(main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "docs"))
