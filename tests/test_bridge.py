"""Offline tests for scripts/scanner_bridge.py, using a stand-in for python-OBD (no adapter, no car)."""

import importlib.util
import json
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

BRIDGE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "scanner_bridge.py"
spec = importlib.util.spec_from_file_location("scanner_bridge", BRIDGE_PATH)
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


class Resp:
    def __init__(self, value):
        self.value = value

    def is_null(self):
        return self.value is None


class Commands:
    GET_DTC = "GET_DTC"
    GET_CURRENT_DTC = "GET_CURRENT_DTC"
    CLEAR_DTC = "CLEAR_DTC"  # exists in python-OBD; the bridge must never use it


def fake_obd(connected=True, stored=None, pending=None, old=False, log=None):
    log = log if log is not None else []

    class Conn:
        def __init__(self, port, **kw):
            if old and kw:
                raise TypeError("unexpected keyword argument")
            log.append(("open", port, tuple(sorted(kw))))

        def is_connected(self):
            return connected

        def query(self, cmd):
            log.append(("query", cmd))
            return Resp({"GET_DTC": stored, "GET_CURRENT_DTC": pending}.get(cmd))

        def close(self):
            log.append(("close",))

    class Module:
        OBD = Conn
        commands = Commands

    return Module, log


def test_reading_has_stored_and_pending_codes_in_torkes_format():
    mod, log = fake_obd(stored=[("P0301", "Cylinder 1 Misfire Detected")], pending=[("P0420", "")])
    feed = bridge.take_reading(mod, "socket://192.168.0.10:35000", vin="1HGCM82633A004352")
    assert feed["codes"] == [{"code": "P0301", "status": "stored", "description": "Cylinder 1 Misfire Detected"},
                             {"code": "P0420", "status": "pending", "description": ""}]
    assert feed["vin"] == "1HGCM82633A004352" and feed["time"].endswith("+00:00")
    assert ("close",) in log
    # and TorKe can read what the bridge writes
    import torke
    parsed = torke._parse_feed(json.loads(json.dumps(feed)))
    assert [c["code"] for c in parsed["codes"]] == ["P0301", "P0420"] and parsed["time"] and parsed["vin"]


def test_it_only_ever_reads_the_two_code_lists():
    mod, log = fake_obd(stored=[], pending=[])
    bridge.take_reading(mod, "/dev/ttyUSB0")
    assert [x[1] for x in log if x[0] == "query"] == ["GET_DTC", "GET_CURRENT_DTC"]
    assert "CLEAR_DTC" not in BRIDGE_PATH.read_text()  # there's no code path that could clear anything


def test_no_codes_is_an_empty_list_not_an_error():
    mod, _ = fake_obd(stored=None, pending=None)
    assert bridge.take_reading(mod, "x")["codes"] == []


def test_a_missing_car_is_explained_and_the_adapter_is_still_closed():
    mod, log = fake_obd(connected=False)
    with pytest.raises(RuntimeError, match="ignition on"):
        bridge.take_reading(mod, "x")
    assert ("close",) in log


def test_older_python_obd_without_the_options_still_works():
    mod, log = fake_obd(old=True, stored=[("P0171", "")])
    assert bridge.take_reading(mod, "x")["codes"][0]["code"] == "P0171"
    assert [x for x in log if x[0] == "open"] == [("open", "x", ())]


def serve(read_feed, token=""):
    server = bridge.make_server("127.0.0.1:0", read_feed, token)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


def get(url, token=""):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"} if token else {})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def test_server_serves_the_reading_and_checks_the_password():
    server, base = serve(lambda: {"codes": [{"code": "P0301"}]}, token="s3cret")
    try:
        assert get(base + "/codes") == (401, {"error": "a password is needed"})
        assert get(base + "/codes", "wrong")[0] == 401
        assert get(base + "/codes", "s3cret") == (200, {"codes": [{"code": "P0301"}]})
        assert get(base + "/", "s3cret")[0] == 200
        assert get(base + "/other", "s3cret") == (404, {"error": "not found"})
    finally:
        server.shutdown()


def test_server_reports_read_failures_and_caches_briefly():
    reads = []

    def read():
        reads.append(1)
        if len(reads) == 1:
            raise RuntimeError("couldn't connect to the adapter and the car")
        return {"codes": []}
    server, base = serve(read)
    try:
        assert get(base + "/codes") == (503, {"error": "couldn't connect to the adapter and the car"})
        assert get(base + "/codes")[0] == 200            # tries again after a failure
        assert get(base + "/codes")[0] == 200 and len(reads) == 2  # then answers from the last reading
    finally:
        server.shutdown()


def test_command_line_rules(capsys, monkeypatch):
    mod, _ = fake_obd(stored=[("P0301", "Misfire")])
    assert bridge.main(["--port", "x", "--listen", "0.0.0.0:8765"], mod) == 2
    assert "needs a password" in capsys.readouterr().err
    assert bridge.main(["--port", "x", "--once"], mod) == 0
    assert json.loads(capsys.readouterr().out)["codes"][0]["code"] == "P0301"
    bad, _ = fake_obd(connected=False)
    assert bridge.main(["--port", "x", "--once"], bad) == 1
    assert "Couldn't read the car" in capsys.readouterr().err
    monkeypatch.setitem(sys.modules, "obd", None)  # as if python-OBD weren't installed
    assert bridge.main(["--port", "x", "--once"]) == 2
    assert "pip install obd" in capsys.readouterr().err
