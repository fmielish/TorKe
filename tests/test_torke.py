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
    out = run(tool.tools_on_hand(["torque wrench"], __user__=USER))
    assert "100-piece socket set" in out and "multimeter" in out and "torque wrench" in out.lower()
    bare = {"id": "u2", "valves": torke.Tools.UserValves(has_starter_kit=False, has_socket_set=False,
                                                          has_multimeter=False, my_tools="")}
    assert "Nothing listed" in run(tool.tools_on_hand([], __user__=bare))


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


def test_parts_links_and_list_off(tool):
    out = run(tool.find_parts(["drain pump W10348269"], "Whirlpool dishwasher", __user__=USER))
    assert "amazon.com/s?k=drain+pump+W10348269" in out
    assert "parts list is off" in run(tool.add_to_parts_list([{"name": "pump"}], "dishwasher", __user__=USER))


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


def test_homebox_lookup(tool, monkeypatch):
    def fake(url, **kw):
        if url.endswith("/users/login"):
            return {"token": "abc"}
        assert kw["headers"]["Authorization"] == "Bearer abc"
        return {"items": [{"name": "Torque wrench 3/8", "quantity": 1, "location": {"name": "Pegboard"}}]}
    monkeypatch.setattr(torke, "_json", fake)
    tool.valves.homebox_lookup = True
    tool.valves.homebox_url = "http://homebox:7745"
    out = run(tool.tools_on_hand(["torque wrench"], __user__=USER))
    assert "Torque wrench 3/8 (qty 1, Pegboard)" in out


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
    tool.valves.parts_list = True
    tool.valves.parts_webhook_url = "http://ha:8123/api/webhook/x"
    out = run(tool.add_to_parts_list(["drain pump", {"name": "clamp", "link": "javascript:x", "qty": 2}],
                                     "dishwasher", __user__=USER))
    assert "Added 2 part(s)" in out and sent[0]["parts"][1]["link"] == ""


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
    assert "Nothing listed" not in run(tool.tools_on_hand(None))
