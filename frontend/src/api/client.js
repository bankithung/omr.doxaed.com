import axios from "axios"

const baseURL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1"

export const api = axios.create({ baseURL })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access")
  if (token) config.headers.Authorization = `Bearer ${token}`
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
