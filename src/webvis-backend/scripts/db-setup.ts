// scripts/db-setup.ts
import { config } from 'dotenv'
import path from 'path'
import fs from 'fs/promises'

// Load .env from the CURRENT WORKING DIRECTORY (project root where you run npm)
const envPath = path.join(process.cwd(), '.env')
console.log('Attempting to load .env from:', envPath)
config({ path: envPath })

// Print to verify env actually loaded
console.log('ENV check:', {
  DB_HOST: process.env.DB_HOST,
  DB_USER: process.env.DB_USER,
  DB_NAME: process.env.DB_NAME
})

// Import AFTER env is loaded
const { pool } = await import('../src/db/pool.js')

async function main() {
  // load schema and create tables
  const sql = await fs.readFile(new URL('../src/db/schema.sql', import.meta.url), 'utf8')
  await pool.query(sql)

  // seed admin user
  const bcrypt = await import('bcryptjs')
  const hash = await bcrypt.default.hash('admin', 10)
  await pool.query(
    'INSERT IGNORE INTO users (id, username, pass_hash, role) VALUES (1, ?, ?, ?)',
    ['admin', hash, 'admin']
  )
  console.log('DB ready. Admin user: admin / admin')
  process.exit(0)
}

main().catch((e) => {
  console.error(e)
  process.exit(1)
})
