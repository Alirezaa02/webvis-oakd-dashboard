import mysql from 'mysql2/promise'

export const pool = mysql.createPool({
  host: process.env.DB_HOST,
  port: Number(process.env.DB_PORT ?? 3306),
  user: process.env.DB_USER,
  password: process.env.DB_PASS,
  database: process.env.DB_NAME,
  connectionLimit: 10,
  multipleStatements: true, 
})

export async function pingDB() {
  const conn = await pool.getConnection()
  try {
    await conn.ping()
  } finally {
    conn.release()
  }
}
