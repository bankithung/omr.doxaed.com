import { api } from "@/api/client"

export const listPlans = () =>
  api.get("/billing/plans/").then((r) => r.data)

export const getPlan = (orgId) =>
  api.get(`/billing/organizations/${orgId}/plan/`).then((r) => r.data)

export const subscribe = (orgId, planCode) =>
  api.post(`/billing/organizations/${orgId}/subscribe/`, { plan_code: planCode }).then((r) => r.data)
