import { chromium } from "playwright"
import { mkdirSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { dirname, join } from "node:path"

const F = "http://localhost:5173"
const API = "http://localhost:8000/api/v1"
const OUT = join(dirname(fileURLToPath(import.meta.url)), "screenshots", "overview")
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

async function section(name, rolls) {
  const sec = await (await fetch(`${API}/classes/`, { method: "POST", headers: O, body: JSON.stringify({ name, parent: cls.id, kind_label: "Section" }) })).json()
  const roster = await (await fetch(`${API}/rosters/`, { method: "POST", headers: O, body: JSON.stringify({ name: "Students", class_group: sec.id }) })).json()
  for (const [roll, full_name] of rolls) {
    await fetch(`${API}/students/`, { method: "POST", headers: O, body: JSON.stringify({ roster: roster.id, roll_number: roll, full_name }) })
  }
  return sec
}
const secA = await section("Section A", [["101", "Asha Devi"], ["102", "Ravi Kumar"], ["103", "Meera Nair"]])
await section("Section B", [["201", "Sahil Khan"], ["202", "Priya Iyer"]])
await fetch(`${API}/tests/`, { method: "POST", headers: O, body: JSON.stringify({ class_group: cls.id, title: "Whole-class Mock", subject: "Maths", mode: "standard" }) })
await fetch(`${API}/tests/`, { method: "POST", headers: O, body: JSON.stringify({ class_group: secA.id, title: "Section A Quiz", subject: "Science", mode: "standard" }) })
await fetch(`${API}/subjects/`, { method: "POST", headers: O, body: JSON.stringify({ class_group: cls.id, name: "Maths" }) })
console.log("class", cls.id)

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
await p.goto(`${F}/classes/${cls.id}`, { waitUntil: "load" })
await p.waitForTimeout(2800)
console.log("overlay:", await p.locator("vite-error-overlay").count())
await p.screenshot({ path: `${OUT}/01-overview.png`, fullPage: true })
await ctx.close()
await b.close()
console.log("DONE — expect Exams 2, Students 5, Sections 2, Subjects 1")
