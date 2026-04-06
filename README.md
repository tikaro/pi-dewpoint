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

3. **Set the bulb** — sends the RGB color directly to the Govee light over your local network using the [Govee LAN API](https://app-h5.govee.com/user-manual/wlan-guide) (UDP, no cloud round-trip).

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Enable LAN Control on your Govee device

Open the Govee app, go to the device settings, and enable **LAN Control**. This allows the Raspberry Pi to communicate with the bulb directly over your local network without going through Govee's cloud servers.

Assign a static IP address (or a DHCP reservation) to your Govee device so that `GOVEE_DEVICE_IP` stays stable across reboots.

### 3. Configure environment variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

| Variable | Description |
|----------|-------------|
| `LATITUDE` | Latitude of the location to monitor |
| `LONGITUDE` | Longitude of the location to monitor |
| `GOVEE_DEVICE_IP` | Local IP address of the Govee device (e.g. `192.168.1.50`) |

### 4. Run

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
