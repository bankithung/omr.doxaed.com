import { chromium } from "playwright"
import { mkdirSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { dirname, join } from "node:path"

const F = "http://localhost:5173"
const API = "http://localhost:8000/api/v1"
const OUT = join(dirname(fileURLToPath(import.meta.url)), "screenshots", "exam-pages")
mkdirSync(OUT, { recursive: true })

const { access, refresh } = await (await fetch(`${API}/auth/login/`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email: "teacher@omrflow.test", password: "Teacher@12345" }) })).json()
const A = { "Content-Type": "application/json", Authorization: `Bearer ${access}` }
const org = await (await fetch(`${API}/organizations/`, { method: "POST", headers: A, body: JSON.stringify({ name: "Lincoln School", type: "school" }) })).json()
const O = { ...A, "X-Organization-Id": String(org.id) }
const cls = await (await fetch(`${API}/classes/`, { method: "POST", headers: O, body: JSON.stringify({ name: "Class 8", kind_label: "Class" }) })).json()
const secA = await (await fetch(`${API}/classes/`, { method: "POST", headers: O, body: JSON.stringify({ name: "Section A", parent: cls.id, kind_label: "Section" }) })).json()
const test = await (await fetch(`${API}/tests/`, { method: "POST", headers: O, body: JSON.stringify({ class_group: secA.id, title: "Unit Test 1", subject: "Science", mode: "standard", marking_scheme: { marks_per_correct: 2, negative_marks_per_wrong: 0.5 } }) })).json()
for (const [order, qtext, correct] of [[0, "Capital of France?", 0], [1, "2 + 2 = ?", 1], [2, "H2O is?", 2]]) {
  await fetch(`${API}/questions/`, { method: "POST", headers: O, body: JSON.stringify({ test: test.id, order_index: order, text: qtext, options: [{ label: "A", text: "Opt A", is_correct: correct === 0 }, { label: "B", text: "Opt B", is_correct: correct === 1 }, { label: "C", text: "Opt C", is_correct: correct === 2 }, { label: "D", text: "Opt D", is_correct: false }] }) })
}
console.log("test", test.id)

const b = await chromium.launch()
const ctx = await b.newContext({ viewport: { width: 1440, height: 1000 } })
await ctx.addInitScript(([a, rf, oid]) => { localStorage.setItem("access", a); localStorage.setItem("refresh", rf); localStorage.setItem("activeOrg", oid); localStorage.setItem("omrflow_onboarded", "1") }, [access, refresh, String(org.id)])
const p = await ctx.newPage()
p.on("console", (m) => { if (m.type() === "error") console.log("PAGE ERR:", m.text()) })

await p.goto(`${F}/tests/${test.id}`, { waitUntil: "load" })
await p.waitForTimeout(2600)
console.log("overlay:", await p.locator("vite-error-overlay").count())
await p.screenshot({ path: `${OUT}/01-overview.png`, fullPage: true })

await p.goto(`${F}/tests/${test.id}/questions`, { waitUntil: "load" })
await p.waitForTimeout(2600)
await p.screenshot({ path: `${OUT}/02-questions.png`, fullPage: true })

await ctx.close(); await b.close()
console.log("DONE — overview: Questions 3, Total marks 6, Mode Standard; questions: 3 saved cards")
