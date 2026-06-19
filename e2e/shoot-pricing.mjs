import { chromium } from "playwright"
import { mkdirSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { dirname, join } from "node:path"

const OUT = join(dirname(fileURLToPath(import.meta.url)), "screenshots", "pricing")
mkdirSync(OUT, { recursive: true })

const b = await chromium.launch()
const ctx = await b.newContext({ viewport: { width: 1440, height: 1200 } })
const p = await ctx.newPage()
await p.goto("http://localhost:5173/pricing", { waitUntil: "load" })
await p.waitForTimeout(1500)
await p.screenshot({ path: `${OUT}/pricing.png`, fullPage: false })
console.log("overlay:", await p.locator("vite-error-overlay").count())
await ctx.close()
await b.close()
console.log("DONE")
