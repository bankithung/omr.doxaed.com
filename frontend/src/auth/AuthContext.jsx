import { createContext, useContext, useEffect, useState } from "react"
import { authApi } from "@/api/client"

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (localStorage.getItem("access")) {
      authApi.me().then((r) => setUser(r.data)).catch(() => {}).finally(() => setLoading(false))
    } else setLoading(false)
  }, [])

  async function login(email, password) {
    const { data } = await authApi.login({ email, password })
    localStorage.setItem("access", data.access)
    localStorage.setItem("refresh", data.refresh)
    setUser(data.user)
  }

  async function logout() {
    const refresh = localStorage.getItem("refresh")
    try { if (refresh) await authApi.logout(refresh) } catch { /* ignore */ }
    localStorage.removeItem("access"); localStorage.removeItem("refresh"); setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, setUser, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
