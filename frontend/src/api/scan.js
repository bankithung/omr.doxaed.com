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
