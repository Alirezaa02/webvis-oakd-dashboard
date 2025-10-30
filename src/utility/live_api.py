# live_api.py
from flask import Flask, jsonify
from flask_cors import CORS
from threading import Thread
import os

app = Flask(__name__)
CORS(app)  # helpful for browser-based polling across hosts

_latest = None  # module-level, updated from main.py via set_latest()

@app.get("/api/sensor/live")
def live():
    global _latest
    if _latest is None:
        return jsonify({"error": "no data"}), 503
    return jsonify(_latest)

def set_latest(payload: dict):
    """Call this from main.py with the already-formatted dict (has ts/temp/.../nh3)."""
    global _latest
    _latest = payload

def start_server(host: str | None = None, port: int | None = None, daemon: bool = True):
    """Run Flask in a background thread so it doesn't block your main loop."""
    h = host or os.environ.get("LIVE_API_HOST", "0.0.0.0")
    p = int(port or int(os.environ.get("LIVE_API_PORT", "5055")))
    t = Thread(target=lambda: app.run(host=h, port=p, threaded=True, use_reloader=False))
    t.daemon = daemon
    t.start()
    return t
