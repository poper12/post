import logging
import json

from aiohttp import web
from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ChatMemberHandler,
    filters,
)

from config import BOT_TOKEN, WEBHOOK_URL, WEBHOOK_PATH, PORT, ADSGRAM_LANDING_ROUTE
from db import ensure_indexes
from db.adredirects import get_redirect
from utils.scheduler import restore_scheduled_jobs, restore_revert_jobs
from utils.miniapp_page import ADSGRAM_PAGE_HTML

from handlers.start import start_command, show_main_menu, on_bot_added_as_admin
from handlers.channels import (
    channels_menu,
    channel_view,
    channel_remove,
    channel_add_prompt,
)
from handlers.create_post import (
    create_post_entry,
    create_pick_channel,
    post_send_now,
    post_schedule_prompt,
    post_add_button_prompt,
    post_clear_buttons,
    post_reedit,
    post_cancel,
)
from handlers.scheduled import (
    scheduled_menu,
    scheduled_pick_channel,
    scheduled_view,
    scheduled_cancel,
)
from handlers.edit_post import (
    edit_menu,
    edit_pick_channel,
    edit_view,
    edit_text_prompt,
    edit_delete,
)
from handlers.stats import stats_menu, stats_pick_channel
from handlers.settings import settings_menu, settings_pick_channel, toggle_setting
from handlers.adsgram import (
    adsgram_open,
    adsgram_toggle,
    adsgram_blockid_prompt,
    adsgram_duration_prompt,
)
from handlers.router import route_message, cancel_op, cancel_command

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


async def post_init(application: Application):
    await ensure_indexes()
    await restore_scheduled_jobs(application.job_queue)
    await restore_revert_jobs(application.job_queue)
    logger.info("Bot initialized: indexes ensured, scheduled + revert jobs restored.")


def build_application() -> Application:
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

    # Commands
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("cancel", cancel_command))

    # Main menu
    app.add_handler(CallbackQueryHandler(show_main_menu, pattern="^menu:root$"))
    app.add_handler(CallbackQueryHandler(create_post_entry, pattern="^menu:create$"))
    app.add_handler(CallbackQueryHandler(scheduled_menu, pattern="^menu:scheduled$"))
    app.add_handler(CallbackQueryHandler(edit_menu, pattern="^menu:edit$"))
    app.add_handler(CallbackQueryHandler(stats_menu, pattern="^menu:stats$"))
    app.add_handler(CallbackQueryHandler(settings_menu, pattern="^menu:settings$"))
    app.add_handler(CallbackQueryHandler(channels_menu, pattern="^menu:channels$"))

    # Create post flow
    app.add_handler(CallbackQueryHandler(create_pick_channel, pattern="^create:pick:"))
    app.add_handler(CallbackQueryHandler(post_send_now, pattern="^post:send:"))
    app.add_handler(CallbackQueryHandler(post_schedule_prompt, pattern="^post:schedule:"))
    app.add_handler(CallbackQueryHandler(post_add_button_prompt, pattern="^post:addbtn:"))
    app.add_handler(CallbackQueryHandler(post_clear_buttons, pattern="^post:clearbtn:"))
    app.add_handler(CallbackQueryHandler(post_reedit, pattern="^post:reedit:"))
    app.add_handler(CallbackQueryHandler(post_cancel, pattern="^post:cancel:"))

    # Scheduled posts
    app.add_handler(CallbackQueryHandler(scheduled_pick_channel, pattern="^sched:pick:"))
    app.add_handler(CallbackQueryHandler(scheduled_view, pattern="^sched:view:"))
    app.add_handler(CallbackQueryHandler(scheduled_cancel, pattern="^sched:cancel:"))

    # Edit sent posts
    app.add_handler(CallbackQueryHandler(edit_pick_channel, pattern="^edit:pick:"))
    app.add_handler(CallbackQueryHandler(edit_view, pattern="^edit:view:"))
    app.add_handler(CallbackQueryHandler(edit_text_prompt, pattern="^edit:text:"))
    app.add_handler(CallbackQueryHandler(edit_delete, pattern="^edit:delete:"))

    # Stats
    app.add_handler(CallbackQueryHandler(stats_pick_channel, pattern="^stats:pick:"))

    # Channel management
    app.add_handler(CallbackQueryHandler(channel_view, pattern="^ch:view:"))
    app.add_handler(CallbackQueryHandler(channel_remove, pattern="^ch:remove:"))
    app.add_handler(CallbackQueryHandler(channel_add_prompt, pattern="^ch:add$"))

    # Settings
    app.add_handler(CallbackQueryHandler(settings_pick_channel, pattern="^settings:pick:"))
    app.add_handler(CallbackQueryHandler(toggle_setting, pattern="^set:"))

    # Adsgram
    app.add_handler(CallbackQueryHandler(adsgram_open, pattern="^ads:open:"))
    app.add_handler(CallbackQueryHandler(adsgram_toggle, pattern="^ads:toggle:"))
    app.add_handler(CallbackQueryHandler(adsgram_blockid_prompt, pattern="^ads:blockid:"))
    app.add_handler(CallbackQueryHandler(adsgram_duration_prompt, pattern="^ads:duration:"))

    # Generic cancel
    app.add_handler(CallbackQueryHandler(cancel_op, pattern="^op:cancel$"))

    # Bot promoted/demoted/added in a channel
    app.add_handler(
        ChatMemberHandler(on_bot_added_as_admin, ChatMemberHandler.MY_CHAT_MEMBER)
    )

    # Catch-all message router (text / photo / video / document, private chats only)
    app.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE & ~filters.COMMAND & (filters.TEXT | filters.PHOTO | filters.VIDEO | filters.Document.ALL),
            route_message,
        )
    )

    return app


async def handle_webhook(request: web.Request):
    app: Application = request.app["ptb_app"]
    try:
        data = await request.json()
    except Exception:
        return web.Response(status=400, text="bad request")
    update = Update.de_json(data, app.bot)
    await app.process_update(update)
    return web.Response(text="ok")


async def handle_ads_page(request: web.Request):
    return web.Response(text=ADSGRAM_PAGE_HTML, content_type="text/html")


async def handle_resolve(request: web.Request):
    token = request.match_info.get("token", "")
    doc = await get_redirect(token)
    if not doc:
        return web.json_response({"error": "not found"}, status=404)
    return web.json_response({"target_url": doc["target_url"], "block_id": doc.get("block_id")})


async def handle_health(request: web.Request):
    return web.Response(text="ok")


async def run_webhook_server(app: Application):
    await app.initialize()
    if app.post_init:
        await app.post_init(app)
    await app.start()

    webapp = web.Application()
    webapp["ptb_app"] = app
    webapp.add_routes(
        [
            web.post(WEBHOOK_PATH, handle_webhook),
            web.get(ADSGRAM_LANDING_ROUTE, handle_ads_page),
            web.get("/resolve/{token}", handle_resolve),
            web.get("/healthz", handle_health),
        ]
    )

    runner = web.AppRunner(webapp)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    full_url = WEBHOOK_URL.rstrip("/") + WEBHOOK_PATH
    await app.bot.set_webhook(url=full_url, drop_pending_updates=True)
    logger.info(f"Webhook server listening on 0.0.0.0:{PORT}, webhook set to {full_url}")

    # Keep the event loop alive
    import asyncio

    await asyncio.Event().wait()


def main():
    app = build_application()

    if WEBHOOK_URL:
        import asyncio

        asyncio.run(run_webhook_server(app))
    else:
        logger.warning(
            "WEBHOOK_URL not set — falling back to polling mode. "
            "Adsgram mini-app links will not be reachable in this mode."
        )
        app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
