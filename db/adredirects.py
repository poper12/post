import time
import secrets

from db import adredirects_col


def _new_token() -> str:
    return secrets.token_urlsafe(9)  # A-Za-z0-9_- only, matches Telegram's startapp charset


async def create_redirect(target_url: str, block_id: str, post_id: str) -> str:
    token = _new_token()
    await adredirects_col.insert_one(
        {
            "token": token,
            "target_url": target_url,
            "block_id": block_id,
            "post_id": post_id,
            "created_at": time.time(),
        }
    )
    return token


async def get_redirect(token: str):
    return await adredirects_col.find_one({"token": token})


async def delete_redirects_for_post(post_id: str):
    await adredirects_col.delete_many({"post_id": post_id})
