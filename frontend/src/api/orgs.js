import { api } from "@/api/client"

export const listOrgs = () =>
  api.get("/organizations/").then((r) => r.data)

export const createOrg = (name) =>
  api.post("/organizations/", { name }).then((r) => r.data)

export const getMembers = (orgId) =>
  api.get(`/organizations/${orgId}/members/`).then((r) => r.data)

export const invite = (orgId, email, role) =>
  api.post(`/organizations/${orgId}/invite/`, { email, role }).then((r) => r.data)

export const acceptInvite = (token) =>
  api.post("/invitations/accept/", { token }).then((r) => r.data)

export const setMemberRole = (orgId, userId, role) =>
  api.patch(`/organizations/${orgId}/members/${userId}/`, { role }).then((r) => r.data)

export const removeMember = (orgId, userId) =>
  api.delete(`/organizations/${orgId}/members/${userId}/`).then((r) => r.data)

export const getAudit = (orgId) =>
  api.get(`/organizations/${orgId}/audit/`).then((r) => r.data)

// Phase 3c: branding
export const getOrgBranding = (orgId) =>
  api.get(`/organizations/${orgId}/branding/`).then((r) => r.data)

/**
 * PUT /organizations/<id>/branding/
 * @param {number} orgId
 * @param {FormData|object} data — pass FormData when uploading a logo file
 */
export const updateOrgBranding = (orgId, data) => {
  const isFormData = typeof FormData !== "undefined" && data instanceof FormData
  return api.put(`/organizations/${orgId}/branding/`, data, {
    headers: isFormData ? { "Content-Type": "multipart/form-data" } : {},
  }).then((r) => r.data)
}
