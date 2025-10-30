import { useEffect, useState } from "react";
import { onWSMessage } from "../lib/ws";

export default function LiveStatus() {
  const [lastTs, setLastTs] = useState<number | null>(null);
  const [count, setCount] = useState(0);

  useEffect(() => {
    return onWSMessage((msg: any) => {
      if (msg?.kind === "sensor" && msg?.data?.ts) {
        setLastTs(Number(msg.data.ts));
        setCount(c => c + 1);
      }
    });
  }, []);

  const age = lastTs ? Math.round((Date.now() - lastTs) / 1000) : null;
  const ok = lastTs && age! < 5;

  return (
    <div style={{display:"flex",gap:12,alignItems:"center",fontSize:13,opacity:0.9}}>
      <span style={{
        width:10,height:10,borderRadius:9999,
        background: ok ? "#22c55e" : "#ef4444",
        boxShadow: ok ? "0 0 8px #22c55e" : "0 0 8px #ef4444"
      }} />
      <span>Live {ok ? "connected" : "idle"}</span>
      <span>• last update: {lastTs ? `${age}s ago` : "—"}</span>
      <span>• msgs: {count}</span>
    </div>
  );
}
