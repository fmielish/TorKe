# Changelog

TorKe is a draft. It passes its offline tests but hasn't been tested in a live Open WebUI, a real Homebox, a real Home Assistant or a real scanner yet. See the end of the [setup guide](docs/SETUP.md#things-to-verify-on-your-setup).

## 0.9.0 (draft, 2026-11-02)

- **Keep copies in Homebox** (new switch, off by default). Pictures and manuals are downloaded once, attached to the item in Homebox, and read from there afterwards:
  - the picture of the thing being fixed (the project card shows the kept one, and doesn't search again),
  - iFixit guides, kept with their license and link,
  - pages and PDFs TorKe reads from the readable manual sites that are on (Operation CHARM, LEMON Manuals and custom sites).
  Kept guides and pages can be searched with the item's manual. Links-only sites (ManualsLib, RepairClinic, carmaker manuals) are never downloaded or copied. A photo already attached to the item in Homebox is shown too, the person's own first. A photo attached in the chat is shown but never saved. TorKe only adds files; it never changes or deletes anything else. Needs Let TorKe update Homebox, and an item whose name has every word of what you called it, so a copy never lands on the wrong year or model.

## 0.8.0 (draft, 2026-10-30)

- **Step card.** When asked to walk through a job, TorKe can show the steps it read from a manual or guide as a card: one step at a time (tap the right side to go forward, the left side to go back) or a full list you can tick off. Torque values not confirmed from a manual are marked, and the card names its source. It doesn't remember which step you're on.
- **Warning gate.** Before first use, each person reads a warning and accepts it. No tool does anything until they do. They can turn it off only after a second, stronger warning. Added [DISCLAIMER.md](DISCLAIMER.md) and a boxed warning at the top of the README.
- **4x4 jobs** in the common jobs list (CV joint boot, axle shafts, U-joint, 4x4 hub or integrated wheel end, differential and transfer case fluid), and the lifting warning now covers hub, axle and driveline jobs.
- **Black and white look**, a fifth color for the theme button. Warnings stay amber.
- **Live scanner reading is switched off ("coming soon")** until an adapter has been tried. Typed-in trouble codes still work.

## 0.7.0 (draft, 2026-10-30)

- **Pick a job** card: a searchable list of jobs grouped by system, from common jobs, the item's manual, iFixit guides (if on) and its repair log.
- **Trouble codes:** a read-only scanner feed and a small bridge program for OBD-II adapters, and a reader for typed-in codes. TorKe never guesses what a code means and never clears codes.

## 0.6.0 (draft, 2026-10-30)

- **Theme button** on every card: dark or light, in cyan, green, violet or red, saved per person.

## 0.5.0 (draft, 2026-10-30)

- **Whole-house switches**, all off by default: scheduled upkeep, critical spares, VIN decoding and complaints, saving facts and invoices on owned items, shop work and warranty tracking, hand-offs to an outside assistant, and room messages through Home Assistant. See [HOUSE-SETUP.md](docs/HOUSE-SETUP.md).

## 0.4.0 and the changes after it (draft, 2026-10-29)

- Everything lives in Homebox: tools, parts, manuals and the repair log.
- Rentals: Got it at pickup, return after the job.
- **Job done:** close out a job in one press, with mileage and notes boxes and pop-up keypads for touchscreens.
- Every shopping link says Buy.

## 0.3.0 (draft, 2026-10-29)

- Parts list and shopping list.

## 0.2.0 (draft, 2026-10-29)

- Tool lists, Homebox, and reading manuals for the tools a job needs.

## 0.1.0 (draft, 2026-10-28)

- The first draft: a project card with six buttons, built as an Open WebUI tool.
