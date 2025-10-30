import { Router } from 'express'
import { pool } from '../db/pool.js'
import { requireAuth } from '../middleware/auth.js'

export const logsRouter = Router()

logsRouter.post('/', requireAuth, async (req, res) => {
  const { level = 'INFO', message = '' } = req.body ?? {}
  await pool.query('INSERT INTO ops_log (ts, level, message) VALUES (?, ?, ?)', [Date.now(), level, message])
  res.status(201).json({ ok: true })
})

logsRouter.get('/recent', requireAuth, async (_req, res) => {
  const [rows] = await pool.query('SELECT * FROM ops_log WHERE ts > ? ORDER BY ts DESC', [Date.now() - 10 * 60 * 1000])
  res.json(rows)
})
