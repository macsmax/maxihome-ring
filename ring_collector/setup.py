"""First-time setup: authenticate with Ring and cache the token.

Skips if a valid token already exists. Run interactively:
    docker compose run --rm ring-setup
"""

import asyncio
import getpass
import json
import os
import sys
from pathlib import Path

from ring_doorbell import Auth, AuthenticationError, Requires2FAError, Ring

DATA_DIR = Path(os.getenv("RING_DATA_DIR", "/app/data"))
TOKEN_CACHE = DATA_DIR / "ring_token.cache"


def token_updated(token: dict):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_CACHE.write_text(json.dumps(token))


async def verify_token() -> bool:
    """Check if the cached token is still valid."""
    if not TOKEN_CACHE.is_file():
        return False
    try:
        auth = Auth("ring_doorbell/0.9", json.loads(TOKEN_CACHE.read_text()), token_updated)
        ring = Ring(auth)
        await ring.async_create_session()
        await auth.async_close()
        return True
    except (AuthenticationError, Exception):
        return False


async def authenticate():
    """Interactive authentication flow."""
    user_agent = "ring_doorbell/0.9"

    print("=" * 50)
    print("  Ring Camera Authentication Setup")
    print("=" * 50)
    print()

    username = input("Ring email: ").strip()
    password = getpass.getpass("Ring password: ")

    auth = Auth(user_agent, None, token_updated)
    try:
        await auth.async_fetch_token(username, password)
    except Requires2FAError:
        print()
        code = input("2FA code (check your phone/email): ").strip()
        await auth.async_fetch_token(username, password, code)

    # Verify it works
    ring = Ring(auth)
    await ring.async_create_session()
    await ring.async_update_data()

    devices = ring.devices()
    all_devices = list(devices.doorbots) + list(devices.stickup_cams) + list(devices.chimes)

    print()
    print("Authenticated successfully!")
    print(f"Token saved to: {TOKEN_CACHE}")
    print()
    print("Devices found:")
    for d in all_devices:
        battery = getattr(d, "battery_life", None)
        print(f"  - {d.name} (battery: {battery}%)")

    await auth.async_close()


async def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if await verify_token():
        print(f"Token already valid at {TOKEN_CACHE} — skipping auth.")
        sys.exit(0)

    # If stdin is not a TTY, can't do interactive auth
    if not sys.stdin.isatty():
        if TOKEN_CACHE.is_file():
            print(f"Token exists at {TOKEN_CACHE} but may be expired.")
            print("Run interactively to re-authenticate:")
            print("  docker compose run --rm ring-setup")
            sys.exit(0)
        else:
            print("No token found. Run interactively to authenticate:")
            print("  docker compose run --rm ring-setup")
            sys.exit(1)

    await authenticate()


if __name__ == "__main__":
    asyncio.run(main())
