# Setting up TorKe

TorKe brings each job's manuals and repair documents together with the tools and parts it needs. It's one Python file that runs inside Open WebUI. Everything it keeps lives in **Homebox**: your tools, tools to get, parts, the manuals attached to your things, and each item's repair log.

## 1. What you need

- **Open WebUI**, a recent version that shows tool cards in the chat (Rich UI embeds).
- **Homebox.** Required for tools, parts and the repair log. Without it, TorKe still helps with a job (manual sites, videos, safety warnings) but can't keep anything.
- **A model that's good at tool calling.** It needs to choose and call TorKe's functions reliably. A model with vision can also look at photos the user attaches.
- **Optional:** SearXNG for pictures and real search results, a YouTube API key, and Home Assistant for copies of the lists.
- **Running a whole-house setup** (scheduled upkeep, recalls, receipts, shop work, room screens)? See [HOUSE-SETUP.md](HOUSE-SETUP.md) for the extra switches and the apps they need.

## 2. Install the tool

1. Open **Workspace > Tools** and select **+**.
2. Paste the whole of [`torke.py`](../torke.py).
3. Name it **TorKe** and set the tool ID to **torke**. The model file below expects that ID.
4. Save.

## 3. Create the TorKe model

**By hand (recommended):**

1. Open **Workspace > Models** and select **+**.
2. Name it **TorKe** and choose your base model.
3. Paste [`model/torke-system-prompt.md`](../model/torke-system-prompt.md) into the system prompt.
4. Under **Tools**, turn on **TorKe**.
5. Optional: upload [`assets/torke-icon.png`](../assets/torke-icon.png) as its picture.
6. Save.

**Or import it:** in **Workspace > Models**, import [`model/torke-model.json`](../model/torke-model.json). Then open the model, choose a base model and save. The file can't know which models you have, so it leaves the base model empty.

## 4. Connect Homebox

In TorKe's settings (**Workspace > Tools > TorKe > gear**):

1. **Turn on Homebox** and fill in its address, such as `http://homebox:7745`.
2. **Sign in:** on Homebox 0.26 or later, create an API key under your Homebox profile and paste it into **Homebox API key**. On older versions, fill in a user and password instead. TorKe sees only what that account can see.
3. **Let TorKe update Homebox:** turn this on so TorKe can save tools and parts and write the repair log. With it off, TorKe only reads Homebox.

**What TorKe can change.** It adds new items, changes only items tagged **Tools** or **Parts**, and adds repair log entries to the item being fixed. It never deletes anything; things it takes off a list are archived, so you can restore them in Homebox. And it saves nothing until the person says yes.

### How TorKe lays things out in Homebox

| What | In Homebox |
|---|---|
| Manuals | Attached to the item, attachment type **Manual** |
| Tools you own | Items tagged **Tools** |
| Tools to get | Tagged **Tools** and **To get**, quantity 0. Also **Rent** when you'll rent or borrow it |
| Rented or borrowed, in hand | Tagged **Tools** and **Rent**, until it goes back after the job; then archived |
| Parts to get | Tagged **Parts** and **To get**, quantity 0, in the **Parts shelf** location, with Part number, Buy link, Price and Store fields |
| Parts waiting to go in | Tagged **Parts**, on the **Parts shelf** |
| Installed parts | Archived. Your parts history stays in Homebox |
| Repair log | The item's own maintenance log |

Each tool or part to get has "For" in its description, such as "For 2012 Honda Civic: front brakes", so TorKe can show what belongs to which job. The tag and location names can be changed in TorKe's settings.

### How a job flows

- **Tools:** the Tools card shows what you have and what's missing. A missing tool never stops the job: TorKe offers to rent or borrow it, a workaround with tools you have, or buying it. Missing tools go on your tools to get. A bought tool moves over to your tools. A rental counts as yours from pickup (Got it) until the job's done; then TorKe asks whether it's gone back and archives it.
- **Parts:** parts you still need go on your parts to get. When they arrive, they move to the Parts shelf. Once installed (old ones tossed), they're archived and the job goes in the item's repair log with the part numbers.
- **Shopping:** "What do I need to buy?" shows tools to get and parts to get side by side. **Buy** opens the store page TorKe saved, or a web search when there isn't one; rentals get **Find a rental**. The two lists stay separate.
- **Job done:** the project card's **Job done** button shows what to close out: installed parts to archive, rented or borrowed tools to return, and anything left on the lists for that job. It has boxes for **Mileage** (vehicles; "Mileage or hours" for yard equipment and other machines; none for appliances) and **Notes**. One tap on **Finish job** does it all and writes the repair log with the date, mileage, notes and part numbers. Homebox's maintenance log has no mileage field, so the mileage goes at the top of the entry's description. On a touchscreen, tapping either box pops up a bigger one. Phones and tablets use their own keyboard (the number pad for mileage). Other touchscreens, such as a garage or wall screen running a desktop browser, get a number pad and a typing pad built into the card, since many have no keyboard of their own. TorKe guesses which from the browser; if it guesses wrong, the pop-up's **Use device keyboard** / **Show on-screen keys** button switches.

**Manuals:** attach the PDF to the item in Homebox with the attachment type **Manual**. TorKe matches items by name, so name them the way people say them, such as "Bosch dishwasher SHE3AR75UC". TorKe reads text from PDFs; a manual that's only scanned pictures has no text, and TorKe says so.

Homebox 0.26 (June 2026) replaced its "items" API with a new "entities" API. TorKe works with both. Try each step once after setup (see the end of this guide).

## 5. Settings

### Admin settings

Every switch starts off.

| Setting | What it does | Needs |
|---|---|---|
| Homebox | Where TorKe keeps tools, parts, manuals and the repair log | Address and an API key or login (section 4) |
| Let TorKe update Homebox | Saving tools and parts, archiving, and the repair log | Homebox |
| Tools, Parts, To get and Rent tags; Tools location; Parts shelf location | The names TorKe uses in Homebox | Homebox |
| SearXNG address | Real search results for pictures, videos, manuals and parts. Without it, TorKe gives plain search links. | SearXNG with JSON output (section 6) |
| Pictures | A photo of the thing on the project card, loaded from the original site with a link to it. A photo the user attaches always shows. | SearXNG |
| YouTube API key | Video results when there's no SearXNG | A key from Google Cloud (section 7) |
| iFixit, ManualsLib, RepairClinic, Carmaker owner's manuals | Manual sites. See [MANUAL-SITES.md](MANUAL-SITES.md) for how each is used. | Nothing |
| Operation CHARM, LEMON Manuals | Factory car manuals. **Legal gray area**, so read the warning first. | Nothing |
| Custom manual sites | Other sites TorKe may search and read | Only sites whose terms allow it |
| Recall checks | US recalls (NHTSA and CPSC) in Safety warnings | Nothing |
| Scanner feed, address and password (coming soon, do nothing yet) | Will read trouble codes from an OBD-II scanner bridge. Read only. | A bridge and an adapter ([SCANNER.md](SCANNER.md)) |
| Parts in Home Assistant, Tools to get in Home Assistant | Copies of the lists on Home Assistant to-do lists | Webhooks (section 8) |
| Scheduled upkeep, Critical spares and consumables, VIN decoding and complaints, Save facts on owned items, Shop work, Hand-offs to an outside assistant, Voice and room screens | The whole-house switches. Each is off until you turn it on. | See [HOUSE-SETUP.md](HOUSE-SETUP.md) |
| YouTube playlist | Each person can add videos to their own playlist | Each person's Google sign-in (section 7) |
| Most results | Results per search, 3 to 10 | |

### Each person's settings

Each person opens **Chat Controls > Valves > TorKe** in a chat. Non-admin users need the **Allow Chat Valves** permission. They're saved with the person's Open WebUI account.

- **Starter kit:** TorKe assumes a basic 100-piece home tool kit, a 100-piece socket set and a basic multimeter. Each can be switched off. Everything else they own goes in Homebox: they can tell TorKe ("I bought a 3/8 torque wrench"), send a photo of a tool, a kit's contents list or a receipt, or tap **I have it** on the Tools card.
- **YouTube sign-in,** for the playlist option (section 7).

## 6. SearXNG

TorKe calls SearXNG's JSON API, which is off by default. In SearXNG's `settings.yml`:

```yaml
search:
  formats:
    - html
    - json
```

Restart SearXNG, then put its address in TorKe's settings, such as `http://searxng:8080`. Pictures use the **images** category, and videos use the **youtube** engine, so keep both enabled.

## 7. YouTube

**Video results without SearXNG:** create a project in Google Cloud, enable **YouTube Data API v3**, create an API key, and paste it into TorKe's settings. Each search uses 100 of the 10,000 free daily units, so about 100 searches a day.

**Adding videos to a playlist.** Each person uses their own Google account, and nothing is downloaded.

1. In Google Cloud, create a project and enable **YouTube Data API v3**.
2. Set up the **OAuth consent screen** and add yourself as a test user.
3. Create an **OAuth client ID** of type **Web application**, with this authorized redirect URI: `https://developers.google.com/oauthplayground`
4. Open the [OAuth 2.0 Playground](https://developers.google.com/oauthplayground). Select the gear, check **Use your own OAuth credentials**, and enter your client ID and secret.
5. In step 1, enter the scope `https://www.googleapis.com/auth/youtube` and authorize with the account that owns the playlist.
6. In step 2, exchange the code for tokens and copy the **refresh token**.
7. In Open WebUI, go to **Chat Controls > Valves > TorKe** and fill in the client ID, client secret, refresh token and playlist ID. The playlist ID is the part after `list=` in the playlist's link.
8. An admin turns on **YouTube playlist** in TorKe's settings.

**The 7-day catch:** while the Google project is in **Testing**, the refresh token expires after 7 days. Publish the app (**In production**) to stop that. For your own account that's one button, though Google may show an "unverified app" warning when you sign in. Google changes these screens from time to time, so follow its current wording.

## 8. Copies in Home Assistant (optional)

Homebox is always the list. If you also want tools and parts to get on Home Assistant to-do lists, add two automations, each with its own long, random webhook ID. Treat the IDs like passwords.

Parts, onto `todo.parts`:

```yaml
alias: TorKe parts to get
triggers:
  - trigger: webhook
    webhook_id: "torke-parts-change-this-to-a-long-random-id"
    allowed_methods: [POST]
    local_only: true
actions:
  - repeat:
      for_each: "{{ trigger.json.parts }}"
      sequence:
        - action: todo.add_item
          target:
            entity_id: todo.parts
          data:
            item: "{{ repeat.item.name }}"
            description: "{{ trigger.json.item }} {{ repeat.item.store }} {{ repeat.item.price }} {{ repeat.item.link }}"
```

Tools, onto `todo.tools_to_get`:

```yaml
alias: TorKe tools to get
triggers:
  - trigger: webhook
    webhook_id: "torke-tools-change-this-to-a-long-random-id"
    allowed_methods: [POST]
    local_only: true
actions:
  - repeat:
      for_each: "{{ trigger.json.tools }}"
      sequence:
        - action: todo.add_item
          target:
            entity_id: todo.tools_to_get
          data:
            item: "{{ repeat.item }}{{ ' (rent or borrow)' if trigger.json.rent else '' }}"
            description: "{{ trigger.json.item }} {{ trigger.json.job }}"
```

Put the addresses (`http://<home-assistant>:8123/api/webhook/<id>`) in **Parts webhook address** and **Tools webhook address**, then turn on the matching switches. Ticking an item off in Home Assistant doesn't change Homebox; use the buttons on TorKe's cards or tell TorKe.

## 9. What TorKe keeps outside Homebox

- **Each person's settings** (starter kit switches, YouTube sign-in), saved with their Open WebUI account.
- **Each person's saved look** (dark or light, and the color), in `<DATA_DIR>/torke/theme-<user id>.json`. Without one, cards open dark and cyan.
- **The open project in each chat,** in `<DATA_DIR>/torke/projects-<user id>.json` on the Open WebUI server, so a restart doesn't forget what you were working on. In the Docker image that's under `/app/backend/data`.

## 10. The buttons and the confirmation prompt

The buttons on TorKe's cards send a message to the chat. Open WebUI shows these cards in a locked-down frame, so it asks you to confirm before a button sends anything. That's the safe default.

The theme button works differently: choosing a look changes the card right away, inside the card. **Save as my look** is the one part that sends a message ("Save my TorKe theme: light, green"), because the card frame can't store anything itself; TorKe then saves it with the person's account. People can also just ask TorKe for a look.

To skip the confirmation, an admin can turn on **Settings > Interface > iframe Sandbox Allow Same Origin**. That gives every card in Open WebUI, from any tool, access to the page it's on, so leave it off unless you trust all your tools.

## 11. Troubleshooting

- **"Homebox isn't set up":** turn on Homebox and fill in its address and sign-in (section 4).
- **"TorKe can only read Homebox":** turn on **Let TorKe update Homebox**.
- **"Couldn't find" an item in Homebox:** check that its name contains the words people use for it, and that TorKe's Homebox account can see it.
- **The model doesn't use the buttons or tools:** check that the TorKe tool is turned on for the model, and try a base model that's stronger at tool calling.
- **No pictures:** turn on **Pictures**, set the SearXNG address, and check that JSON output is on (section 6). Some sites block their images from showing elsewhere; TorKe then shows the placeholder.
- **"Search failed" errors:** Open WebUI's server can't reach SearXNG or the site. Check the address from inside the Open WebUI container.
- **YouTube sign-in failed:** the refresh token expired or was revoked. If the Google project is in Testing, see the 7-day catch in section 7.
- **A manual won't read:** it may be scanned pictures with no text, or over 60 MB. Open WebUI includes the PDF reader TorKe uses (pypdf); if it's missing, install it in Open WebUI's environment.

## Things to verify on your setup

TorKe 0.7.0 passed its offline tests, including against a stand-in Homebox for both the old and new APIs, but hasn't yet been tested in a live Open WebUI or against a real Homebox. Try these once. They're marked `VERIFY` in the code.

- **Homebox updates:** that changing an item (moving a tool to "owned", putting a part on the shelf, archiving) keeps its other details. TorKe sends back everything it read, but Homebox's notes don't spell out how its update works.
- **Homebox sign-in:** that an API key works as a bearer token.
- **Manual downloads** on Homebox versions before 0.26.
- **Attached photos:** that a photo attached in the chat shows on the project card.
- **Buttons:** the confirmation behavior of card buttons.
- **Job done boxes:** that you can type in the Mileage and Notes boxes inside Open WebUI's card frame, that what you typed shows in the Finish job message, and that the keyboard guess is right on your phone and on any garage or wall screen.
- **Pick a job:** that the list opens from the project card's button, that tapping a group opens it and the search filters it inside Open WebUI's frame, and that picking a job starts a project. Jobs from a manual need a manual whose contents page lists jobs with page numbers; many don't, and then only the common jobs show.
- **Scanner:** see the list at the end of [SCANNER.md](SCANNER.md).
- **Theme button:** that the theme popup opens and changes the card inside Open WebUI's frame, that **Save as my look** sends its message, and that the saved look shows on the next card.
- **iFixit:** the search endpoint and guide field names.
- **Model file:** importing `torke-model.json`.
- **Recall checks:** the CPSC manufacturer filter.
