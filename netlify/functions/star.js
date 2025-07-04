import { neon } from '@netlify/neon'

/**
 * POST  /.netlify/functions/star
 * Body: { name: string }
 * → increments the star count for `name`
 */
export async function handler(event) {
  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, body: 'Method Not Allowed' }
  }

  let payload
  try {
    payload = JSON.parse(event.body)
  } catch {
    return { statusCode: 400, body: 'Invalid JSON' }
  }

  const { name } = payload
  if (!name) {
    return { statusCode: 400, body: 'Missing dataset name' }
  }

  const sql = neon()     // reads NETLIFY_DATABASE_URL under the hood

  // increment (or insert+increment) in one query
  await sql`
    INSERT INTO dataset_stars (dataset_name, stars)
    VALUES (${name}, 1)
    ON CONFLICT (dataset_name)
    DO UPDATE SET
      stars = dataset_stars.stars + 1,
      last_starred = NOW()
  `

  return {
    statusCode: 200,
    body: JSON.stringify({ success: true }),
  }
}
