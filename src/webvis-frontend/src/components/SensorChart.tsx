// src/components/SensorChart.tsx
import { useEffect, useRef, useState } from "react";
import { onWSMessage } from "../lib/ws";

type Sensor = {
  ts: number;
  temp?: number;
  pressure?: number;
  humidity?: number;
  light?: number;
  oxidising?: number;
  reducing?: number;
  reduction?: number; // accept legacy alias
  nh3?: number;
};

export default function SensorChart() {
  const [hist, setHist] = useState<Sensor[]>([]);
  const [latest, setLatest] = useState<Sensor | null>(null);

  const canvases = {
    temp: useRef<HTMLCanvasElement>(null),
    humidity: useRef<HTMLCanvasElement>(null),
    pressure: useRef<HTMLCanvasElement>(null),
    light: useRef<HTMLCanvasElement>(null),
    oxidising: useRef<HTMLCanvasElement>(null),
    reducing: useRef<HTMLCanvasElement>(null),
    nh3: useRef<HTMLCanvasElement>(null),
  };

useEffect(() => {
  return onWSMessage(msg => {
    if (msg?.kind === "sensor") {
      // push into local state...
    }
  });
}, []);


  function draw(c: HTMLCanvasElement | null, values: (number | undefined)[]) {
    if (!c) return;
    const ctx = c.getContext("2d"); if (!ctx) return;
    const W = (c.width = c.clientWidth);
    const H = (c.height = 160);
    ctx.clearRect(0,0,W,H);

    const ys = values.filter((v): v is number => typeof v === "number");
    if (ys.length < 2) {
      ctx.fillStyle = "#94a3b8";
      ctx.font = "12px system-ui, sans-serif";
      ctx.fillText("Waiting for data…", 10, 20);
      return;
    }
    const min = Math.min(...ys), max = Math.max(...ys);
    const pad = (max - min) * 0.1 || 1;
    const y0 = min - pad, y1 = max + pad;

    const toY = (v: number) => H - 24 - (H - 44) * ((v - y0) / (y1 - y0 || 1));
    const toX = (i: number) => 32 + (W - 42) * (i / (values.length - 1 || 1));

    ctx.strokeStyle = "#1f2a44";
    ctx.beginPath(); ctx.moveTo(32, 10); ctx.lineTo(32, H - 24); ctx.lineTo(W - 10, H - 24); ctx.stroke();

    ctx.setLineDash([4,4]); ctx.strokeStyle = "#233045";
    [y0, (y0 + y1)/2, y1].forEach(y => {
      const yy = toY(y);
      ctx.beginPath(); ctx.moveTo(32, yy); ctx.lineTo(W - 10, yy); ctx.stroke();
      ctx.fillStyle = "#9ca3af"; ctx.font = "11px system-ui, sans-serif";
      ctx.fillText(y.toFixed(2), 4, yy + 4);
    });
    ctx.setLineDash([]);

    ctx.strokeStyle = "#3b82f6";
    ctx.lineWidth = 2;
    ctx.beginPath();
    values.forEach((v, i) => {
      if (typeof v !== "number") return;
      const x = toX(i), y = toY(v);
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    });
    ctx.stroke();
  }

  useEffect(() => {
    const xs = hist;
    draw(canvases.temp.current, xs.map(d => d.temp));
    draw(canvases.humidity.current, xs.map(d => d.humidity));
    draw(canvases.pressure.current, xs.map(d => d.pressure));
    draw(canvases.light.current, xs.map(d => d.light));
    draw(canvases.oxidising.current, xs.map(d => d.oxidising));
    draw(canvases.reducing.current, xs.map(d => d.reducing ?? d.reduction));
    draw(canvases.nh3.current, xs.map(d => d.nh3));
  }, [hist]);

  return (
    <div style={{ display: "grid", gap: 12, gridTemplateColumns: "repeat(auto-fit,minmax(280px,1fr))" }}>
      <Tile label="Temperature" v={latest?.temp} unit="°C" />
      <Tile label="Humidity" v={latest?.humidity} unit="%" />
      <Tile label="Pressure" v={latest?.pressure} unit="hPa" />
      <Tile label="Light" v={latest?.light} unit="lux" />

      <Tile label="Oxidising" v={latest?.oxidising} unit="kΩ" />
      <Tile label="Reducing" v={latest?.reducing ?? latest?.reduction} unit="kΩ" />
      <Tile label="NH₃" v={latest?.nh3} unit="kΩ" />

      <div style={card}><div style={{ fontWeight: 600, color: "#e5e7eb", marginBottom: 6 }}>Oxidising</div><canvas ref={canvases.oxidising} style={{ width: "100%", height: 160 }} /></div>
      <div style={card}><div style={{ fontWeight: 600, color: "#e5e7eb", marginBottom: 6 }}>Reducing</div><canvas ref={canvases.reducing} style={{ width: "100%", height: 160 }} /></div>
      <div style={card}><div style={{ fontWeight: 600, color: "#e5e7eb", marginBottom: 6 }}>NH₃</div><canvas ref={canvases.nh3} style={{ width: "100%", height: 160 }} /></div>
    </div>
  );
}

function Tile({ label, v, unit }: { label: string; v?: number; unit?: string }) {
  return (
    <div style={tile}>
      <div style={lab}>{label}</div>
      <div style={big}>{typeof v === "number" ? v.toFixed(2) : "—"} {unit}</div>
    </div>
  );
}

const card: React.CSSProperties = { background: "#0b1220", border: "1px solid #263142", borderRadius: 12, padding: 10 };
const tile: React.CSSProperties = { ...card, textAlign: "center" };
const lab: React.CSSProperties = { fontSize: 12, color: "#9ca3af" };
const big: React.CSSProperties = { fontSize: 22, fontWeight: 700, color: "#e5e7eb" };
