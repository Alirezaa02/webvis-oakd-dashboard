from __future__ import annotations
import os, json, time
from typing import Iterable, Optional
from contextlib import contextmanager

from flask import Flask, request, jsonify
from flask_cors import CORS
import pymysql

# --------------------------- config ---------------------------
PORT = int(os.getenv("PORT", "5051"))
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "webvis")
DB_PASS = os.getenv("DB_PASS", "webvis_pw")
DB_NAME = os.getenv("DB_NAME", "webvis")

app = Flask(__name__)
CORS(app)

def now_ms() -> int:
    return int(time.time() * 1000)

# --------------------------- DB helpers ---------------------------
def get_conn():
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        autocommit=False,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.Cursor,
    )

@contextmanager
def db():
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_schema():
    ddl = """
    CREATE TABLE IF NOT EXISTS sensor_readings (
      ts BIGINT PRIMARY KEY,
      temp FLOAT,
      pressure FLOAT,
      humidity FLOAT,
      light FLOAT,
      gas FLOAT
    );

    CREATE TABLE IF NOT EXISTS detections (
      id BIGINT PRIMARY KEY AUTO_INCREMENT,
      ts BIGINT NOT NULL,
      frame_id VARCHAR(64) NOT NULL,
      image_url MEDIUMTEXT NOT NULL,
      aruco_id INT NULL,
      valve_state ENUM('open','closed') NULL,
      conf FLOAT NULL,
      bbox JSON NULL,
      INDEX (ts)
    );

    CREATE TABLE IF NOT EXISTS poses (
      ts BIGINT PRIMARY KEY,
      x  FLOAT NOT NULL,
      y  FLOAT NOT NULL,
      z  FLOAT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS ops_log (
      ts BIGINT PRIMARY KEY,
      level ENUM('INFO','WARN','ERROR') NOT NULL,
      message TEXT NOT NULL
    );
    """
    # run multi-statements safely
    with db() as conn:
        for stmt in ddl.split(";\n"):
            stmt = stmt.strip()
            if stmt:
                with conn.cursor() as cur:
                    cur.execute(stmt)

def log_ops(conn, level: str, message: str):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO ops_log (ts, level, message) VALUES (%s, %s, %s)",
            (now_ms(), level, message[:65535]),
        )

# --------------------------- small utils ---------------------------
def _to_ms(v) -> int:
    try:
        return int(v)
    except Exception:
        return now_ms()

def _as_iter(x) -> Iterable[dict]:
    if x is None:
        return []
    if isinstance(x, list):
        return x
    return [x]

# --------------------------- routes: basics ---------------------------
@app.get("/health")
def health():
    return jsonify(ok=True, ts=now_ms(), db=DB_NAME)

# Mock auth (kept so your frontend login works)
@app.post("/auth/login")
def auth_login():
    data = request.get_json(silent=True) or {}
    if data.get("username") == "admin" and data.get("password") == "admin":
        return jsonify(token="mock-token-123")
    return jsonify(error="invalid credentials"), 401

# --------------------------- routes: sensors ---------------------------
@app.post("/api/sensors")
def api_post_sensor():
    d = request.get_json(silent=True) or {}
    client_ts = d.get("ts")  # optional from device
    server_now = now_ms()

    ts = _to_ms(client_ts) if client_ts is not None else server_now
    temp = d.get("temp")
    pressure = d.get("pressure")
    humidity = d.get("humidity")
    light = d.get("light")
    gas = d.get("gas")

    with db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "REPLACE INTO sensor_readings (ts, temp, pressure, humidity, light, gas) VALUES (%s,%s,%s,%s,%s,%s)",
                (ts, temp, pressure, humidity, light, gas),
            )
        # ops log with latency classification
        if client_ts is not None:
            rt = server_now - _to_ms(client_ts)
            level = "INFO" if rt <= 4000 else "WARN"
            log_ops(conn, level, f"ingest:/api/sensors rt_ms={rt}")
        else:
            log_ops(conn, "INFO", "ingest:/api/sensors no_client_ts")

    return jsonify(ok=True, ts=ts)

@app.get("/api/sensors/latest")
def api_latest_sensors():
    limit = int(request.args.get("limit", "120"))
    with db() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT ts, temp, pressure, humidity, light, gas FROM sensor_readings ORDER BY ts DESC LIMIT %s",
            (limit,),
        )
        rows = cur.fetchall()
    out = [
        {
            "ts": r[0],
            "temp": r[1],
            "pressure": r[2],
            "humidity": r[3],
            "light": r[4],
            "gas": r[5],
        }
        for r in rows
    ]
    return jsonify(out)

# --------------------------- routes: pose ---------------------------
@app.post("/api/pose")
def api_post_pose():
    d = request.get_json(silent=True) or {}
    ts = _to_ms(d.get("ts"))
    x, y, z = d.get("x"), d.get("y"), d.get("z")
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("REPLACE INTO poses (ts, x, y, z) VALUES (%s,%s,%s,%s)", (ts, x, y, z))
        log_ops(conn, "INFO", "ingest:/api/pose")
    return jsonify(ok=True, ts=ts)

@app.get("/api/pose/latest")
def api_latest_pose():
    limit = int(request.args.get("limit", "5"))
    with db() as conn, conn.cursor() as cur:
        cur.execute("SELECT ts, x, y, z FROM poses ORDER BY ts DESC LIMIT %s", (limit,))
        rows = cur.fetchall()
    out = [{"ts": r[0], "x": r[1], "y": r[2], "z": r[3]} for r in rows]
    return jsonify(out)

# --------------------------- routes: detections ---------------------------
@app.post("/api/detections")
def api_post_detection():
    d = request.get_json(silent=True) or {}
    ts = _to_ms(d.get("ts"))
    frame_id = d.get("frame_id") or "frame"
    image_url = d.get("image_url") or ""
    aruco_id = d.get("aruco_id")
    valve_state = d.get("valve_state")
    conf = d.get("conf")
    bbox_json = json.dumps(d.get("bbox")) if d.get("bbox") is not None else None

    with db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO detections (ts, frame_id, image_url, aruco_id, valve_state, conf, bbox)
                VALUES (%s,%s,%s,%s,%s,%s, CAST(%s AS JSON))
                """,
                (ts, frame_id, image_url, aruco_id, valve_state, conf, bbox_json),
            )
        log_ops(conn, "INFO", "ingest:/api/detections")
    return jsonify(ok=True, ts=ts)

@app.get("/api/detections/latest")
def api_latest_detections():
    limit = int(request.args.get("limit", "5"))
    with db() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, ts, frame_id, image_url, aruco_id, valve_state, conf, bbox FROM detections ORDER BY ts DESC LIMIT %s",
            (limit,),
        )
        rows = cur.fetchall()
    out = []
    for r in rows:
        out.append(
            {
                "id": r[0],
                "ts": r[1],
                "frame_id": r[2],
                "image_url": r[3],
                "aruco_id": r[4],
                "valve_state": r[5],
                "conf": r[6],
                "bbox": json.loads(r[7]) if r[7] else None,
            }
        )
    return jsonify(out)

# --------------------------- routes: ops log ---------------------------
@app.get("/api/logs/recent")
def api_logs_recent():
    limit = int(request.args.get("limit", "200"))
    with db() as conn, conn.cursor() as cur:
        cur.execute("SELECT ts, level, message FROM ops_log ORDER BY ts DESC LIMIT %s", (limit,))
        rows = cur.fetchall()
    out = [{"ts": r[0], "level": r[1], "message": r[2]} for r in rows]
    return jsonify(out)

# --------------------------- JSON upload route ---------------------------
def _ingest_one_sensor(conn, row: dict, base_ts: int):
    ts = _to_ms(row.get("ts", base_ts))
    with conn.cursor() as cur:
        cur.execute(
            "REPLACE INTO sensor_readings (ts, temp, pressure, humidity, light, gas) VALUES (%s,%s,%s,%s,%s,%s)",
            (ts, row.get("temp"), row.get("pressure"), row.get("humidity"), row.get("light"), row.get("gas")),
        )

def _ingest_one_pose(conn, row: dict, base_ts: int):
    ts = _to_ms(row.get("ts", base_ts))
    with conn.cursor() as cur:
        cur.execute("REPLACE INTO poses (ts, x, y, z) VALUES (%s,%s,%s,%s)",
                    (ts, row.get("x"), row.get("y"), row.get("z")))

def _ingest_one_detection(conn, row: dict, base_ts: int):
    ts = _to_ms(row.get("ts", base_ts))
    bbox_json = json.dumps(row.get("bbox")) if row.get("bbox") is not None else None
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO detections (ts, frame_id, image_url, aruco_id, valve_state, conf, bbox)
            VALUES (%s,%s,%s,%s,%s,%s, CAST(%s AS JSON))
            """,
            (ts, row.get("frame_id") or "frame", row.get("image_url") or "",
             row.get("aruco_id"), row.get("valve_state"), row.get("conf"), bbox_json),
        )

def ingest_json_payload(payload: dict) -> dict:
    s_count = p_count = d_count = 0
    base_ts = _to_ms(payload.get("ts"))

    with db() as conn:
        for r in _as_iter(payload.get("sensors")):
            _ingest_one_sensor(conn, r, base_ts); s_count += 1
        for r in _as_iter(payload.get("pose")):
            _ingest_one_pose(conn, r, base_ts);    p_count += 1
        for r in _as_iter(payload.get("detections")):
            _ingest_one_detection(conn, r, base_ts); d_count += 1

        log_ops(conn, "INFO", f"upload:json s={s_count} p={p_count} d={d_count}")
    return {"sensors": s_count, "pose": p_count, "detections": d_count}

@app.post("/api/upload/json")
def api_upload_json():
    # Prefer raw JSON body
    data = request.get_json(silent=True)
    if isinstance(data, dict):
        stats = ingest_json_payload(data)
        return jsonify(ok=True, stats=stats)

    # Or multipart file field "file"
    if "file" in request.files:
        f = request.files["file"]
        try:
            payload = json.loads(f.read().decode("utf-8"))
            if isinstance(payload, dict):
                stats = ingest_json_payload(payload)
                return jsonify(ok=True, stats=stats)
        except Exception as e:
            return jsonify(ok=False, error=f"invalid json: {e}"), 400

    return jsonify(ok=False, error="No JSON body or 'file' upload"), 400

# --------------------------- combined latest (optional) ---------------------------
@app.get("/api/state/latest")
def api_state_latest():
    with db() as conn, conn.cursor() as cur:
        cur.execute("SELECT ts, temp, pressure, humidity, light, gas FROM sensor_readings ORDER BY ts DESC LIMIT 1")
        s = cur.fetchone()
        cur.execute("SELECT ts, x, y, z FROM poses ORDER BY ts DESC LIMIT 1")
        p = cur.fetchone()
        cur.execute("""SELECT id, ts, frame_id, image_url, aruco_id, valve_state, conf, bbox
                       FROM detections ORDER BY ts DESC LIMIT 1""")
        d = cur.fetchone()
    out = {
        "sensors": (None if not s else {
            "ts": s[0], "temp": s[1], "pressure": s[2], "humidity": s[3], "light": s[4], "gas": s[5]
        }),
        "pose": (None if not p else {"ts": p[0], "x": p[1], "y": p[2], "z": p[3]}),
        "detection": (None if not d else {
            "id": d[0], "ts": d[1], "frame_id": d[2], "image_url": d[3],
            "aruco_id": d[4], "valve_state": d[5], "conf": d[6],
            "bbox": (json.loads(d[7]) if d[7] else None)
        })
    }
    return jsonify(out)

# --------------------------- boot ---------------------------
if __name__ == "__main__":
    # make sure schema exists
    try:
        init_schema()
    except Exception as e:
        print("Schema init failed:", e)
        raise

    print(f"WebVis Flask API starting on 0.0.0.0:{PORT} (DB={DB_NAME})")
    app.run(host="0.0.0.0", port=PORT, debug=True)
