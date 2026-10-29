# Setting up TorKe

TorKe is one Python file that runs inside Open WebUI. It doesn't need its own container or server.

## What you need

- **Open WebUI**, a recent version that shows tool cards in the chat (Rich UI embeds).
- **A model that's good at tool calling.** It needs to choose and call TorKe's functions reliably. A model with vision can also look at photos the user attaches.
- **Optional:** SearXNG for pictures and real search results, a YouTube API key, Homebox and Home Assistant.

## 1. Install the tool

1. Open **Workspace > Tools** and select **+**.
2. Paste the whole of [`torke.py`](../torke.py).
3. Name it **TorKe** and set the tool ID to **torke**. The model file below expects that ID.
4. Save.

## 2. Create the TorKe model

**By hand (recommended):**

1. Open **Workspace > Models** and select **+**.
2. Name it **TorKe** and choose your base model.
3. Paste [`model/torke-system-prompt.md`](../model/torke-system-prompt.md) into the system prompt.
4. Under **Tools**, turn on **TorKe**.
5. Optional: upload [`assets/torke-icon.png`](../assets/torke-icon.png) as its picture.
6. Save.

**Or import it:** in **Workspace > Models**, import [`model/torke-model.json`](../model/torke-model.json). Then open the model, choose a base model and save. The file can't know which models you have, so it leaves the base model empty.

Start a chat with TorKe and try "My dishwasher won't drain."

## 3. Settings

### Admin settings

Open **Workspace > Tools > TorKe > gear**. Every switch starts off.

| Setting | What it does | Needs |
|---|---|---|
| SearXNG address | Real search results for pictures, videos, manuals and parts. Without it, TorKe gives plain search links. | SearXNG with JSON output (section 4) |
| Pictures | A photo of the thing on the project card, loaded from the original site with a link to it. A photo the user attaches always shows, even with this off. | SearXNG |
| YouTube API key | Video results when there's no SearXNG | A key from Google Cloud (section 5) |
| iFixit, ManualsLib, RepairClinic, Carmaker owner's manuals | Manual sites. See [MANUAL-SITES.md](MANUAL-SITES.md) for how each is used. | Nothing |
| Operation CHARM, LEMON Manuals | Factory car manuals. **Legal gray area**, so read the warning first. | Nothing |
| Custom manual sites | Other sites TorKe may search and read | Only sites whose terms allow it |
| Recall checks | US recalls (NHTSA and CPSC) in Safety warnings | Nothing |
| Repair log | Each person's finished jobs, saved on the server | Nothing (section 9) |
| Homebox | Homebox becomes the list of tools people own, and TorKe reads manuals attached to items | Homebox address and an API key or login (section 6) |
| Let TorKe add new tools to Homebox | Saves tools people tell TorKe about into Homebox, after they confirm. Never changes or deletes existing items. | Homebox |
| Parts in Home Assistant | Also sends parts to Home Assistant, for example a to-do list. TorKe always keeps its own parts list. | A Home Assistant webhook (section 7) |
| Needed tools in Home Assistant | Sends needed tools to their own Home Assistant list, separate from parts | A second webhook (section 8) |
| YouTube playlist | Each person can add videos to their own playlist | Each person's Google sign-in (section 5) |
| Most results | Results per search, 3 to 10 | |

### Each person's settings

Each person opens **Chat Controls > Valves > TorKe** in a chat. Non-admin users need the **Allow Chat Valves** permission.

- **Tools they own.** TorKe assumes a basic 100-piece home tool kit, a 100-piece socket set and a basic multimeter. Each can be switched off. Other tools can be typed in **Other tools I own**, but it's easier to just tell TorKe in a chat (see "Tools you own and tools you need" below).
- **YouTube sign-in,** for the playlist option (section 5).

## 4. SearXNG

TorKe calls SearXNG's JSON API, which is off by default. In SearXNG's `settings.yml`:

```yaml
search:
  formats:
    - html
    - json
```

Restart SearXNG, then put its address in TorKe's settings, such as `http://searxng:8080`. Pictures use the **images** category, and videos use the **youtube** engine, so keep both enabled.

## 5. YouTube

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

## Tools you own and tools you need

TorKe keeps two lists for each person:

- **Tools you own:** the starter kit switches, plus tools they tell TorKe about ("I bought a 3/8 torque wrench"), send a photo of (a tool, a kit's contents list or a receipt), or tap **I have it** on the Tools card. With Homebox on, Homebox is the main list (section 6).
- **Needed tools:** tools a job needs that they don't have yet. This list is separate from the parts list. A tool comes off it when they save it as owned.

To work out a job's tools, TorKe reads the manual for the job when there is one: a PDF attached to the item in Homebox, a PDF attached in the chat, or an iFixit guide. It shows what it found on the Tools card, with what they have and what they need. **Nothing is saved to a list until the person says yes**, and the card's buttons count as a yes.

TorKe reads text from PDFs. A manual that's only scanned pictures has no text to read, and TorKe says so.

## Parts and the shopping list

TorKe also keeps a **parts list** for each person: parts they still need for a job, like new brake pads, with the part number, a buy link and the price. Parts aren't kept as inventory. Once a part is installed it's done, and the repair log notes it.

Ask TorKe "What do I need to buy?" to see the **Shopping list** card: tools to get and parts to get side by side, with a **Buy** link (or **Find it**, a web search, when no link was saved) and a **Got it** button. Got it on a tool saves it to their tools; on a part, it takes it off the list. The tools and parts lists stay separate.

## 6. Homebox (optional)

With Homebox on, Homebox is the main list of tools people own, and TorKe reads manuals attached to the things being fixed.

1. **Sign-in:** on Homebox 0.26 or later, create an API key under your Homebox profile and paste it into **Homebox API key**. On older versions, fill in a user and password instead. TorKe sees only what that account can see.
2. **Tools tag:** TorKe looks for tools tagged **Tools** first (change it in **Homebox tools tag**), then searches all items by name.
3. **Adding tools:** turn on **Let TorKe add new tools to Homebox** if you want TorKe to save new tools there. It creates new items with the Tools tag, in **Homebox tools location** or your first location. It never changes or deletes anything already in Homebox, and it adds nothing until the person confirms. With this off, new tools go to TorKe's own list for that person.
4. **Manuals:** attach the manual PDF to the item in Homebox with the attachment type **Manual**. TorKe matches the item by name, so name items the way people say them, such as "Bosch dishwasher SHE3AR75UC". The item has to be visible to TorKe's Homebox account.

Homebox 0.26 (June 2026) replaced its "items" API with a new "entities" API. TorKe works with both, but try a lookup and a manual once after setup.

## 7. Parts in Home Assistant (optional)

TorKe always keeps its own parts list. It can also send the parts a person adds to a Home Assistant webhook. It never buys anything. This automation adds each part to a to-do list named `todo.parts`:

```yaml
alias: TorKe parts list
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
            description: "{{ trigger.json.job }} {{ repeat.item.store }} {{ repeat.item.price }} {{ repeat.item.link }}"
```

Put `http://<home-assistant>:8123/api/webhook/<your webhook id>` in **Parts webhook address**, then turn on **Parts in Home Assistant**. Treat the webhook ID like a password. Items you tick off in Home Assistant don't come off TorKe's list; tap **Got it** on the Shopping list card or tell TorKe.

## 8. Needed tools in Home Assistant (optional)

TorKe always keeps its own needed tools list. To also see it in Home Assistant, on its own to-do list separate from parts, add a second automation with a different webhook ID. This one adds each tool to `todo.tools_needed`:

```yaml
alias: TorKe needed tools
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
            entity_id: todo.tools_needed
          data:
            item: "{{ repeat.item }}"
            description: "{{ trigger.json.item }} {{ trigger.json.job }}"
```

Put its address in **Needed tools webhook address**, then turn on **Needed tools in Home Assistant**. Items you tick off in Home Assistant don't come off TorKe's list; tell TorKe you got the tool.

## 9. What TorKe saves on the server

Each person's files are kept in `<DATA_DIR>/torke/` on the Open WebUI server. In the Docker image that's under `/app/backend/data`, so they're included when you back up Open WebUI's data volume. People only see their own.

- `repair-log-<user id>.json`: finished jobs, when **Repair log** is on.
- `tools-owned-<user id>.json`: tools they told TorKe about, when they aren't saved to Homebox.
- `tools-needed-<user id>.json`: the needed tools list.
- `parts-needed-<user id>.json`: the parts list.
- `projects-<user id>.json`: the open project in each chat, so a restart doesn't forget it.

Settings each person fills in (their tools box, YouTube sign-in) are saved with their Open WebUI account, so they enter them once.

## 10. The buttons and the confirmation prompt

The buttons on TorKe's cards send a message to the chat. Open WebUI shows these cards in a locked-down frame, so it asks you to confirm before a button sends anything. That's the safe default.

To skip the confirmation, an admin can turn on **Settings > Interface > iframe Sandbox Allow Same Origin**. That gives every card in Open WebUI, from any tool, access to the page it's on, so leave it off unless you trust all your tools.

## 11. Troubleshooting

- **The model doesn't use the buttons or tools:** check that the TorKe tool is turned on for the model, and try a base model that's stronger at tool calling.
- **No pictures:** turn on **Pictures**, set the SearXNG address, and check that JSON output is on (section 4). Some sites block their images from showing elsewhere; TorKe then shows the placeholder.
- **"Search failed" errors:** Open WebUI's server can't reach SearXNG or the site. Check the address from inside the Open WebUI container.
- **YouTube sign-in failed:** the refresh token expired or was revoked. If the Google project is in Testing, see the 7-day catch in section 5.
- **"No item matching" in Homebox:** check that the item's name contains the words people use for it, and that TorKe's Homebox account can see it.
- **A manual won't read:** it may be scanned pictures with no text, or over 60 MB. Open WebUI includes the PDF reader TorKe uses (pypdf); if it's missing, install it in Open WebUI's environment.

## Things to verify on your setup

TorKe 0.3.0 passed its offline tests but hasn't yet been tested in a live Open WebUI. These parts depend on outside services or Open WebUI internals, so try them once. They're marked `VERIFY` in the code.

- **iFixit:** the search endpoint and guide field names.
- **Attached photos:** that a photo attached in the chat shows on the project card.
- **Buttons:** the confirmation behavior of card buttons.
- **Model file:** importing `torke-model.json`.
- **Recall checks:** the CPSC manufacturer filter.
- **Homebox:** that an API key works as a bearer token, and downloading a manual on Homebox versions before 0.26.
