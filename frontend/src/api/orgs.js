import { api } from "@/api/client"

export const listOrgs = () =>
  api.get("/organizations/").then((r) => r.data)

// Accepts a name string (back-compat) or an object { name, type }.
export const createOrg = (data) =>
  api
    .post("/organizations/", typeof data === "string" ? { name: data } : data)
    .then((r) => r.data)

export const updateOrg = (orgId, body) =>
  api.patch(`/organizations/${orgId}/`, body).then((r) => r.data)

export const deleteOrg = (orgId) =>
  api.delete(`/organizations/${orgId}/`).then((r) => r.data)

export const getMembers = (orgId) =>
  api.get(`/organizations/${orgId}/members/`).then((r) => r.data)

export const invite = (orgId, email, rbacRoleId) =>
  api.post(`/organizations/${orgId}/invite/`, { email, rbac_role: rbacRoleId }).then((r) => r.data)

export const acceptInvite = (token) =>
  api.post("/invitations/accept/", { token }).then((r) => r.data)

export const setMemberRole = (orgId, userId, role) =>
  api.patch(`/organizations/${orgId}/members/${userId}/`, { role }).then((r) => r.data)

export const removeMember = (orgId, userId) =>
  api.delete(`/organizations/${orgId}/members/${userId}/`).then((r) => r.data)

export const getAudit = (orgId) =>
  api.get(`/organizations/${orgId}/audit/`).then((r) => r.data)

// Per-teacher class + subject access control (admin-managed grants).
// A grant links (active org, member, class); all_subjects=true means the whole
// class, otherwise only `subjects`. The class id scopes the list endpoint.
export const listClassGrants = (classId) =>
  api.get("/class-grants/", { params: { class_group: classId } }).then((r) => r.data)

export const createClassGrant = (body) =>
  api.post("/class-grants/", body).then((r) => r.data)

export const updateClassGrant = (id, body) =>
  api.patch(`/class-grants/${id}/`, body).then((r) => r.data)

export const deleteClassGrant = (id) =>
  api.delete(`/class-grants/${id}/`).then((r) => r.data)

// RBAC — roles, scoped role bindings, the permission catalog.
export const getPermissionCatalog = () =>
  api.get("/permissions/").then((r) => r.data)

export const listRoles = () =>
  api.get("/roles/").then((r) => r.data)

export const createRole = (body) =>
  api.post("/roles/", body).then((r) => r.data)

export const updateRole = (id, body) =>
  api.patch(`/roles/${id}/`, body).then((r) => r.data)

export const deleteRole = (id) =>
  api.delete(`/roles/${id}/`).then((r) => r.data)

export const listRoleBindings = (params) =>
  api.get("/role-bindings/", { params }).then((r) => r.data)

export const createRoleBinding = (body) =>
  api.post("/role-bindings/", body).then((r) => r.data)

export const deleteRoleBinding = (id) =>
  api.delete(`/role-bindings/${id}/`).then((r) => r.data)

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
