import React, { useMemo } from "react";

/**
 * Zero-dependency semicircle gauge (SVG).
 * Range defaults: 950–1050 hPa (typical sea-level).
 */
export function PressureGauge({ hPa, min = 950, max = 1050 }: { hPa?: number; min?: number; max?: number }) {
  const pct = useMemo(() => {
    if (typeof hPa !== "number") return 0.5;
    const clamped = Math.max(min, Math.min(max, hPa));
    return (clamped - min) / (max - min); // 0..1
  }, [hPa, min, max]);

  // Map percent to angle (-90° to +90°)
  const angle = -90 + pct * 180;

  const size = 220;
  const cx = size / 2;
  const cy = size / 2 + 40; // push arc down a little
  const r = 90;

  // Arc endpoints
  const start = polar(cx, cy, r, -90);
  const end   = polar(cx, cy, r,  90);
  const largeArc = 0;
  const sweep = 1;

  const needle = polar(cx, cy, r - 8, angle);

  return (
    <div style={{ background: "#0f172a", border: "1px solid #1f2a44", borderRadius: 12, padding: 12 }}>
      <h3 style={{ marginTop: 0, color: "#e5e7eb" }}>Pressure Gauge</h3>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ display: "block", margin: "0 auto" }}>
        {/* background arc */}
        <path
          d={`M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} ${sweep} ${end.x} ${end.y}`}
          stroke="#1f2a44"
          strokeWidth="16"
          fill="none"
          strokeLinecap="round"
        />
        {/* foreground arc (colored) */}
        <path
          d={arcPath(cx, cy, r, -90, angle)}
          stroke="#3b82f6"
          strokeWidth="16"
          fill="none"
          strokeLinecap="round"
        />
        {/* ticks */}
        {[-90, -45, 0, 45, 90].map((a, i) => {
          const p1 = polar(cx, cy, r + 0, a);
          const p2 = polar(cx, cy, r + 12, a);
          return <line key={i} x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y} stroke="#334155" strokeWidth="2" />;
        })}
        {/* needle */}
        <line x1={cx} y1={cy} x2={needle.x} y2={needle.y} stroke="#e5e7eb" strokeWidth="3" />
        <circle cx={cx} cy={cy} r="5" fill="#e5e7eb" />
        {/* labels */}
        <text x={cx} y={cy + 28} fill="#94a3b8" fontSize="12" textAnchor="middle">
          {min} hPa
        </text>
        <text x={cx} y={cy - r - 16} fill="#94a3b8" fontSize="12" textAnchor="middle">
          {typeof hPa === "number" ? `${hPa.toFixed(1)} hPa` : "—"}
        </text>
        <text x={cx} y={cy + 44} fill="#94a3b8" fontSize="12" textAnchor="middle">
          {max} hPa
        </text>
      </svg>
    </div>
  );
}

function polar(cx: number, cy: number, r: number, deg: number) {
  const rad = (deg * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

function arcPath(cx: number, cy: number, r: number, startDeg: number, endDeg: number) {
  const s = polar(cx, cy, r, startDeg);
  const e = polar(cx, cy, r, endDeg);
  const largeArc = endDeg - startDeg > 180 ? 1 : 0;
  const sweep = 1;
  return `M ${s.x} ${s.y} A ${r} ${r} 0 ${largeArc} ${sweep} ${e.x} ${e.y}`;
}
