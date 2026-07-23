from telegram import Update, MessageOriginChannel
from telegram.ext import ContextTypes

from db.channels import (
    get_user_channels,
    get_channel,
    remove_channel,
    add_channel,
)

from db.users import (
    set_state,
    get_state,
)

from utils.keyboards import (
    channels_menu_kb,
    channel_view_kb,
    cancel_kb,
)

from states import AWAITING_CHANNEL_FORWARD


async def channels_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    channels = await get_user_channels(user.id)

    text = (
        "📡 Your connected channels:"
        if channels
        else "No channels connected yet."
    )

    await query.edit_message_text(
        text,
        reply_markup=channels_menu_kb(channels),
    )


async def channel_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = int(query.data.split(":")[2])

    ch = await get_channel(chat_id)

    if not ch:
        await query.edit_message_text(
            "Channel not found.",
            reply_markup=channel_view_kb(chat_id),
        )
        return

    link = (
        f"https://t.me/{ch['username']}"
        if ch.get("username")
        else "(private channel)"
    )

    await query.edit_message_text(
        f"<b>{ch['title']}</b>\n"
        f"ID: <code>{ch['chat_id']}</code>\n"
        f"{link}",
        parse_mode="HTML",
        reply_markup=channel_view_kb(chat_id),
    )


async def channel_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = int(query.data.split(":")[2])

    await remove_channel(chat_id)

    channels = await get_user_channels(update.effective_user.id)

    await query.edit_message_text(
        "📡 Your connected channels:",
        reply_markup=channels_menu_kb(channels),
    )


async def channel_add_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await set_state(
        update.effective_user.id,
        AWAITING_CHANNEL_FORWARD,
    )

    await query.edit_message_text(
        "➕ <b>Add a channel</b>\n\n"
        "1. Add me as <b>administrator</b> in your channel.\n"
        "2. Forward any message from that channel to me.\n\n"
        "After forwarding, I'll connect it automatically.",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )


async def handle_forwarded_channel_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user

    state, _ = await get_state(user.id)

    if state != AWAITING_CHANNEL_FORWARD:
        return False

    message = update.effective_message

    origin = message.forward_origin

    if not isinstance(origin, MessageOriginChannel):
        await message.reply_text(
            "❌ Please forward a message from a Telegram channel."
        )
        return True

    channel = origin.chat

    try:
        member = await context.bot.get_chat_member(
            channel.id,
            context.bot.id,
        )

        if member.status not in (
            "administrator",
            "creator",
        ):
            await message.reply_text(
                "❌ Please promote me to administrator in that channel first."
            )
            return True

    except Exception:
        await message.reply_text(
            "❌ I am not in that channel yet.\n"
            "Please add me as administrator first."
        )
        return True

    await add_channel(
        channel.id,
        channel.title,
        channel.username,
        user.id,
    )

    await set_state(user.id, None)

    await message.reply_text(
        f"✅ Successfully connected <b>{channel.title}</b>",
        parse_mode="HTML",
    )

    return True
