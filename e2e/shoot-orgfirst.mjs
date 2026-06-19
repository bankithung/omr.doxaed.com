import { chromium } from "playwright"
import { mkdirSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { dirname, join } from "node:path"

const F = process.env.FRONTEND || "http://localhost:5173"
const API = process.env.API || "http://localhost:8000/api/v1"
const OUT = join(dirname(fileURLToPath(import.meta.url)), "screenshots", "orgfirst")
mkdirSync(OUT, { recursive: true })

// login
const r = await fetch(`${API}/auth/login/`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ email: "teacher@omrflow.test", password: "Teacher@12345" }),
})
const { access, refresh } = await r.json()
const authH = { "Content-Type": "application/json", Authorization: `Bearer ${access}` }

// create a fresh org + a few classes via API
const orgRes = await fetch(`${API}/organizations/`, {
  method: "POST",
  headers: authH,
  body: JSON.stringify({ name: "Springfield High" }),
})
const org = await orgRes.json()
console.log("org:", org.id, org.name)
const orgH = { ...authH, "X-Organization-Id": String(org.id) }
for (const [name, description] of [
  ["Grade 10 — Science", "Physics, Chemistry, Biology"],
  ["Grade 11 — Commerce", "Accounts, Economics, BST"],
  ["NEET Crash Batch", "Weekend intensive"],
  ["JEE Mains 2026", ""],
]) {
  await fetch(`${API}/classes/`, { method: "POST", headers: orgH, body: JSON.stringify({ name, description }) })
}

const b = await chromium.launch()
const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } })
await ctx.addInitScript(([a, rf, oid]) => {
  localStorage.setItem("access", a)
  localStorage.setItem("refresh", rf)
  localStorage.setItem("activeOrg", oid)
  localStorage.setItem("omrflow_onboarded", "1")
}, [access, refresh, String(org.id)])

const p = await ctx.newPage()
p.on("console", (m) => { if (m.type() === "error") console.log("PAGE ERR:", m.text()) })

await p.goto(`${F}/classes`, { waitUntil: "load" })
await p.waitForTimeout(1500)
console.log("vite overlay:", await p.locator("vite-error-overlay").count())
await p.screenshot({ path: `${OUT}/01-classes-grid.png` })
console.log("01-classes-grid.png")

await p.goto(`${F}/classes/new`, { waitUntil: "load" })
await p.waitForTimeout(1000)
await p.screenshot({ path: `${OUT}/02-new-class.png` })
console.log("02-new-class.png")

await p.goto(`${F}/organizations/new`, { waitUntil: "load" })
await p.waitForTimeout(1000)
await p.screenshot({ path: `${OUT}/03-new-org.png` })
console.log("03-new-org.png")

await ctx.close()
await b.close()
console.log("DONE")
