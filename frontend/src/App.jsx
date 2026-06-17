import { Link, Route, Routes, useNavigate } from "react-router-dom"
import { toast } from "sonner"
import { Toaster } from "@/components/ui/sonner"
import { useAuth } from "@/auth/AuthContext"
import ProtectedRoute from "@/auth/ProtectedRoute"

import Health from "@/routes/Health"
import StyleGuide from "@/routes/StyleGuide"
import Login from "@/routes/Login"
import Register from "@/routes/Register"
import VerifyEmail from "@/routes/VerifyEmail"
import ForgotPassword from "@/routes/ForgotPassword"
import ResetPassword from "@/routes/ResetPassword"
import Profile from "@/routes/Profile"
import Classes from "@/routes/Classes"
import TestList from "@/routes/TestList"
import TestWizard from "@/routes/TestWizard"
import Rosters from "@/routes/Rosters"
import RosterDetail from "@/routes/RosterDetail"

function Nav() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  async function handleLogout() {
    await logout()
    navigate("/login")
  }

  return (
    <nav className="flex items-center gap-4 border-b px-4 py-3 text-sm">
      <Link to="/health" className="font-semibold hover:text-primary">
        OMRFlow
      </Link>
      <Link to="/style-guide" className="text-muted-foreground hover:text-foreground">
        Style Guide
      </Link>
      {user && (
        <>
          <Link to="/classes" className="text-muted-foreground hover:text-foreground">
            Classes
          </Link>
          <Link to="/rosters" className="text-muted-foreground hover:text-foreground">
            Rosters
          </Link>
        </>
      )}

      <div className="ml-auto flex items-center gap-3">
        {user ? (
          <>
            <span className="hidden text-muted-foreground sm:inline">{user.email}</span>
            <Link to="/profile" className="hover:text-primary">
              Profile
            </Link>
            <button
              onClick={handleLogout}
              className="text-muted-foreground hover:text-foreground"
            >
              Sign out
            </button>
          </>
        ) : (
          <>
            <Link to="/login" className="hover:text-primary">
              Sign in
            </Link>
            <Link
              to="/register"
              className="rounded-lg bg-primary px-3 py-1 text-primary-foreground hover:bg-primary/80"
            >
              Register
            </Link>
          </>
        )}
      </div>
    </nav>
  )
}

export default function App() {
  return (
    <div className="min-h-screen">
      <Toaster />
      <Nav />
      <Routes>
        {/* Public routes */}
        <Route path="/" element={<Health />} />
        <Route path="/health" element={<Health />} />
        <Route path="/style-guide" element={<StyleGuide />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/verify-email" element={<VerifyEmail />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />

        {/* Protected routes */}
        <Route
          path="/profile"
          element={
            <ProtectedRoute>
              <Profile />
            </ProtectedRoute>
          }
        />
        <Route
          path="/classes"
          element={
            <ProtectedRoute>
              <Classes />
            </ProtectedRoute>
          }
        />
        <Route
          path="/classes/:id"
          element={
            <ProtectedRoute>
              <TestList />
            </ProtectedRoute>
          }
        />
        <Route
          path="/classes/:classId/tests/new"
          element={
            <ProtectedRoute>
              <TestWizard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/rosters"
          element={
            <ProtectedRoute>
              <Rosters />
            </ProtectedRoute>
          }
        />
        <Route
          path="/rosters/:id"
          element={
            <ProtectedRoute>
              <RosterDetail />
            </ProtectedRoute>
          }
        />
      </Routes>
    </div>
  )
}
