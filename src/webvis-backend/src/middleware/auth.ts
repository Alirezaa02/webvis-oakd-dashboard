import type { Request, Response, NextFunction } from 'express'
import jwt from 'jsonwebtoken'

export interface JWTPayload { sub: string; role: 'admin' | 'user' }

export function requireAuth(req: Request, res: Response, next: NextFunction) {
  const hdr = req.headers.authorization
  if (!hdr?.startsWith('Bearer ')) return res.status(401).json({ error: 'missing token' })
  const token = hdr.slice(7)
  try {
    const payload = jwt.verify(token, process.env.JWT_SECRET!) as JWTPayload
    ;(req as any).user = payload
    next()
  } catch {
    return res.status(401).json({ error: 'invalid token' })
  }
}
