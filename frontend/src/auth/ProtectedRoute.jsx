import { Navigate } from "react-router-dom"
import { useAuth } from "@/auth/AuthContext"
import BrandedSplash from "@/components/BrandedSplash"

export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <BrandedSplash />
  return user ? children : <Navigate to="/login" replace />
}
