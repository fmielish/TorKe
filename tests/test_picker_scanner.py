"""Offline tests for the job picker, the Pick a job button and the scanner reader."""

import datetime
import io
from html import unescape
import json
import re
import urllib.error

import pytest

import torke
from test_torke import DISHWASHER_PDF, USER, body, run, tool, use_homebox  # noqa: F401

NOW = datetime.datetime.now(datetime.timezone.utc)


def rows_in(html):
    """The job rows on a picker card as (title, source) pairs."""
    return re.findall(r'<span class="jt">(.*?)</span><span class="src[^"]*">(.*?)</span>', html)


def groups_in(html):
    return re.findall(r'<button type="button" class="gh"[^>]*>(.*?)</button>', html)


# ---------------------------------------------------------------- the Pick a job button

def test_project_card_has_pick_a_job_button(tool):
    html, _ = body(run(tool.open_project("2012 Honda Civic", "", "vehicle", __user__=USER, __chat_id__="c1")))
    assert "Pick a job" in html and "Show me the jobs I can pick for the 2012 Honda Civic." in html
    assert html.count('<button type="button" class="blade') == 6  # the six buttons are unchanged


# ---------------------------------------------------------------- common jobs and grouping

def test_vehicle_picker_groups_by_system_and_is_searchable(tool):
    html, ctx = body(run(tool.job_picker("2012 Honda Civic", "vehicle", __user__=USER)))
    assert groups_in(html)[:3] == ["Routine upkeep", "Brakes", "Engine"]
    jobs = dict(rows_in(html))
    assert jobs["Front brake pads and rotors"] == "Common" and "Oil and filter change" in jobs
    assert 'id="q"' in html and "function filt()" in html and "Ask TorKe about it" in html
    assert "Start this job on my 2012 Honda Civic: Front brake pads and rotors." in html
    assert "no intervals" in ctx and "open_project" in ctx
    # a starting search word is carried into the box
    html, _ = body(run(tool.job_picker("2012 Honda Civic", "vehicle", "brake", __user__=USER)))
    assert 'value="brake"' in html


def test_groups_start_collapsed_and_open_on_tap_or_search(tool):
    html, _ = body(run(tool.job_picker("2012 Honda Civic", "vehicle", __user__=USER)))
    n = len(groups_in(html))
    assert n == 12 and html.count('class="panel grp shut"') == n and html.count('aria-expanded="false"') >= n
    assert "function tog(b)" in html and "setOpen(g,!!q&&n>0)" in html


def test_common_jobs_hold_no_numbers_that_look_like_specs():
    for cat, groups in torke._COMMON_JOBS.items():
        for group, names in groups:
            for n in names:
                assert not re.search(r"\d{3,}|\bmiles?\b|\bmonths?\b|\bqt\b|\bft-?lb", n, re.I), n


def test_other_kinds_group_by_where_the_job_came_from(tool):
    html, _ = body(run(tool.job_picker("Bosch dishwasher SHE3AR75UC", "appliance", __user__=USER)))
    assert groups_in(html) == ["Common jobs"] and ("Not draining", "Common") in rows_in(html)
    html, _ = body(run(tool.job_picker("Mystery gadget", "nonsense", __user__=USER)))
    assert ("Leaking", "Common") in rows_in(html)  # an unknown kind falls back to the general list


def test_uses_the_open_project_and_asks_when_there_is_none(tool):
    assert "Ask what they own" in run(tool.job_picker(__user__=USER, __chat_id__="nope"))
    run(tool.open_project("2012 Honda Civic", "", "vehicle", __user__=USER, __chat_id__="c2"))
    html, _ = body(run(tool.job_picker(__user__=USER, __chat_id__="c2")))
    assert "Front brake pads and rotors" in html


def test_job_group_keywords():
    assert torke._job_group("Front brake pad replacement") == "Brakes"
    assert torke._job_group("Oil and filter change") == "Routine upkeep"
    assert torke._job_group("Timing belt") == "Engine"
    assert torke._job_group("Water pump") == "Cooling"
    assert torke._job_group("Wheel bearing replacement") == "Suspension & steering"
    assert torke._job_group("Cabin air filter") == "Climate control"
    assert torke._job_group("Fuel filter") == "Fuel & emissions"
    assert torke._job_group("Reupholster the thing") == "Other"


def test_the_same_job_from_two_places_shows_once_from_the_most_specific(tool):
    rows = [{"title": "Brake pads", "group": "Brakes", "kind": "common", "source": "Common"},
            {"title": "brake pads!", "kind": "manual", "source": "Manual p.9"},
            {"title": "Brake pads", "kind": "ifixit", "source": "iFixit"}]
    merged = torke._merge_jobs(rows, "vehicle")
    assert len(merged) == 1 and merged[0]["source"] == "Manual p.9" and merged[0]["group"] == "Brakes"


# ---------------------------------------------------------------- manuals, iFixit and the repair log

@pytest.fixture(params=[True, False], ids=["homebox-0.26", "homebox-older"])
def hbtool(request, tool, monkeypatch):
    return tool, use_homebox(tool, monkeypatch, new=request.param)


def test_manual_contents_become_jobs(hbtool, monkeypatch):
    tool, hb = hbtool
    toc = ["Contents\nSafety 1\n5.1 Replacing the drain pump ........ 12\nRemoving the filter 14\n"
           "Cleaning the spray arm 15\nIndex 40"]
    monkeypatch.setattr(torke, "_pdf_pages", lambda data, max_pages=1500: toc)
    html, ctx = body(run(tool.job_picker("Bosch dishwasher SHE3AR75UC", "appliance", __user__=USER)))
    jobs = dict(rows_in(html))
    assert jobs["Replacing the drain pump"] == "Manual p.12" and jobs["Cleaning the spray arm"] == "Manual p.15"
    assert "Safety" not in jobs and "Index" not in jobs
    assert "From your manual" in groups_in(html) and "3 from its manual" in ctx


def test_repair_log_entries_show_as_done_and_due(hbtool):
    tool, hb = hbtool
    hb.maint["e3"] = [
        {"name": "Replaced front brake pads", "completedDate": "2026-03-14", "description": "Mileage: 90,000"},
        {"name": "Change oil", "scheduledDate": "2026-12-01"},
        {"name": "Old note without a date"}]
    html, _ = body(run(tool.job_picker("2012 Honda Civic", "vehicle", __user__=USER)))
    jobs = dict(rows_in(html))
    assert jobs["Replaced front brake pads"] == "Done 2026-03-14" and jobs["Change oil"] == "Due 2026-12-01"
    assert "Old note without a date" not in jobs
    assert 'class="src hot">Due 2026-12-01' in html
    # grouped by system, with the log entry beside the common jobs for that system
    assert "Replaced front brake pads" in html.split(">Brakes</button>")[1].split("</section>")[0]


def test_ifixit_guides_only_when_on_and_links_are_checked(tool, monkeypatch):
    seen = []

    def fake(url, **kw):
        seen.append(url)
        return {"results": [{"dataType": "guide", "title": "Honda Civic <b>Brake Pad</b> Replacement",
                             "url": "https://www.ifixit.com/Guide/Civic/1"},
                            {"dataType": "guide", "title": "Sneaky", "url": "https://evil.example/x"},
                            {"dataType": "wiki", "title": "Not a guide"}]}
    monkeypatch.setattr(torke, "_json", fake)
    html, _ = body(run(tool.job_picker("2012 Honda Civic", "vehicle", __user__=USER)))
    assert not seen and "iFixit" not in html
    tool.valves.site_ifixit = True
    html, _ = body(run(tool.job_picker("2012 Honda Civic", "vehicle", __user__=USER)))
    assert "ifixit.com/api/2.0/search" in seen[0]
    assert ("Honda Civic Brake Pad Replacement", "iFixit") in rows_in(html)
    assert html.count('class="mini" href="https://www.ifixit.com/Guide/Civic/1"') == 1
    assert 'href="https://evil.example' not in html
    assert "Not a guide" not in html


def test_a_failing_source_is_noted_not_fatal(tool, monkeypatch):
    def boom(url, **kw):
        raise OSError("offline")
    monkeypatch.setattr(torke, "_json", boom)
    tool.valves.site_ifixit = True
    html, ctx = body(run(tool.job_picker("2012 Honda Civic", "vehicle", __user__=USER)))
    assert ("Front brake pads and rotors", "Common") in rows_in(html)
    assert "iFixit couldn't be reached" in unescape(html) and "iFixit couldn't be reached" in ctx


def test_hostile_text_is_escaped_on_the_picker(tool):
    html, _ = body(run(tool.job_picker('<script>alert(1)</script>', "other", '"><img src=x>', __user__=USER)))
    assert "<script>alert(1)" not in html.split("<script>const ITEM")[0] and "<img src=x" not in html


def test_picker_card_carries_the_theme_button_and_saved_look(tool):
    run(tool.set_theme("light", "red", __user__=USER))
    html, _ = body(run(tool.job_picker("2012 Honda Civic", "vehicle", __user__=USER)))
    assert 'data-mode="light" data-accent="red"' in html and 'class="themebtn"' in html
    torke._write_store("theme", USER, {})


# ---------------------------------------------------------------- trouble codes

CODES = {"time": NOW.isoformat(), "vin": "1HGCM82633A004352",
         "codes": [{"code": "P0301", "status": "stored", "description": "Cylinder 1 Misfire Detected"},
                   {"code": "p0420", "status": "pending"}, {"code": "P0301", "status": "pending"},
                   "B0100", "ZZZ", {"code": "U3000"}],
         "freeze_frame": {"Engine speed": "2150 rpm", "Coolant temp": "88 C"}}


def feed(tool, monkeypatch, data=CODES, **valves):
    monkeypatch.setattr(torke, "SCANNER_FEED_READY", True)
    tool.valves.scanner_feed = True
    tool.valves.scanner_url = "http://scanner.local:8765/codes"
    for k, v in valves.items():
        setattr(tool.valves, k, v)
    calls = []

    def fake(url, **kw):
        calls.append((url, kw))
        if isinstance(data, Exception):
            raise data
        return data
    monkeypatch.setattr(torke, "_json", fake)
    return calls


def test_live_scanner_is_greyed_out_for_now(tool):
    tool.valves.scanner_feed = True
    tool.valves.scanner_url = "http://scanner.local:8765/codes"
    out = run(tool.read_scanner(__user__=USER))
    assert "isn't available yet" in out and "type the codes" in out
    assert "coming soon" in torke.Tools.Valves.model_fields["scanner_feed"].title.lower()
    assert "P0301" in run(tool.read_scanner(codes=["P0301"], __user__=USER))  # typed codes still work


def test_scanner_is_off_until_switched_on_and_set_up(tool, monkeypatch):
    monkeypatch.setattr(torke, "SCANNER_FEED_READY", True)
    assert "turned off" in run(tool.read_scanner(__user__=USER)) and "type the codes" in run(tool.read_scanner(__user__=USER))
    tool.valves.scanner_feed = True
    assert "address isn't filled in" in run(tool.read_scanner(__user__=USER))
    tool.valves.scanner_url = "ftp://nope"
    assert "address isn't filled in" in run(tool.read_scanner(__user__=USER))


def test_scanner_reading(tool, monkeypatch):
    calls = feed(tool, monkeypatch, scanner_token="s3cret")
    out = run(tool.read_scanner("2012 Honda Civic", __user__=USER))
    assert calls[0][0] == "http://scanner.local:8765/codes" and calls[0][1]["headers"] == {"Authorization": "Bearer s3cret"}
    assert "taken just now" in out
    assert "- P0301 (stored): powertrain" in out and "generic" in out and "ignition system or misfire" in out
    assert "The scanner's description: Cylinder 1 Misfire Detected." in out
    assert "- P0420 (pending)" in out and "- B0100 (reported): body" in out and "U3000 (reported)" in out
    assert out.count("P0301") == 1  # a code reported twice shows once
    assert "ignored: ZZZ" in out
    assert "Freeze frame" in out and "Engine speed: 2150 rpm" in out
    assert "VIN from the scanner: 1HGCM82633A004352" in out
    assert "never guess" in out and "never clears codes" in out and "readiness" in out


def test_scanner_never_invents_what_a_code_means(tool, monkeypatch):
    feed(tool, monkeypatch, data={"codes": [{"code": "P0420", "status": "stored"}]})
    out = run(tool.read_scanner(__user__=USER))
    assert "The scanner's description" not in out  # no description was sent, so none is made up
    assert "catalyst" not in out.lower()


def test_scanner_says_when_a_reading_is_old_or_empty(tool, monkeypatch):
    old = (NOW - datetime.timedelta(hours=5)).isoformat()
    feed(tool, monkeypatch, data={"time": old, "codes": []})
    out = run(tool.read_scanner(__user__=USER))
    assert "5 hours ago" in out and "read it again" in out
    assert "none are stored right now, not that nothing is wrong" in out
    assert "How to use this" not in out  # nothing to act on


def test_scanner_bridge_problems_are_explained(tool, monkeypatch):
    feed(tool, monkeypatch, data=OSError("connection refused"))
    out = run(tool.read_scanner(__user__=USER))
    assert "Couldn't reach the scanner bridge" in out and "ignition is on" in out
    feed(tool, monkeypatch, data=urllib.error.HTTPError("u", 401, "no", {}, io.BytesIO(b"{}")))
    assert "needs the right password" in run(tool.read_scanner(__user__=USER))
    feed(tool, monkeypatch, data=urllib.error.HTTPError(
        "u", 503, "bad", {}, io.BytesIO(json.dumps({"error": "couldn't connect to the adapter"}).encode())))
    assert "couldn't connect to the adapter" in run(tool.read_scanner(__user__=USER))
    feed(tool, monkeypatch, data={"error": "adapter asleep"})
    assert "adapter asleep" in run(tool.read_scanner(__user__=USER))


def test_typed_codes_work_without_a_scanner(tool):
    out = run(tool.read_scanner("2012 Honda Civic", ["p0301", "P0171", "not a code"], __user__=USER))
    assert "codes they typed" in out and "- P0301 (reported)" in out and "- P0171" in out and "ignored: NOTACODE" in out
    assert "taken" not in out
    assert "P0301" in run(tool.read_scanner(codes="P0301, P0420", __user__=USER))


def test_scanner_vin_is_compared_with_the_one_saved_in_homebox(tool, monkeypatch):
    hb = use_homebox(tool, monkeypatch)
    base = hb.json
    feed(tool, monkeypatch, data={"codes": ["P0301"], "vin": "1HGCM82633A004352"})
    hbjson = torke._json

    def both(url, **kw):
        return hbjson(url, **kw) if "scanner" in url else base(url, **kw)
    monkeypatch.setattr(torke, "_json", both)
    out = run(tool.read_scanner("2012 Honda Civic", __user__=USER))
    assert "VIN from the scanner" in out and "matches" not in out  # nothing saved to compare yet
    hb.items["e3"]["fields"] = [{"name": "VIN", "type": "text", "textValue": "1HGCM82633A004352"}]
    assert "matches the VIN saved on 2012 Honda Civic" in run(tool.read_scanner("2012 Honda Civic", __user__=USER))
    hb.items["e3"]["fields"] = [{"name": "VIN", "type": "text", "textValue": "2T1BR32E04C000001"}]
    assert "does NOT match" in run(tool.read_scanner("2012 Honda Civic", __user__=USER))


def test_code_shapes():
    assert "ignition system or misfire" in torke._dtc_info("P0301")
    assert "manufacturer-specific" in torke._dtc_info("P1456") and "area:" not in torke._dtc_info("P1456")
    assert "network and module communication" in torke._dtc_info("U0100")
    assert torke._dtc_info("hello") == "" and torke._dtc_info("P0G01") == ""
    assert "area:" not in torke._dtc_info("P3500")  # no area names are claimed for P3 codes


def test_feed_parsing_is_defensive():
    assert torke._parse_feed("nonsense")["codes"] == [] and torke._parse_feed(None)["codes"] == []
    assert [c["code"] for c in torke._parse_feed(["P0300", "p0301"])["codes"]] == ["P0300", "P0301"]
    big = torke._parse_feed({"codes": [f"P0{i:03X}" for i in range(50)]})
    assert len(big["codes"]) == torke.MAX_SCANNER_CODES and big["more"] == 20
    f = torke._parse_feed({"codes": [{"code": "P0301", "status": "weird", "description": "x" * 999}],
                           "vin": "not a vin", "time": "yesterday-ish", "freeze_frame": ["no"]})
    assert f["codes"][0]["status"] == "reported" and len(f["codes"][0]["description"]) == 200
    assert f["vin"] == "" and f["time"] is None and f["freeze"] == {}


def test_scanner_valves_default_off_and_password_is_hidden():
    v = torke.Tools.Valves()
    assert v.scanner_feed is False and v.scanner_url == ""
    assert torke.Tools.Valves.model_json_schema()["properties"]["scanner_token"]["input"] == {"type": "password"}


def test_no_stylesheet_contains_stray_control_characters():
    # a CSS escape like \25B8 written in a normal Python string becomes a control character and shows as garbage
    for name in dir(torke):
        if name.endswith("_CSS"):
            bad = [c for c in getattr(torke, name) if ord(c) < 32 and c not in "\n\t"]
            assert not bad, (name, bad)


def test_4x4_jobs_are_listed_and_trigger_the_lifting_warning(tool):
    names = [j for g, js in torke._COMMON_JOBS["vehicle"] if g == "Drivetrain & transmission" for j in js]
    for want in ("CV axle replacement", "U-joint replacement", "Front axle shaft replacement",
                 "4x4 hub or integrated wheel end (IWE) replacement", "Transfer case fluid change"):
        assert want in names
    assert torke._job_group("Replace the IWE actuator") == "Drivetrain & transmission"
    out = run(tool.safety_check("Replace the IWE actuator", "2013 Ford F-150", "vehicle", "Ford", "F-150", "2013",
                                __user__=USER))
    assert "jack stands" in out
