# pi-dewpoint

Using a Raspberry Pi Zero W to set the color of a Govee light bulb to match the current dew point.

## How it works

1. **Fetch dew point** — calls the [Open-Meteo](https://open-meteo.com/) API (free, no API key required) for the configured location and returns the current dew point in °F.
2. **Map to color** — linearly interpolates the dew point across a color scale from blue (dry) to red (oppressive).

   | Dew point | Feel | Color |
   |-----------|------|-------|
   | ≤ 35 °F | Dry / very comfortable | 🔵 Blue |
   | 50 °F | Comfortable | 🩵 Cyan |
   | 60 °F | Pleasant | 🟢 Green |
   | 65 °F | Getting humid | 🟡 Yellow |
   | 70 °F | Uncomfortable | 🟠 Orange |
   | ≥ 75 °F | Oppressive | 🔴 Red |

3. **Set the bulb** — sends the RGB color to the Govee light via the [Govee Developer API](https://govee-public.s3.amazonaws.com/developer-docs/GoveeAPIReference.pdf).

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

| Variable | Description |
|----------|-------------|
| `LATITUDE` | Latitude of the location to monitor |
| `LONGITUDE` | Longitude of the location to monitor |
| `GOVEE_API_KEY` | Govee Developer API key (Govee app → Profile → About Us → Apply for API Key) |
| `GOVEE_DEVICE_ID` | Govee device ID (visible in the Govee app under device settings) |
| `GOVEE_MODEL` | Govee device model (e.g. `H6159`) |

### 3. Run

```bash
python dewpoint.py
```

### Run on a schedule (cron)

To update the bulb every 15 minutes, add a crontab entry:

```
*/15 * * * * /usr/bin/python3 /home/pi/pi-dewpoint/dewpoint.py
```

## Running tests

```bash
pip install pytest
pytest test_dewpoint.py -v
```
