import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ["8344576196:AAF6DGhtCTkXndflArkW7fKV0qQEBOjL-Dk"]
MONGO_URI = os.environ["mongodb+srv://vishnumdot67_db_user:9IZOH90Zg3K5Xkyv@cluster0.xwzo4bv.mongodb.net/?appName=Cluster0"]
DB_NAME = os.environ.get("DB_NAME", "campus_post_bot")
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))

# Render provides its own external URL; you can also set WEBHOOK_URL manually.
WEBHOOK_URL = os.environ.get("WEBHOOK_URL") or os.environ.get("RENDER_EXTERNAL_URL", "")
PORT = int(os.environ.get("PORT", 8080))
TIMEZONE = os.environ.get("TIMEZONE", "Asia/Kolkata")

WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"

# Adsgram integration
ADSGRAM_MINIAPP_LINK = os.environ.get("ADSGRAM_MINIAPP_LINK", "")  # e.g. https://t.me/YourBot/ads
ADSGRAM_LANDING_ROUTE = "/ads"
ADSGRAM_RESOLVE_ROUTE = "/resolve"

DEFAULT_SETTINGS = {
    "parse_mode": "HTML",       # HTML | Markdown | None
    "silent": False,            # silent broadcast (no notification)
    "link_preview": True,       # show link previews
    "default_reactions": False, # auto-react to own posts
    "reactions": ["🔥", "❤️", "👍"],
    "adsgram_enabled": False,   # wrap button links with an Adsgram mini app ad
    "adsgram_block_id": None,   # Block ID from your Adsgram account
    "adsgram_revert_days": 7,   # days after which the ad link reverts to the real link
}
