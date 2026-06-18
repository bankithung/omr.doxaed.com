import { api } from "@/api/client"

// Derive the media origin from VITE_API_BASE_URL by stripping /api/v1
function getMediaOrigin() {
  const base = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1"
  // Strip trailing /api/v1 (with or without trailing slash)
  return base.replace(/\/api\/v1\/?$/, "")
}

/**
 * Converts a relative /media/... path to an absolute URL using the API origin.
 */
export function mediaUrl(path) {
  if (!path) return ""
  if (path.startsWith("http://") || path.startsWith("https://")) return path
  const origin = getMediaOrigin()
  return `${origin}${path.startsWith("/") ? "" : "/"}${path}`
}

// Roster API
export const listRosters = () =>
  api.get("/rosters/").then((r) => r.data)

export const createRoster = (d) =>
  api.post("/rosters/", d).then((r) => r.data)

export const getRoster = (id) =>
  api.get(`/rosters/${id}/`).then((r) => r.data)

export const addCount = (id, count) =>
  api.post(`/rosters/${id}/add_count/`, { count }).then((r) => r.data)

// Student API
export const listStudents = (rosterId) =>
  api.get("/students/", { params: { roster: rosterId } }).then((r) => r.data)

export const addStudent = (d) =>
  api.post("/students/", d).then((r) => r.data)

// OMR Sheet API
export const generateSheets = (d) =>
  api.post("/omr/generate/", d).then((r) => r.data)

export const listSheets = (testId) =>
  api.get("/omr/sheets/", { params: { test: testId } }).then((r) => r.data)

/**
 * Fetches an authenticated API endpoint that returns a PDF blob, then
 * triggers a browser download. Used for question-paper endpoints which
 * are auth-gated (NOT served via /media/).
 *
 * @param {string} apiPath   - Absolute URL or path relative to the API base
 *                             (e.g. "http://localhost:8000/api/v1/omr/tests/3/question-papers/")
 * @param {string} filename  - Downloaded file name
 */
export async function downloadAuthedBlob(apiPath, filename) {
  // Derive a path that the axios api client understands.
  // If the URL is absolute (starts with http/https), strip the baseURL prefix so
  // axios doesn't double-up. Otherwise treat it as a relative path directly.
  const base = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1"
  let path = apiPath
  if (path.startsWith(base)) {
    path = path.slice(base.length)
  } else if (path.startsWith("http://") || path.startsWith("https://")) {
    // Absolute URL from a different origin — unlikely but handle gracefully
    // by stripping up to /api/v1 (same approach as mediaUrl)
    const marker = "/api/v1"
    const idx = path.indexOf(marker)
    if (idx !== -1) path = path.slice(idx + marker.length)
  }

  const res = await api.get(path, { responseType: "blob" })
  const url = URL.createObjectURL(res.data)
  const a = document.createElement("a")
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
