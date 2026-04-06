"""
pi-dewpoint: Retrieve the current dew point from Open-Meteo and set a Govee
light bulb to a color that reflects how humid it feels outside.

Configuration is supplied via environment variables (or a .env file):
  LATITUDE         - Location latitude  (e.g. 42.36)
  LONGITUDE        - Location longitude (e.g. -71.06)
  GOVEE_DEVICE_IP  - Local IP address of the Govee device (e.g. 192.168.1.50)
"""

import json
import os
import socket
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
GOVEE_LOCAL_PORT = 4003

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


def set_govee_color(device_ip: str, r: int, g: int, b: int) -> None:
    """Send a color command to a Govee light via the local LAN API (UDP).

    Requires LAN Control to be enabled in the Govee app for the device.
    The device must be reachable at *device_ip* on the local network.
    """
    command = {
        "msg": {
            "cmd": "colorwc",
            "data": {
                "color": {"r": r, "g": g, "b": b},
                "colorTemInKelvin": 0,
            },
        }
    }
    payload = json.dumps(command).encode("utf-8")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.sendto(payload, (device_ip, GOVEE_LOCAL_PORT))


def main() -> None:
    required_vars = (
        "LATITUDE",
        "LONGITUDE",
        "GOVEE_DEVICE_IP",
    )
    missing = [v for v in required_vars if not os.environ.get(v)]
    if missing:
        print(f"Error: missing required environment variables: {', '.join(missing)}")
        sys.exit(1)

    latitude = float(os.environ["LATITUDE"])
    longitude = float(os.environ["LONGITUDE"])
    device_ip = os.environ["GOVEE_DEVICE_IP"]

    print(f"Fetching dew point for ({latitude}, {longitude})...")
    dewpoint = get_dewpoint(latitude, longitude)
    print(f"Current dew point: {dewpoint:.1f} °F")

    r, g, b = dewpoint_to_color(dewpoint)
    print(f"Setting Govee light to RGB({r}, {g}, {b})...")

    set_govee_color(device_ip, r, g, b)
    print("Govee light updated successfully.")


if __name__ == "__main__":
    main()
