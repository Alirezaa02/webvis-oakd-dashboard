# telemetry_client.py
import os
import time
import logging
import requests

# Configure via env or edit defaults here
BACKEND = os.environ.get("BACKEND", "http://127.0.0.1:5051")
USER    = os.environ.get("BACKEND_USER", "admin")
PASS    = os.environ.get("BACKEND_PASS", "admin")

AUTH_EP = f"{BACKEND.rstrip('/')}/auth/login"
POST_EP = f"{BACKEND.rstrip('/')}/api/sensors"

_token = None

def configure(backend: str | None = None, user: str | None = None, password: str | None = None):
    """Optionally override endpoints/creds at runtime."""
    global BACKEND, USER, PASS, AUTH_EP, POST_EP
    if backend:
        BACKEND = backend
        AUTH_EP = f"{BACKEND.rstrip('/')}/auth/login"
        POST_EP = f"{BACKEND.rstrip('/')}/api/sensors"
    if user:
        USER = user
    if password:
        PASS = password

def _get_token() -> str | None:
    global _token
    try:
        r = requests.post(AUTH_EP, json={"username": USER, "password": PASS}, timeout=5)
        r.raise_for_status()
        _token = (r.json() or {}).get("token")
        if not _token:
            logging.warning("telemetry_client: login OK but no token in response")
    except Exception as e:
        logging.warning("telemetry_client: login failed: %s", e)
        _token = None
    return _token

def format_payload(sensor_dict: dict) -> dict:
    """
    Maps teammate keys (Temperature/Pressure/Humidity/Light, Oxidising/Reducing/NH3)
    to the lower-case keys your frontend expects, and adds a timestamp (ms).
    """
    ts = int(time.time() * 1000)
    return {
        "ts":        ts,
        "temp":      sensor_dict.get("Temperature", sensor_dict.get("temp")),
        "pressure":  sensor_dict.get("Pressure",    sensor_dict.get("pressure")),
        "humidity":  sensor_dict.get("Humidity",    sensor_dict.get("humidity")),
        "light":     sensor_dict.get("Light",       sensor_dict.get("light")),
        "oxidising": sensor_dict.get("Oxidising",   sensor_dict.get("oxidising")),
        "reducing":  sensor_dict.get("Reducing",    sensor_dict.get("reducing") or sensor_dict.get("reduction")),
        "nh3":       sensor_dict.get("NH3",         sensor_dict.get("nh3")),
    }

def post_sensor_reading(sensor_dict: dict) -> bool:
    """
    POST a single sensor reading to /api/sensors.
    On success your backend should broadcast to /ws/live, which your frontend already listens to.
    Returns True on success, False on failure (no exception).
    """
    global _token
    if not _token:
        _get_token()

    payload = format_payload(sensor_dict)
    headers = {"Content-Type": "application/json"}
    if _token:
        headers["Authorization"] = f"Bearer {_token}"

    try:
        r = requests.post(POST_EP, json=payload, headers=headers, timeout=5)
        if r.status_code == 401:
            # token expired → refresh once and retry
            _get_token()
            if _token:
                headers["Authorization"] = f"Bearer {_token}"
            r = requests.post(POST_EP, json=payload, headers=headers, timeout=5)
        r.raise_for_status()
        return True
    except Exception as e:
        logging.debug("telemetry_client: post failed: %s", e)
        return False
