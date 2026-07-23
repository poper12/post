import time
import datetime

from db.adredirects import create_redirect, delete_redirects_for_post
from db.posts import get_post, update_content
from config import ADSGRAM_MINIAPP_LINK


async def wrap_buttons_for_adsgram(post_id: str, content: dict, settings: dict) -> dict:
    """If Adsgram is enabled and the post has buttons, replace each button's URL with
    a mini-app link that shows an ad before redirecting to the real URL. Only ever
    touches posts that already have buttons — posts without buttons are left alone."""
    buttons = content.get("buttons") or []
    if not buttons or not settings.get("adsgram_enabled") or not settings.get("adsgram_block_id"):
        return content
    if not ADSGRAM_MINIAPP_LINK:
        return content  # not configured on the server side, skip silently

    block_id = settings["adsgram_block_id"]
    changed = False
    new_rows = []
    for row in buttons:
        new_row = []
        for btn in row:
            if btn.get("original_url"):
                new_row.append(btn)  # already wrapped
                continue
            token = await create_redirect(btn["url"], block_id, post_id)
            new_row.append(
                {
                    "text": btn["text"],
                    "original_url": btn["url"],
                    "url": f"{ADSGRAM_MINIAPP_LINK}?startapp={token}",
                }
            )
            changed = True
        new_rows.append(new_row)

    if changed:
        content["buttons"] = new_rows
        content["adsgram_wrapped_at"] = time.time()
        await update_content(post_id, content)
    return content


def revert_due_at(settings: dict) -> float:
    days = settings.get("adsgram_revert_days", 7)
    return (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=days)).timestamp()


def build_reverted_buttons(content: dict):
    """Return button rows with original (non-ad) URLs restored."""
    buttons = content.get("buttons") or []
    reverted = []
    any_wrapped = False
    for row in buttons:
        new_row = []
        for btn in row:
            if btn.get("original_url"):
                any_wrapped = True
                new_row.append({"text": btn["text"], "url": btn["original_url"]})
            else:
                new_row.append(btn)
        reverted.append(new_row)
    return reverted, any_wrapped
