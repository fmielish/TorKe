# New network devices to Homebox (optional add-on)

When a new device joins your network, this saves it in Homebox, looks for its manual, and asks you on your phone before saving the manual. TorKe can then read that manual.

You don't need this to use TorKe. It runs beside it, and nothing in TorKe changes.

> **Draft, not yet tried on real systems.** The logic passes offline tests with stand-ins. It hasn't run in a real n8n, NetAlertX, Homebox or Home Assistant. See [Things to check](#things-to-check).

## What happens

1. **NetAlertX** sees a new device and sends its MAC address, vendor and hostname to **n8n**.
2. n8n skips what isn't worth keeping: randomized MAC addresses (most phones use these), devices already in Homebox, and anything on your ignore list.
3. n8n **adds the device to Homebox**, tagged **Network device**. This happens without asking.
4. n8n searches **SearXNG** for a PDF manual.
5. **Home Assistant** sends your phone a notification:
   - **Save manual:** downloads the PDF and attaches it to the item as a Manual.
   - **Fix model:** type the maker and model. The item is renamed, and the search runs again.
   - **Skip:** nothing more happens. The item stays in Homebox.
   - Tapping the notification opens the link, so you can check it first.

The first search is a **guess**. A MAC address and hostname often don't say which model something is, and the vendor may be the maker of the network chip. Check the manual, or use Fix model.

## What it saves without asking

TorKe saves nothing without a yes. This add-on makes one exception that you choose by turning it on: new devices are added to Homebox right away. A manual is saved only when you tap **Save manual**, and a name changes only when you type one. It never deletes anything.

## What you need

- NetAlertX, n8n (2.0 or later is what this was written for), SearXNG with JSON output on (see the [setup guide](../../docs/SETUP.md#6-searxng))
- Homebox 0.26 or later, with an API key
- Home Assistant with its phone app

## Set it up

1. **n8n:** import [n8n-workflow.json](n8n-workflow.json).
   - Open **Settings** (the code node) and fill in the addresses and the Homebox API key.
   - Open both webhook nodes and replace `CHANGE-ME` in each path with a different long random string. Anyone who knows a path can use it, so treat them like passwords.
2. **Home Assistant:** follow the comments in [home-assistant.yaml](home-assistant.yaml). Use the same long random ID there and in the workflow's Settings.
3. **Turn the workflow on** (publish or activate it). Buttons only work on the live workflow, not in a test run.
4. **NetAlertX:** let its first scan finish **before** this step, so you aren't flooded. Then turn on the **Webhook** plugin and set:

| Setting | Value |
|---|---|
| When to run | on notification |
| Target URL | the **NetAlertX report** webhook's production address |
| Payload type | json |
| Request method | **POST** (the default is GET, which this won't accept) |
| Max payload size | **1000000** (the default, 1024, cuts the report off) |

   In NetAlertX's notification settings, make sure **new devices** is one of the included sections.

## Settings

| Setting | What it does |
|---|---|
| `tag` | The Homebox tag on devices this adds |
| `location` | Where they go; blank uses the first location |
| `maxNewPerRun` | Most devices added from one report (10). Any more are named in a notification and not added |
| `maxPdfMB` | Largest manual to save (10). Keep it at or under Homebox's upload limit |
| `ignoreMacs` | MAC addresses, or their first part, to leave out |
| `skipSites` | More websites never to download from |

## Safety limits

- Only a direct PDF link is offered. ManualsLib, RepairClinic and the gray-area manual sites are never downloaded from.
- A device chooses its own hostname, and search results come from strangers. Both are cleaned before use. **Open the link and check it before saving.**
- Links and redirects to number addresses and local names are refused. The add-on can't look up where a domain name points, so a public-looking name that points inside your network isn't caught.
- Manual sites have their own terms and copyrights. Save only what you're allowed to keep.
- Your Homebox API key sits in the workflow. Remove it before sharing an export.

## Things to check

These couldn't be tried here:

- The workflow imports, and each node's settings show as expected.
- Code nodes can make web requests, read the downloaded file and remember offers between runs on your n8n version.
- Homebox accepts the new item, the tag filter (including archived items), the rename keeps the item's other details, and the upload shows as a Manual.
- The download node doesn't follow redirects, and the upload sends the file intact.
- The notification shows three buttons, **Fix model** opens a text box, and the reply reaches n8n.
- A report from your NetAlertX version has the fields `eveMac`, `devVendor` and `devName`.

If **Save manual** says "That notification is old" every time, the workflow isn't remembering offers: check that it's published and you're using the production webhook addresses.
