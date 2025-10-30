//import React, { useEffect, useMemo, useRef, useState } from "react";
import React, { useEffect, useMemo, useState } from "react";
import {
  Chart as ChartJS, LineElement, CategoryScale, LinearScale, PointElement, Legend, Tooltip
} from "chart.js";
import { Line } from "react-chartjs-2";

ChartJS.register(LineElement, CategoryScale, LinearScale, PointElement, Legend, Tooltip);

// Where to fetch data from:
// - If you use Option A (pure static), set VITE_DATA_URL (or REACT_APP_DATA_URL) to your teammate’s endpoint.
// - If you use Option B (Flask proxy), leave it as "/api/sensors".
const DATA_URL = import.meta.env.VITE_DATA_URL || "/api/sensors";

type Sensor = {
  ts: number;
  temp?: number;
  pressure?: number;
  humidity?: number;
  light?: number;
  oxidising?: number;
  reducing?: number;   // preferred
  reduction?: number;  // legacy alias accepted
  nh3?: number;
};

export default function GasChannels() {
  const [hist, setHist] = useState<Sensor[]>([]);
  const [err, setErr] = useState<string>("");

  // Poll teammate JSON every 2s. It can be:
  // - a single object { ts, oxidising, reducing|reduction, nh3, ... }
  // - or an array of recent samples [{...}, {...}, ...]
  useEffect(() => {
    let stop = false;

    async function tick() {
      try {
        const r = await fetch(DATA_URL, { cache: "no-store" });
        if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
        const j = await r.json();

        if (stop) return;

        const incoming: Sensor[] = Array.isArray(j) ? j : [j];

        // normalise “reduction” -> “reducing”
        const norm = incoming.map(d => ({
          ...d,
          reducing: d.reducing ?? d.reduction,
        }));

        setHist(prev => {
          const combined = [...prev, ...norm].slice(-180); // keep last ~180 points
          // Deduplicate by ts if needed
          const seen = new Set<number>();
          const dedup = combined.filter(s => {
            if (!s.ts) return true;
            if (seen.has(s.ts)) return false;
            seen.add(s.ts);
            return true;
          });
          return dedup;
        });
        setErr("");
      } catch (e: any) {
        setErr(e?.message || String(e));
      }
    }

    tick();
    const id = setInterval(tick, 2000);
    return () => { stop = true; clearInterval(id); };
  }, []);

  const labels = useMemo(
    () => hist.map(d => new Date(d.ts || Date.now()).toLocaleTimeString()),
    [hist]
  );

  const oxi = hist.map(d => d.oxidising ?? null);
  const red = hist.map(d => (d.reducing ?? d.reduction ?? null));
  const a_nh3 = hist.map(d => d.nh3 ?? null);

  const mkData = (label: string, series: (number | null)[]) => ({
    labels,
    datasets: [{ label, data: series }]
  });

  const opts: any = { responsive: true, maintainAspectRatio: false };

  const latest = hist[hist.length - 1];

  return (
    <div style={{ display: "grid", gap: 12 }}>
      {/* Latest tiles */}
      <div style={{ display: "grid", gap: 12, gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))" }}>
        <Tile label="Oxidising" val={latest?.oxidising} unit="kΩ" />
        <Tile label="Reducing"  val={latest?.reducing ?? latest?.reduction} unit="kΩ" />
        <Tile label="NH₃"       val={latest?.nh3} unit="kΩ" />
      </div>

      {/* Three separate charts */}
      <Card title="Oxidising (kΩ)">
        <div style={{ height: 260 }}><Line data={mkData("Oxidising", oxi)} options={opts} /></div>
      </Card>
      <Card title="Reducing (kΩ)">
        <div style={{ height: 260 }}><Line data={mkData("Reducing", red)} options={opts} /></div>
      </Card>
      <Card title="NH₃ (kΩ)">
        <div style={{ height: 260 }}><Line data={mkData("NH₃", a_nh3)} options={opts} /></div>
      </Card>

      {err && <div style={{ color: "#ef4444", fontSize: 13 }}>Error: {err}</div>}
    </div>
  );
}

function Card({ title, children }:{ title:string; children:React.ReactNode }) {
  return (
    <div style={{ border: "1px solid #e5e7eb", borderRadius: 12, padding: 12, background: "#fff" }}>
      <div style={{ fontWeight: 600, marginBottom: 6 }}>{title}</div>
      {children}
    </div>
  );
}

function Tile({ label, val, unit }:{ label:string; val?:number; unit?:string }) {
  return (
    <div style={{ border: "1px solid #e5e7eb", borderRadius: 12, padding: 12, background: "#fff", textAlign: "center" }}>
      <div style={{ fontSize: 12, color: "#64748b" }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 700 }}>
        {typeof val === "number" ? val.toFixed(2) : "—"} {unit}
      </div>
    </div>
  );
}
