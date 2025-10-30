/* eslint-disable @typescript-eslint/no-explicit-any */
import { useEffect, useState } from "react";
import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  LineElement,
  PointElement,
  LinearScale,
  CategoryScale,
  Tooltip,
  Legend,
  Filler,
} from "chart.js";


import { useRing } from "./lib/useRing";       // your existing ring buffer hook
import { NavBar } from "./components/NavBar";  // simple tab bar (you created this)
import { VideoStream } from "./components/VideoStream"; // your video component
import { SystemLogs } from "./components/SystemLogs";
import { HistoryTable } from "./components/HistoryTable";
import { HealthPanel } from "./components/HealthPanel";

import { connectWS, onWSMessage } from "./lib/ws";
import type { ChartOptions } from "chart.js";
import LiveStatus from "./components/LiveStatus";

// NOTE: GasChannels import removed because you’re drawing the 3 gas charts inline here.

<LiveStatus />

ChartJS.register(LineElement, PointElement, LinearScale, CategoryScale, Tooltip, Legend, Filler);

/* ============================
   Config (outside component)
============================ */
const API_URL = (import.meta.env.VITE_API_URL as string) ?? "http://127.0.0.1:5051";
const BASE = API_URL;
const WS_URL =
  (import.meta.env.VITE_WS_URL as string) ??
  API_URL.replace(/^http/i, "ws").replace(/\/+$/, "") + "/ws/live";
const STREAM_URL =
  (import.meta.env.VITE_STREAM_URL as string) ??
  `http://${window.location.hostname}:5051/video_feed`;

/* ============================
   Types + type guards
============================ */
type SensorData = {
  ts: number;
  temp?: number;
  pressure?: number;
  humidity?: number;
  light?: number;
  oxidising?: number;
  reducing?: number;   // preferred key
  reduction?: number;  // fallback accepted
  nh3?: number;
};

type PoseData = { ts: number; x: number; y: number; z: number };
type DetData = {
  ts: number;
  frame_id: string;
  image_url: string;
  aruco_id?: number;
  valve_state?: "open" | "closed";
  conf?: number;
  bbox?: any;
};
type SensorMsg = { kind: "sensor"; data: SensorData };
type PoseMsg   = { kind: "pose"; data: PoseData };
type DetMsg    = { kind: "detection"; data: DetData };

const isObject = (v: unknown): v is Record<string, unknown> =>
  typeof v === "object" && v !== null;
const isSensorMsg = (v: unknown): v is SensorMsg =>
  isObject(v) && (v as any).kind === "sensor" && isObject((v as any).data);
const isPoseMsg = (v: unknown): v is PoseMsg =>
  isObject(v) && (v as any).kind === "pose" && isObject((v as any).data);
const isDetMsg = (v: unknown): v is DetMsg =>
  isObject(v) && (v as any).kind === "detection" && isObject((v as any).data);

/* ============================
   App
============================ */
type Tab = "dashboard" | "video" | "logs" | "health";

export default function App() {
  const [tab, setTab] = useState<Tab>("dashboard");

  // live rings
  const temp = useRing<{ t: number; v: number }>(180);
  const press = useRing<{ t: number; v: number }>(180);
  const hum = useRing<{ t: number; v: number }>(180);
  const light = useRing<{ t: number; v: number }>(180);
  const oxidising = useRing<{ t: number; v: number }>(180);
  const reducing  = useRing<{ t: number; v: number }>(180);
  const nh3       = useRing<{ t: number; v: number }>(180);

  //const DATA_URL = (import.meta.env.VITE_DATA_URL as string) || "";

  // last-known pose/detection
  const [pose, setPose] = useState<PoseData | null>(null);
  const [det, setDet] = useState<DetData | null>(null);

  // auth token (for logs/history APIs)
  const [token] = useState<string>("");

  // // one-time login: admin/admin
  // useEffect(() => {
  //   (async () => {
  //     try {
  //       const r = await fetch(`${BASE}/auth/login`, {
  //         method: "POST",
  //         headers: { "Content-Type": "application/json" },
  //         body: JSON.stringify({ username: "admin", password: "admin" }),
  //       });
  //       const j = await r.json();
  //       if (j?.token) setToken(j.token as string);
  //     } catch {
  //       // ignore login failure; UI just shows "no token"
  //     }
  //   })();
  // }, []);

  // connect WS once
  useEffect(() => {
    const offSocket = connectWS(WS_URL);
  const offMsg = onWSMessage((msg: unknown) => {
    if (isSensorMsg(msg)) {
      const d = (msg as SensorMsg).data;
      if (typeof d.temp === "number")     temp.push({ t: d.ts, v: d.temp });
      if (typeof d.pressure === "number") press.push({ t: d.ts, v: d.pressure });
      if (typeof d.humidity === "number") hum.push({ t: d.ts, v: d.humidity });
      if (typeof d.light === "number")    light.push({ t: d.ts, v: d.light });

      if (typeof d.oxidising === "number") oxidising.push({ t: d.ts, v: d.oxidising });
      const red = (d.reducing ?? d.reduction);
      if (typeof red === "number") reducing.push({ t: d.ts, v: red });
      if (typeof d.nh3 === "number") nh3.push({ t: d.ts, v: d.nh3 });

    } else if (isPoseMsg(msg)) {
      setPose((msg as PoseMsg).data);
    } else if (isDetMsg(msg)) {
      setDet((msg as DetMsg).data);
    }
  });
  return () => { offMsg(); offSocket?.(); };
}, []);

  // chart helpers (build from ring buffers)
  const mkData = (label: string, series: { t: number; v: number }[], color: string) => ({
    labels: series.map((p) => new Date(p.t).toLocaleTimeString()),
    datasets: [
      {
        label,
        data: series.map((p) => p.v),
        fill: true,
        backgroundColor: color + "22",
        borderColor: color,
        borderWidth: 2,
        tension: 0.25,
        pointRadius: 0,
      },
    ],
  });
  
    const chartOpts: ChartOptions<"line"> = {
     responsive: true,
    animation: false,            // literal false, type-safe
    maintainAspectRatio: false,
};




  return (
    <div
      style={{
        padding: 16,
        background: "#0a1020",
        color: "#e2e8f0",
        minHeight: "100vh",
        fontFamily: "system-ui, sans-serif",
      }}
    >
      <NavBar tab={tab} setTab={setTab} />

      {/* DASHBOARD */}
      {tab === "dashboard" && (
        <>
          {/* charts grid */}
          <section
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(2, 1fr)",
              gap: 16,
              marginBottom: 16,
            }}
          >
            <div style={card}>
              <div style={{ height: 260 }}>
                <Line data={mkData("Temperature (°C)", temp.data, "#ef4444")} options={chartOpts} />
              </div>
            </div>
            <div style={card}>
              <div style={{ height: 260 }}>
                <Line data={mkData("Pressure (hPa)", press.data, "#3b82f6")} options={chartOpts} />
              </div>
            </div>
            <div style={card}>
              <div style={{ height: 260 }}>
                <Line data={mkData("Humidity (%)", hum.data, "#22c55e")} options={chartOpts} />
              </div>
            </div>
            <div style={card}>
              <div style={{ height: 260 }}>
                <Line data={mkData("Light", light.data, "#facc15")} options={chartOpts} />
              </div>
            </div>

            {/* Three separate gas channels */}
            <div style={card}>
              <div style={{ height: 260 }}>
                <Line data={mkData("Oxidising (ppm)", oxidising.data, "#22c55e")} options={chartOpts} />
              </div>
            </div>
            <div style={card}>
              <div style={{ height: 260 }}>
                <Line data={mkData("Reducing (ppm)", reducing.data, "#ec4899")} options={chartOpts} />
              </div>
            </div>
            <div style={card}>
              <div style={{ height: 260 }}>
                <Line data={mkData("NH₃ (ppm)", nh3.data, "#a855f7")} options={chartOpts} />
              </div>
            </div>
          </section>

          {/* detection + pose */}
          <section style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <div style={card}>
              <h3 style={{ marginTop: 0 }}>Latest Detection</h3>
              {det ? (
                <div style={{ display: "grid", gridTemplateColumns: "200px 1fr", gap: 12 }}>
                  {/* eslint-disable-next-line */}
                  <img
                    src={det.image_url}
                    alt="det"
                    style={{
                      width: 200,
                      height: 140,
                      objectFit: "cover",
                      borderRadius: 8,
                      border: "1px solid #334155",
                    }}
                  />
                  <div style={{ fontSize: 14 }}>
                    <div><b>Frame:</b> {det.frame_id}</div>
                    <div><b>Aruco:</b> {det.aruco_id ?? "-"}</div>
                    <div><b>Valve:</b> {det.valve_state ?? "-"}</div>
                    <div><b>Conf:</b> {det.conf ?? "-"}</div>
                    <div><b>Time:</b> {new Date(det.ts).toLocaleTimeString()}</div>
                  </div>
                </div>
              ) : (
                <em style={{ color: "#94a3b8" }}>No detection yet</em>
              )}
            </div>

            <div style={card}>
              <h3 style={{ marginTop: 0 }}>Pose</h3>
              {pose ? (
                <div style={{ display: "flex", gap: 24, fontSize: 18 }}>
                  <div><b>x:</b> {pose.x.toFixed(2)} m</div>
                  <div><b>y:</b> {pose.y.toFixed(2)} m</div>
                  <div><b>z:</b> {pose.z.toFixed(2)} m</div>
                  <div style={{ fontSize: 12, opacity: 0.7, alignSelf: "end" }}>
                    {new Date(pose.ts).toLocaleTimeString()}
                  </div>
                </div>
              ) : (
                <em style={{ color: "#94a3b8" }}>No pose yet</em>
              )}
            </div>
          </section>
        </>
      )}

      {/* VIDEO */}
      {tab === "video" && (
        <section style={card}>
          <VideoStream url={STREAM_URL} />
          <div style={{ color: "#94a3b8", fontSize: 12, marginTop: 8 }}>
            Stream: <code>{STREAM_URL}</code>
          </div>
        </section>
      )}

      {/* LOGS + HISTORY */}
      {tab === "logs" && (
        <section style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          <SystemLogs base={BASE} token={token} />
          <HistoryTable base={BASE} token={token} />
        </section>
      )}

      {/* HEALTH */}
      {tab === "health" && (
        <section>
          <HealthPanel base={BASE} />
        </section>
      )}

      <footer style={{ opacity: 0.7, fontSize: 12, marginTop: 8 }}>
        © 2025 WebVis Project · Group 23
      </footer>
    </div>
  );
}

/* small shared style */
const card: React.CSSProperties = {
  background: "#0b1220",
  padding: 12,
  borderRadius: 12,
  border: "1px solid #263142",
};
