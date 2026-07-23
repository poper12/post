from telegram import Update
from telegram.ext import ContextTypes

from db.channels import get_user_channels, get_channel
from db.settings import get_settings, cycle_parse_mode, toggle_bool
from utils.keyboards import channel_list_kb, settings_kb


async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    channels = await get_user_channels(update.effective_user.id)
    if not channels:
        await query.edit_message_text("No channels connected yet.")
        return
    if len(channels) == 1:
        await _show_settings(query, channels[0]["chat_id"])
    else:
        await query.edit_message_text(
            "Pick a channel to configure:", reply_markup=channel_list_kb(channels, "settings:pick")
        )


async def settings_pick_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = int(query.data.split(":")[2])
    await _show_settings(query, chat_id)


async def _show_settings(query, chat_id):
    settings = await get_settings(chat_id)
    ch = await get_channel(chat_id)
    context_data = {"chat_id": chat_id}
    query.data = query.data  # no-op, chat_id is embedded via closure below
    await query.edit_message_text(
        f"⚙️ Settings for <b>{ch['title']}</b>\n\nChoose what you want to change.",
        parse_mode="HTML",
        reply_markup=_settings_kb_with_chat(settings, chat_id),
    )


def _settings_kb_with_chat(settings, chat_id):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    pm = settings.get("parse_mode", "HTML")
    silent = "ON" if settings.get("silent") else "OFF"
    preview = "ON" if settings.get("link_preview") else "OFF"
    reactions = "ON" if settings.get("default_reactions") else "OFF"
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(f"Auto Formatting: {pm}", callback_data=f"set:parse_mode:{chat_id}")],
            [InlineKeyboardButton(f"Silent Broadcast: {silent}", callback_data=f"set:silent:{chat_id}")],
            [InlineKeyboardButton(f"Link Previews: {preview}", callback_data=f"set:link_preview:{chat_id}")],
            [InlineKeyboardButton(f"Default Reactions: {reactions}", callback_data=f"set:default_reactions:{chat_id}")],
            [InlineKeyboardButton("🎯 Adsgram", callback_data=f"ads:open:{chat_id}")],
            [InlineKeyboardButton("« Back", callback_data="menu:root")],
        ]
    )


async def toggle_setting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    _, key, chat_id = query.data.split(":")
    chat_id = int(chat_id)

    if key == "parse_mode":
        await cycle_parse_mode(chat_id)
    else:
        await toggle_bool(chat_id, key)

    await query.answer()
    settings = await get_settings(chat_id)
    ch = await get_channel(chat_id)
    await query.edit_message_text(
        f"⚙️ Settings for <b>{ch['title']}</b>\n\nChoose what you want to change.",
        parse_mode="HTML",
        reply_markup=_settings_kb_with_chat(settings, chat_id),
    )
