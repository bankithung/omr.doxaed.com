import { useCallback, useEffect, useRef, useState } from "react"
import { useNavigate } from "react-router-dom"
import { Loader2 } from "lucide-react"
import { toast } from "sonner"
import { useAuth } from "@/auth/AuthContext"
import { Button } from "@/components/ui/button"

const GIS_SRC = "https://accounts.google.com/gsi/client"
const CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID

// Injects the Google Identity Services script exactly once for the whole app and
// reports readiness. Multiple GoogleButtons share the same load promise.
let gisPromise = null
function loadGis() {
  if (typeof window === "undefined") return Promise.reject(new Error("no window"))
  if (window.google?.accounts?.id) return Promise.resolve()
  if (gisPromise) return gisPromise
  gisPromise = new Promise((resolve, reject) => {
    const existing = document.querySelector(`script[src="${GIS_SRC}"]`)
    if (existing) {
      existing.addEventListener("load", () => resolve())
      existing.addEventListener("error", () => reject(new Error("GIS failed to load")))
      return
    }
    const script = document.createElement("script")
    script.src = GIS_SRC
    script.async = true
    script.defer = true
    script.onload = () => resolve()
    script.onerror = () => reject(new Error("GIS failed to load"))
    document.head.appendChild(script)
  })
  return gisPromise
}

function useGoogleScript() {
  const [ready, setReady] = useState(() => !!window?.google?.accounts?.id)
  useEffect(() => {
    if (!CLIENT_ID) return
    let active = true
    loadGis()
      .then(() => active && setReady(true))
      .catch(() => active && setReady(false))
    return () => {
      active = false
    }
  }, [])
  return ready
}

// Flat brand "G" mark (multi-colour Google logo as an inline SVG, flat fills).
function GoogleGSvg({ className }) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true">
      <path
        fill="#4285F4"
        d="M23.52 12.27c0-.82-.07-1.6-.21-2.36H12v4.48h6.47a5.53 5.53 0 0 1-2.4 3.62v3h3.88c2.27-2.09 3.57-5.17 3.57-8.74Z"
      />
      <path
        fill="#34A853"
        d="M12 24c3.24 0 5.96-1.07 7.94-2.91l-3.88-3.01c-1.08.72-2.45 1.15-4.06 1.15-3.12 0-5.77-2.11-6.71-4.95H1.27v3.1A12 12 0 0 0 12 24Z"
      />
      <path
        fill="#FBBC05"
        d="M5.29 14.28a7.2 7.2 0 0 1 0-4.56v-3.1H1.27a12 12 0 0 0 0 10.76l4.02-3.1Z"
      />
      <path
        fill="#EA4335"
        d="M12 4.75c1.76 0 3.34.61 4.59 1.8l3.43-3.43A11.96 11.96 0 0 0 12 0 12 12 0 0 0 1.27 6.62l4.02 3.1C6.23 6.86 8.88 4.75 12 4.75Z"
      />
    </svg>
  )
}

/**
 * "Continue with Google" — env-gated social sign-in.
 *
 * Renders NOTHING when VITE_GOOGLE_CLIENT_ID is unset, so the auth pages stay
 * fully functional (and error-free) until the owner configures Google. When
 * configured it uses Google Identity Services: clicking initialises GIS with the
 * client ID and opens the One Tap / account-chooser prompt; the credential JWT
 * is exchanged for our own session via authApi.googleLogin().
 */
export default function GoogleButton({ label = "Continue with Google" }) {
  const { loginWithGoogle } = useAuth()
  const navigate = useNavigate()
  const ready = useGoogleScript()
  const [loading, setLoading] = useState(false)
  const initialised = useRef(false)

  const handleCredential = useCallback(
    async (response) => {
      try {
        await loginWithGoogle(response.credential)
        navigate("/dashboard")
      } catch {
        toast.error("Google sign-in failed. Please try again.")
      } finally {
        setLoading(false)
      }
    },
    [loginWithGoogle, navigate],
  )

  // Gate the WHOLE feature behind the env var — no client id, no button.
  if (!CLIENT_ID) return null

  function ensureInit() {
    if (initialised.current) return true
    const idApi = window.google?.accounts?.id
    if (!idApi) return false
    idApi.initialize({
      client_id: CLIENT_ID,
      callback: handleCredential,
    })
    initialised.current = true
    return true
  }

  function handleClick() {
    if (loading) return
    if (!ensureInit()) {
      toast.error("Google sign-in is still loading. Please try again.")
      return
    }
    setLoading(true)
    window.google.accounts.id.prompt((notification) => {
      // If the One Tap prompt cannot be shown (dismissed / not displayed), drop
      // the spinner so the button is usable again.
      if (notification.isNotDisplayed?.() || notification.isSkippedMoment?.()) {
        setLoading(false)
      }
    })
  }

  return (
    <Button
      type="button"
      variant="outline"
      className="h-11 w-full justify-center gap-2.5"
      disabled={loading || !ready}
      onClick={handleClick}
    >
      {loading ? (
        <Loader2 className="size-4 animate-spin" aria-hidden="true" />
      ) : (
        <GoogleGSvg className="size-4" />
      )}
      {label}
    </Button>
  )
}

// A simple "or continue with email" divider, used between the Google button and
// the email form on Login / Register.
export function OrDivider({ children = "or continue with email" }) {
  return (
    <div className="flex items-center gap-3" role="separator" aria-label={children}>
      <span className="h-px flex-1 bg-border" />
      <span className="text-xs text-muted-foreground">{children}</span>
      <span className="h-px flex-1 bg-border" />
    </div>
  )
}
