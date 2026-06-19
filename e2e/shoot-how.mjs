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
await p.goto(`${F}/how-it-works`, { waitUntil: "load" })
await p.waitForTimeout(1200)
const overlay = await p.locator("vite-error-overlay").count()
console.log("vite overlay:", overlay)
await p.screenshot({ path: `${OUT}/40-how-top.png` })
console.log("40-how-top.png")

// scroll-sweep to arm in-view animations, then capture two module sections
const tot = await p.evaluate(() => document.body.scrollHeight)
for (let y = 0; y <= tot; y += 320) { await p.evaluate((yy) => scrollTo(0, yy), y); await p.waitForTimeout(80) }
await p.evaluate(() => scrollTo(0, 0)); await p.waitForTimeout(400)

async function shotModule(text, file) {
  try {
    const t = p.getByText(text, { exact: false }).first()
    await t.scrollIntoViewIfNeeded(); await p.waitForTimeout(600)
    await p.evaluate(() => window.scrollBy(0, -120)); await p.waitForTimeout(500)
    await p.screenshot({ path: `${OUT}/${file}` })
    console.log(file)
  } catch (e) { console.log("MISS", text, String(e).slice(0, 60)) }
}
await shotModule("a unique sheet per student", "41-how-generate.png")
await shotModule("never guessed", "42-how-grade.png")
await p.screenshot({ path: `${OUT}/43-how-full.png`, fullPage: true })
console.log("43-how-full.png")

await ctx.close(); await b.close()
console.log("DONE")
