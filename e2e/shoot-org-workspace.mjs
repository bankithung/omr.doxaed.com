import { chromium } from "playwright"
import { mkdirSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { dirname, join } from "node:path"

const F = "http://localhost:5173"
const API = "http://localhost:8000/api/v1"
const OUT = join(dirname(fileURLToPath(import.meta.url)), "screenshots", "org-workspace")
mkdirSync(OUT, { recursive: true })

const { access, refresh } = await (await fetch(`${API}/auth/login/`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email: "teacher@omrflow.test", password: "Teacher@12345" }) })).json()
const A = { "Content-Type": "application/json", Authorization: `Bearer ${access}` }
const org = await (await fetch(`${API}/organizations/`, { method: "POST", headers: A, body: JSON.stringify({ name: "Riverside School", type: "school" }) })).json()
const O = { ...A, "X-Organization-Id": String(org.id) }
for (const n of ["Class 6", "Class 7", "Class 8"]) {
  await fetch(`${API}/classes/`, { method: "POST", headers: O, body: JSON.stringify({ name: n, kind_label: "Class" }) })
}
console.log("org", org.id, "slug", org.slug)

const b = await chromium.launch()
const ctx = await b.newContext({ viewport: { width: 1440, height: 1000 } })
await ctx.addInitScript(([a, rf, oid]) => { localStorage.setItem("access", a); localStorage.setItem("refresh", rf); localStorage.setItem("activeOrg", oid); localStorage.setItem("omrflow_onboarded", "1") }, [access, refresh, String(org.id)])
const p = await ctx.newPage()
p.on("console", (m) => { if (m.type() === "error") console.log("PAGE ERR:", m.text()) })

// 1. Org list → click the org → should route to /org/<slug>
await p.goto(`${F}/organizations`, { waitUntil: "load" })
await p.waitForTimeout(1500)
await p.getByText("Riverside School").first().click()
await p.waitForTimeout(2000)
console.log("after click URL:", p.url())
await p.screenshot({ path: `${OUT}/01-dashboard.png`, fullPage: true })

// 2. Usage
await p.goto(`${F}/org/${org.slug}/usage`, { waitUntil: "load" })
await p.waitForTimeout(2000)
console.log("overlay:", await p.locator("vite-error-overlay").count())
await p.screenshot({ path: `${OUT}/02-usage.png`, fullPage: true })

// 3. Members
await p.goto(`${F}/org/${org.slug}/members`, { waitUntil: "load" })
await p.waitForTimeout(2000)
await p.screenshot({ path: `${OUT}/03-members.png`, fullPage: true })

// 4. Settings
await p.goto(`${F}/org/${org.slug}/settings`, { waitUntil: "load" })
await p.waitForTimeout(2000)
await p.screenshot({ path: `${OUT}/04-settings.png`, fullPage: true })

// 5. Legacy redirect /organizations/:id/members → /org/:slug/members
await p.goto(`${F}/organizations/${org.id}/members`, { waitUntil: "load" })
await p.waitForTimeout(1500)
console.log("legacy redirect URL:", p.url())

await ctx.close(); await b.close()
console.log("DONE")
