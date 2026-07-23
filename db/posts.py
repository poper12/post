import time
import uuid
from db import posts_col


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


async def create_draft(owner_id: int, chat_id: int, content: dict) -> str:
    post_id = _new_id()
    await posts_col.insert_one(
        {
            "post_id": post_id,
            "owner_id": owner_id,
            "chat_id": chat_id,
            "content": content,
            "status": "draft",
            "created_at": time.time(),
        }
    )
    return post_id


async def get_post(post_id: str):
    return await posts_col.find_one({"post_id": post_id})


async def update_content(post_id: str, content: dict):
    await posts_col.update_one({"post_id": post_id}, {"$set": {"content": content}})


async def add_button(post_id: str, text: str, url: str):
    post = await get_post(post_id)
    buttons = post["content"].get("buttons", [])
    buttons.append([{"text": text, "url": url}])
    await posts_col.update_one(
        {"post_id": post_id}, {"$set": {"content.buttons": buttons}}
    )


async def clear_buttons(post_id: str):
    await posts_col.update_one({"post_id": post_id}, {"$set": {"content.buttons": []}})


async def mark_sent(post_id: str, message_id: int):
    await posts_col.update_one(
        {"post_id": post_id},
        {"$set": {"status": "sent", "message_id": message_id, "sent_at": time.time()}},
    )


async def set_adsgram_revert_at(post_id: str, revert_at: float):
    await posts_col.update_one(
        {"post_id": post_id}, {"$set": {"adsgram_revert_at": revert_at, "adsgram_reverted": False}}
    )


async def mark_adsgram_reverted(post_id: str):
    await posts_col.update_one(
        {"post_id": post_id}, {"$set": {"adsgram_reverted": True}, "$unset": {"adsgram_revert_at": ""}}
    )


async def get_posts_pending_revert():
    cursor = posts_col.find(
        {"status": "sent", "adsgram_revert_at": {"$exists": True}, "adsgram_reverted": {"$ne": True}}
    )
    return [p async for p in cursor]


async def schedule_post(post_id: str, when_ts: float):
    await posts_col.update_one(
        {"post_id": post_id},
        {"$set": {"status": "scheduled", "scheduled_at": when_ts}},
    )


async def cancel_schedule(post_id: str):
    await posts_col.update_one({"post_id": post_id}, {"$set": {"status": "draft"}})


async def delete_post(post_id: str):
    await posts_col.delete_one({"post_id": post_id})


async def get_scheduled_posts(chat_id: int):
    cursor = posts_col.find({"chat_id": chat_id, "status": "scheduled"}).sort(
        "scheduled_at", 1
    )
    return [p async for p in cursor]


async def get_all_scheduled():
    cursor = posts_col.find({"status": "scheduled"})
    return [p async for p in cursor]


async def get_sent_posts(chat_id: int, limit: int = 15):
    cursor = (
        posts_col.find({"chat_id": chat_id, "status": "sent"})
        .sort("sent_at", -1)
        .limit(limit)
    )
    return [p async for p in cursor]
