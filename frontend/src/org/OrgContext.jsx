import { createContext, useCallback, useContext, useEffect, useState } from "react"
import { useAuth } from "@/auth/AuthContext"
import { listOrgs } from "@/api/orgs"

const OrgContext = createContext(null)

const LS_KEY = "activeOrg"

export function OrgProvider({ children }) {
  const { user } = useAuth()
  const [orgs, setOrgs] = useState([])
  const [activeOrgId, setActiveOrgId] = useState(() => localStorage.getItem(LS_KEY) || null)

  const refreshOrgs = useCallback(async () => {
    if (!user) return
    try {
      const data = await listOrgs()
      setOrgs(data.results ?? data)
    } catch {
      setOrgs([])
    }
  }, [user])

  useEffect(() => {
    if (user) {
      refreshOrgs()
    } else {
      setOrgs([])
      setActiveOrgId(null)
      localStorage.removeItem(LS_KEY)
    }
  }, [user, refreshOrgs])

  function setActiveOrg(id) {
    if (id) {
      localStorage.setItem(LS_KEY, id)
    } else {
      localStorage.removeItem(LS_KEY)
    }
    setActiveOrgId(id || null)
  }

  const activeOrg = orgs.find((o) => String(o.id) === String(activeOrgId)) || null

  return (
    <OrgContext.Provider value={{ activeOrgId, activeOrg, orgs, setActiveOrg, refreshOrgs }}>
      {children}
    </OrgContext.Provider>
  )
}

export const useOrg = () => useContext(OrgContext)
