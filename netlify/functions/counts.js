import { neon } from '@netlify/neon'

export async function handler() {
  const sql = neon()
  const rows = await sql`
    SELECT dataset_name, stars
      FROM dataset_stars
  `
  const result = {}
  rows.forEach(r => { result[r.dataset_name] = r.stars })
  return {
    statusCode: 200,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(result)
  }
}
