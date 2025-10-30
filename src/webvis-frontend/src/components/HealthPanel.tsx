import { useEffect, useState } from "react";

type HealthResponse = { status: "ok" | "error"; now?: number };

export function HealthPanel({ base }: { base: string }) {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [latency, setLatency] = useState<number | null>(null);
  const [error, setError] = useState<string>("");

  async function ping() {
    setError("");
    try {
      const t0 = performance.now();
      const r = await fetch(`${base.replace(/\/+$/, "")}/health`, { cache: "no-store" });
      const t1 = performance.now();
      setLatency(Math.round(t1 - t0));
      if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
      const j = (await r.json()) as HealthResponse;
      setHealth(j);
    } catch (e: any) {
      setError(String(e?.message || e));
    }
  }

  useEffect(() => {
    ping();
    const t = setInterval(ping, 5000);
    return () => clearInterval(t);
  }, [base]);

  return (
    <div style={card}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <h3 style={{ margin: 0 }}>Service Health</h3>
        <button onClick={ping} style={btn}>Ping</button>
      </div>
      {error && <div style={err}>{error}</div>}
      <div style={{ display: "grid", gap: 8, marginTop: 8 }}>
        <div>
          <b>Status:</b>{" "}
          {health?.status === "ok" ? <span style={{ color: "#22c55e" }}>OK</span> : <span style={{ color: "#f87171" }}>ERROR</span>}
        </div>
        <div>
          <b>Latency:</b> {latency != null ? `${latency} ms` : "—"}
        </div>
        <div>
          <b>Server time:</b> {health?.now ? new Date(health.now).toLocaleTimeString() : "—"}
        </div>
      </div>
    </div>
  );
}

const card: React.CSSProperties = {
  background: "#0b1220",
  padding: 12,
  borderRadius: 12,
  border: "1px solid #263142",
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
