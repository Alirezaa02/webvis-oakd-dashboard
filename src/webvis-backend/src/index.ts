import 'dotenv/config'
import express from 'express'
import cors from 'cors'
import helmet from 'helmet'
import pino from 'pino'
import pinoHttp from 'pino-http'
import rateLimit from 'express-rate-limit'
import { createServer } from 'http'
import { WebSocketServer } from 'ws'
import { createProxyMiddleware } from 'http-proxy-middleware'

import { authRouter } from './routes/auth.js'
import { sensorsRouter } from './routes/sensors.js'
import { detectionsRouter } from './routes/detections.js'
import { poseRouter } from './routes/pose.js'
import { logsRouter } from './routes/logs.js'
import { attachLiveWS, broadcast } from './ws/live.js'

const app = express()
const logger = pino({ level: process.env.NODE_ENV === 'production' ? 'info' : 'debug' })

app.set('trust proxy', true) // good practice behind proxies

/* ----------------------- MJPEG proxy: /video_feed -> Flask:5052 ----------------------- */
/* Put this BEFORE body parsers/routers so nothing eats the stream */
app.use(
  '/video_feed',
  createProxyMiddleware({
    target: 'http://127.0.0.1:5052',
    changeOrigin: true,
    ws: false,                 // MJPEG is plain HTTP, not websockets
    xfwd: true,
    proxyTimeout: 30_000,      // keep proxy alive
    timeout: 30_000,
    selfHandleResponse: false, // let http-proxy stream the bytes
    logLevel: 'silent',
    onProxyRes(proxyRes, req, res) {
      // ensure browser treats it as MJPEG stream & never caches
      res.setHeader('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
      res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate')
      res.setHeader('Pragma', 'no-cache')
      res.setHeader('Expires', '0')
    },
  })
)
/* -------------------------------------------------------------------------------------- */

app.use(pinoHttp({ logger }))
app.use(helmet())
app.use(cors({ origin: process.env.CORS_ORIGIN?.split(',') ?? true, credentials: true }))
app.use(express.json({ limit: '10mb' }))

const ingestLimiter = rateLimit({ windowMs: 10_000, max: 200, standardHeaders: true })
app.use('/api', ingestLimiter)

/* keep /health simple JSON */
app.get('/health', (_req, res) => res.json({ status: 'ok', now: Date.now() }))

/* routers */
app.use('/auth', authRouter)
app.use('/api/sensors', sensorsRouter)
app.use('/api/detections', detectionsRouter)
app.use('/api/pose', poseRouter)
app.use('/api/logs', logsRouter)

/* server + WS */
const server = createServer(app)
const wss = new WebSocketServer({ server, path: '/ws/live' })
attachLiveWS(wss)

const PORT = Number(process.env.PORT ?? 5000)
server.listen(PORT, '0.0.0.0', () => {
  logger.info({ PORT }, 'webvis backend listening on all interfaces')
})

/* demo heartbeat */
setInterval(() => {
  broadcast({ kind: 'tick', ts: Date.now() })
}, 5000)
