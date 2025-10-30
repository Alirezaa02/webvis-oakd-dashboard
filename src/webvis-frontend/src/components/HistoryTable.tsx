import { useEffect, useMemo, useState } from "react";

type SensorRow = {
  ts: number;
  temp?: number;
  pressure?: number;
  humidity?: number;
  light?: number;
  oxidising?: number;
  reducing?: number;
  nh3?: number;
};

export function HistoryTable({ base, token }: { base: string; token?: string }) {
  const [rows, setRows] = useState<SensorRow[]>([]);
  const [error, setError] = useState<string>("");

  const headers = useMemo(() => {
    const h: Record<string, string> = {};
    if (token) h.Authorization = `Bearer ${token}`;
    return h;
  }, [token]);

  async function load() {
    setError("");
    try {
      const r = await fetch(`${base.replace(/\/+$/, "")}/api/sensors/latest?limit=50`, { headers });
      if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
      const j = (await r.json()) as SensorRow[];
      setRows(j);
    } catch (e: any) {
      setError(String(e?.message || e));
    }
  }

  useEffect(() => {
    load();
  }, [base, headers]);

  const value = (v?: number) => (typeof v === "number" ? v.toFixed(2) : "—");

  return (
    <div style={card}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <h3 style={{ margin: 0 }}>Sensor History (latest 50)</h3>
        <button onClick={load} style={btn}>Reload</button>
      </div>

      <div style={{ overflowX: "auto", marginTop: 8 }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "#0b1220" }}>
              <th style={th}>Timestamp</th>
              <th style={th}>Time</th>
              <th style={th}>Temp (°C)</th>
              <th style={th}>Pressure (hPa)</th>
              <th style={th}>Humidity (%)</th>
              <th style={th}>Light (lux)</th>
              <th style={th}>Oxidising (kΩ)</th>
              <th style={th}>Reducing (kΩ)</th>
              <th style={th}>NH₃ (kΩ)</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.ts} style={{ borderTop: "1px solid #233045" }}>
                <td style={td}>{r.ts}</td>
                <td style={td}>{new Date(r.ts).toLocaleString()}</td>
                <td style={td}>{value(r.temp)}</td>
                <td style={td}>{value(r.pressure)}</td>
                <td style={td}>{value(r.humidity)}</td>
                <td style={td}>{value(r.light)}</td>
                <td style={td}>{value(r.oxidising)}</td>
                <td style={td}>{value(r.reducing)}</td>
                <td style={td}>{value(r.nh3)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {error && <div style={err}>Error: {error}</div>}
    </div>
  );
}

const card: React.CSSProperties = {
  background: "#0b1220",
  padding: 12,
  borderRadius: 12,
  border: "1px solid #263142",
};

const th: React.CSSProperties = { textAlign: "left", padding: 8, borderBottom: "1px solid #233045" };
const td: React.CSSProperties = { padding: 8 };

const btn: React.CSSProperties = {
  padding: "6px 10px",
  borderRadius: 8,
  border: "1px solid #1f2a44",
  background: "#0b1220",
  color: "#e5e7eb",
  cursor: "pointer",
};

const err: React.CSSProperties = {
  marginTop: 8,
  color: "#f87171",
  fontSize: 13,
};
