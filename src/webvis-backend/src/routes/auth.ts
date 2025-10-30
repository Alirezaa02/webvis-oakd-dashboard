import { Router } from 'express'
import jwt from 'jsonwebtoken'
import bcrypt from 'bcryptjs'
import { pool } from '../db/pool.js'

export const authRouter = Router()

authRouter.post('/login', async (req, res) => {
  const { username, password } = req.body as { username?: string; password?: string }
  if (!username || !password) return res.status(400).json({ error: 'missing fields' })
  const [rows] = await pool.query('SELECT id, username, pass_hash, role FROM users WHERE username=?', [username])
  const user = (rows as any[])[0]
  if (!user) return res.status(401).json({ error: 'invalid credentials' })
  const ok = await bcrypt.compare(password, user.pass_hash)
  if (!ok) return res.status(401).json({ error: 'invalid credentials' })
  const token = jwt.sign({ sub: String(user.id), role: user.role }, process.env.JWT_SECRET!, { expiresIn: '2h' })
  res.json({ token })
})
