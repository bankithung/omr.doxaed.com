import { chromium } from "playwright"
import { mkdirSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { dirname, join } from "node:path"

const F = process.env.FRONTEND || "http://localhost:5173"
const API = process.env.API || "http://localhost:8000/api/v1"
const OUT = join(dirname(fileURLToPath(import.meta.url)), "screenshots", "roles")
mkdirSync(OUT, { recursive: true })

const r = await fetch(`${API}/auth/login/`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ email: "teacher@omrflow.test", password: "Teacher@12345" }),
})
const { access, refresh } = await r.json()
const A = { "Content-Type": "application/json", Authorization: `Bearer ${access}` }
const org = await (await fetch(`${API}/organizations/`, { method: "POST", headers: A, body: JSON.stringify({ name: "Riverdale High", type: "school" }) })).json()
console.log("org", org.id)

const b = await chromium.launch()
const ctx = await b.newContext({ viewport: { width: 1440, height: 950 } })
await ctx.addInitScript(([a, rf, oid]) => {
  localStorage.setItem("access", a)
  localStorage.setItem("refresh", rf)
  localStorage.setItem("activeOrg", oid)
  localStorage.setItem("omrflow_onboarded", "1")
}, [access, refresh, String(org.id)])

const p = await ctx.newPage()
p.on("console", (m) => { if (m.type() === "error") console.log("PAGE ERR:", m.text()) })

await p.goto(`${F}/organizations/${org.id}/roles`, { waitUntil: "load" })
await p.waitForTimeout(1400)
console.log("overlay:", await p.locator("vite-error-overlay").count())
await p.screenshot({ path: `${OUT}/01-roles.png` })

// open the New role dialog (the permission matrix)
await p.getByRole("button", { name: "New role" }).first().click()
await p.waitForTimeout(700)
await p.screenshot({ path: `${OUT}/02-new-role.png` })
console.log("DONE")

await ctx.close()
await b.close()
