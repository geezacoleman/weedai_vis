import { neon } from '@netlify/neon'

export async function handler() {
  const sql = neon()
  const rows = await sql`
    SELECT sb.dataset_name,
           COUNT(*) AS recent_stars
      FROM starred_by_ip AS sb
     WHERE sb.starred_at >= NOW() - INTERVAL '30 days'
     GROUP BY sb.dataset_name
     ORDER BY recent_stars DESC
     LIMIT 5
  `
  return {
    statusCode: 200,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(rows)
  }
}
