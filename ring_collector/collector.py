"""Collect Ring camera battery data using the ring_doorbell library."""

import asyncio
import csv
import json
import os
import logging
from datetime import datetime
from pathlib import Path

from ring_doorbell import Auth, AuthenticationError, Requires2FAError, Ring

logger = logging.getLogger(__name__)

TOKEN_CACHE = Path(os.getenv("RING_DATA_DIR", "data")) / "ring_token.cache"


def token_updated(token: dict):
    TOKEN_CACHE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_CACHE.write_text(json.dumps(token))


async def get_ring_session() -> Ring:
    user_agent = "maxihome-ring/1.0"

    if TOKEN_CACHE.is_file():
        auth = Auth(user_agent, json.loads(TOKEN_CACHE.read_text()), token_updated)
        ring = Ring(auth)
        try:
            await ring.async_create_session()
            return ring
        except AuthenticationError:
            logger.warning("Cached token expired, need re-authentication")
            raise
    else:
        raise FileNotFoundError(
            f"No token cache at {TOKEN_CACHE}. "
            "Run 'python -m ring_collector.auth' to authenticate first."
        )


def get_csv_path(device_name: str) -> Path:
    data_dir = Path(os.getenv("RING_DATA_DIR", "data"))
    data_dir.mkdir(parents=True, exist_ok=True)
    safe_name = device_name.lower().replace(" ", "_")
    return data_dir / f"ring_{safe_name}.csv"


async def collect_once():
    """Collect battery data from all configured Ring devices."""
    ring = await get_ring_session()
    await ring.async_update_data()

    devices = ring.devices()
    all_devices = (
        devices.get("doorbots", [])
        + devices.get("authorized_doorbots", [])
        + devices.get("stickup_cams", [])
    )

    target_names = [
        n.strip()
        for n in os.getenv("RING_DEVICES", "Front Door,Garden Cam").split(",")
    ]

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    collected = []

    for device in all_devices:
        name = device.name
        if name not in target_names:
            continue

        battery_pct = device.battery_life
        # ac_power can be various values depending on model
        # Doorbells: 0=battery, 1=wired
        # Stickup cams: 8=battery, 9=solar/wired
        ac_power_raw = getattr(device, "existing_doorbell_type", None)
        if ac_power_raw is None:
            ac_power_raw = 0

        csv_path = get_csv_path(name)
        with open(csv_path, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([now, ac_power_raw, battery_pct])

        collected.append({"device": name, "battery": battery_pct, "ac_power": ac_power_raw})
        logger.info(f"Collected: {name} — battery={battery_pct}%, ac_power={ac_power_raw}")

    await ring._auth.async_close()
    return collected


def collect_sync():
    """Synchronous wrapper for the collector."""
    return asyncio.run(collect_once())
