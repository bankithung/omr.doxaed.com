import { chromium } from "playwright"
import { mkdirSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { dirname, join } from "node:path"

const F = process.env.FRONTEND || "http://localhost:5173"
const API = process.env.API || "http://localhost:8000/api/v1"
const OUT = join(dirname(fileURLToPath(import.meta.url)), "screenshots", "classws")
mkdirSync(OUT, { recursive: true })

const r = await fetch(`${API}/auth/login/`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ email: "teacher@omrflow.test", password: "Teacher@12345" }),
})
const { access, refresh } = await r.json()
const A = { "Content-Type": "application/json", Authorization: `Bearer ${access}` }

const org = await (await fetch(`${API}/organizations/`, { method: "POST", headers: A, body: JSON.stringify({ name: "Doxaed Academy" }) })).json()
const O = { ...A, "X-Organization-Id": String(org.id) }
const cls = await (await fetch(`${API}/classes/`, { method: "POST", headers: O, body: JSON.stringify({ name: "Grade 10 — Science", description: "Physics, Chemistry & Biology · 2026 batch" }) })).json()
for (const name of ["Physics", "Chemistry", "Biology"]) {
  await fetch(`${API}/subjects/`, { method: "POST", headers: O, body: JSON.stringify({ class_group: cls.id, name }) })
}
const roster = await (await fetch(`${API}/rosters/`, { method: "POST", headers: O, body: JSON.stringify({ name: "Section A", class_group: cls.id }) })).json()
await fetch(`${API}/rosters/${roster.id}/add_count/`, { method: "POST", headers: O, body: JSON.stringify({ count: 32 }) })
for (const [title, subject] of [["Unit Test 1 — Kinematics", "Physics"], ["Mid-term — Periodic Table", "Chemistry"], ["Mock NEET 01", ""]]) {
  await fetch(`${API}/tests/`, { method: "POST", headers: O, body: JSON.stringify({ class_group: cls.id, title, subject }) })
}
console.log("org", org.id, "class", cls.id)

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
p.on("response", (resp) => {
  if (resp.status() === 404 && resp.url().includes("/api/")) console.log("404 API:", resp.url())
})

await p.goto(`${F}/classes/${cls.id}`, { waitUntil: "load" })
await p.waitForTimeout(1500)
console.log("LS activeOrg after load:", await p.evaluate(() => localStorage.getItem("activeOrg")))
console.log("expected org:", org.id, "class:", cls.id)

for (const [path, label] of [
  [`/classes/${cls.id}`, "01-class-overview"],
  [`/classes/${cls.id}/exams`, "02-class-exams"],
  [`/classes/${cls.id}/students`, "03-class-students"],
  [`/classes/${cls.id}/subjects`, "04-class-subjects"],
  [`/classes/${cls.id}/settings`, "05-class-settings"],
]) {
  await p.goto(`${F}${path}`, { waitUntil: "load" })
  await p.waitForTimeout(1200)
  await p.screenshot({ path: `${OUT}/${label}.png` })
  console.log(label, "overlay:", await p.locator("vite-error-overlay").count())
}

await ctx.close()
await b.close()
console.log("DONE")
