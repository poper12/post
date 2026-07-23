import datetime

from telegram import Bot

from db.settings import get_settings
from db.posts import mark_sent, set_adsgram_revert_at
from utils.formatting import resolve_parse_mode, buttons_to_markup
from utils.adsgram import wrap_buttons_for_adsgram, revert_due_at


async def send_post_to_channel(bot: Bot, post: dict, job_queue=None) -> int:
    """Sends a stored post dict to its target channel, applying channel settings.
    If Adsgram is enabled and the post has buttons, button links are wrapped with
    the ad mini-app first and a revert job is scheduled (only ever for posts that
    already have buttons). Returns the sent message_id."""
    chat_id = post["chat_id"]
    content = post["content"]
    settings = await get_settings(chat_id)

    # Only posts that already have buttons are ever touched by Adsgram.
    if content.get("buttons"):
        content = await wrap_buttons_for_adsgram(post["post_id"], content, settings)

    parse_mode = resolve_parse_mode(settings.get("parse_mode", "HTML"))
    disable_preview = not settings.get("link_preview", True)
    silent = settings.get("silent", False)
    reply_markup = buttons_to_markup(content.get("buttons", []))

    kind = content.get("type", "text")
    text = content.get("text") or ""
    file_id = content.get("file_id")

    common = dict(
        chat_id=chat_id,
        parse_mode=parse_mode,
        disable_notification=silent,
        reply_markup=reply_markup,
    )

    if kind == "text":
        msg = await bot.send_message(
            text=text or "​",
            link_preview_options={"is_disabled": disable_preview} if parse_mode else None,
            **common,
        )
    elif kind == "photo":
        msg = await bot.send_photo(photo=file_id, caption=text, **common)
    elif kind == "video":
        msg = await bot.send_video(video=file_id, caption=text, **common)
    elif kind == "document":
        msg = await bot.send_document(document=file_id, caption=text, **common)
    else:
        msg = await bot.send_message(text=text or "​", **common)

    if settings.get("default_reactions"):
        emojis = settings.get("reactions", [])
        if emojis:
            try:
                await bot.set_message_reaction(
                    chat_id=chat_id, message_id=msg.message_id, reaction=emojis[0]
                )
            except Exception:
                pass  # reactions may not be permitted in every channel

    await mark_sent(post["post_id"], msg.message_id)

    # Schedule the ad-link revert if this post actually got wrapped.
    if any(b.get("original_url") for row in content.get("buttons", []) for b in row):
        when_ts = revert_due_at(settings)
        await set_adsgram_revert_at(post["post_id"], when_ts)
        if job_queue is not None:
            from utils.scheduler import schedule_revert_job

            schedule_revert_job(
                job_queue,
                post["post_id"],
                datetime.datetime.fromtimestamp(when_ts, tz=datetime.timezone.utc),
            )

    return msg.message_id
