"""Offline tests for the network devices add-on. The n8n code nodes run in Node with stand-ins for
Homebox, SearXNG and the phone. Skipped when Node isn't installed."""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ADDON = Path(__file__).resolve().parents[1] / "addons" / "network-devices"
WORKFLOW = json.loads((ADDON / "n8n-workflow.json").read_text(encoding="utf-8"))
NODES = {n["name"]: n for n in WORKFLOW["nodes"]}
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(not NODE, reason="Node isn't installed")

HARNESS = r"""
const input = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const { code, world } = input;
const calls = [];
const helpers = {
  getBinaryDataBuffer: async () => Buffer.from(world.file || '', 'latin1'),
  httpRequest: async (o) => {
    calls.push({ method: o.method, url: o.url, body: o.body, headers: o.headers, opts: o });
    if (o.url.startsWith('http://ha/')) return {};
    if (o.url.startsWith('http://sx/')) { if (world.searchDown) throw new Error('down'); return { results: world.results || [] }; }
    if (o.method === 'HEAD') return (world.heads || {})[o.url] || { statusCode: 200, headers: {} };
    if (world.homeboxDown) throw new Error('down');
    const path = o.url.replace('http://hb/api/v1', '');
    if (path === '/tags') return o.method === 'POST' ? { id: 'tag-1' } : (world.tags || []);
    if (path.startsWith('/entities?isLocation')) return { items: [{ id: 'loc-1', name: 'Home' }] };
    if (path.startsWith('/entities?')) return { items: world.items || [] };
    if (path === '/entities') return { id: 'item-' + calls.filter((c) => c.url.endsWith('/entities')).length };
    if (path.startsWith('/entities/')) return o.method === 'PUT' ? {} : world.item;
    throw new Error('unexpected ' + o.url);
  },
};
const settings = Object.assign({ homeboxUrl: 'http://hb/', homeboxApiKey: 'hb_test', searxngUrl: 'http://sx',
  notifyWebhookUrl: 'http://ha/hook', tag: 'Network device', location: '', maxNewPerRun: 10, maxPdfMB: 10,
  ignoreMacs: [], skipSites: [] }, world.settings || {});
const nodes = {
  'Settings': { first: () => ({ json: { settings, body: world.body || {} } }) },
  'Phone reply': { isExecuted: Boolean(world.fromPhone) },
  'Handle reply': { first: () => ({ json: world.job }) },
};
const $input = { first: () => world.input || { json: {} } };
const memory = world.memory || {};
const AsyncFunction = Object.getPrototypeOf(async () => {}).constructor;
// No require, URL or process: the n8n sandbox may not offer them.
const run = new AsyncFunction('$', '$input', '$getWorkflowStaticData', 'require', 'URL', 'process', code);
run.call({ helpers }, (n) => nodes[n], $input, () => memory)
  .then((out) => process.stdout.write(JSON.stringify({ out, calls, memory })))
  .catch((e) => process.stdout.write(JSON.stringify({ error: String(e.message), calls, memory })));
"""


def run(node, **world):
    payload = json.dumps({"code": NODES[node]["parameters"]["jsCode"], "world": world})
    done = subprocess.run([NODE, "-e", HARNESS], input=payload, capture_output=True, text=True, timeout=30)
    assert done.returncode == 0 and done.stdout, done.stderr
    return json.loads(done.stdout)


def report(*devices, as_text=False):
    text = {"new_devices": [dict(eveMac=m, devVendor=v, devName=n) for m, v, n in devices]}
    return {"attachments": [{"text": json.dumps(text) if as_text else text}]}


def sent(result):
    return [c["body"] for c in result["calls"] if c["url"] == "http://ha/hook"]


def created(result):
    return [c["body"] for c in result["calls"] if c["method"] == "POST" and c["url"].endswith("/entities")]


PRINTER = ("00:1b:a9:11:22:33", "Brother Industries", "BRW-office")
GOOD = {"url": "https://download.example.com/hl-l2350dw.pdf", "title": "HL-L2350DW User Guide"}


def offered(url=GOOD["url"], **extra):
    """Memory and item after a manual was offered for item-1."""
    return dict(fromPhone=True, memory={"offers": {"item-1": {"hash": "0a1b2c3d", "url": url, "name": "Printer"}}},
                item={"id": "item-1", "name": "Printer", "tags": [{"id": "tag-1", "name": "Network device"}],
                      "attachments": [], **extra})


def press(verb, text="", ident="0a1b2c3d"):
    return {"action": f"TORKE_{verb}|item-1|{ident}", "reply_text": text}


# ---------------------------------------------------------------- the files themselves

def test_workflow_wiring_and_safe_defaults():
    for source, outs in WORKFLOW["connections"].items():
        assert source in NODES
        assert all(link["node"] in NODES for link in outs["main"][0])
    assert WORKFLOW["active"] is False
    text = json.dumps(WORKFLOW)
    assert "PASTE_HOMEBOX_API_KEY" in text and not re.search(r"hb_[A-Za-z0-9]{12}", text)
    download = NODES["Download PDF"]["parameters"]["options"]["redirect"]["redirect"]
    assert download["followRedirects"] is False
    assert '"DELETE"' not in text and "'DELETE'" not in text


def test_home_assistant_ids_match_the_workflow():
    yaml = (ADDON / "home-assistant.yaml").read_text(encoding="utf-8")
    path = NODES["Phone reply"]["parameters"]["path"]
    assert path in yaml
    assert "PASTE_LONG_RANDOM_ID" in yaml and "PASTE_LONG_RANDOM_ID" in NODES["Settings"]["parameters"]["jsCode"]
    assert "startswith('TORKE_')" in yaml and "local_only: true" in yaml


# ---------------------------------------------------------------- new devices

@needs_node
@pytest.mark.parametrize("as_text", [False, True])
def test_new_device_is_saved_then_offered(as_text):
    r = run("New devices", body=report(PRINTER, as_text=as_text), results=[GOOD])
    made = created(r)
    assert len(made) == 1 and made[0]["name"] == "Brother Industries BRW-office"
    assert made[0]["parentId"] == "loc-1" and made[0]["tagIds"] == ["tag-1"]
    assert PRINTER[0] in made[0]["description"] and "guess" in made[0]["description"]
    note = sent(r)[0]
    assert [a["title"] for a in note["actions"]] == ["Save manual", "Fix model", "Skip"]
    assert note["url"] == GOOD["url"] and "download.example.com" in note["message"]
    assert not any("attachments" in c["url"] for c in r["calls"])  # nothing downloaded or attached yet
    assert r["memory"]["offers"]["item-1"]["url"] == GOOD["url"]
    assert all(c["headers"]["Authorization"] == "Bearer hb_test" for c in r["calls"] if "hb/api" in c["url"])


@needs_node
def test_older_field_names_work():
    body = {"attachments": [{"text": {"new_devices": [{"MAC": "00-1B-A9-11-22-33", "Device name": "(unknown) TEST"}]}}]}
    assert created(run("New devices", body=body))[0]["name"] == "TEST"


@needs_node
@pytest.mark.parametrize("mac", ["da:a1:19:00:00:01", "02:42:ac:11:00:02", "01:00:5e:00:00:01", "not-a-mac",
                                 "00:00:00:00:00:00"])
def test_randomized_and_bad_addresses_are_skipped(mac):
    r = run("New devices", body=report((mac, "x", "phone")))
    assert r["out"] == [] and r["calls"] == []


@needs_node
def test_duplicates_and_ignored_devices_are_skipped():
    items = [{"id": "old", "name": "Printer", "description": "MAC 00:1b:a9:11:22:33."}]
    r = run("New devices", body=report(PRINTER, PRINTER), items=items)
    assert created(r) == [] and sent(r) == []
    r = run("New devices", body=report(PRINTER), settings={"ignoreMacs": ["00-1B-A9"]})
    assert r["calls"] == []
    r = run("New devices", body=report(PRINTER, PRINTER))
    assert len(created(r)) == 1


@needs_node
def test_limit_per_report_names_the_rest():
    devices = [(f"00:1b:a9:00:00:{i:02x}", "Acme", f"d{i}") for i in range(4)]
    r = run("New devices", body=report(*devices), settings={"maxNewPerRun": 2})
    assert len(created(r)) == 2
    assert "00:1b:a9:00:00:02" in sent(r)[-1]["message"] and "00:1b:a9:00:00:03" in sent(r)[-1]["message"]


@needs_node
def test_hostile_names_are_cleaned():
    r = run("New devices", body=report(("00:1b:a9:11:22:33", "{{ states }}", "<b>evil\n\u202ename</b>" + "x" * 300)))
    name = created(r)[0]["name"]
    assert len(name) <= 121 and not re.search(r"[<>{}\n\u202e]", name)


@needs_node
@pytest.mark.parametrize("url", [
    "https://www.manualslib.com/x.pdf", "https://charm.li/x.pdf", "https://www.repairclinic.com/x.pdf",
    "http://192.168.1.5/x.pdf", "http://2130706433/x.pdf", "http://0x7f.0.0.1/x.pdf", "http://[::1]/x.pdf",
    "http://nas/x.pdf", "http://nas.local/x.pdf", "http://printer.home.arpa/x.pdf", "ftp://example.com/x.pdf",
    "https://user@example.com/x.pdf", "https://example.com:8123/x.pdf", "https://example.com\\@10.0.0.1/x.pdf",
    "https://example.com/manual.html"])
def test_links_that_are_never_offered(url):
    r = run("New devices", body=report(PRINTER), results=[{"url": url, "title": "x"}])
    note = sent(r)[0]
    assert note["title"] == "Manual needed" and [a["title"] for a in note["actions"]] == ["Fix model", "Skip"]


@needs_node
def test_search_down_still_saves_the_device():
    r = run("New devices", body=report(PRINTER), searchDown=True)
    assert len(created(r)) == 1 and "search failed" in sent(r)[0]["message"]


@needs_node
def test_homebox_down_is_reported():
    r = run("New devices", body=report(PRINTER), homeboxDown=True)
    assert r["error"] and "00:1b:a9:11:22:33" in sent(r)[0]["message"]


@needs_node
def test_branches_ignore_each_other():
    assert run("New devices", body=report(PRINTER), fromPhone=True)["calls"] == []
    assert run("Handle reply", body=press("SAVE"))["calls"] == []


# ---------------------------------------------------------------- replies

@needs_node
def test_save_passes_the_link_on():
    r = run("Handle reply", body=press("SAVE"), **offered())
    job = r["out"][0]["json"]
    assert job["url"] == GOOD["url"] and job["fileName"] == "network-manual-0a1b2c3d.pdf"


@needs_node
def test_old_or_forged_buttons_change_nothing():
    for body in (press("SAVE", ident="ffffffff"), {"action": "TORKE_SAVE|../x|0a1b2c3d"}, {"action": "OTHER"}):
        r = run("Handle reply", body=body, **offered())
        assert r["out"] == [] and not any("hb/api" in c["url"] for c in r["calls"])


@needs_node
def test_skip_forgets_the_offer():
    r = run("Handle reply", body=press("SKIP"), **offered())
    assert r["out"] == [] and r["calls"] == [] and r["memory"]["offers"] == {}


@needs_node
def test_already_saved():
    world = offered(attachments=[{"title": "network-manual-0a1b2c3d.pdf"}])
    r = run("Handle reply", body=press("SAVE"), **world)
    assert r["out"] == [] and sent(r)[0]["title"] == "Already saved"


@needs_node
def test_redirects_are_checked():
    start = GOOD["url"]
    ok = {start: {"statusCode": 302, "headers": {"location": "/files/real.pdf"}}}
    r = run("Handle reply", body=press("SAVE"), heads=ok, **offered())
    assert r["out"][0]["json"]["url"] == "https://download.example.com/files/real.pdf"
    for bad in ("http://192.168.1.1/admin", "//nas.local/x.pdf", "https://www.manualslib.com/x.pdf", "file:///etc/x"):
        heads = {start: {"statusCode": 302, "headers": {"location": bad}}}
        r = run("Handle reply", body=press("SAVE"), heads=heads, **offered())
        assert r["out"] == [] and sent(r)[0]["title"] == "Not saved", bad
    loop = {start: {"statusCode": 302, "headers": {"location": start}}}
    assert run("Handle reply", body=press("SAVE"), heads=loop, **offered())["out"] == []


@needs_node
def test_too_big_is_refused_before_download():
    heads = {GOOD["url"]: {"statusCode": 200, "headers": {"content-length": "20000000"}}}
    r = run("Handle reply", body=press("SAVE"), heads=heads, **offered())
    assert r["out"] == [] and "over 10 MB" in sent(r)[0]["message"]


@needs_node
def test_fix_model_renames_keeps_details_and_searches_again():
    world = offered(serialNumber="SN1", fields=[{"name": "Room"}], parent={"id": "loc-1"}, notes="mine")
    r = run("Handle reply", body=press("MODEL", "Brother HL-L2350DW"), results=[GOOD], **world)
    put = next(c["body"] for c in r["calls"] if c["method"] == "PUT")
    assert put["name"] == put["modelNumber"] == "Brother HL-L2350DW"
    assert put["serialNumber"] == "SN1" and put["notes"] == "mine" and put["fields"] == [{"name": "Room"}]
    assert put["parentId"] == "loc-1" and put["tagIds"] == ["tag-1"] and "attachments" not in put
    search = next(c["url"] for c in r["calls"] if c["url"].startswith("http://sx/"))
    assert "Brother%20HL-L2350DW%20manual" in search
    assert sent(r)[-1]["actions"][0]["title"] == "Save manual" and r["out"] == []
    assert r["memory"]["offers"]["item-1"]["hash"] != "0a1b2c3d"


@needs_node
def test_fix_model_only_touches_tagged_items_and_needs_text():
    r = run("Handle reply", body=press("MODEL", "X1"), **offered(tags=[{"id": "t", "name": "Tools"}]))
    assert not any(c["method"] == "PUT" for c in r["calls"])
    r = run("Handle reply", body=press("MODEL", "  "), **offered())
    assert not any(c["method"] == "PUT" for c in r["calls"]) and sent(r)[0]["title"] == "No model typed"


# ---------------------------------------------------------------- the downloaded file

JOB = {"itemId": "item-1", "name": "Printer", "url": GOOD["url"], "fileName": "network-manual-0a1b2c3d.pdf"}


@needs_node
@pytest.mark.parametrize("content,passes", [("%PDF-1.7 body", True), ("<html>sign in</html>", False), ("", False)])
def test_only_a_real_pdf_is_attached(content, passes):
    r = run("Check PDF", job=JOB, file=content, input={"json": {}, "binary": {"data": {"fileName": "x"}}})
    assert bool(r["out"]) is passes
    if passes:
        assert r["out"][0]["binary"]["data"]["fileName"] == JOB["fileName"]
    else:
        assert sent(r)[0]["title"] == "Manual not saved"


@needs_node
def test_failed_or_huge_download():
    assert run("Check PDF", job=JOB, input={"json": {"error": "302"}})["out"] == []
    r = run("Check PDF", job=JOB, file="%PDF-" + "x" * 2_000_000, settings={"maxPdfMB": 1},
            input={"json": {}, "binary": {"data": {}}})
    assert r["out"] == []


@needs_node
def test_result_message():
    memory = {"offers": {"item-1": {}}}
    r = run("Report result", job=JOB, memory=memory, input={"json": {"id": "item-1"}})
    assert sent(r)[0]["title"] == "Manual saved" and r["memory"]["offers"] == {}
    r = run("Report result", job=JOB, memory=memory, input={"json": {"error": "413"}})
    assert sent(r)[0]["title"] == "Manual not saved" and r["memory"]["offers"] == memory["offers"]
