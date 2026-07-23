import datetime
from telegram.ext import ContextTypes

from db.posts import (
    get_post,
    get_all_scheduled,
    get_posts_pending_revert,
    mark_adsgram_reverted,
    update_content,
)
from db.adredirects import delete_redirects_for_post
from utils.sender import send_post_to_channel


async def _fire_scheduled_post(context: ContextTypes.DEFAULT_TYPE):
    post_id = context.job.data["post_id"]
    post = await get_post(post_id)
    if not post or post.get("status") != "scheduled":
        return
    try:
        await send_post_to_channel(context.bot, post, context.job_queue)
    except Exception as e:
        try:
            await context.bot.send_message(
                post["owner_id"],
                f"⚠️ Failed to send scheduled post to {post['chat_id']}: {e}",
            )
        except Exception:
            pass


def schedule_job(job_queue, post_id: str, when: datetime.datetime):
    job_queue.run_once(
        _fire_scheduled_post,
        when=when,
        data={"post_id": post_id},
        name=f"post:{post_id}",
    )


def cancel_job(job_queue, post_id: str):
    for job in job_queue.get_jobs_by_name(f"post:{post_id}"):
        job.schedule_removal()


async def restore_scheduled_jobs(job_queue):
    """Call once on startup so scheduled posts survive a Render restart/redeploy."""
    now = datetime.datetime.now(datetime.timezone.utc)
    for post in await get_all_scheduled():
        when_ts = post.get("scheduled_at")
        if not when_ts:
            continue
        when = datetime.datetime.fromtimestamp(when_ts, tz=datetime.timezone.utc)
        if when <= now:
            when = now + datetime.timedelta(seconds=5)
        schedule_job(job_queue, post["post_id"], when)


# ---------- Adsgram revert jobs ----------

async def _fire_adsgram_revert(context: ContextTypes.DEFAULT_TYPE):
    from utils.adsgram import build_reverted_buttons
    from utils.formatting import buttons_to_markup

    post_id = context.job.data["post_id"]
    post = await get_post(post_id)
    if not post or post.get("adsgram_reverted"):
        return

    reverted_rows, any_wrapped = build_reverted_buttons(post["content"])
    if not any_wrapped:
        await mark_adsgram_reverted(post_id)
        return

    try:
        await context.bot.edit_message_reply_markup(
            chat_id=post["chat_id"],
            message_id=post["message_id"],
            reply_markup=buttons_to_markup(reverted_rows),
        )
    except Exception as e:
        try:
            await context.bot.send_message(
                post["owner_id"],
                f"⚠️ Couldn't revert Adsgram link on a post in {post['chat_id']}: {e}",
            )
        except Exception:
            pass
        return

    content = post["content"]
    content["buttons"] = reverted_rows
    await update_content(post_id, content)
    await mark_adsgram_reverted(post_id)
    await delete_redirects_for_post(post_id)


def schedule_revert_job(job_queue, post_id: str, when: datetime.datetime):
    job_queue.run_once(
        _fire_adsgram_revert,
        when=when,
        data={"post_id": post_id},
        name=f"revert:{post_id}",
    )


def cancel_revert_job(job_queue, post_id: str):
    for job in job_queue.get_jobs_by_name(f"revert:{post_id}"):
        job.schedule_removal()


async def restore_revert_jobs(job_queue):
    now = datetime.datetime.now(datetime.timezone.utc)
    for post in await get_posts_pending_revert():
        when_ts = post.get("adsgram_revert_at")
        if not when_ts:
            continue
        when = datetime.datetime.fromtimestamp(when_ts, tz=datetime.timezone.utc)
        if when <= now:
            when = now + datetime.timedelta(seconds=10)
        schedule_revert_job(job_queue, post["post_id"], when)
