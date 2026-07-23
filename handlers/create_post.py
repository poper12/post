import datetime
import pytz

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from db.channels import get_user_channels, get_channel
from db.users import set_state, get_state, set_selected_channel
from db.posts import (
    create_draft,
    update_content,
    get_post,
    add_button,
    clear_buttons,
    delete_post,
    schedule_post,
    cancel_schedule,
)
from utils.keyboards import channel_list_kb, post_preview_kb, sent_kb, cancel_kb
from utils.formatting import buttons_to_markup, resolve_parse_mode, build_post_link
from utils.sender import send_post_to_channel
from utils.scheduler import schedule_job, cancel_job
from states import (
    AWAITING_POST_CONTENT,
    AWAITING_REEDIT_CONTENT,
    AWAITING_BUTTON_TEXT,
    AWAITING_BUTTON_URL,
    AWAITING_SCHEDULE_TIME,
)
from config import TIMEZONE

TZ = pytz.timezone(TIMEZONE)


# ---------- entry point ----------

async def create_post_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    channels = await get_user_channels(user.id)

    if not channels:
        await query.edit_message_text(
            "You have no connected channels. Add me as admin to a channel first, "
            "then use Channels ➜ Add Channel.",
        )
        return

    if len(channels) == 1:
        await _prompt_for_content(query.message.chat_id, channels[0]["chat_id"], user.id, context)
        await query.edit_message_text(
            f"✍️ Send the content for <b>{channels[0]['title']}</b> now "
            f"(text, or a photo/video with caption). HTML formatting supported.",
            parse_mode="HTML",
            reply_markup=cancel_kb(),
        )
    else:
        await query.edit_message_text(
            "Which channel do you want to post to?",
            reply_markup=channel_list_kb(channels, "create:pick"),
        )


async def create_pick_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = int(query.data.split(":")[2])
    user = update.effective_user
    await set_selected_channel(user.id, chat_id)
    await _prompt_for_content(query.message.chat_id, chat_id, user.id, context)
    ch = await get_channel(chat_id)
    await query.edit_message_text(
        f"✍️ Send the content for <b>{ch['title']}</b> now "
        f"(text, or a photo/video with caption). HTML formatting supported.",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )


async def _prompt_for_content(chat_id, target_channel_id, user_id, context):
    await set_state(user_id, AWAITING_POST_CONTENT, {"chat_id": target_channel_id})


# ---------- receiving content (called from router) ----------

def extract_content_from_message(message) -> dict:
    if message.photo:
        return {"type": "photo", "file_id": message.photo[-1].file_id, "text": message.caption_html or "", "buttons": []}
    if message.video:
        return {"type": "video", "file_id": message.video.file_id, "text": message.caption_html or "", "buttons": []}
    if message.document:
        return {"type": "document", "file_id": message.document.file_id, "text": message.caption_html or "", "buttons": []}
    return {"type": "text", "file_id": None, "text": message.text_html or "", "buttons": []}


async def handle_new_post_content(update: Update, context: ContextTypes.DEFAULT_TYPE, state_data: dict):
    user = update.effective_user
    target_channel_id = state_data["chat_id"]
    content = extract_content_from_message(update.message)

    post_id = await create_draft(user.id, target_channel_id, content)
    await set_state(user.id, None)

    ch = await get_channel(target_channel_id)
    await update.message.reply_text(
        f"🗂 1 message ready to be sent to <b>{ch['title']}</b>.",
        parse_mode="HTML",
    )
    await _send_preview(update.message.chat_id, post_id, context)


async def handle_reedit_content(update: Update, context: ContextTypes.DEFAULT_TYPE, state_data: dict):
    user = update.effective_user
    post_id = state_data["post_id"]
    content = extract_content_from_message(update.message)
    post = await get_post(post_id)
    content["buttons"] = post["content"].get("buttons", [])  # keep existing buttons
    await update_content(post_id, content)
    await set_state(user.id, None)
    await update.message.reply_text("✅ Content updated.")
    await _send_preview(update.message.chat_id, post_id, context)


async def _send_preview(chat_id, post_id, context: ContextTypes.DEFAULT_TYPE):
    post = await get_post(post_id)
    content = post["content"]
    kb = post_preview_kb(post_id)
    kind = content.get("type")
    text = content.get("text") or "(no caption)"

    if kind == "photo":
        await context.bot.send_photo(chat_id, content["file_id"], caption=text, reply_markup=kb, parse_mode=ParseMode.HTML)
    elif kind == "video":
        await context.bot.send_video(chat_id, content["file_id"], caption=text, reply_markup=kb, parse_mode=ParseMode.HTML)
    elif kind == "document":
        await context.bot.send_document(chat_id, content["file_id"], caption=text, reply_markup=kb, parse_mode=ParseMode.HTML)
    else:
        await context.bot.send_message(chat_id, text, reply_markup=kb, parse_mode=ParseMode.HTML)


# ---------- preview action buttons ----------

async def post_send_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    post_id = query.data.split(":")[2]
    post = await get_post(post_id)
    if not post:
        await query.answer("Post not found (maybe already sent).", show_alert=True)
        return
    await query.answer("Sending...")
    try:
        message_id = await send_post_to_channel(context.bot, post, context.job_queue)
    except Exception as e:
        await query.message.reply_text(f"❌ Failed to send: {e}")
        return
    ch = await get_channel(post["chat_id"])
    link = build_post_link(ch, message_id)
    await query.message.reply_text("Done!", reply_markup=sent_kb(link))


async def post_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    post_id = query.data.split(":")[2]
    await delete_post(post_id)
    await query.answer("Cancelled")
    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_text("❌ Draft discarded.")


async def post_reedit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    post_id = query.data.split(":")[2]
    await query.answer()
    await set_state(update.effective_user.id, AWAITING_REEDIT_CONTENT, {"post_id": post_id})
    await query.message.reply_text(
        "✍️ Send the new content to replace this draft (text, or photo/video with caption).",
        reply_markup=cancel_kb(),
    )


async def post_clear_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    post_id = query.data.split(":")[2]
    await clear_buttons(post_id)
    await query.answer("Buttons cleared")


async def post_add_button_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    post_id = query.data.split(":")[2]
    await query.answer()
    await set_state(update.effective_user.id, AWAITING_BUTTON_TEXT, {"post_id": post_id})
    await query.message.reply_text("🔘 Send the button's label text:", reply_markup=cancel_kb())


async def handle_button_text(update: Update, context: ContextTypes.DEFAULT_TYPE, state_data: dict):
    user = update.effective_user
    state_data["button_text"] = update.message.text.strip()
    await set_state(user.id, AWAITING_BUTTON_URL, state_data)
    await update.message.reply_text("🔗 Now send the button's URL (must start with http:// or https://):")


async def handle_button_url(update: Update, context: ContextTypes.DEFAULT_TYPE, state_data: dict):
    user = update.effective_user
    url = update.message.text.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        await update.message.reply_text("That doesn't look like a valid URL. Try again, or /cancel.")
        return
    post_id = state_data["post_id"]
    await add_button(post_id, state_data["button_text"], url)
    await set_state(user.id, None)
    await update.message.reply_text("✅ Button added.")
    await _send_preview(update.message.chat_id, post_id, context)


# ---------- scheduling ----------

async def post_schedule_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    post_id = query.data.split(":")[2]
    await query.answer()
    await set_state(update.effective_user.id, AWAITING_SCHEDULE_TIME, {"post_id": post_id})
    await query.message.reply_text(
        f"🗓 Send the date & time to post this, in <b>{TIMEZONE}</b> time, format:\n"
        f"<code>YYYY-MM-DD HH:MM</code>\n\nExample: <code>2026-07-25 21:30</code>",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )


async def handle_schedule_time(update: Update, context: ContextTypes.DEFAULT_TYPE, state_data: dict):
    user = update.effective_user
    post_id = state_data["post_id"]
    raw = update.message.text.strip()
    try:
        naive = datetime.datetime.strptime(raw, "%Y-%m-%d %H:%M")
        local_dt = TZ.localize(naive)
        utc_dt = local_dt.astimezone(pytz.utc)
    except ValueError:
        await update.message.reply_text("Invalid format. Use YYYY-MM-DD HH:MM, e.g. 2026-07-25 21:30")
        return

    if utc_dt <= datetime.datetime.now(pytz.utc):
        await update.message.reply_text("That time is in the past. Please send a future date/time.")
        return

    await schedule_post(post_id, utc_dt.timestamp())
    schedule_job(context.job_queue, post_id, utc_dt)
    await set_state(user.id, None)
    await update.message.reply_text(
        f"✅ Scheduled for {local_dt.strftime('%Y-%m-%d %H:%M')} {TIMEZONE}."
    )
