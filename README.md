# maxihome-ring

Ring camera battery monitoring dashboard. Collects battery level and power status every 15 minutes, displays interactive charts showing charge/drain cycles over time.

Part of the [maxihome](https://github.com/macsmax/maxihome-hub) ecosystem.

## Setup

1. Install and authenticate the Ring CLI:
```bash
pip install ring-doorbell
ring-doorbell --auth
```

2. Generate a token cache:
```bash
python -m ring_collector.auth
```

3. Create `.env`:
```bash
cp .env.example .env
```

4. Run:
```bash
docker compose up -d
```

5. Open http://localhost:8502

## Importing existing data

If you have CSV files from the old script, place them in the `data/` volume:
- Format: `timestamp,ac_power,battery_pct` (no header)
- Naming: `ring_front_door.csv`, `ring_garden_cam.csv`
