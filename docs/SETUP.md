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
| Repair log | Each person's finished jobs, saved on the server | Nothing (section 8) |
| Homebox | Checks Homebox for tools you own (read-only) | Homebox address and a login (section 6) |
| Parts list | Sends parts to Home Assistant, for example a to-do list | A Home Assistant webhook (section 7) |
| YouTube playlist | Each person can add videos to their own playlist | Each person's Google sign-in (section 5) |
| Most results | Results per search, 3 to 10 | |

### Each person's settings

Each person opens **Chat Controls > Valves > TorKe** in a chat. Non-admin users need the **Allow Chat Valves** permission.

- **Tools they own.** TorKe assumes a basic 100-piece home tool kit, a 100-piece socket set and a basic multimeter. Each can be switched off, and anything else goes in **Other tools I own**, such as "torque wrench 3/8 in, jack stands, OBD2 scanner".
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

## 6. Homebox (optional)

Make a separate Homebox login for TorKe, then fill in the Homebox address, user and password in TorKe's settings and turn on **Homebox**. TorKe only searches items; it never adds, changes or deletes anything. Homebox's API paths can change between versions, so try a lookup once after setup.

## 7. Parts list in Home Assistant (optional)

TorKe can send the parts a person wants to a Home Assistant webhook. It never buys anything. This automation adds each part to a to-do list named `todo.parts`:

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

Put `http://<home-assistant>:8123/api/webhook/<your webhook id>` in **Parts webhook address**, then turn on **Parts list**. Treat the webhook ID like a password.

## 8. Repair log

With **Repair log** on, each person's jobs are saved on the Open WebUI server at `<DATA_DIR>/torke/repair-log-<user id>.json`. In the Docker image that's under `/app/backend/data`, so it's included when you back up Open WebUI's data volume. People only see their own log.

## 9. The buttons and the confirmation prompt

The buttons on TorKe's cards send a message to the chat. Open WebUI shows these cards in a locked-down frame, so it asks you to confirm before a button sends anything. That's the safe default.

To skip the confirmation, an admin can turn on **Settings > Interface > iframe Sandbox Allow Same Origin**. That gives every card in Open WebUI, from any tool, access to the page it's on, so leave it off unless you trust all your tools.

## 10. Troubleshooting

- **The model doesn't use the buttons or tools:** check that the TorKe tool is turned on for the model, and try a base model that's stronger at tool calling.
- **No pictures:** turn on **Pictures**, set the SearXNG address, and check that JSON output is on (section 4). Some sites block their images from showing elsewhere; TorKe then shows the placeholder.
- **"Search failed" errors:** Open WebUI's server can't reach SearXNG or the site. Check the address from inside the Open WebUI container.
- **YouTube sign-in failed:** the refresh token expired or was revoked. If the Google project is in Testing, see the 7-day catch in section 5.

## Things to verify on your setup

TorKe 0.1.0 passed its offline tests but hasn't yet been tested in a live Open WebUI. These parts depend on outside services or Open WebUI internals, so try them once. They're marked `VERIFY` in the code.

- **iFixit:** the search endpoint and guide field names.
- **Attached photos:** that a photo attached in the chat shows on the project card.
- **Buttons:** the confirmation behavior of card buttons.
- **Model file:** importing `torke-model.json`.
- **Recall checks:** the CPSC manufacturer filter.
