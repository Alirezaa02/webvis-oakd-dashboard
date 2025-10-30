import { Router } from 'express'
import { pool } from '../db/pool.js'
import { PoseSchema } from '../types/schemas.js'
import { validateBody } from '../middleware/validate.js'
import { requireAuth } from '../middleware/auth.js'
import { broadcast } from '../ws/live.js'

export const poseRouter = Router()

// POST /api/pose
poseRouter.post('/', requireAuth, validateBody(PoseSchema), async (req, res) => {
  const d = (req as any).data

  // Insert pose
  await pool.query('INSERT INTO poses (ts, x, y, z) VALUES (?, ?, ?, ?)', [d.ts, d.x, d.y, d.z])

  // Live push
  broadcast({ kind: 'pose', data: d })


  const now = Date.now()
  const rt = now - d.ts
  await pool.query(
    'INSERT INTO ops_log (ts, level, message) VALUES (?, ?, ?)',
    [now, rt <= 4000 ? 'INFO' : 'WARN', `ingest:${req.path} rt_ms=${rt}`]
  )

  res.status(201).json({ ok: true })
})

// GET /api/pose/latest
poseRouter.get('/latest', requireAuth, async (_req, res) => {
  const [rows] = await pool.query('SELECT * FROM poses ORDER BY ts DESC LIMIT 30')
  res.json(rows)
})
