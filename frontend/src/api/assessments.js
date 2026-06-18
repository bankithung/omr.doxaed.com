import { api } from "@/api/client"

export const listClasses = () =>
  api.get("/classes/").then((r) => r.data)

export const getClass = (id) =>
  api.get(`/classes/${id}/`).then((r) => r.data)

export const createClass = (d) =>
  api.post("/classes/", d).then((r) => r.data)

export const listTests = (classId) =>
  api.get("/tests/", { params: { class_group: classId } }).then((r) => r.data)

/**
 * Create a test. Accepts plain objects (JSON) or FormData (multipart, for logo upload).
 */
export const createTest = (d) => {
  const isFormData = typeof FormData !== "undefined" && d instanceof FormData
  return api.post("/tests/", d, {
    headers: isFormData ? { "Content-Type": "multipart/form-data" } : {},
  }).then((r) => r.data)
}

/**
 * Update a test. Accepts plain objects (JSON) or FormData (multipart, for logo upload).
 */
export const updateTest = (id, d) => {
  const isFormData = typeof FormData !== "undefined" && d instanceof FormData
  return api.patch(`/tests/${id}/`, d, {
    headers: isFormData ? { "Content-Type": "multipart/form-data" } : {},
  }).then((r) => r.data)
}

export const retest = (id) =>
  api.post(`/tests/${id}/retest/`).then((r) => r.data)

export const listQuestions = (testId) =>
  api.get("/questions/", { params: { test: testId } }).then((r) => r.data)

export const createQuestion = (d) =>
  api.post("/questions/", d).then((r) => r.data)
