"""Offline tests for TorKe. Network calls are replaced with canned answers.

Run from the repo root:  python -m pytest -q
"""

import asyncio
import base64
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import torke  # noqa: E402

PNG_1PX = "data:image/png;base64," + base64.b64encode(
    bytes.fromhex("89504e470d0a1a0a0000000d4948445200000001000000010806000000"
                  "1f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082")
).decode()


def run(coro):
    return asyncio.run(coro)


def body(result):
    resp, context = result
    return resp.body.decode("utf-8"), context


@pytest.fixture
def tool(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    torke._PROJECTS.clear()
    return torke.Tools()


USER = {"id": "u1", "name": "Test", "valves": torke.Tools.UserValves()}


# ---------------------------------------------------------------- project card

def test_card_has_six_buttons_and_log_off_by_default(tool):
    html, ctx = body(run(tool.open_project("2012 Honda Civic", "timing belt", "vehicle", "Honda", "Civic", "2012",
                                           __user__=USER, __chat_id__="c1")))
    for name in ("Manuals", "Videos", "Parts", "Tools you&#x27;ll need", "Safety warnings", "Repair log"):
        assert name in html
    assert html.count('<button type="button" class="blade') == 6
    assert 'aria-disabled="true"' in html  # repair log is off
    assert "Manual sites on: none" in ctx
    assert "iframe:height" in html and "input:prompt:submit" in html


def test_card_escapes_hostile_text(tool):
    html, _ = body(run(tool.open_project('<script>alert(1)</script>', '"><img src=x onerror=alert(1)>',
                                         __user__=USER)))
    assert "<script>alert(1)" not in html
    assert "<img src=x" not in html


def test_card_uses_attached_photo(tool):
    msgs = [{"role": "user", "content": [{"type": "text", "text": "fix this"},
                                         {"type": "image_url", "image_url": {"url": PNG_1PX}}]}]
    html, ctx = body(run(tool.open_project("Shop vac", __user__=USER, __messages__=msgs)))
    assert PNG_1PX in html and "Your photo" in html and "user photo" in ctx


def test_card_web_picture_only_when_switched_on(tool, monkeypatch):
    calls = []
    monkeypatch.setattr(torke, "_json", lambda url, **kw: calls.append(url) or {"results": [
        {"img_src": "https://img.example.com/civic.jpg", "url": "https://example.com/civic", "title": "Civic"}]})
    tool.valves.searxng_url = "http://searxng:8080"
    html, _ = body(run(tool.open_project("2012 Honda Civic", __user__=USER)))
    assert not calls and "img.example.com" not in html
    tool.valves.show_pictures = True
    html, _ = body(run(tool.open_project("2012 Honda Civic", __user__=USER)))
    assert "https://img.example.com/civic.jpg" in html and "Photo from" in html
    assert "categories=images" in calls[0]


def test_hazards_respect_category():
    names = {h["key"] for h in torke._hazards("2012 Civic replace front brake pads, jack it up", "vehicle")}
    assert {"brakes", "lifting"} <= names
    names = {h["key"] for h in torke._hazards("fuel pump and gas tank", "vehicle")}
    assert "fuel" in names and "gas" not in names
    names = {h["key"] for h in torke._hazards("gas furnace pilot won't light", "home")}
    assert "gas" in names and "fuel" not in names
    assert not torke._hazards("wobbly chair leg", "other")


def test_safe_img_rejects_scripts():
    assert torke._safe_img("javascript:alert(1)") == ""
    assert torke._safe_img("data:text/html;base64,PHNjcmlwdD4=") == ""
    assert torke._safe_img('data:image/png;base64,AAAA" onerror="x') == ""
    assert torke._safe_img(PNG_1PX) == PNG_1PX
    assert torke._safe_img("//i.ytimg.com/vi/x/mqdefault.jpg").startswith("https://")


# ---------------------------------------------------------------- videos

def test_videos_without_backend_link_to_youtube_search(tool):
    html, ctx = body(run(tool.find_videos("2012 Honda Civic timing belt", __user__=USER)))
    assert "youtube.com/results?search_query=2012+Honda+Civic+timing+belt" in html
    assert "Search YouTube" in html and "search link" in ctx


def test_videos_from_searxng(tool, monkeypatch):
    monkeypatch.setattr(torke, "_json", lambda url, **kw: {"results": [
        {"url": "https://www.youtube.com/watch?v=abc123XYZ", "title": "Civic belt &amp; pump", "author": "Shop",
         "length": 754},
        {"url": "https://vimeo.com/123", "title": "not youtube"}]})
    tool.valves.searxng_url = "http://searxng:8080"
    html, ctx = body(run(tool.find_videos("civic timing belt", __user__=USER)))
    assert "watch?v=abc123XYZ" in html and "12:34" in html and "vimeo" not in html
    assert "Civic belt &amp; pump" in html  # unescaped once, escaped once for HTML
    assert "Add to my playlist" not in html
    tool.valves.youtube_playlist = True
    html, _ = body(run(tool.find_videos("civic timing belt", __user__=USER)))
    assert "Add to my playlist" in html


def test_youtube_ids():
    assert torke._youtube_id("https://youtu.be/abc123XYZ?t=4") == "abc123XYZ"
    assert torke._youtube_id("https://www.youtube.com/shorts/abc123XYZ") == "abc123XYZ"
    assert torke._youtube_id("https://evil.example/watch?v=abc") == ""


# ---------------------------------------------------------------- manuals

def test_manuals_with_no_sites(tool):
    out = run(tool.find_manuals("Bosch dishwasher", "Bosch", "SHE3AR75UC", __user__=USER))
    assert "No manual sites are turned on" in out and "duckduckgo.com" in out


def test_link_only_site_gives_links(tool):
    tool.valves.site_manualslib = True
    out = run(tool.find_manuals("Bosch dishwasher", "Bosch", "SHE3AR75UC", __user__=USER))
    assert "ManualsLib (links only" in out and "site%3Amanualslib.com" in out


def test_gray_site_start_page(tool):
    tool.valves.site_charm_li = True
    out = run(tool.find_manuals("2012 Honda Civic", "honda", "Civic", "2012", __user__=USER))
    assert "https://charm.li/Honda/2012/" in out and "legal gray area" in out


def test_read_page_rules(tool, monkeypatch):
    assert "terms don't allow" in run(tool.read_manual_page("https://www.manualslib.com/manual/1/x.html"))
    assert "isn't on TorKe's list" in run(tool.read_manual_page("https://charm.li/Honda/"))
    tool.valves.site_charm_li = True
    monkeypatch.setattr(torke, "_is_public", lambda url: False)
    assert "private network" in run(tool.read_manual_page("https://charm.li/Honda/"))
    monkeypatch.setattr(torke, "_is_public", lambda url: True)
    monkeypatch.setattr(torke, "_fetch_page", lambda url, domains, timeout=25:
                        '<html><body><h1>Honda</h1><a href="/Honda/2012/">2012</a><script>bad()</script></body></html>')
    out = run(tool.read_manual_page("https://charm.li/Honda/"))
    assert "Honda" in out and "https://charm.li/Honda/2012/" in out and "bad()" not in out
    assert torke.WEB_NOTE in out


def test_custom_site_must_be_public(tool, monkeypatch):
    tool.valves.custom_manual_sites = "https://support.example.com/manuals, not a domain"
    assert torke._clean_domains(tool.valves.custom_manual_sites) == ["support.example.com"]
    monkeypatch.setattr(torke, "_is_public", lambda url: False)
    assert "private network" in run(tool.read_manual_page("http://support.example.com/a"))


def test_ifixit_guide(tool, monkeypatch):
    guide = {"title": "Replacing the drain pump", "url": "https://www.ifixit.com/Guide/Drain+Pump/123",
             "difficulty": "Moderate", "tools": [{"text": "Phillips #2", "url": "https://www.ifixit.com/t/1"}],
             "parts": [{"text": "Drain pump", "url": "https://www.ifixit.com/p/2"}],
             "steps": [{"title": "Unplug it", "lines": [{"text_raw": "Unplug the **dishwasher**."}]}]}
    monkeypatch.setattr(torke, "_json", lambda url, **kw: guide)
    assert "iFixit is off" in run(tool.read_manual_page("https://www.ifixit.com/Guide/Drain+Pump/123"))
    tool.valves.site_ifixit = True
    out = run(tool.read_manual_page("https://www.ifixit.com/Guide/Drain+Pump/123"))
    assert "Replacing the drain pump" in out and "https://www.ifixit.com/t/1" in out and "Step 1: Unplug it" in out
    assert "CC BY-NC-SA" in out


# ---------------------------------------------------------------- tools, safety, parts, log

def test_tools_baseline_and_user_list(tool):
    out = run(tool.check_tools(__user__=USER))
    assert "100-piece socket set" in out and "multimeter" in out and "torque wrench" in out.lower()
    bare = {"id": "u2", "valves": torke.Tools.UserValves(has_starter_kit=False, has_socket_set=False,
                                                          has_multimeter=False, my_tools="")}
    assert "Nothing listed" in run(tool.check_tools([], __user__=bare))


def test_safety_with_recalls(tool, monkeypatch):
    monkeypatch.setattr(torke, "_json", lambda url, **kw: {"results": [
        {"NHTSACampaignNumber": "12V000000", "Component": "BRAKES", "Summary": "Pads may wear", "Remedy": "Replace"}]})
    out = run(tool.safety_check("front brake pads", "2012 Honda Civic", "vehicle", "Honda", "Civic", "2012",
                                __user__=USER))
    assert "Brakes and steering" in out and "12V000000" not in out  # recalls off by default
    tool.valves.recall_checks = True
    out = run(tool.safety_check("front brake pads", "2012 Honda Civic", "vehicle", "Honda", "Civic", "2012",
                                __user__=USER))
    assert "12V000000" in out


def test_stop_rules_come_first(tool):
    out = run(tool.safety_check("replace the magnetron", "Microwave", "appliance", __user__=USER))
    assert out.startswith("STOP:")


def test_parts_links_and_no_brand_note(tool):
    out = run(tool.find_parts(["drain pump W10348269"], "Whirlpool dishwasher", __user__=USER))
    assert "amazon.com/s?k=drain+pump+W10348269" in out
    assert "quality brand" not in out and "save_needed_parts" in out


def test_repair_log(tool):
    assert "repair log is off" in run(tool.repair_history("Civic", __user__=USER))
    tool.valves.repair_log = True
    run(tool.log_repair("2012 Honda Civic", "Timing belt", "Belt, tensioner, water pump at 104k mi",
                        "2026-10-01", "$310", __user__=USER))
    run(tool.log_repair("Bosch dishwasher", "Cleaned filter", "Drained again", __user__=USER))
    out = run(tool.repair_history("honda civic", __user__=USER))
    assert "Timing belt" in out and "dishwasher" not in out
    other = {"id": "someone-else", "valves": torke.Tools.UserValves()}
    assert "No repairs logged" in run(tool.repair_history("civic", __user__=other))
    html, _ = body(run(tool.open_project("2012 Honda Civic", __user__=USER)))
    assert "1 entry" in html


def test_buttons_use_open_project(tool):
    run(tool.open_project("Bosch dishwasher", "won't drain", "appliance", "Bosch", "SHE3AR75UC",
                          __user__=USER, __chat_id__="c9"))
    out = run(tool.find_manuals(__user__=USER, __chat_id__="c9"))
    assert "Bosch SHE3AR75UC" in out


def test_playlist_needs_switch_and_sign_in(tool):
    assert "option is off" in run(tool.add_to_playlist(["https://youtu.be/abc123XYZ"], __user__=USER))
    tool.valves.youtube_playlist = True
    assert "hasn't set up" in run(tool.add_to_playlist(["https://youtu.be/abc123XYZ"], __user__=USER))


def test_valve_defaults_are_off():
    v = torke.Tools.Valves()
    switches = {k: getattr(v, k) for k in type(v).model_fields if isinstance(getattr(v, k), bool)}
    assert switches and not any(switches.values())
    assert json.dumps(torke.Tools.Valves.model_json_schema())  # schema renders


# ---------------------------------------------------------------- remaining paths, with fake services

def test_ifixit_search_and_links_via_searxng(tool, monkeypatch):
    def fake(url, **kw):
        if "ifixit.com/api" in url:
            return {"results": [{"dataType": "guide", "guideid": 77, "title": "Drain pump", "url": "https://www.ifixit.com/Guide/x/77"}]}
        return {"results": [{"url": "https://www.manualslib.com/manual/1/Bosch.html", "title": "Bosch manual"},
                            {"url": "https://elsewhere.example/x", "title": "off-site"}]}
    monkeypatch.setattr(torke, "_json", fake)
    tool.valves.searxng_url = "http://searxng:8080"
    tool.valves.site_ifixit = True
    tool.valves.site_manualslib = True
    out = run(tool.find_manuals("Bosch dishwasher", "Bosch", "SHE3AR75UC", __user__=USER))
    assert "guide id 77" in out and "manualslib.com/manual/1" in out and "elsewhere.example" not in out


def test_cpsc_recalls_for_products(tool, monkeypatch):
    seen = []
    monkeypatch.setattr(torke, "_json", lambda url, **kw: seen.append(url) or [
        {"RecallDate": "2025-01-02T00:00:00", "Title": "Space heaters recalled", "URL": "https://www.cpsc.gov/r/1"}])
    tool.valves.recall_checks = True
    out = run(tool.safety_check("won't turn on", "space heater", "home", "Acme", "SH-100", __user__=USER))
    assert "Space heaters recalled" in out and "saferproducts.gov" in seen[0]


def test_playlist_success(tool, monkeypatch):
    posted = []
    monkeypatch.setattr(torke, "_json", lambda url, **kw: {"access_token": "tok"})
    monkeypatch.setattr(torke, "_http", lambda url, **kw: posted.append((url, json.loads(kw["data"]))) or "{}")
    tool.valves.youtube_playlist = True
    user = {"id": "u1", "valves": torke.Tools.UserValves(youtube_client_id="id", youtube_client_secret="s",
                                                          youtube_refresh_token="r", youtube_playlist_id="PL1")}
    out = run(tool.add_to_playlist(["https://youtu.be/abc123XYZ", "https://vimeo.com/1"], __user__=user))
    assert "Added 1 video" in out and "vimeo" in out
    assert posted[0][1]["snippet"]["resourceId"]["videoId"] == "abc123XYZ"


def test_parts_list_webhook(tool, monkeypatch):
    sent = []
    monkeypatch.setattr(torke, "_http", lambda url, **kw: sent.append(json.loads(kw["data"])) or "")
    out = run(tool.save_needed_parts(["drain pump"], "won't drain", "Whirlpool dishwasher", __user__=USER))
    assert "Added to your parts list: drain pump" in out and not sent  # kept by TorKe; HA off by default
    tool.valves.parts_list = True
    tool.valves.parts_webhook_url = "http://ha:8123/api/webhook/x"
    out = run(tool.save_needed_parts([{"name": "clamp", "link": "javascript:x", "qty": 2, "part_number": "W1"}],
                                     "won't drain", "Whirlpool dishwasher", __user__=USER))
    assert "Sent to Home Assistant" in out
    assert sent[0]["parts"] == [{"name": "clamp (W1)", "link": "", "store": "", "price": "", "qty": 2}]


def test_photo_read_from_upload_record(tmp_path):
    png = tmp_path / "photo.png"
    png.write_bytes(base64.b64decode(PNG_1PX.split(",", 1)[1]))
    files = [{"type": "file", "file": {"path": str(png), "meta": {"content_type": "image/png"}}}]
    assert torke._latest_user_photo([], files).startswith("data:image/png;base64,")
    files[0]["file"]["meta"]["content_type"] = "text/plain"
    assert torke._latest_user_photo([], files) == ""


def test_missing_user_and_null_args(tool):
    html, _ = body(run(tool.open_project("Drill", None, None, None, None, None)))
    assert "Drill" in html
    assert "Nothing listed" not in run(tool.check_tools(None))


# ---------------------------------------------------------------- tool lists, Homebox and manuals (v0.2)

import urllib.error  # noqa: E402
import urllib.parse  # noqa: E402


def make_pdf(pages):
    """A small real PDF with one text page per string ("" makes a page with no text)."""
    objs = {1: b"<< /Type /Catalog /Pages 2 0 R >>",
            3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"}
    kids = " ".join(f"{5 + 2 * i} 0 R" for i in range(len(pages)))
    objs[2] = f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode()
    for i, text in enumerate(pages):
        ops = ["BT /F1 11 Tf 50 750 Td 14 TL"]
        for ln in text.split("\n"):
            ops.append("(" + ln.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)") + ") Tj T*")
        stream = ("\n".join(ops) + "\nET").encode() if text else b""
        objs[4 + 2 * i] = b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream"
        objs[5 + 2 * i] = (f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R "
                           f">> >> /Contents {4 + 2 * i} 0 R >>").encode()
    out, offsets = bytearray(b"%PDF-1.4\n"), {}
    for num in sorted(objs):
        offsets[num] = len(out)
        out += f"{num} 0 obj\n".encode() + objs[num] + b"\nendobj\n"
    xref, total = len(out), max(objs) + 1
    out += f"xref\n0 {total}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{offsets[n]:010d} 00000 n \n".encode() for n in range(1, total))
    out += f"trailer\n<< /Size {total} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


DISHWASHER_PDF = make_pdf([
    "Contents\nSafety 1\nDrain pump 2\nError codes 3",
    "Drain pump removal\nYou will need: Torx screwdriver T20, 7 mm socket, long-nose pliers\n"
    "Unplug the dishwasher. Remove the 4 screws on the base.",
    "Error E24: the drain is blocked. Clean the filter and the drain pump.",
])


class FakeHomebox:
    """Enough of Homebox's API for TorKe: new (0.26+, entities and tags) or old (items and labels)."""

    def __init__(self, new=True):
        self.new, self.posts = new, []
        where = "parent" if new else "location"
        self.entities = [
            {"id": "e1", "name": "Torque wrench 3/8", "quantity": 1, where: {"name": "Pegboard"},
             "tags": [{"name": "Tools"}]},
            {"id": "e2", "name": "Bosch dishwasher SHE3AR75UC", "quantity": 1, "tags": []},
        ]
        self.atts = {"e2": [{"id": "a1", "type": "manual", "title": "SHE3AR75UC manual.pdf",
                             "mimeType": "application/pdf"}]}

    def json(self, url, method="GET", data=None, headers=None, **kw):
        path = url.split("/api/v1", 1)[1]
        if path == "/users/login":
            return {"token": "tok"}
        assert headers["Authorization"] in ("Bearer tok", "Bearer hb_key")
        base, _, query = path.partition("?")
        q = urllib.parse.parse_qs(query)
        if (self.new and (base.startswith("/items") or base in ("/labels", "/locations"))) or \
                (not self.new and (base.startswith("/entities") or base == "/tags")):
            raise urllib.error.HTTPError(url, 404, "not found", {}, None)
        coll = "/entities" if self.new else "/items"
        if method == "POST":
            body = json.loads(data)
            self.posts.append((base, body))
            return {"id": "new1", **body}
        if base in ("/tags", "/labels"):
            return [{"id": "t1", "name": "Tools"}]
        if base == "/locations" or q.get("isLocation"):
            return [{"id": "L1", "name": "Shelf"}, {"id": "L2", "name": "Garage"}]
        if base == coll:
            rows = self.entities
            if q.get("tags" if self.new else "labels"):
                rows = [e for e in rows if e["tags"]]
            term = (q.get("q") or [""])[0].lower()
            if term:
                rows = [e for e in rows if any(w in e["name"].lower() for w in term.split())]
            return {"items": rows, "total": len(rows)}
        if base.startswith(coll + "/"):
            eid = base.split("/")[2]
            return {"id": eid, "attachments": self.atts.get(eid, [])}
        raise AssertionError(path)

    def fetch(self, url, headers=None, max_bytes=0, timeout=0):
        assert url.endswith(("/entities/e2/attachments/a1", "/items/e2/attachments/a1"))
        return DISHWASHER_PDF


def use_homebox(tool, monkeypatch, new=True, add=False, api_key=""):
    hb = FakeHomebox(new)
    monkeypatch.setattr(torke, "_json", hb.json)
    monkeypatch.setattr(torke, "_fetch_bytes", hb.fetch)
    tool.valves.homebox_lookup = True
    tool.valves.homebox_url = "http://homebox:7745"
    tool.valves.homebox_api_key = api_key
    tool.valves.homebox_add_tools = add
    tool.valves.homebox_tools_location = "Garage"
    torke._PDF_CACHE.clear()
    return hb


def test_tool_matching_rules():
    assert torke._tool_match("torque wrench", "Torque wrench 3/8 in")
    assert torke._tool_match("jack stands", "Jack stand, 3 ton")
    assert torke._tool_match("3/8 drive torque wrench", "torque wrench")
    assert not torke._tool_match("torque wrench", "wrench")
    assert not torke._tool_match("10 mm socket", "metric socket set")
    uv = torke.Tools.UserValves()
    assert "socket set" in torke._kit_covers("10 mm socket", uv)
    assert "tool kit" in torke._kit_covers("T20 Torx bit", uv)
    assert "tool kit" in torke._kit_covers("standard screwdriver", uv)
    assert torke._kit_covers("torque wrench", uv) == ""
    assert torke._kit_covers("1/2 in drive breaker bar", uv) == ""
    assert torke._kit_covers("jack stands", uv) == ""


def test_tools_card(tool):
    user = {"id": "t1", "valves": torke.Tools.UserValves(my_tools="torque wrench 3/8 in")}
    html, ctx = body(run(tool.check_tools(["torque wrench", "10 mm socket", "jack stands", "<b>x</b> puller"],
                                          "front brakes", "2012 Honda Civic", __user__=user)))
    assert "You have" in html and "You need" in html and "Add 2 to my needed tools" in html
    assert "I have it" in html and "<b>x</b>" not in html
    assert "torque wrench: have" in ctx and "10 mm socket: kit" in ctx and "jack stands: need" in ctx


def test_needed_list_is_separate_and_clears_when_owned(tool, monkeypatch):
    sent = []
    monkeypatch.setattr(torke, "_http", lambda url, **kw: sent.append((url, json.loads(kw["data"]))) or "")
    tool.valves.tools_needed_list = True
    tool.valves.tools_needed_webhook_url = "http://ha:8123/api/webhook/tools"
    out = run(tool.save_needed_tools(["jack stands", "32 mm axle nut socket"], "CV axle", "2012 Honda Civic",
                                     "manual p. 4", __user__=USER))
    assert "jack stands" in out and "Home Assistant" in out
    assert sent[0][0].endswith("/tools") and sent[0][1]["tools"] == ["jack stands", "32 mm axle nut socket"]
    assert "already" in run(tool.save_needed_tools(["jack stands"], "CV axle", "2012 Honda Civic", __user__=USER)).lower()
    out = run(tool.needed_tools_list("Honda Civic", __user__=USER))
    assert "32 mm axle nut socket" in out and "manual p. 4" in out
    out = run(tool.save_my_tools(["jack stands, 3 ton"], "garage", __user__=USER))
    assert "Saved to your TorKe tool list" in out and "Took 1 off the needed tools list" in out
    assert "jack stands" not in run(tool.needed_tools_list(__user__=USER))
    assert "Took 1" in run(tool.remove_needed_tools(["32 mm axle nut socket"], __user__=USER))
    assert "empty" in run(tool.needed_tools_list(__user__=USER))
    assert "Removed 1" in run(tool.remove_my_tools(["jack stands, 3 ton"], __user__=USER))
    assert not any("/parts" in u for u, _ in sent)


def test_homebox_new_api_tools_and_adding(tool, monkeypatch):
    hb = use_homebox(tool, monkeypatch, new=True, api_key="hb_key")
    html, ctx = body(run(tool.check_tools(["torque wrench", "jack stands"], "brakes", __user__=USER)))
    assert "Torque wrench 3/8, Pegboard (Homebox)" in html and "jack stands: need" in ctx
    out = run(tool.save_my_tools(["Jack stands 3 ton"], __user__=USER))
    assert "Adding to Homebox is off" in out and not hb.posts  # never writes unless allowed
    tool.valves.homebox_add_tools = True
    out = run(tool.save_my_tools(["Floor jack", "Torque wrench 3/8"], __user__=USER))
    assert "Added to Homebox: Floor jack (Garage)" in out and "already in Homebox" in out
    assert hb.posts == [("/entities", {"name": "Floor jack", "description": "Added by TorKe", "quantity": 1,
                                       "parentId": "L2", "tagIds": ["t1"]})]


def test_homebox_old_api(tool, monkeypatch):
    hb = use_homebox(tool, monkeypatch, new=False, add=True)
    html, _ = body(run(tool.check_tools(["torque wrench"], __user__=USER)))
    assert "Pegboard (Homebox)" in html
    run(tool.save_my_tools(["Floor jack"], __user__=USER))
    assert hb.posts == [("/items", {"name": "Floor jack", "description": "Added by TorKe",
                                    "locationId": "L2", "labelIds": ["t1"]})]


def test_manual_attached_in_homebox(tool, monkeypatch):
    use_homebox(tool, monkeypatch)
    out = run(tool.find_manuals("Bosch dishwasher", __user__=USER))
    assert "Attached to Bosch dishwasher SHE3AR75UC in Homebox: SHE3AR75UC manual.pdf" in out
    out = run(tool.read_item_manual("Bosch dishwasher", "error E24", __user__=USER))
    assert "--- Page 3 ---" in out and "drain is blocked" in out and torke.MANUAL_NOTE in out
    out = run(tool.read_item_manual("Bosch dishwasher", page=2, __user__=USER))
    assert "Drain pump removal" in out
    out = run(tool.find_tools_in_manual("drain pump", "Bosch dishwasher", __user__=USER))
    low = out.lower()
    assert "torx screwdriver" in low and "7 mm socket" in low and "long-nose pliers" in low and "(p2)" in out
    assert "You will need" in out and "check_tools" in out


def test_manual_attached_in_chat_and_scanned_pages(tool, tmp_path):
    pdf = tmp_path / "manual.pdf"
    pdf.write_bytes(DISHWASHER_PDF)
    files = [{"type": "file", "file": {"id": "f1", "path": str(pdf),
                                       "meta": {"name": "manual.pdf", "content_type": "application/pdf"}}}]
    out = run(tool.read_item_manual("Bosch dishwasher", "drain pump", __user__=USER, __files__=files))
    assert "manual.pdf (attached in this chat)" in out and "Page 2" in out
    scan = tmp_path / "scan.pdf"
    scan.write_bytes(make_pdf(["", ""]))
    files = [{"type": "file", "file": {"id": "f2", "path": str(scan),
                                       "meta": {"name": "scan.pdf", "content_type": "application/pdf"}}}]
    assert "no readable text" in run(tool.read_item_manual("x", __user__=USER, __files__=files))
    assert "No manual file found" in run(tool.read_item_manual("x", __user__=USER))


def test_ifixit_tools_from_guide(tool, monkeypatch):
    monkeypatch.setattr(torke, "_json", lambda url, **kw: {"url": "https://www.ifixit.com/Guide/x/9",
                                                          "tools": [{"text": "Spudger"}, {"text": "Phillips #1"}]})
    assert "iFixit is off" in run(tool.find_tools_in_manual(guide_url="https://www.ifixit.com/Guide/x/9"))
    tool.valves.site_ifixit = True
    out = run(tool.find_tools_in_manual(guide_url="https://www.ifixit.com/Guide/x/9"))
    assert "- Spudger" in out and "- Phillips #1" in out


def test_open_project_survives_restart(tool):
    run(tool.open_project("Bosch dishwasher", "won't drain", "appliance", "Bosch", "SHE3AR75UC",
                          __user__=USER, __chat_id__="c42"))
    torke._PROJECTS.clear()  # what a restart does
    assert "Bosch SHE3AR75UC" in run(tool.find_manuals(__user__=USER, __chat_id__="c42"))


# ---------------------------------------------------------------- parts list and shopping card (v0.3)

def test_shopping_card_and_got_it(tool):
    run(tool.open_project("2012 Honda Civic", "front brakes", "vehicle", "Honda", "Civic", "2012",
                          __user__=USER, __chat_id__="s1"))
    run(tool.save_needed_tools(["jack stands"], __user__=USER, __chat_id__="s1"))
    out = run(tool.save_needed_parts([
        {"name": "Front brake pads", "part_number": "D1089", "link": "https://www.rockauto.com/x",
         "price": "$42.99", "store": "RockAuto"},
        {"name": "Brake fluid DOT 3", "qty": 2}], __user__=USER, __chat_id__="s1"))
    assert "Front brake pads, Brake fluid DOT 3" in out
    assert "Already listed" in run(tool.save_needed_parts(["Front brake pads"], __user__=USER, __chat_id__="s1"))
    html, ctx = body(run(tool.shopping_list(__user__=USER)))
    assert "Tools to get" in html and "Parts to get" in html and "1 tool, 2 parts" in html
    assert 'href="https://www.rockauto.com/x"' in html and ">Buy<" in html and ">Find it<" in html
    assert "Part D1089. $42.99 at RockAuto" in html and "Brake fluid DOT 3 x2" in html
    assert "I got this part: Front brake pads. Take it off my parts list." in html
    assert "I got this tool: jack stands. Save it to my tools." in html
    assert "#D1089" in ctx and "remove_needed_parts" in ctx
    card, _ = body(run(tool.open_project("2012 Honda Civic", __user__=USER)))
    assert "2 on your list" in card and "1 needed" in card
    assert "Took 1" in run(tool.remove_needed_parts(["front brake pads"], __user__=USER))
    html, _ = body(run(tool.shopping_list("Bosch dishwasher", __user__=USER)))
    assert html.count("Nothing to get.") == 2


def test_shopping_card_escapes(tool):
    run(tool.save_needed_parts([{"name": "<img src=x onerror=alert(1)>", "link": 'https://x.example/"onclick=1'}],
                               __user__=USER))
    html, _ = body(run(tool.shopping_list(__user__=USER)))
    assert "<img src=x" not in html and '"onclick=1' not in html
