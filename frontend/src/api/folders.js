import { api } from "@/api/client"

// ─── Folders ──────────────────────────────────────────────────────────────────

export const listFolders = () =>
  api.get("/folders/").then((r) => r.data)

export const getFolder = (id) =>
  api.get(`/folders/${id}/`).then((r) => r.data)

export const createFolder = (d) =>
  api.post("/folders/", d).then((r) => r.data)

export const updateFolder = (id, d) =>
  api.patch(`/folders/${id}/`, d).then((r) => r.data)

export const deleteFolder = (id) =>
  api.delete(`/folders/${id}/`).then((r) => r.data)

// ─── Folder shares ──────────────────────────────────────────────────────────────

export const listShares = (folderId) =>
  api.get(`/folders/${folderId}/shares/`).then((r) => r.data)

/**
 * Create a share.
 * @param {number} folderId
 * @param {object} body — {shared_with, share_scope:"member", permission} OR
 *                        {share_scope:"org", permission}
 */
export const createShare = (folderId, body) =>
  api.post(`/folders/${folderId}/shares/`, body).then((r) => r.data)

export const deleteShare = (folderId, shareId) =>
  api.delete(`/folders/${folderId}/shares/${shareId}/`).then((r) => r.data)
