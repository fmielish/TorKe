"""TorKe scanner bridge: reads trouble codes from an OBD-II adapter and serves them as JSON for TorKe.

READ ONLY. It asks the car for its stored and pending trouble codes and nothing else. It has no way to clear
codes or send anything that changes the car.

It uses the python-OBD library (pip install obd), so it reaches the adapters that library can:
  - Wi-Fi adapters:                       --port socket://192.168.0.10:35000   (use your adapter's address)
  - USB or serial adapters:               --port /dev/ttyUSB0   or   --port COM3
  - Classic Bluetooth adapters on Linux:  pair it, bind it to a serial port (rfcomm), then --port /dev/rfcomm0
It does NOT reach Bluetooth Low Energy adapters.

Run it on a computer in or near the car (a Raspberry Pi works) that TorKe's server can reach:

    pip install obd
    python scripts/scanner_bridge.py --port socket://192.168.0.10:35000 --listen 0.0.0.0:8765 --token CHANGE-ME

Then, in TorKe's settings, turn on Scanner feed and set its address to http://<that computer>:8765/codes
(and the same password). Test the adapter without TorKe first:  python scripts/scanner_bridge.py --port ... --once

Experimental: it has been tested here only against a stand-in for python-OBD, not a real adapter or car.
"""

import argparse
import datetime
import hmac
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CACHE_SECONDS = 10  # a second request within this long gets the last reading, so refreshing doesn't hammer the car
LOOPBACK = ("127.0.0.1", "localhost", "::1")


def take_reading(obd, port: str, vin: str = "") -> dict:
    """One reading: stored and pending trouble codes, in the feed format TorKe reads."""
    try:
        conn = obd.OBD(port, fast=False, timeout=5, check_voltage=False)
    except TypeError:  # an older python-OBD without those options
        conn = obd.OBD(port)
    try:
        if not conn.is_connected():
            raise RuntimeError("couldn't connect to the adapter and the car (is the adapter plugged in and the "
                               "ignition on?)")
        codes = []
        for status, command in (("stored", "GET_DTC"), ("pending", "GET_CURRENT_DTC")):
            cmd = getattr(obd.commands, command, None)
            if cmd is None:
                continue
            resp = conn.query(cmd)
            if resp is None or resp.is_null() or not isinstance(resp.value, (list, tuple)):
                continue
            for entry in resp.value:
                code, desc = (entry[0], entry[1]) if isinstance(entry, (list, tuple)) and len(entry) > 1 else (entry, "")
                codes.append({"code": str(code), "status": status, "description": str(desc or "")})
        feed = {"time": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), "codes": codes}
        if vin:
            feed["vin"] = vin
        return feed
    finally:
        conn.close()


def make_server(listen: str, read_feed, token: str = "") -> ThreadingHTTPServer:
    host, _, port = listen.rpartition(":")
    lock, cache = threading.Lock(), {"at": 0.0, "feed": None}

    def cached_feed():
        with lock:
            if cache["feed"] is None or time.monotonic() - cache["at"] > CACHE_SECONDS:
                cache["feed"], cache["at"] = read_feed(), time.monotonic()
            return cache["feed"]

    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, body: dict):
            data = json.dumps(body).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path.split("?")[0] not in ("/", "/codes"):
                return self._send(404, {"error": "not found"})
            if token and not hmac.compare_digest(self.headers.get("Authorization", ""), f"Bearer {token}"):
                return self._send(401, {"error": "a password is needed"})
            try:
                self._send(200, cached_feed())
            except Exception as e:
                self._send(503, {"error": str(e)[:160]})

        def log_message(self, fmt, *args):
            sys.stderr.write("scanner bridge: " + fmt % args + "\n")

    return ThreadingHTTPServer((host or "127.0.0.1", int(port)), Handler)


def main(argv=None, obd_module=None) -> int:
    ap = argparse.ArgumentParser(description="Serve an OBD-II adapter's trouble codes to TorKe (read only).")
    ap.add_argument("--port", required=True, help="the adapter: socket://HOST:PORT, /dev/ttyUSB0, COM3, /dev/rfcomm0")
    ap.add_argument("--listen", default="127.0.0.1:8765", help="address to serve on (default 127.0.0.1:8765)")
    ap.add_argument("--token", default=os.environ.get("TORKE_SCANNER_TOKEN", ""),
                    help="a password TorKe must send (or set TORKE_SCANNER_TOKEN)")
    ap.add_argument("--vin", default="", help="the car's VIN, if you want it included in the reading")
    ap.add_argument("--once", action="store_true", help="read once, print it and exit (tests the adapter)")
    args = ap.parse_args(argv)
    obd = obd_module
    if obd is None:
        try:
            import obd  # type: ignore
        except ImportError:
            print("python-OBD isn't installed. Run: pip install obd", file=sys.stderr)
            return 2
    if args.once:
        try:
            print(json.dumps(take_reading(obd, args.port, args.vin), indent=2))
            return 0
        except Exception as e:
            print(f"Couldn't read the car: {e}", file=sys.stderr)
            return 1
    host = args.listen.rpartition(":")[0]
    if host not in LOOPBACK and not args.token:
        print("Listening beyond this computer needs a password. Add --token (or set TORKE_SCANNER_TOKEN).",
              file=sys.stderr)
        return 2
    server = make_server(args.listen, lambda: take_reading(obd, args.port, args.vin), args.token)
    print(f"Serving trouble codes at http://{args.listen}/codes (read only). Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
