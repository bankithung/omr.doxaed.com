import { api } from "@/api/client"

/**
 * Upload scanned OMR files for a test.
 * @param {number|string} testId
 * @param {FileList|File[]} files
 * @returns {Promise<{batch_id: number, total: number, processed: number}>}
 */
export function uploadScan(testId, files) {
  const fd = new FormData()
  fd.append("test", testId)
  Array.from(files).forEach((f) => fd.append("files", f))
  // Let axios set the Content-Type / multipart boundary automatically
  return api.post("/omr/scan/", fd).then((r) => r.data)
}

/**
 * Get the progress of a scan batch.
 * @param {number|string} id  batch_id
 * @returns {Promise<{id: number, status: string, total: number, processed: number}>}
 */
export function getBatch(id) {
  return api.get(`/omr/scan-batches/${id}/`).then((r) => r.data)
}

/**
 * Get per-sheet correction objects for a batch.
 * @param {number|string} id  batch_id
 * @returns {Promise<Array>}  array of sheet objects
 */
export function getBatchSheets(id) {
  return api.get(`/omr/scan-batches/${id}/sheets/`).then((r) => r.data)
}

/**
 * Regrade a sheet with corrected answers.
 * @param {number|string} omrSheetId
 * @param {Object} answers  {q_pos: [labels]}
 * @param {string|null} roll  optional corrected roll
 * @param {number|null} studentId  optional corrected student_id
 * @returns {Promise<Object>}  updated student_result
 */
export function regradeSheet(omrSheetId, answers, roll = null, studentId = null) {
  const body = { answers }
  if (roll != null) body.roll = roll
  if (studentId != null) body.student_id = studentId
  return api.post(`/omr/sheets/${omrSheetId}/regrade/`, body).then((r) => r.data)
}

/**
 * Fetch the warped sheet PNG as an authenticated blob URL.
 * @param {number|string} scanJobId
 * @returns {Promise<string>}  object URL (caller must revoke when done)
 */
export async function getWarpedImageUrl(scanJobId) {
  const resp = await api.get(`/omr/scan-jobs/${scanJobId}/warped/`, {
    responseType: "blob",
  })
  return URL.createObjectURL(resp.data)
}

/**
 * List StudentResults for a test.
 * @param {number|string} testId
 * @returns {Promise<object>}  paginated or array
 */
export function listResults(testId) {
  return api.get("/results/", { params: { test: testId } }).then((r) => r.data)
}

/**
 * List open ReviewItems for a test.
 * @param {number|string} testId
 * @returns {Promise<object>}
 */
export function listReview(testId) {
  return api.get("/review/", { params: { test: testId } }).then((r) => r.data)
}

/**
 * Resolve a ReviewItem by providing the corrected marked options.
 * @param {number|string} id  review item id
 * @param {string[]} markedOptions  e.g. ["A"] or ["B","C"]
 * @returns {Promise<object>}
 */
export function resolveReview(id, markedOptions) {
  return api.post(`/review/${id}/resolve/`, { marked_options: markedOptions }).then((r) => r.data)
}
