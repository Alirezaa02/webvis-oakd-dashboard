import type { WebSocketServer } from 'ws'

let wssRef: WebSocketServer | null = null

export function attachLiveWS(wss: WebSocketServer) {
  wssRef = wss
  wss.on('connection', (ws) => {
    ws.send(JSON.stringify({ kind: 'hello', ts: Date.now() }))
  })
}

export function broadcast(payload: unknown) {
  if (!wssRef) return
  const data = JSON.stringify(payload)
  for (const client of wssRef.clients) {
    if ((client as any).readyState === 1) client.send(data)
  }
}
