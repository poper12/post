from db import settings_col
from config import DEFAULT_SETTINGS


async def get_settings(chat_id: int) -> dict:
    doc = await settings_col.find_one({"chat_id": chat_id})
    if not doc:
        doc = {"chat_id": chat_id, **DEFAULT_SETTINGS}
        await settings_col.insert_one(doc)
    else:
        # backfill any new default keys added in later versions
        changed = False
        for k, v in DEFAULT_SETTINGS.items():
            if k not in doc:
                doc[k] = v
                changed = True
        if changed:
            await settings_col.update_one({"chat_id": chat_id}, {"$set": doc})
    return doc


async def update_setting(chat_id: int, key: str, value):
    await settings_col.update_one(
        {"chat_id": chat_id}, {"$set": {key: value}}, upsert=True
    )


async def cycle_parse_mode(chat_id: int) -> str:
    order = ["HTML", "Markdown", "None"]
    s = await get_settings(chat_id)
    current = s.get("parse_mode", "HTML")
    nxt = order[(order.index(current) + 1) % len(order)]
    await update_setting(chat_id, "parse_mode", nxt)
    return nxt


async def toggle_bool(chat_id: int, key: str) -> bool:
    s = await get_settings(chat_id)
    new_val = not s.get(key, False)
    await update_setting(chat_id, key, new_val)
    return new_val
