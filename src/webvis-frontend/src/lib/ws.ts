// src/lib/ws.ts
let socket: WebSocket | null = null;
type Handler = (msg: any) => void;
const listeners = new Set<Handler>();

/** Connect using a FULL URL, e.g. "ws://10.88.32.129:5051/ws/live" */
export function connectWS(url: string) {
  if (socket) return () => { /* already connected */ };

  socket = new WebSocket(url);

  socket.onmessage = (ev) => {
    try {
      const j = JSON.parse(ev.data);
      listeners.forEach(h => h(j));
    } catch {
      // ignore non-JSON frames
    }
  };

  socket.onclose = () => {
    socket = null;
    // simple auto-reconnect
    setTimeout(() => connectWS(url), 1500);
  };

  // cleanup
  return () => {
    try { socket?.close(); } catch {}
    socket = null;
  };
}

/** Register a listener; returns a cleanup fn (void), NOT a boolean. */
export function onWSMessage(h: Handler) {
  listeners.add(h);
  return () => { listeners.delete(h); };
}
