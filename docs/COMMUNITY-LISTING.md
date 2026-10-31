# Text for the Open WebUI community listing

Copy what you need into the community site's form. Nothing here is posted for you.

## Title

TorKe

## One line

Fix it yourself with pubs and videos: a repair coach with project cards, tool and parts lists, and a repair log kept in Homebox.

## Description

TorKe (say "torque") is a repair coach for Open WebUI. Tell it what you're fixing, a 2012 Civic's brakes or a dishwasher that won't drain, and it opens a project card with a picture and buttons for manuals, videos, parts, tools, safety warnings and the repair log.

- **Reads your own manuals first.** PDFs attached to the item in Homebox or in the chat, then the manual sites you choose to turn on. Torque specs, part numbers and other numbers come only from a source it has read, with the source named. If it doesn't have a number, it says so.
- **Knows what you own.** Your tools, the parts you need and your repair log live in Homebox. A missing tool never stops a job: TorKe offers renting, borrowing, a workaround or buying. It never buys anything.
- **Pick a job.** A searchable list of jobs for the thing you own, from common jobs, its manual, iFixit and its repair log.
- **Step by step.** A step card shows a job one step at a time (tap the right side to go forward, the left side to go back) or as a list.
- **Safety first.** Built-in safety reminders for hazards like lifting a car, brakes, gas and mains electricity, and it tells you when a job is for a professional.
- **Looks.** Dark or light, in cyan, green, violet, red or black and white, saved per person.
- **Careful by design.** It never deletes anything, saves nothing without a yes, and most options start off.

## You need

- Open WebUI, and a model that is good at calling tools.
- [Homebox](https://homebox.software), for tools, parts, manuals and the repair log.
- Optional: SearXNG or a YouTube key for real video results, and Home Assistant for the extra whole-house switches.

## Install

1. In Open WebUI, open Workspace > Tools, select +, paste `torke.py`, name it TorKe and save.
2. In Workspace > Models, create a model named TorKe, choose your base model, paste `model/torke-system-prompt.md` as its system prompt (or import `model/torke-model.json`), turn on the TorKe tool and save.
3. In the tool's settings, connect Homebox and turn on "Let TorKe update Homebox".
4. Start a chat with TorKe: "My dishwasher won't drain."

Full guide: https://github.com/Fmielish/TorKe/blob/main/docs/SETUP.md

## Warning

Repairs can injure or kill you, start fires and destroy property. TorKe is an AI hobby tool, it can be wrong, and it is not a mechanic or any other licensed professional. Check every number against the manufacturer's manual for your exact item, and use a professional for brakes, airbags, gas, high voltage and anything you're unsure about. You use TorKe at your own risk. TorKe shows this warning before first use and does nothing until the person accepts it. Read the full text: https://github.com/Fmielish/TorKe/blob/main/DISCLAIMER.md

## Status

A draft. It passes its offline tests but hasn't been tested in a live Open WebUI or against a real Homebox yet, so expect rough edges. Live trouble-code scanning is switched off for now.

## License

PolyForm Noncommercial 1.0.0: free to use, change and share for any noncommercial purpose. Selling it, or using it in a business, isn't allowed. Required Notice: Copyright 2026 Fmielish (https://github.com/Fmielish/TorKe)

## Links

- Source: https://github.com/Fmielish/TorKe
- Changelog: https://github.com/Fmielish/TorKe/blob/main/CHANGELOG.md
- Report a problem: https://github.com/Fmielish/TorKe/issues
