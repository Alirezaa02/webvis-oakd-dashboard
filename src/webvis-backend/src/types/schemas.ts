import { z } from 'zod'

export const SensorSchema = z.object({
  ts: z.number().int().nonnegative(),
  temp: z.number().optional(),
  pressure: z.number().optional(),
  humidity: z.number().optional(),
  light: z.number().optional(),
  gas: z.number().optional()
})

export const DetectionSchema = z.object({
  ts: z.number().int().nonnegative(),
  frame_id: z.string().min(1),
  image_url: z.string().url().or(z.string().startsWith('data:image/')),
  aruco_id: z.number().int().optional(),
  valve_state: z.enum(['open', 'closed']).optional(),
  conf: z.number().min(0).max(1).optional(),
  bbox: z.any().optional()
})

export const PoseSchema = z.object({
  ts: z.number().int().nonnegative(),
  x: z.number(),
  y: z.number(),
  z: z.number()
})

export type SensorDTO = z.infer<typeof SensorSchema>
export type DetectionDTO = z.infer<typeof DetectionSchema>
export type PoseDTO = z.infer<typeof PoseSchema>
