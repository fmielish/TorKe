<p align="center"><img src="assets/torke-icon.png" width="96" alt="TorKe icon"></p>

# TorKe

Fix it yourself with pubs and videos.

TorKe (say "torque") is a repair coach for [Open WebUI](https://openwebui.com). Tell it what you're fixing and it opens a project card in the chat: a picture of the thing on the right, and six buttons on the left. It helps with vehicles, appliances, tools, electronics, yard equipment and the house.

<p align="center">
  <img src="docs/card-photo.png" width="640" alt="Project card for a Bosch dishwasher that won't drain, with six buttons on the left and the user's photo in a circular frame on the right">
</p>
<p align="center">
  <img src="docs/card-vehicle-phone.png" width="260" alt="The same card on a phone, for a 2012 Honda Civic brake job, with a safety warning strip">
</p>

## What the buttons do

| Button | What it does | Out of the box |
|---|---|---|
| **Manuals** | Finds manuals and repair guides on the sites you turn on | A web search link |
| **Videos** | Shows YouTube how-to videos as cards you can tap | A YouTube search link. Real results with SearXNG or a YouTube API key |
| **Parts** | Finds where to buy each part, matched to your model | Search links. Optional parts list in Home Assistant |
| **Tools you'll need** | Compares the job's tools with what you own | Assumes a basic 100-piece tool kit, a 100-piece socket set and a multimeter |
| **Safety warnings** | Built-in rules for hazards like lifting a car, brakes, airbags, fuel, house wiring, gas and refrigerant, plus optional US recall checks | Built-in rules |
| **Repair log** | Keeps each person's finished jobs on your server | Off |

Most options start **off**. Each one is a switch in the tool's settings, so you choose what TorKe can reach.

## Install

1. In Open WebUI, open **Workspace > Tools**, select **+**, paste [`torke.py`](torke.py), name it **TorKe** (tool ID `torke`) and save.
2. In **Workspace > Models**, create a model named **TorKe**: choose a base model that's good at tool calling, paste [`model/torke-system-prompt.md`](model/torke-system-prompt.md) as its system prompt, turn on the TorKe tool and save. You can also import [`model/torke-model.json`](model/torke-model.json) and then choose the base model.
3. Start a chat with TorKe: "My dishwasher won't drain."

The [setup guide](docs/SETUP.md) covers every setting, SearXNG, YouTube, Homebox and Home Assistant.

## Your tools

Each person sets their own tools under **Chat Controls > Valves > TorKe**. The starting point is a basic 100-piece home tool kit, a 100-piece socket set and a multimeter. Switch off what you don't have and add what you do, such as "torque wrench, jack stands, OBD2 scanner". TorKe never assumes a torque wrench, jack stands or specialty tools; it asks.

## Manual sites

All off by default:

- **iFixit:** read through its official API, with credit and links.
- **ManualsLib and RepairClinic:** links only, because their terms ban or don't clearly allow automated reading.
- **Carmaker owner's manuals:** links only.
- **Operation CHARM and LEMON Manuals:** factory car manuals, in a **legal gray area**.
- **Your own sites.**

[MANUAL-SITES.md](docs/MANUAL-SITES.md) explains each one.

## Privacy

- **No outside fonts, scripts or tracking.** Cards are self-contained.
- **Pictures, when turned on,** load from the site they came from, so that site sees the request.
- **Searches** go through your own SearXNG if you set one. Otherwise TorKe gives you links to open yourself.
- **The repair log** stays on your Open WebUI server.

## Safety

TorKe points you to the manual and tells you when a job is for a professional, but you're responsible for your own work. It never guesses torque specs or other critical numbers, and it treats text from websites as information, never as instructions. The software comes with no warranty (see the license).

## Status

Version 0.1.0 is a first draft. It passes its offline tests but hasn't been tested in a live Open WebUI yet. The parts to check first are listed at the end of the [setup guide](docs/SETUP.md#things-to-verify-on-your-setup).

## For developers

- `python -m pytest -q` runs the offline tests. They need `pydantic` and `pytest`.
- `python scripts/render_preview.py` redraws the preview images. It needs `playwright` and `pillow`.

## License

[PolyForm Noncommercial 1.0.0](LICENSE.md). You can use, change and share TorKe for free for any noncommercial purpose. Selling it, or using it in a business, is not allowed.

Required Notice: Copyright 2026 Fmielish (https://github.com/Fmielish/TorKe)
