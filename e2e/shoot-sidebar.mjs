import { chromium } from "playwright"
import { mkdirSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { dirname, join } from "node:path"

const F = process.env.FRONTEND || "http://localhost:5173"
const API = process.env.API || "http://localhost:8000/api/v1"
const OUT = join(dirname(fileURLToPath(import.meta.url)), "screenshots", "amber")
mkdirSync(OUT, { recursive: true })

// Log in via the API to get tokens, then inject them so the shell renders.
const r = await fetch(`${API}/auth/login/`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ email: "teacher@omrflow.test", password: "Teacher@12345" }),
})
const { access, refresh } = await r.json()
if (!access) { console.log("LOGIN FAILED"); process.exit(1) }

const b = await chromium.launch()
const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } })
await ctx.addInitScript(([a, rf]) => {
  localStorage.setItem("access", a)
  localStorage.setItem("refresh", rf)
  localStorage.setItem("omrflow_onboarded", "1")
}, [access, refresh])

const p = await ctx.newPage()
await p.goto(`${F}/dashboard`, { waitUntil: "load" })
await p.waitForTimeout(1800)
console.log("vite overlay:", await p.locator("vite-error-overlay").count())
await p.screenshot({ path: `${OUT}/90-rail-collapsed.png` })
console.log("90-rail-collapsed.png")

// Hover the primary rail → it should expand and reveal labels.
const rail = p.locator('aside[aria-label="Primary"]')
await rail.hover()
await p.waitForTimeout(600)
await p.screenshot({ path: `${OUT}/91-rail-hover.png` })
console.log("91-rail-hover.png")

await ctx.close(); await b.close()
console.log("DONE")
