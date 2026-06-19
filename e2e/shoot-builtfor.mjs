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
await p.goto(`${F}/built-for`, { waitUntil: "load" }); await p.waitForTimeout(1200)
console.log("vite overlay:", await p.locator("vite-error-overlay").count())
await p.screenshot({ path: `${OUT}/80-builtfor-top.png` }); console.log("80-builtfor-top.png")

const tot = await p.evaluate(() => document.body.scrollHeight)
for (let y = 0; y <= tot; y += 320) { await p.evaluate((yy) => scrollTo(0, yy), y); await p.waitForTimeout(70) }
await p.evaluate(() => scrollTo(0, 0)); await p.waitForTimeout(400)
async function shotAt(text, file) {
  try { const t = p.getByText(text, { exact: false }).first(); await t.scrollIntoViewIfNeeded(); await p.waitForTimeout(500); await p.evaluate(() => window.scrollBy(0, -110)); await p.waitForTimeout(400); await p.screenshot({ path: `${OUT}/${file}` }); console.log(file) } catch (e) { console.log("MISS", text, String(e).slice(0,50)) }
}
await shotAt("Batch whole cohorts", "81-builtfor-coaching.png")
await shotAt("Standardise unit tests", "82-builtfor-schools.png")
await p.screenshot({ path: `${OUT}/83-builtfor-full.png`, fullPage: true }); console.log("83-builtfor-full.png")
await ctx.close(); await b.close()
console.log("DONE")
