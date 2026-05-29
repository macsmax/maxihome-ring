"""Interactive authentication for Ring. Run once to generate token cache."""

import asyncio
import getpass
import json
import os
from pathlib import Path

from ring_doorbell import Auth, Requires2FAError

TOKEN_CACHE = Path(os.getenv("RING_DATA_DIR", "data")) / "ring_token.cache"


def token_updated(token: dict):
    TOKEN_CACHE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_CACHE.write_text(json.dumps(token))


async def authenticate():
    user_agent = "maxihome-ring/1.0"
    username = input("Ring email: ")
    password = getpass.getpass("Ring password: ")

    auth = Auth(user_agent, None, token_updated)
    try:
        await auth.async_fetch_token(username, password)
    except Requires2FAError:
        code = input("2FA code: ")
        await auth.async_fetch_token(username, password, code)

    print(f"Token cached at: {TOKEN_CACHE}")
    await auth.async_close()


if __name__ == "__main__":
    asyncio.run(authenticate())
