# Running TorKe the way the house does

TorKe works on its own for anyone: Open WebUI plus Homebox, with everything else off. This guide is for people who want the **whole-house setup**: TorKe keeping up with scheduled upkeep, recalls, receipts and shop work, and talking to the screens around the home.

Nothing here is on by default. Each house feature is a switch in TorKe's settings. Leave a switch off and TorKe behaves exactly as the main [setup guide](SETUP.md) describes.

> **Status:** this is the plan. The switches below are **not built yet**; the code on the `draft` branch has none of them. Each row says what it will do so the code and this guide stay in step.

## What you need to run

| App | Needed for | Required? |
|---|---|---|
| **Open WebUI** | TorKe itself | Always |
| **Homebox** | Tools, parts, manuals, repair log, saved facts, attached invoices | Always, for anything TorKe keeps |
| **Home Assistant** | Room screens, voice, scheduled upkeep reminders | For the house switches that talk to the home |
| **Cybertron and Signal** | Hand-offs: weekly what's due, monthly recall check, receipts, the device list, shop invoice photos | Only for the Cybertron switches |
| SearXNG | Pictures and real search results | Optional (see SETUP.md) |

If you run these as containers, each needs to be reachable from Open WebUI's container by address (for example `http://homebox:7745`). Test that from inside the Open WebUI container before blaming TorKe.

## Keeping things in Homebox

The house uses the same Homebox layout as everyone else: **To get**, **Rent** and the **Parts shelf**. The Home Assistant parts list is no longer the house's list. It stays available as the optional copy described in section 8 of SETUP.md.

## The house switches

All off by default. "Public" means what someone who never touches the switch gets.

| Switch | What it does when on | Needs |
|---|---|---|
| **Cybertron hand-offs** | Lets Cybertron ask TorKe for the weekly what's due and the monthly recall check, and hand over receipts, the device list and shop invoices | Cybertron, Signal |
| **Scheduled upkeep** | Keeps upkeep schedules and "next oil change at" targets on each item and tells you when something is due | Homebox |
| **Save facts on owned items** | Saves facts about an item you own (model, part numbers, capacities) onto the item in Homebox, and attaches invoices | Homebox, and permission to add attachments beyond Tools and Parts |
| **Critical spares and consumables** | Tracks the spares and consumables you never want to run out of, and flags them when low | Homebox |
| **Voice to the nearest room screen** | Speaks answers, and shows the project card, on the screen nearest you | Home Assistant |
| **VIN decoding and NHTSA complaints** | Decodes a vehicle's VIN and adds NHTSA complaint data to its safety warnings | Nothing beyond internet access |
| **Shop work** | Turns a photo of a shop invoice into a repair record: oil changes, tires, glass and any other automotive work. Tracks the warranty on the work and the cost history per vehicle, and attaches the invoice to the vehicle | Homebox, Cybertron, Signal |

### About shop work

Today neither TorKe nor the old house Fix-it records shop work, and Cybertron's photo triage would file a shop invoice as a purchase receipt. When this is built, Cybertron needs to send invoices to TorKe instead. The photo arrives on Signal, so that route needs Cybertron and Signal running.

Attaching the invoice means TorKe may add an attachment to a vehicle, which goes beyond its usual rule of changing only items tagged **Tools** or **Parts**. That permission will be its own switch, and TorKe will still never delete anything.

## Turning on the house setup, in plain steps

1. Finish the main [setup guide](SETUP.md) first, including Homebox and **Let TorKe update Homebox**.
2. Make sure Home Assistant is running and Open WebUI can reach it.
3. Turn on only the house switches you want, one at a time, and try each before the next.
4. For the Cybertron switches, confirm Cybertron and Signal are running and Cybertron can reach Open WebUI.

## Retiring the old house Fix-it

Fix-it stays until TorKe has passed its live test (the checklist at the end of SETUP.md). After that the house moves to TorKe and Fix-it is retired.
