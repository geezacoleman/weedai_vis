import { neon } from '@netlify/neon'

export async function handler() {
  const sql = neon()
  const rows = await sql`
    SELECT dataset_name, stars
      FROM dataset_stars
     ORDER BY stars DESC
     LIMIT 10
  `
  return {
    statusCode: 200,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(rows)
  }
}
