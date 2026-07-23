# Campus Post Bot

A Telegram bot for managing channel posts — create, schedule, edit, and track
posts across one or more channels, entirely from a private chat with the bot.
Modeled after the "Campus Manga post" bot workflow (Create Post / Scheduled
Posts / Edit Post / Channel Stats / Settings).

## Features

- **Multi-channel support** — connect any number of channels; the bot picks
  the right one automatically or asks you to choose.
- **Create Post** — send text, or a photo/video/document with caption, and
  the bot turns it into a post with a live preview.
- **Automatic HTML formatting** — any formatting you apply with Telegram's
  own text tools (bold, italic, <blockquote>, spoilers, links, etc.) is
  captured and reused automatically. You never need to type raw HTML tags —
  just format the message the normal way in Telegram and send it; the bot
  reads the formatting straight from the message entities.
- **Inline buttons** — attach one or more URL buttons to any post before
  sending.
- **Send Now or Schedule** — post immediately, or schedule for a specific
  date/time (persisted in MongoDB, survives restarts/redeploys).
- **Edit Post** — pick from your recently sent posts and edit the live
  text/caption in the channel, or delete it.
- **Channel Stats** — subscriber count, posts sent in 24h / 7d / all-time,
  and currently scheduled count.
- **Adsgram integration** — optionally wrap a post's button link(s) with an
  Adsgram ad. Viewers see the ad in a Telegram Mini App, then get redirected
  to your real link. After a duration you set (e.g. 7 days), the button
  quietly reverts to the plain link with no other change to the post. This
  only ever applies to posts that already have a button — text/media-only
  posts are never touched.
- **Per-channel Settings**
  - Auto Formatting: `HTML` / `Markdown` / `None`
  - Silent Broadcast: on/off (no notification sound)
  - Link Previews: on/off
  - Default Reactions: auto-react to the bot's own posts
- **Auto-connect on admin promotion** — add the bot as admin to a channel
  and it registers itself automatically; you can also connect a channel by
  forwarding a message from it.
- **Render-ready** — runs its own aiohttp server on Render's free web-service
  tier, serving the Telegram webhook plus the Adsgram mini-app landing page.

## Project layout

```
campus-post-bot/
├── main.py                # app wiring + webhook/polling entrypoint
├── config.py               # env var loading
├── states.py                # FSM state name constants
├── db/                       # MongoDB access layer (motor, async)
│   ├── channels.py
│   ├── settings.py
│   ├── posts.py
│   └── users.py
├── handlers/                 # Telegram update handlers
│   ├── start.py
│   ├── channels.py
│   ├── create_post.py
│   ├── scheduled.py
│   ├── edit_post.py
│   ├── stats.py
│   ├── settings.py
│   └── router.py            # routes free-text/media replies by FSM state
└── utils/
    ├── keyboards.py          # all inline keyboards
    ├── formatting.py         # parse_mode / buttons / post-link helpers
    ├── sender.py              # shared "send a post to its channel" logic
    └── scheduler.py           # JobQueue scheduling + restore on boot
```

## 1. Create the bot

1. Talk to [@BotFather](https://t.me/BotFather) → `/newbot` → copy the token.
2. In BotFather, run `/setjoingroups` and `/setprivacy` → set privacy to
   **Disabled** isn't required (the bot only needs channel admin rights, not
   group message access).
3. Add the bot as **admin** to each channel you want to manage, with at
   least: Post Messages, Edit Messages, Delete Messages.

## 2. Get a MongoDB connection string

Use a free [MongoDB Atlas](https://www.mongodb.com/cloud/atlas/register)
cluster (M0 tier is enough). Create a database user, allow access from
anywhere (`0.0.0.0/0`) for Render's dynamic IPs, and copy the connection
string.

## 3. Local setup (optional, for testing)

```bash
git clone <your-repo-url>
cd campus-post-bot
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in BOT_TOKEN, MONGO_URI, OWNER_ID
python main.py          # runs in polling mode if WEBHOOK_URL is empty
```

## 4. Deploy to Render

1. Push this repo to GitHub.
2. On Render: **New → Web Service** → connect the repo (or use the included
   `render.yaml` with **New → Blueprint** for one-click setup).
3. Set environment variables in the Render dashboard:
   - `BOT_TOKEN`
   - `MONGO_URI`
   - `OWNER_ID` (your numeric Telegram user ID, from [@userinfobot](https://t.me/userinfobot))
   - `DB_NAME` (optional, defaults to `campus_post_bot`)
   - `TIMEZONE` (optional, defaults to `Asia/Kolkata`)
   - `WEBHOOK_URL` — leave **unset**; Render auto-provides
     `RENDER_EXTERNAL_URL`, which `config.py` picks up automatically. Only
     set this manually if you're deploying somewhere else.
4. Deploy. Render will run `python main.py`, which starts an HTTP server on
   `$PORT` and registers the Telegram webhook automatically on boot.
5. Message your bot with `/start`.

## 5. One-time Adsgram Mini App setup (optional)

Skip this if you don't want the Adsgram feature — everything else works
without it.

1. Get a Block ID from your [Adsgram](https://partner.adsgram.ai) account
   (Interstitial format recommended for this use case).
2. Decide where the `/ads` landing page will live:
   - **Easiest:** use the bot's own built-in `/ads` route — no extra
     deploy needed, skip to step 3 using `https://<your-bot-render-url>/ads`.
   - **Or:** deploy the separate `adsgram-landing` service (included
     alongside this repo) for a nicer branded page on its own URL — see
     its own README for deploy steps, then use its `/ads` URL below.
3. Talk to [@BotFather](https://t.me/BotFather) → `/newapp` → select your
   bot → give it a short name (e.g. `ads`) → when asked for the Web App
   URL, use whichever `/ads` URL you picked above.
4. BotFather gives you a direct link like `https://t.me/YourBot/ads`. Put
   that in the `ADSGRAM_MINIAPP_LINK` env var on Render and redeploy.
5. In the bot: **Settings → Adsgram** (per channel) → set your **Block ID**
   → set the **revert duration** in days → toggle **Adsgram: ON**.

From then on, any post you create for that channel **that has at least one
button** will have its button link(s) swapped for the ad mini-app link when
sent. Posts without buttons are never touched. After the revert duration
elapses, the bot edits the live post's button back to the plain link
automatically — nothing else about the post changes, and the schedule
survives restarts the same way scheduled posts do.

> Adsgram's server-side ad API (`api.adsgram.ai/advbot`) is designed for
> per-user DM delivery, not static channel post buttons — this bot instead
> uses Adsgram's client-side Mini App SDK inside a small landing page it
> hosts at `/ads`, which is the supported approach for ads triggered from a
> button click. No content beyond the click token ever leaves your own
> Render service and Adsgram's SDK.

> **Free tier note:** Render's free web services sleep after inactivity and
> take a few seconds to wake on the next incoming update — normal for a
> low-traffic personal bot. Scheduled posts still fire correctly on wake
> because they're restored from MongoDB on every startup, but a scheduled
> time that arrives while the service is fully asleep will only fire once a
> new request (e.g. any Telegram update) wakes it. For guaranteed
> on-time scheduled posts, use Render's paid tier or an external uptime
> pinger.

## Usage

- `/start` — open the main menu.
- **Create Post** → pick a channel (if you have more than one) → send
  text or media with caption → preview appears with **Send Now**,
  **Schedule**, **Add Button**, **Clear Buttons**, **Re-edit Content**,
  **Cancel**.
- **Scheduled Posts** → browse and cancel pending scheduled posts per
  channel.
- **Edit Post** → pick a recently sent post → edit its text/caption live in
  the channel, or delete it.
- **Channel Stats** → subscriber count and posting activity.
- **Settings** → toggle formatting mode, silent broadcast, link previews,
  and default reactions per channel.
- **Channels** → view connected channels, remove one, or add a new one
  (forward a message from it, or just promote the bot to admin there).
- `/cancel` — abort whatever you're in the middle of (e.g. mid-schedule
  input).

## Notes on the "Default Reactions" feature

Telegram only allows a bot to set a reaction on its **own** messages in
chats where it's an admin with reaction permissions. If reactions fail
silently, double-check the bot's admin rights include reactions, and that
the channel type supports custom reactions.
