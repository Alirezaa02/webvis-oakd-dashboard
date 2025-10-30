import { Router } from 'express'
import { pool } from '../db/pool.js'
import { SensorSchema } from '../types/schemas.js'
import { validateBody } from '../middleware/validate.js'
import { requireAuth } from '../middleware/auth.js'
import { broadcast } from '../ws/live.js'

export const sensorsRouter = Router()


sensorsRouter.post('/', requireAuth, validateBody(SensorSchema), async (req, res) => {
  const d = (req as any).data

  // Insert reading
  await pool.query(
    'INSERT INTO sensor_readings (ts, temp, pressure, humidity, light, gas) VALUES (?, ?, ?, ?, ?, ?)',
    [d.ts, d.temp ?? null, d.pressure ?? null, d.humidity ?? null, d.light ?? null, d.gas ?? null]
  )

  // Live push
  broadcast({ kind: 'sensor', data: d })


  const now = Date.now()
  const rt = now - d.ts
  await pool.query(
    'INSERT INTO ops_log (ts, level, message) VALUES (?, ?, ?)',
    [now, rt <= 4000 ? 'INFO' : 'WARN', `ingest:${req.path} rt_ms=${rt}`]
  )

  res.status(201).json({ ok: true })
})

// GET /api/sensors/latest
sensorsRouter.get('/latest', requireAuth, async (_req, res) => {
  const [rows] = await pool.query('SELECT * FROM sensor_readings ORDER BY ts DESC LIMIT 60')
  res.json(rows)
})
