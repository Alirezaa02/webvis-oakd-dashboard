import { Router } from 'express'
import { pool } from '../db/pool.js'
import { DetectionSchema } from '../types/schemas.js'
import { validateBody } from '../middleware/validate.js'
import { requireAuth } from '../middleware/auth.js'
import { broadcast } from '../ws/live.js'

export const detectionsRouter = Router()

// POST /api/detections
detectionsRouter.post('/', requireAuth, validateBody(DetectionSchema), async (req, res) => {
  const d = (req as any).data

  // Insert detection
  await pool.query(
    'INSERT INTO detections (ts, frame_id, image_url, aruco_id, valve_state, conf, bbox) VALUES (?, ?, ?, ?, ?, ?, ?)',
    [d.ts, d.frame_id, d.image_url, d.aruco_id ?? null, d.valve_state ?? null, d.conf ?? null, JSON.stringify(d.bbox ?? null)]
  )

  // Live push
  broadcast({ kind: 'detection', data: d })


  const now = Date.now()
  const rt = now - d.ts
  await pool.query(
    'INSERT INTO ops_log (ts, level, message) VALUES (?, ?, ?)',
    [now, rt <= 4000 ? 'INFO' : 'WARN', `ingest:${req.path} rt_ms=${rt}`]
  )

  res.status(201).json({ ok: true })
})

// GET /api/detections/latest
detectionsRouter.get('/latest', requireAuth, async (_req, res) => {
  const [rows] = await pool.query('SELECT * FROM detections ORDER BY ts DESC LIMIT 10')
  res.json(rows)
})
