import { chromium } from "playwright"
import { mkdirSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { dirname, join } from "node:path"

const F = "http://localhost:5173"
const API = "http://localhost:8000/api/v1"
const OUT = join(dirname(fileURLToPath(import.meta.url)), "screenshots", "wizard-section")
mkdirSync(OUT, { recursive: true })

const { access, refresh } = await (await fetch(`${API}/auth/login/`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ email: "teacher@omrflow.test", password: "Teacher@12345" }),
})).json()
const A = { "Content-Type": "application/json", Authorization: `Bearer ${access}` }
const org = await (await fetch(`${API}/organizations/`, { method: "POST", headers: A, body: JSON.stringify({ name: "Lincoln School", type: "school" }) })).json()
const O = { ...A, "X-Organization-Id": String(org.id) }
const cls = await (await fetch(`${API}/classes/`, { method: "POST", headers: O, body: JSON.stringify({ name: "Class 8", kind_label: "Class" }) })).json()
const secA = await (await fetch(`${API}/classes/`, { method: "POST", headers: O, body: JSON.stringify({ name: "Section A", parent: cls.id, kind_label: "Section" }) })).json()
await fetch(`${API}/classes/`, { method: "POST", headers: O, body: JSON.stringify({ name: "Section B", parent: cls.id, kind_label: "Section" }) })

// A whole-class exam + a section-scoped exam, to prove the class Exams page aggregates both.
await fetch(`${API}/tests/`, { method: "POST", headers: O, body: JSON.stringify({ class_group: cls.id, title: "Whole-class Mock", subject: "Maths", mode: "standard" }) })
await fetch(`${API}/tests/`, { method: "POST", headers: O, body: JSON.stringify({ class_group: secA.id, title: "Section A Quiz", subject: "Science", mode: "standard" }) })
console.log("class", cls.id, "secA", secA.id)

const b = await chromium.launch()
const ctx = await b.newContext({ viewport: { width: 1440, height: 1000 } })
await ctx.addInitScript(([a, rf, oid]) => {
  localStorage.setItem("access", a)
  localStorage.setItem("refresh", rf)
  localStorage.setItem("activeOrg", oid)
  localStorage.setItem("omrflow_onboarded", "1")
}, [access, refresh, String(org.id)])
const p = await ctx.newPage()
p.on("console", (m) => { if (m.type() === "error") console.log("PAGE ERR:", m.text()) })

// 1) Test wizard — section selector should be present in Step 1
await p.goto(`${F}/classes/${cls.id}/tests/new`, { waitUntil: "load" })
await p.waitForTimeout(1500)
console.log("overlay:", await p.locator("vite-error-overlay").count())
await p.screenshot({ path: `${OUT}/01-wizard.png`, fullPage: true })
// open the section Select
const secTrigger = p.locator("#test-section")
if (await secTrigger.count()) {
  await secTrigger.click()
  await p.waitForTimeout(500)
  await p.screenshot({ path: `${OUT}/02-section-open.png` })
  await p.keyboard.press("Escape")
}

// 2) Class Exams page — aggregated list + section filter
await p.goto(`${F}/classes/${cls.id}/exams`, { waitUntil: "load" })
await p.waitForTimeout(1500)
await p.screenshot({ path: `${OUT}/03-exams.png`, fullPage: true })

await ctx.close()
await b.close()
console.log("DONE")
