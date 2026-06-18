import { api } from "@/api/client"

export const getTestAnalytics = (testId) =>
  api.get(`/analytics/test/${testId}/`).then((r) => r.data)

export const getImprovement = (testId) =>
  api.get(`/analytics/test/${testId}/improvement/`).then((r) => r.data)

export const getStudentDetail = (testId, studentId) =>
  api.get(`/analytics/test/${testId}/student/${studentId}/`).then((r) => r.data)

/**
 * GET /analytics/test/<testId>/publish/
 * Returns { slug, public_url, is_published, access_mode, show_names, show_leaderboard }
 */
export const getPublishSettings = (testId) =>
  api.get(`/analytics/test/${testId}/publish/`).then((r) => r.data)

/**
 * PUT /analytics/test/<testId>/publish/
 * Body: { is_published, access_mode, access_code?, show_names, show_leaderboard }
 * Returns updated publish settings.
 */
export const setPublishSettings = (testId, body) =>
  api.put(`/analytics/test/${testId}/publish/`, body).then((r) => r.data)

export async function exportResults(testId, output_format) {
  const extMap = { csv: "csv", xlsx: "xlsx", pdf: "pdf" }
  const ext = extMap[output_format] ?? output_format

  const res = await api.get(`/analytics/test/${testId}/export/`, {
    params: { output_format },
    responseType: "blob",
  })

  const url = URL.createObjectURL(res.data)
  const a = document.createElement("a")
  a.href = url
  a.download = `results.${ext}`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
