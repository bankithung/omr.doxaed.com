import { chromium } from "playwright"
import { mkdirSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { dirname, join } from "node:path"

const F = process.env.FRONTEND || "http://localhost:5173"
const API = process.env.API || "http://localhost:8000/api/v1"
const OUT = join(dirname(fileURLToPath(import.meta.url)), "screenshots", "orglist")
mkdirSync(OUT, { recursive: true })

const r = await fetch(`${API}/auth/login/`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ email: "teacher@omrflow.test", password: "Teacher@12345" }),
})
const { access, refresh } = await r.json()

const b = await chromium.launch()
const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } })
await ctx.addInitScript(([a, rf]) => {
  localStorage.setItem("access", a)
  localStorage.setItem("refresh", rf)
  localStorage.setItem("omrflow_onboarded", "1")
  localStorage.removeItem("activeOrg")
}, [access, refresh])

const p = await ctx.newPage()
p.on("console", (m) => { if (m.type() === "error") console.log("PAGE ERR:", m.text()) })

for (const [path, label] of [
  ["/organizations", "01-org-list"],
  ["/organizations/new", "02-create-org"],
]) {
  await p.goto(`${F}${path}`, { waitUntil: "load" })
  await p.waitForTimeout(1300)
  await p.screenshot({ path: `${OUT}/${label}.png` })
  console.log(label, "overlay:", await p.locator("vite-error-overlay").count())
}

await ctx.close()
await b.close()
console.log("DONE")
