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


# ---------------------------------------------------------------- Homebox: tools, parts, manuals, repair log

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
    """A small in-memory Homebox: new API (0.26+, entities and tags) or old (items and labels)."""

    def __init__(self, new=True):
        self.new, self.calls, self.created, self.puts, self.n = new, [], [], [], 100
        self.tags = {"t1": "Tools"}
        self.locs = {"L1": "Shelf", "L2": "Garage", "L3": "Parts shelf"}
        self.items, self.maint = {}, {}
        self.add("e1", "Torque wrench 3/8", ["Tools"], "L2")
        self.add("e2", "Bosch dishwasher SHE3AR75UC", [], "L1")
        self.add("e3", "2012 Honda Civic", [], "L2")
        self.add("e4", "Paint brushes", [], "L1")  # not tagged Tools or Parts: TorKe must never change it
        self.atts = {"e2": [{"id": "a1", "type": "manual", "title": "SHE3AR75UC manual.pdf",
                             "mimeType": "application/pdf"}]}

    def tag_named(self, name):
        for k, v in self.tags.items():
            if v.lower() == name.lower():
                return k
        k = f"t{len(self.tags) + 1}"
        self.tags[k] = name
        return k

    def add(self, eid, name, tags, loc):
        self.items[eid] = {"id": eid, "name": name, "quantity": 1, "description": "", "archived": False,
                           "tagIds": [self.tag_named(t) for t in tags], "loc": loc, "fields": [],
                           "purchasePrice": 12.5}

    def by_name(self, name):
        return next(i for i in self.items.values() if i["name"].lower() == name.lower())

    def tag_names(self, it):
        return sorted(self.tags[t] for t in it["tagIds"])

    def view(self, it):
        loc = {"id": it["loc"], "name": self.locs.get(it["loc"], "")}
        tags = [{"id": t, "name": self.tags[t]} for t in it["tagIds"]]
        d = {k: v for k, v in it.items() if k not in ("tagIds", "loc")}
        d.update({"parent": loc, "tags": tags} if self.new else {"location": loc, "labels": tags})
        return d

    def json(self, url, method="GET", data=None, headers=None, **kw):
        path = url.split("/api/v1", 1)[1]
        self.calls.append((method, path))
        if path == "/users/login":
            return {"token": "tok"}
        assert headers["Authorization"] in ("Bearer tok", "Bearer hb_key")
        base, _, query = path.partition("?")
        q = urllib.parse.parse_qs(query)
        if (self.new and (base.startswith("/items") or base in ("/labels", "/locations"))) or \
                (not self.new and (base.startswith("/entities") or base == "/tags")):
            raise urllib.error.HTTPError(url, 404, "not found", {}, None)
        coll, tag_word = ("/entities", "tags") if self.new else ("/items", "labels")
        loc_key, tag_key = ("parentId", "tagIds") if self.new else ("locationId", "labelIds")
        body = json.loads(data) if data else None
        if base == "/" + tag_word:
            if method == "POST":
                return {"id": self.tag_named(body["name"]), "name": body["name"]}
            return [{"id": k, "name": v} for k, v in self.tags.items()]
        if base == "/locations" or q.get("isLocation"):
            return [{"id": k, "name": v} for k, v in self.locs.items()]
        if base == coll and method == "GET":
            rows = [i for i in self.items.values() if not i["archived"]]
            if q.get(tag_word):
                rows = [i for i in rows if set(q[tag_word]) & set(i["tagIds"])]
            term = (q.get("q") or [""])[0].lower()
            if term:
                rows = [i for i in rows if any(w in i["name"].lower() for w in term.split())]
            return {"items": [self.view(i) for i in rows], "total": len(rows)}
        if base == coll and method == "POST":
            assert set(body) <= {"name", "description", "quantity", loc_key, tag_key}, body
            eid = f"n{self.n}"
            self.n += 1
            self.items[eid] = {"id": eid, "name": body["name"], "quantity": body.get("quantity", 1),
                               "description": body.get("description", ""), "archived": False,
                               "tagIds": body.get(tag_key, []), "loc": body.get(loc_key), "fields": []}
            self.created.append(body)
            return {"id": eid}
        parts = base.split("/")
        eid = parts[2] if len(parts) > 2 else ""
        if len(parts) == 3 and method == "GET":
            return dict(self.view(self.items[eid]), attachments=self.atts.get(eid, []))
        if len(parts) == 3 and method == "PUT":
            it = self.items[eid]
            assert body["id"] == eid and body.get("purchasePrice") == it.get("purchasePrice")  # nothing dropped
            it.update(name=body["name"], quantity=body["quantity"], description=body["description"],
                      archived=body.get("archived", False), fields=body.get("fields", []),
                      tagIds=body[tag_key], loc=body[loc_key])
            self.puts.append((eid, body))
            return self.view(it)
        if len(parts) == 4 and parts[3] == "maintenance":
            if method == "POST":
                self.maint.setdefault(eid, []).append(body)
                return body
            return list(self.maint.get(eid, []))
        raise AssertionError((method, path))

    def fetch(self, url, headers=None, max_bytes=0, timeout=0):
        assert url.endswith(("/entities/e2/attachments/a1", "/items/e2/attachments/a1"))
        return DISHWASHER_PDF


def use_homebox(tool, monkeypatch, new=True, write=True, api_key=""):
    hb = FakeHomebox(new)
    monkeypatch.setattr(torke, "_json", hb.json)
    monkeypatch.setattr(torke, "_fetch_bytes", hb.fetch)
    tool.valves.homebox_lookup = True
    tool.valves.homebox_url = "http://homebox:7745"
    tool.valves.homebox_api_key = api_key
    tool.valves.homebox_write = write
    tool.valves.homebox_tools_location = "Garage"
    torke._PDF_CACHE.clear()
    return hb


@pytest.fixture(params=[True, False], ids=["homebox-0.26", "homebox-older"])
def hbtool(request, tool, monkeypatch):
    return tool, use_homebox(tool, monkeypatch, new=request.param)


def test_without_homebox(tool):
    for out in (run(tool.save_my_tools(["torque wrench"], __user__=USER)),
                run(tool.save_needed_parts(["pads"], __user__=USER)),
                run(tool.shopping_list(__user__=USER)),
                run(tool.log_repair("Civic", "Brakes", "pads", __user__=USER)),
                run(tool.repair_history("Civic", __user__=USER))):
        assert "Homebox isn't set up" in out
    out = run(tool.check_tools(["torque wrench", "10 mm socket"], "brakes", "Civic", __user__=USER))
    assert isinstance(out, str) and "starter kit only" in out and "10 mm socket: kit" in out
    assert "rent or borrow" in out.lower()
    html, _ = body(run(tool.open_project("2012 Honda Civic", __user__=USER)))
    assert "Needs Homebox" in html


def test_read_only_until_allowed(tool, monkeypatch):
    hb = use_homebox(tool, monkeypatch, write=False)
    assert "can only read Homebox" in run(tool.save_my_tools(["floor jack"], __user__=USER))
    assert "can only read Homebox" in run(tool.log_repair("2012 Honda Civic", "x", "y", __user__=USER))
    assert not hb.created and not hb.puts and not hb.maint


def test_api_key_skips_login(tool, monkeypatch):
    hb = use_homebox(tool, monkeypatch, api_key="hb_key")
    run(tool.check_tools(__user__=USER))
    assert not any(path == "/users/login" for _, path in hb.calls)


def test_tools_card_from_homebox(hbtool):
    tool, hb = hbtool
    html, ctx = body(run(tool.check_tools(["torque wrench", "10 mm socket", "jack stands", "<b>x</b> puller"],
                                          "front brakes", "2012 Honda Civic", __user__=USER)))
    assert "Torque wrench 3/8, Garage (Homebox)" in html and "Missing" in html
    assert "You can still do this job" in html and "Rent or borrow" in html and "I have it" in html
    assert "Add 2 to my tools to get" in html and "<b>x</b>" not in html
    assert "torque wrench: have" in ctx and "10 mm socket: kit" in ctx and "jack stands: need" in ctx
    assert "don't stop the job" in ctx


def test_tools_to_get_flow(hbtool):
    tool, hb = hbtool
    out = run(tool.save_needed_tools(["jack stands"], "front brakes", "2012 Honda Civic", "manual p. 4", __user__=USER))
    assert "jack stands" in out
    jack = hb.by_name("jack stands")
    assert hb.tag_names(jack) == ["To get", "Tools"] and jack["description"] == "For 2012 Honda Civic: front brakes"
    assert {"name": "Source", "type": "text", "textValue": "manual p. 4"} in jack["fields"]
    assert jack["quantity"] == 0 and jack["loc"] == "L2"
    run(tool.save_needed_tools(["floor jack"], "front brakes", "2012 Honda Civic", rent=True, __user__=USER))
    assert hb.tag_names(hb.by_name("floor jack")) == ["Rent", "To get", "Tools"]
    assert "Now to buy: floor jack" in run(tool.save_needed_tools(["floor jack"], "front brakes", "2012 Honda Civic",
                                                                  __user__=USER))
    run(tool.save_needed_tools(["floor jack"], "front brakes", "2012 Honda Civic", rent=True, __user__=USER))
    assert "floor jack (rent or borrow)" in run(tool.needed_tools_list("Honda Civic", __user__=USER))
    out = run(tool.save_my_tools(["Jack stands, 3 ton"], __user__=USER))
    assert "Moved to your tools: Jack stands, 3 ton" in out
    assert hb.tag_names(jack) == ["Tools"] and jack["quantity"] == 1
    assert "archived in Homebox): floor jack" in run(tool.remove_needed_tools(["floor jack"], __user__=USER))
    assert hb.by_name("floor jack")["archived"]
    assert "Already in Homebox" in run(tool.save_my_tools(["Torque wrench 3/8"], __user__=USER))
    assert "Archived in Homebox: Torque wrench 3/8" in run(tool.remove_my_tools(["torque wrench"], __user__=USER))
    assert "None of those" in run(tool.remove_my_tools(["paint brushes"], __user__=USER))
    assert not hb.by_name("Paint brushes")["archived"]
    with pytest.raises(PermissionError):
        tool._edit(tool._hb(), {"id": "e4", "name": "Paint brushes", "tags": []}, archived=True)


def test_parts_flow_and_repair_log(hbtool, monkeypatch):
    tool, hb = hbtool
    sent = []
    monkeypatch.setattr(torke, "_http", lambda url, **kw: sent.append(json.loads(kw["data"])) or "")
    tool.valves.parts_list = True
    tool.valves.parts_webhook_url = "http://ha:8123/api/webhook/x"
    out = run(tool.save_needed_parts([{"name": "Front brake pads", "part_number": "D1089", "price": "$42.99",
                                       "store": "RockAuto", "link": "https://www.rockauto.com/x", "qty": 2},
                                      "Brake fluid DOT 3"], "front brakes", "2012 Honda Civic", __user__=USER))
    assert "Front brake pads, Brake fluid DOT 3" in out and "Sent to Home Assistant" in out
    assert sent[0]["parts"][0]["name"] == "Front brake pads (D1089)"
    pads = hb.by_name("Front brake pads")
    assert hb.tag_names(pads) == ["Parts", "To get"] and pads["loc"] == "L3" and pads["quantity"] == 0
    assert "Already listed" in run(tool.save_needed_parts(["Front brake pads"], "front brakes", "2012 Honda Civic",
                                                          __user__=USER))
    html, ctx = body(run(tool.shopping_list(__user__=USER)))
    assert "Front brake pads x2" in html and "Part D1089. $42.99 at RockAuto" in html
    assert 'href="https://www.rockauto.com/x"' in html and ">Buy<" in html and ">Find it<" in html
    assert "The Front brake pads arrived. Put it on the parts shelf." in html
    assert "On the parts shelf: Front brake pads" in run(tool.parts_arrived(["front brake pads"], __user__=USER))
    assert hb.tag_names(pads) == ["Parts"] and pads["quantity"] == 2 and pads["loc"] == "L3"
    card, _ = body(run(tool.open_project("2012 Honda Civic", __user__=USER)))
    assert "1 to get" in card  # brake fluid still to get
    assert "archived" in run(tool.use_parts(["front brake pads"], "2012 Honda Civic", __user__=USER))
    assert pads["archived"] and pads["quantity"] == 0
    assert "Took off" in run(tool.remove_needed_parts(["brake fluid"], __user__=USER))
    out = run(tool.log_repair("2012 Honda Civic", "Front brakes", "Pads D1089, 104k mi", "2026-10-29", "$90",
                              __user__=USER))
    assert "Logged on 2012 Honda Civic" in out
    assert hb.maint["e3"] == [{"name": "Front brakes", "description": "Pads D1089, 104k mi",
                               "completedDate": "2026-10-29", "cost": 90.0}]
    assert "Front brakes: Pads D1089" in run(tool.repair_history("2012 Honda Civic", __user__=USER))
    card, _ = body(run(tool.open_project("2012 Honda Civic", __user__=USER)))
    assert "1 entry" in card
    assert "Couldn't find" in run(tool.log_repair("Spaceship", "x", "y", __user__=USER))


def test_shopping_card_rentals_and_escaping(tool, monkeypatch):
    use_homebox(tool, monkeypatch)
    run(tool.save_needed_tools(["floor jack"], "front brakes", "2012 Honda Civic", rent=True, __user__=USER))
    run(tool.save_needed_parts([{"name": "<img src=x onerror=alert(1)>", "link": 'https://x.example/"onclick=1'}],
                               __user__=USER))
    html, _ = body(run(tool.shopping_list(__user__=USER)))
    assert "Find a rental" in html and "Rent or borrow. For 2012 Honda Civic" in html
    assert "I got the rental floor jack for this job." in html and "Returned" not in html
    assert "<img src=x" not in html and '"onclick=1' not in html
    html, _ = body(run(tool.shopping_list("Bosch dishwasher", __user__=USER)))
    assert html.count("Nothing to get.") == 2


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


def test_rental_lifecycle(hbtool):
    tool, hb = hbtool
    run(tool.save_needed_tools(["floor jack"], "front brakes", "2012 Honda Civic", rent=True, __user__=USER))
    html, _ = body(run(tool.check_tools(["floor jack"], "front brakes", "2012 Honda Civic", __user__=USER)))
    assert "Got the rental" in html and "I own one" in html and "Rent or borrow</button>" not in html
    assert "floor jack" in run(tool.rental_picked_up(["floor jack"], __user__=USER))
    jack = hb.by_name("floor jack")
    assert hb.tag_names(jack) == ["Rent", "Tools"] and jack["quantity"] == 1
    _, ctx = body(run(tool.check_tools(["floor jack"], "front brakes", "2012 Honda Civic", __user__=USER)))
    assert "floor jack: have (Rented or borrowed. Return it after the job)" in ctx
    html, ctx = body(run(tool.shopping_list(__user__=USER)))
    assert "floor jack" not in html and "ask about returning only when the job is over" in ctx
    card, _ = body(run(tool.open_project("2012 Honda Civic", __user__=USER)))
    assert "1 rented" in card
    out = run(tool.log_repair("2012 Honda Civic", "Front brakes", "Pads", __user__=USER))
    assert "still out: floor jack" in out and "rental_returned" in out
    assert "Returned and archived in Homebox: floor jack" in run(tool.rental_returned(["floor jack"], __user__=USER))
    assert jack["archived"]
    assert "still out" not in run(tool.log_repair("2012 Honda Civic", "Rotors", "x", __user__=USER))
    assert "Already in Homebox" in run(tool.save_my_tools(["Torque wrench 3/8"], __user__=USER))


def test_job_done_closes_everything_in_one_press(hbtool):
    tool, hb = hbtool
    card, _ = body(run(tool.open_project("2012 Honda Civic", "front brakes", "vehicle", "Honda", "Civic", "2012",
                                         __user__=USER, __chat_id__="j1")))
    assert "Job done" in card and "The job is done: the 2012 Honda Civic (front brakes). Close it out." in card
    run(tool.save_needed_parts([{"name": "Front brake pads", "part_number": "D1089"}, "Brake cleaner"],
                               __user__=USER, __chat_id__="j1"))
    run(tool.parts_arrived(["front brake pads"], __user__=USER))
    run(tool.save_needed_tools(["floor jack"], rent=True, __user__=USER, __chat_id__="j1"))
    run(tool.rental_picked_up(["floor jack"], __user__=USER))
    run(tool.save_needed_tools(["breaker bar"], __user__=USER, __chat_id__="j1"))
    run(tool.save_needed_parts(["Cabin air filter"], "air filter swap", "2012 Honda Civic", __user__=USER))  # other job
    html, ctx = body(run(tool.complete_job(__user__=USER, __chat_id__="j1")))
    assert "Parts to archive" in html and "Front brake pads" in html and "Part D1089" in html
    assert "Tools to return" in html and "floor jack" in html
    assert "Take off the lists" in html and "Brake cleaner" in html and "breaker bar" in html
    assert "Cabin air filter" not in html
    assert "Finish the job on 2012 Honda Civic: archive the parts, return the rentals" in html
    out = run(tool.finish_job(notes="Pads and rotors at 104k mi", __user__=USER, __chat_id__="j1"))
    assert "Parts archived: Front brake pads (D1089)" in out and "Returned: floor jack" in out
    assert "Brake cleaner" in out and "breaker bar" in out and "Logged on 2012 Honda Civic" in out
    for name in ("Front brake pads", "floor jack", "Brake cleaner", "breaker bar"):
        assert hb.by_name(name)["archived"]
    assert not hb.by_name("Cabin air filter")["archived"]
    entry = hb.maint["e3"][-1]
    assert entry["name"] == "front brakes" and "Parts installed: Front brake pads (D1089)" in entry["description"]
    assert "Pads and rotors at 104k mi" in entry["description"] and "returned: floor jack" in entry["description"]


def test_job_done_needs_homebox_and_write(tool, monkeypatch):
    card, _ = body(run(tool.open_project("2012 Honda Civic", __user__=USER)))
    assert "Job done" not in card
    assert "Homebox isn't set up" in run(tool.complete_job("2012 Honda Civic", __user__=USER))
    use_homebox(tool, monkeypatch, write=False)
    assert "can only read Homebox" in run(tool.finish_job("2012 Honda Civic", "brakes", __user__=USER))
