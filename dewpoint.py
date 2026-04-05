"""
pi-dewpoint: Retrieve the current dew point from Open-Meteo and set a Govee
light bulb to a color that reflects how humid it feels outside.

Configuration is supplied via environment variables (or a .env file):
  LATITUDE        - Location latitude  (e.g. 42.36)
  LONGITUDE       - Location longitude (e.g. -71.06)
  GOVEE_API_KEY   - Govee Developer API key
  GOVEE_DEVICE_ID - Govee device ID (from Govee app)
  GOVEE_MODEL     - Govee device model (e.g. H6004)
"""

import os
import sys
import uuid

import requests
from dotenv import load_dotenv

load_dotenv()

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
GOVEE_API_URL = "https://openapi.api.govee.com/router/api/v1/device/control"

# Dewpoint comfort categories from tikaro/sandex (sourced from WeatherSpark).
# Each entry is (upper_exclusive_threshold_°F, R, G, B).
# The final entry covers dewpoint >= 76 °F (miserable).
_DEWPOINT_COLORS = [
    (50,  0, 204, 255),  # #0CF    — very dry    (dewpoint < 50)
    (56,  0, 255,   0),  # #0F0    — dry         (50 ≤ dewpoint < 56)
    (61, 255, 204,   3),  # #FFCC03 — comfortable (56 ≤ dewpoint < 61)
    (66, 254, 153,   1),  # #FE9901 — humid       (61 ≤ dewpoint < 66)
    (71, 255, 101,   0),  # #FF6500 — muggy       (66 ≤ dewpoint < 71)
    (76, 254,   0,   0),  # #FE0000 — oppressive  (71 ≤ dewpoint < 76)
    (float("inf"), 130, 2, 4),  # #820204 — miserable  (dewpoint >= 76)
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
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(max_retries=3)
    session.mount("https://", adapter)
    response = session.get(OPEN_METEO_URL, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
    return float(data["current"]["dew_point_2m"])


def dewpoint_to_color(dewpoint_f: float) -> tuple[int, int, int]:
    """Map a dew point temperature (°F) to an (R, G, B) tuple.

    Uses the comfort categories from tikaro/sandex (step function, no blending).
    """
    for threshold, r, g, b in _DEWPOINT_COLORS:
        if dewpoint_f < threshold:
            return (r, g, b)
    # Should never be reached (last threshold is inf)
    _, r, g, b = _DEWPOINT_COLORS[-1]
    return (r, g, b)


def set_govee_color(
    api_key: str,
    device_id: str,
    model: str,
    r: int,
    g: int,
    b: int,
) -> dict:
    """Send a color command to a Govee light via the Govee OpenAPI."""
    headers = {
        "Govee-API-Key": api_key,
        "Content-Type": "application/json",
    }
    color_int = (r << 16) | (g << 8) | b
    payload = {
        "requestId": str(uuid.uuid4()),
        "payload": {
            "sku": model,
            "device": device_id,
            "capability": {
                "type": "devices.capabilities.color_setting",
                "instance": "colorRgb",
                "value": color_int,
            },
        },
    }
    response = requests.post(GOVEE_API_URL, headers=headers, json=payload, timeout=10)
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
