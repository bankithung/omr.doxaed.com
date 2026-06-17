import { Navigate } from "react-router-dom"
import { useAuth } from "@/auth/AuthContext"

export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="p-8">Loading…</div>
  return user ? children : <Navigate to="/login" replace />
}
