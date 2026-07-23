from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from db.channels import get_user_channels, get_channel
from db.posts import get_sent_posts, get_post, update_content, delete_post
from db.users import set_state
from db.settings import get_settings
from utils.keyboards import channel_list_kb, sent_posts_kb, edit_view_kb, cancel_kb
from utils.formatting import content_preview_text, resolve_parse_mode, buttons_to_markup
from states import AWAITING_EDIT_TEXT


async def edit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    channels = await get_user_channels(update.effective_user.id)
    if not channels:
        await query.edit_message_text("No channels connected yet.")
        return
    if len(channels) == 1:
        await _show_sent(query, channels[0]["chat_id"])
    else:
        await query.edit_message_text(
            "Pick a channel:", reply_markup=channel_list_kb(channels, "edit:pick")
        )


async def edit_pick_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = int(query.data.split(":")[2])
    await _show_sent(query, chat_id)


async def _show_sent(query, chat_id):
    posts = await get_sent_posts(chat_id)
    if not posts:
        await query.edit_message_text("No sent posts found yet.")
        return
    await query.edit_message_text(
        f"✏️ Last {len(posts)} sent post(s) — pick one to edit:",
        reply_markup=sent_posts_kb(posts),
    )


async def edit_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    post_id = query.data.split(":")[2]
    post = await get_post(post_id)
    if not post:
        await query.edit_message_text("Post not found.")
        return
    snippet = content_preview_text(post["content"])
    await query.edit_message_text(f"{snippet}\n\nWhat do you want to do?", reply_markup=edit_view_kb(post_id))


async def edit_text_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    post_id = query.data.split(":")[2]
    await query.answer()
    await set_state(update.effective_user.id, AWAITING_EDIT_TEXT, {"post_id": post_id})
    await query.message.reply_text(
        "✏️ Send the replacement text/caption:", reply_markup=cancel_kb()
    )


async def handle_edit_text(update: Update, context: ContextTypes.DEFAULT_TYPE, state_data: dict):
    user = update.effective_user
    post_id = state_data["post_id"]
    post = await get_post(post_id)
    if not post:
        await update.message.reply_text("That post no longer exists.")
        return
    new_text = update.message.text_html or update.message.text or ""
    content = post["content"]
    content["text"] = new_text
    settings = await get_settings(post["chat_id"])
    parse_mode = resolve_parse_mode(settings.get("parse_mode", "HTML"))
    markup = buttons_to_markup(content.get("buttons", []))

    try:
        if content["type"] == "text":
            await context.bot.edit_message_text(
                chat_id=post["chat_id"],
                message_id=post["message_id"],
                text=new_text,
                parse_mode=parse_mode,
                reply_markup=markup,
            )
        else:
            await context.bot.edit_message_caption(
                chat_id=post["chat_id"],
                message_id=post["message_id"],
                caption=new_text,
                parse_mode=parse_mode,
                reply_markup=markup,
            )
    except Exception as e:
        await update.message.reply_text(f"❌ Couldn't edit the channel message: {e}")
        return

    await update_content(post_id, content)
    await set_state(user.id, None)
    await update.message.reply_text("✅ Post updated in the channel.")


async def edit_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    post_id = query.data.split(":")[2]
    post = await get_post(post_id)
    if not post:
        await query.answer("Not found", show_alert=True)
        return
    try:
        await context.bot.delete_message(post["chat_id"], post["message_id"])
    except Exception as e:
        await query.answer(f"Failed: {e}", show_alert=True)
        return
    await delete_post(post_id)
    await query.answer("Deleted from channel")
    await query.edit_message_text("🗑 Post deleted from the channel.")
