"""Offline tests for the whole-house switches. Every switch starts off; each test turns on only what it needs."""

import base64
import datetime
import json

import pytest

import torke
from test_torke import FakeHomebox, PNG_1PX, USER, run, tool, use_homebox  # noqa: F401

TODAY = datetime.date.today()
PNG_BYTES = base64.b64decode(PNG_1PX.split(",", 1)[1])

HOUSE_SWITCHES = ("house_upkeep", "house_spares", "house_vin", "house_save_facts", "house_shop_work",
                  "house_handoffs", "house_voice")


def world(tool, monkeypatch, new=True, extra=None, **switches):
    """A fake Homebox plus canned public services; returns the Homebox and the list of file/webhook posts."""
    hb = use_homebox(tool, monkeypatch, new=new)
    posts = []

    def fake_json(url, **kw):
        if "homebox:7745" in url:
            return hb.json(url, **kw)
        for key, val in (extra or {}).items():
            if key in url:
                return val(url) if callable(val) else val
        raise AssertionError(f"unexpected call: {url}")

    def fake_http(url, **kw):
        posts.append((url, kw))
        return '{"id": "att1"}'

    monkeypatch.setattr(torke, "_json", fake_json)
    monkeypatch.setattr(torke, "_http", fake_http)
    for k, v in switches.items():
        setattr(tool.valves, k, v)
    return hb, posts


@pytest.fixture(params=[True, False], ids=["homebox-0.26", "homebox-older"])
def is_new(request):
    return request.param


# ---------------------------------------------------------------- everything is off until switched on

def test_every_house_function_refuses_when_its_switch_is_off(tool, monkeypatch):
    hb, posts = world(tool, monkeypatch)
    calls = [tool.set_upkeep("2012 Honda Civic", "Oil change", due_date=TODAY.isoformat()), tool.whats_due(),
             tool.set_spare("Furnace filter"), tool.use_spare("Furnace filter"), tool.spares_check(),
             tool.decode_vin("1HGCM82633A004352"), tool.vehicle_complaints("2012", "Honda", "Civic"),
             tool.save_item_facts("2012 Honda Civic", ["Year: 2012"]), tool.attach_invoice("2012 Honda Civic", PNG_1PX),
             tool.record_shop_work("2012 Honda Civic", "Oil change"), tool.cost_history("2012 Honda Civic"),
             tool.warranty_status("2012 Honda Civic"), tool.device_list(), tool.weekly_summary(),
             tool.monthly_recall_check(), tool.tell_room("Dinner is ready")]
    for c in calls:
        out = run(c)
        assert "off" in out or "isn't set up" in out, out
    assert not hb.created and not hb.puts and not hb.maint and not posts


def test_house_switches_need_homebox_and_write_permission(tool, monkeypatch):
    tool.valves.house_upkeep = tool.valves.house_shop_work = True
    assert "Homebox isn't set up" in run(tool.whats_due())
    assert "Homebox isn't set up" in run(tool.record_shop_work("Civic", "Oil change"))
    hb, _ = world(tool, monkeypatch, house_upkeep=True, house_shop_work=True, homebox_write=False)
    assert "can only read Homebox" in run(tool.set_upkeep("2012 Honda Civic", "Oil", due_date=TODAY.isoformat()))
    assert "can only read Homebox" in run(tool.record_shop_work("2012 Honda Civic", "Oil change"))
    assert not hb.maint


# ---------------------------------------------------------------- scheduled upkeep

def test_upkeep_dates_and_mileage_targets(tool, monkeypatch, is_new):
    hb, _ = world(tool, monkeypatch, new=is_new, house_upkeep=True)
    soon = (TODAY + datetime.timedelta(days=5)).isoformat()
    late = (TODAY - datetime.timedelta(days=3)).isoformat()
    far = (TODAY + datetime.timedelta(days=200)).isoformat()
    for d, task in ((soon, "Replace furnace filter"), (late, "Test smoke alarms"), (far, "Flush water heater")):
        assert "Saved on" in run(tool.set_upkeep("2012 Honda Civic", task, due_date=d, repeat="every 6 months"))
    assert hb.maint["e3"][0]["scheduledDate"] == soon and "Repeats every 6 months" in hb.maint["e3"][0]["description"]
    assert "YYYY-MM-DD" in run(tool.set_upkeep("2012 Honda Civic", "x", due_date="next week"))
    assert "Couldn't find" in run(tool.set_upkeep("Spaceship", "x", due_date=soon))

    out = run(tool.whats_due(days=30))
    assert "Replace furnace filter" in out and "Test smoke alarms" in out and "(overdue)" in out
    assert "Flush water heater" not in out  # beyond 30 days

    # a mileage target needs Save facts on owned items
    assert "off" in run(tool.set_upkeep("2012 Honda Civic", "Oil change", due_at="105000"))
    assert not hb.puts
    tool.valves.house_save_facts = True
    assert "at 105000" in run(tool.set_upkeep("2012 Honda Civic", "Oil change", due_at="105000"))
    hb.maint["e3"].append({"name": "Brakes", "description": "Mileage: 104,250", "completedDate": "2026-09-01"})
    out = run(tool.whats_due(item="2012 Honda Civic"))
    assert "oil change at 105000" in out and "750 to go" in out and "104,250" in out
    # the item's other details survive the update
    assert hb.items["e3"]["purchasePrice"] == 12.5


def test_nothing_due(tool, monkeypatch):
    world(tool, monkeypatch, house_upkeep=True)
    assert "Nothing due in the next 30 days" in run(tool.whats_due())


# ---------------------------------------------------------------- critical spares

def test_spares_track_low_and_stay_out_of_job_closeout(tool, monkeypatch, is_new):
    hb, _ = world(tool, monkeypatch, new=is_new, house_spares=True)
    assert "Now tracking" in run(tool.set_spare("Furnace filter 16x25x1", 3, 2, "2012 Honda Civic"))
    made = hb.by_name("Furnace filter 16x25x1")
    assert hb.tag_names(made) == ["Critical spare", "Parts"] and made["quantity"] == 3
    assert "LOW" not in run(tool.spares_check())

    out = run(tool.use_spare("furnace filter", 2))
    assert "1 left" in out and "below the minimum" in out and "save_needed_parts" in out
    assert "(LOW)" in run(tool.spares_check())
    assert "Updated" in run(tool.set_spare("Furnace filter 16x25x1", 4, 2))
    assert "isn't tracked" in run(tool.use_spare("Garden hose"))

    # a spare described as "For <item>" must not be archived when that item's job closes out
    tool.valves.homebox_write = True
    run(tool.finish_job("2012 Honda Civic", "Brake pads"))
    assert not hb.by_name("Furnace filter 16x25x1")["archived"]


# ---------------------------------------------------------------- VIN and complaints

VPIC = {"Results": [{"ModelYear": "2012", "Make": "HONDA", "Model": "Civic", "Trim": "EX", "DisplacementL": "1.8",
                     "EngineCylinders": "4", "FuelTypePrimary": "Gasoline", "BodyClass": "Sedan",
                     "DriveType": "FWD", "ErrorText": "0"}]}
COMPLAINTS = {"results": [
    {"components": "ENGINE,ELECTRICAL SYSTEM", "summary": "Stalls at idle", "dateComplaintFiled": "2025-03-02",
     "crash": False, "fire": False, "numberOfInjuries": 0},
    {"components": "ENGINE", "summary": "Check engine light", "dateComplaintFiled": "2025-05-09",
     "crash": True, "fire": False, "numberOfInjuries": 1}]}


def test_vin_decode_and_save(tool, monkeypatch):
    hb, _ = world(tool, monkeypatch, extra={"vpic.nhtsa.dot.gov": VPIC}, house_vin=True)
    assert "17 letters" in run(tool.decode_vin("1HGCM826O3A004352"))  # contains an O
    out = run(tool.decode_vin("1hg cm82633a004352"))
    assert "Make: Honda" in out and "Engine: 1.8L 4-cyl" in out and "Offer to save" in out
    assert not hb.puts
    # saving needs its own switch
    assert "Not saved" in run(tool.decode_vin("1HGCM82633A004352", "2012 Honda Civic", save=True))
    tool.valves.house_save_facts = True
    assert "Saved on 2012 Honda Civic" in run(tool.decode_vin("1HGCM82633A004352", "2012 Honda Civic", save=True))
    fields = {f["name"]: f["textValue"] for f in hb.items["e3"]["fields"]}
    assert fields == {"Year": "2012", "Make": "Honda", "Model": "Civic", "Engine": "1.8L 4-cyl",
                      "VIN": "1HGCM82633A004352"}


def test_complaints_and_safety_check(tool, monkeypatch):
    world(tool, monkeypatch, extra={"complaintsByVehicle": COMPLAINTS}, house_vin=True)
    out = run(tool.vehicle_complaints("2012", "Honda", "Civic"))
    assert "complaints for 2012 Honda Civic: 2" in out and "Engine (2)" in out and "1 crashes" in out
    assert "not recalls" in out and "Check engine light" in out
    out = run(tool.safety_check("front brake pads", "2012 Honda Civic", "vehicle", "Honda", "Civic", "2012",
                                __user__=USER))
    assert "NHTSA owner complaints" in out
    tool.valves.house_vin = False
    assert "NHTSA owner complaints" not in run(
        tool.safety_check("front brake pads", "2012 Honda Civic", "vehicle", "Honda", "Civic", "2012", __user__=USER))


# ---------------------------------------------------------------- facts and invoices on owned items

def test_facts_go_on_any_owned_item_only_when_allowed(tool, monkeypatch):
    hb, _ = world(tool, monkeypatch)
    assert "off" in run(tool.save_item_facts("Paint brushes", ["Size: 2 in"]))
    tool.valves.house_save_facts = True
    assert "Give each fact" in run(tool.save_item_facts("Paint brushes", ["no colon here"]))
    assert "Saved on Paint brushes" in run(tool.save_item_facts("Paint brushes", ["Size: 2 in", "Bristle: nylon"]))
    assert {f["name"] for f in hb.items["e4"]["fields"]} == {"Size", "Bristle"}
    assert hb.items["e4"]["purchasePrice"] == 12.5
    # the original rule still holds: TorKe's own edits stay on Tools and Parts, and the wider edit needs the switch
    client, brushes = tool._hb(), {"id": "e4", "name": "Paint brushes", "tags": []}
    with pytest.raises(PermissionError):
        tool._edit(client, brushes, quantity=0)
    tool.valves.house_save_facts = False
    with pytest.raises(PermissionError):
        tool._edit_any(client, brushes, quantity=0)
    assert hb.items["e4"]["quantity"] == 1


def test_attach_invoice(tool, monkeypatch):
    hb, posts = world(tool, monkeypatch, house_save_facts=True)
    assert "no photo" in run(tool.attach_invoice("2012 Honda Civic")).lower()
    assert "no photo" in run(tool.attach_invoice("2012 Honda Civic", "not base64 of a picture")).lower()
    msgs = [{"role": "user", "content": [{"type": "image_url", "image_url": {"url": PNG_1PX}}]}]
    assert "Attached the invoice to 2012 Honda Civic" in run(tool.attach_invoice("2012 Honda Civic",
                                                                                 __messages__=msgs))
    url, kw = posts[0]
    assert url.endswith("/attachments") and "e3" in url
    assert kw["headers"]["Content-Type"].startswith("multipart/form-data; boundary=")
    assert b'name="type"\r\n\r\nreceipt' in kw["data"] and PNG_BYTES in kw["data"]
    assert kw["headers"]["Authorization"] == "Bearer tok"
    assert "Couldn't find" in run(tool.attach_invoice("Spaceship", PNG_1PX))


# ---------------------------------------------------------------- shop work

def test_shop_work_warranty_cost_and_invoice(tool, monkeypatch, is_new):
    hb, posts = world(tool, monkeypatch, new=is_new, house_shop_work=True)
    out = run(tool.record_shop_work("2012 Honda Civic", "Oil change and tire rotation", "Quick Lube", "", "$89.95",
                                    "104,250", "12", "12000", "Used 0W-20 synthetic", PNG_1PX))
    assert "Recorded on 2012 Honda Civic" in out and "$89.95" in out
    assert "wasn't attached" in out and not posts  # Save facts on owned items is off
    entry = hb.maint["e3"][0]
    assert entry["cost"] == 89.95 and entry["completedDate"] == TODAY.isoformat()
    until = torke._add_months(TODAY, 12).isoformat()
    for line in ("Mileage: 104,250", "Done by: Quick Lube", "Used 0W-20 synthetic", "Warranty: 12 months or 12,000 miles",
                 f"Warranty until: {until}", "Warranty ends at: 116,250 miles"):
        assert line in entry["description"]

    tool.valves.house_save_facts = True
    out = run(tool.record_shop_work("2012 Honda Civic", "New windshield", "Glass Co", "2025-01-15", "400", "",
                                    "", "", "", PNG_1PX))
    assert "Invoice attached" in out and posts and "receipt" in posts[0][1]["data"].decode("latin-1")
    out = run(tool.record_shop_work("2012 Honda Civic", "Tires", invoice_image="garbage"))
    assert "couldn't be read" in out
    assert "YYYY-MM-DD" in run(tool.record_shop_work("2012 Honda Civic", "Tires", date="Tuesday"))
    assert "nothing was recorded" in run(tool.record_shop_work("Spaceship", "Tires"))

    out = run(tool.cost_history("2012 Honda Civic"))
    assert "$489.95 across 2 jobs" in out and "2025: $400.00" in out and f"{TODAY.year}: $89.95" in out
    out = run(tool.warranty_status("2012 Honda Civic"))
    assert "Still covered" in out and "Oil change and tire rotation" in out and f"until {until}" in out
    assert "to 116,250 miles" in out and "Expired" not in out


def test_warranty_expires_by_date_and_miles(tool, monkeypatch):
    hb, _ = world(tool, monkeypatch, house_shop_work=True)
    hb.maint["e3"] = [
        {"name": "Battery", "completedDate": "2020-01-01", "cost": 150,
         "description": "Warranty until: 2023-01-01"},
        {"name": "Alternator", "completedDate": "2026-01-01", "cost": 300,
         "description": "Mileage: 90,000\nWarranty ends at: 102,000 miles"},
        {"name": "Oil", "completedDate": "2026-09-01", "description": "Mileage: 104,250"}]
    out = run(tool.warranty_status("2012 Honda Civic"))
    assert "Expired:" in out and "Battery" in out and "Alternator" in out and "Still covered" not in out
    assert "No costs" in run(tool.cost_history("Paint brushes"))
    assert "No warranties" in run(tool.warranty_status("Paint brushes"))


# ---------------------------------------------------------------- hand-offs and voice

def test_handoffs(tool, monkeypatch):
    nhtsa = {"results": [{"NHTSACampaignNumber": "12V000000", "Component": "AIR BAGS", "Summary": "Inflator",
                          "Remedy": "Replace"}]}
    cpsc = []
    hb, _ = world(tool, monkeypatch, house_handoffs=True, house_upkeep=True, house_spares=True,
                  extra={"recallsByVehicle": nhtsa, "saferproducts.gov": cpsc})
    hb.items["e3"]["fields"] = [{"name": n, "type": "text", "textValue": v}
                                for n, v in (("Year", "2012"), ("Make", "Honda"), ("Model", "Civic"))]
    hb.items["e2"].update(manufacturer="Bosch", modelNumber="SHE3AR75UC")
    run(tool.set_upkeep("Bosch dishwasher SHE3AR75UC", "Clean filter", due_date=TODAY.isoformat()))
    run(tool.set_spare("Dishwasher salt", 0, 1))

    out = run(tool.device_list())
    assert "Bosch dishwasher SHE3AR75UC" in out and "Bosch SHE3AR75UC" in out and "2012 Honda Civic" in out
    assert "| 2012" in out and "Torque wrench" not in out  # tools aren't devices

    out = run(tool.weekly_summary())
    assert "Clean filter" in out and "Dishwasher salt (0 of 1)" in out

    out = run(tool.monthly_recall_check())
    assert "12V000000" in out and "2012 Honda Civic" in out and "1 with possible recalls" in out
    assert "Bosch dishwasher" not in out  # CPSC found nothing for it


def test_recall_check_with_nothing_found_and_a_failure(tool, monkeypatch):
    def boom(url):
        raise OSError("down")
    hb, _ = world(tool, monkeypatch, house_handoffs=True, extra={"recallsByVehicle": boom, "saferproducts.gov": []})
    hb.items["e3"]["fields"] = [{"name": n, "type": "text", "textValue": v}
                                for n, v in (("Year", "2012"), ("Make", "Honda"), ("Model", "Civic"))]
    out = run(tool.monthly_recall_check())
    assert "0 items checked" in out and "Couldn't check: 2012 Honda Civic" in out


def test_tell_room(tool, monkeypatch):
    _, posts = world(tool, monkeypatch, house_voice=True)
    assert "isn't set up" in run(tool.tell_room("Dinner is ready"))
    tool.valves.screen_webhook_url = "http://homeassistant:8123/api/webhook/abc"
    assert "nearest room screen" in run(tool.tell_room("Dinner is ready", speak=False))
    assert "Kitchen" in run(tool.tell_room("The oven is on", "Kitchen"))
    sent = json.loads(posts[0][1]["data"])
    assert sent == {"message": "Dinner is ready", "room": "", "speak": False, "from": "TorKe"}
    assert json.loads(posts[1][1]["data"])["room"] == "Kitchen"
    assert "There's nothing to send" in run(tool.tell_room("  "))


def test_helpers():
    assert torke._add_months(datetime.date(2026, 1, 31), 1) == datetime.date(2026, 2, 28)
    assert torke._add_months(datetime.date(2026, 11, 15), 3) == datetime.date(2027, 2, 15)
    assert torke._money("$1,089.50") == 1089.5 and torke._money("free") is None
    assert torke._num("104,250 miles") == 104250 and torke._num("") is None
    assert torke._fact_lines(["Year: 2012", "junk", "VIN:  X "]) == {"Year": "2012", "VIN": "X"}
    assert torke._decode_file("not base64 at all!!")[0] == b""
    assert torke._decode_file(PNG_1PX) == (PNG_BYTES, "image/png")
    assert torke._decode_file(base64.b64encode(PNG_BYTES).decode()) == (PNG_BYTES, "image/png")
    assert torke._decode_file("data:text/html;base64,PGI+") == (b"", "")
