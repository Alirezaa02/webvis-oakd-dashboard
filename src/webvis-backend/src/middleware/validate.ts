import type { Request, Response, NextFunction } from 'express'
import type { ZodSchema } from 'zod'

export function validateBody<T>(schema: ZodSchema<T>) {
  return (req: Request, res: Response, next: NextFunction) => {
    const parsed = schema.safeParse(req.body)
    if (!parsed.success) {
      return res.status(400).json({ error: 'invalid body', issues: parsed.error.issues })
    }
    ;(req as any).data = parsed.data
    next()
  }
}
