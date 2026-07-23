from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from db.channels import get_channel
from db.settings import get_settings, update_setting, toggle_bool
from db.users import set_state
from utils.keyboards import cancel_kb
from states import AWAITING_ADSGRAM_BLOCKID, AWAITING_ADSGRAM_DURATION
from config import ADSGRAM_MINIAPP_LINK


def adsgram_kb(settings: dict, chat_id: int):
    enabled = "ON ✅" if settings.get("adsgram_enabled") else "OFF"
    block_id = settings.get("adsgram_block_id") or "not set"
    days = settings.get("adsgram_revert_days", 7)
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(f"Adsgram: {enabled}", callback_data=f"ads:toggle:{chat_id}")],
            [InlineKeyboardButton(f"Block ID: {block_id}", callback_data=f"ads:blockid:{chat_id}")],
            [InlineKeyboardButton(f"Revert after: {days} day(s)", callback_data=f"ads:duration:{chat_id}")],
            [InlineKeyboardButton("« Back", callback_data="menu:settings")],
        ]
    )


def _intro(settings: dict) -> str:
    warn = "" if ADSGRAM_MINIAPP_LINK else (
        "\n\n⚠️ <code>ADSGRAM_MINIAPP_LINK</code> isn't set on the server yet, so this "
        "will stay off even if enabled here. See the README for the one-time Mini App setup."
    )
    return (
        "🎯 <b>Adsgram</b>\n\n"
        "When ON, any post <b>with at least one button</b> will have its button link(s) "
        "swapped for an Adsgram mini-app ad. The viewer sees the ad, then gets redirected "
        "to your real link automatically. After the revert duration, the button quietly "
        "switches back to the plain link — nothing else about the post changes."
        f"{warn}"
    )


async def adsgram_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    query = update.callback_query
    settings = await get_settings(chat_id)
    await query.edit_message_text(
        _intro(settings), parse_mode="HTML", reply_markup=adsgram_kb(settings, chat_id)
    )


async def adsgram_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = int(query.data.split(":")[2])
    await adsgram_menu(update, context, chat_id)


async def adsgram_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = int(query.data.split(":")[2])
    settings = await get_settings(chat_id)
    if not settings.get("adsgram_block_id") and not settings.get("adsgram_enabled"):
        await query.answer("Set a Block ID first.", show_alert=True)
        return
    await toggle_bool(chat_id, "adsgram_enabled")
    await query.answer()
    await adsgram_menu(update, context, chat_id)


async def adsgram_blockid_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = int(query.data.split(":")[2])
    await query.answer()
    await set_state(update.effective_user.id, AWAITING_ADSGRAM_BLOCKID, {"chat_id": chat_id})
    await query.message.reply_text(
        "🔑 Send your Adsgram <b>Block ID</b> (from your Adsgram account, numeric part only, "
        "no <code>bot-</code> prefix):",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )


async def handle_adsgram_blockid(update: Update, context: ContextTypes.DEFAULT_TYPE, state_data: dict):
    chat_id = state_data["chat_id"]
    block_id = update.message.text.strip()
    await update_setting(chat_id, "adsgram_block_id", block_id)
    await set_state(update.effective_user.id, None)
    await update.message.reply_text(f"✅ Block ID saved: <code>{block_id}</code>", parse_mode="HTML")


async def adsgram_duration_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = int(query.data.split(":")[2])
    await query.answer()
    await set_state(update.effective_user.id, AWAITING_ADSGRAM_DURATION, {"chat_id": chat_id})
    await query.message.reply_text(
        "🗓 After how many days should the ad link revert to the normal link? Send a number "
        "(e.g. <code>7</code>):",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )


async def handle_adsgram_duration(update: Update, context: ContextTypes.DEFAULT_TYPE, state_data: dict):
    chat_id = state_data["chat_id"]
    raw = update.message.text.strip()
    if not raw.isdigit() or int(raw) <= 0:
        await update.message.reply_text("Please send a positive whole number of days, e.g. 7")
        return
    await update_setting(chat_id, "adsgram_revert_days", int(raw))
    await set_state(update.effective_user.id, None)
    await update.message.reply_text(f"✅ Ads will revert to the normal link after {raw} day(s).")
