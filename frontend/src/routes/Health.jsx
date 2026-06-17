import { useEffect, useState } from "react"
import { api } from "@/api/client"

export default function Health() {
  const [status, setStatus] = useState("loading…")
  const [error, setError] = useState(null)

  useEffect(() => {
    api
      .get("/health/")
      .then((res) => setStatus(JSON.stringify(res.data)))
      .catch((err) => setError(err.message))
  }, [])

  return (
    <div className="p-8 space-y-2">
      <h1 className="text-2xl font-semibold">API Health</h1>
      {error ? (
        <p className="text-[color:var(--color-error)]">Error: {error}</p>
      ) : (
        <p className="text-base">Backend says: {status}</p>
      )}
    </div>
  )
}
