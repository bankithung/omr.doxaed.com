/**
 * Public (no-auth) API client for the student-facing result portal.
 * IMPORTANT: Uses a plain axios instance — NO JWT/auth interceptors.
 */
import axios from "axios"

const baseURL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1"

const publicApi = axios.create({ baseURL })

/**
 * GET /public/r/<slug>/
 * Returns { test_title, org_name, access_mode, show_leaderboard }
 * Throws with status 404 if not published.
 */
export function getPortalMeta(slug) {
  return publicApi.get(`/public/r/${slug}/`).then((r) => r.data)
}

/**
 * POST /public/r/<slug>/lookup/
 * Body: { roll_number, access_code? }
 * Returns { name, roll_number, score, max_score, percentile, rank }
 * Throws with status 403 for invalid access code, 404 for no result.
 */
export function lookupResult(slug, rollNumber, accessCode) {
  const body = { roll_number: rollNumber }
  if (accessCode) body.access_code = accessCode
  return publicApi.post(`/public/r/${slug}/lookup/`, body).then((r) => r.data)
}

/**
 * GET /public/r/<slug>/leaderboard/
 * Returns [{ rank, name, score, percentile }]
 * Throws with status 404 unless published + show_leaderboard.
 */
export function getLeaderboard(slug) {
  return publicApi.get(`/public/r/${slug}/leaderboard/`).then((r) => r.data)
}
