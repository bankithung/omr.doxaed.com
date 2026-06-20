import { chromium } from "playwright"
import { mkdirSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { dirname, join } from "node:path"

const F = "http://localhost:5173"
const API = "http://localhost:8000/api/v1"
const OUT = join(dirname(fileURLToPath(import.meta.url)), "screenshots", "newclass")
mkdirSync(OUT, { recursive: true })

const { access, refresh } = await (await fetch(`${API}/auth/login/`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email: "teacher@omrflow.test", password: "Teacher@12345" }) })).json()
const A = { "Content-Type": "application/json", Authorization: `Bearer ${access}` }
const org = await (await fetch(`${API}/organizations/`, { method: "POST", headers: A, body: JSON.stringify({ name: "Temp Modal Org", type: "school" }) })).json()
console.log("org", org.id, org.slug)

const b = await chromium.launch()
const ctx = await b.newContext({ viewport: { width: 1440, height: 1000 } })
await ctx.addInitScript(([a, rf, oid]) => { localStorage.setItem("access", a); localStorage.setItem("refresh", rf); localStorage.setItem("activeOrg", oid); localStorage.setItem("omrflow_onboarded", "1") }, [access, refresh, String(org.id)])
const p = await ctx.newPage()
p.on("console", (m) => { if (m.type() === "error") console.log("PAGE ERR:", m.text()) })
await p.goto(`${F}/org/${org.slug}`, { waitUntil: "load" })
await p.waitForTimeout(2000)
await p.getByRole("button", { name: /New class/i }).first().click()
await p.waitForTimeout(700)
console.log("overlay:", await p.locator("vite-error-overlay").count())
// fill a name + add sections + subjects to show the chips
await p.getByLabel("Class name").fill("Class 8")
const secInput = p.getByPlaceholder("e.g. Section A")
await secInput.fill("Section A"); await p.getByRole("button", { name: "Add" }).first().click()
await secInput.fill("Section B"); await p.getByRole("button", { name: "Add" }).first().click()
const subInput = p.getByPlaceholder("e.g. Mathematics")
await subInput.fill("Maths"); await p.getByRole("button", { name: "Add" }).nth(1).click()
await subInput.fill("Science"); await p.getByRole("button", { name: "Add" }).nth(1).click()
await p.waitForTimeout(400)
await p.screenshot({ path: `${OUT}/01-modal.png` })

await ctx.close(); await b.close()
// cleanup the temp org
await fetch(`${API}/organizations/${org.id}/`, { method: "DELETE", headers: A })
console.log("DONE + cleaned up")
