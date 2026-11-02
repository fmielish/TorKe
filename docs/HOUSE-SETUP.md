# Running TorKe as a whole-house assistant

TorKe works on its own for anyone: Open WebUI plus Homebox, with everything else off. This guide is for people who want more: upkeep schedules, spares that never run out, recalls checked every month, work a shop did on the car, and messages on the screen in the room you're in.

Every one of these is a switch in TorKe's settings, and **every switch starts off**. Leave one off and TorKe behaves exactly as the main [setup guide](SETUP.md) describes. Turn on only what you want.

Version 0.5.0 builds all of this and passes its offline tests against a stand-in Homebox. It hasn't been tried against a real Homebox or Home Assistant yet; the list at the end says what to check first.

## What you need to run

| App | What it's for | Needed? |
|---|---|---|
| **Open WebUI** | TorKe itself | Always |
| **Homebox** | Everything TorKe keeps: tools, parts, manuals, repair log, upkeep, spares, invoices | Always, for any of the switches below except VIN decoding and voice |
| **Home Assistant** | Speaking and showing messages in rooms; optional copies of your to-get lists | Only for **Voice and room screens** |
| **An outside assistant** | Anything else that talks to TorKe for you: a chat bot, a home automation, a program that reads photos you send it. It asks TorKe questions and hands it results. | Only for **Hand-offs** and for shop invoices that arrive as photos outside Open WebUI |
| SearXNG | Pictures and real search results | Optional (see [SETUP.md](SETUP.md)) |

TorKe also reaches out to NHTSA (vehicles) and CPSC (household products) for recalls and complaints. Both are free US government services and need only an internet connection.

If these run as containers, each one must be reachable from Open WebUI's container by its address, for example `http://homebox:7745`. Test that from inside the Open WebUI container before blaming TorKe.

## The switches

Admins find them in **Workspace > Tools > TorKe > gear**. Each saving switch also needs **Let TorKe update Homebox** (setup guide, section 4).

| Switch | What it does | Also needs |
|---|---|---|
| **Scheduled upkeep** | Saves a due date (a scheduled entry in the item's maintenance log) or a target like "next oil change at 105,000", repeats noted in words, and answers "what's due?" with dates, overdue items and how far each target is from the last mileage or hours in the repair log | Mileage targets need *Save facts on owned items* |
| **Critical spares and consumables** | Tracks things you never want to run out of (filters, bulbs, belts) with how many you have and the least you want. Using one takes it off the count and says when it's below the minimum, then offers to add it to parts to get. Spares never get archived when a job closes out | |
| **VIN decoding and complaints** | Turns a VIN into year, make, model and engine, and adds NHTSA owner complaints to a vehicle's safety warnings. The VIN is sent to NHTSA | Saving the result on the vehicle needs *Save facts on owned items* |
| **Save facts on owned items** | Lets TorKe write facts (model number, capacities, filter size, VIN, upkeep targets) on **any** item you own in Homebox, and attach invoices to it, not only items tagged Tools or Parts. It still never deletes anything and still asks first | |
| **Shop work** | Records work a shop did: a repair log entry with the shop, cost, mileage and warranty, plus the invoice attached to the item. Shows the cost history and warranties for each vehicle or item | The invoice attachment needs *Save facts on owned items* |
| **Hand-offs to an outside assistant** | Lets an outside assistant ask for the weekly what's due, a monthly recall check and the device list | The parts of the weekly summary follow their own switches (upkeep, spares) |
| **Voice and room screens** | Sends a short message to Home Assistant to be spoken or shown on the screen nearest you | The webhook address (below) |

### What it saves, so you can find it in Homebox

- **Upkeep:** scheduled entries in the item's maintenance log. A mileage target is a field named like `Next oil change at`.
- **Spares:** items tagged **Parts** and **Critical spare** (the tag name can be changed) on the Parts shelf, with the quantity as the count and a `Minimum` field.
- **Facts:** fields on the item, such as `Year`, `Make`, `Model`, `VIN`.
- **Shop work:** a maintenance log entry whose description holds the mileage, `Done by`, notes and warranty lines, with the cost in the entry's cost field. The invoice is attached with the type **Receipt**.

## Shop work, step by step

1. You send a photo of the invoice to the outside assistant, or attach it to a chat with TorKe.
2. Something has to read the photo. TorKe doesn't read pictures itself; the model behind it (or the outside assistant) does, and it needs vision to do so.
3. TorKe shows what it read: the shop, date, work, cost, mileage and any warranty. You say yes.
4. TorKe adds the repair log entry and, if *Save facts on owned items* is on, attaches the invoice to the vehicle.
5. Later, ask for the vehicle's **cost history** or its **warranties**. A warranty counts as over once its date has passed or the last mileage in the log reaches its mileage limit.

Anything automotive works: oil changes, tires, glass and anything else. It's also fine for appliances and other items.

If your outside assistant files every photo as a purchase receipt, point shop invoices at TorKe instead; otherwise they'll be treated as shopping.

## Turn it on

1. Finish the main [setup guide](SETUP.md) first, including Homebox and **Let TorKe update Homebox**.
2. Turn on the switches you want, one at a time, and try each before the next.
3. For **Voice and room screens**, add the webhook below, paste its address into **Room screen webhook address** and turn the switch on.
4. For **Hand-offs**, set up your outside assistant to ask the TorKe model in Open WebUI. How it does that depends on that assistant; TorKe just answers.

## Voice and room screens in Home Assistant

TorKe sends `message`, `room` (a name, or empty for "nearest the person") and `speak` to a webhook. Home Assistant decides what "nearest" means, usually from presence sensors you already have, and which speaker or screen to use. This example is a starting point: the entity names are placeholders, so change them to yours, and note that Home Assistant renames things from time to time.

```yaml
alias: TorKe room message
triggers:
  - trigger: webhook
    webhook_id: "torke-room-change-this-to-a-long-random-id"
    allowed_methods: [POST]
    local_only: true
actions:
  - action: persistent_notification.create
    data:
      title: TorKe
      message: "{{ trigger.json.message }}"
  - if: "{{ trigger.json.speak }}"
    then:
      - action: tts.speak
        target:
          entity_id: tts.your_text_to_speech
        data:
          media_player_entity_id: >-
            {{ 'media_player.' ~ (trigger.json.room | lower | replace(' ', '_'))
               if trigger.json.room else 'media_player.kitchen' }}
          message: "{{ trigger.json.message }}"
```

Put the address (`http://<home-assistant>:8123/api/webhook/<id>`) in TorKe's settings and treat the id like a password.

## Keeping lists in Homebox

The house uses the same Homebox layout as everyone else: **To get**, **Rent** and the **Parts shelf**. The Home Assistant to-do lists are an optional copy only (section 8 of the setup guide).

## Check these on your setup

They're marked `VERIFY` in the code.

- **Scheduled upkeep:** that Homebox lists scheduled entries across all items at `/maintenance?status=scheduled`, and that an entry with only a scheduled date saves.
- **Invoice upload:** that Homebox accepts the attachment (multipart fields `file`, `type`, `name`) and shows it with the type Receipt.
- **Facts and targets:** that saving a field keeps the item's other details (the same check as for tools and parts).
- **Device list:** that Homebox returns the brand, model number and serial number on each item.
- **Room messages:** that your Home Assistant automation speaks and shows them where you expect.
- **NHTSA:** that the VIN decoder and complaints answers look right for your vehicles.
