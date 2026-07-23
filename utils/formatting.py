from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode

PARSE_MODE_MAP = {
    "HTML": ParseMode.HTML,
    "Markdown": ParseMode.MARKDOWN_V2,
    "None": None,
}


def resolve_parse_mode(name: str):
    return PARSE_MODE_MAP.get(name, ParseMode.HTML)


def buttons_to_markup(buttons: list) -> InlineKeyboardMarkup | None:
    if not buttons:
        return None
    rows = []
    for row in buttons:
        rows.append([InlineKeyboardButton(b["text"], url=b["url"]) for b in row])
    return InlineKeyboardMarkup(rows)


def build_post_link(channel: dict, message_id: int) -> str:
    username = channel.get("username")
    if username:
        return f"https://t.me/{username}/{message_id}"
    chat_id = str(channel["chat_id"])
    internal = chat_id[4:] if chat_id.startswith("-100") else chat_id.lstrip("-")
    return f"https://t.me/c/{internal}/{message_id}"


def content_preview_text(content: dict) -> str:
    """Small textual summary shown in bot chat, e.g. when listing drafts."""
    kind = content.get("type", "text")
    text = content.get("text") or ""
    prefix = {"photo": "🖼", "video": "🎬", "document": "📄", "text": "📝"}.get(kind, "📝")
    snippet = text.strip().splitlines()[0][:60] if text.strip() else "(no caption)"
    return f"{prefix} {snippet}"
