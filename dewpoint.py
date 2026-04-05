"""
pi-dewpoint: Retrieve the current dew point from Open-Meteo and set a Govee
light bulb to a color that reflects how humid it feels outside.

Configuration is supplied via environment variables (or a .env file):
  LATITUDE        - Location latitude  (e.g. 42.36)
  LONGITUDE       - Location longitude (e.g. -71.06)
  GOVEE_API_KEY   - Govee Developer API key
  GOVEE_DEVICE_ID - Govee device ID (from Govee app)
  GOVEE_MODEL     - Govee device model (e.g. H6159)
"""

import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
GOVEE_API_URL = "https://developer-api.govee.com/v1/devices/control"

# Color stops: (dew_point_°F, R, G, B)
# Below 35 °F → blue (crisp/dry); above 75 °F → red (oppressive)
_COLOR_STOPS = [
    (35, 0, 0, 255),    # Blue   — dry / very comfortable
    (50, 0, 255, 255),  # Cyan   — comfortable
    (60, 0, 255, 0),    # Green  — pleasant
    (65, 255, 255, 0),  # Yellow — getting humid
    (70, 255, 128, 0),  # Orange — uncomfortable
    (75, 255, 0, 0),    # Red    — oppressive
]


def get_dewpoint(latitude: float, longitude: float) -> float:
    """Return the current dew point in °F for the given coordinates.

    Uses the Open-Meteo API, which is free and requires no API key.
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "dew_point_2m",
        "temperature_unit": "fahrenheit",
        "forecast_days": 1,
    }
    response = requests.get(OPEN_METEO_URL, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
    return float(data["current"]["dew_point_2m"])


def dewpoint_to_color(dewpoint_f: float) -> tuple[int, int, int]:
    """Map a dew point temperature (°F) to an (R, G, B) tuple.

    Values are linearly interpolated between the color stops defined in
    _COLOR_STOPS so the transition looks smooth on the bulb.
    """
    if dewpoint_f <= _COLOR_STOPS[0][0]:
        return (_COLOR_STOPS[0][1], _COLOR_STOPS[0][2], _COLOR_STOPS[0][3])
    if dewpoint_f >= _COLOR_STOPS[-1][0]:
        return (_COLOR_STOPS[-1][1], _COLOR_STOPS[-1][2], _COLOR_STOPS[-1][3])

    for i in range(len(_COLOR_STOPS) - 1):
        t0, r0, g0, b0 = _COLOR_STOPS[i]
        t1, r1, g1, b1 = _COLOR_STOPS[i + 1]
        if t0 <= dewpoint_f <= t1:
            fraction = (dewpoint_f - t0) / (t1 - t0)
            r = round(r0 + fraction * (r1 - r0))
            g = round(g0 + fraction * (g1 - g0))
            b = round(b0 + fraction * (b1 - b0))
            return (r, g, b)

    # Should never be reached, but keep mypy happy
    return (_COLOR_STOPS[-1][1], _COLOR_STOPS[-1][2], _COLOR_STOPS[-1][3])


def set_govee_color(
    api_key: str,
    device_id: str,
    model: str,
    r: int,
    g: int,
    b: int,
) -> dict:
    """Send a color command to a Govee light via the Govee Developer API."""
    headers = {
        "Govee-API-Key": api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "device": device_id,
        "model": model,
        "cmd": {
            "name": "color",
            "value": {"r": r, "g": g, "b": b},
        },
    }
    response = requests.put(GOVEE_API_URL, headers=headers, json=payload, timeout=10)
    response.raise_for_status()
    return response.json()


def main() -> None:
    required_vars = (
        "LATITUDE",
        "LONGITUDE",
        "GOVEE_API_KEY",
        "GOVEE_DEVICE_ID",
        "GOVEE_MODEL",
    )
    missing = [v for v in required_vars if not os.environ.get(v)]
    if missing:
        print(f"Error: missing required environment variables: {', '.join(missing)}")
        sys.exit(1)

    latitude = float(os.environ["LATITUDE"])
    longitude = float(os.environ["LONGITUDE"])
    api_key = os.environ["GOVEE_API_KEY"]
    device_id = os.environ["GOVEE_DEVICE_ID"]
    model = os.environ["GOVEE_MODEL"]

    print(f"Fetching dew point for ({latitude}, {longitude})...")
    dewpoint = get_dewpoint(latitude, longitude)
    print(f"Current dew point: {dewpoint:.1f} °F")

    r, g, b = dewpoint_to_color(dewpoint)
    print(f"Setting Govee light to RGB({r}, {g}, {b})...")

    set_govee_color(api_key, device_id, model, r, g, b)
    print("Govee light updated successfully.")


if __name__ == "__main__":
    main()
