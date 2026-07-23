import time

from telegram import Update
from telegram.ext import ContextTypes

from db.channels import get_user_channels, get_channel
from db import posts_col
from utils.keyboards import channel_list_kb, back_button


async def stats_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    channels = await get_user_channels(update.effective_user.id)
    if not channels:
        await query.edit_message_text("No channels connected yet.")
        return
    if len(channels) == 1:
        await _show_stats(query, context, channels[0]["chat_id"])
    else:
        await query.edit_message_text(
            "Pick a channel:", reply_markup=channel_list_kb(channels, "stats:pick")
        )


async def stats_pick_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = int(query.data.split(":")[2])
    await _show_stats(query, context, chat_id)


async def _show_stats(query, context, chat_id):
    ch = await get_channel(chat_id)
    try:
        member_count = await context.bot.get_chat_member_count(chat_id)
    except Exception:
        member_count = "N/A"

    now = time.time()
    day_ago = now - 86400
    week_ago = now - 7 * 86400

    total_sent = await posts_col.count_documents({"chat_id": chat_id, "status": "sent"})
    last_24h = await posts_col.count_documents(
        {"chat_id": chat_id, "status": "sent", "sent_at": {"$gte": day_ago}}
    )
    last_7d = await posts_col.count_documents(
        {"chat_id": chat_id, "status": "sent", "sent_at": {"$gte": week_ago}}
    )
    scheduled = await posts_col.count_documents({"chat_id": chat_id, "status": "scheduled"})

    text = (
        f"📊 <b>{ch['title']}</b>\n\n"
        f"👥 Subscribers: <b>{member_count}</b>\n"
        f"📝 Total posts sent: <b>{total_sent}</b>\n"
        f"🕐 Last 24h: <b>{last_24h}</b>\n"
        f"📅 Last 7 days: <b>{last_7d}</b>\n"
        f"🗓 Currently scheduled: <b>{scheduled}</b>"
    )
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=back_button())
