import { useEffect, useState } from "react"
import { getTest } from "@/api/assessments"

// Tiny module-level cache so an exam's title + class resolve instantly across the
// shell panel and breadcrumb without refetching on every nav — mirrors useClass.
const cache = new Map()

export function primeTest(test) {
  if (test?.id != null) cache.set(String(test.id), test)
}

export function useTest(id) {
  const [test, setTest] = useState(() => (id != null ? cache.get(String(id)) ?? null : null))

  useEffect(() => {
    if (id == null) return
    const key = String(id)
    if (cache.has(key)) {
      setTest(cache.get(key))
      return
    }
    let cancelled = false
    getTest(id)
      .then((t) => {
        if (cancelled) return
        cache.set(key, t)
        setTest(t)
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [id])

  return test
}
