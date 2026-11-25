"""Offline tests for Keep copies in Homebox: the item's picture, iFixit guides, manual pages and PDFs are downloaded
once, attached to the item, and read from there afterwards. A stateful stand-in Homebox keeps what is attached."""

import base64
import re

import pytest

import torke
from test_torke import DISHWASHER_PDF, PNG_1PX, USER, body, run, tool, use_homebox  # noqa: F401

PNG_BYTES = base64.b64decode(PNG_1PX.split(",", 1)[1])
CIVIC, DISHWASHER = "2012 Honda Civic", "Bosch dishwasher SHE3AR75UC"
GUIDE_URL = "https://www.ifixit.com/Guide/Drain+Pump/123"
GUIDE = {"title": "Replacing the drain pump", "url": GUIDE_URL, "difficulty": "Moderate",
         "tools": [{"text": "Phillips #2", "url": "https://www.ifixit.com/t/1"}], "parts": [],
         "steps": [{"title": "Unplug it", "lines": [{"text_raw": "Unplug the dishwasher and shut off the water."}]}]}
PAGE_URL = "https://charm.li/Honda/2012/Civic/Brakes"
PAGE_HTML = '<html><body><h1>Brakes</h1><p>Caliper bolt torque 80 ft-lb</p><a href="/Honda/2012/Civic/Pads">Pads</a></body></html>'
PDF_URL = "https://charm.li/manuals/civic-service.pdf"
SEARX = {"results": [{"img_src": "https://img.example.com/civic.png", "thumbnail_src": "https://img.example.com/t.png",
                      "url": "https://example.com/civic", "title": "Civic"}]}


@pytest.fixture(params=[True, False], ids=["homebox-0.26", "homebox-older"])
def world(request, tool, monkeypatch):
    """Homebox that remembers attachments, a counted fake web, and the switches Keep copies needs."""
    hb = use_homebox(tool, monkeypatch, new=request.param)
    w = type("World", (), {})()
    w.hb, w.tool, w.store, w.uploads = hb, tool, {}, []
    w.json_calls, w.web_calls, w.page_calls = [], [], []
    w.web = {"https://img.example.com/civic.png": PNG_BYTES, PDF_URL: DISHWASHER_PDF}
    w.guides = {"ifixit.com/api/2.0/guides/123": GUIDE}

    def fake_json(url, **kw):
        if "homebox:7745" in url:
            return hb.json(url, **kw)
        w.json_calls.append(url)
        if "searxng:8080" in url:
            return SEARX
        for key, val in w.guides.items():
            if key in url:
                return val
        raise AssertionError(f"unexpected call: {url}")

    def fake_http(url, **kw):  # the multipart upload that attaches a file to an item
        data, boundary = kw["data"], kw["headers"]["Content-Type"].split("boundary=")[1].encode()
        kind = re.search(rb'name="type"\r\n\r\n(.*?)\r\n', data).group(1).decode()
        head, _, rest = data.partition(b'name="file"')
        mime = re.search(rb"Content-Type: (.*?)\r\n", rest).group(1).decode()
        payload = rest.partition(b"\r\n\r\n")[2]
        payload = payload[: payload.rindex(b"\r\n--" + boundary + b"--")]
        title = re.search(rb'filename="(.*?)"', rest).group(1).decode()
        eid, aid = url.split("/")[-2], f"u{len(w.store) + 1}"
        w.store[aid] = payload
        hb.atts.setdefault(eid, []).append({"id": aid, "type": kind, "title": title, "mimeType": mime})
        w.uploads.append((eid, kind, title, mime))
        return '{"id": "%s"}' % aid

    def fake_fetch_bytes(url, headers=None, max_bytes=0, timeout=0):  # Homebox downloads
        aid = url.rsplit("/", 1)[1]
        data = w.store[aid] if aid in w.store else hb.fetch(url)
        if max_bytes and len(data) > max_bytes:
            raise ValueError("too big")
        return data

    def fake_limited(url, max_bytes, domains=None, timeout=0):
        w.web_calls.append(url)
        if len(w.web[url]) > max_bytes:
            raise ValueError("too big")
        return w.web[url]

    def fake_page(url, domains, timeout=25):
        w.page_calls.append(url)
        return PAGE_HTML

    monkeypatch.setattr(torke, "_json", fake_json)
    monkeypatch.setattr(torke, "_http", fake_http)
    monkeypatch.setattr(torke, "_fetch_bytes", fake_fetch_bytes)
    monkeypatch.setattr(torke, "_fetch_limited", fake_limited)
    monkeypatch.setattr(torke, "_fetch_page", fake_page)
    monkeypatch.setattr(torke, "_is_public", lambda url: True)
    tool.valves.keep_copies = True
    tool.valves.site_ifixit = True
    tool.valves.site_charm_li = True
    return w


def card(w, item=CIVIC, **kw):
    return body(run(w.tool.open_project(item, __user__=USER, __chat_id__="c1", **kw)))


# ---------------------------------------------------------------- the picture

def test_web_picture_downloaded_once_and_kept(world):
    world.tool.valves.show_pictures, world.tool.valves.searxng_url = True, "http://searxng:8080"
    html, ctx = card(world)
    assert world.web_calls == ["https://img.example.com/civic.png"]
    assert world.uploads == [("e3", "photo", "torke-picture-example.com.png", "image/png")]
    assert PNG_1PX in html and "Photo saved from example.com" in html and "kept in Homebox" in ctx
    searches = len(world.json_calls)
    html, _ = card(world)  # the next time: nothing searched, nothing downloaded, nothing attached
    assert len(world.web_calls) == 1 and len(world.uploads) == 1 and len(world.json_calls) == searches
    assert PNG_1PX in html and "Photo saved from example.com" in html


def test_picture_not_kept_when_switched_off(world):
    world.tool.valves.show_pictures, world.tool.valves.searxng_url = True, "http://searxng:8080"
    world.tool.valves.keep_copies = False
    html, _ = card(world)
    assert "https://img.example.com/civic.png" in html and not world.web_calls and not world.uploads
    world.tool.valves.keep_copies, world.tool.valves.homebox_write = True, False
    html, _ = card(world)
    assert "https://img.example.com/civic.png" in html and not world.uploads  # read only: nothing attached


def test_picture_only_kept_on_the_exact_item(world):
    world.tool.valves.show_pictures, world.tool.valves.searxng_url = True, "http://searxng:8080"
    html, _ = card(world, "2013 Honda Civic")  # Homebox only has the 2012: don't attach to the wrong car
    assert not world.uploads and "https://img.example.com/civic.png" in html
    html, _ = card(world, "Spaceship")
    assert not world.uploads


def test_picture_too_big_falls_back_to_the_link(world):
    world.tool.valves.show_pictures, world.tool.valves.searxng_url = True, "http://searxng:8080"
    world.web["https://img.example.com/civic.png"] = b"\x89PNG\r\n\x1a\n" + b"0" * (torke.MAX_KEPT_PICTURE_BYTES + 1)
    world.web["https://img.example.com/t.png"] = b"not a picture"
    html, _ = card(world)
    assert not world.uploads and "https://img.example.com/civic.png" in html


def test_smaller_version_kept_when_the_full_one_is_too_big(world):
    world.tool.valves.show_pictures, world.tool.valves.searxng_url = True, "http://searxng:8080"
    world.web["https://img.example.com/civic.png"] = b"\x89PNG\r\n\x1a\n" + b"0" * (torke.MAX_KEPT_PICTURE_BYTES + 1)
    world.web["https://img.example.com/t.png"] = PNG_BYTES
    html, _ = card(world)
    assert world.uploads and world.web_calls[-1] == "https://img.example.com/t.png" and PNG_1PX in html


def test_own_photo_in_homebox_beats_the_kept_one_and_the_chat_photo_beats_both(world):
    world.hb.atts["e3"] = [{"id": "m1", "type": "photo", "title": "torke-picture-old.example.com.png", "mimeType": "x"},
                           {"id": "m2", "type": "photo", "title": "my civic.jpg", "mimeType": "x"}]
    mine = b"\xff\xd8\xff" + b"jpeg"
    world.store.update(m1=PNG_BYTES, m2=mine)
    html, _ = card(world)
    assert "Photo from Homebox" in html and base64.b64encode(mine).decode() in html
    msgs = [{"role": "user", "content": [{"type": "image_url", "image_url": {"url": PNG_1PX}}]}]
    html, _ = card(world, __messages__=msgs)
    assert "Your photo" in html and not world.uploads  # their chat photo is shown, never saved


def test_saved_picture_is_read_even_without_keep_copies(world):
    world.tool.valves.show_pictures, world.tool.valves.searxng_url = True, "http://searxng:8080"
    card(world)
    world.tool.valves.keep_copies = False
    html, _ = card(world)
    assert PNG_1PX in html and len(world.web_calls) == 1


# ---------------------------------------------------------------- guides and pages

def test_ifixit_guide_downloaded_once_and_kept(world):
    first = run(world.tool.read_manual_page(GUIDE_URL, DISHWASHER))
    assert "Step 1: Unplug it" in first and f"A copy was saved to {DISHWASHER} in Homebox" in first
    assert world.uploads[0][0] == "e2" and world.uploads[0][1] == "manual" and world.uploads[0][3] == "application/json"
    assert re.fullmatch(r"torke-copy-[0-9a-f]{12}-replacing-the-drain-pump\.json", world.uploads[0][2])
    n = len(world.json_calls)
    again = run(world.tool.read_manual_page(GUIDE_URL, DISHWASHER))
    assert "Step 1: Unplug it" in again and "nothing was downloaded" in again and len(world.uploads) == 1
    assert not [u for u in world.json_calls[n:] if "ifixit" in u]
    tools = run(world.tool.find_tools_in_manual("drain pump", DISHWASHER, guide_url=GUIDE_URL))
    assert "Phillips #2" in tools and not [u for u in world.json_calls[n:] if "ifixit" in u]


def test_ifixit_guide_uses_the_open_project_item(world):
    run(world.tool.open_project(DISHWASHER, "drain pump", "appliance", __user__=USER, __chat_id__="c9"))
    out = run(world.tool.read_manual_page(GUIDE_URL, __user__=USER, __chat_id__="c9"))
    assert f"A copy was saved to {DISHWASHER}" in out


def test_ifixit_guide_not_kept_without_an_item_or_switch(world):
    assert "No item was named" in run(world.tool.read_manual_page(GUIDE_URL))
    assert "isn't in Homebox, so no copy was kept" in run(world.tool.read_manual_page(GUIDE_URL, "Spaceship"))
    world.tool.valves.keep_copies = False
    out = run(world.tool.read_manual_page(GUIDE_URL, DISHWASHER))
    assert "Step 1" in out and "copy" not in out.lower().replace("copyright", "") and not world.uploads


def test_junk_from_ifixit_is_not_kept(world):
    world.guides["ifixit.com/api/2.0/guides/123"] = {"code": 404}
    run(world.tool.read_manual_page(GUIDE_URL, DISHWASHER))
    assert not world.uploads


def test_kept_guide_can_be_searched_like_a_manual(world):
    run(world.tool.read_manual_page(GUIDE_URL, DISHWASHER))
    out = run(world.tool.read_item_manual(DISHWASHER, "unplug water"))
    assert "Unplug the dishwasher and shut off the water" in out and "torke-copy-" in out


def test_manual_site_page_downloaded_once_and_kept(world):
    first = run(world.tool.read_manual_page(PAGE_URL, CIVIC))
    assert "Caliper bolt torque 80 ft-lb" in first and "/Honda/2012/Civic/Pads" in first
    assert f"A copy was saved to {CIVIC}" in first and world.page_calls == [PAGE_URL]
    again = run(world.tool.read_manual_page(PAGE_URL, CIVIC))
    assert "Caliper bolt torque 80 ft-lb" in again and "/Honda/2012/Civic/Pads" in again  # the links come back too
    assert "nothing was downloaded" in again and world.page_calls == [PAGE_URL] and len(world.uploads) == 1


def test_manual_site_pdf_downloaded_once_and_kept(world):
    first = run(world.tool.read_manual_page(PDF_URL, CIVIC))
    assert "PDF:" in first and "pages" in first and f"A copy was saved to {CIVIC}" in first
    eid, kind, title, mime = world.uploads[0]
    assert (eid, kind, mime) == ("e3", "manual", "application/pdf") and title.endswith(".pdf")
    assert world.store["u1"] == DISHWASHER_PDF and world.web_calls == [PDF_URL]
    again = run(world.tool.read_manual_page(PDF_URL, CIVIC))
    assert "nothing was downloaded" in again and world.web_calls == [PDF_URL]
    assert "drain" in run(world.tool.read_item_manual(CIVIC, "drain pump")).lower()


def test_links_only_sites_are_never_downloaded_or_kept(world):
    world.tool.valves.site_manualslib = True
    out = run(world.tool.read_manual_page("https://www.manualslib.com/manual/1/x.html", CIVIC))
    assert "terms don't allow" in out
    out = run(world.tool.read_manual_page("https://www.manualslib.com/manual/1/x.pdf", CIVIC))
    assert "terms don't allow" in out and not world.web_calls and not world.page_calls and not world.uploads
    assert "isn't on TorKe's list" in run(world.tool.read_manual_page("https://random.example.org/a.pdf", CIVIC))


def test_failed_save_is_reported_not_fatal(world, monkeypatch):
    def boom(url, **kw):
        raise OSError("disk full")
    monkeypatch.setattr(torke, "_http", boom)
    out = run(world.tool.read_manual_page(GUIDE_URL, DISHWASHER))
    assert "Step 1: Unplug it" in out and "couldn't be saved to Homebox (disk full)" in out


# ---------------------------------------------------------------- the download helper

def test_fetch_limited_refuses_private_addresses(monkeypatch):
    monkeypatch.undo()
    for url in ("http://127.0.0.1/x.png", "http://localhost:8080/a", "http://169.254.169.254/latest", "file:///etc/passwd"):
        with pytest.raises(ValueError):
            torke._fetch_limited(url, 1000)


def test_copy_names_and_image_types():
    key = torke._copy_key("https://example.com/a")
    name = torke._copy_name(key, "Replacing the Drain Pump (Bosch)!", "json")
    assert name == f"torke-copy-{key}-replacing-the-drain-pump-bosch.json"
    assert torke._is_copy({"title": name}, key) and not torke._is_copy({"title": name}, torke._copy_key("other"))
    assert not torke._is_copy({"title": "my manual.pdf"}, key)
    assert torke._image_mime(PNG_BYTES) == "image/png" and torke._image_mime(b"\xff\xd8\xffx") == "image/jpeg"
    assert torke._image_mime(b"RIFF1234WEBPxxxx") == "image/webp" and torke._image_mime(b"<html>") == ""
