from telegram import Update, MessageOriginChannel
from telegram.ext import ContextTypes

from db.users import get_state, set_state
from handlers.channels import handle_forwarded_channel_message
from handlers.create_post import (
    handle_new_post_content,
    handle_reedit_content,
    handle_button_text,
    handle_button_url,
    handle_schedule_time,
)
from handlers.edit_post import handle_edit_text
from handlers.adsgram import (
    handle_adsgram_blockid,
    handle_adsgram_duration,
)
from states import (
    AWAITING_POST_CONTENT,
    AWAITING_REEDIT_CONTENT,
    AWAITING_BUTTON_TEXT,
    AWAITING_BUTTON_URL,
    AWAITING_SCHEDULE_TIME,
    AWAITING_EDIT_TEXT,
    AWAITING_ADSGRAM_BLOCKID,
    AWAITING_ADSGRAM_DURATION,
)

STATE_HANDLERS = {
    AWAITING_POST_CONTENT: handle_new_post_content,
    AWAITING_REEDIT_CONTENT: handle_reedit_content,
    AWAITING_BUTTON_TEXT: handle_button_text,
    AWAITING_BUTTON_URL: handle_button_url,
    AWAITING_SCHEDULE_TIME: handle_schedule_time,
    AWAITING_EDIT_TEXT: handle_edit_text,
    AWAITING_ADSGRAM_BLOCKID: handle_adsgram_blockid,
    AWAITING_ADSGRAM_DURATION: handle_adsgram_duration,
}


async def route_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    message = update.effective_message

    if (
        message.forward_origin
        and isinstance(message.forward_origin, MessageOriginChannel)
    ):
        handled = await handle_forwarded_channel_message(update, context)
        if handled:
            return

    user = update.effective_user
    if not user:
        return

    state, state_data = await get_state(user.id)

    if not state:
        return

    handler = STATE_HANDLERS.get(state)

    if handler:
        await handler(update, context, state_data)


async def cancel_op(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Cancelled")
    await set_state(update.effective_user.id, None)
    await query.edit_message_text("❌ Cancelled.")


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await set_state(update.effective_user.id, None)
    await update.message.reply_text("❌ Cancelled current action.")
