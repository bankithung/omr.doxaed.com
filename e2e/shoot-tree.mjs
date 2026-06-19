import { chromium } from "playwright"
import { mkdirSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { dirname, join } from "node:path"

const F = process.env.FRONTEND || "http://localhost:5173"
const API = process.env.API || "http://localhost:8000/api/v1"
const OUT = join(dirname(fileURLToPath(import.meta.url)), "screenshots", "tree")
mkdirSync(OUT, { recursive: true })

const r = await fetch(`${API}/auth/login/`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ email: "teacher@omrflow.test", password: "Teacher@12345" }),
})
const { access, refresh } = await r.json()
const A = { "Content-Type": "application/json", Authorization: `Bearer ${access}` }

const org = await (await fetch(`${API}/organizations/`, { method: "POST", headers: A, body: JSON.stringify({ name: "Hilltop School", type: "school" }) })).json()
const O = { ...A, "X-Organization-Id": String(org.id) }
const cls = await (await fetch(`${API}/classes/`, { method: "POST", headers: O, body: JSON.stringify({ name: "Class 10", kind_label: "Class", description: "Science stream" }) })).json()
for (const name of ["Section A", "Section B", "Section C"]) {
  await fetch(`${API}/classes/`, { method: "POST", headers: O, body: JSON.stringify({ name, parent: cls.id, kind_label: "Section" }) })
}
console.log("org", org.id, "type school", "class", cls.id)

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

for (const [path, label] of [
  ["/classes", "01-classes-grid"],
  [`/classes/${cls.id}`, "02-class-overview"],
  [`/classes/${cls.id}/groups`, "03-sections"],
]) {
  await p.goto(`${F}${path}`, { waitUntil: "load" })
  await p.waitForTimeout(1200)
  await p.screenshot({ path: `${OUT}/${label}.png` })
  console.log(label, "overlay:", await p.locator("vite-error-overlay").count())
}

await ctx.close()
await b.close()
console.log("DONE")
