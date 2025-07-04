import { neon } from '@netlify/neon'

/**
 * GET  /.netlify/functions/leaderboard
 * → returns top 10 starred datasets
 */
export async function handler() {
  const sql = neon()

  // fetch top 10 by stars
  const rows = await sql`
    SELECT dataset_name, stars
      FROM dataset_stars
     ORDER BY stars DESC
     LIMIT 10
  `

  return {
    statusCode: 200,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(rows),
  }
}
