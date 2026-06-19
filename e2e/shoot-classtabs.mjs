import { chromium } from "playwright"
import { mkdirSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { dirname, join } from "node:path"

const F = process.env.FRONTEND || "http://localhost:5173"
const API = process.env.API || "http://localhost:8000/api/v1"
const OUT = join(dirname(fileURLToPath(import.meta.url)), "screenshots", "amber")
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
}, [access, refresh])

const p = await ctx.newPage()
await p.goto(`${F}/classes`, { waitUntil: "load" })
await p.waitForTimeout(1300)
const href = await p.evaluate(() => {
  const a = [...document.querySelectorAll("a[href]")].find((el) => /^\/classes\/\d+/.test(el.getAttribute("href")))
  return a?.getAttribute("href")
})
console.log("class href:", href)
await p.goto(`${F}${href}`, { waitUntil: "load" })
await p.waitForTimeout(1300)
console.log("vite overlay:", await p.locator("vite-error-overlay").count())
await p.screenshot({ path: `${OUT}/a0-class-tests.png` })
console.log("a0-class-tests.png")

await p.getByRole("tab", { name: "Rosters" }).click()
await p.waitForTimeout(800)
await p.screenshot({ path: `${OUT}/a1-class-rosters.png` })
console.log("a1-class-rosters.png")

await p.getByRole("tab", { name: "Subjects" }).click()
await p.waitForTimeout(800)
await p.screenshot({ path: `${OUT}/a2-class-subjects.png` })
console.log("a2-class-subjects.png")

await ctx.close(); await b.close()
console.log("DONE")
