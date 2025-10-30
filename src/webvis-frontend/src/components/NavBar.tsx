//import React from "react";

type Tab = "dashboard" | "video" | "logs" | "health";

export function NavBar({ tab, setTab }: { tab: Tab; setTab: (t: Tab) => void }) {
  const tabs: [Tab, string][] = [
    ["dashboard", "📊 Dashboard"],
    ["video", "🎥 Video"],
    ["logs", "🧾 Logs"],
    ["health", "💚 Health"],
  ];

  return (
    <nav
      style={{
        display: "flex",
        gap: 8,
        background: "#0b1220",
        border: "1px solid #263142",
        borderRadius: 12,
        padding: 8,
        marginBottom: 16,
      }}
    >
      {tabs.map(([key, label]) => (
        <button
          key={key}
          onClick={() => setTab(key)}
          style={{
            flex: 1,
            padding: "10px 0",
            borderRadius: 8,
            border: "none",
            cursor: "pointer",
            fontWeight: tab === key ? 600 : 400,
            color: tab === key ? "#fff" : "#cbd5e1",
            background: tab === key ? "#1d4ed8" : "transparent",
            transition: "background 0.2s ease",
          }}
        >
          {label}
        </button>
      ))}
    </nav>
  );
}
