import { chromium } from "playwright"
import { mkdirSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { dirname, join } from "node:path"

const F = process.env.FRONTEND || "http://localhost:5173"
const OUT = join(dirname(fileURLToPath(import.meta.url)), "screenshots", "amber")
mkdirSync(OUT, { recursive: true })

const b = await chromium.launch()
const ctx = await b.newContext({ viewport: { width: 1440, height: 1000 } })
const p = await ctx.newPage()

async function shot(path, file, wait = 800) {
  await p.goto(`${F}${path}`, { waitUntil: "load" })
  await p.waitForTimeout(wait)
  // surface a Vite error overlay if a file is mid-edit
  const overlay = await p.locator("vite-error-overlay").count()
  await p.screenshot({ path: `${OUT}/${file}` })
  console.log(file, overlay ? "(VITE ERROR OVERLAY!)" : "")
}

await shot("/login", "20-login.png")
await shot("/register", "21-register.png")
await shot("/forgot-password", "22-forgot.png")

await ctx.close()
const mctx = await b.newContext({ viewport: { width: 390, height: 844 } })
const mp = await mctx.newPage()
await mp.goto(`${F}/login`, { waitUntil: "load" })
await mp.waitForTimeout(700)
await mp.screenshot({ path: `${OUT}/23-login-mobile.png` })
console.log("23-login-mobile.png")
await mctx.close(); await b.close()
console.log("DONE")
