import { useEffect, useState } from "react"
import { getClass } from "@/api/assessments"

// Tiny module-level cache so the class name resolves instantly across the shell
// panel, the breadcrumb, and the section pages without refetching on every nav.
const cache = new Map()

export function primeClass(cls) {
  if (cls?.id != null) cache.set(String(cls.id), cls)
}

export function useClass(id) {
  const [cls, setCls] = useState(() => (id != null ? cache.get(String(id)) ?? null : null))

  useEffect(() => {
    if (id == null) return
    const key = String(id)
    if (cache.has(key)) {
      setCls(cache.get(key))
      return
    }
    let cancelled = false
    getClass(id)
      .then((c) => {
        if (cancelled) return
        cache.set(key, c)
        setCls(c)
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [id])

  return cls
}
