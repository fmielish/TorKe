# Reading trouble codes from the car

TorKe can read the trouble codes your car has stored (the ones behind the check engine light, like `P0301`) and help you work out what to do about them. It only **reads**. It can't clear codes or send anything to the car, and there's no setting that changes that.

**Live scanning is switched off for now ("coming soon").** The settings are there but greyed out in name and do nothing, because no adapter has been tried yet. Typing codes into the chat works today. When an adapter is on hand, flipping `SCANNER_FEED_READY` in `torke.py` to `True` turns live reading on.

Version 0.7.0 builds this and passes its offline tests against a stand-in for the adapter library. It hasn't been tried with a real adapter or car yet; the list at the end says what to check first.

## How it fits together

An OBD-II adapter plugs into the car's diagnostic port (under the dashboard on most cars). Open WebUI runs on a server, so it can't talk to the adapter directly. A small program, the **bridge**, does that job: it runs on a computer near the car, reads the adapter, and offers the codes at a web address. TorKe reads that address when you ask.

```
car  ->  adapter  ->  bridge (a small program)  ->  TorKe's "Scanner feed"
```

## What you need

- **An OBD-II adapter** that the bridge can reach (below).
- **A computer for the bridge** with Python, in or near the car and on the same network as Open WebUI. A Raspberry Pi works.
- **Open WebUI and TorKe**, set up as in the [setup guide](SETUP.md). Homebox is optional here: with it, TorKe can also check a VIN against the one saved on your vehicle and look at the repair log for the same code.

## Which adapters work

The bridge uses the [python-OBD](https://github.com/brendanwhitfield/python-OBD) library, so it reaches:

| Adapter | Works with the bridge? |
|---|---|
| **Wi-Fi** | Yes. Use the adapter's address, often something like `socket://192.168.0.10:35000` (check its instructions). |
| **USB or serial cable** | Yes. For example `/dev/ttyUSB0` or `COM3`. |
| **Classic Bluetooth** | Yes, on Linux. Pair it, bind it to a serial port (`rfcomm`), and use that port, such as `/dev/rfcomm0`. Your system's Bluetooth documentation has the steps. |
| **Bluetooth Low Energy (LE)** | **No.** The bridge can't reach these. |

Two cautions from [Car Scanner's guide to choosing an adapter](https://www.carscanner.info/?p=40):
- Bad clones are common and can fail to connect, freeze, or return wrong data. Very cheap adapters and unknown brands are the usual culprits. Buy a reputable make.
- iPhones can't use classic Bluetooth adapters. That only matters for phone apps, not for this bridge.

I couldn't confirm which specific models are Wi-Fi, classic Bluetooth or LE, so check a model's type before buying it for the bridge.

**Bluetooth LE adapters.** Browsers can only reach Bluetooth LE devices on secure pages, and TorKe's cards sit in a locked-down frame inside Open WebUI, so TorKe can't pair with an adapter itself either way. The Home Assistant community has [an ESPHome component for BLE ELM327 adapters](https://community.home-assistant.io/t/custom-esphome-component-for-ble-elm327-obd2/1011293). I couldn't confirm that it, or the [elm327-obdii library](https://pypi.org/project/elm327-obdii/0.0.3/) behind Home Assistant's BLE integration, reads trouble codes rather than live sensor values. If you build a bridge of your own, the feed format below is all TorKe needs.

## Run the bridge

On the computer near the car:

```
pip install obd
python scripts/scanner_bridge.py --port socket://192.168.0.10:35000 --listen 0.0.0.0:8765 --token CHOOSE-A-PASSWORD
```

- `--port` is the adapter (see the table).
- `--listen` is where TorKe will reach the bridge. The bridge refuses to listen beyond its own computer unless you also set a `--token`, which is a password TorKe must send.
- `--vin` (optional) adds the car's VIN to each reading, so TorKe can check it's the right car.
- **Test the adapter first:** add `--once` to read once, print the codes and exit. Turn the ignition on (engine off is fine for most cars) before you try.

The bridge keeps the last reading for 10 seconds, so refreshing doesn't hammer the car.

## Turn it on in TorKe

In TorKe's settings (**Workspace > Tools > TorKe > gear**), an admin turns on **Scanner feed**, fills in **Scanner feed address** (`http://<the bridge computer>:8765/codes`) and **Scanner feed password** (the same `--token`). Open WebUI's server must be able to reach that address.

## What TorKe does with the codes

Ask something like "Read the codes on my Civic." For each code, TorKe shows its status (stored, pending or permanent when the scanner says), the scanner's own description if it sent one, and what the code's shape tells you: which system it belongs to, and whether it's a generic code (the same on every make) or manufacturer-specific.

What TorKe won't do:
- **Guess what a code means.** A code points at a system or circuit; it doesn't say which part failed. TorKe gets the meaning for your make and engine from your manual or a guide, says where it came from, and checks your repair log for the same code first.
- **Tell you to clear the codes first.** Clearing them erases the evidence and resets the car's emissions readiness checks.
- **Clear anything itself.** The bridge has no code path for it.

Airbag and other safety-system codes are sent to a pro, as with TorKe's other safety rules.

If you'd rather not run a bridge, you can type codes into the chat and TorKe works with them the same way, without the scanner's description or freeze frame.

## The feed format, for other tools

The bridge serves JSON like this. Any tool that serves the same shape works with TorKe.

```json
{
  "time": "2026-10-30T12:40:00+00:00",
  "vin": "1HGCM82633A004352",
  "codes": [
    {"code": "P0301", "status": "stored", "description": "Cylinder 1 Misfire Detected"},
    {"code": "P0420", "status": "pending"}
  ],
  "freeze_frame": {"Engine speed": "2150 rpm"}
}
```

- Only `codes` is needed. Each can be a plain string like `"P0301"`. Status is `stored`, `pending` or `permanent`; anything else shows as "reported".
- A password is sent as `Authorization: Bearer <password>`. On a failure, answer with an HTTP error and `{"error": "what went wrong"}` and TorKe will show that message.
- TorKe reads up to 30 codes, ignores anything that isn't a valid code, and warns when a reading is more than an hour old.

## Check these on your setup

They're marked as untested because no real adapter or car was available.

- **The bridge with your adapter:** run it with `--once` and compare the codes with what a trusted scanner app shows.
- **Pending codes:** that your car answers the pending-codes request (not all do).
- **TorKe reaching the bridge:** the address, the password, and that Open WebUI's server (not just your laptop) can reach the bridge's computer.
- **A car with no codes,** which should come back as "none are stored", not as an error.
