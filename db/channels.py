import time
from db import channels_col


async def add_channel(chat_id: int, title: str, username: str | None, owner_id: int):
    await channels_col.update_one(
        {"chat_id": chat_id},
        {
            "$set": {
                "chat_id": chat_id,
                "title": title,
                "username": username,
                "updated_at": time.time(),
            },
            "$setOnInsert": {"added_at": time.time()},
            "$addToSet": {"owners": owner_id},
        },
        upsert=True,
    )


async def remove_channel(chat_id: int):
    await channels_col.delete_one({"chat_id": chat_id})


async def get_channel(chat_id: int):
    return await channels_col.find_one({"chat_id": chat_id})


async def get_user_channels(owner_id: int):
    cursor = channels_col.find({"owners": owner_id})
    return [c async for c in cursor]


async def is_owner_of_channel(user_id: int, chat_id: int) -> bool:
    ch = await get_channel(chat_id)
    return bool(ch and user_id in ch.get("owners", []))
