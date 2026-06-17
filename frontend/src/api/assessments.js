import { api } from "@/api/client"

export const listClasses = () =>
  api.get("/classes/").then((r) => r.data)

export const getClass = (id) =>
  api.get(`/classes/${id}/`).then((r) => r.data)

export const createClass = (d) =>
  api.post("/classes/", d).then((r) => r.data)

export const listTests = (classId) =>
  api.get("/tests/", { params: { class_group: classId } }).then((r) => r.data)

export const createTest = (d) =>
  api.post("/tests/", d).then((r) => r.data)

export const updateTest = (id, d) =>
  api.patch(`/tests/${id}/`, d).then((r) => r.data)

export const retest = (id) =>
  api.post(`/tests/${id}/retest/`).then((r) => r.data)

export const listQuestions = (testId) =>
  api.get("/questions/", { params: { test: testId } }).then((r) => r.data)

export const createQuestion = (d) =>
  api.post("/questions/", d).then((r) => r.data)
