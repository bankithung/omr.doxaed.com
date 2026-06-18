import axios from "axios"

const baseURL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1"

export const api = axios.create({ baseURL })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access")
  if (token) config.headers.Authorization = `Bearer ${token}`
  const org = localStorage.getItem("activeOrg")
  if (org) config.headers["X-Organization-Id"] = org
  return config
})

let refreshPromise = null

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      const refresh = localStorage.getItem("refresh")
      if (!refresh) return Promise.reject(error)
      try {
        refreshPromise =
          refreshPromise || axios.post(`${baseURL}/auth/token/refresh/`, { refresh })
        const { data } = await refreshPromise
        refreshPromise = null
        localStorage.setItem("access", data.access)
        original.headers.Authorization = `Bearer ${data.access}`
        return api(original)
      } catch (e) {
        refreshPromise = null
        return Promise.reject(e)
      }
    }
    return Promise.reject(error)
  },
)

export const authApi = {
  register: (d) => api.post("/auth/register/", d),
  verifyEmail: (d) => api.post("/auth/verify-email/", d),
  login: (d) => api.post("/auth/login/", d),
  googleLogin: (idToken) => api.post("/auth/google/", { id_token: idToken }),
  logout: (refresh) => api.post("/auth/logout/", { refresh }),
  passwordReset: (email) => api.post("/auth/password-reset/", { email }),
  passwordResetConfirm: (d) => api.post("/auth/password-reset-confirm/", d),
  me: () => api.get("/auth/me/"),
  updateMe: (d) => api.patch("/auth/me/", d),
}
