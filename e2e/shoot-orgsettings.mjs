import { chromium } from "playwright"
import { mkdirSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { dirname, join } from "node:path"

const F = "http://localhost:5173"
const API = "http://localhost:8000/api/v1"
const OUT = join(dirname(fileURLToPath(import.meta.url)), "screenshots", "orgsettings")
mkdirSync(OUT, { recursive: true })

const { access, refresh } = await (await fetch(`${API}/auth/login/`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ email: "teacher@omrflow.test", password: "Teacher@12345" }),
})).json()
const oid = process.env.OID || "21"

const b = await chromium.launch()
const ctx = await b.newContext({ viewport: { width: 1440, height: 1000 } })
await ctx.addInitScript(([a, rf, o]) => {
  localStorage.setItem("access", a)
  localStorage.setItem("refresh", rf)
  localStorage.setItem("activeOrg", o)
  localStorage.setItem("omrflow_onboarded", "1")
}, [access, refresh, oid])
const p = await ctx.newPage()
p.on("console", (m) => { if (m.type() === "error") console.log("PAGE ERR:", m.text()) })
await p.goto(`${F}/organizations/${oid}/settings`, { waitUntil: "load" })
await p.waitForTimeout(1300)
console.log("overlay:", await p.locator("vite-error-overlay").count())
await p.screenshot({ path: `${OUT}/01-settings.png` })
await ctx.close()
await b.close()
console.log("DONE")
