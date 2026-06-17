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
