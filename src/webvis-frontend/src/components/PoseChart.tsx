//import React, { useEffect, useRef, useState } from "react";

import { useEffect, useRef, useState } from "react";
import { onWSMessage } from "../lib/ws";

type Pose = { ts:number, x?:number, y?:number, z?:number };

export default function PoseChart() {
  const [hist, setHist] = useState<Pose[]>([]);
  const canvasRef = useRef<HTMLCanvasElement>(null);

useEffect(() => {
  return onWSMessage(msg => {
    if (msg?.kind === "pose") setHist(h => {
      const a = [...h, msg.data];
      if (a.length > 180) a.shift();
      return a;
    });
  });
}, []);


  useEffect(() => {
    const c = canvasRef.current; if (!c) return;
    const ctx = c.getContext("2d"); if (!ctx) return;
    const W = c.width = c.clientWidth, H = c.height = 160;
    ctx.fillStyle="#0b1220"; ctx.fillRect(0,0,W,H);

    const draw = (key:string, color:string, yoff:number) => {
      const vals = hist.map(p => (p as any)[key] ?? 0);
      if (vals.length < 2) return;
      const min = Math.min(...vals), max = Math.max(...vals);
      ctx.strokeStyle=color; ctx.lineWidth=2; ctx.beginPath();
      vals.forEach((v,i)=>{ const x=(i/(vals.length-1))*(W-10)+5; const y=H-12-((v-min)/(max-min||1))*(H-28); i?ctx.lineTo(x,y):ctx.moveTo(x,y); });
      ctx.stroke();
      ctx.fillStyle="#94a3b8"; ctx.fillText(`${key}: min ${min.toFixed(2)} max ${max.toFixed(2)}`, 8, yoff);
    };

    draw("x", "#60a5fa", 14);
    draw("y", "#f97316", 28);
    draw("z", "#22c55e", 42);
  }, [hist]);

  return (
    <div style={card}>
      <h3 style={h3}>Pose (x,y,z)</h3>
      <canvas ref={canvasRef} style={{width:"100%", height:160}} />
    </div>
  );
}
const card = { background:"#0b1220", border:"1px solid #263142", borderRadius:12, padding:12, color:"#e2e8f0" };
const h3 = { margin:0, marginBottom:8 };
