from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatMemberStatus

from db.users import upsert_user, get_selected_channel, set_selected_channel
from db.channels import add_channel, get_user_channels
from utils.keyboards import main_menu

WELCOME = (
    "Here you can create rich posts, view stats and accomplish other tasks.\n\n"
    "Add me as an admin to your channel first (with post/edit/delete rights), "
    "then use <b>Channels ➜ Add Channel</b> to connect it."
)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await upsert_user(user.id, user.username)
    channels = await get_user_channels(user.id)

    if not channels:
        await update.message.reply_text(
            "👋 Welcome! You don't have any connected channels yet.\n\n"
            "1️⃣ Add me as <b>admin</b> in your channel\n"
            "2️⃣ Forward any message from that channel here, or tap Add Channel below\n\n"
            "Then you can create, schedule and manage posts right from this chat.",
            parse_mode="HTML",
            reply_markup=main_menu(),
        )
        return

    selected = await get_selected_channel(user.id)
    if not selected:
        await set_selected_channel(user.id, channels[0]["chat_id"])

    await update.message.reply_text(WELCOME, parse_mode="HTML", reply_markup=main_menu())


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(WELCOME, parse_mode="HTML", reply_markup=main_menu())


async def on_bot_added_as_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fires when the bot's own membership status changes in a chat (added/promoted/removed)."""
    cmu = update.my_chat_member
    if cmu.chat.type not in ("channel", "supergroup"):
        return

    new_status = cmu.new_chat_member.status
    adder = cmu.from_user

    if new_status in (ChatMemberStatus.ADMINISTRATOR,):
        await add_channel(
            chat_id=cmu.chat.id,
            title=cmu.chat.title,
            username=cmu.chat.username,
            owner_id=adder.id,
        )
        try:
            await context.bot.send_message(
                adder.id,
                f"✅ Connected channel <b>{cmu.chat.title}</b>. "
                f"Use /start to open the menu.",
                parse_mode="HTML",
            )
        except Exception:
            pass  # user may not have started the bot in DM yet
