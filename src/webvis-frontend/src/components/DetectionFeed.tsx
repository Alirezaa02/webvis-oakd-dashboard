//import React, { useEffect, useState } from "react";
import { useEffect, useState } from "react";
import { onWSMessage } from "../lib/ws";

type Det = {
  ts: number;
  frame_id?: string;
  image_url?: string;
  image_b64?: string; // if you choose to send base64 later
  aruco_id?: number;
  valve_state?: string;
  conf?: number;
};

export default function DetectionFeed() {
  const [items, setItems] = useState<Det[]>([]);

useEffect(() => {
  return onWSMessage(msg => {
    if (msg?.kind === "detection" || msg?.kind === "frame") {
      // ...
    }
  });
}, []);


  return (
    <div style={card}>
      <h3 style={{margin:0, marginBottom:8}}>Detections</h3>
      {items.length === 0 && <div style={{color:"#9ca3af"}}>No detections yet…</div>}
      <div style={{display:"grid", gridTemplateColumns:"repeat(auto-fit,minmax(220px,1fr))", gap:10}}>
        {items.map((d, i) => (
          <div key={i} style={it}>
            <div style={{fontSize:12, color:"#9ca3af"}}>{new Date(d.ts).toLocaleTimeString()}</div>
            {(d.image_url || d.image_b64) ? (
              <img
                src={d.image_url || `data:image/jpeg;base64,${d.image_b64}`}
                alt="det"
                style={{width:"100%", height:"auto", borderRadius:8, border:"1px solid #263142", marginTop:6}}
              />
            ) : <div style={{color:"#94a3b8"}}>no image</div>}
            <div style={{marginTop:6}}>
              <b>frame:</b> {d.frame_id ?? "-"}<br/>
              <b>aruco:</b> {d.aruco_id ?? "-"} &nbsp; <b>valve:</b> {d.valve_state ?? "-"}<br/>
              <b>conf:</b> {d.conf?.toFixed?.(2) ?? "-"}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
const card = { background:"#0b1220", border:"1px solid #263142", borderRadius:12, padding:12, color:"#e2e8f0" };
const it = { background:"#0e1726", border:"1px solid #263142", borderRadius:10, padding:10 };
