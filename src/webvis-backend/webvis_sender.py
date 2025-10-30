import time, base64, requests, random

# ==== CONFIG ====
BASE = "http://10.88.13.209:5051"   # <-- change to your Mac IP
USER, PASS = "admin", "admin"
# =================

def login():
    r = requests.post(f"{BASE}/auth/login",
                      json={"username": USER, "password": PASS},
                      timeout=5)
    r.raise_for_status()
    token = r.json().get("token")
    if not token:
        raise RuntimeError("login failed")
    return token

def post(path, payload, token):
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.post(f"{BASE}{path}", json=payload, headers=headers, timeout=5)
    r.raise_for_status()
    return r.json()

def now_ms():
    return int(time.time() * 1000)

def send_sensor(token):
    payload = {
        "ts": now_ms(),
        "temp": round(23 + random.random(), 2),
        "pressure": round(1006 + random.random() * 2, 2),
        "humidity": round(40 + random.random() * 10, 2),
        "light": int(300 + random.random() * 50),
        "gas": round(0.1 + random.random() * 0.05, 3),
    }
    return post("/api/sensors", payload, token)

def send_pose(token):
    payload = {"ts": now_ms(),
               "x": round(random.uniform(0.5, 0.8), 3),
               "y": round(random.uniform(-0.8, -0.5), 3),
               "z": round(random.uniform(1.2, 1.4), 3)}
    return post("/api/pose", payload, token)

def send_detection(token):
    # 1x1 transparent pixel as placeholder
    image_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII="
    data_url = f"data:image/png;base64,{image_b64}"
    payload = {
        "ts": now_ms(),
        "frame_id": "f1",
        "image_url": data_url,
        "aruco_id": 7,
        "valve_state": "open",
        "conf": 0.92,
        "bbox": {"x": 120, "y": 80, "w": 60, "h": 60},
    }
    return post("/api/detections", payload, token)

if __name__ == "__main__":
    token = login()
    print("✅ Logged in to", BASE)

    # send a few demo packets
    for i in range(5):
        print(f"Sensor {i+1} ->", send_sensor(token))
        print(f"Pose {i+1}   ->", send_pose(token))
        if i % 2 == 0:
            print("Detection ->", send_detection(token))
        time.sleep(1)
