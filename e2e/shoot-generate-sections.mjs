import { chromium } from "playwright"
import { mkdirSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { dirname, join } from "node:path"

const F = "http://localhost:5173"
const API = "http://localhost:8000/api/v1"
const OUT = join(dirname(fileURLToPath(import.meta.url)), "screenshots", "generate-sections")
mkdirSync(OUT, { recursive: true })

const { access, refresh } = await (await fetch(`${API}/auth/login/`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email: "teacher@omrflow.test", password: "Teacher@12345" }) })).json()
const A = { "Content-Type": "application/json", Authorization: `Bearer ${access}` }
const org = await (await fetch(`${API}/organizations/`, { method: "POST", headers: A, body: JSON.stringify({ name: "Lincoln School", type: "school" }) })).json()
const O = { ...A, "X-Organization-Id": String(org.id) }
const cls = await (await fetch(`${API}/classes/`, { method: "POST", headers: O, body: JSON.stringify({ name: "Class 8", kind_label: "Class" }) })).json()

async function section(name, rolls) {
  const sec = await (await fetch(`${API}/classes/`, { method: "POST", headers: O, body: JSON.stringify({ name, parent: cls.id, kind_label: "Section" }) })).json()
  const roster = await (await fetch(`${API}/rosters/`, { method: "POST", headers: O, body: JSON.stringify({ name: "Students", class_group: sec.id }) })).json()
  for (const [roll, full_name] of rolls) {
    await fetch(`${API}/students/`, { method: "POST", headers: O, body: JSON.stringify({ roster: roster.id, roll_number: roll, full_name }) })
  }
}
await section("Section A", [["101", "Asha Devi"], ["102", "Ravi Kumar"]])
await section("Section B", [["201", "Sahil Khan"]])

// A whole-class exam with one question + answer key so it is generatable.
const test = await (await fetch(`${API}/tests/`, { method: "POST", headers: O, body: JSON.stringify({ class_group: cls.id, title: "Term Exam", subject: "Maths", mode: "roster_prebubbled" }) })).json()
await fetch(`${API}/questions/`, { method: "POST", headers: O, body: JSON.stringify({ test: test.id, order: 1, options: [{ label: "A" }, { label: "B" }, { label: "C" }, { label: "D" }], correct_options: [0] }) })
console.log("test", test.id)

const b = await chromium.launch()
const ctx = await b.newContext({ viewport: { width: 1440, height: 1000 } })
await ctx.addInitScript(([a, rf, oid]) => { localStorage.setItem("access", a); localStorage.setItem("refresh", rf); localStorage.setItem("activeOrg", oid); localStorage.setItem("omrflow_onboarded", "1") }, [access, refresh, String(org.id)])
const p = await ctx.newPage()
p.on("console", (m) => { if (m.type() === "error") console.log("PAGE ERR:", m.text()) })
await p.goto(`${F}/tests/${test.id}/sheets`, { waitUntil: "load" })
await p.waitForTimeout(2000)
console.log("overlay:", await p.locator("vite-error-overlay").count())
const rosterTrigger = p.locator("#roster-select")
if (await rosterTrigger.count()) {
  await rosterTrigger.click()
  await p.waitForTimeout(500)
}
await p.screenshot({ path: `${OUT}/01-roster-open.png`, fullPage: true })
await ctx.close(); await b.close()
console.log("DONE — roster picker should list 'Section A · Students' and 'Section B · Students'")
