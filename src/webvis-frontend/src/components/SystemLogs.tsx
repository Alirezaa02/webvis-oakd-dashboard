import { useEffect, useMemo, useState } from "react";

type LogRow = { ts: number; level: "INFO" | "WARN" | "ERROR"; message: string };

export function SystemLogs({ base, token }: { base: string; token?: string }) {
  const [rows, setRows] = useState<LogRow[]>([]);
  const [error, setError] = useState<string>("");

  const headers = useMemo(() => {
    const h: Record<string, string> = {};
    if (token) h.Authorization = `Bearer ${token}`;
    return h;
  }, [token]);

  async function load() {
    setError("");
    try {
      const r = await fetch(`${base.replace(/\/+$/, "")}/api/logs/recent`, { headers });
      if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
      const j = (await r.json()) as LogRow[];
      setRows(j);
    } catch (e: any) {
      setError(String(e?.message || e));
    }
  }

  useEffect(() => {
    load();
    const t = setInterval(load, 5000); // poll every 5s
    return () => clearInterval(t);
  }, [base, headers]);

  return (
    <div style={card}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <h3 style={{ margin: 0 }}>System Logs (latest)</h3>
        <button onClick={load} style={btn}>Refresh</button>
        <span style={{ marginLeft: "auto", fontSize: 12, opacity: 0.8 }}>
          {token ? "🔒 authed" : "🔓 no token"}
        </span>
      </div>
      {error && <div style={err}>{error}</div>}
      <div style={{ maxHeight: 320, overflow: "auto", marginTop: 8 }}>
        <table style={table}>
          <thead>
            <tr>
              <th>Time</th>
              <th>Level</th>
              <th>Message</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr>
                <td colSpan={3} style={{ color: "#94a3b8" }}>
                  No log rows yet
                </td>
              </tr>
            )}
            {rows.map((r, i) => (
              <tr key={i}>
                <td>{new Date(r.ts).toLocaleTimeString()}</td>
                <td style={{ color: colorFor(r.level) }}>{r.level}</td>
                <td style={{ whiteSpace: "pre-wrap" }}>{r.message}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function colorFor(level: LogRow["level"]) {
  if (level === "ERROR") return "#f87171";
  if (level === "WARN") return "#facc15";
  return "#93c5fd";
}

const card: React.CSSProperties = {
  background: "#0b1220",
  padding: 12,
  borderRadius: 12,
  border: "1px solid #263142",
  minHeight: 200,
};

const table: React.CSSProperties = {
  width: "100%",
  borderCollapse: "collapse",
  fontSize: 14,
  color: "#e2e8f0",
};

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
