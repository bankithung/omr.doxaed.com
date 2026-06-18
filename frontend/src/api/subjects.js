import { api } from "@/api/client"

// ─── Subjects (per class) ───────────────────────────────────────────────────────

export const listSubjects = (classId) =>
  api.get("/subjects/", { params: { class_group: classId } }).then((r) => r.data)

export const createSubject = (d) =>
  api.post("/subjects/", d).then((r) => r.data)

export const deleteSubject = (id) =>
  api.delete(`/subjects/${id}/`).then((r) => r.data)
