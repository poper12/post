from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI, DB_NAME

client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]

channels_col = db["channels"]
settings_col = db["settings"]
posts_col = db["posts"]
users_col = db["users"]
adredirects_col = db["adredirects"]


async def ensure_indexes():
    await channels_col.create_index("chat_id", unique=True)
    await settings_col.create_index("chat_id", unique=True)
    await posts_col.create_index("post_id", unique=True)
    await posts_col.create_index([("chat_id", 1), ("status", 1)])
    await users_col.create_index("user_id", unique=True)
    await adredirects_col.create_index("token", unique=True)
