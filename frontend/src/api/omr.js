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
