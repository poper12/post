import datetime
import pytz

from telegram import Update
from telegram.ext import ContextTypes

from db.channels import get_user_channels, get_channel
from db.posts import get_scheduled_posts, get_post, cancel_schedule
from utils.keyboards import channel_list_kb, scheduled_list_kb, scheduled_view_kb
from utils.scheduler import cancel_job
from utils.formatting import content_preview_text
from config import TIMEZONE

TZ = pytz.timezone(TIMEZONE)


async def scheduled_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    channels = await get_user_channels(user.id)
    if not channels:
        await query.edit_message_text("No channels connected yet.")
        return
    if len(channels) == 1:
        await _show_scheduled(query, channels[0]["chat_id"])
    else:
        await query.edit_message_text(
            "Pick a channel to view scheduled posts:",
            reply_markup=channel_list_kb(channels, "sched:pick"),
        )


async def scheduled_pick_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = int(query.data.split(":")[2])
    await _show_scheduled(query, chat_id)


async def _show_scheduled(query, chat_id):
    posts = await get_scheduled_posts(chat_id)
    if not posts:
        await query.edit_message_text("No scheduled posts for this channel.", reply_markup=scheduled_list_kb([]))
        return
    await query.edit_message_text(
        f"🗓 {len(posts)} scheduled post(s):", reply_markup=scheduled_list_kb(posts)
    )


async def scheduled_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    post_id = query.data.split(":")[2]
    post = await get_post(post_id)
    if not post:
        await query.edit_message_text("Post not found.")
        return
    when = datetime.datetime.fromtimestamp(post["scheduled_at"], tz=pytz.utc).astimezone(TZ)
    snippet = content_preview_text(post["content"])
    await query.edit_message_text(
        f"{snippet}\n\n🗓 Scheduled for: <b>{when.strftime('%Y-%m-%d %H:%M')} {TIMEZONE}</b>",
        parse_mode="HTML",
        reply_markup=scheduled_view_kb(post_id),
    )


async def scheduled_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    post_id = query.data.split(":")[2]
    post = await get_post(post_id)
    if post:
        cancel_job(context.job_queue, post_id)
        await cancel_schedule(post_id)
    await query.answer("Schedule cancelled")
    await query.edit_message_text("❌ Schedule cancelled. The draft is kept — create a new post to resend it.")
