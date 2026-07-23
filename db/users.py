from db import users_col


async def upsert_user(user_id: int, username: str | None):
    await users_col.update_one(
        {"user_id": user_id},
        {"$set": {"user_id": user_id, "username": username}},
        upsert=True,
    )


async def set_selected_channel(user_id: int, chat_id: int):
    await users_col.update_one(
        {"user_id": user_id}, {"$set": {"selected_channel": chat_id}}, upsert=True
    )


async def get_selected_channel(user_id: int):
    doc = await users_col.find_one({"user_id": user_id})
    return doc.get("selected_channel") if doc else None


async def set_state(user_id: int, state: str | None, extra: dict | None = None):
    payload = {"state": state}
    if extra is not None:
        payload["state_data"] = extra
    await users_col.update_one({"user_id": user_id}, {"$set": payload}, upsert=True)


async def get_state(user_id: int):
    doc = await users_col.find_one({"user_id": user_id})
    if not doc:
        return None, {}
    return doc.get("state"), doc.get("state_data", {})
