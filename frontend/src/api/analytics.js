import { api } from "@/api/client"

export const getTestAnalytics = (testId) =>
  api.get(`/analytics/test/${testId}/`).then((r) => r.data)

export const getImprovement = (testId) =>
  api.get(`/analytics/test/${testId}/improvement/`).then((r) => r.data)

export const getStudentDetail = (testId, studentId) =>
  api.get(`/analytics/test/${testId}/student/${studentId}/`).then((r) => r.data)

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
