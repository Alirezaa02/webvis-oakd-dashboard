// server.js (Node/Express + ws)
// Runs HTTP API on :5051 and a WebSocket at /ws/live

import express from "express";
import http from "http";
import cors from "cors";
import { WebSocketServer } from "ws";

// ---------- Config ----------
const PORT = process.env.PORT ? Number(process.env.PORT) : 5051;
const ENABLE_SIM = (process.env.SIM || "on").toLowerCase() !== "off"; // set SIM=off to disable generator

// ---------- App / HTTP ----------
const app = express();
app.use(cors());
app.use(express.json({ limit: "1mb" }));

app.get("/health", (_req, res) => res.json({ ok: true, wsClients: wss?.clients?.size || 0 }));

// Accept sensor readings (from Pi or curl) and broadcast immediately
app.post("/api/sensors", (req, res) => {
  const d = req.body || {};

  // normalize alias "reduction" -> "reducing"
  if (d.reduction != null && d.reducing == null) d.reducing = d.reduction;

  const row = {
    ts: Number(d.ts || Date.now()),
    temp:      isNum(d.temp)      ? Number(d.temp)      : null,
    pressure:  isNum(d.pressure)  ? Number(d.pressure)  : null,
    humidity:  isNum(d.humidity)  ? Number(d.humidity)  : null,
    light:     isNum(d.light)     ? Number(d.light)     : null,
    oxidising: isNum(d.oxidising) ? Number(d.oxidising) : null,
    reducing:  isNum(d.reducing)  ? Number(d.reducing)  : null,
    nh3:       isNum(d.nh3)       ? Number(d.nh3)       : null
  };

  //console.log("RX sensor:", new Date().toISOString(), req.body);   // to see the data is works correct

  broadcast({ kind: "sensor", data: row });
  return res.status(201).json({ ok: true });
});

// (Optional) simple endpoints you may already use in the UI, implement as needed:
app.post("/auth/login", (req, res) => {
  // If you don’t need auth, leave this as a dummy that always returns a token.
  const { username, password } = req.body || {};
  if (username && password) return res.json({ token: "dev-demo-token" });
  return res.status(400).json({ error: "missing credentials" });
});


// --- add near your other routes ---
app.get("/video_feed", async (req, res) => {
  try {
    // Point this to your camera/Pi MJPEG endpoint
    const upstream = process.env.UPSTREAM_VIDEO_URL
      || "http://10.88.32.129:5055/video_feed"; // <-- change if your stream lives elsewhere

    const r = await fetch(upstream); // Node 18+: global fetch
    if (!r.ok || !r.body) {
      return res.status(502).send("Upstream video unavailable");
    }

    // pass through headers so the browser treats it as MJPEG
    for (const [k, v] of r.headers) {
      if (k.toLowerCase() === "content-type" || k.toLowerCase() === "content-length" || k.toLowerCase() === "cache-control")
        res.setHeader(k, v);
    }

    res.status(200);
    r.body.pipe(res);

    req.on("close", () => {
      try { r.body.cancel?.(); } catch {}
    });
  } catch (e) {
    console.error("video proxy error:", e);
    res.status(500).send("video proxy error");
  }
});


// ---------- HTTP server + WebSocket ----------
const server = http.createServer(app);
const wss = new WebSocketServer({ noServer: true });

server.on("upgrade", (req, socket, head) => {
  // Only accept upgrades for our path
  if (req.url !== "/ws/live") {
    socket.destroy();
    return;
  }
  wss.handleUpgrade(req, socket, head, (ws) => {
    wss.emit("connection", ws, req);
  });
});

wss.on("connection", (ws) => {
  ws.send(JSON.stringify({ kind: "hello", data: { t: Date.now() } }));
  ws.on("error", () => {/* ignore */});
});

// Broadcast helper
function broadcast(obj) {
  const s = JSON.stringify(obj);
  for (const client of wss.clients) {
    if (client.readyState === 1) client.send(s);
  }
}

function isNum(x) {
  return typeof x === "number" && Number.isFinite(x);
}

// ---------- Optional simulator (for testing without the Pi) ----------
if (ENABLE_SIM) {
  console.log("SIM: on (set SIM=off to disable)");
  let t = 0;
  setInterval(() => {
    const ts = Date.now();
    const rand = (n) => (Math.random() - 0.5) * n;

    // Fake channels; tune as you like
    const temp = 22.0 + Math.sin(t / 20) * 1.2 + rand(0.2);
    const pressure = 1012 + Math.cos(t / 60) * 4 + rand(0.5);
    const humidity = 45 + Math.sin(t / 40) * 8 + rand(1);
    const light = 100 + Math.abs(Math.sin(t / 30)) * 50 + rand(5);

    const oxidising = 0.6 + Math.abs(Math.sin(t / 12)) * 0.3 + rand(0.05);
    const reducing  = 1.0 + Math.abs(Math.cos(t / 14)) * 0.5 + rand(0.05);
    const nh3       = 0.4 + Math.abs(Math.sin(t / 16)) * 0.25 + rand(0.05);

    const row = { ts, temp, pressure, humidity, light, oxidising, reducing, nh3 };
    broadcast({ kind: "sensor", data: row });
    t += 1;
  }, 1000);
} else {
  console.log("SIM: off");
}

server.listen(PORT, () => {
  console.log(`HTTP  : http://0.0.0.0:${PORT}`);
  console.log(`WS    : ws://0.0.0.0:${PORT}/ws/live`);
});
