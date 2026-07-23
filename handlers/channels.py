from telegram import Update
from telegram.ext import ContextTypes

from db.channels import get_user_channels, get_channel, remove_channel, add_channel
from db.users import set_state, get_state
from utils.keyboards import channels_menu_kb, channel_view_kb, cancel_kb
from states import AWAITING_CHANNEL_FORWARD


async def channels_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    channels = await get_user_channels(user.id)
    text = "📡 Your connected channels:" if channels else "No channels connected yet."
    await query.edit_message_text(text, reply_markup=channels_menu_kb(channels))


async def channel_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = int(query.data.split(":")[2])
    ch = await get_channel(chat_id)
    if not ch:
        await query.edit_message_text("Channel not found.", reply_markup=channel_view_kb(chat_id))
        return
    link = f"https://t.me/{ch['username']}" if ch.get("username") else "(private channel)"
    await query.edit_message_text(
        f"<b>{ch['title']}</b>\nID: <code>{ch['chat_id']}</code>\n{link}",
        parse_mode="HTML",
        reply_markup=channel_view_kb(chat_id),
    )


async def channel_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = int(query.data.split(":")[2])
    await remove_channel(chat_id)
    await query.answer("Channel removed.")
    channels = await get_user_channels(update.effective_user.id)
    await query.edit_message_text("📡 Your connected channels:", reply_markup=channels_menu_kb(channels))


async def channel_add_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await set_state(update.effective_user.id, AWAITING_CHANNEL_FORWARD)
    await query.edit_message_text(
        "➕ <b>Add a channel</b>\n\n"
        "1. Add me as <b>admin</b> in your channel (I'll auto-connect it), <b>or</b>\n"
        "2. Forward any message from that channel to me here right now.",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )


async def handle_forwarded_channel_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    state, _ = await get_state(user.id)
    if state != AWAITING_CHANNEL_FORWARD:
        return False

    fwd_chat = update.message.forward_from_chat
    if not fwd_chat or fwd_chat.type != "channel":
        await update.message.reply_text(
            "That doesn't look like a forward from a channel. Please forward a message "
            "directly from your channel, or add me as admin there instead."
        )
        return True

    try:
        member = await context.bot.get_chat_member(fwd_chat.id, context.bot.id)
        if member.status not in ("administrator", "creator"):
            await update.message.reply_text(
                "I'm in that channel but I'm not an admin yet. Please promote me to admin "
                "and try again."
            )
            return True
    except Exception:
        await update.message.reply_text(
            "I'm not a member of that channel yet. Please add me as admin first."
        )
        return True

    await add_channel(fwd_chat.id, fwd_chat.title, fwd_chat.username, user.id)
    await set_state(user.id, None)
    await update.message.reply_text(f"✅ Connected channel <b>{fwd_chat.title}</b>!", parse_mode="HTML")
    return True
