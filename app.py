"""Ring Camera Battery Dashboard."""

import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

from ring_collector.scheduler import start_scheduler

load_dotenv()

st.set_page_config(
    page_title="Ring Battery Monitor",
    page_icon="🔋",
    layout="wide",
)

st.title("Ring Camera Battery Monitor")

DATA_DIR = Path(os.getenv("RING_DATA_DIR", "data"))
DEVICES = [d.strip() for d in os.getenv("RING_DEVICES", "Front Door,Garden Cam").split(",")]

# Check for auth token before starting collector
TOKEN_PATH = DATA_DIR / "ring_token.cache"
if not TOKEN_PATH.is_file():
    st.error("**Ring not authenticated.** Run the setup to authenticate:")
    st.code("docker compose run --rm ring-setup", language="bash")
    st.info("This will prompt for your Ring email, password, and 2FA code. Only needed once — the token is cached.")
    st.stop()

# Start background collector (only if authenticated)
start_scheduler()


def load_device_data(device_name: str) -> pd.DataFrame:
    safe_name = device_name.lower().replace(" ", "_")
    csv_path = DATA_DIR / f"ring_{safe_name}.csv"

    if not csv_path.exists():
        return pd.DataFrame(columns=["timestamp", "ac_power", "battery_pct"])

    df = pd.read_csv(
        csv_path,
        header=None,
        names=["timestamp", "ac_power", "battery_pct"],
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="mixed", dayfirst=False, errors="coerce", utc=True)
    df = df.dropna(subset=["timestamp"])
    df["timestamp"] = df["timestamp"].dt.tz_localize(None)
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


def normalize_ac_power(ac_power: int) -> int:
    """Normalize AC power values across device types."""
    # Stickup cams report 8=battery, 9=solar/wired
    if ac_power == 8:
        return 0
    elif ac_power == 9:
        return 1
    return ac_power


# Sidebar
with st.sidebar:
    st.header("Settings")
    days_back = st.slider("Days to show", min_value=1, max_value=90, value=30)
    auto_refresh = st.checkbox("Auto-refresh (60s)", value=True)
    if auto_refresh:
        st.markdown("*Page refreshes every 60 seconds*")

if auto_refresh:
    st.empty()
    import time
    # Streamlit native auto-rerun
    st.markdown(
        """<meta http-equiv="refresh" content="60">""",
        unsafe_allow_html=True,
    )

cutoff = pd.Timestamp.now() - timedelta(days=days_back)

# Overview metrics
cols = st.columns(len(DEVICES))
device_data = {}

for i, device_name in enumerate(DEVICES):
    df = load_device_data(device_name)
    device_data[device_name] = df

    with cols[i]:
        if df.empty:
            st.metric(device_name, "No data")
            continue

        latest = df.iloc[-1]
        battery = int(latest["battery_pct"])
        ac = normalize_ac_power(int(latest["ac_power"]))

        # Battery status icon
        if battery > 70:
            icon = "🟢"
        elif battery > 30:
            icon = "🟡"
        else:
            icon = "🔴"

        power_status = "⚡ Wired" if ac > 0 else "🔋 Battery"

        # Calculate drain rate (last 24h)
        recent = df[df["timestamp"] > pd.Timestamp.now() - timedelta(hours=24)]
        if len(recent) > 1:
            drain = recent.iloc[0]["battery_pct"] - recent.iloc[-1]["battery_pct"]
            delta_str = f"{drain:+.0f}% / 24h"
        else:
            delta_str = None

        st.metric(
            f"{icon} {device_name}",
            f"{battery}%",
            delta=delta_str,
            delta_color="inverse",
        )
        st.caption(power_status)

st.divider()

# Charts for each device
for device_name in DEVICES:
    df = device_data[device_name]
    if df.empty:
        st.warning(f"**{device_name}** — No data yet. Collector will start populating data every {os.getenv('RING_INTERVAL_MINUTES', '15')} minutes.")
        continue

    df_filtered = df[df["timestamp"] > cutoff].copy()
    if df_filtered.empty:
        st.info(f"**{device_name}** — No data in the last {days_back} days.")
        continue

    df_filtered["ac_power_norm"] = df_filtered["ac_power"].apply(normalize_ac_power)

    st.subheader(f"📷 {device_name}")

    fig = go.Figure()

    # Battery percentage
    fig.add_trace(go.Scatter(
        x=df_filtered["timestamp"],
        y=df_filtered["battery_pct"],
        name="Battery %",
        line=dict(color="#22c55e", width=2),
        yaxis="y",
    ))

    # AC power as filled area on secondary axis
    fig.add_trace(go.Scatter(
        x=df_filtered["timestamp"],
        y=df_filtered["ac_power_norm"],
        name="AC Power",
        fill="tozeroy",
        line=dict(color="#f97316", width=1),
        opacity=0.3,
        yaxis="y2",
    ))

    fig.update_layout(
        height=350,
        margin=dict(t=10, b=10),
        yaxis=dict(title="Battery %", range=[0, 100], side="left"),
        yaxis2=dict(title="AC Power", range=[0, 2], side="right", overlaying="y"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        hovermode="x unified",
    )

    st.plotly_chart(fig, use_container_width=True)

    # Stats
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Min Battery", f"{df_filtered['battery_pct'].min():.0f}%")
    col2.metric("Max Battery", f"{df_filtered['battery_pct'].max():.0f}%")
    col3.metric("Readings", f"{len(df_filtered):,}")

    # Time on battery vs wired
    on_battery = (df_filtered["ac_power_norm"] == 0).sum()
    on_wired = (df_filtered["ac_power_norm"] > 0).sum()
    total = on_battery + on_wired
    if total > 0:
        col4.metric("Time on Battery", f"{on_battery / total * 100:.0f}%")

st.divider()

# Import existing data notice
with st.expander("Import existing CSV data"):
    st.markdown("""
If you have existing Ring CSV data from the old script, place it in the `data/` directory:
- `data/ring_front_door.csv` for "Front Door"
- `data/ring_garden_cam.csv` for "Garden Cam"

CSV format: `timestamp,ac_power,battery_pct` (no header row)

Example: `2024-06-15 14:30:00,0,85`
""")

# Footer
st.caption(f"Collecting every {os.getenv('RING_INTERVAL_MINUTES', '15')} min | Data dir: {DATA_DIR}")
