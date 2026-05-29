# maxihome-ring

Ring camera battery monitoring dashboard. Collects battery level and power status every 15 minutes, displays interactive charts showing charge/drain cycles over time.

Part of the [maxihome](https://github.com/macsmax/maxihome-hub) ecosystem.

## Setup

1. Create `.env`:
```bash
cp .env.example .env
```

2. Authenticate with Ring (one-time, interactive):
```bash
docker compose run --rm ring-setup
```
This prompts for your Ring email, password, and 2FA code. The token is cached in a Docker volume and persists across restarts.

3. Start the dashboard:
```bash
docker compose up -d
```

4. Open http://localhost:8502

## Re-authenticating

If the token expires (Ring tokens last several months), run the setup again:
```bash
docker compose run --rm ring-setup
```

## Importing existing data

If you have CSV files from the old cron-based script, copy them into the data volume:
```bash
docker cp ring.csv maxihome-ring:/app/data/ring_front_door.csv
docker cp ring_garden.csv maxihome-ring:/app/data/ring_garden_cam.csv
```

CSV format: `timestamp,ac_power,battery_pct` (no header row)
